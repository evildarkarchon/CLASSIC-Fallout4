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

CLASSIC is a repo-root Cargo workspace with C++ frontends and a Rust core.

- `classic-cli/` - C++20 CLI frontend.
- `classic-gui/` - Qt 6 C++20 desktop GUI.
- `foundation/` - shared runtime and utility crates such as `classic-shared-core`.
- `business-logic/` - domain crates, usually named `*-core`.
- `cpp-bindings/classic-cpp-bridge/` - C++ bridge into Rust.
- `node-bindings/classic-node/` - active Node.js and Bun binding surface.
- `python-bindings/` - active Python binding tree and binding-local tooling.
- `ui-applications/classic-tui/` - Rust TUI application crates.
- `deprecated/` - archived Python-era implementation; do not add new product features here unless the task explicitly targets migration or legacy maintenance.

Repo-root workspace layout:

1. `foundation/`
   - Shared runtime and utility crates such as `classic-shared-core`.
2. `business-logic/`
   - Domain crates, usually named `*-core`.
   - Crash scanning, YAML and config handling, file I/O, version registry, update logic, and related core behavior belong here.
3. `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/`
   - Language and platform bindings.
4. `ui-applications/classic-tui/`
   - Rust TUI application crates.

Placement guidance:

- Put new product behavior in Rust core when it should be shared across frontends or bindings.
- Keep `classic-cli/` and `classic-gui/` focused on frontend and integration concerns.
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

# Build plus selected tests
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -CTestName "ThreadPool executes all enqueued tasks"
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -IntegrationTestName help,version
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test -CTestName classic-gui-test-scan-settings-wiring

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

Policy: NEVER run C++ tests by invoking test binaries or raw `ctest` directly. Always run C++ tests through the PowerShell build wrappers.

```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -CTestName "ThreadPool executes all enqueued tasks"
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -IntegrationTestName help,version
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test -CTestName classic-gui-test-scan-settings-wiring
```

### Rust workspace

```powershell
cargo build --workspace
cargo build --workspace --release

cargo test --workspace
cargo test --workspace -- --nocapture
cargo test -p classic-scanlog-core

cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

### Node bindings

Run these from `node-bindings/classic-node`.

```powershell
bun install
bun run build
bun run cli -- --version
bun run parity:gate
bun run test:bun
bun run test:node
bun run dts:freshness:check
```

### Python bindings

```powershell
uv venv python-bindings/.venv
uv pip install --python python-bindings/.venv/Scripts/python.exe -r python-bindings/requirements-ci.txt
python tools/python_api_parity/check_parity_gate.py --repo-root .
python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry
uv run --python python-bindings/.venv/Scripts/python.exe python -m pytest python-bindings/tests -q
```

Use a bindings-local virtual environment at `python-bindings/.venv`; do not rely on a repo-root `.venv` for Python binding smoke tests.

## Repo Conventions and Constraints

- Maintain one shared Tokio runtime from the Rust core runtime facilities.
- Rust edition is 2024.
- Rust workspace policy denies `unsafe_code`.
- C++ standard is C++20.
- Native builds are MSVC-oriented and use vcpkg plus Corrosion.
- Keep top-level docs synchronized with architecture or workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` as a file path on Windows.

## Node API Parity Workflow

Use this when Rust APIs exposed through Node bindings change.

For the maintained binding-workflow narrative, pair this checklist with `docs/api/binding-contract-refresh-note.md` and `docs/api/node-python-contract-map.md`.

Trigger paths usually include:

- `business-logic/classic-scanlog-core/src/lib.rs`
- `business-logic/classic-config-core/src/lib.rs`
- `business-logic/classic-version-registry-core/src/lib.rs`
- `node-bindings/classic-node/src/`
- `node-bindings/classic-node/index.d.ts`

Required follow-up in the same change:

1. Update `docs/implementation/node_api_parity/baseline/parity_contract.json` when the tracked public Node surface intentionally changes.
2. Update `node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` when runtime coverage ownership changes.
3. Refresh and commit the affected artifacts, typically:
   - `node-bindings/classic-node/index.d.ts`
   - `node-bindings/classic-node/parity-artifacts/tier1_gate_report.md`
   - `node-bindings/classic-node/parity-artifacts/parity_diff_report.md`
   - `node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.md`
4. Run from `node-bindings/classic-node`:
   - `bun run parity:gate`
   - `bun run parity:gate:update-baseline` only when the plain gate shows intentional source-backed drift
   - `bun run parity:gate`
   - `bun run test:bun`
   - `bun run test:node`
   - `bun run dts:freshness:check`
5. Use `docs/workspace-migration-matrix.md` for old-to-new path translation instead of copying legacy path prose into this guide.
6. Make sure `ci-typescript.yml` parity jobs pass before merge.

Release gate:

- Do not tag a release unless the Tier-1 parity gate passes and the `index.d.ts` freshness gate passes in CI.

## Python API Parity Workflow

Use this when Rust APIs exposed through Python bindings change.

For the maintained binding-workflow narrative, pair this checklist with `docs/api/binding-contract-refresh-note.md` and `docs/api/node-python-contract-map.md`.

Trigger paths usually include:

- `business-logic/classic-scanlog-core/src/lib.rs`
- `business-logic/classic-config-core/src/lib.rs`
- `business-logic/classic-version-registry-core/src/lib.rs`
- `python-bindings/*-py/src/`
- `python-bindings/*-py/*.pyi`

Required follow-up in the same change:

1. Update `docs/implementation/python_api_parity/baseline/parity_contract.json` when the tracked public Python surface intentionally changes.
2. Update `python-bindings/tests/fixtures/runtime_coverage_registry.json` when runtime coverage ownership changes.
3. Refresh and commit the affected artifacts, typically:
   - `python-bindings/parity-artifacts/tier1_gate_report.md`
   - `python-bindings/parity-artifacts/parity_diff_report.md`
   - `python-bindings/parity-artifacts/runtime_coverage_summary.md`
   - `python-bindings/parity-artifacts/stub_validation_report.json`
   - the touched `python-bindings/*-py/*.pyi` files
4. Run:
   - `uv venv python-bindings/.venv`
   - `uv pip install --python python-bindings/.venv/Scripts/python.exe -r python-bindings/requirements-ci.txt`
   - `python tools/python_api_parity/check_parity_gate.py --repo-root .`
   - `python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings`
   - `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_shared classic_config classic_scanlog classic_version_registry`
   - `uv run --python python-bindings/.venv/Scripts/python.exe python -m pytest python-bindings/tests -q`
5. Use `docs/workspace-migration-matrix.md` for old-to-new path translation instead of copying legacy path prose into this guide.
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
