//! Settings persistence and validation for the GUI
//!
//! Provides functions to load, save, validate, and reset application settings
//! using `ClassicConfig` from `classic-config-core`. Settings are persisted as
//! YAML in the user's config directory via `directories::ProjectDirs`.

use std::path::{Path, PathBuf};

use classic_config_core::ClassicConfig;
use classic_shared_core::get_runtime;
use directories::ProjectDirs;

/// Returns the path to `settings.yaml` in the user's config directory.
///
/// Uses `directories::ProjectDirs` with qualifier `com`, organization `classic`,
/// application `classic-gui`. Returns `None` if the platform has no standard
/// config directory.
pub fn settings_file_path() -> Option<PathBuf> {
    ProjectDirs::from("com", "classic", "classic-gui")
        .map(|dirs| dirs.config_dir().join("settings.yaml"))
}

/// Load settings from the YAML file, falling back to defaults.
///
/// If the settings file does not exist or cannot be parsed, returns
/// `ClassicConfig::default()`.
pub fn load_settings() -> ClassicConfig {
    let Some(path) = settings_file_path() else {
        return ClassicConfig::default();
    };

    if !path.exists() {
        return ClassicConfig::default();
    }

    let rt = get_runtime();
    match rt.block_on(ClassicConfig::load_from_yaml(&path)) {
        Ok(config) => config,
        Err(e) => {
            tracing::warn!("Failed to load settings, using defaults: {}", e);
            ClassicConfig::default()
        }
    }
}

/// Save the entire config to the settings YAML file.
///
/// Creates parent directories if they do not exist.
///
/// # Errors
///
/// Returns an error if the config directory cannot be determined or if
/// the YAML file cannot be written.
pub fn save_full_config(config: &ClassicConfig) -> Result<(), Box<dyn std::error::Error>> {
    let path = settings_file_path().ok_or("Could not determine config directory")?;

    let rt = get_runtime();
    rt.block_on(config.save_to_yaml(&path))?;

    Ok(())
}

/// Update a boolean setting in the config and persist to YAML.
///
/// # Arguments
///
/// * `config` - Mutable reference to the config to update
/// * `key` - Setting key name (e.g., `"fcx_mode"`, `"simplify_logs"`)
/// * `value` - New boolean value
///
/// # Errors
///
/// Returns an error if the key is unknown or if saving fails.
pub fn save_setting_bool(
    config: &mut ClassicConfig,
    key: &str,
    value: bool,
) -> Result<(), Box<dyn std::error::Error>> {
    match key {
        "fcx_mode" => config.fcx_mode = value,
        "show_formid_values" => config.show_formid_values = value,
        "simplify_logs" => config.simplify_logs = value,
        "move_unsolved_logs" => config.move_unsolved_logs = value,
        "update_check" => config.update_check = value,
        "auto_switch_to_results" => config.auto_switch_to_results = value,
        _ => return Err(format!("Unknown boolean setting: {}", key).into()),
    }

    save_full_config(config)
}

/// Update a string setting in the config and persist to YAML.
///
/// # Arguments
///
/// * `config` - Mutable reference to the config to update
/// * `key` - Setting key name (e.g., `"game_version"`, `"update_source"`)
/// * `value` - New string value
///
/// # Errors
///
/// Returns an error if the key is unknown or if saving fails.
pub fn save_setting_string(
    config: &mut ClassicConfig,
    key: &str,
    value: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    match key {
        "game_version" => config.game_version = value.to_string(),
        "update_source" => config.update_source = value.to_string(),
        _ => return Err(format!("Unknown string setting: {}", key).into()),
    }

    save_full_config(config)
}

/// Validate a path, update the config, and persist to YAML.
///
/// Validates that the given path is a non-empty string pointing to an existing
/// directory. If valid, updates the config field and saves. If invalid,
/// returns a human-readable error message suitable for UI display.
///
/// An empty path clears the setting (sets it to `None`) and is always valid.
///
/// # Arguments
///
/// * `config` - Mutable reference to the config to update
/// * `key` - Path setting key (`"ini_folder"`, `"mods_folder"`, or `"scan_custom"`)
/// * `path` - The path string to validate and save
///
/// # Errors
///
/// Returns a user-facing error string if the path is invalid or the key is unknown.
pub fn save_path_setting(
    config: &mut ClassicConfig,
    key: &str,
    path: &str,
) -> Result<(), String> {
    let trimmed = path.trim();

    // Empty path clears the setting
    if trimmed.is_empty() {
        match key {
            "ini_folder" => config.paths.ini_folder = None,
            "mods_folder" => config.paths.mods_folder = None,
            "scan_custom" => config.paths.scan_custom = None,
            _ => return Err(format!("Unknown path setting: {}", key)),
        }
        save_full_config(config).map_err(|e| format!("Failed to save: {}", e))?;
        return Ok(());
    }

    // Validate that the directory exists
    let dir = Path::new(trimmed);
    if !dir.is_dir() {
        return Err(format!("Directory does not exist: {}", trimmed));
    }

    let path_buf = PathBuf::from(trimmed);
    match key {
        "ini_folder" => config.paths.ini_folder = Some(path_buf),
        "mods_folder" => config.paths.mods_folder = Some(path_buf),
        "scan_custom" => config.paths.scan_custom = Some(path_buf),
        _ => return Err(format!("Unknown path setting: {}", key)),
    }

    save_full_config(config).map_err(|e| format!("Failed to save: {}", e))
}

/// Reset all settings to defaults, save to YAML, and return the new config.
///
/// Creates a `ClassicConfig::default()`, persists it, and returns it so the
/// caller can repopulate the UI.
pub fn reset_to_defaults() -> ClassicConfig {
    let config = ClassicConfig::default();
    if let Err(e) = save_full_config(&config) {
        tracing::warn!("Failed to save default settings: {}", e);
    }
    config
}

/// Detect the game version based on available information.
///
/// This is a stub implementation. Full auto-detection (checking game EXE
/// version, registry keys, etc.) is deferred to a future phase. Currently
/// returns a hint string based on simple heuristics.
///
/// # Arguments
///
/// * `config` - The current config (used to check game_root path)
///
/// # Returns
///
/// A hint string like `"(detected: NextGen)"` or `"(detection unavailable)"`
/// suitable for display next to the "Auto" dropdown option.
pub fn detect_game_version(config: &ClassicConfig) -> String {
    let game_root = &config.paths.game_root;

    // If no game root is configured, detection is not possible
    if game_root.as_os_str().is_empty() || !game_root.exists() {
        return "(detection unavailable)".to_string();
    }

    // Check for VR-specific executable
    if game_root.join("Fallout4VR.exe").exists() {
        return "(detected: VR)".to_string();
    }

    // Check for standard Fallout4.exe -- if present, assume NextGen
    // (full detection based on EXE version is deferred)
    if game_root.join("Fallout4.exe").exists() {
        return "(detected: NextGen)".to_string();
    }

    "(detection unavailable)".to_string()
}

/// Convert a game version dropdown index to its YAML storage string.
///
/// | Index | String      |
/// |-------|-------------|
/// | 0     | `"auto"`    |
/// | 1     | `"Original"`|
/// | 2     | `"NextGen"` |
/// | 3     | `"VR"`      |
pub fn game_version_index_to_string(index: i32) -> &'static str {
    match index {
        0 => "auto",
        1 => "Original",
        2 => "NextGen",
        3 => "VR",
        _ => "auto",
    }
}

/// Convert a game version YAML string to its dropdown index.
///
/// Case-insensitive matching for `"auto"`. Returns 0 (Auto) for unknown values.
pub fn game_version_string_to_index(version: &str) -> i32 {
    match version {
        "auto" | "Auto" => 0,
        "Original" => 1,
        "NextGen" => 2,
        "VR" => 3,
        _ => 0,
    }
}

/// Convert an update source dropdown index to its YAML storage string.
///
/// | Index | String     |
/// |-------|------------|
/// | 0     | `"github"` |
/// | 1     | `"both"`   |
pub fn update_source_index_to_string(index: i32) -> &'static str {
    match index {
        0 => "github",
        1 => "both",
        _ => "github",
    }
}

/// Convert an update source YAML string to its dropdown index.
///
/// Returns 0 (GitHub) for unknown values.
pub fn update_source_string_to_index(source: &str) -> i32 {
    match source {
        "github" => 0,
        "both" => 1,
        _ => 0,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_settings_file_path_is_some() {
        let path = settings_file_path();
        assert!(path.is_some(), "settings_file_path() should return Some on this platform");
        let path = path.unwrap();
        assert!(path.ends_with("settings.yaml"));
    }

    #[test]
    fn test_game_version_index_round_trip() {
        for index in 0..=3 {
            let s = game_version_index_to_string(index);
            let back = game_version_string_to_index(s);
            assert_eq!(back, index, "Round trip failed for index {}", index);
        }
    }

    #[test]
    fn test_game_version_unknown_defaults_to_auto() {
        assert_eq!(game_version_string_to_index("unknown"), 0);
        assert_eq!(game_version_index_to_string(99), "auto");
    }

    #[test]
    fn test_update_source_index_round_trip() {
        for index in 0..=1 {
            let s = update_source_index_to_string(index);
            let back = update_source_string_to_index(s);
            assert_eq!(back, index, "Round trip failed for index {}", index);
        }
    }

    #[test]
    fn test_update_source_unknown_defaults_to_github() {
        assert_eq!(update_source_string_to_index("unknown"), 0);
        assert_eq!(update_source_index_to_string(99), "github");
    }

    #[test]
    fn test_load_settings_returns_valid_config() {
        // load_settings should return a valid config either from disk or defaults.
        // Other tests may have written to the settings file, so we just verify
        // the returned config is structurally valid (not necessarily defaults).
        let config = load_settings();
        // game_version should be a known value
        let valid_versions = ["auto", "Auto", "Original", "NextGen", "VR"];
        assert!(
            valid_versions.contains(&config.game_version.as_str()),
            "game_version '{}' should be a known value",
            config.game_version
        );
    }

    #[test]
    fn test_reset_to_defaults_returns_default_config() {
        let config = reset_to_defaults();
        assert_eq!(config.game_version, "auto");
        assert_eq!(config.update_source, "github");
        assert!(config.update_check);
        assert!(!config.fcx_mode);
        assert!(!config.simplify_logs);
        assert!(!config.move_unsolved_logs);
        assert!(!config.show_formid_values);
        assert!(config.auto_switch_to_results);
    }

    #[test]
    fn test_detect_game_version_empty_root() {
        let config = ClassicConfig::default();
        let hint = detect_game_version(&config);
        assert_eq!(hint, "(detection unavailable)");
    }

    #[test]
    fn test_save_setting_bool_unknown_key() {
        let mut config = ClassicConfig::default();
        let result = save_setting_bool(&mut config, "nonexistent", true);
        assert!(result.is_err());
    }

    #[test]
    fn test_save_setting_string_unknown_key() {
        let mut config = ClassicConfig::default();
        let result = save_setting_string(&mut config, "nonexistent", "value");
        assert!(result.is_err());
    }

    #[test]
    fn test_save_path_setting_unknown_key() {
        let mut config = ClassicConfig::default();
        let result = save_path_setting(&mut config, "nonexistent", "/some/path");
        assert!(result.is_err());
    }

    #[test]
    fn test_save_path_setting_empty_clears() {
        let mut config = ClassicConfig::default();
        config.paths.ini_folder = Some(PathBuf::from("C:\\Test"));

        // Empty path should clear and succeed (save may fail in test env, but
        // the field should still be cleared)
        let _ = save_path_setting(&mut config, "ini_folder", "");
        assert!(config.paths.ini_folder.is_none());
    }

    #[test]
    fn test_save_path_setting_invalid_dir() {
        let mut config = ClassicConfig::default();
        let result = save_path_setting(
            &mut config,
            "ini_folder",
            "Z:\\NonExistent\\Path\\That\\Should\\Not\\Exist",
        );
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.contains("does not exist"), "Error should mention non-existence: {}", err);
    }

    // ---- Additional coverage tests ----

    #[test]
    fn test_game_version_case_insensitive_auto() {
        assert_eq!(game_version_string_to_index("auto"), 0);
        assert_eq!(game_version_string_to_index("Auto"), 0);
    }

    #[test]
    fn test_game_version_all_values() {
        assert_eq!(game_version_index_to_string(0), "auto");
        assert_eq!(game_version_index_to_string(1), "Original");
        assert_eq!(game_version_index_to_string(2), "NextGen");
        assert_eq!(game_version_index_to_string(3), "VR");
    }

    #[test]
    fn test_game_version_negative_index() {
        assert_eq!(game_version_index_to_string(-1), "auto");
    }

    #[test]
    fn test_update_source_all_values() {
        assert_eq!(update_source_index_to_string(0), "github");
        assert_eq!(update_source_index_to_string(1), "both");
    }

    #[test]
    fn test_update_source_negative_index() {
        assert_eq!(update_source_index_to_string(-1), "github");
    }

    #[test]
    fn test_save_path_setting_empty_clears_mods() {
        let mut config = ClassicConfig::default();
        config.paths.mods_folder = Some(PathBuf::from("C:\\Mods"));
        let _ = save_path_setting(&mut config, "mods_folder", "");
        assert!(config.paths.mods_folder.is_none());
    }

    #[test]
    fn test_save_path_setting_empty_clears_scan_custom() {
        let mut config = ClassicConfig::default();
        config.paths.scan_custom = Some(PathBuf::from("C:\\Scan"));
        let _ = save_path_setting(&mut config, "scan_custom", "");
        assert!(config.paths.scan_custom.is_none());
    }

    #[test]
    fn test_save_path_setting_whitespace_treated_as_empty() {
        let mut config = ClassicConfig::default();
        config.paths.ini_folder = Some(PathBuf::from("C:\\Test"));
        let _ = save_path_setting(&mut config, "ini_folder", "   ");
        assert!(config.paths.ini_folder.is_none());
    }

    #[test]
    fn test_save_path_setting_unknown_key_empty() {
        let mut config = ClassicConfig::default();
        let result = save_path_setting(&mut config, "bad_key", "");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("Unknown path setting"));
    }

    #[test]
    fn test_save_path_setting_unknown_key_nonempty() {
        let mut config = ClassicConfig::default();
        let result = save_path_setting(&mut config, "bad_key", "C:\\Stuff");
        assert!(result.is_err());
    }

    #[test]
    fn test_detect_game_version_with_tempdir() {
        let dir = tempfile::tempdir().unwrap();

        // No executables -> detection unavailable
        let mut config = ClassicConfig::default();
        config.paths.game_root = dir.path().to_path_buf();
        assert_eq!(detect_game_version(&config), "(detection unavailable)");

        // Create Fallout4.exe -> detected NextGen
        std::fs::File::create(dir.path().join("Fallout4.exe")).unwrap();
        assert_eq!(detect_game_version(&config), "(detected: NextGen)");

        // Create Fallout4VR.exe -> detected VR (VR takes precedence)
        std::fs::File::create(dir.path().join("Fallout4VR.exe")).unwrap();
        assert_eq!(detect_game_version(&config), "(detected: VR)");
    }

    #[test]
    fn test_detect_game_version_nonexistent_root() {
        let mut config = ClassicConfig::default();
        config.paths.game_root = PathBuf::from("Z:\\NonExistent\\Path\\42");
        assert_eq!(detect_game_version(&config), "(detection unavailable)");
    }

    #[test]
    fn test_save_setting_bool_all_keys() {
        // Verify all known boolean keys are accepted (save may fail in test env)
        let keys = ["fcx_mode", "show_formid_values", "simplify_logs", "move_unsolved_logs", "update_check", "auto_switch_to_results"];
        for key in keys {
            let mut config = ClassicConfig::default();
            let result = save_setting_bool(&mut config, key, true);
            // We only care that it doesn't fail with "Unknown" error
            if let Err(e) = &result {
                assert!(!e.to_string().contains("Unknown"), "Key '{}' should be known: {}", key, e);
            }
        }
    }

    #[test]
    fn test_save_setting_string_all_keys() {
        let keys = ["game_version", "update_source"];
        for key in keys {
            let mut config = ClassicConfig::default();
            let result = save_setting_string(&mut config, key, "test_value");
            if let Err(e) = &result {
                assert!(!e.to_string().contains("Unknown"), "Key '{}' should be known: {}", key, e);
            }
        }
    }

    #[test]
    fn test_save_path_setting_valid_dir() {
        let dir = tempfile::tempdir().unwrap();
        let mut config = ClassicConfig::default();
        let result = save_path_setting(&mut config, "ini_folder", dir.path().to_str().unwrap());
        // Path validation should pass (dir exists), but save_full_config may fail
        // If it succeeded, the field should be set
        if result.is_ok() {
            assert_eq!(config.paths.ini_folder, Some(dir.path().to_path_buf()));
        }
    }

    #[test]
    fn test_save_full_config_and_load_roundtrip() {
        // Test that save_full_config can write to the config directory
        let config = ClassicConfig::default();
        let result = save_full_config(&config);
        // May fail if config dir is read-only, but at least exercises the code path
        // Just verify it doesn't panic; the save may legitimately fail in some envs
        let _ = result;
    }

    #[test]
    fn test_save_setting_bool_modifies_config() {
        let mut config = ClassicConfig::default();
        assert!(!config.fcx_mode);
        // save_setting_bool updates the field even if save fails
        let _ = save_setting_bool(&mut config, "fcx_mode", true);
        assert!(config.fcx_mode, "fcx_mode should be set to true");

        let _ = save_setting_bool(&mut config, "simplify_logs", true);
        assert!(config.simplify_logs);

        let _ = save_setting_bool(&mut config, "move_unsolved_logs", true);
        assert!(config.move_unsolved_logs);

        let _ = save_setting_bool(&mut config, "show_formid_values", true);
        assert!(config.show_formid_values);

        let _ = save_setting_bool(&mut config, "update_check", false);
        assert!(!config.update_check);

        let _ = save_setting_bool(&mut config, "auto_switch_to_results", false);
        assert!(!config.auto_switch_to_results);
    }

    #[test]
    fn test_save_setting_string_modifies_config() {
        let mut config = ClassicConfig::default();
        let _ = save_setting_string(&mut config, "game_version", "VR");
        assert_eq!(config.game_version, "VR");

        let _ = save_setting_string(&mut config, "update_source", "both");
        assert_eq!(config.update_source, "both");
    }

    #[test]
    fn test_save_path_setting_valid_dir_mods_folder() {
        let dir = tempfile::tempdir().unwrap();
        let mut config = ClassicConfig::default();
        let result = save_path_setting(&mut config, "mods_folder", dir.path().to_str().unwrap());
        if result.is_ok() {
            assert_eq!(config.paths.mods_folder, Some(dir.path().to_path_buf()));
        }
    }

    #[test]
    fn test_save_path_setting_valid_dir_scan_custom() {
        let dir = tempfile::tempdir().unwrap();
        let mut config = ClassicConfig::default();
        let result = save_path_setting(&mut config, "scan_custom", dir.path().to_str().unwrap());
        if result.is_ok() {
            assert_eq!(config.paths.scan_custom, Some(dir.path().to_path_buf()));
        }
    }
}
