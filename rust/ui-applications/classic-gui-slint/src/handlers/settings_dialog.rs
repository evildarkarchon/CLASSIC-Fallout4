// Settings dialog handlers - Comprehensive settings management
#![allow(dead_code)]
use anyhow::{Context, Result};
use crate::app_state::SharedAppState;
use std::path::PathBuf;

/// Settings data structure for dialog-AppState synchronization
///
/// This struct represents all settings that can be modified in the settings dialog.
/// It provides a clean interface between the UI and AppState.
#[derive(Debug, Clone)]
pub struct SettingsData {
    // General settings
    pub fcx_mode: bool,
    pub show_formid_values: bool,
    pub stat_logging: bool,
    pub update_check: bool,
    pub vr_mode: bool,
    pub auto_switch_to_results: bool,

    // Advanced settings
    pub move_unsolved_logs: bool,
    pub simplify_logs: bool,

    // Path settings
    pub game_root: String,
    pub docs_root: String,
    pub ini_folder: String,
    pub mods_folder: String,
    pub scan_custom: String,
}

impl SettingsData {
    /// Load current settings from AppState
    ///
    /// Extracts all settings from the shared AppState and converts paths to strings
    /// for display in the UI.
    ///
    /// # Arguments
    /// * `state` - Shared application state
    ///
    /// # Returns
    /// SettingsData populated with current configuration
    pub fn from_app_state(state: SharedAppState) -> Self {
        let state_guard = state.read();

        Self {
            fcx_mode: state_guard.fcx_mode(),
            show_formid_values: state_guard.show_formid_values(),
            stat_logging: state_guard.stat_logging(),
            update_check: state_guard.update_check(),
            vr_mode: state_guard.vr_mode(),
            auto_switch_to_results: state_guard.auto_switch_to_results(),
            move_unsolved_logs: state_guard.move_unsolved_logs(),
            simplify_logs: state_guard.simplify_logs(),
            game_root: state_guard.game_root().to_string_lossy().to_string(),
            docs_root: state_guard
                .docs_root()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default(),
            ini_folder: state_guard
                .ini_folder()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default(),
            mods_folder: state_guard
                .mods_folder()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default(),
            scan_custom: state_guard
                .scan_folder()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_default(),
        }
    }

    /// Save settings to AppState and persist to YAML
    ///
    /// Updates the AppState configuration and saves it to CLASSIC_Settings.yaml.
    ///
    /// # Arguments
    /// * `state` - Shared application state to update
    ///
    /// # Returns
    /// * `Ok(())` - Settings saved successfully
    /// * `Err(anyhow::Error)` - Failed to save settings
    pub async fn save_to_app_state(&self, state: SharedAppState) -> Result<()> {
        tracing::info!("Saving settings to AppState...");

        // Update AppState with new settings
        {
            let mut state_guard = state.write();

            // Update boolean settings
            tracing::debug!("Updating settings:");
            tracing::debug!("  FCX Mode: {}", self.fcx_mode);
            state_guard.set_fcx_mode(self.fcx_mode);

            tracing::debug!("  Show FormID Values: {}", self.show_formid_values);
            state_guard.set_show_formid_values(self.show_formid_values);

            tracing::debug!("  Stat Logging: {}", self.stat_logging);
            state_guard.set_stat_logging(self.stat_logging);

            tracing::debug!("  Update Check: {}", self.update_check);
            state_guard.set_update_check(self.update_check);

            tracing::debug!("  VR Mode: {}", self.vr_mode);
            state_guard.set_vr_mode(self.vr_mode);

            tracing::debug!("  Auto-Switch to Results: {}", self.auto_switch_to_results);
            state_guard.set_auto_switch_to_results(self.auto_switch_to_results);

            tracing::debug!("  Move Unsolved Logs: {}", self.move_unsolved_logs);
            state_guard.set_move_unsolved_logs(self.move_unsolved_logs);

            tracing::debug!("  Simplify Logs: {}", self.simplify_logs);
            state_guard.set_simplify_logs(self.simplify_logs);

            // Update path settings
            tracing::debug!("  Game Root: {}", self.game_root);
            state_guard.set_game_root(PathBuf::from(&self.game_root));

            tracing::debug!("  Docs Root: {}", self.docs_root);
            state_guard.set_docs_root(
                if self.docs_root.is_empty() {
                    None
                } else {
                    Some(PathBuf::from(&self.docs_root))
                }
            );

            tracing::debug!("  INI Folder: {}", self.ini_folder);
            state_guard.set_ini_folder(
                if self.ini_folder.is_empty() {
                    None
                } else {
                    Some(PathBuf::from(&self.ini_folder))
                }
            );

            tracing::debug!("  Mods Folder: {}", self.mods_folder);
            if !self.mods_folder.is_empty() {
                state_guard.set_mods_folder(PathBuf::from(&self.mods_folder));
            }

            tracing::debug!("  Scan Custom: {}", self.scan_custom);
            if !self.scan_custom.is_empty() {
                state_guard.set_scan_folder(PathBuf::from(&self.scan_custom));
            }
        }

        // Save configuration to YAML file
        tracing::info!("Persisting settings to YAML file...");

        state.read().save_config().await
            .context("Failed to save configuration to YAML")?;

        tracing::info!("Settings saved successfully");
        Ok(())
    }

    /// Validate settings before saving
    ///
    /// Checks that required paths exist and are valid directories.
    ///
    /// # Returns
    /// * `Ok(())` - All settings are valid
    /// * `Err(anyhow::Error)` - One or more settings are invalid
    pub fn validate(&self) -> Result<()> {
        tracing::debug!("Validating settings...");

        // Validate game root (required)
        if self.game_root.is_empty() {
            anyhow::bail!("Game root directory is required");
        }

        let game_root_path = PathBuf::from(&self.game_root);
        if !game_root_path.exists() {
            anyhow::bail!(
                "Game root directory does not exist: {}",
                self.game_root
            );
        }

        if !game_root_path.is_dir() {
            anyhow::bail!(
                "Game root path is not a directory: {}",
                self.game_root
            );
        }

        // Validate optional paths (only if not empty)
        if !self.docs_root.is_empty() {
            let docs_path = PathBuf::from(&self.docs_root);
            if !docs_path.exists() {
                anyhow::bail!(
                    "Documents root directory does not exist: {}",
                    self.docs_root
                );
            }
        }

        if !self.ini_folder.is_empty() {
            let ini_path = PathBuf::from(&self.ini_folder);
            if !ini_path.exists() {
                anyhow::bail!(
                    "INI folder does not exist: {}",
                    self.ini_folder
                );
            }
        }

        if !self.mods_folder.is_empty() {
            let mods_path = PathBuf::from(&self.mods_folder);
            if !mods_path.exists() {
                anyhow::bail!(
                    "Mods folder does not exist: {}",
                    self.mods_folder
                );
            }
        }

        if !self.scan_custom.is_empty() {
            let scan_path = PathBuf::from(&self.scan_custom);
            if !scan_path.exists() {
                anyhow::bail!(
                    "Custom scan folder does not exist: {}",
                    self.scan_custom
                );
            }
        }

        tracing::debug!("Settings validation passed");
        Ok(())
    }
}

/// Browse for a directory path using native file dialog
///
/// Opens a folder picker dialog and returns the selected path.
///
/// # Arguments
/// * `path_type` - Type of path being browsed (for dialog title)
/// * `current_path` - Current path value (used as starting location if valid)
///
/// # Returns
/// * `Ok(Some(PathBuf))` - User selected a path
/// * `Ok(None)` - User cancelled the dialog
/// * `Err(anyhow::Error)` - Dialog failed to open
pub fn browse_settings_path(path_type: &str, current_path: &str) -> Result<Option<PathBuf>> {
    tracing::info!("Opening folder picker for: {}", path_type);

    let title = match path_type {
        "game-root" => "Select Game Root Directory",
        "docs-root" => "Select Documents Root Directory",
        "ini-folder" => "Select INI Folder",
        "mods-folder" => "Select Mods Folder",
        "scan-custom" => "Select Custom Scan Folder",
        _ => "Select Folder",
    };

    let mut dialog = rfd::FileDialog::new().set_title(title);

    // Set starting directory if current path is valid
    if !current_path.is_empty() {
        let current = PathBuf::from(current_path);
        if current.exists() && current.is_dir() {
            dialog = dialog.set_directory(&current);
        }
    }

    // Open folder picker
    let result = dialog.pick_folder();

    if let Some(path) = result {
        tracing::info!("Path selected: {}", path.display());
        Ok(Some(path))
    } else {
        tracing::debug!("Path selection cancelled");
        Ok(None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_settings_validation() {
        let mut settings = SettingsData {
            fcx_mode: true,
            show_formid_values: false,
            stat_logging: true,
            update_check: true,
            vr_mode: false,
            auto_switch_to_results: true,
            move_unsolved_logs: false,
            simplify_logs: false,
            game_root: "".to_string(),
            docs_root: "".to_string(),
            ini_folder: "".to_string(),
            mods_folder: "".to_string(),
            scan_custom: "".to_string(),
        };

        // Empty game root should fail
        assert!(settings.validate().is_err());

        // Set a valid game root (current directory for test)
        settings.game_root = std::env::current_dir()
            .unwrap()
            .to_string_lossy()
            .to_string();

        // Should pass now
        assert!(settings.validate().is_ok());
    }

    #[test]
    fn test_invalid_path_validation() {
        let settings = SettingsData {
            fcx_mode: false,
            show_formid_values: false,
            stat_logging: false,
            update_check: true,
            vr_mode: false,
            auto_switch_to_results: true,
            move_unsolved_logs: false,
            simplify_logs: false,
            game_root: "C:\\NonExistentPath\\Game".to_string(),
            docs_root: "".to_string(),
            ini_folder: "".to_string(),
            mods_folder: "".to_string(),
            scan_custom: "".to_string(),
        };

        // Invalid game root should fail
        assert!(settings.validate().is_err());
    }
}
