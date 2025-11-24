"""
Pure Python implementation of mod detection.

This module provides the fallback Python implementation for detecting
modifications (mods) when Rust acceleration is not available. It handles
mod identification, conflict detection, and compatibility checking.
"""

import re
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from ClassicLib.ScanLog.fragments import ReportFragment


def _convert_to_lowercase(data: dict[str, str]) -> dict[str, str]:
    """
    Converts all keys in a dictionary to lowercase.

    This function takes a dictionary where the keys are strings and returns a new
    dictionary where all the keys have been converted to lowercase. The values
    in the dictionary remain unchanged.

    Args:
        data (dict[str, str]): A dictionary with string keys and string values.

    Returns:
        dict[str, str]: A new dictionary with all keys converted to lowercase.
    """
    return {key.lower(): value for key, value in data.items()}


def _validate_warning(mod_name: str, warning: str) -> None:
    """
    Validates the presence of a warning message for a given module name. If no warning is
    found, raises a ValueError to indicate a missing warning entry in the database.

    Args:
        mod_name (str): The name of the module to validate.
        warning (str): The warning message associated with the module.

    Raises:
        ValueError: If the warning message is empty or not provided.
    """
    if not warning:
        raise ValueError(f"ERROR: {mod_name} has no warning in the database!")


def detect_mods_single(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> "ReportFragment":
    """
    Detect modifications from the given mod dictionary and crash log plugins.

    This function identifies modifications (mods) in a given crash log by matching them
    against a dictionary of known mods and their associated warnings. It uses optimized
    techniques for matching and processing the data to ensure efficient execution.

    The process includes:
    1. Lowercasing input dictionaries for case-insensitive matching.
    2. Sorting mod names by length to match the most specific names first.
    3. Building a combined regex pattern for efficient matching against all plugin names.
    4. Consolidating matches with warnings and formatting output for compatibility.

    The function returns a `ReportFragment` object containing detailed information about
    the identified mods, their associated warnings, and matching plugin information.

    Args:
        yaml_dict (dict[str, str]): A dictionary where keys represent mod names and values
            represent their corresponding warnings or descriptions.
        crashlog_plugins (dict[str, str]): A dictionary where keys represent plugin names
            and values represent plugin IDs, extracted from a crash log.

    Returns:
        ReportFragment: An object encapsulating the lines of the consolidated report about
        detected mods, warnings, and matched plugins.
    """
    from ClassicLib.ScanLog.fragments import ReportFragment

    lines = []
    yaml_dict_lower = _convert_to_lowercase(yaml_dict)
    crashlog_plugins_lower = _convert_to_lowercase(crashlog_plugins)

    # Sort mod names by length (longest first) to find most specific matches first
    mod_items = sorted(yaml_dict_lower.items(), key=lambda x: len(x[0]), reverse=True)

    # Build a single regex pattern that matches all mod names
    mod_patterns = [re.escape(mod_name) for mod_name, _ in mod_items]
    if not mod_patterns:
        return ReportFragment.empty()

    # Create a single compiled pattern with alternation for efficient matching
    combined_pattern = re.compile("|".join(mod_patterns), re.IGNORECASE)

    # Create a lookup dictionary for O(1) access to mod warnings
    mod_lookup = dict(mod_items)

    # Track matching plugins for each mod to consolidate output
    mod_matches = {}

    # Process each plugin once with the combined pattern
    for plugin_name, plugin_id in crashlog_plugins_lower.items():
        match = combined_pattern.search(plugin_name)
        if match:
            matched_mod = match.group().lower()
            # Only store the first match for each mod
            if matched_mod not in mod_matches:
                mod_matches[matched_mod] = plugin_id

    # Build output lines for all matches
    for mod_name in sorted(mod_matches.keys(), key=len, reverse=True):
        mod_warning = mod_lookup[mod_name]
        _validate_warning(mod_name, mod_warning)

        plugin_id = mod_matches[mod_name]
        plugin_list = f"[{plugin_id}]"

        # Build the complete entry using hybrid approach with Qt-compatible newlines
        warning_lines = mod_warning.splitlines()
        if warning_lines:
            # First line (mod name) goes on the same line as FOUND header
            mod_name = warning_lines[0].strip()
            lines.append(f"**[!] FOUND : {plugin_list} {mod_name}**\n\n")

            # Remaining lines are indented with double newlines for Qt compatibility
            for line in warning_lines[1:]:
                if line.strip():  # Only add content lines
                    lines.append(f"{line}\n\n")
                else:
                    lines.append("\n")  # Preserve empty lines as single newlines
        else:
            # Fallback if no warning content
            lines.append(f"**[!] FOUND : {plugin_list}**\n\n")

    return ReportFragment.from_lines(lines)


def detect_mods_double(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> "ReportFragment":
    """
    Detect conflicting mods from given data and generate a report fragment.

    This function analyzes two dictionaries: one containing pairs of mods with associated warnings
    and another representing plugins presumably linked to the mods. It detects potential conflicts
    between mods listed in the dictionaries and creates a report fragment containing any relevant
    warnings.

    Args:
        yaml_dict (dict[str, str]): A dictionary where the keys are pairs of mod names separated by
            ' | ' and the values are the corresponding warnings.
        crashlog_plugins (dict[str, str]): A dictionary representing the crashlog plugins, with
            plugin names as keys.

    Returns:
        ReportFragment: An instance of `ReportFragment` containing any detected conflicts along with
        warnings.
    """
    from ClassicLib.ScanLog.fragments import ReportFragment

    lines = []
    yaml_dict_lower = _convert_to_lowercase(yaml_dict)
    crashlog_plugins_lower = _convert_to_lowercase(crashlog_plugins)

    # Build a set of all unique mod names from the pairs
    all_mod_names = set()
    mod_pairs_map = {}

    for mod_pair, mod_warning in yaml_dict_lower.items():
        mod1, mod2 = mod_pair.split(" | ", 1)
        all_mod_names.add(mod1)
        all_mod_names.add(mod2)
        mod_pairs_map[mod1, mod2] = mod_warning

    if not all_mod_names:
        return ReportFragment.empty()

    # Create a single regex pattern to find all mods in one pass
    mod_patterns = [re.escape(mod) for mod in all_mod_names]
    combined_pattern = re.compile("|".join(mod_patterns), re.IGNORECASE)

    # Find which mods are present in the plugins
    mods_present = set()
    for plugin_name in crashlog_plugins_lower:
        matches = combined_pattern.findall(plugin_name)
        mods_present.update(match.lower() for match in matches)

    # Check for conflicting pairs
    for (mod1, mod2), mod_warning in mod_pairs_map.items():
        if mod1 in mods_present and mod2 in mods_present:
            _validate_warning(f"{mod1} | {mod2}", mod_warning)
            lines.extend(("[!] CAUTION : Conflicting mods detected\n", mod_warning))
            if not mod_warning.endswith("\n"):
                lines.append("\n")
            lines.append("\n")

    return ReportFragment.from_lines(lines)


def detect_mods_important(
    yaml_dict: dict[str, str], crashlog_plugins: dict[str, str], gpu_rival: Literal["nvidia", "amd"] | None
) -> "ReportFragment":
    """
    Processes mod detection based on provided plugin data and YAML configuration.

    This function performs detection of important mods by comparing plugin names
    against a pattern matching system created from a YAML configuration dictionary.
    Additionally, it validates whether certain mods are suitable for the detected
    GPU type and provides warnings accordingly. The function generates a report
    fragment containing details about the found or missing mods.

    Args:
        yaml_dict (dict[str, str]): Dictionary where keys represent mod entries in
            the format "mod_id | mod_display_name" and values are warning messages or
            additional notes about GPU compatibility or potential issues.
        crashlog_plugins (dict[str, str]): Dictionary containing plugin names
            extracted from the crash log report. The keys of this dictionary are
            plugin identifiers in lowercase as a result of preprocessing.
        gpu_rival (Literal["nvidia", "amd"] | None): String indicating the type
            of the GPU detected. It is either "nvidia" or "amd", or None if the GPU
            type is not explicitly specified.

    Returns:
        ReportFragment: A report fragment instance summarizing the detection results
        for important mods. It includes details about detected mods, missing mods,
        and any warnings related to GPU compatibility.

    """
    from ClassicLib.ScanLog.fragments import ReportFragment

    lines = [
        "### Checking for Important Mods\n\n",
    ]

    # Convert plugin names to lowercase once
    plugin_names_lower = list(_convert_to_lowercase(crashlog_plugins).keys())
    all_plugins_text = " ".join(plugin_names_lower)

    # Build patterns for all mod IDs
    mod_patterns = {}
    for mod_entry in yaml_dict:
        mod_id, _ = mod_entry.split(" | ", 1)
        mod_patterns[mod_entry] = re.compile(re.escape(mod_id.lower()), re.IGNORECASE)

    for mod_entry, mod_warning in yaml_dict.items():
        mod_id, mod_display_name = mod_entry.split(" | ", 1)
        mod_found = bool(mod_patterns[mod_entry].search(all_plugins_text))

        if mod_found:
            if gpu_rival and cast("str", gpu_rival) in mod_warning.lower():
                lines.extend((
                    "\n\n",
                    f"❓ {mod_display_name} is installed, BUT IT SEEMS YOU DON'T HAVE AN {gpu_rival.upper()} GPU?\n",
                    "IF THIS IS CORRECT, COMPLETELY UNINSTALL THIS MOD TO AVOID ANY PROBLEMS! \n\n",
                ))
            else:
                lines.append(f"\n✔️ {mod_display_name} is installed!\n\n")
        elif (gpu_rival and mod_warning) and gpu_rival not in mod_warning.lower():
            lines.extend((f"\n❌ {mod_display_name} is not installed!\n", mod_warning, "\n\n"))

    # For important mods, we return content even if empty as absence is information
    return ReportFragment.from_lines(lines, check_content=False) if lines else ReportFragment.empty()
