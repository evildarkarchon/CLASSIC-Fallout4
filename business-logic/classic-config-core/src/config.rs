//! Unified configuration for CLI and TUI applications
//!
//! This module provides shared configuration types and YAML persistence
//! for both classic-cli and classic-tui applications.

use anyhow::{Context, Result};
use classic_settings_core::{YamlOperations, load_yaml_merged_async};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use tokio::fs;
use yaml_rust2::{Yaml, YamlEmitter};

// Import the LinkedHashMap type that yaml-rust2 uses
type LinkedHashMap<K, V> = hashlink::LinkedHashMap<K, V>;

const DEFAULT_CONFIG_FILENAME: &str = "CLASSIC Settings.yaml";
fn resolve_application_dir(current_exe: Option<&Path>) -> Option<PathBuf> {
    current_exe.and_then(|path| path.parent().map(Path::to_path_buf))
}

fn application_dir() -> Option<PathBuf> {
    // Binding layers (Python, Node) auto-register APP_DIR at module init
    // so settings resolve relative to the working directory rather than
    // the interpreter's install directory (python.exe, node.exe, etc.).
    classic_registry_core::get_application_dir().or_else(|| {
        std::env::current_exe()
            .ok()
            .and_then(|path| resolve_application_dir(Some(path.as_path())))
    })
}

fn resolve_user_config_dir(config_dir: Option<&Path>) -> Option<PathBuf> {
    config_dir.map(|dir| dir.join("CLASSIC"))
}

fn user_config_dir() -> Option<PathBuf> {
    let config_dir = dirs::config_dir();
    resolve_user_config_dir(config_dir.as_deref())
}

fn resolve_settings_search_paths(app_dir: Option<&Path>, _user_dir: Option<&Path>) -> Vec<PathBuf> {
    let mut paths = Vec::new();

    if let Some(app_dir) = app_dir {
        paths.push(app_dir.join(DEFAULT_CONFIG_FILENAME));
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

    let _ = user_dir;

    PathBuf::from(DEFAULT_CONFIG_FILENAME)
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
    _user_dir: Option<&Path>,
    can_update_existing: impl Fn(&Path) -> bool,
    can_create_new: impl Fn(&Path) -> bool,
) -> Result<Option<PathBuf>> {
    for candidate in resolve_settings_search_paths(app_dir, None) {
        if existing_paths.iter().any(|path| path == &candidate) && can_update_existing(&candidate) {
            return Ok(Some(candidate));
        }
    }

    if let Some(app_target) = app_dir.map(|dir| dir.join(DEFAULT_CONFIG_FILENAME))
        && can_create_new(&app_target)
    {
        return Ok(Some(app_target));
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
    if app_dir.is_none() {
        return PathBuf::from(DEFAULT_CONFIG_FILENAME);
    }

    let existing_paths: Vec<_> = resolve_settings_search_paths(app_dir, None)
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
    for path in resolve_settings_search_paths(app_dir, None) {
        if path.exists() {
            return ClassicConfig::load_from_yaml(&path).await;
        }
    }

    let _ = user_dir;

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
                resolve_settings_read_path(app_dir.as_deref(), None)
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
        // Shippable sources (Main, per-game database) must go through the
        // cache-aware loader so that YAML updates delivered via the
        // yaml-update-delivery flow are actually consumed at runtime. Reading
        // the bundled install-tree copy directly would let `check_yaml_update`
        // report "Installed" while the app kept loading the pre-update bytes.
        // See `shippable::load_shippable_yaml` for the precedence rules.
        if let Some(loaded) = load_via_shippable(self, game).await? {
            return Ok(loaded);
        }

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

/// Route `YamlSource::Main` and per-game databases through
/// [`load_shippable_yaml`] when a matching client schema range is declared;
/// return `Ok(None)` for sources that are not cache-eligible so the caller
/// falls through to the direct bundled load.
async fn load_via_shippable(source: &YamlSource, game: &str) -> Result<Option<Yaml>> {
    use crate::client_schemas::{GAME_FALLOUT4_YAML, MAIN_YAML};
    use crate::shippable::{ShippableFile, load_shippable_yaml};

    let (file, compat, display) = match source {
        YamlSource::Main => (
            ShippableFile::main(),
            &MAIN_YAML,
            "Main Database".to_string(),
        ),
        YamlSource::Game if game == "Fallout4" => (
            ShippableFile::game(game),
            &GAME_FALLOUT4_YAML,
            format!("{} Database", game),
        ),
        _ => return Ok(None),
    };

    load_shippable_yaml(file, compat)
        .await
        .map(|loaded| Some(loaded.yaml))
        .with_context(|| format!("Failed to load {} (shippable)", display))
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

    /// Optional absolute folder for Unsolved Logs relocation
    pub unsolved_logs_destination: Option<PathBuf>,

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
            unsolved_logs_destination: None,
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
        let unsolved_logs_destination = yaml["unsolved_logs_destination"]
            .as_str()
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .map(PathBuf::from);
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
            unsolved_logs_destination,
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
        if let Some(destination) = &self.unsolved_logs_destination {
            root.insert(
                Yaml::String("unsolved_logs_destination".to_string()),
                Yaml::String(destination.to_string_lossy().to_string()),
            );
        }
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
    ///
    /// # Returns
    /// * Configuration loaded from file (if exists)
    /// * Default configuration (if no file found)
    pub async fn load_or_default() -> Result<Self> {
        let app_dir = application_dir();
        load_or_default_from_dirs(app_dir.as_deref(), None).await
    }

    /// Get the default config path
    pub fn get_config_path(&self) -> PathBuf {
        let app_dir = application_dir();
        resolve_settings_write_path(app_dir.as_deref(), None)
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

        if let Some(ref ini_folder) = self.paths.ini_folder
            && !ini_folder.exists()
        {
            anyhow::bail!("INI folder does not exist: {}", ini_folder.display());
        }

        if let Some(ref scan_custom) = self.paths.scan_custom
            && !scan_custom.exists()
        {
            anyhow::bail!(
                "Custom scan folder does not exist: {}",
                scan_custom.display()
            );
        }

        if let Some(ref mods_folder) = self.paths.mods_folder
            && !mods_folder.exists()
        {
            anyhow::bail!("Mods folder does not exist: {}", mods_folder.display());
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
                format!(
                    "Failed to load Local.yaml file for save: {}",
                    path.display()
                )
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
#[path = "config_tests.rs"]
mod tests;
