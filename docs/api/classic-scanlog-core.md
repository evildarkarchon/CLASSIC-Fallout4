# `classic-scanlog-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-scanlog-core/`](../../ClassicLib-rs/business-logic/classic-scanlog-core).

Crate metadata:

- Crate: `classic-scanlog-core`
- Description: `Pure Rust business logic for log parsing and analysis (NO PyO3)`

This crate is the Rust-side crash-log analysis layer for CLASSIC. It parses crash logs, builds an analysis pipeline, applies scan rules and registries, and produces contributor- and user-facing autoscan report text.

It is a pure Rust business-logic crate. It does not own a UI surface, binding layer, or Tokio runtime.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- parse Bethesda-style crash logs into named sections
- build an analysis pipeline from loaded YAML/config data
- analyze plugins, FormIDs, named records, suspects, GPU hints, and crashgen settings
- generate Python-parity-style autoscan report fragments or full reports
- batch-process logs or write `-AUTOSCAN.md` outputs from Rust

Do not use this crate for:

- loading CLASSIC YAML files directly
- owning a shared runtime or creating a new Tokio runtime per caller
- exposing FFI or binding-specific wrapper types
- front-end presentation logic

Those concerns live in related crates such as [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core), [`classic-shared-core`](../../ClassicLib-rs/foundation/classic-shared-core), [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node), and [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge).

---

## Module Map

### `orchestrator`

Top-level scan pipeline and the main integration surface.

- `AnalysisConfig` - assembled scan configuration for a game/version mode
- `AnalysisResult` - result payload for one analyzed log
- `OrchestratorCore` - async scan runner and report writer
- `ScanProgressPhase` - coarse phase callbacks for progress reporting
- `build_analysis_config_from_yaml()` - canonical bridge from [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core)
- `resolve_batch_concurrency()` - public helper for the same batch-concurrency policy used by `process_logs_batch()`

### `parser`

Log segmentation, header parsing, pattern matching, and streaming helpers.

- `LogParser` - primary parser with named-section APIs and caches
- `StreamingLogParser` - buffered streaming parser for large logs
- `StreamingIteratorParser` - iterator-first streaming utilities

### `crashgen_registry` and `settings_validator`

Crashgen-specific settings validation.

- `CrashgenRegistry` - normalized crashgen-name lookup table
- `CrashgenEntry` - per-crashgen display/check/rules entry
- `CheckId` - named built-in settings checks
- `SettingsValidator` - applies YAML rule sets or legacy fallback checks

### `plugin_analyzer`, `formid_analyzer`, `record_scanner`, `suspect_scanner`, `mod_detector`

Analysis helpers used by the orchestrator and usable independently.

- `PluginAnalyzer` - plugin extraction, plugin-limit checks, plugin suspect matching
- `FormIDAnalyzerCore` - async FormID correlation and optional DB-backed value lookup
- `RecordScanner` - named-record detection
- `SuspectScanner` - known error/stack suspect matching
- `detect_mods_single()`, `detect_mods_double()`, `detect_mods_important()` - standalone mod checks

### `report`

Report composition primitives.

- `ReportFragment` - immutable fragment unit
- `ReportComposer` - combines fragments into a final report
- `ReportGenerator` - Python-parity report sections
- `StringPool` - shared string interning helper

### Utility modules

- `version` - crashgen version parsing and status checks
- `gpu_detector` - GPU vendor extraction from system sections
- `fcx_handler` - FCX-mode message/state container
- `papyrus` - Papyrus log monitoring, separate from crash-log autoscan
- `formid` - legacy/back-compat FormID helper wrapper types
- `segment_key` - named section constants like `settings`, `plugins`, and `stack_dump`

---

## Public API Surface

## `AnalysisConfig`

`AnalysisConfig` is the main input model for `OrchestratorCore`.

Important fields include:

- identity and version data: `game`, `crashgen_name`, `crashgen_latest`, `game_version`, `game_version_vr`, `xse_acronym`, `classic_version`
- behavior flags: `show_formid_values`, `fcx_mode`, `simplify_logs`
- scan inputs: `ignore_plugins`, `ignore_records`, `ignore_list`, `remove_list`
- YAML-derived suspect rules and mod databases: `suspect_error_rules`, `suspect_stack_rules`, `mods_freq`, `mods_solu`
- structured core mod entries: `mods_core` (`Vec<CoreModEntry>`)
- structured mod conflict entries: `mods_conf` (`Vec<ModConflictEntry>`)
- structured solution entries: `mods_solu` (`Vec<ModSolutionEntry>`) with grouped `criteria.any` / `criteria.all`, optional `exceptions`, and explicit `name` / `description` fields
- named-record and settings inputs: `classic_records_list`, `crashgen_registry`

Important constructors/helpers:

- `AnalysisConfig::new(game, selected_game_version)`
- `build_analysis_config_from_yaml(yaml, game, selected_game_version, show_formid_values, fcx_mode, simplify_logs, remove_list)`

Contributor notes:

- `build_analysis_config_from_yaml()` is the canonical bridge from [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core).
- Version Registry data is preferred when available; YAML values are used as compatibility fallback.
- OG/VR selection is resolved before scan-time settings validation from `selected_game_version` plus Version Registry data.
- VR mode is still tracked internally and is not exposed as a public field; `game_version_vr` carries the VR version string when registry data provides one.

## `OrchestratorCore`

`OrchestratorCore` coordinates the full scan pipeline.

Important methods:

- `OrchestratorCore::new(config) -> Result<Self, ScanLogError>`
- `with_database_pool(pool) -> Result<Self, ScanLogError>`
- `attach_database_pool(&mut self, pool) -> Result<(), ScanLogError>`
- `async_enter(db_paths) -> Result<(), ScanLogError>`
- `async_exit() -> Result<(), ScanLogError>`
- `process_log(log_path) -> Result<AnalysisResult, ScanLogError>`
- `process_log_with_progress(log_path, on_phase) -> Result<AnalysisResult, ScanLogError>`
- `process_logs_batch(log_paths, max_concurrent) -> Vec<AnalysisResult>`
- `write_reports_batch(reports) -> Result<Vec<PathBuf>, ScanLogError>`

Useful helpers that are part of the public surface:

- `config()`
- `resolve_batch_concurrency(total_logs, max_concurrent) -> usize`
- `reformat_crash_data_inline()`
- `detect_incomplete_log()` / `detect_incomplete_log_slice()`
- `detect_failed_log()`
- `create_report_generator()`
- `create_settings_validator()`
- `check_crashgen_version_list()`
- `check_crashgen_version_for_detected_game()`
- `check_loadorder_exists()` and `load_loadorder_async()`
- `is_feature_complete()`

Behavior worth knowing:

- `process_logs_batch()` is fail-soft: per-log failures become `AnalysisResult::failure(...)` entries instead of aborting the batch.
- Batch result order is not guaranteed to match input order because it uses unordered buffering.
- `resolve_batch_concurrency()` returns `1` for empty batches, clamps explicit overrides to a minimum of `1`, and otherwise uses the crate's adaptive CPU-aware default.
- `write_reports_batch()` logs write failures and returns only successfully written paths.
- `mods_solu` detection is no longer routed through the legacy single-map matcher; it evaluates grouped `any` / `all` criteria, suppresses matches through optional exceptions, and renders report titles/bodies from the structured `name` / `description` fields.
- `is_feature_complete()` currently means plugin analyzer and suspect scanner are present; a database pool is optional.

## `AnalysisResult`

`AnalysisResult` is the report/result payload returned by the orchestrator.

Key fields:

- `log_path`, `report_lines`, `success`, `error`
- `processing_time_us`, `processing_time_ms`
- `formid_count`, `plugin_count`, `suspect_count`
- Python-parity counters: `scanned`, `incomplete`, `failed`, `trigger_scan_failed`

Important constructors/mutators:

- `AnalysisResult::success(log_path, report_lines, processing_time_us)`
- `AnalysisResult::failure(log_path, error)`
- `mark_incomplete()`
- `mark_failed()`

## `LogParser`

`LogParser` is the primary parsing API.

Important methods:

- `LogParser::new(None)`
- `add_pattern(name, pattern)`
- `clear_caches()`
- `parse_all_sections_arc()` - primary segmentation API
- `parse_all_sections()` - `String`-based wrapper
- `get_section()`
- `parse_crash_header()`
- `find_patterns()` / `find_patterns_chunked()`
- `extract_formids()` / `extract_plugins()` / `extract_addresses()` / `find_errors()`
- `get_segment_sizes()` / `get_stats()` / `benchmark()`

Named section guarantees from `parse_all_sections_arc()` and `parse_all_sections()`:

- all 8 keys are always present
- keys are `settings`, `system`, `callstack`, `modules`, `xse_modules`, `plugins`, `registers`, `stack_dump`
- absent sections map to empty vectors instead of being omitted

Deprecated parser APIs still present:

- `parse_segments()`
- `parse_segments_parallel()` -- Python binding now returns `dict[str, list[str]]` (was `list[list[str]]`) and emits `DeprecationWarning`

These are compatibility shims over `parse_all_sections_arc()` and are marked deprecated in source. The Python binding's `parse_segments_parallel` was migrated to delegate to `parse_all_sections_arc` with a dict return type matching `parse_all_sections`.

## `CrashgenRegistry`, `CrashgenEntry`, and `CheckId`

These types model per-crashgen settings behavior.

- `CheckId` variants: `Achievements`, `MemoryManagement`, `ArchiveLimit`, `LooksMenu`
- `CrashgenEntry` fields: `display_section`, `ignore_keys`, `checks`, `settings_rules`
- `CrashgenRegistry::new(entries, default)` normalizes keys for lookup
- `CrashgenRegistry::lookup(name)` is case-insensitive and whitespace-normalized

Unknown crashgen names fall back to the registry default entry.

## `SettingsValidator`

`SettingsValidator` validates parsed crashgen settings against either YAML-defined rules or legacy built-in checks.

Important methods:

- `SettingsValidator::new(crashgen_name, entry)`
- `scan_all_settings(crashgen, xse_modules, crashgen_version, config_layout)`
- `check_disabled_settings(crashgen)`
- `scan_buffout_achievements_setting(...)`
- `scan_buffout_memorymanagement_settings(...)`
- `scan_archivelimit_setting(...)`
- `scan_buffout_looksmenu_setting(...)`
- `scan_addictol_settings_scaffold(...)`

Contributor notes:

- If `CrashgenEntry.settings_rules` exists, the validator prefers those rules and only falls back to legacy checks for uncovered areas.
- Rule-driven preflight outcomes can now carry a report bucket from [`classic-crashgen-settings-core`](../../ClassicLib-rs/business-logic/classic-crashgen-settings-core); `error_information` outcomes are promoted into the report's `Error Information` section while the default bucket still renders under settings-related issues.
- `check_disabled_settings()` always runs and uses `ignore_keys` as its skip set.
- In `classic-scanlog-core`, `config_layout` is currently a coarse valid/invalid fact for settings evaluation: `derive_scanlog_config_layout()` returns `Og` for parseable detected versions and `Unknown` otherwise.
- OG vs VR selection is handled earlier through `AnalysisConfig` construction and Version Registry data, not by `config_layout` in this crate.
- The current Addictol path is explicitly a scaffold notice, not a full rule implementation.

## `PluginAnalyzer`

Important methods:

- `PluginAnalyzer::new(...)`
- `loadorder_scan_loadorder_txt()`
- `loadorder_scan_log(segment_plugins, game_version, version_current)`
- `check_plugin_limit(segment_plugins, game_version, version_current)`
- `plugin_match(...)`
- `filter_ignored_plugins(...)`

Standalone helpers:

- `detect_plugins_batch(logs)`
- `contains_plugin(line)`

Behavior worth knowing:

- plugin maps are stored as `IndexMap<String, String>` to preserve load order for parity
- duplicate plugins are skipped case-insensitively
- plugin-limit handling depends on detected game version classification and crashgen version

## `FormIDAnalyzerCore`

Important methods:

- `FormIDAnalyzerCore::new(db_pool, show_formid_values, crashgen_name, important_mods, mods_single, mods_double)`
- `extract_formids(segment_callstack)`
- `formid_match(formids_matches, crashlog_plugins)`
- `lookup_formid_value(formid, plugin)`
- `detect_mods_single_basic(crashlog_plugins)`
- `detect_mods_conflicts(crashlog_plugins)`
- `detect_mods_important_basic(crashlog_plugins, gpu_rival, xse_modules)`

Standalone helpers:

- `extract_formids_batch(callstack_segments)`
- `is_valid_formid(formid)`
- `validate_formids_batch(formids)`

Behavior worth knowing:

- `extract_formids()` keeps `00000000` but filters `FF`-prefixed plugin-limit markers.
- `formid_match()` is async and does batched database lookups when `show_formid_values` is enabled and a `DatabasePool` is attached.
- DB lookup failures are intentionally fail-soft; rows still render without descriptions.

## Report types

- `ReportFragment` - immutable content container with `empty()`, `from_lines()`, `combine()`, `to_list()`, `is_empty()`
- `ReportComposer` - `add()`, `add_many()`, `compose()`, `compose_optimized()`, `build_string()`, `get_pool_stats()`
- `ReportGenerator` - `new()`, `with_config()`, and section builders such as `generate_header()`, `generate_error_section_with_status()`, `generate_settings_section_header()`, and `generate_footer()`
- `StringPool` - `intern()`, `intern_batch()`, `get_stats()`, `clear()`

The report module is designed around Python-parity text output, not a stable intermediate schema.

## Other public utilities

- `version`: `CrashgenVersion`, `CrashgenVersionStatus`, `crashgen_version_gen()`, `check_crashgen_version_status()`
- `gpu_detector`: `GpuVendor`, `GpuInfo`, `GpuDetector`
- `papyrus`: `PapyrusAnalyzer`, `PapyrusStats`, `PapyrusError`
- `fcx_handler`: `FcxModeHandler`, `FcxResetError`, `ConfigIssue`, `GLOBAL_FCX_HANDLER`
- `formid`: `RustFormIDAnalyzer`, `FormIDAnalyzer` legacy wrapper
- `detect_vr_log(content)` - simple Fallout 4 VR log detection helper

### FCX global state reset contract

`FcxModeHandler::reset_global_state()` is the contributor-facing reset hook for the process-wide FCX singleton.

- Signature: `Result<(), FcxResetError>`
- Locking behavior: it uses a blocking mutex lock, so reset requests wait for in-flight FCX work instead of silently skipping under contention
- Success path: `Ok(())` means stale cached FCX results were cleared for a new scan session
- No-op path: `Err(FcxResetError::Unnecessary)` means the singleton was already clean; bindings should treat this as benign and continue

Binding expectation:

- binding entrypoints should auto-call the reset hook at scan start so each scan session begins from clean FCX state
- bindings may expose explicit reset entrypoints for callers that want to clear the singleton between sessions
- bindings should not treat `Unnecessary` as a scan-start failure

---

## Scan And Processing Flow

The main contributor-facing pipeline looks like this:

1. Load YAML/config data with [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core).
2. Convert `YamlDataCore` into `AnalysisConfig` with `build_analysis_config_from_yaml()`.
3. Construct `OrchestratorCore::new(config)`.
4. Optionally attach a [`classic-database-core`](../../ClassicLib-rs/business-logic/classic-database-core) `DatabasePool` for FormID value lookups.
5. `process_log()` reads the file with [`classic-file-io-core`](../../ClassicLib-rs/business-logic/classic-file-io-core) and preprocesses lines with `reformat_crash_data_inline()`.
6. `LogParser::parse_all_sections_arc()` builds named sections.
7. The orchestrator extracts header metadata, resolves crashgen identity/version status, and builds report helpers.
8. Analysis passes run over the prepared data:
   - plugin extraction and plugin suspect matching
   - suspect/error scanning
   - crashgen settings validation
   - mod detection
   - FormID extraction and optional DB value lookup
   - named-record scanning
   - FCX message inclusion
9. `ReportComposer` combines fragments and produces `report_lines`.
10. Callers can write report files with `write_reports_batch()` or handle `report_lines` directly.

One subtle integration rule from the source: the effective crashgen name used for settings and report text can switch to `Addictol` when the header or XSE modules indicate it, even if the base `AnalysisConfig` was built for another crashgen.

---

## Error Handling Model

Most crate APIs use `Result<T, ScanLogError>` via `error::Result<T>`.

`ScanLogError` variants include:

- `ParseError(String)`
- `InvalidFormID(String)`
- `DatabaseError(String)`
- `IoError(std::io::Error)`
- `FileIOError(classic_file_io_core::error::FileIOError)`
- `RegexError(regex::Error)`
- `ConfigError(String)`
- `AnalysisError(String)`
- `InvalidInput(String)`
- `PatternError(aho_corasick::BuildError)`
- `ReportError(String)`
- `GpuError(String)`
- `ValidationError(String)`
- `Internal(String)`

Important exceptions to that model:

- `process_logs_batch()` converts per-log failures into `AnalysisResult::failure(...)` instead of returning an error for the whole batch.
- `PapyrusAnalyzer` uses its own `PapyrusError` enum.
- Some constructors currently return `Result` for API consistency even though the present implementation does not fail in normal construction paths.

---

## Async, Runtime, And Concurrency Notes

This crate exposes async APIs but does not create its own runtime.

- Async entry points include `OrchestratorCore::async_enter()`, `async_exit()`, `process_log()`, `process_log_with_progress()`, `process_logs_batch()`, `load_loadorder_async()`, `write_reports_batch()`, and `FormIDAnalyzerCore::formid_match()`.
- The crate depends on `tokio` and `futures`, but the source does not construct a Tokio runtime in production code.
- In CLASSIC, higher layers are expected to use the shared runtime model from [`classic-shared-core`](../../ClassicLib-rs/foundation/classic-shared-core) rather than introducing a second runtime.

Internal concurrency/performance patterns visible in the source:

- Rayon is used for CPU-bound parsing and batch helpers.
- `process_logs_batch()` uses bounded async concurrency with `buffer_unordered()` and resolves its worker count through `resolve_batch_concurrency()`.
- `LogParser` maintains bounded LRU caches for segments and pattern matches.
- `ReportComposer` switches to parallel composition when fragment count crosses its threshold.

Contributor rule: keep new async work compatible with the shared runtime model and avoid adding runtime ownership to this crate.

---

## Feature Flags

Contributor-relevant feature flags from `Cargo.toml`:

- default features: none
- `mimalloc` - enables `mimalloc` as the crate's global allocator

Notes:

- The allocator switch is opt-in and framed in source as a performance optimization for allocation-heavy workloads.
- Because it installs a global allocator for the crate build, contributors should treat it as an environment/performance choice rather than a behavioral feature.

---

## Related Crates And Integration Points

- [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core) - provides `YamlDataCore` and crashgen registry source data used by `build_analysis_config_from_yaml()`
- [`classic-crashgen-settings-core`](../../ClassicLib-rs/business-logic/classic-crashgen-settings-core) - typed settings-rule evaluation used by `SettingsValidator`
- [`classic-version-registry-core`](../../ClassicLib-rs/business-logic/classic-version-registry-core) - resolves game-version matches and valid crashgen versions
- [`classic-database-core`](../../ClassicLib-rs/business-logic/classic-database-core) - optional FormID description lookups through `DatabasePool`
- [`classic-file-io-core`](../../ClassicLib-rs/business-logic/classic-file-io-core) - async file reads and writes used by the orchestrator
- [`classic-shared-core`](../../ClassicLib-rs/foundation/classic-shared-core) - shared runtime policy used by higher layers in this repo
- [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node) and [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge) - binding layers that should stay aligned with this crate's public behavior

In practice, `classic-scanlog-core` is the downstream analysis layer that turns config/YAML data into scan results and autoscan reports.

---

## Usage Example

This example follows the intended contributor flow: load YAML with [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core), build an `AnalysisConfig`, and process a log with `OrchestratorCore`.

```rust
use classic_config_core::YamlDataCore;
use classic_scanlog_core::{
    OrchestratorCore,
    build_analysis_config_from_yaml,
};
use std::path::PathBuf;

# async fn example() -> Result<(), Box<dyn std::error::Error>> {
let yaml_dirs = vec![
    PathBuf::from("C:/CLASSIC"),
    PathBuf::from("C:/CLASSIC/CLASSIC Data"),
];

let yaml = YamlDataCore::load_from_yaml_files(
    yaml_dirs,
    "Fallout4".to_string(),
    "auto".to_string(),
)
.await?;

let config = build_analysis_config_from_yaml(
    &yaml,
    "Fallout4",
    "auto",
    false,          // show_formid_values
    false,          // fcx_mode
    false,          // simplify_logs
    Vec::new(),     // remove_list
);

let orchestrator = OrchestratorCore::new(config)?;
let result = orchestrator
    .process_log("C:/CLASSIC/crash-2026-03-09.log".to_string())
    .await?;

if result.success {
    println!("Processed {} in {} ms", result.log_path, result.processing_time_ms);
    println!("Report lines: {}", result.report_lines.len());
}
# Ok(())
# }
```

If you need FormID descriptions instead of raw IDs only, attach a `DatabasePool` before calling `process_log()`.

---

## Contributor Notes And Known Limits

- `classic-scanlog-core` is downstream of [`classic-config-core`](../../docs/api/classic-config-core.md); update both docs if the YAML-to-analysis contract changes.
- `parse_segments()` and `parse_segments_parallel()` are still public but explicitly deprecated. The Python binding `parse_segments_parallel` now returns `dict[str, list[str]]` instead of `list[list[str]]`.
- The source contains performance claims in comments and docs, but this page does not treat them as compatibility guarantees.
- `process_logs_batch()` does not preserve input ordering.
- `SettingsValidator::scan_addictol_settings_scaffold()` is intentionally a scaffold, not a complete Addictol rules implementation.
- `derive_scanlog_config_layout()` is effectively a valid/invalid gate today: it returns `Og` for parseable detected versions and `Unknown` otherwise.
- `classic-crashgen-settings-core` still defines `ConfigLayout::Vr`, but this crate no longer uses `ConfigLayout` as the OG/VR selector; that decision now lives in Version Registry-backed config building.
- Report output is designed for Python parity, so text shape matters to downstream consumers more than a stable structured schema does.

If you extend this crate, update this document when you change:

- re-exported types in `lib.rs`
- the named-section contract in `parser`
- `AnalysisConfig` construction rules or Version Registry precedence
- runtime/concurrency expectations
- report text or helper behavior that bindings depend on
