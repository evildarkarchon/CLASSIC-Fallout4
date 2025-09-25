"""
Component Factory Module

Provides factory functions for creating the appropriate implementation
(Rust or Python) of each component based on runtime availability.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from .config import DISABLE_RUST_ENV_VAR
from .detector import detect_rust_components

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)

# Cache for component availability to avoid repeated detection
_components_cache: dict[str, bool] | None = None


def _get_components() -> dict[str, bool]:
    """Get cached component availability or detect if not cached."""
    global _components_cache
    if _components_cache is None:
        _components_cache = detect_rust_components()
    return _components_cache


def _is_rust_disabled() -> bool:
    """Check if Rust is disabled via environment variable."""
    return os.environ.get(DISABLE_RUST_ENV_VAR, "").lower() in ("1", "true", "yes")


def get_file_io(encoding: str = "utf-8", errors: str = "ignore") -> Any:
    """
    Get the best available file I/O implementation.

    Args:
        encoding: Text encoding to use
        errors: Error handling mode

    Returns:
        RustFileIO if available, otherwise FileIOCore
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("file_io_core", False):
        try:
            from ClassicLib.rust.file_io_rust import RustFileIOCore
            logger.debug("Using Rust FileIOCore (10-20x file ops, 30-40x DDS processing)")
            return RustFileIOCore(encoding, errors)
        except ImportError as e:
            logger.warning(f"Failed to import Rust FileIOCore: {e}")

    # Fall back to Python implementation
    from ClassicLib.python.file_io_py import FileIOCore
    logger.debug("Using Python FileIOCore implementation")
    return FileIOCore(encoding, errors)


def get_parser() -> Any:
    """
    Get the best available log parser implementation.

    Returns:
        RustLogParser wrapper if available, otherwise Python parser
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("parser", False):
        try:
            # Import the wrapper that handles both Rust and Python
            from ClassicLib.rust.parser_rust import RustLogParser
            logger.debug("Using RustLogParser wrapper (150x speedup potential)")
            return RustLogParser()
        except ImportError as e:
            logger.warning(f"Failed to import RustLogParser: {e}")

    # Fall back to pure Python functions
    # Return a wrapper that provides the same interface
    logger.debug("Using Python parser implementation")

    class PythonParserWrapper:
        """Wrapper for Python parser functions to match RustLogParser interface."""

        def find_segments(self, crash_data, crashgen_name, xse_acronym, game_root_name):
            from ClassicLib.python.parser_py import find_segments
            return find_segments(crash_data, crashgen_name, xse_acronym, game_root_name)

        def extract_section(self, crash_data, start_marker, end_marker):
            # Python implementation
            section = []
            in_section = False

            for line in crash_data:
                if line.startswith(start_marker):
                    in_section = True
                    continue
                elif line.startswith(end_marker):
                    break
                elif in_section:
                    section.append(line)

            return section if section else None

    return PythonParserWrapper()


def get_formid_analyzer(
    yamldata: ClassicScanLogsInfo,
    show_values: bool,
    db_exists: bool
) -> Any:
    """
    Get the best available FormID analyzer implementation.

    Args:
        yamldata: YAML configuration data
        show_values: Whether to show FormID values
        db_exists: Whether FormID database exists

    Returns:
        RustFormIDAnalyzer wrapper if available, otherwise Python analyzer
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("formid_analyzer", False):
        try:
            from ClassicLib.rust.formid_rust import RustFormIDAnalyzer
            logger.debug("Using RustFormIDAnalyzer wrapper (50x speedup potential)")
            return RustFormIDAnalyzer(yamldata, show_values, db_exists)
        except ImportError as e:
            logger.warning(f"Failed to import RustFormIDAnalyzer: {e}")

    # Fall back to Python implementation
    from ClassicLib.python.formid_py import FormIDAnalyzer
    logger.debug("Using Python FormIDAnalyzer implementation")
    return FormIDAnalyzer(yamldata, show_values, db_exists)


def get_plugin_analyzer(yamldata: ClassicScanLogsInfo) -> Any:
    """
    Get the best available plugin analyzer implementation.

    Args:
        yamldata: YAML configuration data

    Returns:
        RustPluginAnalyzer wrapper if available, otherwise Python analyzer
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("plugin_analyzer", False):
        try:
            from ClassicLib.rust.plugin_rust import RustPluginAnalyzer
            logger.debug("Using RustPluginAnalyzer wrapper (30x speedup potential)")
            return RustPluginAnalyzer(yamldata)
        except ImportError as e:
            logger.warning(f"Failed to import RustPluginAnalyzer: {e}")

    # Fall back to Python implementation
    from ClassicLib.python.plugin_py import PluginAnalyzer
    logger.debug("Using Python PluginAnalyzer implementation")
    return PluginAnalyzer(yamldata)


def get_record_scanner(yamldata: ClassicScanLogsInfo) -> Any:
    """
    Get the best available record scanner implementation.

    Args:
        yamldata: YAML configuration data

    Returns:
        RustRecordScanner wrapper if available, otherwise Python scanner
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("record_scanner", False):
        try:
            from ClassicLib.rust.record_rust import RustRecordScanner
            logger.debug("Using RustRecordScanner wrapper (40x speedup potential)")
            return RustRecordScanner(yamldata)
        except ImportError as e:
            logger.warning(f"Failed to import RustRecordScanner: {e}")

    # Fall back to Python implementation
    from ClassicLib.python.record_py import RecordScanner
    logger.debug("Using Python RecordScanner implementation")
    return RecordScanner(yamldata)


def get_report_generator(yamldata: ClassicScanLogsInfo | None = None) -> Any:
    """
    Get the best available report generator implementation.

    Args:
        yamldata: Optional YAML configuration data

    Returns:
        Rust report generator if available, otherwise Python implementation
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("report_generation", False):
        try:
            # Try to import Rust report generator wrapper
            from ClassicLib.rust.report_rust import RustAcceleratedReportGenerator
            logger.debug("Using Rust ReportGenerator (75x speedup potential)")
            return RustAcceleratedReportGenerator(yamldata)
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to get Rust ReportGenerator: {e}")

    # Fall back to Python implementation
    from ClassicLib.python.report_py import ReportGenerator
    logger.debug("Using Python report generator implementation")
    return ReportGenerator(yamldata)


def get_yaml_operations() -> Any:
    """
    Get the best available YAML operations implementation.

    Returns:
        RustYamlOperations if available, otherwise Python implementation
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("yaml_operations", False):
        try:
            import classic_core
            if hasattr(classic_core, "yaml") and hasattr(classic_core.yaml, "RustYamlOperations"):
                logger.debug("Using Rust YAML Operations (15-30x parsing, 10-20x writing speedup)")
                return classic_core.yaml.RustYamlOperations()
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to get Rust YAML Operations: {e}")

    # Fall back to Python implementation - return None to indicate no acceleration available
    logger.debug("Using Python YAML implementation (ruamel.yaml)")
    return None


def get_database_pool(max_connections: int = 10, cache_ttl_seconds: int = 300) -> Any:
    """
    Get the best available database pool implementation.

    Args:
        max_connections: Maximum number of database connections
        cache_ttl_seconds: TTL for cache entries in seconds

    Returns:
        RustAsyncDatabasePool if available, otherwise AsyncDatabasePool
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("database_pool", False):
        try:
            from ClassicLib.rust.database_rust import RustAsyncDatabasePool
            logger.debug("Using Rust DatabasePool (25x speedup)")
            return RustAsyncDatabasePool(max_connections, cache_ttl_seconds)
        except ImportError as e:
            logger.warning(f"Failed to import Rust DatabasePool: {e}")

    # Fall back to Python implementation
    from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool
    logger.debug("Using Python AsyncDatabasePool implementation")
    return AsyncDatabasePool(max_connections)


def get_mod_detector() -> dict[str, Any]:
    """
    Get the best available mod detector functions.

    Returns:
        Dictionary containing detect_mods_single and detect_mods_batch functions
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("mod_detector", False):
        try:
            from ClassicLib.rust.mod_detector_rust import detect_mods_single, detect_mods_batch
            logger.debug("Using Rust mod detector functions (35x speedup)")
            return {
                "detect_mods_single": detect_mods_single,
                "detect_mods_batch": detect_mods_batch,
            }
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to get Rust mod detector: {e}")

    # Fall back to Python implementation
    from ClassicLib.python.mod_detector_py import detect_mods_single, detect_mods_batch
    logger.debug("Using Python mod detector implementation")
    return {
        "detect_mods_single": detect_mods_single,
        "detect_mods_batch": detect_mods_batch,
    }


def reset_cache() -> None:
    """Reset the component cache to force re-detection."""
    global _components_cache
    _components_cache = None
    logger.debug("Component cache reset")
