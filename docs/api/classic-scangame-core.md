# `classic-scangame-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-scangame-core/`](../../business-logic/classic-scangame-core).

Crate metadata:

- Crate: `classic-scangame-core`
- Description: `Pure Rust business logic for game scanning and validation (NO PyO3)`

This crate is the Rust-side game-installation and mod-file scanning layer for CLASSIC. It covers setup-time validation, Address Library and crashgen config checks, loose-file and BA2 archive scanning, game log scanning, Wrye Bash report parsing, ENB detection, and mod INI/config inspection.

It is a pure Rust business-logic crate. It does not own a UI surface, binding layer, or long-lived Tokio runtime.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- validate a game install before or alongside crash-log analysis
- scan loose mod files and BA2 archives for format and compatibility issues
- inspect crashgen TOML settings and XSE Address Library installation
- scan mod/game INI and CONF files for known bad settings, duplicates, and VSync state
- parse Wrye Bash `ModChecker.html` output into structured issues
- assemble contributor-facing text reports from multiple checks

Do not use this crate for:

- loading CLASSIC YAML datasets directly
- crash-log parsing or autoscan report generation from crash logs
- owning or creating an application runtime
- binding-specific wrapper APIs

Those concerns live in related crates such as [`classic-config-core`](../../business-logic/classic-config-core), [`classic-scanlog-core`](../../business-logic/classic-scanlog-core), [`classic-file-io-core`](../../business-logic/classic-file-io-core), and [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge).

---

## Module Map

This crate exposes public modules directly and also re-exports most contributor-facing types from `src/lib.rs`.

### Orchestration modules

- `orchestrator` - top-level async game/mod scan runner
- `game_setup_intake` - setup-time path, version, registry, executable, documents, and XSE intake diagnostics
- `crashgen_orchestrator` - crashgen config-path resolution, plugin detection, and report packaging
- `game_report` - text report builders for loose-file and BA2 scan results

### Validation and scan modules

- `xse` - Address Library validation against detected game mode/version
- `toml` - crashgen TOML validation, with optional rule-driven path using the crashgen rule model in [`classic-config-core`](classic-config-core.md#crashgen-rule-model)
- `integrity` - executable hash and installation-location checks
- `enb` - ENB binary/config detection
- `logs` - non-crash log scanning with include/exclude patterns
- `wrye` - Wrye Bash `ModChecker.html` parsing and formatting
- `unpacked` - loose mod-file scanning
- `ba2` - BA2 archive scanning
- `mod_ini` - higher-level mod INI orchestration built on config caching
- `config_cache` - encoding-aware INI/CONF cache plus duplicate detection
- `config` - lower-level duplicate config-file detector
- `ini` - standalone INI validator APIs used less often than `mod_ini`

### Root re-exports

`lib.rs` re-exports the main integration types, including:

- `GameScanOrchestrator`, `GameScanConfig`, `GameScanResult`, `ModScanResult`
- `detect_config_issues(game_path, game_name)`
- `CrashgenCheckOrchestrator`, `CrashgenReport`
- `GameSetupIntake`, `GameSetupIntakeResult`, `GameSetupCheck`, `game_setup_needs_path_detection()`
- `GameIntegrityChecker`, `IntegrityConfig`
- `XseChecker`, `GameVersion`, `ValidationResult`
- `CrashgenChecker`, `TomlConfigIssue`
- `ModIniScanner`, `ModIniScanResult`
- `UnpackedScanner`, `UnpackedIssues`
- `BA2Scanner`, `BA2Issues`
- `WryeBashParser`, `WryeIssue`
- `ConfigFileCache`, `CachedConfigFile`

---

## Public API Surface

## `GameScanConfig`

`GameScanConfig` is the main caller-provided input for full game scanning.

Important fields include:

- core paths: `game_path`, `docs_path`, `mods_path`, `plugins_path`
- version/mode data: `is_vr`, `game_version`, `game_target`, `game_name`
- XSE/crashgen data: `xse_acronym`, `xse_scriptfiles`, `crashgen_name`, `crashgen_settings_rules`
- Wrye/log inputs: `wrye_warnings`, `log_catch_errors`, `log_exclude_files`, `log_exclude_errors`

Contributor note:

- the orchestrator does not load YAML itself; callers must already resolve paths, game mode, XSE hash expectations, and optional crashgen rules

## `GameScanOrchestrator`

`GameScanOrchestrator` is the highest-level integration point.

Important methods:

- `GameScanOrchestrator::new(config)`
- `run_game_checks() -> Result<GameScanResult, OrchestratorError>`
- `run_mod_scans() -> Result<ModScanResult, OrchestratorError>`
- `run_full_scan() -> Result<(GameScanResult, ModScanResult), OrchestratorError>`

Behavior worth knowing from the source:

- `run_game_checks()` starts independent tasks for XSE, crashgen TOML, ENB, docs logs, game logs, Wrye Bash, and mod INI scanning
- per-task failures are collected into `GameScanResult.errors`; one failed sub-check does not abort the whole `run_game_checks()` call
- the read-only config-issue portion of `run_game_checks()` now shares the public `detect_config_issues(game_path, game_name)` helper
- `run_mod_scans()` returns a soft failure payload when `mods_path` is missing or nonexistent instead of throwing an orchestrator error
- loose-file DDS dimension validation is delegated to [`classic-file-io-core`](../../business-logic/classic-file-io-core) `DDSAnalyzer`
- BA2 archive findings are converted into the same category map used by `ScanReportBuilder`

## `detect_config_issues()`

This standalone helper exposes the same read-only FCX/config-issue scan used by `GameScanOrchestrator`.

- `detect_config_issues(game_path, game_name) -> Vec<ConfigIssue>`
- it builds a `ConfigFileCache` with no duplicate whitelist overrides and delegates to `ModIniScanner::scan_with_cache()`
- invalid paths or cache/scan failures collapse to an empty `Vec` instead of an orchestrator error

## `GameScanResult`, `ModScanResult`, and `CheckResult`

- `GameScanResult` contains `report`, `config_issues`, `check_results`, and non-fatal `errors`
- `ModScanResult` contains `report`, unpacked/archive issue counts, and non-fatal `errors`
- `CheckResult` is the per-subtask payload with `name` and formatted `output`

`report` fields are plain text assembled from sub-check output, not a stable structured schema.

## `CrashgenCheckOrchestrator` and `CrashgenReport`

Use `CrashgenCheckOrchestrator` when the caller wants crashgen checking plus path/plugin discovery.

Important methods:

- `check(plugins_path, crashgen_name)`
- `check_with_rules(plugins_path, crashgen_name, settings_rules)`
- `detect_plugins(plugins_path)`
- `resolve_config_path(plugins_path)`

`CrashgenReport` contains:

- `message` - formatted output text
- `issues: Vec<TomlConfigIssue>` - structured findings
- `crashgen_name`
- `config_path: Option<PathBuf>`
- `installed_plugins: Vec<String>`

Behavior worth knowing:

- config resolution prefers `Buffout4/config.toml` over `Buffout4.toml` when both exist
- `detect_plugins()` lowercases filenames and returns every directory entry name it can stringify, not only `.dll` files

## `CrashgenChecker` and `TomlConfigIssue`

`CrashgenChecker` is the lower-level TOML validator used by the orchestrator.

Important methods:

- `CrashgenChecker::new(plugins_path, crashgen_name)`
- `new_with_rules(plugins_path, crashgen_name, settings_rules)`
- `config_file()`
- `installed_plugins()`
- `check() -> Result<(String, Vec<TomlConfigIssue>), TomlError>`

`TomlConfigIssue` fields:

- `file_path`, `section`, `setting`
- `current_value`, `recommended_value`
- `description`, `severity`

Source-visible rules and limits:

- if `settings_rules` is present, the crate uses `evaluate_rules()` from the crashgen rule model in [`classic-config-core`](classic-config-core.md#crashgen-rule-model) instead of the legacy hardcoded checks
- without YAML-defined rules, the legacy path checks Achievements, X-Cell/Addictol-related memory settings, Archive Limit, `MaxStdIO`, and LooksMenu/F4EE compatibility
- Addictol has a legacy short-circuit path only when `settings_rules` is absent; rule-based callers are expected to model that as preflight logic upstream
- TOML settings are flattened by key name only before rule evaluation, so section names are descriptive output metadata rather than part of the lookup key
- both `Buffout4/config.toml` and `Buffout4.toml` present produces warning text, but validation still prefers the OG-style path

## `XseChecker`, `GameVersion`, `AddressLibInfo`, and `ValidationResult`

This module validates Address Library installation.

Important types and methods:

- `GameVersion` variants: `Null`, `Original`, `NextGen`, `AnniversaryEdition`, `Vr`
- `GameVersion::is_null()` and `description()`
- `AddressLibInfo::{vr, original, next_gen, anniversary_edition}()`
- `XseChecker::new(plugins_path, game_version)`
- `check() -> ValidationResult`
- `format_message(result)`
- `validate()`

`ValidationResult` variants:

- `CorrectVersion`
- `WrongVersion`
- `NotFound`
- `VersionNotDetected`
- `PluginsPathNotFound`

Behavior worth knowing:

- Address Library metadata is pulled from [`classic-version-registry-core`](../../business-logic/classic-version-registry-core) when available, with hardcoded Fallout 4 fallbacks otherwise
- non-VR mode treats OG, NG, and AE Address Library files as acceptable; VR mode expects only the VR file
- `PluginsPathNotFound` is public but not produced by `check()`; invalid paths fail earlier in `XseChecker::new()` with `XseError::InvalidPath`

## `IntegrityConfig`, `GameIntegrityChecker`, `IntegrityCheckResult`, and `CheckType`

This module handles setup-time executable and install-location checks.

Important methods:

- `IntegrityConfig::new(game_exe_path, valid_exe_hashes, root_name)`
- `with_steam_ini(path)` and `with_root_warn(message)`
- `GameIntegrityChecker::new(config)`
- `check_executable_version()`
- `check_installation_location()`
- `run_all_checks()`
- `run_full_check()`
- `config()`

Behavior worth knowing:

- executable validation hashes the file with SHA256 and compares against `valid_exe_hashes`
- presence of `steam_ini_path` counts as an outdated-install hint even when the executable hash matches
- installation-location validation is a string-contains check for `Program Files`, not a canonicalized Windows path policy
- missing executables usually become invalid `IntegrityCheckResult` values instead of hard errors, except direct hashing failures in internal helpers

## `GameSetupIntake`, `GameSetupIntakeResult`, and setup helpers

This module owns read-only setup intake for supported game installs.

Important items:

- `GameSetupIntake::new(game_id, selected_game_version)`
- `GameSetupIntake::with_game_root(path)`
- `GameSetupIntake::with_docs_root(path)`
- `GameSetupIntake::with_xse_log_path(path)`
- `GameSetupIntake::run() -> GameSetupIntakeResult`
- `normalize_game_setup_version_selection(value)`
- `game_setup_needs_path_detection(game_path, docs_path)`

`GameSetupIntakeResult` offers:

- `has_errors()`
- `total_checks()`
- `failed_checks()`
- `rendered_report`
- `checks: Vec<GameSetupCheck>`
- `actions: Vec<GameSetupRequiredAction>`
- `path_updates: Vec<GameSetupPathUpdate>`

Behavior worth knowing:

- Game Setup Intake is read-only; detected paths are returned as proposed updates instead of being persisted.
- `auto` mode reads executable PE version metadata and attempts a Version Registry match.
- failed setup diagnostics are typed checks; the top-level status is `ActionRequired` only when user input is missing.
- the module covers setup-only diagnostics, not ENB, crashgen TOML, Wrye, BA2, loose-file, or mod INI scans.

## Loose-file and archive scanning APIs

### `UnpackedScanner` and `UnpackedIssues`

Important methods:

- `UnpackedScanner::new()`
- `scan_directory(mod_path, xse_scriptfiles) -> Result<UnpackedIssues, UnpackedError>`

`UnpackedIssues` fields:

- `animdata`
- `tex_frmt`
- `snd_frmt`
- `xse_file`
- `previs`
- `dds_files`

Contributor notes:

- scanning is recursive and parallelized with Rayon over `WalkDir` entries
- `.tga` and `.png` are flagged as texture-format issues unless the path contains `BodySlide`
- `.mp3` and `.m4a` are flagged as sound-format issues
- `.dds` files are collected for later DDS validation instead of being validated inline
- XSE script detection requires both a `scripts/` path segment and an exact filename match against caller-provided `xse_scriptfiles`

### `BA2Scanner` and `BA2Issues`

Important methods:

- `BA2Scanner::new()` and `with_xse_patterns(...)`
- `scan_archive(path) -> Result<BA2Issues, BA2Error>`
- `scan_archives_batch(paths) -> Vec<Result<BA2Issues, BA2Error>>`
- `find_ba2_files(dir) -> Vec<PathBuf>`

`BA2Issues` fields:

- `tex_dims`
- `tex_frmt`
- `snd_frmt`
- `xse_file`

Platform and behavior notes:

- on non-Windows builds, `scan_archive()` returns `BA2Error::UnsupportedPlatform`
- `find_ba2_files()` recurses and intentionally skips `prp - main.ba2`
- DX10 archive entries are checked for non-DDS texture names and odd-numbered dimensions
- general archives flag `.mp3` and `.m4a` and look for XSE-like script paths

## Config and INI inspection APIs

### `ConfigFileCache` and `CachedConfigFile`

`ConfigFileCache` is the main cache-oriented config reader used by `ModIniScanner` and the public `detect_config_issues()` helper that powers orchestrator FCX-style issue detection.

Important methods:

- `ConfigFileCache::new(game_root, duplicate_whitelist)`
- `contains(file_name_lower)`
- `get_path(file_name_lower)`
- `iter()`
- `has_setting(...)`
- `get_str(...)`, `get_bool(...)`, `get_int(...)`, `get_float(...)`
- `detect_issue(...)`
- `config_files()`
- `read_toml_value(toml_path, section, key)`

Behavior worth knowing:

- files are scanned eagerly but parsed lazily on first access
- INI parsing disables inline comment stripping so values like `; F10` survive intact
- duplicate detection uses hash equality or size-plus-mtime equality; unlike `config.rs`, the cache path does not do text-similarity or structural INI comparison
- encoding is auto-detected with `chardetng` and `encoding_rs`

### `ModIniScanner`, `ModIniScanResult`, `VsyncEntry`, and `DuplicateEntry`

This is the contributor-facing higher-level INI scan entry point.

Important methods:

- `ModIniScanner::scan(game_root, game_name)`
- `scan_with_cache(cache, game_name)`

`ModIniScanResult` contains:

- `message`
- `issues: Vec<ConfigIssue>`
- `vsync_files: Vec<VsyncEntry>`
- `duplicates: Vec<DuplicateEntry>`

Behavior worth knowing:

- it checks `sStartingConsoleCommand`, multiple VSync settings, a small set of known per-mod INI problems, and duplicate config files
- duplicate reporting comes from `ConfigFileCache.duplicate_files`
- the built-in duplicate whitelist used by `scan()` is `F4EE`

### `ConfigDuplicateDetector`

This is the lower-level duplicate-finding API in `config.rs`.

Important methods:

- `ConfigDuplicateDetector::new()`
- `with_whitelist(...)`
- `scan_directory(root_path) -> Result<HashMap<String, Vec<PathBuf>>, ConfigError>`
- `get_duplicates()`

Source-observed limitation:

- `scan_directory()` returns a duplicate map, but the separate `duplicate_groups` field returned by `get_duplicates()` does not appear to be populated by the current implementation

### `IniValidator`

`IniValidator` is the older standalone INI validator.

Important methods:

- `IniValidator::new(game_name)`
- `load_ini(file_path)`
- `detect_all_issues(config_files)`
- `validate_inis(game_root)`
- `scan_config_files(game_root)`

Contributor note:

- newer crate paths prefer `ConfigFileCache` plus `ModIniScanner` because they include encoding detection, cache reuse, and duplicate handling

## `LogProcessor`

Important methods:

- `LogProcessor::new(catch_errors, exclude_files, exclude_errors)`
- `process_logs(folder_path) -> Result<String, LogError>`
- `error_patterns()`

Behavior worth knowing:

- it scans only top-level `.log` files in the target directory
- files whose paths contain `crash-` are always excluded
- content matching is case-insensitive via Aho-Corasick
- output keeps only the last 50 matched error lines per file while preserving the total count

## `EnbChecker` and ENB result types

Important types and methods:

- `EnbResult`: `Present`, `Partial`, `NotInstalled`
- `EnbConfigResult`: `Valid`, `NotFound`, `Unreadable`
- `EnbValidationResult::is_present()` and `is_fully_configured()`
- `EnbChecker::new(game_path)`
- `check_binaries()`, `check_config()`, `validate()`, `format_message(...)`

Behavior worth knowing:

- ENB presence means `d3d11.dll` and/or `d3dcompiler_46e.dll`
- `check_config()` uses metadata access, not full file parsing

## `WryeBashParser`, `WryeIssue`, and `WryeSeverity`

Important methods:

- `WryeBashParser::new(wrye_warnings)`
- `parse(html_content) -> Vec<WryeIssue>`
- `format_report(issues)`

Behavior worth knowing:

- parsing is based on `<h3>` sections followed by sibling `<p>` entries
- `Active Plugins:` is always skipped
- `ESL Capable` is treated specially in formatted output and does not list each plugin back out
- warning lookup is substring-based against the caller-supplied `wrye_warnings` map

---

## Scan And Validation Flow

The main contributor-facing full-scan flow is:

1. Resolve game paths, version mode, XSE metadata, and optional crashgen settings rules outside this crate.
2. Build `GameScanConfig`.
3. Construct `GameScanOrchestrator::new(config)`.
4. Call one of:
   - `run_game_checks()` for install/config/log-oriented checks
   - `run_mod_scans()` for loose-file + BA2 validation
   - `run_full_scan()` for both in parallel
5. `run_game_checks()` concurrently performs:
   - XSE Address Library validation
   - crashgen TOML/config validation
   - ENB detection
   - optional docs-folder log scanning
   - game-folder log scanning
   - Wrye Bash HTML parsing when `ModChecker.html` exists
   - mod INI scanning
6. `run_mod_scans()` concurrently performs:
   - loose-file scan via `UnpackedScanner`
   - BA2 archive scan via `BA2Scanner`
7. Loose `.dds` files from the unpacked scan are validated afterward with [`classic-file-io-core`](../../business-logic/classic-file-io-core) `DDSAnalyzer`.
8. `ScanReportBuilder` formats unpacked/archive issue maps into the final mod-scan report text.

Crashgen TOML flow in more detail:

1. `CrashgenCheckOrchestrator` or `CrashgenChecker` locates `Buffout4/config.toml` or `Buffout4.toml`.
2. The checker scans the plugins directory and lowercases discovered names.
3. If no config file exists, it returns notice text and no structured issues.
4. If YAML-backed `CrashgenSettingsRules` are supplied, `evaluate_rules()` drives issue detection.
5. Otherwise, the crate falls back to legacy hardcoded plugin/setting checks.
6. Results are returned as formatted text plus `Vec<TomlConfigIssue>`.

Game Setup Intake flow:

1. Build `GameSetupIntake` with a `GameId`, selected version, and any saved paths.
2. Call `run()`.
3. The crate resolves paths, registry metadata, executable facts, documents diagnostics, and XSE setup diagnostics.
4. Callers use `rendered_report` for text display and `checks` for structured UI/status handling.

---

## Error Handling Model

This crate does not have one dominant error type.

## Module-specific error enums

Most functional areas define their own `Result<T, ErrorEnum>` model:

- `OrchestratorError`
- `CrashgenOrchestratorError`
- `TomlError`
- `XseError`
- `IntegrityError`
- `SetupError`
- `LogError`
- `ConfigCacheError`
- `ConfigError`
- `IniError`
- `EnbError`
- `BA2Error`
- `UnpackedError`
- `WryeError`

## Root-level `ScanGameError`

`error.rs` exposes `ScanGameError` and `error::Result<T>`, but most public modules currently use their own specialized error enums instead of converting into this shared type.

## Fail-soft behavior

Several top-level flows intentionally keep going after sub-failures:

- `GameScanOrchestrator::run_game_checks()` stores subtask failures in `GameScanResult.errors`
- `GameScanOrchestrator::run_mod_scans()` stores scan failures in `ModScanResult.errors`
- `run_full_scan()` only fails hard if one of its spawned top-level tasks returns an orchestrator error or panics
- `CrashgenChecker::check()` returns notice text instead of an error when the config file is absent
- `BA2Scanner::scan_archives_batch()` returns per-archive `Result`s

That split matters for contributors: this crate mixes strict module-level errors with report-oriented workflows that degrade gracefully.

---

## Async, Runtime, And Concurrency Notes

This crate exposes async orchestration APIs but does not create its own runtime.

- async entry points are mainly in `GameScanOrchestrator`: `run_game_checks()`, `run_mod_scans()`, and `run_full_scan()`
- those async methods use `tokio::task::JoinSet` and `spawn_blocking()` to run CPU-bound or blocking work concurrently
- scanning helpers such as `UnpackedScanner`, `BA2Scanner`, and `LogProcessor` are otherwise synchronous and often use Rayon internally
- current source does not visibly call `classic-shared-core::get_runtime()` or construct a Tokio runtime directly

Contributor rule: keep runtime ownership outside this crate and preserve compatibility with the repo-wide shared Tokio runtime assumption.

Concurrency/performance patterns visible in source:

- `JoinSet` is used for orchestrator fan-out/fan-in
- `spawn_blocking()` wraps sync scanners and parsers
- Rayon powers loose-file walking, BA2 batch scanning, and log-file processing
- `ConfigFileCache` and `CrashgenChecker` are mutable, cache-owning helpers and are not exposed as shared concurrent types

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `classic-file-io-core` - DDS validation helpers used during loose-file scans
- `classic-config-core` - optional rule-evaluation path for crashgen TOML checks via the absorbed crashgen rule model (`classic_config_core::crashgen_rules::*`, formerly a separate crate)
- `classic-path-core` - path resolution and documents-folder checks used by Game Setup Intake
- `classic-version-registry-core` - setup expectation metadata, Address Library metadata, and Fallout 4 version descriptions
- `tokio` - async orchestration only
- `rayon` - parallel synchronous scanning work
- `walkdir` - recursive file discovery
- `configparser`, `toml`, `encoding_rs`, `chardetng` - config parsing and encoding detection
- `scraper` - Wrye Bash HTML parsing
- `ba2` - native Fallout 4 BA2 archive access on Windows

Related CLASSIC crates:

- [`classic-config-core`](../../business-logic/classic-config-core) - upstream source for paths, game-version decisions, optional `CrashgenSettingsRules`, AND the shared rule model reused for TOML validation (see the "Crashgen rule model" section in [classic-config-core.md](classic-config-core.md#crashgen-rule-model))
- [`classic-scanlog-core`](../../business-logic/classic-scanlog-core) - downstream crash-log analysis layer that complements setup/game scanning rather than replacing it
- [`classic-file-io-core`](../../business-logic/classic-file-io-core) - shared DDS and file helpers used here
- [`classic-version-registry-core`](../../business-logic/classic-version-registry-core) - registry-backed Fallout 4 version and Address Library metadata
- [`classic-shared-core`](../../foundation/classic-shared-core) - shared runtime policy; currently a dependency without visible direct runtime calls in this crate's source

---

## Usage Example

This example follows the real public API and shows the main contributor path: assemble `GameScanConfig`, then run the orchestrator.

```rust
use classic_file_io_core::dds::GameTarget;
use classic_scangame_core::{GameScanConfig, GameScanOrchestrator, GameVersion};
use std::collections::HashMap;
use std::path::PathBuf;

# async fn example() -> Result<(), classic_scangame_core::OrchestratorError> {
let config = GameScanConfig {
    game_path: PathBuf::from("C:/Games/Fallout4"),
    docs_path: Some(PathBuf::from("C:/Users/Alice/Documents/My Games/Fallout4")),
    mods_path: Some(PathBuf::from("C:/ModManager/Fallout4/mods")),
    xse_acronym: "F4SE".to_string(),
    xse_scriptfiles: HashMap::new(),
    plugins_path: Some(PathBuf::from("C:/Games/Fallout4/Data/F4SE/Plugins")),
    is_vr: false,
    game_version: GameVersion::Original,
    crashgen_name: "Buffout4".to_string(),
    crashgen_settings_rules: None,
    wrye_warnings: HashMap::new(),
    log_catch_errors: vec!["error".to_string(), "fatal".to_string()],
    log_exclude_files: vec!["crash-".to_string()],
    log_exclude_errors: vec![],
    game_target: GameTarget::Fallout4,
    game_name: "Fallout4".to_string(),
};

let orchestrator = GameScanOrchestrator::new(config);
let (game_result, mod_result) = orchestrator.run_full_scan().await?;

println!("Game report bytes: {}", game_result.report.len());
println!("Game sub-check errors: {}", game_result.errors.len());
println!("Loose-file issues: {}", mod_result.unpacked_issue_count);
println!("Archive issues: {}", mod_result.archived_issue_count);
# Ok(())
# }
```

If the caller already has YAML-backed crashgen settings rules from [`classic-config-core`](../../business-logic/classic-config-core), pass them through `GameScanConfig.crashgen_settings_rules` or `CrashgenCheckOrchestrator::check_with_rules()`.

---

## Contributor Notes And Known Limits

- `lib.rs` re-exports many types directly; changing those re-exports changes the contributor-facing API surface.
- The crate has overlapping config/INI layers: `ini` and `config` are lower-level, while `config_cache` and `mod_ini` are the more integrated paths used by the orchestrator.
- `ConfigFileCache` duplicate detection is simpler than `ConfigDuplicateDetector`; the two APIs do not currently implement identical duplicate semantics.
- `ConfigDuplicateDetector::duplicate_groups` appears unused by the current implementation.
- `Game Setup Intake` is setup-only; broader game-file and crash-log-adjacent checks remain in the orchestrator and scanner modules.
- `LogProcessor` scans only the top level of the target directory; it does not recurse.
- `CrashgenChecker` flattens TOML settings by key name only for rule evaluation, so same-named keys in multiple sections would collide.
- `detect_plugins()` and `CrashgenChecker` plugin discovery include any stringifiable entry names in the plugins directory, not just DLLs.
- BA2 content scanning is Windows-only; non-Windows callers keep the same API but get `UnsupportedPlatform`.
- Current Fallout 4-oriented assumptions are visible throughout version, Address Library, and Buffout4-specific paths.

If you extend this crate, update this document when you change:

- root re-exports in `src/lib.rs`
- `GameScanConfig` inputs or orchestrator task composition
- crashgen TOML rule precedence or config-path resolution
- duplicate-detection semantics in `config` or `config_cache`
- runtime/concurrency behavior
- Windows/BA2 platform behavior or related report text
