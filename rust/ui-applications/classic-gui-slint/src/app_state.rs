//! Application state management for CLASSIC Slint GUI
//!
//! This module provides a thread-safe, shared application state that holds
//! configuration, paths, and runtime settings accessible to all handlers.

use anyhow::{Context, Result};
use classic_config_core::{ClassicConfig, YamlSource};
use parking_lot::RwLock;
use std::path::PathBuf;
use std::sync::Arc;

/// Global application state shared across all GUI components
///
/// This struct holds all configuration and runtime state needed by the GUI:
/// - Game selection (Fallout4, Skyrim, etc.)
/// - File paths (game root, docs, mods, etc.)
/// - User preferences
/// - Runtime settings
///
/// # Thread Safety
/// Wrapped in `Arc<RwLock<>>` for safe concurrent access from UI callbacks.
///
/// # Usage
/// ```rust,no_run
/// use classic_gui_slint::AppState;
///
/// // Load at startup
/// let state = AppState::load().await?;
///
/// // Access from handlers
/// let game_path = state.read().game_root().clone();
/// let game = state.read().game_name();
/// ```
#[derive(Debug, Clone)]
pub struct AppState {
    /// Game selection (e.g., "Fallout4", "Skyrim")
    game: String,

    /// Loaded configuration from YAML files
    config: ClassicConfig,

    /// Mods folder path (from UI or config)
    mods_folder: Option<PathBuf>,

    /// Custom scan folder path (from UI or config)
    scan_folder: Option<PathBuf>,
}

impl AppState {
    /// Load application state at startup
    ///
    /// This performs the following initialization:
    /// 1. Load ClassicConfig from CLASSIC_Settings.yaml (or defaults)
    /// 2. Detect/load game paths from GameLocal YAML
    /// 3. Initialize runtime state
    ///
    /// # Returns
    /// * `Ok(Arc<RwLock<AppState>>)` - Thread-safe shared state
    /// * `Err(anyhow::Error)` - Failed to load configuration
    ///
    /// # Examples
    /// ```rust,no_run
    /// let state = AppState::load().await?;
    /// ```
    pub async fn load() -> Result<Arc<RwLock<Self>>> {
        // Load base configuration
        let mut config = ClassicConfig::load_or_default()
            .await
            .context("Failed to load CLASSIC configuration")?;

        // Default game selection (TODO: Load from settings or last used)
        let game = "Fallout4".to_string();

        // Load game-specific paths from GameLocal YAML
        config
            .load_local_yaml_paths(&game)
            .await
            .context("Failed to load game paths from Local YAML")?;

        tracing::info!(
            "Loaded configuration for {} - Game root: {}",
            game,
            config.paths.game_root.display()
        );

        let state = Self {
            game,
            config,
            mods_folder: None,
            scan_folder: None,
        };

        Ok(Arc::new(RwLock::new(state)))
    }

    /// Get the current game name (e.g., "Fallout4", "Skyrim")
    pub fn game_name(&self) -> &str {
        &self.game
    }

    /// Get the game root directory path
    pub fn game_root(&self) -> &PathBuf {
        &self.config.paths.game_root
    }

    /// Get the game documents directory path
    pub fn docs_root(&self) -> Option<&PathBuf> {
        self.config.paths.docs_root.as_ref()
    }

    /// Get the mods folder path
    pub fn mods_folder(&self) -> Option<&PathBuf> {
        self.mods_folder
            .as_ref()
            .or(self.config.paths.mods_folder.as_ref())
    }

    /// Get the custom scan folder path
    pub fn scan_folder(&self) -> Option<&PathBuf> {
        self.scan_folder
            .as_ref()
            .or(self.config.paths.scan_custom.as_ref())
    }

    /// Get the INI folder path
    #[allow(dead_code)]
    pub fn ini_folder(&self) -> Option<&PathBuf> {
        self.config.paths.ini_folder.as_ref()
    }

    /// Set the mods folder path (from UI)
    pub fn set_mods_folder(&mut self, path: PathBuf) {
        self.mods_folder = Some(path);
    }

    /// Set the custom scan folder path (from UI)
    pub fn set_scan_folder(&mut self, path: PathBuf) {
        self.scan_folder = Some(path);
    }

    /// Set FCX mode setting
    #[allow(dead_code)]
    pub fn set_fcx_mode(&mut self, enabled: bool) {
        self.config.fcx_mode = enabled;
    }

    /// Set show FormID values setting
    #[allow(dead_code)]
    pub fn set_show_formid_values(&mut self, enabled: bool) {
        self.config.show_formid_values = enabled;
    }

    /// Set stat logging setting
    #[allow(dead_code)]
    pub fn set_stat_logging(&mut self, enabled: bool) {
        self.config.stat_logging = enabled;
    }

    /// Set move unsolved logs setting
    #[allow(dead_code)]
    pub fn set_move_unsolved_logs(&mut self, enabled: bool) {
        self.config.move_unsolved_logs = enabled;
    }

    /// Set simplify logs setting
    #[allow(dead_code)]
    pub fn set_simplify_logs(&mut self, enabled: bool) {
        self.config.simplify_logs = enabled;
    }

    /// Set update check setting
    #[allow(dead_code)]
    pub fn set_update_check(&mut self, enabled: bool) {
        self.config.update_check = enabled;
    }

    /// Set VR mode setting
    #[allow(dead_code)]
    pub fn set_vr_mode(&mut self, enabled: bool) {
        self.config.vr_mode = enabled;
    }

    /// Set auto-switch to results tab setting
    #[allow(dead_code)]
    pub fn set_auto_switch_to_results(&mut self, enabled: bool) {
        self.config.auto_switch_to_results = enabled;
    }

    /// Set game root path
    #[allow(dead_code)]
    pub fn set_game_root(&mut self, path: PathBuf) {
        self.config.paths.game_root = path;
    }

    /// Set docs root path
    #[allow(dead_code)]
    pub fn set_docs_root(&mut self, path: Option<PathBuf>) {
        self.config.paths.docs_root = path;
    }

    /// Set INI folder path
    #[allow(dead_code)]
    pub fn set_ini_folder(&mut self, path: Option<PathBuf>) {
        self.config.paths.ini_folder = path;
    }

    /// Get FCX mode setting
    pub fn fcx_mode(&self) -> bool {
        self.config.fcx_mode
    }

    /// Get show FormID values setting
    #[allow(dead_code)]
    pub fn show_formid_values(&self) -> bool {
        self.config.show_formid_values
    }

    /// Get stat logging setting
    #[allow(dead_code)]
    pub fn stat_logging(&self) -> bool {
        self.config.stat_logging
    }

    /// Get move unsolved logs setting
    #[allow(dead_code)]
    pub fn move_unsolved_logs(&self) -> bool {
        self.config.move_unsolved_logs
    }

    /// Get simplify logs setting
    #[allow(dead_code)]
    pub fn simplify_logs(&self) -> bool {
        self.config.simplify_logs
    }

    /// Get update check setting
    #[allow(dead_code)]
    pub fn update_check(&self) -> bool {
        self.config.update_check
    }

    /// Get VR mode setting
    #[allow(dead_code)]
    pub fn vr_mode(&self) -> bool {
        self.config.vr_mode
    }

    /// Get auto-switch to results tab setting
    #[allow(dead_code)]
    pub fn auto_switch_to_results(&self) -> bool {
        self.config.auto_switch_to_results
    }

    /// Validate that all required paths exist
    ///
    /// # Returns
    /// * `Ok(())` - All paths are valid
    /// * `Err(anyhow::Error)` - One or more paths are invalid
    #[allow(dead_code)]
    pub fn validate_paths(&self) -> Result<()> {
        self.config.validate_paths()
    }

    /// Save current configuration to YAML file
    #[allow(dead_code)]
    pub async fn save_config(&self) -> Result<()> {
        let config_path = self.config.get_config_path();
        self.config
            .save_to_yaml(&config_path)
            .await
            .context("Failed to save configuration")
    }

    /// Get config data for external saving (avoids holding lock across await)
    #[allow(dead_code)]
    pub fn get_config_for_save(&self) -> (PathBuf, classic_config_core::ClassicConfig) {
        (self.config.get_config_path(), self.config.clone())
    }

    /// Reload configuration from disk
    ///
    /// This is useful if configuration was modified externally.
    #[allow(dead_code)]
    pub async fn reload(&mut self) -> Result<()> {
        self.config = ClassicConfig::load_or_default().await?;
        self.config.load_local_yaml_paths(&self.game).await?;
        Ok(())
    }

    /// Load YAML data for a specific source
    ///
    /// Helper method to load YAML files using YamlSource enum.
    ///
    /// # Arguments
    /// * `source` - The YAML source to load
    ///
    /// # Examples
    /// ```rust,no_run
    /// let yaml = state.load_yaml(YamlSource::Game).await?;
    /// ```
    #[allow(dead_code)]
    pub async fn load_yaml(&self, source: YamlSource) -> Result<yaml_rust2::Yaml> {
        source.load(&self.game).await
    }
}

/// Type alias for the shared application state
pub type SharedAppState = Arc<RwLock<AppState>>;

impl Default for AppState {
    /// Create a default AppState with fallback configuration
    ///
    /// This is used when configuration loading fails at startup.
    /// Some features may not work with default configuration.
    fn default() -> Self {
        Self {
            game: "Fallout4".to_string(),
            config: ClassicConfig::default(),
            mods_folder: None,
            scan_folder: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_app_state_creation() {
        // This test requires valid configuration files
        // Skip if not available
        if !PathBuf::from("CLASSIC Data").exists() {
            return;
        }

        let state = AppState::load().await;
        assert!(state.is_ok(), "Failed to load app state");

        let state = state.unwrap();
        let state_guard = state.read();
        assert_eq!(state_guard.game_name(), "Fallout4");
        assert!(!state_guard.game_root().as_os_str().is_empty());
    }

    #[tokio::test]
    async fn test_path_accessors() {
        let mut config = ClassicConfig::default();
        config.paths.mods_folder = Some(PathBuf::from("test_mods"));
        config.paths.scan_custom = Some(PathBuf::from("test_scan"));

        let state = AppState {
            game: "TestGame".to_string(),
            config,
            mods_folder: None,
            scan_folder: None,
        };

        assert_eq!(state.game_name(), "TestGame");
        assert_eq!(state.mods_folder(), Some(&PathBuf::from("test_mods")));
        assert_eq!(state.scan_folder(), Some(&PathBuf::from("test_scan")));
    }

    #[tokio::test]
    async fn test_path_override() {
        let config = ClassicConfig::default();
        let mut state = AppState {
            game: "TestGame".to_string(),
            config,
            mods_folder: None,
            scan_folder: None,
        };

        // Set override paths
        state.set_mods_folder(PathBuf::from("override_mods"));
        state.set_scan_folder(PathBuf::from("override_scan"));

        // Override paths take precedence
        assert_eq!(state.mods_folder(), Some(&PathBuf::from("override_mods")));
        assert_eq!(state.scan_folder(), Some(&PathBuf::from("override_scan")));
    }
}
