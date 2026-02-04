# Pitfalls Research

**Domain:** Hybrid Python-Rust codebase cleanup, consolidation, and performance optimization
**Researched:** 2026-02-01
**Updated:** 2026-02-04 (added Performance Benchmarking Pitfalls for v8.3.0)
**Confidence:** HIGH (based on codebase analysis docs, project history, official PyO3 documentation)

---

## Performance Benchmarking Pitfalls (v8.3.0 Section)

**Context:** This section covers pitfalls specific to benchmarking and optimizing the hybrid Python-Rust performance work for v8.3.0. CLASSIC already has Rust acceleration in place (15-150x speedups); this milestone focuses on establishing baselines, profiling hot paths, and fixing pre-existing bugs.

### Critical Performance Pitfalls

#### Pitfall P1: Measuring FFI Overhead Without Isolating Type Conversion

**What goes wrong:** Benchmarks attribute all latency to "Rust code" when significant time is actually spent in Python-to-Rust type conversion (marshaling). Teams optimize the wrong thing.

**Why it happens:** PyO3 automatically converts between Python and Rust types (e.g., `dict` to `HashMap`, `list` to `Vec`). This conversion happens transparently but has measurable cost, especially for nested structures. The `yaml_to_python()` and `python_to_yaml()` functions in `classic-yaml-py` perform recursive conversion for every YAML operation.

**Consequences:**
- Optimize Rust code when the bottleneck is actually marshaling
- Miss opportunities to batch operations or use zero-copy techniques
- False conclusions about Rust speedup factors (claim 10x but actually 2x after accounting for conversion)

**Prevention:**
1. Use CLASSIC's existing `tools/ffi_profiler.py` to measure `input_size`, `output_size`, and `input_type` for every timed FFI call
2. Benchmark Rust-side logic separately using `criterion` in Rust tests (no PyO3 boundary)
3. For hot paths, consider `#[pyclass]` wrappers to keep data on Rust side between operations
4. Measure "conversion tax" explicitly: time the operation with and without data conversion

**Detection (warning signs):**
- "Rust speedup is inconsistent between small and large inputs" (small = high conversion ratio)
- Profiling shows most time in `python_to_yaml` / `yaml_to_python` conversion functions
- Speedup factor varies wildly (5x to 50x) for similar operations

**Phase relevance:** Phase 1 (Baseline Establishment) - must capture conversion overhead from the start

**CLASSIC-specific note:** The `yaml_to_python` function at line 370 of `classic-yaml-py/src/lib.rs` recursively converts every YAML node. For deeply nested YAML like the game database files, this can be significant.

---

#### Pitfall P2: Holding GIL During Long Rust Operations

**What goes wrong:** Python's Global Interpreter Lock (GIL) remains held during Rust computation, blocking all other Python threads and async tasks. The application appears frozen.

**Why it happens:** By default, PyO3 holds the GIL during Rust function execution. Developers assume "Rust is fast so it doesn't matter" but even 50ms blocks the entire Python runtime. Per [PyO3 Performance Guide](https://pyo3.rs/main/performance): "Operations expected to take multiple milliseconds can benefit from detaching from the interpreter."

**Consequences:**
- GUI becomes unresponsive during analysis operations
- async tasks starve waiting for GIL
- Benchmarks show good Rust performance but real-world application feels slow

**Prevention:**
1. Use `py.allow_threads(|| { ... })` for any Rust operation >1ms
2. For CLASSIC's current pattern with `asyncio.to_thread()`, ensure Rust functions don't block GIL acquisition
3. Benchmark with concurrent Python operations running, not in isolation
4. Add GIL-release instrumentation to `FFIProfiler.gil_contention_events`

**Detection:**
- GUI freezes during Rust operations despite "fast" benchmarks
- `FFIProfiler.gil_contention_events` shows >0.1ms wait times
- Profiling shows time in "waiting for GIL" category
- Process at 100% single-core CPU while other Python threads idle

**Phase relevance:** Phase 2 (Hot Path Optimization) - GIL release must be part of optimization work

**CRITICAL FINDING:** Grep of `rust/` directory shows NO matches for `allow_threads` or `py.allow_threads`. This is a gap that v8.3.0 should address for any operation >1ms.

---

#### Pitfall P3: Global Static State Causing Test Non-Determinism

**What goes wrong:** Rust's `static` variables (like `YAML_CACHE` at line 153 of `classic-yaml-core/src/lib.rs`) persist across test runs, causing tests to fail intermittently or in specific orders.

**Why it happens:**
- Rust tests run in parallel by default
- Static variables like `Lazy<DashMap<PathBuf, CachedYaml>>` are shared across all tests in a process
- Cache state from one test pollutes another

**Consequences:**
- Tests pass locally but fail in CI (different parallelism)
- `test_clear_cache` assertion fails: "expected 0, got 1" (the exact pre-existing bug documented in PROJECT.md)
- Flaky tests that pass on retry

**Prevention:**
1. Use `#[serial_test::serial]` for tests touching global state (CLASSIC already does this in metrics tests)
2. Call `clear_*_cache()` at start AND end of tests, not just one
3. For Python tests, ensure singleton cleanup in fixtures
4. Consider per-test state injection instead of global statics

**Detection:**
- Tests pass with `cargo test -- --test-threads=1` but fail with parallel execution
- Assertion failures about cache/counter values
- "Pre-existing" test failures that nobody can reproduce locally

**Phase relevance:** Phase 3 (Bug Fixes) - the `test_clear_cache` fix requires understanding this pitfall

**CLASSIC-specific note:** The `test_clear_cache` bug in `classic-yaml-core` (line 1792) is exactly this pitfall. The test loads a file (populating `YAML_CACHE`), clears cache, but another parallel test may have loaded a file between the assertion and clear.

---

#### Pitfall P4: Benchmarking Debug Builds Instead of Release

**What goes wrong:** Performance measurements use Rust debug builds (10-100x slower), leading to incorrect optimization decisions.

**Why it happens:**
- `cargo test` uses debug by default
- Development workflow uses `maturin develop` (debug) not `maturin develop --release`
- CI may not specify release mode
- `rebuild_rust.ps1` without explicit release flag

**Consequences:**
- Massive performance regression reported that doesn't exist in release
- Optimization work targets already-fast code
- False comparisons between Python (optimized) and Rust (unoptimized)

**Prevention:**
1. Always benchmark with `--release` flag
2. Add CI check that performance tests use release builds
3. Document build mode in all benchmark results
4. Use `CARGO_PROFILE_RELEASE_DEBUG=true` for profiling with symbols (as configured in workspace `Cargo.toml` line 169)
5. Use `rebuild_rust.ps1` which builds release by default

**Detection:**
- Rust code slower than Python for same algorithm
- 10x+ performance difference between "local" and "CI" results
- Profiling shows unexpected time in bounds checking / overflow checks
- Missing SIMD/LTO optimizations visible in assembly

**Phase relevance:** Phase 1 (Baseline) - establish release-mode baselines from day one

---

#### Pitfall P5: Using Mean Instead of Minimum for Microbenchmarks

**What goes wrong:** Benchmark reports use mean/average timing, which is heavily influenced by outliers from OS scheduling, GC pauses, and thermal throttling.

**Why it happens:** Statistical intuition says "average multiple samples" but benchmarking is not a normal distribution - interference only makes things slower, never faster. As [Python timeit documentation](https://docs.python.org/3/library/timeit.html) states: "the min() of the result is probably the only number you should be interested in."

**Consequences:**
- High variance in reported numbers (50ms +/- 40ms is not meaningful)
- Can't detect real regressions amid noise
- Over-optimization of already-fast code based on spurious slow samples

**Prevention:**
1. Use minimum of multiple runs as primary metric
2. Report percentiles (p50, p95, p99) not just mean - CLASSIC's `FFIProfileStats` already has `p95_call_time` and `p99_call_time`
3. Use statistical benchmarking tools: `criterion` (Rust), `pyperf` (Python)
4. Warm up before measuring (both CPU and JIT)
5. Run on quiet system with performance governor if possible

**Detection:**
- Coefficient of variation >20% across runs
- "Improvements" that disappear on re-run
- Benchmark results change dramatically between machines

**Phase relevance:** Phase 1 (Baseline) - measurement methodology must be correct from start

---

### Moderate Performance Pitfalls

#### Pitfall P6: Not Warming Up JIT/CPU Before Measurement

**What goes wrong:** First runs are significantly slower due to cold CPU caches, JIT compilation (if any), and lazy initialization.

**Prevention:**
1. Run 3-5 warmup iterations before measurement
2. Use `criterion`'s built-in warmup phase
3. For Python, prime caches and imports before timing
4. Ensure Rust's `Lazy<>` statics are initialized pre-benchmark (YAML_CACHE, METRICS)

**Phase relevance:** Phase 1 (Baseline)

---

#### Pitfall P7: Measuring Wall Clock Without CPU Time

**What goes wrong:** Benchmarks report wall-clock time, which includes time spent waiting for I/O, GIL, and other processes.

**Prevention:**
1. Report both wall time and CPU time (`time.process_time()`)
2. Use `FFIProfiler`'s `cpu_time` field alongside `wall_time`
3. For I/O-bound operations, also measure throughput (bytes/second)
4. Run benchmarks on quiet systems or in isolated containers

**CLASSIC-specific:** The `FFICall` dataclass in `tools/ffi_profiler.py` already captures both `wall_time` and `cpu_time` at lines 74-75.

**Phase relevance:** Phase 2 (Hot Path Optimization) - need CPU time to find true hotspots

---

#### Pitfall P8: Ignoring Memory Allocation in Performance Analysis

**What goes wrong:** Focus on time metrics while memory allocation patterns cause GC pressure and cache misses.

**Prevention:**
1. Track memory deltas using `FFIProfiler.memory_before/after`
2. Use Rust's memory-efficient types (`SmartString`, `lasso` for interning - already in workspace dependencies)
3. Profile with memory analyzers (Valgrind/DHAT for Rust, memory_profiler for Python)
4. Watch for "memory leak" warnings (>10MB growth per call)
5. Monitor `FFIProfileStats.memory_leaks_detected` in profiling output

**Phase relevance:** Phase 2 (Hot Path Optimization)

---

#### Pitfall P9: Optimizing Infrequently Called Code

**What goes wrong:** Significant effort optimizing code paths that execute once per session while ignoring code called thousands of times.

**Prevention:**
1. Use `FFIProfiler.call_counts` to identify high-frequency functions first
2. Apply Amdahl's Law: optimize what takes most total time, not just slowest single call
3. Sort by `total_time = call_count * avg_time` not just `avg_time`
4. Focus on "hot paths" identified by profiling, not intuition
5. Use `FFIProfileStats.high_frequency_calls` list for targeting

**Phase relevance:** Phase 2 (Hot Path Optimization)

---

#### Pitfall P10: Async Overhead for Fast Operations

**What goes wrong:** Wrapping sub-millisecond Rust calls in `asyncio.to_thread()` adds more overhead than the operation itself.

**Prevention:**
1. Only use `asyncio.to_thread()` for operations >1ms
2. Batch small operations before crossing async boundary
3. Use direct sync calls for fast operations in sync contexts
4. Measure the "async tax" for each operation type

**Phase relevance:** Phase 2 (Hot Path Optimization)

**CLASSIC-specific note:** The codebase already documents this pattern in `game_files_manager.py` (line 137): "overhead of using run_in_executor (typically < 1ms)" - ensure this threshold is validated in benchmarks.

---

### Minor Performance Pitfalls

#### Pitfall P11: Forgetting to Clear Caches Between Benchmark Iterations

**What goes wrong:** Cache hits make second iteration artificially fast, skewing comparison.

**Prevention:**
1. Call `clear_cache()` methods before each iteration
2. Use fresh temp files/directories per benchmark
3. Document cache state assumptions in benchmark comments

---

#### Pitfall P12: Platform-Specific Performance Assumptions

**What goes wrong:** Benchmarks on Linux show different results than Windows/macOS due to filesystem, thread scheduling, and memory management differences.

**Prevention:**
1. Run benchmarks on all target platforms
2. Document platform for all reported numbers
3. Use relative comparisons (speedup factor) not absolute times

---

#### Pitfall P13: Tokio Runtime Misconfiguration

**What goes wrong:** Using `tokio::spawn` with `FuturesUnordered` causes quadratic scaling (per [ScyllaDB analysis](https://www.scylladb.com/2022/01/12/async-rust-in-practice-performance-pitfalls-profiling/)), or using wrong thread pool size.

**Prevention:**
1. Use `tokio::join!` for preserving order (CLASSIC already does this - see 05-memories.md)
2. Profile with different `TOKIO_WORKER_THREADS` values
3. Avoid nested `block_on()` calls (panic/deadlock)
4. Respect ONE RUNTIME rule from CLASSIC architecture

**Phase relevance:** Phase 2 if Rust async optimization is attempted

---

#### Pitfall P14: Relative Path Bugs in Different Working Directories

**What goes wrong:** Code using `Path("filename.yaml")` works from project root but fails from GUI context where CWD differs.

**Prevention:**
1. Always use absolute paths or paths relative to known anchors (`__file__`, registry paths)
2. Test from multiple working directories
3. Avoid bare `Path("name")` - resolve against application directory

**Phase relevance:** Phase 3 (Bug Fixes) - the `classic_settings()` GUI bug is exactly this

**CLASSIC-specific note:** Line 196 of `convenience.py` has `settings_path = Path("CLASSIC Settings.yaml")` - this is the pre-existing bug that fails when CWD is not project root.

---

### Phase-Specific Performance Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Baseline establishment | P4: Debug builds, P5: wrong statistics | Use release mode, report minimum + percentiles |
| FFI measurement | P1: Type conversion hidden | Use `FFIProfiler`, benchmark Rust separately |
| GIL analysis | P2: Holding GIL too long | Add `py.allow_threads()`, test with concurrent load |
| Cache testing | P3: Parallel test pollution | `#[serial_test::serial]`, clear before AND after |
| Hot path optimization | P9: Optimizing wrong code | Sort by total time, not per-call time |
| GUI bug fix | P14: Relative path assumptions | Use absolute paths, test from multiple CWDs |
| Async optimization | P10: Over-using `to_thread()` | Threshold check (>1ms), batch small operations |

---

### Pre-Existing Bug Analysis (v8.3.0 Scope)

#### Bug 1: `test_clear_cache` in classic-yaml-core

**Root cause:** Pitfall P3 (Global Static State)
- `YAML_CACHE` is a global `Lazy<DashMap<PathBuf, CachedYaml>>` (line 153)
- Test at line 1792 loads file, then asserts `cached_files >= 1`
- Clears cache, asserts `cached_files == 0`
- But parallel tests may load files between clear and final assertion

**Fix approach:**
1. Add `#[serial]` attribute if not already present (it is, but verify)
2. Clear cache at start of test, not just rely on `YamlOperations::new()`
3. Or: use test-specific cache instance instead of global

#### Bug 2: GUI file path resolution in `classic_settings()`

**Root cause:** Pitfall P14 (Relative Path)
- Line 196: `settings_path = Path("CLASSIC Settings.yaml")`
- Works when CWD is project root (CLI, pytest)
- Fails when CWD is different (GUI launched from Start menu, shortcuts)

**Fix approach:**
1. Resolve path against application directory: `Path(__file__).parent.parent.parent / "CLASSIC Settings.yaml"`
2. Or: use existing path resolution through YamlSettingsCache which should handle this
3. Or: change CWD on GUI startup (less recommended)

---

### Performance Verification Checklist

Before starting v8.3.0 performance work:

- [ ] All benchmarks use release builds (`--release`, `maturin build --release`)
- [ ] Measurement methodology documented (min vs mean, warmup count)
- [ ] FFI overhead vs Rust logic measured separately using `FFIProfiler`
- [ ] GIL release patterns reviewed for hot paths (currently NONE - gap to address)
- [ ] Test isolation verified for cache-related tests (`#[serial]` attribute)
- [ ] Baselines captured on target platforms (Windows primary)
- [ ] Pre-existing bugs documented with root cause analysis
- [ ] `FFIProfileStats` reporting configured (p50, p95, p99, not just mean)

---

### Performance Sources

**HIGH Confidence (Official Documentation):**
- [PyO3 Performance Guide](https://pyo3.rs/main/performance) - GIL release, type conversion, reference pool
- [Python timeit Documentation](https://docs.python.org/3/library/timeit.html) - Use minimum not mean
- [Criterion.rs Documentation](https://bheisler.github.io/criterion.rs/book/) - Rust benchmarking best practices
- [The Rust Performance Book - Benchmarking](https://nnethercote.github.io/perf-book/benchmarking.html) - Release builds, warmup

**MEDIUM Confidence (Verified Technical Sources):**
- [ScyllaDB Async Rust Performance](https://www.scylladb.com/2022/01/12/async-rust-in-practice-performance-pitfalls-profiling/) - FuturesUnordered pitfall
- [PyO3 GitHub Discussion #3442](https://github.com/PyO3/pyo3/discussions/3442) - FFI overhead analysis
- [py-spy Profiler](https://github.com/benfred/py-spy) - Sampling profiler for Python with Rust support

**LOW Confidence (Community Sources, Needs Validation):**
- General blog posts on Python-Rust performance
- Stack Overflow answers on benchmarking methodology

---

## Migration-Specific Pitfalls (New Section)

**Context:** This section covers pitfalls specific to migrating remaining Python business logic to Rust for the v2.0 milestone. CLASSIC has already successfully migrated YAML parsing, database operations, crash log parsing, FormID analysis, and file I/O. The remaining migrations target scanning orchestration, game detection, report generation, and settings management.

### Critical Migration Pitfalls

#### Pitfall M1: Nested Runtime Errors (ONE RUNTIME RULE Violation)

**What goes wrong:** Creating multiple Tokio runtimes causes "Cannot start a runtime from within a runtime" panics. This happens when:
- Calling `get_runtime().block_on()` from within an already-async context
- Creating new `Runtime::new()` instances in individual crates
- Using `#[tokio::main]` in library code meant to be called from Python

**Why it happens:** PyO3 functions called from Python are already running in a context where Python holds the GIL. If that function creates a Tokio runtime and blocks, then calls another function that also tries to create/block on a runtime, you get nested runtime errors.

**Consequences:**
- Application panics with cryptic "cannot start a runtime from within a runtime" errors
- Random deadlocks that are extremely difficult to debug
- Failures that only occur in production, not in isolated Rust tests

**Prevention:**
1. **Always use `classic_shared_core::get_runtime()`** - Never create new runtimes
2. **Check context before blocking** - Use `.await` directly in async contexts, only use `block_on()` at sync boundaries
3. **Release GIL with `py.allow_threads()`** before entering async blocks

```rust
// CORRECT: Use shared runtime
#[pyfunction]
fn process_data(py: Python<'_>, data: String) -> PyResult<String> {
    py.allow_threads(|| {
        classic_shared_core::get_runtime().block_on(async move {
            // async work here
        })
    })
}

// WRONG: Creating new runtime
#[pyfunction]
fn process_data(data: String) -> PyResult<String> {
    let rt = Runtime::new()?;  // NEVER DO THIS
    rt.block_on(async { ... })
}
```

**Detection:**
- Panic messages containing "cannot start a runtime"
- Intermittent hangs when processing multiple items
- Code review: search for `Runtime::new()` or `tokio::runtime::Builder`

**Phase impact:** ALL migration phases - This is a foundational rule that affects every Rust component.

---

#### Pitfall M2: GIL Deadlock During Async Operations

**What goes wrong:** Holding the Python GIL while doing async work in multi-threaded Tokio runtime causes deadlocks. Thread A holds GIL, awaits async work that gets scheduled on Thread B. Thread B needs GIL to return result to Python, but Thread A is blocked waiting for Thread B.

**Why it happens:** PyO3's default behavior keeps the GIL held during function execution. When combined with multi-threaded async runtime, work can be distributed across threads that all need GIL access.

**Consequences:**
- Complete application freeze (deadlock)
- Only manifests in multi-threaded scenarios (not in tests)
- No error messages - just a hung process

**Prevention:**
1. **Use `py.allow_threads()`** to release GIL before any async work
2. **Detach Python objects** before sending to other threads: `py.detach()`
3. **Use `Python::attach()`** when you need GIL back in worker threads
4. **Avoid holding Python references** across await points

```rust
// CORRECT: Release GIL for parallel work
#[pyfunction]
fn parallel_operation(py: Python<'_>, paths: Vec<String>) -> PyResult<Vec<String>> {
    py.allow_threads(|| {
        classic_shared_core::get_runtime().block_on(async {
            // Async work happens without GIL
            process_paths_parallel(paths).await
        })
    })
}
```

**Detection:**
- Application hangs with no output or error
- Process stuck at 0% CPU (waiting, not computing)
- Only happens when processing multiple items concurrently
- `RUST_BACKTRACE=1` shows threads waiting on GIL

**Phase impact:** Orchestration migration, batch processing, any parallel operations.

---

#### Pitfall M3: Behavioral Parity Regression

**What goes wrong:** Rust implementation produces different output than Python for edge cases, making the migration appear successful in tests but fail in production.

**Why it happens:**
- Python's dynamic typing allows implicit conversions that Rust requires explicit handling for
- Unicode handling differences (Python strings vs Rust &str)
- Floating-point formatting differences
- Empty collection handling (Python's truthiness vs Rust's explicit checks)
- Dictionary iteration order (Python preserves insertion order, HashMap doesn't by default)

**Consequences:**
- Reports look slightly different, confusing users
- Edge cases (empty logs, corrupted data) crash Rust but not Python
- Test suite passes but production fails on real-world data

**Prevention:**
1. **Golden file testing** - Compare Rust output against captured Python output for real crash logs
2. **Use `IndexMap`** instead of `HashMap` when order matters (CLASSIC already does this in `classic-scanlog-core`)
3. **Explicit error handling** for all edge cases Python handles implicitly
4. **Fuzz testing** with random/malformed input
5. **Character-by-character comparison** of report output during testing

```rust
// Preserve insertion order like Python dict
use indexmap::IndexMap;

fn process_plugins(plugins: Vec<String>) -> IndexMap<String, String> {
    let mut result = IndexMap::new();
    // Order will match Python's dict behavior
}
```

**Detection:**
- Diff reports: `diff python_output.md rust_output.md`
- Unit tests that compare exact string output
- User reports of "output looks different"

**Phase impact:** Report generation migration, mod detection, any human-readable output.

---

#### Pitfall M4: Memory Ownership Across Python/Rust Boundary

**What goes wrong:** Passing Python objects to Rust, doing async work, then trying to use the objects causes "borrowed data escapes outside of function" or use-after-free errors.

**Why it happens:** Python objects have lifetimes tied to the GIL. When you release the GIL (`py.allow_threads()`), Python can garbage collect objects. If Rust is still referencing them, undefined behavior occurs.

**Consequences:**
- Segmentation faults
- Memory corruption
- Data returned to Python contains garbage
- Errors only under memory pressure

**Prevention:**
1. **Clone data** before releasing GIL - don't hold references
2. **Convert to owned types** at the boundary: `String` not `&str`, `Vec` not `&[]`
3. **Use `Py<T>`** for Python objects that need to outlive GIL release
4. **Never hold `&PyAny`** across `py.allow_threads()` boundaries

```rust
// CORRECT: Clone data at boundary
#[pyfunction]
fn process_log(py: Python<'_>, content: String, plugins: Vec<String>) -> PyResult<String> {
    // content and plugins are owned - safe to use after GIL release
    py.allow_threads(|| {
        classic_shared_core::get_runtime().block_on(async move {
            process_async(content, plugins).await
        })
    })
}

// WRONG: Holding borrowed reference
#[pyfunction]
fn process_log<'py>(py: Python<'py>, content: &'py str) -> PyResult<String> {
    py.allow_threads(|| {
        // content is borrowed from Python - UNDEFINED BEHAVIOR
        process_sync(content)
    })
}
```

**Detection:**
- Compile errors about lifetimes (the good case)
- Segfaults during parallel processing (the bad case)
- Random garbage in results under load

**Phase impact:** ALL migration phases - every PyO3 function needs correct ownership handling.

---

### Moderate Migration Pitfalls

#### Pitfall M5: Type Conversion Overhead at Hot Paths

**What goes wrong:** Repeatedly converting between Python and Rust types in tight loops negates the performance benefits of Rust.

**Why it happens:**
- Calling Rust functions from Python loop (N boundary crossings)
- Converting `list[str]` to `Vec<String>` for each item
- String encoding/decoding on every call

**Prevention:**
1. **Batch operations** - Pass entire collections, not individual items
2. **Keep data on Rust side** between operations
3. **Measure conversion overhead** before assuming Rust is faster
4. See `docs/development/pyo3_integration_patterns.md` Type Conversion Performance Reference

```python
# WRONG: N boundary crossings
for log in logs:
    result = rust_process(log)  # Python->Rust->Python per log

# CORRECT: Single boundary crossing
results = rust_process_batch(logs)  # Python->Rust->Python once
```

**Detection:**
- Rust version not faster than Python for small inputs
- Profiling shows time spent in `FromPyObject::extract`

**Phase impact:** Batch processing, report generation, any loop-heavy operations.

---

#### Pitfall M6: Incomplete Error Propagation

**What goes wrong:** Rust errors get swallowed or converted to generic Python exceptions, losing context needed for debugging.

**Why it happens:**
- Using `.unwrap()` instead of proper error handling
- Converting all errors to a single exception type
- Not preserving error chains

**Prevention:**
1. **Define specific exception types** for each error category using `define_exceptions!` macro from `classic_shared`
2. **Include context** in error messages (file path, line number, data sample)
3. **Use `?` with custom `Into<PyErr>` implementations**
4. **Log errors** at Rust level before converting to Python

```rust
// CLASSIC's pattern: 3-tier exception hierarchy (from classic-scanlog-py)
define_exceptions!(
    module: classic_scanlog,
    base: RustScanLogError,        // Generic
    io: RustParseError,            // Parse/analysis errors
    parse: RustConfigError         // Configuration errors
);
```

**Detection:**
- Generic "Error" exceptions in Python with no context
- Unable to determine what file/data caused failure
- Users reporting unhelpful error messages

**Phase impact:** ALL migration phases - every Rust component needs proper error handling.

---

#### Pitfall M7: State Synchronization Between Python and Rust

**What goes wrong:** Python and Rust have their own caches/state that get out of sync, causing inconsistent behavior.

**Why it happens:**
- Rust component caches data independently
- Python modifies state that Rust doesn't see
- Multiple entry points updating different caches

**Prevention:**
1. **Single source of truth** - either Python OR Rust owns state, not both
2. **Explicit invalidation** - when state changes, notify all caches
3. **Prefer stateless functions** where possible
4. **Document state ownership** clearly

**Detection:**
- Results change based on call order
- Caches contain stale data
- "Works the second time" bugs

**Phase impact:** Settings management migration, game detection (anything with cached state).

---

#### Pitfall M8: PyO3 API Version Mismatches (Bound<'py, T> Migration)

**What goes wrong:** Using outdated PyO3 patterns from pre-0.21 code examples causes compile errors or deprecation warnings that accumulate into maintenance burden.

**Why it happens:** PyO3 0.21+ introduced `Bound<'py, T>` to replace "GIL Refs" (`&'py PyAny`). Old code examples, StackOverflow answers, and even some official docs still show the old pattern.

**Consequences:**
- Deprecation warnings flood the build output
- Mix of old and new patterns creates confusion
- Eventually the old API will be removed, requiring migration

**Prevention:**
1. **Use `Bound<'py, T>`** not `&'py PyAny` for all new code
2. **Reference current PyO3 docs** (v0.22+), not older tutorials
3. **CI check** that warns about deprecated API usage

```rust
// OLD (deprecated)
#[pyfunction]
fn process(data: &PyAny) -> PyResult<()> { ... }

// NEW (correct)
#[pyfunction]
fn process(data: Bound<'_, PyAny>) -> PyResult<()> { ... }
```

**Detection:**
- Deprecation warnings during `cargo build`
- Compile errors after PyO3 upgrade

**Phase impact:** ALL migration phases - affects how PyO3 bindings are written.

---

### Minor Migration Pitfalls

#### Pitfall M9: Missing or Stale Type Stubs (.pyi)

**What goes wrong:** Python type stubs out of sync with actual Rust module, causing IDE errors and mypy failures.

**Prevention:**
1. **Generate stubs automatically** where possible
2. **Include stub updates** in Rust change PRs
3. **CI check** that stubs match runtime introspection

**Detection:**
- IDE shows wrong types
- mypy errors on valid code

**Phase impact:** Developer experience, type safety throughout migration.

---

#### Pitfall M10: Build Artifact Confusion

**What goes wrong:** Old `.pyd` files cached, changes not reflected, wrong version loaded.

**Prevention:**
1. **Use rebuild_rust.ps1** - unified build script
2. **Force reinstall** with `--force-reinstall`
3. **Check version** after rebuild: `python -c "import classic_scanlog; print(classic_scanlog.__version__)"`

**Detection:**
- Changes not reflected after rebuild
- Version number doesn't match

**Phase impact:** Development workflow throughout migration.

---

### CLASSIC-Specific Learned Patterns (From Project History)

From `.claude/rules/05-memories.md`:

**AsyncBridge Usage Pattern:**
- **GUI and testing only**: AsyncBridge for same-thread GUI contexts
- **CLI uses async-first**: Single `asyncio.run(main())` at entry point
- **Thread-local**: Cannot use in cross-thread workers (QRunnable, QThread)

**PyO3 Patterns Already Established:**
- **GIL handling**: Use `py.detach()` to release GIL, `Python::attach()` to reacquire
- **Runtime conflicts**: Avoid `get_runtime().block_on()` when already in Python context
- **Custom exceptions**: Each `-py` crate defines exceptions via `create_exception!` macro

**Bug Fixes to Remember:**
- **YAML helper methods**: Use `.get()` on Hash nodes, not index notation
- **Parallel YAML loading**: Use `tokio::join!` (preserves order), not `JoinSet::join_next()` (completion order)

---

### Migration Phase-Specific Warnings

| Migration Component | Likely Pitfall | Mitigation |
|---------------------|----------------|------------|
| Scanning Orchestration | M2: GIL deadlock in batch processing | Release GIL before batch loop |
| Game Detection | M7: State sync between Python/Rust paths | Single source of truth for paths |
| Report Generation | M3: Behavioral parity in formatting | Golden file testing against Python output |
| Settings Management | M5: Type conversion overhead | Batch settings loads |
| Integration Layer | M1: Nested runtime creation | Audit for `Runtime::new()` |

---

### Migration Pre-Flight Checklist

Before migrating any component from Python to Rust:

- [ ] Uses `classic_shared_core::get_runtime()` (not new runtime)
- [ ] Releases GIL with `py.allow_threads()` for async work
- [ ] Clones data at Python/Rust boundary (owned types, not references)
- [ ] Has specific exception types using `define_exceptions!` macro
- [ ] Has golden file tests comparing to Python output
- [ ] Preserves iteration order with IndexMap where needed
- [ ] Updates type stubs (.pyi) when API changes
- [ ] Tested with real crash logs, not just unit tests
- [ ] Follows `-core`/`-py` separation (business logic vs PyO3 bindings)
- [ ] Documented in crate-level `//!` docs

---

### Migration Sources

- [PyO3 Migration Guide](https://pyo3.rs/v0.22.4/migration) - Official PyO3 migration documentation
- [PyO3 FAQ and Troubleshooting](https://pyo3.rs/main/faq) - Common issues and solutions
- [PyO3 Async/Await Guide](https://pyo3.rs/v0.13.2/ecosystem/async-await) - Async runtime patterns
- [GIL Deadlock Discussion](https://github.com/PyO3/pyo3/discussions/3045) - Multi-threaded Tokio GIL issues
- [Migrating from Python to Rust](https://corrode.dev/learn/migration-guides/python-to-rust/) - General migration best practices
- [Incrementally Porting Python to Rust](https://blog.waleedkhan.name/port-python-to-rust/) - Incremental migration strategies
- CLASSIC project documentation:
  - `docs/development/pyo3_integration_patterns.md`
  - `docs/development/async_development_guide.md`
  - `docs/development/rust_workspace_architecture.md`
  - `.claude/rules/05-memories.md`

---

## Critical Pitfalls (Cleanup Phase - From Previous Research)

### Pitfall 1: Removing "Dead" Python Fallbacks That Are Active in Deployed Builds

**What goes wrong:**
A Python fallback implementation appears dead because Rust is always available in the dev environment. The cleanup deletes it. But in deployed PyInstaller builds, Rust extension loading can fail silently (DLL not found, ABI mismatch, missing redistributable on user machine). The factory pattern returns the Python fallback -- which no longer exists. The app crashes on launch for some users while working perfectly for the developer.

**Why it happens:**
The factory pattern in `ClassicLib/integration/factory/` caches Rust component availability at startup. In development, Rust modules are always built and available. The developer never exercises the fallback path. There is no CI matrix testing "Rust unavailable" mode. The Python fallback code looks dead because `detect_rust_components()` always returns `True` for everything.

**How to avoid:**
1. Before removing any Python fallback, verify by running the full test suite with `CLASSIC_DISABLE_RUST=1` environment variable (the `is_rust_disabled()` check in `factory/core.py` supports this).
2. For each factory function (`get_parser()`, `get_file_io()`, `get_database_pool()`, etc.), explicitly decide: "Is this fallback still needed?" Document the answer.
3. If a fallback IS removed, the factory function must raise a clear error ("Rust module X required but not found") instead of silently returning None or crashing with ImportError.
4. Test the PyInstaller build without Rust extensions present to verify error messages are user-friendly.

**Warning signs:**
- Factory functions that import both Rust and Python implementations but Python side has no recent test coverage
- `detect_rust_components()` returns all-True in every test run
- No tests marked with `CLASSIC_DISABLE_RUST=1` or mocking Rust unavailability

**Phase to address:**
Inventory/audit phase (first phase). Before removing anything, catalog which fallbacks are exercised and which are truly dead.

---

### Pitfall 2: Breaking PyInstaller Hidden Imports When Renaming or Moving Modules

**What goes wrong:**
A module is moved, renamed, or consolidated during cleanup. Python tests pass because pytest uses direct imports. But PyInstaller bundles based on `hiddenimports` in `CLASSIC.spec` and the `pyinstaller_rust_helper`. The renamed module is not in the bundle. The app crashes at runtime with `ModuleNotFoundError` -- but only in the distributed executable, not in development.

**Why it happens:**
`CLASSIC.spec` hardcodes module paths like `ClassicLib.rust_loader`, `ClassicLib.integration.factory`, and every Rust binding name. The `collect_all()` calls for PySide6 and Textual also depend on the import graph being intact. When modules are moved or merged, the spec file and hidden import list become stale. PyInstaller's analysis only traces `import` statements it can find statically -- lazy imports, factory patterns, and `importlib` calls are invisible to it.

**How to avoid:**
1. Maintain a checklist: every module rename/move must update `CLASSIC.spec` hidden imports.
2. After any cleanup phase, do a test PyInstaller build (`uv run pyinstaller --clean CLASSIC.spec`) and verify the executable launches.
3. Treat the `CLASSIC.spec` file as a first-class artifact that must be updated in the same commit as any module restructuring.
4. The `pyinstaller_rust_helper.find_rust_extensions()` scans for `.pyd`/`.so` files -- if Rust crate names change, this helper must be updated too.

**Warning signs:**
- Module renames that do not touch `CLASSIC.spec` in the same commit
- `hiddenimports` list in spec file references modules that no longer exist
- Nobody has done a PyInstaller build in the current cleanup cycle

**Phase to address:**
Every phase that moves or renames modules. Add "PyInstaller build test" as a phase gate for any structural cleanup phase.

---

### Pitfall 3: Singleton State Leaks Across Cleanup Boundaries

**What goes wrong:**
During cleanup, singletons (GlobalRegistry, MessageHandler, AsyncBridge, `_components_cache` in factory/core.py) accumulate stale state references to removed or restructured code. Tests pass individually but fail in batch. Or worse, tests pass but the singletons hold references to old module paths, causing subtle runtime bugs.

**Why it happens:**
CLASSIC uses at least four singletons with module-level mutable state:
- `GlobalRegistry` (class-level dict)
- `MessageHandler` (singleton)
- `AsyncBridge._instances` (thread-local dict)
- `_components_cache` in `ClassicLib/integration/factory/core.py` (module-level dict)
- `_VERSION_WARNING_LOGGED` in `ClassicLib/support/game_path.py` (module-level bool)

When cleanup changes what these singletons reference (e.g., moving a message backend, restructuring the registry), the cached state becomes stale. CONCERNS.md already documents that `_VERSION_WARNING_LOGGED` is fragile in tests. The `_components_cache` caches Rust availability once -- if a factory is restructured, the cache does not know.

**How to avoid:**
1. Reset ALL singleton state between test runs. The existing `reset_cache()` in factory/core.py is a good pattern -- extend it to all singletons.
2. During cleanup, if a singleton's interface changes, grep for all call sites. Singletons are referenced everywhere and don't show up in import graphs.
3. Consider adding a `reset_all_singletons()` test fixture that is `autouse=True` for the entire test suite.
4. When consolidating singletons (e.g., merging GlobalRegistry with another registry), do it in a single atomic step with all tests updated.

**Warning signs:**
- Tests pass individually (`pytest tests/path/to/test.py`) but fail in batch (`pytest -n auto`)
- Test order affects results (classic singleton contamination)
- Module-level mutable variables (`global` keyword in function body)

**Phase to address:**
First phase (inventory) should catalog all singletons. Singleton cleanup should be its own focused step, not mixed with other refactoring.

---

### Pitfall 4: Breaking the Async/Sync Boundary During Sync Wrapper Removal

**What goes wrong:**
The cleanup removes deprecated sync wrappers (as recommended in CONCERNS.md for FormIDAnalyzer). But some call site deep in the GUI layer was using the sync wrapper from a QThread worker context where `await` is not available and `asyncio.run()` would conflict with the existing event loop. The GUI freezes or deadlocks.

**Why it happens:**
CLASSIC has a complex async model:
- CLI: native `asyncio.run()` at entry point
- GUI: Qt event loop + AsyncBridge for sync-to-async
- Workers: QThread with AsyncBridge (thread-local instances)
- Rust: Tokio runtime (single global)

The sync wrappers exist because some GUI code paths cannot use `await`. Removing them requires understanding which call sites need AsyncBridge and which are already async. The CONCERNS.md notes: "No tests verify sync wrappers aren't called in CLI/TUI mode." This means the usage map is incomplete.

**How to avoid:**
1. Before removing any sync wrapper, trace ALL call sites using grep. Pay special attention to `ClassicLib/Interface/workers/` and `ClassicLib/Interface/controllers/`.
2. For each call site, determine the execution context: Is it in a QThread? Is it in the Qt main thread? Is it in an async context?
3. Replace sync wrappers with the appropriate async pattern for each context:
   - QThread workers: `AsyncBridge.run_async(coro)`
   - Qt main thread slots: `qasync` integration
   - CLI/TUI: direct `await`
4. Test GUI functionality manually after each sync wrapper removal. Deadlocks are not caught by unit tests.

**Warning signs:**
- Sync wrapper removal PR that only updates unit tests, not integration tests
- No GUI testing (manual or automated) after removing sync code
- AsyncBridge `run_async` calls that were previously sync wrapper calls -- verify the caller is actually in a sync context

**Phase to address:**
Dual interface consolidation phase. This should be a dedicated phase, not mixed with dead code removal, because the failure mode (deadlock) is invisible to automated tests.

---

### Pitfall 5: Removing Rust Crates That Are Depended On Through Cargo Workspace Features

**What goes wrong:**
A Rust `-core` crate appears unused (no Python binding imports it directly). It is removed from `Cargo.toml` workspace members. But another `-core` crate depends on it via `[dependencies]`. The entire Rust workspace fails to build. Or worse, the dependency was optional and the build succeeds but a feature is silently disabled.

**Why it happens:**
The workspace has 19 business-logic crates and matching Python binding crates. The dependency graph between `-core` crates is not obvious from the workspace member list. For example, `classic-scanlog-core` likely depends on `classic-yaml-core` for reading configuration, and `classic-scangame-core` may depend on `classic-path-core`. Removing a crate that looks unused from the Python side can break the Rust side.

**How to avoid:**
1. Before removing any Rust crate, run `cargo tree -p classic-<name>-core --invert` to see what depends on it.
2. Run `cargo build --workspace` after every crate removal to verify the workspace is intact.
3. Check both the `-core` and `-py` crate for each removal -- the `-py` crate may re-export types from `-core` that other `-py` crates use.
4. Look at `[workspace.dependencies]` in the root `Cargo.toml` -- removing a crate from `members` does not remove its entry from workspace deps, which can cause confusing errors.

**Warning signs:**
- Crate removed from workspace members but `cargo build` not run before committing
- `Cargo.lock` changes that remove transitive dependencies unexpectedly
- `-py` crate that wraps a `-core` crate where the `-core` crate is being removed

**Phase to address:**
Rust cleanup phase (should be separate from Python cleanup). Rust crate dependencies form a graph that needs analysis before removal.

---

### Pitfall 6: Consolidating Overlapping Abstractions Breaks the Integration Layer Contract

**What goes wrong:**
Two abstractions that appear redundant (e.g., `FileIOCore` Python + `classic_file_io` Rust) are merged into one. But the factory pattern in `ClassicLib/integration/factory/file_io.py` expects a specific interface -- method names, parameter signatures, return types. The consolidated version has a slightly different interface. The factory returns an object that does not match what callers expect.

**Why it happens:**
The Rust and Python implementations of the same concept often have subtly different APIs. The Python version might return `pathlib.Path`, the Rust version returns `str`. The Python version might be async, the Rust version sync. The factory normalizes this -- but the normalization logic is in the factory function, not in the implementations. When you consolidate, you lose the normalization.

**How to avoid:**
1. Document the interface contract for each factory function BEFORE consolidating. What methods? What signatures? What return types?
2. Use Python Protocol classes (typing.Protocol) to define the interface, then verify both implementations satisfy it.
3. When consolidating, update the factory function and all callers in the same PR. Do not leave the factory pointing at a half-migrated implementation.
4. Run integration tests (not just unit tests) after consolidation -- the factory/caller interaction is an integration boundary.

**Warning signs:**
- Factory function updated without updating callers
- Return type changes (e.g., `str` to `Path`, sync to async) without updating all consumers
- Tests that mock the factory return value (these tests pass even when the real factory is broken)

**Phase to address:**
Abstraction flattening phase. This needs careful interface documentation before any merging begins.

---

### Pitfall 7: Lazy YAML Import Discipline Breaks During Module Consolidation

**What goes wrong:**
CLAUDE.md rule 8 states: "Lazy YAML imports -- Import `yaml_settings`, `classic_settings` inside functions to avoid circular imports." During cleanup, modules are merged or moved. The developer adds a top-level import of YAML settings in the consolidated module because it looks cleaner. Circular import chain triggers at startup. Application fails to launch.

**Why it happens:**
CLASSIC's YAML configuration system is loaded eagerly during `SetupCoordinator.initialize_application()`. Many modules need YAML settings, but the YAML module itself depends on core infrastructure that depends on other modules that need settings. The lazy import pattern breaks this cycle. During cleanup, the "why" behind lazy imports is not obvious -- it looks like sloppy code that should be cleaned up.

**How to avoid:**
1. Add a comment on every lazy YAML import: `# Lazy import: circular dependency with ClassicLib.io.yaml`
2. During cleanup, if two modules with lazy imports are merged, keep the lazy import pattern even if it looks redundant.
3. Test startup (not just individual module tests) after any module consolidation: `uv run python -c "from ClassicLib import ..."` to verify no circular imports.
4. Consider creating a `LAZY_IMPORTS.md` document listing all intentional lazy imports and why they exist, so cleanup does not accidentally "fix" them.

**Warning signs:**
- `ImportError` or `AttributeError` at startup that was not present before cleanup
- Module consolidation PR that converts lazy (function-level) imports to module-level imports
- Circular import errors only visible when running the actual application, not in isolated tests

**Phase to address:**
Any phase that moves or consolidates Python modules. This is a cross-cutting concern, not a single phase.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems during cleanup.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Removing code without tracing all callers | Faster cleanup | Runtime crashes in untested paths | Never during cleanup of a production app |
| Skipping PyInstaller build verification | Saves 5-10 minutes per change | Broken release build discovered late | Never -- build verification is non-negotiable |
| Updating tests to pass without understanding why they broke | Green CI faster | Masks real breakage, false confidence | Never -- broken tests mean the refactoring is wrong |
| Removing sync wrappers without GUI testing | Simplifies code quickly | Deadlocks in GUI that only show under load | Never for GUI-affecting changes |
| Cleaning Python and Rust in the same commit | Fewer commits | Impossible to bisect if something breaks | Only for trivially coupled changes (e.g., removing a stub + its binding) |

## Integration Gotchas

Common mistakes when changing the Python-Rust boundary during cleanup.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| PyO3 bindings (`.pyi` stubs) | Removing or renaming a Python-side module without updating the `.pyi` type stub for the Rust binding | Update `.pyi` stubs in the same commit as any interface change; run `pyright` to verify |
| Factory pattern | Changing a Rust module's Python API without updating the factory fallback | Test with `CLASSIC_DISABLE_RUST=1` after any Rust API change |
| `classic_shared::get_runtime()` | Creating a second Tokio runtime during refactoring of async code | grep for `tokio::runtime::Runtime::new` -- there should be exactly one, in classic-shared-core |
| PyInstaller Rust bundling | Moving `.pyd` files or renaming crates without updating `pyinstaller_rust_helper` | Run `find_rust_extensions()` manually and verify it finds all expected modules |
| `_components_cache` | Not calling `reset_cache()` in test fixtures after changing detector behavior | Add `reset_cache()` to test setup for any test touching the integration layer |

## Performance Traps

Patterns that work at small scale but fail during cleanup verification.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Running full test suite after every small cleanup change | Test runs take 5+ minutes, developer starts skipping tests | Use `pytest -m "unit and not slow"` for fast feedback; full suite as phase gate only | When cleanup changes span 20+ files |
| `cargo build --workspace` on every Rust change | 2-5 minute incremental builds on Windows | Use `cargo check` for quick verification; full build at phase end | When touching Cargo.toml workspace config |
| PyInstaller rebuild after every Python change | 3-10 minute builds | Only rebuild at phase boundaries or when module structure changes | When cleanup is module-level restructuring |

## UX Pitfalls

Common mistakes that affect end users during cleanup of a user-facing tool.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Changing log output format during "cleanup" | Users who parse CLASSIC output with scripts break | Treat output format as API -- no changes unless explicitly decided |
| Renaming CLI arguments for "consistency" | Users' batch scripts and shortcuts break | CLI arguments are user-facing API -- deprecate, do not rename |
| Changing crash report markdown format | Users familiar with report layout are confused | Report format is a feature -- changes require explicit decision |
| Removing "redundant" error messages that users rely on for debugging | Users lose diagnostic information | Before removing any user-visible message, verify it is not documented in community guides |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces during cleanup.

- [ ] **Dead code removal:** Module deleted but still referenced in `CLASSIC.spec` hidden imports -- verify spec file is updated
- [ ] **Sync wrapper removal:** Wrapper deleted but AsyncBridge call site not updated in GUI worker -- verify all GUI paths manually
- [ ] **Factory consolidation:** Factory updated but `.pyi` type stubs still reference old interface -- run `pyright` strict mode
- [ ] **Rust crate removal:** Crate removed from workspace but still in another crate's `[dependencies]` -- run `cargo build --workspace`
- [ ] **Import cleanup:** Module-level import replaces lazy import, works in tests, circular import in production -- test with `uv run python CLASSIC_Interface.py` and `uv run python CLASSIC_ScanLogs.py`
- [ ] **Test fixture cleanup:** Fixture removed but another fixture depended on it via conftest chain -- run `pytest --collect-only` to verify all tests are discoverable
- [ ] **Singleton cleanup:** Singleton interface changed but test reset fixtures not updated -- run full suite with `pytest -n auto` (parallel catches state leaks)

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Broken PyInstaller build | LOW | Revert module rename, update spec, rebuild. Git bisect to find breaking commit. |
| Deadlocked GUI after sync removal | MEDIUM | Revert sync wrapper removal. Map all call sites more carefully. Reapply with correct AsyncBridge calls. |
| Circular import from lazy import cleanup | LOW | Revert to lazy import. Add comment explaining why. |
| Broken Rust workspace | LOW | `cargo build --workspace` error message identifies the missing dep. Re-add crate or update dependents. |
| Singleton state corruption in tests | MEDIUM | Add `autouse=True` reset fixture. May need to audit all test files for implicit singleton usage. |
| Removed fallback causes user crashes | HIGH | Emergency release with fallback restored. Requires understanding which users are affected (those without Rust extensions). |
| Factory contract broken | MEDIUM | Add Protocol class defining the interface. Update both implementations to match. Run integration tests. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Removing active Python fallbacks | Audit/inventory phase | Run test suite with `CLASSIC_DISABLE_RUST=1`; all core features must pass |
| Breaking PyInstaller hidden imports | Every structural phase | PyInstaller build + launch test at each phase gate |
| Singleton state leaks | Singleton cleanup sub-phase | Full test suite with `pytest -n auto` (parallel) -- no order-dependent failures |
| Async/sync boundary breakage | Dual interface consolidation phase | Manual GUI testing + stress test with concurrent scanning |
| Rust crate dependency breakage | Rust cleanup phase | `cargo build --workspace` + `cargo test --workspace` at phase gate |
| Factory contract breakage | Abstraction flattening phase | Integration tests for each factory function with both Rust and Python paths |
| Circular import from lazy import loss | Any module consolidation phase | `uv run python -c "import ClassicLib"` and both entry points launch successfully |
| M1: Nested runtime | Every migration phase | grep for `Runtime::new()`, only one in classic-shared-core |
| M2: GIL deadlock | Orchestration migration | Manual batch processing test, check for hangs |
| M3: Behavioral parity | Report generation migration | Golden file tests against Python output |
| M4: Memory ownership | Every migration phase | Clippy lints, fuzz testing |
| P1: Type conversion overhead | Performance baseline phase | FFIProfiler data showing conversion vs compute time |
| P2: GIL holding | Hot path optimization | Add `py.allow_threads()` to operations >1ms |
| P3: Test non-determinism | Bug fix phase | Tests pass with parallel execution |
| P4: Debug builds | All performance work | Release mode documented in all benchmarks |
| P5: Mean vs minimum | All performance work | Report percentiles, use minimum for comparisons |

## Sources

- `J:\CLASSIC-Fallout4\.planning\codebase\CONCERNS.md` -- Known bugs, tech debt, fragile areas, test gaps
- `J:\CLASSIC-Fallout4\.planning\codebase\ARCHITECTURE.md` -- Data flow, async patterns, factory pattern
- `J:\CLASSIC-Fallout4\.planning\codebase\TESTING.md` -- Test organization, singleton mocking patterns
- `J:\CLASSIC-Fallout4\.planning\codebase\STRUCTURE.md` -- Module layout, Rust crate inventory
- `J:\CLASSIC-Fallout4\.planning\PROJECT.md` -- Cleanup scope, constraints, key decisions
- `J:\CLASSIC-Fallout4\CLASSIC.spec` -- PyInstaller configuration with hardcoded module paths
- `J:\CLASSIC-Fallout4\rust\Cargo.toml` -- Workspace membership and dependency graph
- `J:\CLASSIC-Fallout4\ClassicLib\integration\factory\core.py` -- Singleton cache, Rust disable mechanism
- `J:\CLASSIC-Fallout4\.claude\rules\` -- Project conventions (lazy imports, ONE RUNTIME, TDD)
- [PyO3 Performance Guide](https://pyo3.rs/main/performance) -- GIL release, type conversion, reference pool
- [PyO3 Migration Guide](https://pyo3.rs/v0.22.4/migration) -- Official PyO3 migration documentation
- [PyO3 FAQ and Troubleshooting](https://pyo3.rs/main/faq) -- Common issues and solutions
- [Python timeit Documentation](https://docs.python.org/3/library/timeit.html) -- Use minimum not mean
- [Criterion.rs Documentation](https://bheisler.github.io/criterion.rs/book/) -- Rust benchmarking best practices
- [The Rust Performance Book](https://nnethercote.github.io/perf-book/benchmarking.html) -- Release builds, warmup
- [ScyllaDB Async Rust Performance](https://www.scylladb.com/2022/01/12/async-rust-in-practice-performance-pitfalls-profiling/) -- FuturesUnordered pitfall
- [GIL Deadlock Discussion](https://github.com/PyO3/pyo3/discussions/3045) -- Multi-threaded Tokio GIL issues
- [Migrating from Python to Rust](https://corrode.dev/learn/migration-guides/python-to-rust/) -- General migration best practices
- [py-spy Profiler](https://github.com/benfred/py-spy) -- Sampling profiler for Python with Rust support

---
*Pitfalls research for: CLASSIC hybrid Python-Rust codebase cleanup, migration, and performance optimization*
*Initially researched: 2026-02-01*
*Updated for migration pitfalls: 2026-02-02*
*Updated for performance benchmarking pitfalls (v8.3.0): 2026-02-04*
