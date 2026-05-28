# CLASSIC Testing Guide Index

This index points contributors to the active testing workflows for the current **C++ + Rust** architecture.

Need the old-to-new path translation first? Use the [Workspace Migration Matrix](../workspace-migration-matrix.md).

## 1) Primary testing entry points (active)

### C++ frontend tests (via script wrappers + CTest)

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
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
  - C++ CLI/GUI build + test jobs on Windows
- [`ci-rust.yml`](../../.github/workflows/ci-rust.yml)
  - Rust format/lint/build/test jobs
- [`ci-typescript.yml`](../../.github/workflows/ci-typescript.yml)
  - Node binding parity gate and Bun/Node runtime tests
- [`ci-python-bindings.yml`](../../.github/workflows/ci-python-bindings.yml)
  - Python binding parity gate, stub validation, and smoke tests
- [`benchmarks.yml`](../../.github/workflows/benchmarks.yml)
  - benchmark regression checks

Use local command sets that mirror these workflows before opening PRs.

---

## 3) Binding-specific testing flows

### Node bindings (`node-bindings/classic-node`)

```powershell
# From node-bindings/classic-node
bun install
bun run build
bun run cli -- --version
bun run parity:gate
bun run test:bun
bun run test:node
```

### Python bindings (`python-bindings`)

```powershell
# python-bindings/ is a uv-managed project (pyproject.toml + uv.lock).
# `--inexact` stops uv from pruning maturin-built classic-*-py wheels.
# Add `--group drift-guards` to also install ruamel.yaml for schema_version_gate.py.
uv sync --project python-bindings --inexact --group drift-guards
uv run --project python-bindings python tools/python_api_parity/check_parity_gate.py --repo-root .
uv run --project python-bindings python tools/cxx_api_parity/check_parity_gate.py --repo-root .
uv run --project python-bindings python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --project python-bindings python -m pytest python-bindings/tests -q
```

---

## 4) Scope boundaries (important)

- Active app/runtime paths:
  - [`classic-cli/`](../../classic-cli)
  - [`classic-gui/`](../../classic-gui)
  - [`foundation/`](../../foundation)
  - [`business-logic/`](../../business-logic)
  - [`cpp-bindings/classic-cpp-bridge/`](../../cpp-bindings/classic-cpp-bridge)
  - [`ui-applications/classic-tui/`](../../ui-applications/classic-tui)
- Maintained integration bindings:
  - [`node-bindings/classic-node/`](../../node-bindings/classic-node)
  - [`python-bindings/`](../../python-bindings)
- Deprecated runtime entrypoints/orchestration:
  - [`deprecated/`](../../deprecated)

Do not assume Python runtime/orchestration tests under `deprecated/` are part of the default contributor test flow unless the task explicitly targets migration/legacy support.

---

## 5) Related testing docs

- [`docs/testing/rust_testing_guide.md`](rust_testing_guide.md)
- [`docs/testing/TEST_STRUCTURE.md`](TEST_STRUCTURE.md)
- [`docs/testing/test_pollution_guide.md`](test_pollution_guide.md)
- [`docs/testing/testing_async_bridge.md`](testing_async_bridge.md) *(legacy Python-runtime context)*
- [`docs/testing/testing_global_registry.md`](testing_global_registry.md) *(legacy Python-runtime context)*
- [`docs/testing/testing_yaml_cache.md`](testing_yaml_cache.md) *(legacy Python-runtime context)*

---

## 6) Quick pre-PR checklist

- [ ] Ran relevant C++ wrapper script tests (`classic-cli` / `classic-gui`)
- [ ] Ran Rust format/lint/tests for touched crates
- [ ] Ran Node parity/runtime checks if Node-exposed APIs changed
- [ ] Ran Python parity/stub/runtime checks if Python-exposed APIs changed
- [ ] Updated docs when architecture/build/test behavior changed

Canonical policy reference: [`AGENTS.md`](../../AGENTS.md).

> Migration note: older `ClassicLib-rs/...` testing instructions are historical only; translate them through the [Workspace Migration Matrix](../workspace-migration-matrix.md).

