//! Pure Rust YamlData business logic
//!
//! This module provides configuration loading without any PyO3 dependencies.
//! Achieves 15-30x faster configuration loading by:
//! 1. Using yaml-rust2 for parsing (vs ruamel.yaml)
//! 2. Parallel loading of multiple YAML files with Tokio
//! 3. Efficient memory representation

use crate::CrashgenSettingsRules;
use crate::crashgen_registry_yaml::parse_crashgen_registry;
use classic_settings_core::YamlOperations;
use classic_settings_core::{SettingsError, merge_yaml_documents, parse_yaml_content};
use classic_version_registry_core::{
    GameVersion as RegistryGameVersion, VersionInfo, get_version_registry,
};
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

/// Grouped match criteria for a structured mod entry.
#[derive(Debug, Clone, PartialEq)]
pub enum ModSolutionCriteria {
    /// Match when any listed substring appears in installed plugin filenames.
    Any(Vec<String>),
    /// Match only when all listed substrings appear in installed plugin filenames.
    All(Vec<String>),
}

impl ModSolutionCriteria {
    /// Return the active criterion values.
    pub fn values(&self) -> &[String] {
        match self {
            Self::Any(values) | Self::All(values) => values,
        }
    }
}

/// A structured entry from a structured mod YAML section.
#[derive(Debug, Clone, PartialEq)]
pub struct ModSolutionEntry {
    /// Stable machine-readable identifier for the entry.
    pub id: String,
    /// Grouped match criteria used to detect this solution entry.
    pub criteria: ModSolutionCriteria,
    /// Optional plugin substrings that suppress the match when present.
    pub exceptions: Vec<String>,
    /// Human-readable display name shown in the report.
    pub name: String,
    /// Report body shown when the entry is detected.
    pub description: String,
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

fn parse_structured_section_entries<'a>(
    game_data: &'a Yaml,
    section_name: &'static str,
) -> Result<Option<&'a [Yaml]>, ConfigError> {
    let section = &game_data[section_name];
    match section {
        Yaml::BadValue | Yaml::Null => Ok(None),
        Yaml::Array(entries) => Ok(Some(entries.as_slice())),
        Yaml::Hash(_) => Err(ConfigError::ParseError {
            context: "Failed to parse game YAML".to_string(),
            message: format!(
                "{section_name} uses retired legacy map format; expected a YAML sequence of structured entries"
            ),
        }),
        other => Err(ConfigError::ParseError {
            context: "Failed to parse game YAML".to_string(),
            message: format!(
                "{section_name} must be a YAML sequence of structured entries, found {}",
                yaml_node_kind(other)
            ),
        }),
    }
}

fn parse_mod_check_entries(
    game_data: &Yaml,
    section_name: &'static str,
) -> Result<Vec<ModSolutionEntry>, ConfigError> {
    let Some(entries) = parse_structured_section_entries(game_data, section_name)? else {
        return Ok(Vec::new());
    };

    let mut result = Vec::with_capacity(entries.len());

    for (index, entry_yaml) in entries.iter().enumerate() {
        let Some(map) = entry_yaml.as_hash() else {
            log::debug!(
                "Skipping {}[{}]: expected mapping, got {:?}",
                section_name,
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

        let get_string_list = |yaml: &Yaml| -> Vec<String> {
            yaml.as_vec()
                .map(|items| {
                    items
                        .iter()
                        .filter_map(|item| item.as_str().map(|s| s.trim().to_string()))
                        .filter(|item| !item.is_empty())
                        .collect()
                })
                .unwrap_or_default()
        };

        let (id, name, description) = match (get_str("id"), get_str("name"), get_str("description"))
        {
            (Some(id), Some(name), Some(description)) => (id, name, description),
            _ => {
                log::debug!(
                    "Skipping {}[{}]: missing required field(s) (id, name, description)",
                    section_name,
                    index
                );
                continue;
            }
        };

        let criteria = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("criteria")).then_some(v))
            .and_then(Yaml::as_hash)
            .and_then(|criteria_map| {
                let any = criteria_map
                    .iter()
                    .find_map(|(k, v)| (k.as_str() == Some("any")).then_some(v))
                    .map(get_string_list)
                    .filter(|values| !values.is_empty());
                let all = criteria_map
                    .iter()
                    .find_map(|(k, v)| (k.as_str() == Some("all")).then_some(v))
                    .map(get_string_list)
                    .filter(|values| !values.is_empty());

                match (any, all) {
                    (Some(values), None) => Some(ModSolutionCriteria::Any(values)),
                    (None, Some(values)) => Some(ModSolutionCriteria::All(values)),
                    _ => None,
                }
            });

        let Some(criteria) = criteria else {
            log::debug!(
                "Skipping {}[{}]: criteria must define exactly one non-empty group (`any` or `all`)",
                section_name,
                index
            );
            continue;
        };

        let exceptions = map
            .iter()
            .find_map(|(k, v)| (k.as_str() == Some("exceptions")).then_some(v))
            .map(get_string_list)
            .unwrap_or_default();

        result.push(ModSolutionEntry {
            id,
            criteria,
            exceptions,
            name,
            description,
        });
    }

    Ok(result)
}

/// Parse the `Mods_FREQ` YAML section into a structured `Vec<ModSolutionEntry>`.
fn parse_mods_freq(game_data: &Yaml) -> Result<Vec<ModSolutionEntry>, ConfigError> {
    parse_mod_check_entries(game_data, "Mods_FREQ")
}

/// Parse the `Mods_SOLU` YAML section into a `Vec<ModSolutionEntry>`.
fn parse_mods_solu(game_data: &Yaml) -> Result<Vec<ModSolutionEntry>, ConfigError> {
    parse_mod_check_entries(game_data, "Mods_SOLU")
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

fn yaml_node_kind(value: &Yaml) -> &'static str {
    match value {
        Yaml::Real(_) => "real",
        Yaml::Integer(_) => "integer",
        Yaml::String(_) => "string",
        Yaml::Boolean(_) => "boolean",
        Yaml::Array(_) => "sequence",
        Yaml::Hash(_) => "mapping",
        Yaml::Alias(_) => "alias",
        Yaml::Null => "null",
        Yaml::BadValue => "missing",
    }
}

fn parse_suspect_rule_entries<'a>(
    game_data: &'a Yaml,
    section_name: &'static str,
) -> Result<Option<&'a [Yaml]>, ConfigError> {
    let section = &game_data[section_name];
    match section {
        Yaml::BadValue | Yaml::Null => Ok(None),
        Yaml::Array(entries) => Ok(Some(entries.as_slice())),
        Yaml::Hash(_) => Err(ConfigError::ParseError {
            context: "Failed to parse game YAML".to_string(),
            message: format!(
                "{section_name} uses retired legacy map format; expected a YAML sequence of rule objects"
            ),
        }),
        other => Err(ConfigError::ParseError {
            context: "Failed to parse game YAML".to_string(),
            message: format!(
                "{section_name} must be a YAML sequence of rule objects, found {}",
                yaml_node_kind(other)
            ),
        }),
    }
}

fn parse_suspect_error_rules(game_data: &Yaml) -> Result<Vec<SuspectErrorRule>, ConfigError> {
    let Some(entries) = parse_suspect_rule_entries(game_data, "Crashlog_Error_Check")? else {
        return Ok(Vec::new());
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

    Ok(result)
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

fn parse_suspect_stack_rules(game_data: &Yaml) -> Result<Vec<SuspectStackRule>, ConfigError> {
    let Some(entries) = parse_suspect_rule_entries(game_data, "Crashlog_Stack_Check")? else {
        return Ok(Vec::new());
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

    Ok(result)
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
/// * `game_mods_freq` - A `Vec<ModSolutionEntry>` of structured frequent-crash mod entries.
/// * `game_mods_solu` - A `Vec<ModSolutionEntry>` of structured solution-related mod entries.
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

    // Mod databases
    /// Mod conflict pairs parsed from `Mods_CONF` (deduplicated at load time)
    pub game_mods_conf: Vec<ModConflictEntry>,
    /// Core / important mod entries parsed from `Mods_CORE` (structured sequence)
    pub game_mods_core: Vec<CoreModEntry>,
    /// Frequent-crash game mod entries parsed from `Mods_FREQ` (structured sequence)
    pub game_mods_freq: Vec<ModSolutionEntry>,
    /// Solution-related game mod entries parsed from `Mods_SOLU` (structured sequence)
    pub game_mods_solu: Vec<ModSolutionEntry>,

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
    ) -> Result<Self, ConfigError> {
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
            suspect_error_rules: parse_suspect_error_rules(game_data)?,
            suspect_stack_rules: parse_suspect_stack_rules(game_data)?,
            game_mods_conf: parse_mods_conf(game_data),
            game_mods_core: parse_mods_core(game_data),
            game_mods_freq: parse_mods_freq(game_data)?,
            game_mods_solu: parse_mods_solu(game_data)?,
            game_version: yaml_ops.get_string_value(game_data, "Game_Info.GameVersion", ""),

            // Ignore YAML values
            ignore_list: yaml_ops.get_vec_value(ignore_data, &format!("CLASSIC_Ignore_{game}")),

            // Per-crashgen registry (game YAML)
            crashgen_registry: parse_crashgen_registry(game_data),
        };

        data.apply_metadata_fallbacks(selected_game_version, crashgen_ignore_is_configured);
        Ok(data)
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

        Self::build_from_yaml_documents(
            &main_data,
            &game_data,
            &ignore_data,
            &game,
            &selected_game_version,
        )
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

        Self::build_from_yaml_documents(
            &main_data,
            &game_data,
            &ignore_data,
            &game,
            &selected_game_version,
        )
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
#[cfg(test)]
#[path = "yamldata_tests.rs"]
mod tests;
