# FormID Settings Boundary

Contributor-facing notes for the current FormID database settings split between [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core) and [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge).

This page is intentionally narrow. It documents the active source-backed boundary contributors hit when tracing why configured FormID database paths do or do not affect scan startup.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page when you need to:

- understand which settings shape `classic-config-core` persists today
- understand which settings shape active scan startup in `classic-cpp-bridge` consumes today
- trace how GUI or binding surfaces fit into that split
- debug why a FormID database path saved through one surface does not show up during scanning

This page describes behavior visible in active Rust and C++-facing source today. It does not propose a future migration plan.

---

## Current Boundary At A Glance

There are two different active representations for per-game FormID database paths.

## `classic-config-core` representation

[`ClassicLib-rs/business-logic/classic-config-core/src/config.rs`](../../ClassicLib-rs/business-logic/classic-config-core/src/config.rs) defines:

- `ClassicConfig.formid_databases: HashMap<String, Vec<PathBuf>>`
- YAML key: top-level `formid_databases`
- shape: snake_case map from game name to zero or more paths

## `classic-cpp-bridge` scan-startup representation

[`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs) reads:

- YAML key path: `CLASSIC_Settings.FormID Databases.{game}`
- source file search order: `CLASSIC Settings.yaml`, then `CLASSIC_Settings.yaml`
- shape: legacy nested settings tree read through `YamlOperations`

Important contributor takeaway:

- these are not the same YAML key
- active scan startup does not currently read `ClassicConfig.formid_databases`
- `ClassicConfig::load_from_yaml()` does not currently read `CLASSIC_Settings.FormID Databases.{game}` into `formid_databases`

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

## What `classic-cpp-bridge` Reads At Scan Startup Today

Active scan startup goes through `build_full_scan_config()` and `resolve_formid_db_paths()` in [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs).

Current path assembly order is:

1. main DB: `<yaml_dir_data>/databases/{game} FormIDs Main.db`
2. hardcoded extras from `hardcoded_formid_db_relpaths(game)`
3. user paths from `CLASSIC_Settings.FormID Databases.{game}`
4. de-duplicate normalized paths while preserving first occurrence

Current hardcoded extras:

- `Fallout4` -> `databases/FOLON FormIDs.db`
- `Fallout4VR` -> `databases/FOLON FormIDs.db`
- other games -> none

Current settings-read details:

- the bridge checks `CLASSIC Settings.yaml` first, then `CLASSIC_Settings.yaml`
- it loads the file with `YamlOperations`, not `ClassicConfig`
- relative user paths are resolved against `yaml_dir_data` (`CLASSIC Data`)
- absolute user paths are used as-is after normalization
- existence is not checked during path assembly

Grounded legacy YAML shape consumed by scan startup:

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

Bridge tests currently cover two contributor-relevant cases:

- an explicit empty `CLASSIC_Settings.FormID Databases.Fallout4: []` still yields main DB plus hardcoded `FOLON FormIDs.db`
- a user entry that duplicates the hardcoded FOLON path is removed by de-duplication

---

## Where Bindings And UI Surfaces Fit

The active repo surfaces are split across this same boundary.

## Surfaces that expose `ClassicConfig.formid_databases`

These wrappers expose the Rust `ClassicConfig` field directly:

- [`ClassicLib-rs/node-bindings/classic-node/src/config.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/config.rs)
- [`ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs`](../../ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs)

Current binding behavior:

- getters return `HashMap<String, Vec<String>>`
- setters write back into `ClassicConfig.formid_databases`
- the Node test suite covers round-trip behavior for `Fallout4` and `Skyrim`

These bindings mirror the Rust config model. They do not, in the inspected source, redirect scan startup to the legacy nested key.

## Surface that still uses the legacy nested settings path

[`classic-gui/src/app/settingsdialog.cpp`](../../classic-gui/src/app/settingsdialog.cpp) still reads and writes:

- `CLASSIC_Settings.FormID Databases.{game}`

Contributor-visible GUI details:

- the list is labeled `Additional FormID Databases`
- helper text says the built-in database is always included
- load and save both use `yaml_ops_get_vec()` / `yaml_ops_set_vec_setting()` against the legacy nested key

That means the GUI is currently aligned with active scan startup in `classic-cpp-bridge`, not with `ClassicConfig` YAML serialization.

---

## Why This Matters When Debugging Missing DB Paths

This split is the main source-backed reason a contributor can see "saved" FormID DB paths that do not affect real scans.

Common failure patterns:

- a path saved through `ClassicConfig::save_to_yaml()` appears under top-level `formid_databases`, but active scan startup ignores it because the bridge only reads `CLASSIC_Settings.FormID Databases.{game}`
- a path saved through the GUI appears under `CLASSIC_Settings.FormID Databases.{game}` and affects scanning, but `ClassicConfig::load_from_yaml()` still shows an empty `formid_databases` map if no top-level key exists
- a relative path may look correct in YAML but resolves under `yaml_dir_data` (`CLASSIC Data`), not relative to the settings file itself
- a missing DB file may not fail scan startup loudly because `DatabasePool::initialize()` later skips nonexistent files with a warning instead of a hard error

Practical debugging rule:

- if the problem is "scan did not load my extra DB," inspect `CLASSIC_Settings.FormID Databases.{game}` first, then verify the path resolves under `CLASSIC Data` for relative entries
- if the problem is "Rust config API did not round-trip my DB list," inspect the top-level `formid_databases` key instead

---

## Limits And Caveats

These details are source-backed today and matter for contributors, but they should not be treated as an implied future design.

- `classic-cpp-bridge` currently reads settings YAML directly instead of loading `ClassicConfig`
- `classic-config-core` currently ignores the legacy nested `CLASSIC_Settings.FormID Databases.{game}` path
- `classic-config-core` path validation does not validate FormID database files
- bridge path normalization uses `path.components().collect()`; it does not canonicalize case or resolve symlinks
- bridge de-duplication is path-based, not content-based
- missing files are filtered later by [`classic-database-core`](../../ClassicLib-rs/business-logic/classic-database-core) during `DatabasePool::initialize()`, not during settings parsing
- for `Fallout4` and `Fallout4VR`, the hardcoded `FOLON FormIDs.db` path is included even when the user list is empty

---

## Related Docs

- [`classic-config-core.md`](classic-config-core.md) - full Rust config API and runtime settings model
- [`classic-database-core.md`](classic-database-core.md) - database pool initialization and missing-file behavior
- [`formid-sqlite-conventions.md`](formid-sqlite-conventions.md) - broader fixture, schema, lookup, and path rules for FormID DB work
