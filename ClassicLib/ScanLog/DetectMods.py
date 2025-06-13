from typing import Literal, cast


def _convert_to_lowercase(data: dict[str, str]) -> dict[str, str]:
    """Convert dictionary keys to lowercase for case-insensitive comparisons."""
    return {key.lower(): value for key, value in data.items()}


def _validate_warning(mod_name: str, warning: str) -> None:
    """Validate that a mod has an associated warning message."""
    if not warning:
        raise ValueError(f"ERROR: {mod_name} has no warning in the database!")


def detect_mods_single(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> bool:
    """
    Detects modifications (mods) based on provided YAML dictionary, crashlog plugins, and updates the
    autoscan report accordingly.

    This function checks if any mod names from the YAML dictionary exist in the crashlog plugins. If a match is found, it
    will append the respective plugin's identifier and a warning message to the autoscan report.

    Args:
        yaml_dict (dict[str, str]): A mapping of mod names (as keys) to their respective warnings (as values).
        crashlog_plugins (dict[str, str]): A mapping of plugin names (as keys) to their corresponding identifiers
            (as values).
        autoscan_report (list[str]): A collection of strings that the function updates to log findings based on the match
            results.

    Returns:
        bool: True if at least one mod was detected in the crashlog plugins; otherwise, False.

    Raises:
        ValueError: If a mod from the YAML dictionary has no warning defined and is found in the crashlog plugins.
    """
    mods_found = False
    yaml_dict_lower: dict[str, str] = _convert_to_lowercase(yaml_dict)
    crashlog_plugins_lower: dict[str, str] = _convert_to_lowercase(crashlog_plugins)

    for mod_name, mod_warning in yaml_dict_lower.items():
        for plugin_name, plugin_id in crashlog_plugins_lower.items():
            if mod_name in plugin_name:
                _validate_warning(mod_name, mod_warning)
                autoscan_report.extend((f"[!] FOUND : [{plugin_id}] ", mod_warning))
                mods_found = True
                break

    return mods_found


def detect_mods_double(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> bool:
    """
    Detects conflicts or combinations of specific plugins based on given mappings and produces warnings
    or errors if necessary.

    This function checks for combinations of mods (plugins) defined in the `yaml_dict` by iterating
    over the plugins extracted from a crash log. If a predefined combination is found, it either raises
    an error or appends a caution message to the report. Matches are case-insensitive.

    Args:
        yaml_dict (dict[str, str]): A dictionary where the key is a combination of two mod names joined
            by ' | ', and the value is either a warning message or an empty string.
        crashlog_plugins (dict[str, str]): A dictionary containing plugin names identified in a crash log.
        autoscan_report (list[str]): A list to collect warnings or other scan-related messages.

    Returns:
        bool: True if any combination of mods was found; otherwise, False.

    Raises:
        ValueError: If a detected mod combination from the database has no warning associated with it.
    """
    mods_found = False
    yaml_dict_lower: dict[str, str] = _convert_to_lowercase(yaml_dict)
    crashlog_plugins_lower: dict[str, str] = _convert_to_lowercase(crashlog_plugins)
    # Convert to list once to avoid repeated iteration
    plugin_names_list = list(crashlog_plugins_lower.keys())

    for mod_pair, mod_warning in yaml_dict_lower.items():
        mod1, mod2 = mod_pair.split(" | ", 1)

        mod1_found: bool = any(mod1 in plugin_name for plugin_name in plugin_names_list)
        mod2_found: bool = any(mod2 in plugin_name for plugin_name in plugin_names_list)

        if mod1_found and mod2_found:
            _validate_warning(mod_pair, mod_warning)
            autoscan_report.extend(("[!] CAUTION : ", mod_warning))
            mods_found = True

    return mods_found


def detect_mods_important(
    yaml_dict: dict[str, str], crashlog_plugins: dict[str, str], autoscan_report: list[str], gpu_rival: Literal["nvidia", "amd"] | None
) -> None:
    """
    Detects and evaluates important mods based on provided information, updating a report accordingly.

    This function processes a dictionary of mods and their warnings, compares them
    against available plugins, and generates a report indicating whether a mod is
    installed and compatible with the specified GPU (if provided).

    Args:
        yaml_dict (dict[str, str]): A dictionary where keys represent mod names
            and values contain any warnings or messages associated with those mods.
        crashlog_plugins (dict[str, str]): A dictionary of plugins present in the
            crash log, used to check for installed mods.
        autoscan_report (list[str]): A list that serves as a report, updated with
            the status of mods (installed, not installed, or incompatible).
        gpu_rival (Literal["nvidia", "amd"] | None): An optional indicator of a GPU
            type to be compared against mod warnings. If provided, it is used to
            adjust the compatibility checks and generate warnings.
    """
    plugin_names_lower: list[str] = list(_convert_to_lowercase(crashlog_plugins).keys())

    for mod_entry, mod_warning in yaml_dict.items():
        mod_id, mod_display_name = mod_entry.split(" | ", 1)
        mod_found: bool = any(mod_id.lower() in plugin_name for plugin_name in plugin_names_lower)

        if mod_found:
            if gpu_rival and cast("str", gpu_rival) in mod_warning.lower():
                autoscan_report.extend((
                    f"❓ {mod_display_name} is installed, BUT IT SEEMS YOU DON'T HAVE AN {gpu_rival.upper()} GPU?\n",
                    "IF THIS IS CORRECT, COMPLETELY UNINSTALL THIS MOD TO AVOID ANY PROBLEMS! \n\n",
                ))
            else:
                autoscan_report.append(f"✔️ {mod_display_name} is installed!\n\n")
        elif (gpu_rival and mod_warning) and gpu_rival not in mod_warning.lower():
            autoscan_report.extend((f"❌ {mod_display_name} is not installed!\n", mod_warning, "\n"))
