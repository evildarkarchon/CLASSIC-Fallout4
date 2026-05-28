# CLASSIC Repo Guide

Use this reference when a task needs repository-specific details that are too bulky for the always-on prompt.

## Table of Contents

1. Architecture Map
2. Build, Test, and Validation Commands
3. Repo Conventions and Constraints
4. CXX API Parity Workflow
5. Node API Parity Workflow
6. Python API Parity Workflow
7. YAML Data Publish Workflow
8. App Update Notification Publish Workflow
9. CI and Platform Notes

## Architecture Map

CLASSIC is a repo-root Cargo workspace with native C++ frontends, a Rust core, thin binding layers, and repo-owned YAML data.

- `classic-cli/` - C++20 CLI frontend.
- `classic-gui/` - Qt 6 C++20 desktop GUI.
- `foundation/` - shared runtime and utility crates such as `classic-shared-core`.
- `business-logic/` - 16 active domain crates, usually named `*-core`.
- `cpp-bindings/classic-cpp-bridge/` - C++ bridge into Rust.
- `node-bindings/classic-node/` - active Node.js and Bun binding surface.
- `python-bindings/` - active Python binding tree, binding-local virtualenv, and tracked Python parity artifacts.
- `ui-applications/classic-tui/` - Rust TUI application crate.
- `CLASSIC Data/` - repo-owned runtime data, including shippable YAML databases under `CLASSIC Data/databases/` and app-update notification source `CLASSIC Data/app-notification.yaml`.
- `sample_logs/FO4/` - crash-log fixture corpus used by CLI integration-style tests.
- `ClassicLib-rs/` - historical residue only; do not treat it as the live workspace root.

Repo-root workspace shell:

- `Cargo.toml`, `Cargo.lock`, and `.cargo/config.toml` at repo root are the only live Cargo workspace shell.
- Use `docs/workspace-migration-matrix.md` when translating older `ClassicLib-rs/...` path or command guidance.

Placement guidance:

- Put new product behavior in Rust core when it should be shared across frontends or bindings.
- Keep `classic-cli/` and `classic-gui/` focused on frontend and integration concerns.
- Keep bindings thin: C++, Node, and Python should wrap Rust APIs rather than reimplementing logic.
- Treat Python as an active compatibility surface, not the default place for new product logic.
- Keep YAML/schema-version behavior in the Rust core crates that own the contract, then wire release and validation tooling around that behavior.

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
- For CLI integration-style tests, initialize fixture submodules first: `git submodule update --init --recursive`.

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

If a local build or test path touches PyO3 crates, set `PYO3_PYTHON` for the current PowerShell session first:

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
```

Run the main Rust workspace commands from the repo root:

```powershell
cargo build --workspace
cargo build --workspace --release

cargo test --workspace
cargo test --workspace -- --nocapture
cargo test -p classic-scanlog-core

cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

### CXX parity gate

Run these from the repo root.

```powershell
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline
```

The gate is source-only. It updates local diagnostics under `cpp-bindings/classic-cpp-bridge/parity-artifacts/` and compares or refreshes the committed baseline under `docs/implementation/cxx_api_parity/baseline/`.

### Node bindings

Run these from `node-bindings/classic-node`.

```powershell
bun install
bun run build
bun run cli -- --version

bun run parity:gate
bun run parity:gate:update-baseline
bun run parity:gate:ci
bun run parity:gate:local
bun run parity:gate:local:vsdev

bun run test:bun
bun run test:node
bun run dts:freshness:check
```

`parity:gate:ci` mirrors the CI verification pair (`parity:gate` plus `dts:freshness:check`). `parity:gate:local` refreshes the tracked Node baseline and `index.d.ts` together for intentional source-backed drift.

### Python bindings

Use a bindings-local virtual environment at `python-bindings/.venv`; do not rely on a repo-root `.venv` for Python binding smoke tests.

Before local PyO3-flavored cargo flows, set `PYO3_PYTHON` for the current shell:

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
```

Typical local workflow from the repo root:

```powershell
# `python-bindings/` is a uv-managed project (`pyproject.toml` + `uv.lock`).
# `uv sync` creates the venv at python-bindings/.venv and installs the
# locked tooling (maturin, pytest). `--inexact` is load-bearing: it stops
# uv from pruning the maturin-built `classic-*-py` wheels on re-sync.
# Add `--group drift-guards` when you need `ruamel.yaml` for schema_version_gate.py.
uv sync --project python-bindings --inexact --group drift-guards

uv run --project python-bindings python tools/python_api_parity/check_parity_gate.py --repo-root .
uv run --project python-bindings python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
uv run --project python-bindings python tools/schema_version_gate.py --repo-root .

pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
uv run --project python-bindings python -m pytest python-bindings/tests -q
```

Before `uv run --project python-bindings python -m pytest python-bindings/tests -q`, rebuild the Python bindings with `rebuild_rust.ps1 -Target python` so every `-py` crate is installed into `python-bindings/.venv/`. Use `python -m pytest`, not the `.venv\Scripts\pytest.exe` console-script entrypoint, because some tests anchor settings lookup to `sys.argv[0]`'s parent. You can pass crate filters only when deliberately narrowing a local iteration loop.

### YAML data validation and publish helpers

Run these from the repo root when changing `CLASSIC Data/databases/`, schema-version behavior, or YAML publish tooling.

```powershell
python tools/schema_version_gate.py --repo-root .
python tools/publish_yaml_data/validate.py --databases-dir "CLASSIC Data/databases" --schema-ranges "CLASSIC Data/databases/client-schema-ranges.yaml"
```

The maintainer publish workflow lives in `.github/workflows/publish-yaml-data.yml` and runs only for pushed `yaml-data-v*` tags.

### App-update notification validation and publish helpers

Run these from the repo root when changing `CLASSIC Data/app-notification.yaml`, app-notification publish tooling, or manifest delivery behavior.

```powershell
uv sync --project python-bindings --inexact --group drift-guards
uv run --project python-bindings python tools/publish_app_notification/validate.py --source "CLASSIC Data/app-notification.yaml"
uv run --project python-bindings python tools/publish_app_notification/generate_manifest.py --source "CLASSIC Data/app-notification.yaml" --output "$env:TEMP\classic-app-notification-manifest.json" --published-at "2026-05-23T00:00:00Z"
uv run --project python-bindings python -m pytest tools/publish_app_notification/tests -q
```

The generator command writes a disposable local preview; do not commit generated `manifest.json` or `gh-pages` outputs. The `uv` commands use the bindings-local tool environment so `ruamel.yaml` and pytest are available without relying on whatever `python` happens to resolve in the shell.

The maintainer publish workflow lives in `.github/workflows/publish-app-notification.yml` and runs only for pushed `app-notification-v*` tags. This channel is disjoint from `yaml-data-v*` data publishes and binary `v*` releases.

## Repo Conventions and Constraints

- Maintain one shared Tokio runtime from the Rust core runtime facilities.
- Rust edition is 2024.
- Rust workspace policy denies `unsafe_code`.
- C++ standard is C++20.
- Native builds are MSVC-oriented and use vcpkg plus Corrosion.
- Keep top-level docs synchronized with architecture or workflow changes, especially `README.md` and `AGENTS.md`.
- Keep live guidance on repo-root paths. Use `docs/workspace-migration-matrix.md` for older `ClassicLib-rs/...` docs instead of restating the migration ad hoc.
- Before local cargo commands that touch PyO3, set `PYO3_PYTHON` per shell. `.cargo/config.toml` intentionally omits a global pin so Windows-only venv paths do not leak into Linux or macOS builds. If PyO3 still reports a missing Python after setting it, check for a stale global `VIRTUAL_ENV` pointing at a removed or moved interpreter.
- Use `python-bindings/.venv` for Python binding build and test workflows, and run pytest through `uv run --project python-bindings python -m pytest ...` rather than the `.venv\Scripts\pytest.exe` console-script entrypoint.
- Rust unit tests live in sibling `*_tests.rs` files declared with `#[cfg(test)] #[path = "<name>_tests.rs"] mod tests;`, not inline `#[cfg(test)] mod tests { ... }` blocks. Full contract: `openspec/specs/rust-test-module-layout/spec.md`.
- Never write to `NUL` or `nul` as a file path on Windows.

## CXX API Parity Workflow

Use this when `cpp-bindings/classic-cpp-bridge/` changes or a public Rust API change alters the `#[cxx::bridge]` contract.

Trigger paths usually include:

- `cpp-bindings/classic-cpp-bridge/src/`
- `cpp-bindings/classic-cpp-bridge/build.rs`
- public Rust `lib.rs` entrypoints in `foundation/` or `business-logic/` crates that the bridge exposes

Required follow-up in the same change:

1. Run `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`.
2. If the drift is intentional, refresh the committed baseline with `python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline`.
3. Review and stage the committed baseline under `docs/implementation/cxx_api_parity/baseline/`.
4. Do not commit `cpp-bindings/classic-cpp-bridge/parity-artifacts/`; they are local diagnostics only.
5. Run the relevant `classic-cli/build_cli.ps1 -Test` and/or `classic-gui/build_gui.ps1 -Test` flows if bridge consumers changed.
6. Make sure `ci-cpp.yml` passes before merge.

Reference: `docs/api/cxx-parity-gate.md`.

## Node API Parity Workflow

Use this when Rust APIs exposed through Node bindings change.

Pair this checklist with `docs/api/binding-contract-refresh-note.md`, `docs/api/node-python-contract-map.md`, and `docs/api/binding-parity-policy.md`.

Trigger paths usually include:

- `business-logic/*/src/lib.rs` or `foundation/*/src/lib.rs` for Node-exposed public APIs
- `node-bindings/classic-node/src/`
- `node-bindings/classic-node/index.d.ts`
- `node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json`

Required follow-up in the same change:

1. Update `docs/implementation/node_api_parity/baseline/parity_contract.json` when the tracked public Node surface intentionally changes.
2. Update `node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` when runtime coverage ownership changes.
3. Refresh and commit the checked-in baseline reports under `docs/implementation/node_api_parity/baseline/` when gate-backed results legitimately change.
4. Refresh and commit `node-bindings/classic-node/index.d.ts` when the public Node export surface changes.
5. Run from `node-bindings/classic-node`:
   - `bun run parity:gate`
   - `bun run parity:gate:update-baseline` only when the plain gate shows intentional source-backed drift
   - `bun run parity:gate`
   - `bun run test:bun`
   - `bun run test:node`
   - `bun run dts:freshness:check`
6. Do not commit `node-bindings/classic-node/parity-artifacts/` or `index.js`; they are generated local diagnostics or gitignored outputs.
7. Use `docs/workspace-migration-matrix.md` for old-to-new path translation instead of copying legacy path prose into this guide.
8. Make sure `ci-typescript.yml` passes before merge.

Release gate:

- Do not tag a release unless the Tier-1 Node parity gate and the `index.d.ts` freshness gate pass in CI.

## Python API Parity Workflow

Use this when Rust APIs exposed through Python bindings change.

Pair this checklist with `docs/api/binding-contract-refresh-note.md`, `docs/api/node-python-contract-map.md`, and `docs/api/binding-parity-policy.md`.

Trigger paths usually include:

- `business-logic/*/src/lib.rs` or `foundation/*/src/lib.rs` for Python-exposed public APIs
- `python-bindings/*-py/src/`
- `python-bindings/*-py/*.pyi`
- `python-bindings/tests/fixtures/runtime_coverage_registry.json`

Required follow-up in the same change:

1. Update `docs/implementation/python_api_parity/baseline/parity_contract.json` when the tracked public Python surface intentionally changes.
2. Update `python-bindings/tests/fixtures/runtime_coverage_registry.json` when runtime coverage ownership changes.
3. Refresh and commit the touched `python-bindings/*-py/*.pyi` files when the public Python surface changes.
4. Refresh and commit the tracked outputs under `python-bindings/parity-artifacts/` and any affected checked-in baseline reports under `docs/implementation/python_api_parity/baseline/` when generated results legitimately change.
5. Run:
   - `uv sync --project python-bindings --inexact --group drift-guards` (creates/refreshes `python-bindings/.venv` from the locked tooling set; `--inexact` preserves the maturin-built `classic-*-py` wheels)
   - `$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"`
   - `uv run --project python-bindings python tools/python_api_parity/check_parity_gate.py --repo-root .`
   - `uv run --project python-bindings python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings`
   - `uv run --project python-bindings python tools/schema_version_gate.py --repo-root .` when the change touches shippable YAML data or schema-version constants
   - `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python`
   - `uv run --project python-bindings python -m pytest python-bindings/tests -q`
6. Use `docs/workspace-migration-matrix.md` for old-to-new path translation instead of copying legacy path prose into this guide.
7. Make sure `ci-python-bindings.yml` passes before merge.

## YAML Data Publish Workflow

Use this when changing shippable YAML data, schema-version rules, or YAML-data release tooling.

Trigger paths usually include:

- `CLASSIC Data/databases/*.yaml`
- `CLASSIC Data/databases/client-schema-ranges.yaml`
- `tools/schema_version_gate.py`
- `tools/publish_yaml_data/*`
- `.github/workflows/publish-yaml-data.yml`

Required follow-up in the same change:

1. Run `python tools/schema_version_gate.py --repo-root .` to verify checked-in YAML `schema_version` headers still match the Rust-side acceptance contract.
2. Run `python tools/publish_yaml_data/validate.py --databases-dir "CLASSIC Data/databases" --schema-ranges "CLASSIC Data/databases/client-schema-ranges.yaml"`.
3. If loader, manifest, or delivery behavior changes, update `docs/api/yaml-update-delivery.md` and any affected crate API docs in `docs/api/`.
4. Remember `publish-yaml-data.yml` is maintainer-triggered only on pushed `yaml-data-v*` tags; PRs do not publish YAML data.
5. Account for the workflow's downstream effects: GitHub release assets are validated before publish, then Pages manifests are pushed under `gh-pages` `yaml-data/` entries. The YAML-data and app-notification workflows intentionally share the `publish-gh-pages-${{ github.repository }}` concurrency group because both mutate the same Pages branch.

## App Update Notification Publish Workflow

Use this when changing the payload-free app-update notification source, manifest contract, publish tooling, or delivery workflow.

Trigger paths usually include:

- `CLASSIC Data/app-notification.yaml`
- `tools/publish_app_notification/*`
- `.github/workflows/publish-app-notification.yml`
- `tools/publish_yaml_data/smoke_test_pages.py` when changing behavior reused by the notification channel
- `docs/api/app-update-notification-delivery.md`
- notification-facing public APIs documented under `docs/api/`, especially `classic-update-core.md`, `classic-path-core.md`, and `error-contract.md`

Required follow-up in the same change:

1. Run `uv sync --project python-bindings --inexact --group drift-guards`, then `uv run --project python-bindings python tools/publish_app_notification/validate.py --source "CLASSIC Data/app-notification.yaml"`.
2. If publish tooling changes, also run `uv run --project python-bindings python -m pytest tools/publish_app_notification/tests -q` and generate a disposable manifest preview with `uv run --project python-bindings python tools/publish_app_notification/generate_manifest.py`.
3. If manifest fields, validation rules, cache/fallback behavior, or delivery sequencing changes, update `docs/api/app-update-notification-delivery.md` and any affected crate API docs under `docs/api/`.
4. Do not commit generated `manifest.json` previews or `gh-pages` publish outputs; the workflow owns those artifacts.
5. Preserve tag namespace separation: `app-notification-v*` wakes the notification publish workflow, which validates the stricter `app-notification-v<SEMVER>` shape before publishing; `yaml-data-v*` triggers YAML-data publishes, and binary `v*` releases remain the advertised install target. In `CLASSIC Data/app-notification.yaml`, `release_tag` is the binary `v*` tag being advertised, not the `app-notification-v*` workflow tag. The notification and YAML-data workflows intentionally share the `publish-gh-pages-${{ github.repository }}` concurrency group because both mutate the same Pages branch.
6. Preserve `--latest=false` on app-notification GitHub release operations so the repository's "latest" pointer stays on the newest binary `v*` release.
7. Remember `publish-app-notification.yml` is maintainer-triggered only on pushed `app-notification-v*` tags and rejects non-SemVer suffixes; PRs do not publish app notifications.

Reference: `docs/api/app-update-notification-delivery.md`.

## CI and Platform Notes

Primary CI workflows:

1. `ci-cpp.yml` - C++ bridge parity plus CLI and GUI build/test pipeline.
2. `ci-rust.yml` - Rust format, lint, build, and test pipeline.
3. `ci-typescript.yml` - Node binding parity and runtime tests.
4. `ci-python-bindings.yml` - Python binding parity, stub validation, schema drift guard, rebuild, and smoke tests.
5. `publish-yaml-data.yml` - maintainer YAML-data release workflow for `yaml-data-v*` tags.
6. `publish-app-notification.yml` - maintainer app-update notification workflow for `app-notification-v*` tags.
7. `benchmarks.yml` - benchmark and performance pipeline.

Platform notes:

- `classic-cli` and `classic-gui` are Windows-focused and require MSVC.
- `node-bindings/classic-node` currently targets `x86_64-pc-windows-msvc`.
- CLI integration tests need `sample_logs/FO4` checked out from submodules.
- The CXX parity gate, YAML publish validation helpers, and app-notification publish validation helpers are source-only and do not require MSVC.
- Some Rust crates depend on DirectX-related tooling via transitive `ba2` paths and may need subset builds on Linux.
- On Linux or cloud environments, prefer Rust-only crate subsets plus source-only parity gates when the full workspace is not portable.
