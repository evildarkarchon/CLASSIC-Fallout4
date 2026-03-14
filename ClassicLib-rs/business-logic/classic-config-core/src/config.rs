//! Unified configuration for CLI and TUI applications
//!
//! This module provides shared configuration types and YAML persistence
//! for both classic-cli and classic-tui applications.

use anyhow::{Context, Result};
use classic_settings_core::load_yaml_merged_async;
use classic_yaml_core::YamlOperations;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use tokio::fs;
use yaml_rust2::{Yaml, YamlEmitter};

// Import the LinkedHashMap type that yaml-rust2 uses
type LinkedHashMap<K, V> = hashlink::LinkedHashMap<K, V>;

const DEFAULT_CONFIG_FILENAME: &str = "CLASSIC Settings.yaml";
const LEGACY_CONFIG_FILENAME: &str = "CLASSIC_Settings.yaml";

fn resolve_application_dir(current_exe: Option<&Path>) -> Option<PathBuf> {
    current_exe.and_then(|path| path.parent().map(Path::to_path_buf))
}

fn application_dir() -> Option<PathBuf> {
    std::env::current_exe()
        .ok()
        .and_then(|path| resolve_application_dir(Some(path.as_path())))
}

fn resolve_user_config_dir(config_dir: Option<&Path>) -> Option<PathBuf> {
    config_dir.map(|dir| dir.join("CLASSIC"))
}

fn user_config_dir() -> Option<PathBuf> {
    let config_dir = dirs::config_dir();
    resolve_user_config_dir(config_dir.as_deref())
}

fn resolve_settings_search_paths(app_dir: Option<&Path>, user_dir: Option<&Path>) -> Vec<PathBuf> {
    let mut paths = Vec::new();

    if let Some(app_dir) = app_dir {
        paths.push(app_dir.join(DEFAULT_CONFIG_FILENAME));
        paths.push(app_dir.join(LEGACY_CONFIG_FILENAME));
    }

    if let Some(user_dir) = user_dir {
        paths.push(user_dir.join(DEFAULT_CONFIG_FILENAME));
        paths.push(user_dir.join(LEGACY_CONFIG_FILENAME));
    }

    paths
}

fn resolve_existing_settings_path(
    app_dir: Option<&Path>,
    user_dir: Option<&Path>,
) -> Option<PathBuf> {
    resolve_settings_search_paths(app_dir, user_dir)
        .into_iter()
        .find(|path| path.exists())
}

fn resolve_preferred_settings_path(app_dir: Option<&Path>, user_dir: Option<&Path>) -> PathBuf {
    if let Some(app_target) = app_dir.map(|dir| dir.join(DEFAULT_CONFIG_FILENAME)) {
        return app_target;
    }

    if let Some(user_target) = user_dir.map(|dir| dir.join(DEFAULT_CONFIG_FILENAME)) {
        return user_target;
    }

    resolve_settings_search_paths(app_dir, user_dir)
        .into_iter()
        .next()
        .unwrap_or_else(|| PathBuf::from(DEFAULT_CONFIG_FILENAME))
}

fn choose_settings_write_path(
    existing_paths: &[PathBuf],
    app_dir: Option<&Path>,
    user_dir: Option<&Path>,
) -> Result<Option<PathBuf>> {
    choose_settings_write_path_with_access(
        existing_paths,
        app_dir,
        user_dir,
        can_update_existing_settings_file,
        can_create_new_settings_file,
    )
}

fn choose_settings_write_path_with_access(
    existing_paths: &[PathBuf],
    app_dir: Option<&Path>,
    user_dir: Option<&Path>,
    can_update_existing: impl Fn(&Path) -> bool,
    can_create_new: impl Fn(&Path) -> bool,
) -> Result<Option<PathBuf>> {
    for candidate in resolve_settings_search_paths(app_dir, user_dir) {
        if existing_paths.iter().any(|path| path == &candidate) && can_update_existing(&candidate) {
            return Ok(Some(candidate));
        }
    }

    if let Some(app_target) = app_dir.map(|dir| dir.join(DEFAULT_CONFIG_FILENAME)) {
        if can_create_new(&app_target) {
            return Ok(Some(app_target));
        }
    }

    if let Some(user_target) = user_dir.map(|dir| dir.join(DEFAULT_CONFIG_FILENAME)) {
        if can_create_new(&user_target) {
            return Ok(Some(user_target));
        }
    }

    Ok(None)
}

fn can_update_existing_settings_file(path: &Path) -> bool {
    std::fs::OpenOptions::new()
        .read(true)
        .write(true)
        .open(path)
        .is_ok()
}

fn can_create_new_settings_file(path: &Path) -> bool {
    let Some(parent) = path.parent() else {
        return false;
    };

    if std::fs::create_dir_all(parent).is_err() {
        return false;
    }

    let probe_name = format!(
        ".classic-write-test-{}-{}.tmp",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or_default()
    );
    let probe_path = parent.join(probe_name);

    match std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&probe_path)
    {
        Ok(file) => {
            drop(file);
            let _ = std::fs::remove_file(probe_path);
            true
        }
        Err(_) => false,
    }
}

fn resolve_settings_write_path(app_dir: Option<&Path>, user_dir: Option<&Path>) -> PathBuf {
    if app_dir.is_none() && user_dir.is_none() {
        return PathBuf::from(DEFAULT_CONFIG_FILENAME);
    }

    let existing_paths: Vec<_> = resolve_settings_search_paths(app_dir, user_dir)
        .into_iter()
        .filter(|path| path.exists())
        .collect();

    choose_settings_write_path(&existing_paths, app_dir, user_dir)
        .ok()
        .flatten()
        .unwrap_or_else(|| resolve_preferred_settings_path(app_dir, user_dir))
}

fn resolve_settings_read_path(app_dir: Option<&Path>, user_dir: Option<&Path>) -> PathBuf {
    resolve_existing_settings_path(app_dir, user_dir)
        .unwrap_or_else(|| resolve_preferred_settings_path(app_dir, user_dir))
}

fn resolve_cache_path(user_dir: Option<&Path>, app_dir: Option<&Path>) -> PathBuf {
    user_dir
        .map(|dir| dir.join("cache.yaml"))
        .or_else(|| app_dir.map(|dir| dir.join("CLASSIC").join("cache.yaml")))
        .unwrap_or_else(|| PathBuf::from("CLASSIC").join("cache.yaml"))
}

async fn load_or_default_from_dirs(
    app_dir: Option<&Path>,
    user_dir: Option<&Path>,
) -> Result<ClassicConfig> {
    for path in resolve_settings_search_paths(app_dir, user_dir) {
        if path.exists() {
            return ClassicConfig::load_from_yaml(&path).await;
        }
    }

    Ok(ClassicConfig::default())
}

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

    /// Cache: User config dir/CLASSIC/cache.yaml
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
            Self::Settings => {
                let app_dir = application_dir();
                let user_dir = user_config_dir();
                resolve_settings_read_path(app_dir.as_deref(), user_dir.as_deref())
            }
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
                let app_dir = application_dir();
                let user_dir = user_config_dir();
                resolve_cache_path(user_dir.as_deref(), app_dir.as_deref())
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

        load_yaml_merged_async(&path)
            .await
            .with_context(|| format!("Failed to load {}: {}", display, path.display()))
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
        let yaml = load_yaml_merged_async(path)
            .await
            .with_context(|| format!("Failed to load merged config YAML: {}", path.display()))?;

        Self::from_yaml(&yaml).context("Failed to extract configuration from YAML")
    }

    /// Convert YAML document to ClassicConfig
    fn from_yaml(yaml: &Yaml) -> Result<Self> {
        let fcx_mode = yaml["fcx_mode"].as_bool().unwrap_or(false);
        let show_formid_values = yaml["show_formid_values"].as_bool().unwrap_or(false);
        let stat_logging = yaml["stat_logging"].as_bool().unwrap_or(false);
        let move_unsolved_logs = yaml["move_unsolved_logs"].as_bool().unwrap_or(false);
        let simplify_logs = yaml["simplify_logs"].as_bool().unwrap_or(false);
        let update_check = yaml["update_check"].as_bool().unwrap_or(true);
        let game_version = yaml["game_version"].as_str().unwrap_or("auto").to_string();
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
    /// 1. Application directory: CLASSIC Settings.yaml
    /// 2. Application directory: CLASSIC_Settings.yaml (legacy fallback)
    /// 3. User config directory: CLASSIC Settings.yaml
    /// 4. User config directory: CLASSIC_Settings.yaml (legacy fallback)
    ///
    /// # Returns
    /// * Configuration loaded from file (if exists)
    /// * Default configuration (if no file found)
    pub async fn load_or_default() -> Result<Self> {
        let app_dir = application_dir();
        let user_dir = user_config_dir();
        load_or_default_from_dirs(app_dir.as_deref(), user_dir.as_deref()).await
    }

    /// Get the default config path
    pub fn get_config_path(&self) -> PathBuf {
        let app_dir = application_dir();
        let user_dir = user_config_dir();
        resolve_settings_write_path(app_dir.as_deref(), user_dir.as_deref())
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

        let doc = load_yaml_merged_async(&local_yaml_path)
            .await
            .with_context(|| {
                format!(
                    "Failed to load Local.yaml file: {}",
                    local_yaml_path.display()
                )
            })?;

        // Extract paths from Game_Info section
        if let Some(game_root_str) = doc["Game_Info"]["Root_Folder_Game"].as_str() {
            self.paths.game_root = PathBuf::from(game_root_str);
        }

        if let Some(docs_root_str) = doc["Game_Info"]["Root_Folder_Docs"].as_str() {
            self.paths.docs_root = Some(PathBuf::from(docs_root_str));
        }

        Ok(())
    }

    /// Save `game_root` and `docs_root` to the game's Local.yaml file.
    ///
    /// Uses the standard `YamlSource::GameLocal` location for the provided game.
    /// If both paths are empty, this is a no-op.
    pub async fn save_local_yaml_paths(&self, game: &str) -> Result<()> {
        let local_yaml_path = YamlSource::GameLocal.path(game);
        self.save_local_yaml_paths_to(&local_yaml_path).await
    }

    /// Save `game_root` and `docs_root` to an explicit Local.yaml path.
    ///
    /// Creates parent directories as needed and creates the file when it does not
    /// already exist. Existing YAML content is merged first so unrelated keys under
    /// `Game_Info` are preserved.
    pub async fn save_local_yaml_paths_to(&self, path: &Path) -> Result<()> {
        if self.paths.game_root.as_os_str().is_empty() && self.paths.docs_root.is_none() {
            return Ok(());
        }

        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .await
                .with_context(|| format!("Failed to create directory: {}", parent.display()))?;
        }

        let yaml_ops = YamlOperations::new();
        let mut yaml = if path.exists() {
            load_yaml_merged_async(path).await.with_context(|| {
                format!("Failed to load Local.yaml file for save: {}", path.display())
            })?
        } else {
            Yaml::Hash(yaml_rust2::yaml::Hash::new())
        };

        if !self.paths.game_root.as_os_str().is_empty() {
            yaml = yaml_ops
                .set_setting(
                    &yaml,
                    "Game_Info.Root_Folder_Game",
                    Yaml::String(self.paths.game_root.to_string_lossy().to_string()),
                )
                .context("Failed to set Game_Info.Root_Folder_Game in Local.yaml")?;
        }

        if let Some(ref docs_root) = self.paths.docs_root {
            yaml = yaml_ops
                .set_setting(
                    &yaml,
                    "Game_Info.Root_Folder_Docs",
                    Yaml::String(docs_root.to_string_lossy().to_string()),
                )
                .context("Failed to set Game_Info.Root_Folder_Docs in Local.yaml")?;
        }

        let path = path.to_path_buf();
        tokio::task::spawn_blocking(move || {
            // Build a fresh helper on the blocking worker so the synchronous save
            // stays fully owned by that thread.
            let yaml_ops = YamlOperations::new();
            yaml_ops
                .save_yaml_file(&path, &yaml)
                .map_err(anyhow::Error::new)
        })
        .await
        .context("Local.yaml save task panicked")??;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use classic_settings_core::{merge_yaml_documents, parse_yaml_content};
    use std::sync::{Mutex, OnceLock};
    use tempfile::tempdir;

    fn current_dir_lock() -> &'static Mutex<()> {
        static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
        LOCK.get_or_init(|| Mutex::new(()))
    }

    fn parse_yaml_document(yaml_str: &str) -> Yaml {
        let docs = parse_yaml_content("memory://config.rs", yaml_str).unwrap();
        merge_yaml_documents("memory://config.rs", &docs).unwrap()
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

    #[tokio::test]
    async fn test_load_from_yaml_merges_multiple_documents() {
        let temp_dir = tempdir().unwrap();
        let config_path = temp_dir.path().join("CLASSIC Settings.yaml");

        std::fs::write(
            &config_path,
            concat!(
                "paths:\n",
                "  game_root: C:/Games/Fallout4\n",
                "formid_databases:\n",
                "  Fallout4:\n",
                "    - databases/FOLON FormIDs.db\n",
                "---\n",
                "fcx_mode: true\n",
                "paths:\n",
                "  docs_root: C:/Users/Test/Documents/My Games/Fallout4\n",
            ),
        )
        .unwrap();

        let config = ClassicConfig::load_from_yaml(&config_path).await.unwrap();

        assert!(config.fcx_mode);
        assert_eq!(config.paths.game_root, PathBuf::from("C:/Games/Fallout4"));
        assert_eq!(
            config.paths.docs_root,
            Some(PathBuf::from("C:/Users/Test/Documents/My Games/Fallout4"))
        );
        assert_eq!(
            config.formid_databases.get("Fallout4"),
            Some(&vec![PathBuf::from("databases/FOLON FormIDs.db")])
        );
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
    fn test_missing_game_version_defaults_to_auto() {
        let yaml_str = "fcx_mode: false\n";
        let yaml = parse_yaml_document(yaml_str);

        let config = ClassicConfig::from_yaml(&yaml).unwrap();

        assert_eq!(config.game_version, "auto");
    }

    #[test]
    fn test_game_version_is_loaded_when_set() {
        let yaml_str = "game_version: Original\n";
        let yaml = parse_yaml_document(yaml_str);

        let config = ClassicConfig::from_yaml(&yaml).unwrap();

        assert_eq!(config.game_version, "Original");
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
    fn test_load_local_yaml_paths_merges_multiple_documents() {
        let _guard = current_dir_lock().lock().unwrap();
        let original_dir = std::env::current_dir().unwrap();
        let temp_dir = tempdir().unwrap();
        let local_yaml_dir = temp_dir.path().join("CLASSIC Data");
        let local_yaml_path = local_yaml_dir.join("CLASSIC Task4Merge Local.yaml");

        std::fs::create_dir_all(&local_yaml_dir).unwrap();
        std::fs::write(
            &local_yaml_path,
            concat!(
                "Game_Info:\n",
                "  Root_Folder_Game: C:/Games/Fallout4\n",
                "---\n",
                "Game_Info:\n",
                "  Root_Folder_Docs: C:/Users/Test/Documents/My Games/Fallout4\n",
            ),
        )
        .unwrap();

        std::env::set_current_dir(temp_dir.path()).unwrap();

        let mut config = ClassicConfig::default();
        let runtime = tokio::runtime::Runtime::new().unwrap();
        let result = runtime.block_on(config.load_local_yaml_paths("Task4Merge"));

        std::env::set_current_dir(original_dir).unwrap();

        result.unwrap();
        assert_eq!(config.paths.game_root, PathBuf::from("C:/Games/Fallout4"));
        assert_eq!(
            config.paths.docs_root,
            Some(PathBuf::from("C:/Users/Test/Documents/My Games/Fallout4"))
        );
    }

    #[tokio::test]
    async fn test_save_local_yaml_paths_to_creates_missing_file() {
        let temp_dir = tempdir().unwrap();
        let local_yaml_path = temp_dir
            .path()
            .join("CLASSIC Data")
            .join("CLASSIC Fallout4 Local.yaml");

        let config = ClassicConfig {
            paths: PathConfig {
                ini_folder: None,
                scan_custom: None,
                mods_folder: None,
                game_root: PathBuf::from("C:/Games/Fallout4"),
                docs_root: Some(PathBuf::from("C:/Users/Test/Documents/My Games/Fallout4")),
            },
            ..Default::default()
        };

        config.save_local_yaml_paths_to(&local_yaml_path).await.unwrap();

        assert!(local_yaml_path.exists());

        let yaml = load_yaml_merged_async(&local_yaml_path).await.unwrap();
        assert_eq!(
            yaml["Game_Info"]["Root_Folder_Game"].as_str(),
            Some("C:/Games/Fallout4")
        );
        assert_eq!(
            yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
            Some("C:/Users/Test/Documents/My Games/Fallout4")
        );
    }

    #[tokio::test]
    async fn test_save_local_yaml_paths_to_preserves_existing_keys() {
        let temp_dir = tempdir().unwrap();
        let local_yaml_path = temp_dir
            .path()
            .join("CLASSIC Data")
            .join("CLASSIC Fallout4 Local.yaml");

        std::fs::create_dir_all(local_yaml_path.parent().unwrap()).unwrap();
        std::fs::write(
            &local_yaml_path,
            concat!(
                "Game_Info:\n",
                "  Docs_Folder_XSE: C:/Users/Test/Documents/My Games/Fallout4/F4SE\n",
            ),
        )
        .unwrap();

        let config = ClassicConfig {
            paths: PathConfig {
                ini_folder: None,
                scan_custom: None,
                mods_folder: None,
                game_root: PathBuf::from("C:/Games/Fallout4"),
                docs_root: Some(PathBuf::from("C:/Users/Test/Documents/My Games/Fallout4")),
            },
            ..Default::default()
        };

        config.save_local_yaml_paths_to(&local_yaml_path).await.unwrap();

        let yaml = load_yaml_merged_async(&local_yaml_path).await.unwrap();
        assert_eq!(
            yaml["Game_Info"]["Root_Folder_Game"].as_str(),
            Some("C:/Games/Fallout4")
        );
        assert_eq!(
            yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
            Some("C:/Users/Test/Documents/My Games/Fallout4")
        );
        assert_eq!(
            yaml["Game_Info"]["Docs_Folder_XSE"].as_str(),
            Some("C:/Users/Test/Documents/My Games/Fallout4/F4SE")
        );
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

    #[test]
    fn test_resolve_application_dir_returns_none_without_exe_path() {
        assert_eq!(resolve_application_dir(None), None);
    }

    #[test]
    fn test_resolve_user_config_dir_returns_none_without_base_dir() {
        assert_eq!(resolve_user_config_dir(None), None);
    }

    #[test]
    fn test_resolve_user_config_dir_appends_classic_directory_name() {
        let config_dir = PathBuf::from("C:/Users/Test/AppData/Roaming");

        assert_eq!(
            resolve_user_config_dir(Some(&config_dir)),
            Some(config_dir.join("CLASSIC"))
        );
    }

    #[test]
    fn test_resolve_settings_search_paths_prefers_app_dir_then_user_dir_and_legacy_names() {
        let app_dir = PathBuf::from("C:/ClassicApp");
        let user_dir = PathBuf::from("C:/Users/Test/AppData/Roaming/CLASSIC");

        let paths = resolve_settings_search_paths(Some(&app_dir), Some(&user_dir));

        assert_eq!(paths[0], app_dir.join("CLASSIC Settings.yaml"));
        assert_eq!(paths[1], app_dir.join("CLASSIC_Settings.yaml"));
        assert_eq!(paths[2], user_dir.join("CLASSIC Settings.yaml"));
        assert_eq!(paths[3], user_dir.join("CLASSIC_Settings.yaml"));
    }

    #[test]
    fn test_resolve_settings_search_paths_uses_app_dir_only_when_user_dir_missing() {
        let app_dir = PathBuf::from("C:/ClassicApp");

        let paths = resolve_settings_search_paths(Some(&app_dir), None);

        assert_eq!(paths.len(), 2);
        assert_eq!(paths[0], app_dir.join("CLASSIC Settings.yaml"));
        assert_eq!(paths[1], app_dir.join("CLASSIC_Settings.yaml"));
    }

    #[test]
    fn test_resolve_settings_search_paths_uses_user_dir_only_when_app_dir_missing() {
        let user_dir = PathBuf::from("C:/Users/Test/AppData/Roaming/CLASSIC");

        let paths = resolve_settings_search_paths(None, Some(&user_dir));

        assert_eq!(paths.len(), 2);
        assert_eq!(paths[0], user_dir.join("CLASSIC Settings.yaml"));
        assert_eq!(paths[1], user_dir.join("CLASSIC_Settings.yaml"));
    }

    #[test]
    fn test_resolve_settings_search_paths_returns_empty_when_no_dirs_are_available() {
        let paths = resolve_settings_search_paths(None, None);

        assert!(paths.is_empty());
    }

    #[test]
    fn test_choose_settings_write_path_prefers_existing_app_dir_file() {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&app_dir).unwrap();
        std::fs::create_dir_all(&user_dir).unwrap();

        let existing_path = app_dir.join("CLASSIC_Settings.yaml");
        std::fs::write(&existing_path, "fcx_mode: true\n").unwrap();
        let existing = vec![existing_path.clone()];
        let chosen =
            choose_settings_write_path(&existing, Some(&app_dir), Some(&user_dir)).unwrap();

        assert_eq!(chosen, Some(existing_path));
    }

    #[test]
    fn test_choose_settings_write_path_prefers_existing_user_dir_file_when_app_has_none() {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&app_dir).unwrap();
        std::fs::create_dir_all(&user_dir).unwrap();

        let existing_path = user_dir.join("CLASSIC Settings.yaml");
        std::fs::write(&existing_path, "fcx_mode: true\n").unwrap();
        let existing = vec![existing_path.clone()];
        let chosen =
            choose_settings_write_path(&existing, Some(&app_dir), Some(&user_dir)).unwrap();

        assert_eq!(chosen, Some(existing_path));
    }

    #[test]
    fn test_choose_settings_write_path_skips_existing_app_file_when_exact_file_is_not_writable() {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&app_dir).unwrap();
        std::fs::create_dir_all(&user_dir).unwrap();

        let app_file = app_dir.join("CLASSIC Settings.yaml");
        let user_file = user_dir.join("CLASSIC Settings.yaml");
        let existing = vec![app_file.clone(), user_file.clone()];

        let chosen = choose_settings_write_path_with_access(
            &existing,
            Some(&app_dir),
            Some(&user_dir),
            |path| path != app_file.as_path(),
            |_| true,
        )
        .unwrap();

        assert_eq!(chosen, Some(user_file));
    }

    #[test]
    fn test_choose_settings_write_path_falls_back_to_user_dir_when_app_dir_target_is_not_writable()
    {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&app_dir).unwrap();
        std::fs::create_dir_all(&user_dir).unwrap();

        let chosen = choose_settings_write_path_with_access(
            &[],
            Some(&app_dir),
            Some(&user_dir),
            |_| true,
            |path| path.parent() != Some(app_dir.as_path()),
        )
        .unwrap();

        assert_eq!(chosen, Some(user_dir.join("CLASSIC Settings.yaml")));
    }

    #[test]
    fn test_choose_settings_write_path_prefers_new_modern_file_in_app_dir() {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&app_dir).unwrap();
        std::fs::create_dir_all(&user_dir).unwrap();

        let chosen = choose_settings_write_path(&[], Some(&app_dir), Some(&user_dir)).unwrap();

        assert_eq!(chosen, Some(app_dir.join("CLASSIC Settings.yaml")));
    }

    #[test]
    fn test_choose_settings_write_path_prefers_new_modern_file_in_user_dir_when_app_missing() {
        let temp_dir = tempdir().unwrap();
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&user_dir).unwrap();

        let chosen = choose_settings_write_path(&[], None, Some(&user_dir)).unwrap();

        assert_eq!(chosen, Some(user_dir.join("CLASSIC Settings.yaml")));
    }

    #[test]
    fn test_choose_settings_write_path_returns_none_when_no_dirs_are_available() {
        let chosen = choose_settings_write_path(&[], None, None).unwrap();

        assert_eq!(chosen, None);
    }

    #[test]
    fn test_resolve_settings_path_uses_compatibility_fallback_when_no_dirs_are_available() {
        assert_eq!(
            resolve_settings_write_path(None, None),
            PathBuf::from(DEFAULT_CONFIG_FILENAME)
        );
    }

    #[test]
    fn test_resolve_settings_write_path_does_not_use_compatibility_fallback_when_dirs_are_available()
     {
        let app_dir = PathBuf::from("C:/ClassicApp");

        let path = resolve_settings_write_path(Some(&app_dir), None);

        assert_ne!(path, PathBuf::from(DEFAULT_CONFIG_FILENAME));
    }

    #[test]
    fn test_resolve_existing_settings_path_prefers_actual_existing_file_in_search_order() {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&app_dir).unwrap();
        std::fs::create_dir_all(&user_dir).unwrap();

        let existing_path = user_dir.join(LEGACY_CONFIG_FILENAME);
        std::fs::write(&existing_path, "fcx_mode: true\n").unwrap();

        let resolved = resolve_existing_settings_path(Some(&app_dir), Some(&user_dir));

        assert_eq!(resolved, Some(existing_path));
    }

    #[test]
    fn test_resolve_settings_read_path_prefers_existing_file_over_write_target() {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&app_dir).unwrap();
        std::fs::create_dir_all(&user_dir).unwrap();

        let existing_path = user_dir.join(LEGACY_CONFIG_FILENAME);
        std::fs::write(&existing_path, "fcx_mode: true\n").unwrap();

        let resolved = resolve_settings_read_path(Some(&app_dir), Some(&user_dir));

        assert_eq!(resolved, existing_path);
    }

    #[test]
    fn test_resolve_settings_read_path_has_no_directory_creation_side_effects() {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");

        let resolved = resolve_settings_read_path(Some(&app_dir), Some(&user_dir));

        assert_eq!(resolved, app_dir.join(DEFAULT_CONFIG_FILENAME));
        assert!(!app_dir.exists());
        assert!(!user_dir.exists());
    }

    #[test]
    fn test_resolve_cache_path_prefers_user_config_dir() {
        let user_dir = PathBuf::from("C:/Users/Test/AppData/Roaming/CLASSIC");

        assert_eq!(
            resolve_cache_path(Some(&user_dir), None),
            user_dir.join("cache.yaml")
        );
    }

    #[test]
    fn test_resolve_cache_path_prefers_application_dir_compatibility_fallback_without_user_config_dir()
     {
        let app_dir = PathBuf::from("C:/ClassicApp");

        assert_eq!(
            resolve_cache_path(None, Some(&app_dir)),
            app_dir.join("CLASSIC").join("cache.yaml")
        );
    }

    #[test]
    fn test_resolve_cache_path_uses_relative_compatibility_fallback_without_user_or_app_dir() {
        assert_eq!(
            resolve_cache_path(None, None),
            PathBuf::from("CLASSIC").join("cache.yaml")
        );
    }

    #[tokio::test]
    async fn test_load_or_default_no_file() {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&app_dir).unwrap();
        std::fs::create_dir_all(&user_dir).unwrap();

        let config = load_or_default_from_dirs(Some(&app_dir), Some(&user_dir))
            .await
            .unwrap();
        assert!(!config.fcx_mode);
        assert!(config.update_check);
    }

    #[tokio::test]
    async fn test_load_or_default_prefers_existing_app_dir_file_when_both_locations_exist() {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&app_dir).unwrap();
        std::fs::create_dir_all(&user_dir).unwrap();
        let app_settings_path = app_dir.join("CLASSIC Settings.yaml");
        let user_settings_path = user_dir.join("CLASSIC Settings.yaml");

        std::fs::write(&app_settings_path, "fcx_mode: true\n").unwrap();
        std::fs::write(&user_settings_path, "fcx_mode: false\n").unwrap();

        let config = load_or_default_from_dirs(Some(&app_dir), Some(&user_dir))
            .await
            .unwrap();
        assert!(config.fcx_mode);
    }

    #[tokio::test]
    async fn test_load_or_default_falls_back_to_user_dir_when_app_has_no_settings_file() {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&app_dir).unwrap();
        std::fs::create_dir_all(&user_dir).unwrap();
        let settings_path = user_dir.join("CLASSIC Settings.yaml");

        std::fs::write(settings_path, "fcx_mode: true\n").unwrap();

        let config = load_or_default_from_dirs(Some(&app_dir), Some(&user_dir))
            .await
            .unwrap();
        assert!(config.fcx_mode);
    }

    #[tokio::test]
    async fn test_load_or_default_reads_legacy_underscore_filename_from_app_dir() {
        let temp_dir = tempdir().unwrap();
        let app_dir = temp_dir.path().join("app");
        let user_dir = temp_dir.path().join("user");
        std::fs::create_dir_all(&app_dir).unwrap();
        std::fs::create_dir_all(&user_dir).unwrap();
        let settings_path = app_dir.join("CLASSIC_Settings.yaml");

        std::fs::write(settings_path, "fcx_mode: true\n").unwrap();

        let config = load_or_default_from_dirs(Some(&app_dir), Some(&user_dir))
            .await
            .unwrap();
        assert!(config.fcx_mode);
    }

    #[test]
    fn test_yaml_source_settings_path_mirrors_resolved_settings_path() {
        assert_eq!(
            YamlSource::Settings.path(""),
            resolve_settings_read_path(application_dir().as_deref(), user_config_dir().as_deref())
        );
    }

    #[test]
    fn test_yaml_source_cache_path_matches_resolved_cache_path() {
        assert_eq!(
            YamlSource::Cache.path(""),
            resolve_cache_path(user_config_dir().as_deref(), application_dir().as_deref())
        );
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
        let yaml = parse_yaml_document(yaml_str);

        let config = ClassicConfig::from_yaml(&yaml).unwrap();
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
