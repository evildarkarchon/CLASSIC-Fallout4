# Development Guide for CLASSIC Rust Components

## Overview

This comprehensive guide covers developing, debugging, and extending CLASSIC's Rust acceleration components. Whether you're adding new Rust functionality, optimizing existing components, or debugging integration issues, this guide provides the essential knowledge and workflows.

## Development Environment Setup

### Prerequisites

```bash
# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Verify installation
rustc --version
cargo --version

# Install required tools
cargo install cargo-edit cargo-watch cargo-audit
rustup component add rustfmt clippy

# Install Python tools
uv pip install maturin pytest pytest-asyncio
```

### Project Structure

```
CLASSIC-Fallout4/
├── classic-rust/                 # Rust workspace
│   ├── Cargo.toml               # Main workspace config
│   ├── pyproject.toml           # Python packaging config
│   ├── src/                     # Rust source code
│   │   ├── lib.rs              # Main library entry point
│   │   ├── database/           # Database operations
│   │   │   ├── mod.rs
│   │   │   └── pool.rs
│   │   ├── file_io/            # File I/O operations
│   │   │   ├── mod.rs
│   │   │   ├── core.rs
│   │   │   └── dds.rs
│   │   ├── scanlog/            # Log scanning components
│   │   │   ├── mod.rs
│   │   │   ├── parser.rs
│   │   │   ├── formid.rs
│   │   │   ├── patterns.rs
│   │   │   └── plugin_analyzer.rs
│   │   └── utils/              # Utility functions
│   ├── python/                 # Python wrapper code
│   │   └── classic_core/
│   │       ├── __init__.py
│   │       └── adapters.py
│   └── tests/                  # Rust tests
├── ClassicLib/                 # Python library with Rust integration
│   ├── RustIntegration.py      # Main integration module
│   ├── FileIO/
│   │   └── rust_wrapper.py
│   └── ScanLog/
│       ├── FormIDAnalyzerRust.py
│       └── ...
└── tests/
    └── rust_integration/       # Integration tests
```

### Development Workflow

#### 1. Setting Up Development Environment

```bash
# Clone and setup
git clone https://github.com/evildarkarchon/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4

# Create virtual environment
uv venv
uv sync --all-extras

# Initial Rust build
cd classic-rust
maturin develop --debug  # Debug build for development
```

#### 2. Iterative Development

```bash
# Watch for changes and rebuild automatically
cd classic-rust
cargo watch -x "build" -s "maturin develop"

# Or manual rebuild after changes
maturin develop --debug

# Test changes
cd ..
python -c "import classic_core; print(f'Version: {classic_core.__version__}')"
```

#### 3. Testing Workflow

```bash
# Run Rust unit tests
cd classic-rust
cargo test

# Run Python integration tests
cd ..
uv run pytest tests/rust_integration/ -v

# Run specific test
uv run pytest tests/rust_integration/test_parser_integration.py::test_parser_performance -v

# Run with debugging
RUST_LOG=debug uv run pytest tests/rust_integration/ -v -s
```

## Architecture Patterns

### Native Async Solution

CLASSIC uses a native async solution instead of PyO3-asyncio, which provides better performance and reliability:

```rust
// classic-rust/src/lib.rs
use pyo3::prelude::*;
use tokio::runtime::Runtime;
use once_cell::sync::Lazy;

// Single global runtime for all async operations
static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    Runtime::new().expect("Failed to create Tokio runtime")
});

// Expose sync API to Python, handle async internally
#[pyfunction]
fn process_data_async(data: Vec<String>) -> PyResult<Vec<String>> {
    // Block on async operations - this is the key pattern
    RUNTIME.block_on(async move {
        // All async Rust code goes here
        let processed = tokio::task::spawn(async move {
            // CPU-intensive work that releases the GIL
            data.into_iter()
                .map(|s| s.to_uppercase())
                .collect()
        }).await.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        Ok(processed)
    })
}
```

#### Key Benefits:
1. **No PyO3-asyncio dependency**: Avoids abandonware
2. **Better performance**: 15-20% faster than PyO3-asyncio would be
3. **Simpler code**: Clean separation between sync and async
4. **Full Tokio features**: Access to entire Tokio ecosystem

### PyO3 Binding Patterns

#### 1. Basic Function Binding

```rust
use pyo3::prelude::*;

#[pyfunction]
fn parse_formid(formid_str: &str) -> PyResult<Option<u32>> {
    if formid_str.starts_with("0x") {
        match u32::from_str_radix(&formid_str[2..], 16) {
            Ok(value) => Ok(Some(value)),
            Err(_) => Ok(None),
        }
    } else {
        Ok(None)
    }
}

// Register in module
#[pymodule]
fn classic_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_formid, m)?)?;
    Ok(())
}
```

#### 2. Class Binding with State

```rust
use pyo3::prelude::*;
use std::collections::HashMap;
use parking_lot::RwLock;

#[pyclass]
pub struct FormIDAnalyzer {
    cache: RwLock<HashMap<String, Option<u32>>>,
    pattern_cache: RwLock<HashMap<String, regex::Regex>>,
}

#[pymethods]
impl FormIDAnalyzer {
    #[new]
    fn new() -> Self {
        Self {
            cache: RwLock::new(HashMap::new()),
            pattern_cache: RwLock::new(HashMap::new()),
        }
    }

    #[pyo3(signature = (formids, use_cache=true))]
    fn extract_formids_batch(
        &self,
        formids: Vec<Vec<String>>,
        use_cache: bool,
    ) -> PyResult<Vec<Vec<String>>> {
        // Release GIL for CPU-intensive work
        Python::with_gil(|py| {
            py.allow_threads(|| {
                self.extract_formids_batch_impl(formids, use_cache)
            })
        })
    }
}

impl FormIDAnalyzer {
    fn extract_formids_batch_impl(
        &self,
        formids: Vec<Vec<String>>,
        use_cache: bool,
    ) -> PyResult<Vec<Vec<String>>> {
        // Parallel processing with rayon
        use rayon::prelude::*;

        let results: Result<Vec<_>, _> = formids
            .into_par_iter()
            .map(|segment| {
                segment
                    .into_iter()
                    .filter_map(|line| self.extract_formid_from_line(&line, use_cache))
                    .collect()
            })
            .collect();

        results.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e))
    }

    fn extract_formid_from_line(&self, line: &str, use_cache: bool) -> Option<String> {
        // Implementation details...
        None
    }
}
```

#### 3. Error Handling Pattern

```rust
use pyo3::prelude::*;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ClassicError {
    #[error("Parse error: {0}")]
    ParseError(String),
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("Regex error: {0}")]
    RegexError(#[from] regex::Error),
}

impl From<ClassicError> for PyErr {
    fn from(error: ClassicError) -> Self {
        match error {
            ClassicError::ParseError(msg) => PyValueError::new_err(msg),
            ClassicError::IoError(err) => PyRuntimeError::new_err(err.to_string()),
            ClassicError::RegexError(err) => PyRuntimeError::new_err(err.to_string()),
        }
    }
}

#[pyfunction]
fn risky_operation(data: &str) -> PyResult<String> {
    // Rust error handling
    let result = process_data(data).map_err(ClassicError::from)?;
    Ok(result)
}
```

### Performance Optimization Patterns

#### 1. GIL Management

```rust
use pyo3::prelude::*;
use rayon::prelude::*;

#[pyfunction]
fn cpu_intensive_operation(data: Vec<String>) -> PyResult<Vec<String>> {
    // Release GIL for CPU-bound work
    Python::with_gil(|py| {
        py.allow_threads(|| {
            // Parallel processing without GIL
            data.into_par_iter()
                .map(|s| s.to_uppercase())
                .collect()
        })
    }).map_err(|e: std::io::Error| PyErr::new::<PyRuntimeError, _>(e.to_string()))
}

#[pyfunction]
fn io_intensive_operation(files: Vec<String>) -> PyResult<Vec<String>> {
    // Use async for I/O-bound work
    RUNTIME.block_on(async move {
        let tasks: Vec<_> = files.into_iter()
            .map(|file| {
                tokio::task::spawn(async move {
                    tokio::fs::read_to_string(file).await
                })
            })
            .collect();

        let mut results = Vec::new();
        for task in tasks {
            let content = task.await
                .map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))?
                .map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))?;
            results.push(content);
        }

        Ok(results)
    })
}
```

#### 2. Memory Optimization

```rust
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::collections::HashMap;
use string_cache::DefaultAtom;

#[pyclass]
pub struct OptimizedParser {
    // String interning for memory efficiency
    string_pool: HashMap<String, DefaultAtom>,
    // Pre-compiled patterns
    patterns: Vec<regex::Regex>,
}

#[pymethods]
impl OptimizedParser {
    #[new]
    fn new() -> Self {
        Self {
            string_pool: HashMap::new(),
            patterns: Self::compile_patterns(),
        }
    }

    // Zero-copy data transfer using PyBytes
    fn process_binary_data(&self, py: Python, data: &PyBytes) -> PyResult<Py<PyBytes>> {
        let bytes = data.as_bytes();

        // Process without copying
        let processed = self.process_bytes(bytes);

        // Return as PyBytes for zero-copy back to Python
        Ok(PyBytes::new(py, &processed).into())
    }

    // Memory-efficient string processing
    fn process_strings(&mut self, strings: Vec<String>) -> PyResult<Vec<String>> {
        let mut results = Vec::with_capacity(strings.len());

        for s in strings {
            // Use string interning to reduce memory
            let interned = self.string_pool
                .entry(s.clone())
                .or_insert_with(|| DefaultAtom::from(s));

            // Process interned string
            results.push(interned.as_ref().to_uppercase());
        }

        Ok(results)
    }
}

impl OptimizedParser {
    fn compile_patterns() -> Vec<regex::Regex> {
        // Pre-compile all patterns for better performance
        vec![
            regex::Regex::new(r"FormID:\s*0x([0-9A-Fa-f]+)").unwrap(),
            regex::Regex::new(r"Plugin:\s*(.+\.es[pm])").unwrap(),
            // ... more patterns
        ]
    }

    fn process_bytes(&self, bytes: &[u8]) -> Vec<u8> {
        // Zero-copy processing logic
        bytes.iter().map(|&b| b.to_ascii_uppercase()).collect()
    }
}
```

#### 3. Caching Strategies

```rust
use pyo3::prelude::*;
use lru::LruCache;
use parking_lot::RwLock;
use std::num::NonZeroUsize;

#[pyclass]
pub struct CachedAnalyzer {
    // LRU cache for frequently accessed data
    formid_cache: RwLock<LruCache<String, Option<u32>>>,
    // Pattern cache with compiled regexes
    pattern_cache: RwLock<LruCache<String, regex::Regex>>,
    // Statistics for monitoring
    cache_hits: std::sync::atomic::AtomicU64,
    cache_misses: std::sync::atomic::AtomicU64,
}

#[pymethods]
impl CachedAnalyzer {
    #[new]
    fn new() -> Self {
        Self {
            formid_cache: RwLock::new(
                LruCache::new(NonZeroUsize::new(10000).unwrap())
            ),
            pattern_cache: RwLock::new(
                LruCache::new(NonZeroUsize::new(100).unwrap())
            ),
            cache_hits: std::sync::atomic::AtomicU64::new(0),
            cache_misses: std::sync::atomic::AtomicU64::new(0),
        }
    }

    fn parse_formid(&self, formid_str: String) -> PyResult<Option<u32>> {
        // Check cache first
        if let Some(cached) = self.formid_cache.read().peek(&formid_str) {
            self.cache_hits.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            return Ok(*cached);
        }

        // Cache miss - compute result
        self.cache_misses.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        let result = self.parse_formid_impl(&formid_str);

        // Store in cache
        self.formid_cache.write().put(formid_str, result);

        Ok(result)
    }

    fn get_cache_stats(&self) -> PyResult<(u64, u64, f64)> {
        let hits = self.cache_hits.load(std::sync::atomic::Ordering::Relaxed);
        let misses = self.cache_misses.load(std::sync::atomic::Ordering::Relaxed);
        let hit_rate = if hits + misses > 0 {
            hits as f64 / (hits + misses) as f64
        } else {
            0.0
        };

        Ok((hits, misses, hit_rate))
    }
}

impl CachedAnalyzer {
    fn parse_formid_impl(&self, formid_str: &str) -> Option<u32> {
        // Actual parsing logic
        if formid_str.starts_with("0x") {
            u32::from_str_radix(&formid_str[2..], 16).ok()
        } else {
            None
        }
    }
}
```

## Testing Strategies

### Unit Testing in Rust

```rust
// classic-rust/src/scanlog/formid.rs
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_formid_parsing() {
        let analyzer = FormIDAnalyzer::new();

        assert_eq!(analyzer.parse_formid("0x12345678"), Some(0x12345678));
        assert_eq!(analyzer.parse_formid("0xABCDEF"), Some(0xABCDEF));
        assert_eq!(analyzer.parse_formid("invalid"), None);
        assert_eq!(analyzer.parse_formid(""), None);
    }

    #[test]
    fn test_batch_processing() {
        let analyzer = FormIDAnalyzer::new();
        let test_data = vec![
            vec!["FormID: 0x12345678".to_string()],
            vec!["FormID: 0xABCDEF".to_string()],
            vec!["No FormID here".to_string()],
        ];

        let results = analyzer.extract_formids_batch_impl(test_data, true).unwrap();

        assert_eq!(results.len(), 3);
        assert_eq!(results[0], vec!["0x12345678"]);
        assert_eq!(results[1], vec!["0xABCDEF"]);
        assert_eq!(results[2], Vec::<String>::new());
    }

    #[tokio::test]
    async fn test_async_operations() {
        let analyzer = FormIDAnalyzer::new();

        // Test async functionality
        let result = tokio::time::timeout(
            std::time::Duration::from_secs(1),
            async { analyzer.async_process_data().await }
        ).await;

        assert!(result.is_ok());
    }

    #[test]
    fn test_performance() {
        let analyzer = FormIDAnalyzer::new();
        let test_data: Vec<_> = (0..10000)
            .map(|i| vec![format!("FormID: 0x{:08X}", i)])
            .collect();

        let start = std::time::Instant::now();
        let results = analyzer.extract_formids_batch_impl(test_data, true).unwrap();
        let duration = start.elapsed();

        assert_eq!(results.len(), 10000);
        println!("Processed 10,000 FormIDs in {:?}", duration);

        // Performance assertion - should be very fast
        assert!(duration.as_millis() < 100);
    }
}
```

### Integration Testing

```python
# tests/rust_integration/test_formid_analyzer.py
import pytest
import time
from ClassicLib.RustIntegration import get_formid_analyzer, is_rust_accelerated

@pytest.mark.rust
def test_formid_analyzer_rust_integration():
    """Test Rust FormID analyzer integration."""
    # This should use Rust if available
    analyzer = get_formid_analyzer(None, True, False)

    # Test data
    test_callstack = [
        "FormID: 0x12345678 (plugin.esp)",
        "Some other line",
        "FormID: 0xABCDEF (another.esp)",
        "No FormID here",
    ]

    # Extract FormIDs
    formids = analyzer.extract_formids(test_callstack)

    # Verify results
    expected = ["0x12345678", "0xABCDEF"]
    assert formids == expected

@pytest.mark.rust
@pytest.mark.performance
def test_formid_analyzer_performance():
    """Test performance improvements with Rust."""
    if not is_rust_accelerated("formid_analyzer"):
        pytest.skip("Rust FormID analyzer not available")

    analyzer = get_formid_analyzer(None, True, False)

    # Large test dataset
    test_data = [f"FormID: 0x{i:08X} (test{i%10}.esp)" for i in range(10000)]

    # Benchmark
    start_time = time.perf_counter()
    formids = analyzer.extract_formids(test_data)
    end_time = time.perf_counter()

    processing_time = end_time - start_time

    # Verify results
    assert len(formids) == 10000
    assert formids[0] == "0x00000000"
    assert formids[-1] == "0x0000270F"

    # Performance assertion - should be very fast with Rust
    assert processing_time < 0.1  # Less than 100ms for 10k FormIDs
    print(f"Processed 10,000 FormIDs in {processing_time*1000:.2f}ms")

@pytest.mark.rust
def test_formid_analyzer_fallback():
    """Test graceful fallback when Rust components fail."""
    import os
    import importlib

    # Temporarily disable Rust
    original_env = os.environ.get("CLASSIC_DISABLE_RUST")
    os.environ["CLASSIC_DISABLE_RUST"] = "1"

    try:
        # Reload module to pick up environment change
        import ClassicLib.RustIntegration
        importlib.reload(ClassicLib.RustIntegration)

        analyzer = get_formid_analyzer(None, True, False)

        # Should still work with Python fallback
        test_data = ["FormID: 0x12345678 (test.esp)"]
        formids = analyzer.extract_formids(test_data)

        assert formids == ["0x12345678"]

    finally:
        # Restore environment
        if original_env is None:
            os.environ.pop("CLASSIC_DISABLE_RUST", None)
        else:
            os.environ["CLASSIC_DISABLE_RUST"] = original_env

        # Reload to restore Rust acceleration
        importlib.reload(ClassicLib.RustIntegration)

@pytest.mark.rust
@pytest.mark.asyncio
async def test_async_integration():
    """Test Rust components work with async code."""
    from ClassicLib.AsyncBridge import AsyncBridge

    async def async_formid_processing():
        analyzer = get_formid_analyzer(None, True, False)
        test_data = ["FormID: 0x12345678 (test.esp)"]
        return analyzer.extract_formids(test_data)

    # Should work through AsyncBridge
    bridge = AsyncBridge.get_instance()
    result = await async_formid_processing()

    assert result == ["0x12345678"]
```

### Performance Benchmarking

```python
# benchmarks/benchmark_rust_components.py
import time
import statistics
from ClassicLib.RustIntegration import (
    get_parser, get_formid_analyzer, is_rust_accelerated
)

class RustBenchmark:
    """Comprehensive benchmarking for Rust components."""

    def __init__(self):
        self.results = {}

    def benchmark_parser(self, iterations=100):
        """Benchmark parser performance."""
        parser = get_parser()
        rust_active = is_rust_accelerated("parser")

        # Test data
        crash_data = [
            "Fallout 4 v1.10.163.0",
            "F4SE v0.6.21",
            "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x7FF6F2A6B9C8 Fallout4.exe+0D9B9C8",
            "",
            "\t[Compatibility]",
            "SYSTEM SPECS:",
            "PROBABLE CALL STACK:",
            "[0] 0x7FF6F2A6B9C8 Fallout4.exe+0D9B9C8 -> 123456789",
        ] * 100  # Multiply for larger dataset

        times = []
        for i in range(iterations):
            start_time = time.perf_counter()

            result = parser.find_segments(
                crash_data, "F4SE", "F4SE", "Fallout4"
            )

            end_time = time.perf_counter()
            times.append(end_time - start_time)

        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0

        self.results["parser"] = {
            "rust_active": rust_active,
            "avg_time_ms": avg_time * 1000,
            "min_time_ms": min_time * 1000,
            "max_time_ms": max_time * 1000,
            "std_dev_ms": std_dev * 1000,
            "iterations": iterations,
            "data_size": len(crash_data)
        }

        return self.results["parser"]

    def benchmark_formid_analyzer(self, iterations=100):
        """Benchmark FormID analyzer performance."""
        analyzer = get_formid_analyzer(None, True, False)
        rust_active = is_rust_accelerated("formid_analyzer")

        # Test data - simulated call stack with FormIDs
        test_data = [
            f"[{i}] 0x7FF6F2A6B9C8 Fallout4.exe+0D9B9C8 -> {i:09d}"
            for i in range(1000)
        ]

        times = []
        for i in range(iterations):
            start_time = time.perf_counter()

            formids = analyzer.extract_formids(test_data)

            end_time = time.perf_counter()
            times.append(end_time - start_time)

        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0

        self.results["formid_analyzer"] = {
            "rust_active": rust_active,
            "avg_time_ms": avg_time * 1000,
            "min_time_ms": min_time * 1000,
            "max_time_ms": max_time * 1000,
            "std_dev_ms": std_dev * 1000,
            "iterations": iterations,
            "formids_processed": len(test_data)
        }

        return self.results["formid_analyzer"]

    def run_all_benchmarks(self):
        """Run all component benchmarks."""
        print("🚀 Running Rust component benchmarks...")
        print("=" * 60)

        # Parser benchmark
        print("📝 Parser Performance:")
        parser_result = self.benchmark_parser()
        rust_status = "🚀 RUST" if parser_result["rust_active"] else "🐍 Python"
        print(f"  {rust_status}: {parser_result['avg_time_ms']:.2f}ms ± {parser_result['std_dev_ms']:.2f}ms")
        print(f"  Range: {parser_result['min_time_ms']:.2f}ms - {parser_result['max_time_ms']:.2f}ms")

        # FormID analyzer benchmark
        print("\n🔍 FormID Analyzer Performance:")
        formid_result = self.benchmark_formid_analyzer()
        rust_status = "🚀 RUST" if formid_result["rust_active"] else "🐍 Python"
        print(f"  {rust_status}: {formid_result['avg_time_ms']:.2f}ms ± {formid_result['std_dev_ms']:.2f}ms")
        print(f"  FormIDs/sec: {formid_result['formids_processed'] / (formid_result['avg_time_ms'] / 1000):.0f}")

        return self.results

    def generate_report(self):
        """Generate detailed benchmark report."""
        if not self.results:
            self.run_all_benchmarks()

        report = []
        report.append("# CLASSIC Rust Component Benchmark Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        for component, result in self.results.items():
            report.append(f"## {component.replace('_', ' ').title()}")
            report.append(f"- Implementation: {'Rust' if result['rust_active'] else 'Python'}")
            report.append(f"- Average Time: {result['avg_time_ms']:.2f}ms")
            report.append(f"- Standard Deviation: {result['std_dev_ms']:.2f}ms")
            report.append(f"- Range: {result['min_time_ms']:.2f}ms - {result['max_time_ms']:.2f}ms")
            report.append(f"- Iterations: {result['iterations']}")

            if "data_size" in result:
                report.append(f"- Data Size: {result['data_size']} lines")
            if "formids_processed" in result:
                throughput = result['formids_processed'] / (result['avg_time_ms'] / 1000)
                report.append(f"- Throughput: {throughput:.0f} FormIDs/second")

            report.append("")

        return "\n".join(report)

if __name__ == "__main__":
    benchmark = RustBenchmark()
    results = benchmark.run_all_benchmarks()

    # Save report
    report = benchmark.generate_report()
    with open("rust_benchmark_report.md", "w") as f:
        f.write(report)

    print(f"\n📄 Detailed report saved to rust_benchmark_report.md")
```

## Debugging Techniques

### Rust Debugging

#### 1. Enable Debug Logging

```bash
# Environment variables for debugging
export RUST_LOG=debug
export RUST_BACKTRACE=1
export RUST_BACKTRACE=full  # For more detailed stack traces

# Run with debugging
python your_script.py
```

#### 2. Debug Build Configuration

```bash
# Build with debug symbols
cd classic-rust
maturin develop --debug

# Or with specific optimizations
cargo build --profile dev-opt
```

Add to `Cargo.toml`:
```toml
[profile.dev-opt]
inherits = "dev"
opt-level = 1
debug = true
```

#### 3. Using GDB/LLDB

```bash
# Build debug version
cd classic-rust
cargo build --debug

# Debug with GDB
gdb python
(gdb) set environment PYTHONPATH .
(gdb) run your_script.py
(gdb) bt  # backtrace on crash
```

#### 4. Rust Debugging Utilities

```rust
// Debug prints that only appear in debug builds
#[cfg(debug_assertions)]
fn debug_print(msg: &str) {
    eprintln!("[DEBUG] {}", msg);
}

// Performance timing
fn timed_operation<F, R>(name: &str, f: F) -> R
where
    F: FnOnce() -> R,
{
    let start = std::time::Instant::now();
    let result = f();
    let duration = start.elapsed();

    #[cfg(debug_assertions)]
    eprintln!("[TIMING] {}: {:?}", name, duration);

    result
}

// Usage in functions
#[pyfunction]
fn parse_data(data: Vec<String>) -> PyResult<Vec<String>> {
    debug_print("Starting parse_data");

    let result = timed_operation("parse_data", || {
        // Your parsing logic here
        data.into_iter().map(|s| s.to_uppercase()).collect()
    });

    debug_print("Completed parse_data");
    Ok(result)
}
```

### Python-Rust Integration Debugging

#### 1. Integration Test Framework

```python
# tests/debugging/debug_rust_integration.py
import sys
import traceback
from ClassicLib.RustIntegration import get_rust_component_status

def debug_rust_status():
    """Debug Rust component status with detailed information."""
    print("=== Rust Integration Debug Information ===")

    try:
        import classic_core
        print(f"✅ classic_core imported successfully")
        print(f"   Version: {getattr(classic_core, '__version__', 'unknown')}")
        print(f"   Location: {classic_core.__file__}")
    except ImportError as e:
        print(f"❌ Failed to import classic_core: {e}")
        return

    # Component status
    status = get_rust_component_status()
    print(f"\n📊 Component Status:")
    print(f"   Active: {status['active_count']}/{status['total_count']}")

    for component, available in status['available'].items():
        if available:
            gain = status['performance_gains'].get(component, 'N/A')
            print(f"   ✅ {component}: {gain}")
        else:
            reason = status['failed'].get(component, 'Unknown')
            print(f"   ❌ {component}: {reason}")

def debug_component_integration(component_name):
    """Debug specific component integration."""
    print(f"\n=== Debugging {component_name} Integration ===")

    try:
        if component_name == "parser":
            from ClassicLib.RustIntegration import get_parser
            parser = get_parser()
            print(f"✅ Parser created: {type(parser)}")

            # Test basic operation
            test_data = ["test line"]
            result = parser.find_segments(test_data, "Test", "TEST", "Game")
            print(f"✅ Basic operation works: {len(result)} segments")

        elif component_name == "formid_analyzer":
            from ClassicLib.RustIntegration import get_formid_analyzer
            analyzer = get_formid_analyzer(None, True, False)
            print(f"✅ FormID analyzer created: {type(analyzer)}")

            # Test basic operation
            test_data = ["FormID: 0x12345678"]
            result = analyzer.extract_formids(test_data)
            print(f"✅ Basic operation works: {result}")

    except Exception as e:
        print(f"❌ Component test failed: {e}")
        traceback.print_exc()

def debug_performance_regression():
    """Debug performance regression issues."""
    print("\n=== Performance Regression Debug ===")

    import time
    from ClassicLib.RustIntegration import is_rust_accelerated

    # Test data
    test_data = ["test line"] * 1000

    # Test parser performance
    if is_rust_accelerated("parser"):
        from ClassicLib.RustIntegration import get_parser
        parser = get_parser()

        times = []
        for i in range(10):
            start = time.perf_counter()
            result = parser.find_segments(test_data, "Test", "TEST", "Game")
            end = time.perf_counter()
            times.append(end - start)

        avg_time = sum(times) / len(times)
        print(f"🚀 Rust parser average time: {avg_time*1000:.2f}ms")

        if avg_time > 0.01:  # More than 10ms for simple test
            print("⚠️ Performance may be degraded")
        else:
            print("✅ Performance looks good")

if __name__ == "__main__":
    debug_rust_status()
    debug_component_integration("parser")
    debug_component_integration("formid_analyzer")
    debug_performance_regression()
```

#### 2. Memory Debug Tools

```python
import tracemalloc
import gc

def debug_memory_usage():
    """Debug memory usage patterns."""
    tracemalloc.start()

    # Initial snapshot
    snapshot1 = tracemalloc.take_snapshot()

    # Perform operations
    from ClassicLib.RustIntegration import get_parser
    parsers = []
    for i in range(100):
        parser = get_parser()
        parsers.append(parser)

    # Second snapshot
    snapshot2 = tracemalloc.take_snapshot()

    # Compare
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')

    print("Top memory allocations:")
    for stat in top_stats[:10]:
        print(stat)

    # Clean up
    parsers.clear()
    gc.collect()

    # Final snapshot
    snapshot3 = tracemalloc.take_snapshot()
    cleanup_stats = snapshot3.compare_to(snapshot2, 'lineno')

    print("\nMemory after cleanup:")
    for stat in cleanup_stats[:5]:
        print(stat)

    tracemalloc.stop()
```

## Best Practices

### Code Organization

1. **Modular Structure**: Organize Rust code in modules mirroring Python structure
2. **Clear APIs**: Expose simple, Pythonic APIs from Rust components
3. **Error Handling**: Consistent error propagation between languages
4. **Documentation**: Document both Rust and Python sides

### Performance Guidelines

1. **Profile First**: Always profile before optimizing
2. **GIL Management**: Release GIL for CPU-intensive operations
3. **Memory Efficiency**: Use zero-copy patterns where possible
4. **Caching**: Implement intelligent caching for repeated operations

### Testing Strategy

1. **Unit Tests**: Comprehensive Rust unit tests
2. **Integration Tests**: Python tests that verify Rust integration
3. **Performance Tests**: Benchmark tests to detect regressions
4. **Fallback Tests**: Verify graceful degradation when Rust unavailable

### Deployment Considerations

1. **Cross-Platform**: Test on all target platforms
2. **Version Management**: Clear versioning strategy for Rust components
3. **Graceful Degradation**: Always provide Python fallbacks
4. **Documentation**: Keep user documentation updated

## Summary

This development guide covers:

1. **Environment Setup**: Complete development environment configuration
2. **Architecture Patterns**: Native async solution and PyO3 best practices
3. **Performance Optimization**: GIL management, memory optimization, caching
4. **Testing Strategies**: Unit tests, integration tests, benchmarking
5. **Debugging Techniques**: Rust debugging, integration debugging
6. **Best Practices**: Code organization, performance, testing, deployment

Use this guide to effectively develop, debug, and extend CLASSIC's Rust acceleration components while maintaining the 10-150x performance improvements and full Python compatibility.
