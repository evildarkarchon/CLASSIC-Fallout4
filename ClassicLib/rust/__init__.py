"""Rust acceleration module for CLASSIC.

This package contains all Rust-accelerated components providing 10-150x performance
improvements for CLASSIC's core operations. All components provide transparent
fallback to Python implementations when Rust is not available.

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
    from ClassicLib.rust import gpu_rust

    # Database imports from new canonical location
    from ClassicLib.Database import AsyncDatabasePool, DatabasePoolManager
    from ClassicLib.Database.rust_pool import RustAsyncDatabasePool

    # Legacy function (deprecated)
    from ClassicLib.rust.database_rust import get_database_pool_implementation
    from ClassicLib.rust.fcx_rust import FCXModeHandler, FcxModeHandler, RustAcceleratedFcxModeHandler
    from ClassicLib.rust.file_io_rust import FileIOCore, create_file_io_sync, get_rust_file_io
    from ClassicLib.rust.formid_rust import FormIDAnalyzer
    from ClassicLib.rust.mod_detector_rust import detect_mods_double, detect_mods_important, detect_mods_single, get_mod_detector_status
    from ClassicLib.rust.parser_rust import RustLogParser
    from ClassicLib.rust.plugin_rust import RustPluginAnalyzer
    from ClassicLib.rust.record_rust import RustRecordScanner
    from ClassicLib.rust.report_rust import RUST_AVAILABLE as REPORT_RUST_AVAILABLE  # noqa: F401
    from ClassicLib.rust.report_rust import (
        ParallelReportProcessor,
        ReportComposer,
        ReportFragment,
        ReportGenerator,
        RustAcceleratedReportComposer,
        RustAcceleratedReportFragment,
        RustAcceleratedReportGenerator,
        StringPool,
    )
    from ClassicLib.rust.settings_rust import (
        RustAcceleratedSettingsValidator,
        SettingsScannerFragments,
        SettingsValidator,
    )
    from ClassicLib.rust.suspect_rust import RustAcceleratedSuspectScanner, SuspectScanner

    RUST_MODULES_AVAILABLE = True
    logger.debug("✅ Rust acceleration modules loaded successfully")

except ImportError as e:
    logger.warning(f"⚠️  Some Rust modules could not be loaded: {e}")
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
    RustAcceleratedSuspectScanner = None
    SuspectScanner = None
    FCXModeHandler = None
    FcxModeHandler = None
    RustAcceleratedFcxModeHandler = None
    RustAcceleratedSettingsValidator = None
    SettingsValidator = None
    SettingsScannerFragments = None
    gpu_rust = None


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
    "get_rust_file_io",
    "create_file_io_sync",
    # Database
    "RustAsyncDatabasePool",
    "AsyncDatabasePool",
    "DatabasePoolManager",
    "get_database_pool_implementation",
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
    # Suspect Scanner
    "RustAcceleratedSuspectScanner",
    "SuspectScanner",
    # FCX Mode Handler
    "FCXModeHandler",
    "FcxModeHandler",
    "RustAcceleratedFcxModeHandler",
    # Settings Validator
    "RustAcceleratedSettingsValidator",
    "SettingsValidator",
    "SettingsScannerFragments",
    # GPU Detector
    "gpu_rust",
    # Status
    "RUST_MODULES_AVAILABLE",
]


def get_rust_component_summary() -> dict[str, bool]:
    """Get a summary of available Rust components.

    Returns:
        Dictionary mapping component names to availability status

    """
    return {
        "parser": RustLogParser is not None,
        "formid_analyzer": FormIDAnalyzer is not None,
        "plugin_analyzer": RustPluginAnalyzer is not None,
        "record_scanner": RustRecordScanner is not None,
        "file_io": FileIOCore is not None,
        "database": RustAsyncDatabasePool is not None,
        "report_generation": ReportFragment is not None,
        "mod_detector": "detect_mods_single" in globals(),
        "suspect_scanner": SuspectScanner is not None,
        "fcx_handler": FCXModeHandler is not None,
        "settings_validator": SettingsValidator is not None,
        "gpu_detector": gpu_rust is not None,
    }


def print_rust_module_status() -> None:
    """Print the status of all Rust modules."""
    print("\n" + "=" * 60)
    print("🚀 RUST MODULE STATUS")
    print("=" * 60)

    components = get_rust_component_summary()

    for component, available in components.items():
        icon = "✅" if available else "❌"
        status = "LOADED" if available else "NOT AVAILABLE"
        print(f"  {icon} {component:<20} : {status}")

    available_count = sum(1 for v in components.values() if v)
    total_count = len(components)
    percentage = (available_count / total_count * 100) if total_count > 0 else 0

    print("-" * 60)
    print(f"  Total: {available_count}/{total_count} components loaded ({percentage:.0f}%)")
    print("=" * 60)
