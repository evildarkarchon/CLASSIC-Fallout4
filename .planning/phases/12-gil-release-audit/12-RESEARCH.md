# Phase 12: GIL Release Audit - Research

**Researched:** 2026-02-04
**Domain:** PyO3 GIL Management, Rust FFI Performance Measurement
**Confidence:** HIGH

## Summary

This phase audits all 18 Python binding crates to ensure proper GIL release during long-running Rust operations. The codebase already has a `without_gil()` helper in `classic-shared-py` that wraps `py.detach()` (PyO3 0.27's renamed `allow_threads`). However, current usage is limited to 9 files, leaving significant FFI operations without GIL release.

The audit will:
1. Identify ALL FFI operations across 18 `-py` crates
2. Measure timing for each operation to determine GIL release candidates (>1ms guideline)
3. Implement `py.detach()` for long-running operations
4. Create permanent Criterion benchmarks that feed into Phase 13 infrastructure
5. Add integration tests proving GIL release allows concurrent Python threads

**Primary recommendation:** Audit systematically by crate, measure first (data-driven), then implement GIL release for operations exceeding 1ms. Create Criterion benchmarks measuring pure Rust compute time separately from FFI overhead.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyO3 | 0.27.2 | Rust-Python bindings | Project already uses, `py.detach()` is canonical GIL release |
| Criterion | 0.5.x | Rust benchmarking | Statistics-driven, permanent baselines, stable API |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| std::time | Rust stdlib | Timing measurements | Quick inline timing for FFI overhead |
| std::hint::black_box | Rust stdlib | Prevent compiler optimization | In benchmarks to ensure work isn't optimized away |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Criterion | divan | Newer, simpler API but less mature ecosystem |
| Manual timing | Built-in test timing | Criterion provides statistical rigor |
| py.detach() | spawn_blocking | py.detach() is simpler, no Tokio dependency in sync code |

**Installation:**
Already in workspace `Cargo.toml`, but for benchmarks:
```toml
[dev-dependencies]
criterion = "0.5.1"

[[bench]]
name = "gil_benchmarks"
harness = false
```

## Architecture Patterns

### Recommended Project Structure

```
rust/python-bindings/
├── classic-scanlog-py/
│   ├── src/
│   │   └── *.rs           # Existing bindings
│   └── benches/
│       └── gil_benchmarks.rs  # NEW: FFI timing benchmarks
├── classic-file-io-py/
│   └── benches/
│       └── gil_benchmarks.rs
└── ... (other -py crates with benchmarks as needed)

tests/rust_integration/
└── gil_release/           # NEW: GIL release verification tests
    ├── test_concurrent_operations.py
    └── conftest.py
```

### Pattern 1: GIL Release with py.detach()

**What:** Release GIL during long-running Rust operations
**When to use:** Operations taking >1ms that don't need Python object access
**Example:**
```rust
// Source: PyO3 docs - https://pyo3.rs/main/parallelism
use pyo3::prelude::*;

#[pyfunction]
fn expensive_operation(py: Python<'_>, data: Vec<String>) -> PyResult<Vec<String>> {
    // Release GIL during computation
    let result = py.detach(|| {
        // This runs without holding the GIL
        data.iter()
            .map(|s| process_string(s))
            .collect()
    });
    Ok(result)
}
```

### Pattern 2: Existing `without_gil()` Helper

**What:** Project's wrapper around `py.detach()`
**When to use:** All GIL release operations for consistency
**Example:**
```rust
// Source: classic-shared-py/src/lib.rs
use classic_shared::without_gil;

#[pyfunction]
fn process_log(py: Python<'_>, log_path: String) -> PyResult<PyAnalysisResult> {
    let result = without_gil(py, || {
        get_runtime()
            .block_on(async { self.inner.process_log(log_path).await })
            .map_err(crate::to_pyerr)
    })?;
    Ok(PyAnalysisResult { inner: result })
}
```

### Pattern 3: Criterion Benchmark Structure

**What:** Permanent benchmarks with FFI overhead separation
**When to use:** Measuring FFI operations for GIL audit
**Example:**
```rust
// Source: Criterion.rs docs
use criterion::{criterion_group, criterion_main, Criterion, BenchmarkId};
use std::time::Duration;

fn bench_ffi_operations(c: &mut Criterion) {
    let mut group = c.benchmark_group("ffi_overhead");

    // Configure for consistency
    group.sample_size(100)
         .measurement_time(Duration::from_secs(5));

    // Test data
    let test_data = generate_test_data();

    // Benchmark pure Rust compute (no FFI)
    group.bench_function("pure_rust", |b| {
        b.iter(|| {
            std::hint::black_box(process_data(&test_data))
        })
    });

    // Benchmark with FFI overhead (type conversions)
    // This would need to be called from Python integration test

    group.finish();
}

criterion_group!(benches, bench_ffi_operations);
criterion_main!(benches);
```

### Pattern 4: Debug Assertion for GIL Release

**What:** Runtime check that GIL is released for expensive operations
**When to use:** Development builds to catch missing GIL releases
**Example:**
```rust
/// Marker that operation expects GIL to be released
#[cfg(debug_assertions)]
fn assert_gil_released<F, R>(py: Python<'_>, f: F) -> R
where
    F: FnOnce() -> R + Send,
    R: Send,
{
    // In debug builds, verify we can release GIL
    py.detach(|| {
        // If we got here, GIL was successfully released
        f()
    })
}

#[cfg(not(debug_assertions))]
fn assert_gil_released<F, R>(_py: Python<'_>, f: F) -> R
where
    F: FnOnce() -> R + Send,
    R: Send,
{
    f()
}
```

### Anti-Patterns to Avoid

- **Releasing GIL for sub-millisecond operations:** Overhead of GIL release/reacquire (~0.1ms) negates benefit
- **Releasing GIL while holding Python objects:** Will panic - extract all data before `py.detach()`
- **Not documenting GIL release in docstrings:** Future maintainers need to know which operations release GIL
- **Hardcoding threshold without measurement:** Always measure timing first, use 1ms as guideline not hard rule

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GIL release wrapper | Custom py.allow_threads wrapper | Project's `without_gil()` helper | Already exists, consistent API |
| Benchmark framework | Manual timing loops | Criterion | Statistical rigor, baselines, regression detection |
| Concurrent test framework | Thread.join() timing | pytest-asyncio + ThreadPoolExecutor | Existing test patterns in codebase |
| Threshold configuration | Hardcoded constants | Environment variable | Already decided: runtime-configurable |

**Key insight:** The codebase already has the GIL release infrastructure (`without_gil`), the work is auditing usage and measuring to identify gaps.

## Common Pitfalls

### Pitfall 1: Releasing GIL While Holding Python Objects

**What goes wrong:** Panic at runtime - Rust tries to access Python object without GIL
**Why it happens:** Data extraction from PyAny happens inside `py.detach()` closure
**How to avoid:** Extract ALL Python data BEFORE calling `py.detach()`
**Warning signs:** `PyRef<T>`, `&Bound<T>`, or `&PyAny` inside closure

```rust
// WRONG - accessing PyDict inside detach
fn bad_example(py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<String> {
    py.detach(|| {
        // PANIC: data requires GIL
        data.get_item("key")  // <-- This will panic!
    })
}

// CORRECT - extract data before detach
fn good_example(py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<String> {
    // Extract while holding GIL
    let key_value: String = data.get_item("key")?.extract()?;

    py.detach(|| {
        // Process extracted Rust data only
        process_string(&key_value)
    })
}
```

### Pitfall 2: Over-Optimizing Fast Operations

**What goes wrong:** GIL release overhead exceeds computation time, slowing things down
**Why it happens:** Assuming all operations benefit from GIL release
**How to avoid:** Measure first! Only release GIL for operations >1ms
**Warning signs:** Simple getters, property access, small data conversions

### Pitfall 3: Inconsistent Threshold Handling

**What goes wrong:** Some operations release GIL at 0.5ms, others at 2ms, confusion ensues
**How to avoid:** Use 1ms guideline consistently, document exceptions
**Warning signs:** Random GIL release decisions without timing data

### Pitfall 4: Missing Test Coverage for GIL Release

**What goes wrong:** GIL release looks correct but doesn't actually work
**Why it happens:** Unit tests don't exercise concurrent Python thread scenarios
**How to avoid:** Integration tests with multiple Python threads accessing Rust concurrently
**Warning signs:** Tests pass but production shows single-threaded behavior

## Code Examples

### Existing GIL Release Usage (9 files currently)

```rust
// Source: classic-scanlog-py/src/orchestrator.rs
pub fn process_log(&self, py: Python<'_>, log_path: String) -> PyResult<PyAnalysisResult> {
    let result = without_gil(py, || {
        get_runtime()
            .block_on(async { self.inner.process_log(log_path).await })
            .map_err(crate::to_pyerr)
    })?;
    Ok(PyAnalysisResult { inner: result })
}
```

### GIL Release Test Pattern

```python
# Test that GIL is released by running concurrent operations
import threading
import time
from concurrent.futures import ThreadPoolExecutor

def test_gil_release_allows_concurrency():
    """Prove GIL is released by running operations concurrently."""
    import classic_scanlog

    parser = classic_scanlog.LogParser()
    test_data = ["line1", "line2", ...] * 1000  # Large enough to take >1ms

    results = []
    start_time = time.time()

    def parse_in_thread():
        # This should run concurrently if GIL is released
        return parser.parse_segments(test_data)

    # Run 4 threads concurrently
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(parse_in_thread) for _ in range(4)]
        results = [f.result() for f in futures]

    elapsed = time.time() - start_time

    # If GIL released: ~T (parallel)
    # If GIL held: ~4T (sequential)
    # Allow 2x sequential as threshold (imperfect parallelism)
    single_time = measure_single_call_time()
    assert elapsed < single_time * 2.5, "Operations appear to be sequential (GIL not released)"
```

### Criterion Benchmark Example

```rust
// Source: Criterion.rs documentation
use criterion::{criterion_group, criterion_main, Criterion, BenchmarkId};

fn bench_log_parsing(c: &mut Criterion) {
    let mut group = c.benchmark_group("log_parsing");

    // Test with different input sizes
    for size in [100, 1000, 10000] {
        let test_lines: Vec<String> = generate_test_lines(size);

        group.bench_with_input(
            BenchmarkId::new("parse_segments", size),
            &test_lines,
            |b, lines| {
                let parser = LogParser::new(None).unwrap();
                b.iter(|| {
                    std::hint::black_box(parser.parse_segments(lines))
                })
            }
        );
    }

    group.finish();
}

criterion_group!(benches, bench_log_parsing);
criterion_main!(benches);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Python::allow_threads()` | `Python::detach()` | PyO3 0.26 | Renamed for free-threading clarity |
| `Python::with_gil()` | `Python::attach()` | PyO3 0.26 | Renamed for free-threading clarity |
| Manual benchmarks | Criterion | N/A | Statistical rigor standard |

**Deprecated/outdated:**
- `py.allow_threads()`: Renamed to `py.detach()` in PyO3 0.26 (project already updated)
- `pyo3::prepare_freethreaded_python`: Renamed to `Python::initialize()`

## Audit Scope Summary

### Python Binding Crates (18 total)

Based on codebase analysis, prioritized by complexity:

**High Priority (Complex operations, likely >1ms):**
1. `classic-scanlog-py` - Log parsing, mod detection, FormID analysis
2. `classic-file-io-py` - File I/O, DDS processing
3. `classic-database-py` - Database queries
4. `classic-config-py` - YAML loading (already uses without_gil)
5. `classic-scangame-py` - Game scanning, integrity checks

**Medium Priority (Mixed operations):**
6. `classic-yaml-py` - YAML parsing
7. `classic-update-py` - Network requests (async already)
8. `classic-path-py` - Path operations

**Low Priority (Fast operations, likely <1ms):**
9. `classic-message-py` - Logging
10. `classic-perf-py` - Metrics
11. `classic-registry-py` - Registry access
12. `classic-settings-py` - Settings access
13. `classic-version-py` - Version comparison
14. `classic-web-py` - URL utilities
15. `classic-xse-py` - XSE checks
16. `classic-constants-py` - Constants
17. `classic-resource-py` - Resource lookup
18. `classic-shared-py` - Already has without_gil helper

### Current without_gil Usage (9 files)

- `classic-scanlog-py/src/orchestrator.rs` - process_log, process_logs_batch
- `classic-scanlog-py/src/parser.rs` - parse_segments, find_patterns
- `classic-scanlog-py/src/formid_analyzer.rs`
- `classic-file-io-py/src/core.rs` - clear_cache, read_dds_header
- `classic-file-io-py/src/log_collector.rs`
- `classic-config-py/src/lib.rs` - YamlData::new
- `classic-shared-py/src/lib.rs` - Helper definition
- `classic-shared-py/src/strings_py.rs`
- `classic-shared-py/src/path_py.rs`

### Gaps Identified (Operations Without GIL Release)

**classic-yaml-py:**
- `parse_yaml` - String parsing, could be slow for large YAML
- `load_yaml_file` - File I/O
- `save_yaml_file` - File I/O
- `dump_yaml` - Serialization

**classic-scanlog-py:**
- `detect_mods_single/double/batch` - Pattern matching
- `extract_formids_batch` - Regex operations
- `scan_records_batch` - Pattern scanning
- Report generation operations

**classic-file-io-py:**
- `walk_directory` - Directory traversal
- `read_dds_headers_batch` - Batch file I/O

**classic-scangame-py:**
- `check_executable_version` - SHA256 hashing
- `run_all_checks` - Multiple file operations

**classic-database-py:**
- Uses async `future_into_py` which has different GIL semantics - verify

## Open Questions

1. **Async Operations GIL Handling**
   - What we know: `future_into_py` returns a coroutine immediately, no blocking
   - What's unclear: Does the async execution properly release GIL?
   - Recommendation: Verify with concurrent tests; async should be fine

2. **TUI Review Scope**
   - What we know: TUI uses Ratatui, separate Rust application
   - What's unclear: How much overlap with Python GIL concerns?
   - Recommendation: Minimal review for async/blocking consistency patterns only

3. **Threshold Edge Cases**
   - What we know: 1ms guideline with documented exceptions
   - What's unclear: How to handle operations that vary widely (50us - 5ms)
   - Recommendation: Benchmark with realistic data sizes, document p95 timing

## Sources

### Primary (HIGH confidence)

- `/pyo3/pyo3` Context7 - GIL release patterns, `py.detach()` usage
- `/bheisler/criterion.rs` Context7 - Benchmark configuration and structure
- `classic-shared-py/src/lib.rs` - Existing `without_gil()` implementation
- `classic-scanlog-py/src/orchestrator.rs` - Production GIL release patterns

### Secondary (MEDIUM confidence)

- Existing Criterion benchmarks in `classic-shared-core/benches/` - Project patterns
- Existing concurrency tests in `tests/rust_integration/e2e/` - Test patterns

### Tertiary (LOW confidence)

- General PyO3 training knowledge (verified against Context7)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified with Context7, already in project
- Architecture: HIGH - Patterns exist in codebase, verified with official docs
- Pitfalls: HIGH - Based on PyO3 documentation and codebase analysis
- Audit scope: HIGH - Direct analysis of 18 crates

**Research date:** 2026-02-04
**Valid until:** 60 days (stable APIs, minimal change expected)
