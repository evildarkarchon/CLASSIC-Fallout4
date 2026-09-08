use crate::{CrashgenEntryRaw, CrashgenSettingsRules, parse_crashgen_expectations};
use serde_json::{Map, Number, Value};
use std::collections::HashMap;
use yaml_rust2::Yaml;

/// Parse the `Crashgen_Registry` top-level key from a game YAML document.
///
/// Returns a map of crashgen name to raw entry data, including the `"default"` key if present.
/// Missing or malformed entries are silently skipped, with debug logs for malformed fields.
pub(crate) fn parse_crashgen_registry(game_data: &Yaml) -> HashMap<String, CrashgenEntryRaw> {
    let mut result = HashMap::new();

    let Some(registry_node) = game_data["Crashgen_Registry"].as_hash() else {
        return result;
    };

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

/// Validate every present `Crashgen_Registry` value before tolerant parsing can discard it.
pub(crate) fn validate_crashgen_registry(game_data: &Yaml) -> Result<(), String> {
    let registry_yaml = &game_data["Crashgen_Registry"];
    if matches!(registry_yaml, Yaml::BadValue) {
        return Ok(());
    }
    let registry = registry_yaml
        .as_hash()
        .ok_or_else(|| "`Crashgen_Registry` must be a mapping".to_string())?;

    for (name_yaml, entry_yaml) in registry {
        let name = name_yaml
            .as_str()
            .filter(|name| !name.trim().is_empty())
            .ok_or_else(|| "`Crashgen_Registry` keys must be non-empty strings".to_string())?;
        entry_yaml
            .as_hash()
            .ok_or_else(|| format!("`Crashgen_Registry.{name}` must be a mapping"))?;

        validate_optional_registry_string(entry_yaml, name, "display_section")?;
        validate_optional_registry_string_list(entry_yaml, name, "ignore_keys")?;
        validate_optional_registry_string_list(entry_yaml, name, "checks")?;
        let version = validate_optional_registry_version(entry_yaml, name)?;

        let settings_rules = &entry_yaml["settings_rules"];
        if !matches!(settings_rules, Yaml::BadValue) {
            if settings_rules.as_hash().is_none() {
                return Err(format!(
                    "`Crashgen_Registry.{name}.settings_rules` must be a mapping"
                ));
            }
            let parsed = parse_crashgen_expectations(&yaml_to_json(settings_rules), version);
            if let Some(diagnostic) = parsed.diagnostics.first() {
                return Err(format!(
                    "`Crashgen_Registry.{name}.settings_rules{}` is invalid: {}",
                    diagnostic.path.trim_start_matches('$'),
                    diagnostic.message
                ));
            }
            if parsed.rules.is_none() {
                return Err(format!(
                    "`Crashgen_Registry.{name}.settings_rules` did not produce typed rules"
                ));
            }
        }
    }

    Ok(())
}

/// Validate one optional scalar string field in a registry entry.
fn validate_optional_registry_string(
    entry_yaml: &Yaml,
    entry_name: &str,
    field_name: &str,
) -> Result<(), String> {
    let value = &entry_yaml[field_name];
    if matches!(value, Yaml::BadValue) || value.as_str().is_some() {
        Ok(())
    } else {
        Err(format!(
            "`Crashgen_Registry.{entry_name}.{field_name}` must be a string"
        ))
    }
}

/// Validate one optional string-list field without silently dropping items.
fn validate_optional_registry_string_list(
    entry_yaml: &Yaml,
    entry_name: &str,
    field_name: &str,
) -> Result<(), String> {
    let value = &entry_yaml[field_name];
    if matches!(value, Yaml::BadValue) {
        return Ok(());
    }
    let items = value.as_vec().ok_or_else(|| {
        format!("`Crashgen_Registry.{entry_name}.{field_name}` must be a sequence of strings")
    })?;
    if items.iter().all(|item| item.as_str().is_some()) {
        Ok(())
    } else {
        Err(format!(
            "`Crashgen_Registry.{entry_name}.{field_name}` must contain only strings"
        ))
    }
}

/// Validate and return optional registry rule-version metadata.
fn validate_optional_registry_version(
    entry_yaml: &Yaml,
    entry_name: &str,
) -> Result<Option<u32>, String> {
    let value = &entry_yaml["settings_rules_version"];
    match value {
        Yaml::BadValue => Ok(None),
        Yaml::Integer(value) => u32::try_from(*value).map(Some).map_err(|_| {
            format!(
                "`Crashgen_Registry.{entry_name}.settings_rules_version` must fit an unsigned 32-bit integer"
            )
        }),
        Yaml::String(value) => value.trim().parse::<u32>().map(Some).map_err(|_| {
            format!(
                "`Crashgen_Registry.{entry_name}.settings_rules_version` must be an unsigned 32-bit integer"
            )
        }),
        _ => Err(format!(
            "`Crashgen_Registry.{entry_name}.settings_rules_version` must be an integer or numeric string"
        )),
    }
}

fn parse_string_list_field(entry_name: &str, field_name: &str, field_yaml: &Yaml) -> Vec<String> {
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

fn parse_settings_rules(
    entry_name: &str,
    settings_rules_version: Option<u32>,
    field_yaml: &Yaml,
) -> Option<CrashgenSettingsRules> {
    if field_yaml.as_hash().is_none() {
        if !matches!(field_yaml, Yaml::BadValue) {
            log::debug!(
                "Crashgen_Registry.{}.settings_rules is malformed (expected mapping): {:?}",
                entry_name,
                field_yaml
            );
        }
        return None;
    }

    let document = yaml_to_json(field_yaml);
    let result = parse_crashgen_expectations(&document, settings_rules_version);
    for diagnostic in &result.diagnostics {
        log::debug!(
            "Crashgen_Registry.{}.settings_rules{}: {}",
            entry_name,
            diagnostic.path.trim_start_matches('$'),
            diagnostic.message
        );
    }
    result.rules
}

fn yaml_to_json(yaml: &Yaml) -> Value {
    match yaml {
        Yaml::Real(value) => value
            .parse::<f64>()
            .ok()
            .and_then(Number::from_f64)
            .map(Value::Number)
            .unwrap_or(Value::Null),
        Yaml::Integer(value) => Value::Number(Number::from(*value)),
        Yaml::String(value) => Value::String(value.clone()),
        Yaml::Boolean(value) => Value::Bool(*value),
        Yaml::Array(items) => Value::Array(items.iter().map(yaml_to_json).collect()),
        Yaml::Hash(items) => {
            let mut map = Map::new();
            for (key, value) in items {
                if let Some(key) = key.as_str() {
                    map.insert(key.to_string(), yaml_to_json(value));
                }
            }
            Value::Object(map)
        }
        Yaml::Alias(_) | Yaml::Null | Yaml::BadValue => Value::Null,
    }
}

#[cfg(test)]
#[path = "crashgen_registry_yaml_tests.rs"]
mod tests;
