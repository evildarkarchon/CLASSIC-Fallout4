# FormID Settings Boundary

Contributor-facing notes for the current FormID database settings split between [`classic-config-core`](../../business-logic/classic-config-core), typed [`classic-user-settings-core`](../../business-logic/classic-user-settings-core), and scan-time intake in [`classic-scanlog-core`](../../business-logic/classic-scanlog-core), consumed by [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge).

This page is intentionally narrow. It documents the active source-backed boundary contributors hit when tracing why configured FormID database paths do or do not affect scan startup.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page when you need to:

- understand which settings shape `classic-config-core` persists today
- understand which settings shape active scan startup consumes through Crash Log Scan Intake today
- trace how GUI or binding surfaces fit into that split
- debug why a FormID database path saved through one surface does not show up during scanning

This page describes behavior visible in active Rust and C++-facing source today. It does not propose a future migration plan.

---

## Current Boundary At A Glance

There are three active representations for per-game FormID database paths. Typed User Settings is the canonical persisted choice, and the native CLI and GUI scan adapters project the selected game's entries into explicit scan facts. `ClassicConfig.formid_databases` remains a separate compatibility representation.

## `classic-config-core` representation

[`business-logic/classic-config-core/src/config.rs`](../../business-logic/classic-config-core/src/config.rs) defines:

- `ClassicConfig.formid_databases: HashMap<String, Vec<PathBuf>>`
- YAML key: top-level `formid_databases`
- shape: snake_case map from game name to zero or more paths

## `classic-user-settings-core` representation

[`business-logic/classic-user-settings-core/src/scan_settings.rs`](../../business-logic/classic-user-settings-core/src/scan_settings.rs) defines:

- `CrashLogScanSettings::formid_databases() -> &BTreeMap<String, Vec<String>>`
- canonical YAML key: `CLASSIC_Settings.FormID Databases`
- shape: game-name map from each game to zero or more unnormalized path strings
- missing or untrusted values: an empty map with `PreferenceOrigin::Default` or `DegradedFallback`

The typed read path retains relative strings exactly; Crash Log Scan preparation remains responsible for resolving them against CLASSIC Data. `UserSettingsUpdate::with_formid_databases(...)` can validate a replacement mapping as part of an all-or-nothing, non-persisting preview. It does not save the mapping.

## Scan-startup intake representation

[`business-logic/classic-scanlog-core/src/scan_intake.rs`](../../business-logic/classic-scanlog-core/src/scan_intake.rs) accepts:

- `CrashLogScanFacts.formid_database_paths: Vec<PathBuf>`
- one caller-projected path list for the selected game
- relative or absolute paths without any User Settings document/key knowledge

Important contributor takeaway:

- these are not the same persisted representation
- `classic-user-settings-core` owns the typed canonical projection; the native CLI and GUI select the effective game and copy only that game's rows into `ScanRunRequestDto.formid_database_paths`
- active scan startup does not currently read `ClassicConfig.formid_databases`
- `ClassicConfig::load_from_yaml()` does not currently read `CLASSIC_Settings.FormID Databases.{game}` into `formid_databases`
- `classic-cpp-bridge` converts the request vector into `CrashLogScanFacts`; scanlog-core owns path resolution, built-in ordering, and de-duplication

---

## What `classic-config-core` Persists And Loads Today

`ClassicConfig` is the active Rust settings model for runtime configuration APIs.

Source-backed behavior from `config.rs`:

- `Default::default()` initializes `formid_databases` as an empty `HashMap`
- `from_yaml()` reads only the top-level `formid_databases` key
- each game key maps to a `Vec<PathBuf>` and preserves multiple paths per game
- missing `formid_databases` defaults to an empty map
- `to_yaml()` writes only the top-level `formid_databases` key when the map is non-empty
- `validate_paths()` checks `game_root`, `ini_folder`, `scan_custom`, and `mods_folder`, but not FormID database files

Grounded YAML shape for the Rust config model:

```yaml
formid_databases:
  Fallout4:
    - databases/FOLON FormIDs.db
    - D:/Custom/My FormIDs.db
  Skyrim: []
```

Source-backed test coverage in the same file confirms:

- empty-by-default behavior
- missing-key fallback to empty
- multi-path round-trip for one game
- preservation of an explicit empty list such as `Skyrim: []`

Practical limit:

- this crate stores path strings as `PathBuf`s but does not resolve relative entries during load or save

---

## What Crash Log Scan Intake Reads At Scan Startup Today

Native CLI scan startup opens `CrashLogScanSettingsDto`, selects the flattened rows for the effective game, and sends them through `ScanRunRequestDto.formid_database_paths`. Native GUI settings load opens one `GuiSettingsSnapshotDto`; at scan startup its Qt adapter creates an immutable `CrashLogScanLaunchSettings` from that accepted revision, selecting the effective game's FormID rows. `buildScanRunRequest(...)` copies those rows into the same request field. The C++ bridge creates `CrashLogScanFacts`, then `CrashLogScanRunService` attaches those facts to `CrashLogScanIntake::from_yaml_paths(...).prepare()`.

Current path assembly order is:

1. main DB: `<yaml_dir_data>/databases/{game} FormIDs Main.db`
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
- the preserved lower-level `build_full_scan_config()` shape can still prepare config and create an orchestrator with built-in paths only

---

## Where Bindings And UI Surfaces Fit

The active repo surfaces are split across this same boundary.

## Surfaces that expose `ClassicConfig.formid_databases`

These wrappers expose the Rust `ClassicConfig` field directly:

- [`node-bindings/classic-node/src/config.rs`](../../node-bindings/classic-node/src/config.rs)
- [`python-bindings/classic-config-py/src/lib.rs`](../../python-bindings/classic-config-py/src/lib.rs)

Current binding behavior:

- getters return `HashMap<String, Vec<String>>`
- setters write back into `ClassicConfig.formid_databases`
- the Node test suite covers round-trip behavior for `Fallout4` and `Skyrim`

These bindings mirror the Rust config model. They do not, in the inspected source, redirect scan startup to the canonical nested User Settings key.

## Surfaces that expose typed User Settings FormID databases

The CXX, Node, and Python User Settings adapters expose `CrashLogScanSettings.formid_databases` from the canonical nested document together with its preference origin. Their update-preview adapters validate requested replacement maps without writing. The native CLI consumes the narrow CXX typed group. The native GUI consumes the aggregate `GuiSettingsSnapshotDto`, whose four settings groups come from one source revision, then projects explicit `CrashLogScanFacts` through its immutable launch object.

## Native GUI typed edit and scan-launch surface

[`classic-gui/src/core/guiusersettings.cpp`](../../classic-gui/src/core/guiusersettings.cpp) is the Qt-facing adapter for the cohesive CXX snapshot. [`classic-gui/src/app/settingsdialog.cpp`](../../classic-gui/src/app/settingsdialog.cpp) loads the additional-database list from that typed snapshot and submits the full per-game map through the revision-aware User Settings Update seam.

Contributor-visible GUI details:

- the list is still labeled `Additional FormID Databases`
- helper text still says the built-in database is always included
- accepting the dialog previews and commits FormID rows with every other selected setting as one atomic update
- cancel performs no update; rejection writes nothing; a stale revision reports a conflict and preserves the newer document
- the preservation-aware Rust patch retains unknown keys, unrelated known-invalid values, and other games' FormID lists

[`classic-gui/src/workers/scanrequestbuilder.cpp`](../../classic-gui/src/workers/scanrequestbuilder.cpp) is the GUI's separate scan-request boundary. `MainWindow` derives `CrashLogScanLaunchSettings` from the accepted cached snapshot, and the controller and worker forward that immutable value. Scan launch neither reopens User Settings nor reads `CLASSIC_Settings.FormID Databases.{game}` through generic YAML operations.

---

## Why This Matters When Debugging Missing DB Paths

This split is the main source-backed reason a contributor can see "saved" FormID DB paths that do not affect real scans.

Common failure patterns:

- a path saved through `ClassicConfig::save_to_yaml()` appears under top-level `formid_databases`, but native scan startup ignores it because the CLI consumes typed User Settings instead
- a path accepted by the GUI appears under `CLASSIC_Settings.FormID Databases.{game}` and is reflected in the newly accepted typed snapshot; scan launch deliberately uses that snapshot rather than reopening or rediscovering the key
- a relative path may look correct in YAML but resolves under `yaml_dir_data` (`CLASSIC Data`), not relative to the settings file itself
- a missing DB file may not fail scan startup loudly because `DatabasePool::initialize()` later skips nonexistent files with a warning instead of a hard error

Practical debugging rule:

- if the problem is "scan did not load my extra DB," inspect the typed snapshot and the adapter's selected `formid_database_paths` rows, then verify the path resolves under `CLASSIC Data` for relative entries
- if the problem is "Rust config API did not round-trip my DB list," inspect the top-level `formid_databases` key instead

---

## Limits And Caveats

These details are source-backed today and matter for contributors, but they should not be treated as an implied future design.

- `classic-scanlog-core` intake has no User Settings discovery or raw-key behavior; callers must provide configured paths explicitly
- the native CLI consumes the typed group and the native GUI consumes the cohesive typed snapshot; other adapters remain responsible for projecting their own `CrashLogScanFacts`
- `classic-config-core` currently ignores the nested `CLASSIC_Settings.FormID Databases.{game}` path
- `classic-config-core` path validation does not validate FormID database files
- bridge path normalization uses `path.components().collect()`; it does not canonicalize case or resolve symlinks
- bridge de-duplication is path-based, not content-based
- missing files are filtered later by [`classic-database-core`](../../business-logic/classic-database-core) during `DatabasePool::initialize()`, not during settings parsing
- for `Fallout4` and `Fallout4VR`, the hardcoded `FOLON FormIDs.db` path is included even when the user list is empty

---

## Related Docs

- [`classic-config-core.md`](classic-config-core.md) - full Rust config API and runtime settings model
- [`classic-user-settings-core.md`](classic-user-settings-core.md) - typed canonical User Settings projection and update preview
- [`classic-scanlog-core.md`](classic-scanlog-core.md) - Crash Log Scan Intake and downstream analysis
- [`classic-database-core.md`](classic-database-core.md) - database pool initialization and missing-file behavior
- [`formid-sqlite-conventions.md`](formid-sqlite-conventions.md) - broader fixture, schema, lookup, and path rules for FormID DB work
