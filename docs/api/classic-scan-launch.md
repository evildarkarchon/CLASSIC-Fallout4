# classic-scan-launch

`business-logic/classic-scan-launch` owns **Crash Log Scan Launch**: the read-only projection of
saved User Settings, the selected game, and per-run overrides into a Crash Log Scan Run request.
`GLOSSARY.md` defines the term; [`../adr/0009-rust-owns-crash-log-scan-launch-and-settled-recovery.md`](../adr/0009-rust-owns-crash-log-scan-launch-and-settled-recovery.md)
records the decision, which supersedes the ADR-0002 clause that gave adapters typed request
projection.

It never persists User Settings and never runs the scan. A frontend that wants to save a value does
so as its own User Settings Update, before or apart from launching.

## Status

The crate and its binding surfaces exist; **no frontend launches through it yet**. The GUI, CLI,
TUI, Node CLI and Python CLI still build their own requests and switch in a later change. One launch
rule from ADR-0009 is not implemented yet and is tracked separately:

- the full FCX setup context (the XSE log resolved from XSE Folder rules, and an FCX Mode override).

Until then the interface already has the slot it fills: `CrashLogScanLaunchRequest::setup_context`
already returns the Crash Log Scan Setup Context of an FCX request. Today an FCX request carries the
saved game folder, documents folder and game executable, and no XSE log.

## Dependency boundary

```text
classic-scan-launch ──► classic-scanlog-core          (owns the request)
                    └─► classic-user-settings-core     (owns the saved values and FormID rows)
```

The edges are one-way. `classic-scanlog-core` keeps User Settings as a dev-dependency only: the
Crash Log Scan Setup Context definition keeps User Settings loading out of scanlog core.
`tests/dependency_boundary.rs` reads both manifests and fails if scanlog core gains a normal
dependency on User Settings, or if this crate loses either edge.

## Interface

```rust
pub fn prepare_launch(
    installation_root: impl AsRef<Path>,
    intent: CrashLogScanIntent,
    overrides: &CrashLogScanLaunchOverrides,
) -> Result<CrashLogScanLaunchRequest, CrashLogScanLaunchError>;
```

| Type | Role |
|---|---|
| `CrashLogScanIntent` | `Standard`, or `Targeted(Vec<PathBuf>)` with explicit inputs in order |
| `CrashLogScanLaunchOverrides` | Optional per-run values, built with `with_*` methods so later overrides do not break callers |
| `MaxConcurrency` | `Adaptive` or `Limit(NonZeroUsize)`; `from_count(0)` is `Adaptive` |
| `CrashLogScanLaunchRequest` | `request()`, `setup_context()`, `diagnostics()`, `into_request()`, `into_parts()` |
| `CrashLogScanLaunchDiagnostic` | Non-fatal launch fact: `UserSettings(Diagnostic)`, or `SavedValueNotApplied { value, managed_game, target_game }` from the game-differs rule |
| `CrashLogScanLaunchDiagnosticKind` | Vocabulary enum; tokens `user_settings`, `game_version_not_applied`, `fcx_mode_not_applied`, `custom_scan_folder_not_applied`, `setup_folders_not_applied` |
| `SavedGameSpecificValue` | Which saved value the game-differs rule withheld: `GameVersion`, `FcxMode`, `CustomScanFolder`, `SetupFolders`; `not_applied_kind()` names its diagnostic kind |
| `CrashLogScanLaunchError` / `…ErrorKind` | Typed refusal; today only `TargetedWithoutInputs` (token `targeted_without_inputs`) |
| `GameVersionSelection` | Re-exported from User Settings for the game-version override |

The diagnostic and error enums are deliberately **exhaustive**: a new kind fails to compile in every
binding that projects it, which is how CXX, Node and Python stay in parity with it.

## Rules

- **Read-only.** `UserSettings::open` reads the document; nothing is written, created or moved. A
  test proves the document is byte-identical and nothing appears beside it.
- **Override model.** Every override is optional and a supplied override wins over the saved value.
  - *Explicit value wins:* game, game version, scan path, max concurrency.
  - *Supplied as on:* FormID values and simplify logs. Supplying one turns the option on for the
    run; not supplying it keeps the saved value. There is no way to turn a saved option off for one
    run, matching the CLI flags these model.
- **Max concurrency.** `MaxConcurrency::Adaptive` is a distinct override value, so explicitly asking
  for adaptive concurrency overrides a saved limit. A saved `Max Concurrent Scans: 0` is adaptive.
- **Base folder.** A Standard scan's base folder is always the Installation Root. The scan path
  override, then the saved custom scan folder, are the explicit way to scan elsewhere. The configured
  documents root is the saved documents folder.
- **Unsolved Logs.** A Standard request moves Unsolved Logs to the configured or default destination
  when the saved Move Unsolved Logs is on, and leaves them in place otherwise. The saved destination
  travels in the run configuration. A Targeted request has no Unsolved Logs capability.
- **FormID rows** come from `CrashLogScanSettings::formid_databases_for_game` for the scanned game,
  so a Fallout 4 VR scan reads the shared `Fallout4` rows followed by legacy `Fallout4VR` rows,
  de-duplicated (see [`formid-settings-boundary.md`](formid-settings-boundary.md)).
- **Degraded User Settings** (malformed, newer, needing migration) are never an error. The request
  is built from the values User Settings projected for that document (its degraded fallbacks for an
  untrusted document) and every User Settings diagnostic is reported as a
  `CrashLogScanLaunchDiagnostic::UserSettings`, code unchanged.
- **Game-differs rule.** When the scanned game (the game override) differs from the managed game,
  the managed game's saved game-specific values are not applied: the game version (`auto` is used),
  FCX Mode, the custom scan folder, and the setup folders (game folder, documents folder and game
  executable, which also drops the Standard source's configured documents root). Each withheld
  value is reported as a `SavedValueNotApplied` diagnostic, after any User Settings diagnostics and
  in that order, but only when the same launch against the managed game would have used it: a value
  an override replaced is not reported (an explicit override still wins for the non-managed game),
  and a Targeted scan without saved FCX Mode reports neither the custom scan folder nor the setup
  folders, because it reads neither. Naming the managed game explicitly is not a game difference.
  Values that are not game-specific (FormID options, simplify logs, Unsolved Logs, max concurrency)
  still apply, and FormID rows follow the scanned game as above.
- **Display Content.** `classic-scan-presentation::render_launch_diagnostics` renders every launch
  diagnostic, User Settings ones included, as one display line each (ADR-0007); see
  [`classic-scan-presentation.md`](classic-scan-presentation.md). Each binding carries those lines
  beside the typed diagnostics, so frontends keep only Display Layout.
- **Errors** are reserved for invalid caller input. A Targeted intent with no inputs is
  `TargetedWithoutInputs`, and User Settings are not opened.

## Binding surfaces

Launch is exposed on the existing scan-run surfaces, the same way scan presentation is; there is no
new bridge module and no new Python facade.

| Surface | Entry points | Notes |
|---|---|---|
| CXX `classic::scanner` (`cpp-bindings/classic-cpp-bridge/src/scanner/launch.rs`) | `scan_run_launch_standard(root, overrides)`, `scan_run_launch_targeted(root, inputs, overrides)` → opaque `ScanRunLaunch`; `scan_run_launch_error`, `scan_run_launch_view`, `scan_run_launch_request` | `ScanRunLaunchOverridesDto` uses presence flags; `max_concurrent` 0 with `has_max_concurrent` is adaptive. `ScanRunLaunchErrorDto.has_error` is authoritative. The view reuses `ScanRunConfigurationDto`, `ScanRunStandardSourceDto`, `ScanRunTargetedSourceDto` and `ScanRunSetupContextDto`, plus `display_lines`. Exceptions are reserved for unrepresentable input (blank paths, an unknown game-version token, an out-of-range game discriminant). |
| Node (`node-bindings/classic-node/src/scan_run_launch.rs`) | `ScanRunLaunch.standard(root, overrides?)`, `ScanRunLaunch.targeted(root, inputs, overrides?)` | Getters `intent`, `configuration`, `standardSource`, `unsolvedLogs`, `targetedSource`, `fcxEnabled`, `setupContext`, `diagnostics`, `displayLines`; `request()` returns a `ScanRunRequest`. A typed launch error throws with `code` and `kind` set to its token; diagnostic kinds are camelCase (`userSettings`, `gameVersionNotApplied`, …). |
| Python `classic_scanlog` (`classic_scanlog/scan_launch.rs`) | `ScanRunLaunch.standard(root, overrides=None)`, `ScanRunLaunch.targeted(root, inputs, overrides=None)`, `ScanRunLaunchOverrides(...)` | Flat read-only properties (`game`, `game_version`, `formid_database_paths`, `base_directory`, `unsolved_logs`, `targeted_inputs`, `setup_context`, `diagnostics`, `display_lines`, …); `request()` returns a `ScanRunRequest`. `ScanRunLaunchTargetedWithoutInputsError` subclasses `ScanRunLaunchError(ValueError)`. |

Every binding parses the game-version override with `GameVersionSelection::parse` and maps a
max-concurrency count with `MaxConcurrency::from_count`, so none of them restates a merge rule.

## Conformance

The `crash-log-scan-launch` executable conformance family
(`tests/conformance/packs/crash_log_scan_launch/v1.json`, fixtures in
`tests/fixtures/crash_log_scan_launch_conformance/`) pins override merging, the adaptive-concurrency
override, the Fallout 4 VR row rule, the game-differs rule, degraded settings, Targeted inputs, and the typed Targeted
error. It runs through the shared scan-run launcher with one runner per adapter, each traversing its
own DTOs (ADR-0008); see [`binding-compliance-suite.md`](binding-compliance-suite.md).

## Tests

- `tests/launch_behavior.rs` — temp-dir User Settings fixtures through the public interface.
- `tests/game_differs.rs` — the game-differs rule: each withheld saved value and its diagnostic, nothing reported for the managed game, overrides still winning, and Targeted intents.
- `tests/dependency_boundary.rs` — the manifest boundary above.
- `tests/launch_conformance.rs` — the Rust conformance runner (skips without a run plan).
- `src/lib_tests.rs` — `MaxConcurrency::from_count` and Vocabulary conformance.
