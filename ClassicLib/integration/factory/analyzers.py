"""Analyzer factory functions.

Provides factory functions for various analysis components,
selecting between Rust and Python implementations.

Functions:
    get_formid_analyzer: Retrieve the best available FormID analyzer.
    get_plugin_analyzer: Retrieve the most efficient plugin analyzer.
    get_record_scanner: Retrieve the best available record scanner.
    get_suspect_scanner: Retrieve the suspect scanner implementation.
    get_settings_validator: Retrieve the settings validator implementation.
    get_gpu_detector: Retrieve the GPU detector implementation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ClassicLib.integration.factory.core import get_components, is_rust_disabled

if TYPE_CHECKING:
    from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)


def get_formid_analyzer(yamldata: ClassicScanLogsInfo, show_values: bool, db_exists: bool) -> Any:
    """Get an appropriate FormIDAnalyzer instance based on available components.

    This function determines whether the Rust-based `FormIDAnalyzer` or
    the Python implementation `FormIDAnalyzer` should be used for form ID
    analysis, prioritizing the Rust implementation if it is available and
    Rust-based components are not disabled. This provides potential
    performance benefits. If the Rust implementation is unavailable or fails
    to import, the fallback Python implementation is used.

    Args:
        yamldata: The YAML data to be analyzed.
        show_values: Flag indicating whether to include values in the analysis.
        db_exists: Flag indicating whether a database exists for reference
            during analysis.

    Returns:
        Any: An instance of RustFormIDAnalyzer or FormIDAnalyzer, depending on
        the available runtime components.

    """
    components = get_components()

    if not is_rust_disabled() and components.get("formid_analyzer", False):
        try:
            from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer

            logger.debug("Using Rust FormIDAnalyzer wrapper (50x speedup potential)")
            return FormIDAnalyzer(yamldata, show_values, db_exists)
        except ImportError as e:
            logger.warning(f"Failed to import Rust FormIDAnalyzer: {e}")

    # Fall back to Python implementation
    from ClassicLib.integration.python.formid_py import FormIDAnalyzer

    logger.debug("Using Python FormIDAnalyzer implementation")
    return FormIDAnalyzer(yamldata, show_values, db_exists)


def get_plugin_analyzer(yamldata: ClassicScanLogsInfo) -> Any:
    """Retrieve the appropriate plugin analyzer.

    This function attempts to use `RustPluginAnalyzer` for faster performance.
    If the Rust implementation is not available or cannot be imported, it falls
    back to the `PluginAnalyzer` provided in Python. The selection is based on
    the availability of the necessary components and the Rust support status.

    Args:
        yamldata: Input data of type `ClassicScanLogsInfo`, which is required
            to initialize the plugin analyzer.

    Returns:
        Any: An instance of the selected plugin analyzer, either the Rust-based
        `RustPluginAnalyzer` or the Python-based `PluginAnalyzer`.

    """
    components = get_components()

    if not is_rust_disabled() and components.get("plugin_analyzer", False):
        try:
            from ClassicLib.integration.rust.plugin_rust import RustPluginAnalyzer

            logger.debug("Using RustPluginAnalyzer wrapper (30x speedup potential)")
            return RustPluginAnalyzer(yamldata)
        except ImportError as e:
            logger.warning(f"Failed to import RustPluginAnalyzer: {e}")

    # Fall back to Python implementation
    from ClassicLib.integration.python.plugin_py import PluginAnalyzer

    logger.debug("Using Python PluginAnalyzer implementation")
    return PluginAnalyzer(yamldata)


def get_record_scanner(yamldata: ClassicScanLogsInfo) -> Any:
    """Create and return an appropriate record scanner instance.

    This function prioritizes the Rust-based implementation which offers
    significant performance benefits if available and falls back to the
    Python implementation otherwise.

    Args:
        yamldata: The YAML data required for scanning and processing records.

    Returns:
        Any: An instance of a record scanner (either RustRecordScanner or
        RecordScanner) that can process the given YAML data.

    Raises:
        ImportError: If the Rust-based library is not available when attempting
        to use the Rust implementation.

    """
    components = get_components()

    if not is_rust_disabled() and components.get("record_scanner", False):
        try:
            from ClassicLib.integration.rust.record_rust import RustRecordScanner

            logger.debug("Using RustRecordScanner wrapper (40x speedup potential)")
            return RustRecordScanner(yamldata)
        except ImportError as e:
            logger.warning(f"Failed to import RustRecordScanner: {e}")

    # Fall back to Python implementation
    from ClassicLib.integration.python.record_py import RecordScanner

    logger.debug("Using Python RecordScanner implementation")
    return RecordScanner(yamldata)


def get_suspect_scanner(yamldata: ClassicScanLogsInfo) -> Any:
    """Return a SuspectScanner instance suitable for scanning the given YAML data.

    This function automatically determines whether to use the Rust-accelerated
    or Python implementation of the SuspectScanner based on runtime availability
    of the Rust module. The Rust implementation provides significant speed
    enhancements when available.

    Args:
        yamldata: A ClassicScanLogsInfo object containing the log information
            to be scanned.

    Returns:
        Any: An instance of the SuspectScanner initialized with the provided
            log data.

    """
    # Use wrapper that handles Rust/Python automatically
    from ClassicLib.integration.rust.suspect_rust import RUST_AVAILABLE, SuspectScanner

    if RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated SuspectScanner (40x speedup potential)")
    else:
        logger.debug("Using Python SuspectScanner implementation")

    return SuspectScanner(yamldata)


def get_settings_validator(yamldata: ClassicScanLogsInfo) -> Any:
    """Retrieve and return a settings validator instance.

    This function determines the appropriate settings validation implementation
    to use, depending on the availability of a Rust-accelerated version. If Rust
    support is available, it uses the Rust-accelerated `SettingsValidator`.
    Otherwise, it defaults to a Python-based implementation.

    Args:
        yamldata: An instance of ClassicScanLogsInfo to be passed to the
            settings validator.

    Returns:
        Any: A settings validator instance, either Rust-accelerated or
        implemented in Python.

    """
    # Use wrapper that handles Rust/Python automatically
    from ClassicLib.integration.rust.settings_rust import RUST_AVAILABLE, SettingsValidator

    if RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated SettingsValidator")
    else:
        logger.debug("Using Python SettingsScannerFragments implementation")

    return SettingsValidator(yamldata)


def get_gpu_detector() -> Any:
    """Retrieve the GPU detector function with automatic Rust or Python fallback.

    This function determines whether the Rust-accelerated GPU detection
    implementation is available. If Rust is available, the Rust-based
    implementation is used and logged; otherwise, the Python-based
    implementation is used. The returned function provides GPU detection
    capabilities depending on the selected implementation.

    Returns:
        Any: The GPU detection function, automatically selecting between
        Rust-accelerated and Python implementations.

    """
    # Use wrapper that provides get_gpu_info function with automatic Rust/Python fallback
    from ClassicLib.integration.rust import gpu_rust

    if gpu_rust.RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated GpuDetector")
    else:
        logger.debug("Using Python GPUDetector implementation")

    return gpu_rust
