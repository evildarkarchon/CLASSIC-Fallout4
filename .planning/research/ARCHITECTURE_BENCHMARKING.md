# Architecture Patterns: Performance Benchmarking Integration

**Domain:** Performance benchmarking for hybrid Rust-Python application
**Researched:** 2026-02-04
**Confidence:** HIGH (based on existing codebase analysis + Criterion documentation)

## Executive Summary

CLASSIC already has benchmark infrastructure in `classic-shared-core` using Criterion. The architecture question is how to **extend** this to cover the full stack: pure Rust business logic, PyO3 bindings overhead, and Python-to-Rust call patterns. The recommended approach follows Rust conventions with `benches/` directories in individual crates plus a workspace-level benchmark crate for cross-cutting concerns.

## Existing Benchmark Infrastructure

CLASSIC already has Criterion benchmarks in place:

```
rust/foundation/classic-shared-core/benches/
  path_benchmarks.rs       # PathHandler caching and operations
  performance_benchmarks.rs # Metrics system (Timer, record_timing)
  string_benchmarks.rs     # String interning, batch operations
```

**Cargo.toml configuration pattern** (from `classic-shared-core`):
```toml
[dev-dependencies]
criterion = { version = "0.8.1", features = ["html_reports"] }

[[bench]]
name = "string_benchmarks"
harness = false
```

**Benchmark style** - uses standard Criterion patterns:
- `criterion_group!` and `criterion_main!` macros
- `BenchmarkGroup` for related tests
- `black_box()` to prevent optimization
- Parameter sweeps with `BenchmarkId::new()`

## Recommended Architecture

### Component 1: Crate-Level Benchmarks (Pure Rust)

**Location:** `rust/business-logic/{crate}/benches/`

Each `-core` crate should have its own `benches/` directory benchmarking pure Rust performance. This follows the existing pattern in `classic-shared-core`.

**Priority crates for benchmarking:**

| Crate | Why | Key Operations |
|-------|-----|----------------|
| `classic-yaml-core` | YAML is a hot path (15-30x vs Python) | `load()`, `load_all()`, cache hits/misses |
| `classic-scanlog-core` | Crash log parsing is primary workload | `parse()`, segment extraction, FormID analysis |
| `classic-file-io-core` | File I/O underlies everything | Encoding detection, mmap reads, DDS parsing |
| `classic-database-core` | Database lookups in analysis | FormID resolution, batch queries |
| `classic-settings-core` | Settings loaded on every operation | Cache performance, DashMap access |

**Directory structure per crate:**
```
rust/business-logic/classic-yaml-core/
  Cargo.toml          # Add [[bench]] entries
  src/
  benches/
    load_benchmarks.rs      # YAML loading operations
    cache_benchmarks.rs     # Cache hit/miss performance
```

### Component 2: Workspace Benchmark Crate (Cross-Cutting)

**Location:** `rust/benchmarks/classic-bench/`

Create a dedicated benchmark crate for cross-cutting concerns that span multiple crates. This is a pure `rlib` crate (no PyO3) that depends on all `-core` crates and provides:

1. **End-to-end pipelines** - Benchmark full scanning workflow
2. **Comparative benchmarks** - A vs B implementation choices
3. **Baseline establishment** - Historical comparison data

**Cargo.toml:**
```toml
[package]
name = "classic-bench"
version = "8.3.0"
edition = "2024"

[lib]
crate-type = ["rlib"]

[dependencies]
# All -core crates for integration benchmarks
classic-shared-core = { path = "../../foundation/classic-shared-core" }
classic-yaml-core = { path = "../../business-logic/classic-yaml-core" }
classic-scanlog-core = { path = "../../business-logic/classic-scanlog-core" }
classic-file-io-core = { path = "../../business-logic/classic-file-io-core" }
classic-database-core = { path = "../../business-logic/classic-database-core" }
classic-settings-core = { path = "../../business-logic/classic-settings-core" }

[dev-dependencies]
criterion = { version = "0.8.1", features = ["html_reports"] }

[[bench]]
name = "pipeline_benchmarks"
harness = false

[[bench]]
name = "baseline_benchmarks"
harness = false
```

### Component 3: PyO3 Overhead Benchmarks (Python Integration)

**Location:** `tests/benchmarks/` (Python pytest-benchmark)

PyO3 FFI overhead cannot be measured from Rust alone. Use Python-side benchmarking with `pytest-benchmark` to measure:

1. **Round-trip overhead** - Time for Python -> Rust -> Python
2. **Type conversion costs** - String, list, dict conversion overhead
3. **Batch vs single-call** - N calls vs 1 batch call
4. **GIL impact** - Parallel calls from Python

**Structure:**
```
tests/benchmarks/
  conftest.py            # pytest-benchmark fixtures
  test_yaml_bench.py     # YAML operations from Python
  test_scanlog_bench.py  # Scanning from Python
  test_ffi_overhead.py   # Pure FFI overhead (minimal work)
```

**pytest-benchmark example pattern:**
```python
def test_yaml_load_small(benchmark, tmp_path):
    """Benchmark YAML loading via PyO3."""
    file_path = tmp_path / "test.yaml"
    file_path.write_text("key: value\n" * 100)

    def load():
        import classic_yaml
        ops = classic_yaml.RustYamlOperations()
        return ops.load(str(file_path))

    result = benchmark(load)
    assert "key" in result
```

## Integration Points

### 1. How Rust Benchmarks Integrate

```
rust/
  Cargo.toml                    # Workspace root - add classic-bench to members
  benchmarks/
    classic-bench/              # NEW: Workspace benchmark crate
      Cargo.toml
      src/lib.rs               # Shared benchmark utilities
      benches/
        pipeline_benchmarks.rs  # Full pipeline benchmarks
        baseline_benchmarks.rs  # Baseline establishment
  foundation/
    classic-shared-core/
      benches/                  # EXISTING: Foundation benchmarks
  business-logic/
    classic-yaml-core/
      benches/                  # NEW: YAML-specific benchmarks
    classic-scanlog-core/
      benches/                  # NEW: Scanlog-specific benchmarks
```

### 2. Build Order and Dependencies

```
[Independent - can run in parallel]
  classic-yaml-core/benches
  classic-file-io-core/benches
  classic-database-core/benches
  classic-settings-core/benches

[Depends on above crates]
  classic-scanlog-core/benches    # Depends on yaml, file-io, database

[Depends on all -core crates]
  classic-bench                   # Integration/pipeline benchmarks

[Depends on Rust being built]
  tests/benchmarks/               # Python FFI overhead tests
```

### 3. Running Benchmarks

**Rust benchmarks (from workspace root):**
```bash
# Run all benchmarks
cargo bench --workspace

# Run specific crate benchmarks
cargo bench -p classic-yaml-core

# Run workspace benchmark crate
cargo bench -p classic-bench

# Run with baseline comparison
cargo bench -- --save-baseline main
cargo bench -- --baseline main
```

**Python benchmarks:**
```bash
# Run all Python benchmarks
uv run pytest tests/benchmarks/ --benchmark-only

# Run with comparison
uv run pytest tests/benchmarks/ --benchmark-compare
```

## Measuring PyO3 Overhead

The critical measurement is: "How much time is lost to the Python-Rust boundary?"

### Strategy 1: Same Work, Different Paths

```python
# tests/benchmarks/test_ffi_overhead.py

def test_rust_yaml_load(benchmark, yaml_file):
    """Pure Rust path (from Python)."""
    import classic_yaml
    ops = classic_yaml.RustYamlOperations()
    benchmark(lambda: ops.load(str(yaml_file)))

def test_python_yaml_load(benchmark, yaml_file):
    """Pure Python path (ruamel.yaml fallback - for comparison only)."""
    import ruamel.yaml
    yaml = ruamel.yaml.YAML()
    benchmark(lambda: yaml.load(yaml_file))
```

### Strategy 2: Minimal Work, Measure Overhead

```python
def test_ffi_noop(benchmark):
    """Minimal Rust call to isolate FFI overhead."""
    import classic_perf
    # Record a single timing - minimal computation
    benchmark(lambda: classic_perf.record_timing("bench_op", 0.001))
```

### Strategy 3: Batch vs Individual

```python
def test_individual_calls(benchmark, items):
    """N individual FFI calls."""
    import classic_yaml
    ops = classic_yaml.RustYamlOperations()
    def run():
        for item in items:
            ops.validate(item)
    benchmark(run)

def test_batch_call(benchmark, items):
    """Single batched FFI call."""
    import classic_yaml
    ops = classic_yaml.RustYamlOperations()
    benchmark(lambda: ops.validate_batch(items))
```

## Component Boundaries

| Layer | Responsibility | Benchmark Location |
|-------|---------------|-------------------|
| `-core` crates | Pure Rust algorithms | `{crate}/benches/` |
| `-py` crates | PyO3 type conversion | `tests/benchmarks/` (Python-side) |
| Python integration | Full end-to-end paths | `tests/benchmarks/` |
| Cross-crate pipelines | Full Rust pipelines | `rust/benchmarks/classic-bench/` |

## Data Flow for Benchmarking

```
                    +---------------------------------+
                    |   Python Application            |
                    |   (tests/benchmarks/)           |
                    +----------------+----------------+
                                     |
                    +----------------v----------------+
                    |    PyO3 Bindings                |
                    |    (-py crates)                 |
                    |    [Type conversion]            |
                    +----------------+----------------+
                                     |
                    +----------------v----------------+
                    |   Business Logic                |
                    |   (-core crates)                |
                    |   [benches/ dirs]               |
                    +----------------+----------------+
                                     |
                    +----------------v----------------+
                    |   Foundation                    |
                    |   (classic-shared-core)         |
                    |   [benches/ exists]             |
                    +---------------------------------+
```

## Suggested Implementation Order

### Phase 1: Foundation Benchmarks (Days 1-2)

Extend existing `classic-shared-core/benches/` with additional coverage. This validates the infrastructure works and establishes patterns.

1. Verify existing benchmarks run: `cargo bench -p classic-shared-core`
2. Add any missing benchmark groups
3. Document baseline numbers

### Phase 2: Hot Path Crate Benchmarks (Days 3-5)

Add `benches/` to the most performance-critical `-core` crates:

1. `classic-yaml-core/benches/` - YAML is called constantly
2. `classic-scanlog-core/benches/` - Core business operation
3. `classic-file-io-core/benches/` - Underlies everything

### Phase 3: PyO3 Overhead Measurement (Days 6-7)

Create Python-side benchmarks to measure FFI overhead:

1. Add `pytest-benchmark` to dev dependencies
2. Create `tests/benchmarks/` structure
3. Measure Rust vs Python paths
4. Measure batch vs individual calls
5. Identify PyO3 conversion hotspots

### Phase 4: Workspace Integration Crate (Days 8-10)

Create `rust/benchmarks/classic-bench/` for:

1. End-to-end pipeline benchmarks
2. Baseline establishment
3. Historical comparison infrastructure

### Phase 5: CI Integration (Day 11+)

Add benchmark regression detection:

1. Store baselines in CI artifacts
2. Compare PRs against baselines
3. Alert on significant regressions

## Anti-Patterns to Avoid

### Anti-Pattern 1: Benchmarking Through PyO3 for Pure Rust

**Wrong:** Benchmarking Rust code by calling from Python
```python
# This includes FFI overhead, not pure Rust performance
benchmark(lambda: classic_yaml.RustYamlOperations().load(path))
```

**Right:** Benchmark pure Rust separately, measure FFI overhead separately
```rust
// Pure Rust benchmark
b.iter(|| yaml_operations::load(&path));
```
```python
# FFI overhead benchmark (measures the boundary, not the work)
benchmark(lambda: ops.load(path))  # Compare to pure Rust baseline
```

### Anti-Pattern 2: Not Warming Caches

**Wrong:** First-call benchmarks include cache population
```rust
b.iter(|| path_handler.normalize_path(&path));  // First iter is cold!
```

**Right:** Prime caches before benchmark loop
```rust
path_handler.normalize_path(&path);  // Warm cache
b.iter(|| path_handler.normalize_path(&path));  // All hot
```

### Anti-Pattern 3: Mixing Compilation in Timing

**Wrong:** Including regex compilation in benchmark
```rust
b.iter(|| {
    let re = Regex::new(pattern).unwrap();
    re.is_match(text)
});
```

**Right:** Pre-compile outside benchmark
```rust
let re = Regex::new(pattern).unwrap();
b.iter(|| re.is_match(text));
```

### Anti-Pattern 4: Ignoring Variability

**Wrong:** Single sample size, no statistical analysis
**Right:** Use Criterion's statistical analysis, check confidence intervals

## Scalability Considerations

| Scale | Benchmark Focus | Infrastructure |
|-------|-----------------|----------------|
| Single crate | `{crate}/benches/` | Local `cargo bench` |
| Multiple crates | `classic-bench` integration | Workspace-level |
| CI/CD | Baseline comparison | GitHub Actions + artifacts |
| Historical | Trend analysis | External service (Bencher, DataDog) |

## Sources

Research conducted using:
- [Criterion.rs documentation](https://docs.rs/criterion/latest/criterion/)
- [Criterion.rs GitHub repository](https://github.com/bheisler/criterion.rs)
- [PyO3 performance analysis](https://github.com/PyO3/pyo3/issues/1607)
- [Rust Cargo workspace documentation](https://doc.rust-lang.org/book/ch14-03-cargo-workspaces.html)
- [Large Rust Workspaces patterns](https://matklad.github.io/2021/08/22/large-rust-workspaces.html)
- Existing CLASSIC codebase analysis (HIGH confidence - direct inspection)
