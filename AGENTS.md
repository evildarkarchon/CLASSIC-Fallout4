# AGENTS.md

This file provides guidance to GitHub Copilot and other AI coding agents working in this repository.

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is now a **C++ + Rust** application:

- **CLI:** `classic-cli/` (C++20)
- **GUI:** `classic-gui/` (Qt 6, C++20)
- **Core/business logic:** `ClassicLib-rs/` (Rust workspace)
- **C++ bridge to Rust:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`

The prior Python implementation is deprecated and archived under `deprecated/`.

---

## Active Build & Development Commands

### C++ Build (recommended scripts)

> These scripts auto-detect Visual Studio, initialize VS Dev Shell, and run CMake/Ninja.

```powershell
# Build CLI
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1

# Build GUI (Qt 6)
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1

# Build + tests
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test

# Clean rebuild
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean

# Install/package artifacts
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Install
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Package
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Install
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Package
```

### C++ prerequisites

- Visual Studio with C++ Desktop workload (MSVC toolchain)
- `VCPKG_ROOT` set (example: `C:\vcpkg`)
- Ninja available in VS Dev Shell
- Qt 6 installed for GUI builds (see preset defaults in `classic-gui/CMakePresets.json`)

### Rust Build

```powershell
cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo build --workspace --release --manifest-path ClassicLib-rs/Cargo.toml
```

### Node Bindings (NAPI-RS)

```powershell
# From ClassicLib-rs/node-bindings/classic-node
bun install
bun run build
bun run cli -- --version
bun run parity:gate:local
bun run test:bun
bun run test:node
```

### Python Bindings (PyO3)

```powershell
uv venv
uv pip install maturin pytest
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry classic_pybridge
uv run python -m pytest ClassicLib-rs/python-bindings/tests -q
```

---

## Testing

### C++ tests (Catch2 via CTest)

Policy: run C++ tests through CTest (or script wrappers), not direct test binaries.

```powershell
# Recommended
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test

# CLI integration tests (requires built classic-cli.exe)
pwsh -ExecutionPolicy Bypass -File classic-cli/test_cli.ps1
```

### Rust tests

```powershell
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml -- --nocapture
cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml
```

### Rust lint/format

```powershell
cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings
```

---

## Architecture

### Rust workspace (`ClassicLib-rs/`)

1. **Foundation** (`ClassicLib-rs/foundation/`)
   - Shared runtime/utilities (e.g., `classic-shared-core`)

2. **Business Logic** (`ClassicLib-rs/business-logic/`)
   - Pure Rust domain crates (`*-core`)
   - Crash scan, YAML/config, file I/O, version registry, update system, etc.

3. **Bindings** (`ClassicLib-rs/cpp-bindings/`, `ClassicLib-rs/node-bindings/`, `ClassicLib-rs/python-bindings/`)
   - C++ bridge for native apps
   - Node.js/Bun bindings (active)
   - Python bindings retained for legacy/deprecation support only

4. **UI Applications** (`ClassicLib-rs/ui-applications/`)
   - Rust TUI crate(s)

### Native application frontends

- `classic-cli/`: C++ scanner executable using CLI11/fmt + Rust bridge
- `classic-gui/`: Qt 6 C++ desktop application + Rust bridge

### Deprecated Python codebase

- All legacy Python entry points and packages are under `deprecated/`.
- Do not add new product features to deprecated Python paths unless explicitly requested for migration support.
- Prefer implementing functionality in C++ frontends and/or Rust core crates.

---

## Key Conventions

### ONE RUNTIME RULE

Maintain a single shared Tokio runtime from Rust core/runtime facilities. Do not introduce additional independent runtimes.

### Rust standards

- Rust 2024 edition
- `unsafe_code = "deny"`
- Workspace lints deny deprecated/unused patterns

### C++ standards

- C++20
- MSVC on Windows (`/utf-8 /W4`)
- CMake 3.25+
- Ninja generator
- vcpkg dependencies
- Corrosion for Rust integration

### Windows-specific caution

- Never write to `NUL`/`nul` as if it were a file path.

---

## CI Pipeline

Current primary CI workflows:

1. **`ci-cpp.yml`** - C++ CLI/GUI build and test pipeline
2. **`ci-rust.yml`** - Rust format/lint/build/test
3. **`ci-typescript.yml`** - Node binding parity gates + Bun/Node runtime tests
4. **`ci-python-bindings.yml`** - Python binding parity gates + smoke tests
5. **`benchmarks.yml`** - benchmark/performance pipeline

The legacy Python CI workflow has been retired from the active pipeline as part of Python deprecation.

---

## Node API Parity Contributor Checklist

When changing Rust APIs that are exposed through Node bindings, parity updates are required in the same PR.

Trigger paths (minimum):

- `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs`
- `ClassicLib-rs/node-bindings/classic-node/src/`
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts`

Checklist:

1. Classify affected APIs as Tier-1 or Tier-2 using `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md`.
2. If promoting to Tier-1, update `docs/implementation/node_api_parity/baseline/parity_contract.json`.
3. Update `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` for any new runtime-verified or deferred coverage surface.
4. Refresh and commit:
   - `ClassicLib-rs/node-bindings/classic-node/index.d.ts`
   - `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json`
   - `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md`
   - `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json`
5. Run from `ClassicLib-rs/node-bindings/classic-node`:
   - `bun run parity:gate:local`
   - `bun run test:bun`
   - `bun run test:node`
6. Confirm `ci-typescript.yml` parity jobs pass before merge.

Release gate policy:

- Do not tag a release unless Tier-1 parity gate passes and `index.d.ts` freshness gate passes in CI.

---

## Python API Parity Contributor Checklist

When changing Rust APIs that are exposed through Python bindings, parity updates are required in the same PR.

Trigger paths (minimum):

- `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs`
- `ClassicLib-rs/python-bindings/*-py/src/`
- `ClassicLib-rs/python-bindings/*-py/*.pyi`

Checklist:

1. Classify affected APIs as Tier-1 or Tier-2 using `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md`.
2. If promoting to Tier-1, update `docs/implementation/python_api_parity/baseline/parity_contract.json`.
3. Update `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` for any new runtime-verified or deferred coverage surface.
4. Refresh and commit:
   - `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json`
   - `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md`
   - `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json`
   - `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json`
5. Run local gates:
   - `python tools/python_api_parity/check_parity_gate.py --repo-root .`
   - `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings`
   - `uv run python -m pytest ClassicLib-rs/python-bindings/tests -q`
6. Confirm `ci-python-bindings.yml` jobs pass before merge.

---

## Linux/Cloud Notes

- C++ targets (`classic-cli`, `classic-gui`) require MSVC and are Windows-focused.
- Some Rust crates depend on DirectX-related tooling via `ba2` transitive paths and may not build on Linux without exclusions.
- Rust-only CI/dev on Linux should build/test crate subsets when platform constraints apply.

---

## Agent Policy for This Repository

1. Prioritize C++ (`classic-cli/`, `classic-gui/`) and Rust (`ClassicLib-rs/`) for active work.
2. Treat `deprecated/` as archival unless a task explicitly targets migration or legacy maintenance.
3. Keep docs synchronized with architecture changes (especially top-level `README.md` and this file).
