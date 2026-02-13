# Profiling Workflow for CLASSIC

This guide describes the workflow for identifying performance bottlenecks, establishing baselines, implementing optimizations, and verifying improvements in the CLASSIC hybrid Python-Rust codebase.

## Overview

Performance optimization in CLASSIC follows a systematic four-step process:

1. **Identify** - Find hot paths using profiling tools
2. **Baseline** - Establish measurable performance baseline
3. **Optimize** - Implement targeted improvements
4. **Verify** - Confirm improvements without regressions

## Prerequisites

### Required Tools

- **Rust toolchain** with Cargo (for Criterion benchmarks)
- **uv** package manager (for Python environment)
- **py-spy** (optional, for Python+Rust combined profiling) - Note: incompatible with Python 3.14+

### Optional Tools

- **cargo-flamegraph** - Rust flamegraph generation
- **critcmp** - Enhanced benchmark comparison (`cargo install critcmp`)
- **dhat** - Heap profiling for Rust code

### Setup

```bash
# Ensure Python environment is ready
uv sync --all-extras

# Build Rust extensions
./rebuild_rust.ps1

# Install optional Rust profiling tools
cargo install flamegraph
cargo install critcmp
```

## Step 1: Identify Hot Path

Before optimizing, identify where time is actually spent. Use profiling tools to find bottlenecks.

### For Rust Code: Flamegraph

Generate CPU flamegraphs for Rust benchmarks or applications:

```powershell
# Quick profiling during development
.\scripts\profile\run_flamegraph.ps1

# Thorough profiling for detailed analysis
.\scripts\profile\run_flamegraph.ps1 -Mode thorough

# Profile specific benchmark
.\scripts\profile\run_flamegraph.ps1 -Bench -BenchFilter "parse_yaml"

# Profile specific crate
.\scripts\profile\run_flamegraph.ps1 -Crate classic-yaml-core -Open
```

Output: `target/profiling/flamegraphs/flamegraph-{timestamp}.svg`

### For Python+Rust Code: py-spy

Capture combined Python and Rust stack traces:

```powershell
# Quick profiling (10 seconds)
.\scripts\profile\run_pyspy.ps1

# Thorough profiling (60 seconds)
.\scripts\profile\run_pyspy.ps1 -Mode thorough

# Profile CLI entry point instead of GUI
.\scripts\profile\run_pyspy.ps1 -EntryPoint CLASSIC_ScanLogs.py

# Output to speedscope format
.\scripts\profile\run_pyspy.ps1 -Format speedscope -Open
```

Output: `target/profiling/pyspy/pyspy-{timestamp}.svg`

**Note:** py-spy 0.4.1 is incompatible with Python 3.14+. Use cProfile for Python-only profiling on newer Python versions.

### For Memory Analysis: dhat

Profile heap allocations in Rust code:

```powershell
# Profile tests
.\scripts\profile\run_dhat.ps1 -Crate classic-yaml-core -Test

# Profile specific test
.\scripts\profile\run_dhat.ps1 -Crate classic-settings-core -Test -TestFilter "test_load"

# Profile benchmarks
.\scripts\profile\run_dhat.ps1 -Crate classic-yaml-core -Bench
```

Output: `target/profiling/dhat/dhat-heap-{timestamp}.json`

View results at: https://nnethercote.github.io/dh_view/dh_view.html

### For Cache Performance

Check cache hit rates to identify caching issues:

```powershell
.\scripts\profile\dump_cache_stats.ps1

# Export to JSON
.\scripts\profile\dump_cache_stats.ps1 -Format json -Output cache-stats.json
```

## Step 2: Establish Baseline

Before making changes, establish a measurable baseline using Criterion benchmarks.

### Understanding BENCH_MODE

All benchmarks support two modes controlled by the `BENCH_MODE` environment variable:

| Mode | Sample Size | Measurement Time | Use Case |
|------|-------------|------------------|----------|
| `quick` (default) | 50 | 3 seconds | Development iteration |
| `thorough` | 200 | 10 seconds | Baseline establishment |

### Running Benchmarks

```powershell
# Run all benchmarks in quick mode (default)
.\scripts\bench\run_benchmarks.ps1

# Run all benchmarks in thorough mode for baselines
.\scripts\bench\run_benchmarks.ps1 -Mode thorough

# Run specific crate benchmarks
.\scripts\bench\run_benchmarks.ps1 -Crate classic-yaml-core

# Filter to specific benchmark
.\scripts\bench\run_benchmarks.ps1 -Filter "parse_yaml"
```

### Saving Baselines

```powershell
# Save baseline with auto-generated timestamp name
.\scripts\bench\run_benchmarks.ps1 -Mode thorough -SaveBaseline

# Save baseline with custom name (recommended)
.\scripts\bench\run_benchmarks.ps1 -Mode thorough -SaveBaseline -BaselineName "pre-optimization"
```

Baseline location: `ClassicLib-rs/target/criterion/{baseline-name}/`

### GIL Benchmarks

For Python-binding crates, GIL benchmarks measure pure Rust compute time:

```bash
# Run GIL benchmarks for YAML operations
BENCH_MODE=quick cargo bench --bench gil_benchmarks -p classic-yaml-py

# Run GIL benchmarks for scanlog operations
BENCH_MODE=thorough cargo bench --bench gil_benchmarks -p classic-scanlog-py

# Run GIL benchmarks for file-io operations
BENCH_MODE=quick cargo bench --bench gil_benchmarks -p classic-file-io-py
```

## Step 3: Implement Optimization

With a baseline established and hot path identified, implement targeted optimizations.

### Optimization Guidelines

1. **Focus on the hot path** - Only optimize code that profiling identified as slow
2. **Measure, don't guess** - Verify assumptions with profiling data
3. **Consider algorithmic improvements first** - O(n) to O(1) often beats micro-optimizations
4. **Keep changes atomic** - One optimization per commit for easy verification

### Common Optimization Patterns in CLASSIC

| Bottleneck | Optimization |
|------------|--------------|
| Repeated string allocations | Use string interning or `Arc<str>` |
| Dictionary membership checks | Use `set()` instead of `list` |
| File re-reading | Add caching with mod-time validation |
| GIL contention | Release GIL for Rust operations >1ms |
| Repeated regex compilation | Pre-compile patterns at module load |

### Example: Set-Backed List Pattern

```python
# Before: O(n) membership check
plugins = ["Plugin1.esp", "Plugin2.esp", ...]
if plugin in plugins:  # O(n)
    ...

# After: O(1) membership check
plugins = ["Plugin1.esp", "Plugin2.esp", ...]
plugins_set = set(plugins)  # Create once
if plugin in plugins_set:  # O(1)
    ...
```

## Step 4: Verify Improvement

After implementing optimizations, verify improvements without introducing regressions.

### Compare Against Baseline

```powershell
# Compare current performance against saved baseline
.\scripts\bench\compare_baselines.ps1 -Baseline "pre-optimization"

# Compare with custom threshold (highlight >5% changes)
.\scripts\bench\compare_baselines.ps1 -Baseline "pre-optimization" -Threshold 5

# Export comparison to JSON
.\scripts\bench\compare_baselines.ps1 -Baseline "pre-optimization" -ExportJson results.json
```

### Interpreting Results

Output shows percentage change from baseline:

- **Green (negative %)**: Performance improved
- **Red (positive %)**: Performance regressed
- **Yellow**: Within noise threshold (typically 1-3%)

### CI Integration

Pull requests automatically run benchmarks and compare against the `main` baseline:

- **Warning**: >5% regression
- **Failure**: >10% regression (blocks merge)
- **Bypass**: Add `perf-regression-accepted` label for intentional regressions

## Quick Reference

### Profiling Commands

| Tool | Command | Output |
|------|---------|--------|
| Flamegraph | `.\scripts\profile\run_flamegraph.ps1` | SVG flamegraph |
| py-spy | `.\scripts\profile\run_pyspy.ps1` | SVG/speedscope |
| dhat | `.\scripts\profile\run_dhat.ps1 -Crate {name} -Test` | JSON heap data |
| Cache stats | `.\scripts\profile\dump_cache_stats.ps1` | Console/JSON |

### Benchmark Commands

| Action | Command |
|--------|---------|
| Quick run | `.\scripts\bench\run_benchmarks.ps1` |
| Thorough run | `.\scripts\bench\run_benchmarks.ps1 -Mode thorough` |
| Save baseline | `.\scripts\bench\run_benchmarks.ps1 -SaveBaseline -BaselineName "name"` |
| Compare | `.\scripts\bench\compare_baselines.ps1 -Baseline "name"` |
| List benchmarks | `.\scripts\bench\run_benchmarks.ps1 -List` |

### Environment Variables

| Variable | Values | Effect |
|----------|--------|--------|
| `BENCH_MODE` | `quick`, `thorough` | Controls sample size and duration |

## Related Documentation

- [Cache Patterns](./cache_patterns.md) - Caching strategies in CLASSIC
- [GIL Audit Guide](./gil_audit.md) - GIL release decisions for PyO3
- [PyO3 Integration Patterns](./pyo3_integration_patterns.md) - Rust-Python binding patterns
- [CI/CD Guide](./ci_cd_guide.md) - Automated testing and benchmarking
- [Rust Acceleration Guide](./rust_acceleration_guide.md) - Rust performance patterns
