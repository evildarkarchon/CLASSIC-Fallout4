//! Native YAML fields and empty structured collection observations.
use classic_config_core::YamlDataCore;
use serde_json::{Value, json};

/// Read raw and compatibility views of the same core-owned parsed data.
pub(super) fn observe(data: &YamlDataCore) -> Value {
    let mut values = serde_json::Map::new();
    values.insert("classic_version".into(), json!(data.classic_version));
    values.insert(
        "classic_version_date".into(),
        json!(data.classic_version_date),
    );
    values.insert("crashgen_name_field".into(), json!(data.crashgen_name));
    values.insert("crashgen_latest_og".into(), json!(data.crashgen_latest_og));
    values.insert("warn_noplugins".into(), json!(data.warn_noplugins));
    values.insert("warn_outdated".into(), json!(data.warn_outdated));
    values.insert("xse_acronym".into(), json!(data.xse_acronym));
    values.insert("autoscan_text".into(), json!(data.autoscan_text));
    values.insert("game_version".into(), json!(data.game_version));
    values.insert("game_root_name_field".into(), json!(data.game_root_name));
    values.insert("classic_game_hints".into(), json!(data.classic_game_hints));
    values.insert(
        "classic_records_list".into(),
        json!(data.classic_records_list),
    );
    values.insert("crashgen_ignore_og".into(), json!(data.crashgen_ignore));
    values.insert(
        "game_ignore_plugins".into(),
        json!(data.game_ignore_plugins),
    );
    values.insert(
        "game_ignore_records".into(),
        json!(data.game_ignore_records),
    );
    values.insert("ignore_list".into(), json!(data.ignore_list));
    values.insert(
        "suspects_error_keys".into(),
        json!(
            data.suspect_error_rules
                .iter()
                .map(|entry| entry.id.clone())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "suspects_error_values".into(),
        json!(
            data.suspect_error_rules
                .iter()
                .map(|entry| entry.name.clone())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "suspects_stack_keys".into(),
        json!(
            data.suspect_stack_rules
                .iter()
                .map(|entry| entry.id.clone())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "mods_core_keys".into(),
        json!(
            data.game_mods_core
                .iter()
                .map(|entry| entry.detect.clone())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "mods_core_values".into(),
        json!(
            data.game_mods_core
                .iter()
                .map(|entry| entry.description.clone())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "mods_core_names".into(),
        json!(
            data.game_mods_core
                .iter()
                .map(|entry| entry.name.clone())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "mods_core_gpus".into(),
        json!(
            data.game_mods_core
                .iter()
                .map(|entry| entry.gpu.clone().unwrap_or_default())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "mods_conf_mod_a".into(),
        json!(
            data.game_mods_conf
                .iter()
                .map(|entry| entry.mod_a.clone())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "mods_conf_mod_b".into(),
        json!(
            data.game_mods_conf
                .iter()
                .map(|entry| entry.mod_b.clone())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "mods_conf_name_a".into(),
        json!(
            data.game_mods_conf
                .iter()
                .map(|entry| entry.name_a.clone())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "mods_conf_name_b".into(),
        json!(
            data.game_mods_conf
                .iter()
                .map(|entry| entry.name_b.clone())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "mods_conf_descriptions".into(),
        json!(
            data.game_mods_conf
                .iter()
                .map(|entry| entry.description.clone())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "mods_conf_fixes".into(),
        json!(
            data.game_mods_conf
                .iter()
                .map(|entry| entry.fix.clone().unwrap_or_default())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "mods_conf_links".into(),
        json!(
            data.game_mods_conf
                .iter()
                .map(|entry| entry.link.clone().unwrap_or_default())
                .collect::<Vec<_>>()
        ),
    );
    values.insert("mods_core_count".into(), json!(data.game_mods_core.len()));
    values.insert("mods_conf_count".into(), json!(data.game_mods_conf.len()));
    values.insert("mods_freq_entries".into(), json!(data.game_mods_freq.len()));
    values.insert("mods_solu_entries".into(), json!(data.game_mods_solu.len()));
    values.insert(
        "suspects_error_rules".into(),
        json!(data.suspect_error_rules.len()),
    );
    values.insert(
        "suspects_stack_rules_metadata".into(),
        json!(data.suspect_stack_rules.len()),
    );
    values.insert(
        "mods_conf_has_fixes".into(),
        json!(
            data.game_mods_conf
                .iter()
                .map(|entry| entry.fix.is_some())
                .collect::<Vec<_>>()
        ),
    );
    values.insert(
        "suspects_stack_count_rules_for_id".into(),
        json!(
            data.suspect_stack_rules
                .iter()
                .filter(|entry| entry.id == "absent-rule")
                .map(|entry| entry.stack_contains_at_least.len())
                .sum::<usize>()
        ),
    );
    values.insert("get_crashgen_name".into(), json!(data.get_crashgen_name()));
    values.insert(
        "get_game_root_name".into(),
        json!(data.get_game_root_name()),
    );
    values.insert(
        "get_crashgen_ignore".into(),
        json!(data.get_crashgen_ignore()),
    );
    Value::Object(values)
}
