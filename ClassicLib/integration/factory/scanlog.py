"""Scanlog factory functions.

Provides factory functions for crash log scanning and reporting,
selecting between Rust and Python implementations.

Functions:
    get_report_generator: Retrieve the most efficient report generator.
    get_mod_detector: Retrieve mod detection functions.
    get_orchestrator: Retrieve the crash log orchestrator.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ClassicLib.integration.factory.core import get_components, is_rust_disabled

if TYPE_CHECKING:
    from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)


def get_report_generator(yamldata: ClassicScanLogsInfo | None = None) -> Any:
    """Generate a report generator instance.

    This function determines the appropriate implementation of the report generator
    to use. It prioritizes the Rust-accelerated version for performance, but if Rust
    support is unavailable or fails to initialize, it falls back to the Python-based
    implementation.

    Args:
        yamldata: An optional ClassicScanLogsInfo instance containing data to
            initialize the report generator. If None, the generator will be
            created without pre-loaded data.

    Returns:
        Any: An instance of the chosen report generator (RustAcceleratedReportGenerator
        or Python ReportGenerator implementations).

    """
    components = get_components()

    if not is_rust_disabled() and components.get("report_generation", False):
        try:
            # Try to import Rust report generator wrapper
            from ClassicLib.integration.rust.report_rust import RustAcceleratedReportGenerator

            logger.debug("Using Rust ReportGenerator (75x speedup potential)")
            return RustAcceleratedReportGenerator(yamldata)
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to get Rust ReportGenerator: {e}")

    # Fall back to Python implementation
    from ClassicLib.integration.python.report_py import ReportGenerator

    logger.debug("Using Python report generator implementation")
    return ReportGenerator(yamldata)  # type: ignore[arg-type]


def get_mod_detector() -> dict[str, Any]:
    """Fetch appropriate mod detection function implementations.

    The function first attempts to load the Rust-optimized mod detector for
    improved performance. If the Rust module is unavailable or an error occurs
    during its loading, it falls back to the Python implementation.

    Returns:
        dict[str, Any]: A dictionary containing mod detection functions:
            - `detect_mods_single`
            - `detect_mods_double`
            - `detect_mods_important`

    Raises:
        ImportError: If there is an issue importing the mod detection module.
        AttributeError: If there is an issue accessing attributes during module
            loading.

    """
    components = get_components()

    if not is_rust_disabled() and components.get("mod_detector", False):
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
    # Fall back to Python implementation
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
) -> Any:
    """Return an orchestrator instance for crash log processing and analysis.

    This function provides a hybrid orchestrator that uses both Python and Rust
    implementations to maximize performance. The hybrid approach uses:
    - Python OrchestratorCore for single-log processing (complex analysis logic)
    - Rust ClassicOrchestrator for batch processing (10-20x speedup via parallelism)

    The factory automatically detects Rust availability and provides graceful
    degradation to pure Python when Rust components are unavailable.

    Args:
        yamldata: Configuration data loaded from YAML files (ClassicScanLogsInfo
            or YamlData instance).
        fcx_mode: Whether to enable FCX (File Configuration eXtender) mode for
            detecting configuration issues in game INI files.
        show_formid_values: Whether to display FormID hexadecimal values in the
            generated analysis reports.
        formid_db_exists: Whether the FormID database file exists and can be
            used for FormID-to-plugin resolution.
        remove_list: Optional tuple of strings to filter out during processing.
            Defaults to None.

    Returns:
        Any: A HybridOrchestrator instance if Rust is available for batch
        processing, otherwise a pure Python OrchestratorCore instance.
        Both provide the same async interface:
        - async with orchestrator: context manager for resource management
        - async process_crash_log(path): process single log
        - async process_crash_logs_batch(paths): process multiple logs

    Performance:
        - Single log: Uses Python (same performance as OrchestratorCore)
        - Batch (5+ logs): Uses Rust if available (10-20x speedup)
        - Small batches (1-4 logs): Uses Python (avoid Rust overhead)

    Example:
        >>> yamldata = get_yamldata()
        >>> orch = get_orchestrator(
        ...     yamldata=yamldata,
        ...     fcx_mode=False,
        ...     show_formid_values=True,
        ...     formid_db_exists=True
        ... )
        >>> async with orch:
        ...     # Process single log
        ...     result = await orch.process_crash_log(Path("crash.log"))
        ...
        ...     # Process batch with Rust acceleration
        ...     results = await orch.process_crash_logs_batch(log_paths)

    Note:
        The HybridOrchestrator maintains full backward compatibility with
        OrchestratorCore. Existing code can switch to the factory without
        any changes to the calling code.

    """
    components = get_components()

    # Check if Rust orchestrator is available for batch processing
    if not is_rust_disabled() and components.get("orchestrator", False):
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

    # Fall back to pure Python orchestrator
    from ClassicLib.scanning.logs.orchestrator_core import OrchestratorCore

    logger.debug("Using Python OrchestratorCore implementation")
    return OrchestratorCore(
        yamldata=yamldata,
        fcx_mode=fcx_mode,
        show_formid_values=show_formid_values,
        formid_db_exists=formid_db_exists,
        remove_list=remove_list,
    )
