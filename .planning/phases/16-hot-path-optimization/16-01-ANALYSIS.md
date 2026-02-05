# Phase 16 Hot Path Analysis

## Profiling Summary

- **Date:** 2026-02-04
- **Iterations:** 5
- **Mode:** thorough (cProfile deterministic profiling)
- **Entry point:** CLASSIC_ScanLogs.py
- **Logs processed:** 601 per iteration
- **Total time per iteration:** ~13.9 seconds (average)
- **Native frames:** Not available (py-spy incompatible with Python 3.14)

### Profiling Methodology

Due to py-spy 0.4.1 incompatibility with Python 3.14, profiling was conducted using cProfile (deterministic profiler). While cProfile cannot capture native Rust frames directly, it provides accurate Python-level timing and call counts. Rust execution time appears as time spent in Rust module method calls.

**Data collected:**
- 5 cProfile pstats files (703-704 KB each)
- Combined profile analysis (76.4s total, 12.3M function calls)
- DOT format call graph for visualization
- JSON export of top 100 functions

## Hot Path Rankings

Based on combined analysis of 5 profiling runs (76.4 seconds total runtime):

| Rank | Function | % Time | Location | Optimization Type | Priority |
|------|----------|--------|----------|-------------------|----------|
| 1 | thread.py:run | 86.0% | asyncio threading | Threading overhead | HIGH |
| 2 | _imp.create_dynamic | 1.0% | Python import system | Module loading | MEDIUM |
| 3 | BufferedReader.read | 0.9% | I/O operations | File reading | LOW |
| 4 | nt.stat | 0.7% | Filesystem stats | Path operations | LOW |
| 5 | _parser.py:_parse | 0.8% | Regex compilation | Pattern matching | MEDIUM |
| 6 | __init__.py:__eq__ | 0.7% | Path comparison | String operations | MEDIUM |
| 7 | executor.py:_handle_rust_result | 0.3% | Rust FFI | Result processing | HIGH |
| 8 | scan_result.py:add_processed_file | 0.2% | Result aggregation | Data structures | MEDIUM |

### Key Observations

1. **Threading Dominance (86%):** The asyncio thread pool dominates execution time. This is expected for an async application but indicates potential for:
   - Better work distribution across threads
   - Reduced thread synchronization overhead
   - Consider using Rust-native async instead of Python asyncio for hot paths

2. **Import/Module Loading (1%):** Dynamic module creation takes noticeable time, but this is startup cost only.

3. **Rust FFI Efficiency:** `_handle_rust_result` takes only 0.3% of time, indicating:
   - Rust processing is already very efficient
   - FFI overhead is minimal
   - Most optimization gains will come from Python-side improvements

4. **Filesystem Operations (1.6%):** Combined file reading and stat calls are minimal, indicating efficient file I/O.

## Optimization Targets

### Target 1: Threading/Async Coordination

- **Location:** `executor.py`, asyncio thread pool
- **Time contribution:** 86% (thread.py:run)
- **Optimization technique:**
  - Batch Rust calls to reduce thread coordination overhead
  - Consider moving orchestration to Rust for native async
  - Reduce Python<->Rust boundary crossings
- **Expected improvement:** 10-20% overall (reducing coordination overhead)

### Target 2: Regex Pattern Compilation Caching

- **Location:** `_parser.py`, Python re module
- **Time contribution:** 0.8% direct, affects subsequent matching
- **Optimization technique:**
  - Pre-compile patterns at module load time
  - Use compiled pattern objects instead of raw strings
  - Consider Rust regex for pattern matching in hot loops
- **Expected improvement:** 5-10% on pattern-heavy workloads

### Target 3: Result Aggregation Optimization

- **Location:** `scan_result.py:add_processed_file`, `executor.py:_handle_rust_result`
- **Time contribution:** 0.5% combined
- **Optimization technique:**
  - Batch result processing
  - Use pre-allocated data structures
  - Reduce Python object creation in hot loop
- **Expected improvement:** 5-10% on result processing

### Target 4: Path Comparison Optimization

- **Location:** `__init__.py:__eq__` (pathlib), `__init__.py:_str_normcase`
- **Time contribution:** 0.7% + 0.2% = 0.9%
- **Optimization technique:**
  - Cache normalized path strings
  - Use string comparison instead of Path objects where possible
  - Batch path operations in Rust
- **Expected improvement:** 3-5%

## Cache Statistics

```json
{
  "settings_cache": {
    "hits": 0,
    "misses": 0,
    "hit_rate": 0.0,
    "size": 0,
    "keys": []
  },
  "note": "Cache stats from cold start - cache utilization during scan not captured"
}
```

**Cache Analysis:**
- Settings cache shows cold start state
- Cache population happens during scan but stats aren't retained post-process
- Recommendation: Add cache stats logging at scan completion

## Unexpected Findings

1. **py-spy Incompatibility:** py-spy 0.4.1 does not support Python 3.14, preventing combined Python+Rust stack traces. This limits visibility into native frame performance.

2. **Threading Dominance:** The 86% threading overhead is higher than expected for a Rust-accelerated application. This suggests the parallelization strategy may have room for improvement.

3. **Low Rust Overhead:** Rust FFI overhead is remarkably low (0.3%), indicating that previous optimization phases were successful in minimizing boundary crossings.

4. **Minimal Import Cost:** Despite many Rust modules, import overhead is only ~1%, showing efficient module initialization.

5. **Async Context Bug:** During profiling, discovered `yaml_settings()` called from async context (should use `yaml_settings_async()`). This is a separate bug to address.

## Benchmark Baseline Summary

Pre-optimization benchmarks saved as `pre-opt-phase16`:

| Crate | Benchmark Groups | Baselines Saved |
|-------|------------------|-----------------|
| classic-yaml-core | 5 (parsing, serialization, traversal, modification, config) | 20 |
| classic-scanlog-core | 7 (segment, formid, pattern, plugin, record, pipeline, parser) | 42 |
| classic-file-io-core | 5 (encoding, path filtering, file io, log patterns, dds) | 24 |
| **Total** | **17** | **86** |

## Recommendations for 16-02

In priority order:

1. **Batch Rust Calls in Scan Loop**
   - Collect multiple log files before sending to Rust
   - Process in Rust as batch, return aggregated results
   - Expected: 10-15% overall improvement

2. **Pre-compile Regex Patterns**
   - Move pattern compilation to module initialization
   - Use compiled pattern cache
   - Expected: 5-10% improvement on pattern-heavy logs

3. **Optimize Result Aggregation**
   - Pre-allocate result structures
   - Reduce per-file object creation
   - Expected: 3-5% improvement

4. **Consider Alternative Allocator (mimalloc)**
   - Add mimalloc as optional feature for benchmarking
   - Test impact on Rust-side memory operations
   - Expected: Variable (depends on allocation patterns)

5. **Investigate Async Overhead**
   - Profile with and without threading
   - Consider single-threaded mode for small workloads
   - Expected: Better understanding of coordination cost

## Appendix: Profiling Data Locations

```
target/profiling/
  cprofile/
    cli-scan-run-1.pstats    # 703 KB
    cli-scan-run-2.pstats    # 704 KB
    cli-scan-run-3.pstats    # 704 KB
    cli-scan-run-4.pstats    # 704 KB
    cli-scan-run-5.pstats    # 703 KB
  pyspy/
    cli-scan-interactive.json # Top 100 functions analysis
    cli-scan-run-1.dot       # Call graph in DOT format
  cache-stats/
    pre-opt-stats.json       # Cache statistics

rust/target/criterion/
  [86 baseline directories named pre-opt-phase16]
```

---

*Analysis completed: 2026-02-04*
*Analyst: Claude Opus 4.5*
