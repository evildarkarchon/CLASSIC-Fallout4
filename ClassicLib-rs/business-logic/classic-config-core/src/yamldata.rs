//! Pure Rust YamlData business logic
//!
//! This module provides configuration loading without any PyO3 dependencies.
//! Achieves 15-30x faster configuration loading by:
//! 1. Using yaml-rust2 for parsing (vs ruamel.yaml)
//! 2. Parallel loading of multiple YAML files with Tokio
//! 3. Efficient memory representation

use classic_crashgen_settings_core::{
    CheckRule, ConfigLayout, CrashgenSettingsRules, ExpectedValue, Predicate, PreflightAction,
    PreflightActionKind, PreflightRule, RuleMessages, RuleSeverity, RuleTarget, TargetValueType,
};
use classic_yaml_core::YamlOperations;
use indexmap::IndexMap;
use std::collections::HashMap;
use std::path::PathBuf;
use yaml_rust2::{Yaml, YamlLoader};

/// Raw per-crashgen settings configuration deserialized from YAML.
///
/// This is a simple transport type used to carry `Crashgen_Registry` data
/// from `YamlDataCore` into the crash-log analysis layer (`classic-scanlog-core`),
/// which converts it to the `CrashgenRegistry` / `CrashgenEntry` types.
#[derive(Debug, Clone)]
pub struct CrashgenEntryRaw {
    /// Bracket header used by this crashgen (e.g., `"[Compatibility]"`), for display only.
    pub display_section: String,
    /// Settings keys to skip in `check_disabled_settings()`.
    pub ignore_keys: Vec<String>,
    /// String names of named checks (e.g., `"achievements"`, `"memory_management"`).
    pub checks: Vec<String>,
    /// Optional settings rules schema version.
    pub settings_rules_version: Option<u32>,
    /// Optional full settings rules block.
    pub settings_rules: Option<CrashgenSettingsRules>,
}

/// Parse the `Crashgen_Registry` top-level key from a game YAML document.
///
/// Returns a map of crashgen name → raw entry data (including the `"default"` key if present).
/// Missing or malformed entries are silently skipped.
fn parse_crashgen_registry(game_data: &Yaml) -> HashMap<String, CrashgenEntryRaw> {
    let mut result = HashMap::new();

    let Some(registry_node) = game_data["Crashgen_Registry"].as_hash() else {
        return result;
    };

    fn parse_string_list_field(
        entry_name: &str,
        field_name: &str,
        field_yaml: &Yaml,
    ) -> Vec<String> {
        if let Some(items) = field_yaml.as_vec() {
            items
                .iter()
                .enumerate()
                .filter_map(|(index, item)| match item.as_str() {
                    Some(text) => Some(text.to_string()),
                    None => {
                        log::debug!(
                            "Skipping non-string Crashgen_Registry.{}.{} item at index {}: {:?}",
                            entry_name,
                            field_name,
                            index,
                            item
                        );
                        None
                    }
                })
                .collect()
        } else {
            if !matches!(field_yaml, Yaml::BadValue) {
                log::debug!(
                    "Crashgen_Registry.{}.{} is malformed (expected array), using empty list: {:?}",
                    entry_name,
                    field_name,
                    field_yaml
                );
            }
            Vec::new()
        }
    }

    fn parse_version_field(entry_name: &str, field_yaml: &Yaml) -> Option<u32> {
        match field_yaml {
            Yaml::Integer(value) if *value >= 0 => Some(*value as u32),
            Yaml::String(value) => value.trim().parse::<u32>().ok(),
            Yaml::BadValue => None,
            other => {
                log::debug!(
                    "Crashgen_Registry.{}.settings_rules_version is malformed (expected int/string): {:?}",
                    entry_name,
                    other
                );
                None
            }
        }
    }

    fn parse_predicate(yaml: &Yaml) -> Option<Predicate> {
        let map = yaml.as_hash()?;

        if let Some(all_yaml) = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("all")).then_some(v))
        {
            let items = all_yaml
                .as_vec()?
                .iter()
                .filter_map(parse_predicate)
                .collect::<Vec<_>>();
            return Some(Predicate::All(items));
        }

        if let Some(any_yaml) = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("any")).then_some(v))
        {
            let items = any_yaml
                .as_vec()?
                .iter()
                .filter_map(parse_predicate)
                .collect::<Vec<_>>();
            return Some(Predicate::Any(items));
        }

        if let Some(not_yaml) = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("not")).then_some(v))
        {
            return parse_predicate(not_yaml).map(|item| Predicate::Not(Box::new(item)));
        }

        if let Some(plugin_yaml) = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("plugin_any")).then_some(v))
        {
            let plugins = plugin_yaml
                .as_vec()?
                .iter()
                .filter_map(Yaml::as_str)
                .map(|value| value.to_lowercase())
                .collect::<Vec<_>>();
            return Some(Predicate::PluginAny(plugins));
        }

        if let Some(layout_yaml) = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("config_layout_is")).then_some(v))
        {
            return ConfigLayout::parse(layout_yaml.as_str()?).map(Predicate::ConfigLayoutIs);
        }

        if let Some(version_yaml) = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("crashgen_version_lt")).then_some(v))
        {
            let parts = version_yaml
                .as_str()?
                .split('.')
                .map(|part| part.trim().parse::<u32>().ok())
                .collect::<Vec<_>>();
            if parts.len() == 3 {
                return Some(Predicate::CrashgenVersionLt((
                    parts[0]?, parts[1]?, parts[2]?,
                )));
            }
        }

        None
    }

    fn parse_severity(yaml: &Yaml, default: RuleSeverity) -> RuleSeverity {
        yaml.as_str()
            .and_then(RuleSeverity::parse)
            .unwrap_or(default)
    }

    fn parse_preflight_rule(yaml: &Yaml) -> Option<PreflightRule> {
        let map = yaml.as_hash()?;
        let id = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("id")).then_some(v))?
            .as_str()?
            .to_string();

        let when = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("when")).then_some(v))
            .and_then(parse_predicate)
            .unwrap_or(Predicate::Always);

        let action_yaml = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("action")).then_some(v))?;
        let action_map = action_yaml.as_hash()?;

        let kind = action_map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("kind")).then_some(v))
            .and_then(Yaml::as_str)
            .and_then(PreflightActionKind::parse)
            .unwrap_or(PreflightActionKind::Notice);

        let severity = action_map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("severity")).then_some(v))
            .map(|value| parse_severity(value, RuleSeverity::Info))
            .unwrap_or(RuleSeverity::Info);

        let message = action_map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("message")).then_some(v))?
            .as_str()?
            .to_string();

        let fix = action_map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("fix")).then_some(v))
            .and_then(Yaml::as_str)
            .map(ToString::to_string);

        Some(PreflightRule {
            id,
            when,
            action: PreflightAction {
                kind,
                severity,
                message,
                fix,
            },
        })
    }

    fn parse_expected_value(expect_yaml: &Yaml) -> Option<ExpectedValue> {
        let map = expect_yaml.as_hash()?;
        let equals_yaml = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("equals")).then_some(v))?;
        match equals_yaml {
            Yaml::Boolean(value) => Some(ExpectedValue::Bool(*value)),
            Yaml::Integer(value) => Some(ExpectedValue::Int(*value)),
            Yaml::String(value) => Some(ExpectedValue::String(value.to_string())),
            _ => None,
        }
    }

    fn parse_check_rule(yaml: &Yaml) -> Option<CheckRule> {
        let map = yaml.as_hash()?;
        let id = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("id")).then_some(v))?
            .as_str()?
            .to_string();

        let when = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("when")).then_some(v))
            .and_then(parse_predicate)
            .unwrap_or(Predicate::Always);

        let target_map = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("target")).then_some(v))?
            .as_hash()?;
        let target = RuleTarget {
            section: target_map
                .iter()
                .find_map(|(k, v)| (k.as_str() == Some("section")).then_some(v))?
                .as_str()?
                .to_string(),
            key: target_map
                .iter()
                .find_map(|(k, v)| (k.as_str() == Some("key")).then_some(v))?
                .as_str()?
                .to_string(),
            value_type: target_map
                .iter()
                .find_map(|(k, v)| (k.as_str() == Some("type")).then_some(v))
                .and_then(Yaml::as_str)
                .and_then(TargetValueType::parse)
                .unwrap_or(TargetValueType::Bool),
        };

        let expect = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("expect")).then_some(v))
            .and_then(parse_expected_value)?;

        let messages_map = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("messages")).then_some(v))?
            .as_hash()?;
        let messages = RuleMessages {
            fail: messages_map
                .iter()
                .find_map(|(k, v)| (k.as_str() == Some("fail")).then_some(v))?
                .as_str()?
                .to_string(),
            fix: messages_map
                .iter()
                .find_map(|(k, v)| (k.as_str() == Some("fix")).then_some(v))
                .and_then(Yaml::as_str)
                .map(ToString::to_string),
            pass: messages_map
                .iter()
                .find_map(|(k, v)| (k.as_str() == Some("pass")).then_some(v))
                .and_then(Yaml::as_str)
                .map(ToString::to_string),
        };

        let severity = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("severity")).then_some(v))
            .map(|value| parse_severity(value, RuleSeverity::Warning))
            .unwrap_or(RuleSeverity::Warning);

        Some(CheckRule {
            id,
            target,
            when,
            expect,
            messages,
            severity,
        })
    }

    fn parse_settings_rules(entry_name: &str, field_yaml: &Yaml) -> Option<CrashgenSettingsRules> {
        let Some(map) = field_yaml.as_hash() else {
            if !matches!(field_yaml, Yaml::BadValue) {
                log::debug!(
                    "Crashgen_Registry.{}.settings_rules is malformed (expected mapping): {:?}",
                    entry_name,
                    field_yaml
                );
            }
            return None;
        };

        let preflight = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("preflight")).then_some(v))
            .and_then(Yaml::as_vec)
            .map(|items| items.iter().filter_map(parse_preflight_rule).collect())
            .unwrap_or_default();

        let checks = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("checks")).then_some(v))
            .and_then(Yaml::as_vec)
            .map(|items| items.iter().filter_map(parse_check_rule).collect())
            .unwrap_or_default();

        Some(CrashgenSettingsRules {
            version: 1,
            preflight,
            checks,
        })
    }

    for (name_yaml, entry_yaml) in registry_node {
        let Some(name) = name_yaml.as_str() else {
            log::debug!(
                "Skipping Crashgen_Registry entry with non-string key: {:?}",
                name_yaml
            );
            continue;
        };

        if entry_yaml.as_hash().is_none() {
            log::debug!(
                "Skipping Crashgen_Registry.{} because entry is malformed (expected mapping): {:?}",
                name,
                entry_yaml
            );
            continue;
        }

        let display_field = &entry_yaml["display_section"];
        let display_section = display_field.as_str().unwrap_or("").to_string();
        if !matches!(display_field, Yaml::BadValue) && display_field.as_str().is_none() {
            log::debug!(
                "Crashgen_Registry.{}.display_section is malformed (expected string), using empty string: {:?}",
                name,
                display_field
            );
        }

        let ignore_keys = parse_string_list_field(name, "ignore_keys", &entry_yaml["ignore_keys"]);
        let checks = parse_string_list_field(name, "checks", &entry_yaml["checks"]);
        let settings_rules_version =
            parse_version_field(name, &entry_yaml["settings_rules_version"]);
        let settings_rules = parse_settings_rules(name, &entry_yaml["settings_rules"]);

        result.insert(
            name.to_string(),
            CrashgenEntryRaw {
                display_section,
                ignore_keys,
                checks,
                settings_rules_version,
                settings_rules,
            },
        );
    }

    result
}

#[cfg(test)]
mod crashgen_registry_tests {
    use super::*;

    fn parse_yaml_document(yaml_content: &str) -> Yaml {
        YamlLoader::load_from_str(yaml_content)
            .unwrap()
            .into_iter()
            .next()
            .unwrap()
    }

    #[test]
    fn test_parse_crashgen_registry_parses_valid_entry() {
        let game_data = parse_yaml_document(
            r#"
Crashgen_Registry:
  crash-og:
    display_section: "[Compatibility]"
    ignore_keys:
      - "Achievements"
      - "MemoryManager"
    checks:
      - "achievements"
      - "memory_management"
"#,
        );

        let registry = parse_crashgen_registry(&game_data);
        let entry = registry.get("crash-og").expect("missing crash-og entry");

        assert_eq!(entry.display_section, "[Compatibility]");
        assert_eq!(
            entry.ignore_keys,
            vec!["Achievements".to_string(), "MemoryManager".to_string()]
        );
        assert_eq!(
            entry.checks,
            vec!["achievements".to_string(), "memory_management".to_string()]
        );
        assert_eq!(entry.settings_rules_version, None);
        assert!(entry.settings_rules.is_none());
    }

    #[test]
    fn test_parse_crashgen_registry_skips_malformed_keys_and_entries() {
        let game_data = parse_yaml_document(
            r#"
Crashgen_Registry:
  valid:
    display_section: "[Valid]"
  123:
    display_section: "[InvalidKey]"
  malformed_entry: "not-a-mapping"
"#,
        );

        let registry = parse_crashgen_registry(&game_data);

        assert_eq!(registry.len(), 1);
        assert!(registry.contains_key("valid"));
        assert!(!registry.contains_key("malformed_entry"));
    }

    #[test]
    fn test_parse_crashgen_registry_non_array_fields_default_to_empty_lists() {
        let game_data = parse_yaml_document(
            r#"
Crashgen_Registry:
  crash-og:
    display_section: "[Compatibility]"
    ignore_keys: "not-an-array"
    checks: 99
"#,
        );

        let registry = parse_crashgen_registry(&game_data);
        let entry = registry.get("crash-og").expect("missing crash-og entry");

        assert!(entry.ignore_keys.is_empty());
        assert!(entry.checks.is_empty());
        assert!(entry.settings_rules.is_none());
    }

    #[test]
    fn test_parse_crashgen_registry_mixed_array_types_keep_only_strings() {
        let game_data = parse_yaml_document(
            r#"
Crashgen_Registry:
  crash-og:
    ignore_keys:
      - "AchievementWarnings"
      - 42
      - true
      - "MemoryManager"
    checks:
      - "achievements"
      - false
      - "memory_management"
"#,
        );

        let registry = parse_crashgen_registry(&game_data);
        let entry = registry.get("crash-og").expect("missing crash-og entry");

        assert_eq!(
            entry.ignore_keys,
            vec![
                "AchievementWarnings".to_string(),
                "MemoryManager".to_string()
            ]
        );
        assert_eq!(
            entry.checks,
            vec!["achievements".to_string(), "memory_management".to_string()]
        );
        assert!(entry.settings_rules.is_none());
    }

    #[test]
    fn test_parse_crashgen_registry_parses_settings_rules() {
        let game_data = parse_yaml_document(
            r#"
Crashgen_Registry:
  crash-og:
    settings_rules_version: 1
    settings_rules:
      preflight:
        - id: addictol_skip
          when:
            plugin_any: ["addictol.dll"]
          action:
            kind: notice_and_skip_remaining
            severity: info
            message: "skip"
      checks:
        - id: achievements
          target:
            section: "Patches"
            key: "Achievements"
            type: "bool"
          when:
            plugin_any: ["achievements.dll"]
          expect:
            equals: false
          messages:
            fail: "bad"
            fix: "fix"
            pass: "ok"
          severity: warning
"#,
        );

        let registry = parse_crashgen_registry(&game_data);
        let entry = registry.get("crash-og").expect("missing crash-og entry");
        assert_eq!(entry.settings_rules_version, Some(1));
        let rules = entry
            .settings_rules
            .as_ref()
            .expect("expected parsed settings rules");
        assert_eq!(rules.preflight.len(), 1);
        assert_eq!(rules.checks.len(), 1);
        assert_eq!(rules.checks[0].target.key, "Achievements");
    }
}

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
///
/// # Version Registry Migration
///
/// VR-specific static metadata fields (`crashgen_name_vr`, `crashgen_latest_vr`,
/// `crashgen_ignore_vr`, `game_version_vr`, `game_root_name_vr`) have been removed.
/// This data is now provided by the Version Registry (`classic-version-registry-core`),
/// which serves as the single source of truth for version-specific metadata.
/// Only runtime path data and shared configuration remain in this struct.
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
    /// Identifier for the crash generation configuration (from Game_Info)
    pub crashgen_name: String,
    /// Latest original generation crash identifier
    pub crashgen_latest_og: String,
    /// Items to be ignored during crash generation (from Game_Info)
    pub crashgen_ignore: Vec<String>,

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

    // Game root names
    /// Main root name for the game (from Game_Info.Main_Root_Name)
    pub game_root_name: String,

    /// Per-crashgen settings registry loaded from `Crashgen_Registry` in the game YAML.
    ///
    /// Maps crashgen names (including `"default"`) to their raw configuration data.
    /// Converted to `CrashgenRegistry` by `build_analysis_config_from_yaml` in
    /// `classic-scanlog-core`.
    pub crashgen_registry: HashMap<String, CrashgenEntryRaw>,
}

impl YamlDataCore {
    /// Get crash generator name.
    ///
    /// Returns the crashgen log name from `Game_Info.CRASHGEN_LogName`.
    /// VR-specific crashgen names are now provided by the Version Registry.
    pub fn get_crashgen_name(&self) -> &str {
        &self.crashgen_name
    }

    /// Get crash generator ignore list.
    ///
    /// Returns the crashgen ignore list from `Game_Info.CRASHGEN_Ignore`.
    /// VR-specific ignore lists are now provided by the Version Registry.
    pub fn get_crashgen_ignore(&self) -> &[String] {
        &self.crashgen_ignore
    }

    /// Get game root name.
    ///
    /// Returns the main root name from `Game_Info.Main_Root_Name`.
    /// VR-specific root names are now provided by the Version Registry.
    pub fn get_game_root_name(&self) -> &str {
        &self.game_root_name
    }

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
        // NOTE: vr_mode parameter is kept in signature for API compatibility
        // but is no longer used. VR-specific metadata is now in the Version Registry.
        let _ = vr_mode;

        // Build the configuration struct.
        // All values come from Game_Info (not GameVR_Info, which has been deprecated).
        // VR-specific static metadata (crashgen names, game root names, version strings)
        // is now provided by the Version Registry.
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

            // Crashgen config (from Game_Info only; VR equivalents now in Version Registry)
            crashgen_name: yaml_ops.get_string_value(game_data, "Game_Info.CRASHGEN_LogName", ""),
            crashgen_ignore: yaml_ops.get_vec_value(game_data, "Game_Info.CRASHGEN_Ignore"),
            game_root_name: yaml_ops.get_string_value(game_data, "Game_Info.Main_Root_Name", ""),

            crashgen_latest_og: yaml_ops.get_string_value(
                game_data,
                "Game_Info.CRASHGEN_LatestVer",
                "",
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

            // Ignore YAML values
            ignore_list: yaml_ops.get_vec_value(ignore_data, &format!("CLASSIC_Ignore_{}", game)),

            // Per-crashgen registry (game YAML)
            crashgen_registry: parse_crashgen_registry(game_data),
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
        // NOTE: vr_mode parameter is kept in signature for API compatibility
        // but is no longer used. VR-specific metadata is now in the Version Registry.
        let _ = vr_mode;

        // Build the configuration struct.
        // All values come from Game_Info (not GameVR_Info, which has been deprecated).
        // VR-specific static metadata (crashgen names, game root names, version strings)
        // is now provided by the Version Registry.
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

            // Crashgen config (from Game_Info only; VR equivalents now in Version Registry)
            crashgen_name: yaml_ops.get_string_value(game_data, "Game_Info.CRASHGEN_LogName", ""),
            crashgen_ignore: yaml_ops.get_vec_value(game_data, "Game_Info.CRASHGEN_Ignore"),
            game_root_name: yaml_ops.get_string_value(game_data, "Game_Info.Main_Root_Name", ""),

            crashgen_latest_og: yaml_ops.get_string_value(
                game_data,
                "Game_Info.CRASHGEN_LatestVer",
                "",
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

            // Ignore YAML values
            ignore_list: yaml_ops.get_vec_value(ignore_data, &format!("CLASSIC_Ignore_{}", game)),

            // Per-crashgen registry (game YAML)
            crashgen_registry: parse_crashgen_registry(game_data),
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
  CRASHGEN_LogName: "crash-og"
  CRASHGEN_Ignore:
    - "OGIgnoreItem1"
    - "OGIgnoreItem2"
  Main_Root_Name: "Fallout4"
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
        assert_eq!(config.classic_game_hints, vec!["Hint 1", "Hint 2"]);
        assert_eq!(config.warn_noplugins, "No plugins found!");
        assert_eq!(config.warn_outdated, "Your version is outdated.");

        // Crashgen/game_root fields (from Game_Info)
        assert_eq!(config.crashgen_name, "crash-og");
        assert_eq!(
            config.crashgen_ignore,
            vec!["OGIgnoreItem1", "OGIgnoreItem2"]
        );
        assert_eq!(config.game_root_name, "Fallout4");
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
            Some(&vec![
                "Stack pattern 1".to_string(),
                "Stack pattern 2".to_string()
            ])
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
    fn test_from_yaml_content_vr_mode_ignored() {
        // vr_mode parameter is ignored; VR metadata is now in Version Registry
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        // Game_Info fields populated
        assert_eq!(config.crashgen_name, "crash-og");
        assert_eq!(
            config.crashgen_ignore,
            vec!["OGIgnoreItem1", "OGIgnoreItem2"]
        );
        assert_eq!(config.game_root_name, "Fallout4");
    }

    #[test]
    fn test_accessor_methods() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        // Accessors return Game_Info values
        assert_eq!(config.get_crashgen_name(), "crash-og");
        assert_eq!(
            config.get_crashgen_ignore(),
            &["OGIgnoreItem1", "OGIgnoreItem2"]
        );
        assert_eq!(config.get_game_root_name(), "Fallout4");
    }

    #[test]
    fn test_vr_mode_parameter_does_not_affect_loading() {
        // Loading with vr_mode=true should produce identical results to vr_mode=false
        let config_og = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            false,
        )
        .unwrap();

        let config_vr = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            true,
        )
        .unwrap();

        assert_eq!(config_og.crashgen_name, config_vr.crashgen_name);
        assert_eq!(config_og.crashgen_ignore, config_vr.crashgen_ignore);
        assert_eq!(config_og.game_root_name, config_vr.game_root_name);
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
    async fn test_load_from_yaml_files_game_info_loading() {
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

        let result =
            YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), false).await;

        assert!(result.is_ok());
        let config = result.unwrap();
        // Game_Info fields should be populated
        assert_eq!(config.crashgen_name, "crash-og");
        assert_eq!(config.game_root_name, "Fallout4");
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
