# `classic-cpp-bridge` Data Entry Points

Contributor-facing documentation for the active C++ bridge entry points in:

- [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs)
- [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/files.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/files.rs)
- [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs)
- [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs)

This page is the companion to [`classic-cpp-bridge-game-entrypoints.md`](classic-cpp-bridge-game-entrypoints.md). It documents the current CXX FFI surface that active C++ callers use for config loading, file utilities, FormID database access, crash-log scanning, and Papyrus monitoring.

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

## `src/config.rs` -> `classic::config`

This file exposes a read-mostly bridge around `classic_config_core::YamlDataCore`.

It owns:

- YAML dataset loading through `yaml_data_load(...)`
- field getters for selected scalar and `Vec<String>` values
- flattened `IndexMap` access for suspect and mod dictionaries

It does not expose the full `YamlDataCore` model, `ClassicConfig`, YAML save APIs, or raw crashgen registry data.

## `src/files.rs` -> `classic::files`

This file is the mixed file-operations bridge.

It owns:

- typed backup workflows through `classic_file_io_core::backup::BackupManager`
- generic file-group backup, restore, and remove through `classic_file_io_core::game_files::GameFilesManager`
- crash-log collection through `classic_file_io_core::log_collection::LogCollector`
- small standalone helpers for file similarity, encoding-aware reads and writes, and AUTOSCAN report files

Some report-file helpers are bridge-local convenience code, not direct crate re-exports.

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
- `OrchestratorCore` creation and single and batch scan entry points
- bridge-local FormID DB path resolution and remove-list loading
- progress callback DTOs for batch scanning
- small scan utilities such as `detect_vr_log` and `detect_crash_pattern`
- Papyrus monitoring through `classic_scanlog_core::papyrus::PapyrusAnalyzer`

This is currently where `classic-config-core`, `classic-database-core`, `classic-scanlog-core`, `classic-yaml-core`, and `classic-shared-core` meet for the C++ scanning path.

---

## FFI Surface By File

## `classic::config` entry points

### `yaml_data_load(yaml_dir_root, yaml_dir_data, game, game_version) -> Result<Box<YamlData>>`

Forwards to:

- `classic_shared_core::get_runtime()`
- `classic_config_core::YamlDataCore::load_from_yaml_files(...)`

Current bridge behavior:

- always uses the 2-directory loader shape `[yaml_dir_root, yaml_dir_data]`
- blocks on the shared runtime with `block_on(...)`
- preserves load failure as a CXX `Result` error string instead of using sentinel values

### Selected scalar and vector getters

These entry points expose only a slice of `YamlDataCore`:

- scalar field getters such as `yaml_data_classic_version`, `yaml_data_crashgen_name_field`, `yaml_data_xse_acronym`, `yaml_data_autoscan_text`, and `yaml_data_game_version`
- helper-backed accessors `yaml_data_get_crashgen_name`, `yaml_data_get_game_root_name`, and `yaml_data_get_crashgen_ignore`
- vector getters such as `yaml_data_classic_records_list`, `yaml_data_game_ignore_plugins`, `yaml_data_game_ignore_records`, and `yaml_data_ignore_list`

Forwarding notes:

- most scalar getters read the stored `YamlDataCore` field directly
- `yaml_data_get_crashgen_name()` and `yaml_data_get_game_root_name()` forward through `YamlDataCore` helper methods
- `yaml_data_get_crashgen_ignore()` forwards through `YamlDataCore::get_crashgen_ignore()`

### Flattened map getters

These functions flatten `IndexMap` fields into paired vectors because the bridge does not share map wrapper types across modules:

- suspects error map: `yaml_data_suspects_error_keys()` and `yaml_data_suspects_error_values()`
- mods maps: `yaml_data_mods_core_*`, `yaml_data_mods_freq_*`, `yaml_data_mods_conf_*`, `yaml_data_mods_solu_*`, `yaml_data_mods_opc2_*`, and `yaml_data_mods_folon_*`

Important current boundary:

- `yaml_data_suspects_stack_keys()` exposes only keys from `YamlDataCore.suspects_stack_list`
- the bridge does **not** expose the corresponding `Vec<String>` values even though the Rust field is `IndexMap<String, Vec<String>>`
- the bridge exposes no raw `CrashgenEntryRaw` or `crashgen_registry` data at all

---

## `classic::files` entry points

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

### `log_collector_collect_all` and `log_collector_collect_crash_logs`

Forwards to `LogCollector::collect_all()` and `collect_crash_logs()`.

Bridge narrowing:

- returned paths are lossy UTF-8 strings
- the bridge does not expose `move_from_base_folder()`, `copy_from_xse_folder()`, `crash_logs_dir()`, or `pastebin_dir()` separately

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

- `YamlDataCore::load_from_yaml_files(...)`
- `classic_scanlog_core::build_analysis_config_from_yaml(...)`

And also uses bridge-local helpers:

- `load_exclude_log_records(yaml_dir_data)`
- `resolve_formid_db_paths(yaml_dir_root, yaml_dir_data, game)`

Current bridge behavior that matters:

- `remove_list` comes from `CLASSIC Main.yaml` key `exclude_log_records`, not from the public `classic::config` surface
- FormID DB paths are assembled from three sources in bridge code: main DB, hardcoded FOLON DB for Fallout 4 and Fallout 4 VR, and user settings entries from `CLASSIC Settings.yaml`
- relative user DB paths are resolved relative to `yaml_dir_data`
- paths are deduplicated before pool initialization

Important boundary:

- this bridge still reads `CLASSIC Settings.yaml` directly for FormID DB paths instead of using `ClassicConfig.formid_databases` through a bridge DTO

### `orchestrator_new(config) -> Result<Box<Orchestrator>>`

Forwards to `classic_scanlog_core::OrchestratorCore::new(...)` and optionally `attach_database_pool(...)`.

Current bridge behavior:

- if `config.inner.show_formid_values` is false, no database pool is created
- if it is true, the bridge constructs its own `DatabasePool`, applies a short-scan profile, initializes it from the resolved DB path list, and attaches it to the orchestrator
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

### `orchestrator_process_log(orch, log_path) -> Result<ScanResult>`

Forwards to `OrchestratorCore::process_log(...)`.

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

- `max_concurrent == 0` becomes `None`, which activates the crate adaptive concurrency path
- results are returned in completion order, not input order, because the lower layer uses unordered buffering

### `orchestrator_process_logs_batch_with_progress(...) -> Vec<BatchScanResult>`

This is mostly bridge-local orchestration around `OrchestratorCore::process_log_with_progress(...)`.

Current behavior that matters:

- emits `Queued`, `Started`, `Phase`, `Completed`, and `Failed` events to the C++ callback
- preserves `input_index` so callers can map completion-order results back to the original request list
- computes adaptive concurrency locally when `max_concurrent == 0`
- tries to drain ready phase events before terminal completion events so per-log event ordering stays monotonic
- still returns results in completion order, not input order

## Small scan utilities

### `detect_vr_log(content) -> bool`

This is bridge-local logic. It checks only for the substrings `Fallout4VR.esm` or `SkyrimVR.esm`.

### `detect_crash_pattern(content) -> String`

Creates `classic_scanlog_core::LogParser::new(None)` and forwards to `LogParser::parse_crash_header(...)`, returning only the parsed `main_error` text.

Fail-soft behavior:

- parser construction failure or header parse failure becomes `""`

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
- `ScanResult`, `BatchScanResult`, and `PapyrusStatsDto`
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
- does not expose `ClassicConfig` at all
- drops `suspects_stack_list` values
- drops `crashgen_registry` and other richer YAML-derived structures

## `src/files.rs`

- narrows `BackupInfo` to a summary string and existence boolean
- narrows `FileOperationResult` to a summary string, dropping structured partial-failure detail
- fixes `FileIOCore` configuration instead of exposing it
- adds report-file helpers that are bridge-local and therefore do not expand the underlying crate API

## `src/database.rs`

- narrows `DatabasePool` to only a few lifecycle and lookup calls
- collapses `Option<String>` and `DatabaseError` into `String` or empty results
- flattens batch results into strings and fixes batch size at `50`
- does not expose stats, optimization, or connection rebalance behavior

## `src/scanner.rs`

- exposes the main scan path, but not the full `OrchestratorCore` helper surface
- constructs DB path lists in bridge code instead of exposing a first-class config bridge for that data
- drops `AnalysisResult` fields that some lower-level Rust and parity paths still use
- adds bridge-local batch progress coordination, VR detection, crash-pattern extraction, and DB-profile tuning

---

## Contributor Debugging Notes

## Config flow

When C++ YAML-backed scan behavior looks wrong, check these in order:

1. confirm whether the frontend used `classic::config::yaml_data_load()` or the fuller `classic::scanner::build_full_scan_config()` path
2. verify the bridge got the 2-directory layout the Rust loader expects
3. remember that `yaml_data_load()` loads bulk scan YAML only and does not read `CLASSIC Settings.yaml`
4. if stack-suspect output is incomplete, remember the bridge exports only stack keys, not stack value lists

## File flow

When file helper output looks weaker than the Rust crate API:

1. remember that backup and game-file entry points intentionally return summary strings, not structured result objects
2. check whether `write_file_string()` failed because parent directories do not exist
3. remember that `GameFilesManager` pattern matching is case-insensitive substring matching over direct children of `game_root`
4. remember that `discover_report_files()` is non-recursive and silently returns empty on unreadable directories

## Database flow

When FormID lookup looks empty:

1. check whether the pool was actually initialized and `db_pool_is_available()` is true
2. remember that missing DB files may be skipped during initialization without surfacing an error
3. remember that `db_pool_get_entry()` returns empty string for both miss and failure
4. if batch results look odd, remember the bridge zips `formids` and `plugins` and silently truncates to the shorter length
5. if ordering matters, remember the batch result vector comes from a `HashMap` and is not stable

## Scan flow

When the C++ scan path diverges from the crate docs:

1. check whether the frontend used `orchestrator_new()` or `orchestrator_new_minimal()`
2. if FormID values are missing, verify `show_formid_values` was true when the full config was built
3. remember that the bridge resolves FormID DB paths itself, including a hardcoded FOLON DB path for Fallout 4 modes
4. if batch progress looks surprising, remember result order is completion order and `input_index` is the stable correlation key
5. use `CLASSIC_SCAN_DIAGNOSTICS` to turn on progress diagnostics and `CLASSIC_DB_COUNTER_INTERVAL` to control periodic DB counter logging

## Papyrus flow

When Papyrus monitoring looks stale:

1. confirm whether the caller used `start_monitoring()` or `analyze_full()`
2. remember that `start_monitoring()` begins at end-of-file, so old lines are intentionally ignored
3. remember that `papyrus_check_updates()` suppresses update errors and returns last-known stats
4. if a log was rotated or truncated, lower layers reset and re-read from the beginning

---

## Source-Backed Limits And Caveats

- `src/config.rs` is a narrow read bridge over `YamlDataCore`, not a general config bridge
- `src/config.rs` does not expose `YamlDataCore.suspects_stack_list` values, only keys
- `src/files.rs::write_file_string()` does not create parent directories because it uses `FileIOCore::write_file()`
- `src/files.rs::discover_report_files()` is bridge-local, non-recursive, and fail-soft on unreadable directories
- `src/database.rs::db_pool_get_entry()` cannot distinguish miss, closed pool, and query failure
- `src/database.rs::db_pool_get_entries_batch()` fixes batch size at `50` and flattens `formid:plugin` keys into tab-delimited strings
- `src/scanner.rs` still reads `CLASSIC Settings.yaml` directly for user FormID DB paths
- `src/scanner.rs` hardcodes `databases/FOLON FormIDs.db` for `Fallout4` and `Fallout4VR`
- `src/scanner.rs::orchestrator_process_logs_batch_with_progress()` is bridge-local coordination on top of per-log crate calls, not a direct wrapper over one lower-level batch API
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
