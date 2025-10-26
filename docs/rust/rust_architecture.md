# CLASSIC Rust Architecture Documentation

## Overview

CLASSIC uses a hybrid Python-Rust architecture to achieve high performance while maintaining ease of development. The Rust components provide optimized implementations of performance-critical operations, exposed to Python through PyO3 bindings.

## Key Architectural Decisions

### Native Async Solution (No PyO3-asyncio)

**Important:** This project does NOT use PyO3-asyncio (which is abandonware and incompatible with modern PyO3 versions). Instead, we use a native async solution with the following pattern:

```rust
// Global Tokio runtime for all async operations
static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    Runtime::new().expect("Failed to create Tokio runtime")
});

// Expose sync API to Python, use async internally
#[pymethods]
impl MyClass {
    fn sync_method(&self) -> PyResult<String> {
        // Block on async operation internally
        RUNTIME.block_on(async move {
            // Async operations here
            async_operation().await
        })
    }
}
```

### Benefits of This Approach

1. **No External Dependencies**: Avoids abandonware PyO3-asyncio
2. **Clean API**: Python sees simple sync methods, complexity hidden in Rust
3. **True Parallelism**: Can release GIL and use Tokio's full async capabilities
4. **Performance**: Internal async operations can run concurrently
5. **Compatibility**: Works with all PyO3 versions

## Module Structure

```
classic-rust/
├── src/
│   ├── lib.rs              # Main module entry point and registration
│   ├── database/           # Database operations with connection pooling
│   │   ├── mod.rs
│   │   └── pool.rs         # RustDatabasePool implementation
│   ├── file_io/            # High-performance file operations
│   │   ├── mod.rs
│   │   ├── core.rs         # RustFileIOCore with async I/O
│   │   └── encoding.rs     # Encoding detection utilities
│   ├── scanlog/            # Log scanning and pattern matching
│   │   ├── mod.rs
│   │   ├── formid.rs       # FormID extraction and validation
│   │   ├── formid_analyzer.rs # FormIDAnalyzerCore port
│   │   ├── mod_detector.rs # Mod detection patterns
│   │   ├── parser.rs       # Log parsing utilities
│   │   ├── patterns.rs     # Pattern matching engine
│   │   ├── plugin_analyzer.rs # Plugin analysis
│   │   ├── record_scanner.rs # Record scanning
│   │   └── test_class.rs   # Testing utilities
│   └── utils/              # Core utilities
│       ├── mod.rs
│       ├── errors.rs       # Error types and handling
│       ├── log_processing.rs # Log processing utilities
│       ├── path.rs         # Path handling with caching
│       ├── performance.rs  # Performance monitoring
│       └── strings.rs      # String optimization utilities
```

## Core Modules

### 1. Database Module (`database/`)

**Purpose**: Provides high-performance SQLite operations with connection pooling and caching.

**Key Components**:
- `RustDatabasePool`: Connection pool with automatic management
- Query result caching with DashMap
- Async operations internally, sync API to Python
- WAL mode and optimized pragmas for performance

**Performance Features**:
- Connection reuse to avoid overhead
- Query result caching
- Batch operations support
- Parallel query execution with Tokio

### 2. File I/O Module (`file_io/`)

**Purpose**: High-performance file operations with encoding detection and caching.

**Key Components**:
- `RustFileIOCore`: Main file I/O operations
- `EncodingDetector`: Automatic encoding detection
- LRU cache for recently read files
- Memory-mapped file support for large files

**Performance Features**:
- Async I/O with Tokio
- Read caching with LRU eviction
- Batch file operations
- Parallel directory traversal

### 3. ScanLog Module (`scanlog/`)

**Purpose**: Core log scanning functionality with pattern matching and analysis.

**Key Components**:
- `FormIDAnalyzer`: Legacy FormID analyzer (being replaced)
- `FormIDAnalyzerCore`: High-performance FormID extraction and validation
- `ModDetector`: Mod detection with single/double word patterns
- `LogParser`: Segment-based log parsing
- `PatternMatcher`: Regex pattern matching with caching
- `PluginAnalyzer`: Plugin detection and analysis
- `RecordScanner`: Call stack record scanning

**Performance Features**:
- Precompiled regex patterns with lazy_static
- Parallel processing with Rayon
- Pattern caching with DashMap
- Batch operations for multiple logs

### 4. Utils Module (`utils/`)

**Purpose**: Foundational utilities optimized for crash log processing.

**Key Components**:
- `StringProcessor`: String manipulation optimized for logs
- `PathHandler`: Path operations with validation and caching
- `LogProcessor`: Specialized log processing utilities
- `RustPerformanceMonitor`: Performance tracking
- `ClassicError`/`ClassicResult`: Error handling types

**Performance Features**:
- String interning for memory efficiency
- Path caching to avoid repeated validation
- Zero-copy string operations where possible

## Async Architecture Pattern

### The Block-On Pattern

All Rust modules follow a consistent pattern for async operations:

```rust
use tokio::runtime::Runtime;
use once_cell::sync::Lazy;

// Single global runtime shared by all modules
static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    Runtime::new().expect("Failed to create Tokio runtime")
});

#[pyclass]
struct MyClass {
    // Internal state
}

#[pymethods]
impl MyClass {
    // Sync method exposed to Python
    fn process(&self, data: String) -> PyResult<String> {
        // Use the global runtime to run async code
        RUNTIME.block_on(async move {
            // Async operations here
            let result = async_operation(data).await?;
            Ok(result)
        })
    }
}
```

### Benefits Over PyO3-asyncio

1. **Simplicity**: No complex async/await bridging between Python and Rust
2. **Performance**: Can use full Tokio ecosystem without limitations
3. **Maintenance**: No dependency on abandoned libraries
4. **Compatibility**: Works with any PyO3 version
5. **GIL Management**: Can easily release GIL for CPU-bound operations

### GIL Release Pattern

For CPU-intensive operations, we release the GIL:

```rust
fn cpu_intensive_operation(&self, data: Vec<String>) -> Vec<String> {
    Python::with_gil(|py| {
        // Release GIL for parallel processing
        py.allow_threads(|| {
            // Use Rayon for parallel computation
            data.par_iter()
                .map(|item| process_item(item))
                .collect()
        })
    })
}
```

## Performance Optimizations

### 1. Caching Strategies

- **LRU Caches**: For frequently accessed data with size limits
- **DashMap**: Concurrent hash map for thread-safe caching
- **Once_cell/Lazy**: For one-time initialization of expensive resources

### 2. Parallel Processing

- **Rayon**: Data parallelism for CPU-bound operations
- **Tokio**: Task parallelism for I/O-bound operations
- **Crossbeam**: Low-level concurrency primitives

### 3. Memory Optimization

- **String Interning**: Reuse common strings
- **SmartString**: Small string optimization
- **Zero-Copy Operations**: Use references where possible
- **Memory Mapping**: For large file operations

### 4. Pattern Matching

- **Precompiled Regex**: Compile once, use many times
- **Aho-Corasick**: Efficient multi-pattern matching
- **Memchr**: SIMD-accelerated byte searching

## Integration with Python

### Module Registration

All Rust modules are registered in `lib.rs`:

```rust
#[pymodule]
fn classic_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register classes
    m.add_class::<FileReader>()?;
    m.add_class::<FormIDProcessor>()?;

    // Register submodules
    let utils_module = PyModule::new_bound(m.py(), "utils")?;
    utils::register_module(&utils_module)?;
    m.add_submodule(&utils_module)?;

    Ok(())
}
```

### Python Usage

```python
import classic_core

# Use Rust implementations directly
file_reader = classic_core.FileReader()
content = file_reader.read_file("path/to/file.txt")

# Or use through submodules
from classic_core.scanlog import FormIDAnalyzerCore
analyzer = FormIDAnalyzerCore(yamldata, show_formid_values=True)
```

### Backward Compatibility

Python code can seamlessly use Rust implementations:

```python
try:
    # Try to import Rust implementation
    from classic_core.file_io import RustFileIOCore as FileIOCore
except ImportError:
    # Fall back to Python implementation
    from ClassicLib.FileIOCore import FileIOCore
```

## Building and Development

### Build Requirements

- Rust 1.75+ (for stable async features)
- Python 3.12+ (for abi3 compatibility)
- Maturin for building Python wheels

### Development Workflow

1. **Development Build**:
   ```bash
   maturin develop
   ```

2. **Release Build**:
   ```bash
   maturin build --release
   ```

3. **Run Tests**:
   ```bash
   # Rust tests
   cargo test

   # Python integration tests
   pytest tests/test_rust_integration.py
   ```

### Performance Testing

Use the included benchmarks:

```bash
# Run Rust benchmarks
cargo bench

# Run Python benchmarks
python benchmarks/benchmark_suite.py
```

## Future Improvements

### Planned Enhancements

1. **SIMD Optimizations**: Use explicit SIMD for pattern matching
2. **Custom Allocators**: Experiment with jemalloc or mimalloc
3. **Streaming Parsers**: For handling very large log files
4. **GPU Acceleration**: For massive parallel pattern matching

### Migration Path

The project is following a phased migration plan:
- Phase 1: Foundation and utilities ✅ (Complete)
- Phase 2: Pattern matching engine ✅ (Complete)
- Phase 3: File I/O operations ✅ (Complete)
- Phase 4: Database operations ✅ (Complete)
- Phase 5: String processing (In Progress)
- Phase 6: Integration and optimization (Planned)

## Debugging and Profiling

### Debug Builds

Include debug symbols for profiling:

```toml
[profile.dev]
debug = true
opt-level = 0

[profile.release]
debug = 1  # Include debug info in release builds
```

### Performance Profiling

1. **Rust Side**: Use `cargo flamegraph` or `perf`
2. **Python Side**: Use `py-spy` or `cProfile`
3. **Memory**: Use `valgrind` or `heaptrack`

### Logging

Enable Rust logging:

```python
import os
os.environ['RUST_LOG'] = 'debug'
import classic_core  # Logging now enabled
```

## Best Practices

### Do's

- ✅ Use the global `RUNTIME` for async operations
- ✅ Release GIL for CPU-bound operations
- ✅ Cache expensive computations
- ✅ Use batch operations when possible
- ✅ Profile before optimizing

### Don'ts

- ❌ Don't create multiple Tokio runtimes
- ❌ Don't hold GIL during long operations
- ❌ Don't use PyO3-asyncio (it's abandonware)
- ❌ Don't forget error handling at boundaries
- ❌ Don't optimize prematurely

## Conclusion

The Rust architecture provides significant performance improvements while maintaining clean Python integration. By avoiding PyO3-asyncio and using a native async solution, we achieve better performance, maintainability, and compatibility.
