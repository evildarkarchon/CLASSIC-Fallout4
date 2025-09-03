import re
from typing import Literal, cast

from ClassicLib.ScanLog.ReportFragment import ReportFragment


def _convert_to_lowercase(data: dict[str, str]) -> dict[str, str]:
    """Convert dictionary keys to lowercase for case-insensitive comparisons."""
    return {key.lower(): value for key, value in data.items()}


def _validate_warning(mod_name: str, warning: str) -> None:
    """Validate that a mod has an associated warning message."""
    if not warning:
        raise ValueError(f"ERROR: {mod_name} has no warning in the database!")


def detect_mods_single(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> ReportFragment:
    """
    Detects modifications (mods) based on provided YAML dictionary and crashlog plugins.

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

    # Build a single regex pattern that matches all mod names
    mod_patterns = [re.escape(mod_name) for mod_name, _ in mod_items]
    if not mod_patterns:
        return ReportFragment.empty()

    # Create a single compiled pattern with alternation for efficient matching
    combined_pattern = re.compile("|".join(mod_patterns), re.IGNORECASE)

    # Create a lookup dictionary for O(1) access to mod warnings
    mod_lookup = {mod_name: warning for mod_name, warning in mod_items}

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
    for mod_name in sorted(mod_matches.keys(), key=lambda x: len(x), reverse=True):
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
                    lines.append(f"    {line}\n\n")
                else:
                    lines.append("\n")  # Preserve empty lines as single newlines
        else:
            # Fallback if no warning content
            lines.append(f"**[!] FOUND : {plugin_list}**\n\n")

    return ReportFragment.from_lines(lines)


def detect_mods_double(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> ReportFragment:
    """
    Detects conflicts or combinations of specific plugins based on given mappings.

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
        mod_pairs_map[(mod1, mod2)] = mod_warning

    if not all_mod_names:
        return ReportFragment.empty()

    # Create a single regex pattern to find all mods in one pass
    mod_patterns = [re.escape(mod) for mod in all_mod_names]
    combined_pattern = re.compile("|".join(mod_patterns), re.IGNORECASE)

    # Find which mods are present in the plugins
    mods_present: set[str] = set()
    for plugin_name in crashlog_plugins_lower.keys():
        matches = combined_pattern.findall(plugin_name)
        mods_present.update(match.lower() for match in matches)

    # Check for conflicting pairs
    for (mod1, mod2), mod_warning in mod_pairs_map.items():
        if mod1 in mods_present and mod2 in mods_present:
            _validate_warning(f"{mod1} | {mod2}", mod_warning)
            lines.append("[!] CAUTION : Conflicting mods detected\n")
            lines.append(mod_warning)
            if not mod_warning.endswith("\n"):
                lines.append("\n")
            lines.append("\n")

    return ReportFragment.from_lines(lines)


def detect_mods_important(
    yaml_dict: dict[str, str], crashlog_plugins: dict[str, str], gpu_rival: Literal["nvidia", "amd"] | None
) -> ReportFragment:
    """
    Detects and evaluates important mods based on provided information.

    This function processes a dictionary of mods and their warnings, compares them
    against available plugins, and returns a fragment indicating whether mods are
    installed and compatible with the specified GPU.

    Args:
        yaml_dict: Dictionary where keys represent mod names and values contain warnings.
        crashlog_plugins: Dictionary of plugins present in the crash log.
        gpu_rival: Optional GPU type for compatibility checks.

    Returns:
        ReportFragment containing important mod status.
    """
    lines = [
        "### Checking for Important Mods\n\n",
    ]

    # Convert plugin names to lowercase once
    plugin_names_lower = list(_convert_to_lowercase(crashlog_plugins).keys())
    all_plugins_text = " ".join(plugin_names_lower)

    # Build patterns for all mod IDs
    mod_patterns: dict[str, re.Pattern[str]] = {}
    for mod_entry in yaml_dict:
        mod_id, _ = mod_entry.split(" | ", 1)
        mod_patterns[mod_entry] = re.compile(re.escape(mod_id.lower()), re.IGNORECASE)

    for mod_entry, mod_warning in yaml_dict.items():
        mod_id, mod_display_name = mod_entry.split(" | ", 1)
        mod_found = bool(mod_patterns[mod_entry].search(all_plugins_text))

        if mod_found:
            if gpu_rival and cast("str", gpu_rival) in mod_warning.lower():
                lines.append("\n\n")
                lines.append(f"❓ {mod_display_name} is installed, BUT IT SEEMS YOU DON'T HAVE AN {gpu_rival.upper()} GPU?\n")
                lines.append("IF THIS IS CORRECT, COMPLETELY UNINSTALL THIS MOD TO AVOID ANY PROBLEMS! \n\n")
            else:
                lines.append(f"\n✔️ {mod_display_name} is installed!\n\n")
        elif (gpu_rival and mod_warning) and gpu_rival not in mod_warning.lower():
            lines.append(f"\n❌ {mod_display_name} is not installed!\n")
            lines.append(mod_warning)
            lines.append("\n\n")

    # For important mods, we return content even if empty as absence is information
    return ReportFragment.from_lines(lines, check_content=False) if lines else ReportFragment.empty()
