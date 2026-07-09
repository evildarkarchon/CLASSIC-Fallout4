# CLASSIC Project Guide

This file supplements `AGENTS.md`. Keep always-on architecture rules there; keep exact commands, artifact ownership, publish preflights, and CI/platform details here.

## Command Picker

| Touched surface | Local checks to consider | Artifacts or docs to consider |
| --- | --- | --- |
| Rust-only crates | `cargo fmt`, `cargo clippy`, focused `cargo test`; set `PYO3_PYTHON` first if PyO3 can build | Affected `docs/api/` pages for public contracts |
| `classic-cli/` or `classic-gui/` | PowerShell wrappers in `Native C++ Wrappers` | Packaging/install output only when requested; CLI integration fixtures may require submodules |
| `cpp-bindings/classic-cpp-bridge/` or Rust APIs exposed through C++ | CXX parity gate, then CLI/GUI wrapper tests for changed consumers | `docs/implementation/cxx_api_parity/baseline/`; `docs/api/cxx-parity-gate.md` |
| `node-bindings/classic-node/` or Rust APIs exposed through Node | Node parity gate, declaration freshness, Bun and Node tests | `index.d.ts`, Node runtime coverage registry, `docs/implementation/node_api_parity/baseline/` |
| `python-bindings/` or Rust APIs exposed through Python | Python parity gate, stub validation, rebuild, pytest | `.pyi` files, Python runtime coverage registry, `python-bindings/parity-artifacts/`, `docs/implementation/python_api_parity/baseline/` |
| `CLASSIC Data/databases/` or schema-version behavior | Schema drift guard and YAML publish validator | `docs/api/yaml-update-delivery.md` for loader, manifest, or delivery contract changes |
| `CLASSIC Data/app-notification.yaml` or notification publish tooling | Notification source validator, dry-run harness, publish-tool tests | `docs/api/app-update-notification-delivery.md` and affected update/path/error API docs |
| Linux or cloud validation | Rust-only subsets and source-only gates first | Note any skipped Windows/MSVC-native checks explicitly |

## Native C++ Wrappers

Run from the repo root. The wrappers initialize the Visual Studio developer shell, configure CMake/Ninja, and support `-Compiler clang-cl` while keeping the MSVC ABI. `-Package` implies `-Install` for both wrappers.

```powershell
# Build
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Compiler clang-cl
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Compiler clang-cl

# Build plus all tests
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test

# Selected tests. CLI supports both CTest and integration scenario filters; GUI supports CTest filters only.
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -CTestName "ThreadPool executes all enqueued tasks"
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -IntegrationTestName help,version
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test -CTestName classic-gui-test-scan-settings-wiring

# Clean rebuild, install, or package
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Install
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Install
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Package
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Package
```

CLI integration scenarios use the crash-log fixture corpus under `sample_logs/FO4`; initialize it with `git submodule update --init --recursive` when that directory is missing.

## Rust And PyO3 Commands

Before cargo commands that can build PyO3 crates, point PyO3 at the binding-local interpreter:

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
```

Common workspace checks:

```powershell
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
cargo test -p classic-scanlog-core
cargo build --workspace
cargo build --workspace --release
```

Create or refresh the Python binding tool environment before Python binding smoke tests:

```powershell
uv sync --project python-bindings --inexact
uv sync --project python-bindings --inexact --group drift-guards
```

Use the `--group drift-guards` form when the schema drift guard or YAML publish tooling needs `ruamel.yaml`.

## Binding Parity Workflows

### CXX

Use this when bridge source, `cpp-bindings/classic-cpp-bridge/build.rs`, or a Rust public API exposed through the bridge changes.

```powershell
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline
```

Only run `--update-baseline` for intentional source-backed drift. Commit the refreshed files under `docs/implementation/cxx_api_parity/baseline/`; leave `cpp-bindings/classic-cpp-bridge/parity-artifacts/` as local diagnostics. The gate is source-only. For changed consumers, add the relevant CLI or GUI wrapper test command from `Native C++ Wrappers`.

### Node

Run from `node-bindings/classic-node`.

```powershell
bun install
bun run parity:gate
bun run parity:gate:local
bun run test:bun
bun run test:node
bun run dts:freshness:check
bun run cli -- --version
```

Use `parity:gate:local` only for intentional source-backed drift; it refreshes `index.d.ts`, updates the tracked Node baseline, and verifies declaration freshness. Commit affected files under `docs/implementation/node_api_parity/baseline/`, `node-bindings/classic-node/index.d.ts`, and `node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` when ownership changes. Do not commit `node-bindings/classic-node/parity-artifacts/` or generated `index.js`.

### Python

Run from the repo root.

```powershell
uv sync --project python-bindings --inexact
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"

uv run --project python-bindings python tools/python_api_parity/check_parity_gate.py --repo-root .
uv run --project python-bindings python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
uv run --project python-bindings python -m pytest python-bindings/tests -q
```

When the same change touches shippable YAML data or schema-version constants, start with:

```powershell
uv sync --project python-bindings --inexact --group drift-guards
uv run --project python-bindings python tools/schema_version_gate.py --repo-root .
```

Commit touched `.pyi` files, runtime coverage registry changes under `python-bindings/tests/fixtures/`, tracked reports under `python-bindings/parity-artifacts/`, and affected files under `docs/implementation/python_api_parity/baseline/` when generated results legitimately change.

## Data Publish Workflows

### YAML Data

Use this for shippable YAML databases, client schema ranges, schema-version rules, or YAML publish tooling.

```powershell
uv sync --project python-bindings --inexact --group drift-guards
uv run --project python-bindings python tools/schema_version_gate.py --repo-root .
uv run --project python-bindings python tools/publish_yaml_data/validate.py --databases-dir "CLASSIC Data/databases" --schema-ranges "CLASSIC Data/databases/client-schema-ranges.yaml"
```

Update `docs/api/yaml-update-delivery.md` when loader, manifest, cache, fallback, or delivery behavior changes. The maintainer publish workflow is `.github/workflows/publish-yaml-data.yml` and runs only for pushed `yaml-data-v*` tags.

### App Update Notification

Use this for `CLASSIC Data/app-notification.yaml`, notification manifest semantics, or app-notification publish tooling.

```powershell
uv sync --project python-bindings --inexact --group drift-guards
uv run --project python-bindings python tools/publish_app_notification/validate.py --source "CLASSIC Data/app-notification.yaml"
$publishedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
uv run --project python-bindings python tools/publish_app_notification/generate_manifest.py --source "CLASSIC Data/app-notification.yaml" --output "$env:TEMP\classic-app-notification-manifest.json" --published-at $publishedAt
uv run --project python-bindings python tools/publish_app_notification/dry_run.py --workflow-tag app-notification-v9.2.0 --published-at $publishedAt
uv run --project python-bindings python -m pytest tools/publish_app_notification/tests -q
```

Do not commit generated manifest previews or local `gh-pages` output. The maintainer publish workflow is `.github/workflows/publish-app-notification.yml` and runs only for pushed `app-notification-v*` tags. In `CLASSIC Data/app-notification.yaml`, `release_tag` is the advertised binary `v*` release, not the `app-notification-v*` workflow tag. Preserve `--latest=false` on notification release operations so GitHub's latest release pointer stays on binary releases.

## CI And Platform Notes

Primary workflows:

| Workflow | Purpose |
| --- | --- |
| `ci-cpp.yml` | CXX parity plus CLI and GUI build/test pipeline |
| `ci-rust.yml` | Rust format, lint, build, and test pipeline |
| `ci-typescript.yml` | Node parity, declaration freshness, and runtime tests |
| `ci-python-bindings.yml` | Python parity, stub validation, schema drift guard, rebuild, and smoke tests |
| `benchmarks.yml` | Benchmark and performance pipeline |
| `publish-yaml-data.yml` | Maintainer YAML-data release workflow for `yaml-data-v*` tags |
| `publish-app-notification.yml` | Maintainer app-update notification workflow for `app-notification-v*` tags |

Platform constraints worth remembering:

- `classic-cli/` and `classic-gui/` are Windows-focused native surfaces and require an MSVC-compatible toolchain.
- `node-bindings/classic-node` currently targets `x86_64-pc-windows-msvc`.
- The CXX parity gate, YAML publish validator, and app-notification validator are source-only and do not require MSVC.
- Some Rust workspace paths pull Windows-oriented dependencies through archive/DirectX-related crates; on Linux or generic cloud runners, prefer focused Rust subsets plus source-only gates unless full portability is the point of the task.
