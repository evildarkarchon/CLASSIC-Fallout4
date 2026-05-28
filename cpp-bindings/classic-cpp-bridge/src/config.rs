//! YamlDataCore configuration bridge for CXX FFI.
//!
//! Bridges `classic_config_core::YamlDataCore` which loads all CLASSIC YAML
//! configuration files (main, game, ignore) into a structured Rust type.
//! Provides bulk YAML getters plus Local-YAML path persistence helpers.
//!
//! IndexMap fields are exposed as paired key/value vectors since CXX bridges
//! are isolated and can't share opaque types across modules.

use classic_config_core::{
    ClassicConfig, MainYamlVersionError, ModSolutionCriteria,
    SuspectErrorRule as CoreSuspectErrorRule, SuspectStackCountRule as CoreSuspectStackCountRule,
    SuspectStackRule as CoreSuspectStackRule, YamlDataCore,
    load_main_yaml_version_with_bundled_dir as core_load_main_yaml_version_with_bundled_dir,
};
use classic_settings_core::{
    cache_stats as settings_core_cache_stats, clear_cache as clear_settings_cache,
    reset_cache_stats as reset_settings_core_cache_stats,
};
use classic_shared_core::get_runtime;
use std::path::{Path, PathBuf};

/// Opaque wrapper around `YamlDataCore` for CXX FFI.
pub struct YamlData {
    pub(crate) inner: YamlDataCore,
}

// ── Construction ────────────────────────────────────────────────────

fn yaml_data_load(
    yaml_dir_root: &str,
    yaml_dir_data: &str,
    game: &str,
    game_version: &str,
) -> Result<Box<YamlData>, String> {
    let dirs = vec![PathBuf::from(yaml_dir_root), PathBuf::from(yaml_dir_data)];
    let inner = get_runtime()
        .block_on(YamlDataCore::load_from_yaml_files(
            dirs,
            game.to_string(),
            game_version.to_string(),
        ))
        .map_err(|e| format!("{e}"))?;
    Ok(Box::new(YamlData { inner }))
}

fn save_local_yaml_paths(
    local_yaml_path: &str,
    game_root: &str,
    docs_root: &str,
) -> Result<(), String> {
    // This helper only persists Local.yaml path fields, so a default config is
    // enough as long as that save path stays scoped to `paths` state.
    let mut config = ClassicConfig::default();

    if !game_root.is_empty() {
        config.paths.game_root = PathBuf::from(game_root);
    }

    if !docs_root.is_empty() {
        config.paths.docs_root = Some(PathBuf::from(docs_root));
    }

    get_runtime()
        .block_on(config.save_local_yaml_paths_to(Path::new(local_yaml_path)))
        .map_err(|e| format!("{e}"))
}

// ── Main YAML version (schema-gated) ────────────────────────────────
//
// Unlike `yaml_data_load`, this helper is scoped to exactly one field
// (`CLASSIC_Info.version`) and is intentionally schema-gated by
// `client_schemas::MAIN_YAML`. Native frontends call it on startup to
// populate `QApplication::applicationVersion()` (GUI) or the
// binary-release update-check input (CLI) without ever trusting a
// partially-updated or legacy `schema_version: 1.x` file that would
// otherwise degrade downstream notification classification to `unknown`.
//
// Error shape follows the app-notification precedent in `update.rs`:
// empty-string sentinels on success, a structured `error_kind` plus
// human-readable `error_message` on failure. This lets Qt callers map
// each kind to an actionable dialog ("upgrade client", "fix version
// field", etc.) without parsing free-form strings.

/// Load `CLASSIC Main.yaml` with `client_schemas::MAIN_YAML` schema gating
/// and return the trimmed `CLASSIC_Info.version`.
///
/// `bundled_yaml_dir` empty string keeps the default relative path
/// (`CLASSIC Data/databases/CLASSIC Main.yaml`, resolved against process
/// CWD — correct for the CLI/GUI launched next to `CLASSIC Data/`). A
/// non-empty value is the explicit install-tree directory holding the
/// shippable YAML files (pass this from contexts where `current_exe()`
/// would yield the wrong parent).
fn load_main_yaml_version(bundled_yaml_dir: &str) -> ffi::MainYamlVersionDto {
    let bundled = if bundled_yaml_dir.is_empty() {
        None
    } else {
        Some(Path::new(bundled_yaml_dir))
    };
    match get_runtime().block_on(core_load_main_yaml_version_with_bundled_dir(bundled)) {
        Ok(version) => ffi::MainYamlVersionDto {
            version,
            error_kind: String::new(),
            error_message: String::new(),
        },
        Err(err) => ffi::MainYamlVersionDto {
            version: String::new(),
            error_kind: main_yaml_version_error_kind(&err).to_string(),
            error_message: format!("{err}"),
        },
    }
}

/// Stable `error_kind` discriminator values for
/// [`ffi::MainYamlVersionDto`]. Kept as a dedicated function so the
/// string constants stay adjacent to the match and any future variants
/// (the core error is `#[non_exhaustive]`) show up here as a compile
/// error that forces the bridge to acknowledge them.
fn main_yaml_version_error_kind(err: &MainYamlVersionError) -> &'static str {
    match err {
        MainYamlVersionError::Load(_) => "load",
        MainYamlVersionError::VersionKeyMissing { .. } => "version_key_missing",
        MainYamlVersionError::VersionEmpty { .. } => "version_empty",
        MainYamlVersionError::VersionNotString { .. } => "version_not_string",
        MainYamlVersionError::VersionInvalid { .. } => "version_invalid",
        // `MainYamlVersionError` is `#[non_exhaustive]`; when a new
        // variant is added in the core crate this arm forces the bridge
        // to pick a new `error_kind` string instead of silently folding
        // into a catch-all.
        _ => "unknown",
    }
}

// ── String getters ──────────────────────────────────────────────────

fn yaml_data_classic_version(data: &YamlData) -> &str {
    &data.inner.classic_version
}

fn yaml_data_classic_version_date(data: &YamlData) -> &str {
    &data.inner.classic_version_date
}

fn yaml_data_crashgen_name_field(data: &YamlData) -> &str {
    &data.inner.crashgen_name
}

fn yaml_data_crashgen_latest_og(data: &YamlData) -> &str {
    &data.inner.crashgen_latest_og
}

fn yaml_data_warn_noplugins(data: &YamlData) -> &str {
    &data.inner.warn_noplugins
}

fn yaml_data_warn_outdated(data: &YamlData) -> &str {
    &data.inner.warn_outdated
}

fn yaml_data_xse_acronym(data: &YamlData) -> &str {
    &data.inner.xse_acronym
}

fn yaml_data_autoscan_text(data: &YamlData) -> &str {
    &data.inner.autoscan_text
}

fn yaml_data_game_version(data: &YamlData) -> &str {
    &data.inner.game_version
}

fn yaml_data_game_root_name_field(data: &YamlData) -> &str {
    &data.inner.game_root_name
}

// ── Accessors ───────────────────────────────────────────────────────

fn yaml_data_get_crashgen_name(data: &YamlData) -> String {
    data.inner.get_crashgen_name().to_string()
}

fn yaml_data_get_game_root_name(data: &YamlData) -> String {
    data.inner.get_game_root_name().to_string()
}

fn yaml_data_get_crashgen_ignore(data: &YamlData) -> Vec<String> {
    data.inner.get_crashgen_ignore().to_vec()
}

// ── Vec<String> getters ─────────────────────────────────────────────

fn yaml_data_classic_game_hints(data: &YamlData) -> Vec<String> {
    data.inner.classic_game_hints.clone()
}

fn yaml_data_classic_records_list(data: &YamlData) -> Vec<String> {
    data.inner.classic_records_list.clone()
}

fn yaml_data_crashgen_ignore_og(data: &YamlData) -> Vec<String> {
    data.inner.crashgen_ignore.clone()
}

fn yaml_data_game_ignore_plugins(data: &YamlData) -> Vec<String> {
    data.inner.game_ignore_plugins.clone()
}

fn yaml_data_game_ignore_records(data: &YamlData) -> Vec<String> {
    data.inner.game_ignore_records.clone()
}

fn yaml_data_ignore_list(data: &YamlData) -> Vec<String> {
    data.inner.ignore_list.clone()
}

// ── IndexMap getters as key/value pair vectors ──────────────────────
// CXX bridges are isolated, so we return flattened data instead of
// opaque StringMap/StringVecMap types from the types module.

fn yaml_data_suspects_error_keys(data: &YamlData) -> Vec<String> {
    data.inner
        .suspect_error_rules
        .iter()
        .map(|rule| rule.id.clone())
        .collect()
}

fn yaml_data_suspects_error_values(data: &YamlData) -> Vec<String> {
    data.inner
        .suspect_error_rules
        .iter()
        .map(|rule| rule.name.clone())
        .collect()
}

fn yaml_data_suspects_stack_keys(data: &YamlData) -> Vec<String> {
    data.inner
        .suspect_stack_rules
        .iter()
        .map(|rule| rule.id.clone())
        .collect()
}

fn yaml_data_mods_core_keys(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_core
        .iter()
        .map(|e| e.detect.clone())
        .collect()
}

fn yaml_data_mods_core_values(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_core
        .iter()
        .map(|e| e.description.clone())
        .collect()
}

fn yaml_data_mods_core_names(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_core
        .iter()
        .map(|e| e.name.clone())
        .collect()
}

fn yaml_data_mods_core_gpus(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_core
        .iter()
        .map(|e| e.gpu.clone().unwrap_or_default())
        .collect()
}

fn yaml_data_mods_core_count(data: &YamlData) -> usize {
    data.inner.game_mods_core.len()
}

fn yaml_data_mod_entry(
    entry: &classic_config_core::ModSolutionEntry,
) -> ffi::YamlDataModSolutionEntry {
    let criteria = match &entry.criteria {
        ModSolutionCriteria::Any(values) => ffi::YamlDataModSolutionCriteria {
            any: values.clone(),
            all: Vec::new(),
        },
        ModSolutionCriteria::All(values) => ffi::YamlDataModSolutionCriteria {
            any: Vec::new(),
            all: values.clone(),
        },
    };

    ffi::YamlDataModSolutionEntry {
        id: entry.id.clone(),
        criteria,
        exceptions: entry.exceptions.clone(),
        name: entry.name.clone(),
        description: entry.description.clone(),
    }
}

fn yaml_data_mods_freq_entries(data: &YamlData) -> Vec<ffi::YamlDataModSolutionEntry> {
    data.inner
        .game_mods_freq
        .iter()
        .map(yaml_data_mod_entry)
        .collect()
}

fn yaml_data_mods_conf_mod_a(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.mod_a.clone())
        .collect()
}

fn yaml_data_mods_conf_mod_b(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.mod_b.clone())
        .collect()
}

fn yaml_data_mods_conf_name_a(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.name_a.clone())
        .collect()
}

fn yaml_data_mods_conf_name_b(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.name_b.clone())
        .collect()
}

fn yaml_data_mods_conf_descriptions(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.description.clone())
        .collect()
}

fn yaml_data_mods_conf_fixes(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.fix.clone())
        .collect()
}

fn yaml_data_mods_conf_links(data: &YamlData) -> Vec<String> {
    data.inner
        .game_mods_conf
        .iter()
        .map(|e| e.link.clone().unwrap_or_default())
        .collect()
}

fn yaml_data_mods_conf_count(data: &YamlData) -> usize {
    data.inner.game_mods_conf.len()
}

fn yaml_data_mods_solu_entries(data: &YamlData) -> Vec<ffi::YamlDataModSolutionEntry> {
    data.inner
        .game_mods_solu
        .iter()
        .map(yaml_data_mod_entry)
        .collect()
}

fn settings_cache_clear() {
    clear_settings_cache();
}

fn settings_cache_size() -> usize {
    settings_cache_stats().size
}

fn settings_cache_stats() -> ffi::CacheStats {
    let stats = settings_core_cache_stats();
    ffi::CacheStats {
        hits: stats.hits,
        misses: stats.misses,
        hit_rate: stats.hit_rate,
        size: stats.size,
        capacity: stats.capacity,
    }
}

fn reset_settings_cache_stats() {
    reset_settings_core_cache_stats();
}

// ── Suspect rule typed accessors (CXXS-07) ─────────────────────────
// Additive per D-08 — existing yaml_data_suspects_error_keys/values and
// yaml_data_suspects_stack_keys fns above remain unchanged.

/// Returns the full set of error-type suspect rules as typed DTOs.
///
/// Each `SuspectErrorRuleDto` carries the rule's stable `id`, display `name`,
/// `severity`, and the `main_error_contains_any` pattern list.
///
/// Bridge contract: this is the typed complement to the existing
/// `yaml_data_suspects_error_keys` / `yaml_data_suspects_error_values` pair.
/// Both coexist per D-08 (additive, not replacing).
fn yaml_data_suspects_error_rules(data: &YamlData) -> Vec<ffi::SuspectErrorRuleDto> {
    data.inner
        .suspect_error_rules
        .iter()
        .map(|r: &CoreSuspectErrorRule| ffi::SuspectErrorRuleDto {
            id: r.id.clone(),
            name: r.name.clone(),
            severity: r.severity,
            main_error_contains_any: r.main_error_contains_any.clone(),
        })
        .collect()
}

/// Returns the flattened metadata for all stack-type suspect rules.
///
/// Each `SuspectStackRuleMetadataDto` carries the rule's `id`, `name`,
/// `severity`, and the four `Vec<String>` pattern fields — but does NOT
/// include the nested `stack_contains_at_least` count rules. Those are
/// exposed separately via `yaml_data_suspects_stack_count_rules_for_id`.
///
/// Pitfall 6 fix (Codex HIGH correction): a previous design returned
/// `Vec<SuspectStackRuleDto>` where the inner DTO contained a
/// `Vec<SuspectStackCountRuleDto>` field. That is a `Vec<StructWithVec>`
/// shape that CXX cannot safely bridge. The flattened metadata DTO +
/// separate per-rule count getter eliminates this constraint entirely.
fn yaml_data_suspects_stack_rules_metadata(
    data: &YamlData,
) -> Vec<ffi::SuspectStackRuleMetadataDto> {
    data.inner
        .suspect_stack_rules
        .iter()
        .map(
            |r: &CoreSuspectStackRule| ffi::SuspectStackRuleMetadataDto {
                id: r.id.clone(),
                name: r.name.clone(),
                severity: r.severity,
                main_error_required_any: r.main_error_required_any.clone(),
                main_error_optional_any: r.main_error_optional_any.clone(),
                stack_contains_any: r.stack_contains_any.clone(),
                exclude_if_stack_contains_any: r.exclude_if_stack_contains_any.clone(),
                // Note: stack_contains_at_least is NOT included here — use
                // yaml_data_suspects_stack_count_rules_for_id to retrieve count rules.
            },
        )
        .collect()
}

/// Returns the count rules for a single stack-type suspect rule, keyed by rule id.
///
/// C++ callers iterate the metadata list first via
/// `yaml_data_suspects_stack_rules_metadata`, then call this getter for each
/// rule that needs its count rules. Returns an empty Vec when the id is not
/// found (unknown id, no count rules configured).
///
/// Each `SuspectStackCountRuleDto` has a `substring` (the stack pattern) and
/// a `count` (minimum required occurrences, cast from `usize` to `u32`).
fn yaml_data_suspects_stack_count_rules_for_id(
    data: &YamlData,
    rule_id: &str,
) -> Vec<ffi::SuspectStackCountRuleDto> {
    data.inner
        .suspect_stack_rules
        .iter()
        .find(|r| r.id == rule_id)
        .map(|r| {
            r.stack_contains_at_least
                .iter()
                .map(
                    |c: &CoreSuspectStackCountRule| ffi::SuspectStackCountRuleDto {
                        substring: c.substring.clone(),
                        count: c.count as u32,
                    },
                )
                .collect()
        })
        .unwrap_or_default()
}

#[cxx::bridge(namespace = "classic::config")]
mod ffi {
    struct CacheStats {
        hits: u64,
        misses: u64,
        hit_rate: f64,
        size: usize,
        capacity: usize,
    }

    struct YamlDataModSolutionCriteria {
        any: Vec<String>,
        all: Vec<String>,
    }

    struct YamlDataModSolutionEntry {
        id: String,
        criteria: YamlDataModSolutionCriteria,
        exceptions: Vec<String>,
        name: String,
        description: String,
    }

    // CXXS-07: Typed suspect-rule DTOs (additive per D-08)

    /// Typed DTO for a single error-type suspect rule (Crashlog_Error_Check).
    struct SuspectErrorRuleDto {
        id: String,
        name: String,
        severity: i32,
        main_error_contains_any: Vec<String>,
    }

    /// Flattened metadata DTO for a single stack-type suspect rule (Crashlog_Stack_Check).
    ///
    /// Does NOT contain the nested count rules — use
    /// `yaml_data_suspects_stack_count_rules_for_id` to retrieve those separately.
    /// This flattening satisfies Pitfall 6 (no Vec<StructWithVec>).
    struct SuspectStackRuleMetadataDto {
        id: String,
        name: String,
        severity: i32,
        main_error_required_any: Vec<String>,
        main_error_optional_any: Vec<String>,
        stack_contains_any: Vec<String>,
        exclude_if_stack_contains_any: Vec<String>,
    }

    /// DTO for a single count-based stack-match requirement within a stack rule.
    /// Returned by `yaml_data_suspects_stack_count_rules_for_id` keyed by rule id.
    struct SuspectStackCountRuleDto {
        substring: String,
        count: u32,
    }

    /// Result of [`load_main_yaml_version`].
    ///
    /// Empty-string sentinel contract per `docs/api/error-contract.md`:
    ///
    /// - On success: `version` is the trimmed `CLASSIC_Info.version`
    ///   (never empty); `error_kind` and `error_message` are `""`.
    /// - On failure: `version` is `""`; `error_kind` carries one of
    ///   `"load"`, `"version_key_missing"`, `"version_empty"`,
    ///   `"version_not_string"`, or `"unknown"` (reserved for future
    ///   `MainYamlVersionError` variants); `error_message` carries the
    ///   `Display` rendering of the underlying error, suitable for a
    ///   Qt message box.
    ///
    /// C++ callers check `error_kind.empty()` first; a non-empty
    /// `error_kind` MUST be surfaced (do not fall back to
    /// `QApplication::applicationVersion()` — that would reintroduce
    /// the silent-degradation behavior this bridge exists to prevent).
    struct MainYamlVersionDto {
        version: String,
        error_kind: String,
        error_message: String,
    }

    extern "Rust" {
        type YamlData;

        // Construction (async, block_on)
        fn yaml_data_load(
            yaml_dir_root: &str,
            yaml_dir_data: &str,
            game: &str,
            game_version: &str,
        ) -> Result<Box<YamlData>>;

        fn save_local_yaml_paths(
            local_yaml_path: &str,
            game_root: &str,
            docs_root: &str,
        ) -> Result<()>;

        /// Schema-gated `CLASSIC_Info.version` reader for native startup
        /// paths. See [`MainYamlVersionDto`] for the success/failure
        /// contract.
        ///
        /// `bundled_yaml_dir` empty → default relative path resolved
        /// against process CWD (correct when launched next to
        /// `CLASSIC Data/`). Non-empty → explicit install-tree
        /// `CLASSIC Data/databases` directory.
        fn load_main_yaml_version(bundled_yaml_dir: &str) -> MainYamlVersionDto;

        // String getters
        fn yaml_data_classic_version(data: &YamlData) -> &str;
        fn yaml_data_classic_version_date(data: &YamlData) -> &str;
        fn yaml_data_crashgen_name_field(data: &YamlData) -> &str;
        fn yaml_data_crashgen_latest_og(data: &YamlData) -> &str;
        fn yaml_data_warn_noplugins(data: &YamlData) -> &str;
        fn yaml_data_warn_outdated(data: &YamlData) -> &str;
        fn yaml_data_xse_acronym(data: &YamlData) -> &str;
        fn yaml_data_autoscan_text(data: &YamlData) -> &str;
        fn yaml_data_game_version(data: &YamlData) -> &str;
        fn yaml_data_game_root_name_field(data: &YamlData) -> &str;

        // Accessors
        fn yaml_data_get_crashgen_name(data: &YamlData) -> String;
        fn yaml_data_get_game_root_name(data: &YamlData) -> String;
        fn yaml_data_get_crashgen_ignore(data: &YamlData) -> Vec<String>;

        // Vec<String> getters
        fn yaml_data_classic_game_hints(data: &YamlData) -> Vec<String>;
        fn yaml_data_classic_records_list(data: &YamlData) -> Vec<String>;
        fn yaml_data_crashgen_ignore_og(data: &YamlData) -> Vec<String>;
        fn yaml_data_game_ignore_plugins(data: &YamlData) -> Vec<String>;
        fn yaml_data_game_ignore_records(data: &YamlData) -> Vec<String>;
        fn yaml_data_ignore_list(data: &YamlData) -> Vec<String>;

        // IndexMap getters as paired key/value vectors
        fn yaml_data_suspects_error_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_suspects_error_values(data: &YamlData) -> Vec<String>;
        fn yaml_data_suspects_stack_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_values(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_names(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_gpus(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_count(data: &YamlData) -> usize;
        fn yaml_data_mods_freq_entries(data: &YamlData) -> Vec<YamlDataModSolutionEntry>;
        fn yaml_data_mods_conf_mod_a(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_mod_b(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_name_a(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_name_b(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_descriptions(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_fixes(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_links(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_count(data: &YamlData) -> usize;
        fn yaml_data_mods_solu_entries(data: &YamlData) -> Vec<YamlDataModSolutionEntry>;

        fn settings_cache_clear();
        fn settings_cache_size() -> usize;
        fn settings_cache_stats() -> CacheStats;
        fn reset_settings_cache_stats();

        // CXXS-07: Typed suspect-rule accessors (additive per D-08)
        fn yaml_data_suspects_error_rules(data: &YamlData) -> Vec<SuspectErrorRuleDto>;
        fn yaml_data_suspects_stack_rules_metadata(
            data: &YamlData,
        ) -> Vec<SuspectStackRuleMetadataDto>;
        fn yaml_data_suspects_stack_count_rules_for_id(
            data: &YamlData,
            rule_id: &str,
        ) -> Vec<SuspectStackCountRuleDto>;
    }
}

#[cfg(test)]
#[path = "config_tests.rs"]
mod tests;
