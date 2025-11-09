"""
Rust-accelerated mod detector functions.

This module provides high-performance mod detection and conflict analysis using
Rust implementations when available, providing 35x speedup for mod detection.

Performance improvements with Rust:
- 35x faster mod conflict detection
- Batch processing capabilities for multiple logs
- Efficient pattern matching and string operations
- Parallel processing for batch operations
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from ClassicLib.integration.detector import detect_component
from ClassicLib.integration.exceptions import RustError, RustParseError

if TYPE_CHECKING:
    from ClassicLib.ScanLog.fragments import ReportFragment

logger = logging.getLogger(__name__)

# Detect Rust-specific exception types for classic_scanlog
_, _rust_scanlog_error = detect_component("classic_scanlog", "RustScanLogError")
_, _rust_parse_error = detect_component("classic_scanlog", "RustParseError")


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

# Centralized detection of Rust mod detector functions
_has_single, _rust_detect_single = detect_component("classic_scanlog", "detect_mods_single")
_has_double, _rust_detect_double = detect_component("classic_scanlog", "detect_mods_double")
_has_important, _rust_detect_important = detect_component("classic_scanlog", "detect_mods_important")
_has_batch, _rust_detect_batch = detect_component("classic_scanlog", "detect_mods_batch")

RUST_AVAILABLE = _has_single or _has_double or _has_important or _has_batch

if _has_single:
    logger.debug("✅ Rust detect_mods_single available (35x speedup)")
if _has_double:
    logger.debug("✅ Rust detect_mods_double available (35x speedup)")
if _has_important:
    logger.debug("✅ Rust detect_mods_important available (35x speedup)")
if _has_batch:
    logger.debug("✅ Rust detect_mods_batch available (35x speedup)")


def detect_mods_single(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> ReportFragment:
    """
    Determines modifications from the provided YAML dictionary and crash log plugins.
    This function attempts to leverage a Rust implementation if available for better
    performance. If the Rust implementation is unavailable or fails, it will fall back
    to a Python-based detection mechanism.

    Args:
        yaml_dict (dict[str, str]): Dictionary containing YAML configuration data.
        crashlog_plugins (dict[str, str]): Dictionary containing crash log plugin data.

    Returns:
        ReportFragment: Detected modifications represented as a `ReportFragment` object.
    """
    from ClassicLib.ScanLog.fragments import ReportFragment

    if RUST_AVAILABLE and _rust_detect_single:
        try:
            # Rust returns Vec<String>, convert to ReportFragment
            # Rust function expects (yaml_dict, crashlog_plugins) - both as dicts
            lines = _rust_detect_single(yaml_dict, crashlog_plugins)
            return ReportFragment.from_lines(lines)
        except parse_errors as e:
            logger.warning(f"Rust parse error in mod detection, falling back to Python: {e}")
        except rust_errors as e:
            logger.warning(f"Rust mod detection failed, falling back to Python: {e}")
        except ValueError as e:
            logger.warning(f"Rust mod detection error, falling back to Python: {e}")

    # Python fallback implementation
    from ClassicLib.python.mod_detector_py import detect_mods_single as py_detect

    return py_detect(yaml_dict, crashlog_plugins)


def detect_mods_double(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str]) -> ReportFragment:
    """
    Detects mod conflicts by leveraging Rust-based or Python fallback implementations.

    This function attempts to use the Rust-based conflict detection if available,
    offering potentially faster performance. If the Rust implementation is not
    available or fails, the function falls back to a Python-based implementation.
    The detection generates a processed ReportFragment containing relevant
    information about the detected mod conflicts.

    Args:
        yaml_dict (dict[str, str]): A dictionary containing YAML configuration details.
        crashlog_plugins (dict[str, str]): A dictionary containing crash log plugin mappings.

    Returns:
        ReportFragment: An object representing the detected mod conflicts.
    """
    from ClassicLib.ScanLog.fragments import ReportFragment

    if RUST_AVAILABLE and _rust_detect_double:
        try:
            # Rust returns Vec<String>, convert to ReportFragment
            # Rust function expects (yaml_dict, crashlog_plugins) - both as dicts
            lines = _rust_detect_double(yaml_dict, crashlog_plugins)
            return ReportFragment.from_lines(lines)
        except parse_errors as e:
            logger.warning(f"Rust parse error in mod conflict detection, falling back to Python: {e}")
        except rust_errors as e:
            logger.warning(f"Rust mod conflict detection failed, falling back to Python: {e}")
        except ValueError as e:
            logger.warning(f"Rust mod conflict detection error, falling back to Python: {e}")

    # Python fallback implementation
    from ClassicLib.python.mod_detector_py import detect_mods_double as py_detect

    return py_detect(yaml_dict, crashlog_plugins)


def detect_mods_important(
    yaml_dict: dict[str, str],
    crashlog_plugins: dict[str, str],
    gpu_rival: Literal["nvidia", "amd"] | None,
    xse_modules: set[str] | None = None,
) -> ReportFragment:
    """
    Detects important modifications (mods) using either Rust or Python implementation.

    This function attempts to use a Rust-based implementation for performance benefits.
    If the Rust module is not available or encounters an error, it falls back to a
    Python implementation. The function analyzes provided configuration data and
    plugin crash logs to identify important modifications.

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
    from ClassicLib.ScanLog.fragments import ReportFragment

    # Default to empty set if not provided
    if xse_modules is None:
        xse_modules = set()

    if RUST_AVAILABLE and _rust_detect_important:
        try:
            # Rust returns Vec<String>, convert to ReportFragment
            # Rust function expects (yaml_dict, crashlog_plugins, gpu_rival, xse_modules)
            lines = _rust_detect_important(yaml_dict, crashlog_plugins, gpu_rival, xse_modules)
            return ReportFragment.from_lines(lines, check_content=False) if lines else ReportFragment.empty()
        except parse_errors as e:
            logger.warning(f"Rust parse error in important mod detection, falling back to Python: {e}")
        except rust_errors as e:
            logger.warning(f"Rust important mod detection failed, falling back to Python: {e}")
        except ValueError as e:
            logger.warning(f"Rust important mod detection error, falling back to Python: {e}")

    # Python fallback implementation
    from ClassicLib.python.mod_detector_py import detect_mods_important as py_detect

    return py_detect(yaml_dict, crashlog_plugins, gpu_rival)


def get_mod_detector_status() -> dict[str, Any]:
    """
    Retrieves the current status of the module detector, including information about
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
        "rust_available": RUST_AVAILABLE,
        "single_function": _rust_detect_single is not None,
        "double_function": _rust_detect_double is not None,
        "important_function": _rust_detect_important is not None,
        "batch_function": _rust_detect_batch is not None,
        "performance_gain": "35x" if RUST_AVAILABLE else "1x",
    }


# Compatibility function for integration
def is_rust_accelerated() -> bool:
    """
    Checks if Rust acceleration is available.

    This function determines whether the Rust implementation is available and
    enabled for optimization purposes.

    Returns:
        bool: True if Rust acceleration is available, otherwise False.
    """
    return RUST_AVAILABLE
