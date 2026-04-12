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
2. [`docs/api/README.md`](api/README.md) — contributor-facing Rust API docs index for core crates
3. [`docs/api/QUICK_START.md`](api/QUICK_START.md) — practical setup/build/test flow
4. [`docs/development/RUST_INTEGRATION_GUIDE.md`](development/RUST_INTEGRATION_GUIDE.md) — integration surfaces and extension patterns
5. [`docs/testing/TESTING_GUIDE_INDEX.md`](testing/TESTING_GUIDE_INDEX.md) — testing matrix and CI alignment

---

## Contributor API Guides

- [`docs/api/README.md`](api/README.md) — ordered index for contributor-facing crate guides
- [`docs/api/classic-shared-core.md`](api/classic-shared-core.md) — shared runtime, error, path, performance, and string helpers
- [`docs/api/classic-perf-core.md`](api/classic-perf-core.md) — global timing sample collection, summaries, and scoped timer helpers
- [`docs/api/classic-registry-core.md`](api/classic-registry-core.md) — process-wide typed singleton registry and convenience key helpers
- [`docs/api/classic-message-core.md`](api/classic-message-core.md) — shared message DTOs, routing enums, and startup/log formatting helpers
- [`docs/api/classic-settings-core.md`](api/classic-settings-core.md) — YAML settings cache plus sync/async raw-document loading helpers, including the surviving owner docs for absorbed YAML parsing/cache helpers plus `YamlFile` and settings constants
- [`docs/api/classic-version-registry-core.md`](api/classic-version-registry-core.md) — version matching and registry-backed metadata, including the surviving owner docs for `Fallout4Version` and `NULL_VERSION`
- [`docs/api/classic-shared-core.md`](api/classic-shared-core.md) — shared runtime, error, path, performance, and string helpers, including the surviving owner docs for `GameId`
- [`docs/api/classic-version-core.md`](api/classic-version-core.md) — version parsing, text extraction, and PE-version helpers
- [`docs/api/classic-web-core.md`](api/classic-web-core.md) — small URL, user-agent, and mod-site helper layer
- [`docs/api/classic-update-core.md`](api/classic-update-core.md) — async GitHub release/update-check client and DTO layer
- [`docs/api/classic-config-core.md`](api/classic-config-core.md) — CLASSIC settings, Main/Game/Ignore YAML loading, AND the absorbed crashgen rule model (formerly its own crate, merged in v9.1.0 Phase 2)
- [`docs/api/classic-path-core.md`](api/classic-path-core.md) — game-path, documents-path, validation, and backup helpers
- [`docs/api/classic-xse-core.md`](api/classic-xse-core.md) — XSE loader/version detection helpers used by setup checks and bindings
- [`docs/api/game-setup-workflow.md`](api/game-setup-workflow.md) — cross-crate setup/install validation flow across path, XSE, scangame, and version registry crates
- [`docs/api/formid-settings-boundary.md`](api/formid-settings-boundary.md) — current split between config serialization and scan-time FormID DB path loading
- [`docs/api/classic-file-io-core.md`](api/classic-file-io-core.md) — shared file I/O, directory walking, hashing, and log helpers
- [`docs/api/classic-resource-core.md`](api/classic-resource-core.md) — lightweight resource classification, enumeration, and per-file validation helpers
- [`docs/api/classic-database-core.md`](api/classic-database-core.md) — async SQLite/FormID lookup pool and helpers
- [`docs/api/formid-sqlite-conventions.md`](api/formid-sqlite-conventions.md) — current FormID fixture/schema/path conventions from source and tests
- [`docs/api/classic-scangame-core.md`](api/classic-scangame-core.md) — game-installation, archive, loose-file, and setup validation workflows
- [`docs/api/classic-cpp-bridge-game-entrypoints.md`](api/classic-cpp-bridge-game-entrypoints.md) — active C++ bridge entry points for path, game, and scangame workflows
- [`docs/api/classic-cpp-bridge-data-entrypoints.md`](api/classic-cpp-bridge-data-entrypoints.md) — active C++ bridge entry points for config, file I/O, database, and scanlog workflows
- [`docs/api/classic-cpp-bridge-scan-progress-callback.md`](api/classic-cpp-bridge-scan-progress-callback.md) — current `classic::scanner` batch progress callback contract and bridge-local event ordering
- [`docs/api/classic-gui-scan-progress-consumer.md`](api/classic-gui-scan-progress-consumer.md) — how the active Qt frontend consumes batch scan progress into visible progress and status state
- [`docs/api/classic-gui-scan-result-ordering.md`](api/classic-gui-scan-result-ordering.md) — how the active Qt frontend correlates completion-order batch results back to original rows with `input_index`
- [`docs/api/binding-parity-overview.md`](api/binding-parity-overview.md) — current C++ bridge, Node, and Python exposure comparison for shared Rust crates
- [`docs/api/node-python-contract-map.md`](api/node-python-contract-map.md) — where the active Node and Python public contracts, wrapper files, and parity artifacts live
- [`docs/api/binding-contract-refresh-note.md`](api/binding-contract-refresh-note.md) — when Node `index.d.ts` and Python `.pyi` contract artifacts should refresh separately versus together
- [`docs/api/classic-scanlog-core.md`](api/classic-scanlog-core.md) — crash-log parsing, orchestration, and report generation

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

