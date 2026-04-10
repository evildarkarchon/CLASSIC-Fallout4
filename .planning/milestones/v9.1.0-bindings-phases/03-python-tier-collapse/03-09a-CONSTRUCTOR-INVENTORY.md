# Plan 09a — Constructor Inventory (authoritative source for smoke test argument lists)

**Generated:** 2026-04-09 (Task 0 Step 2)
**Source:** Direct read of `ClassicLib-rs/python-bindings/classic-*-py/src/*.rs` for every `#[pyclass]` present in the live residual list.
**Purpose:** Source of truth for constructor arguments used by `_scaffold_plan09a_tests.py` and the hand-authored `test_promoted_residuals_smoke.py`.

## Legend

- **NO_CONSTRUCTOR** — class has `#[pymethods]` but no `#[new]` → factory/data class; construct via Rust API call and wrap
- **NO_PYMETHODS** — class is a bare `#[pyclass]` enum or struct with no method block → variants accessed as `ClassName.VARIANT`
- **args** — literal argument list extracted from the `#[new] fn new(...)` signature (whitespace-normalized)

---

## classic_scangame (43 classes)

From `ClassicLib-rs/python-bindings/classic-scangame-py/src/`:

- `AddressLibInfo` — NO_CONSTRUCTOR (file: xse.rs; getter-only data class)
- `BA2Issues` — NO_CONSTRUCTOR (file: ba2.rs; getter-only accumulator)
- `BA2Scanner` — `fn new() -> Self` (no args; file: ba2.rs)
- `CheckResult` — NO_CONSTRUCTOR (file: orchestrator.rs; enum-like data class)
- `CheckType` — NO_CONSTRUCTOR (file: integrity.rs; enum-like class)
- `ConfigDuplicateDetector` — `fn new() -> Self` (no args; file: config.rs)
- `ConfigIssue` — NO_CONSTRUCTOR (file: ini.rs)
- `CrashgenCheckOrchestrator` — `fn new() -> Self` (no args; file: crashgen_orchestrator.rs)
- `CrashgenChecker` — `fn new(plugins_path: PathBuf, crashgen_name: String, settings_rules: Option<&Bound<'_, PyAny>>)` (file: toml_check.rs)
- `CrashgenReport` — NO_CONSTRUCTOR (file: crashgen_orchestrator.rs)
- `DuplicateEntry` — NO_CONSTRUCTOR (file: config_cache.rs)
- `DuplicateGroup` — NO_CONSTRUCTOR (file: config.rs)
- `EnbChecker` — `fn new(game_path: PathBuf)` (file: enb.rs)
- `EnbConfigResult` — NO_PYMETHODS (enum; file: enb.rs)
- `EnbResult` — NO_PYMETHODS (enum; file: enb.rs)
- `EnbValidationResult` — NO_CONSTRUCTOR (file: enb.rs)
- `GameIntegrityChecker` — `fn new(config: &PyIntegrityConfig)` (file: integrity.rs)
- `GameScanConfig` — `fn new(game_path: PathBuf, xse_acronym: String, crashgen_name: String, game_name: String, docs_path: Option<PathBuf>, mods_path: Option<PathBuf>, xse_scriptfiles: Option<HashMap<String, Vec<String>>>, plugins_path: Option<PathBuf>, is_vr: bool, game_version: Option<&PyGameVersion>, wrye_warnings: Option<HashMap<String, String>>, log_catch_errors: Option<Vec<String>>, log_exclude_files: Option<Vec<String>>, log_exclude_errors: Option<Vec<String>>, crashgen_settings_rules: Option<&Bound<'_, PyAny>>, game_target: Option<&str>)` (file: orchestrator.rs)
- `GameScanOrchestrator` — `fn new(config: &PyGameScanConfig)` (file: orchestrator.rs)
- `GameScanResult` — NO_CONSTRUCTOR (file: orchestrator.rs)
- `GameVersion` — NO_PYMETHODS (enum OG/NG/AE; file: xse.rs; construct via `classic_scangame.GameVersion.OG` etc)
- `IniValidator` — `fn new(game_name: String)` (file: ini.rs)
- `IntegrityCheckResult` — NO_CONSTRUCTOR (file: integrity.rs)
- `IntegrityConfig` — `fn new(game_exe_path: PathBuf, valid_exe_hashes: Vec<String>, root_name: String)` (file: integrity.rs)
- `IssueSeverity` — NO_PYMETHODS (enum; file: ini.rs)
- `LogErrorEntry` — NO_CONSTRUCTOR (file: logs.rs)
- `LogProcessor` — `fn new(catch_errors: Vec<String>, ignore_files: Vec<String>, ignore_errors: Vec<String>)` (file: logs.rs)
- `ModIniScanResult` — NO_CONSTRUCTOR (file: config_cache.rs)
- `ModScanResult` — NO_CONSTRUCTOR (file: orchestrator.rs)
- `RustConfigFileCache` — `fn new(game_root: PathBuf, duplicate_whitelist: Option<Vec<String>>)` (file: config_cache.rs; pyclass name="RustConfigFileCache" struct=PyConfigFileCache)
- `RustModIniScanner` — `fn new() -> Self` (no args; file: config_cache.rs)
- `SetupCheckConfig` — `fn new(game_exe_path: PathBuf, valid_exe_hashes: Vec<String>, root_name: String, game_name: String, docs_path: Option<String>, xse_hashes: Option<Vec<(String, String)>>, ...)` (file: setup.rs; 7+ args)
- `SetupCheckResults` — NO_CONSTRUCTOR (file: setup.rs)
- `TomlConfigIssue` — NO_CONSTRUCTOR (file: toml_check.rs)
- `TomlIssueSeverity` — NO_PYMETHODS (enum; file: toml_check.rs)
- `UnpackedIssues` — NO_CONSTRUCTOR (file: unpacked.rs)
- `UnpackedScanner` — `fn new() -> Self` (no args; file: unpacked.rs)
- `ValidationResult` — NO_PYMETHODS (enum; file: xse.rs)
- `VsyncEntry` — NO_CONSTRUCTOR (file: config_cache.rs)
- `WryeBashParser` — `fn new(wrye_warnings: Option<HashMap<String, String>>)` (file: wrye.rs)
- `WryeIssue` — NO_CONSTRUCTOR (file: wrye.rs)
- `WryeSeverity` — NO_PYMETHODS (enum; file: wrye.rs)
- `XseChecker` — `fn new(plugins_path: PathBuf, game_version: PyGameVersion)` (file: xse.rs)

## classic_path (7 classes)

From `ClassicLib-rs/python-bindings/classic-path-py/src/lib.rs`:

- `BackupManager` — `fn new(backup_root: String)`
- `DocsPathFinder` — `fn new(relative_path: String)`
- `DocumentsChecker` — `fn new(game_name: String)`
- `GamePathFinder` — `fn new(game_exe: String, xse_loader: Option<String>, game_name: String, is_vr: bool)`
- `IniCheckResult` — NO_CONSTRUCTOR (data class)
- `PathValidator` — NO_CONSTRUCTOR (module-level namespace class)
- `XseVersion` — `fn new(version: String)`

## classic_constants (3 classes)

From `ClassicLib-rs/python-bindings/classic-constants-py/src/lib.rs`:

- `Fallout4Version` — NO_CONSTRUCTOR (enum with PyO3 getters; access variants via `Fallout4Version.OG`, `Fallout4Version.NG`, etc. and use `Fallout4Version.from_str("OG")` factory if present)
- `GameId` — NO_CONSTRUCTOR (enum; access via `GameId.FO4`, etc.)
- `YamlFile` — NO_CONSTRUCTOR (enum; access via `YamlFile.GAME`, `YamlFile.MAIN`, etc.)

All three are enum #[pyclass] with methods via #[pymethods] (getters + factory functions like `from_str` / `iter` / etc. that are accessed as class methods).

## classic_message (4 classes)

From `ClassicLib-rs/python-bindings/classic-message-py/src/lib.rs` and `logging.rs`:

- `Logger` — `fn new() -> Self` (no args; file: logging.rs; struct=PyLogger)
- `Message` — `fn new(content: String, msg_type: MessageType)` (file: lib.rs)
- `MessageTarget` — NO_PYMETHODS (enum; file: lib.rs; variants accessed as `MessageTarget.STDOUT`, `MessageTarget.LOGGER`, etc.)
- `MessageType` — NO_CONSTRUCTOR (enum #[pyclass] with getter methods; variants via `MessageType.INFO`, `MessageType.WARNING`, etc.)

## classic_database (1 class)

From `ClassicLib-rs/python-bindings/classic-database-py/src/pool.rs`:

- `DatabasePool` — NO_CONSTRUCTOR (created via factory functions like `DatabasePool.create_async(db_paths)` or `.create_sync(db_paths)`; test must use the factory)

## classic_resource (2 classes)

From `ClassicLib-rs/python-bindings/classic-resource-py/src/lib.rs`:

- `ResourceInfo` — `fn new(path: String)`
- `ResourceType` — NO_CONSTRUCTOR (enum with factory method `from_str(s)` or `from_extension(ext)` and getters)

## classic_xse (2 classes)

From `ClassicLib-rs/python-bindings/classic-xse-py/src/lib.rs`:

- `XseInfo` — `fn new(xse_type: PyXseType, path: String)`
- `XseType` — NO_CONSTRUCTOR (enum; variants via `XseType.F4SE`, `XseType.SKSE`, etc.)

## classic_settings (1 class)

From `ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs`:

- `SettingsCacheStats` — NO_CONSTRUCTOR (read-only data class returned from `cache_stats()` helper)

Note: settings owner is dominated by 12 module-level free functions (`load_settings_sync`, `load_batch_sync`, `cache_stats`, `clear_cache`, etc.). Constructor inventory is minimal; most smoke tests will be free-function tests.

## classic_registry (1 class)

From `ClassicLib-rs/python-bindings/classic-registry-py/src/lib.rs`:

- `Keys` — NO_CONSTRUCTOR (namespace class; attribute access for predefined keys like `Keys.GAME`, `Keys.GAME_PATH`)

Note: registry owner has 18 module-level free functions (`register`, `unregister`, `get`, `set_game`, `is_gui_mode`, etc.).

## classic_yaml (2 classes)

From `ClassicLib-rs/python-bindings/classic-yaml-py/src/lib.rs`:

- `YamlCacheStats` — NO_CONSTRUCTOR (read-only; returned from `YamlOperations.cache_stats()`)
- `YamlOperations` — `fn new() -> Self` (no args; pyclass name="YamlOperations" struct=PyYamlOperations)

## classic_web (1 class)

From `ClassicLib-rs/python-bindings/classic-web-py/src/lib.rs`:

- `ModSite` — NO_CONSTRUCTOR (enum; variants via `ModSite.NEXUS`, `ModSite.BETHESDA`, etc., with getters `.name()`, `.base_url()`, `.game_url()`)

## classic_version (0 classes, 11 module functions)

No residual classes for version — all 11 residuals are module-level free functions: `parse_version`, `format_version`, `compare_versions`, `try_parse_version`, `extract_all_versions`, `extract_pe_version`, `extract_version_from_filename`, `extract_version_from_log`, `is_known_f4se_version`, `is_known_fallout4_version`, `is_valid_pe_path`.

## classic_perf (2 classes)

From `ClassicLib-rs/python-bindings/classic-perf-py/src/lib.rs`:

- `MetricsSummary` — NO_CONSTRUCTOR (read-only; returned from `get_summary()`)
- `Timer` — `fn new(name: String)` (context-manager pattern)

Plus 5 module functions: `start_timer`, `record_timing`, `get_summary`, `clear_metrics`, `reset_metrics`.

## classic_update (3 classes)

From `ClassicLib-rs/python-bindings/classic-update-py/src/github.rs`:

- `GithubAsset` — NO_CONSTRUCTOR (read-only data class returned from release DTO)
- `GithubClient` — `fn new(owner: String, repo: String, token: Option<String>)`
- `GithubRelease` — NO_CONSTRUCTOR (read-only data class returned from client calls)

## classic_scanlog (method residuals only, parent classes already in tier1)

These are the 4 Task-1 "scanlog method residual" entries. All parent classes are ALREADY enrolled in tier1 via Waves 1-3b; only the methods need new rows.

From `ClassicLib-rs/python-bindings/classic-scanlog-py/src/`:

- `CrashgenVersion.to_tuple` — parent `#[pyclass(name="CrashgenVersion")] struct PyCrashgenVersion` (file: version.rs:7-9). Constructor: `fn new(version_str: &str)` (file: version.rs:22). Method signature: `fn to_tuple(&self) -> (u32, u32, u32)` (file: version.rs:49). Test: `CrashgenVersion("1.10.163.0").to_tuple()` must return a 3-tuple.
- `LogParser.find_errors` — parent `#[pyclass(name="LogParser")] struct PyLogParser` (file: parser.rs:37-38). Constructor: `pub fn new(custom_boundaries: Option<Vec<(String, String)>>)` (file: parser.rs:79). Method: `pub fn find_errors(&self, lines: Vec<String>) -> Vec<(usize, String)>` (file: parser.rs:278).
- `PatternMatcher.find_all` — parent `#[pyclass(name="PatternMatcher")] struct PyPatternMatcher` (file: patterns.rs:7-8). Constructor: `pub fn new(patterns: Vec<String>)` (file: patterns.rs:17). Method: `pub fn find_all(&self, text: String) -> Vec<(usize, String)>` (file: patterns.rs:23).
- `PatternMatcher.has_match` — same parent. Method: `pub fn has_match(&self, text: String) -> bool` (file: patterns.rs:28).

## Notes for _scaffold_plan09a_tests.py

1. **NO_CONSTRUCTOR classes** (data/result classes) cannot be directly constructed from test code. Smoke tests for these must either:
   - Call a factory/producer method that returns the instance (e.g., `SetupCheckResults` produced via `SetupCheckConfig(...).run()`)
   - Use a module-level helper that returns a populated instance
   - Verify only `isinstance()` + class-level attribute access
2. **NO_PYMETHODS enums** should be tested by accessing at least one variant and calling any attached getter method (e.g., `ModSite.NEXUS.name()`).
3. **Large-ctor classes** (GameScanConfig 16 args, SetupCheckConfig 7+ args) should use minimal valid args with `tempfile.mkdtemp()` paths and empty Vecs — D-07 only requires "construct + call one method", not end-to-end functionality.
4. **DatabasePool** requires an actual SQLite file to construct via `create_sync()`. Smoke test should create an empty temp DB or use an in-memory DB path.
