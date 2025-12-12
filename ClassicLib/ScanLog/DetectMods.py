"""Detect and evaluate modifications (mods) using YAML mappings and crash log plugins.

This module provides functions to detect the presence of modifications (mods),
evaluate conflicts or combinations of modifications, and assess important mods'
status and compatibility with a GPU type. It uses provided mappings in YAML format
and plugin information extracted from crash logs.

Functions:
    - detect_mods_single: Identifies mods based on direct matches in the mappings.
    - detect_mods_double: Detects combinations or conflicts of mods using specified pairs.
    - detect_mods_important: Evaluates important mod statuses and their GPU compatibility.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Literal, cast

from ClassicLib.rust.report_rust import ReportFragment


def _convert_to_lowercase(data: dict[str, str]) -> dict[str, str]:
    """Convert all keys in a dictionary to lowercase.

    This function takes a dictionary with string keys and values, and returns a new
    dictionary where all the keys are transformed to lowercase. The values remain
    unchanged.

    Args:
        data: A dictionary where both keys and values are strings.

    Returns:
        A new dictionary with all keys converted to lowercase, while retaining the
        original values.

    """
    return {key.lower(): value for key, value in data.items()}


def _validate_warning(mod_name: str, warning: str) -> None:
    """Validate the presence of a warning message for a given module.

    This function checks if the provided warning message is non-empty for the given
    module name. If the warning message is empty, it raises a `ValueError`.

    Args:
        mod_name (str): The name of the module to validate.
        warning (str): The warning message associated with the module.

    Raises:
        ValueError: If the warning message is empty or not provided.

    """
    if not warning:
        raise ValueError(f"ERROR: {mod_name} has no warning in the database!")


@lru_cache(maxsize=128)
def _compile_mod_pattern(mod_names: frozenset[str]) -> re.Pattern[str]:
    """Compiles a regex pattern from a frozenset of mod names with caching.

    This function creates a single compiled regex pattern that matches any of the
    provided mod names using alternation (|). Results are cached for performance.

    Args:
        mod_names: A frozenset of mod names to match (must be hashable for caching).

    Returns:
        A compiled regex pattern with case-insensitive matching.

    """
    # Sort for consistent pattern generation (helps with debugging)
    sorted_names = sorted(mod_names, key=len, reverse=True)
    patterns = [re.escape(name) for name in sorted_names]
    return re.compile("|".join(patterns), re.IGNORECASE)


@lru_cache(maxsize=128)
def _compile_single_pattern(mod_name: str) -> re.Pattern[str]:
    """Compiles a regex pattern for a single mod name with caching.

    Args:
        mod_name: The mod name to compile into a pattern.

    Returns:
        A compiled regex pattern with case-insensitive matching.

    """
    return re.compile(re.escape(mod_name.lower()), re.IGNORECASE)


def detect_mods_single(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> ReportFragment:
    """Detect modifications (mods) based on provided YAML dictionary and crashlog plugins.

    This function checks if any mod names from the YAML dictionary exist in the crashlog plugins.
    If a match is found, it returns a fragment containing the warnings.

    Args:
        yaml_dict: A mapping of mod names to their respective warnings.
        crashlog_plugins: A mapping of plugin names to their corresponding identifiers.

    Returns:
        ReportFragment containing detected mods, or empty fragment if none found.

    Raises:
        ValueError: If a mod from the YAML dictionary has no warning defined.

    """
    lines = []
    yaml_dict_lower = _convert_to_lowercase(yaml_dict)
    crashlog_plugins_lower = _convert_to_lowercase(crashlog_plugins)

    # Sort mod names by length (longest first) to find most specific matches first
    mod_items = sorted(yaml_dict_lower.items(), key=lambda x: len(x[0]), reverse=True)

    # Extract mod names for pattern compilation
    mod_names = frozenset(name for name, _ in mod_items)
    if not mod_names:
        return ReportFragment.empty()

    # Get cached compiled pattern for all mod names
    combined_pattern = _compile_mod_pattern(mod_names)

    # Create a lookup dictionary for O(1) access to mod warnings
    mod_lookup = dict(mod_items)

    # Track matching plugins for each mod to consolidate output
    # Only store the first matching plugin ID for each mod
    mod_matches: dict[str, str] = {}

    # Process each plugin once with the combined pattern
    for plugin_name, plugin_id in crashlog_plugins_lower.items():
        match = combined_pattern.search(plugin_name)
        if match:
            matched_mod = match.group().lower()
            # Only store the first match for each mod
            if matched_mod not in mod_matches:
                mod_matches[matched_mod] = plugin_id

    # Build output lines for all matches
    for mod_name in sorted(mod_matches.keys(), key=lambda x: len(x), reverse=True):  # noqa: PLW0108
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

            # Remaining lines are joined with hard line breaks for single paragraph rendering
            for line in warning_lines[1:]:
                if line.strip():  # Only add content lines
                    lines.append(f"{line}  \n")
                else:
                    lines.append("  \n")  # Preserve empty lines as hard line breaks
        else:
            # Fallback if no warning content
            lines.append(f"**[!] FOUND : {plugin_list}**\n\n")

    return ReportFragment.from_lines(lines)


def detect_mods_double(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> ReportFragment:
    """Detect conflicts or combinations of specific plugins based on given mappings.

    This function checks for combinations of mods (plugins) defined in the yaml_dict.
    If a predefined combination is found, it returns a fragment with caution messages.

    Args:
        yaml_dict: Dictionary where keys are mod pairs joined by ' | ' and values are warnings.
        crashlog_plugins: Dictionary of plugin names from crash log.

    Returns:
        ReportFragment containing conflicts, or empty fragment if none found.

    Raises:
        ValueError: If a detected mod combination has no warning associated.

    """
    lines = []
    yaml_dict_lower = _convert_to_lowercase(yaml_dict)
    crashlog_plugins_lower = _convert_to_lowercase(crashlog_plugins)

    # Build a set of all unique mod names from the pairs
    all_mod_names: set[str] = set()
    mod_pairs_map: dict[tuple[str, str], str] = {}

    for mod_pair, mod_warning in yaml_dict_lower.items():
        mod1, mod2 = mod_pair.split(" | ", 1)
        all_mod_names.add(mod1)
        all_mod_names.add(mod2)
        mod_pairs_map[mod1, mod2] = mod_warning

    if not all_mod_names:
        return ReportFragment.empty()

    # Get cached compiled pattern for all mod names
    combined_pattern = _compile_mod_pattern(frozenset(all_mod_names))

    # Find which mods are present in the plugins
    mods_present: set[str] = set()
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
    yaml_dict: dict[str, str],
    crashlog_plugins: dict[str, str],
    gpu_rival: Literal["nvidia", "amd"] | None,
    xse_modules: set[str],
) -> ReportFragment:
    """Detect and evaluates important mods based on provided information.

    This function processes a dictionary of mods and their warnings, compares them
    against available plugins (ESP/ESM) and XSE modules (DLL), and returns a fragment
    indicating whether mods are installed and compatible with the specified GPU.

    Args:
        yaml_dict: Dictionary where keys represent mod names and values contain warnings.
        crashlog_plugins: Dictionary of ESP/ESM plugins present in the crash log.
        gpu_rival: Optional GPU type for compatibility checks.
        xse_modules: Set of XSE module names (DLL files) from F4SE PLUGINS section.

    Returns:
        ReportFragment containing important mod status.

    """
    lines = [
        "### Checking for Important Mods\n\n",
    ]

    # Convert plugin names to lowercase once
    plugin_names_lower = list(_convert_to_lowercase(crashlog_plugins).keys())

    # Add XSE module names (DLL files) to the search space
    module_names_lower = [name.lower() for name in xse_modules]
    all_plugins_text = " ".join(plugin_names_lower + module_names_lower)

    # Process each mod entry
    for mod_entry, mod_warning in yaml_dict.items():
        mod_id, mod_display_name = mod_entry.split(" | ", 1)
        # Use cached pattern compilation for each mod ID
        pattern = _compile_single_pattern(mod_id.lower())
        mod_found = bool(pattern.search(all_plugins_text))

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
