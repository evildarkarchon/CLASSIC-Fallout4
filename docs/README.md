# CLASSIC Documentation

This documentation set reflects the current **C++ + Rust** product architecture.

## Current Product Architecture (Source of Truth)

- **CLI frontend (active):** [`classic-cli/`](../classic-cli)
- **GUI frontend (active):** [`classic-gui/`](../classic-gui)
- **Rust workspace shell (active):** repo root (`../Cargo.toml`, `../Cargo.lock`, `../.cargo/config.toml`)
- **Shared/runtime crates (active):** [`foundation/`](../foundation)
- **Core/business logic (active):** [`business-logic/`](../business-logic)
- **C++ bridge (active):** [`cpp-bindings/classic-cpp-bridge/`](../cpp-bindings/classic-cpp-bridge)
- **Maintained integration bindings:** [`python-bindings/`](../python-bindings) and [`node-bindings/classic-node/`](../node-bindings/classic-node)
- **Rust TUI app (active):** [`ui-applications/classic-tui/`](../ui-applications/classic-tui)
- **Deprecated Python runtime entrypoints/orchestration (archival):** [`deprecated/`](../deprecated)

For policy-level guidance, see [`AGENTS.md`](../AGENTS.md).
For old-to-new workspace translations, see the [Workspace Migration Matrix](workspace-migration-matrix.md).

---

## Quick Navigation

- [`api/README.md`](api/README.md) - contributor-facing Rust API docs index
- [`api/QUICK_START.md`](api/QUICK_START.md) — contributor quick start for current C++ + Rust workflows
- [`architecture/ARCHITECTURE_OVERVIEW.md`](architecture/ARCHITECTURE_OVERVIEW.md) — architecture map and runtime boundaries
- [`development/RUST_INTEGRATION_GUIDE.md`](development/RUST_INTEGRATION_GUIDE.md) — Rust integration surfaces (C++, Node, Python bindings)
- [`testing/TESTING_GUIDE_INDEX.md`](testing/TESTING_GUIDE_INDEX.md) — local/CI testing matrix and commands
- [`RUST_DOCUMENTATION_INDEX.md`](RUST_DOCUMENTATION_INDEX.md) — Rust-focused index for active workspace docs

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

### Node bindings (when touching NAPI surface)

```powershell
# From node-bindings/classic-node
bun install
bun run build
bun run cli -- --version
bun run parity:gate
bun run test:bun
bun run test:node
```

### Python bindings (when touching PyO3 surface)

```powershell
# python-bindings/ is a uv-managed project (pyproject.toml + uv.lock).
# `--inexact` is load-bearing: it keeps uv from pruning maturin-built classic-*-py wheels.
# Add `--group drift-guards` to also install ruamel.yaml for schema_version_gate.py.
uv sync --project python-bindings --inexact --group drift-guards
uv run --project python-bindings python tools/python_api_parity/check_parity_gate.py --repo-root .
uv run --project python-bindings python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --project python-bindings python -m pytest python-bindings/tests -q
```

---

## CI Workflow Mapping

- [`ci-cpp.yml`](../.github/workflows/ci-cpp.yml) — C++ CLI/GUI build + test on Windows for MSVC and clang-cl
- [`ci-rust.yml`](../.github/workflows/ci-rust.yml) — Rust format/lint/build/test
- [`ci-typescript.yml`](../.github/workflows/ci-typescript.yml) — Node parity gates + Bun/Node runtime tests
- [`ci-python-bindings.yml`](../.github/workflows/ci-python-bindings.yml) — Python parity gates + binding smoke tests
- [`benchmarks.yml`](../.github/workflows/benchmarks.yml) — benchmark regression detection

---

## Documentation Scope Notes

1. Treat C++ frontends + Rust core as the default contributor path.
2. Treat [`python-bindings/`](../python-bindings) and [`node-bindings/classic-node/`](../node-bindings/classic-node) as maintained integration surfaces where applicable.
3. Treat Python runtime entrypoints and orchestration under [`deprecated/`](../deprecated) as archival unless a task explicitly targets migration or legacy support.

> Migration note: if you encounter older `ClassicLib-rs/...` instructions, translate them through the [Workspace Migration Matrix](workspace-migration-matrix.md) instead of treating them as live workspace guidance.

---

## Maintenance Guidance

When architecture/build/test behavior changes, update at minimum:

- [`README.md`](../README.md)
- [`AGENTS.md`](../AGENTS.md)
- [`docs/README.md`](README.md)
- [`docs/architecture/ARCHITECTURE_OVERVIEW.md`](architecture/ARCHITECTURE_OVERVIEW.md)

