//! YamlDataCore configuration bridge for CXX FFI.
//!
//! Bridges `classic_config_core::YamlDataCore` which loads all CLASSIC YAML
//! configuration files (main, game, ignore) into a structured Rust type.
//! Provides 30+ getter functions for all fields.
//!
//! IndexMap fields are exposed as paired key/value vectors since CXX bridges
//! are isolated and can't share opaque types across modules.

use classic_config_core::YamlDataCore;
use classic_shared_core::get_runtime;
use std::path::PathBuf;

/// Opaque wrapper around `YamlDataCore` for CXX FFI.
pub struct YamlData {
    pub(crate) inner: YamlDataCore,
}

// ── Construction ────────────────────────────────────────────────────

fn yaml_data_load(yaml_dir_root: &str, yaml_dir_data: &str, game: &str, vr_mode: bool) -> Result<Box<YamlData>, String> {
    let dirs = vec![PathBuf::from(yaml_dir_root), PathBuf::from(yaml_dir_data)];
    let inner = get_runtime()
        .block_on(YamlDataCore::load_from_yaml_files(
            dirs,
            game.to_string(),
            vr_mode,
        ))
        .map_err(|e| format!("{e}"))?;
    Ok(Box::new(YamlData { inner }))
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

fn yaml_data_crashgen_name_vr_field(data: &YamlData) -> &str {
    &data.inner.crashgen_name_vr
}

fn yaml_data_crashgen_latest_og(data: &YamlData) -> &str {
    &data.inner.crashgen_latest_og
}

fn yaml_data_crashgen_latest_vr(data: &YamlData) -> &str {
    &data.inner.crashgen_latest_vr
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

fn yaml_data_game_version_new(data: &YamlData) -> &str {
    &data.inner.game_version_new
}

fn yaml_data_game_version_vr(data: &YamlData) -> &str {
    &data.inner.game_version_vr
}

fn yaml_data_game_root_name_field(data: &YamlData) -> &str {
    &data.inner.game_root_name
}

fn yaml_data_game_root_name_vr_field(data: &YamlData) -> &str {
    &data.inner.game_root_name_vr
}

// ── VR-aware accessors ──────────────────────────────────────────────

fn yaml_data_get_crashgen_name(data: &YamlData, is_vr: bool) -> String {
    data.inner.get_crashgen_name(is_vr).to_string()
}

fn yaml_data_get_game_root_name(data: &YamlData, is_vr: bool) -> String {
    data.inner.get_game_root_name(is_vr).to_string()
}

fn yaml_data_get_crashgen_ignore(data: &YamlData, is_vr: bool) -> Vec<String> {
    data.inner.get_crashgen_ignore(is_vr).to_vec()
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

fn yaml_data_crashgen_ignore_vr_list(data: &YamlData) -> Vec<String> {
    data.inner.crashgen_ignore_vr.clone()
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
    data.inner.game_mods_core.keys().cloned().collect()
}

fn yaml_data_mods_core_values(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_core.values().cloned().collect()
}

fn yaml_data_mods_freq_keys(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_freq.keys().cloned().collect()
}

fn yaml_data_mods_freq_values(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_freq.values().cloned().collect()
}

fn yaml_data_mods_conf_keys(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_conf.keys().cloned().collect()
}

fn yaml_data_mods_conf_values(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_conf.values().cloned().collect()
}

fn yaml_data_mods_solu_keys(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_solu.keys().cloned().collect()
}

fn yaml_data_mods_solu_values(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_solu.values().cloned().collect()
}

fn yaml_data_mods_opc2_keys(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_opc2.keys().cloned().collect()
}

fn yaml_data_mods_opc2_values(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_opc2.values().cloned().collect()
}

fn yaml_data_mods_folon_keys(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_core_folon.keys().cloned().collect()
}

fn yaml_data_mods_folon_values(data: &YamlData) -> Vec<String> {
    data.inner.game_mods_core_folon.values().cloned().collect()
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
            vr_mode: bool,
        ) -> Result<Box<YamlData>>;

        // String getters
        fn yaml_data_classic_version(data: &YamlData) -> &str;
        fn yaml_data_classic_version_date(data: &YamlData) -> &str;
        fn yaml_data_crashgen_name_field(data: &YamlData) -> &str;
        fn yaml_data_crashgen_name_vr_field(data: &YamlData) -> &str;
        fn yaml_data_crashgen_latest_og(data: &YamlData) -> &str;
        fn yaml_data_crashgen_latest_vr(data: &YamlData) -> &str;
        fn yaml_data_warn_noplugins(data: &YamlData) -> &str;
        fn yaml_data_warn_outdated(data: &YamlData) -> &str;
        fn yaml_data_xse_acronym(data: &YamlData) -> &str;
        fn yaml_data_autoscan_text(data: &YamlData) -> &str;
        fn yaml_data_game_version(data: &YamlData) -> &str;
        fn yaml_data_game_version_new(data: &YamlData) -> &str;
        fn yaml_data_game_version_vr(data: &YamlData) -> &str;
        fn yaml_data_game_root_name_field(data: &YamlData) -> &str;
        fn yaml_data_game_root_name_vr_field(data: &YamlData) -> &str;

        // VR-aware accessors
        fn yaml_data_get_crashgen_name(data: &YamlData, is_vr: bool) -> String;
        fn yaml_data_get_game_root_name(data: &YamlData, is_vr: bool) -> String;
        fn yaml_data_get_crashgen_ignore(data: &YamlData, is_vr: bool) -> Vec<String>;

        // Vec<String> getters
        fn yaml_data_classic_game_hints(data: &YamlData) -> Vec<String>;
        fn yaml_data_classic_records_list(data: &YamlData) -> Vec<String>;
        fn yaml_data_crashgen_ignore_og(data: &YamlData) -> Vec<String>;
        fn yaml_data_crashgen_ignore_vr_list(data: &YamlData) -> Vec<String>;
        fn yaml_data_game_ignore_plugins(data: &YamlData) -> Vec<String>;
        fn yaml_data_game_ignore_records(data: &YamlData) -> Vec<String>;
        fn yaml_data_ignore_list(data: &YamlData) -> Vec<String>;

        // IndexMap getters as paired key/value vectors
        fn yaml_data_suspects_error_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_suspects_error_values(data: &YamlData) -> Vec<String>;
        fn yaml_data_suspects_stack_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_core_values(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_freq_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_freq_values(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_conf_values(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_solu_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_solu_values(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_opc2_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_opc2_values(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_folon_keys(data: &YamlData) -> Vec<String>;
        fn yaml_data_mods_folon_values(data: &YamlData) -> Vec<String>;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_yaml_data_load_invalid_dirs() {
        let result = yaml_data_load(
            "nonexistent_root_dir",
            "nonexistent_data_dir",
            "Fallout4",
            false,
        );
        assert!(result.is_err());
    }

    #[test]
    fn test_yaml_data_load_from_real_dirs() {
        let root_dir = "J:\\CLASSIC-Fallout4";
        let data_dir = "J:\\CLASSIC-Fallout4\\ClassicLib";

        let result = yaml_data_load(root_dir, data_dir, "Fallout4", false);
        if let Ok(data) = result {
            assert!(!yaml_data_classic_version(&data).is_empty());
            assert!(!yaml_data_xse_acronym(&data).is_empty());
            assert!(!yaml_data_crashgen_name_field(&data).is_empty());
            assert!(!yaml_data_game_version(&data).is_empty());

            let og_name = yaml_data_get_crashgen_name(&data, false);
            let vr_name = yaml_data_get_crashgen_name(&data, true);
            assert!(!og_name.is_empty());
            assert!(!vr_name.is_empty());

            // IndexMap key/value pairs should have matching lengths
            let err_keys = yaml_data_suspects_error_keys(&data);
            let err_vals = yaml_data_suspects_error_values(&data);
            assert_eq!(err_keys.len(), err_vals.len());
        }
    }

    #[test]
    fn test_yaml_data_vr_mode() {
        let root_dir = "J:\\CLASSIC-Fallout4";
        let data_dir = "J:\\CLASSIC-Fallout4\\ClassicLib";

        let result_og = yaml_data_load(root_dir, data_dir, "Fallout4", false);
        let result_vr = yaml_data_load(root_dir, data_dir, "Fallout4", true);

        if let (Ok(og), Ok(vr)) = (result_og, result_vr) {
            let og_root = yaml_data_get_game_root_name(&og, false);
            let vr_root = yaml_data_get_game_root_name(&vr, true);
            assert!(!og_root.is_empty());
            assert!(!vr_root.is_empty());
        }
    }
}
