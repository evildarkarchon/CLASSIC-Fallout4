"""
Mod detection fragment generation utilities.

This module provides functions for generating report fragments
related to mod detection and warnings.
"""

from __future__ import annotations

from .report_fragment import ReportFragment


def detect_mods_single_fragment(
    yaml_dict: dict[str, str],
    crashlog_plugins: dict[str, str],
) -> ReportFragment:
    """
    Functional version of detect_mods_single that returns a fragment.

    This is what the refactored version would look like.
    """
    lines = []
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
    """Generate header lines for mod check sections."""
    return (f"### Checking For Mods That {check_type}\n\n",)
