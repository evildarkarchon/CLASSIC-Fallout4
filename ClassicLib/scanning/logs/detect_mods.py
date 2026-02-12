"""Detect and evaluate modifications (mods) using Rust-accelerated pattern matching.

This module delegates to the Rust classic_scanlog binding via the integration layer
for high-performance mod detection. The Rust implementation provides 35x speedup
over the previous Python regex-based approach.

Functions:
    - detect_mods_single: Identifies mods based on direct matches in the mappings.
    - detect_mods_double: Detects combinations or conflicts of mods using specified pairs.
    - detect_mods_important: Evaluates important mod statuses and their GPU compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ClassicLib.scanning.logs.reporting import ReportFragment


def detect_mods_single(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> ReportFragment:
    """Detect modifications (mods) based on provided YAML dictionary and crashlog plugins.

    Delegates to the Rust implementation via classic_scanlog for 35x speedup.

    Args:
        yaml_dict: A mapping of mod names to their respective warnings.
        crashlog_plugins: A mapping of plugin names to their corresponding identifiers.

    Returns:
        ReportFragment containing detected mods, or empty fragment if none found.

    """
    from ClassicLib.integration.rust.mod_detector_rust import detect_mods_single as _rust_detect_mods_single

    return _rust_detect_mods_single(yaml_dict, crashlog_plugins)


def detect_mods_double(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> ReportFragment:
    """Detect conflicts or combinations of specific plugins based on given mappings.

    Delegates to the Rust implementation via classic_scanlog for 35x speedup.

    Args:
        yaml_dict: Dictionary where keys are mod pairs joined by ' | ' and values are warnings.
        crashlog_plugins: Dictionary of plugin names from crash log.

    Returns:
        ReportFragment containing conflicts, or empty fragment if none found.

    """
    from ClassicLib.integration.rust.mod_detector_rust import detect_mods_double as _rust_detect_mods_double

    return _rust_detect_mods_double(yaml_dict, crashlog_plugins)


def detect_mods_important(
    yaml_dict: dict[str, str],
    crashlog_plugins: dict[str, str],
    gpu_rival: Literal["nvidia", "amd"] | None,
    xse_modules: set[str] | None = None,
) -> ReportFragment:
    """Detect and evaluates important mods based on provided information.

    Delegates to the Rust implementation via classic_scanlog for 35x speedup.

    Args:
        yaml_dict: Dictionary where keys represent mod names and values contain warnings.
        crashlog_plugins: Dictionary of ESP/ESM plugins present in the crash log.
        gpu_rival: Optional GPU type for compatibility checks.
        xse_modules: Set of XSE module names (DLL files) from F4SE PLUGINS section.

    Returns:
        ReportFragment containing important mod status.

    """
    from ClassicLib.integration.rust.mod_detector_rust import detect_mods_important as _rust_detect_mods_important

    return _rust_detect_mods_important(yaml_dict, crashlog_plugins, gpu_rival, xse_modules)
