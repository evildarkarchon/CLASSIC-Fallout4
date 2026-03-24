//! YamlDataCore configuration bridge for CXX FFI.
//!
//! Bridges `classic_config_core::YamlDataCore` which loads all CLASSIC YAML
//! configuration files (main, game, ignore) into a structured Rust type.
//! Provides bulk YAML getters plus Local-YAML path persistence helpers.
//!
//! IndexMap fields are exposed as paired key/value vectors since CXX bridges
//! are isolated and can't share opaque types across modules.

use classic_config_core::{ClassicConfig, YamlDataCore};
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
    data.inner.suspects_error_list.keys().cloned().collect()
}

fn yaml_data_suspects_error_values(data: &YamlData) -> Vec<String> {
    data.inner.suspects_error_list.values().cloned().collect()
}

fn yaml_data_suspects_stack_keys(data: &YamlData) -> Vec<String> {
    data.inner.suspects_stack_list.keys().cloned().collect()
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

fn yaml_data_mods_freq_keys(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_freq.keys().cloned().collect()
}

fn yaml_data_mods_freq_values(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_freq.values().cloned().collect()
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

fn yaml_data_mods_solu_keys(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_solu.keys().cloned().collect()
}

fn yaml_data_mods_solu_values(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_solu.values().cloned().collect()
}

#[cxx::bridge(namespace = "classic::config")]
mod ffi {
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
        fn yaml_data_mods_freq_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_freq_values(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_mod_a(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_mod_b(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_name_a(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_name_b(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_descriptions(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_fixes(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_links(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_count(data: &YamlData) -> usize;
        fn yaml_data_mods_solu_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_solu_values(data: &YamlData) -> Vec<String>;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
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

        let yaml = classic_yaml_core::YamlOperations::new()
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
}
