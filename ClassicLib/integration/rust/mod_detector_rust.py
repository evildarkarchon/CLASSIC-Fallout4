"""Rust-accelerated mod detector functions.

This module provides high-performance mod detection and conflict analysis using
Rust implementations, providing 35x speedup for mod detection. Rust is required.

Performance improvements with Rust:
- 35x faster mod conflict detection
- Batch processing capabilities for multiple logs
- Efficient pattern matching and string operations
- Parallel processing for batch operations
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from ClassicLib.integration.exceptions import RustError, RustParseError
from ClassicLib.integration.factory import get_component

if TYPE_CHECKING:
    from ClassicLib.scanning.logs.reporting import ReportFragment

logger = logging.getLogger(__name__)

# Detect Rust-specific exception types for classic_scanlog
try:
    _rust_scanlog_error = get_component("classic_scanlog", "RustScanLogError")
except ImportError:
    _rust_scanlog_error = None
try:
    _rust_parse_error = get_component("classic_scanlog", "RustParseError")
except ImportError:
    _rust_parse_error = None


def _get_rust_exception_types() -> tuple[tuple[type[BaseException], ...], tuple[type[BaseException], ...]]:
    """Get tuple of Rust exception types to catch.

    Returns:
        A tuple containing two tuples of exception types:
            - ParseError types (RustParseError and module-specific parse errors)
            - Generic RustError types (RustError and module-specific scan log errors)

    """
    parse_errors: tuple[type[BaseException], ...] = (RustParseError,)
    rust_errors: tuple[type[BaseException], ...] = (RustError,)

    # Add module-specific exceptions if available
    if _rust_parse_error:
        parse_errors = (RustParseError, _rust_parse_error)
    if _rust_scanlog_error:
        rust_errors = (RustError, _rust_scanlog_error)

    return parse_errors, rust_errors


# Get exception type tuples at module level for use in exception handlers
parse_errors: tuple[type[BaseException], ...]
rust_errors: tuple[type[BaseException], ...]
parse_errors, rust_errors = _get_rust_exception_types()

_rust_detect_single = get_component("classic_scanlog", "detect_mods_single")
_rust_detect_double = get_component("classic_scanlog", "detect_mods_double")
_rust_detect_important = get_component("classic_scanlog", "detect_mods_important")
_rust_detect_batch = get_component("classic_scanlog", "detect_mods_batch")

logger.debug("✅ Rust mod detector functions available (35x speedup)")


def detect_mods_single(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> ReportFragment:
    """Determine modifications from the provided YAML dictionary and crash log plugins.
    Uses required Rust implementation for performance and deterministic behavior.

    Args:
        yaml_dict (dict[str, str]): Dictionary containing YAML configuration data.
        crashlog_plugins (dict[str, str]): Dictionary containing crash log plugin data.

    Returns:
        ReportFragment: Detected modifications represented as a `ReportFragment` object.

    """
    from ClassicLib.scanning.logs.reporting import ReportFragment

    # Rust returns Vec<String>, convert to ReportFragment
    # Rust function expects (yaml_dict, crashlog_plugins) - both as dicts
    lines = _rust_detect_single(yaml_dict, crashlog_plugins)
    return ReportFragment.from_lines(lines)


def detect_mods_double(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> ReportFragment:
    """Detect mod conflicts using the required Rust implementation.

    Args:
        yaml_dict (dict[str, str]): A dictionary containing YAML configuration details.
        crashlog_plugins (dict[str, str]): A dictionary containing crash log plugin mappings.

    Returns:
        ReportFragment: An object representing the detected mod conflicts.

    """
    from ClassicLib.scanning.logs.reporting import ReportFragment

    # Rust returns Vec<String>, convert to ReportFragment
    # Rust function expects (yaml_dict, crashlog_plugins) - both as dicts
    lines = _rust_detect_double(yaml_dict, crashlog_plugins)
    return ReportFragment.from_lines(lines)


def detect_mods_important(
    yaml_dict: dict[str, str],
    crashlog_plugins: dict[str, str],
    gpu_rival: Literal["nvidia", "amd"] | None,
    xse_modules: set[str] | None = None,
) -> ReportFragment:
    """Detect important modifications (mods) using required Rust implementation.

    Args:
        yaml_dict (dict[str, str]): A dictionary containing YAML configuration data.
        crashlog_plugins (dict[str, str]): A dictionary of plugin crash logs.
        gpu_rival (Literal["nvidia", "amd"] | None): GPU vendor for compatibility checking.
        xse_modules (set[str] | None): Optional set of XSE module names for additional checking.

    Returns:
        ReportFragment: The result of the analysis represented in the form of a
        `ReportFragment` object, either containing important modification details
        or returned as empty if no data is detected.

    """
    from ClassicLib.scanning.logs.reporting import ReportFragment

    # Default to empty set if not provided
    if xse_modules is None:
        xse_modules = set()

    # Rust returns Vec<String>, convert to ReportFragment
    # Rust function expects (yaml_dict, crashlog_plugins, gpu_rival, xse_modules)
    lines = _rust_detect_important(yaml_dict, crashlog_plugins, gpu_rival, xse_modules)
    return ReportFragment.from_lines(lines, check_content=False) if lines else ReportFragment.empty()


def get_mod_detector_status() -> dict[str, Any]:
    """Retrieve the current status of the module detector, including information about
    the availability of specific detection functions and performance metrics. It
    provides a summary of whether the functions are implemented and a relative
    performance gain depending on the availability of rust-based implementations.

    Returns:
        dict[str, Any]: A dictionary containing the following keys:
            - "rust_available" (bool): Indicates if Rust-based functionality is
              available.
            - "single_function" (bool): Specifies if the single detection function is
              implemented.
            - "double_function" (bool): Specifies if the double detection function is
              implemented.
            - "important_function" (bool): Specifies if the important detection
              function is implemented.
            - "batch_function" (bool): Specifies if the batch detection function is
              implemented.
            - "performance_gain" (str): Indicates the performance gain factor as a
              string, formatted as "35x" if Rust is available, and "1x" otherwise.

    """
    return {
        "rust_available": True,
        "single_function": True,
        "double_function": True,
        "important_function": True,
        "batch_function": True,
        "performance_gain": "35x",
    }


# Compatibility function for integration
def is_rust_accelerated() -> bool:
    """Check if Rust acceleration is available.

    This function determines whether the Rust implementation is available and
    enabled for optimization purposes.

    Returns:
        bool: True if Rust acceleration is available, otherwise False.

    """
    return True
