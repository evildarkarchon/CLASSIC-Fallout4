//! Configuration data bindings (classic-config-core)
//!
//! Exposes YAML Data and related non-User-Settings helpers to JavaScript/TypeScript:
//!
//! 1. **YamlData** class: Wraps `YamlDataCore` with ~30 field getters for game
//!    configuration data (mod databases, suspect patterns, ignore lists, etc.)
//!
//! 2. **Free functions**: `createYamlDataFromContent()`,
//!    `persistGameLocalPaths()`, `clearYamlCache()`, convenience accessors.

use classic_config_core::{
    ConfigError, MainYamlVersionError, ModConflictEntry, ModSolutionCriteria, ModSolutionEntry,
    SuspectErrorRule, SuspectStackRule, YamlDataCore, YamlSource as CoreYamlSource,
    load_main_yaml_version_with_bundled_dir as core_load_main_yaml_version_with_bundled_dir,
    persist_game_local_paths as core_persist_game_local_paths,
};
use classic_settings_core::SettingsError;
use classic_shared_core::get_runtime;
use napi::Status;
use napi::bindgen_prelude::*;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Once;

static INIT_APP_DIR: Once = Once::new();

/// Ensure APP_DIR is registered so settings resolve relative to the process
/// working directory rather than the interpreter install path (node/bun).
fn ensure_app_dir_initialized() {
    INIT_APP_DIR.call_once(|| {
        if classic_registry_core::get_application_dir().is_none()
            && let Ok(cwd) = std::env::current_dir()
        {
            classic_registry_core::set_application_dir(cwd);
        }
    });
}

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

#[napi(object)]
pub struct JsModSolutionCriteria {
    pub any: Option<Vec<String>>,
    pub all: Option<Vec<String>>,
}

#[napi(object)]
pub struct JsModSolutionEntry {
    pub id: String,
    pub criteria: JsModSolutionCriteria,
    pub exceptions: Vec<String>,
    pub name: String,
    pub description: String,
}

#[napi(object)]
pub struct JsSuspectErrorRule {
    pub id: String,
    pub name: String,
    pub severity: i32,
    pub main_error_contains_any: Vec<String>,
}

impl From<&SuspectErrorRule> for JsSuspectErrorRule {
    fn from(rule: &SuspectErrorRule) -> Self {
        Self {
            id: rule.id.clone(),
            name: rule.name.clone(),
            severity: rule.severity,
            main_error_contains_any: rule.main_error_contains_any.clone(),
        }
    }
}

#[napi(object)]
pub struct JsSuspectStackCountRule {
    pub substring: String,
    pub count: u32,
}

#[napi(object)]
pub struct JsSuspectStackRule {
    pub id: String,
    pub name: String,
    pub severity: i32,
    pub main_error_required_any: Vec<String>,
    pub main_error_optional_any: Vec<String>,
    pub stack_contains_any: Vec<String>,
    pub exclude_if_stack_contains_any: Vec<String>,
    pub stack_contains_at_least: Vec<JsSuspectStackCountRule>,
}

impl From<&SuspectStackRule> for JsSuspectStackRule {
    fn from(rule: &SuspectStackRule) -> Self {
        Self {
            id: rule.id.clone(),
            name: rule.name.clone(),
            severity: rule.severity,
            main_error_required_any: rule.main_error_required_any.clone(),
            main_error_optional_any: rule.main_error_optional_any.clone(),
            stack_contains_any: rule.stack_contains_any.clone(),
            exclude_if_stack_contains_any: rule.exclude_if_stack_contains_any.clone(),
            stack_contains_at_least: rule
                .stack_contains_at_least
                .iter()
                .map(|count_rule| JsSuspectStackCountRule {
                    substring: count_rule.substring.clone(),
                    count: count_rule.count as u32,
                })
                .collect(),
        }
    }
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

impl From<&ModSolutionEntry> for JsModSolutionEntry {
    fn from(entry: &ModSolutionEntry) -> Self {
        let criteria = match &entry.criteria {
            ModSolutionCriteria::Any(values) => JsModSolutionCriteria {
                any: Some(values.clone()),
                all: None,
            },
            ModSolutionCriteria::All(values) => JsModSolutionCriteria {
                any: None,
                all: Some(values.clone()),
            },
        };

        Self {
            id: entry.id.clone(),
            criteria,
            exceptions: entry.exceptions.clone(),
            name: entry.name.clone(),
            description: entry.description.clone(),
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

/// Persist optional runtime paths to an explicit Game Local YAML document.
///
/// Omitted path updates leave their existing keys unchanged. The operation is
/// independent from User Settings and never reads or writes that document.
///
/// @param localYamlPath - Explicit Game Local YAML document path.
/// @param gameRoot - Optional game-root update.
/// @param docsRoot - Optional documents-root update.
/// @throws on directory creation, YAML parsing, or file persistence failures.
#[napi]
pub async fn persist_game_local_paths(
    local_yaml_path: String,
    game_root: Option<String>,
    docs_root: Option<String>,
) -> napi::Result<()> {
    let local_yaml_path = PathBuf::from(local_yaml_path);
    let game_root = game_root.map(PathBuf::from);
    let docs_root = docs_root.map(PathBuf::from);
    let handle = get_runtime().handle().clone();
    let result = handle
        .spawn(async move {
            core_persist_game_local_paths(
                &local_yaml_path,
                game_root.as_deref(),
                docs_root.as_deref(),
            )
            .await
        })
        .await
        .map_err(|err| napi::Error::from_reason(format!("runtime join error: {err}")))?;
    result.map_err(runtime_to_napi_err)
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

    /// Crash generator registry with deprecated checks metadata and optional settings rules.
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
    // Suspect Rules
    // ========================================================================

    /// Structured main-error suspect rules.
    #[napi(getter)]
    pub fn suspect_error_rules(&self) -> Vec<JsSuspectErrorRule> {
        self.inner
            .suspect_error_rules
            .iter()
            .map(JsSuspectErrorRule::from)
            .collect()
    }

    /// Structured stack suspect rules.
    #[napi(getter)]
    pub fn suspect_stack_rules(&self) -> Vec<JsSuspectStackRule> {
        self.inner
            .suspect_stack_rules
            .iter()
            .map(JsSuspectStackRule::from)
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
    pub fn game_mods_freq(&self) -> Vec<JsModSolutionEntry> {
        self.inner
            .game_mods_freq
            .iter()
            .map(JsModSolutionEntry::from)
            .collect()
    }

    /// Solution mods database.
    #[napi(getter)]
    pub fn game_mods_solu(&self) -> Vec<JsModSolutionEntry> {
        self.inner
            .game_mods_solu
            .iter()
            .map(JsModSolutionEntry::from)
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
// 2. YamlSource enum binding
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
// 3. Free Functions
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
    ensure_app_dir_initialized();
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

/// Override the directory used by independent application-local YAML helpers.
/// Call before those helpers if you need a directory other than `process.cwd()`
/// captured at first use. User Settings APIs always take an explicit CLASSIC root.
///
/// @param path - Absolute path to the desired application directory.
#[napi]
pub fn set_application_dir(path: String) {
    classic_registry_core::set_application_dir(PathBuf::from(path));
}

// ============================================================================
// CLASSIC Main.yaml version (schema-gated startup read)
// ============================================================================
//
// Mirrors `classic::config::load_main_yaml_version` on the C++ bridge side:
// startup reader that enforces `client_schemas::MAIN_YAML` before yielding
// `CLASSIC_Info.version`. Message-prefix error discriminator follows the
// `check_app_notification` precedent — napi-rs 3.x `async fn` signatures
// thread errors through `Error<Status>`, where `Status` is a fixed C-style
// enum with no room for custom per-variant codes. The prefix is the only
// representation that survives the async bridge while preserving a stable
// discriminator the consumer can branch on.

/// Error-prefix discriminators on [`load_main_yaml_version`] failures.
const MAIN_YAML_VERSION_CODE_LOAD: &str = "LOAD";
const MAIN_YAML_VERSION_CODE_VERSION_KEY_MISSING: &str = "VERSION_KEY_MISSING";
const MAIN_YAML_VERSION_CODE_VERSION_EMPTY: &str = "VERSION_EMPTY";
const MAIN_YAML_VERSION_CODE_VERSION_NOT_STRING: &str = "VERSION_NOT_STRING";
const MAIN_YAML_VERSION_CODE_VERSION_INVALID: &str = "VERSION_INVALID";
const MAIN_YAML_VERSION_CODE_OTHER: &str = "UNKNOWN";

fn main_yaml_version_error_to_napi(err: MainYamlVersionError) -> napi::Error {
    let code = match &err {
        MainYamlVersionError::Load(_) => MAIN_YAML_VERSION_CODE_LOAD,
        MainYamlVersionError::VersionKeyMissing { .. } => {
            MAIN_YAML_VERSION_CODE_VERSION_KEY_MISSING
        }
        MainYamlVersionError::VersionEmpty { .. } => MAIN_YAML_VERSION_CODE_VERSION_EMPTY,
        MainYamlVersionError::VersionNotString { .. } => MAIN_YAML_VERSION_CODE_VERSION_NOT_STRING,
        MainYamlVersionError::VersionInvalid { .. } => MAIN_YAML_VERSION_CODE_VERSION_INVALID,
        // `MainYamlVersionError` is `#[non_exhaustive]`; new variants in
        // the core crate surface via the `UNKNOWN:` prefix until the
        // binding adds a dedicated code for them.
        _ => MAIN_YAML_VERSION_CODE_OTHER,
    };
    napi::Error::new(Status::GenericFailure, format!("{code}: {err}"))
}

/// Load `CLASSIC Main.yaml` with `MAIN_YAML` schema gating and return
/// `CLASSIC_Info.version`.
///
/// Rejects stale `schema_version: 1.x` files (which still carry the legacy
/// `CLASSIC v...` decoration) before the version ever reaches downstream
/// update-check classification — the schema gate is the whole reason this
/// reader exists. Callers MUST NOT fall back to a raw YAML read on error,
/// since that reintroduces the silent-degradation behavior the gate
/// prevents.
///
/// `bundledYamlDir` empty / null keeps the default relative path
/// (`CLASSIC Data/databases`, resolved against `process.cwd()`). Non-empty
/// values are the explicit install-tree `CLASSIC Data/databases` directory
/// — Node hosts run inside `node.exe` / `bun.exe`, so `process.cwd()`
/// resolution is unreliable unless the caller controls it; prefer an
/// explicit path in that case.
///
/// @param bundledYamlDir Directory containing `CLASSIC Main.yaml`. Pass
///                       `null` or `""` to use the default relative path.
/// @returns The trimmed `CLASSIC_Info.version` value (never empty).
/// @throws an `Error` whose message starts with the variant-keyed code
///         followed by `": "`. Codes: `LOAD:`, `VERSION_KEY_MISSING:`,
///         `VERSION_EMPTY:`, `VERSION_NOT_STRING:`, `VERSION_INVALID:`,
///         `UNKNOWN:`.
#[napi]
pub async fn load_main_yaml_version(bundled_yaml_dir: Option<String>) -> napi::Result<String> {
    let bundled = bundled_yaml_dir.and_then(|s| {
        if s.is_empty() {
            None
        } else {
            Some(PathBuf::from(s))
        }
    });
    let handle = classic_shared_core::get_runtime().handle().clone();
    let result = handle
        .spawn(
            async move { core_load_main_yaml_version_with_bundled_dir(bundled.as_deref()).await },
        )
        .await
        .map_err(|e| napi::Error::from_reason(format!("runtime join error: {e}")))?;
    result.map_err(main_yaml_version_error_to_napi)
}

/// Return the current application directory override, or `undefined` if no
/// override has been registered yet.
#[napi]
pub fn get_application_dir() -> Option<String> {
    classic_registry_core::get_application_dir().map(|p| p.to_string_lossy().into_owned())
}
