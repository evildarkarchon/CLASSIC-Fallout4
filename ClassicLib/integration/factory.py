"""
A module that provides methods for dynamically selecting the most efficient
available implementations of various utilities and analyzers, including
Rust and Python-based alternatives.

This module includes functions for selecting file I/O handlers, log parsers,
FormID analyzers, plugin analyzers, record scanners, report generators,
and Phase 4 utility modules (constants, version, resource, XSE, web),
with fallback mechanisms for Python-based implementations.

Classes:
    PythonParserWrapper: A wrapper class for Python-based log parser
    implementations, mimicking the interface of a Rust-based log parser.

Functions:
    get_file_io: Retrieve the best available file I/O implementation.
    get_parser: Retrieve the most efficient log parser implementation available.
    get_formid_analyzer: Retrieve the best available FormID analyzer
    implementation.
    get_plugin_analyzer: Retrieve the most efficient plugin analyzer implementation.
    get_record_scanner: Retrieve the best available record scanner implementation.
    get_report_generator: Retrieve the most efficient report generator
    implementation.
    get_yaml_operations: Retrieve the Rust YAML operations if available.
    get_database_pool: Retrieve the database pool implementation.
    get_mod_detector: Retrieve mod detection functions.
    get_yamldata: Load YAML data with Rust acceleration if available.
    get_suspect_scanner: Retrieve the suspect scanner implementation.
    get_settings_validator: Retrieve the settings validator implementation.
    get_gpu_detector: Retrieve the GPU detector implementation.
    get_fcx_handler: Retrieve the FCX mode handler implementation.
    get_constants: Retrieve the Rust constants module (Phase 4).
    get_version_utils: Retrieve the Rust version utilities module (Phase 4).
    get_resource_mgmt: Retrieve the Rust resource management module (Phase 4).
    get_xse_utils: Retrieve the Rust XSE utilities module (Phase 4).
    get_web_utils: Retrieve the Rust web utilities module (Phase 4).
    get_path_operations: Retrieve the Rust path operations module.
    reset_cache: Reset the component detection cache.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING, Any

from ClassicLib.integration.config import DISABLE_RUST_ENV_VAR
from ClassicLib.integration.detector import detect_rust_components

if TYPE_CHECKING:
    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)

# Cache for component availability to avoid repeated detection
_components_cache: dict[str, bool] | None = None


def _get_components() -> dict[str, bool]:
    """
    Retrieves the status of Rust components and caches the result.

    This function checks if the Rust components have already been detected and
    cached. If not, it calls the `detect_rust_components` function to get the
    status of the available Rust components, stores the result in a global cache,
    and returns it.

    Returns:
        dict[str, bool]: A dictionary where keys represent Rust components as
        strings and values are booleans indicating the presence of those components.
    """
    global _components_cache
    if _components_cache is None:
        _components_cache = detect_rust_components()
    return _components_cache


def _is_rust_disabled() -> bool:
    """
    Determines if Rust features are disabled based on an environment variable.

    This function checks the presence and value of a specific environment
    variable to determine whether Rust features should be disabled. It is
    commonly used to conditionally enable or disable functionality.

    Returns:
        bool: True if Rust features are disabled, False otherwise.
    """
    return os.environ.get(DISABLE_RUST_ENV_VAR, "").lower() in {"1", "true", "yes"}


# Cache for FileIO singleton
_file_io_instance: Any = None
_file_io_lock = threading.Lock()


def get_file_io(encoding: str = "utf-8", errors: str = "ignore") -> Any:
    """
    Retrieves or initializes a global file I/O instance with the specified encoding and error handling
    mode. The function follows a thread-safe singleton pattern to ensure only one instance is created
    and efficiently reused. It attempts to use a Rust-based implementation for improved performance,
    falling back to a Python-based implementation if unavailable.

    Args:
        encoding (str): The text encoding format to be used for file operations. Defaults to "utf-8".
        errors (str): Specifies the error handling mode for encoding/decoding operations. Defaults
            to "ignore".

    Returns:
        Any: A singleton instance of the file I/O implementation that best fits the system's
        configuration.

    Raises:
        ImportError: If the Rust-based file I/O implementation fails to load, though the Python
        implementation is used as a fallback.
    """
    global _file_io_instance

    # Fast path - instance already exists
    if _file_io_instance is not None:
        return _file_io_instance

    # Slow path - need to create instance
    with _file_io_lock:
        # Double-check pattern
        if _file_io_instance is not None:
            return _file_io_instance

        components = _get_components()

        if not _is_rust_disabled() and components.get("file_io_core", False):
            try:
                from ClassicLib.rust.file_io_rust import RustFileIOCore
                logger.debug("Using Rust FileIOCore (10-20x file ops, 30-40x DDS processing)")
                _file_io_instance = RustFileIOCore(encoding, errors)
                return _file_io_instance
            except ImportError as e:
                logger.warning(f"Failed to import Rust FileIOCore: {e}")

        # Fall back to Python implementation
        from ClassicLib.python.file_io_py import FileIOCore
        logger.debug("Using Python FileIOCore implementation")
        _file_io_instance = FileIOCore(encoding, errors)
        return _file_io_instance


def get_parser() -> Any:
    """
    Retrieves an appropriate parser based on the availability of components and configurations.

    This function determines whether to use a Rust-based parser or a Python-based fallback for
    parsing data. It checks the system configuration and availability of the Rust parser and
    falls back to using pure Python implementations if necessary. The returned parser provides
    the same interface regardless of the underlying implementation, ensuring seamless functionality.

    Returns:
        Any: An instance of the parser, which could be a Rust-based or Python-based implementation.

    Raises:
        ImportError: If the Rust parser module fails to import.
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

        def find_segments(
            self,
            crash_data: list[str],
            crashgen_name: str,
            xse_acronym: str,
            game_root_name: str,
        ) -> tuple[str, str, str, list[list[str]]]:
            """
            Finds and retrieves segments information based on the input parameters.

            This method serves as a wrapper for `find_segments` function, facilitating the
            retrieval of segments information relevant to the crash data. It processes the
            provided arguments to facilitate analysis or further processing of the crash
            data associated with specific conditions.

            Args:
                crash_data: List of strings representing lines of crash data.
                crashgen_name: The name of the crash generation process or identifier.
                xse_acronym: Acronym associated with the XSE process specifics.
                game_root_name: Name of the root directory or identifier for the game's context.

            Returns:
                tuple[str, str, str, list[list[str]]]: A tuple containing game_version,
                crashgen_version, main_error, and processed_segments.
            """
            from ClassicLib.python.parser_py import find_segments
            return find_segments(crash_data, crashgen_name, xse_acronym, game_root_name)

        def extract_section(
            self,
            crash_data: list[str],
            start_marker: str,
            end_marker: str,
        ) -> list[str] | None:
            """
            Extracts a specific section of text from the given crash data based on the
            specified start and end markers.

            This method iterates through a list of text lines and collects all lines
            that appear after the start marker and before the end marker. The resulting
            lines are returned as a list. If no matching section is found, the method
            returns None.

            Args:
                crash_data: List of strings representing lines of crash data.
                start_marker: String that marks the start of the desired section.
                end_marker: String that marks the end of the desired section.

            Returns:
                list[str] | None: A list containing lines of the extracted section, or
                None if no valid section is found.
            """
            # Python implementation
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

            return section or None

    return PythonParserWrapper()


def get_formid_analyzer(
    yamldata: ClassicScanLogsInfo,
    show_values: bool,
    db_exists: bool
) -> Any:
    """
    Gets an appropriate FormIDAnalyzer instance based on available components and runtime configuration.

    This function determines whether the Rust-based `RustFormIDAnalyzer` or
    the Python implementation `FormIDAnalyzer` should be used for form ID
    analysis, prioritizing the Rust implementation if it is available and
    Rust-based components are not disabled. This provides potential
    performance benefits. If the Rust implementation is unavailable or fails
    to import, the fallback Python implementation is used.

    Args:
        yamldata (ClassicScanLogsInfo): The YAML data to be analyzed.
        show_values (bool): Flag indicating whether to include values in the analysis.
        db_exists (bool): Flag indicating whether a database exists for reference during analysis.

    Returns:
        Any: An instance of RustFormIDAnalyzer or FormIDAnalyzer, depending on the available
        runtime components.
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
    Retrieves the appropriate plugin analyzer, opting for a Rust-based implementation
    if available and functional, otherwise defaulting to the Python implementation.

    This function attempts to use `RustPluginAnalyzer` for faster performance.
    If the Rust implementation is not available or cannot be imported, it falls back
    to the `PluginAnalyzer` provided in Python. The selection is based on the
    availability of the necessary components and the Rust support status.

    Args:
        yamldata: Input data of type `ClassicScanLogsInfo`, which is required
            to initialize the plugin analyzer.

    Returns:
        Any: An instance of the selected plugin analyzer, either the Rust-based
        `RustPluginAnalyzer` or the Python-based `PluginAnalyzer`.
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
    Creates and returns an appropriate record scanner instance based on the availability
    of components and the current runtime environment. The function prioritizes the
    Rust-based implementation which offers significant performance benefits if available
    and falls back to the Python implementation otherwise.

    Args:
        yamldata (ClassicScanLogsInfo): The YAML data required for scanning and processing
            records.

    Returns:
        Any: An instance of a record scanner (either RustRecordScanner or RecordScanner)
            that can process the given YAML data.

    Raises:
        ImportError: If the Rust-based library is not available when attempting to use
            the Rust implementation.
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
    Generates a report generator instance.

    This function determines the appropriate implementation of the report generator
    to use. It prioritizes the Rust-accelerated version for performance, but if Rust
    support is unavailable or fails to initialize, it falls back to the Python-based
    implementation.

    Args:
        yamldata: An optional ClassicScanLogsInfo instance containing data to initialize
            the report generator. If None, the generator will be created without
            pre-loaded data.

    Returns:
        Any: An instance of the chosen report generator (RustAcceleratedReportGenerator or
        Python ReportGenerator implementations).
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
    return ReportGenerator(yamldata)  # type: ignore[arg-type]


def get_yaml_operations() -> Any:
    """
    Retrieves the appropriate YAML operations implementation.

    This function determines whether to use a Rust-based YAML operations
    implementation for enhanced performance or to fall back to a Python-based
    implementation. If Rust-based operations are available and not disabled,
    they are utilized; otherwise, the Python implementation serves as the
    default.

    Returns:
        Any: An instance of the Rust-based YAML operations class if available
        and enabled, or None if Python implementation is used or if no
        acceleration is available.
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("yaml_operations", False):
        try:
            import classic_yaml
            if hasattr(classic_yaml, "RustYamlOperations"):
                logger.debug("Using Rust YAML Operations (15-30x parsing, 10-20x writing speedup)")
                return classic_yaml.RustYamlOperations()
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to get Rust YAML Operations: {e}")

    # Fall back to Python implementation - return None to indicate no acceleration available
    logger.debug("Using Python YAML implementation (ruamel.yaml)")
    return None


def get_database_pool(max_connections: int = 10, cache_ttl_seconds: int = 300) -> Any:
    """
    Retrieves a database connection pool, either using a Rust-optimized implementation
    or a Python-based fallback.

    The function prioritizes a Rust-based implementation if available, which provides
    significant performance improvements. If the Rust implementation is not available,
    it resorts to using the Python-based fallback mechanism.

    Args:
        max_connections (int): Maximum number of connections allowed to be managed
            by the database pool. Defaults to 10.
        cache_ttl_seconds (int): Time-to-live of the connection cache in seconds.
            Defaults to 300.

    Returns:
        Any: The database pool instance, which can either be RustAsyncDatabasePool
            or AsyncDatabasePool depending on the availability of the Rust module.
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
    Fetches an appropriate mod detection function implementations based on the
    availability of Rust-optimized and Python-based modules. The function first
    attempts to load the Rust-optimized mod detector for improved performance.
    If the Rust module is unavailable or an error occurs during its loading,
    it falls back to the Python implementation.

    Returns:
        dict[str, Any]: A dictionary containing mod detection functions:
            - `detect_mods_single`
            - `detect_mods_double`
            - `detect_mods_important`

    Raises:
        ImportError: If there is an issue importing the mod detection module.
        AttributeError: If there is an issue accessing attributes during module loading.
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("mod_detector", False):
        try:
            from ClassicLib.rust.mod_detector_rust import (
                detect_mods_double,
                detect_mods_important,
                detect_mods_single,
            )
            logger.debug("Using Rust mod detector functions (35x speedup)")
            return {
                "detect_mods_single": detect_mods_single,
                "detect_mods_double": detect_mods_double,
                "detect_mods_important": detect_mods_important,
            }
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to get Rust mod detector: {e}")

    # Fall back to Python implementation
    from ClassicLib.python.mod_detector_py import (
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


def get_yamldata(yaml_dirs: list | None = None, game: str | None = None, is_vr: bool | None = None) -> Any:  # noqa: ARG001
    """
    Loads YAML data depending on the available components and configurations.

    This function attempts to load YAML data using a Rust-based library for faster
    performance if the component is available and Rust is enabled. If Rust is not
    available, it falls back to a Python-based implementation.

    Args:
        yaml_dirs: A list of directories containing YAML files (deprecated, not used).
        game: The name of the game for which data is being loaded (deprecated, not used).
        is_vr: Indicates if the game is in virtual reality mode (deprecated, not used).

    Returns:
        Any: An instance of the YAML data handler, either Rust or Python-based,
        depending on availability.

    Note:
        The yaml_dirs, game, and is_vr parameters are deprecated and no longer used.
        They are kept for backward compatibility but will be removed in a future version.
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("yamldata", False):
        try:
            from classic_config import YamlData
            logger.debug("Using Rust YamlData (15-30x faster YAML loading)")
            # Note: YamlData initialization may have changed - check Rust implementation
            return YamlData()  # type: ignore[call-arg]
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to import Rust YamlData: {e}")

    # Fall back to Python implementation
    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo
    logger.debug("Using Python ClassicScanLogsInfo implementation")
    return ClassicScanLogsInfo()


def get_suspect_scanner(yamldata: ClassicScanLogsInfo) -> Any:
    """
    Returns a SuspectScanner instance suitable for scanning the given YAML data.

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
    from ClassicLib.rust.suspect_rust import RUST_AVAILABLE, SuspectScanner

    if RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated SuspectScanner (40x speedup potential)")
    else:
        logger.debug("Using Python SuspectScanner implementation")

    return SuspectScanner(yamldata)


def get_settings_validator(yamldata: ClassicScanLogsInfo) -> Any:
    """
    Retrieves and returns a settings validator instance.

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
    from ClassicLib.rust.settings_rust import RUST_AVAILABLE, SettingsValidator

    if RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated SettingsValidator")
    else:
        logger.debug("Using Python SettingsScannerFragments implementation")

    return SettingsValidator(yamldata)


def get_gpu_detector() -> Any:
    """
    Retrieves the GPU detector function with automatic Rust or Python fallback.

    This function determines whether the Rust-accelerated GPU detection implementation
    is available. If Rust is available, the Rust-based implementation is used and logged;
    otherwise, the Python-based implementation is used. The returned function provides
    GPU detection capabilities depending on the selected implementation.

    Returns:
        Any: The GPU detection function, automatically selecting between Rust-accelerated
        and Python implementations.
    """
    # Use wrapper that provides get_gpu_info function with automatic Rust/Python fallback
    from ClassicLib.rust import gpu_rust

    if gpu_rust.RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated GpuDetector")
    else:
        logger.debug("Using Python GPUDetector implementation")

    return gpu_rust


def get_fcx_handler(fcx_mode: bool | None) -> Any:
    """
    Determines and returns the appropriate FCXModeHandler based on the provided
    mode and availability of Rust-accelerated functionality.

    The function utilizes a Rust-accelerated implementation if available (`RUST_AVAILABLE`),
    otherwise falls back to the Python implementation. This provides flexibility
    and optimized performance where possible.

    Args:
        fcx_mode (bool | None): Determines the specific mode for the FCXModeHandler.
            Can be `True`, `False`, or `None` to represent different behavior.

    Returns:
        Any: An instance of the appropriate FCXModeHandler (either Python or Rust-based).
    """
    # Use wrapper that handles Rust/Python automatically
    from ClassicLib.rust.fcx_rust import RUST_AVAILABLE, FCXModeHandler

    if RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated FcxModeHandler")
    else:
        logger.debug("Using Python FCXModeHandler implementation")

    return FCXModeHandler(fcx_mode)


def reset_cache() -> None:
    """
    Resets the global components cache.

    This function sets the global `_components_cache` variable to `None` and logs
    a debug message indicating that the component cache has been reset.

    Raises:
        None
    """
    global _components_cache
    _components_cache = None
    logger.debug("Component cache reset")


# ============================================================================
# Phase 4 - Constants and Utilities
# ============================================================================


def get_constants() -> Any | None:
    """
    Retrieves the Rust-based constants module if available.

    This function attempts to import and return the Rust `classic_constants`
    module, which provides game constants, enumerations, and common values
    with high performance. If the module is unavailable or Rust is disabled,
    returns None.

    Returns:
        Any | None: The classic_constants module if available, None otherwise.

    Examples:
        >>> constants = get_constants()
        >>> if constants:
        ...     game = constants.GameId.fallout4()
        ...     print(f"Game: {game.as_str()}")
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("constants", False):
        try:
            import classic_constants
            logger.debug("Using Rust constants module")
            return classic_constants
        except ImportError as e:
            logger.warning(f"Failed to import classic_constants: {e}")

    logger.debug("Constants module not available")
    return None


def get_version_utils() -> Any | None:
    """
    Retrieves the Rust-based version utilities module if available.

    This function attempts to import and return the Rust `classic_version`
    module, which provides fast version parsing, comparison, and extraction
    utilities. If the module is unavailable or Rust is disabled, returns None.

    Returns:
        Any | None: The classic_version module if available, None otherwise.

    Examples:
        >>> version = get_version_utils()
        >>> if version:
        ...     v = version.parse_version("1.10.163")
        ...     print(f"Parsed: {v}")
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("version_utils", False):
        try:
            import classic_version
            logger.debug("Using Rust version utilities module")
            return classic_version
        except ImportError as e:
            logger.warning(f"Failed to import classic_version: {e}")

    logger.debug("Version utilities module not available")
    return None


def get_resource_mgmt() -> Any | None:
    """
    Retrieves the Rust-based resource management module if available.

    This function attempts to import and return the Rust `classic_resource`
    module, which provides fast resource file detection, enumeration, and
    validation. If the module is unavailable or Rust is disabled, returns None.

    Returns:
        Any | None: The classic_resource module if available, None otherwise.

    Examples:
        >>> resource = get_resource_mgmt()
        >>> if resource:
        ...     rt = resource.detect_resource_type("texture.dds")
        ...     print(f"Type: {rt.as_str()}")
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("resource_mgmt", False):
        try:
            import classic_resource
            logger.debug("Using Rust resource management module")
            return classic_resource
        except ImportError as e:
            logger.warning(f"Failed to import classic_resource: {e}")

    logger.debug("Resource management module not available")
    return None


def get_xse_utils() -> Any | None:
    """
    Retrieves the Rust-based XSE utilities module if available.

    This function attempts to import and return the Rust `classic_xse`
    module, which provides Script Extender (XSE) detection, version checking,
    and status information for F4SE, SKSE, SFSE, and their VR variants. If the
    module is unavailable or Rust is disabled, returns None.

    Returns:
        Any | None: The classic_xse module if available, None otherwise.

    Examples:
        >>> xse = get_xse_utils()
        >>> if xse:
        ...     info = xse.get_xse_info("C:/Games/Fallout4", xse.XseType.f4se())
        ...     print(f"F4SE installed: {info.installed()}")
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("xse_utils", False):
        try:
            import classic_xse
            logger.debug("Using Rust XSE utilities module")
            return classic_xse
        except ImportError as e:
            logger.warning(f"Failed to import classic_xse: {e}")

    logger.debug("XSE utilities module not available")
    return None


def get_web_utils() -> Any | None:
    """
    Retrieves the Rust-based web utilities module if available.

    This function attempts to import and return the Rust `classic_web`
    module, which provides URL validation, user agent generation, and
    mod site constants. If the module is unavailable or Rust is disabled,
    returns None.

    Returns:
        Any | None: The classic_web module if available, None otherwise.

    Examples:
        >>> web = get_web_utils()
        >>> if web:
        ...     ua = web.get_user_agent()
        ...     print(f"User agent: {ua}")
        ...     valid = web.is_valid_url("https://www.nexusmods.com")
        ...     print(f"Valid URL: {valid}")
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("web_utils", False):
        try:
            import classic_web
            logger.debug("Using Rust web utilities module")
            return classic_web
        except ImportError as e:
            logger.warning(f"Failed to import classic_web: {e}")

    logger.debug("Web utilities module not available")
    return None


def get_path_operations() -> Any | None:
    """
    Retrieves the Rust-based path operations module if available.

    This function attempts to import and return the Rust `classic_path`
    module, which provides high-performance path validation, game path
    detection, registry queries, and XSE log parsing. If the module is
    unavailable or Rust is disabled, returns None for fallback to Python
    implementations in GamePath, DocsPath, and PathValidator modules.

    **Performance**: Rust acceleration provides 10-50x speedup for:
    - Windows registry queries for game paths
    - Path validation and existence checks
    - XSE log parsing for game detection
    - File system operations

    Returns:
        Any | None: The classic_path module if available, None otherwise.
            Calling code should check for None and use Python fallback.

    Examples:
        >>> path_ops = get_path_operations()
        >>> if path_ops:
        ...     # Use Rust acceleration
        ...     finder = path_ops.GamePathFinder(exe_name, xse_loader, game, is_vr)
        ...     path = finder.find_game_path(cached_path, xse_log_path)
        ... else:
        ...     # Use Python fallback
        ...     path = _python_find_game_path()
    """
    components = _get_components()

    if not _is_rust_disabled() and components.get("path_operations", False):
        try:
            import classic_path
            logger.debug("Using Rust path operations module (10-50x speedup)")
            return classic_path
        except ImportError as e:
            logger.warning(f"Failed to import classic_path: {e}")

    logger.debug("Path operations module not available, using Python fallback")
    return None
