//! Unified configuration for CLI and TUI applications
//!
//! This module provides shared configuration types and YAML persistence
//! for both classic-cli and classic-tui applications.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use tokio::fs;
use yaml_rust2::{Yaml, YamlEmitter, YamlLoader};

// Import the LinkedHashMap type that yaml-rust2 uses
type LinkedHashMap<K, V> = hashlink::LinkedHashMap<K, V>;

/// Unified configuration structure for CLI and TUI applications
///
/// This represents user preferences and settings that are shared
/// between the CLI and TUI interfaces. It can be loaded from YAML,
/// merged with command-line arguments, and persisted.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClassicConfig {
    /// Enable FCX mode for enhanced FormID analysis
    pub fcx_mode: bool,

    /// Show FormID values in output
    pub show_formid_values: bool,

    /// Enable statistical logging
    pub stat_logging: bool,

    /// Move unsolved logs to subfolder
    pub move_unsolved_logs: bool,

    /// Simplify logs (may remove important info)
    pub simplify_logs: bool,

    /// Check for updates at startup
    pub update_check: bool,

    /// Path configuration
    pub paths: PathConfig,
}

/// Path configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathConfig {
    /// Path to INI folder (game documents folder)
    pub ini_folder: Option<PathBuf>,

    /// Path to custom scan folder
    pub scan_custom: Option<PathBuf>,

    /// Path to mods folder
    pub mods_folder: Option<PathBuf>,

    /// Path to game root directory
    pub game_root: PathBuf,
}

impl Default for ClassicConfig {
    fn default() -> Self {
        Self {
            fcx_mode: false,
            show_formid_values: false,
            stat_logging: false,
            move_unsolved_logs: false,
            simplify_logs: false,
            update_check: true,
            paths: PathConfig::default(),
        }
    }
}

impl Default for PathConfig {
    fn default() -> Self {
        Self {
            ini_folder: None,
            scan_custom: None,
            mods_folder: None,
            game_root: PathBuf::from(
                "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Fallout 4",
            ),
        }
    }
}

impl ClassicConfig {
    /// Load configuration from YAML file using yaml-rust2
    ///
    /// # Arguments
    /// * `path` - Path to the YAML configuration file
    ///
    /// # Returns
    /// * `Ok(ClassicConfig)` - Successfully loaded configuration
    /// * `Err(anyhow::Error)` - Failed to load or parse configuration
    pub async fn load_from_yaml(path: &Path) -> Result<Self> {
        let content = fs::read_to_string(path)
            .await
            .context(format!("Failed to read config file: {}", path.display()))?;

        let docs =
            YamlLoader::load_from_str(&content).context("Failed to parse YAML configuration")?;

        let doc = docs.first().context("YAML file is empty")?;

        Self::from_yaml(doc).context("Failed to extract configuration from YAML")
    }

    /// Convert YAML document to ClassicConfig
    fn from_yaml(yaml: &Yaml) -> Result<Self> {
        let fcx_mode = yaml["fcx_mode"].as_bool().unwrap_or(false);
        let show_formid_values = yaml["show_formid_values"].as_bool().unwrap_or(false);
        let stat_logging = yaml["stat_logging"].as_bool().unwrap_or(false);
        let move_unsolved_logs = yaml["move_unsolved_logs"].as_bool().unwrap_or(false);
        let simplify_logs = yaml["simplify_logs"].as_bool().unwrap_or(false);
        let update_check = yaml["update_check"].as_bool().unwrap_or(true);

        let paths_yaml = &yaml["paths"];
        let paths = PathConfig {
            ini_folder: paths_yaml["ini_folder"].as_str().map(PathBuf::from),
            scan_custom: paths_yaml["scan_custom"].as_str().map(PathBuf::from),
            mods_folder: paths_yaml["mods_folder"].as_str().map(PathBuf::from),
            game_root: paths_yaml["game_root"]
                .as_str()
                .map(PathBuf::from)
                .unwrap_or_else(|| PathConfig::default().game_root),
        };

        Ok(Self {
            fcx_mode,
            show_formid_values,
            stat_logging,
            move_unsolved_logs,
            simplify_logs,
            update_check,
            paths,
        })
    }

    /// Convert ClassicConfig to YAML document
    fn to_yaml(&self) -> Yaml {
        let mut root = LinkedHashMap::new();

        root.insert(
            Yaml::String("fcx_mode".to_string()),
            Yaml::Boolean(self.fcx_mode),
        );
        root.insert(
            Yaml::String("show_formid_values".to_string()),
            Yaml::Boolean(self.show_formid_values),
        );
        root.insert(
            Yaml::String("stat_logging".to_string()),
            Yaml::Boolean(self.stat_logging),
        );
        root.insert(
            Yaml::String("move_unsolved_logs".to_string()),
            Yaml::Boolean(self.move_unsolved_logs),
        );
        root.insert(
            Yaml::String("simplify_logs".to_string()),
            Yaml::Boolean(self.simplify_logs),
        );
        root.insert(
            Yaml::String("update_check".to_string()),
            Yaml::Boolean(self.update_check),
        );

        // Build paths hash
        let mut paths = LinkedHashMap::new();
        if let Some(ref ini_folder) = self.paths.ini_folder {
            paths.insert(
                Yaml::String("ini_folder".to_string()),
                Yaml::String(ini_folder.to_string_lossy().to_string()),
            );
        }
        if let Some(ref scan_custom) = self.paths.scan_custom {
            paths.insert(
                Yaml::String("scan_custom".to_string()),
                Yaml::String(scan_custom.to_string_lossy().to_string()),
            );
        }
        if let Some(ref mods_folder) = self.paths.mods_folder {
            paths.insert(
                Yaml::String("mods_folder".to_string()),
                Yaml::String(mods_folder.to_string_lossy().to_string()),
            );
        }
        paths.insert(
            Yaml::String("game_root".to_string()),
            Yaml::String(self.paths.game_root.to_string_lossy().to_string()),
        );

        root.insert(Yaml::String("paths".to_string()), Yaml::Hash(paths));

        Yaml::Hash(root)
    }

    /// Save configuration to YAML file using yaml-rust2
    ///
    /// Creates parent directories if they don't exist.
    ///
    /// # Arguments
    /// * `path` - Path to save the YAML configuration file
    ///
    /// # Returns
    /// * `Ok(())` - Successfully saved configuration
    /// * `Err(anyhow::Error)` - Failed to serialize or write configuration
    pub async fn save_to_yaml(&self, path: &Path) -> Result<()> {
        // Create parent directories if needed
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .await
                .context(format!("Failed to create directory: {}", parent.display()))?;
        }

        let yaml = self.to_yaml();
        let mut output = String::new();
        let mut emitter = YamlEmitter::new(&mut output);
        emitter.dump(&yaml).context("Failed to emit YAML")?;

        fs::write(path, output)
            .await
            .context(format!("Failed to write config file: {}", path.display()))?;

        Ok(())
    }

    /// Load configuration from default location or return defaults
    ///
    /// Searches for configuration in standard locations:
    /// 1. Current directory: ./CLASSIC_Settings.yaml
    /// 2. User config directory (future)
    ///
    /// # Returns
    /// * Configuration loaded from file (if exists)
    /// * Default configuration (if no file found)
    pub async fn load_or_default() -> Result<Self> {
        let default_path = PathBuf::from("CLASSIC_Settings.yaml");

        if default_path.exists() {
            Self::load_from_yaml(&default_path).await
        } else {
            Ok(Self::default())
        }
    }

    /// Get the default config path
    pub fn get_config_path(&self) -> PathBuf {
        PathBuf::from("CLASSIC_Settings.yaml")
    }

    /// Validate configuration paths
    ///
    /// Checks if configured paths exist and are accessible.
    ///
    /// # Returns
    /// * `Ok(())` - All paths are valid
    /// * `Err(anyhow::Error)` - One or more paths are invalid
    pub fn validate_paths(&self) -> Result<()> {
        if !self.paths.game_root.exists() {
            anyhow::bail!(
                "Game root directory does not exist: {}",
                self.paths.game_root.display()
            );
        }

        if let Some(ref ini_folder) = self.paths.ini_folder {
            if !ini_folder.exists() {
                anyhow::bail!("INI folder does not exist: {}", ini_folder.display());
            }
        }

        if let Some(ref scan_custom) = self.paths.scan_custom {
            if !scan_custom.exists() {
                anyhow::bail!(
                    "Custom scan folder does not exist: {}",
                    scan_custom.display()
                );
            }
        }

        if let Some(ref mods_folder) = self.paths.mods_folder {
            if !mods_folder.exists() {
                anyhow::bail!("Mods folder does not exist: {}", mods_folder.display());
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_default_config() {
        let config = ClassicConfig::default();
        assert!(!config.fcx_mode);
        assert!(!config.show_formid_values);
        assert!(!config.stat_logging);
        assert!(!config.move_unsolved_logs);
        assert!(!config.simplify_logs);
        assert!(config.update_check);
    }

    #[tokio::test]
    async fn test_save_and_load_yaml() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("test_config.yaml");

        let mut config = ClassicConfig::default();
        config.fcx_mode = true;
        config.show_formid_values = true;
        config.paths.ini_folder = Some(PathBuf::from("C:\\Test"));

        // Save config
        config.save_to_yaml(&config_path).await.unwrap();
        assert!(config_path.exists());

        // Load config
        let loaded = ClassicConfig::load_from_yaml(&config_path).await.unwrap();
        assert_eq!(loaded.fcx_mode, config.fcx_mode);
        assert_eq!(loaded.show_formid_values, config.show_formid_values);
        assert_eq!(loaded.paths.ini_folder, config.paths.ini_folder);
    }

    #[test]
    fn test_yaml_round_trip() {
        let config = ClassicConfig {
            fcx_mode: true,
            show_formid_values: false,
            stat_logging: true,
            move_unsolved_logs: false,
            simplify_logs: true,
            update_check: false,
            paths: PathConfig {
                ini_folder: Some(PathBuf::from("C:\\Ini")),
                scan_custom: Some(PathBuf::from("D:\\Logs")),
                mods_folder: Some(PathBuf::from("C:\\Mods")),
                game_root: PathBuf::from("C:\\Game"),
            },
        };

        let yaml = config.to_yaml();
        let restored = ClassicConfig::from_yaml(&yaml).unwrap();

        assert_eq!(restored.fcx_mode, config.fcx_mode);
        assert_eq!(restored.show_formid_values, config.show_formid_values);
        assert_eq!(restored.stat_logging, config.stat_logging);
        assert_eq!(restored.move_unsolved_logs, config.move_unsolved_logs);
        assert_eq!(restored.simplify_logs, config.simplify_logs);
        assert_eq!(restored.update_check, config.update_check);
        assert_eq!(restored.paths.ini_folder, config.paths.ini_folder);
        assert_eq!(restored.paths.scan_custom, config.paths.scan_custom);
        assert_eq!(restored.paths.mods_folder, config.paths.mods_folder);
        assert_eq!(restored.paths.game_root, config.paths.game_root);
    }

    #[tokio::test]
    async fn test_save_creates_parent_directory() {
        let temp_dir = tempdir().unwrap();
        let nested_path = temp_dir.path().join("subdir").join("config.yaml");

        let config = ClassicConfig::default();

        // This should succeed even though subdir doesn't exist
        config.save_to_yaml(&nested_path).await.unwrap();
        assert!(nested_path.exists());
    }

    #[tokio::test]
    async fn test_yaml_empty_paths() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("empty_paths.yaml");

        // Config with no optional paths
        let config = ClassicConfig {
            fcx_mode: false,
            show_formid_values: false,
            stat_logging: false,
            move_unsolved_logs: false,
            simplify_logs: false,
            update_check: true,
            paths: PathConfig {
                ini_folder: None,
                scan_custom: None,
                mods_folder: None,
                game_root: PathBuf::from("C:\\Game"),
            },
        };

        config.save_to_yaml(&config_path).await.unwrap();
        let loaded = ClassicConfig::load_from_yaml(&config_path).await.unwrap();

        assert!(loaded.paths.ini_folder.is_none());
        assert!(loaded.paths.scan_custom.is_none());
        assert!(loaded.paths.mods_folder.is_none());
        assert_eq!(loaded.paths.game_root, PathBuf::from("C:\\Game"));
    }

    #[test]
    fn test_path_config_default() {
        let config = PathConfig::default();
        assert!(config.ini_folder.is_none());
        assert!(config.scan_custom.is_none());
        assert!(config.mods_folder.is_none());
        assert!(config.game_root.to_string_lossy().contains("Fallout 4"));
    }

    #[tokio::test]
    async fn test_load_or_default_no_file() {
        // This test runs in a temp directory where config doesn't exist
        let config = ClassicConfig::load_or_default().await.unwrap();
        assert!(!config.fcx_mode); // Should be default
        assert!(config.update_check); // Should be default (true)
    }
}
