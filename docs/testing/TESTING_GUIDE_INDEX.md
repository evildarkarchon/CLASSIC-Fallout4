# CLASSIC Testing Guide Index

This index points contributors to the active testing workflows for the current **C++ + Rust** architecture.

Need the old-to-new path translation first? Use the [Workspace Migration Matrix](../workspace-migration-matrix.md).

## 1) Primary testing entry points (active)

### C++ frontend tests (via script wrappers + CTest)

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -Compiler clang-cl
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test -Compiler clang-cl
```

CLI integration test wrapper:

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/test_cli.ps1
```

> Policy: run C++ tests via wrapper scripts/CTest path, not by invoking test binaries directly.

### Rust workspace tests and quality gates

```powershell
cargo test --workspace
cargo test --workspace -- --nocapture

cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

---

## 2) CI workflow mapping

- [`ci-cpp.yml`](../../.github/workflows/ci-cpp.yml)
  - C++ CLI/GUI build + test jobs on Windows for MSVC and clang-cl
- [`ci-rust.yml`](../../.github/workflows/ci-rust.yml)
  - Rust format/lint/build/test jobs
- [`ci-binding-compliance.yml`](../../.github/workflows/ci-binding-compliance.yml)
  - umbrella over `ci-rust.yml` and `ci-cpp.yml` plus the conformance-only `full` verdict
- [`benchmarks.yml`](../../.github/workflows/benchmarks.yml)
  - benchmark regression checks

Use local command sets that mirror these workflows before opening PRs.

---

## 3) Repository gates

The Python and Node bindings are retired (ADR-0010, in [`docs/adr/`](../adr/)). Repository tooling under `tools/` runs from the tools-only uv project:

```powershell
uv sync --project tools
uv run --project tools python tools/user_settings_ownership/check.py --repo-root .
uv run --project tools python tools/binding_compliance/scan_run_workflow_policy.py --repo-root .
```

See [Repository gates](../development/repository-gates.md) for where each check runs in CI.

---

## 4) Scope boundaries (important)

- Active app/runtime paths:
  - [`classic-cli/`](../../classic-cli)
  - [`classic-gui/`](../../classic-gui)
  - [`foundation/`](../../foundation)
  - [`business-logic/`](../../business-logic)
  - [`cpp-bindings/classic-cpp-bridge/`](../../cpp-bindings/classic-cpp-bridge)
  - [`ui-applications/classic-tui/`](../../ui-applications/classic-tui)
The pure-Python runtime and its pytest suite have been removed from the repo. Their documentation is preserved under [`docs/archive/python-era/`](../archive/python-era) as historical record only — it is not part of any contributor test flow.

---

## 5) Related testing docs

- [`docs/testing/rust_testing_guide.md`](rust_testing_guide.md)
- [`docs/archive/python-era/`](../archive/python-era) — test-structure, pollution, fixture, async-bridge, global-registry, and YAML-cache guides for the retired pure-Python suite. Historical record only.

---

## 6) Quick pre-PR checklist

- [ ] Ran relevant C++ wrapper script tests (`classic-cli` / `classic-gui`)
- [ ] Ran Rust format/lint/tests for touched crates
- [ ] Ran Node parity/runtime checks if Node-exposed APIs changed
- [ ] Ran Python parity/stub/runtime checks if Python-exposed APIs changed
- [ ] Updated docs when architecture/build/test behavior changed

Canonical policy reference: [`AGENTS.md`](../../AGENTS.md).

> Migration note: older `ClassicLib-rs/...` testing instructions are historical only; translate them through the [Workspace Migration Matrix](../workspace-migration-matrix.md).

