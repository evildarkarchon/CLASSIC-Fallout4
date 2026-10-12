# CLASSIC Project Guide

This file supplements `AGENTS.md`. Keep always-on architecture rules there; keep exact commands, artifact ownership, publish preflights, and CI/platform details here.

## Command Picker

| Touched surface | Local checks to consider | Artifacts or docs to consider |
| --- | --- | --- |
| Rust-only crates | `cargo fmt`, `cargo clippy`, focused `cargo test` | Affected `docs/api/` pages for public contracts |
| `classic-cli/` or `classic-gui/` | PowerShell wrappers in `Native C++ Wrappers` | Packaging/install output only when requested; CLI integration fixtures may require submodules |
| `cpp-bindings/classic-cpp-bridge/` or Rust APIs exposed through C++ | `cargo xtask cxx-bridge-gate`, then CLI/GUI wrapper tests for changed consumers | `docs/api/cxx-bridge-policy.md`; `tests/conformance/participants.json` when the change alters which conformance families CXX runs |
| `tests/conformance/` packs or catalogs, or CI conformance steps | `cargo xtask conformance check`, then `cargo xtask conformance run` for the affected participants | `docs/development/conformance.md`, `docs/development/repository-gates.md` |
| `CLASSIC Data/databases/` or schema-version behavior | `classic-config-core` schema-version test and YAML publish validator | `docs/api/yaml-update-delivery.md` for loader, manifest, or delivery contract changes |
| `CLASSIC Data/app-notification.yaml` or notification publish tooling | Notification source validator, dry-run harness, publish-tool tests | `docs/api/app-update-notification-delivery.md` and affected update/path/error API docs |
| Linux or cloud validation | Rust-only subsets and source-only gates first | Note any skipped Windows/MSVC-native checks explicitly |

## Native C++ Wrappers

Run from the repo root. The wrappers initialize the Visual Studio developer shell, configure CMake/Ninja, and support `-Compiler clang-cl` while keeping the MSVC ABI. `-Package` implies `-Install` for both wrappers.

The two wrappers do **not** take the same parameters. Check this table before composing a command; passing a parameter the other wrapper lacks fails with "parameter cannot be found".

| Parameter | `build_cli.ps1` | `build_gui.ps1` |
| --- | --- | --- |
| `-Clean`, `-Test`, `-Debug`, `-Install`, `-Package`, `-Compiler` | yes | yes |
| `-TestOnly` | yes | yes |
| `-CTestName`, `-CTestArgs` | yes | yes |
| `-IntegrationTestName` | yes | **no** |
| `-Preset`, `-TestTimeoutSec` | **no** | yes |

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

# Reuse a completed build in the same checkout for a separate CI receipt test.
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -TestOnly -CTestName classic-cxx-conformance
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test -TestOnly -CTestName classic-gui-consumer-conformance

# Clean rebuild, install, or package
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Install
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Install
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Package
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Package
```

`-TestOnly` verifies the completed build marker's compiler, preset, and Git
revision before running the wrapper's selected tests; it skips configure/build.
Run a normal build/test through the matching wrapper first. Native CI fetches
the pinned Corrosion source once for its compiler jobs and reuses that source
for their initial CMake configure; ordinary local builds retain FetchContent.

CLI integration scenarios use the crash-log fixture corpus under `sample_logs/FO4`; initialize it with `git submodule update --init --recursive` when that directory is missing.

## Rust Commands

Common workspace checks:

```powershell
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
cargo test -p classic-scanlog-core
cargo build --workspace
cargo build --workspace --release
```

Repository tooling is the `cargo xtask` crate (`cargo xtask --help`); its tests run with `cargo test -p xtask`.

## Conformance And Bridge Workflows

The conformance engine is `cargo xtask conformance` (`docs/development/conformance.md`).
`run` executes every family that requires one participant and writes each
family's plan, receipt, attempt and report under `--artifact-root` (default
`target/conformance`); `verdict` certifies the repository only over a directory
holding every required participant and execution instance:

```powershell
cargo xtask conformance check
cargo xtask conformance run --participant rust [--family <family>]
cargo xtask conformance run --participant tui
# cxx, cli and gui reuse a completed wrapper build of the same commit (-Test -TestOnly)
cargo xtask conformance run --participant cxx --compiler msvc
cargo xtask conformance run --participant cli --compiler clang-cl
cargo xtask conformance run --participant gui --compiler msvc [--preset <preset>]
cargo xtask conformance verdict --receipts target/conformance --output target/conformance-verdict.json
```

Use a fresh `--artifact-root` per run of an execution instance: two runs of one
instance under one directory are duplicate evidence to the verdict. Missing or
stale receipts fail the verdict; one participant's run cannot certify the
repository. `tests/conformance/participants.json` declares which families CXX
runs, and `tests/conformance/consumer-obligations.json` registers the CLI, GUI
and TUI consumers. The checks CI runs as direct steps are listed in
`docs/development/repository-gates.md`. The command below is a focused source
diagnostic; it does not grant runtime proof.

### CXX

Use this when bridge source, `cpp-bindings/classic-cpp-bridge/build.rs`, or a Rust public API exposed through the bridge changes.

```powershell
cargo xtask cxx-bridge-gate
```

The gate fails on any bridge export that no `classic-cli/src` or `classic-gui/src` production code calls; there is no baseline to refresh. It is source-only and runs in CI as the blocking `cxx-bridge-gate` job in `ci-cpp.yml`. Add an export in the same change as its first production call site and remove it with its last (`docs/api/cxx-bridge-policy.md`). For changed consumers, add the relevant CLI or GUI wrapper test command from `Native C++ Wrappers`.

## Data Publish Workflows

### YAML Data

Use this for shippable YAML databases, client schema ranges, schema-version rules, or YAML publish tooling.

```powershell
cargo test -p classic-config-core --lib client_schema
cargo xtask yaml-data validate --databases-dir "CLASSIC Data/databases" --schema-ranges "CLASSIC Data/databases/client-schema-ranges.yaml"
cargo test -p xtask
```

Update `docs/api/yaml-update-delivery.md` when loader, manifest, cache, fallback, or delivery behavior changes. The maintainer publish workflow is `.github/workflows/publish-yaml-data.yml` and runs only for pushed `yaml-data-v*` tags; its steps run `cargo xtask yaml-data validate | manifest | verify-assets | smoke-pages`. The blocking `xtask-linux` job in `ci-rust.yml` runs the same validation on every pull request.

### App Update Notification

Use this for `CLASSIC Data/app-notification.yaml`, notification manifest semantics, or app-notification publish tooling.

```powershell
cargo xtask app-notification validate --source "CLASSIC Data/app-notification.yaml"
$publishedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
cargo xtask app-notification manifest --source "CLASSIC Data/app-notification.yaml" --output "$env:TEMP\classic-app-notification-manifest.json" --published-at $publishedAt
cargo xtask app-notification dry-run --workflow-tag app-notification-v<VERSION> --published-at $publishedAt
cargo test -p xtask --test app_notification
```

Do not commit generated manifest previews or local `gh-pages` output. The maintainer publish workflow is `.github/workflows/publish-app-notification.yml` and runs only for pushed `app-notification-v*` tags; its steps run `cargo xtask app-notification validate | manifest | verify-asset | smoke-pages`. The blocking `xtask-linux` job in `ci-rust.yml` validates the source and runs `cargo xtask app-notification dry-run` on every pull request. In `CLASSIC Data/app-notification.yaml`, `release_tag` is the advertised binary `v*` release, not the `app-notification-v*` workflow tag. Preserve `--latest=false` on notification release operations so GitHub's latest release pointer stays on binary releases.

## CI And Platform Notes

Primary workflows:

| Workflow | Purpose |
| --- | --- |
| `ci-binding-compliance.yml` | Blocking umbrella: same-revision reusable `rust` and `native` participant workflows, then `cargo xtask conformance verdict` over every uploaded conformance artifact |
| `ci-cpp.yml` | CXX bridge gate (orphan exports) plus CLI and GUI build/test pipeline, with the `cxx`, `cli` and `gui` conformance runs on both compilers |
| `ci-rust.yml` | Rust format, lint (plus the `cargo xtask user-settings-ownership` gate and the `cargo xtask conformance check` gate), build, and test pipeline, with the `rust` and `tui` conformance runs |
| `benchmarks.yml` | Benchmark and performance pipeline |
| `publish-yaml-data.yml` | Maintainer YAML-data release workflow for `yaml-data-v*` tags |
| `publish-app-notification.yml` | Maintainer app-update notification workflow for `app-notification-v*` tags |

Platform constraints worth remembering:

- `classic-cli/` and `classic-gui/` are Windows-focused native surfaces and require an MSVC-compatible toolchain.
- The CXX bridge gate (`cargo xtask cxx-bridge-gate`), YAML publish validator, and app-notification validator are source-only and do not require MSVC.
- Some Rust workspace paths pull Windows-oriented dependencies through archive/DirectX-related crates; on Linux or generic cloud runners, prefer focused Rust subsets plus source-only gates unless full portability is the point of the task.
