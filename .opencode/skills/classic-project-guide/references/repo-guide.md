# CLASSIC Repo Guide

Use this reference when a task needs repository-specific details that are too bulky for the always-on prompt.

## Table of Contents

1. Architecture Map
2. Build, Test, and Validation Commands
3. Repo Conventions and Constraints
4. Node API Parity Workflow
5. Python API Parity Workflow
6. CI and Platform Notes

## Architecture Map

CLASSIC is now a C++ plus Rust application.

- `classic-cli/` - C++20 CLI frontend.
- `classic-gui/` - Qt 6 C++20 desktop GUI.
- `ClassicLib-rs/` - Rust workspace for business logic and shared runtime facilities.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/` - C++ bridge into Rust.
- `ClassicLib-rs/node-bindings/` - active Node.js and Bun binding surface.
- `ClassicLib-rs/python-bindings/` - retained for legacy and deprecation support.
- `deprecated/` - archived Python-era implementation; do not add new product features here unless the task explicitly targets migration or legacy maintenance.

Rust workspace layout:

1. `ClassicLib-rs/foundation/`
   - Shared runtime and utility crates such as `classic-shared-core`.
2. `ClassicLib-rs/business-logic/`
   - Domain crates, usually named `*-core`.
   - Crash scanning, YAML and config handling, file I/O, version registry, update logic, and related core behavior belong here.
3. `ClassicLib-rs/cpp-bindings/`, `ClassicLib-rs/node-bindings/`, `ClassicLib-rs/python-bindings/`
   - Language and platform bindings.
4. `ClassicLib-rs/ui-applications/`
   - Rust TUI application crates.

Placement guidance:

- Keep all business logic in Rust core. Shared behavior, state transitions, data mutation, persistence rules, and validation belong in Rust unless the task is explicitly interface-only.
- Keep `classic-cli/` and `classic-gui/` focused on frontend and integration concerns.
- Keep C++, Python, Node, and other UI or binding layers thin wrappers over Rust APIs rather than reimplementing logic, unless the performance cost of FFI bridging is demonstrated to be too high for that specific path.
- Treat Python bindings as compatibility work, not the default place for new features.

## Build, Test, and Validation Commands

### Native C++ builds

Recommended wrappers auto-detect Visual Studio, initialize the VS developer shell, and run CMake plus Ninja.

```powershell
# Build CLI
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1

# Build GUI
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1

# Build plus tests
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test

# Clean rebuild
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean

# Install or package
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Install
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Package
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Install
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Package
```

Prerequisites:

- Visual Studio with the C++ Desktop workload.
- `VCPKG_ROOT` configured, for example `C:\vcpkg`.
- Ninja available in the VS developer shell.
- Qt 6 installed for GUI work; see `classic-gui/CMakePresets.json`.

### C++ tests

Policy: run C++ tests through CTest or the script wrappers, not by invoking test binaries directly.

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-cli/test_cli.ps1
```

### Rust workspace

```powershell
cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo build --workspace --release --manifest-path ClassicLib-rs/Cargo.toml

cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml -- --nocapture
cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml

cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings
```

### Node bindings

Run these from `ClassicLib-rs/node-bindings/classic-node`.

```powershell
bun install
bun run build
bun run cli -- --version
bun run parity:gate:local
bun run test:bun
bun run test:node
```

### Python bindings

```powershell
uv venv
uv pip install maturin pytest
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry classic_pybridge
uv run python -m pytest ClassicLib-rs/python-bindings/tests -q
```

## Repo Conventions and Constraints

- Keep business logic in Rust and treat non-interface layers as thin wrappers unless measured FFI overhead justifies local implementation.
- Maintain one shared Tokio runtime from the Rust core runtime facilities.
- Rust edition is 2024.
- Rust workspace policy denies `unsafe_code`.
- C++ standard is C++20.
- Native builds are MSVC-oriented and use vcpkg plus Corrosion.
- Keep top-level docs synchronized with architecture or workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` as a file path on Windows.

## Node API Parity Workflow

Use this when Rust APIs exposed through Node bindings change.

Trigger paths usually include:

- `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs`
- `ClassicLib-rs/node-bindings/classic-node/src/`
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts`

Required follow-up in the same change:

1. Classify affected APIs as Tier-1 or Tier-2 using `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md`.
2. If an API is promoted to Tier-1, update `docs/implementation/node_api_parity/baseline/parity_contract.json`.
3. Update `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` for new runtime-verified or deferred surfaces.
4. Refresh and commit:
   - `ClassicLib-rs/node-bindings/classic-node/index.d.ts`
   - `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json`
   - `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md`
   - `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json`
5. Run:
   - `bun run parity:gate:local`
   - `bun run test:bun`
   - `bun run test:node`
6. Make sure `ci-typescript.yml` parity jobs pass before merge.

Release gate:

- Do not tag a release unless the Tier-1 parity gate passes and the `index.d.ts` freshness gate passes in CI.

## Python API Parity Workflow

Use this when Rust APIs exposed through Python bindings change.

Trigger paths usually include:

- `ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs`
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs`
- `ClassicLib-rs/python-bindings/*-py/src/`
- `ClassicLib-rs/python-bindings/*-py/*.pyi`

Required follow-up in the same change:

1. Classify affected APIs as Tier-1 or Tier-2 using `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md`.
2. If an API is promoted to Tier-1, update `docs/implementation/python_api_parity/baseline/parity_contract.json`.
3. Update `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` for new runtime-verified or deferred surfaces.
4. Refresh and commit:
   - `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json`
   - `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md`
   - `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json`
   - `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json`
5. Run:
   - `python tools/python_api_parity/check_parity_gate.py --repo-root .`
   - `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings`
   - `uv run python -m pytest ClassicLib-rs/python-bindings/tests -q`
6. Make sure `ci-python-bindings.yml` jobs pass before merge.

## CI and Platform Notes

Primary CI workflows:

1. `ci-cpp.yml` - C++ CLI and GUI build plus test pipeline.
2. `ci-rust.yml` - Rust format, lint, build, and test pipeline.
3. `ci-typescript.yml` - Node binding parity and runtime tests.
4. `ci-python-bindings.yml` - Python binding parity and smoke tests.
5. `benchmarks.yml` - benchmark and performance pipeline.

Platform notes:

- `classic-cli` and `classic-gui` are Windows-focused and require MSVC.
- Some Rust crates depend on DirectX-related tooling via transitive `ba2` paths and may need subset builds on Linux.
- On Linux or cloud environments, prefer Rust-only crate subsets when the full workspace is not portable.
