from typing import Literal, cast


def detect_mods_single(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> bool:
    """
    Detects modifications (mods) based on provided YAML dictionary, crashlog plugins, and updates the
    autoscan report accordingly.

    This function checks if any mod names from the YAML dictionary exist in the crashlog plugins. If a match is found, it
    will append the respective plugin's identifier and a warning message to the autoscan report. If a mod in the YAML
    dictionary has no associated warning but is found in the crashlog plugins, a ValueError is raised.

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
    trigger_mod_found = False
    yaml_dict_lower = {key.lower(): value for key, value in yaml_dict.items()}
    crashlog_plugins_lower = {key.lower(): value for key, value in crashlog_plugins.items()}

    for mod_name_lower, mod_warn in yaml_dict_lower.items():
        for plugin_name_lower, plugin_fid in crashlog_plugins_lower.items():
            if mod_name_lower in plugin_name_lower:
                if mod_warn:
                    autoscan_report.extend((f"[!] FOUND : [{plugin_fid}] ", mod_warn))
                else:
                    raise ValueError(f"ERROR: {mod_name_lower} has no warning in the database!")
                trigger_mod_found = True
                break
    return trigger_mod_found


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
    trigger_mod_found = False
    yaml_dict_lower = {key.lower(): value for key, value in yaml_dict.items()}
    crashlog_plugins_lower = {key.lower(): value for key, value in crashlog_plugins.items()}

    for mod_name_lower, mod_warn in yaml_dict_lower.items():
        mod_split = mod_name_lower.split(" | ", 1)
        mod1_found = mod2_found = False
        for plugin_name_lower in crashlog_plugins_lower:
            if not mod1_found and mod_split[0] in plugin_name_lower:
                mod1_found = True
                continue
            if not mod2_found and mod_split[1] in plugin_name_lower:
                mod2_found = True
                continue
        if mod1_found and mod2_found:
            if mod_warn:
                autoscan_report.extend(("[!] CAUTION : ", mod_warn))
            else:
                raise ValueError(f"ERROR: {mod_name_lower} has no warning in the database!")
            trigger_mod_found = True
    return trigger_mod_found


def detect_mods_important(yaml_dict: dict[str, str],
                          crashlog_plugins: dict[str, str],
                          autoscan_report: list[str],
                          gpu_rival: Literal["nvidia", "amd"] | None) -> None:
    """
    Detects and evaluates important mods based on provided information, updating a report accordingly.

    This function processes a dictionary of mods and their warnings, compares them
    against available plugins, and generates a report indicating whether a mod is
    installed and compatible with the specified GPU (if provided). It appends the
    status and any relevant warnings to the auto-scan report.

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
    for mod_name in yaml_dict:
        mod_warn = yaml_dict.get(mod_name, "")
        mod_split = mod_name.split(" | ", 1)
        mod_found = False
        for plugin_name in crashlog_plugins:
            if mod_split[0].lower() in plugin_name.lower():
                mod_found = True
                continue
        if mod_found:
            if gpu_rival and cast("str", gpu_rival) in mod_warn.lower():
                autoscan_report.extend((
                    f"❓ {mod_split[1]} is installed, BUT IT SEEMS YOU DON'T HAVE AN {gpu_rival.upper()} GPU?\n",
                    "IF THIS IS CORRECT, COMPLETELY UNINSTALL THIS MOD TO AVOID ANY PROBLEMS! \n\n",
                ))
            else:
                autoscan_report.append(f"✔️ {mod_split[1]} is installed!\n\n")
        elif (gpu_rival and mod_warn) and gpu_rival not in mod_warn.lower():
            autoscan_report.extend((f"❌ {mod_split[1]} is not installed!\n", mod_warn, "\n"))
