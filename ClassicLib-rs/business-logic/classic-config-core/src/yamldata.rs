//! Pure Rust YamlData business logic
//!
//! This module provides configuration loading without any PyO3 dependencies.
//! Achieves 15-30x faster configuration loading by:
//! 1. Using yaml-rust2 for parsing (vs ruamel.yaml)
//! 2. Parallel loading of multiple YAML files with Tokio
//! 3. Efficient memory representation

use classic_crashgen_settings_core::{
    CheckRule, ConfigLayout, CrashgenSettingsRules, ExpectedValue, Predicate, PreflightAction,
    PreflightActionKind, PreflightRule, RuleMessages, RuleReportBucket, RuleSeverity, RuleTarget,
    TargetValueType,
};
use classic_settings_core::{SettingsError, merge_yaml_documents, parse_yaml_content};
use classic_version_registry_core::{
    GameVersion as RegistryGameVersion, VersionInfo, get_version_registry,
};
use classic_yaml_core::YamlOperations;
use indexmap::IndexMap;
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use yaml_rust2::Yaml;

/// A single mod-conflict pair from the `Mods_CONF` YAML section.
///
/// Each entry describes two mods whose simultaneous presence causes
/// crashes or other problems. The `mod_a` / `mod_b` identifiers are
/// matched case-insensitively as substrings against plugin file names
/// in crash logs, while `name_a` / `name_b` are the human-readable
/// display names used in reports.
#[derive(Debug, Clone, PartialEq)]
pub struct ModConflictEntry {
    /// Identifier matched against plugin filenames (case-insensitive substring)
    pub mod_a: String,
    /// Identifier matched against plugin filenames (case-insensitive substring)
    pub mod_b: String,
    /// Human-readable display name for mod A
    pub name_a: String,
    /// Human-readable display name for mod B
    pub name_b: String,
    /// Why the conflict matters
    pub description: String,
    /// What the user should do
    pub fix: String,
    /// Optional URL for patch or alternative
    pub link: Option<String>,
}

/// Condition under which a [`CoreModEntry`] should be excluded from processing.
///
/// Currently supports only plugin-presence checks. New variants can be added
/// (e.g., `All`, `Any`, `Not` combinators) without breaking existing YAML.
#[derive(Debug, Clone, PartialEq)]
pub enum CoreModExclude {
    /// Exclude this entry when any of the listed plugins are present.
    PluginAny(Vec<String>),
}

/// A single entry from the `Mods_CORE` YAML section.
///
/// Each entry describes an important / recommended mod that the scanner
/// checks for in the crash log plugin list. The structured format replaces
/// the old flat `"detect_id | Display Name" -> description` mapping and
/// supports declarative GPU affinity and exclusion conditions.
#[derive(Debug, Clone, PartialEq)]
pub struct CoreModEntry {
    /// Substring matched case-insensitively against plugin / XSE module names.
    pub detect: String,
    /// Human-readable display name shown in the report.
    pub name: String,
    /// Recommendation text shown when the mod is missing or installed.
    pub description: String,
    /// GPU vendor this mod is for (`"nvidia"` or `"amd"`).
    /// When set, the runtime uses this for GPU-specific behavior instead of
    /// text-matching inside the description.
    pub gpu: Option<String>,
    /// Warning text shown when this mod is installed but the user does NOT
    /// have the GPU specified by [`gpu`]. Falls back to a generic message
    /// when absent.
    pub gpu_mismatch_warning: Option<String>,
    /// Optional condition that causes this entry to be skipped entirely.
    pub exclude_when: Option<CoreModExclude>,
}

/// A single entry from the `Crashlog_Error_Check` YAML section.
#[derive(Debug, Clone, PartialEq)]
pub struct SuspectErrorRule {
    /// Stable machine-readable identifier for the rule.
    pub id: String,
    /// Human-readable display name shown in reports.
    pub name: String,
    /// Severity used for sorting and report display.
    pub severity: i32,
    /// Main-error substrings that may trigger this rule.
    pub main_error_contains_any: Vec<String>,
}

/// A minimum-occurrence stack-match requirement for a suspect rule.
#[derive(Debug, Clone, PartialEq)]
pub struct SuspectStackCountRule {
    /// Substring that must appear in the call stack.
    pub substring: String,
    /// Minimum number of occurrences required.
    pub count: usize,
}

/// A single entry from the `Crashlog_Stack_Check` YAML section.
#[derive(Debug, Clone, PartialEq)]
pub struct SuspectStackRule {
    /// Stable machine-readable identifier for the rule.
    pub id: String,
    /// Human-readable display name shown in reports.
    pub name: String,
    /// Severity used for sorting and report display.
    pub severity: i32,
    /// Main-error substrings where any match is required before the rule can match.
    pub main_error_required_any: Vec<String>,
    /// Main-error substrings where any match is optional but can trigger the rule.
    pub main_error_optional_any: Vec<String>,
    /// Stack substrings where any match can trigger the rule.
    pub stack_contains_any: Vec<String>,
    /// Stack substrings that suppress the rule when found.
    pub exclude_if_stack_contains_any: Vec<String>,
    /// Stack substrings that must appear at least `count` times.
    pub stack_contains_at_least: Vec<SuspectStackCountRule>,
}

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

        let bucket = action_map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("bucket")).then_some(v))
            .and_then(Yaml::as_str)
            .and_then(RuleReportBucket::parse)
            .unwrap_or_default();

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
                bucket,
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

    fn parse_settings_rules(
        entry_name: &str,
        settings_rules_version: Option<u32>,
        field_yaml: &Yaml,
    ) -> Option<CrashgenSettingsRules> {
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
            version: settings_rules_version.unwrap_or(1),
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
        let settings_rules =
            parse_settings_rules(name, settings_rules_version, &entry_yaml["settings_rules"]);

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

/// Parse the `Mods_CONF` top-level key from a game YAML document.
///
/// Reads a sequence of structured conflict-pair mappings and returns
/// deduplicated `ModConflictEntry` values. Pairs are canonicalized to
/// `(min, max)` order (case-insensitive) so that `(A, B)` and `(B, A)`
/// are treated as the same logical conflict; the second occurrence is
/// skipped with a warning log.
fn parse_mods_conf(game_data: &Yaml) -> Vec<ModConflictEntry> {
    let Some(entries) = game_data["Mods_CONF"].as_vec() else {
        return Vec::new();
    };

    let mut result = Vec::with_capacity(entries.len());
    let mut seen_pairs: HashSet<(String, String)> = HashSet::new();

    for (index, entry_yaml) in entries.iter().enumerate() {
        let Some(map) = entry_yaml.as_hash() else {
            log::debug!(
                "Skipping Mods_CONF[{}]: expected mapping, got {:?}",
                index,
                entry_yaml
            );
            continue;
        };

        let get_str = |key: &str| -> Option<String> {
            map.iter()
                .find_map(|(k, v)| (k.as_str() == Some(key)).then_some(v))
                .and_then(Yaml::as_str)
                .map(|s| s.trim().to_string())
        };

        let (mod_a, mod_b, name_a, name_b, description, fix) = match (
            get_str("mod_a"),
            get_str("mod_b"),
            get_str("name_a"),
            get_str("name_b"),
            get_str("description"),
            get_str("fix"),
        ) {
            (Some(a), Some(b), Some(na), Some(nb), Some(desc), Some(fx)) => {
                (a, b, na, nb, desc, fx)
            }
            _ => {
                log::debug!(
                    "Skipping Mods_CONF[{}]: missing required field(s) (mod_a, mod_b, name_a, name_b, description, fix)",
                    index
                );
                continue;
            }
        };

        let link = get_str("link");

        let canonical = {
            let a_lower = mod_a.to_lowercase();
            let b_lower = mod_b.to_lowercase();
            if a_lower <= b_lower {
                (a_lower, b_lower)
            } else {
                (b_lower, a_lower)
            }
        };

        if !seen_pairs.insert(canonical.clone()) {
            log::warn!(
                "Skipping duplicate Mods_CONF[{}]: pair ({}, {}) already defined",
                index,
                mod_a,
                mod_b
            );
            continue;
        }

        result.push(ModConflictEntry {
            mod_a,
            mod_b,
            name_a,
            name_b,
            description,
            fix,
            link,
        });
    }

    result
}

/// Parse the `Mods_CORE` YAML section into a `Vec<CoreModEntry>`.
///
/// Expects a YAML sequence of mappings, each with `detect`, `name`, and
/// `description` (required), plus optional `gpu` and `exclude_when` fields.
/// Malformed entries are skipped with a debug log.
fn parse_mods_core(game_data: &Yaml) -> Vec<CoreModEntry> {
    let Some(entries) = game_data["Mods_CORE"].as_vec() else {
        return Vec::new();
    };

    let mut result = Vec::with_capacity(entries.len());

    for (index, entry_yaml) in entries.iter().enumerate() {
        let Some(map) = entry_yaml.as_hash() else {
            log::debug!(
                "Skipping Mods_CORE[{}]: expected mapping, got {:?}",
                index,
                entry_yaml
            );
            continue;
        };

        let get_str = |key: &str| -> Option<String> {
            map.iter()
                .find_map(|(k, v)| (k.as_str() == Some(key)).then_some(v))
                .and_then(Yaml::as_str)
                .map(|s| s.trim().to_string())
        };

        let (detect, name, description) = match (
            get_str("detect"),
            get_str("name"),
            get_str("description"),
        ) {
            (Some(d), Some(n), Some(desc)) => (d, n, desc),
            _ => {
                log::debug!(
                    "Skipping Mods_CORE[{}]: missing required field(s) (detect, name, description)",
                    index
                );
                continue;
            }
        };

        let gpu = get_str("gpu");
        let gpu_mismatch_warning = get_str("gpu_mismatch_warning");

        let exclude_when = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("exclude_when")).then_some(v))
            .and_then(|ew| ew.as_hash())
            .and_then(|ew_map| {
                ew_map
                    .iter()
                    .find_map(|(k, v)| (k.as_str() == Some("plugin_any")).then_some(v))
                    .and_then(Yaml::as_vec)
                    .map(|items| {
                        CoreModExclude::PluginAny(
                            items
                                .iter()
                                .filter_map(|item| item.as_str().map(ToString::to_string))
                                .collect(),
                        )
                    })
            });

        result.push(CoreModEntry {
            detect,
            name,
            description,
            gpu,
            gpu_mismatch_warning,
            exclude_when,
        });
    }

    result
}

fn normalize_registry_key(value: &str) -> String {
    value
        .chars()
        .filter(|ch| ch.is_ascii_alphanumeric())
        .map(|ch| ch.to_ascii_lowercase())
        .collect()
}

fn selected_short_name(selected_game_version: &str) -> Option<&'static str> {
    let normalized: String = selected_game_version
        .chars()
        .filter(|ch| ch.is_ascii_alphanumeric())
        .map(|ch| ch.to_ascii_lowercase())
        .collect();
    match normalized.as_str() {
        "original" | "og" => Some("OG"),
        "nextgen" | "ng" => Some("NG"),
        "anniversaryedition" | "anniversary" | "ae" => Some("AE"),
        "vr" => Some("VR"),
        _ => None,
    }
}

fn yaml_map_get<'a>(map: &'a yaml_rust2::yaml::Hash, key: &str) -> Option<&'a Yaml> {
    map.iter()
        .find_map(|(k, v)| (k.as_str() == Some(key)).then_some(v))
}

fn yaml_map_get_trimmed_string(map: &yaml_rust2::yaml::Hash, key: &str) -> Option<String> {
    yaml_map_get(map, key)
        .and_then(Yaml::as_str)
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}

fn yaml_map_get_i32(map: &yaml_rust2::yaml::Hash, key: &str) -> Option<i32> {
    match yaml_map_get(map, key) {
        Some(Yaml::Integer(value)) => i32::try_from(*value).ok(),
        Some(Yaml::String(value)) => value.trim().parse::<i32>().ok(),
        _ => None,
    }
}

fn yaml_map_get_string_vec(map: &yaml_rust2::yaml::Hash, key: &str) -> Vec<String> {
    yaml_map_get(map, key)
        .and_then(Yaml::as_vec)
        .map(|items| {
            items
                .iter()
                .filter_map(Yaml::as_str)
                .map(|value| value.trim().to_string())
                .filter(|value| !value.is_empty())
                .collect()
        })
        .unwrap_or_default()
}

fn parse_suspect_error_rules(game_data: &Yaml) -> Vec<SuspectErrorRule> {
    let Some(entries) = game_data["Crashlog_Error_Check"].as_vec() else {
        return Vec::new();
    };

    let mut result = Vec::with_capacity(entries.len());

    for (index, entry_yaml) in entries.iter().enumerate() {
        let Some(map) = entry_yaml.as_hash() else {
            log::debug!(
                "Skipping Crashlog_Error_Check[{}]: expected mapping, got {:?}",
                index,
                entry_yaml
            );
            continue;
        };

        let (id, name, severity) = match (
            yaml_map_get_trimmed_string(map, "id"),
            yaml_map_get_trimmed_string(map, "name"),
            yaml_map_get_i32(map, "severity"),
        ) {
            (Some(id), Some(name), Some(severity)) => (id, name, severity),
            _ => {
                log::debug!(
                    "Skipping Crashlog_Error_Check[{}]: missing required field(s) (id, name, severity)",
                    index
                );
                continue;
            }
        };

        let main_error_contains_any = yaml_map_get_string_vec(map, "main_error_contains_any");
        if main_error_contains_any.is_empty() {
            log::debug!(
                "Skipping Crashlog_Error_Check[{}]: main_error_contains_any must contain at least one string",
                index
            );
            continue;
        }

        result.push(SuspectErrorRule {
            id,
            name,
            severity,
            main_error_contains_any,
        });
    }

    result
}

fn parse_stack_count_rules(items: &[Yaml]) -> Vec<SuspectStackCountRule> {
    items
        .iter()
        .enumerate()
        .filter_map(|(index, item)| {
            let Some(map) = item.as_hash() else {
                log::debug!(
                    "Skipping stack_contains_at_least[{}]: expected mapping, got {:?}",
                    index,
                    item
                );
                return None;
            };

            let substring = yaml_map_get_trimmed_string(map, "substring")?;
            let count = match yaml_map_get(map, "count") {
                Some(Yaml::Integer(value)) if *value > 0 => usize::try_from(*value).ok()?,
                Some(Yaml::String(value)) => value
                    .trim()
                    .parse::<usize>()
                    .ok()
                    .filter(|value| *value > 0)?,
                _ => return None,
            };

            Some(SuspectStackCountRule { substring, count })
        })
        .collect()
}

fn parse_suspect_stack_rules(game_data: &Yaml) -> Vec<SuspectStackRule> {
    let Some(entries) = game_data["Crashlog_Stack_Check"].as_vec() else {
        return Vec::new();
    };

    let mut result = Vec::with_capacity(entries.len());

    for (index, entry_yaml) in entries.iter().enumerate() {
        let Some(map) = entry_yaml.as_hash() else {
            log::debug!(
                "Skipping Crashlog_Stack_Check[{}]: expected mapping, got {:?}",
                index,
                entry_yaml
            );
            continue;
        };

        let (id, name, severity) = match (
            yaml_map_get_trimmed_string(map, "id"),
            yaml_map_get_trimmed_string(map, "name"),
            yaml_map_get_i32(map, "severity"),
        ) {
            (Some(id), Some(name), Some(severity)) => (id, name, severity),
            _ => {
                log::debug!(
                    "Skipping Crashlog_Stack_Check[{}]: missing required field(s) (id, name, severity)",
                    index
                );
                continue;
            }
        };

        let main_error_required_any = yaml_map_get_string_vec(map, "main_error_required_any");
        let main_error_optional_any = yaml_map_get_string_vec(map, "main_error_optional_any");
        let stack_contains_any = yaml_map_get_string_vec(map, "stack_contains_any");
        let exclude_if_stack_contains_any =
            yaml_map_get_string_vec(map, "exclude_if_stack_contains_any");
        let stack_contains_at_least = yaml_map_get(map, "stack_contains_at_least")
            .and_then(Yaml::as_vec)
            .map(|items| parse_stack_count_rules(items))
            .unwrap_or_default();

        result.push(SuspectStackRule {
            id,
            name,
            severity,
            main_error_required_any,
            main_error_optional_any,
            stack_contains_any,
            exclude_if_stack_contains_any,
            stack_contains_at_least,
        });
    }

    result
}

fn main_root_matches_registry_info(main_root_name: &str, info: &VersionInfo) -> bool {
    let normalized_root = normalize_registry_key(main_root_name);
    !normalized_root.is_empty()
        && (normalize_registry_key(&info.game) == normalized_root
            || normalize_registry_key(&info.docs_name) == normalized_root)
}

/// Resolve registry-backed static metadata for a Main_Root_Name / mode pair.
///
/// This prefers explicit defaults from `unknown_version_handling.defaults` and
/// falls back to the highest-priority registry entry that matches `Main_Root_Name`.
pub fn resolve_registry_version_info(
    main_root_name: &str,
    selected_game_version: &str,
) -> Option<VersionInfo> {
    if main_root_name.trim().is_empty() {
        return None;
    }

    let registry = get_version_registry();
    let selected_short_name = selected_short_name(selected_game_version);
    let selected_version_is_vr = selected_short_name.is_some_and(|short_name| short_name == "VR");

    // Explicit non-VR mode selection should prefer matching short_name first.
    if let Some(short_name) = selected_short_name
        && short_name != "VR"
        && let Some(info) = registry.get_all().into_iter().find(|info| {
            !info.is_vr
                && info.short_name.eq_ignore_ascii_case(short_name)
                && main_root_matches_registry_info(main_root_name, info)
        })
    {
        return Some((*info).clone());
    }

    // Prefer explicit defaults from registry config (accepting both compact and spaced names).
    let mut default_keys = Vec::new();
    let compact_name: String = main_root_name
        .chars()
        .filter(|ch| !ch.is_whitespace())
        .collect();
    for key_base in [main_root_name.trim(), compact_name.as_str()] {
        if key_base.is_empty() {
            continue;
        }
        default_keys.push(key_base.to_string());
    }

    for key in &default_keys {
        if let Some(default_id) = registry.unknown_version_handling().get_default(key)
            && let Some(info) = registry.get_by_id(default_id)
            && info.is_vr == selected_version_is_vr
            && main_root_matches_registry_info(main_root_name, info)
        {
            return Some(info.clone());
        }
    }

    // Fallback: highest-priority registry entry that matches this root name/mode.
    registry
        .get_all()
        .into_iter()
        .find(|info| {
            info.is_vr == selected_version_is_vr
                && main_root_matches_registry_info(main_root_name, info)
        })
        .map(|info| (*info).clone())
}

/// Format registry `GameVersion` using legacy 3-part style when build is 0.
pub fn format_registry_game_version(version: &RegistryGameVersion) -> String {
    if version.build == 0 {
        format!("{}.{}.{}", version.major, version.minor, version.patch)
    } else {
        version.to_string()
    }
}

fn get_crashgen_registry_entry<'a>(
    crashgen_registry: &'a HashMap<String, CrashgenEntryRaw>,
    entry_name: &str,
) -> Option<&'a CrashgenEntryRaw> {
    crashgen_registry.get(entry_name).or_else(|| {
        crashgen_registry
            .iter()
            .find(|(name, _)| name.eq_ignore_ascii_case(entry_name))
            .map(|(_, entry)| entry)
    })
}

fn resolve_crashgen_ignore_fallback(
    crashgen_registry: &HashMap<String, CrashgenEntryRaw>,
    selected_crashgen: &str,
) -> Option<Vec<String>> {
    get_crashgen_registry_entry(crashgen_registry, selected_crashgen)
        .or_else(|| get_crashgen_registry_entry(crashgen_registry, "default"))
        .map(|entry| entry.ignore_keys.clone())
}

fn map_settings_error(
    parse_context: &str,
    empty_context: &str,
    error: SettingsError,
) -> ConfigError {
    match error {
        SettingsError::IoError { path, source } => ConfigError::IOError {
            context: format!("Failed to read {}", path.display()),
            source,
        },
        SettingsError::YamlParseError { message, .. } => ConfigError::ParseError {
            context: parse_context.to_string(),
            message,
        },
        SettingsError::InvalidYamlStructure {
            source,
            index,
            found,
        } => ConfigError::ParseError {
            context: parse_context.to_string(),
            message: format!(
                "Invalid YAML structure in {}: document {} must be a mapping, found {}",
                source, index, found
            ),
        },
        SettingsError::EmptyDocument { .. } => {
            ConfigError::EmptyDocument(empty_context.to_string())
        }
        SettingsError::TaskJoinError { path, source } => ConfigError::ParseError {
            context: parse_context.to_string(),
            message: format!(
                "Task join error while loading {}: {}",
                path.display(),
                source
            ),
        },
        SettingsError::KeyNotFound(key) => ConfigError::ParseError {
            context: parse_context.to_string(),
            message: format!("Cache key not found: {}", key),
        },
    }
}

fn parse_and_merge_yaml_content(
    source_label: &str,
    empty_label: &str,
    content: &str,
) -> Result<Yaml, ConfigError> {
    let docs = parse_yaml_content(source_label, content).map_err(|error| {
        map_settings_error(
            &format!("Failed to parse {source_label}"),
            empty_label,
            error,
        )
    })?;

    merge_yaml_documents(source_label, &docs).map_err(|error| {
        map_settings_error(
            &format!("Failed to parse {source_label}"),
            empty_label,
            error,
        )
    })
}

#[cfg(test)]
mod crashgen_registry_tests {
    use super::*;

    fn parse_yaml_document(yaml_content: &str) -> Yaml {
        let docs = parse_yaml_content("memory://crashgen_registry", yaml_content).unwrap();
        merge_yaml_documents("memory://crashgen_registry", &docs).unwrap()
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
    settings_rules_version: 2
    settings_rules:
      preflight:
        - id: addictol_skip
          when:
            plugin_any: ["addictol.dll"]
          action:
            kind: notice_and_skip_remaining
            bucket: error_information
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
        assert_eq!(entry.settings_rules_version, Some(2));
        let rules = entry
            .settings_rules
            .as_ref()
            .expect("expected parsed settings rules");
        assert_eq!(rules.version, 2);
        assert_eq!(rules.preflight.len(), 1);
        assert_eq!(rules.checks.len(), 1);
        assert_eq!(
            rules.preflight[0].action.bucket,
            RuleReportBucket::ErrorInformation
        );
        assert_eq!(rules.checks[0].target.key, "Achievements");
    }

    #[test]
    fn test_parse_crashgen_registry_settings_rules_default_version_when_missing() {
        let game_data = parse_yaml_document(
            r#"
Crashgen_Registry:
  crash-og:
    settings_rules:
      preflight:
        - id: addictol_skip
          when:
            plugin_any: ["addictol.dll"]
          action:
            kind: notice_and_skip_remaining
            severity: info
            message: "skip"
"#,
        );

        let registry = parse_crashgen_registry(&game_data);
        let entry = registry.get("crash-og").expect("missing crash-og entry");
        assert_eq!(entry.settings_rules_version, None);
        let rules = entry
            .settings_rules
            .as_ref()
            .expect("expected parsed settings rules");
        assert_eq!(rules.version, 1);
        assert_eq!(rules.preflight.len(), 1);
        assert_eq!(rules.preflight[0].action.bucket, RuleReportBucket::Settings);
        assert!(rules.checks.is_empty());
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
/// * `suspect_error_rules` - Structured main-error suspect rules.
/// * `suspect_stack_rules` - Structured stack suspect rules.
///
/// * `game_mods_conf` - A `Vec<ModConflictEntry>` holding deduplicated mod conflict pairs from `Mods_CONF`.
/// * `game_mods_core` - A `Vec<CoreModEntry>` of structured core/important mod entries from `Mods_CORE`.
/// * `game_mods_freq` - An `IndexMap<String, String>` containing frequently used game mod entries.
/// * `game_mods_solu` - An `IndexMap<String, String>` representing solution-related game mod configurations.
///
/// * `autoscan_text` - A `String` defining the text used in the "autoscan" UI component.
///
/// * `game_version` - A `String` holding the current game version.
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
    /// Identifier for the crash generation configuration.
    ///
    /// Loaded from `Game_Info.CRASHGEN_LogName` when present, otherwise
    /// backfilled from Version Registry metadata using `Game_Info.Main_Root_Name`.
    pub crashgen_name: String,
    /// Latest original generation crash identifier
    pub crashgen_latest_og: String,
    /// Items to be ignored during crash generation.
    ///
    /// Loaded from `Game_Info.CRASHGEN_Ignore` when present. If missing, this
    /// falls back to `Crashgen_Registry.<selected|default>.ignore_keys`.
    pub crashgen_ignore: Vec<String>,

    // Warnings
    /// Warning message for cases where no plugins are active or available
    pub warn_noplugins: String,
    /// Warning message indicating the game version or configuration is outdated
    pub warn_outdated: String,

    // XSE configuration
    /// Acronym for the XSE (XML Scripting Engine) configuration setting.
    ///
    /// Loaded from `Game_Info.XSE_Acronym` or backfilled from Version Registry metadata.
    pub xse_acronym: String,

    // Ignore lists
    /// Plugins to be ignored in the current game configuration
    pub game_ignore_plugins: Vec<String>,
    /// Records to be ignored
    pub game_ignore_records: Vec<String>,
    /// Entries to be collectively ignored
    pub ignore_list: Vec<String>,

    // Suspect patterns
    /// Structured suspect rules for main-error matching.
    pub suspect_error_rules: Vec<SuspectErrorRule>,
    /// Structured suspect rules for stack and main-error matching.
    pub suspect_stack_rules: Vec<SuspectStackRule>,

    // Mod databases (IndexMap preserves YAML key order for Python parity)
    /// Mod conflict pairs parsed from `Mods_CONF` (deduplicated at load time)
    pub game_mods_conf: Vec<ModConflictEntry>,
    /// Core / important mod entries parsed from `Mods_CORE` (structured sequence)
    pub game_mods_core: Vec<CoreModEntry>,
    /// Frequently used game mod entries
    pub game_mods_freq: IndexMap<String, String>,
    /// Solution-related game mod configurations
    pub game_mods_solu: IndexMap<String, String>,

    // UI configuration
    /// Text used in the autoscan UI component
    pub autoscan_text: String,

    // Game versions (stored as strings)
    /// Current game version.
    ///
    /// Loaded from `Game_Info.GameVersion` or backfilled from Version Registry metadata.
    pub game_version: String,

    // Game root names
    /// Main root name for the game (from `Game_Info.Main_Root_Name`)
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
    /// Returns the crashgen log name from YAML, with Version Registry fallback.
    pub fn get_crashgen_name(&self) -> &str {
        &self.crashgen_name
    }

    /// Get crash generator ignore list.
    ///
    /// Returns the crashgen ignore list from YAML or `Crashgen_Registry` fallback.
    pub fn get_crashgen_ignore(&self) -> &[String] {
        &self.crashgen_ignore
    }

    /// Get game root name.
    ///
    /// Returns the main root name from `Game_Info.Main_Root_Name`.
    pub fn get_game_root_name(&self) -> &str {
        &self.game_root_name
    }

    fn build_from_yaml_documents(
        main_data: &Yaml,
        game_data: &Yaml,
        ignore_data: &Yaml,
        game: &str,
        selected_game_version: &str,
    ) -> Self {
        let yaml_ops = YamlOperations::new();

        let crashgen_ignore_is_configured = yaml_ops
            .get_setting(game_data, "Game_Info.CRASHGEN_Ignore")
            .is_some();

        let mut data = Self {
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
                &format!("CLASSIC_Interface.autoscan_text_{game}"),
                "",
            ),

            // Game YAML values
            classic_game_hints: yaml_ops.get_vec_value(game_data, "Game_Hints"),

            // Crashgen config (from Game_Info first; registry fallback is applied after extraction)
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
            suspect_error_rules: parse_suspect_error_rules(game_data),
            suspect_stack_rules: parse_suspect_stack_rules(game_data),
            game_mods_conf: parse_mods_conf(game_data),
            game_mods_core: parse_mods_core(game_data),
            game_mods_freq: yaml_ops.get_indexmap_value(game_data, "Mods_FREQ"),
            game_mods_solu: yaml_ops.get_indexmap_value(game_data, "Mods_SOLU"),
            game_version: yaml_ops.get_string_value(game_data, "Game_Info.GameVersion", ""),

            // Ignore YAML values
            ignore_list: yaml_ops.get_vec_value(ignore_data, &format!("CLASSIC_Ignore_{game}")),

            // Per-crashgen registry (game YAML)
            crashgen_registry: parse_crashgen_registry(game_data),
        };

        data.apply_metadata_fallbacks(selected_game_version, crashgen_ignore_is_configured);
        data
    }

    fn apply_metadata_fallbacks(
        &mut self,
        selected_game_version: &str,
        crashgen_ignore_is_configured: bool,
    ) {
        if !self.game_root_name.trim().is_empty() {
            let registry_info =
                resolve_registry_version_info(&self.game_root_name, selected_game_version);
            let registry_crashgen = registry_info
                .as_ref()
                .and_then(|info| info.crashgen_versions.first());

            if self.crashgen_name.trim().is_empty()
                && let Some(name) = registry_crashgen
                    .map(|config| config.name.as_str())
                    .filter(|name| !name.is_empty())
            {
                self.crashgen_name = name.to_string();
            }

            if self.crashgen_latest_og.trim().is_empty()
                && let Some(version) = registry_crashgen
                    .map(|config| config.version.as_str())
                    .filter(|version| !version.is_empty())
            {
                self.crashgen_latest_og = version.to_string();
            }

            if self.xse_acronym.trim().is_empty()
                && let Some(acronym) = registry_info
                    .as_ref()
                    .and_then(|info| info.xse.as_ref())
                    .map(|xse| xse.acronym.as_str())
                    .filter(|acronym| !acronym.is_empty())
            {
                self.xse_acronym = acronym.to_string();
            }

            if self.game_version.trim().is_empty()
                && let Some(version) = registry_info
                    .as_ref()
                    .map(|info| format_registry_game_version(&info.version))
            {
                self.game_version = version;
            }
        }

        if !crashgen_ignore_is_configured
            && self.crashgen_ignore.is_empty()
            && let Some(ignore) =
                resolve_crashgen_ignore_fallback(&self.crashgen_registry, &self.crashgen_name)
        {
            self.crashgen_ignore = ignore;
        }
    }

    /// Load all configuration from YAML files in parallel (pure Rust)
    ///
    /// # Arguments
    /// * `yaml_dirs` - Vector of directories containing YAML files (main, game, ignore)
    /// * `game` - Game identifier (e.g., "Fallout4", "Skyrim")
    /// * `selected_game_version` - Selected game version mode
    ///   ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", "VR")
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
        selected_game_version: String,
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

        let main_data = parse_and_merge_yaml_content("main YAML", "Main YAML", &main_content)?;
        let game_data = parse_and_merge_yaml_content("game YAML", "Game YAML", &game_content)?;
        let ignore_data =
            parse_and_merge_yaml_content("ignore YAML", "Ignore YAML", &ignore_content)?;

        Ok(Self::build_from_yaml_documents(
            &main_data,
            &game_data,
            &ignore_data,
            &game,
            &selected_game_version,
        ))
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
    /// * `selected_game_version` - Selected game version mode
    ///   ("auto", "Original", "NextGen", "AnniversaryEdition"/"AE", "VR")
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
    ///     "auto".to_string(),
    /// ).unwrap();
    /// ```
    pub fn from_yaml_content(
        main_content: &str,
        game_content: &str,
        ignore_content: &str,
        game: String,
        selected_game_version: String,
    ) -> Result<Self, ConfigError> {
        let main_data = parse_and_merge_yaml_content("main YAML", "Main YAML", main_content)?;
        let game_data = parse_and_merge_yaml_content("game YAML", "Game YAML", game_content)?;
        let ignore_data =
            parse_and_merge_yaml_content("ignore YAML", "Ignore YAML", ignore_content)?;

        Ok(Self::build_from_yaml_documents(
            &main_data,
            &game_data,
            &ignore_data,
            &game,
            &selected_game_version,
        ))
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
    #[error("{context}: {message}")]
    ParseError {
        /// Contextual information about which file failed to parse
        context: String,
        /// The underlying parse or merge failure message
        message: String,
    },

    /// YAML document is empty (no content to parse)
    #[error("Empty YAML document: {0}")]
    EmptyDocument(String),
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
  - id: error_pattern_1
    name: Error Pattern 1
    severity: 4
    main_error_contains_any:
      - "Error description 1"
  - id: error_pattern_2
    name: Error Pattern 2
    severity: 2
    main_error_contains_any:
      - "Error description 2"
Crashlog_Stack_Check:
  - id: stack_pattern_1
    name: Stack Pattern 1
    severity: 3
    main_error_required_any:
      - "Main error required"
    main_error_optional_any:
      - "Main error optional"
    stack_contains_any:
      - "Stack pattern 1"
      - "Stack pattern 2"
    exclude_if_stack_contains_any:
      - "Excluded pattern"
    stack_contains_at_least:
      - substring: "Repeated pattern"
        count: 2
Mods_CONF:
  - mod_a: modA
    mod_b: modB
    name_a: Mod A
    name_b: Mod B
    description: "Config for ModA"
    fix: "Remove one."
Mods_CORE:
  - detect: ModB
    name: Core Mod B
    description: "Core mod B"
  - detect: GpuMod.dll
    name: GPU Mod
    description: "GPU-specific mod"
    gpu: nvidia
  - detect: ExcludedMod.esp
    name: Excluded Mod
    description: "Excluded mod"
    exclude_when:
      plugin_any: [SomeWorldspace.esm]
Mods_FREQ:
  FreqMod: "Frequently used mod"
Mods_SOLU:
  SoluMod: "Solution mod"
"#
    }

    /// Production-shaped Fallout 4 YAML where Game_Info only has Main_Root_Name.
    fn minimal_game_yaml_main_root_only() -> &'static str {
        r#"
Game_Info:
  Main_Root_Name: "Fallout 4"
Crashgen_Registry:
  "Buffout 4":
    ignore_keys:
      - "BuffoutSpecificIgnore"
    checks: []
  default:
    ignore_keys:
      - "DefaultIgnore"
    checks: []
"#
    }

    /// Production-shaped Fallout 4 YAML where Game_Info has compact Main_Root_Name.
    fn minimal_game_yaml_main_root_only_compact() -> &'static str {
        r#"
Game_Info:
  Main_Root_Name: "Fallout4"
Crashgen_Registry:
  "Buffout 4":
    ignore_keys:
      - "BuffoutSpecificIgnore"
    checks: []
  default:
    ignore_keys:
      - "DefaultIgnore"
    checks: []
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
            "auto".to_string(),
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
            "auto".to_string(),
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
            "auto".to_string(),
        )
        .unwrap();

        // Game YAML values
        assert_eq!(config.xse_acronym, "F4SE");
        assert_eq!(config.game_version, "1.10.163");
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
            "auto".to_string(),
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
            "auto".to_string(),
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
            "auto".to_string(),
        )
        .unwrap();

        assert_eq!(config.suspect_error_rules.len(), 2);
        assert_eq!(config.suspect_error_rules[0].id, "error_pattern_1");
        assert_eq!(config.suspect_error_rules[0].name, "Error Pattern 1");
        assert_eq!(config.suspect_error_rules[0].severity, 4);
        assert_eq!(
            config.suspect_error_rules[0].main_error_contains_any,
            vec!["Error description 1".to_string()]
        );

        assert_eq!(config.suspect_stack_rules.len(), 1);
        assert_eq!(config.suspect_stack_rules[0].id, "stack_pattern_1");
        assert_eq!(config.suspect_stack_rules[0].name, "Stack Pattern 1");
        assert_eq!(config.suspect_stack_rules[0].severity, 3);
        assert_eq!(
            config.suspect_stack_rules[0].main_error_required_any,
            vec!["Main error required".to_string()]
        );
        assert_eq!(
            config.suspect_stack_rules[0].main_error_optional_any,
            vec!["Main error optional".to_string()]
        );
        assert_eq!(
            config.suspect_stack_rules[0].stack_contains_any,
            vec!["Stack pattern 1".to_string(), "Stack pattern 2".to_string()]
        );
        assert_eq!(
            config.suspect_stack_rules[0].exclude_if_stack_contains_any,
            vec!["Excluded pattern".to_string()]
        );
        assert_eq!(
            config.suspect_stack_rules[0].stack_contains_at_least.len(),
            1
        );
        assert_eq!(
            config.suspect_stack_rules[0].stack_contains_at_least[0].substring,
            "Repeated pattern"
        );
        assert_eq!(
            config.suspect_stack_rules[0].stack_contains_at_least[0].count,
            2
        );
    }

    #[test]
    fn test_from_yaml_content_skips_zero_string_stack_count_rules() {
        let game_yaml = minimal_game_yaml().replacen("count: 2", "count: \"0\"", 1);

        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            &game_yaml,
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .unwrap();

        assert!(
            config.suspect_stack_rules[0]
                .stack_contains_at_least
                .is_empty()
        );
    }

    #[test]
    fn test_from_yaml_content_extracts_mod_databases() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .unwrap();

        assert_eq!(config.game_mods_conf.len(), 1);
        assert_eq!(config.game_mods_conf[0].mod_a, "modA");
        assert_eq!(config.game_mods_conf[0].description, "Config for ModA");

        assert_eq!(config.game_mods_core.len(), 3);
        assert_eq!(config.game_mods_core[0].detect, "ModB");
        assert_eq!(config.game_mods_core[0].name, "Core Mod B");
        assert_eq!(config.game_mods_core[0].description, "Core mod B");
        assert_eq!(config.game_mods_core[0].gpu, None);
        assert_eq!(config.game_mods_core[0].exclude_when, None);

        assert_eq!(config.game_mods_core[1].detect, "GpuMod.dll");
        assert_eq!(config.game_mods_core[1].gpu, Some("nvidia".to_string()));

        assert_eq!(config.game_mods_core[2].detect, "ExcludedMod.esp");
        assert_eq!(
            config.game_mods_core[2].exclude_when,
            Some(CoreModExclude::PluginAny(vec![
                "SomeWorldspace.esm".to_string()
            ]))
        );
        assert_eq!(
            config.game_mods_freq.get("FreqMod"),
            Some(&"Frequently used mod".to_string())
        );
        assert_eq!(
            config.game_mods_solu.get("SoluMod"),
            Some(&"Solution mod".to_string())
        );
    }

    #[test]
    fn test_from_yaml_content_auto_game_version_uses_game_info_values() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
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
            "auto".to_string(),
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
    fn test_selected_game_version_parameter_does_not_affect_explicit_game_info_values() {
        // This fixture explicitly defines Game_Info values, so mode selection
        // should not change extracted crashgen metadata.
        let config_og = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .unwrap();

        let config_vr = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "VR".to_string(),
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
            "auto".to_string(),
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
            "auto".to_string(),
        )
        .unwrap();

        let skyrim_config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml(),
            minimal_ignore_yaml(),
            "Skyrim".to_string(),
            "auto".to_string(),
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
            "auto".to_string(),
        );

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::ParseError { .. }));
        match err {
            ConfigError::ParseError { context, .. } => {
                assert!(context.to_lowercase().contains("main yaml"));
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
            "auto".to_string(),
        );

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::ParseError { .. }));
        match err {
            ConfigError::ParseError { context, .. } => {
                assert!(context.to_lowercase().contains("game yaml"));
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
            "auto".to_string(),
        );

        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, ConfigError::ParseError { .. }));
        match err {
            ConfigError::ParseError { context, .. } => {
                assert!(context.to_lowercase().contains("ignore yaml"));
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
            "auto".to_string(),
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
            "auto".to_string(),
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
            "auto".to_string(),
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
            "auto".to_string(),
        );

        assert!(result.is_ok());
        let config = result.unwrap();
        // Missing values should be empty strings/vecs
        assert_eq!(config.classic_version, "");
        assert!(config.classic_records_list.is_empty());
        assert!(config.ignore_list.is_empty());
    }

    #[test]
    fn test_from_yaml_content_falls_back_to_registry_metadata_when_game_info_is_minimal() {
        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml_main_root_only(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .unwrap();

        // Main root name is still sourced from YAML.
        assert_eq!(config.game_root_name, "Fallout 4");

        // These fields should be backfilled from version registry metadata.
        assert!(!config.crashgen_name.is_empty());
        assert!(!config.crashgen_latest_og.is_empty());
        assert!(!config.xse_acronym.is_empty());
        assert!(!config.game_version.is_empty());

        // Legacy ignore fallback comes from Crashgen_Registry when Game_Info.CRASHGEN_Ignore is absent.
        assert_eq!(config.crashgen_ignore, vec!["BuffoutSpecificIgnore"]);
    }

    #[test]
    fn test_from_yaml_content_registry_fallback_matches_for_spaced_and_compact_main_root_names() {
        let spaced_config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml_main_root_only(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .unwrap();
        let compact_config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml_main_root_only_compact(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .unwrap();

        assert_eq!(spaced_config.crashgen_name, compact_config.crashgen_name);
        assert_eq!(
            spaced_config.crashgen_latest_og,
            compact_config.crashgen_latest_og
        );
        assert_eq!(spaced_config.xse_acronym, compact_config.xse_acronym);
        assert_eq!(spaced_config.game_version, compact_config.game_version);
        assert_eq!(
            spaced_config.crashgen_ignore,
            compact_config.crashgen_ignore
        );
    }

    #[test]
    fn test_from_yaml_content_registry_selected_mode_resolves_expected_versions() {
        let original = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml_main_root_only(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "Original".to_string(),
        )
        .unwrap();
        let next_gen = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml_main_root_only(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "NextGen".to_string(),
        )
        .unwrap();
        let anniversary = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml_main_root_only(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "AnniversaryEdition".to_string(),
        )
        .unwrap();
        let anniversary_alias = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml_main_root_only(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "AE".to_string(),
        )
        .unwrap();
        let vr = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            minimal_game_yaml_main_root_only(),
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "VR".to_string(),
        )
        .unwrap();

        assert_eq!(original.game_version, "1.10.163");
        assert_eq!(next_gen.game_version, "1.10.984");
        assert_eq!(anniversary.game_version, "1.11.191");
        assert_eq!(anniversary_alias.game_version, anniversary.game_version);
        assert_eq!(vr.game_version, "1.2.72");
    }

    #[test]
    fn test_from_yaml_content_respects_explicit_empty_crashgen_ignore() {
        let game_yaml = r#"
Game_Info:
  Main_Root_Name: "Fallout 4"
  CRASHGEN_LogName: "Buffout 4"
  CRASHGEN_Ignore: []
Crashgen_Registry:
  "Buffout 4":
    ignore_keys:
      - "BuffoutSpecificIgnore"
    checks: []
  default:
    ignore_keys:
      - "DefaultIgnore"
    checks: []
"#;

        let config = YamlDataCore::from_yaml_content(
            minimal_main_yaml(),
            game_yaml,
            minimal_ignore_yaml(),
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .unwrap();

        assert!(
            config.crashgen_ignore.is_empty(),
            "explicit empty CRASHGEN_Ignore must not be replaced by registry fallback"
        );
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

        let result = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await;

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

        let result = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await;

        assert!(result.is_ok(), "Load failed: {:?}", result.err());
        let config = result.unwrap();
        assert_eq!(config.classic_version, "7.31.0");
    }

    #[tokio::test]
    async fn test_load_from_yaml_files_invalid_dir_count() {
        // Provide only 1 directory (invalid)
        let yaml_dirs = vec![PathBuf::from("/some/path")];

        let result = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await;

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

        let result = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await;

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

        let result = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await;

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

        let result = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await;

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

        let result = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await;

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

        let result = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "TestGame".to_string(),
            "auto".to_string(),
        )
        .await;

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

        let result = YamlDataCore::load_from_yaml_files(
            yaml_dirs,
            "Fallout4".to_string(),
            "auto".to_string(),
        )
        .await;

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
            "auto".to_string(),
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
            "auto".to_string(),
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
    fn test_config_error_parse_error_display() {
        let err = ConfigError::ParseError {
            context: "Failed to parse game YAML".to_string(),
            message: "document 1 must be a mapping".to_string(),
        };
        let display = format!("{}", err);
        assert!(display.contains("Failed to parse game YAML"));
        assert!(display.contains("document 1 must be a mapping"));
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
