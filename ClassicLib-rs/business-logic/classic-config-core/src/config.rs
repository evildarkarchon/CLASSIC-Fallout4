//! Unified configuration for CLI and TUI applications
//!
//! This module provides shared configuration types and YAML persistence
//! for both classic-cli and classic-tui applications.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use tokio::fs;
use yaml_rust2::{Yaml, YamlEmitter, YamlLoader};

// Import the LinkedHashMap type that yaml-rust2 uses
type LinkedHashMap<K, V> = hashlink::LinkedHashMap<K, V>;

const DEFAULT_CONFIG_FILENAME: &str = "CLASSIC Settings.yaml";
const LEGACY_CONFIG_FILENAME: &str = "CLASSIC_Settings.yaml";

/// YAML file source identifier - mirrors Python's YAML enum
///
/// This enum provides a single source of truth for YAML file locations
/// throughout the application, similar to Python's `ClassicLib.Constants.YAML`.
///
/// # Examples
/// ```rust,no_run
/// use classic_config_core::YamlSource;
///
/// let path = YamlSource::Game.path("Fallout4");
/// // Returns: "CLASSIC Data/databases/CLASSIC Fallout4.yaml"
///
/// let local_path = YamlSource::GameLocal.path("Skyrim");
/// // Returns: "CLASSIC Data/CLASSIC Skyrim Local.yaml"
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum YamlSource {
    /// Main database: CLASSIC Data/databases/CLASSIC Main.yaml
    Main,

    /// User settings: CLASSIC Settings.yaml
    Settings,

    /// Ignore list: CLASSIC Ignore.yaml
    Ignore,

    /// Game database: CLASSIC Data/databases/CLASSIC {game}.yaml
    Game,

    /// Game local config: CLASSIC Data/CLASSIC {game} Local.yaml
    GameLocal,

    /// Test settings: tests/test_settings.yaml
    Test,

    /// Cache: User config dir/CLASSIC-Fallout4/cache.yaml
    Cache,
}

impl YamlSource {
    /// Get the file path for this YAML source
    ///
    /// # Arguments
    /// * `game` - Game name (e.g., "Fallout4", "Skyrim"). Required for `Game` and `GameLocal` sources.
    ///
    /// # Returns
    /// PathBuf to the YAML file
    ///
    /// # Panics
    /// Panics if `game` is empty for `Game` or `GameLocal` sources
    pub fn path(&self, game: &str) -> PathBuf {
        match self {
            Self::Main => PathBuf::from("CLASSIC Data/databases/CLASSIC Main.yaml"),
            Self::Settings => PathBuf::from("CLASSIC Settings.yaml"),
            Self::Ignore => PathBuf::from("CLASSIC Ignore.yaml"),
            Self::Game => {
                assert!(!game.is_empty(), "Game name required for YamlSource::Game");
                PathBuf::from(format!("CLASSIC Data/databases/CLASSIC {}.yaml", game))
            }
            Self::GameLocal => {
                assert!(
                    !game.is_empty(),
                    "Game name required for YamlSource::GameLocal"
                );
                PathBuf::from(format!("CLASSIC Data/CLASSIC {} Local.yaml", game))
            }
            Self::Test => PathBuf::from("tests/test_settings.yaml"),
            Self::Cache => {
                // TODO: Get actual user config directory
                PathBuf::from("CLASSIC-Fallout4/cache.yaml")
            }
        }
    }

    /// Get the display name for this YAML source
    ///
    /// Note: For Game and GameLocal, this returns a generic name.
    /// Use `display_name_with_game()` to get the actual file name with game substitution.
    pub fn display_name(&self) -> &'static str {
        match self {
            Self::Main => "Main Database",
            Self::Settings => "Settings",
            Self::Ignore => "Ignore List",
            Self::Game => "Game Database",
            Self::GameLocal => "Game Local Config",
            Self::Test => "Test Settings",
            Self::Cache => "Cache",
        }
    }

    /// Get the display name with game substitution (for Game and GameLocal sources)
    ///
    /// # Arguments
    /// * `game` - Game name (e.g., "Fallout4", "Skyrim")
    ///
    /// # Examples
    /// ```
    /// use classic_config_core::YamlSource;
    ///
    /// assert_eq!(YamlSource::Game.display_name_with_game("Fallout4"), "Fallout4 Database");
    /// assert_eq!(YamlSource::GameLocal.display_name_with_game("Skyrim"), "Skyrim Local Config");
    /// ```
    pub fn display_name_with_game(&self, game: &str) -> String {
        match self {
            Self::Main => "Main Database".to_string(),
            Self::Settings => "Settings".to_string(),
            Self::Ignore => "Ignore List".to_string(),
            Self::Game => format!("{} Database", game),
            Self::GameLocal => format!("{} Local Config", game),
            Self::Test => "Test Settings".to_string(),
            Self::Cache => "Cache".to_string(),
        }
    }

    /// Load and parse YAML file from this source
    ///
    /// # Arguments
    /// * `game` - Game name (required for Game/GameLocal sources, empty string for others)
    ///
    /// # Returns
    /// * `Ok(Yaml)` - Parsed YAML document
    /// * `Err(anyhow::Error)` - Failed to read or parse
    ///
    /// # Examples
    /// ```rust,no_run
    /// use classic_config_core::YamlSource;
    ///
    /// # async fn example() -> anyhow::Result<()> {
    /// // Load game-specific YAML
    /// let yaml = YamlSource::Game.load("Fallout4").await?;
    ///
    /// // Load non-game YAML (game parameter ignored)
    /// let settings = YamlSource::Settings.load("").await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn load(&self, game: &str) -> Result<Yaml> {
        let path = self.path(game);
        let display = if game.is_empty() {
            self.display_name().to_string()
        } else {
            self.display_name_with_game(game)
        };

        let content = fs::read_to_string(&path)
            .await
            .with_context(|| format!("Failed to read {}: {}", display, path.display()))?;

        let docs = YamlLoader::load_from_str(&content)
            .with_context(|| format!("Failed to parse {}: {}", display, path.display()))?;

        let doc = docs
            .first()
            .cloned()
            .ok_or_else(|| anyhow::anyhow!("{} file is empty: {}", display, path.display()))?;

        Ok(doc)
    }
}

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

    /// Enable VR mode (for VR-specific game configurations)
    ///
    /// Note: Kept for backward compatibility. New code should use `game_version`
    /// instead. Legacy configs with `vr_mode: true` are auto-migrated to
    /// `game_version: "VR"` on load.
    pub vr_mode: bool,

    /// Game version selection: "auto", "Original", "NextGen", or "VR"
    ///
    /// Stored lowercase "auto" in YAML, display as "Auto" in UI.
    /// When set to "auto", the GUI runs detection and shows a hint.
    pub game_version: String,

    /// Update source: "github" or "both"
    ///
    /// Controls where the application checks for updates.
    pub update_source: String,

    /// Automatically switch to Results tab after scan completion
    pub auto_switch_to_results: bool,

    /// Auto-refresh interval for file watcher in milliseconds
    pub auto_refresh_interval_ms: u64,

    /// Path configuration
    pub paths: PathConfig,

    /// User-configured FormID databases per game
    ///
    /// Key: game name (e.g., "Fallout4"), Value: list of relative or absolute paths.
    /// Relative paths are resolved against the data directory at runtime.
    pub formid_databases: HashMap<String, Vec<PathBuf>>,
}

/// Configuration structure for defining various file system paths related to a game.
///
/// The `PathConfig` struct contains paths to important directories or files
/// required for managing the game's configuration, mods, documents, and related
/// resources.
///
/// # Fields
///
/// * `ini_folder` - An optional path to the folder containing INI configuration files.
///   Typically, this corresponds to the game's documents folder.
///
/// * `scan_custom` - An optional path to a custom folder location to scan for additional resources.
///   This is helpful for specifying user-defined locations outside standard directories.
///
/// * `mods_folder` - An optional path to the folder containing mods for the game. This is the directory
///   where custom modifications for the game are stored or loaded from.
///
/// * `game_root` - The path to the root directory of the game installation. It serves as the main location
///   for the game's necessary files and executables.
///
/// * `docs_root` - An optional path to the game's documents root directory. This path is typically defined in a separate
///   `Local.yaml` configuration file. It may contain user data, save files, or other associated documents.
///
/// # Note
///
/// All paths represented in this structure use [`PathBuf`], which provides an owned, mutable path
/// representation that's platform-independent.
///
/// This struct is serializable and deserializable using the `Serialize` and `Deserialize` traits
/// (from [serde](https://serde.rs/)) and supports cloning and debugging with the respective traits.
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

    /// Path to game documents root directory (from Local.yaml)
    pub docs_root: Option<PathBuf>,
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
            vr_mode: false,
            game_version: "auto".to_string(),
            update_source: "github".to_string(),
            auto_switch_to_results: true, // Enable by default for better UX
            auto_refresh_interval_ms: 5000,
            paths: PathConfig::default(),
            formid_databases: HashMap::new(),
        }
    }
}

impl Default for PathConfig {
    fn default() -> Self {
        Self {
            ini_folder: None,
            scan_custom: None,
            mods_folder: None,
            // NO hardcoded paths - must be loaded from config or Local.yaml
            game_root: PathBuf::new(),
            docs_root: None,
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
        let vr_mode = yaml["vr_mode"].as_bool().unwrap_or(false);

        // Game version with VR mode migration: if legacy config has vr_mode=true
        // but no game_version key, auto-migrate to game_version="VR"
        let game_version = if yaml["game_version"].is_badvalue() && vr_mode {
            "VR".to_string()
        } else {
            yaml["game_version"].as_str().unwrap_or("auto").to_string()
        };
        let update_source = yaml["update_source"]
            .as_str()
            .unwrap_or("github")
            .to_string();

        let auto_switch_to_results = yaml["auto_switch_to_results"].as_bool().unwrap_or(true);
        let auto_refresh_interval_ms =
            yaml["auto_refresh_interval_ms"].as_i64().unwrap_or(5000) as u64;

        let paths_yaml = &yaml["paths"];
        let paths = PathConfig {
            ini_folder: paths_yaml["ini_folder"].as_str().map(PathBuf::from),
            scan_custom: paths_yaml["scan_custom"].as_str().map(PathBuf::from),
            mods_folder: paths_yaml["mods_folder"].as_str().map(PathBuf::from),
            game_root: paths_yaml["game_root"]
                .as_str()
                .map(PathBuf::from)
                .unwrap_or_else(|| PathConfig::default().game_root),
            docs_root: paths_yaml["docs_root"].as_str().map(PathBuf::from),
        };

        // Parse formid_databases map
        let mut formid_databases = HashMap::new();
        if let Some(db_hash) = yaml["formid_databases"].as_hash() {
            for (game_key, paths_yaml) in db_hash {
                if let Some(game_name) = game_key.as_str() {
                    let mut db_paths = Vec::new();
                    if let Some(arr) = paths_yaml.as_vec() {
                        for item in arr {
                            if let Some(s) = item.as_str() {
                                db_paths.push(PathBuf::from(s));
                            }
                        }
                    }
                    formid_databases.insert(game_name.to_string(), db_paths);
                }
            }
        }

        Ok(Self {
            fcx_mode,
            show_formid_values,
            stat_logging,
            move_unsolved_logs,
            simplify_logs,
            update_check,
            vr_mode,
            game_version,
            update_source,
            auto_switch_to_results,
            auto_refresh_interval_ms,
            paths,
            formid_databases,
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
        root.insert(
            Yaml::String("vr_mode".to_string()),
            Yaml::Boolean(self.vr_mode),
        );
        root.insert(
            Yaml::String("game_version".to_string()),
            Yaml::String(self.game_version.clone()),
        );
        root.insert(
            Yaml::String("update_source".to_string()),
            Yaml::String(self.update_source.clone()),
        );
        root.insert(
            Yaml::String("auto_switch_to_results".to_string()),
            Yaml::Boolean(self.auto_switch_to_results),
        );
        root.insert(
            Yaml::String("auto_refresh_interval_ms".to_string()),
            Yaml::Integer(self.auto_refresh_interval_ms as i64),
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
        if let Some(ref docs_root) = self.paths.docs_root {
            paths.insert(
                Yaml::String("docs_root".to_string()),
                Yaml::String(docs_root.to_string_lossy().to_string()),
            );
        }

        root.insert(Yaml::String("paths".to_string()), Yaml::Hash(paths));

        // Build formid_databases hash
        if !self.formid_databases.is_empty() {
            let mut db_hash = LinkedHashMap::new();
            for (game, db_paths) in &self.formid_databases {
                let arr: Vec<Yaml> = db_paths
                    .iter()
                    .map(|p| Yaml::String(p.to_string_lossy().to_string()))
                    .collect();
                db_hash.insert(Yaml::String(game.clone()), Yaml::Array(arr));
            }
            root.insert(
                Yaml::String("formid_databases".to_string()),
                Yaml::Hash(db_hash),
            );
        }

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

        // Clone path and self for the blocking task
        let path = path.to_path_buf();
        let config = self.clone();

        // Run YAML serialization in blocking thread (YamlEmitter is not Send)
        tokio::task::spawn_blocking(move || {
            let yaml = config.to_yaml();
            let mut output = String::new();
            let mut emitter = YamlEmitter::new(&mut output);
            emitter.dump(&yaml).context("Failed to emit YAML")?;

            std::fs::write(&path, output)
                .context(format!("Failed to write config file: {}", path.display()))?;

            Ok(())
        })
        .await
        .context("YAML serialization task panicked")?
    }

    /// Load configuration from default location or return defaults
    ///
    /// Searches for configuration in standard locations:
    /// 1. Current directory: ./CLASSIC Settings.yaml
    /// 2. Current directory: ./CLASSIC_Settings.yaml (legacy fallback)
    /// 3. User config directory (future)
    ///
    /// # Returns
    /// * Configuration loaded from file (if exists)
    /// * Default configuration (if no file found)
    pub async fn load_or_default() -> Result<Self> {
        let default_paths = [
            PathBuf::from(DEFAULT_CONFIG_FILENAME),
            PathBuf::from(LEGACY_CONFIG_FILENAME),
        ];

        for path in &default_paths {
            if path.exists() {
                return Self::load_from_yaml(path).await;
            }
        }

        Ok(Self::default())
    }

    /// Get the default config path
    pub fn get_config_path(&self) -> PathBuf {
        PathBuf::from(DEFAULT_CONFIG_FILENAME)
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

    /// Load paths from Local.yaml file
    ///
    /// Reads the Local.yaml file and populates game_root and docs_root paths.
    /// The Local.yaml file is expected to be at: CLASSIC Data/CLASSIC {game} Local.yaml
    ///
    /// # Arguments
    /// * `game` - Game name (e.g., "Fallout4", "Skyrim")
    ///
    /// # Returns
    /// * `Ok(())` - Successfully loaded paths
    /// * `Err(anyhow::Error)` - Failed to load or parse Local.yaml
    ///
    /// # Note
    /// This function updates the config in place. If Local.yaml doesn't exist,
    /// this is not an error - the config will retain its current paths.
    pub async fn load_local_yaml_paths(&mut self, game: &str) -> Result<()> {
        let local_yaml_path = YamlSource::GameLocal.path(game);

        // If Local.yaml doesn't exist, that's okay - just return without error
        if !local_yaml_path.exists() {
            return Ok(());
        }

        let content = fs::read_to_string(&local_yaml_path).await.context(format!(
            "Failed to read Local.yaml file: {}",
            local_yaml_path.display()
        ))?;

        let docs = YamlLoader::load_from_str(&content)
            .context("Failed to parse Local.yaml configuration")?;

        let doc = docs.first().context("Local.yaml file is empty")?;

        // Extract paths from Game_Info section
        if let Some(game_root_str) = doc["Game_Info"]["Root_Folder_Game"].as_str() {
            self.paths.game_root = PathBuf::from(game_root_str);
        }

        if let Some(docs_root_str) = doc["Game_Info"]["Root_Folder_Docs"].as_str() {
            self.paths.docs_root = Some(PathBuf::from(docs_root_str));
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use std::sync::OnceLock;
    use tempfile::tempdir;
    use tokio::sync::Mutex;

    fn current_dir_lock() -> &'static Mutex<()> {
        static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
        LOCK.get_or_init(|| Mutex::new(()))
    }

    struct CurrentDirGuard {
        original_dir: PathBuf,
    }

    impl CurrentDirGuard {
        fn change_to(path: &Path) -> Self {
            let original_dir = env::current_dir().unwrap();
            env::set_current_dir(path).unwrap();
            Self { original_dir }
        }
    }

    impl Drop for CurrentDirGuard {
        fn drop(&mut self) {
            env::set_current_dir(&self.original_dir).unwrap();
        }
    }

    #[test]
    fn test_default_config() {
        let config = ClassicConfig::default();
        assert!(!config.fcx_mode);
        assert!(!config.show_formid_values);
        assert!(!config.stat_logging);
        assert!(!config.move_unsolved_logs);
        assert!(!config.simplify_logs);
        assert!(config.update_check);
        assert!(!config.vr_mode);
        assert_eq!(config.game_version, "auto");
        assert_eq!(config.update_source, "github");
    }

    #[tokio::test]
    async fn test_save_and_load_yaml() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("test_config.yaml");

        let mut config = ClassicConfig {
            fcx_mode: true,
            show_formid_values: true,
            ..Default::default()
        };
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
            vr_mode: true,
            game_version: "NextGen".to_string(),
            update_source: "both".to_string(),
            auto_switch_to_results: false,
            auto_refresh_interval_ms: 1000,
            paths: PathConfig {
                ini_folder: Some(PathBuf::from("C:\\Ini")),
                scan_custom: Some(PathBuf::from("D:\\Logs")),
                mods_folder: Some(PathBuf::from("C:\\Mods")),
                game_root: PathBuf::from("C:\\Game"),
                docs_root: Some(PathBuf::from("C:\\Docs")),
            },
            formid_databases: HashMap::from([(
                "Fallout4".to_string(),
                vec![PathBuf::from("databases/FOLON FormIDs.db")],
            )]),
        };

        let yaml = config.to_yaml();
        let restored = ClassicConfig::from_yaml(&yaml).unwrap();

        assert_eq!(restored.fcx_mode, config.fcx_mode);
        assert_eq!(restored.show_formid_values, config.show_formid_values);
        assert_eq!(restored.stat_logging, config.stat_logging);
        assert_eq!(restored.move_unsolved_logs, config.move_unsolved_logs);
        assert_eq!(restored.simplify_logs, config.simplify_logs);
        assert_eq!(restored.update_check, config.update_check);
        assert_eq!(restored.vr_mode, config.vr_mode);
        assert_eq!(restored.game_version, config.game_version);
        assert_eq!(restored.update_source, config.update_source);
        assert_eq!(
            restored.auto_switch_to_results,
            config.auto_switch_to_results
        );
        assert_eq!(
            restored.auto_refresh_interval_ms,
            config.auto_refresh_interval_ms
        );
        assert_eq!(restored.paths.ini_folder, config.paths.ini_folder);
        assert_eq!(restored.paths.scan_custom, config.paths.scan_custom);
        assert_eq!(restored.paths.mods_folder, config.paths.mods_folder);
        assert_eq!(restored.paths.game_root, config.paths.game_root);
        assert_eq!(restored.paths.docs_root, config.paths.docs_root);
        assert_eq!(restored.formid_databases, config.formid_databases);
    }

    #[test]
    fn test_vr_mode_migration() {
        // Simulate a legacy YAML with vr_mode: true but no game_version key
        let yaml_str = "vr_mode: true\nfcx_mode: false\n";
        let docs = YamlLoader::load_from_str(yaml_str).unwrap();
        let yaml = docs.first().unwrap();

        let config = ClassicConfig::from_yaml(yaml).unwrap();

        // Should auto-migrate to game_version "VR"
        assert_eq!(config.game_version, "VR");
        // vr_mode should still be true for backward compat
        assert!(config.vr_mode);
    }

    #[test]
    fn test_vr_mode_no_migration_when_game_version_set() {
        // If game_version is already set, vr_mode should NOT override it
        let yaml_str = "vr_mode: true\ngame_version: Original\n";
        let docs = YamlLoader::load_from_str(yaml_str).unwrap();
        let yaml = docs.first().unwrap();

        let config = ClassicConfig::from_yaml(yaml).unwrap();

        // game_version should remain as explicitly set
        assert_eq!(config.game_version, "Original");
        assert!(config.vr_mode);
    }

    #[test]
    fn test_vr_mode_false_no_migration() {
        // If vr_mode is false and no game_version, should default to "auto"
        let yaml_str = "vr_mode: false\n";
        let docs = YamlLoader::load_from_str(yaml_str).unwrap();
        let yaml = docs.first().unwrap();

        let config = ClassicConfig::from_yaml(yaml).unwrap();

        assert_eq!(config.game_version, "auto");
        assert!(!config.vr_mode);
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
            vr_mode: false,
            game_version: "auto".to_string(),
            update_source: "github".to_string(),
            auto_switch_to_results: true,
            auto_refresh_interval_ms: 5000,
            paths: PathConfig {
                ini_folder: None,
                scan_custom: None,
                mods_folder: None,
                game_root: PathBuf::from("C:\\Game"),
                docs_root: None,
            },
            formid_databases: HashMap::new(),
        };

        config.save_to_yaml(&config_path).await.unwrap();
        let loaded = ClassicConfig::load_from_yaml(&config_path).await.unwrap();

        assert!(loaded.paths.ini_folder.is_none());
        assert!(loaded.paths.scan_custom.is_none());
        assert!(loaded.paths.mods_folder.is_none());
        assert_eq!(loaded.paths.game_root, PathBuf::from("C:\\Game"));
        assert!(loaded.paths.docs_root.is_none());
    }

    #[test]
    fn test_path_config_default() {
        let config = PathConfig::default();
        assert!(config.ini_folder.is_none());
        assert!(config.scan_custom.is_none());
        assert!(config.mods_folder.is_none());
        // Default should be empty - must be loaded from config or Local.yaml
        assert_eq!(config.game_root, PathBuf::new());
        assert!(config.docs_root.is_none());
    }

    #[tokio::test]
    async fn test_load_or_default_no_file() {
        let _lock = current_dir_lock().lock().await;
        let temp_dir = tempdir().unwrap();
        let _cwd_guard = CurrentDirGuard::change_to(temp_dir.path());

        let config = ClassicConfig::load_or_default().await.unwrap();
        assert!(!config.fcx_mode);
        assert!(config.update_check);
    }

    #[tokio::test]
    async fn test_load_or_default_accepts_space_settings_filename() {
        let _lock = current_dir_lock().lock().await;
        let temp_dir = tempdir().unwrap();
        let _cwd_guard = CurrentDirGuard::change_to(temp_dir.path());
        let settings_path = temp_dir.path().join("CLASSIC Settings.yaml");

        std::fs::write(settings_path, "fcx_mode: true\n").unwrap();

        let config = ClassicConfig::load_or_default().await.unwrap();
        assert!(config.fcx_mode);
    }

    #[tokio::test]
    async fn test_load_or_default_accepts_legacy_underscore_settings_filename() {
        let _lock = current_dir_lock().lock().await;
        let temp_dir = tempdir().unwrap();
        let _cwd_guard = CurrentDirGuard::change_to(temp_dir.path());
        let settings_path = temp_dir.path().join("CLASSIC_Settings.yaml");

        std::fs::write(settings_path, "fcx_mode: true\n").unwrap();

        let config = ClassicConfig::load_or_default().await.unwrap();
        assert!(config.fcx_mode);
    }

    #[test]
    fn test_formid_databases_default() {
        let config = ClassicConfig::default();
        assert!(config.formid_databases.is_empty());
    }

    #[test]
    fn test_formid_databases_yaml_round_trip() {
        let mut config = ClassicConfig::default();
        config.formid_databases.insert(
            "Fallout4".to_string(),
            vec![PathBuf::from("databases/FOLON FormIDs.db")],
        );
        config.formid_databases.insert("Skyrim".to_string(), vec![]);

        let yaml = config.to_yaml();
        let restored = ClassicConfig::from_yaml(&yaml).unwrap();

        assert_eq!(restored.formid_databases.len(), 2);
        assert_eq!(
            restored.formid_databases["Fallout4"],
            vec![PathBuf::from("databases/FOLON FormIDs.db")]
        );
        assert!(restored.formid_databases["Skyrim"].is_empty());
    }

    #[test]
    fn test_formid_databases_missing_key_defaults_empty() {
        let yaml_str = "fcx_mode: false\n";
        let docs = YamlLoader::load_from_str(yaml_str).unwrap();
        let yaml = docs.first().unwrap();

        let config = ClassicConfig::from_yaml(yaml).unwrap();
        assert!(config.formid_databases.is_empty());
    }

    #[test]
    fn test_formid_databases_multiple_paths_per_game() {
        let mut config = ClassicConfig::default();
        config.formid_databases.insert(
            "Fallout4".to_string(),
            vec![
                PathBuf::from("databases/FOLON FormIDs.db"),
                PathBuf::from("D:/Custom/My FormIDs.db"),
            ],
        );

        let yaml = config.to_yaml();
        let restored = ClassicConfig::from_yaml(&yaml).unwrap();

        assert_eq!(restored.formid_databases["Fallout4"].len(), 2);
        assert_eq!(
            restored.formid_databases["Fallout4"][0],
            PathBuf::from("databases/FOLON FormIDs.db")
        );
        assert_eq!(
            restored.formid_databases["Fallout4"][1],
            PathBuf::from("D:/Custom/My FormIDs.db")
        );
    }
}
