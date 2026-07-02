# Crash Log Scan Run Policy Deepening Brief

This brief captures the accepted design from the architecture review and grilling session for the `Scan Run Policy` candidate. Use it as an implementation brief for a fresh agent session.

Canonical domain language is in [`CONTEXT.md`](../../CONTEXT.md). ADR-0002, [`Rust owns Crash Log Scan Run behavior`](../adr/0002-rust-owns-crash-log-scan-run.md), is the key decision to preserve: adapters select Crash Logs and present results, while Rust owns execution, Autoscan Report writing, progress/cancellation semantics, failed-log accounting, and Unsolved Logs decisions.

## Target

Deepen the `classic-scanlog-core` Crash Log Scan Run module so callers cross one Rust seam with scan intent instead of constructing Standard/Targeted run policy and Unsolved Logs movement details themselves.

Primary files likely affected:

- `business-logic/classic-scanlog-core/src/scan_intake.rs`
- `business-logic/classic-scanlog-core/src/scan_intake_tests.rs`
- `business-logic/classic-scanlog-core/src/scan_run.rs`
- `business-logic/classic-scanlog-core/src/scan_run_tests.rs`
- `business-logic/classic-scanlog-core/src/lib.rs`
- `cpp-bindings/classic-cpp-bridge/src/scanner.rs`
- `cpp-bindings/classic-cpp-bridge/src/scanner/orchestrator.rs`
- `cpp-bindings/classic-cpp-bridge/src/scanner/orchestrator_tests.rs`
- `classic-cli/src/cli_args.h`
- `classic-cli/src/cli_args.cpp`
- `classic-cli/src/scanner.cpp`
- `classic-cli/tests/test_cli_args.cpp`
- `classic-gui/src/app/settingsdialog.h`
- `classic-gui/src/app/settingsdialog.cpp`
- `classic-gui/src/app/mainwindow.h`
- `classic-gui/src/app/mainwindow.cpp`
- `classic-gui/src/controllers/scancontroller.h`
- `classic-gui/src/controllers/scancontroller.cpp`
- `classic-gui/src/workers/scanworker.h`
- `classic-gui/src/workers/scanworker.cpp`
- `classic-gui/tests/test_scan_settings_wiring.cpp`
- `ui-applications/classic-tui/src/app.rs`
- `ui-applications/classic-tui/src/state.rs`
- `business-logic/classic-config-core/src/config.rs`
- `CLASSIC Data/databases/CLASSIC Main.yaml`
- root `CLASSIC Settings.yaml` if it is tracked and intended as the repo sample settings file
- `node-bindings/classic-node/src/scanlog.rs`
- `node-bindings/classic-node/index.d.ts`
- `node-bindings/classic-node/__test__/scanlog.spec.ts`
- `python-bindings/classic-scanlog-py/src/orchestrator.rs`
- `python-bindings/classic-scanlog-py/classic_scanlog.pyi`
- `python-bindings/tests/test_promoted_scanlog_wave3a_smoke.py`
- `docs/api/` pages
- parity artifacts or baselines when binding-visible shapes change

## Accepted Decisions

- Adapters pass scan intent; Rust derives Standard versus Targeted behavior and Unsolved Logs policy behind the `scan_run` seam.
- `ScanReadyAnalysis` becomes intake-owned. Tests and external callers should stop assembling readiness internals field-by-field.
- `ScanReadyAnalysis` carries the path roots needed by `scan_run` to derive the canonical Unsolved Logs Destination.
- The public Rust `scan_run` interface should replace the current `CrashLogScanRunMode` / `StandardCrashLogScanRunOptions` / `UnsolvedLogsPolicy` caller surface.
- The invalid state "Targeted Crash Log Scan Run with Unsolved Logs relocation" should be unrepresentable at the Rust interface.
- Binding adapters may keep their current boolean inputs for compatibility, but must map them into the smaller Rust interface.
- At adapter seams, `targeted_mode = true` wins over `move_unsolved_logs = true` and any supplied custom destination. Targeted runs never move Unsolved Logs.
- `move_unsolved_logs = false` controls Standard runs. A custom destination is ignored unless movement is enabled.
- `move_unsolved_logs = true` with no custom destination uses the configured Unsolved Logs Destination from settings, or the canonical destination if the setting is empty.
- The canonical destination is `CLASSIC Backup/Unsolved Logs` under the path-backed Crash Log Scan Intake root.
- A Standard run that requests movement without an explicit custom destination and without intake path roots must fail setup.
- An explicit custom Unsolved Logs Destination can be used without intake path roots, but it must be absolute.
- Relative Unsolved Logs Destination values are setup errors.
- Absolute destinations do not need to exist at save time. `scan_run` creates the directory lazily when it moves a failed Crash Log or Autoscan Report.
- Invalid or unwritable absolute destinations remain per-log movement failures, preserving current behavior.
- GUI, TUI, CLI, C++, Node, and Python should expose the custom Unsolved Logs Destination capability in the same implementation slice.
- The first slice includes Rust core, C++ bridge, Node, Python, TUI, GUI, CLI, tests, docs, and parity updates.
- Rust `scan_run` tests are the authoritative behavior tests. Adapter tests prove mapping and wiring only.

## Domain And Settings Decisions

`CONTEXT.md` now defines **Unsolved Logs Destination**:

> The directory where a Standard Crash Log Scan Run may move Unsolved Logs when relocation is enabled. It can be the canonical CLASSIC backup location or a user-selected location; Targeted Crash Log Scan Runs do not use it.

Persistent settings decision:

- Key name: `CLASSIC_Settings.Unsolved Logs Destination`
- Missing or empty value means "use the canonical destination".
- Non-empty value must be an absolute filesystem path.
- Resetting to canonical should be an explicit reset action in GUI/TUI/CLI, not an implicit side effect of a failed path parse.
- Saving an absolute path should not create the directory immediately.
- CLI destination option should persist to `CLASSIC Settings.yaml` and the current scan should use the saved value.

Important current-code warning:

- GUI and scan intake currently use nested `CLASSIC_Settings.*` keys through `classic-settings-core::YamlOperations`.
- `classic-config-core::ClassicConfig` currently uses flat keys such as `move_unsolved_logs` and does not read the nested `CLASSIC_Settings.*` settings shape used by active GUI/intake paths.
- Do not add a third independent settings interpretation. Either add a small shared helper for the nested key, or deliberately dual-read/dual-write where the existing interface requires it. Document the choice.

## Proposed Rust Shape

Names are suggestions, but the interface shape should make Targeted-plus-relocation impossible and keep destination resolution local to Rust.

```rust
pub struct CrashLogScanRunRequest {
    pub logs: Vec<PathBuf>,
    pub intent: CrashLogScanRunIntent,
    pub max_concurrent: Option<usize>,
    pub cancellation: Option<Arc<AtomicBool>>,
    pub preserve_order: bool,
}

pub enum CrashLogScanRunIntent {
    Standard(StandardCrashLogScanRunIntent),
    Targeted,
}

pub struct StandardCrashLogScanRunIntent {
    pub unsolved_logs: StandardUnsolvedLogsIntent,
}

pub enum StandardUnsolvedLogsIntent {
    LeaveInPlace,
    MoveToConfiguredOrDefault,
    MoveToCustom(PathBuf),
}
```

Implementation notes:

- `MoveToConfiguredOrDefault` resolves to the configured `Unsolved Logs Destination` from `ScanReadyAnalysis` when present; otherwise it resolves to the canonical destination under intake paths.
- `MoveToCustom(PathBuf)` must validate that the path is absolute before analysis starts. Do not create the directory during setup.
- `MoveToConfiguredOrDefault` with no configured destination and no intake paths should return a setup error before analysis.
- Replace `unsolved_logs_directory(mode: &CrashLogScanRunMode)` with a resolver that accepts `ScanReadyAnalysis` and `CrashLogScanRunIntent`.
- Keep Autoscan Report write failure and Unsolved Logs movement failure as per-log outcomes, not run-level failures.
- Keep cancellation, progress events, adaptive concurrency, result ordering, and per-log counters behavior-preserving.
- If compatibility shims for the old Rust types are temporarily necessary, keep them crate-internal or deprecated and remove adapter use in the same slice. The target is a smaller public Rust test surface.

## Intake Readiness Shape

`ScanReadyAnalysis` should stop being field-constructible by external callers. At minimum, change public fields to private or `pub(crate)` and provide focused getters or constructors.

Suggested additions:

- Store path-backed intake roots in prepared readiness, likely `paths: Option<CrashLogScanIntakePaths>`.
- Store the parsed persistent destination, likely `unsolved_logs_destination: Option<PathBuf>`.
- Parse `CLASSIC_Settings.Unsolved Logs Destination` during `CrashLogScanIntake::prepare()` for path-backed intake.
- Missing or empty value becomes `None`.
- Non-empty relative value returns `ScanLogError::InvalidInput` or another setup-level error before analysis.
- Non-empty absolute value is stored without checking existence.

Testing guidance:

- Prefer exercising readiness through `CrashLogScanIntake::from_yaml_paths(...).prepare()` or `CrashLogScanIntake::from_yaml_data(...)` with owned fixture paths.
- Avoid rebuilding `ScanReadyAnalysis` manually in `scan_run_tests.rs` just to bypass intake. If a narrow test constructor is unavoidable, keep it crate-private and make it preserve the same invariants as real intake.

## Adapter Mapping Rules

All adapters should converge on the same mapping before crossing the Rust seam:

1. If `targeted_mode` is true, use `CrashLogScanRunIntent::Targeted` and ignore `move_unsolved_logs` plus destination inputs.
2. Else if `move_unsolved_logs` is false, use `StandardUnsolvedLogsIntent::LeaveInPlace` and ignore destination inputs.
3. Else if a non-empty destination is supplied, use `StandardUnsolvedLogsIntent::MoveToCustom(destination)`.
4. Else use `StandardUnsolvedLogsIntent::MoveToConfiguredOrDefault`.

Do not duplicate canonical destination construction in adapters. The string `CLASSIC Backup/Unsolved Logs` should not be reintroduced in bridge, Node, Python, CLI, GUI, or TUI mapping code.

## C++ Bridge And Native Frontends

### C++ bridge

Update `ScanRunRequestDto` in `cpp-bindings/classic-cpp-bridge/src/scanner.rs`:

- Keep existing fields for compatibility: `move_unsolved_logs`, `targeted_mode`, `max_concurrent`, `log_paths`, and scan options.
- Add a flattened optional destination string, for example `unsolved_logs_destination` where `""` means not supplied.
- Map DTO fields using the adapter mapping rules above.
- Keep `max_concurrent == 0` mapping to the core adaptive default.
- Keep `preserve_order: false` unless a separate C++ bridge behavior change is intentionally included.
- Update CXX parity baselines if the bridge surface changes.

### CLI

Current CLI hardcodes `request.move_unsolved_logs = false`. This must change.

Expected CLI behavior:

- Read `CLASSIC_Settings.Move Unsolved Logs` from `CLASSIC Settings.yaml` instead of hardcoding false.
- Read `CLASSIC_Settings.Unsolved Logs Destination` from `CLASSIC Settings.yaml`.
- Add a CLI option to set the persistent destination for the current and future scans, for example `--unsolved-logs-destination <absolute-path>`.
- Add a reset option for canonical behavior, for example `--reset-unsolved-logs-destination`.
- Persist destination changes through the settings YAML bridge before starting the scan so the current scan uses the saved value.
- Reject relative destination input with a clear CLI error before scanning.
- Do not make a destination imply movement. `Move Unsolved Logs` remains the controlling boolean.
- If adding CLI flags for `Move Unsolved Logs` itself, keep them separate from the destination option, for example `--move-unsolved-logs` and `--no-move-unsolved-logs`.

Update `classic-cli/tests/test_cli_args.cpp` and any scanner wiring tests that assert request construction.

### GUI

Expected GUI behavior:

- Add a visible `Unsolved Logs Destination` control near the existing `Move Unsolved Logs` setting.
- Provide browse/select and reset-to-canonical actions.
- Load/save `CLASSIC_Settings.Unsolved Logs Destination` through `YamlOperations`.
- Keep empty/missing value as canonical.
- Reject or surface relative paths before save or before scan startup. Use absolute paths only.
- Do not create the directory when saving.
- Pass the destination value through `MainWindow -> ScanController -> ScanWorker -> ScanRunRequestDto` or rely on saved settings read by intake, but do not duplicate canonical path construction.
- Ensure Targeted scans still discard movement and destination at the adapter mapping seam.

Update `classic-gui/tests/test_scan_settings_wiring.cpp`. Existing source-text forwarding tests are brittle; keep adapter tests focused on mapping/wiring and move behavior assertions to Rust `scan_run` tests where possible.

### TUI

Expected TUI behavior:

- Add `Unsolved Logs Destination` to the TUI configuration/editing path.
- Persist/reset it using the same setting semantics as GUI and CLI.
- Stop constructing `CrashLogScanRunMode` / `UnsolvedLogsPolicy` directly in `ui-applications/classic-tui/src/app.rs`.
- Map TUI state into the new Rust `CrashLogScanRunIntent` using the adapter mapping rules.
- Keep the shared Tokio runtime model; do not create another runtime.

## Node And Python Bindings

### Node

Update `JsScanRunOptions` in `node-bindings/classic-node/src/scanlog.rs`:

- Add optional `unsolved_logs_destination: Option<String>`.
- Generated TypeScript should expose `unsolvedLogsDestination?: string` in `index.d.ts`.
- Apply the adapter mapping rules in `scan_run_execute()`.
- Preserve current behavior for callers that omit the new option.
- Update `node-bindings/classic-node/__test__/scanlog.spec.ts` and generated declarations.
- Refresh Node parity and runtime coverage artifacts when required.

### Python

Update `classic_scanlog.scan_run_execute(...)` in `python-bindings/classic-scanlog-py/src/orchestrator.rs`:

- Add an optional destination parameter, likely `unsolved_logs_destination: Option<String> = None` after `move_unsolved_logs` or near the other scan-run policy fields.
- Update `python-bindings/classic-scanlog-py/classic_scanlog.pyi`.
- Apply the adapter mapping rules before calling the Rust seam.
- Preserve current behavior for callers that omit the new parameter.
- Update Python smoke tests and runtime coverage registry if the public surface changes.
- Refresh Python parity artifacts when required.

## Data And Settings Defaults

Update default settings in `CLASSIC Data/databases/CLASSIC Main.yaml`:

```yaml
    # Optional absolute folder for Unsolved Logs relocation.
    # Leave empty to use CLASSIC Backup/Unsolved Logs under the CLASSIC root.
      Unsolved Logs Destination:
```

Schema-version note:

- Adding an optional settings key to shippable YAML Data is additive. If the schema-version gate treats the default settings shape as part of the shippable contract, bump `CLASSIC Main.yaml` from `2.0` to `2.1` and update any schema range metadata required by the gate.
- Run the YAML schema and publish validators either way.

If root `CLASSIC Settings.yaml` is tracked as a sample or active test fixture, add the empty `Unsolved Logs Destination` key there too.

## Implementation Order

1. Update `CONTEXT.md` only if the `Unsolved Logs Destination` term is missing. It is already present if this brief was created from the grilling session.
2. Add intake readiness fields for path roots and configured Unsolved Logs Destination.
3. Add parsing/validation for `CLASSIC_Settings.Unsolved Logs Destination` in path-backed Crash Log Scan Intake.
4. Replace the public Rust `scan_run` request mode/policy surface with scan intent types that make Targeted relocation impossible.
5. Update `scan_run` destination resolution and per-log movement code to use the new intent plus intake readiness.
6. Rewrite Rust `scan_run_tests.rs` and `scan_intake_tests.rs` around the new interface and readiness invariants.
7. Update C++ bridge DTO and mapping.
8. Update CLI settings reads, CLI destination/reset options, persistence, and scanner mapping.
9. Update GUI settings controls, load/save, scan wiring, and tests.
10. Update TUI config/state and scan-run mapping.
11. Update Node and Python binding options, tests, declarations/stubs, parity artifacts, and runtime coverage registries.
12. Update default settings data and schema version/range metadata if required.
13. Update `docs/api/` pages.
14. Run targeted validation, then broader workspace validation as feasible.

## Tests To Add Or Update

Rust unit tests must stay in sibling `*_tests.rs` files.

`classic-scanlog-core/src/scan_intake_tests.rs`:

- Missing `CLASSIC_Settings.Unsolved Logs Destination` produces no configured destination.
- Empty `Unsolved Logs Destination` produces no configured destination.
- Absolute `Unsolved Logs Destination` is stored without requiring the directory to exist.
- Relative `Unsolved Logs Destination` fails setup.
- Path roots are preserved in `ScanReadyAnalysis` for path-backed intake.

`classic-scanlog-core/src/scan_run_tests.rs`:

- Standard run with `LeaveInPlace` does not move failed Crash Logs.
- Standard run with `MoveToConfiguredOrDefault` and no configured destination uses canonical `CLASSIC Backup/Unsolved Logs` from intake paths.
- Standard run with `MoveToConfiguredOrDefault` and configured destination uses the configured destination.
- Standard run with `MoveToCustom` uses the explicit custom destination.
- Standard run with `MoveToConfiguredOrDefault` and no available destination source fails setup before analysis.
- Relative custom destination fails setup.
- Absolute but unwritable destination remains a per-log movement failure, not a run setup failure.
- Targeted intent has no movement option and still never moves failed Crash Logs or Autoscan Reports.
- Existing overwrite-safe movement behavior still preserves stale destination files with suffixes.
- Cancellation and preserve-order behavior remain unchanged.

C++ bridge:

- DTO mapping sends Targeted intent when `targeted_mode` is true even if move/destination fields are set.
- DTO mapping ignores destination when `move_unsolved_logs` is false.
- DTO mapping uses custom destination only when Standard movement is enabled.
- CXX parity baselines reflect the new DTO field.

CLI:

- Argument parsing accepts the destination option and reset option.
- Relative destination option exits with a clear error.
- Destination option and reset option are mutually exclusive.
- Scanner no longer hardcodes `move_unsolved_logs = false`.
- CLI writes the nested settings key before scanning when destination/reset options are used.

GUI:

- Settings dialog loads, saves, browses, and resets `CLASSIC_Settings.Unsolved Logs Destination`.
- Relative value is rejected or surfaced before scan startup.
- Scan worker request mapping includes destination without constructing canonical path.
- Targeted scan wiring still disables movement through adapter mapping.

TUI:

- Config/state persists destination and reset behavior.
- Scan-run mapping no longer constructs `UnsolvedLogsPolicy` directly.

Node:

- `scanRunExecute` accepts `unsolvedLogsDestination`.
- Targeted wins over move plus destination.
- Destination is ignored when `moveUnsolvedLogs` is false.

Python:

- `scan_run_execute` accepts `unsolved_logs_destination`.
- Stub matches runtime signature.
- Targeted wins over move plus destination.
- Destination is ignored when `move_unsolved_logs` is false.

## Docs To Update

- `docs/api/classic-scanlog-core.md`: replace old `CrashLogScanRunMode` / `UnsolvedLogsPolicy` caller guidance with scan intent and Unsolved Logs Destination resolution.
- `docs/api/classic-cpp-bridge-data-entrypoints.md`: document `ScanRunRequestDto.unsolved_logs_destination`, empty-string semantics, Targeted-wins mapping, and setup/per-log error split.
- `docs/api/classic-cpp-bridge-scan-progress-callback.md`: update any wording that names old mode/policy internals.
- `docs/api/classic-gui-scan-result-ordering.md`: update scan worker request notes if fields change.
- `docs/api/classic-gui-scan-progress-consumer.md`: update scan worker request notes if fields change.
- `docs/api/node-python-contract-map.md`: document the Node/Python option addition.
- `docs/api/yaml-update-delivery.md` or YAML schema docs if `CLASSIC Main.yaml` schema version or settings defaults change.
- `docs/api/formid-settings-boundary.md` only if the implementation touches the broader nested-vs-flat settings model.
- Do not re-litigate ADR-0002. Link to it when explaining why Rust owns the policy.

## Validation Commands

Run from repo root unless stated otherwise.

Minimum Rust and formatting checks:

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
cargo fmt --all -- --check
cargo test -p classic-scanlog-core
cargo test -p classic-config-core
```

YAML Data validation if `CLASSIC Data/databases/CLASSIC Main.yaml` or schema metadata changes:

```powershell
python tools/schema_version_gate.py --repo-root .
python tools/publish_yaml_data/validate.py --databases-dir "CLASSIC Data/databases" --schema-ranges "CLASSIC Data/databases/client-schema-ranges.yaml"
```

C++ bridge and native frontend validation. Do not invoke C++ test binaries or raw `ctest` directly:

```powershell
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

Node binding validation from `node-bindings/classic-node` when the Node surface changes:

```powershell
bun install
bun run dts:refresh
bun run parity:gate
bun run test:bun
bun run test:node
bun run dts:freshness:check
```

Python binding validation from repo root when the Python surface changes:

```powershell
uv sync --project python-bindings --inexact --group drift-guards
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
uv run --project python-bindings python tools/python_api_parity/check_parity_gate.py --repo-root .
uv run --project python-bindings python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
uv run --project python-bindings python tools/schema_version_gate.py --repo-root .
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
uv run --project python-bindings python -m pytest python-bindings/tests -q
```

Broader Rust workspace check when feasible:

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

## Non-Goals

- Do not change Autoscan Report Assembly in this slice.
- Do not change Autoscan Report path derivation or report markdown output.
- Do not make Targeted Crash Log Scan Runs move failed logs under any input combination.
- Do not let adapters reconstruct `CLASSIC Backup/Unsolved Logs` themselves.
- Do not introduce a second Tokio runtime.
- Do not move Crash Log selection into `CrashLogScanIntake` or `CrashLogScanRun`; adapters still select logs.
- Do not silently ignore malformed relative Unsolved Logs Destination values.
- Do not create destination directories when saving settings or during scan setup.
- Do not remove lower-level `OrchestratorCore` analysis entry points as part of this change.
