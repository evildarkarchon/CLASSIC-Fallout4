# Feature Landscape: Performance Benchmarking Suite

**Domain:** Hybrid Python-Rust application performance measurement
**Project:** CLASSIC v8.3.0 benchmarking milestone
**Researched:** 2026-02-04
**Confidence:** HIGH (based on official documentation, verified ecosystem research, and existing codebase analysis)

## Table Stakes

Features users expect. Missing = benchmarks are not meaningful or actionable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Wall-clock time measurement | Basic performance metric everyone needs | Low | Already have via `time.perf_counter()` and Criterion |
| Mean/median/stddev statistics | Essential for understanding typical performance | Low | Criterion provides this; pytest-benchmark provides min/max/mean/stddev/median/iqr |
| Rust vs Python comparison | Core value prop of hybrid app is Rust speedup | Medium | Already tracking speedup ratios (15-25x observed in orchestrator results) |
| Warmup iterations | JIT/cache effects distort first runs | Low | Criterion handles automatically; pytest-benchmark has configurable warmup |
| Multiple iterations | Single runs are noisy; need statistical significance | Low | Both Criterion and pytest-benchmark handle this |
| Per-operation timing | Need granular view of hot paths | Low | Already have via `classic-perf-core` Timer |
| Output to file/JSON | Results need to be stored for tracking | Low | pytest-benchmark exports JSON; orchestrator results already CSV format |
| Operations per second (OPS) | Throughput metric for batch operations | Low | Standard metric in pytest-benchmark |

## Differentiators

Features that set the benchmark suite apart. Not expected but add significant value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Historical regression detection** | Catch performance regressions before production | Medium | Bencher provides change point detection; compare against baselines |
| **PyO3 FFI overhead isolation** | Measure actual Rust time vs cross-language overhead | Medium | FFI overhead is 20-40ns per call; batch calls keep overhead <3% |
| **Parallel scaling efficiency** | Measure Amdahl/Gustafson scaling | Medium | Track speedup/cores ratio; target >75% efficiency |
| **Cache hit rate tracking** | Validate DashMap cache effectiveness | Medium | Track hits vs misses for `classic-settings` cache; target >90% hit rate |
| **Memory usage tracking** | Detect memory leaks, measure allocation patterns | High | dhat crate for Rust; tracemalloc for Python; heaptrack for detailed analysis |
| **Percentile latencies (p50/p95/p99)** | Understand tail latency for worst-case users | Medium | p95/p99 critical for SLA guarantees; ensure consistency |
| **Throughput metrics (bytes/sec)** | Measure file I/O and parsing throughput | Low | Already have `record_bytes()` in perf-core; calculate MB/s |
| **CI integration** | Automated regression detection in pull requests | Medium | Bencher supports GitHub Actions; can fail builds on regressions |
| **HTML reports/charts** | Visual performance trends over time | Medium | Criterion generates HTML reports with gnuplot |
| **Component-level breakdown** | Attribute time to parsing/analysis/reporting | Medium | Use Timer spans for each phase in orchestrator pipeline |

## Anti-Features

Features to explicitly NOT build. Common over-engineering mistakes.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Custom benchmark framework** | Reinventing Criterion/pytest-benchmark wastes effort | Use Criterion for Rust, pytest-benchmark for Python, Bencher for tracking |
| **Real-time profiling in production** | Adds overhead, security concerns | Run benchmarks in dedicated test environment |
| **Flame graphs in every run** | Expensive to generate, rarely needed | Generate on-demand when investigating hot paths |
| **Sub-microsecond precision everywhere** | Noise dominates at this scale for most operations | Focus on millisecond-level for end-to-end, microsecond only for FFI overhead |
| **Automatic optimization suggestions** | AI/ML overhead not justified; manual analysis better | Document known optimization patterns, flag regressions for human review |
| **Cross-platform benchmark parity** | Windows/Linux have different performance characteristics | Track per-platform; compare to self, not cross-platform |
| **Memory profiling in every run** | Expensive; distorts timing measurements | Separate memory profiling runs from timing benchmarks |
| **Benchmarking every function** | Diminishing returns; noise in results | Focus on hot paths: orchestrator, YAML parsing, report generation |

## Feature Dependencies

```
Basic Timing
    |
    v
Statistics (mean/median/stddev)
    |
    +---> Regression Detection
    |         |
    |         v
    |     CI Integration
    |
    +---> Historical Tracking
    |         |
    |         v
    |     HTML Reports
    |
    v
Component Breakdown
    |
    +---> FFI Overhead Isolation
    |
    +---> Cache Hit Rate Tracking
    |
    +---> Parallel Scaling Efficiency
```

## Metrics Taxonomy

### Latency Metrics (time per operation)

| Metric | When to Use | Target for CLASSIC |
|--------|-------------|-------------------|
| Mean | General performance overview | Primary display metric |
| Median | Robust to outliers | Use for noisy operations |
| Min | Best-case scenario | Theoretical optimum |
| Max | Worst-case scenario | SLA ceiling |
| p95 | "Unlucky 5%" experience | Report generation targets |
| p99 | Near worst-case | Batch processing targets |
| Stddev | Consistency measure | Lower = more predictable |

### Throughput Metrics (work per time)

| Metric | When to Use | Target for CLASSIC |
|--------|-------------|-------------------|
| Operations/second | Count-based work | Crash logs processed/sec |
| Bytes/second | I/O-bound work | YAML parsing, file reading |
| Speedup ratio | Rust vs Python comparison | Track per operation type |

### Efficiency Metrics (resource utilization)

| Metric | When to Use | Target for CLASSIC |
|--------|-------------|-------------------|
| Parallel efficiency | Multi-threaded operations | (speedup / cores) > 75% |
| Cache hit rate | Caching effectiveness | >90% for settings cache |
| Memory per operation | Memory efficiency | Constant memory (O(1)) via rolling stats |

## Operations to Benchmark

Based on CLASSIC's architecture and existing infrastructure:

### Tier 1: Critical Path (Must Have)

| Operation | Current State | Benchmark Approach |
|-----------|--------------|-------------------|
| Crash log scanning (end-to-end) | Tracked in `orchestrator_single_log.txt` | pytest-benchmark + comparison fixture |
| Batch log processing | Tracked in `orchestrator_batch.txt` | pytest-benchmark with scaling tests |
| YAML settings loading | `test_benchmark_yaml_load_file` exists | Add cache hit/miss tracking |
| Report generation | Not systematically tracked | Add Criterion benchmark in Rust |

### Tier 2: Important (Should Have)

| Operation | Current State | Benchmark Approach |
|-----------|--------------|-------------------|
| FormID extraction | `test_benchmark_scanlog_extract_formids` exists | Add throughput metrics |
| Segment parsing | `test_benchmark_scanlog_parse_segments` exists | Add larger corpus tests |
| Game path detection | Not tracked | Add pytest-benchmark |
| File I/O concurrent reads | `test_concurrent_file_reading` exists | Add scaling tests |

### Tier 3: Nice to Have

| Operation | Current State | Benchmark Approach |
|-----------|--------------|-------------------|
| String interning (lasso) | Criterion benchmarks exist | Track memory efficiency |
| DashMap operations | Not isolated | Add microbenchmarks |
| Regex compilation | Not tracked | One-time cost, low priority |

## Existing Infrastructure Analysis

### What's Already Built

CLASSIC already has significant benchmarking infrastructure:

**Rust (Criterion):**
- `rust/foundation/classic-shared-core/benches/performance_benchmarks.rs` - Timer, metrics recording, throughput calculation, concurrent recording, memory efficiency
- `rust/foundation/classic-shared-core/benches/string_benchmarks.rs` - String operations
- `rust/foundation/classic-shared-core/benches/path_benchmarks.rs` - Path operations

**Python (pytest):**
- `tests/benchmarks/test_rust_ffi_performance.py` - FFI overhead for scanlog and YAML
- `tests/performance/test_benchmarks_performance.py` - File I/O, FormID analyzer, orchestrator, memory efficiency, concurrency
- `tests/performance/` directory with 16+ performance test files

**Historical Tracking:**
- `performance/results/orchestrator_single_log.txt` - CSV with timestamp, Python time, Rust time, speedup ratio
- `performance/results/orchestrator_batch.txt` - Batch processing results

**Observed Speedups (from orchestrator_single_log.txt):**
- Range: 4.6x to 27.8x Rust speedup
- Recent stable: ~20-25x speedup
- Mean Python time: ~4-6 seconds
- Mean Rust time: ~0.17-0.30 seconds

### Gaps to Fill

| Gap | Impact | Recommendation |
|-----|--------|---------------|
| No automated regression detection | Regressions slip through unnoticed | Integrate Bencher or add baseline comparison |
| No cache hit rate tracking | Can't validate cache effectiveness | Instrument DashMap with counters |
| No percentile metrics | Missing tail latency understanding | Add p95/p99 calculation |
| No CI pipeline integration | Manual benchmark running only | Add GitHub Actions workflow |
| Scattered benchmark results | Hard to trend over time | Consolidate to single JSON format |

## MVP Recommendation

For v8.3.0 milestone, prioritize:

1. **Baseline establishment** (Table Stakes)
   - Formalize existing orchestrator_*.txt tracking
   - Add pytest-benchmark to Tier 1 operations
   - Export results to JSON for tracking

2. **Rust vs Python comparison framework** (Table Stakes)
   - Systematic speedup ratio tracking
   - Document methodology for fair comparison

3. **Regression detection** (Differentiator)
   - Integrate with Bencher or custom baseline comparison
   - Fail builds when performance regresses >10%

4. **Cache hit rate tracking** (Differentiator)
   - Instrument `classic-settings` DashMap cache
   - Track and report hit/miss ratios

Defer to post-v8.3.0:
- Memory profiling: Requires separate infrastructure, distorts timing
- HTML reports: Nice for visualization but not blocking
- Sub-component flame graphs: On-demand debugging tool

## Tooling Recommendations

### Rust Benchmarking

**Use:** [Criterion.rs](https://github.com/bheisler/criterion.rs) (already in use)
- Statistics-driven microbenchmarking
- Automatic regression detection
- HTML reports with gnuplot
- Supports throughput measurement

**Version:** Criterion supports Rust 1.88+; CLASSIC uses 1.85+ (compatible)

### Python Benchmarking

**Use:** [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- Integrates with existing pytest infrastructure
- Provides min/max/mean/stddev/median/iqr/outliers/ops/rounds
- JSON export for tracking
- Histogram and SVG plot generation

**Version:** pytest-benchmark 5.2.3 (current)

### Continuous Benchmarking

**Use:** [Bencher](https://bencher.dev/) (recommended) or custom baseline tracking
- Catch performance regressions in CI
- Change point detection (reduces false positives)
- Supports both Criterion and pytest-benchmark adapters
- On-prem or cloud deployment

### Memory Profiling (when needed)

**Rust:** [dhat](https://docs.rs/dhat/latest/dhat/) for heap profiling
**Python:** Built-in `tracemalloc` module
**Cross-language:** heaptrack (Linux) for detailed analysis

## Measurable Outcomes

| Metric | Current State | Target | How to Measure |
|--------|---------------|--------|----------------|
| Benchmark coverage (Tier 1 ops) | Partial | 100% | Count operations with benchmarks |
| Historical data retention | Ad-hoc CSV | 90 days JSON | CI artifact retention |
| Regression detection | Manual | Automated CI | GitHub Actions check |
| Cache hit rate visibility | None | Dashboard metric | Instrumented counters |
| Speedup ratio tracking | Yes (CSV) | Automated trend | Bencher or similar |

## Sources

### Tool Documentation
- [Criterion.rs GitHub](https://github.com/bheisler/criterion.rs)
- [pytest-benchmark Documentation](https://pytest-benchmark.readthedocs.io/)
- [Bencher - Continuous Benchmarking](https://bencher.dev/)
- [dhat crate](https://docs.rs/dhat/latest/dhat/)

### Best Practices
- [How to benchmark Rust code with Criterion](https://bencher.dev/learn/benchmarking/rust/criterion/)
- [PyO3 Performance Analysis](https://github.com/PyO3/pyo3/issues/1607)
- [Rust-Python FFI with PyO3](https://johal.in/rust-python-ffi-with-pyo3-creating-high-performance-extensions-for-performance-critical-apps/)

### Metrics Standards
- [Cache Hit Ratio - Cloudflare](https://www.cloudflare.com/learning/cdn/what-is-a-cache-hit-ratio/)
- [Parallel Scaling Guide - Mines Research Computing](https://rc-docs.mines.edu/pages/user_guides/Parallel_Scaling_Guide.html)
- [Performance Benchmarking Guide - Dev.to](https://dev.to/subham_jha_7b468f2de09618/the-engineers-guide-to-benchmark-testing-moving-beyond-fast-vibes-3120)

### Codebase Analysis
- `j:\CLASSIC-Fallout4\tests\benchmarks\test_rust_ffi_performance.py`
- `j:\CLASSIC-Fallout4\tests\performance\test_benchmarks_performance.py`
- `j:\CLASSIC-Fallout4\rust\foundation\classic-shared-core\benches\performance_benchmarks.rs`
- `j:\CLASSIC-Fallout4\performance\results\orchestrator_single_log.txt`

---
*Feature research for: CLASSIC v8.3.0 performance benchmarking suite*
*Researched: 2026-02-04*
