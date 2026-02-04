# Phase 13: Benchmark Infrastructure - Research

**Researched:** 2026-02-04
**Domain:** Criterion.rs benchmarking, Rust workspace benchmarks, statistical analysis
**Confidence:** HIGH

## Summary

Criterion.rs is the de facto standard benchmarking library for Rust with 132M+ downloads. The project already has Criterion 0.8.1 configured in `classic-shared-core` and 0.5 in the `-py` crates, with existing benchmark files for GIL release auditing from Phase 12. This phase expands that foundation to comprehensive benchmark infrastructure with statistical output and baseline management.

**Key finding:** Criterion does NOT natively report p95/p99 percentiles - only mean, median, median absolute deviation, and slope. Percentiles require post-processing of `raw.csv` files or custom tooling. The `cargo-criterion` tool provides JSON export via `--message-format=json` for machine-readable output.

**Primary recommendation:** Use Criterion 0.8.x with `cargo-criterion` for JSON export, implement a custom post-processing script to calculate p95/p99 from raw.csv data, and use `critcmp` for baseline comparisons. Configure two benchmark profiles (quick/thorough) via environment variable.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| criterion | 0.8.1 | Micro-benchmarking framework | Industry standard, statistics-driven, HTML reports |
| cargo-criterion | 1.1.0 | Benchmark runner with JSON export | Machine-readable output, historical reports |
| critcmp | 0.1.8 | Baseline comparison tool | BurntSushi's comparison utility, JSON export |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| serde_json | 1.0 | JSON parsing for baseline processing | Already in workspace |
| chrono | 0.4 | Timestamp generation for baselines | Already available |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| criterion | divan | Newer, simpler API but less ecosystem support |
| cargo-criterion | raw cargo bench | No JSON export, less features |
| critcmp | manual comparison | More work, less standard output |

**Installation:**
```bash
# Already in workspace, just update versions
cargo install cargo-criterion
cargo install critcmp
```

## Architecture Patterns

### Recommended Benchmark Structure
```
rust/
├── benches/                     # Workspace-level benchmark utilities (optional)
│   └── common/                  # Shared benchmark fixtures and utilities
│       ├── mod.rs
│       ├── fixtures.rs          # Load realistic test data
│       └── synthetic.rs         # Generate synthetic scaling data
├── business-logic/
│   ├── classic-yaml-core/
│   │   └── benches/
│   │       ├── parsing_benches.rs      # YAML parsing operations
│   │       ├── serialization_benches.rs # YAML serialization
│   │       └── cache_benches.rs        # Cache hit/miss scenarios
│   ├── classic-scanlog-core/
│   │   └── benches/
│   │       ├── parser_benches.rs       # Log parsing
│   │       ├── formid_benches.rs       # FormID extraction
│   │       ├── pattern_benches.rs      # Pattern matching
│   │       └── orchestrator_benches.rs # Full pipeline
│   └── classic-file-io-core/
│       └── benches/
│           ├── read_benches.rs         # File reading
│           ├── write_benches.rs        # File writing
│           └── encoding_benches.rs     # Encoding detection
├── python-bindings/
│   └── classic-*-py/
│       └── benches/
│           └── ffi_overhead_benches.rs # FFI round-trip measurement
├── criterion.toml               # Workspace-wide Criterion config
└── scripts/
    └── bench/
        ├── run_benchmarks.ps1   # PowerShell benchmark runner
        ├── extract_percentiles.py # Post-process raw.csv for p95/p99
        └── cleanup_baselines.py # Keep only 10 most recent
```

### Pattern 1: Benchmark Group Organization
**What:** Group related benchmarks for comparative analysis
**When to use:** Always - enables automatic comparison charts
**Example:**
```rust
// Source: https://bheisler.github.io/criterion.rs/book/user_guide/benchmarking_with_inputs.html
fn bench_yaml_parsing(c: &mut Criterion) {
    let mut group = c.benchmark_group("yaml_parsing");

    // Configure based on BENCH_MODE environment variable
    let (sample_size, measurement_time) = match std::env::var("BENCH_MODE").as_deref() {
        Ok("thorough") => (200, Duration::from_secs(10)),
        _ => (50, Duration::from_secs(3)),  // quick mode default
    };

    group.sample_size(sample_size);
    group.measurement_time(measurement_time);

    for size in [100, 500, 1000, 5000] {
        let yaml_content = generate_yaml_content(size);
        group.throughput(Throughput::Bytes(yaml_content.len() as u64));

        group.bench_with_input(
            BenchmarkId::new("parse_lines", size),
            &yaml_content,
            |b, content| {
                b.iter(|| {
                    let result = parse_yaml(black_box(content));
                    black_box(result)
                })
            },
        );
    }

    group.finish();
}
```

### Pattern 2: FFI Overhead Measurement
**What:** Measure Python->Rust->Python round-trip separately from pure Rust
**When to use:** For `-py` crates to isolate FFI cost from compute cost
**Example:**
```rust
// Source: Phase 12 GIL benchmarks pattern
fn bench_ffi_overhead(c: &mut Criterion) {
    let mut group = c.benchmark_group("ffi_overhead");

    // Pure Rust baseline (no Python involvement)
    group.bench_function("pure_rust_compute", |b| {
        let data = prepare_test_data();
        b.iter(|| {
            black_box(rust_only_function(&data))
        })
    });

    // Note: Actual FFI measurement requires Python test harness
    // This establishes the Rust-side baseline for comparison

    group.finish();
}
```

### Pattern 3: Realistic Fixtures
**What:** Use actual crash logs and YAML configs from test data
**When to use:** For representative performance measurement
**Example:**
```rust
// Load realistic test data
fn load_benchmark_fixtures() -> BenchmarkFixtures {
    BenchmarkFixtures {
        small_crash_log: include_str!("../../../tests/test_data/sample_crash_logs/sample_crash_1.log"),
        complex_crash_log: include_str!("../../../tests/test_data/sample_crash_logs/complex_crash.log"),
        yaml_database: include_str!("../../../CLASSIC Data/databases/CLASSIC Fallout4.yaml"),
    }
}
```

### Anti-Patterns to Avoid
- **Thread::sleep in benchmarks:** Never use sleep for simulating work - it measures sleep, not your code
- **Unbounded allocation in loop:** Allocate test data outside `b.iter()` closure
- **Missing black_box:** Always wrap inputs AND outputs to prevent optimization
- **Inconsistent sample sizes:** Use environment variable for mode switching, not hardcoded values

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Baseline comparison | String parsing of cargo bench output | critcmp | Handles edge cases, standard format |
| JSON export | Parse target/criterion/*.json | cargo-criterion --message-format=json | Official tool, stable format |
| Historical tracking | Custom database | Criterion's built-in baseline + critcmp export | Already stores in target/criterion |
| Statistical analysis | Manual mean/stddev calculation | Criterion's built-in analysis | Proper bootstrap confidence intervals |
| Percentile calculation | Hand-roll sorting | Post-process raw.csv with formula | Criterion provides stable raw.csv format |

**Key insight:** Criterion provides extensive built-in statistics. Only percentiles (p95/p99) require custom post-processing since Criterion focuses on mean/median with confidence intervals rather than tail latency percentiles.

## Common Pitfalls

### Pitfall 1: Assuming Criterion Reports Percentiles
**What goes wrong:** Expecting p95/p99 in JSON output, finding only mean/median/MAD
**Why it happens:** Criterion was designed for "typical" performance (mean/median), not tail latency
**How to avoid:** Post-process raw.csv to calculate percentiles
**Warning signs:** Looking for p95/p99 in criterion JSON output

### Pitfall 2: Running Benchmarks in Debug Mode
**What goes wrong:** 10-100x slower measurements, misleading results
**Why it happens:** Forgetting `--release` flag
**How to avoid:** Always use `cargo bench` (implies release) or explicit `--release`
**Warning signs:** Unusually slow benchmark times, no optimization gains

### Pitfall 3: Baseline Name Conflicts
**What goes wrong:** Overwriting baselines unintentionally
**Why it happens:** Using `--save-baseline` without unique names
**How to avoid:** Use timestamp-based naming: `baseline-2026-02-04-143022`
**Warning signs:** Unexpected "improved" results when code didn't change

### Pitfall 4: Measuring JIT/Warmup Effects
**What goes wrong:** First iterations are slow, skewing results
**Why it happens:** Criterion uses too few warmup iterations
**How to avoid:** Use Criterion's default auto-calibrating warmup (don't override)
**Warning signs:** High variance in early samples

### Pitfall 5: Forgetting to Clear State Between Benchmarks
**What goes wrong:** Cache effects from previous benchmarks affect measurements
**Why it happens:** Global state (DashMap caches) persist between benchmark functions
**How to avoid:** Clear global caches in benchmark setup, use `iter_batched` for setup
**Warning signs:** Benchmarks produce different results based on run order

## Code Examples

### Workspace-Level criterion.toml Configuration
```toml
# Source: https://bheisler.github.io/criterion.rs/book/cargo_criterion/configuring_cargo_criterion.html
# rust/criterion.toml

# Store in default location (gitignored via target/)
criterion_home = "./target/criterion"

# Use verbose output for detailed statistics
output_format = "verbose"

# Prefer gnuplot for better charts
plotting_backend = "gnuplot"
```

### Quick vs Thorough Mode Configuration
```rust
// Source: Criterion documentation
use criterion::{Criterion, SamplingMode};
use std::time::Duration;

pub fn configure_criterion() -> Criterion {
    let mut criterion = Criterion::default();

    match std::env::var("BENCH_MODE").as_deref() {
        Ok("thorough") => {
            // Full samples for baseline establishment
            criterion
                .sample_size(200)
                .measurement_time(Duration::from_secs(10))
                .noise_threshold(0.01)  // 1% noise threshold
                .confidence_level(0.99)
        }
        _ => {
            // Quick mode for dev iteration (default)
            criterion
                .sample_size(50)
                .measurement_time(Duration::from_secs(3))
                .noise_threshold(0.03)  // 3% noise threshold - more lenient
                .confidence_level(0.95)
        }
    }
}
```

### Benchmark with Throughput Measurement
```rust
// Source: https://bheisler.github.io/criterion.rs/book/user_guide/benchmarking_with_inputs.html
use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};

fn bench_file_parsing(c: &mut Criterion) {
    let mut group = c.benchmark_group("file_parsing");

    // Test different file sizes
    for (name, content) in [
        ("small_1kb", generate_content(1024)),
        ("medium_10kb", generate_content(10240)),
        ("large_100kb", generate_content(102400)),
    ] {
        group.throughput(Throughput::Bytes(content.len() as u64));
        group.bench_with_input(
            BenchmarkId::new("parse", name),
            &content,
            |b, content| {
                b.iter(|| parse_content(black_box(content)))
            },
        );
    }

    group.finish();
}
```

### Baseline Management Script Pattern
```powershell
# scripts/bench/run_benchmarks.ps1
param(
    [ValidateSet("quick", "thorough")]
    [string]$Mode = "quick",

    [switch]$SaveBaseline,
    [string]$BaselineName = "",
    [switch]$Compare
)

$env:BENCH_MODE = $Mode

if ($SaveBaseline) {
    if (-not $BaselineName) {
        $BaselineName = "baseline-$(Get-Date -Format 'yyyy-MM-dd-HHmmss')"
    }
    cargo bench -- --save-baseline $BaselineName
}
elseif ($Compare -and $BaselineName) {
    cargo bench -- --baseline $BaselineName
}
else {
    cargo bench
}

# Export to JSON for analysis
if ($SaveBaseline) {
    critcmp --export $BaselineName | Out-File "target/criterion/exports/$BaselineName.json"
}
```

### Percentile Extraction Script
```python
#!/usr/bin/env python3
"""Extract p95/p99 percentiles from Criterion raw.csv files."""
# scripts/bench/extract_percentiles.py

import csv
import json
from pathlib import Path
from typing import Dict, List
import math

def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """Calculate p50, p95, p99 from sorted values."""
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def percentile(p: float) -> float:
        idx = math.ceil(p * n) - 1
        return sorted_vals[max(0, min(idx, n - 1))]

    return {
        "p50": percentile(0.50),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "min": sorted_vals[0],
        "max": sorted_vals[-1],
    }

def process_raw_csv(csv_path: Path) -> Dict:
    """Process a Criterion raw.csv file."""
    per_iteration_times = []

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Calculate per-iteration time: sample_measured_value / iteration_count
            measured = float(row["sample_measured_value"])
            iterations = int(row["iteration_count"])
            per_iteration_times.append(measured / iterations)

    return calculate_percentiles(per_iteration_times)

def main():
    criterion_dir = Path("target/criterion")
    results = {}

    for raw_csv in criterion_dir.rglob("new/raw.csv"):
        benchmark_name = raw_csv.parent.parent.name
        results[benchmark_name] = process_raw_csv(raw_csv)

    output_path = criterion_dir / "percentiles.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Percentiles written to {output_path}")

if __name__ == "__main__":
    main()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| libtest bench | Criterion | 2017+ | Stable, statistical analysis, HTML reports |
| Manual baseline | critcmp + cargo-criterion | 2020+ | JSON export, automated comparison |
| Single sample | Bootstrap resampling | Criterion default | Confidence intervals, regression detection |
| Criterion 0.5 | Criterion 0.8 | 2024 | Improved async support, new features |

**Deprecated/outdated:**
- `#[bench]` attribute (requires nightly Rust)
- criterion 0.3.x (0.5+ has better async support)
- Manual CSV parsing of estimates.json (use raw.csv for stability)

## Open Questions

Things that couldn't be fully resolved:

1. **Percentile Calculation Precision**
   - What we know: raw.csv provides sample_measured_value and iteration_count
   - What's unclear: Whether simple percentile calculation is statistically valid given Criterion's bootstrap resampling approach
   - Recommendation: Use simple percentile calculation; it's standard industry practice for tail latency

2. **Async Benchmark Overhead**
   - What we know: Criterion supports async via `to_async()`
   - What's unclear: How much overhead the async executor adds to measurements
   - Recommendation: Measure sync functions directly where possible; note async overhead when used

3. **FFI Benchmark in Pure Rust**
   - What we know: Pure Rust benchmarks establish compute baseline
   - What's unclear: How to measure actual Python-Rust FFI round-trip in Criterion (requires Python runtime)
   - Recommendation: Use Python pytest-benchmark for FFI overhead; compare against Rust baseline

## Sources

### Primary (HIGH confidence)
- [Criterion.rs Documentation](https://bheisler.github.io/criterion.rs/book/) - Official user guide
- [criterion docs.rs](https://docs.rs/criterion/latest/criterion/) - API documentation
- [cargo-criterion GitHub](https://github.com/bheisler/cargo-criterion) - JSON export, configuration
- [critcmp GitHub](https://github.com/BurntSushi/critcmp) - Baseline comparison tool

### Secondary (MEDIUM confidence)
- [Criterion CSV Output](https://bheisler.github.io/criterion.rs/book/user_guide/csv_output.html) - raw.csv format
- [Criterion External Tools](https://bheisler.github.io/criterion.rs/book/cargo_criterion/external_tools.html) - JSON message format

### Tertiary (LOW confidence)
- Community blog posts on percentile calculation methodology

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Criterion is industry standard, well-documented
- Architecture: HIGH - Based on existing project structure and Criterion best practices
- Pitfalls: HIGH - Documented in Criterion FAQ and community experience
- Percentile calculation: MEDIUM - Standard approach but not Criterion-native

**Research date:** 2026-02-04
**Valid until:** 60 days (Criterion is stable, changes infrequently)
