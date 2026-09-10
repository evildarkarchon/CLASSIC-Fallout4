"""Public parsed YAML values, including deliberately empty typed collection cases."""


def yaml_values(data) -> dict:
    """Project a native YAML view without interpreting source YAML in the adapter."""
    values = {}
    values["classic_version"] = data.classic_version
    values["classic_version_date"] = data.classic_version_date
    values["crashgen_name_field"] = data.crashgen_name
    values["crashgen_latest_og"] = data.crashgen_latest_og
    values["warn_noplugins"] = data.warn_noplugins
    values["warn_outdated"] = data.warn_outdated
    values["xse_acronym"] = data.xse_acronym
    values["autoscan_text"] = data.autoscan_text
    values["game_version"] = data.game_version
    values["game_root_name_field"] = data.game_root_name
    values["classic_game_hints"] = list(data.classic_game_hints)
    values["classic_records_list"] = list(data.classic_records_list)
    values["crashgen_ignore_og"] = sorted(data.crashgen_ignore)
    values["game_ignore_plugins"] = list(data.game_ignore_plugins)
    values["game_ignore_records"] = list(data.game_ignore_records)
    values["ignore_list"] = list(data.ignore_list)
    values["suspects_error_keys"] = [
        entry["id"] or "" for entry in data.suspect_error_rules
    ]
    values["suspects_error_values"] = [
        entry["name"] or "" for entry in data.suspect_error_rules
    ]
    values["suspects_stack_keys"] = [
        entry["id"] or "" for entry in data.suspect_stack_rules
    ]
    values["mods_core_keys"] = [entry["detect"] or "" for entry in data.game_mods_core]
    values["mods_core_values"] = [
        entry["description"] or "" for entry in data.game_mods_core
    ]
    values["mods_core_names"] = [entry["name"] or "" for entry in data.game_mods_core]
    values["mods_core_gpus"] = [entry["gpu"] or "" for entry in data.game_mods_core]
    values["mods_conf_mod_a"] = [entry["mod_a"] or "" for entry in data.game_mods_conf]
    values["mods_conf_mod_b"] = [entry["mod_b"] or "" for entry in data.game_mods_conf]
    values["mods_conf_name_a"] = [
        entry["name_a"] or "" for entry in data.game_mods_conf
    ]
    values["mods_conf_name_b"] = [
        entry["name_b"] or "" for entry in data.game_mods_conf
    ]
    values["mods_conf_descriptions"] = [
        entry["description"] or "" for entry in data.game_mods_conf
    ]
    values["mods_conf_fixes"] = [entry["fix"] or "" for entry in data.game_mods_conf]
    values["mods_conf_links"] = [entry["link"] or "" for entry in data.game_mods_conf]
    values["mods_core_count"] = len(data.game_mods_core)
    values["mods_conf_count"] = len(data.game_mods_conf)
    values["mods_freq_entries"] = len(data.game_mods_freq)
    values["mods_solu_entries"] = len(data.game_mods_solu)
    values["suspects_error_rules"] = len(data.suspect_error_rules)
    values["suspects_stack_rules_metadata"] = len(data.suspect_stack_rules)
    values["mods_conf_has_fixes"] = [
        entry["fix"] is not None for entry in data.game_mods_conf
    ]
    values["suspects_stack_count_rules_for_id"] = sum(
        len(entry["stack_contains_at_least"])
        for entry in data.suspect_stack_rules
        if entry["id"] == "absent-rule"
    )
    values["get_crashgen_name"] = data.crashgen_name
    values["get_game_root_name"] = data.game_root_name
    values["get_crashgen_ignore"] = sorted(data.crashgen_ignore)
    return values
