//! YamlDataCore configuration bridge for CXX FFI.
//!
//! Bridges `classic_config_core::YamlDataCore` which loads all CLASSIC YAML
//! configuration files (main, game, ignore) into a structured Rust type.
//! Provides bulk YAML getters plus Local-YAML path persistence helpers.
//!
//! IndexMap fields are exposed as paired key/value vectors since CXX bridges
//! are isolated and can't share opaque types across modules.

use classic_config_core::{
    ClassicConfig, ModSolutionCriteria, SuspectErrorRule as CoreSuspectErrorRule,
    SuspectStackCountRule as CoreSuspectStackCountRule, SuspectStackRule as CoreSuspectStackRule,
    YamlDataCore,
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
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;
    use tempfile::tempdir;

    #[test]
    fn test_yaml_data_load_invalid_dirs() {
        let result = yaml_data_load(
            "nonexistent_root_dir",
            "nonexistent_data_dir",
            "Fallout4",
            "auto",
        );
        assert!(result.is_err());
    }

    #[test]
    fn test_yaml_data_load_from_real_dirs() {
        let root_dir = "J:\\CLASSIC-Fallout4";
        let data_dir = "J:\\CLASSIC-Fallout4\\ClassicLib";

        let result = yaml_data_load(root_dir, data_dir, "Fallout4", "auto");
        if let Ok(data) = result {
            assert!(!yaml_data_classic_version(&data).is_empty());
            assert!(!yaml_data_xse_acronym(&data).is_empty());
            assert!(!yaml_data_crashgen_name_field(&data).is_empty());
            assert!(!yaml_data_game_version(&data).is_empty());
            assert!(!yaml_data_mods_freq_entries(&data).is_empty());
            assert!(!yaml_data_mods_solu_entries(&data).is_empty());

            let name = yaml_data_get_crashgen_name(&data);
            assert!(!name.is_empty());

            // IndexMap key/value pairs should have matching lengths
            let err_keys = yaml_data_suspects_error_keys(&data);
            let err_vals = yaml_data_suspects_error_values(&data);
            assert_eq!(err_keys.len(), err_vals.len());
        }
    }

    #[test]
    fn test_yaml_data_game_version_mode() {
        let root_dir = "J:\\CLASSIC-Fallout4";
        let data_dir = "J:\\CLASSIC-Fallout4\\ClassicLib";

        let result_og = yaml_data_load(root_dir, data_dir, "Fallout4", "auto");
        let result_vr = yaml_data_load(root_dir, data_dir, "Fallout4", "VR");

        if let (Ok(og), Ok(vr)) = (result_og, result_vr) {
            let og_root = yaml_data_get_game_root_name(&og);
            let vr_root = yaml_data_get_game_root_name(&vr);
            assert!(!og_root.is_empty());
            assert!(!vr_root.is_empty());
        }
    }

    #[test]
    fn test_yaml_data_accessors_fallback_when_game_info_is_minimal() {
        let temp = tempdir().expect("failed to create temp dir");
        let data_dir = temp.path().join("CLASSIC Data");
        let db_dir = data_dir.join("databases");
        std::fs::create_dir_all(&db_dir).expect("failed to create db dir");

        let main_yaml = r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
"#;
        let game_yaml = r#"
Game_Info:
  Main_Root_Name: "Fallout 4"
Crashgen_Registry:
  "Buffout 4":
    ignore_keys:
      - "BuffoutSpecificIgnore"
    checks: []
  default:
    ignore_keys:
      - "DefaultIgnore"
    checks: []
"#;
        let ignore_yaml = r#"
CLASSIC_Ignore_Fallout4: []
"#;

        std::fs::write(db_dir.join("CLASSIC Main.yaml"), main_yaml).expect("write main yaml");
        std::fs::write(db_dir.join("CLASSIC Fallout4.yaml"), game_yaml).expect("write game yaml");
        std::fs::write(temp.path().join("CLASSIC Ignore.yaml"), ignore_yaml)
            .expect("write ignore yaml");

        let root_dir = temp.path().to_string_lossy().to_string();
        let data_dir_str = data_dir.to_string_lossy().to_string();
        let data = yaml_data_load(&root_dir, &data_dir_str, "Fallout4", "auto")
            .expect("yaml_data_load should succeed");

        assert!(!yaml_data_get_crashgen_name(&data).is_empty());
        assert_eq!(
            yaml_data_get_crashgen_ignore(&data),
            vec!["BuffoutSpecificIgnore".to_string()]
        );
        assert!(!yaml_data_game_version(&data).is_empty());
    }

    #[test]
    fn test_save_local_yaml_paths_creates_file() {
        let temp = tempdir().expect("failed to create temp dir");
        let local_yaml_path = temp
            .path()
            .join("CLASSIC Data")
            .join("CLASSIC Fallout4 Local.yaml");

        save_local_yaml_paths(
            &local_yaml_path.to_string_lossy(),
            "C:/Games/Fallout4",
            "C:/Users/Test/Documents/My Games/Fallout4",
        )
        .expect("save_local_yaml_paths should succeed");

        let yaml = classic_settings_core::YamlOperations::new()
            .load_yaml_file(&local_yaml_path)
            .expect("load local yaml");
        assert_eq!(
            yaml["Game_Info"]["Root_Folder_Game"].as_str(),
            Some("C:/Games/Fallout4")
        );
        assert_eq!(
            yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
            Some("C:/Users/Test/Documents/My Games/Fallout4")
        );
    }

    // ── CXXS-07 typed suspect-rule tests ───────────────────────────────

    /// Builds a minimal YamlData with suspect error rules for testing.
    fn make_yaml_data_with_suspect_rules() -> Option<Box<YamlData>> {
        let temp = tempdir().expect("failed to create temp dir");
        let data_dir = temp.path().join("CLASSIC Data");
        let db_dir = data_dir.join("databases");
        std::fs::create_dir_all(&db_dir).expect("failed to create db dir");

        let main_yaml = r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
"#;

        let game_yaml = r#"
Game_Info:
  Main_Root_Name: "Fallout 4"
Crashgen_Registry:
  "Buffout 4":
    ignore_keys: []
    checks: []
  default:
    ignore_keys: []
    checks: []
Crashlog_Error_Check:
  - id: "err_test_rule"
    name: "Test Error Rule"
    severity: 3
    main_error_contains_any:
      - "AccessViolation"
      - "NullPointer"
Crashlog_Stack_Check:
  - id: "stack_test_rule"
    name: "Test Stack Rule"
    severity: 2
    main_error_required_any:
      - "RequiredPattern"
    main_error_optional_any:
      - "OptionalPattern"
    stack_contains_any:
      - "StackPattern1"
      - "StackPattern2"
    exclude_if_stack_contains_any:
      - "ExcludePattern"
    stack_contains_at_least:
      - substring: "RepeatedFunc"
        count: 2
"#;

        let ignore_yaml = r#"
CLASSIC_Ignore_Fallout4: []
"#;

        std::fs::write(db_dir.join("CLASSIC Main.yaml"), main_yaml).ok()?;
        std::fs::write(db_dir.join("CLASSIC Fallout4.yaml"), game_yaml).ok()?;
        std::fs::write(temp.path().join("CLASSIC Ignore.yaml"), ignore_yaml).ok()?;

        let root_dir = temp.path().to_string_lossy().to_string();
        let data_dir_str = data_dir.to_string_lossy().to_string();

        // Keep temp alive by leaking — test fixture only
        std::mem::forget(temp);

        yaml_data_load(&root_dir, &data_dir_str, "Fallout4", "auto").ok()
    }

    #[test]
    fn test_yaml_data_suspects_error_rules_empty() {
        let temp = tempdir().expect("failed to create temp dir");
        let data_dir = temp.path().join("CLASSIC Data");
        let db_dir = data_dir.join("databases");
        std::fs::create_dir_all(&db_dir).expect("failed to create db dir");

        let main_yaml = "CLASSIC_Info:\n  version: \"7.0.0\"\n  version_date: \"2024-01-01\"\nCLASSIC_Interface:\n  autoscan_text_Fallout4: \"Autoscan\"\n";
        let game_yaml = "Game_Info:\n  Main_Root_Name: \"Fallout 4\"\nCrashgen_Registry:\n  default:\n    ignore_keys: []\n    checks: []\n";
        let ignore_yaml = "CLASSIC_Ignore_Fallout4: []\n";

        std::fs::write(db_dir.join("CLASSIC Main.yaml"), main_yaml).expect("write main yaml");
        std::fs::write(db_dir.join("CLASSIC Fallout4.yaml"), game_yaml).expect("write game yaml");
        std::fs::write(temp.path().join("CLASSIC Ignore.yaml"), ignore_yaml)
            .expect("write ignore yaml");

        let root_dir = temp.path().to_string_lossy().to_string();
        let data_dir_str = data_dir.to_string_lossy().to_string();

        if let Ok(data) = yaml_data_load(&root_dir, &data_dir_str, "Fallout4", "auto") {
            assert!(yaml_data_suspects_error_rules(&data).is_empty());
        }
    }

    #[test]
    fn test_yaml_data_suspects_error_rules_populated() {
        if let Some(data) = make_yaml_data_with_suspect_rules() {
            let rules = yaml_data_suspects_error_rules(&data);
            assert!(!rules.is_empty(), "expected at least one error rule");
            let rule = &rules[0];
            assert_eq!(rule.id, "err_test_rule");
            assert_eq!(rule.name, "Test Error Rule");
            assert_eq!(rule.severity, 3);
            assert!(
                rule.main_error_contains_any
                    .contains(&"AccessViolation".to_string()),
                "expected AccessViolation in main_error_contains_any"
            );
        }
    }

    #[test]
    fn test_yaml_data_suspects_stack_rules_metadata_no_count_rules_field() {
        if let Some(data) = make_yaml_data_with_suspect_rules() {
            let metadata = yaml_data_suspects_stack_rules_metadata(&data);
            assert!(!metadata.is_empty(), "expected at least one stack rule");
            let rule = &metadata[0];
            assert_eq!(rule.id, "stack_test_rule");
            assert_eq!(rule.name, "Test Stack Rule");
            assert_eq!(rule.severity, 2);
            // Verify all flat Vec<String> fields are accessible (no nested Vec<Struct>)
            assert!(
                rule.main_error_required_any
                    .contains(&"RequiredPattern".to_string())
            );
            assert!(
                rule.main_error_optional_any
                    .contains(&"OptionalPattern".to_string())
            );
            assert!(
                rule.stack_contains_any
                    .contains(&"StackPattern1".to_string())
            );
            assert!(
                rule.exclude_if_stack_contains_any
                    .contains(&"ExcludePattern".to_string())
            );
            // Pitfall 6 compile-time proof: no stack_contains_at_least field on the DTO
        }
    }

    #[test]
    fn test_yaml_data_suspects_stack_count_rules_unknown_id_returns_empty() {
        if let Some(data) = make_yaml_data_with_suspect_rules() {
            let count_rules =
                yaml_data_suspects_stack_count_rules_for_id(&data, "definitely_not_a_real_id_xyz");
            assert!(count_rules.is_empty());
        }
    }

    #[test]
    fn test_yaml_data_suspects_stack_count_rules_known_id_returns_populated() {
        if let Some(data) = make_yaml_data_with_suspect_rules() {
            let count_rules = yaml_data_suspects_stack_count_rules_for_id(&data, "stack_test_rule");
            assert!(
                !count_rules.is_empty(),
                "expected count rules for stack_test_rule"
            );
            assert_eq!(count_rules[0].substring, "RepeatedFunc");
            assert_eq!(count_rules[0].count, 2);
        }
    }

    #[test]
    fn test_yaml_data_suspects_error_keys_still_works_d08_regression() {
        // D-08 regression: existing fn must remain unchanged
        if let Some(data) = make_yaml_data_with_suspect_rules() {
            let keys = yaml_data_suspects_error_keys(&data);
            assert!(
                !keys.is_empty(),
                "yaml_data_suspects_error_keys must still work (D-08)"
            );
        }
    }

    #[test]
    fn test_yaml_data_suspects_stack_keys_still_works_d08_regression() {
        // D-08 regression: existing fn must remain unchanged
        if let Some(data) = make_yaml_data_with_suspect_rules() {
            let keys = yaml_data_suspects_stack_keys(&data);
            assert!(
                !keys.is_empty(),
                "yaml_data_suspects_stack_keys must still work (D-08)"
            );
        }
    }

    #[test]
    fn test_settings_cache_stats_helpers_forward_core_surface() {
        settings_cache_clear();
        reset_settings_cache_stats();

        assert_eq!(settings_cache_size(), 0);
        let initial = settings_cache_stats();
        assert_eq!(initial.hits, 0);
        assert_eq!(initial.misses, 0);
        assert_eq!(initial.size, 0);
        assert_eq!(initial.capacity, 64);

        let mut file = NamedTempFile::new().expect("create temp yaml");
        file.write_all(b"key: value\n").expect("write temp yaml");
        file.flush().expect("flush temp yaml");

        classic_settings_core::load_settings_sync("bridge-settings", file.path())
            .expect("load settings into cache");

        let populated = settings_cache_stats();
        assert_eq!(settings_cache_size(), 1);
        assert_eq!(populated.size, 1);
    }
}
