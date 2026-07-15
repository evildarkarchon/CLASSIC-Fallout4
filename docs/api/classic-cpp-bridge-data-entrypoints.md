# `classic-cpp-bridge` Data Entry Points

Contributor-facing documentation for the active C++ bridge entry points in:

- [`cpp-bindings/classic-cpp-bridge/src/settings.rs`](../../cpp-bindings/classic-cpp-bridge/src/settings.rs) (renamed from `yaml.rs` during v9.1.0 Phase 1 Plan 2)
- [`cpp-bindings/classic-cpp-bridge/src/config.rs`](../../cpp-bindings/classic-cpp-bridge/src/config.rs)
- [`cpp-bindings/classic-cpp-bridge/src/files.rs`](../../cpp-bindings/classic-cpp-bridge/src/files.rs)
- [`cpp-bindings/classic-cpp-bridge/src/database.rs`](../../cpp-bindings/classic-cpp-bridge/src/database.rs)
- [`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs)
- [`cpp-bindings/classic-cpp-bridge/src/update.rs`](../../cpp-bindings/classic-cpp-bridge/src/update.rs)

This page is the companion to [`classic-cpp-bridge-game-entrypoints.md`](classic-cpp-bridge-game-entrypoints.md). It documents the current CXX FFI surface that active C++ callers use for YAML operations, config loading, file utilities, FormID database access, crash-log scanning, and Papyrus monitoring.

It is intentionally about the bridge surface that exists in source today. It does **not** describe a future unified bridge and it does **not** imply that the bridge exposes every capability of the underlying Rust crates.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page when you need to understand:

- which bridge file owns which `classic::*` C++ namespace
- which Rust business-logic crate each exported function actually calls
- where the bridge returns opaque wrappers, flattened DTOs, preformatted strings, or fail-soft primitives
- where the bridge narrows, hardcodes, or drops part of the lower-level Rust API
- how to debug contributor issues that appear in the C++ frontend but originate in Rust config, file, database, or scanlog code

This page is for contributors working on the active Rust/C++ path.

For crate-level behavior, see:

- [`classic-config-core.md`](classic-config-core.md)
- [`classic-file-io-core.md`](classic-file-io-core.md)
- [`classic-database-core.md`](classic-database-core.md)
- [`classic-scanlog-core.md`](classic-scanlog-core.md)
- [`formid-settings-boundary.md`](formid-settings-boundary.md)

---

## Current Bridge Ownership

## `src/settings.rs` -> `classic::settings`

This file (formerly `src/yaml.rs` -> `classic::yaml`; renamed during v9.1.0 Phase 1 Plan 2) exposes a stateful `YamlOps` wrapper over `classic_settings_core::YamlOperations` plus bridge-local `YamlValue` and `YamlCacheStatsDto` DTOs that CXX can move by value, AND the D-09 expansion surface: generic settings-core cache operations and scalar validator helpers mirroring the Python surface.

It owns:

- YAML parse/load/save helpers through `yaml_ops_*`
- typed setting inspection and mutation helpers through `YamlValue`
- YAML (path-backed) cache helpers `yaml_ops_clear_cache()`, `yaml_ops_cache_stats()`, and the narrowed `yaml_ops_cache_size()` adapter
- settings-core cache-populating loaders `settings_load_sync`, `settings_load_async_blocking`, `settings_load_batch_sync`, `settings_load_batch_async_blocking` (return a `u32` doc count; the full `Arc<Vec<Yaml>>` does not cross CXX)
- settings-core cache observability: `settings_cache_stats` (returns `SettingsCacheStats`), `settings_cache_size`, `settings_cache_keys`, `settings_is_cached`, `settings_invalidate`, `settings_clear_cache`, `settings_reset_cache_stats`
- generic scalar validators mirroring the Python surface: `settings_validate_value` and `settings_coerce_value` (returns `SettingsCoercedValue`)

Current cache-observability behavior:

- `yaml_ops_cache_stats()` forwards to the canonical `classic_settings_core::yaml_cache_stats()` contract with `hits`, `misses`, `hit_rate`, `size`, and `capacity` — returned through the `YamlCacheStatsDto` shared struct (renamed from a pre-existing `CacheStats` DTO during Phase 1 Plan 2 to avoid collision with the new `SettingsCacheStats`)
- `yaml_ops_cache_size()` stays as `yaml_ops_cache_stats().size` for older C++ callers
- `settings_cache_stats()` forwards to `classic_settings_core::cache_stats()` and returns `SettingsCacheStats`; this is a distinct cache (capacity `64`) from the yaml file cache (capacity `128`)
- YAML-specific legacy byte totals remain on the Rust side through `YamlOperations::get_cache_stats()` and are not widened into either DTO

Two CXX type-system exceptions (bridge-internal design notes):

- `get_cached()` returning `Option<Arc<Vec<Yaml>>>` cannot cross the CXX boundary; the bridge does not expose it. Callers fall back to `yaml_ops_*` when they need parsed YAML documents back out.
- `load_settings_*()` Rust APIs return `Arc<Vec<Yaml>>`; the bridge's `settings_load_*` variants return only a `u32` doc count because `Arc<Vec<Yaml>>` is not CXX-movable.

## `src/config.rs` -> `classic::config`

This file exposes a mostly read-oriented bridge around `classic_config_core::YamlDataCore`, a small Local-YAML path persistence helper, and settings-cache observability helpers that forward into `classic_settings_core`.

It owns:

- YAML dataset loading through `yaml_data_load(...)`
- Local-YAML path persistence through `save_local_yaml_paths(...)`
- field getters for selected scalar and `Vec<String>` values
- flattened `IndexMap` access for suspect and mod dictionaries
- settings cache helpers `settings_cache_clear()`, `settings_cache_stats()`, `settings_cache_size()`, and `reset_settings_cache_stats()`

It does not expose the full `YamlDataCore` model, any User Settings save API, or raw crashgen registry data.

## `src/files.rs` -> `classic::files`

This file is the mixed file-operations bridge.

It owns:

- typed backup workflows through `classic_file_io_core::backup::BackupManager`
- generic file-group backup, restore, and remove through `classic_file_io_core::game_files::GameFilesManager`
- crash-log collection through `classic_file_io_core::log_collection::LogCollector`
- hash cache helpers `hash_cache_clear()`, `hash_cache_stats()`, `hash_cache_size()`, and `reset_hash_cache_stats()` through `classic_file_io_core::hash::FileHasher`
- small standalone helpers for file similarity, encoding-aware reads and writes, and AUTOSCAN report files

Some report-file helpers are bridge-local convenience code, not direct crate re-exports.

## `src/update.rs` -> `classic::update`

This file exposes the native update bridge for binary update compatibility, app-update notifications, and YAML Data updates.

For YAML Data, native CLI/GUI callers use the first-party helpers:

- `yaml_data_check_update(enabled) -> YamlUpdateStatusDto`
- `yaml_data_apply_update(enabled, approved) -> YamlUpdateReportDto`
- `yaml_data_rollback_update() -> YamlRollbackReportDto`

These helpers forward to `classic_update_core::yaml_update` first-party functions. Rust owns the Pages URL shape, `yaml-data-v*` tag namespace, shippable YAML file list, accepted schema ranges, installed-file enrichment, and rollback targets. The bridge only passes the user's `Update Check` policy bit and the reviewed `ApprovedUpdateDto` identity captured from a prior check.

The lower-level compatibility helpers remain public:

- `yaml_check_update(pages_url, tag_prefix, entries, enabled, bundled_yaml_dir)`
- `yaml_apply_update(request)`
- `yaml_rollback_update(file_name)`

Use the generic helpers only for tests or unusual hosts that intentionally need explicit channel coordinates or caller-built schema entries. Native first-party code should not call them.

## `src/database.rs` -> `classic::database`

This file exposes a narrow FormID database pool surface over `classic_database_core::DatabasePool`.

It owns:

- pool construction and initialization
- single and batch FormID lookup
- a few cache and lifecycle helpers

It does not expose stats, optimization, connection-budget tuning, rebalance controls, or typed lookup results.

## `src/scanner.rs` -> `classic::scanner`

This file is the largest bridge surface in this group.

It owns:

- YAML-backed scan config construction
- explicit FCX singleton reset through `classic::scanner::fcx_reset_global_state()`
- `OrchestratorCore` creation and single and batch scan entry points
- full Crash Log Scan Run execution through `scan_run_execute(...)`
- delegation to `classic-scanlog-core` Crash Log Scan Intake for remove-list loading, FormID DB path selection, and short-scan cache profile choice
- progress callback DTOs for batch scanning
- small scan utilities such as `detect_vr_log` and `detect_crash_pattern`
- Papyrus monitoring through `classic_scanlog_core::papyrus::PapyrusAnalyzer`

This is currently where `classic-config-core`, `classic-database-core`, `classic-scanlog-core`, `classic-settings-core` (which absorbed the former ``yaml-core`` in v9.1.0 Phase 1), and `classic-shared-core` meet for the C++ scanning path.

---

## FFI Surface By File

## `classic::settings` entry points

(This namespace was renamed from `classic::yaml` during v9.1.0 Phase 1 Plan 2 and expanded with the D-09 settings-core surface in the same change.)

### Typed User Settings groups, migration plans, update previews, and commits

`user_settings_open_update_preferences(classic_root) -> UpdatePreferencesDto` forwards an explicit CLASSIC root to `classic_user_settings_core::UserSettings::open(...)`. Rust owns canonical/legacy discovery, schema classification, published defaults, fail-closed fallbacks, content revision, commit eligibility, and diagnostics; C++ does not interpret a raw User Settings key path.

`UpdatePreferencesDto.update_check_enabled` is ready for policy use. Missing settings produce the published default `true`; invalid, malformed, unreadable, older-incompatible, and future-major inputs produce `false`. `update_source` carries the canonical `GitHub` or `Both` token, and both preferences carry independent provenance. The remaining fields expose source location/path, document classification, optional schema version, revision token, commit policy, structured diagnostics, and the exact original source bytes when available.

`user_settings_plan_migration(classic_root) -> UserSettingsMigrationPlanningOutcomeDto` returns `not_required`, `planned`, or `unsupported` without writing, relocating, or backing up files. A planned result carries requiredness, the base revision, source/target location and optional major/minor versions, ordered reversible change rows, and exact original/proposed bytes. CXX presence flags distinguish absent endpoints and values from meaningful empty strings; unsupported results carry structured diagnostics and no partial plan.

`user_settings_reverse_migration_plan(plan) -> Result<UserSettingsMigrationPlanningOutcomeDto>` validates a complete planned DTO, reconstructs it as an unattested core review plan, and delegates its exact in-memory inverse to Rust. The core swaps endpoints and byte payloads, reverses and inverts every review row, and anchors the inverse to the SHA-256 revision of the forward proposed bytes; invalid tokens or terminal outcome DTOs return an error rather than fabricating a partial inverse.

`user_settings_apply_migration(classic_root, approved) -> Result<Box<UserSettingsMigrationApplyHandle>>` explicitly applies a caller-approved planned DTO without trusting its mutable bytes as persistence input. The adapter reopens and replans through Rust, returns a stale base revision as conflict data, rejects proposed-content mismatches as approval errors, and passes only the fresh core plan to the locked apply seam. `user_settings_migration_apply_outcome(handle)` reports `applied` or `conflict`; an applied result includes inspectable source, destination, backup, endpoint, and revision fields while the unforgeable core receipt remains inside the opaque handle.

`user_settings_restore_migration(classic_root, handle) -> Result<UserSettingsMigrationRestoreOutcomeDto>` explicitly restores through that retained receipt. `restored` and `conflict` are normal DTO statuses. A conflicted apply handle has no receipt and returns an error; backup verification, publication, reopen, and rollback failures propagate as `rust::Error` with the stable core code in the message.

`user_settings_open_crash_log_scan_settings(classic_root) -> CrashLogScanSettingsDto` exposes the safety-adjusted FCX, simplification, statistics, FormID Value Lookup/database, Unsolved Logs, custom scan, game-version, and concurrency choices with per-field provenance. FormID database maps cross CXX as a game list plus flattened `{ game, path }` rows so explicit empty game lists survive without using an unsupported nested-vector DTO.

`user_settings_open_game_setup_settings(classic_root) -> GameSetupSettingsDto` exposes the managed game, selected version, game root, executable, Documents and INI paths, mods/staging path, custom-scan path, and Papyrus log path with per-field provenance. Rust resolves compatibility labels and retains persisted separator spelling before the DTO is formed.

`user_settings_open_frontend_state(classic_root) -> FrontendStateDto` exposes canonical presentation preferences, the four named GUI tab geometries, and the namespaced TUI remembered state with per-field provenance. The DTO contains primitives and stable tab-name tokens rather than Qt widget types. `MainWindow::restoreTabGeometry(...)` consumes this typed read; its existing raw geometry writer remains because geometry fields are not yet represented by `UserSettingsUpdate`.

`user_settings_open_gui_settings(classic_root) -> GuiSettingsSnapshotDto` opens User Settings once and projects `UpdatePreferencesDto`, `CrashLogScanSettingsDto`, `GameSetupSettingsDto`, and `FrontendStateDto` from that same Rust snapshot. This is the cohesive native-GUI read seam: every group carries the same classification, revision, commit policy, and diagnostic context rather than being assembled from independently reopened documents.

`user_settings_gui_published_defaults() -> GuiSettingsSnapshotDto` returns the same aggregate from `UserSettings::published_defaults()` without a root path or filesystem access. The Settings dialog uses it only to populate reset state; persistence still requires the ordinary preview and revision-anchored commit flow after the user accepts the dialog.

`user_settings_preview_update(classic_root, update) -> UserSettingsUpdatePreviewDto` validates every requested field, including Update Source, Auto Switch After Scan, and Game Setup fields, as one unit and performs no write. Accepted results carry the opened base revision and only requested canonical fields; rejected results contain all field diagnostics and no partial fields. Optional strings and omitted fields use separate presence flags, while accepted field values use an explicit `value_kind` plus typed value members.

`user_settings_commit_update(classic_root, base_revision, update) -> Result<UserSettingsCommitResultDto>` requires the revision returned by the accepted preview, reopens and compares it before revalidating the request, then delegates publication to the Rust core's locked atomic commit. `status` is `committed`, `conflict`, or `rejected`; the DTO carries the new revision, expected/actual conflict revisions, or rejection diagnostics as appropriate. Operational failures propagate as `rust::Error` with the stable core code prefixed in the message. C++ never reconstructs or trusts an `AcceptedUserSettingsUpdate` from the flattened preview fields.

The native CLI scan adapter opens the Crash Log Scan and Game Setup DTOs once, reports their structured diagnostics and migration/blocked-commit state, then builds explicit scan facts. Saved values supply game/version, FCX Mode, Simplify Logs, FormID Value Lookup and configured databases, custom scan input, concurrency, setup paths, and Unsolved Logs policy; explicitly present CLI options override the corresponding saved value. `--unsolved-logs-destination` and `--reset-unsolved-logs-destination` preview and commit through the typed revision-aware CXX seam before the scan snapshot is reopened.

The native CLI YAML Data check/apply commands and `--check-app-update` both consume `UpdatePreferencesDto` rather than a raw key path. Disabled or degraded policy short-circuits before network work with the command's established exit behavior, while migration and validation diagnostics remain visible. The typed frontend DTO separately drives GUI geometry restoration.

The native GUI's `GuiUserSettings` Qt adapter consumes `GuiSettingsSnapshotDto`. The Settings dialog submits every selected visible change through one preview and one revision-anchored commit; cancel performs no update, rejection writes nothing, and a concurrent edit returns an actionable conflict without overwriting the newer document. Unknown keys and unrelated invalid settings survive because Rust patches only accepted canonical fields. The accepted snapshot also produces an immutable `CrashLogScanLaunchSettings` value object. `MainWindow`, `ScanController`, and `ScanWorker` forward that value through `buildScanRunRequest(...)`, including the selected game's FormID database paths, without rereading User Settings or interpreting raw YAML during scan launch.

### YAML file-cache helpers

These helpers keep the C++ YAML surface aligned with the canonical Phase 4 cache stats contract:

- `yaml_ops_clear_cache(ops)` forwards to `YamlOperations::clear_cache()`
- `yaml_ops_cache_stats(ops) -> YamlCacheStatsDto` forwards to `classic_settings_core::yaml_cache_stats()`
- `yaml_ops_cache_size(ops) -> usize` is a narrowed adapter over `yaml_ops_cache_stats(ops).size`

Current bridge behavior:

- the returned `YamlCacheStatsDto` DTO uses the exact shared five-field cache stats contract (`hits`, `misses`, `hit_rate`, `size`, `capacity`)
- the DTO was renamed from the pre-existing `CacheStats` shared struct during Phase 1 Plan 2 to avoid collision with the new `SettingsCacheStats`
- C++ does not receive YAML-specific `total_bytes`; that legacy detail remains Rust-only

### Settings-core cache loaders (D-09 expansion)

- `settings_load_sync(key, path) -> Result<u32>` forwards to `classic_settings_core::load_settings_sync(...)`, returning the number of parsed YAML documents
- `settings_load_async_blocking(key, path) -> Result<u32>` wraps the async loader with `block_on(...)` on the shared runtime
- `settings_load_batch_sync(paths) -> Result<u32>` forwards to `classic_settings_core::load_batch_sync(...)`
- `settings_load_batch_async_blocking(paths) -> Result<u32>` wraps the async batch loader with `block_on(...)`

These return only a `u32` document count because the Rust APIs return `Arc<Vec<Yaml>>` which cannot cross the CXX boundary. Callers that need the documents back out currently fall back to `yaml_ops_*`.

### Settings-core cache observability (D-09 expansion)

- `settings_cache_stats() -> SettingsCacheStats` forwards to `classic_settings_core::cache_stats()`
- `settings_cache_size() -> usize`, `settings_cache_keys() -> Vec<String>`, `settings_is_cached(key) -> bool`, `settings_invalidate(key) -> bool`, `settings_clear_cache()`, `settings_reset_cache_stats()` — forward to the matching settings-core APIs
- `SettingsCacheStats` is a distinct shared struct from `YamlCacheStatsDto`: the settings cache has capacity `64` while the yaml file cache has capacity `128`. Confusing the two would silently swap cache numbers.

### Generic scalar validators (D-09 expansion)

- `settings_validate_value(value, expected_type) -> bool` forwards to `validate_setting_value(...)` with a 9-token case-insensitive type parser (`int`, `integer`, `bool`, `boolean`, `float`, `double`, `path`, `string`, `str`; `list`/`map`/`array` are rejected because the underlying `SettingType` enum has only five variants)
- `settings_coerce_value(value, target_type) -> Result<SettingsCoercedValue>` forwards to `coerce_setting_value(...)` using the same 9-token parser

Shared structs in this expansion: `SettingsCacheStats`, `SettingsCoercedValue`, `YamlCacheStatsDto`.

## `classic::config` entry points

### Settings cache helpers

These helpers give C++ the same bounded-cache observability surface that Node and Python expose for `classic_settings_core`:

- `settings_cache_clear()` forwards to `classic_settings_core::clear_cache()`
- `settings_cache_stats() -> CacheStats` forwards to `classic_settings_core::cache_stats()`
- `settings_cache_size() -> usize` is a narrowed adapter over `settings_cache_stats().size`
- `reset_settings_cache_stats()` forwards to `classic_settings_core::reset_cache_stats()`

Current bridge behavior:

- the C++ `CacheStats` DTO matches the canonical Phase 4 contract exactly: `hits`, `misses`, `hit_rate`, `size`, `capacity`
- cache ownership and invalidation semantics stay in Rust core; the bridge only reshapes the DTO for CXX

### `yaml_data_load(yaml_dir_root, yaml_dir_data, game, game_version) -> Result<Box<YamlData>>`

Forwards to:

- `classic_shared_core::get_runtime()`
- `classic_config_core::YamlDataCore::load_from_yaml_files(...)`

Current bridge behavior:

- always uses the 2-directory loader shape `[yaml_dir_root, yaml_dir_data]`
- blocks on the shared runtime with `block_on(...)`
- preserves load failure as a CXX `Result` error string instead of using sentinel values

### `save_local_yaml_paths(local_yaml_path, game_root, docs_root) -> Result<()>`

Forwards to:

- `classic_shared_core::get_runtime()`
- `classic_config_core::persist_game_local_paths(...)`

Current bridge behavior:

- treats empty `game_root` or `docs_root` strings as unset optional values
- lets Rust create `CLASSIC Data/CLASSIC {game} Local.yaml` when the file is missing
- reads and writes only the caller-selected Game Local YAML document; it does not load or save User Settings
- preserves Rust-side error propagation as a CXX `Result` error string

### Selected scalar and vector getters

These entry points expose only a slice of `YamlDataCore`:

- scalar field getters such as `yaml_data_classic_version`, `yaml_data_crashgen_name_field`, `yaml_data_xse_acronym`, `yaml_data_autoscan_text`, and `yaml_data_game_version`
- helper-backed accessors `yaml_data_get_crashgen_name`, `yaml_data_get_game_root_name`, and `yaml_data_get_crashgen_ignore`
- vector getters such as `yaml_data_classic_records_list`, `yaml_data_game_ignore_plugins`, `yaml_data_game_ignore_records`, and `yaml_data_ignore_list`

Forwarding notes:

- most scalar getters read the stored `YamlDataCore` field directly
- `yaml_data_get_crashgen_name()` and `yaml_data_get_game_root_name()` forward through `YamlDataCore` helper methods
- `yaml_data_get_crashgen_ignore()` forwards through `YamlDataCore::get_crashgen_ignore()`

### Flattened and structured getters

These functions flatten selected YAML-backed fields into vectors where needed, while `Mods_FREQ` and `Mods_SOLU` now cross the bridge as explicit shared struct sequences:

- suspect rule ids and names: `yaml_data_suspects_error_keys()` and `yaml_data_suspects_error_values()`
- mods entries: `yaml_data_mods_core_*` (structured keys/names/gpus), `yaml_data_mods_freq_entries()` (structured sequence)
- structured mod-check entries: `yaml_data_mods_freq_entries()` and `yaml_data_mods_solu_entries()` return ordered `YamlDataModSolutionEntry` values with `id`, grouped `criteria`, `exceptions`, `name`, and `description`
- mod conflict entries (structured): `yaml_data_mods_conf_mod_a()`, `yaml_data_mods_conf_mod_b()`, `yaml_data_mods_conf_name_a()`, `yaml_data_mods_conf_name_b()`, `yaml_data_mods_conf_descriptions()`, `yaml_data_mods_conf_fixes()`, `yaml_data_mods_conf_links()`, `yaml_data_mods_conf_count()`

Important current boundary:

- `yaml_data_suspects_stack_keys()` exposes only `YamlDataCore.suspect_stack_rules[].id`
- the bridge does **not** expose the rest of each structured stack rule yet
- the bridge exposes no raw `CrashgenEntryRaw` or `crashgen_registry` data at all

---

## `classic::files` entry points

## Hash cache helpers

These helpers expose the `classic_file_io_core::hash::FileHasher` cache directly to C++ callers:

- `hash_cache_clear()` forwards to `FileHasher::clear_cache()`
- `hash_cache_stats() -> CacheStats` forwards to `FileHasher::cache_stats()`
- `hash_cache_size() -> usize` is a narrowed adapter over `hash_cache_stats().size`
- `reset_hash_cache_stats()` forwards to `FileHasher::reset_cache_stats()`

Current bridge behavior:

- the returned `CacheStats` DTO uses the same five-field cache stats contract as `classic::settings` and `classic::config`
- hash calculation and cache semantics remain owned by `classic-file-io-core`; the bridge just forwards the data

## Backup helpers

### `backup_manager_new(game_root)`

Forwards to `classic_file_io_core::backup::BackupManager::new(PathBuf::from(game_root), None)`.

Current bridge choice:

- always uses the crate default backup root under `game_root/CLASSIC_Backups`
- does not expose the optional custom backup base

### `backup_manager_exists`, `backup_manager_create`, `backup_manager_restore`, `backup_manager_remove`

Forwards to `BackupManager::backup_exists()`, `create_backup()`, `restore_backup()`, and `remove_backup()`.

Bridge narrowing:

- backup types are parsed by bridge-local `backup_type_from_str()`
- accepted type strings are only `xse`, `reshade`, `vulkan`, and `enb`
- `backup_manager_create()` drops `BackupInfo` detail and returns only a formatted summary string based on `file_count`
- `backup_manager_exists()` returns only existence, not creation time or file count

## Game-file group helpers

### `game_files_manager_new(game_root, backup_root)`

Forwards to `classic_file_io_core::game_files::GameFilesManager::new(...)`.

### `game_files_backup`, `game_files_restore`, `game_files_remove`

Forwards to `GameFilesManager::backup()`, `restore()`, and `remove()`.

Current bridge behavior that matters:

- the Rust crate uses case-insensitive substring matching against direct children of `game_root`
- restore only copies files that both match the patterns and already exist in the labeled backup directory
- remove treats already-missing paths as success in lower layers
- each bridge function drops `FileOperationResult.operation`, `label`, and the actual `errors` list
- callers get only a formatted string of the form `N files affected, M errors`

## Log collection helpers

### `log_collector_new(crash_logs_dir, xse_folder, custom_folder)`

Forwards to `classic_file_io_core::log_collection::LogCollector::new(...)`.

Current bridge choice:

- empty `xse_folder` and `custom_folder` become `None`
- the first parameter is the `base_folder`; the Rust crate will create `Crash Logs` under that base folder

### `log_collector_new_for_scan(base_folder, yaml_dir_data, game, selected_game_version, configured_docs_root, custom_folder)`

Forwards to `classic_file_io_core::log_collection::LogCollector::new_for_scan(...)`.

Current bridge behavior:

- XSE Folder resolution stays in Rust via the file-IO/XSE core crates
- empty `configured_docs_root` and `custom_folder` become `None`
- custom scan folders are additive to the normal XSE crash-log import; they do not suppress XSE collection

### `log_collector_collect_all` and `log_collector_collect_crash_logs`

Forwards to `LogCollector::collect_all()` and `collect_crash_logs()`.

Bridge narrowing:

- returned paths are lossy UTF-8 strings
- the bridge does not expose `move_from_base_folder()`, `copy_from_xse_folder()`, `crash_logs_dir()`, or `pastebin_dir()` separately

## Targeted input resolution

### `resolve_targeted_inputs(input_paths) -> TargetedResolutionDto`

Forwards to `classic_file_io_core::log_collection::resolve_targeted_inputs(...)`.

Bridge DTO shape (`TargetedResolutionDto`):

- `logs: Vec<String>` - deduplicated targeted log paths that were accepted
- `rejected_paths: Vec<String>` - original paths of rejected inputs (parallel with `rejected_reasons`)
- `rejected_reasons: Vec<String>` - human-readable rejection reasons (parallel with `rejected_paths`)

Current bridge behavior:

- converts `&[String]` input paths to `Vec<PathBuf>` for the Rust call
- runs the async resolver on the shared runtime with `block_on(...)`
- returned paths are lossy UTF-8 strings
- explicit regular file paths are accepted regardless of file name; directory inputs remain recursively constrained to `**/crash-*.log`
- `RejectedInput` structs are flattened into parallel path and reason vectors, matching the bridge's existing pattern for map-like data

## Standalone file helpers

### `calculate_file_similarity(path1, path2) -> Result<f64>`

Forwards to `classic_file_io_core::similarity::calculate_similarity(...)`.

### `read_file_with_encoding(path) -> Result<String>`

Creates `FileIOCore::new(utf-8, replace, 4, 8)` and forwards to `FileIOCore::read_file(...)`.

### `write_file_string(path, content) -> Result<()>`

Creates `FileIOCore::new(utf-8, replace, 4, 8)` and forwards to `FileIOCore::write_file(...)`.

Important current boundary:

- each call creates a fresh `FileIOCore`, so bridge callers do not reuse the crate caches
- the bridge hardcodes replace-style decoding behavior instead of exposing `FileIOCore` configuration
- `write_file_string()` inherits `FileIOCore::write_file()` behavior and does not create parent directories

## Bridge-local report helpers

### `write_autoscan_report(log_path, content) -> Result<String>`

This is bridge-local code that derives a sibling `*-AUTOSCAN.md` path from the source log name and then uses `FileIOCore::write_file(...)`.

### `discover_report_files(directory) -> Vec<String>`

This is bridge-local code using `std::fs::read_dir(...)`.

Current behavior:

- searches only the provided directory, not recursively
- matches only names ending in `-AUTOSCAN.md`
- sorts newest first by modified time
- returns `Vec::new()` if the directory does not exist or cannot be read

### `read_report_file(path) -> Result<String>`

Thin wrapper over `read_file_with_encoding(path)`.

---

## `classic::database` entry points

### `db_pool_new(game_table, max_connections, cache_ttl_secs) -> Box<DbPool>`

Forwards to `classic_database_core::DatabasePool::new(...)`.

Bridge choice:

- `max_connections == 0` becomes `None`, which activates the crate default global connection budget
- cache TTL is expressed only as whole seconds here

### `db_pool_initialize(pool, db_paths) -> Result<()>`

Forwards to `DatabasePool::initialize(...)` on the shared runtime.

Contributor note:

- lower layers skip nonexistent database files instead of failing the whole initialization path if at least one usable path remains

### `db_pool_get_entry(pool, formid, plugin) -> String`

Forwards to `DatabasePool::get_entry(formid, plugin, None)`.

Fail-soft behavior:

- `Ok(Some(entry))` becomes the entry text
- `Ok(None)` becomes `""`
- any `DatabaseError` also becomes `""`

This means the C++ side cannot distinguish miss, uninitialized pool, and query error from this entry point alone.

### `db_pool_get_entries_batch(pool, formids, plugins) -> Vec<String>`

Forwards to `DatabasePool::get_entries_batch(pairs, None, 50)`.

Current bridge behavior:

- pairs are built by zipping `formids` and `plugins`, so extra items on the longer side are silently dropped
- each result is flattened as ``{key}\t{value}``
- the `key` comes from the Rust map key shape `formid:plugin`, not from a structured DTO
- any error returns an empty vector

Bridge narrowing:

- no typed batch result exists
- no exposure exists for caller-controlled table name or batch size
- result ordering is not guaranteed because the lower layer returns a `HashMap`

### Cache and lifecycle helpers

- `db_pool_is_available()` forwards to `DatabasePool::is_available()`
- `db_pool_cache_size()` forwards to `DatabasePool::cache_size()`
- `db_pool_clear_cache(expired_only)` forwards to `DatabasePool::clear_cache(...)`
- `db_pool_close()` forwards to `DatabasePool::close()` as a CXX `Result`
- `db_pool_game_table()` forwards to `DatabasePool::get_game_table()`

The bridge does not expose `get_stats()`, `optimize()`, `rebalance_connections()`, or any tuning setters beyond constructor inputs.

---

## `classic::scanner` entry points

## Config construction

### `build_full_scan_config(...) -> Result<Box<FullScanConfig>>`

Forwards to:

- `classic_scanlog_core::CrashLogScanIntake::from_yaml_paths(...)`
- `CrashLogScanIntake::prepare()`, which loads path-backed `YamlDataCore`, resolves YAML Data-owned simplify-log removal rules, builds `AnalysisConfig`, and selects built-in FormID readiness

Current bridge behavior that matters:

- `remove_list` comes from `CLASSIC Main.yaml` key `exclude_log_records`, not from the public `classic::config` surface
- this compatibility constructor supplies no caller-projected FormID paths, so its DB list contains the main DB plus the hardcoded FOLON DB for Fallout 4 and Fallout 4 VR
- paths are deduplicated before pool initialization

Important boundary:

- the public CXX call shape is preserved for lower-level callers, but it does not open User Settings. Native full scans should use `scan_run_execute(...)` and provide configured paths through its typed request.

### `orchestrator_new(config) -> Result<Box<Orchestrator>>`

Forwards to `classic_scanlog_core::OrchestratorCore::new(...)` and optionally `attach_database_pool(...)`.

Current bridge behavior:

- if intake produced `show_formid_values=false`, no database pool is created
- if it produced `show_formid_values=true`, the bridge constructs its own `DatabasePool`, applies the intake-selected short-scan profile, initializes it from the intake-selected DB path list, and attaches it to the orchestrator
- missing FOLON or user DB files do not necessarily fail this path because `DatabasePool::initialize()` skips nonexistent paths

Source-backed short-scan profile:

- cache capacity `30000`
- cleanup threshold `4096`
- cleanup interval `300` seconds
- cache TTL uses `classic_database_core::BATCH_CACHE_TTL_SECS`

### `orchestrator_new_minimal(game, game_version, crashgen_name, xse_acronym)`

Forwards to `AnalysisConfig::new(...)` plus `OrchestratorCore::new(...)`.

Current boundary:

- this is intentionally not YAML-backed
- it sets only `crashgen_name` and `xse_acronym` on top of the default `AnalysisConfig`
- no DB pool is attached here

## Scan execution

### `fcx_reset_global_state() -> Result<()>`

Forwards to `classic_scanlog_core::FcxModeHandler::reset_global_state()`.

Current bridge behavior:

- keeps C++ reset-only for FCX in this phase; there is no bridge API for inspecting FCX issues yet
- maps `FcxResetError::Unnecessary` to success so callers can reset aggressively without aborting clean sessions
- maps real reset failures to a returned bridge error string so callers can stop before reusing stale FCX state

Contributor note:

- this explicit reset entry point remains public even though the main scan-session functions below also auto-reset before work begins

### `orchestrator_process_log(orch, log_path) -> Result<ScanResult>`

Forwards to `OrchestratorCore::process_log(...)`.

Current bridge behavior:

- calls `fcx_reset_global_state()` before starting scan work
- treats `FcxResetError::Unnecessary` as success via the helper above
- returns a bridge error and aborts the scan start if FCX reset fails for a real reason

Bridge DTO shape:

- `log_path`
- `success`
- `report_lines`
- `error_message`
- `processing_time_ms`
- `formid_count`
- `plugin_count`
- `suspect_count`

Bridge narrowing:

- drops `processing_time_us`
- drops Python-parity counters such as `scanned`, `incomplete`, `failed`, and `trigger_scan_failed`

### `orchestrator_process_logs_batch(orch, log_paths, max_concurrent) -> Vec<ScanResult>`

Forwards to `OrchestratorCore::process_logs_batch(...)`.

Current bridge behavior:

- calls `fcx_reset_global_state()` before any batch work begins
- `max_concurrent == 0` becomes `None`, which activates the crate adaptive concurrency path
- results are returned in completion order, not input order, because the lower layer uses unordered buffering

FCX reset failure mapping:

- `FcxResetError::Unnecessary` stays on the normal execution path and does not abort the batch
- a real reset failure short-circuits the batch before scan work starts and returns a single failed `ScanResult` carrying the reset error text

### `orchestrator_process_logs_batch_with_progress(...) -> Vec<BatchScanResult>`

This is mostly bridge-local orchestration around `OrchestratorCore::process_log_with_progress(...)`.

Current behavior that matters:

- calls `fcx_reset_global_state()` before queuing or emitting any progress events
- emits `Queued`, `Started`, `Phase`, `Completed`, and `Failed` events to the C++ callback
- preserves `input_index` so callers can map completion-order results back to the original request list
- computes adaptive concurrency locally when `max_concurrent == 0`
- tries to drain ready phase events before terminal completion events so per-log event ordering stays monotonic
- still returns results in completion order, not input order

FCX reset failure mapping:

- `FcxResetError::Unnecessary` remains non-fatal
- a real reset failure aborts the scan session before callback activity begins and returns a single failed `BatchScanResult` with the reset error text

### `scan_run_contract_execute(request, cancellation, observer) -> ScanRunContractExecutionResult`

This is the final C++ projection of
`classic_scanlog_core::scan_run::contract::execute(...)`. It is additive during
the coordinated expand-contract migration; the older `scan_run_execute(...)`
surface below remains available until the native-consumer contraction ticket.

Requests are opaque Rust-owned `ScanRunRequest` values. C++ constructs them
through exactly the same valid matrix as the core contract:

- `scan_run_request_standard(configuration, source, unsolved_logs)`
- `scan_run_request_standard_with_fcx(configuration, source, unsolved_logs, setup_context)`
- `scan_run_request_targeted(configuration, source)`
- `scan_run_request_targeted_with_fcx(configuration, source, setup_context)`

`ScanRunConfigurationDto` contains YAML roots, typed game text, selected game
version, non-FCX analysis options, configured FormID database paths, an optional
configured Unsolved Logs destination, and optional explicit concurrency.
Optional inputs use `has_*` plus the corresponding value: `has_max_concurrent =
false` selects Rust's adaptive value, while a present zero reaches the final
operation as a typed `RequestValidation` infrastructure error. Optional request paths use the same presence convention;
their value strings are ignored when the presence flag is false.

Standard callers select one opaque `ScanRunUnsolvedLogs` value with
`scan_run_unsolved_logs_leave_in_place()`,
`scan_run_unsolved_logs_move_to_configured_or_default()`, or
`scan_run_unsolved_logs_move_to_custom(path)`. Targeted constructors accept no
movement value. FCX constructors require `ScanRunSetupContextDto`; an explicitly
supplied context whose four optional path fields are absent still means FCX is
enabled and is not collapsed into the non-FCX variant.

`ScanRunCancellation` is an opaque monotonic control with `new`, `cancel`, and
`is_cancelled` operations. It deliberately has no reset operation. Pass
`nullptr` for `observer` to disable observation, or pass a live
`ScanRunObserver` declared in
`include/classic_cxx_bridge/scan_run_observer.h`. Observer calls are serialized
and cover `DiscoveryCompleted`, `EffectiveConcurrencySelected`, `LogQueued`,
`LogStarted`, `LogPhase`, and `LogFinished`. A `LogFinished` event carries the
typed `Succeeded`, `Failed`, or `CancelledBeforeStart` disposition. Fields not
applicable to an event's tag contain defaults and must be ignored.

The callback is `noexcept`: delivery or presentation failures remain adapter
concerns. An adapter may record the failure and call
`scan_run_cancellation_cancel(...)` to stop future admission at safe seams; it
must not throw through the callback or turn delivery failure into a core scan
failure.

`ScanRunContractExecutionResult` is a typed result/error envelope. Exactly one
of `has_result` and `has_error` is true:

- `result` retains the typed five-way run status, optional discovery, optional
  FCX setup, optional effective concurrency, optional message, aggregate counts,
  and per-log results in discovery order
- each discovery rejection is one `{path, reason}` object rather than parallel
  arrays
- each log retains its typed disposition, every structured failure
  (`Analysis`, `ReportWrite`, `UnsolvedLogsFinalization`), optional report path,
  optional message, movement flag, microsecond and millisecond timing, and counts
- `error` retains all six infrastructure stages, its message, and an optional
  relevant path

Every optional output uses an explicit `has_*` flag, so an absent value is not
conflated with an empty string or zero. Bridge paths use the repository's
existing lossy UTF-8 CXX string conversion policy.

### Legacy expand-contract surface: `scan_run_execute(request, callback, cancellation_token) -> Result<ScanRunResult>`

Forwards to the Rust `classic_scanlog_core::CrashLogScanRunService` facade. Rust owns Standard/Targeted discovery, optional FCX setup result shaping, Crash Log Scan Intake preparation, Autoscan Report writing, and Unsolved Logs policy.

C++ callers populate `ScanRunRequestDto` and pass it by reference. Request fields:

- `yaml_dir_root`
- `yaml_dir_data`
- `game`
- `game_version`
- `show_formid_values`
- `formid_database_paths` (caller-projected configured paths; relative values resolve under `yaml_dir_data`)
- `fcx_mode`
- `simplify_logs`
- `base_directory`
- `custom_scan_directory`
- `configured_documents_root`
- `setup_game_root`
- `setup_docs_root`
- `setup_game_exe_path`
- `setup_xse_log_path`
- `move_unsolved_logs`
- `unsolved_logs_destination` (empty string means not supplied)
- `targeted_mode`
- `targeted_inputs`
- `max_concurrent`
- `log_paths` (fallback Targeted input list for older callers)

Current bridge behavior:

- builds a typed `CrashLogScanSource::Standard` from `base_directory`, `custom_scan_directory`, and `configured_documents_root` when `targeted_mode = false`
- builds a typed `CrashLogScanSource::Targeted` from `targeted_inputs` when present, falling back to `log_paths` for older callers when `targeted_mode = true`
- forwards optional FCX setup facts through `CrashLogScanSetupContext`; FCX setup failures are returned as `ScanRunResult.status = "setup_failed"` with `setup` data rather than as per-log failures
- the bridge packages `formid_database_paths` and `unsolved_logs_destination` as `CrashLogScanFacts` and forwards movement and concurrency facts unchanged; request normalization is core-owned. The core owns the resulting behavior:
- `request.max_concurrent == 0` is folded to the core adaptive concurrency default at the scan-run seam (equivalent to `None`)
- `request.targeted_mode = true` creates a Targeted Crash Log Scan Run and ignores `move_unsolved_logs` plus `unsolved_logs_destination`
- `request.targeted_mode = false` creates a Standard Crash Log Scan Run
- Standard discovery preserves `LogCollector` behavior; no accepted logs return `ScanRunResult.status = "no_crash_logs_found"` with discovery data and an empty `logs` vector
- Targeted discovery returns rejected inputs under `ScanRunResult.discovery.rejected_paths` and `rejected_reasons`; rejected Targeted inputs are not per-log analysis failures
- Standard requests with `move_unsolved_logs = false` leave failed logs in place and ignore `unsolved_logs_destination`
- Standard requests with `move_unsolved_logs = true` and non-empty `unsolved_logs_destination` request that custom destination (the core trims the string and treats empty/whitespace as not supplied); Rust rejects relative paths as setup errors
- Standard requests with `move_unsolved_logs = true` and empty `unsolved_logs_destination` use the canonical `CLASSIC Backup/Unsolved Logs` directory under path-backed intake roots; native adapters put a configured destination into the typed request when one exists
- Rust writes Autoscan Reports before returning per-log results; C++ callers no longer receive `report_lines` from this entry point
- infrastructure failures and prepared-run setup errors such as a relative custom Unsolved Logs destination return a CXX `Result` error; per-log analysis, Autoscan Report write, and invalid or unwritable absolute Unsolved Logs movement failures are represented in nested `ScanRunLogResult` values
- progress uses the existing `ScanBatchProgressCallback` and `BatchProgressEvent` DTO shape
- cooperative cancellation uses a Rust-owned `ScanCancellationToken`; callers create/reset the token, pass it alongside the request to `scan_run_execute(...)`, and call `scan_cancellation_token_cancel(...)` to stop queued logs before they start

Bridge DTO shape for `ScanRunResult`:

- `status`
- `message`
- `total`, `succeeded`, `failed`, `cancelled`
- `discovery` (`source`, `accepted_logs`, `rejected_paths`, `rejected_reasons`, `searched_locations`)
- `setup` (`status`, `message`, `rendered_report`, `checks`, `path_updates`, `configuration_issues`, `actions`, `fatal_errors`)
- `logs`

Bridge DTO shape for `ScanRunLogResult`:

- `input_index`
- `log_path`
- `autoscan_report_path` (empty when no report was written)
- `success`
- `report_write_failed`
- `cancelled`
- `moved_to_unsolved_logs`
- `error_message`
- `processing_time_ms`
- `formid_count`, `plugin_count`, `suspect_count`

Contributor note:

- new C++ consumers should use `scan_run_contract_execute(...)`; this legacy
  flag-based DTO, resettable token, mandatory batch callback, and the older
  `orchestrator_*` functions remain only as temporary native-consumer migration
  aids

## Small scan utilities

### `detect_vr_log(content) -> bool`

This is bridge-local logic. It checks only for the substrings `Fallout4VR.esm` or `SkyrimVR.esm`.

### `detect_crash_pattern(content) -> String`

Reuses one module-level default `LogParser` and forwards to `LogParser::parse_crash_header(...)`, returning only the parsed `main_error` text.

Contributor note:

- `detect_crash_pattern` keeps the same fail-soft `""` behavior, but it now reuses a cached default parser internally instead of constructing `LogParser::new(None)` on every call

Fail-soft behavior:

- header parse failure becomes `""`

Initialization note:

- default parser construction is now a one-time module initialization step rather than per-call bridge work

## Papyrus monitoring

### `papyrus_analyzer_new(log_path)`

Forwards to `classic_scanlog_core::papyrus::PapyrusAnalyzer::new(...)`.

### `papyrus_start_monitoring`, `papyrus_check_updates`, `papyrus_analyze_full`, `papyrus_log_exists`, `papyrus_reset`

Forwards to the matching `PapyrusAnalyzer` methods.

Bridge DTO shape for `PapyrusStatsDto`:

- `dumps`
- `stacks`
- `warnings`
- `errors`
- `lines_processed`
- `dumps_stacks_ratio`

Current bridge behavior:

- `papyrus_check_updates()` intentionally ignores errors and returns last-known stats
- `papyrus_start_monitoring()` starts from the end of the current file, matching the Rust tail-style behavior
- `papyrus_reset()` clears stats and resets position to the start of the file

---

## Current DTO And Error Pattern

The active bridge mostly uses four patterns.

## 1. Opaque wrapper types

Longer-lived Rust objects stay behind boxed bridge wrappers:

- `YamlData`
- `CxxBackupManager`
- `CxxGameFilesManager`
- `CxxLogCollector`
- `DbPool`
- `FullScanConfig`
- `Orchestrator`
- `CxxPapyrusAnalyzer`

## 2. Flattened DTOs or vector pairs

When the bridge cannot or does not want to expose a richer Rust type, it flattens:

- paired key and value vectors for config maps
- `ScanResult`, `BatchScanResult`, `ScanRunLogResult`, and `PapyrusStatsDto`
- tab-delimited batch DB lookup strings instead of a structured map DTO

## 3. Preformatted text summaries

Several helpers return already-formatted text rather than structured Rust data:

- backup creation summary strings
- game-files operation summary strings
- autoscan report paths and report-file lists

## 4. Fail-soft primitives

Several entry points erase typed errors and return defaults instead:

- empty string on DB miss or DB failure in `db_pool_get_entry()`
- empty vector on batch DB failure in `db_pool_get_entries_batch()`
- empty string on crash-header parse failure in `detect_crash_pattern()`
- last-known Papyrus stats on update failure in `papyrus_check_updates()`

---

## Where The Bridge Narrows The Rust APIs

## `src/config.rs`

- exposes only selected `YamlDataCore` fields and helper methods
- does not expose User Settings source discovery, schema, defaults, or persistence
- drops most structured stack-rule fields, exposing only ids today
- drops `crashgen_registry` and other richer YAML-derived structures

## `src/files.rs`

- narrows `BackupInfo` to a summary string and existence boolean
- narrows `FileOperationResult` to a summary string, dropping structured partial-failure detail
- fixes `FileIOCore` configuration instead of exposing it
- adds report-file helpers that are bridge-local and therefore do not expand the underlying crate API
- flattens `TargetedResolution` into `TargetedResolutionDto` with parallel path and reason vectors for rejected inputs

## `src/database.rs`

- narrows `DatabasePool` to only a few lifecycle and lookup calls
- collapses `Option<String>` and `DatabaseError` into `String` or empty results
- flattens batch results into strings and fixes batch size at `50`
- does not expose stats, optimization, or connection rebalance behavior

## `src/scanner.rs`

- exposes the main scan path, but not the full `OrchestratorCore` helper surface
- keeps FCX bridge exposure reset-only in this phase; no C++ FCX issue DTO or getter exists yet
- keeps the CXX config/orchestrator call shape while scanlog-core intake selects DB path lists and simplify-log removal rules
- drops `AnalysisResult` fields that some lower-level Rust and parity paths still use
- adds bridge-local batch progress coordination, VR detection, and crash-pattern extraction, while applying the intake-selected DB cache profile
- exposes `scan_run_execute(...)` for full Crash Log Scan Run behavior while keeping report writing and Unsolved Logs policy in Rust

---

## Contributor Debugging Notes

## Config flow

When C++ YAML-backed scan behavior looks wrong, check these in order:

1. confirm whether the frontend used `classic::config::yaml_data_load()` or the fuller `classic::scanner::build_full_scan_config()` path
2. verify the bridge got the 2-directory layout the Rust loader expects
3. remember that `yaml_data_load()` loads bulk scan YAML only and does not read `CLASSIC Settings.yaml`
4. if stack-suspect output is incomplete, remember the bridge exports only stack rule ids, not full structured rule content

## File flow

When file helper output looks weaker than the Rust crate API:

1. remember that backup and game-file entry points intentionally return summary strings, not structured result objects
2. check whether `write_file_string()` failed because parent directories do not exist
3. remember that `GameFilesManager` pattern matching is case-insensitive substring matching over direct children of `game_root`
4. remember that `discover_report_files()` is non-recursive and silently returns empty on unreadable directories
5. for targeted scans, check that `resolve_targeted_inputs()` returned non-empty `logs` and inspect `rejected_paths`/`rejected_reasons` for inputs that did not resolve

## Database flow

When FormID lookup looks empty:

1. check whether the pool was actually initialized and `db_pool_is_available()` is true
2. remember that missing DB files may be skipped during initialization without surfacing an error
3. remember that `db_pool_get_entry()` returns empty string for both miss and failure
4. if batch results look odd, remember the bridge zips `formids` and `plugins` and silently truncates to the shorter length
5. if ordering matters, remember the batch result vector comes from a `HashMap` and is not stable

## Scan flow

When the C++ scan path diverges from the crate docs:

1. check whether the frontend used `scan_run_execute(...)`, `orchestrator_new()`, or `orchestrator_new_minimal()`
2. if FormID values are missing, verify `show_formid_values` was true when the full config was built
3. remember that scanlog-core intake resolves FormID DB paths for the bridge, including a hardcoded FOLON DB path for Fallout 4 modes
4. if a scan aborts before work starts, check whether `fcx_reset_global_state()` failed and left an FCX reset error string in the bridge result path
5. if batch progress looks surprising, remember result order is completion order and `input_index` is the stable correlation key
6. for native scan-run consumers, remember Rust writes Autoscan Reports and owns Standard versus Targeted Unsolved Logs movement
7. use `CLASSIC_SCAN_DIAGNOSTICS` to turn on progress diagnostics and `CLASSIC_DB_COUNTER_INTERVAL` to control periodic DB counter logging

## Papyrus flow

When Papyrus monitoring looks stale:

1. confirm whether the caller used `start_monitoring()` or `analyze_full()`
2. remember that `start_monitoring()` begins at end-of-file, so old lines are intentionally ignored
3. remember that `papyrus_check_updates()` suppresses update errors and returns last-known stats
4. if a log was rotated or truncated, lower layers reset and re-read from the beginning

---

## Source-Backed Limits And Caveats

- `src/config.rs` is a narrow read bridge over `YamlDataCore`, not a general config bridge
- `src/config.rs` does not expose full `YamlDataCore.suspect_stack_rules` entries yet, only ids
- `src/files.rs::write_file_string()` does not create parent directories because it uses `FileIOCore::write_file()`
- `src/files.rs::resolve_targeted_inputs()` flattens `RejectedInput` structs into parallel vectors; callers must zip `rejected_paths` and `rejected_reasons` to reconstruct per-input context
- `src/files.rs::discover_report_files()` is bridge-local, non-recursive, and fail-soft on unreadable directories
- `src/database.rs::db_pool_get_entry()` cannot distinguish miss, closed pool, and query failure
- `src/database.rs::db_pool_get_entries_batch()` fixes batch size at `50` and flattens `formid:plugin` keys into tab-delimited strings
- `src/scanner.rs` delegates scan-readiness path ordering and YAML Data sidecars to `classic-scanlog-core`; configured FormID paths and Unsolved Logs destination cross as explicit `CrashLogScanFacts`
- scanlog-core intake hardcodes `databases/FOLON FormIDs.db` for `Fallout4` and `Fallout4VR`
- `src/scanner.rs` exposes only FCX reset control in C++; FCX issue inspection remains out of scope for this phase
- `src/scanner.rs::orchestrator_process_logs_batch_with_progress()` is bridge-local coordination on top of per-log crate calls, not a direct wrapper over one lower-level batch API
- `src/scanner.rs::scan_run_execute()` is the full Crash Log Scan Run seam; callers should not duplicate Autoscan Report writing or Unsolved Logs movement around it
- `src/scanner.rs::detect_vr_log()` is a simple substring heuristic, not a full parser
- `src/scanner.rs::papyrus_check_updates()` intentionally hides update errors from C++ callers

These are current behavior notes, not recommendations for future design.

---

## Contributor Rule Of Thumb

- If you need loaded YAML fields for scan-time C++ code, start in `src/config.rs`.
- If you need backup, log collection, or small report-file helpers, start in `src/files.rs`.
- If you need FormID lookup from C++, start in `src/database.rs`.
- If you need crash-log orchestration, progress callbacks, or Papyrus monitoring, start in `src/scanner.rs`.
- If you need richer Rust behavior than the bridge exposes, change the bridge intentionally and document the new boundary in this file and the crate-level docs in the same change.
