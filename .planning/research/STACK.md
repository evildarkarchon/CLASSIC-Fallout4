# Technology Stack for Performance Benchmarking and Profiling

**Project:** CLASSIC Performance Benchmarking Milestone
**Researched:** 2026-02-04
**Confidence:** HIGH - Verified against official documentation and existing project infrastructure

## Executive Summary

CLASSIC already has Criterion 0.8.1 in the workspace for microbenchmarking. This milestone adds **targeted profiling tools** and **CI regression detection**, while avoiding tool bloat. The focus is instrumenting the hybrid Python-Rust boundary and establishing performance baselines.

**Key additions:**
- Profiling: `cargo-flamegraph` (sampling), `tracing-flame` (async spans)
- Memory: `dhat` (heap profiling with Rust global allocator)
- CI: `github-action-benchmark` or Bencher for regression detection
- PyO3: `py-spy` for cross-boundary profiling

**Total new dev-dependencies: 3-4** (carefully selected, not bloat)

## Current State

### Already In Place (DO NOT re-add)

| Tool | Version | Location | Purpose |
|------|---------|----------|---------|
| `criterion` | 0.8.1 | `classic-shared-core` dev-deps | Statistical microbenchmarking |
| `tracing` | 0.1.44 | workspace | Instrumentation framework |
| `tracing-subscriber` | 0.3.22 | workspace | Subscriber layers |
| Existing benchmarks | - | `rust/foundation/classic-shared-core/benches/` | Performance, string, path benchmarks |

### Existing Benchmark Coverage

```
benches/
  performance_benchmarks.rs  # Timer, metrics, concurrent recording
  string_benchmarks.rs       # String interning, smartstring
  path_benchmarks.rs         # Path validation
```

**Gap analysis:** Business-logic crates (`-core`) lack benchmarks. YAML, scanlog, and database operations are unbenchmarked.

## Recommended Stack Additions

### 1. Profiling Tools

#### cargo-flamegraph (RECOMMENDED)

**Purpose:** CPU profiling with visual flamegraph output
**Version:** 0.6.11 (released 2026-01-19)

```bash
# Install globally (not a project dependency)
cargo install flamegraph
```

**Configuration required in workspace `Cargo.toml`:**
```toml
[profile.release-with-debug]
inherits = "release"
debug = true  # Already present in project
```

**Usage:**
```bash
# Profile specific benchmark
cargo flamegraph --bench performance_benchmarks -- --bench record_timing

# Profile with frame pointers for better stacks
RUSTFLAGS="-C force-frame-pointers=yes" cargo flamegraph --release --bin classic-tui
```

**Why flamegraph:**
- Wraps `perf` (Linux) and `dtrace` (macOS) automatically
- Produces interactive SVG flamegraphs
- Works with existing release-with-debug profile
- No code changes required

**Platform note:** Windows support is limited. Use WSL2 for profiling on Windows.

**Sources:**
- [flamegraph-rs GitHub](https://github.com/flamegraph-rs/flamegraph)
- [Rust Performance Book - Profiling](https://nnethercote.github.io/perf-book/profiling.html)

#### tracing-flame (RECOMMENDED for async profiling)

**Purpose:** Generate flamegraphs from `tracing` spans (async-aware)
**Version:** 0.2.0

```toml
# Add to workspace Cargo.toml
[workspace.dependencies]
tracing-flame = "0.2"
inferno = "0.12"  # For converting folded stacks to SVG
```

**Usage pattern:**
```rust
use tracing_flame::FlameLayer;
use tracing_subscriber::{prelude::*, registry::Registry};

fn setup_profiling() -> impl Drop {
    let (flame_layer, guard) = FlameLayer::with_file("./tracing.folded").unwrap();
    tracing_subscriber::registry()
        .with(flame_layer)
        .init();
    guard  // Drop guard writes output
}

// Convert to flamegraph
// cat tracing.folded | inferno-flamegraph > profile.svg
```

**Why tracing-flame:**
- Integrates with existing `tracing` infrastructure (already in workspace)
- Captures async task boundaries (critical for Tokio-based code)
- Produces folded stacks compatible with standard flamegraph tools
- Zero runtime cost when disabled

**Sources:**
- [tracing-flame on lib.rs](https://lib.rs/crates/tracing-flame)

#### samply (Alternative to flamegraph - OPTIONAL)

**Purpose:** Interactive web-based profiling with Firefox Profiler UI
**Version:** 0.13

```bash
# Install globally
cargo install samply
```

**When to use:** When you need interactive exploration rather than static SVG.

**Sources:**
- [Profiling Rust programs the easy way](https://ntietz.com/blog/profiling-rust-programs-the-easy-way/)

### 2. Memory Profiling

#### dhat (RECOMMENDED)

**Purpose:** Heap allocation profiling with test assertions
**Version:** 0.3.3

```toml
# Add to workspace Cargo.toml
[workspace.dependencies]
dhat = "0.3"
```

**Usage in benchmarks:**
```rust
#[cfg(feature = "dhat-heap")]
#[global_allocator]
static ALLOC: dhat::Alloc = dhat::Alloc;

fn main() {
    #[cfg(feature = "dhat-heap")]
    let _profiler = dhat::Profiler::new_heap();

    // ... benchmark code
}
```

**Test allocation counts:**
```rust
#[test]
fn test_yaml_parse_allocations() {
    let _profiler = dhat::Profiler::builder().testing().build();

    let stats_before = dhat::HeapStats::get();
    parse_yaml_document(&content);
    let stats_after = dhat::HeapStats::get();

    // Assert allocation count is reasonable
    assert!(stats_after.total_blocks - stats_before.total_blocks < 100);
}
```

**Why dhat:**
- Pure Rust implementation (no external dependencies)
- Works on all platforms including Windows
- Supports assertion-based testing (CI-friendly)
- Lower overhead than Valgrind-based tools
- Views with DHAT viewer at https://nicopollas.github.io/nicopollas/dhat-viewer/

**Sources:**
- [dhat crate documentation](https://docs.rs/dhat/latest/dhat/)
- [Rust Performance Book - Heap Allocations](https://nnethercote.github.io/perf-book/heap-allocations.html)

### 3. PyO3 Cross-Boundary Profiling

#### py-spy (RECOMMENDED)

**Purpose:** Profile Python code including Rust extensions
**Version:** 0.4 (latest)

```bash
# Install via pip (not Rust)
pip install py-spy
```

**Usage:**
```bash
# Profile CLASSIC GUI with native extension support
py-spy record --native -o profile.svg -- python CLASSIC_Interface.py

# Top-like view
py-spy top --native -- python CLASSIC_ScanLogs.py
```

**Why py-spy:**
- Written in Rust, low overhead (~2%)
- `--native` flag captures Rust stack frames alongside Python
- No code changes required
- Can attach to running processes

**Limitation:** Requires debug symbols in Rust extensions. Build with:
```bash
# Windows: use release-with-debug profile
maturin build --profile release-with-debug
```

**Sources:**
- [py-spy GitHub](https://github.com/benfred/py-spy)
- [PyO3 Performance Analysis](https://github.com/PyO3/pyo3/issues/1607)

#### Custom FFI Overhead Measurement (RECOMMENDED)

Create dedicated benchmarks for Python/Rust boundary crossing:

```rust
// In classic-yaml-py/benches/ffi_overhead.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use pyo3::prelude::*;

fn bench_ffi_roundtrip(c: &mut Criterion) {
    pyo3::prepare_freethreaded_python();

    Python::with_gil(|py| {
        let module = PyModule::import(py, "classic_yaml").unwrap();

        c.bench_function("yaml_parse_small", |b| {
            b.iter(|| {
                let result = module
                    .call_method1("parse_yaml", ("key: value",))
                    .unwrap();
                black_box(result);
            });
        });
    });
}

criterion_group!(ffi_benches, bench_ffi_roundtrip);
criterion_main!(ffi_benches);
```

### 4. CI Regression Detection

#### github-action-benchmark (RECOMMENDED)

**Purpose:** Track benchmark results over time, alert on regressions

```yaml
# .github/workflows/benchmark.yml
name: Benchmark
on:
  push:
    branches: [main]
  pull_request:

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run benchmarks
        run: cargo bench --bench performance_benchmarks -- --output-format bencher | tee output.txt

      - name: Store benchmark result
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'cargo'
          output-file-path: output.txt
          github-token: ${{ secrets.GITHUB_TOKEN }}
          auto-push: true
          alert-threshold: '150%'
          fail-on-alert: false
          comment-on-alert: true
```

**Why github-action-benchmark:**
- Free for public repos
- No external service dependency
- Stores results in GitHub Pages
- Configurable thresholds (default 200%, recommend 150% for CLASSIC)

**Alternative: Bencher**

For more sophisticated regression analysis with statistical significance:

```yaml
- uses: bencherdev/bencher@main
- name: Track Benchmarks
  run: |
    bencher run \
      --project classic \
      --token ${{ secrets.BENCHER_API_TOKEN }} \
      --branch main \
      --testbed ubuntu-latest \
      --adapter rust_criterion \
      "cargo bench"
```

**Sources:**
- [github-action-benchmark](https://github.com/benchmark-action/github-action-benchmark)
- [Bencher documentation](https://bencher.dev/docs/how-to/github-actions/)

### 5. Async Runtime Profiling

#### tokio-console (RECOMMENDED for debugging)

**Purpose:** Real-time async task visualization
**Already in ecosystem:** Uses `console-subscriber` with existing `tracing`

```toml
# Add to workspace (dev-only feature flag recommended)
[workspace.dependencies]
console-subscriber = { version = "0.4", optional = true }
```

**Usage:**
```rust
#[cfg(feature = "tokio-console")]
fn setup_console() {
    console_subscriber::init();
}
```

```bash
# Run with console
RUSTFLAGS="--cfg tokio_unstable" cargo run --features tokio-console

# In another terminal
tokio-console
```

**Why tokio-console:**
- Visual task inspector for async code
- Shows task spawn points, poll counts, waker events
- Identifies stuck or slow tasks
- Useful for debugging, not production profiling

**Sources:**
- [tokio-console GitHub](https://github.com/tokio-rs/console)

## Recommended Stack Configuration

### Workspace Cargo.toml Additions

```toml
[workspace.dependencies]
# Profiling (dev-only)
tracing-flame = "0.2"
inferno = "0.12"
dhat = "0.3"
console-subscriber = "0.4"

# Criterion already present at 0.8.1
```

### Per-Crate Configuration Pattern

For crates that need benchmarks:

```toml
# business-logic/classic-yaml-core/Cargo.toml
[dev-dependencies]
criterion = { workspace = true }
dhat = { workspace = true }

[features]
dhat-heap = []

[[bench]]
name = "yaml_benchmarks"
harness = false
```

## What NOT to Add

| Tool | Reason to Avoid |
|------|-----------------|
| `iai-callgrind` | Requires Valgrind (Linux only), CLASSIC targets Windows primarily |
| `pprof-rs` | jemalloc-based, conflicts with system allocator; dhat is simpler |
| `heaptrack` | Linux only, high memory overhead |
| `tikv-jemallocator` | Requires replacing global allocator, invasive change |
| `criterion-perf-events` | Linux only, requires perf setup |
| `divan` | Project already standardized on Criterion 0.8.1; switching adds friction |
| `codspeed` | External service dependency; github-action-benchmark is self-hosted |

### Why Stay with Criterion (Not Divan)

The project already uses Criterion 0.8.1 with 3 benchmark files. While Divan offers ergonomic improvements:
- Existing benchmarks would need rewriting
- Team familiarity with Criterion API
- Criterion's HTML reports are mature
- Statistical rigor is equivalent

**Recommendation:** Expand Criterion coverage rather than switch frameworks.

## Integration with Existing Infrastructure

### Feature Flags Pattern

```toml
# In workspace Cargo.toml
[workspace.features]
# Development-only profiling
profiling = ["tracing-flame", "dhat", "console-subscriber"]
```

### Benchmark Directory Structure

```
rust/
  foundation/classic-shared-core/benches/  # Already exists
  business-logic/
    classic-yaml-core/benches/
      yaml_benchmarks.rs          # NEW: YAML parsing benchmarks
      yaml_memory.rs              # NEW: Allocation profiling
    classic-scanlog-core/benches/
      scanlog_benchmarks.rs       # NEW: Crash log parsing
    classic-database-core/benches/
      database_benchmarks.rs      # NEW: SQLite operations
  python-bindings/
    classic-yaml-py/benches/
      ffi_benchmarks.rs           # NEW: PyO3 boundary overhead
```

### Scripts for Profiling Workflows

```powershell
# scripts/profile-release.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$Target,

    [string]$OutputDir = "profiles"
)

$env:RUSTFLAGS = "-C force-frame-pointers=yes"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Write-Host "Building with debug symbols..."
cargo build --profile release-with-debug --bin $Target

Write-Host "Profiling with flamegraph..."
cargo flamegraph --profile release-with-debug --bin $Target -o "$OutputDir/$Target.svg"

Write-Host "Profile saved to $OutputDir/$Target.svg"
```

## Version Verification

| Crate | Recommended Version | Verified Date | Source |
|-------|---------------------|---------------|--------|
| criterion | 0.8.1 | 2026-02-04 | [docs.rs](https://docs.rs/crate/criterion/0.8.1) - Released 2025-12-07 |
| flamegraph | 0.6.11 | 2026-02-04 | [GitHub releases](https://github.com/flamegraph-rs/flamegraph/releases) - Released 2026-01-19 |
| tracing-flame | 0.2.0 | 2026-02-04 | [lib.rs](https://lib.rs/crates/tracing-flame) |
| dhat | 0.3.3 | 2026-02-04 | [docs.rs](https://docs.rs/dhat/latest/dhat/) |
| console-subscriber | 0.4.x | 2026-02-04 | [crates.io](https://crates.io/crates/console-subscriber) |
| py-spy | 0.4.x | 2026-02-04 | [GitHub](https://github.com/benfred/py-spy) |

## Summary

**New workspace dependencies (dev-only):**
1. `tracing-flame = "0.2"` - Async-aware flame profiling
2. `inferno = "0.12"` - Folded stack to SVG conversion
3. `dhat = "0.3"` - Heap allocation profiling
4. `console-subscriber = "0.4"` (optional feature) - Tokio debugging

**External tools (not deps):**
1. `cargo-flamegraph` - CPU profiling
2. `py-spy` - Python/Rust cross-boundary profiling

**CI Integration:**
1. `github-action-benchmark` - Free, self-hosted regression tracking

**Total impact:** 3-4 small crates added to dev-dependencies, no runtime changes, no production code modifications required.

## Sources

- [Criterion.rs Documentation](https://bheisler.github.io/criterion.rs/book/getting_started.html)
- [The Rust Performance Book](https://nnethercote.github.io/perf-book/profiling.html)
- [flamegraph-rs GitHub](https://github.com/flamegraph-rs/flamegraph)
- [tracing-flame on lib.rs](https://lib.rs/crates/tracing-flame)
- [dhat crate documentation](https://docs.rs/dhat/latest/dhat/)
- [py-spy GitHub](https://github.com/benfred/py-spy)
- [PyO3 Performance Analysis Issue](https://github.com/PyO3/pyo3/issues/1607)
- [github-action-benchmark](https://github.com/benchmark-action/github-action-benchmark)
- [Bencher CI documentation](https://bencher.dev/docs/how-to/github-actions/)
- [tokio-console GitHub](https://github.com/tokio-rs/console)
- [Profiling Rust programs the easy way](https://ntietz.com/blog/profiling-rust-programs-the-easy-way/)
