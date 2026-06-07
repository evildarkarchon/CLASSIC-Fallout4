use crate::{
    CheckRule, ConfigLayout, CrashgenEntryRaw, CrashgenSettingsRules, ExpectedValue, Predicate,
    PreflightAction, PreflightActionKind, PreflightRule, RuleMessages, RuleReportBucket,
    RuleSeverity, RuleTarget, TargetValueType,
};
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

fn get_hash_value<'a>(yaml: &'a Yaml, key: &str) -> Option<&'a Yaml> {
    yaml.as_hash()?
        .iter()
        .find_map(|(k, v)| (k.as_str() == Some(key)).then_some(v))
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

fn parse_predicate(yaml: &Yaml) -> Option<Predicate> {
    if let Some(all_yaml) = get_hash_value(yaml, "all") {
        let items = all_yaml
            .as_vec()?
            .iter()
            .filter_map(parse_predicate)
            .collect::<Vec<_>>();
        return Some(Predicate::All(items));
    }

    if let Some(any_yaml) = get_hash_value(yaml, "any") {
        let items = any_yaml
            .as_vec()?
            .iter()
            .filter_map(parse_predicate)
            .collect::<Vec<_>>();
        return Some(Predicate::Any(items));
    }

    if let Some(not_yaml) = get_hash_value(yaml, "not") {
        return parse_predicate(not_yaml).map(|item| Predicate::Not(Box::new(item)));
    }

    if let Some(plugin_yaml) = get_hash_value(yaml, "plugin_any") {
        let plugins = plugin_yaml
            .as_vec()?
            .iter()
            .filter_map(Yaml::as_str)
            .map(|value| value.to_lowercase())
            .collect::<Vec<_>>();
        return Some(Predicate::PluginAny(plugins));
    }

    if let Some(layout_yaml) = get_hash_value(yaml, "config_layout_is") {
        return ConfigLayout::parse(layout_yaml.as_str()?).map(Predicate::ConfigLayoutIs);
    }

    if let Some(version_yaml) = get_hash_value(yaml, "crashgen_version_lt") {
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
    let id = get_hash_value(yaml, "id")?.as_str()?.to_string();
    let when = get_hash_value(yaml, "when")
        .and_then(parse_predicate)
        .unwrap_or(Predicate::Always);
    let action_yaml = get_hash_value(yaml, "action")?;

    let kind = get_hash_value(action_yaml, "kind")
        .and_then(Yaml::as_str)
        .and_then(PreflightActionKind::parse)
        .unwrap_or(PreflightActionKind::Notice);
    let bucket = get_hash_value(action_yaml, "bucket")
        .and_then(Yaml::as_str)
        .and_then(RuleReportBucket::parse)
        .unwrap_or_default();
    let severity = get_hash_value(action_yaml, "severity")
        .map(|value| parse_severity(value, RuleSeverity::Info))
        .unwrap_or(RuleSeverity::Info);
    let message = get_hash_value(action_yaml, "message")?
        .as_str()?
        .to_string();
    let fix = get_hash_value(action_yaml, "fix")
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
    let equals_yaml = get_hash_value(expect_yaml, "equals")?;
    match equals_yaml {
        Yaml::Boolean(value) => Some(ExpectedValue::Bool(*value)),
        Yaml::Integer(value) => Some(ExpectedValue::Int(*value)),
        Yaml::String(value) => Some(ExpectedValue::String(value.to_string())),
        _ => None,
    }
}

fn parse_check_rule(yaml: &Yaml) -> Option<CheckRule> {
    let id = get_hash_value(yaml, "id")?.as_str()?.to_string();
    let when = get_hash_value(yaml, "when")
        .and_then(parse_predicate)
        .unwrap_or(Predicate::Always);
    let target_yaml = get_hash_value(yaml, "target")?;
    let target = RuleTarget {
        section: get_hash_value(target_yaml, "section")?
            .as_str()?
            .to_string(),
        key: get_hash_value(target_yaml, "key")?.as_str()?.to_string(),
        value_type: get_hash_value(target_yaml, "type")
            .and_then(Yaml::as_str)
            .and_then(TargetValueType::parse)
            .unwrap_or(TargetValueType::Bool),
    };
    let expect = get_hash_value(yaml, "expect").and_then(parse_expected_value)?;
    let messages_yaml = get_hash_value(yaml, "messages")?;
    let messages = RuleMessages {
        fail: get_hash_value(messages_yaml, "fail")?.as_str()?.to_string(),
        fix: get_hash_value(messages_yaml, "fix")
            .and_then(Yaml::as_str)
            .map(ToString::to_string),
        pass: get_hash_value(messages_yaml, "pass")
            .and_then(Yaml::as_str)
            .map(ToString::to_string),
    };
    let severity = get_hash_value(yaml, "severity")
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

    let preflight = get_hash_value(field_yaml, "preflight")
        .and_then(Yaml::as_vec)
        .map(|items| items.iter().filter_map(parse_preflight_rule).collect())
        .unwrap_or_default();
    let checks = get_hash_value(field_yaml, "checks")
        .and_then(Yaml::as_vec)
        .map(|items| items.iter().filter_map(parse_check_rule).collect())
        .unwrap_or_default();

    Some(CrashgenSettingsRules {
        version: settings_rules_version.unwrap_or(1),
        preflight,
        checks,
    })
}

#[cfg(test)]
#[path = "crashgen_registry_yaml_tests.rs"]
mod tests;
