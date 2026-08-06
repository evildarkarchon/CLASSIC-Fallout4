# Rust Integration Guide

This guide describes how Rust integrates into the current CLASSIC codebase, where **C++ frontends consume Rust core services**.

## 1. Integration Model (Current)

### Active runtime architecture

- Native C++ CLI: [`classic-cli/`](../../classic-cli)
- Native C++ GUI: [`classic-gui/`](../../classic-gui)
- Rust core/business logic: [`business-logic/`](../../business-logic) and [`foundation/`](../../foundation)
- C++ ↔ Rust bridge crate: [`cpp-bindings/classic-cpp-bridge/`](../../cpp-bindings/classic-cpp-bridge)

### Maintained binding surfaces

- Node bindings (NAPI-RS): [`node-bindings/`](../../node-bindings)
- Python bindings (PyO3): [`python-bindings/`](../../python-bindings)

### Deprecated runtime scope

The legacy Python runtime and orchestration layer has been removed from the repo; its documentation is preserved under [`docs/archive/python-era/`](../archive/python-era).

---

## 2. Rust Workspace Layers

### Layer 1: Foundation

- Path: [`foundation/`](../../foundation)
- Purpose: shared runtime, common utilities, shared error/infra primitives

### Layer 2: Business logic (`*-core` crates)

- Path: [`business-logic/`](../../business-logic)
- Purpose: pure Rust domain logic; no PyO3 coupling in core crates

### Layer 3: Bindings/adapters

- C++ bridge: [`cpp-bindings/classic-cpp-bridge/`](../../cpp-bindings/classic-cpp-bridge)
- Node adapters: [`node-bindings/`](../../node-bindings)
- Python adapters: [`python-bindings/`](../../python-bindings)

---

## 3. Key Integration Rules

1. **ONE RUNTIME RULE**
   - Use shared runtime facilities from Rust core/foundation.
   - Do not create independent Tokio runtime islands.

2. **Layer separation**
   - Keep business/domain behavior in `*-core` crates.
   - Keep binding-layer concerns in binding crates.

3. **Native apps consume bridge APIs, not ad-hoc FFI**
   - Route C++ integration through [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge).

4. **Python scope distinction**
   - Maintained: PyO3 bindings in [`python-bindings/`](../../python-bindings)
   - Removed: the Python app runtime entrypoints/orchestration (docs under [`docs/archive/python-era/`](../archive/python-era))

---

## 4. Canonical Build and Test Commands

### C++ build/test (recommended wrappers)

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1

pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

### Rust build/test/lint

```powershell
cargo build --workspace
cargo build --workspace --release

cargo test --workspace
cargo test --workspace -- --nocapture

cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

### Node parity/runtime checks (when relevant)

```powershell
# From node-bindings/classic-node
bun install
bun run build
bun run parity:gate:local
bun run test:bun
bun run test:node
```

### Python parity/runtime checks (when relevant)

```powershell
# python-bindings/ is a uv-managed project (pyproject.toml + uv.lock).
# --inexact is load-bearing: it keeps uv from pruning maturin-built classic-*-py wheels.
uv sync --project python-bindings --inexact
python tools/python_api_parity/check_parity_gate.py --repo-root .
python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --python python-bindings/.venv/Scripts/python.exe python -m pytest python-bindings/tests -q
```

---

## 5. CI Contract

- [`ci-cpp.yml`](../../.github/workflows/ci-cpp.yml): C++ apps + CTest pipeline
- [`ci-rust.yml`](../../.github/workflows/ci-rust.yml): rustfmt, clippy, build, tests
- [`ci-typescript.yml`](../../.github/workflows/ci-typescript.yml): Node parity + runtime tests
- [`ci-python-bindings.yml`](../../.github/workflows/ci-python-bindings.yml): Python parity + smoke tests
- [`benchmarks.yml`](../../.github/workflows/benchmarks.yml): performance regression checks

When changing build/test instructions in docs, ensure this guide remains consistent with these workflows and [`AGENTS.md`](../../AGENTS.md).

---

## 6. Typical Contributor Workflows

### A) C++ frontend change

1. Modify files in [`classic-cli/`](../../classic-cli) and/or [`classic-gui/`](../../classic-gui)
2. Build using wrapper scripts
3. Run script-driven CTest via `-Test`

### B) Rust core change

1. Modify crates in [`business-logic/`](../../business-logic)
2. Run Rust format/lint/tests
3. Rebuild C++ frontend if bridge-exposed behavior changed

### C) Bridge/API surface change

1. Update Rust core + [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge)
2. Update C++ call sites as needed
3. Run C++ and Rust checks
4. If Node-facing APIs changed, run parity/test commands in [`classic-node`](../../node-bindings/classic-node)

### D) Python binding maintenance (not runtime orchestration)

1. Update crates under [`python-bindings/`](../../python-bindings)
2. Validate against relevant Rust crates/tests
3. Keep scope limited to the maintained bindings

---

## 7. Transition Note

Historical docs may still describe Python runtime orchestration as the default app path. Treat those references as archival context unless they explicitly target migration/legacy support work.

