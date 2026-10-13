# Rust Integration Guide

This guide describes how Rust integrates into the current CLASSIC codebase, where **C++ frontends consume Rust core services**.

## 1. Integration Model (Current)

### Active runtime architecture

- Native C++ CLI: [`classic-cli/`](../../classic-cli)
- Native C++ GUI: [`classic-gui/`](../../classic-gui)
- Rust core/business logic: [`business-logic/`](../../business-logic) and [`foundation/`](../../foundation)
- C++ ↔ Rust bridge crate: [`cpp-bindings/classic-cpp-bridge/`](../../cpp-bindings/classic-cpp-bridge)

### Retired binding surfaces

The Python and Node bindings retired with ADR-0010 (in [`docs/adr/`](../adr/)); the C++ bridge is the only binding layer.

### Deprecated runtime scope

The legacy Python runtime and orchestration layer has been removed from the repo; its documentation is preserved under [`docs/archive/python-era/`](../archive/python-era).

---

## 2. Rust Workspace Layers

### Layer 1: Foundation

- Path: [`foundation/`](../../foundation)
- Purpose: shared runtime, common utilities, shared error/infra primitives

### Layer 2: Business logic (`*-core` crates)

- Path: [`business-logic/`](../../business-logic)
- Purpose: pure Rust domain logic; no binding-framework coupling in core crates

### Layer 3: Bindings/adapters

- C++ bridge: [`cpp-bindings/classic-cpp-bridge/`](../../cpp-bindings/classic-cpp-bridge)

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
   - Retired: the Python and Node bindings (ADR-0010)
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

## 5. CI Contract

- [`ci-cpp.yml`](../../.github/workflows/ci-cpp.yml): C++ apps + CTest pipeline
- [`ci-rust.yml`](../../.github/workflows/ci-rust.yml): rustfmt, clippy, build, tests
- [`ci-binding-compliance.yml`](../../.github/workflows/ci-binding-compliance.yml): umbrella plus the conformance-only `full` verdict
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

## 7. Transition Note

Historical docs may still describe Python runtime orchestration as the default app path. Treat those references as archival context unless they explicitly target migration/legacy support work.

