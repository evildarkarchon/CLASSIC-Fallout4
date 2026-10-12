# CLASSIC Documentation

This documentation set reflects the current **C++ + Rust** product architecture.

## Current Product Architecture (Source of Truth)

- **CLI frontend (active):** [`classic-cli/`](../classic-cli)
- **GUI frontend (active):** [`classic-gui/`](../classic-gui)
- **Rust workspace shell (active):** repo root (`../Cargo.toml`, `../Cargo.lock`, `../.cargo/config.toml`)
- **Shared/runtime crates (active):** [`foundation/`](../foundation)
- **Core/business logic (active):** [`business-logic/`](../business-logic)
- **C++ bridge (active):** [`cpp-bindings/classic-cpp-bridge/`](../cpp-bindings/classic-cpp-bridge)
- **Rust TUI app (active):** [`ui-applications/classic-tui/`](../ui-applications/classic-tui)

For policy-level guidance, see [`AGENTS.md`](../AGENTS.md).
For old-to-new workspace translations, see the [Workspace Migration Matrix](workspace-migration-matrix.md).

---

## Quick Navigation

- [`api/README.md`](api/README.md) - contributor-facing Rust API docs index
- [`api/QUICK_START.md`](api/QUICK_START.md) — contributor quick start for current C++ + Rust workflows
- [`architecture/ARCHITECTURE_OVERVIEW.md`](architecture/ARCHITECTURE_OVERVIEW.md) — architecture map and runtime boundaries
- [`development/RUST_INTEGRATION_GUIDE.md`](development/RUST_INTEGRATION_GUIDE.md) — Rust integration surfaces (the C++ bridge)
- [`testing/TESTING_GUIDE_INDEX.md`](testing/TESTING_GUIDE_INDEX.md) — local/CI testing matrix and commands
- [`RUST_DOCUMENTATION_INDEX.md`](RUST_DOCUMENTATION_INDEX.md) — Rust-focused index for active workspace docs
- [`archive/README.md`](archive/README.md) — historical records only; never live guidance

---

## Canonical Build/Test Command Map

These are the canonical commands for active product paths.

Need the legacy-to-current translation table first? Open the [Workspace Migration Matrix](workspace-migration-matrix.md).

### C++

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Compiler clang-cl
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Compiler clang-cl

pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -Compiler clang-cl
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test -Compiler clang-cl

pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -CTestName "ThreadPool executes all enqueued tasks"
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -IntegrationTestName help,version
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test -CTestName classic-gui-test-scan-settings-wiring
```

Use the PowerShell wrappers for all C++ testing. Do not invoke raw `ctest` or C++ test executables directly.

### Rust

```powershell
cargo build --workspace
cargo test --workspace
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

### Repository tooling

The Python and Node bindings are retired (ADR-0010, in [`docs/adr/`](adr/)). Repository tooling under `tools/` runs from the tools-only uv project:

```powershell
uv sync --project tools
uv run --project tools python -m pytest tools/user_settings_ownership/tests -q
```

The checks CI runs as direct steps are listed in [Repository gates](development/repository-gates.md).

---

## CI Workflow Mapping

- [`ci-cpp.yml`](../.github/workflows/ci-cpp.yml) — C++ CLI/GUI build + test on Windows for MSVC and clang-cl
- [`ci-rust.yml`](../.github/workflows/ci-rust.yml) — Rust format/lint/build/test
- [`ci-binding-compliance.yml`](../.github/workflows/ci-binding-compliance.yml) — umbrella over `ci-rust.yml` and `ci-cpp.yml` plus the conformance-only `full` verdict
- [`benchmarks.yml`](../.github/workflows/benchmarks.yml) — benchmark regression detection

---

## Documentation Scope Notes

1. Treat C++ frontends + Rust core as the default contributor path.
2. Treat everything under [`archive/`](archive/README.md) as historical record, not live guidance. Do not follow its commands or paths.

> Migration note: if you encounter older `ClassicLib-rs/...` instructions, translate them through the [Workspace Migration Matrix](workspace-migration-matrix.md) instead of treating them as live workspace guidance.

---

## Maintenance Guidance

When architecture/build/test behavior changes, update at minimum:

- [`README.md`](../README.md)
- [`AGENTS.md`](../AGENTS.md)
- [`docs/README.md`](README.md)
- [`docs/architecture/ARCHITECTURE_OVERVIEW.md`](architecture/ARCHITECTURE_OVERVIEW.md)

