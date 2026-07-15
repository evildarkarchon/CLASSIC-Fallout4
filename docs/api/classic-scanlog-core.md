# `classic-scanlog-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-scanlog-core/`](../../business-logic/classic-scanlog-core).

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
- prepare an existing Crash Log for analysis from path-backed or in-memory YAML Data
- execute a high-level Crash Log Scan Run with Rust-owned discovery, setup validation, intake, reporting, and Unsolved Logs policy
- build an analysis pipeline from loaded YAML/config data
- analyze plugins, FormIDs, named records, suspects, GPU hints, and crashgen settings
- generate Python-parity-style autoscan report fragments or full reports
- batch-process logs or write `-AUTOSCAN.md` outputs from Rust

Do not use this crate for:

- general-purpose YAML editing or settings-cache operations
- owning a shared runtime or creating a new Tokio runtime per caller
- exposing FFI or binding-specific wrapper types
- front-end presentation logic

Those concerns live in related crates such as [`classic-config-core`](../../business-logic/classic-config-core), [`classic-shared-core`](../../foundation/classic-shared-core), [`classic-node`](../../node-bindings/classic-node), and [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge).

---

## Module Map

### `scan_intake`

Crash Log Scan Intake prepares an existing Crash Log for analysis before orchestration starts.

- `CrashLogScanIntake` - path-backed or in-memory intake builder
- `CrashLogScanOptions` - caller scan flags for FormID values, FCX mode, and simplify logs
- `CrashLogScanFacts` - typed FormID and Unsolved Logs facts projected by the caller's User Settings adapter
- `CrashLogScanIntakePaths` - root/data paths used for path-backed YAML Data and canonical backup placement
- `ScanReadyAnalysis` - scan-ready payload containing `AnalysisConfig`, FormID readiness, and cache profile choice
- `FormIdReadiness` - whether FormID databases should initialize and which paths to use
- `ShortScanCacheProfile`, `SHORT_SCAN_CACHE_PROFILE` - short native-scan DB cache profile selected by intake
- `load_simplify_remove_list()`, `resolve_formid_database_paths()` - characterization-friendly helpers for YAML Data and typed-path readiness rules
- `scan_sidecar_settings` - crate-private implementation that keeps YAML Data sidecar names, compatibility paths, normalization, validation, and fail-soft behavior local to intake

### `orchestrator`

Top-level scan pipeline and the main integration surface.

- `AnalysisConfig` - assembled scan configuration for a game/version mode
- `AnalysisResult` - result payload for one analyzed log
- `BatchScanOptions`, `BatchScanEvent`, `BatchScanEventKind`, `IndexedAnalysisResult` - indexed/evented batch scan primitives for thin bindings
- `OrchestratorCore` - async scan runner and report writer
- `ScanProgressPhase` - coarse phase callbacks for progress reporting
- `build_analysis_config_from_yaml()` - canonical bridge from [`classic-config-core`](../../business-logic/classic-config-core)
- `resolve_batch_concurrency()` - public helper for the same batch-concurrency policy used by `process_logs_batch()`

### `scan_run`

Crash Log Scan Run owns discovery, optional FCX setup validation, and the post-intake transaction for accepted Crash Logs.

- `scan_run::contract::execute(request, cancellation, observer)` - final single-operation Rust contract used by the coordinated cutover
- `scan_run::contract::Request::{Standard, Targeted}` - tagged request whose constructors make FCX-without-context and Targeted Unsolved Logs movement unrepresentable
- `scan_run::contract::{Cancellation, Observer, Event}` - separate opaque cancellation and optional non-controlling lifecycle observation
- `scan_run::contract::{RunResult, LogResult, LogDisposition, InfrastructureError, InfrastructureErrorStage}` - retained discovery/concurrency, typed per-log dispositions, and stable run-wide failures
- `CrashLogScanRunService` - high-level facade that owns Standard/Targeted discovery, FCX setup validation, intake preparation, and scan-run execution
- `CrashLogScanRunServiceRequest` - YAML roots, game/version, scan options, source, setup context, movement, concurrency, cancellation, and ordering preference
- `CrashLogScanSource`, `StandardCrashLogScanSource`, `TargetedCrashLogScanSource` - typed Standard versus Targeted discovery requests
- `CrashLogScanDiscoveryResult`, `CrashLogScanRejectedInput` - accepted logs, rejected Targeted inputs, and searched locations
- `CrashLogScanSetupContext`, `CrashLogScanSetupResult`, `CrashLogScanSetupCheck`, `CrashLogScanSetupPathUpdate` - typed FCX setup inputs/results
- `CrashLogScanRunStatus` - top-level lifecycle status returned by the high-level service
- `CrashLogScanRun` - deep module that executes selected Crash Logs after Crash Log Scan Intake
- `CrashLogScanRunRequest` - selected Crash Logs, run intent, concurrency, optional cancellation, and ordering preference
- `CrashLogScanRunIntent`, `StandardCrashLogScanRunIntent`, `StandardUnsolvedLogsIntent` - Standard versus Targeted Crash Log Scan Run behavior and Unsolved Logs intent
- `CrashLogScanRunResult`, `CrashLogScanRunLogOutcome`, `CrashLogScanOutcome` - per-run and per-log observable outcomes
- `CrashLogScanRunEvent`, `CrashLogScanRunEventKind` - progress events emitted through the module interface

The module keeps `OrchestratorCore` as internal analysis implementation, writes Autoscan Reports itself, and applies Unsolved Logs rules in Rust.

### `parser`

Log segmentation, header parsing, pattern matching, and streaming helpers.

- `LogParser` - primary parser with named-section APIs and caches
- `StreamingLogParser` - buffered streaming parser for large logs
- `StreamingIteratorParser` - iterator-first streaming utilities

### `crashgen_registry` and `settings_validator`

Crashgen-specific settings validation.

- `CrashgenRegistry` - normalized crashgen-name lookup table
- `CrashgenEntry` - per-crashgen display/ignore/rules entry
- `SettingsValidator` - scanlog adapter over YAML-backed Crashgen Expectations and Disabled Setting Notices

### `plugin_analyzer`, `formid_analyzer`, `record_scanner`, `suspect_scanner`, `mod_detector`

Analysis helpers used by the orchestrator and usable independently.

- `PluginAnalyzer` - plugin extraction, plugin-limit checks, plugin suspect matching
- `FormIDAnalyzerCore` - async FormID correlation and optional DB-backed value lookup
- `RecordScanner` - named-record detection with per-instance fallible `OnceLock<AhoCorasick>` matcher caches built on first use
- `SuspectScanner` - known error/stack suspect matching
- `detect_mods_single()`, `detect_mods_double()`, `detect_mods_important()` - standalone mod checks

`record_scanner` contributor note:

- `RecordScanner` now exposes additive fallible APIs for matcher-building/search paths: `try_scan_named_records()`, `try_scan_named_records_with_crashgen_name()`, `try_scan_named_records_with_crashgen_name_and_lowercase()`, and `try_extract_records()`.
- The free function `try_scan_records_batch()` is the fallible counterpart to `scan_records_batch()`.
- Existing infallible methods and `scan_records_batch()` remain compatibility wrappers with unchanged success output shapes; callers that need to distinguish invalid input or Aho-Corasick matcher-build failures should use the `try_*` variants.
- The lowercase-reuse fallible API returns `ScanLogError::InvalidInput` when the original and lowercased slices are not index-aligned instead of panicking.

`mod_detector` contributor note:

- `detect_mods_single()`, `detect_mods_double()`, and `detect_mods_batch()` now reuse process-wide bounded `LazyLock<quick_cache::sync::Cache<...>>` matcher caches keyed by normalized content hashes of the relevant mod-list inputs.
- Those caches intentionally cover only input-derived alternation regexes in the hot paths. They are not a repo-wide "make every regex static" sweep; truly constant regex helpers should still compile once through dedicated `LazyLock` statics.
- Cache validation should assert reuse and bounded capacity/stat behavior, not a specific eviction victim.

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

## `CrashLogScanIntake`

`CrashLogScanIntake` is the high-level seam for Crash Log Scan Intake. It turns selected game/version input, YAML Data, scan options, simplify-log removal rules, Crashgen metadata, and FormID readiness into a `ScanReadyAnalysis`.

Important constructors/helpers:

- `CrashLogScanIntake::from_yaml_paths(yaml_dir_root, yaml_dir_data, game, selected_game_version, options)`
- `CrashLogScanIntake::from_yaml_data(yaml, paths, game, selected_game_version, options)`
- `CrashLogScanIntake::with_scan_facts(CrashLogScanFacts)`
- `CrashLogScanIntake::prepare().await -> Result<ScanReadyAnalysis, ScanLogError>`
- `CrashLogScanOptions::new(show_formid_values, fcx_mode, simplify_logs)`
- `resolve_formid_database_paths(yaml_dir_data, game, configured_paths)`
- `load_simplify_remove_list(yaml_dir_data)`

Behavior worth knowing:

- Path-backed intake loads YAML Data through `classic-config-core::YamlDataCore::load_from_yaml_files()`.
- In-memory intake accepts an already-loaded `YamlDataCore` so tests and later adapters can use the same readiness seam without unnecessary file setup.
- `CrashLogScanFacts` carries caller-projected configured FormID database paths and the optional Unsolved Logs Destination. Intake never discovers, opens, previews, or persists User Settings.
- Supplying paths to in-memory intake lets it resolve the same YAML Data-owned `CLASSIC Main.yaml` `exclude_log_records` sidecar as path-backed intake. Missing or unreadable simplify-log data remains fail-soft.
- `ScanReadyAnalysis` stores path roots and the caller-provided Unsolved Logs Destination for scan-run destination resolution. `None` means canonical behavior; a non-empty relative destination is a setup error.
- FormID database path order is main game DB, hardcoded Fallout 4/Fallout 4 VR FOLON DB, then caller-provided configured paths. Relative configured paths resolve under `yaml_dir_data`, and normalized path de-duplication preserves first occurrence.
- The crate-private sidecar settings module owns only YAML Data sidecar names, compatibility database paths, normalization, and validation. It has no User Settings file or key-path knowledge.
- Intake chooses the short-scan cache profile, but `classic-database-core` still owns pool initialization, cache bounds, connection behavior, and lookup mechanics.

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

- Prefer `CrashLogScanIntake` when you need a complete scan-ready payload. `build_analysis_config_from_yaml()` remains the focused YAML-to-config conversion helper and compatibility seam.
- `build_analysis_config_from_yaml()` is the canonical bridge from [`classic-config-core`](../../business-logic/classic-config-core).
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
- `process_logs_batch_with_events(log_paths, options, on_event) -> Vec<IndexedAnalysisResult>`
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
- `process_logs_batch_with_events()` is the richer core batch primitive used by bindings that need stable input indices, optional input-order result restoration, cancellation checks before each log starts, and queued/started/phase/terminal events.
- `resolve_batch_concurrency()` returns `1` for empty batches, clamps explicit overrides to a minimum of `1`, and otherwise uses the crate's adaptive CPU-aware default.
- `write_reports_batch()` logs write failures and returns only successfully written paths.
- New adapter code that needs the full Crash Log Scan Run transaction should prefer `CrashLogScanRun` over manually sequencing `OrchestratorCore`, report writing, and Unsolved Logs movement.
- `check_crashgen_version_for_detected_game()` filters registry-backed crashgen floors by the detected or configured crashgen product before comparing versions.
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

## Crash Log Scan Run

### Final `scan_run::contract` interface

`scan_run::contract` is the final language-neutral Rust seam established for the coordinated cutover. It has one execution operation:

- `contract::execute(request, cancellation, observer).await -> Result<contract::RunResult, contract::InfrastructureError>`
- `request: contract::Request` is tagged `Standard(contract::StandardRequest)` or `Targeted(contract::TargetedRequest)`
- `cancellation: &contract::Cancellation` is an opaque, cloneable cooperative control separate from the request
- `observer: Option<&mut dyn contract::Observer>` is optional and non-controlling; an adapter requests stopping through the cancellation control

`contract::Configuration` carries YAML roots, typed `GameId`, selected version mode, caller-projected `CrashLogScanFacts`, non-FCX analysis options, and optional explicit concurrency. `contract::Options` deliberately has no FCX boolean.

The constructor matrix is exhaustive:

- `Request::standard(...)` and `Request::standard_with_fcx(..., setup_context)` each accept `LeaveInPlace`, `MoveToConfiguredOrDefault`, or `MoveToCustom(path)`
- `Request::targeted(...)` and `Request::targeted_with_fcx(..., setup_context)` accept a Targeted source and have no Unsolved Logs parameter
- every FCX constructor requires `CrashLogScanSetupContext`; there is no FCX state that omits it

Stable event variants are `DiscoveryCompleted`, `EffectiveConcurrencySelected`, `LogQueued`, `LogStarted`, `LogPhase`, and `LogFinished`. Log-scoped events carry a discovery index and path. `LogFinished` carries one of the stable dispositions: `Succeeded`, `Failed`, or `CancelledBeforeStart`. `LogResult.failures` independently preserves every applicable structured failure stage (`Analysis`, `ReportWrite`, and `UnsolvedLogsFinalization`) so a finalization failure cannot erase the preceding analysis or report failure.

`contract::RunResult` retains completed discovery, Rust-selected effective concurrency once scheduling is reached, setup data, lifecycle status, aggregate counts, and per-log results in discovery order. Cancellation before or during discovery returns `CancelledBeforeDiscovery` with no discovery result and emits no `DiscoveryCompleted` event. Once discovery commits, the emitted payload and retained result contain the same complete accepted paths, Targeted rejections, source, and searched locations. Cancellation requested by the discovery observer returns `Cancelled`, retains that payload, marks every accepted log `CancelledBeforeStart`, and stops before effective concurrency is selected. An explicit concurrency value of zero is a typed request-validation failure; low-volume runs report effective concurrency capped by the discovered work volume.

Run-wide failures use `contract::InfrastructureError { stage, message, path }`. Stable stages are `RequestValidation`, `Discovery`, `Intake`, `FormIdDatabaseAccess`, `Initialization`, and `InternalInvariant`. Expected states such as no logs, setup failure, and cancellation remain structured `RunResult` data rather than infrastructure errors.

The expand implementation temporarily delegates execution to the same internals as `CrashLogScanRunService` through a transitional lifecycle hook. Discovery is cooperatively cancellable without exposing partial accumulators: Standard collection checks between completed directory and per-file move/copy operations plus enumeration entries, while Targeted collection checks around metadata operations and recursive directory entries. Completed Standard filesystem mutations are not rolled back when cancellation is observed at the next seam. After discovery commits, effective concurrency and log events reach the final observer in lifecycle order unless the observer requests cancellation immediately from `DiscoveryCompleted`. The dedicated scheduling/cancellation and finalization tickets replace the remaining compatibility routing. The operation is async and creates no runtime; callers enter it through `classic-shared-core`'s shared Tokio runtime.

### Provisional expand-step interfaces

`CrashLogScanRunService` is the public high-level facade for a full Crash Log Scan Run. It accepts typed Standard or Targeted source facts, optionally validates FCX setup, prepares intake, and executes accepted Crash Logs. `CrashLogScanRun` remains the lower prepared-run module for callers that already have `ScanReadyAnalysis` and an accepted log list.

These interfaces remain temporarily available so existing C++, Node, Python, and TUI consumers can migrate through their dedicated cutover tickets. They are not alternate constructors or execution paths in the final `scan_run::contract` model and are removed/internalized by the coordinated contract step.

Important service types:

- `CrashLogScanRunService::execute(request, on_event).await -> Result<CrashLogScanRunResult, ScanLogError>`
- `CrashLogScanRunServiceRequest { yaml_dir_root, yaml_dir_data, game, game_version, options, source, setup_context, move_unsolved_logs, unsolved_logs_destination, max_concurrent, cancellation, preserve_order }`
- `CrashLogScanSource::Standard(StandardCrashLogScanSource { base_directory, custom_scan_directory, configured_documents_root })`
- `CrashLogScanSource::Targeted(TargetedCrashLogScanSource { inputs })`
- `CrashLogScanRunResult { status, discovery, setup, message, total, succeeded, failed, cancelled, logs }`

High-level behavior worth knowing:

- Standard discovery uses the existing `LogCollector::new_for_scan(...)` behavior: it creates/uses `Crash Logs/` and `Crash Logs/Pastebin/`, copies XSE Folder logs when resolvable, includes the optional custom scan directory non-recursively, and returns accepted logs in collector order.
- Targeted discovery canonicalizes and de-duplicates explicit file or directory inputs while preserving first accepted order. Inputs that do not resolve to accepted Crash Logs are returned in `discovery.rejected_inputs`; they are not per-log analysis failures.
- Cancellation before either discovery mode commits returns `status = CancelledBeforeDiscovery`, omits discovery data, and emits no discovery event; accumulated accepted paths and rejections are discarded.
- Cancellation after `DiscoveryCompleted` retains the exact complete discovery payload and returns accepted logs as cancellation-related non-start outcomes without selecting effective concurrency.
- If discovery accepts no logs, the service returns `status = NoCrashLogsFound` with discovery data and no per-log outcomes. This is result data, not an infrastructure error.
- If FCX setup is requested but setup facts are missing, action-required, or fatal, the service returns `status = SetupFailed` with `setup` data and no per-log outcomes. Infrastructure failures such as YAML loading or unexpected analysis setup still return `Err`.
- Progress events begin only after discovery has accepted logs, so progress totals match the accepted scan set.

`CrashLogScanRun` is the prepared-run layer for executing a full Crash Log Scan Run after intake. It accepts a `ScanReadyAnalysis`, selected Crash Logs, a Standard or Targeted intent, optional concurrency and cancellation settings, and a progress callback.

Important types:

- `CrashLogScanRun::new(scan_ready)`
- `CrashLogScanRun::run(request, on_event).await -> Result<CrashLogScanRunResult, ScanLogError>`
- `CrashLogScanRunRequest { logs, intent, max_concurrent, cancellation, preserve_order }`
- `CrashLogScanRunIntent::Standard(...)` and `CrashLogScanRunIntent::Targeted`
- `CrashLogScanRunIntent::from_adapter_flags(targeted_mode, move_unsolved_logs, unsolved_logs_destination: Option<&str>)`
- `CrashLogScanRunIntent::from_configured_flags(targeted_mode, move_unsolved_logs, unsolved_logs_destination: Option<PathBuf>)`
- `StandardUnsolvedLogsIntent::LeaveInPlace`, `MoveToConfiguredOrDefault`, and `MoveToCustom(path)`

Request normalization seam:

- `from_adapter_flags` and `from_configured_flags` are the infallible request-normalization constructors adapters build against. Callers pass user intent facts — Targeted mode, whether to move Unsolved Logs, and an optional destination — and the core derives the Standard/Targeted intent so every binding shares one rule set instead of re-deriving it.
- Derivation rules: Targeted mode always wins over movement; `move_unsolved_logs == false` maps to `LeaveInPlace` and ignores the destination; move with a destination maps to `MoveToCustom`; move without a destination maps to `MoveToConfiguredOrDefault`.
- `from_adapter_flags` takes the raw string destination used by the CXX, Node, and Python surfaces and owns the sentinel convention: it trims the destination and treats an empty or whitespace-only result as absent. `from_configured_flags` takes an already-parsed `Option<PathBuf>` (used by the TUI) so callers that already hold a path avoid a lossy path -> string -> path round trip. `from_adapter_flags` delegates to `from_configured_flags` after trimming.
- Absolute-path validation of a custom destination stays in `run` (see below); the constructors themselves are infallible.

Behavior worth knowing:

- High-level adapters should prefer `CrashLogScanRunService` so discovery, no-log results, setup results, intake, report writing, and Unsolved Logs policy stay in Rust.
- Prepared-run callers that already have accepted Crash Logs may still use `CrashLogScanRun`; in that layer callers own selection and `CrashLogScanRun` owns execution after selection.
- `CrashLogScanRunRequest.max_concurrent = Some(0)` is treated as the adaptive default at the scan-run seam, identical to `None`. `run` folds `Some(0) -> None` before building batch options; only positive values pin the concurrency. This fold lives at the scan-run seam only and does not change `resolve_batch_concurrency`, which keeps `Some(0) -> 1` (serial) for the analysis-batch callers.
- `Standard` runs may move failed Crash Logs and sibling Autoscan Reports to Unsolved Logs when their intent requests movement.
- `Targeted` runs never move Crash Logs or Autoscan Reports to Unsolved Logs.
- `MoveToConfiguredOrDefault` uses the typed destination supplied through `CrashLogScanFacts` when present, otherwise the canonical `CLASSIC Backup/Unsolved Logs` directory under path-backed intake roots.
- `MoveToCustom(path)` requires an absolute path and fails setup before analysis when the path is relative. It does not create the directory during setup.
- Missing path roots with `MoveToConfiguredOrDefault` and no configured destination are setup errors. Invalid or unwritable absolute destinations remain per-log movement failures.
- Autoscan Report paths are derived as sibling `{stem}-AUTOSCAN.md` paths and written by this module when analysis succeeds and report lines are present.
- Autoscan Report write failure is a per-log failure in `CrashLogScanRunLogOutcome`, not a run-level setup error. These outcomes set `report_write_failed = true` so adapters can separate report failures from analysis failures.
- `cancellation` is a cooperative shared atomic checked before queued Crash Logs start; binding adapters should pass their frontend cancellation token rather than polling locally only.
- Progress events reuse `ScanProgressPhase` and carry stable input indices so adapters can correlate completion-order results to their selected Crash Log list.
- Binding adapters expose the high-level service as `classic::scanner::scan_run_execute(request, callback, cancellation_token)` for C++, `scanRunExecute(...)` for Node, and `classic_scanlog.scan_run_execute(...)` for Python. Adapter scan flows should not duplicate discovery policy, FCX setup result shaping, Autoscan Report writing, or Unsolved Logs movement around those calls.

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

## `CrashgenRegistry` and `CrashgenEntry`

These types model per-crashgen settings behavior.

- `CrashgenEntry` fields: `display_section`, `ignore_keys`, `settings_rules`
- `CrashgenRegistry::new(entries, default)` normalizes keys for lookup
- `CrashgenRegistry::lookup(name)` is case-insensitive and whitespace-normalized

Unknown crashgen names fall back to the registry default entry. The YAML `checks` key may still be accepted by upstream loaders as deprecated inert compatibility metadata, but it is not part of `CrashgenEntry` and must not drive scan-time behavior.

## `SettingsValidator`

`SettingsValidator` validates parsed crashgen settings against YAML-backed Crashgen Expectations and universal Disabled Setting Notices.

Important methods:

- `SettingsValidator::new(crashgen_name, entry)`
- `scan_all_settings(crashgen_settings_snapshot, xse_modules, crashgen_version, config_layout)`
- `check_disabled_settings(crashgen_settings_snapshot)`

Contributor notes:

- `scan_all_settings()` and `check_disabled_settings()` accept `classic_config_core::CrashgenSettingsSnapshot`, not a flattened key/value map.
- Crashgen Expectations look up settings by `RuleTarget.section` and `RuleTarget.key`; unscoped settings do not satisfy sectioned rules.
- Disabled Setting Notices still apply `ignore_keys` by setting key while iterating the snapshot's final setting values.
- `CrashgenEntry.settings_rules` is the only per-crashgen expectation source; there is no fallback to hardcoded Achievements, memory-management, ArchiveLimit, LooksMenu, or Addictol scaffold checks.
- If `CrashgenEntry.settings_rules` is absent, no per-crashgen expectations run; `scan_all_settings()` still appends Disabled Setting Notices for non-ignored disabled settings.
- Rule-driven preflight outcomes can now carry Autoscan Report Placement from the crashgen rule model in [`classic-config-core`](classic-config-core.md#crashgen-rule-model); `error_information` outcomes are promoted into the report's `Error Information` section while the default `settings` placement still renders under settings-related issues.
- `check_disabled_settings()` is the focused utility for Disabled Setting Notices and uses `ignore_keys` as its skip set.
- In `classic-scanlog-core`, `config_layout` is currently a coarse valid/invalid fact for settings evaluation: `derive_scanlog_config_layout()` returns `Og` for parseable detected versions and `Unknown` otherwise.
- OG vs VR selection is handled earlier through `AnalysisConfig` construction and Version Registry data, not by `config_layout` in this crate.

## Autoscan Report Assembly

`AutoscanReportAssembler` owns the canonical per-log Autoscan Report order and turns scan facts plus typed `AutoscanReportContribution` values into final report lines.

Canonical section ownership:

- header and Error Information
- Crashgen Expectation outcomes placed in Error Information before that section's separator
- crash suspect section, always present, including the no-suspects footer
- FCX Mode notice from per-log facts
- settings-related guidance, including settings-placement Crashgen Expectation outcomes and Disabled Setting Notices
- Mod Guidance groups in fixed order: conflicts, frequent crashes, solutions, important mods
- Plugin Evidence, FormID Finding, and Named Record Finding sections
- footer

The assembler does not choose Autoscan Report paths, write files, move Unsolved Logs, or run analyzers. `process_log_with_progress()` collects contributions during `Analyze` and performs assembly during `Finalize`.

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

- `version`: `CrashgenVersion`, `CrashgenVersionStatus`, `crashgen_version_gen()`, `check_crashgen_version_status()`. Configured crash generator versions are treated as minimum supported floors; detected versions equal to or newer than the relevant floor are valid.
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

1. Prepare Crash Log Scan Intake with `CrashLogScanIntake::from_yaml_paths(...)` or `CrashLogScanIntake::from_yaml_data(...)` and attach caller-projected `CrashLogScanFacts` when User Settings affect the run.
2. Use `prepare().await` to produce `ScanReadyAnalysis`; intake reads YAML Data but does not open or persist User Settings.
3. For a full Crash Log Scan Run, construct `CrashLogScanRun::new(scan_ready)` and call `run(...)` with selected Crash Logs.
4. Inside the module, `OrchestratorCore` reads each file with [`classic-file-io-core`](../../business-logic/classic-file-io-core) and preprocesses lines with `reformat_crash_data_inline()`.
5. `LogParser::parse_all_sections_arc()` builds named sections.
6. The orchestrator extracts header metadata, resolves crashgen identity/version status, and builds report helpers.
7. Analysis passes run over the prepared data:
   - plugin extraction and plugin suspect matching
   - suspect/error scanning
   - crashgen settings validation
   - mod detection
   - FormID extraction and optional DB value lookup
   - named-record scanning
   - FCX message inclusion
8. `ReportComposer` combines fragments and produces `report_lines`.
9. `CrashLogScanRun` writes Autoscan Reports, accounts per-log outcomes, and applies Standard versus Targeted Unsolved Logs rules.

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
- `CrashLogScanIntake::prepare()` is also async for path-backed YAML loading.
- The crate depends on `tokio` and `futures`, but the source does not construct a Tokio runtime in production code.
- In CLASSIC, higher layers are expected to use the shared runtime model from [`classic-shared-core`](../../foundation/classic-shared-core) rather than introducing a second runtime.

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

- [`classic-config-core`](../../business-logic/classic-config-core) - provides `YamlDataCore`, crashgen registry source data used by `build_analysis_config_from_yaml()`, and the typed Crashgen Expectation model/evaluator at `classic_config_core::crashgen_rules::*` used by `SettingsValidator`
- [`classic-settings-core`](../../business-logic/classic-settings-core) - provides `YamlOperations` used by intake only for YAML Data-owned simplify-log removal rules
- [`classic-version-registry-core`](../../business-logic/classic-version-registry-core) - resolves game-version matches and valid crashgen versions
- [`classic-database-core`](../../business-logic/classic-database-core) - optional FormID description lookups through `DatabasePool`
- [`classic-file-io-core`](../../business-logic/classic-file-io-core) - async file reads and writes used by the orchestrator
- [`classic-shared-core`](../../foundation/classic-shared-core) - shared runtime policy used by higher layers in this repo
- [`classic-node`](../../node-bindings/classic-node) and [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge) - binding layers that should stay aligned with this crate's public behavior

In practice, `classic-scanlog-core` is the downstream analysis layer that turns config/YAML data into scan results and autoscan reports.

---

## Usage Example

This example follows the intended contributor flow for a full Crash Log Scan Run: prepare scan intake, construct the run module, and execute selected Crash Logs.

```rust
use classic_scanlog_core::{
    CrashLogScanFacts,
    CrashLogScanRun,
    CrashLogScanRunIntent,
    CrashLogScanRunRequest,
    CrashLogScanIntake,
    CrashLogScanOptions,
    StandardCrashLogScanRunIntent,
    StandardUnsolvedLogsIntent,
};
use std::path::PathBuf;

# async fn example() -> Result<(), Box<dyn std::error::Error>> {
let intake = CrashLogScanIntake::from_yaml_paths(
    PathBuf::from("C:/CLASSIC"),
    PathBuf::from("C:/CLASSIC/CLASSIC Data"),
    "Fallout4",
    "auto",
    CrashLogScanOptions::new(
        false,      // show_formid_values
        false,      // fcx_mode
        false,      // simplify_logs
    ),
)
.with_scan_facts(CrashLogScanFacts {
    formid_database_paths: vec![PathBuf::from("databases/custom.db")],
    unsolved_logs_destination: Some(PathBuf::from("C:/CLASSIC/Unsolved Logs")),
});

let scan_ready = intake.prepare().await?;
let run = CrashLogScanRun::new(scan_ready);
let result = run.run(
    CrashLogScanRunRequest {
        logs: vec![PathBuf::from("C:/CLASSIC/crash-2026-03-09.log")],
        intent: CrashLogScanRunIntent::Standard(StandardCrashLogScanRunIntent {
            unsolved_logs: StandardUnsolvedLogsIntent::LeaveInPlace,
        }),
        max_concurrent: None,
        cancellation: None,
        preserve_order: true,
    },
    |_| {},
).await?;

if let Some(log) = result.logs.first() {
    println!("Processed {} in {} ms", log.crash_log.display(), log.processing_time_ms);
}
# Ok(())
# }
```

If you need lower-level analysis-only behavior, `OrchestratorCore` remains public. New adapter code that wants Autoscan Report writing and Unsolved Logs behavior should prefer `CrashLogScanRun`.

---

## Contributor Notes And Known Limits

- `classic-scanlog-core` is downstream of [`classic-config-core`](../../docs/api/classic-config-core.md); update both docs if the YAML-to-analysis contract changes.
- Crash Log collection and XSE Folder discovery stay outside `CrashLogScanIntake`; Unsolved Logs movement belongs to `CrashLogScanRun` for full run execution.
- `parse_segments()` and `parse_segments_parallel()` are still public but explicitly deprecated. The Python binding `parse_segments_parallel` now returns `dict[str, list[str]]` instead of `list[list[str]]`.
- The source contains performance claims in comments and docs, but this page does not treat them as compatibility guarantees.
- `process_logs_batch()` does not preserve input ordering.
- Addictol compatibility guidance is expressed through YAML `settings_rules.preflight`; there is no hardcoded Addictol scaffold path.
- `derive_scanlog_config_layout()` is effectively a valid/invalid gate today: it returns `Og` for parseable detected versions and `Unknown` otherwise.
- The crashgen rule model in `classic-config-core` still defines `ConfigLayout::Vr`, but this crate no longer uses `ConfigLayout` as the OG/VR selector; that decision now lives in Version Registry-backed config building.
- Report output is designed for Python parity, so text shape matters to downstream consumers more than a stable structured schema does.

If you extend this crate, update this document when you change:

- re-exported types in `lib.rs`
- Crash Log Scan Intake readiness rules
- the named-section contract in `parser`
- `AnalysisConfig` construction rules or Version Registry precedence
- runtime/concurrency expectations
- report text or helper behavior that bindings depend on
