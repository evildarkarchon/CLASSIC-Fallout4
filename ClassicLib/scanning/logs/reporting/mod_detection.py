"""Mod detection fragment generation utilities.

This module provides functions for generating report fragments
related to mod detection and warnings.
"""

from __future__ import annotations

from ClassicLib.integration.rust.report_rust import ReportFragment


def detect_mods_single_fragment(
    yaml_dict: dict[str, str],
    crashlog_plugins: dict[str, str],
) -> ReportFragment:
    """Detect mod-related warnings by analyzing YAML-defined mod descriptions
    against provided crashlog plugins and returns a formatted report fragment.

    Args:
        yaml_dict (dict[str, str]): A dictionary where keys are mod names
            (including conditions for required plugins separated by "|") and
            values are their corresponding descriptive warnings.
        crashlog_plugins (dict[str, str]): A dictionary representing detected
            plugins in the crash log where keys are plugin identifiers and values
            are plugin descriptions.

    Returns:
        ReportFragment: An object representing the formatted list of mod-related
            warnings if any are found; otherwise, an empty report fragment.

    """
    lines: list[str] = []
    found_count = 0

    for mod_name, mod_description in yaml_dict.items():
        # Check if all required plugins are present
        if "|" in mod_name:
            required_plugins = [p.strip() for p in mod_name.split("|")]
            if not all(any(p.lower() in plugin.lower() for plugin in crashlog_plugins) for p in required_plugins):
                continue
        # Single plugin check
        elif not any(mod_name.lower() in plugin.lower() for plugin in crashlog_plugins):
            continue

        # Add the warning for this mod
        lines.append(f"* ⚠️ {mod_description}\n")
        found_count += 1

    if found_count > 0:
        lines.append("\n")

    return ReportFragment.from_lines(lines)


def generate_mod_check_header_fragment(check_type: str) -> tuple[str, ...]:
    """Generate a markdown header fragment for mods based on the specified check type.

    This function creates a tuple containing a single markdown header string for
    displaying mod check information, which is formatted to include the provided
    `check_type`.

    Args:
        check_type (str): The type of check to be included in the header fragment.

    Returns:
        tuple[str, ...]: A tuple containing the formatted markdown header string.

    """
    return (f"### Checking For Mods That {check_type}\n\n",)
