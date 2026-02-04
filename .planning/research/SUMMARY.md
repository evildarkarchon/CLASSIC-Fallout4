# Project Research Summary

**Project:** CLASSIC v8.3.0 Performance & Polish
**Domain:** Hybrid Python-Rust application performance benchmarking and optimization
**Researched:** 2026-02-04
**Confidence:** HIGH

## Executive Summary

CLASSIC is a mature hybrid Python-Rust application that has already achieved significant performance gains (15-150x speedups) through Rust acceleration in its hot paths. The v8.3.0 milestone focuses on establishing scientific baselines, identifying remaining optimization opportunities, and fixing pre-existing bugs rather than speculative optimization. Research shows that CLASSIC already has the correct benchmarking infrastructure (Criterion 0.8.1 for Rust, FFIProfiler for PyO3 overhead tracking) but lacks automated regression detection and systematic GIL release patterns.

The recommended approach is methodical: establish release-mode baselines first, profile to identify hot paths second, optimize with measurement third. Research identified a critical gap: **zero usage of `py.allow_threads()` in the Rust codebase**, meaning Python's Global Interpreter Lock is held during all Rust operations. This blocks the Python runtime even when Rust is doing fast work, causing GUI freezes and async starvation. The priority order should be: (1) fix the GIL holding pattern, (2) establish accurate baselines, (3) profile to identify actual bottlenecks, (4) optimize based on data.

Key risks center on measurement methodology mistakes (debug builds instead of release, mean instead of minimum for microbenchmarks, type conversion overhead hidden in "Rust time") and test non-determinism from global cache state. These are well-documented in official PyO3 and Criterion documentation, giving high confidence in prevention strategies. The two pre-existing bugs (yaml-core cache test, GUI path resolution) have clear root causes and straightforward fixes.

## Key Findings

### Recommended Stack

CLASSIC should add minimal profiling tools to its existing Criterion 0.8.1 infrastructure rather than switching frameworks. The stack additions are strategic: `cargo-flamegraph` for CPU profiling, `tracing-flame` for async-aware profiling, `dhat` for heap analysis, and `py-spy` for cross-boundary profiling.

**Core additions:**
- **tracing-flame (0.2)**: Async-aware flame profiling — integrates with existing tracing infrastructure, captures async task boundaries critical for Tokio-based code
- **dhat (0.3.3)**: Heap allocation profiling — pure Rust, works on Windows, supports test assertions for CI-friendly allocation counting
- **cargo-flamegraph (0.6.11)**: CPU profiling tool — wraps perf/dtrace automatically, produces interactive SVG flamegraphs, no code changes required
- **py-spy (0.4)**: Python/Rust cross-boundary profiler — captures Rust stack frames alongside Python with `--native` flag, 2% overhead
- **github-action-benchmark**: CI regression detection — free for public repos, stores results in GitHub Pages, configurable alert thresholds

**What NOT to add:** Custom frameworks (Criterion already works), jemalloc (invasive), Divan (would require rewriting existing benchmarks), iai-callgrind (Linux-only, Windows is primary platform).

**Total impact:** 3-4 dev-dependencies, all opt-in via feature flags, zero runtime overhead when disabled.

### Expected Features

The benchmarking suite research identified table stakes (must have for meaningful benchmarks), differentiators (features that add significant value), and anti-features (common over-engineering to avoid).

**Must have (table stakes):**
- Wall-clock and CPU time measurement — already have via FFIProfiler
- Statistical rigor (mean/median/stddev/percentiles) — Criterion provides, pytest-benchmark provides
- Rust vs Python comparison — core value prop, already tracking speedup ratios
- Warmup iterations — handled by Criterion automatically
- JSON export for historical tracking — pytest-benchmark supports

**Should have (competitive differentiators):**
- **Historical regression detection** — catch performance regressions in CI before production (Bencher or github-action-benchmark)
- **PyO3 FFI overhead isolation** — measure type conversion vs actual Rust work separately (FFIProfiler already instruments this)
- **Cache hit rate tracking** — validate DashMap effectiveness in classic-settings (currently no instrumentation)
- **Percentile latencies (p95/p99)** — understand tail latency for worst-case users
- **Component-level breakdown** — attribute time to parsing/analysis/reporting phases

**Defer (anti-features to avoid):**
- Custom benchmark framework — reinventing Criterion wastes effort
- Real-time profiling in production — overhead and security concerns
- Flame graphs in every run — expensive, generate on-demand only
- Sub-microsecond precision everywhere — noise dominates at this scale for most operations
- Cross-platform benchmark parity — Windows and Linux have different characteristics, compare to self not cross-platform

### Architecture Approach

CLASSIC's benchmarking architecture should follow Rust workspace conventions: crate-level `benches/` directories for pure Rust benchmarks, Python-side pytest-benchmark for FFI overhead measurement, and a workspace-level `classic-bench` integration crate for end-to-end pipelines. The architecture separates concerns: pure Rust performance is measured without PyO3 overhead, then FFI overhead is measured separately, allowing clear attribution of time spent.

**Major components:**
1. **Crate-level Rust benchmarks** (`{crate}/benches/`) — Pure Rust microbenchmarks using Criterion, measuring algorithm performance without Python boundary crossing. Priority crates: classic-yaml-core, classic-scanlog-core, classic-file-io-core.
2. **Workspace integration benchmarks** (`rust/benchmarks/classic-bench/`) — New dedicated benchmark crate for cross-cutting concerns and end-to-end pipelines, depends on all -core crates.
3. **Python FFI overhead tests** (`tests/benchmarks/`) — Python-side pytest-benchmark measuring round-trip overhead, type conversion costs, batch vs individual calls, GIL impact. Cannot be measured from Rust alone.
4. **CI regression detection** — GitHub Actions workflow storing baselines, comparing PRs against baselines, alerting on regressions >10-15%.

**Key architectural decision:** Measure pure Rust and FFI overhead separately. Benchmarking Rust code by calling from Python conflates the two and makes optimization decisions unclear. The FFIProfiler already captures this separation (wall_time, cpu_time, input_size, output_size per call).

### Critical Pitfalls

Research identified 14 performance-specific pitfalls plus 10 migration pitfalls (for context). The top 5 for v8.3.0 are:

1. **Holding GIL during long Rust operations (Pitfall P2 - CRITICAL)** — Python's Global Interpreter Lock remains held during Rust execution by default, blocking all Python threads and async tasks. Even 50ms blocks the entire runtime. **CRITICAL FINDING: grep of rust/ directory shows ZERO matches for `py.allow_threads()` or `allow_threads`.** This is a systemic gap. Prevention: Use `py.allow_threads(|| { ... })` for any operation >1ms. Detection: GUI freezes during "fast" Rust operations, async tasks starve.

2. **Measuring FFI overhead without isolating type conversion (Pitfall P1)** — PyO3 type conversion (dict to HashMap, list to Vec) happens transparently but has measurable cost. The `yaml_to_python()` function in classic-yaml-py recursively converts every node. For nested YAML, this is significant. Prevention: Use FFIProfiler to measure input_size/output_size, benchmark Rust-side logic separately using Criterion. Detection: Speedup varies wildly (5x to 50x) for similar operations.

3. **Global static state causing test non-determinism (Pitfall P3)** — Rust's `static` variables like `YAML_CACHE` persist across parallel test runs, causing intermittent failures. The pre-existing `test_clear_cache` bug is exactly this pitfall. Prevention: Use `#[serial_test::serial]` for tests touching global state, clear cache at start AND end of tests. Detection: Tests pass with `--test-threads=1` but fail in parallel.

4. **Benchmarking debug builds instead of release (Pitfall P4)** — Debug builds are 10-100x slower. Prevention: Always use `--release`, document build mode in results, use `rebuild_rust.ps1` which defaults to release. Detection: Rust slower than Python for same algorithm.

5. **Using mean instead of minimum for microbenchmarks (Pitfall P5)** — Mean is heavily influenced by outliers from OS scheduling and thermal throttling. As Python timeit docs state: "the min() of the result is probably the only number you should be interested in." Prevention: Report minimum + percentiles (p50/p95/p99), not just mean. FFIProfileStats already has p95_call_time and p99_call_time.

## Implications for Roadmap

Based on research, the milestone should be structured around measurement methodology first, then optimization based on data. The critical GIL finding elevates "fix GIL holding" to a foundational step before accurate benchmarking.

### Phase 1: GIL Release Audit & Baseline Establishment
**Rationale:** Cannot establish accurate baselines until GIL holding is fixed. If Rust operations block Python threads, the measured performance does not reflect actual user experience. This phase fixes the foundational issue and establishes measurement methodology.

**Delivers:**
- Audit of all PyO3 functions for GIL release patterns
- Add `py.allow_threads()` to operations >1ms (scan_log, yaml parsing, database queries)
- Establish release-mode baselines for Tier 1 operations (crash log scanning, YAML loading, report generation)
- Document measurement methodology (minimum vs mean, warmup, percentiles)

**Addresses:**
- Table stakes: Wall-clock time, statistical rigor, warmup iterations
- Pitfall P2 (GIL holding) - foundational fix
- Pitfall P4 (debug builds) - establish release baselines

**Avoids:**
- Measuring performance with GIL blocking threads (false baselines)
- Optimizing based on debug build timings
- Using mean when minimum is more meaningful

**Research flag:** Standard pattern - PyO3 Performance Guide documents GIL release extensively. No deep research needed.

### Phase 2: Hot Path Profiling & Cache Instrumentation
**Rationale:** Once baselines are accurate (GIL not blocking, release builds), use profiling to identify actual bottlenecks rather than optimizing by intuition. Add cache hit rate tracking to validate assumptions about DashMap effectiveness.

**Delivers:**
- Flamegraph profiling of full scan workflow
- FFI overhead breakdown (conversion vs computation time)
- Cache hit rate instrumentation for classic-settings DashMap
- Identification of top 3-5 hot paths by total time (not per-call time)

**Uses:**
- cargo-flamegraph for CPU profiling
- tracing-flame for async task boundaries
- py-spy for Python/Rust cross-boundary profiling
- FFIProfiler for type conversion overhead measurement

**Implements:**
- Component-level breakdown architecture (Timer spans for parse/analyze/report phases)
- Cache hit rate tracking (differentiator feature)

**Avoids:**
- Pitfall P1 (FFI overhead hidden) - explicit measurement
- Pitfall P9 (optimizing wrong code) - sort by total time

**Research flag:** Standard pattern - profiling workflows well-documented in Rust Performance Book and PyO3 guides.

### Phase 3: Bug Fixes & Test Stabilization
**Rationale:** Fix pre-existing bugs with clear root causes before performance optimization. Test non-determinism masks real issues and must be resolved for reliable benchmarking.

**Delivers:**
- Fix `test_clear_cache` in classic-yaml-core (Pitfall P3)
- Fix GUI `classic_settings()` path resolution (Pitfall P14 - relative path bug)
- Ensure all cache-related tests use `#[serial]` attribute
- Verify tests pass with parallel execution (`pytest -n auto`)

**Addresses:**
- Pitfall P3 (global static state) - the exact root cause of test_clear_cache bug
- Pitfall P14 (relative path assumptions) - the exact root cause of GUI bug

**Avoids:**
- Flaky tests that pass/fail based on execution order
- GUI failures from path resolution bugs

**Research flag:** Standard pattern - bugs have documented root causes, fixes are straightforward.

### Phase 4: Hot Path Optimization (Data-Driven)
**Rationale:** Only after accurate baselines, profiling data, and stable tests should optimization begin. This phase targets the actual bottlenecks identified by profiling, not intuition.

**Delivers:**
- Optimize top 3 hot paths identified in Phase 2
- Batch small operations to reduce FFI crossings (if conversion overhead is high)
- Async optimization if Tokio runtime shows issues
- Re-benchmark to validate improvements

**Uses:**
- Profiling data from Phase 2 to target optimization
- Criterion for before/after microbenchmarks
- FFIProfiler to track improvement in FFI overhead

**Avoids:**
- Pitfall P9 (optimizing infrequently called code) - only target hot paths
- Pitfall P10 (async overhead for fast ops) - threshold check >1ms

**Research flag:** May need deeper research depending on which hot paths are identified. If optimization targets unusual areas (e.g., GUI rendering, database indexing), use `/gsd:research-phase`.

### Phase 5: CI Regression Detection
**Rationale:** Lock in performance gains with automated regression detection. This prevents future changes from undoing optimization work.

**Delivers:**
- GitHub Actions workflow for benchmark runs
- Baseline storage and comparison
- Alert on regressions >10-15%
- HTML reports for trend visualization

**Uses:**
- github-action-benchmark for free self-hosted solution
- Criterion's `--baseline` feature for comparison

**Addresses:**
- Differentiator: Historical regression detection
- CI integration feature

**Research flag:** Standard pattern - github-action-benchmark documentation covers setup thoroughly.

### Phase Ordering Rationale

- **GIL release before baselines:** Baselines are meaningless if GIL is blocking threads. This is foundational.
- **Profiling before optimization:** Avoid Pitfall P9 (optimizing wrong code). Measure, then optimize.
- **Bug fixes before optimization:** Test non-determinism masks real issues. Stable tests are prerequisite.
- **CI regression detection last:** Only after optimization is complete and working well should we lock in baselines for regression detection.

**Dependency chain:**
```
Phase 1 (GIL + Baselines)
    |
    v
Phase 2 (Profiling) <-- depends on accurate baselines
    |
    v
Phase 3 (Bug Fixes) <-- parallel to Phase 2, no dependency
    |
    v
Phase 4 (Optimization) <-- depends on profiling data
    |
    v
Phase 5 (CI) <-- depends on optimized baselines being stable
```

### Research Flags

**Phases with standard patterns (skip research-phase):**
- **Phase 1:** GIL release patterns extensively documented in PyO3 Performance Guide
- **Phase 2:** Profiling workflows covered in Rust Performance Book and flamegraph docs
- **Phase 3:** Bug root causes identified, fixes are straightforward path resolution and test isolation
- **Phase 5:** github-action-benchmark has clear setup documentation

**Phases that may need research:**
- **Phase 4:** Depends on what hot paths are identified. If optimization targets unusual areas (e.g., GUI rendering bottlenecks, SQLite query optimization, regex performance), use `/gsd:research-phase` to investigate best practices for that specific domain. If hot paths are in well-covered areas (YAML parsing, file I/O, string operations), existing research is sufficient.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Criterion already in use, profiling tools verified against official docs, versions checked |
| Features | HIGH | Table stakes and differentiators based on existing infrastructure analysis and benchmarking best practices |
| Architecture | HIGH | Existing codebase already has Criterion benchmarks, architecture extends established patterns |
| Pitfalls | HIGH | GIL finding verified by grep, PyO3 Performance Guide is authoritative source, bug root causes identified in codebase |

**Overall confidence:** HIGH

Research is based on official documentation (PyO3 Performance Guide, Criterion.rs docs, Rust Performance Book, Python timeit module), verified against existing CLASSIC codebase (FFIProfiler, Criterion usage, orchestrator results), and cross-referenced with technical sources (ScyllaDB async Rust analysis, py-spy profiler).

### Gaps to Address

**GIL release implementation details:** While the pattern (`py.allow_threads()` for operations >1ms) is clear from documentation, applying it to CLASSIC's specific Rust functions requires reviewing each PyO3 function's context. Some functions may be called from within `asyncio.to_thread()` already, which changes the threading model. This needs careful analysis during Phase 1 implementation, not just mechanical application of the pattern.

**Cache hit rate instrumentation approach:** Research identified that cache hit rate tracking is valuable (differentiator feature), but the specific mechanism for instrumenting DashMap in classic-settings-core is not detailed. Options include: atomic counters, tracing spans with metrics, or DashMap wrapper with counting. This is a low-risk gap (any approach works), but the choice affects performance measurement overhead.

**Hot path identity:** Cannot predict which hot paths profiling will identify until Phase 2 completes. If profiling reveals unexpected bottlenecks (e.g., string formatting, GUI rendering, regex compilation), those areas may need targeted research. The roadmap should budget for optional `/gsd:research-phase` invocation in Phase 4 based on profiling results.

**Pre-existing bug severity:** The `test_clear_cache` bug and GUI path resolution bug have clear root causes, but their real-world impact is not quantified. If these bugs affect production users frequently, they should be elevated in priority. Recommend asking: "How often do users report these issues?" before finalizing phase order.

## Sources

### Primary (HIGH confidence)
- [PyO3 Performance Guide](https://pyo3.rs/main/performance) — GIL release patterns, type conversion overhead, reference pool
- [Criterion.rs Documentation](https://bheisler.github.io/criterion.rs/book/) — Statistical benchmarking, baseline comparison, HTML reports
- [Python timeit Documentation](https://docs.python.org/3/library/timeit.html) — Use minimum not mean for microbenchmarks
- [The Rust Performance Book](https://nnethercote.github.io/perf-book/profiling.html) — Release builds, profiling workflows, heap allocations
- [cargo-flamegraph GitHub](https://github.com/flamegraph-rs/flamegraph) — Version 0.6.11, usage patterns
- [dhat crate documentation](https://docs.rs/dhat/latest/dhat/) — Heap profiling, test assertions
- [py-spy GitHub](https://github.com/benfred/py-spy) — Python/Rust cross-boundary profiling with `--native` flag
- [github-action-benchmark](https://github.com/benchmark-action/github-action-benchmark) — CI regression detection setup
- CLASSIC codebase analysis:
  - `j:\CLASSIC-Fallout4\tests\benchmarks\test_rust_ffi_performance.py`
  - `j:\CLASSIC-Fallout4\tests\performance\test_benchmarks_performance.py`
  - `j:\CLASSIC-Fallout4\rust\foundation\classic-shared-core\benches\performance_benchmarks.rs`
  - `j:\CLASSIC-Fallout4\performance\results\orchestrator_single_log.txt`
  - `j:\CLASSIC-Fallout4\tools\ffi_profiler.py`

### Secondary (MEDIUM confidence)
- [ScyllaDB Async Rust Performance](https://www.scylladb.com/2022/01/12/async-rust-in-practice-performance-pitfalls-profiling/) — FuturesUnordered quadratic scaling pitfall
- [PyO3 GitHub Discussion #3442](https://github.com/PyO3/pyo3/discussions/3442) — FFI overhead analysis
- [Bencher documentation](https://bencher.dev/docs/how-to/github-actions/) — Alternative CI regression detection
- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/) — Python benchmarking with statistics

### Tertiary (LOW confidence)
- Blog posts on Python-Rust performance — general patterns, not CLASSIC-specific
- Community discussions on benchmarking methodology — useful context but not authoritative

---
*Research completed: 2026-02-04*
*Ready for roadmap: yes*
