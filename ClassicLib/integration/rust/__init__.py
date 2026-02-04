"""Rust acceleration module for CLASSIC.

This package contains Rust-accelerated components. Use factory functions
from ClassicLib.integration.factory for all component access:
- get_suspect_scanner(yamldata)
- get_settings_validator(yamldata)
- get_gpu_detector()
- get_fcx_handler(fcx_mode)
- get_parser()
- get_file_io()
- get_report_generator(yamldata)
- get_formid_analyzer(yamldata, show_values, db_exists)
- get_plugin_analyzer(yamldata)
- get_record_scanner(yamldata)

Performance Gains:
- LogParser: 150x faster crash log parsing
- FormIDAnalyzer: 50x faster FormID extraction
- PluginAnalyzer: 30x faster plugin analysis
- RecordScanner: 40x faster record scanning
- ReportGeneration: 75x faster report composition
- FileIOCore: 10-20x faster file ops, 40x faster DDS
- DatabasePool: 25x faster database lookups
- ModDetector: 35x faster mod conflict detection
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Import all Rust wrapper components
try:
    from ClassicLib.integration.rust.file_io_rust import FileIOCore
    from ClassicLib.integration.rust.formid_rust import FormIDAnalyzer
    from ClassicLib.integration.rust.mod_detector_rust import (
        detect_mods_double,
        detect_mods_important,
        detect_mods_single,
        get_mod_detector_status,
    )
    from ClassicLib.integration.rust.parser_rust import RustLogParser
    from ClassicLib.integration.rust.plugin_rust import RustPluginAnalyzer
    from ClassicLib.integration.rust.record_rust import RustRecordScanner
    from ClassicLib.integration.rust.report_rust import RUST_AVAILABLE as REPORT_RUST_AVAILABLE  # noqa: F401
    from ClassicLib.integration.rust.report_rust import (
        ParallelReportProcessor,
        ReportComposer,
        ReportFragment,
        ReportGenerator,
        RustAcceleratedReportComposer,
        RustAcceleratedReportFragment,
        RustAcceleratedReportGenerator,
        StringPool,
    )
    from ClassicLib.io.database import AsyncDatabasePool, DatabasePoolManager
    from ClassicLib.io.database.rust_pool import RustAsyncDatabasePool

    RUST_MODULES_AVAILABLE = True
    logger.debug("Rust acceleration modules loaded successfully")

except ImportError as e:
    logger.warning(f"Some Rust modules could not be loaded: {e}")
    RUST_MODULES_AVAILABLE = False

    # Provide None for missing components
    RustLogParser = None
    FormIDAnalyzer = None
    RustPluginAnalyzer = None
    RustRecordScanner = None
    FileIOCore = None
    RustAsyncDatabasePool = None
    RustAcceleratedReportFragment = None
    RustAcceleratedReportComposer = None
    RustAcceleratedReportGenerator = None
    ParallelReportProcessor = None
    ReportFragment = None
    ReportComposer = None
    ReportGenerator = None
    StringPool = None


# Export all components
__all__ = [
    # Parser
    "RustLogParser",
    # FormID Analyzer
    "FormIDAnalyzer",
    # Plugin Analyzer
    "RustPluginAnalyzer",
    # Record Scanner
    "RustRecordScanner",
    # File I/O
    "FileIOCore",
    # Database
    "RustAsyncDatabasePool",
    "AsyncDatabasePool",
    "DatabasePoolManager",
    # Mod Detector
    "detect_mods_single",
    "detect_mods_double",
    "detect_mods_important",
    "get_mod_detector_status",
    # Report Generation
    "RustAcceleratedReportFragment",
    "RustAcceleratedReportComposer",
    "RustAcceleratedReportGenerator",
    "ParallelReportProcessor",
    "ReportFragment",
    "ReportComposer",
    "ReportGenerator",
    "StringPool",
    # Status
    "RUST_MODULES_AVAILABLE",
]


def get_rust_component_summary() -> dict[str, bool]:
    """Get a summary of available Rust components.

    Returns:
        Dictionary mapping component names to availability status

    """
    from ClassicLib.integration.factory import is_component_available

    return {
        "parser": RustLogParser is not None,
        "formid_analyzer": FormIDAnalyzer is not None,
        "plugin_analyzer": RustPluginAnalyzer is not None,
        "record_scanner": RustRecordScanner is not None,
        "file_io": FileIOCore is not None,
        "database": RustAsyncDatabasePool is not None,
        "report_generation": ReportFragment is not None,
        "mod_detector": "detect_mods_single" in globals(),
        # Use factory detection for components without wrappers
        "suspect_scanner": is_component_available("classic_scanlog", "SuspectScanner"),
        "fcx_handler": is_component_available("classic_scanlog", "FcxModeHandler"),
        "settings_validator": is_component_available("classic_scanlog", "SettingsValidator"),
        "gpu_detector": is_component_available("classic_scanlog", "GpuDetector"),
    }


def print_rust_module_status() -> None:
    """Print the status of all Rust modules."""
    print("\n" + "=" * 60)
    print("RUST MODULE STATUS")
    print("=" * 60)

    components = get_rust_component_summary()

    for component, available in components.items():
        icon = "[OK]" if available else "[--]"
        status = "LOADED" if available else "NOT AVAILABLE"
        print(f"  {icon} {component:<20} : {status}")

    available_count = sum(1 for v in components.values() if v)
    total_count = len(components)
    percentage = (available_count / total_count * 100) if total_count > 0 else 0

    print("-" * 60)
    print(f"  Total: {available_count}/{total_count} components loaded ({percentage:.0f}%)")
    print("=" * 60)
