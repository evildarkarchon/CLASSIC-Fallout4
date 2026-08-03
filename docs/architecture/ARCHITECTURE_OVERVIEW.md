# CLASSIC Architecture Overview

> Last updated: 2026-03-04

This document describes the **current active** CLASSIC architecture.

## Executive Summary

CLASSIC is a **C++ + Rust** application:

- Native frontends in C++:
  - [`classic-cli/`](../../classic-cli)
  - [`classic-gui/`](../../classic-gui)
- Core domain logic in Rust workspace:
  - Rust workspace root: the repository root (`../../Cargo.toml`)
- C++/Rust integration boundary:
  - [`cpp-bindings/classic-cpp-bridge/`](../../cpp-bindings/classic-cpp-bridge)

The pure-Python runtime and orchestration layer has been removed from the repo; its documentation is preserved under [`docs/archive/python-era/`](../archive/python-era).

---

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Frontends[Native Frontends (Active)]
        CLI[classic-cli/\nC++20 + CLI11/fmt]
        GUI[classic-gui/\nQt 6 + C++20]
    end

    subgraph Bridge[C++ ↔ Rust Bridge]
        CPPBRIDGE[classic-cpp-bridge\n(cxx + corrosion)]
    end

    subgraph Core[Rust Core Workspace (Active)]
        FOUNDATION[foundation/*\nshared runtime/utilities]
        BIZ[business-logic/*-core\npure Rust domain crates]
        BINDINGS[bindings/*\nnode-bindings + python-bindings]
    end

    subgraph Legacy[Deprecated Runtime Paths (Archival)]
        PYRT[removed\nlegacy Python entrypoints/orchestration]
    end

    CLI --> CPPBRIDGE
    GUI --> CPPBRIDGE
    CPPBRIDGE --> FOUNDATION
    CPPBRIDGE --> BIZ
    BIZ --> FOUNDATION
    BINDINGS --> BIZ
```

---

## Runtime Boundaries and Status

| Area                                             | Status                | Notes                                                                        |
| ------------------------------------------------ | --------------------- | ---------------------------------------------------------------------------- |
| `classic-cli/`                                   | Active                | Primary CLI runtime in C++                                                   |
| `classic-gui/`                                   | Active                | Primary desktop GUI runtime in Qt/C++                                        |
| `business-logic/`                  | Active                | Primary domain/business logic                                                |
| `cpp-bindings/classic-cpp-bridge/` | Active                | Native bridge consumed by C++ apps                                           |
| `node-bindings/`                   | Maintained            | Integration/API surface for Node                                             |
| `python-bindings/`                 | Maintained            | Integration/API surface for Python consumers                                 |
| Pure-Python entrypoints/orchestration            | Removed from repo     | Docs preserved under `docs/archive/python-era/`; no product work targets this |

---

## Rust Workspace Layers

1. **Foundation** — [`foundation/`](../../foundation)
   - Shared runtime/utilities (including single shared Tokio runtime facilities).

2. **Business logic** — [`business-logic/`](../../business-logic)
   - Pure Rust `*-core` crates.
   - Crash scan, config/yaml, file I/O, version registry, update system, and related services.

3. **Bindings** — [`cpp-bindings/`](../../cpp-bindings), [`node-bindings/`](../../node-bindings), [`python-bindings/`](../../python-bindings)
   - C++ bridge for native applications.
   - Node and Python maintained integration surfaces.

4. **UI applications (Rust workspace-local)** — [`ui-applications/`](../../ui-applications)
   - Rust UI/tooling crates where applicable.

---

## Build and Test Entry Points (Canonical)

### C++ frontends

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1

pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

### Rust core

```powershell
cargo build --workspace
cargo test --workspace
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

### Node bindings (when API/bindings change)

```powershell
# From node-bindings/classic-node
bun install
bun run build
bun run parity:gate:local
bun run test:bun
bun run test:node
```

### Python bindings (when API/bindings change)

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

## CI Workflow Mapping

- [`ci-cpp.yml`](../../.github/workflows/ci-cpp.yml): C++ CLI/GUI build + test pipeline for MSVC and clang-cl
- [`ci-rust.yml`](../../.github/workflows/ci-rust.yml): Rust format/lint/build/test
- [`ci-typescript.yml`](../../.github/workflows/ci-typescript.yml): Node parity and runtime tests
- [`ci-python-bindings.yml`](../../.github/workflows/ci-python-bindings.yml): Python parity and runtime smoke tests
- [`benchmarks.yml`](../../.github/workflows/benchmarks.yml): benchmark regression gates

---

## Transition/Deprecation Note

Historical docs that describe Python runtime entrypoints as first-class app architecture should be treated as legacy context. For active development, prioritize C++ frontends and Rust core, with Python scope limited to maintained bindings under [`python-bindings/`](../../python-bindings).

