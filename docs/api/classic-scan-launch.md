# classic-scan-launch

`business-logic/classic-scan-launch` owns **Crash Log Scan Launch**: the read-only projection of
saved User Settings, the selected game, and per-run overrides into a Crash Log Scan Run request.
`GLOSSARY.md` defines the term; [`../adr/0009-rust-owns-crash-log-scan-launch-and-settled-recovery.md`](../adr/0009-rust-owns-crash-log-scan-launch-and-settled-recovery.md)
records the decision, which supersedes the ADR-0002 clause that gave adapters typed request
projection.

It never persists User Settings and never runs the scan. A frontend that wants to save a value does
so as its own User Settings Update, before or apart from launching.

## Status

The crate and its binding surfaces exist. The Node and Python CLIs launch through it (#290). The
native C++ CLI launches through it too (#289): it maps its flags onto overrides, saves
`--unsolved-logs-destination` as a separate User Settings Update before launching, and prints the
launch's `display_lines`. Frontends not yet switched still build their own requests and switch in
their own changes. Every launch rule from ADR-0009 is implemented:

- the game-differs rule (#285): saved game-specific values are not applied to a non-managed game,
  each one reported as a typed launch diagnostic rendered as Display Content;
- the FCX setup context (#286): with FCX Mode on, by saved setting or by override, the request
  carries the game folder, documents folder, game executable and XSE log for both intents. The
  folders come from the game-differs-filtered saved values, so an FCX launch for a non-managed game
  carries no saved folders.

## Dependency boundary

```text
classic-scan-launch ──► classic-scanlog-core          (owns the request)
                    ├─► classic-user-settings-core     (owns the saved values and FormID rows)
                    ├─► classic-scangame-core          (owns the one XSE log lookup, #283)
                    ├─► classic-config-core            (Version Registry entry naming the game executable)
                    └─► classic-version-registry-core  (the registry scope a facade passes)
```

Scangame, config and the version registry already sit below scanlog core, so the FCX edges add no
cycle.

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

pub fn prepare_launch_in_scopes(
    installation_root: impl AsRef<Path>,
    intent: CrashLogScanIntent,
    overrides: &CrashLogScanLaunchOverrides,
    version_registry: &VersionRegistryScope,
    yaml_file_cache: &YamlFileCacheScope,
) -> Result<CrashLogScanLaunchRequest, CrashLogScanLaunchError>;
```

`prepare_launch` reads Version Registry metadata and the Game Local document through the process
default scopes. `prepare_launch_in_scopes` reads them only through the caller's scopes, so a binding
facade that executes its runs in its own scopes launches with FCX setup facts from the same
snapshot; the Python `classic_scanlog` facade passes its own. The scopes are read only when FCX Mode
is on.

| Type | Role |
|---|---|
| `CrashLogScanIntent` | `Standard`, or `Targeted(Vec<PathBuf>)` with explicit inputs in order |
| `CrashLogScanLaunchOverrides` | Optional per-run values, built with `with_*` methods so later overrides do not break callers |
| `MaxConcurrency` | `Adaptive` or `Limit(NonZeroUsize)`; `from_count(0)` is `Adaptive` |
| `CrashLogScanLaunchRequest` | `request()`, `setup_context()`, `diagnostics()`, `into_request()`, `into_parts()` |
| `CrashLogScanLaunchDiagnostic` | Non-fatal launch fact: `UserSettings(Diagnostic)`, or `SavedValueNotApplied { value, managed_game, target_game }` from the game-differs rule |
| `CrashLogScanLaunchDiagnosticKind` | Vocabulary enum; tokens `user_settings`, `game_version_not_applied`, `fcx_mode_not_applied`, `custom_scan_folder_not_applied`, `setup_folders_not_applied` |
| `SavedGameSpecificValue` | Which saved value the game-differs rule withheld: `GameVersion`, `FcxMode`, `CustomScanFolder`, `SetupFolders`; `not_applied_kind()` names its diagnostic kind |
| `CrashLogScanLaunchError` / `…ErrorKind` | Typed refusal: `TargetedWithoutInputs` (token `targeted_without_inputs`) and `XseLogInspect { path, message }` (token `xse_log_inspect`) |
| `GameVersionSelection` | Re-exported from User Settings for the game-version override |

The diagnostic and error enums are deliberately **exhaustive**: a new kind fails to compile in every
binding that projects it, which is how CXX, Node and Python stay in parity with it.

## Rules

- **Read-only.** `UserSettings::open` reads the document; nothing is written, created or moved. A
  test proves the document is byte-identical and nothing appears beside it.
- **Override model.** Every override is optional and a supplied override wins over the saved value.
  - *Explicit value wins:* game, game version, scan path, max concurrency.
  - *Supplied as on:* FormID values, simplify logs and FCX Mode (`with_fcx_mode`). Supplying one
    turns the option on for the run; not supplying it keeps the saved value. There is no way to
    turn a saved option off for one run, matching the CLI flags these model.
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
  executable, which also drops the Standard source's configured documents root and leaves an FCX
  setup context without saved folders). Each withheld value is reported as a `SavedValueNotApplied`
  diagnostic, after any User Settings diagnostics and in that order, but only when the same launch
  against the managed game would have used it: a value an override replaced is not reported (an
  explicit override still wins for the non-managed game, and the FCX Mode override turns FCX Mode
  on, so saved FCX Mode is not reported), and a Targeted scan with FCX Mode neither saved nor
  overridden on reports neither the custom scan folder nor the setup folders, because it reads
  neither. Naming the managed game explicitly is not a game difference. Values that are not
  game-specific (FormID options, simplify logs, Unsolved Logs, max concurrency) still apply, and
  FormID rows follow the scanned game as above.
- **FCX setup context.** When FCX Mode is on, by saved setting or by override, the request
  carries its Crash Log Scan Setup Context for a Standard and a Targeted intent alike:
  - the saved game folder and documents folder, trimmed; blank means none. These are the values
    left after the game-differs rule, so a non-managed game has none;
  - the game executable, by the rule the GUI applied before launch moved into Rust: a saved
    executable is kept only when it exists directly inside the game folder (compared
    case-insensitively); otherwise the selected version's `<docs_name>.exe` from its Version
    Registry entry under the game folder applies (`Fallout4.exe` when no entry resolves); with no
    game folder the saved executable passes through. The one difference from the GUI is Fallout 4
    VR on `auto`, which names `Fallout4VR.exe` rather than the flat-screen default;
  - the XSE log, from `classic_scangame_core::resolve_xse_log_for_scan_in_scopes` under
    `<Installation Root>/CLASSIC Data` with the scanned game, the selected version and the saved
    documents folder, so Fallout 4 VR gets its own `f4sevr.log`.

  Missing folders are **not** a launch error: saved folders that do not exist are passed through
  and unsaved ones stay empty, so FCX setup validation reports them in the Crash Log Scan Setup
  Result. A missing XSE log leaves the XSE log empty. With FCX Mode off nothing above is read.
- **Display Content.** `classic-scan-presentation::render_launch_diagnostics` renders every launch
  diagnostic, User Settings ones included, as one display line each (ADR-0007); see
  [`classic-scan-presentation.md`](classic-scan-presentation.md). Each binding carries those lines
  beside the typed diagnostics, so frontends keep only Display Layout.
- **Errors** are reserved for invalid caller input and operational failures the launch cannot
  decide past. A Targeted intent with no inputs is `TargetedWithoutInputs`, and User Settings are
  not opened. With FCX Mode on, an XSE log location that cannot be inspected for a reason other
  than absence (access denied, an invalid file name) is `XseLogInspect`, carrying the candidate
  path and the I/O failure text.

## Binding surfaces

Launch is exposed on the existing scan-run surfaces, the same way scan presentation is; there is no
new bridge module and no new Python facade.

| Surface | Entry points | Notes |
|---|---|---|
| CXX `classic::scanner` (`cpp-bindings/classic-cpp-bridge/src/scanner/launch.rs`) | `scan_run_launch_standard(root, overrides)`, `scan_run_launch_targeted(root, inputs, overrides)` → opaque `ScanRunLaunch`; `scan_run_launch_error`, `scan_run_launch_view`, `scan_run_launch_request` | `ScanRunLaunchOverridesDto` uses presence flags; `max_concurrent` 0 with `has_max_concurrent` is adaptive; `fcx_mode` is supplied-as-on. `ScanRunLaunchErrorDto.has_error` is authoritative; `ScanRunLaunchErrorKind` is `TargetedWithoutInputs` or `XseLogInspect`. The view reuses `ScanRunConfigurationDto`, `ScanRunStandardSourceDto`, `ScanRunTargetedSourceDto` and `ScanRunSetupContextDto`, plus `display_lines`. Exceptions are reserved for unrepresentable input (blank paths, an unknown game-version token, an out-of-range game discriminant). |
| Node (`node-bindings/classic-node/src/scan_run_launch.rs`) | `ScanRunLaunch.standard(root, overrides?)`, `ScanRunLaunch.targeted(root, inputs, overrides?)` | Getters `intent`, `configuration`, `standardSource`, `unsolvedLogs`, `targetedSource`, `fcxEnabled`, `setupContext`, `diagnostics`, `displayLines`; `request()` returns a `ScanRunRequest`. Overrides include `fcxMode`. A typed launch error throws with `code` and `kind` set to its token (`targeted_without_inputs`, `xse_log_inspect`); diagnostic kinds are camelCase (`userSettings`, `gameVersionNotApplied`, …). |
| Python `classic_scanlog` (`classic_scanlog/scan_launch.rs`) | `ScanRunLaunch.standard(root, overrides=None)`, `ScanRunLaunch.targeted(root, inputs, overrides=None)`, `ScanRunLaunchOverrides(...)` | Flat read-only properties (`game`, `game_version`, `formid_database_paths`, `base_directory`, `unsolved_logs`, `targeted_inputs`, `setup_context`, `diagnostics`, `display_lines`, …); `request()` returns a `ScanRunRequest`. Overrides include `fcx_mode=False`. `ScanRunLaunchTargetedWithoutInputsError` and `ScanRunLaunchXseLogInspectError` subclass `ScanRunLaunchError(ValueError)`. Launches go through `prepare_launch_in_scopes` with the facade's own Version Registry and YAML-file scopes, the ones `scan_run_execute` uses. |

Every binding parses the game-version override with `GameVersionSelection::parse` and maps a
max-concurrency count with `MaxConcurrency::from_count`, so none of them restates a merge rule.

## Frontend consumers

- **Node CLI** (`node-bindings/classic-node/cli/run-scan.ts`) launches a Standard scan with
  `ScanRunLaunch.standard(installationRoot, overrides)` and executes `launch.request()`. Only the
  flags the user supplied become overrides (`--game`, `--game-version`, `--scan-path`,
  `--max-concurrent` with `0` meaning adaptive, and the supplied-as-on `--fcx-mode`,
  `--show-fid-values`, `--simplify-logs`); an omitted `--game` scans the managed game. The Standard
  base folder is therefore the Installation Root, not the working directory. It prints
  `displayLines` before the run and carries the typed `diagnostics` as `launchDiagnostics` in its
  JSON summary. A launch error is a fatal (exit 2).
- **Python CLI** (`classic-py scan logs`) launches a Targeted scan of `--path` with
  `ScanRunLaunch.targeted(installation_root, [path])`, no overrides, and executes
  `launch.request()`. Its text stream prints `display_lines` ahead of the run's lines; its JSON
  `data.launchDiagnostics` carries the typed diagnostics. A launch error is reported like any other
  binding exception (exit 1).

Neither CLI keeps a game-name table, opens User Settings to build a request, or settles Local
Ignore recovery: a paused run stays terminal and exits as a product failure (exit 1).

## Conformance

The `crash-log-scan-launch` executable conformance family
(`tests/conformance/packs/crash_log_scan_launch/v1.json`, fixtures in
`tests/fixtures/crash_log_scan_launch_conformance/`) pins override merging, the adaptive-concurrency
override, the Fallout 4 VR row rule, the game-differs rule, degraded settings, Targeted inputs, the
typed Targeted error, and the FCX setup context: saved setup for the managed game, the Fallout 4 VR
XSE log, missing folders still launching, the FCX Mode override on a Targeted intent, and the typed
`xse_log_inspect` error. FCX fixtures name the Installation Root through an
`{{installationRoot}}` placeholder each runner fills, and scenarios list empty `files` to create
beneath it. It runs through the shared scan-run launcher with one runner per adapter, each traversing its
own DTOs (ADR-0008); see [`binding-compliance-suite.md`](binding-compliance-suite.md).

## Tests

- `tests/launch_behavior.rs` — temp-dir User Settings fixtures through the public interface.
- `tests/game_differs.rs` — the game-differs rule: each withheld saved value and its diagnostic, nothing reported for the managed game, overrides still winning, and Targeted intents.
- `tests/fcx_setup_context.rs` — the FCX setup context, the game executable rule, the XSE log and
  its typed error, and the FCX override for a non-managed game (no saved folders).
- `tests/dependency_boundary.rs` — the manifest boundary above.
- `tests/launch_conformance.rs` — the Rust conformance runner (skips without a run plan).
- `src/lib_tests.rs` — `MaxConcurrency::from_count` and Vocabulary conformance.
