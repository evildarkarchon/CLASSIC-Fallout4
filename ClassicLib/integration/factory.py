"""Factory module for required Rust implementation loading.

Provides factory functions that resolve mandatory Rust bindings for each
component. CLASSIC no longer supports Python fallback execution paths.

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
    get_xse_checker: XSE Address Library checker factory.
    get_wrye_parser: Wrye Bash report parser factory.
    get_crashgen_orchestrator: Crash generator orchestrator factory.
    get_config_file_cache: Rust ConfigFileCache factory.
    get_mod_ini_scanner: Rust ModIniScanner factory.
    get_game_scan_orchestrator: Rust GameScanOrchestrator factory.
    get_game_scan_config: Rust GameScanConfig factory.
    get_dds_analyzer: Rust DDSAnalyzer factory.
    get_scan_report_builder: Rust scan report builder functions factory.
    get_papyrus_analyzer: Papyrus log analyzer factory.
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
import types
from typing import TYPE_CHECKING, Any, cast

from ClassicLib.integration.exceptions import (
    RustBindingError,
    RustBindingImportError,
    RustBindingInitError,
    get_rust_rebuild_remediation,
)
from ClassicLib.integration.factory_internal.detection import detect_component as _detect_component
from ClassicLib.integration.factory_internal.detection import (
    get_binding_contract as _get_binding_contract,
)
from ClassicLib.integration.factory_internal.detection import (
    get_component as _get_component,
)
from ClassicLib.integration.factory_internal.detection import (
    validate_rust_modules as _validate_rust_modules,
)
from ClassicLib.integration.factory_internal.logging_contract import (
    EVENT_STARTUP_BINDING_CONTRACT_FAILED,
    EVENT_STARTUP_BINDING_CONTRACT_VALIDATED,
    format_contract_event,
)
from ClassicLib.integration.factory_internal.status import (
    COMPONENT_KEY_MAP,
    compute_rust_component_status,
)
from ClassicLib.integration.factory_internal.wrappers import FcxHandlerWrapper
from ClassicLib.integration.factory_internal.wrappers import (
    SettingsValidatorWrapper as _SettingsValidatorWrapper,
)
from ClassicLib.integration.factory_internal.wrappers import (
    SuspectScannerWrapper as _SuspectScannerWrapper,
)

if TYPE_CHECKING:
    from ClassicLib.integration.types import (
        DatabasePoolProtocol,
        FCXHandlerProtocol,
        FileIOProtocol,
        FormIDAnalyzerProtocol,
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
# Startup validation
# ---------------------------------------------------------------------------


def validate_rust_modules(contract: str = "startup_all") -> None:
    """Validate a required Rust binding contract at startup.

    Checks each required Rust native module and raises a clear error if any
    are missing. Call this early in both GUI and CLI entry points to provide
    a user-friendly error message instead of a confusing ImportError later.

    Raises:
        RuntimeError: If any required Rust module is not available, with a
            message identifying the missing module and suggesting reinstallation.

    Example:
        >>> from ClassicLib.integration.factory import validate_rust_modules
        >>> validate_rust_modules()  # Raises RuntimeError if modules missing

    """
    try:
        _validate_rust_modules(contract)
    except RustBindingError as error:
        logger.error(
            format_contract_event(
                component="integration.startup",
                event=EVENT_STARTUP_BINDING_CONTRACT_FAILED,
                severity="error",
                outcome="failure",
                context={
                    "contract": contract,
                    "missing_binding": error.binding,
                    "failure_type": error.failure_type,
                    "failure_hint": get_rust_rebuild_remediation(),
                    "error": error.details,
                },
            )
        )
        raise

    logger.info(
        format_contract_event(
            component="integration.startup",
            event=EVENT_STARTUP_BINDING_CONTRACT_VALIDATED,
            severity="info",
            outcome="success",
            context={
                "contract": contract,
                "checked_bindings": len(_get_binding_contract(contract)),
            },
        )
    )


def get_binding_contract(contract: str = "startup_all") -> list[tuple[str, str | None]]:
    """Return named startup binding contracts used by entrypoints."""
    return _get_binding_contract(contract)


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
    return _detect_component(module_name, class_name)


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


def get_component(module_name: str, class_name: str | None = None) -> Any:
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
    return _get_component(module_name, class_name)


# ---------------------------------------------------------------------------
# FileIO singleton state
# ---------------------------------------------------------------------------

_file_io_instance: Any = None
_file_io_lock = threading.Lock()


def reset_file_io_singleton() -> None:
    """Reset the FileIO singleton instance (for test isolation)."""
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
    """Retrieve the Rust-accelerated log parser implementation.

    Returns:
        Any: A parser instance providing find_segments() and extract_section().

    Raises:
        RuntimeError: If Rust parser module is not available.

    """
    from ClassicLib.integration.rust.parser_rust import RustLogParser

    logger.debug("Using RustLogParser wrapper (150x speedup potential)")
    return cast("LogParserProtocol", RustLogParser())


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

    if _file_io_instance is not None:
        return _file_io_instance

    with _file_io_lock:
        if _file_io_instance is not None:
            return _file_io_instance

        from ClassicLib.integration.rust.file_io_rust import FileIOCore

        logger.debug("Using Rust FileIOCore (10-20x file ops, 30-40x DDS processing)")
        _file_io_instance = FileIOCore(encoding, errors)
        return _file_io_instance


def get_yaml_operations() -> YamlOperationsProtocol:
    """Retrieve required Rust YAML operations implementation."""
    try:
        YamlOperations = get_component("classic_yaml", "YamlOperations")
        logger.debug("Using Rust YAML Operations")
        return YamlOperations()
    except (RustBindingImportError, RustBindingInitError):
        raise
    except Exception as exc:
        raise RustBindingInitError("classic_yaml.YamlOperations", str(exc)) from exc


def get_formid_analyzer(yamldata: ClassicScanLogsInfo, show_values: bool, db_exists: bool) -> FormIDAnalyzerProtocol:
    """Get an appropriate FormIDAnalyzer instance.

    Args:
        yamldata: The YAML data to be analyzed.
        show_values: Whether to include values in the analysis.
        db_exists: Whether a database exists for reference.

    Returns:
        Any: An instance of RustFormIDAnalyzer or FormIDAnalyzer.

    """
    from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer

    logger.debug("Using Rust FormIDAnalyzer wrapper (50x speedup potential)")
    return FormIDAnalyzer(yamldata, show_values, db_exists)


def get_plugin_analyzer(yamldata: ClassicScanLogsInfo) -> PluginAnalyzerProtocol:
    """Retrieve the appropriate plugin analyzer.

    Args:
        yamldata: Input data required to initialize the plugin analyzer.

    Returns:
        Any: An instance of the selected plugin analyzer.

    """
    from ClassicLib.integration.rust.plugin_rust import RustPluginAnalyzer

    logger.debug("Using RustPluginAnalyzer wrapper (30x speedup potential)")
    return RustPluginAnalyzer(yamldata)


def get_record_scanner(yamldata: ClassicScanLogsInfo) -> RecordScannerProtocol:
    """Create and return an appropriate record scanner instance.

    Args:
        yamldata: The YAML data required for scanning records.

    Returns:
        Any: An instance of RustRecordScanner or RecordScanner.

    """
    from ClassicLib.integration.rust.record_rust import RustRecordScanner

    logger.debug("Using RustRecordScanner wrapper (40x speedup potential)")
    return RustRecordScanner(yamldata)


def get_suspect_scanner(yamldata: ClassicScanLogsInfo) -> SuspectScannerProtocol:
    """Return a SuspectScanner wrapper for the given yamldata.

    This function extracts suspects lists from yamldata and constructs
    a Rust SuspectScanner. The returned wrapper converts Rust list[str]
    returns to Python ReportFragment for API compatibility.

    Args:
        yamldata: A ClassicScanLogsInfo object containing log information.

    Returns:
        SuspectScannerProtocol: A wrapper around Rust SuspectScanner.

    Raises:
        RuntimeError: If Rust SuspectScanner module is not available.

    """
    import json

    from classic_scanlog import SuspectScanner as RustSuspectScanner

    # Extract suspects lists from yamldata for Rust constructor
    suspects_error_list = getattr(yamldata, "suspects_error_list", {})
    raw_stack_list = getattr(yamldata, "suspects_stack_list", {})

    # Rust expects Dict[String, List[String]], convert inner dicts to JSON strings
    suspects_stack_list = {}
    for k, v in raw_stack_list.items():
        if isinstance(v, list):
            suspects_stack_list[k] = [json.dumps(item) if isinstance(item, dict) else str(item) for item in v]
        else:
            suspects_stack_list[k] = v

    rust_scanner = RustSuspectScanner(suspects_error_list, suspects_stack_list)
    logger.debug("Using Rust-accelerated SuspectScanner (40x speedup potential)")

    # Return wrapper that handles ReportFragment conversion
    return _SuspectScannerWrapper(rust_scanner)


def _normalize_crashgen_name(name: str) -> str:
    """Normalize a crashgen name for robust matching."""
    return "".join(ch for ch in name if not ch.isspace()).lower()


def _coerce_ignore_keys(raw_ignore_keys: Any) -> list[str]:
    """Convert registry ignore_keys data to a normalized list[str]."""
    if not isinstance(raw_ignore_keys, (list, tuple, set)):
        return []

    ignore_keys: list[str] = []
    seen: set[str] = set()
    for item in raw_ignore_keys:
        if not isinstance(item, str):
            continue
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ignore_keys.append(key)
    return ignore_keys


def _resolve_crashgen_name_for_settings(yamldata: ClassicScanLogsInfo) -> str:
    """Resolve crashgen name with Version Registry fallback."""
    crashgen_name = getattr(yamldata, "crashgen_name", "")
    if isinstance(crashgen_name, str) and crashgen_name.strip():
        return crashgen_name

    from ClassicLib.core.registry import get_game, is_vr_version
    from ClassicLib.support.versions import get_detected_version_info, get_version_registry

    version_info = get_detected_version_info()
    if version_info is None:
        registry = get_version_registry()
        candidates = registry.get_all_for_game(get_game(), is_vr_version())
        if candidates:
            version_info = candidates[0]

    if version_info is not None and version_info.crashgen_versions:
        crashgen_config = version_info.crashgen_versions[0]
        if crashgen_config.name:
            return crashgen_config.name

    return "Buffout 4"


def _extract_crashgen_ignore_keys_from_registry(yamldata: ClassicScanLogsInfo, crashgen_name: str) -> list[str]:
    """Resolve ignore keys from Crashgen_Registry for the selected crashgen."""
    crashgen_registry = getattr(yamldata, "crashgen_registry", None)
    if not isinstance(crashgen_registry, dict):
        return []

    normalized_target = _normalize_crashgen_name(crashgen_name)
    default_entry: dict[str, Any] | None = None
    prefix_match_ignore_keys: list[str] = []
    prefix_match_len = -1

    for entry_name, entry in crashgen_registry.items():
        if not isinstance(entry_name, str) or not isinstance(entry, dict):
            continue

        if entry_name.strip().lower() == "default":
            default_entry = entry
            continue

        normalized_entry = _normalize_crashgen_name(entry_name)
        if normalized_entry == normalized_target:
            return _coerce_ignore_keys(entry.get("ignore_keys"))

        # Allow "Buffout 4" registry entries to match names like "Buffout 4 NG".
        if normalized_entry and normalized_target.startswith(normalized_entry) and len(normalized_entry) > prefix_match_len:
            prefix_match_ignore_keys = _coerce_ignore_keys(entry.get("ignore_keys"))
            prefix_match_len = len(normalized_entry)

    if prefix_match_len >= 0:
        return prefix_match_ignore_keys

    if default_entry is not None:
        return _coerce_ignore_keys(default_entry.get("ignore_keys"))

    return []


def get_settings_validator(yamldata: ClassicScanLogsInfo) -> SettingsValidatorProtocol:
    """Return a SettingsValidator wrapper for the given yamldata.

    This function resolves crashgen_name (with Version Registry fallback),
    then reads ignore keys from the per-crashgen `Crashgen_Registry`
    configuration and constructs a Rust SettingsValidator. The returned
    wrapper converts dict values to strings (for Rust) and Rust list[str]
    returns to ReportFragment.

    Args:
        yamldata: An instance of ClassicScanLogsInfo.

    Returns:
        SettingsValidatorProtocol: A wrapper around Rust SettingsValidator.

    Raises:
        RuntimeError: If Rust SettingsValidator module is not available.

    """
    from classic_scanlog import SettingsValidator as RustSettingsValidator

    crashgen_name = _resolve_crashgen_name_for_settings(yamldata)
    crashgen_ignore = _extract_crashgen_ignore_keys_from_registry(yamldata, crashgen_name)

    rust_validator = RustSettingsValidator(crashgen_name, crashgen_ignore)
    logger.debug("Using Rust-accelerated SettingsValidator (%d ignore keys)", len(crashgen_ignore))

    return _SettingsValidatorWrapper(rust_validator)


def get_gpu_detector() -> types.SimpleNamespace:
    """Return GPU detector with get_gpu_info function.

    Returns a namespace with get_gpu_info(segment_system) -> dict function.

    Returns:
        types.SimpleNamespace: Namespace with get_gpu_info function.

    Raises:
        RuntimeError: If Rust GpuDetector module is not available.

    """
    from classic_scanlog import GpuDetector as RustGpuDetector

    def get_gpu_info(segment_system: list[str]) -> dict[str, str | None]:
        detector = RustGpuDetector()
        gpu_info = detector.extract_gpu_info(segment_system)
        return gpu_info.to_dict()

    logger.debug("Using Rust-accelerated GpuDetector")
    return types.SimpleNamespace(get_gpu_info=get_gpu_info)


def get_database_pool(
    max_connections: int = 10,
    cache_ttl_seconds: int = 300,
    cache_capacity: int | None = None,
    cleanup_threshold: int | None = None,
    cleanup_interval_seconds: int | None = None,
) -> DatabasePoolProtocol:
    """Retrieve a database connection pool.

    Args:
        max_connections: Global connection budget across active DB files. Defaults to 10.
        cache_ttl_seconds: Cache time-to-live in seconds. Defaults to 300.
        cache_capacity: Optional maximum number of cache entries.
        cleanup_threshold: Optional proactive cleanup threshold (operation count).
        cleanup_interval_seconds: Optional proactive cleanup interval in seconds.

    Returns:
        Any: The database pool instance.

    """
    from ClassicLib.io.database.rust_pool import RustAsyncDatabasePool

    logger.debug("Using Rust DatabasePool")
    return RustAsyncDatabasePool(
        max_connections=max_connections,
        cache_ttl_seconds=cache_ttl_seconds,
        cache_capacity=cache_capacity,
        cleanup_threshold=cleanup_threshold,
        cleanup_interval_seconds=cleanup_interval_seconds,
    )


def get_report_generator(yamldata: ClassicScanLogsInfo | None = None) -> ReportGeneratorProtocol:
    """Generate a report generator instance.

    Args:
        yamldata: Optional ClassicScanLogsInfo instance.

    Returns:
        Any: An instance of the chosen report generator.

    """
    from ClassicLib.integration.rust.report_rust import RustAcceleratedReportGenerator

    logger.debug("Using Rust ReportGenerator (75x speedup potential)")
    return RustAcceleratedReportGenerator(yamldata)


def get_mod_detector() -> dict[str, Any]:  # Returns dict of callable functions
    """Fetch appropriate mod detection function implementations.

    Returns:
        dict[str, Any]: A dictionary containing mod detection functions.

    """
    from ClassicLib.integration.rust.mod_detector_rust import (
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


def get_orchestrator(
    yamldata: Any = None,  # noqa: ARG001 - kept for API compatibility
    fcx_mode: bool = False,  # noqa: ARG001 - kept for API compatibility
    show_formid_values: bool = False,  # noqa: ARG001 - kept for API compatibility
    formid_db_exists: bool = False,  # noqa: ARG001 - kept for API compatibility
    remove_list: tuple[str, ...] | None = None,  # noqa: ARG001 - kept for API compatibility
) -> OrchestratorProtocol:
    """Return a Rust orchestrator instance for crash log processing and analysis.

    Phase 9: Returns Rust Orchestrator directly via ClassicOrchestrator wrapper.
    No Python fallback - Rust is required.

    Args:
        yamldata: Ignored - configuration loaded from Rust YamlData.
        fcx_mode: Ignored - read from settings.
        show_formid_values: Ignored - read from settings.
        formid_db_exists: Ignored - detected automatically.
        remove_list: Ignored - read from settings.

    Returns:
        ClassicOrchestrator: Rust-accelerated orchestrator instance.

    Raises:
        RuntimeError: If Rust orchestrator module is not available.

    """
    from ClassicLib.integration.rust.orchestrator_api import ClassicOrchestrator

    logger.debug("Using Rust Orchestrator (10-150x speedup)")
    return ClassicOrchestrator()  # type: ignore[return-value]


def get_yamldata() -> Any:
    """Load YAML data using required Rust YamlData."""
    YamlData = get_component("classic_config", "YamlData")

    from ClassicLib.core.registry import get_game, get_vr
    from ClassicLib.support.resources import ResourceLoader

    logger.debug("Using Rust YamlData")
    data_dir = ResourceLoader.get_data_directory()
    yaml_dirs = [str(data_dir.parent), str(data_dir)]
    game = get_game()
    vr_mode = get_vr() == "VR"
    return YamlData(yaml_dirs=yaml_dirs, game=game, vr_mode=vr_mode)


def get_fcx_handler(fcx_mode: bool | None) -> FCXHandlerProtocol:
    """Return FCXModeHandler wrapper for the given mode.

    Converts None to False for Rust constructor and wraps to convert
    Rust list[str] returns to ReportFragment.

    Args:
        fcx_mode: FCX mode flag (True, False, or None).

    Returns:
        FCXHandlerProtocol: A wrapper around Rust FcxModeHandler.

    Raises:
        RuntimeError: If Rust FcxModeHandler module is not available.

    """
    from classic_scanlog import FcxModeHandler as RustFcxModeHandler

    # Rust doesn't accept None, convert to False
    rust_fcx_mode = fcx_mode if fcx_mode is not None else False
    rust_handler = RustFcxModeHandler(rust_fcx_mode)

    logger.debug("Using Rust-accelerated FcxModeHandler")
    return FcxHandlerWrapper(rust_handler, fcx_mode)


# ---------------------------------------------------------------------------
# Phase 4 utility factories
# ---------------------------------------------------------------------------


def get_xse_checker(plugins_path: Any, is_vr_mode: bool = False, game_version: str = "Original") -> Any:
    """Retrieve a Rust XseChecker instance for Address Library validation.

    Args:
        plugins_path: Path to the F4SE/SKSE plugins directory.
        is_vr_mode: Whether the game is running in VR mode.
        game_version: Game version name ('Null', 'Original', 'NextGen',
            'AnniversaryEdition', 'Vr').

    Returns:
        Any: An XseChecker instance from the Rust classic_scangame module.

    """
    from classic_scangame import GameVersion as RustGameVersion
    from classic_scangame import XseChecker

    rust_game_version = getattr(RustGameVersion, game_version, RustGameVersion.Original)
    logger.debug("Using Rust XseChecker for Address Library validation")
    return XseChecker(plugins_path, is_vr_mode, rust_game_version)


def get_wrye_parser(wrye_warnings: dict[str, str] | None = None) -> Any:
    """Retrieve a Rust WryeBashParser instance for Wrye Bash report parsing.

    Args:
        wrye_warnings: Warning messages keyed by section title substring.
            If None, an empty dict is used.

    Returns:
        Any: A WryeBashParser instance from the Rust classic_scangame module.

    """
    WryeBashParser = get_component("classic_scangame", "WryeBashParser")

    logger.debug("Using Rust WryeBashParser for Wrye Bash report parsing")
    return WryeBashParser(wrye_warnings)


def get_crashgen_orchestrator() -> Any:
    """Retrieve the Rust CrashgenCheckOrchestrator class.

    Returns:
        Any: The CrashgenCheckOrchestrator class from Rust classic_scangame.
            Call CrashgenCheckOrchestrator.check(path, name) for full validation.

    """
    CrashgenCheckOrchestrator = get_component("classic_scangame", "CrashgenCheckOrchestrator")

    logger.debug("Using Rust CrashgenCheckOrchestrator for crashgen validation")
    return CrashgenCheckOrchestrator


def get_config_file_cache(game_root: Any, duplicate_whitelist: list[str] | None = None) -> Any:
    """Retrieve a Rust ConfigFileCache instance for INI/CONF file scanning.

    Args:
        game_root: Path to the game root directory.
        duplicate_whitelist: Optional list of directory/filename prefixes for duplicate detection.

    Returns:
        Any: A RustConfigFileCache instance from the Rust classic_scangame module.

    """
    RustConfigFileCache = get_component("classic_scangame", "RustConfigFileCache")

    logger.debug("Using Rust ConfigFileCache for INI/CONF file scanning")
    return RustConfigFileCache(game_root, duplicate_whitelist)


def get_mod_ini_scanner() -> Any:
    """Retrieve the Rust ModIniScanner class for mod INI scanning.

    Returns:
        Any: The RustModIniScanner class from Rust classic_scangame.
            Call RustModIniScanner.scan(game_root, game_name) to scan.

    """
    RustModIniScanner = get_component("classic_scangame", "RustModIniScanner")

    logger.debug("Using Rust ModIniScanner for mod INI scanning")
    return RustModIniScanner


def get_game_scan_orchestrator(config: Any) -> Any:
    """Retrieve a Rust GameScanOrchestrator instance.

    Args:
        config: A PyGameScanConfig instance from classic_scangame.

    Returns:
        Any: A GameScanOrchestrator instance from Rust classic_scangame.

    """
    GameScanOrchestrator = get_component("classic_scangame", "GameScanOrchestrator")

    logger.debug("Using Rust GameScanOrchestrator for game integrity scanning")
    return GameScanOrchestrator(config)


def get_game_scan_config(**kwargs: Any) -> Any:
    """Retrieve a Rust GameScanConfig instance.

    Accepts the same keyword arguments as the Rust GameScanConfig constructor.

    Returns:
        Any: A GameScanConfig instance from Rust classic_scangame.

    """
    GameScanConfig = get_component("classic_scangame", "GameScanConfig")

    return GameScanConfig(**kwargs)


def get_dds_analyzer(game_target: str = "fallout4") -> Any:
    """Retrieve a Rust DDSAnalyzer instance for DDS texture validation.

    Args:
        game_target: Game to validate against ("fallout4" or "skyrimse").

    Returns:
        Any: A DDSAnalyzer instance from Rust classic_file_io.

    """
    DDSAnalyzer = get_component("classic_file_io", "DDSAnalyzer")

    logger.debug("Using Rust DDSAnalyzer for DDS texture validation")
    return DDSAnalyzer(game_target)


def get_scan_report_builder() -> Any:
    """Retrieve Rust scan report building functions.

    Returns:
        Any: A module-like namespace with build_unpacked_report,
            build_archived_report, build_combined_scan_report,
            get_scan_issue_messages.

    """
    import classic_scangame

    logger.debug("Using Rust ScanReportBuilder functions")
    return classic_scangame


def get_papyrus_analyzer(log_path: Any = None) -> Any:
    """Retrieve a Rust PapyrusAnalyzer instance for Papyrus log analysis.

    Args:
        log_path: Path to the Papyrus log file. If None, must be set later.

    Returns:
        Any: A PapyrusAnalyzer instance from the Rust classic_scanlog module.

    Raises:
        RuntimeError: If Rust PapyrusAnalyzer module is not available.

    """
    from classic_scanlog import PapyrusAnalyzer

    logger.debug("Using Rust PapyrusAnalyzer (15-30x speedup)")
    if log_path is not None:
        return PapyrusAnalyzer(log_path)
    msg = "log_path is required for PapyrusAnalyzer"
    raise ValueError(msg)


def get_constants() -> Any:
    """Retrieve required Rust constants module."""
    constants = get_component("classic_constants")
    logger.debug("Using Rust constants module")
    return constants


def get_version_utils() -> Any:
    """Retrieve required Rust version utilities module."""
    version = get_component("classic_version")
    logger.debug("Using Rust version utilities module")
    return version


def get_resource_mgmt() -> Any:
    """Retrieve required Rust resource management module."""
    resource = get_component("classic_resource")
    logger.debug("Using Rust resource management module")
    return resource


def get_xse_utils() -> Any:
    """Retrieve required Rust XSE utilities module."""
    xse = get_component("classic_xse")
    logger.debug("Using Rust XSE utilities module")
    return xse


def get_web_utils() -> Any:
    """Retrieve required Rust web utilities module."""
    web = get_component("classic_web")
    logger.debug("Using Rust web utilities module")
    return web


def get_path_operations() -> types.ModuleType:
    """Retrieve the Rust-based path operations module (required).

    The classic_path module is required for game path detection.
    ImportError propagates if the module is not available.

    Returns:
        ModuleType: The classic_path module.

    Raises:
        ImportError: If classic_path module is not available.
            This indicates the Rust module was not built or installed.

    """
    import classic_path

    logger.debug("Using Rust path operations module (10-50x speedup)")
    return classic_path


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


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
    mapping = COMPONENT_KEY_MAP.get(component_name)
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
    components = {key: is_rust_accelerated(key) for key in COMPONENT_KEY_MAP}
    return compute_rust_component_status(components)


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
    # Startup validation
    "validate_rust_modules",
    "get_binding_contract",
    # Detection utilities
    "detect_component",
    "is_component_available",
    "get_component",
    # Core
    "reset_cache",
    "reset_file_io_singleton",
    # Parsers
    "get_parser",
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
    # XSE
    "get_xse_checker",
    # Wrye Bash
    "get_wrye_parser",
    # Crashgen
    "get_crashgen_orchestrator",
    # Config cache / Mod INI
    "get_config_file_cache",
    "get_mod_ini_scanner",
    # Game Scan Orchestrator
    "get_game_scan_orchestrator",
    "get_game_scan_config",
    # DDS
    "get_dds_analyzer",
    # Scan Report
    "get_scan_report_builder",
    # Papyrus
    "get_papyrus_analyzer",
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
