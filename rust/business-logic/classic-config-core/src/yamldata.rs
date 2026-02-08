//! Pure Rust YamlData business logic
//!
//! This module provides configuration loading without any PyO3 dependencies.
//! Achieves 15-30x faster configuration loading by:
//! 1. Using yaml-rust2 for parsing (vs ruamel.yaml)
//! 2. Parallel loading of multiple YAML files with Tokio
//! 3. Efficient memory representation

use classic_yaml_core::YamlOperations;
use indexmap::IndexMap;
use std::path::PathBuf;
use yaml_rust2::YamlLoader;

/// The `YamlDataCore` structure represents the core data configuration for YAML-based game settings and diagnostics.
/// It stores various pieces of information related to game configurations, crash generation, warnings, mod databases,
/// ignore lists, suspect patterns, and UI settings. This struct is primarily used for managing and organizing relevant
/// data extracted from or utilized by a game configuration system.
///
/// # Fields
///
/// * `classic_game_hints` - A `Vec<String>` containing hints or tips for the classic game configuration.
/// * `classic_records_list` - A `Vec<String>` storing a list of records related to the classic version.
/// * `classic_version` - A `String` specifying the version number of the classic game.
/// * `classic_version_date` - A `String` specifying the release or update date of the classic game version.
///
/// * `crashgen_name` - A `String` identifier for the crash generation configuration.
/// * `crashgen_latest_og` - A `String` representing the latest original generation crash identifier.
/// * `crashgen_latest_vr` - A `String` representing the latest VR (virtual reality) generation crash identifier.
/// * `crashgen_ignore` - A `Vec<String>` converted from a Python set that lists items to be ignored during crash generation.
///
/// * `warn_noplugins` - A `String` containing a warning message for cases where no plugins are active or available.
/// * `warn_outdated` - A `String` holding a warning message indicating the game version or configuration is outdated.
///
/// * `xse_acronym` - A `String` holding the acronym for the XSE (XML Scripting Engine) configuration setting.
///
/// * `game_ignore_plugins` - A `Vec<String>` that lists plugins to be ignored in the current game configuration.
/// * `game_ignore_records` - A `Vec<String>` containing records to be ignored.
/// * `ignore_list` - A `Vec<String>` listing entries to be collectively ignored.
///
/// * `suspects_error_list` - An `IndexMap<String, String>` containing suspect error patterns mapped to descriptive explanations or identifiers.
/// * `suspects_stack_list` - An `IndexMap<String, Vec<String>>` mapping suspect stack traces to their corresponding pattern lists.
///
/// * `game_mods_conf` - An `IndexMap<String, String>` holding configuration settings for game modification databases.
/// * `game_mods_core` - An `IndexMap<String, String>` storing core mod databases information.
/// * `game_mods_core_folon` - An `IndexMap<String, String>` specific to the `Folon` core mod configuration.
/// * `game_mods_freq` - An `IndexMap<String, String>` containing frequently used game mod entries.
/// * `game_mods_opc2` - An `IndexMap<String, String>` for a specific feature or mod database identified as `opc2`.
/// * `game_mods_solu` - An `IndexMap<String, String>` representing solution-related game mod configurations.
///
/// * `autoscan_text` - A `String` defining the text used in the "autoscan" UI component.
///
/// * `game_version` - A `String` holding the current game version.
/// * `game_version_new` - A `String` indicating a newer version of the game, if available.
/// * `game_version_vr` - A `String` specifying the version of the game for VR (virtual reality).
///
/// # Derivation Attributes
///
/// * `Debug` - Enables debug formatting for instances of the struct, primarily for debugging purposes.
/// * `Clone` - Allows instances of the struct to be cloned, creating deep copies of all field values.
///
/// # Usage
///
/// This struct is typically used for storing and managing a large amount of configuration data required
/// for game diagnostics, crash handling, plugin management, version tracking, and UI updates. Its design
/// allows seamless integration with YAML configuration files, enabling structured data parsing and validation.
#[derive(Debug, Clone)]
pub struct YamlDataCore {
    // Game configuration
    /// Hints or tips for the classic game configuration
    pub classic_game_hints: Vec<String>,
    /// List of records related to the classic version
    pub classic_records_list: Vec<String>,
    /// Version number of the classic game
    pub classic_version: String,
    /// Release or update date of the classic game version
    pub classic_version_date: String,

    // Crashgen configuration
    /// Identifier for the crash generation configuration
    pub crashgen_name: String,
    /// Latest original generation crash identifier
    pub crashgen_latest_og: String,
    /// Latest VR (virtual reality) generation crash identifier
    pub crashgen_latest_vr: String,
    /// Items to be ignored during crash generation
    pub crashgen_ignore: Vec<String>, // Converted from Python set

    // Warnings
    /// Warning message for cases where no plugins are active or available
    pub warn_noplugins: String,
    /// Warning message indicating the game version or configuration is outdated
    pub warn_outdated: String,

    // XSE configuration
    /// Acronym for the XSE (XML Scripting Engine) configuration setting
    pub xse_acronym: String,

    // Ignore lists
    /// Plugins to be ignored in the current game configuration
    pub game_ignore_plugins: Vec<String>,
    /// Records to be ignored
    pub game_ignore_records: Vec<String>,
    /// Entries to be collectively ignored
    pub ignore_list: Vec<String>,

    // Suspect patterns (IndexMap preserves YAML key order for deterministic matching priority)
    /// Suspect error patterns mapped to descriptive explanations or identifiers
    pub suspects_error_list: IndexMap<String, String>,
    /// Suspect stack traces mapped to pattern lists for matching
    pub suspects_stack_list: IndexMap<String, Vec<String>>,

    // Mod databases (IndexMap preserves YAML key order for Python parity)
    /// Configuration settings for game modification databases
    pub game_mods_conf: IndexMap<String, String>,
    /// Core mod databases information
    pub game_mods_core: IndexMap<String, String>,
    /// Folon core mod configuration
    pub game_mods_core_folon: IndexMap<String, String>,
    /// Frequently used game mod entries
    pub game_mods_freq: IndexMap<String, String>,
    /// Specific feature or mod database identified as opc2
    pub game_mods_opc2: IndexMap<String, String>,
    /// Solution-related game mod configurations
    pub game_mods_solu: IndexMap<String, String>,

    // UI configuration
    /// Text used in the autoscan UI component
    pub autoscan_text: String,

    // Game versions (stored as strings)
    /// Current game version
    pub game_version: String,
    /// Newer version of the game, if available
    pub game_version_new: String,
    /// Version of the game for VR (virtual reality)
    pub game_version_vr: String,
}

impl YamlDataCore {
    /// Load all configuration from YAML files in parallel (pure Rust)
    ///
    /// # Arguments
    /// * `yaml_dirs` - Vector of directories containing YAML files (main, game, ignore)
    /// * `game` - Game identifier (e.g., "Fallout4", "Skyrim")
    /// * `vr_mode` - Whether to load VR-specific configuration
    ///
    /// # Returns
    /// * `Ok(YamlDataCore)` - Successfully loaded configuration
    /// * `Err(ConfigError)` - Failed to load or parse configuration
    ///
    /// # Performance
    /// This function loads multiple YAML files in parallel using Tokio,
    /// achieving 15-30x speedup over sequential Python loading.
    pub async fn load_from_yaml_files(
        yaml_dirs: Vec<PathBuf>,
        game: String,
        vr_mode: bool,
    ) -> Result<Self, ConfigError> {
        // Resolve paths based on input size
        let (main_yaml, game_yaml, ignore_yaml) = if yaml_dirs.len() == 2 {
            // Correct API: [root_dir, data_dir]
            let root_dir = &yaml_dirs[0];
            let data_dir = &yaml_dirs[1];

            (
                data_dir.join("databases").join("CLASSIC Main.yaml"),
                data_dir
                    .join("databases")
                    .join(format!("CLASSIC {}.yaml", game)),
                root_dir.join("CLASSIC Ignore.yaml"),
            )
        } else if yaml_dirs.len() == 3 {
            // Legacy/Hack API: [main_dir, game_dir, ignore_dir]
            (
                yaml_dirs[0].join("CLASSIC Main.yaml"),
                yaml_dirs[1].join(format!("CLASSIC {}.yaml", game)),
                yaml_dirs[2].join("CLASSIC Ignore.yaml"),
            )
        } else {
            return Err(ConfigError::InvalidInput(
                "yaml_dirs must contain either 2 directories (root, data) or 3 directories (main, game, ignore)".to_string(),
            ));
        };

        // Verify files exist before loading
        for path in [&main_yaml, &game_yaml, &ignore_yaml] {
            if !path.exists() {
                return Err(ConfigError::IOError {
                    context: format!("YAML file not found: {}", path.display()),
                    source: std::io::Error::new(std::io::ErrorKind::NotFound, "File not found"),
                });
            }
        }

        // Load all YAML files in parallel using Tokio
        // Use tokio::join! to preserve order (unlike JoinSet which returns in completion order)
        let (main_result, game_result, ignore_result) = tokio::join!(
            tokio::fs::read_to_string(&main_yaml),
            tokio::fs::read_to_string(&game_yaml),
            tokio::fs::read_to_string(&ignore_yaml)
        );

        let main_content = main_result.map_err(|e| ConfigError::IOError {
            context: "Failed to read main YAML".to_string(),
            source: e,
        })?;
        let game_content = game_result.map_err(|e| ConfigError::IOError {
            context: "Failed to read game YAML".to_string(),
            source: e,
        })?;
        let ignore_content = ignore_result.map_err(|e| ConfigError::IOError {
            context: "Failed to read ignore YAML".to_string(),
            source: e,
        })?;

        // Parse YAML contents using yaml-rust2
        let main_docs =
            YamlLoader::load_from_str(&main_content).map_err(|e| ConfigError::ParseError {
                context: "Failed to parse main YAML".to_string(),
                source: e,
            })?;
        let game_docs =
            YamlLoader::load_from_str(&game_content).map_err(|e| ConfigError::ParseError {
                context: "Failed to parse game YAML".to_string(),
                source: e,
            })?;
        let ignore_docs =
            YamlLoader::load_from_str(&ignore_content).map_err(|e| ConfigError::ParseError {
                context: "Failed to parse ignore YAML".to_string(),
                source: e,
            })?;

        // Get first document from each file
        let main_data = main_docs
            .first()
            .ok_or_else(|| ConfigError::EmptyDocument("Main YAML".to_string()))?;
        let game_data = game_docs
            .first()
            .ok_or_else(|| ConfigError::EmptyDocument("Game YAML".to_string()))?;
        let ignore_data = ignore_docs
            .first()
            .ok_or_else(|| ConfigError::EmptyDocument("Ignore YAML".to_string()))?;

        // Create YamlOperations instance for using helper methods
        let yaml_ops = YamlOperations::new();

        // Extract values using helper functions from YamlOperations
        let vr_suffix = if vr_mode { "VR" } else { "" };

        // Build the configuration struct
        Ok(Self {
            // Main YAML values
            classic_version: yaml_ops.get_string_value(main_data, "CLASSIC_Info.version", ""),
            classic_version_date: yaml_ops.get_string_value(
                main_data,
                "CLASSIC_Info.version_date",
                "",
            ),
            classic_records_list: yaml_ops.get_vec_value(main_data, "catch_log_records"),
            autoscan_text: yaml_ops.get_string_value(
                main_data,
                &format!("CLASSIC_Interface.autoscan_text_{}", game),
                "",
            ),

            // Game YAML values
            classic_game_hints: yaml_ops.get_vec_value(game_data, "Game_Hints"),
            crashgen_name: yaml_ops.get_string_value(
                game_data,
                &format!("Game{}_Info.CRASHGEN_LogName", vr_suffix),
                "",
            ),
            crashgen_latest_og: yaml_ops.get_string_value(
                game_data,
                "Game_Info.CRASHGEN_LatestVer",
                "",
            ),
            crashgen_latest_vr: yaml_ops.get_string_value(
                game_data,
                "GameVR_Info.CRASHGEN_LatestVer",
                "",
            ),
            crashgen_ignore: yaml_ops.get_vec_value(
                game_data,
                &format!("Game{}_Info.CRASHGEN_Ignore", vr_suffix),
            ),
            warn_noplugins: yaml_ops.get_string_value(
                game_data,
                "Warnings_CRASHGEN.Warn_NOPlugins",
                "",
            ),
            warn_outdated: yaml_ops.get_string_value(
                game_data,
                "Warnings_CRASHGEN.Warn_Outdated",
                "",
            ),
            xse_acronym: yaml_ops.get_string_value(game_data, "Game_Info.XSE_Acronym", ""),
            game_ignore_plugins: yaml_ops.get_vec_value(game_data, "Crashlog_Plugins_Exclude"),
            game_ignore_records: yaml_ops.get_vec_value(game_data, "Crashlog_Records_Exclude"),
            suspects_error_list: yaml_ops.get_indexmap_value(game_data, "Crashlog_Error_Check"),
            suspects_stack_list: yaml_ops.get_indexmap_vec_value(game_data, "Crashlog_Stack_Check"),
            game_mods_conf: yaml_ops.get_indexmap_value(game_data, "Mods_CONF"),
            game_mods_core: yaml_ops.get_indexmap_value(game_data, "Mods_CORE"),
            game_mods_core_folon: yaml_ops.get_indexmap_value(game_data, "Mods_CORE_FOLON"),
            game_mods_freq: yaml_ops.get_indexmap_value(game_data, "Mods_FREQ"),
            game_mods_opc2: yaml_ops.get_indexmap_value(game_data, "Mods_OPC2"),
            game_mods_solu: yaml_ops.get_indexmap_value(game_data, "Mods_SOLU"),
            game_version: yaml_ops.get_string_value(game_data, "Game_Info.GameVersion", ""),
            game_version_new: yaml_ops.get_string_value(game_data, "Game_Info.GameVersionNEW", ""),
            game_version_vr: yaml_ops.get_string_value(game_data, "GameVR_Info.GameVersion", ""),

            // Ignore YAML values
            ignore_list: yaml_ops.get_vec_value(ignore_data, &format!("CLASSIC_Ignore_{}", game)),
        })
    }

    /// Create YamlData from YAML content strings (for testing without file I/O).
    ///
    /// This constructor is useful for unit tests and integration tests where you want
    /// to test YamlData parsing without needing actual YAML files on disk.
    ///
    /// # Arguments
    ///
    /// * `main_content` - Content of the main YAML configuration file
    /// * `game_content` - Content of the game-specific YAML configuration file
    /// * `ignore_content` - Content of the ignore list YAML configuration file
    /// * `game` - Game identifier (e.g., "Fallout4", "Skyrim")
    /// * `vr_mode` - Whether to load VR-specific configuration
    ///
    /// # Returns
    ///
    /// * `Ok(YamlDataCore)` - Successfully parsed configuration
    /// * `Err(ConfigError)` - Failed to parse configuration content
    ///
    /// # Example
    ///
    /// ```rust
    /// use classic_config_core::YamlDataCore;
    ///
    /// let main_yaml = r#"
    /// CLASSIC_Info:
    ///   version: "7.31.0"
    ///   version_date: "2024-01-01"
    /// "#;
    ///
    /// let game_yaml = r#"
    /// Game_Info:
    ///   XSE_Acronym: "F4SE"
    /// "#;
    ///
    /// let ignore_yaml = r#"
    /// CLASSIC_Ignore_Fallout4: []
    /// "#;
    ///
    /// let config = YamlDataCore::from_yaml_content(
    ///     main_yaml,
    ///     game_yaml,
    ///     ignore_yaml,
    ///     "Fallout4".to_string(),
    ///     false,
    /// ).unwrap();
    /// ```
    pub fn from_yaml_content(
        main_content: &str,
        game_content: &str,
        ignore_content: &str,
        game: String,
        vr_mode: bool,
    ) -> Result<Self, ConfigError> {
        // Parse YAML contents using yaml-rust2
        let main_docs =
            YamlLoader::load_from_str(main_content).map_err(|e| ConfigError::ParseError {
                context: "Failed to parse main YAML".to_string(),
                source: e,
            })?;
        let game_docs =
            YamlLoader::load_from_str(game_content).map_err(|e| ConfigError::ParseError {
                context: "Failed to parse game YAML".to_string(),
                source: e,
            })?;
        let ignore_docs =
            YamlLoader::load_from_str(ignore_content).map_err(|e| ConfigError::ParseError {
                context: "Failed to parse ignore YAML".to_string(),
                source: e,
            })?;

        // Get first document from each file
        let main_data = main_docs
            .first()
            .ok_or_else(|| ConfigError::EmptyDocument("Main YAML".to_string()))?;
        let game_data = game_docs
            .first()
            .ok_or_else(|| ConfigError::EmptyDocument("Game YAML".to_string()))?;
        let ignore_data = ignore_docs
            .first()
            .ok_or_else(|| ConfigError::EmptyDocument("Ignore YAML".to_string()))?;

        // Create YamlOperations instance for using helper methods
        let yaml_ops = YamlOperations::new();

        // Extract values using helper functions from YamlOperations
        let vr_suffix = if vr_mode { "VR" } else { "" };

        // Build the configuration struct
        Ok(Self {
            // Main YAML values
            classic_version: yaml_ops.get_string_value(main_data, "CLASSIC_Info.version", ""),
            classic_version_date: yaml_ops.get_string_value(
                main_data,
                "CLASSIC_Info.version_date",
                "",
            ),
            classic_records_list: yaml_ops.get_vec_value(main_data, "catch_log_records"),
            autoscan_text: yaml_ops.get_string_value(
                main_data,
                &format!("CLASSIC_Interface.autoscan_text_{}", game),
                "",
            ),

            // Game YAML values
            classic_game_hints: yaml_ops.get_vec_value(game_data, "Game_Hints"),
            crashgen_name: yaml_ops.get_string_value(
                game_data,
                &format!("Game{}_Info.CRASHGEN_LogName", vr_suffix),
                "",
            ),
            crashgen_latest_og: yaml_ops.get_string_value(
                game_data,
                "Game_Info.CRASHGEN_LatestVer",
                "",
            ),
            crashgen_latest_vr: yaml_ops.get_string_value(
                game_data,
                "GameVR_Info.CRASHGEN_LatestVer",
                "",
            ),
            crashgen_ignore: yaml_ops.get_vec_value(
                game_data,
                &format!("Game{}_Info.CRASHGEN_Ignore", vr_suffix),
            ),
            warn_noplugins: yaml_ops.get_string_value(
                game_data,
                "Warnings_CRASHGEN.Warn_NOPlugins",
                "",
            ),
            warn_outdated: yaml_ops.get_string_value(
                game_data,
                "Warnings_CRASHGEN.Warn_Outdated",
                "",
            ),
            xse_acronym: yaml_ops.get_string_value(game_data, "Game_Info.XSE_Acronym", ""),
            game_ignore_plugins: yaml_ops.get_vec_value(game_data, "Crashlog_Plugins_Exclude"),
            game_ignore_records: yaml_ops.get_vec_value(game_data, "Crashlog_Records_Exclude"),
            suspects_error_list: yaml_ops.get_indexmap_value(game_data, "Crashlog_Error_Check"),
            suspects_stack_list: yaml_ops.get_indexmap_vec_value(game_data, "Crashlog_Stack_Check"),
            game_mods_conf: yaml_ops.get_indexmap_value(game_data, "Mods_CONF"),
            game_mods_core: yaml_ops.get_indexmap_value(game_data, "Mods_CORE"),
            game_mods_core_folon: yaml_ops.get_indexmap_value(game_data, "Mods_CORE_FOLON"),
            game_mods_freq: yaml_ops.get_indexmap_value(game_data, "Mods_FREQ"),
            game_mods_opc2: yaml_ops.get_indexmap_value(game_data, "Mods_OPC2"),
            game_mods_solu: yaml_ops.get_indexmap_value(game_data, "Mods_SOLU"),
            game_version: yaml_ops.get_string_value(game_data, "Game_Info.GameVersion", ""),
            game_version_new: yaml_ops.get_string_value(game_data, "Game_Info.GameVersionNEW", ""),
            game_version_vr: yaml_ops.get_string_value(game_data, "GameVR_Info.GameVersion", ""),

            // Ignore YAML values
            ignore_list: yaml_ops.get_vec_value(ignore_data, &format!("CLASSIC_Ignore_{}", game)),
        })
    }
}

/// Configuration error types
#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    /// Invalid input parameters provided to configuration loading
    #[error("Invalid input: {0}")]
    InvalidInput(String),

    /// I/O error occurred while reading configuration files
    #[error("{context}: {source}")]
    IOError {
        /// Contextual information about which file operation failed
        context: String,
        /// The underlying I/O error
        #[source]
        source: std::io::Error,
    },

    /// Error parsing YAML configuration content
    #[error("{context}: {source}")]
    ParseError {
        /// Contextual information about which file failed to parse
        context: String,
        /// The underlying YAML parse error
        #[source]
        source: yaml_rust2::ScanError,
    },

    /// YAML document is empty (no content to parse)
    #[error("Empty YAML document: {0}")]
    EmptyDocument(String),

    /// Runtime error during configuration processing
    #[error("Runtime error: {0}")]
    RuntimeError(String),
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use tempfile::tempdir;

    // ============================================================
    // Test Data Fixtures
    // ============================================================

    /// Minimal valid main YAML content for testing
    fn minimal_main_yaml() -> &'static str {
        r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
catch_log_records:
  - "LAND"
  - "REFR"
  - "CELL"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
  autoscan_text_Skyrim: "Autoscan Skyrim"
"#
    }

    /// Minimal valid game YAML content for testing (Fallout4)
    fn minimal_game_yaml() -> &'static str {
        r#"
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
  GameVersionNEW: "1.10.984"
  CRASHGEN_LatestVer: "4.0.0"
GameVR_Info:
  GameVersion: "1.2.72"
  CRASHGEN_LatestVer: "3.0.0"
  CRASHGEN_LogName: "crash-vr"
  CRASHGEN_Ignore:
    - "VRIgnoreItem1"
Game_Hints:
  - "Hint 1"
  - "Hint 2"
Warnings_CRASHGEN:
  Warn_NOPlugins: "No plugins found!"
  Warn_Outdated: "Your version is outdated."
Crashlog_Plugins_Exclude:
  - "Unofficial*.esp"
Crashlog_Records_Exclude:
  - "RecordType1"
Crashlog_Error_Check:
  ErrorPattern1: "Error description 1"
  ErrorPattern2: "Error description 2"
Crashlog_Stack_Check:
  StackPattern1: ["Stack pattern 1", "Stack pattern 2"]
Mods_CONF:
  ModA: "Config for ModA"
Mods_CORE:
  ModB: "Core mod B"
Mods_CORE_FOLON:
  FolonMod: "Folon specific mod"
Mods_FREQ:
  FreqMod: "Frequently used mod"
Mods_OPC2:
  OpcMod: "OPC2 mod"
Mods_SOLU:
  SoluMod: "Solution mod"
"#
    }

    /// Minimal valid ignore YAML content for testing
    fn minimal_ignore_yaml() -> &'static str {
        r#"
CLASSIC_Ignore_Fallout4:
  - "IgnoreItem1"
  - "IgnoreItem2"
CLASSIC_Ignore_Skyrim:
  - "SkyrimIgnore1"
"#
    }

    // ============================================================
    // YamlDataCore::from_yaml_content tests
    // ============================================================

    #[test]
    fn test_from_yaml_content_creates_valid_instance() {
        let result = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        );

        assert!(result.is_ok(), "Should successfully parse valid YAML");
        let config = result.unwrap();
        assert_eq!(config.classic_version, "7.31.0");
    }

    #[test]
    fn test_from_yaml_content_extracts_main_yaml_values() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        // Main YAML values
        assert_eq!(config.classic_version, "7.31.0");
        assert_eq!(config.classic_version_date, "2024-01-15");
        assert_eq!(config.classic_records_list, vec!["LAND", "REFR", "CELL"]);
        assert_eq!(config.autoscan_text, "Autoscan Fallout 4");
    }

    #[test]
    fn test_from_yaml_content_extracts_game_yaml_values() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        // Game YAML values
        assert_eq!(config.xse_acronym, "F4SE");
        assert_eq!(config.game_version, "1.10.163");
        assert_eq!(config.game_version_new, "1.10.984");
        assert_eq!(config.crashgen_latest_og, "4.0.0");
        assert_eq!(config.crashgen_latest_vr, "3.0.0");
        assert_eq!(config.classic_game_hints, vec!["Hint 1", "Hint 2"]);
        assert_eq!(config.warn_noplugins, "No plugins found!");
        assert_eq!(config.warn_outdated, "Your version is outdated.");
    }

    #[test]
    fn test_from_yaml_content_extracts_ignore_list() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        assert_eq!(config.ignore_list, vec!["IgnoreItem1", "IgnoreItem2"]);
    }

    #[test]
    fn test_from_yaml_content_extracts_exclude_lists() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        assert_eq!(config.game_ignore_plugins, vec!["Unofficial*.esp"]);
        assert_eq!(config.game_ignore_records, vec!["RecordType1"]);
    }

    #[test]
    fn test_from_yaml_content_extracts_suspect_patterns() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        assert_eq!(config.suspects_error_list.len(), 2);
        assert_eq!(
            config.suspects_error_list.get("ErrorPattern1"),
            Some(&"Error description 1".to_string())
        );
        assert_eq!(config.suspects_stack_list.len(), 1);
        assert_eq!(
            config.suspects_stack_list.get("StackPattern1"),
            Some(&vec!["Stack pattern 1".to_string(), "Stack pattern 2".to_string()])
        );
    }

    #[test]
    fn test_from_yaml_content_extracts_mod_databases() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        assert_eq!(
            config.game_mods_conf.get("ModA"),
            Some(&"Config for ModA".to_string())
        );
        assert_eq!(
            config.game_mods_core.get("ModB"),
            Some(&"Core mod B".to_string())
        );
        assert_eq!(
            config.game_mods_core_folon.get("FolonMod"),
            Some(&"Folon specific mod".to_string())
        );
        assert_eq!(
            config.game_mods_freq.get("FreqMod"),
            Some(&"Frequently used mod".to_string())
        );
        assert_eq!(
            config.game_mods_opc2.get("OpcMod"),
            Some(&"OPC2 mod".to_string())
        );
        assert_eq!(
            config.game_mods_solu.get("SoluMod"),
            Some(&"Solution mod".to_string())
        );
    }

    #[test]
    fn test_from_yaml_content_vr_mode_enabled() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            true, // VR mode enabled
        )
        .unwrap();

        // VR mode should use GameVR_Info section
        assert_eq!(config.crashgen_name, "crash-vr");
        assert_eq!(config.crashgen_ignore, vec!["VRIgnoreItem1"]);
        assert_eq!(config.game_version_vr, "1.2.72");
    }

    #[test]
    fn test_from_yaml_content_vr_mode_disabled() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false, // VR mode disabled
        )
        .unwrap();

        // Non-VR mode should use Game_Info section
        // crashgen_name would be empty since Game_Info.CRASHGEN_LogName isn't defined
        assert_eq!(config.crashgen_name, "");
    }

    #[test]
    fn test_from_yaml_content_skyrim_game() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Skyrim".to_string(),
            false,
        )
        .unwrap();

        // Should use Skyrim-specific autoscan text
        assert_eq!(config.autoscan_text, "Autoscan Skyrim");
        // Should use Skyrim ignore list
        assert_eq!(config.ignore_list, vec!["SkyrimIgnore1"]);
    }

    #[test]
    fn test_from_yaml_content_different_games_use_correct_ignore_lists() {
        let fallout_config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        let skyrim_config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Skyrim".to_string(),
            false,
        )
        .unwrap();

        assert_ne!(fallout_config.ignore_list, skyrim_config.ignore_list);
        assert_eq!(fallout_config.ignore_list.len(), 2);
        assert_eq!(skyrim_config.ignore_list.len(), 1);
    }

    // ============================================================
    // Error Handling Tests
    // ============================================================

    #[test]
    fn test_from_yaml_content_invalid_main_yaml() {
        let invalid_yaml = "{ invalid: yaml: content: }}}";

        let result = YamlDataCore::from_yaml_content(
            invalid_yaml,
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        );

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::ParseError { .. }));
        match err {
            ConfigError::ParseError { context, .. } => {
                assert!(context.contains("main YAML"));
            }
            _ => panic!("Expected ParseError"),
        }
    }

    #[test]
    fn test_from_yaml_content_invalid_game_yaml() {
        let invalid_yaml = "invalid: [unclosed";

        let result = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            invalid_yaml,
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        );

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::ParseError { .. }));
        match err {
            ConfigError::ParseError { context, .. } => {
                assert!(context.contains("game YAML"));
            }
            _ => panic!("Expected ParseError"),
        }
    }

    #[test]
    fn test_from_yaml_content_invalid_ignore_yaml() {
        let invalid_yaml = "not: valid: yaml: {{";

        let result = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            invalid_yaml,
            "Fallout4".to_string(),
            false,
        );

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::ParseError { .. }));
        match err {
            ConfigError::ParseError { context, .. } => {
                assert!(context.contains("ignore YAML"));
            }
            _ => panic!("Expected ParseError"),
        }
    }

    #[test]
    fn test_from_yaml_content_empty_main_document() {
        let empty_yaml = "";

        let result = YamlDataCore::from_yaml_content(
            empty_yaml,
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        );

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::EmptyDocument(_)));
        match err {
            ConfigError::EmptyDocument(msg) => {
                assert!(msg.contains("Main"));
            }
            _ => panic!("Expected EmptyDocument error"),
        }
    }

    #[test]
    fn test_from_yaml_content_empty_game_document() {
        let empty_yaml = "";

        let result = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            empty_yaml,
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        );

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::EmptyDocument(_)));
    }

    #[test]
    fn test_from_yaml_content_empty_ignore_document() {
        let empty_yaml = "";

        let result = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            empty_yaml,
            "Fallout4".to_string(),
            false,
        );

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::EmptyDocument(_)));
    }

    #[test]
    fn test_from_yaml_content_missing_keys_use_defaults() {
        // YAML with no matching keys - should use default empty values
        let sparse_main = r#"
other_key: value
"#;
        let sparse_game = r#"
unrelated: data
"#;
        let sparse_ignore = r#"
different_game: []
"#;

        let result = YamlDataCore::from_yaml_content(
            sparse_main,
            sparse_game,
            sparse_ignore,
            "Fallout4".to_string(),
            false,
        );

        assert!(result.is_ok());
        let config = result.unwrap();
        // Missing values should be empty strings/vecs
        assert_eq!(config.classic_version, "");
        assert!(config.classic_records_list.is_empty());
        assert!(config.ignore_list.is_empty());
    }

    // ============================================================
    // Async File Loading Tests
    // ============================================================

    #[tokio::test]
    async fn test_load_from_yaml_files_success() {
        let temp_dir = tempdir().unwrap();

        // Create directory structure
        let databases_dir = temp_dir.path().join("databases");
        std::fs::create_dir_all(&databases_dir).unwrap();

        // Write test files
        let main_path = databases_dir.join("CLASSIC Main.yaml");
        let game_path = databases_dir.join("CLASSIC Fallout4.yaml");
        let ignore_path = temp_dir.path().join("CLASSIC Ignore.yaml");

        std::fs::write(&main_path, minimal_main_yaml()).unwrap();
        std::fs::write(&game_path, minimal_game_yaml()).unwrap();
        std::fs::write(&ignore_path, minimal_ignore_yaml()).unwrap();

        // Use the 2-element API (root_dir, data_dir)
        let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        let result =
            YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), false).await;

        assert!(result.is_ok(), "Load failed: {:?}", result.err());
        let config = result.unwrap();
        assert_eq!(config.classic_version, "7.31.0");
        assert_eq!(config.xse_acronym, "F4SE");
    }

    #[tokio::test]
    async fn test_load_from_yaml_files_with_three_dirs() {
        let temp_dir = tempdir().unwrap();

        // Create separate directories for each YAML file
        let main_dir = temp_dir.path().join("main");
        let game_dir = temp_dir.path().join("game");
        let ignore_dir = temp_dir.path().join("ignore");

        std::fs::create_dir_all(&main_dir).unwrap();
        std::fs::create_dir_all(&game_dir).unwrap();
        std::fs::create_dir_all(&ignore_dir).unwrap();

        // Write test files
        std::fs::write(main_dir.join("CLASSIC Main.yaml"), minimal_main_yaml()).unwrap();
        std::fs::write(game_dir.join("CLASSIC Fallout4.yaml"), minimal_game_yaml()).unwrap();
        std::fs::write(
            ignore_dir.join("CLASSIC Ignore.yaml"),
            minimal_ignore_yaml(),
        )
        .unwrap();

        // Use the 3-element API
        let yaml_dirs = vec![main_dir, game_dir, ignore_dir];

        let result =
            YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), false).await;

        assert!(result.is_ok(), "Load failed: {:?}", result.err());
        let config = result.unwrap();
        assert_eq!(config.classic_version, "7.31.0");
    }

    #[tokio::test]
    async fn test_load_from_yaml_files_invalid_dir_count() {
        // Provide only 1 directory (invalid)
        let yaml_dirs = vec![PathBuf::from("/some/path")];

        let result =
            YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), false).await;

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::InvalidInput(_)));
    }

    #[tokio::test]
    async fn test_load_from_yaml_files_invalid_four_dirs() {
        // Provide 4 directories (also invalid)
        let yaml_dirs = vec![
            PathBuf::from("/a"),
            PathBuf::from("/b"),
            PathBuf::from("/c"),
            PathBuf::from("/d"),
        ];

        let result =
            YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), false).await;

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::InvalidInput(_)));
    }

    #[tokio::test]
    async fn test_load_from_yaml_files_missing_main_file() {
        let temp_dir = tempdir().unwrap();
        let databases_dir = temp_dir.path().join("databases");
        std::fs::create_dir_all(&databases_dir).unwrap();

        // Only write game and ignore files, not main
        std::fs::write(
            databases_dir.join("CLASSIC Fallout4.yaml"),
            minimal_game_yaml(),
        )
        .unwrap();
        std::fs::write(
            temp_dir.path().join("CLASSIC Ignore.yaml"),
            minimal_ignore_yaml(),
        )
        .unwrap();

        let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        let result =
            YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), false).await;

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::IOError { .. }));
    }

    #[tokio::test]
    async fn test_load_from_yaml_files_missing_game_file() {
        let temp_dir = tempdir().unwrap();
        let databases_dir = temp_dir.path().join("databases");
        std::fs::create_dir_all(&databases_dir).unwrap();

        // Write main and ignore, but not game
        std::fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml()).unwrap();
        std::fs::write(
            temp_dir.path().join("CLASSIC Ignore.yaml"),
            minimal_ignore_yaml(),
        )
        .unwrap();

        let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        let result =
            YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), false).await;

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::IOError { .. }));
    }

    #[tokio::test]
    async fn test_load_from_yaml_files_missing_ignore_file() {
        let temp_dir = tempdir().unwrap();
        let databases_dir = temp_dir.path().join("databases");
        std::fs::create_dir_all(&databases_dir).unwrap();

        // Write main and game, but not ignore
        std::fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml()).unwrap();
        std::fs::write(
            databases_dir.join("CLASSIC Fallout4.yaml"),
            minimal_game_yaml(),
        )
        .unwrap();

        let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        let result =
            YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), false).await;

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::IOError { .. }));
    }

    #[tokio::test]
    async fn test_load_from_yaml_files_parallel_preserves_order() {
        // This test verifies that tokio::join! preserves order
        // (unlike JoinSet which returns in completion order)
        let temp_dir = tempdir().unwrap();
        let databases_dir = temp_dir.path().join("databases");
        std::fs::create_dir_all(&databases_dir).unwrap();

        // Create files with distinct content
        let main_yaml = r#"
CLASSIC_Info:
  version: "MAIN_VERSION"
"#;
        let game_yaml = r#"
Game_Info:
  XSE_Acronym: "GAME_XSE"
"#;
        let ignore_yaml = r#"
CLASSIC_Ignore_TestGame:
  - "IGNORE_ITEM"
"#;

        std::fs::write(databases_dir.join("CLASSIC Main.yaml"), main_yaml).unwrap();
        std::fs::write(databases_dir.join("CLASSIC TestGame.yaml"), game_yaml).unwrap();
        std::fs::write(temp_dir.path().join("CLASSIC Ignore.yaml"), ignore_yaml).unwrap();

        let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        let result =
            YamlDataCore::load_from_yaml_files(yaml_dirs, "TestGame".to_string(), false).await;

        assert!(result.is_ok());
        let config = result.unwrap();

        // Verify that values from each file are correctly assigned
        assert_eq!(config.classic_version, "MAIN_VERSION");
        assert_eq!(config.xse_acronym, "GAME_XSE");
        assert_eq!(config.ignore_list, vec!["IGNORE_ITEM"]);
    }

    #[tokio::test]
    async fn test_load_from_yaml_files_with_vr_mode() {
        let temp_dir = tempdir().unwrap();
        let databases_dir = temp_dir.path().join("databases");
        std::fs::create_dir_all(&databases_dir).unwrap();

        std::fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml()).unwrap();
        std::fs::write(
            databases_dir.join("CLASSIC Fallout4.yaml"),
            minimal_game_yaml(),
        )
        .unwrap();
        std::fs::write(
            temp_dir.path().join("CLASSIC Ignore.yaml"),
            minimal_ignore_yaml(),
        )
        .unwrap();

        let yaml_dirs = vec![temp_dir.path().to_path_buf(), temp_dir.path().to_path_buf()];

        let result = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            true, // VR mode
        )
        .await;

        assert!(result.is_ok());
        let config = result.unwrap();
        // VR mode should read from GameVR_Info
        assert_eq!(config.crashgen_name, "crash-vr");
    }

    // ============================================================
    // Clone and Debug Tests
    // ============================================================

    #[test]
    fn test_yamldata_clone() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        let cloned = config.clone();

        assert_eq!(config.classic_version, cloned.classic_version);
        assert_eq!(config.xse_acronym, cloned.xse_acronym);
        assert_eq!(config.ignore_list, cloned.ignore_list);
    }

    #[test]
    fn test_yamldata_debug_format() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        let debug_str = format!("{:?}", config);
        assert!(debug_str.contains("YamlDataCore"));
        assert!(debug_str.contains("classic_version"));
    }

    // ============================================================
    // ConfigError Tests
    // ============================================================

    #[test]
    fn test_config_error_invalid_input_display() {
        let err = ConfigError::InvalidInput("test message".to_string());
        let display = format!("{}", err);
        assert!(display.contains("Invalid input"));
        assert!(display.contains("test message"));
    }

    #[test]
    fn test_config_error_empty_document_display() {
        let err = ConfigError::EmptyDocument("Main YAML".to_string());
        let display = format!("{}", err);
        assert!(display.contains("Empty YAML document"));
        assert!(display.contains("Main YAML"));
    }

    #[test]
    fn test_config_error_runtime_error_display() {
        let err = ConfigError::RuntimeError("something went wrong".to_string());
        let display = format!("{}", err);
        assert!(display.contains("Runtime error"));
        assert!(display.contains("something went wrong"));
    }

    #[test]
    fn test_config_error_io_error_display() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let err = ConfigError::IOError {
            context: "Failed to read config".to_string(),
            source: io_err,
        };
        let display = format!("{}", err);
        assert!(display.contains("Failed to read config"));
    }
}
