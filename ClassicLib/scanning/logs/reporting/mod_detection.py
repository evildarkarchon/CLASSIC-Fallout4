"""Mod detection fragment generation utilities.

This module provides functions for generating report fragments
related to mod detection and warnings. Delegates to Rust-accelerated
mod detection (classic_scanlog.detect_mods_single) and report generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ClassicLib.integration.rust.mod_detector_rust import detect_mods_single as _rust_detect_mods_single
from ClassicLib.integration.rust.report.generator import RustAcceleratedReportGenerator

if TYPE_CHECKING:
    from ClassicLib.integration.rust.report_rust import ReportFragment

_report_generator = RustAcceleratedReportGenerator()


def detect_mods_single_fragment(
    yaml_dict: dict[str, str],
    crashlog_plugins: dict[str, str],
) -> ReportFragment:
    """Detect mod-related warnings using Rust-accelerated pattern matching.

    Delegates to Rust classic_scanlog.detect_mods_single() for 35x faster
    mod detection with compiled regex and parallel processing.

    Args:
        yaml_dict: Dictionary mapping mod names to warning descriptions.
            Pipe-separated keys (e.g., "PluginA | PluginB") require all plugins present.
        crashlog_plugins: Dictionary of detected plugins from the crash log.

    Returns:
        ReportFragment containing formatted mod warnings, or empty if none found.

    """
    return _rust_detect_mods_single(yaml_dict, crashlog_plugins)


def generate_mod_check_header_fragment(check_type: str) -> tuple[str, ...]:
    """Generate a markdown header fragment for mod checks.

    Delegates to Rust ReportGenerator.generate_mod_check_header() and
    returns a tuple for backward compatibility with existing callers.

    Args:
        check_type: The type of check (e.g., "Cause Crashes", "Have Known Issues").

    Returns:
        A tuple containing the formatted markdown header string.

    """
    fragment = _report_generator.generate_mod_check_header(check_type)
    return tuple(fragment.to_list())
