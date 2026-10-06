# FormID Settings Boundary

Contributor-facing notes for the FormID database boundary between typed [`classic-user-settings-core`](../../business-logic/classic-user-settings-core) and explicit scan-time facts in [`classic-scanlog-core`](../../business-logic/classic-scanlog-core), consumed by the maintained adapters.

This page is intentionally narrow. It documents the active source-backed boundary contributors hit when tracing why configured FormID database paths do or do not affect scan startup.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page when you need to:

- understand the canonical typed User Settings shape
- understand which settings shape active scan startup consumes through Crash Log Scan Intake today
- trace how GUI or binding surfaces fit into that split
- debug why a FormID database path saved through one surface does not show up during scanning

This page describes behavior visible in active Rust and C++-facing source today. It does not propose a future migration plan.

---

## Current Boundary At A Glance

There are two active representations for per-game FormID database paths: the canonical persisted typed User Settings map and the selected game's explicit scan-startup facts.

## `classic-user-settings-core` representation

[`business-logic/classic-user-settings-core/src/scan_settings.rs`](../../business-logic/classic-user-settings-core/src/scan_settings.rs) defines:

- `CrashLogScanSettings::formid_databases() -> &BTreeMap<String, Vec<String>>`
- canonical YAML key: `CLASSIC_Settings.FormID Databases`
- shape: game-name map from each game to zero or more unnormalized path strings
- missing or untrusted values: an empty map with `PreferenceOrigin::Default` or `DegradedFallback`

The typed read path retains relative strings exactly; Crash Log Scan preparation remains responsible for resolving them against CLASSIC Data. `UserSettingsUpdate::with_formid_databases(...)` can validate a replacement mapping as part of an all-or-nothing, non-persisting preview. It does not save the mapping.

### Game-aware scan read (the VR read rule)

`CrashLogScanSettings::formid_databases_for_game(game: GameId) -> Vec<&str>` is the only scan-selection read of that map. Frontends never pick rows out of `formid_databases()` for a scan, and none keeps its own game-to-key mapping. Crash Log Scan Launch ([`classic-scan-launch.md`](classic-scan-launch.md)) uses the same read for the scanned game when it builds a request, so a launched request carries exactly these rows.

- **Fallout 4 VR** shares the Fallout 4 corpus, as it already does for the Main database and YAML Data. Reading for `Fallout4VR` returns the `Fallout4` rows followed by any legacy `Fallout4VR` rows, de-duplicated with the first occurrence kept. Older documents that saved VR rows under `Fallout4VR` keep working.
- **Every other game** (`Fallout4`, `Skyrim`, `Starfield`) reads exactly the rows saved under its own key, with no de-duplication. A Fallout 4 (non-VR) scan never reads `Fallout4VR` rows, so it sees exactly the rows it saw before this rule.
- The raw keyed map stays readable through `formid_databases()`, and the stored document shape is unchanged. The write side is the game-aware save below.

Bindings expose the same rule as a precomputed per-game projection taken from one snapshot, so it cannot drift from the raw map:

| Surface | Field | Shape |
| --- | --- | --- |
| CXX | `CrashLogScanSettingsDto::scan_formid_database_paths` | `FormIdDatabasePathDto { game, path }` rows grouped in supported-game order |
| Node | `JsCrashLogScanSettings.scanFormidDatabases` | `Record<string, string[]>` keyed by game token |
| Python | `CrashLogScanSettings.scan_formid_databases` | `dict[str, list[str]]` keyed by game token |

Games whose scan reads no rows are absent from all three. The `user-settings` conformance pack pins the rule with the `canonical-current-nested` (Fallout4 rows only), `vr-shared-and-legacy-formid-databases` (both keys, with a duplicate), and `vr-legacy-formid-databases` (legacy VR rows only) scenarios through the `scan_formid_databases` observation field.

### Game-aware save (the VR save rule)

`UserSettingsUpdate::with_formid_databases_for_game(game, paths)` is the only way a frontend saves one game's rows; none rewrites the raw map by its own game key.

- **Fallout 4 VR**: the rows are stored under `Fallout4` and a legacy `Fallout4VR` key is removed. The removal is never silent: it is reported as `legacy_formid_databases_key_removed` (field `/CLASSIC_Settings/FormID Databases`) on `AcceptedUserSettingsUpdate::diagnostics()` before commit, and again on `UserSettingsCommitOutcome::Committed { diagnostics, .. }`.
- **Every other game** replaces only its own key; every other game's rows, including legacy `Fallout4VR` rows, are preserved.
- The save publishes the complete resulting mapping as the one accepted `FormID Databases` field, anchored to the preview revision, so the stored document shape is unchanged.

| Surface | Save request | Effect diagnostics |
| --- | --- | --- |
| CXX | `UserSettingsUpdateDto::has_formid_database_save`, `formid_database_save_game`, `formid_database_save_paths` | `UserSettingsUpdatePreviewDto::diagnostics` when accepted; `UserSettingsCommitResultDto::diagnostics` when committed |
| Node | `JsUserSettingsUpdate.formidDatabasesForGame: { game: JsGameId, paths }` | `JsUserSettingsUpdatePreview.diagnostics` when accepted; `JsUserSettingsCommitResult.diagnostics` when committed |
| Python | `UserSettingsUpdate.set_formid_databases_for_game(game, paths)` | `UserSettingsUpdatePreview.diagnostics` when accepted; `UserSettingsCommitOutcome.diagnostics` when committed |

The GUI Settings dialog lists `GuiCrashLogScanSettings::scanFormIdDatabases` for the managed game (so a VR user with legacy rows sees the merged list), saves through `GuiUserSettingsChanges::formIdDatabaseSave`, and shows any committed effect diagnostics in an information box. The `user-settings` conformance pack pins the rule with `commit-fallout4-vr-formid-save-removes-legacy-key`, `commit-other-game-formid-save-preserves-every-other-game`, and `preview-fallout4-formid-save-keeps-legacy-vr-rows`; a requested selector `/CLASSIC_Settings/FormID Databases/<game>` names the save.

## Scan-startup intake representation

[`business-logic/classic-scanlog-core/src/scan_intake.rs`](../../business-logic/classic-scanlog-core/src/scan_intake.rs) accepts:

- `CrashLogScanFacts.formid_database_paths: Vec<PathBuf>`
- one caller-projected path list for the selected game
- relative or absolute paths without any User Settings document/key knowledge

Important contributor takeaway:

- the typed map is the only persisted representation
- `classic-user-settings-core` owns the typed canonical projection and the game-aware scan read; the native CLI copies the effective game's Rust-selected rows into `ScanRunConfigurationDto.formid_database_paths`, while the GUI projects its selected rows through its native launch request
- `classic-cpp-bridge` converts the request vector into `CrashLogScanFacts`; scanlog-core owns path resolution, built-in ordering, and de-duplication

---

## What Crash Log Scan Intake Reads At Scan Startup Today

Native CLI scan startup opens `CrashLogScanSettingsDto`, selects the `scan_formid_database_paths` rows for the effective game, and sends them through `ScanRunConfigurationDto.formid_database_paths` into a tagged final-contract request. The native GUI launches through Crash Log Scan Launch, which selects the managed game's rows in Rust when the scan starts; its settings snapshot keeps the same Rust-selected projection (`GuiCrashLogScanSettings::scanFormIdDatabases`) only for the Settings dialog. The C++ bridge creates `CrashLogScanFacts`, and the Rust-owned Crash Log Scan Run attaches those facts to `CrashLogScanIntake::from_installed_yaml_data(...).prepare()`. Intake receives the immutable snapshot selected once from the request's installation root and typed game and does not reopen selected Main, game, or Local Ignore paths.

Current path assembly order is:

1. main DB: `<yaml_dir_data>/databases/{game-data-identity} FormIDs Main.db` (`Fallout4VR` shares `Fallout4 FormIDs Main.db`)
2. hardcoded extras from `hardcoded_formid_db_relpaths(game)`
3. caller-projected configured paths from `CrashLogScanFacts.formid_database_paths`
4. de-duplicate normalized paths while preserving first occurrence

Current hardcoded extras:

- `Fallout4` -> `databases/FOLON FormIDs.db`
- `Fallout4VR` -> `databases/FOLON FormIDs.db`
- other games -> none

Current typed-facts details:

- Crash Log Scan Intake never opens or persists User Settings
- the native CLI gets paths from the Rust-typed `CrashLogScanSettingsDto`, and the native GUI gets them from the cohesive `GuiSettingsSnapshotDto`; neither scan-launch path uses generic YAML operations
- relative configured paths are resolved against `yaml_dir_data` (`CLASSIC Data`)
- absolute configured paths are used as-is after normalization
- existence is not checked during path assembly

Grounded canonical User Settings shape projected by both native adapters:

```yaml
CLASSIC_Settings:
  FormID Databases:
    Fallout4:
      - databases/FOLON FormIDs.db
      - databases/custom.db
```

With `yaml_dir_data = <root>/CLASSIC Data`, the bridge resolves that to:

- `<root>/CLASSIC Data/databases/Fallout4 FormIDs Main.db`
- `<root>/CLASSIC Data/databases/FOLON FormIDs.db`
- `<root>/CLASSIC Data/databases/custom.db`

Intake and bridge adapter tests cover contributor-relevant cases:

- an empty typed path list still yields main DB plus hardcoded `FOLON FormIDs.db`
- a configured entry that duplicates the hardcoded FOLON path is removed by de-duplication
- a sentinel User Settings document with values that would fail the old raw reader is not opened by intake
- the GUI request-builder behavior test forwards both relative and absolute configured FormID rows from one typed launch object without opening User Settings
- a final-contract request with no configured FormID rows still executes with
  the built-in database paths selected by Rust-owned intake

---

## Where Bindings And UI Surfaces Fit

The active repo surfaces are split across this same boundary.

## Retired flat binding surface

Node and Python do not expose a flat settings facade. Their inspection and scan-start paths use the canonical typed User Settings group.

## Surfaces that expose typed User Settings FormID databases

The CXX, Node, and Python User Settings adapters expose `CrashLogScanSettings.formid_databases` from the canonical nested document together with its preference origin, plus the game-aware scan projection described above. Their update-preview adapters validate requested replacement maps without writing. The native CLI consumes the narrow CXX typed group; the Node CLI reads the scanned game's rows from `scanFormidDatabases` and supplies them as `JsScanRunConfiguration.formidDatabasePaths`; the Python CLI reads the managed game's rows from `scan_formid_databases`. `scanRunExecute` consumes only that explicit request configuration. The native GUI consumes the aggregate `GuiSettingsSnapshotDto`, whose four settings groups come from one source revision. The Rust TUI opens the same core snapshot directly and calls `formid_databases_for_game` for the managed game. Every maintained frontend takes the scanned game's rows from the Rust read and projects explicit `CrashLogScanFacts`; scanlog core never opens a settings document.

The CLI, GUI, and TUI `*.settings-scan-projection` consumer obligations in `tests/conformance/consumer-obligations.json` each observe a Fallout 4 case and a Fallout 4 VR managed-game case through the frontend's own scan-launch boundary.

## Native GUI typed edit and scan-launch surface

[`classic-gui/src/core/guiusersettings.cpp`](../../classic-gui/src/core/guiusersettings.cpp) is the Qt-facing adapter for the cohesive CXX snapshot. [`classic-gui/src/app/settingsdialog.cpp`](../../classic-gui/src/app/settingsdialog.cpp) loads the additional-database list from the snapshot's Rust-selected `scanFormIdDatabases` rows for the managed game and submits the edited list as one game-aware save (`formIdDatabaseSave`) through the revision-aware User Settings Update seam; it never reads or writes the raw map by the managed game's key.

Contributor-visible GUI details:

- the list is still labeled `Additional FormID Databases`
- helper text still says the built-in database is always included
- accepting the dialog previews and commits FormID rows with every other selected setting as one atomic update
- cancel performs no update; rejection writes nothing; a stale revision reports a conflict and preserves the newer document
- the preservation-aware Rust patch retains unknown keys, unrelated known-invalid values, and other games' FormID lists
- a committed save that removed a legacy `Fallout4VR` key shows the `legacy_formid_databases_key_removed` diagnostic in a `Settings Saved` information box

A GUI Crash Log Scan does not read FormID rows from the snapshot at all. [`classic-gui/src/workers/scanlaunch.cpp`](../../classic-gui/src/workers/scanlaunch.cpp) launches through Rust's Crash Log Scan Launch with the Installation Root and no overrides, and the launch selects the scanned game's rows with `formid_databases_for_game` (see [`classic-scan-launch.md`](classic-scan-launch.md)). Neither path reads `CLASSIC_Settings.FormID Databases.{game}` through generic YAML operations.

---

## Why This Matters When Debugging Missing DB Paths

The typed-snapshot-to-explicit-facts handoff is the main place to inspect when a saved FormID DB path does not affect a scan.

Common failure patterns:

- a path accepted by the GUI appears under `CLASSIC_Settings.FormID Databases.{game}`; a GUI scan reads it through Crash Log Scan Launch, which reopens User Settings read-only when the scan starts
- a relative path may look correct in YAML but resolves under `yaml_dir_data` (`CLASSIC Data`), not relative to the settings file itself
- a missing DB file may not fail scan startup loudly because `DatabasePool::initialize()` later skips nonexistent files with a warning instead of a hard error

Practical debugging rule:

- if the problem is "scan did not load my extra DB," inspect the typed snapshot and the adapter's selected `formid_database_paths` rows, then verify the path resolves under `CLASSIC Data` for relative entries
- for a Fallout 4 VR scan, remember the read rule: rows saved under `Fallout4` apply, followed by any legacy `Fallout4VR` rows; a Fallout 4 scan never reads `Fallout4VR` rows

---

## Limits And Caveats

These details are source-backed today and matter for contributors, but they should not be treated as an implied future design.

- `classic-scanlog-core` intake has no User Settings discovery or raw-key behavior; callers must provide configured paths explicitly
- the native CLI consumes the typed group and the native GUI consumes the cohesive typed snapshot; other adapters remain responsible for projecting their own `CrashLogScanFacts`, always from the game-aware read
- bridge path normalization uses `path.components().collect()`; it does not canonicalize case or resolve symlinks
- bridge de-duplication is path-based, not content-based
- missing files are filtered later by [`classic-database-core`](../../business-logic/classic-database-core) during `DatabasePool::initialize()`, not during settings parsing
- for `Fallout4` and `Fallout4VR`, the hardcoded `FOLON FormIDs.db` path is included even when the user list is empty

---

## Related Docs

- [`classic-user-settings-core.md`](classic-user-settings-core.md) - typed canonical User Settings projection and update preview
- [`classic-scanlog-core.md`](classic-scanlog-core.md) - Crash Log Scan Intake and downstream analysis
- [`classic-database-core.md`](classic-database-core.md) - database pool initialization and missing-file behavior
- [`formid-sqlite-conventions.md`](formid-sqlite-conventions.md) - broader fixture, schema, lookup, and path rules for FormID DB work
