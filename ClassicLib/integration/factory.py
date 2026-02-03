"""Factory module for dynamic Rust/Python implementation selection.

Provides factory functions that return the best available implementation
(Rust-accelerated or Python fallback) for each component. Each factory
function uses a direct try-import pattern -- Python's sys.modules handles
caching, so no custom detection layers are needed.

Also provides ``detect_component`` and ``is_component_available`` utilities
used by the integration/rust/ wrapper modules.

Functions:
    detect_component: Try-import a module/class and return (available, obj).
    is_component_available: Bool convenience wrapper around detect_component.
    get_component: Get a component or raise ImportError.
    get_parser: Log parser factory.
    get_file_io: File I/O singleton factory.
    get_yaml_operations: YAML operations factory.
    get_formid_analyzer: FormID analyzer factory.
    get_plugin_analyzer: Plugin analyzer factory.
    get_record_scanner: Record scanner factory.
    get_suspect_scanner: Suspect scanner factory.
    get_settings_validator: Settings validator factory.
    get_gpu_detector: GPU detector factory.
    get_database_pool: Database pool factory.
    get_report_generator: Report generator factory.
    get_mod_detector: Mod detection functions factory.
    get_orchestrator: Crash log orchestrator factory.
    get_yamldata: YAML data loader factory.
    get_fcx_handler: FCX mode handler factory.
    get_constants: Rust constants module factory.
    get_version_utils: Rust version utilities factory.
    get_resource_mgmt: Rust resource management factory.
    get_xse_utils: Rust XSE utilities factory.
    get_web_utils: Rust web utilities factory.
    get_path_operations: Rust path operations factory.
    reset_cache: Reset factory singletons (for test isolation).
    reset_file_io_singleton: Reset the FileIO singleton.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ClassicLib.integration.types import (
        DatabasePoolProtocol,
        FCXHandlerProtocol,
        FileIOProtocol,
        FormIDAnalyzerProtocol,
        GpuDetectorProtocol,
        LogParserProtocol,
        OrchestratorProtocol,
        PluginAnalyzerProtocol,
        RecordScannerProtocol,
        ReportGeneratorProtocol,
        SettingsValidatorProtocol,
        SuspectScannerProtocol,
        YamlOperationsProtocol,
    )
    from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Centralized component detection
# ---------------------------------------------------------------------------


def detect_component(module_name: str, class_name: str | None = None) -> tuple[bool, Any | None]:
    """Detect if a Rust component is available via try-import.

    Args:
        module_name: Python module name (e.g., "classic_yaml").
        class_name: Optional class/attribute name within module.

    Returns:
        Tuple of (available: bool, component: module or class or None).

    Example:
        >>> available, YamlOps = detect_component("classic_yaml", "YamlOperations")
        >>> if available:
        ...     ops = YamlOps()

    """
    try:
        module = __import__(module_name)

        if class_name:
            if not hasattr(module, class_name):
                return (False, None)
            return (True, getattr(module, class_name))

        return (True, module)
    except ImportError:
        return (False, None)


def is_component_available(module_name: str, class_name: str | None = None) -> bool:
    """Check if a Rust component is available (convenience wrapper).

    Args:
        module_name: Python module name.
        class_name: Optional class name within module.

    Returns:
        True if component is available, False otherwise.

    Example:
        >>> if is_component_available("classic_yaml", "YamlOperations"):
        ...     print("Rust YAML acceleration available")

    """
    available, _ = detect_component(module_name, class_name)
    return available


def get_component(module_name: str, class_name: str) -> Any:
    """Get a Rust component or raise ImportError.

    Args:
        module_name: Python module name.
        class_name: Class name within module.

    Returns:
        The component class.

    Raises:
        ImportError: If component is not available.

    Example:
        >>> YamlOps = get_component("classic_yaml", "YamlOperations")
        >>> ops = YamlOps()

    """
    available, component = detect_component(module_name, class_name)
    if not available:
        msg = f"Rust component {module_name}.{class_name} not available"
        raise ImportError(msg)
    return component


# ---------------------------------------------------------------------------
# PythonParserWrapper (fallback for get_parser)
# ---------------------------------------------------------------------------


class PythonParserWrapper:
    """Wrapper for Python parser functions to match RustLogParser interface."""

    @staticmethod
    def find_segments(
        crash_data: list[str],
        crashgen_name: str,
        xse_acronym: str,
        game_root_name: str,
    ) -> tuple[str, str, str, list[list[str]]]:
        """Find and retrieve segments from crash data.

        Args:
            crash_data: List of strings representing lines of crash data.
            crashgen_name: The name of the crash generation process or identifier.
            xse_acronym: Acronym associated with the XSE process specifics.
            game_root_name: Name of the root directory or identifier for the game's context.

        Returns:
            tuple[str, str, str, list[list[str]]]: A tuple containing game_version,
            crashgen_version, main_error, and processed_segments.

        """
        from ClassicLib.integration.python.parser_py import find_segments

        return find_segments(crash_data, crashgen_name, xse_acronym, game_root_name)

    @staticmethod
    def extract_section(
        crash_data: list[str],
        start_marker: str,
        end_marker: str,
    ) -> list[str] | None:
        """Extract a specific section of text from the given crash data.

        Args:
            crash_data: List of strings representing lines of crash data.
            start_marker: String that marks the start of the desired section.
            end_marker: String that marks the end of the desired section.

        Returns:
            list[str] | None: A list containing lines of the extracted section, or
            None if no valid section is found.

        """
        section = []
        in_section = False

        for line in crash_data:
            if line.startswith(start_marker):
                in_section = True
                continue
            if line.startswith(end_marker):
                break
            if in_section:
                section.append(line)

        return section or None  # pyright: ignore[reportUnknownVariableType]


# ---------------------------------------------------------------------------
# FileIO singleton state
# ---------------------------------------------------------------------------

_file_io_instance: Any = None
_file_io_lock = threading.Lock()


def reset_file_io_singleton() -> None:
    """Reset the FileIO singleton instance (for test isolation).

    Thread-safe reset of the cached FileIO instance.
    """
    global _file_io_instance  # noqa: PLW0603
    with _file_io_lock:
        _file_io_instance = None


def reset_cache() -> None:
    """Reset factory singletons for test isolation.

    Resets the FileIO singleton. No component detection cache exists
    in this module -- Python's sys.modules handles import caching.
    """
    reset_file_io_singleton()
    logger.debug("Factory cache reset")


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def get_parser() -> LogParserProtocol:
    """Retrieve the best available log parser implementation.

    Returns an instance of RustLogParser if Rust acceleration is available,
    otherwise returns a PythonParserWrapper.

    Returns:
        Any: A parser instance providing find_segments() and extract_section().

    """
    try:
        from ClassicLib.integration.rust.parser_rust import RustLogParser

        logger.debug("Using RustLogParser wrapper (150x speedup potential)")
        return RustLogParser()
    except ImportError as e:
        logger.warning(f"Failed to import RustLogParser: {e}")

    logger.debug("Using Python parser implementation")
    return PythonParserWrapper()


def get_file_io(encoding: str = "utf-8", errors: str = "ignore") -> FileIOProtocol:
    """Retrieve or initialize a global file I/O instance.

    Thread-safe singleton pattern. Attempts Rust-based implementation first.

    Args:
        encoding: Text encoding format. Defaults to "utf-8".
        errors: Error handling mode. Defaults to "ignore".

    Returns:
        Any: A singleton FileIOCore instance.

    """
    global _file_io_instance  # noqa: PLW0603

    # Fast path - instance already exists
    if _file_io_instance is not None:
        return _file_io_instance

    # Slow path - need to create instance
    with _file_io_lock:
        # Double-check pattern
        if _file_io_instance is not None:
            return _file_io_instance

        try:
            from ClassicLib.integration.rust.file_io_rust import FileIOCore

            logger.debug("Using Rust FileIOCore (10-20x file ops, 30-40x DDS processing)")
            _file_io_instance = FileIOCore(encoding, errors)
            return _file_io_instance
        except ImportError as e:
            msg = f"Required Rust module for FileIO not available: {e}. Reinstall CLASSIC."
            raise RuntimeError(msg) from e


def get_yaml_operations() -> YamlOperationsProtocol | None:
    """Retrieve the appropriate YAML operations implementation.

    Returns:
        Any: An instance of Rust YamlOperations if available, or None
        if Python implementation is used.

    """
    try:
        import classic_yaml

        if hasattr(classic_yaml, "YamlOperations"):
            logger.debug("Using Rust YAML Operations (15-30x parsing, 10-20x writing speedup)")
            return classic_yaml.YamlOperations()
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to get Rust YAML Operations: {e}")

    logger.debug("Using Python YAML implementation (ruamel.yaml)")
    return None


def get_formid_analyzer(yamldata: ClassicScanLogsInfo, show_values: bool, db_exists: bool) -> FormIDAnalyzerProtocol:
    """Get an appropriate FormIDAnalyzer instance.

    Args:
        yamldata: The YAML data to be analyzed.
        show_values: Whether to include values in the analysis.
        db_exists: Whether a database exists for reference.

    Returns:
        Any: An instance of RustFormIDAnalyzer or FormIDAnalyzer.

    """
    try:
        from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer

        logger.debug("Using Rust FormIDAnalyzer wrapper (50x speedup potential)")
        return FormIDAnalyzer(yamldata, show_values, db_exists)
    except ImportError as e:
        msg = f"Required Rust module for FormIDAnalyzer not available: {e}. Reinstall CLASSIC."
        raise RuntimeError(msg) from e


def get_plugin_analyzer(yamldata: ClassicScanLogsInfo) -> PluginAnalyzerProtocol:
    """Retrieve the appropriate plugin analyzer.

    Args:
        yamldata: Input data required to initialize the plugin analyzer.

    Returns:
        Any: An instance of the selected plugin analyzer.

    """
    try:
        from ClassicLib.integration.rust.plugin_rust import RustPluginAnalyzer

        logger.debug("Using RustPluginAnalyzer wrapper (30x speedup potential)")
        return RustPluginAnalyzer(yamldata)
    except ImportError as e:
        logger.warning(f"Failed to import RustPluginAnalyzer: {e}")

    from ClassicLib.integration.python.plugin_py import PluginAnalyzer

    logger.debug("Using Python PluginAnalyzer implementation")
    return PluginAnalyzer(yamldata)


def get_record_scanner(yamldata: ClassicScanLogsInfo) -> RecordScannerProtocol:
    """Create and return an appropriate record scanner instance.

    Args:
        yamldata: The YAML data required for scanning records.

    Returns:
        Any: An instance of RustRecordScanner or RecordScanner.

    """
    try:
        from ClassicLib.integration.rust.record_rust import RustRecordScanner

        logger.debug("Using RustRecordScanner wrapper (40x speedup potential)")
        return RustRecordScanner(yamldata)
    except ImportError as e:
        msg = f"Required Rust module for RecordScanner not available: {e}. Reinstall CLASSIC."
        raise RuntimeError(msg) from e


def get_suspect_scanner(yamldata: ClassicScanLogsInfo) -> SuspectScannerProtocol:
    """Return a SuspectScanner instance for scanning the given YAML data.

    Args:
        yamldata: A ClassicScanLogsInfo object containing log information.

    Returns:
        Any: An instance of the SuspectScanner.

    """
    from ClassicLib.integration.rust.suspect_rust import RUST_AVAILABLE, SuspectScanner

    if RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated SuspectScanner (40x speedup potential)")
    else:
        logger.debug("Using Python SuspectScanner implementation")

    return SuspectScanner(yamldata)


def get_settings_validator(yamldata: ClassicScanLogsInfo) -> SettingsValidatorProtocol:
    """Retrieve and return a settings validator instance.

    Args:
        yamldata: An instance of ClassicScanLogsInfo.

    Returns:
        Any: A settings validator instance.

    """
    from ClassicLib.integration.rust.settings_rust import RUST_AVAILABLE, SettingsValidator

    if RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated SettingsValidator")
    else:
        logger.debug("Using Python SettingsScannerFragments implementation")

    return SettingsValidator(yamldata)


def get_gpu_detector() -> GpuDetectorProtocol:
    """Retrieve the GPU detector with automatic Rust or Python fallback.

    Returns:
        Any: The gpu_rust module providing GPU detection capabilities.

    """
    from ClassicLib.integration.rust import gpu_rust

    if gpu_rust.RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated GpuDetector")
    else:
        logger.debug("Using Python GPUDetector implementation")

    return gpu_rust


def get_database_pool(max_connections: int = 10, cache_ttl_seconds: int = 300) -> DatabasePoolProtocol:
    """Retrieve a database connection pool.

    Args:
        max_connections: Maximum number of connections. Defaults to 10.
        cache_ttl_seconds: Cache time-to-live in seconds. Defaults to 300.

    Returns:
        Any: The database pool instance.

    """
    try:
        from ClassicLib.io.database.rust_pool import RustAsyncDatabasePool

        logger.debug("Using Rust DatabasePool (25x speedup)")
        return RustAsyncDatabasePool(max_connections, cache_ttl_seconds)
    except ImportError as e:
        logger.warning(f"Failed to import Rust DatabasePool: {e}")

    from ClassicLib.io.database.async_pool import AsyncDatabasePool

    logger.debug("Using Python AsyncDatabasePool implementation")
    return AsyncDatabasePool(max_connections)


def get_report_generator(yamldata: ClassicScanLogsInfo | None = None) -> ReportGeneratorProtocol:
    """Generate a report generator instance.

    Args:
        yamldata: Optional ClassicScanLogsInfo instance.

    Returns:
        Any: An instance of the chosen report generator.

    """
    try:
        from ClassicLib.integration.rust.report_rust import RustAcceleratedReportGenerator

        logger.debug("Using Rust ReportGenerator (75x speedup potential)")
        return RustAcceleratedReportGenerator(yamldata)
    except (ImportError, AttributeError) as e:
        msg = f"Required Rust module for ReportGenerator not available: {e}. Reinstall CLASSIC."
        raise RuntimeError(msg) from e


def get_mod_detector() -> dict[str, Any]:  # Returns dict of callable functions
    """Fetch appropriate mod detection function implementations.

    Returns:
        dict[str, Any]: A dictionary containing mod detection functions.

    """
    try:
        from ClassicLib.integration.rust.mod_detector_rust import (
            detect_mods_double,
            detect_mods_important,
            detect_mods_single,
        )
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to get Rust mod detector: {e}")
    else:
        logger.debug("Using Rust mod detector functions (35x speedup)")
        return {
            "detect_mods_single": detect_mods_single,
            "detect_mods_double": detect_mods_double,
            "detect_mods_important": detect_mods_important,
        }

    from ClassicLib.integration.python.mod_detector_py import (
        detect_mods_double,
        detect_mods_important,
        detect_mods_single,
    )

    logger.debug("Using Python mod detector implementation")
    return {
        "detect_mods_single": detect_mods_single,
        "detect_mods_double": detect_mods_double,
        "detect_mods_important": detect_mods_important,
    }


def get_orchestrator(
    yamldata: Any,
    fcx_mode: bool,
    show_formid_values: bool,
    formid_db_exists: bool,
    remove_list: tuple[str, ...] | None = None,
) -> OrchestratorProtocol:
    """Return an orchestrator instance for crash log processing and analysis.

    Args:
        yamldata: Configuration data loaded from YAML files.
        fcx_mode: Whether to enable FCX mode.
        show_formid_values: Whether to display FormID hex values.
        formid_db_exists: Whether the FormID database file exists.
        remove_list: Optional tuple of strings to filter. Defaults to None.

    Returns:
        Any: A HybridOrchestrator or OrchestratorCore instance.

    """
    try:
        from ClassicLib.scanning.logs.hybrid_orchestrator import HybridOrchestrator

        logger.debug("Using HybridOrchestrator (Rust-accelerated batch processing, 10-20x speedup)")
        return HybridOrchestrator(
            yamldata=yamldata,
            fcx_mode=fcx_mode,
            show_formid_values=show_formid_values,
            formid_db_exists=formid_db_exists,
            remove_list=remove_list,
        )
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to import HybridOrchestrator: {e}")

    from ClassicLib.scanning.logs.orchestrator_core import OrchestratorCore

    logger.debug("Using Python OrchestratorCore implementation")
    return OrchestratorCore(
        yamldata=yamldata,
        fcx_mode=fcx_mode,
        show_formid_values=show_formid_values,
        formid_db_exists=formid_db_exists,
        remove_list=remove_list,
    )


def get_yamldata() -> Any:  # Returns Rust YamlData or Python ClassicScanLogsInfo (incompatible interfaces)
    """Load YAML data using Rust acceleration if available.

    Returns:
        Any: A YamlData or ClassicScanLogsInfo instance.

    """
    try:
        from classic_config import YamlData

        from ClassicLib.core.registry import get_game, get_vr
        from ClassicLib.support.resources import ResourceLoader

        logger.debug("Using Rust YamlData (15-30x faster YAML loading)")

        data_dir = ResourceLoader.get_data_directory()
        yaml_dirs = [
            str(data_dir.parent),
            str(data_dir),
        ]

        game = get_game()
        vr_mode = get_vr() == "VR"

        return YamlData(yaml_dirs=yaml_dirs, game=game, vr_mode=vr_mode)
    except (ImportError, AttributeError, TypeError, ValueError, OSError) as e:
        logger.warning(f"Failed to initialize Rust YamlData: {e}")

    from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo

    logger.debug("Using Python ClassicScanLogsInfo implementation")
    return ClassicScanLogsInfo()


def get_fcx_handler(fcx_mode: bool | None) -> FCXHandlerProtocol:
    """Determine and return the appropriate FCXModeHandler.

    Args:
        fcx_mode: FCX mode flag (True, False, or None).

    Returns:
        Any: An instance of the appropriate FCXModeHandler.

    """
    from ClassicLib.integration.rust.fcx_rust import RUST_AVAILABLE, FCXModeHandler

    if RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated FcxModeHandler")
    else:
        logger.debug("Using Python FCXModeHandler implementation")

    return FCXModeHandler(fcx_mode)


# ---------------------------------------------------------------------------
# Phase 4 utility factories
# ---------------------------------------------------------------------------


def get_constants() -> Any | None:
    """Retrieve the Rust-based constants module if available.

    Returns:
        Any | None: The classic_constants module if available, None otherwise.

    """
    try:
        import classic_constants
    except ImportError as e:
        logger.warning(f"Failed to import classic_constants: {e}")
    else:
        logger.debug("Using Rust constants module")
        return classic_constants

    logger.debug("Constants module not available")
    return None


def get_version_utils() -> Any | None:
    """Retrieve the Rust-based version utilities module if available.

    Returns:
        Any | None: The classic_version module if available, None otherwise.

    """
    try:
        import classic_version
    except ImportError as e:
        logger.warning(f"Failed to import classic_version: {e}")
    else:
        logger.debug("Using Rust version utilities module")
        return classic_version

    logger.debug("Version utilities module not available")
    return None


def get_resource_mgmt() -> Any | None:
    """Retrieve the Rust-based resource management module if available.

    Returns:
        Any | None: The classic_resource module if available, None otherwise.

    """
    try:
        import classic_resource
    except ImportError as e:
        logger.warning(f"Failed to import classic_resource: {e}")
    else:
        logger.debug("Using Rust resource management module")
        return classic_resource

    logger.debug("Resource management module not available")
    return None


def get_xse_utils() -> Any | None:
    """Retrieve the Rust-based XSE utilities module if available.

    Returns:
        Any | None: The classic_xse module if available, None otherwise.

    """
    try:
        import classic_xse
    except ImportError as e:
        logger.warning(f"Failed to import classic_xse: {e}")
    else:
        logger.debug("Using Rust XSE utilities module")
        return classic_xse

    logger.debug("XSE utilities module not available")
    return None


def get_web_utils() -> Any | None:
    """Retrieve the Rust-based web utilities module if available.

    Returns:
        Any | None: The classic_web module if available, None otherwise.

    """
    try:
        import classic_web
    except ImportError as e:
        logger.warning(f"Failed to import classic_web: {e}")
    else:
        logger.debug("Using Rust web utilities module")
        return classic_web

    logger.debug("Web utilities module not available")
    return None


def get_path_operations() -> Any | None:
    """Retrieve the Rust-based path operations module if available.

    Returns:
        Any | None: The classic_path module if available, None otherwise.

    """
    try:
        import classic_path
    except ImportError as e:
        logger.warning(f"Failed to import classic_path: {e}")
    else:
        logger.debug("Using Rust path operations module (10-50x speedup)")
        return classic_path

    logger.debug("Path operations module not available, using Python fallback")
    return None


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------

# Component key -> (module_name, class_name) mapping for is_rust_accelerated shim
_COMPONENT_KEY_MAP: dict[str, tuple[str, str | None]] = {
    "parser": ("classic_scanlog", "LogParser"),
    "formid_analyzer": ("classic_scanlog", "FormIDAnalyzer"),
    "plugin_analyzer": ("classic_scanlog", "PluginAnalyzer"),
    "record_scanner": ("classic_scanlog", "RecordScanner"),
    "report_generation": ("classic_scanlog", "ReportGenerator"),
    "suspect_scanner": ("classic_scanlog", "SuspectScanner"),
    "settings_validator": ("classic_scanlog", "SettingsValidator"),
    "gpu_detector": ("classic_scanlog", "GpuDetector"),
    "fcx_handler": ("classic_scanlog", "FcxModeHandler"),
    "orchestrator": ("classic_scanlog", "Orchestrator"),
    "mod_detector": ("classic_scanlog", "detect_mods_batch"),
    "database": ("classic_database", None),
    "database_pool": ("classic_database", "DatabasePool"),
    "file_io": ("classic_file_io", None),
    "file_io_core": ("classic_file_io", "FileIOCore"),
    "yaml": ("classic_yaml", None),
    "yaml_operations": ("classic_yaml", "YamlOperations"),
    "path": ("classic_path", None),
    "path_operations": ("classic_path", "PathValidator"),
    "yamldata": ("classic_config", "YamlData"),
    "constants": ("classic_constants", None),
    "version_utils": ("classic_version", None),
    "resource_mgmt": ("classic_resource", None),
    "xse_utils": ("classic_xse", None),
    "web_utils": ("classic_web", None),
    "scangame": ("classic_scangame", None),
    "ba2_scanner": ("classic_scangame", "BA2Scanner"),
    "config_duplicates": ("classic_scangame", "ConfigDuplicateDetector"),
    "unpacked_scanner": ("classic_scangame", "UnpackedScanner"),
    "log_processor": ("classic_scangame", "LogProcessor"),
    "ini_validator": ("classic_scangame", "IniValidator"),
    "crashgen_checker": ("classic_scangame", "CrashgenChecker"),
    "xse_checker": ("classic_scangame", "XseChecker"),
    "integrity_checker": ("classic_scangame", "GameIntegrityChecker"),
}


def is_rust_accelerated(component_name: str) -> bool:
    """Check if a Rust component is available by legacy component key.

    This bridges the old status.py API (keyed by component names like
    "parser") to the new detect_component API. Used by tests and the
    acceleration coordinator (both removed in 02-02).

    Args:
        component_name: Legacy component key (e.g. "parser", "file_io").

    Returns:
        True if the component is available, False otherwise.

    """
    mapping = _COMPONENT_KEY_MAP.get(component_name)
    if mapping is None:
        return False
    module_name, class_name = mapping
    return is_component_available(module_name, class_name)


def get_rust_component_status() -> dict[str, Any]:
    """Get a summary of Rust component availability.

    Provides a compatible replacement for the deleted status.py function.
    Returns a dict with component availability, counts, and acceleration level.

    Returns:
        dict[str, Any]: Status dictionary with availability info.

    """
    components = {key: is_rust_accelerated(key) for key in _COMPONENT_KEY_MAP}
    active_count = sum(1 for v in components.values() if v)
    total_count = len(components)
    percentage = (active_count / total_count * 100) if total_count > 0 else 0

    if percentage >= 90:
        level = "FULLY ACCELERATED"
    elif percentage >= 70:
        level = "HIGHLY ACCELERATED"
    elif percentage >= 30:
        level = "PARTIALLY ACCELERATED"
    elif active_count > 0:
        level = "MINIMAL ACCELERATION"
    else:
        level = "NO ACCELERATION"

    return {
        "available": components,
        "initialized": {},
        "failed": {},
        "performance_gains": {},
        "active_count": active_count,
        "total_count": total_count,
        "percentage": percentage,
        "acceleration_active": active_count > 0,
        "acceleration_level": level,
        "versions": {},
        "disabled": False,
    }


def print_rust_status() -> None:
    """Print a summary of Rust acceleration status.

    Simplified replacement for the deleted status.py function.
    """
    status = get_rust_component_status()
    active = [k for k, v in status["available"].items() if v]
    print(f"Rust acceleration: {len(active)}/{status['total_count']} components ({status['acceleration_level']})")
    if active:
        print(f"  Active: {', '.join(active)}")


__all__ = [
    # Detection utilities
    "detect_component",
    "is_component_available",
    "get_component",
    # Core
    "reset_cache",
    "reset_file_io_singleton",
    # Parsers
    "get_parser",
    "PythonParserWrapper",
    # File I/O
    "get_file_io",
    "get_yaml_operations",
    # Analyzers
    "get_formid_analyzer",
    "get_plugin_analyzer",
    "get_record_scanner",
    "get_suspect_scanner",
    "get_settings_validator",
    "get_gpu_detector",
    # Database
    "get_database_pool",
    # Scanlog
    "get_report_generator",
    "get_mod_detector",
    "get_orchestrator",
    # Game
    "get_yamldata",
    "get_fcx_handler",
    # Utilities
    "get_constants",
    "get_version_utils",
    "get_resource_mgmt",
    "get_xse_utils",
    "get_web_utils",
    "get_path_operations",
    # Backward compatibility (status.py replacements)
    "is_rust_accelerated",
    "get_rust_component_status",
    "print_rust_status",
]
