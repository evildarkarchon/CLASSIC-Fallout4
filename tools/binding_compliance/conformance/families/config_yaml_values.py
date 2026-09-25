"""Bounded raw YAML accessor coverage over complete observed projections."""

from collections.abc import Mapping

from ..coverage import CoveragePredicate

YAML_VALUE_KEYS = (
    "classic_version",
    "classic_version_date",
    "crashgen_name_field",
    "crashgen_latest_og",
    "warn_noplugins",
    "warn_outdated",
    "xse_acronym",
    "autoscan_text",
    "game_version",
    "game_root_name_field",
    "classic_game_hints",
    "classic_records_list",
    "crashgen_ignore_og",
    "game_ignore_plugins",
    "game_ignore_records",
    "ignore_list",
    "suspects_error_keys",
    "suspects_error_values",
    "suspects_stack_keys",
    "mods_core_keys",
    "mods_core_values",
    "mods_core_names",
    "mods_core_gpus",
    "mods_conf_mod_a",
    "mods_conf_mod_b",
    "mods_conf_name_a",
    "mods_conf_name_b",
    "mods_conf_descriptions",
    "mods_conf_fixes",
    "mods_conf_links",
    "mods_core_count",
    "mods_conf_count",
    "mods_freq_entries",
    "mods_solu_entries",
    "suspects_error_rules",
    "suspects_stack_rules_metadata",
    "mods_conf_has_fixes",
    "suspects_stack_count_rules_for_id",
    "get_crashgen_name",
    "get_game_root_name",
    "get_crashgen_ignore",
)


def matches_yaml_values(observation):
    """Require the complete public accessor projection and exact source envelope."""
    result = observation.get("result")
    values = result.get("yamlValues") if isinstance(result, Mapping) else None
    return (
        set(observation) == {"result", "error", "files"}
        and observation["error"] is None
        and isinstance(values, Mapping)
        and set(values) == set(YAML_VALUE_KEYS)
        and values.get("classic_version") == result.get("classicVersion")
        and values.get("get_crashgen_name") == values.get("crashgen_name_field")
        and values.get("get_game_root_name") == values.get("game_root_name_field")
    )


YAML_VALUES_PREDICATE = CoveragePredicate(
    "config-operations.yaml-values",
    "config-operations.yaml-values",
    "config-operations.load-explicit",
    "values",
    ("YamlDataCore",),
    matches_yaml_values,
    runtime_operations=(
        None,
        "createYamlDataFromContent",
        "YamlData.from_yaml_content",
        "YamlData.__repr__",
        "yaml_data_classic_version",
        "yaml_data_classic_version_date",
        "yaml_data_crashgen_name_field",
        "yaml_data_crashgen_latest_og",
        "yaml_data_warn_noplugins",
        "yaml_data_warn_outdated",
        "yaml_data_xse_acronym",
        "yaml_data_autoscan_text",
        "yaml_data_game_version",
        "yaml_data_game_root_name_field",
        "yaml_data_classic_game_hints",
        "yaml_data_classic_records_list",
        "yaml_data_crashgen_ignore_og",
        "yaml_data_game_ignore_plugins",
        "yaml_data_game_ignore_records",
        "yaml_data_ignore_list",
        "yaml_data_suspects_error_keys",
        "yaml_data_suspects_error_values",
        "yaml_data_suspects_stack_keys",
        "yaml_data_mods_core_keys",
        "yaml_data_mods_core_values",
        "yaml_data_mods_core_names",
        "yaml_data_mods_core_gpus",
        "yaml_data_mods_conf_mod_a",
        "yaml_data_mods_conf_mod_b",
        "yaml_data_mods_conf_name_a",
        "yaml_data_mods_conf_name_b",
        "yaml_data_mods_conf_descriptions",
        "yaml_data_mods_conf_fixes",
        "yaml_data_mods_conf_links",
        "yaml_data_mods_core_count",
        "yaml_data_mods_conf_count",
        "yaml_data_mods_freq_entries",
        "yaml_data_mods_solu_entries",
        "yaml_data_suspects_error_rules",
        "yaml_data_suspects_stack_rules_metadata",
        "yaml_data_mods_conf_has_fixes",
        "yaml_data_suspects_stack_count_rules_for_id",
        "yaml_data_get_crashgen_name",
        "yaml_data_get_game_root_name",
        "yaml_data_get_crashgen_ignore",
    ),
)
