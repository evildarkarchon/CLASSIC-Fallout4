# CLASSIC Rust Documentation Index

This index tracks Rust-centric documentation for the **active** CLASSIC architecture: C++ frontends + Rust core.

## Architecture Context

- Active frontends: [`classic-cli/`](../classic-cli), [`classic-gui/`](../classic-gui)
- Active core: [`ClassicLib-rs/`](../ClassicLib-rs)
- Active bridge to native frontends: [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`](../ClassicLib-rs/cpp-bindings/classic-cpp-bridge)
- Maintained integration bindings: [`ClassicLib-rs/node-bindings/`](../ClassicLib-rs/node-bindings), [`ClassicLib-rs/python-bindings/`](../ClassicLib-rs/python-bindings)
- Deprecated Python runtime entrypoints/orchestration: [`deprecated/`](../deprecated)

For contributor policy and canonical command expectations, see [`AGENTS.md`](../AGENTS.md).

---

## Start Here

1. [`docs/architecture/ARCHITECTURE_OVERVIEW.md`](architecture/ARCHITECTURE_OVERVIEW.md) — current system architecture and runtime boundaries
2. [`docs/api/QUICK_START.md`](api/QUICK_START.md) — practical setup/build/test flow
3. [`docs/development/RUST_INTEGRATION_GUIDE.md`](development/RUST_INTEGRATION_GUIDE.md) — integration surfaces and extension patterns
4. [`docs/testing/TESTING_GUIDE_INDEX.md`](testing/TESTING_GUIDE_INDEX.md) — testing matrix and CI alignment

---

## Rust Workspace Documentation

### Core architecture and implementation

- [`docs/development/rust_workspace_architecture.md`](development/rust_workspace_architecture.md)
- [`docs/rust/rust_architecture.md`](rust/rust_architecture.md)
- [`docs/rust/rust_modules_detailed.md`](rust/rust_modules_detailed.md)
- [`docs/rust/rust_parser_module.md`](rust/rust_parser_module.md)

### Runtime and async model

- [`docs/development/async_development_guide.md`](development/async_development_guide.md)
- [`docs/rust/rust_async_pattern.md`](rust/rust_async_pattern.md)
- [`docs/rust/gil_release_pattern_pyo3_0.27.md`](rust/gil_release_pattern_pyo3_0.27.md)

### PyO3 and Python binding surfaces (maintained integration surface)

- [`docs/development/pyo3_integration_patterns.md`](development/pyo3_integration_patterns.md)
- [`docs/rust/PyO3-0.27-migration.md`](rust/PyO3-0.27-migration.md)
- [`docs/rust/pyo3_quick_reference.md`](rust/pyo3_quick_reference.md)

> Scope note: this section documents maintained binding surfaces under [`ClassicLib-rs/python-bindings/`](../ClassicLib-rs/python-bindings), not deprecated Python app runtime entrypoints.

### Development and troubleshooting

- [`docs/rust/development_with_rust.md`](rust/development_with_rust.md)
- [`docs/rust/troubleshooting_rust.md`](rust/troubleshooting_rust.md)
- [`docs/development/RUST_INTEGRATION_GUIDE.md`](development/RUST_INTEGRATION_GUIDE.md)

### Performance and benchmarking

- [`docs/performance/performance_monitoring.md`](performance/performance_monitoring.md)
- [`docs/performance/rust_db_benchmark_baseline.md`](performance/rust_db_benchmark_baseline.md)
- [`docs/implementation/performance_optimization_complete.md`](implementation/performance_optimization_complete.md)

---

## Canonical Build/Test Commands (Rust)

```powershell
cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo build --workspace --release --manifest-path ClassicLib-rs/Cargo.toml

cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml -- --nocapture

cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings
```

---

## CI Mapping

- Rust quality/build/test pipeline: [`ci-rust.yml`](../.github/workflows/ci-rust.yml)
- C++ frontend build/test pipeline that consumes Rust artifacts: [`ci-cpp.yml`](../.github/workflows/ci-cpp.yml)
- Node parity/runtime checks for Rust-exposed APIs: [`ci-typescript.yml`](../.github/workflows/ci-typescript.yml)
- Performance regression checks: [`benchmarks.yml`](../.github/workflows/benchmarks.yml)

---

## Historical/Transition Note

Older documents may still discuss hybrid Python-runtime execution or fallback-heavy flows. Treat those as historical unless they are explicitly aligned with:

1. Current active architecture (`classic-cli` + `classic-gui` + `ClassicLib-rs`)
2. Maintained binding surfaces (`python-bindings`, `node-bindings`)
3. Deprecated runtime scope (`deprecated/`)

