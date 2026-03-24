//! Configuration data bindings (classic-config-core)
//!
//! Exposes two main types to JavaScript/TypeScript:
//!
//! 1. **YamlData** class: Wraps `YamlDataCore` with ~30 field getters for game
//!    configuration data (mod databases, suspect patterns, ignore lists, etc.)
//!
//! 2. **ClassicConfig** class: Wraps the runtime settings configuration with
//!    getters/setters for feature flags, paths, and preferences.
//!
//! 3. **Free functions**: `createYamlDataFromContent()`, `createDefaultConfig()`,
//!    `clearYamlCache()`, convenience accessors.

use classic_config_core::{
    ClassicConfig as CoreClassicConfig, ConfigError, ModConflictEntry,
    PathConfig as CorePathConfig, YamlDataCore, YamlSource as CoreYamlSource,
};
use classic_settings_core::SettingsError;
use classic_shared_core::get_runtime;
use napi::Status;
use napi::bindgen_prelude::*;
use std::collections::HashMap;
use std::path::PathBuf;

use crate::crashgen_rules::{JsCrashgenRegistryEntry, core_rules_to_js};

#[napi(object)]
pub struct JsModConflictEntry {
    pub mod_a: String,
    pub mod_b: String,
    pub name_a: String,
    pub name_b: String,
    pub description: String,
    pub fix: String,
    pub link: Option<String>,
}

impl From<&ModConflictEntry> for JsModConflictEntry {
    fn from(e: &ModConflictEntry) -> Self {
        Self {
            mod_a: e.mod_a.clone(),
            mod_b: e.mod_b.clone(),
            name_a: e.name_a.clone(),
            name_b: e.name_b.clone(),
            description: e.description.clone(),
            fix: e.fix.clone(),
            link: e.link.clone(),
        }
    }
}

fn config_error_status(err: &ConfigError) -> Status {
    match err {
        ConfigError::IOError { .. } => Status::GenericFailure,
        ConfigError::ParseError { .. }
        | ConfigError::EmptyDocument(_)
        | ConfigError::InvalidInput(_) => Status::InvalidArg,
    }
}

fn config_error_to_napi_err(err: &ConfigError, message: &str) -> napi::Error {
    napi::Error::new(config_error_status(err), message.to_string())
}

fn settings_error_to_napi_err(err: &SettingsError, message: &str) -> napi::Error {
    let status = match err {
        SettingsError::IoError { .. } => Status::GenericFailure,
        SettingsError::YamlParseError { .. }
        | SettingsError::EmptyDocument { .. }
        | SettingsError::InvalidYamlStructure { .. }
        | SettingsError::KeyNotFound(_) => Status::InvalidArg,
        SettingsError::TaskJoinError { .. } => Status::GenericFailure,
    };
    napi::Error::new(status, message.to_string())
}

/// Convert config/runtime errors to a classified napi::Error.
fn runtime_to_napi_err(err: anyhow::Error) -> napi::Error {
    let display = format!("{err:#}");
    let mut current: Option<&(dyn std::error::Error + 'static)> = Some(err.as_ref());

    while let Some(cause) = current {
        if let Some(config_err) = cause.downcast_ref::<ConfigError>() {
            return config_error_to_napi_err(config_err, &display);
        }
        if let Some(settings_err) = cause.downcast_ref::<SettingsError>() {
            return settings_error_to_napi_err(settings_err, &display);
        }
        if cause.downcast_ref::<std::io::Error>().is_some() {
            return napi::Error::new(Status::GenericFailure, display);
        }
        current = cause.source();
    }

    napi::Error::new(Status::GenericFailure, display)
}

// ============================================================================
// 1. YamlData class -- wraps YamlDataCore
// ============================================================================

/// Game configuration data loaded from YAML files.
///
/// This class holds all parsed game configuration including mod databases,
/// suspect patterns, ignore lists, version info, and UI text. It is immutable
/// after creation and thread-safe.
///
/// Construct via `new YamlData(yamlDirs, game, gameVersion)` or the static
/// `YamlData.fromYamlContent(...)` method for testing.
#[napi]
pub struct YamlData {
    inner: YamlDataCore,
}

#[napi]
impl YamlData {
    /// Load all configuration from YAML files.
    ///
    /// @param yamlDirs - Array of directory paths containing YAML files.
    ///   Either 2 elements `[rootDir, dataDir]` or 3 elements `[mainDir, gameDir, ignoreDir]`.
    /// @param game - Game identifier (e.g., "Fallout4", "Skyrim").
    /// @param gameVersion - Selected mode
    ///   ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", "VR").
    /// @throws on I/O errors, parse errors, or invalid input.
    #[napi(constructor)]
    pub fn new(yaml_dirs: Vec<String>, game: String, game_version: String) -> Result<Self> {
        let dirs: Vec<PathBuf> = yaml_dirs.into_iter().map(PathBuf::from).collect();
        let inner = get_runtime()
            .block_on(async { YamlDataCore::load_from_yaml_files(dirs, game, game_version).await })
            .map_err(|err| config_error_to_napi_err(&err, &err.to_string()))?;
        Ok(Self { inner })
    }

    /// Create YamlData from YAML content strings (for testing without file I/O).
    ///
    /// @param mainContent - Content of the main YAML configuration file.
    /// @param gameContent - Content of the game-specific YAML configuration file.
    /// @param ignoreContent - Content of the ignore list YAML configuration file.
    /// @param game - Game identifier (e.g., "Fallout4", "Skyrim").
    /// @param gameVersion - Selected mode
    ///   ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", "VR").
    /// @throws on parse errors or empty documents.
    #[napi(factory)]
    pub fn from_yaml_content(
        main_content: String,
        game_content: String,
        ignore_content: String,
        game: String,
        game_version: String,
    ) -> Result<Self> {
        let inner = YamlDataCore::from_yaml_content(
            &main_content,
            &game_content,
            &ignore_content,
            game,
            game_version,
        )
        .map_err(|err| config_error_to_napi_err(&err, &err.to_string()))?;
        Ok(Self { inner })
    }

    // ========================================================================
    // Game Configuration Properties
    // ========================================================================

    /// Hints or tips for the classic game configuration.
    #[napi(getter)]
    pub fn classic_game_hints(&self) -> Vec<String> {
        self.inner.classic_game_hints.clone()
    }

    /// List of records related to the classic version.
    #[napi(getter)]
    pub fn classic_records_list(&self) -> Vec<String> {
        self.inner.classic_records_list.clone()
    }

    /// CLASSIC version number string.
    #[napi(getter)]
    pub fn classic_version(&self) -> String {
        self.inner.classic_version.clone()
    }

    /// Release or update date of the CLASSIC version.
    #[napi(getter)]
    pub fn classic_version_date(&self) -> String {
        self.inner.classic_version_date.clone()
    }

    // ========================================================================
    // Crashgen Configuration Properties
    // ========================================================================

    /// Crash generator name identifier.
    #[napi(getter)]
    pub fn crashgen_name(&self) -> String {
        self.inner.crashgen_name.clone()
    }

    /// Latest original (non-VR) crash generator version.
    #[napi(getter)]
    pub fn crashgen_latest_og(&self) -> String {
        self.inner.crashgen_latest_og.clone()
    }

    /// Items to ignore during crash generation (as an array).
    #[napi(getter)]
    pub fn crashgen_ignore(&self) -> Vec<String> {
        self.inner.crashgen_ignore.clone()
    }

    /// Crash generator registry with checks and optional settings rules.
    #[napi(getter)]
    pub fn crashgen_registry(&self) -> HashMap<String, JsCrashgenRegistryEntry> {
        self.inner
            .crashgen_registry
            .iter()
            .map(|(name, entry)| {
                (
                    name.clone(),
                    JsCrashgenRegistryEntry {
                        display_section: entry.display_section.clone(),
                        ignore_keys: entry.ignore_keys.clone(),
                        checks: entry.checks.clone(),
                        settings_rules_version: entry.settings_rules_version,
                        settings_rules: core_rules_to_js(entry.settings_rules.as_ref()),
                    },
                )
            })
            .collect()
    }

    // ========================================================================
    // Warning Properties
    // ========================================================================

    /// Warning message for cases where no plugins are active.
    #[napi(getter)]
    pub fn warn_noplugins(&self) -> String {
        self.inner.warn_noplugins.clone()
    }

    /// Warning message indicating the version is outdated.
    #[napi(getter)]
    pub fn warn_outdated(&self) -> String {
        self.inner.warn_outdated.clone()
    }

    // ========================================================================
    // XSE Configuration
    // ========================================================================

    /// Acronym for the script extender (e.g., "F4SE").
    #[napi(getter)]
    pub fn xse_acronym(&self) -> String {
        self.inner.xse_acronym.clone()
    }

    // ========================================================================
    // Ignore Lists
    // ========================================================================

    /// Plugins to ignore in the game configuration.
    #[napi(getter)]
    pub fn game_ignore_plugins(&self) -> Vec<String> {
        self.inner.game_ignore_plugins.clone()
    }

    /// Records to ignore in the game configuration.
    #[napi(getter)]
    pub fn game_ignore_records(&self) -> Vec<String> {
        self.inner.game_ignore_records.clone()
    }

    /// User-defined ignore list entries.
    #[napi(getter)]
    pub fn ignore_list(&self) -> Vec<String> {
        self.inner.ignore_list.clone()
    }

    // ========================================================================
    // Suspect Pattern Dictionaries
    // ========================================================================

    /// Suspect error patterns mapped to descriptive explanations.
    ///
    /// Returns a `Record<string, string>` preserving YAML source order.
    #[napi(getter)]
    pub fn suspects_error_list(&self) -> HashMap<String, String> {
        self.inner
            .suspects_error_list
            .iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect()
    }

    /// Suspect stack trace patterns mapped to pattern lists.
    ///
    /// Returns a `Record<string, string[]>` preserving YAML source order.
    #[napi(getter)]
    pub fn suspects_stack_list(&self) -> HashMap<String, Vec<String>> {
        self.inner
            .suspects_stack_list
            .iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect()
    }

    // ========================================================================
    // Mod Database Dictionaries
    // ========================================================================

    /// Conflicting mod pairs database.
    #[napi(getter)]
    pub fn game_mods_conf(&self) -> Vec<JsModConflictEntry> {
        self.inner
            .game_mods_conf
            .iter()
            .map(JsModConflictEntry::from)
            .collect()
    }

    /// Core/essential mods database.
    #[napi(getter)]
    pub fn game_mods_core_count(&self) -> u32 {
        self.inner.game_mods_core.len() as u32
    }

    /// Core mods detect ids.
    #[napi(getter)]
    pub fn game_mods_core_detects(&self) -> Vec<String> {
        self.inner
            .game_mods_core
            .iter()
            .map(|e| e.detect.clone())
            .collect()
    }

    /// Core mods display names.
    #[napi(getter)]
    pub fn game_mods_core_names(&self) -> Vec<String> {
        self.inner
            .game_mods_core
            .iter()
            .map(|e| e.name.clone())
            .collect()
    }

    /// Core mods descriptions.
    #[napi(getter)]
    pub fn game_mods_core_descriptions(&self) -> Vec<String> {
        self.inner
            .game_mods_core
            .iter()
            .map(|e| e.description.clone())
            .collect()
    }

    /// Core mods GPU fields (empty string if not set).
    #[napi(getter)]
    pub fn game_mods_core_gpus(&self) -> Vec<String> {
        self.inner
            .game_mods_core
            .iter()
            .map(|e| e.gpu.clone().unwrap_or_default())
            .collect()
    }

    /// Frequently problematic mods database.
    #[napi(getter)]
    pub fn game_mods_freq(&self) -> HashMap<String, String> {
        self.inner
            .game_mods_freq
            .iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect()
    }

    /// Solution mods database.
    #[napi(getter)]
    pub fn game_mods_solu(&self) -> HashMap<String, String> {
        self.inner
            .game_mods_solu
            .iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect()
    }

    // ========================================================================
    // UI Configuration
    // ========================================================================

    /// Text used in the autoscan UI component.
    #[napi(getter)]
    pub fn autoscan_text(&self) -> String {
        self.inner.autoscan_text.clone()
    }

    // ========================================================================
    // Game Versions
    // ========================================================================

    /// Current game version string.
    #[napi(getter)]
    pub fn game_version(&self) -> String {
        self.inner.game_version.clone()
    }

    // ========================================================================
    // Game Root Names
    // ========================================================================

    /// Game root name.
    #[napi(getter)]
    pub fn game_root_name(&self) -> String {
        self.inner.game_root_name.clone()
    }

    // ========================================================================
    // Accessor Methods
    // ========================================================================

    /// Get crash generator name.
    #[napi]
    pub fn get_crashgen_name(&self) -> String {
        self.inner.get_crashgen_name().to_string()
    }

    /// Get crash generator ignore list.
    #[napi]
    pub fn get_crashgen_ignore(&self) -> Vec<String> {
        self.inner.get_crashgen_ignore().to_vec()
    }

    /// Get game root name.
    #[napi]
    pub fn get_game_root_name(&self) -> String {
        self.inner.get_game_root_name().to_string()
    }

    // ========================================================================
    // Utility Methods
    // ========================================================================

    /// Get a human-readable string representation.
    #[napi(js_name = "toString")]
    pub fn to_string_repr(&self) -> String {
        format!(
            "YamlData(game={}, version={})",
            self.inner
                .crashgen_name
                .split('_')
                .next()
                .unwrap_or("unknown"),
            self.inner.classic_version,
        )
    }
}

// ============================================================================
// 2. PathConfig DTO
// ============================================================================

/// Path configuration for game directories.
#[napi(object)]
pub struct JsPathConfig {
    /// Path to INI folder (game documents folder), or undefined if not set.
    pub ini_folder: Option<String>,
    /// Path to custom scan folder, or undefined if not set.
    pub scan_custom: Option<String>,
    /// Path to mods folder, or undefined if not set.
    pub mods_folder: Option<String>,
    /// Path to game root directory.
    pub game_root: String,
    /// Path to game documents root directory, or undefined if not set.
    pub docs_root: Option<String>,
}

impl From<&CorePathConfig> for JsPathConfig {
    fn from(p: &CorePathConfig) -> Self {
        Self {
            ini_folder: p
                .ini_folder
                .as_ref()
                .map(|p| p.to_string_lossy().to_string()),
            scan_custom: p
                .scan_custom
                .as_ref()
                .map(|p| p.to_string_lossy().to_string()),
            mods_folder: p
                .mods_folder
                .as_ref()
                .map(|p| p.to_string_lossy().to_string()),
            game_root: p.game_root.to_string_lossy().to_string(),
            docs_root: p
                .docs_root
                .as_ref()
                .map(|p| p.to_string_lossy().to_string()),
        }
    }
}

impl From<&JsPathConfig> for CorePathConfig {
    fn from(p: &JsPathConfig) -> Self {
        Self {
            ini_folder: p.ini_folder.as_ref().map(PathBuf::from),
            scan_custom: p.scan_custom.as_ref().map(PathBuf::from),
            mods_folder: p.mods_folder.as_ref().map(PathBuf::from),
            game_root: PathBuf::from(&p.game_root),
            docs_root: p.docs_root.as_ref().map(PathBuf::from),
        }
    }
}

// ============================================================================
// 3. ClassicConfig class -- wraps CoreClassicConfig
// ============================================================================

/// Runtime configuration for CLASSIC (settings, feature flags, paths).
///
/// Construct with `new ClassicConfig()` for defaults, or use
/// `ClassicConfig.loadFromYaml(path)` to load from a YAML file.
#[napi]
pub struct ClassicConfigJs {
    inner: CoreClassicConfig,
}

impl Default for ClassicConfigJs {
    fn default() -> Self {
        Self::new()
    }
}

#[napi]
impl ClassicConfigJs {
    /// Create a new ClassicConfig with default values.
    #[napi(constructor)]
    pub fn new() -> Self {
        Self {
            inner: CoreClassicConfig::default(),
        }
    }

    /// Load configuration from a YAML file.
    ///
    /// @param path - Path to the YAML configuration file.
    /// @throws on I/O or parse errors.
    #[napi(factory)]
    pub fn load_from_yaml(path: String) -> Result<Self> {
        let p = PathBuf::from(&path);
        let inner = get_runtime()
            .block_on(async { CoreClassicConfig::load_from_yaml(&p).await })
            .map_err(runtime_to_napi_err)?;
        Ok(Self { inner })
    }

    /// Load configuration from default location, or return defaults if no file exists.
    #[napi(factory)]
    pub fn load_or_default() -> Result<Self> {
        let inner = get_runtime()
            .block_on(async { CoreClassicConfig::load_or_default().await })
            .map_err(runtime_to_napi_err)?;
        Ok(Self { inner })
    }

    /// Save configuration to a YAML file.
    ///
    /// Creates parent directories if they do not exist.
    ///
    /// @param path - Path to save the YAML configuration file.
    /// @throws on I/O or serialization errors.
    #[napi]
    pub fn save_to_yaml(&self, path: String) -> Result<()> {
        let p = PathBuf::from(&path);
        get_runtime()
            .block_on(async { self.inner.save_to_yaml(&p).await })
            .map_err(runtime_to_napi_err)
    }

    /// Get the default config file path.
    #[napi]
    pub fn get_config_path(&self) -> String {
        self.inner.get_config_path().to_string_lossy().to_string()
    }

    /// Validate that configured paths exist.
    ///
    /// @throws if any configured path does not exist.
    #[napi]
    pub fn validate_paths(&self) -> Result<()> {
        self.inner.validate_paths().map_err(runtime_to_napi_err)
    }

    /// Load paths from the game's Local.yaml file.
    ///
    /// Updates game_root and docs_root in place. If the Local.yaml file does not
    /// exist, this is not an error -- the config retains its current paths.
    ///
    /// @param game - Game name (e.g., "Fallout4", "Skyrim").
    #[napi]
    pub fn load_local_yaml_paths(&mut self, game: String) -> Result<()> {
        get_runtime()
            .block_on(async { self.inner.load_local_yaml_paths(&game).await })
            .map_err(runtime_to_napi_err)
    }

    // ========================================================================
    // Feature Flag Getters / Setters
    // ========================================================================

    /// Whether FCX mode (enhanced FormID analysis) is enabled.
    #[napi(getter)]
    pub fn fcx_mode(&self) -> bool {
        self.inner.fcx_mode
    }

    /// Set FCX mode.
    #[napi(setter)]
    pub fn set_fcx_mode(&mut self, value: bool) {
        self.inner.fcx_mode = value;
    }

    /// Whether FormID values are shown in output.
    #[napi(getter)]
    pub fn show_formid_values(&self) -> bool {
        self.inner.show_formid_values
    }

    /// Set show FormID values.
    #[napi(setter)]
    pub fn set_show_formid_values(&mut self, value: bool) {
        self.inner.show_formid_values = value;
    }

    /// Whether statistical logging is enabled.
    #[napi(getter)]
    pub fn stat_logging(&self) -> bool {
        self.inner.stat_logging
    }

    /// Set statistical logging.
    #[napi(setter)]
    pub fn set_stat_logging(&mut self, value: bool) {
        self.inner.stat_logging = value;
    }

    /// Whether unsolved logs are moved to a subfolder.
    #[napi(getter)]
    pub fn move_unsolved_logs(&self) -> bool {
        self.inner.move_unsolved_logs
    }

    /// Set move unsolved logs.
    #[napi(setter)]
    pub fn set_move_unsolved_logs(&mut self, value: bool) {
        self.inner.move_unsolved_logs = value;
    }

    /// Whether logs are simplified (may remove important info).
    #[napi(getter)]
    pub fn simplify_logs(&self) -> bool {
        self.inner.simplify_logs
    }

    /// Set simplify logs.
    #[napi(setter)]
    pub fn set_simplify_logs(&mut self, value: bool) {
        self.inner.simplify_logs = value;
    }

    /// Whether update checks at startup are enabled.
    #[napi(getter)]
    pub fn update_check(&self) -> bool {
        self.inner.update_check
    }

    /// Set update check.
    #[napi(setter)]
    pub fn set_update_check(&mut self, value: bool) {
        self.inner.update_check = value;
    }

    /// Game version selection:
    /// "auto", "Original", "NextGen", "AnniversaryEdition"/"AE", or "VR".
    #[napi(getter)]
    pub fn game_version(&self) -> String {
        self.inner.game_version.clone()
    }

    /// Set game version.
    #[napi(setter)]
    pub fn set_game_version(&mut self, value: String) {
        self.inner.game_version = value;
    }

    /// Update source: "github" or "both".
    #[napi(getter)]
    pub fn update_source(&self) -> String {
        self.inner.update_source.clone()
    }

    /// Set update source.
    #[napi(setter)]
    pub fn set_update_source(&mut self, value: String) {
        self.inner.update_source = value;
    }

    /// Whether to auto-switch to Results tab after scan completion.
    #[napi(getter)]
    pub fn auto_switch_to_results(&self) -> bool {
        self.inner.auto_switch_to_results
    }

    /// Set auto-switch to results.
    #[napi(setter)]
    pub fn set_auto_switch_to_results(&mut self, value: bool) {
        self.inner.auto_switch_to_results = value;
    }

    /// Auto-refresh interval for file watcher in milliseconds.
    #[napi(getter)]
    pub fn auto_refresh_interval_ms(&self) -> u32 {
        self.inner.auto_refresh_interval_ms as u32
    }

    /// Set auto-refresh interval in milliseconds.
    #[napi(setter)]
    pub fn set_auto_refresh_interval_ms(&mut self, value: u32) {
        self.inner.auto_refresh_interval_ms = value as u64;
    }

    // ========================================================================
    // Path Configuration
    // ========================================================================

    /// Get the path configuration as a JavaScript object.
    #[napi(getter)]
    pub fn paths(&self) -> JsPathConfig {
        JsPathConfig::from(&self.inner.paths)
    }

    /// Set the path configuration from a JavaScript object.
    #[napi(setter)]
    pub fn set_paths(&mut self, value: JsPathConfig) {
        self.inner.paths = CorePathConfig::from(&value);
    }

    // ========================================================================
    // FormID Databases
    // ========================================================================

    /// User-configured FormID databases per game.
    ///
    /// Returns a `Record<string, string[]>` mapping game names to lists of database paths.
    #[napi(getter)]
    pub fn formid_databases(&self) -> HashMap<String, Vec<String>> {
        self.inner
            .formid_databases
            .iter()
            .map(|(k, v)| {
                (
                    k.clone(),
                    v.iter().map(|p| p.to_string_lossy().to_string()).collect(),
                )
            })
            .collect()
    }

    /// Set FormID databases.
    #[napi(setter)]
    pub fn set_formid_databases(&mut self, value: HashMap<String, Vec<String>>) {
        self.inner.formid_databases = value
            .into_iter()
            .map(|(k, v)| (k, v.into_iter().map(PathBuf::from).collect()))
            .collect();
    }
}

// ============================================================================
// 4. YamlSource enum binding
// ============================================================================

/// YAML file source identifier.
///
/// Provides paths and display names for the various YAML configuration files
/// used by CLASSIC.
#[napi(string_enum)]
pub enum JsYamlSource {
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
    /// Cache: user config dir/CLASSIC/cache.yaml
    Cache,
}

impl From<JsYamlSource> for CoreYamlSource {
    fn from(js: JsYamlSource) -> Self {
        match js {
            JsYamlSource::Main => CoreYamlSource::Main,
            JsYamlSource::Settings => CoreYamlSource::Settings,
            JsYamlSource::Ignore => CoreYamlSource::Ignore,
            JsYamlSource::Game => CoreYamlSource::Game,
            JsYamlSource::GameLocal => CoreYamlSource::GameLocal,
            JsYamlSource::Test => CoreYamlSource::Test,
            JsYamlSource::Cache => CoreYamlSource::Cache,
        }
    }
}

// ============================================================================
// 5. Free Functions
// ============================================================================

/// Create YamlData from YAML content strings (convenience free function).
///
/// Equivalent to `YamlData.fromYamlContent(...)`.
#[napi]
pub fn create_yaml_data_from_content(
    main_content: String,
    game_content: String,
    ignore_content: String,
    game: String,
    game_version: String,
) -> Result<YamlData> {
    YamlData::from_yaml_content(
        main_content,
        game_content,
        ignore_content,
        game,
        game_version,
    )
}

/// Create a new ClassicConfig with default values (convenience free function).
///
/// Equivalent to `new ClassicConfig()`.
#[napi]
pub fn create_default_config() -> ClassicConfigJs {
    ClassicConfigJs::new()
}

/// Clear the global YAML cache.
///
/// Useful for testing to ensure clean state between test runs.
#[napi]
pub fn clear_yaml_cache() {
    classic_config_core::clear_global_yaml_cache();
}

/// Get the file path for a YAML source.
///
/// @param source - The YAML source type.
/// @param game - Game name (required for Game and GameLocal sources; empty string for others).
/// @returns The file path as a string.
#[napi]
pub fn get_yaml_source_path(source: JsYamlSource, game: String) -> String {
    let core_source: CoreYamlSource = source.into();
    core_source.path(&game).to_string_lossy().to_string()
}

/// Get the display name for a YAML source.
///
/// @param source - The YAML source type.
/// @returns A human-readable display name.
#[napi]
pub fn get_yaml_source_display_name(source: JsYamlSource) -> String {
    let core_source: CoreYamlSource = source.into();
    core_source.display_name().to_string()
}

/// Get the display name for a YAML source with game substitution.
///
/// @param source - The YAML source type.
/// @param game - Game name (e.g., "Fallout4", "Skyrim").
/// @returns A human-readable display name with the game name included.
#[napi]
pub fn get_yaml_source_display_name_with_game(source: JsYamlSource, game: String) -> String {
    let core_source: CoreYamlSource = source.into();
    core_source.display_name_with_game(&game)
}
