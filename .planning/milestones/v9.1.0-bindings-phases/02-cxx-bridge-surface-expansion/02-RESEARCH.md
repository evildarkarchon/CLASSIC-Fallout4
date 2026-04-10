# Phase 2: CXX Bridge Surface Expansion - Research

**Researched:** 2026-04-07
**Domain:** CXX FFI bridge expansion — `classic-cpp-bridge` widening + C++ consumer migration
**Confidence:** HIGH — all findings grounded in direct source-file reads of the actual bridge, core crates, and C++ frontends. No speculative claims.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** XSE helpers move to a NEW `src/xse.rs` file under `#[cxx::bridge(namespace = "classic::xse")]`. Existing string-based XSE helpers in `game.rs` (`detect_xse_version_string`, `is_xse_installed_check`, `xse_type_from_str`) move into the new file. Pitfall 5 clean `-Test` build cycle is required immediately after the file lands.

**D-02:** Version-registry helpers move to a NEW `src/version_registry.rs` file under `#[cxx::bridge(namespace = "classic::version_registry")]`. Existing `version_registry_*` and `parse_game_version` helpers in `game.rs` move there. The current `src/registry.rs` is UNCHANGED — it stays as the `classic-registry-core` typed key/value singleton bridge. CXXS-06's "registry" wording is interpreted as the `classic::version_registry` namespace; the `classic::registry` namespace continues to mean classic-registry-core.

**D-03:** `src/path.rs` is added to `build.rs::cxx_build::bridges` AS-IS in an early Phase 2 plan, then widened in subsequent plans within the same phase to cover the full `classic-path-core` surface (validation helpers, backup helpers, restricted-path checks, `DocsPathFinder` INI variants per CXXS-08).

**D-04:** `classic-constants-core` enums (`GameId`, `YamlFile`, `Fallout4Version`) are exposed as CXX shared enums declared inside `#[cxx::bridge(namespace = "classic::constants")]` blocks.

**D-05:** Default DTO shape for "list of issues" results is flat CXX shared structs per issue type. Each domain gets a `#[cxx::bridge]` shared struct with flat scalar/`String` fields only. No nested `Vec` anywhere.

**D-06:** Nested orchestrator results are flattened across the FFI boundary by exposing one bridge fn per sub-domain rather than one fn returning a nested aggregate.

**D-07:** Severity/category enums cross the boundary as CXX shared enums declared inside `#[cxx::bridge]`.

**D-08:** Bridge keeps core-side combined-output summary helpers alongside new structured DTOs. Existing GUI code paths that just dump text continue to work without modification.

**D-09:** `python tools/cxx_api_parity/check_parity_gate.py --update-baseline` runs per plan, in the same commit as the surface change. Each plan commits refreshed `docs/implementation/cxx_api_parity/baseline/parity_contract.json` + `cxx_diff_report.{json,md}` + `cxx_gate_report.md`.

**D-10:** Clean MSVC builds (`pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` AND `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Clean -Test`) are MANDATORY before committing any plan that adds a new `src/*.rs` to `build.rs::cxx_build::bridges`.

**D-11:** Phase 2 MIGRATES classic-cli/classic-gui call sites that currently hand-roll scangame, path, xse, or version-registry logic in C++ specifically because the bridge was too narrow. New bridge functions land with at least one production caller.

**D-12:** Every new bridge function gets a Rust-side `#[cfg(test)] mod tests` block in its bridge file. C++ Catch2 tests added only if Rust-side test cannot exercise the code path.

### Claude's Discretion

- Exact field names and ordering inside each new shared struct DTO.
- Whether `extract_pe_version_string`, `find_game_path`, `validate_path`, and `check_restricted_path` from `game.rs` move into `path.rs` during the path-widening plan or stay as compatibility shims.
- Internal organisation of the new `src/scangame.rs` file once widened.
- Whether `classic::web::ModSite::game_url(GameId)` is exposed as one bridge fn or split per `ModSite` variant.
- Whether the FCX issue getter (CXXS-03) returns `Vec<FcxIssueDto>` or a single combined-output string.
- Whether the database typed result API (CXXS-05) keeps the existing tab-delimited path AND adds a typed `Vec<FormIdEntryDto>` path (additive), or replaces the tab-delimited helper outright.

### Deferred Ideas (OUT OF SCOPE)

- CI wiring of the CXX gate (Phase 5)
- Python and Node tier collapse (Phases 3 and 4)
- Tier-2 governance file deletion and harmony-doc rewrite (Phase 6)
- HARM-05 error-contract documentation (Phase 6)
- Any classic-cli/classic-gui rewrite that is not directly proving a new bridge entry point
- Error contract standardization across bindings (Pitfall 7 / Phase 6)
- `docs/api/classic-cpp-bridge-*.md` rewrite (Phase 6)
- `docs/api/binding-parity-overview.md` rewrite (Phase 6)
- C++ Catch2 tests unless Rust-side cannot cover the path

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CXXS-01 | New `constants` module covering `classic-constants-core` | GameId/YamlFile/Fallout4Version enums enumerated; SETTINGS_IGNORE_NONE; must_not_be_none — all flat primitives, no DTO nesting issues |
| CXXS-02 | New `web` module covering `classic-web-core` URL/user-agent/mod-site helpers | ModSite enum (3 variants), validate_url/is_valid_url/extract_domain/join_url/build_url_with_query — all return String or bool; no nested structs |
| CXXS-03 | FCX issue getter in `scanner.rs` alongside existing `fcx_reset_global_state()` | ConfigIssue struct from fcx_handler.rs enumerated (7 flat string fields); section field is Option<String> — bridge as String + bool sentinel |
| CXXS-04 | `scangame` widened from 2 entry points to full `classic-scangame-core` orchestration surface | All scangame sub-domain types enumerated; BA2Issues contains Vec<String> fields → must split to per-issue-type bridge fns |
| CXXS-05 | `database` exposes typed FormID result API | pool_sqlx.rs get_entry returns String; get_entries_batch returns tab-delimited strings → additive typed Vec<FormIdEntryDto> path |
| CXXS-06 | `version_registry` exposes full OG/NG/AE/VR selection metadata | Already partially bridged in game.rs; D-02 moves to new file — surface already confirmed complete in game.rs; migration only |
| CXXS-07 | `config` exposes suspect-rule subset | SuspectErrorRule/SuspectStackRule/SuspectStackCountRule enumerated; stack_contains_at_least is Vec<SuspectStackCountRule> → requires per-field flattening |
| CXXS-08 | `path` exposes every `classic-path-core` validation/backup helper | path.rs already has 3 functions; needs is_valid_path, is_restricted_path, validate_path_exists, validate_required_files, backup helpers, IniCheckResult |
| CXXS-09 | `xse` exposes every `classic-xse-core` detection helper | XseType enum (6 variants), XseInfo struct, detect_xse_version, is_xse_installed, get_xse_info — all enumerated |
| CXXS-10 | All existing C++ frontend code builds clean against widened bridge | Call-site migration enumerated; clean-build cadence (D-10) validated |

</phase_requirements>

---

## Summary

Phase 2 adds 4 new bridge modules (`constants.rs`, `web.rs`, `xse.rs`, `version_registry.rs`), promotes `path.rs` from source-only to a `build.rs`-listed module, widens `scangame.rs` from 2 to ~12 entry points, adds FCX getter to `scanner.rs`, adds typed FormID API to `database.rs`, and adds suspect-rule accessors to `config.rs`. Every plan commits a refreshed parity gate baseline in the same commit. At least 5 plans trigger mandatory clean MSVC build cycles (one per new `build.rs` entry).

The critical insight from source reading is that `BA2Issues`, `SuspectStackRule`, and similar types contain `Vec<Vec<...>>` structures that CANNOT cross the CXX boundary as-is. The D-06 flattening rule (one bridge fn per sub-domain) is the correct architectural response. The `SuspectStackRule.stack_contains_at_least: Vec<SuspectStackCountRule>` requires a separate Vec pair (substrings + counts) rather than a nested DTO.

The D-11 migration audit confirms that `classic-gui/src/app/pathdialog.cpp` already calls `classic::game::check_restricted_path()` and `classic::game::validate_path()` — these helpers currently live in `game.rs` but belong in `path.rs`. The `MainWindow` uses `classic::path::detect_fallout4_game_path()` and `detect_fallout4_docs_path()` from the already-existing (but unbridged) `path.rs`. The `GameFilesWorker` uses `classic::scangame::run_setup_checks()` — the D-08 backward-compat pattern keeps this working while new structured DTOs are added.

**Primary recommendation:** Plan the phase in 8 focused plans: (1) path.rs promotion + validator widening, (2) constants.rs new module, (3) web.rs new module, (4) xse.rs split + version_registry.rs split (both trigger clean builds — can be one plan if the operator batches), (5) scangame.rs BA2/INI/ENB widening, (6) scangame.rs TOML/Wrye/integrity/setup widening, (7) config.rs suspect-rules + database.rs typed API, (8) scanner.rs FCX getter. Each plan commits code + parity artifacts together.

---

## Current Bridge Surface Inventory

### `build.rs` — Current 14-file list (source: direct file read)

```
src/types.rs, src/runtime.rs, src/registry.rs, src/yaml.rs, src/config.rs,
src/scanner.rs, src/database.rs, src/files.rs, src/scangame.rs, src/game.rs,
src/update.rs, src/message.rs, src/perf.rs, src/markdown.rs
```

Phase 2 adds: `src/path.rs`, `src/constants.rs`, `src/web.rs`, `src/xse.rs`, `src/version_registry.rs`

### `src/scangame.rs` — Current 2 entry points (confirmed by direct read)

```
namespace = "classic::scangame"

Structs: SetupCheckResult { combined_output, has_errors, total_checks }
         PathDetectionNeeds { needs_game_path, needs_docs_path }

extern "Rust":
  fn run_setup_checks(game_exe_path, game_root, docs_path, game_name) -> SetupCheckResult
  fn needs_path_detection(game_path, docs_path) -> PathDetectionNeeds
```

### `src/game.rs` — Current surface (will be split per D-01/D-02)

```
namespace = "classic::game"

Structs: VersionInfoDto { id, version_string, short_name, game, docs_name, steam_id: u32, is_vr, found }
         XseConfigDto { acronym, full_name, compatible_version, loader, file_count: u32, found }
         CrashgenConfigDto { version, name, acronym, dll_file, description, download_url }
         MatchResultDto { matched_id, confidence, message, is_match }
         GameVersionDto { major, minor, patch, build: u32 each, valid }

extern "Rust":
  // Version Registry (moves to version_registry.rs per D-02)
  fn version_registry_get_by_id(id) -> VersionInfoDto
  fn version_registry_get_all_ids() -> Vec<String>
  fn version_registry_get_all_count() -> usize
  fn version_registry_match_version(version_str, game, is_vr) -> MatchResultDto
  fn version_registry_get_xse_config(id) -> XseConfigDto
  fn version_registry_get_crashgen_configs(id) -> Vec<CrashgenConfigDto>
  fn version_registry_get_crashgen_config(id, crashgen_version) -> CrashgenConfigDto

  // Version parsing (moves to version_registry.rs per D-02)
  fn parse_game_version(version_str) -> GameVersionDto

  // PE version (stays in game.rs per CONTEXT.md discretion note)
  fn extract_pe_version_string(exe_path) -> String

  // XSE (moves to xse.rs per D-01)
  fn detect_xse_version_string(exe_path, xse_type_str) -> String
  fn is_xse_installed_check(game_root, xse_type_str) -> bool

  // Path (moves to path.rs per D-03 / CONTEXT.md discretion note)
  fn find_game_path(game_exe, xse_loader, game_name, is_vr, cached_path, xse_log_path) -> String
  fn validate_path(path) -> bool
  fn check_restricted_path(path) -> bool
```

### `src/path.rs` — Current content (source-only, not in build.rs)

```
namespace = "classic::path"

extern "Rust":
  fn detect_fallout4_game_path(cached_path, selected_game_version) -> String
  fn resolve_fallout4_exe_name(selected_game_version) -> String
  fn detect_fallout4_docs_path(cached_path, selected_game_version) -> String
```

NOTE: These 3 functions exist but the file is NOT in `build.rs`. D-03 adds it.

### `src/database.rs` — Current surface (confirmed by direct read)

```
namespace = "classic::database"

Opaque: type DbPool

extern "Rust":
  fn db_pool_new(game_table, max_connections: u32, cache_ttl_secs: u64) -> Box<DbPool>
  fn db_pool_initialize(pool, db_paths: &[String]) -> Result<()>
  fn db_pool_get_entry(pool, formid, plugin) -> String  // "" on miss
  fn db_pool_get_entries_batch(pool, formids, plugins) -> Vec<String>  // "formid\tvalue" tab-delimited
  fn db_pool_is_available(pool) -> bool
  fn db_pool_cache_size(pool) -> usize
  fn db_pool_clear_cache(pool, expired_only) -> usize
  fn db_pool_close(pool) -> Result<()>
  fn db_pool_game_table(pool) -> String
```

CXXS-05 gap: No typed `FormIdEntryDto` return; only tab-delimited String results.

### `src/config.rs` — Current surface (confirmed by direct read)

```
namespace = "classic::config"

Opaque: type YamlData

Shared structs: CacheStats { hits: u64, misses: u64, hit_rate: f64, size: usize, capacity: usize }
                YamlDataModSolutionCriteria { any: Vec<String>, all: Vec<String> }
                YamlDataModSolutionEntry { id, criteria: YamlDataModSolutionCriteria,
                                           exceptions: Vec<String>, name, description }

extern "Rust" (YamlData-bound): yaml_data_load, yaml_data_classic_version[_date],
  yaml_data_crashgen_name_field, yaml_data_crashgen_latest_og, yaml_data_warn_noplugins,
  yaml_data_warn_outdated, yaml_data_xse_acronym, yaml_data_autoscan_text,
  yaml_data_game_version, yaml_data_game_root_name_field,
  yaml_data_get_crashgen_name, yaml_data_get_game_root_name, yaml_data_get_crashgen_ignore,
  yaml_data_classic_game_hints, yaml_data_classic_records_list, yaml_data_crashgen_ignore_og,
  yaml_data_game_ignore_plugins, yaml_data_game_ignore_records, yaml_data_ignore_list,
  yaml_data_suspects_error_keys, yaml_data_suspects_error_values,
  yaml_data_suspects_stack_keys,   <-- only keys exposed for suspect_stack, NOT full rule details
  yaml_data_mods_core_keys/values/names/gpus/count, yaml_data_mods_freq_entries,
  yaml_data_mods_conf_mod_a/b/name_a/b/descriptions/fixes/links/count,
  yaml_data_mods_solu_entries,
  save_local_yaml_paths, settings_cache_clear, settings_cache_size, settings_cache_stats,
  reset_settings_cache_stats
```

CXXS-07 gap: `yaml_data_suspects_stack_keys` exposes only the IDs. The full `SuspectStackRule` fields (severity, match patterns, exclusions, count rules) are absent. `SuspectErrorRule` has keys+values only; severity and `main_error_contains_any` pattern Vec are absent.

### `src/scanner.rs` — Current FCX surface (confirmed by direct read)

```
fn fcx_reset_global_state() -> Result<()>   // exists
// get_fcx_config_issues() NOT YET EXPOSED  <- CXXS-03 gap
```

### `src/registry.rs` — STAYS UNCHANGED (classic-registry-core KV bridge per D-02)

---

## Target Rust Crate Public Surfaces

### `classic-constants-core` (source: direct read of lib.rs)

**Enums to expose as CXX shared enums:**

`GameId` (4 variants): `Fallout4`, `Fallout4VR`, `Skyrim`, `Starfield`
  - Method `as_str()` → expose as bridge fn `game_id_as_str(GameId) -> &str`

`YamlFile` — needs direct read to enumerate variants (NOT yet read — see gap)

`Fallout4Version` (4 variants): `Original`, `NextGen`, `AnniversaryEdition`, `Vr`
  - Key methods: `registry_id() -> &'static str`, `is_vr() -> bool`, `is_standard() -> bool`,
    `exe_name() -> &'static str`, `docs_folder_name() -> &'static str`, `steam_app_id() -> u32`
  - `get_version_info()` delegates to VersionRegistry — NOT bridged directly (returns `&'static VersionInfo` opaque)
  - `game_version()`, `version_semver()`, `xse_acronym()` delegate to registry — expose only `registry_id()` from bridge; callers use `version_registry_get_by_id()`

**Constants:**
`NULL_VERSION: Version = Version::new(0,0,0)` — NOT directly bridgeable (semver type). Bridge as helper fn `is_null_version(major: u32, minor: u32, patch: u32) -> bool`.

`SETTINGS_IGNORE_NONE: &[&str]` — array of 5 string literals. Bridge as `settings_ignore_none_contains(key: &str) -> bool` and `must_not_be_none(key: &str) -> bool`.

**Key CXX constraint:** `GameId` is used in `ModSite::game_url(GameId)` — the shared enum in `constants.rs` must be declared before it's referenced in `web.rs`. Declare `GameId` in `constants.rs` and reference it from `web.rs` OR duplicate the declaration (CXX shared enums in different bridge blocks do not automatically share; use a `types.rs` addition or ensure declaration order).

**RESOLUTION:** Expose `ModSite::game_url(GameId)` as a bridge fn in `web.rs` that takes the `GameId` CXX shared enum variant as a u8/string discriminant to avoid cross-module enum reference. Use the string form: `mod_site_game_url(site_name: &str, game_id_str: &str) -> String`.

### `classic-web-core` (source: direct read of lib.rs)

**Functions to expose:**
- `validate_url(url_str: &str) -> Result<(), String>` — bridge returns `Result<(), String>` (bool alternative: use `is_valid_url`)
- `is_valid_url(url_str: &str) -> bool` — directly bridgeable
- `extract_domain(url_str: &str) -> Result<String, String>` — returns `Result<String>`
- `get_user_agent() -> String` — directly bridgeable
- `get_user_agent_with_suffix(suffix: &str) -> String` — directly bridgeable
- `join_url(base: &str, path: &str) -> Result<String, String>` — via `Result<String>`
- `build_url_with_query(base: &str, params: &[(&str, &str)]) -> Result<String, String>` — PROBLEM: `&[(&str, &str)]` slices of tuples are not CXX-bridgeable. Must take two `&[String]` parallel vectors (keys + values).

**ModSite enum methods:**
- `ModSite::base_url() -> &'static str` — expose as `mod_site_base_url(site_name: &str) -> String`
- `ModSite::name() -> &'static str` — expose as `mod_site_name(site_name: &str) -> String`
- `ModSite::game_url(GameId) -> String` — expose as `mod_site_game_url(site_name: &str, game_id_str: &str) -> String`

**CXX shared enum for ModSite (3 variants):** `NexusMods`, `BethesdaNet`, `ModDB`
- Declare `ModSite` as a CXX shared enum in `web.rs` per D-04 and D-07.

**WebError:** NOT bridgeable as a typed error; bridge functions return `Result<T, String>` or fail-soft per Pitfall 7.

**Pitfall 6 check:** All `classic-web-core` bridge fns return `String`, `bool`, or `Result<String>`. No Vec<StructWithVec>. CLEAR.

### `classic-xse-core` (source: direct read of lib.rs)

**CXX shared enum `XseType` (6 variants):** F4SE, F4SEVR, SKSE, SKSE64, SKSEVR, SFSE

**Functions currently in `game.rs` that MOVE to `xse.rs` (D-01):**
- `detect_xse_version_string(exe_path: &str, xse_type_str: &str) -> String` (string-based dispatch, stays string-based for existing callers per D-08)
- `is_xse_installed_check(game_root: &str, xse_type_str: &str) -> bool`
- `xse_type_from_str(s: &str) -> Result<XseType, String>` (internal helper, stays private or becomes bridge fn)

**NEW functions for CXXS-09 (using typed `XseType` enum):**
- `xse_get_loader_name(xse_type: XseType) -> String` (wraps `XseType::loader_name()`)
- `xse_get_dll_prefix(xse_type: XseType) -> String` (wraps `XseType::dll_prefix()`)
- `xse_get_type_from_game_id(game_id_str: &str) -> String` (wraps `XseType::from_game_id()`)
- `xse_get_info(game_path: &str, xse_type_str: &str) -> XseInfoDto` (wraps `get_xse_info()`)

**`XseInfoDto` shared struct (flat, Pitfall 6 CLEAR):**
```
XseInfoDto {
    xse_type: String,     // as_str() value
    path: String,
    version: String,      // "" if None
    installed: bool,
}
```

### `classic-version-registry-core` (source: direct read; currently bridged in `game.rs`)

**D-02 migration:** All `version_registry_*` and `parse_game_version` fns move from `game.rs` to new `version_registry.rs`. The DTO structs (`VersionInfoDto`, `XseConfigDto`, `CrashgenConfigDto`, `MatchResultDto`, `GameVersionDto`) also move.

**CXXS-06 gap check — what is NOT yet bridged:**
- `VersionRegistry::get_all_for_game(game, is_vr_filter)` — new fn `version_registry_get_all_for_game(game: &str, is_vr: bool) -> Vec<VersionInfoDto>`
- Full crashgen rule resolution surface is ALREADY bridged via `version_registry_get_crashgen_configs` and `version_registry_get_crashgen_config`.
- OG/NG/AE/VR enum discrimination is done via the `VersionInfoDto.is_vr` field and `VersionInfoDto.id` (e.g., "FO4_OG"). All variants are accessible via `version_registry_get_by_id()`.

**Pitfall 6 check:** `VersionInfoDto`, `CrashgenConfigDto` — all flat String/bool/u32 fields. `Vec<CrashgenConfigDto>` is bridgeable (flat struct). CLEAR.

### `classic-config-core` (source: direct read of yamldata.rs)

**CXXS-07 gap — SuspectErrorRule fields NOT yet bridged:**

`SuspectErrorRule` has 4 fields: `id: String`, `name: String`, `severity: i32`, `main_error_contains_any: Vec<String>`
- Current bridge: `yaml_data_suspects_error_keys()` (ids only) + `yaml_data_suspects_error_values()` (names only)
- Missing: severity values, `main_error_contains_any` per-rule Vec

**Bridge approach for CXXS-07 (D-05/D-06 flat rule):**
- Add `yaml_data_suspects_error_severities(data: &YamlData) -> Vec<i32>`
- Add `yaml_data_suspects_error_pattern_count(data: &YamlData) -> usize` + index-based getter? OR use combined flat string: `yaml_data_suspects_error_patterns(data: &YamlData) -> Vec<String>` as tab-separated patterns per rule (since different rules have different-length pattern Vecs, cannot be a simple Vec<String>).
- **Cleaner:** Add a new `SuspectErrorRuleDto` shared struct: `{ id: String, name: String, severity: i32, patterns: String }` where `patterns` is `\n`-joined or `|`-delimited for C++ to split. This avoids `Vec<Vec<String>>` while staying in D-05 territory.
- Alternative: Use the `YamlDataModSolutionEntry` pattern — a shared struct with the inner Vec flattened to `Vec<String>`. `SuspectErrorRuleDto { id, name, severity, main_error_contains_any: Vec<String> }` is VALID because the inner type is `String`, not a struct-with-Vec. Pitfall 6 says `Vec<StructWithVec>` is forbidden, but `Vec<String>` inside a struct is fine (confirmed by existing `YamlDataModSolutionCriteria.any: Vec<String>`).

**RESOLUTION for CXXS-07:** Add `SuspectErrorRuleDto { id: String, name: String, severity: i32, main_error_contains_any: Vec<String> }` — this has the SAME nesting depth as `YamlDataModSolutionCriteria` (inner Vec<String> is OK). Add bridge fn `yaml_data_suspects_error_rules(data: &YamlData) -> Vec<SuspectErrorRuleDto>`.

**`SuspectStackRule` requires more analysis:**

`SuspectStackRule` fields: `id`, `name`, `severity: i32`, `main_error_required_any: Vec<String>`, `main_error_optional_any: Vec<String>`, `stack_contains_any: Vec<String>`, `exclude_if_stack_contains_any: Vec<String>`, `stack_contains_at_least: Vec<SuspectStackCountRule>`

`SuspectStackCountRule` fields: `substring: String`, `count: usize`

`Vec<SuspectStackCountRule>` inside `SuspectStackRule` makes it a `Vec<StructWithPrimitiveFields>` — this is VALID for CXX (it's only `Vec<StructWithVec>` that is forbidden). However, `SuspectStackRule` itself has FIVE `Vec<String>` fields + one `Vec<SuspectStackCountRule>` field. A shared struct with multiple Vec fields is valid as long as none of those Vec items contain Vecs themselves.

**RESOLUTION for CXXS-07 stack rules:** `SuspectStackCountRuleDto { substring: String, count: u32 }` (flat). `SuspectStackRuleDto { id, name, severity: i32, main_error_required_any: Vec<String>, main_error_optional_any: Vec<String>, stack_contains_any: Vec<String>, exclude_if_stack_contains_any: Vec<String>, stack_contains_at_least: Vec<SuspectStackCountRuleDto> }`. This is valid because `SuspectStackCountRuleDto` contains NO Vec fields. Add bridge fn `yaml_data_suspects_stack_rules(data: &YamlData) -> Vec<SuspectStackRuleDto>`.

**FCX getter (CXXS-03):**

`ConfigIssue` from `classic_scanlog_core::fcx_handler` has 7 fields: `file_path: String`, `section: Option<String>`, `setting: String`, `current_value: String`, `recommended_value: String`, `description: String`, `severity: String`.

`Option<String>` is NOT CXX-bridgeable as-is. Bridge as `FcxIssueDto { file_path, section_or_empty: String, setting, current_value, recommended_value, description, severity }` where `section_or_empty` is `""` when `section` is `None`.

Source in `scanner.rs` bridge: `FcxModeHandler::reset_global_state()` already bridged as `fcx_reset_global_state()`. Access to `GLOBAL_FCX_HANDLER.lock().unwrap().get_detected_issues()` gives `&[ConfigIssue]`.

**Bridge fn:** `get_fcx_config_issues() -> Vec<FcxIssueDto>` — reads from the global FCX singleton.

**Pitfall 6 check:** `FcxIssueDto` — all `String` fields, no nested Vec. CLEAR.

### `classic-database-core` pool_sqlx.rs (CXXS-05)

`get_entry(formid, plugin, None) -> Result<Option<String>>` — currently bridged as fail-soft `String` return.
`get_entries_batch(pairs, None, 50) -> Result<HashMap<(formid,plugin), value>>` — currently bridged as tab-delimited strings.

**CXXS-05 typed result API addition (additive per D-08):**

`FormIdEntryDto { formid: String, plugin: String, value: String, found: bool }` — flat, Pitfall 6 CLEAR.

Add: `db_pool_get_entry_typed(pool: &DbPool, formid: &str, plugin: &str) -> FormIdEntryDto`
Add: `db_pool_get_entries_batch_typed(pool: &DbPool, formids: &[String], plugins: &[String]) -> Vec<FormIdEntryDto>`

Keep existing `db_pool_get_entry` and `db_pool_get_entries_batch` unchanged per D-08.

### `classic-path-core` (CXXS-08)

**Current `path.rs` bridge functions (3 fns, NOT yet in build.rs):**
- `detect_fallout4_game_path(cached_path, selected_game_version) -> String`
- `resolve_fallout4_exe_name(selected_game_version) -> String`
- `detect_fallout4_docs_path(cached_path, selected_game_version) -> String`

**Functions from `game.rs` that should MOVE to `path.rs` (planner discretion per CONTEXT.md D-04 note):**
- `find_game_path(game_exe, xse_loader, game_name, is_vr, cached_path, xse_log_path) -> String`
- `validate_path(path) -> bool`
- `check_restricted_path(path) -> bool`

**New functions for CXXS-08 (not yet bridged):**

From `validator.rs`:
- `validate_path_exists(path: &str) -> Result<(), String>`
- `validate_is_directory(path: &str) -> Result<(), String>`
- `validate_is_file(path: &str) -> Result<(), String>`
- `validate_required_files(dir: &str, required: &[String]) -> Result<(), String>`
- `validate_custom_scan_path(path: &str) -> Result<(), String>`

From `checker.rs` (`IniCheckResult`):
`IniCheckResult { has_ini: bool, has_custom_ini: bool, has_prefs_ini: bool, ini_path: String, custom_ini_path: String, prefs_ini_path: String }` — flat, Pitfall 6 CLEAR.
- `docs_checker_check_ini_files(docs_path: &str, game_name: &str) -> IniCheckResult`

From `backup.rs` (`BackupManager`):
- `backup_create_timestamped(source_path: &str, game_name: &str) -> Result<String, String>` (returns created backup path)
- `backup_list_existing(source_path: &str, game_name: &str) -> Vec<String>`

From `game_path.rs`:
- `parse_xse_log(log_path: &str) -> Result<String, String>` (wraps `parse_xse_log`)

**Pitfall 6 check:** `IniCheckResult` — all String/bool fields. CLEAR.

### `classic-scangame-core` (CXXS-04)

**Full sub-domain analysis for bridge fns (D-06 one-fn-per-subdomain rule):**

**BA2 sub-domain:**
`BA2Issues { tex_dims: Vec<String>, tex_frmt: Vec<String>, snd_frmt: Vec<String>, xse_file: Vec<String> }`

Direct `Vec<String>` fields — `BA2Issues` itself is NOT a flat struct (it has 4 `Vec<String>` fields). While `Vec<String>` inside a struct IS valid per the YamlDataModSolutionCriteria precedent, `Vec<BA2Issues>` would be a `Vec<StructWithVec>` — Pitfall 6 violation.

**RESOLUTION (D-06 split):** Return `Ba2IssuesSummaryDto` for scalar totals + 4 separate fns returning `Vec<String>` per issue category:
- `scangame_run_ba2_check(archive_path: &str) -> Ba2IssuesSummaryDto { tex_dim_count, tex_fmt_count, snd_fmt_count, xse_file_count, total: u32, has_issues: bool }`
- `scangame_get_ba2_tex_dims(archive_path: &str) -> Vec<String>`
- `scangame_get_ba2_tex_frmt(archive_path: &str) -> Vec<String>`
- `scangame_get_ba2_snd_frmt(archive_path: &str) -> Vec<String>`
- `scangame_get_ba2_xse_files(archive_path: &str) -> Vec<String>`

**INI sub-domain:**
`scangame::ini::ConfigIssue { key: String, section: String, found_value: String, expected_value: String, severity: IssueSeverity enum }`
`IssueSeverity enum`: `Error`, `Warning`, `Info`

`IssueSeverity` as CXX shared enum per D-07. `ConfigIssue` flat fields.

- `scangame_run_ini_check(ini_path: &str, game_name: &str) -> Vec<IniConfigIssueDto>` where `IniConfigIssueDto { key, section, found_value, expected_value, severity: IssueSeverity }`.

Note: `scangame::ini::ConfigIssue` is a DIFFERENT type from `scanlog::fcx_handler::ConfigIssue` — name collision in the bridge namespace. Use `IniConfigIssueDto` for scangame and `FcxIssueDto` for FCX.

**ENB sub-domain:**
`EnbValidationResult { enb_result: EnbResult, config_result: EnbConfigResult, errors: Vec<String> }`
`EnbResult enum { NotPresent, PresentNoConfig, PresentWithConfig, PresentWithIniOverride }`
`EnbConfigResult enum { Valid, HasConflicts, Missing, NotApplicable }`

`EnbValidationResult.errors: Vec<String>` inside a struct — valid (String items). But if we need `Vec<EnbValidationResult>`, that's `Vec<StructWithVec>` — Pitfall 6. Return a single `EnbValidationResultDto`.

- `scangame_run_enb_check(game_path: &str) -> EnbValidationResultDto`
  `EnbValidationResultDto { enb_result: EnbResult, config_result: EnbConfigResult, errors_csv: String }` where `errors_csv` is `\n`-joined.

OR use separate getters:
- `scangame_run_enb_check_result(game_path: &str) -> EnbResult` (enum return)
- `scangame_run_enb_check_config_result(game_path: &str) -> EnbConfigResult` (enum return)
- `scangame_run_enb_check_errors(game_path: &str) -> Vec<String>`

**TOML sub-domain (crashgen):**
`TomlConfigIssue { key: String, found_value: String, expected_value: String, severity: TomlIssueSeverity enum, description: String }`
`TomlIssueSeverity enum { Info, Warning, Error }`

- `scangame_run_toml_check(toml_path: &str, game_path: &str) -> Vec<TomlConfigIssueDto>` where `TomlConfigIssueDto { key, found_value, expected_value, severity: TomlIssueSeverity, description }` — flat, CLEAR.

**Wrye sub-domain:**
`WryeIssue { plugin_name: String, issue_type: String, severity: WryeSeverity enum, details: String }`
`WryeSeverity enum { Error, Warning, Info, Note }`

- `scangame_run_wrye_check(wrye_html_path: &str) -> Vec<WryeIssueDto>` where `WryeIssueDto { plugin_name, issue_type, severity: WryeSeverity, details }` — flat, CLEAR.

**Integrity sub-domain:**
`IntegrityCheckResult { check_type: CheckType enum, passed: bool, message: String }`
`CheckType enum { Existence, Format, Content, Structure, Custom }`

- `scangame_run_integrity_check(game_exe_path: &str, game_name: &str) -> Vec<IntegrityCheckResultDto>` where `IntegrityCheckResultDto { check_type: CheckType, passed: bool, message }` — flat, CLEAR.

**Setup orchestrator sub-domain (D-06 keep D-08 backward compat):**
Keep existing `run_setup_checks` + `needs_path_detection` per D-08. Add:
- `scangame_run_setup_structured(game_exe_path, game_root, docs_path, game_name) -> ScanGameSetupDto`
  `ScanGameSetupDto { check_count: u32, error_count: u32, warning_count: u32, has_errors: bool }` — flat counts.

**Mod-INI sub-domain (if in scope):**
`ModIniScanResult { issues: Vec<...> }` — requires sub-domain decomposition. Defer unless explicitly in CXXS-04 scope (CXXS-04 says "orchestration entry points used by Python/Node bindings"). If Python/Node expose mod_ini, include; otherwise defer.

**Logs sub-domain:** `LogErrorEntry { timestamp, level, message, source_file, line_number }` — all String/u32, flat.
- `scangame_get_log_errors(log_path: &str) -> Vec<LogErrorDto>` — if Python/Node expose this.

**CrashgenOrchestrator sub-domain:**
`CrashgenReport { crashgen_name, is_installed: bool, has_config: bool, config_issues: Vec<TomlConfigIssue>, version_string, status_message }`

`config_issues: Vec<TomlConfigIssue>` inside `CrashgenReport` makes it a `Vec<StructWithVec>` if returned in a Vec. But as a SINGLE return it's still `StructWithVec` which triggers Pitfall 6 (the inner `config_issues` Vec makes the struct non-trivially shareable).

**RESOLUTION:** Use D-06 split — separate fns:
- `scangame_run_crashgen_check(game_path, game_name, crashgen_name) -> CrashgenReportSummaryDto`
  `CrashgenReportSummaryDto { crashgen_name, is_installed, has_config, version_string, status_message, issue_count: u32 }` — flat.
- `scangame_get_crashgen_issues(game_path, game_name, crashgen_name) -> Vec<TomlConfigIssueDto>` — reuses `TomlConfigIssueDto` from TOML sub-domain.

---

## D-11 Consumer Migration Enumeration

### `classic-gui/src/app/pathdialog.cpp`

| Location | What it hand-rolls | New bridge fn | CXXS req |
|----------|--------------------|---------------|----------|
| `ManualPathDialog::validateAndAccept()` | Calls `classic::game::check_restricted_path()` via `game.h` include | After D-01/D-02/D-03: `classic::path::check_restricted_path()` or stays at `classic::game::check_restricted_path()` if game.rs keeps shim | CXXS-08 / D-03 |

**Current include:** `#include "classic_cxx_bridge/game.h"`

After Phase 2 the `check_restricted_path` fn should resolve through `classic::path` namespace. If the planner decides to keep it as a shim in `game.rs`, no include change needed. If the fn moves to `path.rs`, the include changes to `"classic_cxx_bridge/path.h"`.

**Recommendation:** Keep `classic::game::check_restricted_path` as a delegation shim calling `classic_path_core::is_restricted_path`. Add the same fn as `classic::path::check_restricted_path` in `path.rs`. C++ callers that already use `game.h` continue to work (D-08 backward compat). New code should use `path.h`.

### `classic-gui/src/app/mainwindow.cpp`

| Location | What it hand-rolls | New bridge fn | CXXS req |
|----------|--------------------|---------------|----------|
| `MainWindow` startup (path detection) | Already uses `classic::path::detect_fallout4_game_path()` and `classic::path::detect_fallout4_docs_path()` via `path.h` | No migration needed — ALREADY USES path.rs bridge | CXXS-08 (path.rs promotion to build.rs unlocks these) |
| Settings save on path confirm | Calls `classic::config::save_local_yaml_paths()` via `config.h` | Already bridged | None |
| `needs_path_detection` usage | Uses `classic::scangame::needs_path_detection()` via `scangame.h` | Already bridged | None |

**KEY FINDING:** `mainwindow.cpp` includes `"classic_cxx_bridge/path.h"` and calls `classic::path::detect_fallout4_game_path()` / `classic::path::detect_fallout4_docs_path()`. These functions EXIST in `src/path.rs` but path.rs is NOT in `build.rs`. This means the GUI currently CANNOT build against path.rs — OR it falls back to a different implementation. D-03 (adding path.rs to build.rs) is what actually makes these GUI calls work.

**VERIFICATION NEEDED:** If `mainwindow.cpp` includes `path.h` but path.rs is not in build.rs, the current build must be failing OR there is another mechanism. Check if path.rs symbols are exposed through another module. Given that the build is green (Phase 1 complete), path.rs may be included via game.rs by some other mechanism, OR these path.h includes were added in anticipation.

### `classic-gui/src/workers/gamefilesworker.cpp`

| Location | What it hand-rolls | New bridge fn | CXXS req |
|----------|--------------------|---------------|----------|
| `GameFilesWorker::doScan()` | Calls `classic::scangame::run_setup_checks()` — returns `SetupCheckResult.combined_output` string only | Keep for D-08 compat. New structured DTOs from CXXS-04 enable richer UI if GUI wants to show per-issue breakdowns | CXXS-04 / D-08 |

**D-11 qualification:** `gamefilesworker.cpp` IS the production caller that proves `run_setup_checks` works. The CXXS-04 widening adds new fns alongside it. D-11 requires that each new scangame fn has at least one production caller — the GUI would need to call the new fns for D-11 to be satisfied for those entry points. The planner must either (a) add new GUI call sites consuming the new structured DTOs, or (b) document that the CLI is the production caller for certain scangame fns.

### `classic-cli/src/scanner.cpp`

| Location | What it hand-rolls | New bridge fn | CXXS req |
|----------|--------------------|---------------|----------|
| `scan_with_config()` | Uses `classic::scanner::*` extensively — already bridged | None | None |
| `resolve_xse_folder_for_scan()` | Hand-rolls YAML read to get XSE folder path | No new bridge fn needed (this reads game-specific YAML data, not XSE detection logic) | None |
| `find_data_root()` | C++ filesystem walk for CLASSIC Data dir — pure C++ path resolution, NOT a scangame/path/xse concern | No migration needed | None |

**Assessment:** `classic-cli/src/scanner.cpp` does NOT hand-roll scangame, path, xse, or version-registry logic in ways that qualify for D-11 migration. The `resolve_xse_folder_for_scan()` reads a YAML key — it's not an xse-core concern, just a YAML data read.

### Summary of D-11 migrations

| File | Migration Type | Phase 2 action |
|------|----------------|----------------|
| `pathdialog.cpp` | `check_restricted_path` (game.h → path.h) | Add `classic::path::check_restricted_path` to path.rs; keep game.rs shim for D-08; add `path.h` include to pathdialog.cpp |
| `mainwindow.cpp` | `detect_fallout4_game_path`, `detect_fallout4_docs_path` (path.h) | Ensure path.rs is in build.rs (D-03) so existing `path.h` includes actually compile |
| `gamefilesworker.cpp` | `run_setup_checks` (existing CXXS-04 D-08 caller) | Keep as-is; add new scangame structured-DTO callers in a GUI controller or new worker method |

**For new CXXS-04 scangame fns:** The planner should add at least one new C++ call site for each new scangame bridge fn. Candidates: a new `GameFilesWorker::doDetailedScan()` method or a `GameFilesController` slot that calls `scangame_run_ba2_check()` for the textures tab, or CLI output showing per-category BA2 issue counts.

---

## Pitfall 6 DTO Validation (All Planned DTOs)

| DTO | Inner Vec types | Pitfall 6 status | Resolution |
|-----|-----------------|------------------|------------|
| `Ba2IssuesSummaryDto` | None (u32 scalars only) | CLEAR | Direct use |
| `IniConfigIssueDto` | None (String + IssueSeverity enum) | CLEAR | Direct use |
| `EnbValidationResultDto` | None (enums + String) | CLEAR | Direct use |
| `TomlConfigIssueDto` | None (String + TomlIssueSeverity enum) | CLEAR | Direct use |
| `WryeIssueDto` | None (String + WryeSeverity enum) | CLEAR | Direct use |
| `IntegrityCheckResultDto` | None (CheckType enum + bool + String) | CLEAR | Direct use |
| `ScanGameSetupDto` | None (u32 scalars + bool) | CLEAR | Direct use |
| `CrashgenReportSummaryDto` | None (flat scalars + String) | CLEAR | Direct use |
| `FcxIssueDto` | None (String fields only) | CLEAR | Direct use |
| `FormIdEntryDto` | None (String + bool) | CLEAR | Direct use |
| `XseInfoDto` | None (String + bool) | CLEAR | Direct use |
| `IniCheckResult` (path) | None (String + bool) | CLEAR | Direct use |
| `SuspectErrorRuleDto` | `main_error_contains_any: Vec<String>` | CLEAR — `Vec<String>` is valid inner type | Matches `YamlDataModSolutionCriteria` precedent |
| `SuspectStackCountRuleDto` | None (String + u32) | CLEAR | Direct use |
| `SuspectStackRuleDto` | 4 `Vec<String>` + `Vec<SuspectStackCountRuleDto>` | `SuspectStackCountRuleDto` has NO Vec — CLEAR at one extra level | Valid per CXX rules |
| `BA2Issues` (raw Rust) | 4 `Vec<String>` | CANNOT return `Vec<BA2Issues>` | D-06 split to per-category fns |
| `EnbValidationResult` (raw Rust) | `errors: Vec<String>` | `Vec<EnbValidationResult>` would be Pitfall 6 | Single-return DTO, no nesting |
| `CrashgenReport` (raw Rust) | `config_issues: Vec<TomlConfigIssue>` | `Vec<CrashgenReport>` would be Pitfall 6 | D-06 split to summary + issue-list |

---

## Clean-Build Cadence (D-10)

**Mandatory clean-build cycles for build.rs additions:**

| Plan | New file in build.rs | Clean build required |
|------|----------------------|---------------------|
| Plan adding `path.rs` | `src/path.rs` | YES — both cli + gui |
| Plan adding `constants.rs` | `src/constants.rs` | YES — both cli + gui |
| Plan adding `web.rs` | `src/web.rs` | YES — both cli + gui |
| Plan adding `xse.rs` (D-01) | `src/xse.rs` | YES — both cli + gui |
| Plan adding `version_registry.rs` (D-02) | `src/version_registry.rs` | YES — both cli + gui |

If `xse.rs` and `version_registry.rs` land in the same plan (both are splits from `game.rs`), they share one mandatory clean-build cycle — minimum 5 cycles if batched as above, or 4 if xse+version_registry are one plan.

**Plans that modify existing build.rs-listed files (incremental build only):**
- Widening `scangame.rs`, `config.rs`, `database.rs`, `scanner.rs` — incremental builds sufficient, NO clean required (unless a new shared struct conflicts with header order, which only affects NEW file additions).

---

## Baseline Refresh Cadence (D-09)

**Per-plan commit includes:**
1. Rust bridge source change
2. C++ consumer migration (if D-11)
3. `python tools/cxx_api_parity/check_parity_gate.py --update-baseline`
4. Commit: `docs/implementation/cxx_api_parity/baseline/parity_contract.json` + `cxx_diff_report.{json,md}` + `cxx_gate_report.md`

**Edge cases:**
- When `xse.rs` is added and `game.rs` XSE helpers are REMOVED, the baseline will show REMOVED entries from `game.rs` and ADDED entries in `xse.rs`. The gate's id-based comparison (sha256 of `rustSymbol:kind:bridgeModule`) will see both removals and additions as drift unless `--update-baseline` is run. This is expected and correct behavior — run `--update-baseline` after the move.
- Same applies for `version_registry.rs` split from `game.rs`.
- The `game.rs` shim approach (keep fn but delegate) avoids removals from the baseline — if the planner keeps shims, no baseline removals occur; just additions in the new files.

---

## Test Strategy (D-12)

**Default: Rust-side `#[cfg(test)] mod tests` in each bridge file.**

| Bridge file | Test approach | C++ Catch2 needed? |
|-------------|---------------|---------------------|
| `constants.rs` | Rust test: verify enum variant names, `must_not_be_none("Root_Folder_Game")` returns true | No — pure data, no C++ logic |
| `web.rs` | Rust test: `is_valid_url`, `get_user_agent`, `mod_site_base_url("NexusMods")` | No |
| `xse.rs` | Rust test: `xse_type_from_str`, `is_xse_installed_check` nonexistent path returns false | No |
| `version_registry.rs` | Move existing `game.rs` tests verbatim; add `version_registry_get_all_for_game` test | No |
| `path.rs` widening | Rust test: `validate_path` on CARGO_MANIFEST_DIR, `check_restricted_path` on system paths | No |
| `scangame.rs` widening | Rust test: `scangame_run_ba2_check` with nonexistent path returns 0 counts; `scangame_run_ini_check` with empty path returns empty vec | No |
| `config.rs` CXXS-07 | Rust test: verify `yaml_data_suspects_error_rules` returns empty vec when data has no rules | No |
| `database.rs` CXXS-05 | Rust test: `db_pool_get_entry_typed` before init returns `found: false` | No |
| `scanner.rs` CXXS-03 | Rust test: `get_fcx_config_issues()` after clean state returns empty vec | No |

**C++ Catch2 test candidates (only if Rust-side cannot cover):**
- `IssueSeverity`, `EnbResult`, `EnbConfigResult`, `CheckType`, `TomlIssueSeverity`, `WryeSeverity` enum exhaustiveness in C++ switch statements. If the GUI or CLI contains `switch (severity) { case IssueSeverity::Error: ... }` blocks, adding a new variant silently compiles without the new case unless C++ `-Wswitch` or equivalent is enabled. This is the one case where a C++ Catch2 test verifying all enum variants are handled could be valuable. **Defer per D-12 — only add if the planner identifies specific C++ switch blocks.**

---

## Plan Sequencing Recommendation

**Proposed 8-plan sequence with wave assignments:**

### Wave 1 — Foundation (plans 1-3, independent, can be sequenced)

**Plan 2-01: path.rs Promotion (CXXS-08, D-03)**
- Add `src/path.rs` to `build.rs::cxx_build::bridges`
- Add `path` module to `lib.rs`
- MANDATORY clean build: `build_cli.ps1 -Clean -Test` + `build_gui.ps1 -Clean -Test`
- Add `is_valid_path`, `is_restricted_path`, `validate_path_exists` to path.rs
- Widen path.rs with IniCheckResult, docs_checker, backup helpers
- Consumer migration: `pathdialog.cpp` adds `path.h` include + `classic::path::check_restricted_path()` call
- Commit: code + refreshed parity artifacts
- CXXS-08 complete.

**Plan 2-02: constants.rs New Module (CXXS-01, D-04)**
- Create `src/constants.rs` with `namespace = "classic::constants"`
- Expose `GameId` (4-variant enum), `Fallout4Version` (4-variant enum), `YamlFile` (enum TBD), `must_not_be_none`, `settings_ignore_none_contains`
- Add to `build.rs` + `lib.rs`
- MANDATORY clean build
- Commit + parity refresh
- CXXS-01 complete.

**Plan 2-03: web.rs New Module (CXXS-02, D-04)**
- Create `src/web.rs` with `namespace = "classic::web"`
- Expose `ModSite` (3-variant enum), `is_valid_url`, `validate_url_string`, `extract_domain`, `get_user_agent`, `get_user_agent_with_suffix`, `join_url`, `build_url_with_query` (keys+values parallel vecs), `mod_site_base_url`, `mod_site_name`, `mod_site_game_url`
- Add to `build.rs` + `lib.rs`
- MANDATORY clean build
- Commit + parity refresh
- CXXS-02 complete.

### Wave 2 — Splits (plan 4, one plan for both splits to minimize clean builds)

**Plan 2-04: xse.rs Split + version_registry.rs Split (CXXS-06, CXXS-09, D-01, D-02)**
- Create `src/xse.rs` — move XSE helpers from `game.rs`, add `XseType` enum, `XseInfoDto`, `xse_get_loader_name`, `xse_get_info`
- Create `src/version_registry.rs` — move version registry helpers from `game.rs`
- Leave compatibility shims in `game.rs` per D-08 (delegates to new namespaces) OR remove and update callers (planner decision)
- Add both to `build.rs` + `lib.rs`
- MANDATORY clean build (both files in same plan = 1 clean build cycle)
- Commit + parity refresh
- CXXS-06 + CXXS-09 complete.

### Wave 3 — Scangame Widening (plans 5-6)

**Plan 2-05: scangame.rs Widening Part 1 (CXXS-04 partial) — BA2, INI, ENB**
- Add `IssueSeverity`, `EnbResult`, `EnbConfigResult` CXX shared enums
- Add `IniConfigIssueDto`, `EnbValidationResultDto`, `Ba2IssuesSummaryDto`
- Add bridge fns: `scangame_run_ba2_check`, `scangame_get_ba2_*`, `scangame_run_ini_check`, `scangame_run_enb_check`
- D-11 consumer: Add a new `GameFilesController` or `GameFilesWorker` method that calls these fns (e.g., a per-archive BA2 check when user selects a BA2 file)
- Commit + parity refresh (incremental build — no new build.rs entries)

**Plan 2-06: scangame.rs Widening Part 2 (CXXS-04 complete) — TOML, Wrye, Integrity, Crashgen**
- Add `TomlIssueSeverity`, `WryeSeverity`, `CheckType` CXX shared enums
- Add `TomlConfigIssueDto`, `WryeIssueDto`, `IntegrityCheckResultDto`, `ScanGameSetupDto`, `CrashgenReportSummaryDto`
- Add bridge fns: `scangame_run_toml_check`, `scangame_run_wrye_check`, `scangame_run_integrity_check`, `scangame_run_setup_structured`, `scangame_run_crashgen_check`, `scangame_get_crashgen_issues`
- D-11 consumer: Add calls in `GameFilesWorker` or `GameFilesController` for at least one new fn
- Commit + parity refresh

### Wave 4 — Data Surfaces (plans 7-8)

**Plan 2-07: config.rs CXXS-07 + database.rs CXXS-05**
- Add `SuspectErrorRuleDto`, `SuspectStackCountRuleDto`, `SuspectStackRuleDto` to `config.rs`
- Add `yaml_data_suspects_error_rules`, `yaml_data_suspects_stack_rules` bridge fns
- Add `FormIdEntryDto` to `database.rs`
- Add `db_pool_get_entry_typed`, `db_pool_get_entries_batch_typed` bridge fns
- D-11 consumer: Add one call site in CLI or GUI consuming the new typed DB API
- Commit + parity refresh
- CXXS-05 + CXXS-07 complete.

**Plan 2-08: scanner.rs FCX Getter (CXXS-03) + Final Verification**
- Add `FcxIssueDto` shared struct to `scanner.rs`
- Add `get_fcx_config_issues() -> Vec<FcxIssueDto>` bridge fn (reads `GLOBAL_FCX_HANDLER`)
- D-11 consumer: Add a `get_fcx_config_issues()` call in the GUI's FCX mode result display OR in the CLI's post-scan summary
- Run full `build_cli.ps1 -Test` + `build_gui.ps1 -Test` (final CXXS-10 proof)
- Commit + parity refresh
- CXXS-03 + CXXS-10 complete.

---

## Architecture Patterns

### Pattern: New Bridge File

```rust
// src/constants.rs
use classic_constants_core::{GameId, Fallout4Version, must_not_be_none};

fn game_id_as_str(id: ffi::GameId) -> String { ... }
fn must_not_be_none_key(key: &str) -> bool { must_not_be_none(key) }

#[cxx::bridge(namespace = "classic::constants")]
mod ffi {
    #[repr(u8)]
    enum GameId { Fallout4 = 0, Fallout4VR = 1, Skyrim = 2, Starfield = 3 }

    #[repr(u8)]
    enum Fallout4Version { Original = 0, NextGen = 1, AnniversaryEdition = 2, Vr = 3 }

    extern "Rust" {
        fn game_id_as_str(id: GameId) -> String;
        fn must_not_be_none_key(key: &str) -> bool;
    }
}
```

### Pattern: Split Migration (game.rs shim)

```rust
// game.rs — shim delegates to new module after D-01
// Keep at same location for D-08 backward compat
// Bridge fn in classic::game stays; internally delegates

fn detect_xse_version_string(exe_path: &str, xse_type_str: &str) -> String {
    crate::xse::detect_xse_version_string_impl(exe_path, xse_type_str)
}
```

### Pattern: `build_url_with_query` key/value parallel vectors

```rust
// web.rs
fn web_build_url_with_query(base: &str, keys: &[String], values: &[String]) -> Result<String, String> {
    let params: Vec<(&str, &str)> = keys.iter().zip(values.iter())
        .map(|(k, v)| (k.as_str(), v.as_str())).collect();
    classic_web_core::build_url_with_query(base, &params)
        .map_err(|e| format!("{e}"))
}
```

### Pattern: per-plan parity refresh

```bash
# Run after every bridge surface change, before commit
python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
# Verify gate is green
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
# Stage and commit together with code
```

---

## Environment Availability

Step 2.6: SKIPPED (no new external tool dependencies). All Phase 2 work uses existing MSVC toolchain, PowerShell wrappers, and Python gate scripts established in Phase 1.

**Required tools (pre-existing):**
- `VCPKG_ROOT` — required for C++ builds; must be set
- Visual Studio MSVC toolchain — required for clean builds
- Python (for parity gate) — already operational from Phase 1
- `pwsh` for build wrappers — pre-existing

---

## Validation Architecture

**nyquist_validation: enabled (absent from config = treat as enabled)**

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `cargo test` (Rust, primary) + `build_cli.ps1 -Test` / `build_gui.ps1 -Test` (C++) |
| Config file | `ClassicLib-rs/Cargo.toml` (Rust workspace) |
| Quick run command | `cargo test --manifest-path ClassicLib-rs/Cargo.toml -p classic-cpp-bridge` |
| Full suite command | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` |
| C++ test command | `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CXXS-01 | `game_id_as_str(GameId::Fallout4)` returns "Fallout4" | unit | `cargo test -p classic-cpp-bridge constants` | Wave 0 — create `src/constants.rs` with `#[cfg(test)]` block |
| CXXS-02 | `is_valid_url("https://nexusmods.com")` returns true | unit | `cargo test -p classic-cpp-bridge web` | Wave 0 — create `src/web.rs` |
| CXXS-03 | `get_fcx_config_issues()` after clean global state returns empty vec | unit | `cargo test -p classic-cpp-bridge scanner::tests::test_get_fcx_config_issues_empty` | ❌ Wave 0 |
| CXXS-04 | `scangame_run_ba2_check(nonexistent) -> has_issues=false, counts=0` | unit | `cargo test -p classic-cpp-bridge scangame` | ❌ Wave 0 |
| CXXS-05 | `db_pool_get_entry_typed` before init returns `found: false` | unit | `cargo test -p classic-cpp-bridge database` | ✅ (extend existing) |
| CXXS-06 | `version_registry_get_all_for_game("Fallout4", false)` returns 3+ entries | unit | `cargo test -p classic-cpp-bridge version_registry` | Wave 0 — new file |
| CXXS-07 | `yaml_data_suspects_error_rules` on loaded data returns non-empty with correct severity | unit | `cargo test -p classic-cpp-bridge config::tests::test_suspects_error_rules` | ❌ Wave 0 |
| CXXS-08 | `validate_path(CARGO_MANIFEST_DIR)` returns true | unit | `cargo test -p classic-cpp-bridge path` | ✅ (extend existing) |
| CXXS-09 | `xse_get_loader_name(XseType::F4SE)` returns "f4se_loader.exe" | unit | `cargo test -p classic-cpp-bridge xse` | Wave 0 — new file |
| CXXS-10 | `build_cli.ps1 -Test` and `build_gui.ps1 -Test` pass with widened bridge | C++ build | `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Clean -Test` | ✅ (pre-existing CI) |
| CXXS-10 | Parity gate 0 drift | gate check | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` | ✅ (Phase 1 created) |
| CXXS-10 | At least 1 production C++ caller per new bridge fn | code review | Manual per D-11 | Enumerated above |

### Sampling Rate
- **Per task commit:** `cargo test --manifest-path ClassicLib-rs/Cargo.toml -p classic-cpp-bridge`
- **Per wave merge:** `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`
- **Phase gate:** Full suite green + `build_cli.ps1 -Clean -Test` + `build_gui.ps1 -Clean -Test` before `/gsd:verify-work`

### Wave 0 Gaps (tests that do not yet exist)

- [ ] `src/constants.rs` with `#[cfg(test)] mod tests` block — covers CXXS-01
- [ ] `src/web.rs` with `#[cfg(test)] mod tests` block — covers CXXS-02
- [ ] `src/xse.rs` with `#[cfg(test)] mod tests` block — covers CXXS-09
- [ ] `src/version_registry.rs` with `#[cfg(test)] mod tests` block — covers CXXS-06
- [ ] `scanner.rs::test_get_fcx_config_issues_empty` — covers CXXS-03
- [ ] `config.rs::test_suspects_error_rules` — covers CXXS-07 (new DTO path)
- [ ] `scangame.rs` extended tests for new BA2/INI/ENB/TOML/Wrye fns — covers CXXS-04

*(These tests are created in Wave 0 of each plan, before implementation, per D-12 Rust-first pattern.)*

---

## Common Pitfalls

### Pitfall 5: CXX Header Generation Order (D-10)

**What goes wrong:** Adding a new `pub mod` to `lib.rs` and relying on incremental builds — MSVC sees "incomplete type" on the first use of a new shared struct in an existing generated header.

**Prevention:** `build_cli.ps1 -Clean -Test` + `build_gui.ps1 -Clean -Test` after every `build.rs` list addition (5 mandatory cycles minimum in Phase 2).

**Warning signs:** MSVC error `C2027: use of undefined type` in a pre-existing `.cpp` file.

### Pitfall 6: `rust::Vec<T>` ABI Restriction

**What goes wrong:** A shared struct containing `Vec<StructThatHasVec>` fails at `cargo build` with opaque CXX trait error.

**Prevention:** All DTOs verified against the max-nesting rule. `Vec<String>` inside a shared struct is valid. `Vec<StructWithVec>` is not. All Phase 2 DTOs verified above.

### game.rs Split Compatibility

**What goes wrong:** Moving fns from `game.rs` to `xse.rs`/`version_registry.rs` changes the C++ namespace from `classic::game::*` to `classic::xse::*` / `classic::version_registry::*`, breaking existing C++ callers.

**Prevention per D-08:** Keep shims in `game.rs` that delegate. Both `pathdialog.cpp` (uses `classic::game::check_restricted_path`) and any other `game.h` consumers continue to compile. New code uses the correct namespace.

### `build.rs` Order Matters for Shared Enums

**What goes wrong:** `web.rs` uses `GameId` enum declared in `constants.rs`. If `constants.rs` is listed after `web.rs` in `build.rs`, the generated headers may have forward-declaration order issues.

**Prevention:** List `constants.rs` before `web.rs` in `build.rs` bridges array. This ensures `GameId` is defined before `web.rs` generated headers reference it. However — since each bridge module gets its own generated header and they don't directly `#include` each other, this may not be a problem in practice. The safer approach is to use string discriminants for cross-module enum references (already resolved above via `mod_site_game_url(site_name: &str, game_id_str: &str)` pattern).

---

## Open Questions

1. **YamlFile enum variant names (constants.rs CXXS-01)**
   - What we know: `YamlFile` is mentioned in CONTEXT.md canonical refs but not directly read
   - What's unclear: Exact variants of `YamlFile` enum (Settings, Main, Game, Ignore?)
   - Recommendation: Read `ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs` lines 400-600 before writing the constants.rs plan

2. **path.rs + mainwindow.cpp include resolution**
   - What we know: `mainwindow.cpp` includes `"classic_cxx_bridge/path.h"` and calls `classic::path::detect_fallout4_game_path()`; `path.rs` is NOT in `build.rs`
   - What's unclear: How the GUI currently builds with this include if path.h is not generated
   - Recommendation: The planner should verify with a build before Plan 2-01. The path.rs functions may have been added to path.rs but not to build.rs intentionally (as a Phase 2 setup). Adding path.rs to build.rs in Plan 2-01 is the first and most critical action.

3. **CXXS-04 scope: which scangame sub-domains are "used by Python/Node bindings"?**
   - What we know: CXXS-04 says "orchestration entry points used by Python/Node bindings"
   - What's unclear: Exactly which of ba2/ini/enb/toml/wrye/unpacked/integrity/logs/mod_ini/orchestrator/setup/crashgen_orchestrator/game_report are exposed in Python and Node
   - Recommendation: Check `ClassicLib-rs/python-bindings/` and `ClassicLib-rs/node-bindings/classic-node/src/` for scangame exposure before finalizing scangame plan scope. Modules not exposed in Python/Node may not need C++ bridge entry points.

4. **ModSite game_url cross-module enum reference**
   - What we know: `ModSite::game_url(GameId)` takes `classic_constants_core::GameId`; bridging this across module boundaries requires either shared CXX enum or string-based dispatch
   - What's unclear: Whether CXX allows a shared enum declared in one bridge to be referenced by another bridge's extern "Rust" fn signature
   - Recommendation: Use string-based dispatch (`mod_site_game_url(site_name: &str, game_id_str: &str)`) to avoid the cross-module enum reference issue entirely. This is the safe default.

---

## Sources

### Primary (HIGH confidence)
- Direct read: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs` — current 2-fn surface confirmed
- Direct read: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` — full XSE/version-registry/path surface confirmed
- Direct read: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` — 3 fns, NOT in build.rs confirmed
- Direct read: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` — tab-delimited gap confirmed
- Direct read: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` — suspect-stack gap confirmed
- Direct read: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` — fcx_reset but no get_fcx confirmed
- Direct read: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` — 14-file list confirmed
- Direct read: `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs` — full ModSite/URL surface
- Direct read: `ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs` — full XseType/XseInfo surface
- Direct read: `ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs` (partial) — GameId/Fallout4Version/NULL_VERSION/SETTINGS_IGNORE_NONE confirmed
- Direct read: `ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs` (struct defs) — SuspectErrorRule/SuspectStackRule field sets confirmed
- Direct read: `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs` (partial) — ConfigIssue 7-field struct confirmed
- Direct read: `ClassicLib-rs/business-logic/classic-scangame-core/src/` (all pub struct/enum) — complete sub-domain type inventory
- Direct read: `classic-gui/src/app/pathdialog.cpp` — D-11 call-site confirmed (check_restricted_path)
- Direct read: `classic-gui/src/app/mainwindow.cpp` (partial) — path.h include + path fn calls confirmed
- Direct read: `classic-gui/src/workers/gamefilesworker.cpp` — run_setup_checks caller confirmed
- Direct read: `classic-cli/src/scanner.cpp` — no D-11-qualifying hand-rolled logic confirmed
- Direct read: `.planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md` — all locked decisions
- Direct read: `.planning/REQUIREMENTS.md` — CXXS-01..10 full text
- Direct read: `.planning/research/PITFALLS.md` — Pitfall 5, 6, 7 full text

### Secondary (MEDIUM confidence)
- `.planning/ROADMAP.md` Phase 2 success criteria — success critera confirmed
- `.planning/STATE.md` — Phase 1 complete, Phase 2 pending

---

## Metadata

**Confidence breakdown:**
- Current bridge surface inventory: HIGH — direct file reads, no speculation
- Target Rust crate surface: HIGH — direct source reads
- D-11 call-site migration: HIGH — direct C++ source reads
- Pitfall 6 DTO analysis: HIGH — each DTO individually verified
- Plan sequence: MEDIUM — sequencing is a recommendation; planner may restructure
- YamlFile enum variants: LOW — not directly read (open question #1)
- scangame Python/Node scope: MEDIUM — CXXS-04 wording implies "all", but parity check is open question #3

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable codebase — Rust crate APIs change slowly; C++ frontend structure stable)
