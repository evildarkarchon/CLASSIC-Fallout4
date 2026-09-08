// SPDX-License-Identifier: MIT
/// Read raw and compatibility accessors, including empty structured collection transport.
json config_yaml_values(const config_operations::YamlData& data) {
    json values = json::object();
    values["classic_version"] = std::string(config_operations::yaml_data_classic_version(data));
    values["classic_version_date"] = std::string(config_operations::yaml_data_classic_version_date(data));
    values["crashgen_name_field"] = std::string(config_operations::yaml_data_crashgen_name_field(data));
    values["crashgen_latest_og"] = std::string(config_operations::yaml_data_crashgen_latest_og(data));
    values["warn_noplugins"] = std::string(config_operations::yaml_data_warn_noplugins(data));
    values["warn_outdated"] = std::string(config_operations::yaml_data_warn_outdated(data));
    values["xse_acronym"] = std::string(config_operations::yaml_data_xse_acronym(data));
    values["autoscan_text"] = std::string(config_operations::yaml_data_autoscan_text(data));
    values["game_version"] = std::string(config_operations::yaml_data_game_version(data));
    values["game_root_name_field"] = std::string(config_operations::yaml_data_game_root_name_field(data));
    values["classic_game_hints"] = json::array();
    for (const auto& item : config_operations::yaml_data_classic_game_hints(data))
        values["classic_game_hints"].push_back(owned_string(item));
    values["classic_records_list"] = json::array();
    for (const auto& item : config_operations::yaml_data_classic_records_list(data))
        values["classic_records_list"].push_back(owned_string(item));
    values["crashgen_ignore_og"] = json::array();
    for (const auto& item : config_operations::yaml_data_crashgen_ignore_og(data))
        values["crashgen_ignore_og"].push_back(owned_string(item));
    values["game_ignore_plugins"] = json::array();
    for (const auto& item : config_operations::yaml_data_game_ignore_plugins(data))
        values["game_ignore_plugins"].push_back(owned_string(item));
    values["game_ignore_records"] = json::array();
    for (const auto& item : config_operations::yaml_data_game_ignore_records(data))
        values["game_ignore_records"].push_back(owned_string(item));
    values["ignore_list"] = json::array();
    for (const auto& item : config_operations::yaml_data_ignore_list(data))
        values["ignore_list"].push_back(owned_string(item));
    values["suspects_error_keys"] = json::array();
    for (const auto& item : config_operations::yaml_data_suspects_error_keys(data))
        values["suspects_error_keys"].push_back(owned_string(item));
    values["suspects_error_values"] = json::array();
    for (const auto& item : config_operations::yaml_data_suspects_error_values(data))
        values["suspects_error_values"].push_back(owned_string(item));
    values["suspects_stack_keys"] = json::array();
    for (const auto& item : config_operations::yaml_data_suspects_stack_keys(data))
        values["suspects_stack_keys"].push_back(owned_string(item));
    values["mods_core_keys"] = json::array();
    for (const auto& item : config_operations::yaml_data_mods_core_keys(data))
        values["mods_core_keys"].push_back(owned_string(item));
    values["mods_core_values"] = json::array();
    for (const auto& item : config_operations::yaml_data_mods_core_values(data))
        values["mods_core_values"].push_back(owned_string(item));
    values["mods_core_names"] = json::array();
    for (const auto& item : config_operations::yaml_data_mods_core_names(data))
        values["mods_core_names"].push_back(owned_string(item));
    values["mods_core_gpus"] = json::array();
    for (const auto& item : config_operations::yaml_data_mods_core_gpus(data))
        values["mods_core_gpus"].push_back(owned_string(item));
    values["mods_conf_mod_a"] = json::array();
    for (const auto& item : config_operations::yaml_data_mods_conf_mod_a(data))
        values["mods_conf_mod_a"].push_back(owned_string(item));
    values["mods_conf_mod_b"] = json::array();
    for (const auto& item : config_operations::yaml_data_mods_conf_mod_b(data))
        values["mods_conf_mod_b"].push_back(owned_string(item));
    values["mods_conf_name_a"] = json::array();
    for (const auto& item : config_operations::yaml_data_mods_conf_name_a(data))
        values["mods_conf_name_a"].push_back(owned_string(item));
    values["mods_conf_name_b"] = json::array();
    for (const auto& item : config_operations::yaml_data_mods_conf_name_b(data))
        values["mods_conf_name_b"].push_back(owned_string(item));
    values["mods_conf_descriptions"] = json::array();
    for (const auto& item : config_operations::yaml_data_mods_conf_descriptions(data))
        values["mods_conf_descriptions"].push_back(owned_string(item));
    values["mods_conf_fixes"] = json::array();
    for (const auto& item : config_operations::yaml_data_mods_conf_fixes(data))
        values["mods_conf_fixes"].push_back(owned_string(item));
    values["mods_conf_links"] = json::array();
    for (const auto& item : config_operations::yaml_data_mods_conf_links(data))
        values["mods_conf_links"].push_back(owned_string(item));
    values["get_crashgen_ignore"] = json::array();
    for (const auto& item : config_operations::yaml_data_get_crashgen_ignore(data))
        values["get_crashgen_ignore"].push_back(owned_string(item));
    values["get_crashgen_name"] = owned_string(config_operations::yaml_data_get_crashgen_name(data));
    values["get_game_root_name"] = owned_string(config_operations::yaml_data_get_game_root_name(data));
    values["mods_core_count"] = config_operations::yaml_data_mods_core_count(data);
    values["mods_conf_count"] = config_operations::yaml_data_mods_conf_count(data);
    values["mods_freq_entries"] = config_operations::yaml_data_mods_freq_entries(data).size();
    values["mods_solu_entries"] = config_operations::yaml_data_mods_solu_entries(data).size();
    values["suspects_error_rules"] = config_operations::yaml_data_suspects_error_rules(data).size();
    values["suspects_stack_rules_metadata"] = config_operations::yaml_data_suspects_stack_rules_metadata(data).size();
    values["mods_conf_has_fixes"] = json::array();
    for (bool value : config_operations::yaml_data_mods_conf_has_fixes(data))
        values["mods_conf_has_fixes"].push_back(value);
    values["suspects_stack_count_rules_for_id"] =
        config_operations::yaml_data_suspects_stack_count_rules_for_id(data, "absent-rule").size();
    return values;
}
