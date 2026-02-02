"""Crash log scanning and analysis.

This package provides functionality for scanning and analyzing crash logs
from Bethesda games (Fallout 4, Skyrim).

**IMPORTANT - Rust Acceleration**:
The classes and functions exported from this `__init__.py` are Python reference
implementations. For automatic Rust acceleration (10-150x speedups), import from
the factory module instead:

```python
# ❌ Python-only (no Rust acceleration)
from ClassicLib.scanning.logs import SuspectScanner

# ✅ Automatic Rust acceleration when available
from ClassicLib.integration.factory import get_formid_analyzer, get_suspect_scanner
```

Subpackages:
- analyzers: Individual analyzer components (FormID, GPU, Plugin, etc.)
- models: Data models for scan configuration and results
- reporting: Report generation and composition
"""

# Core scanning components
from ClassicLib.io.database import AsyncDatabasePool

# Analyzers
from ClassicLib.scanning.logs.analyzers.FormIDAnalyzerCore import FormIDAnalyzerCore
from ClassicLib.scanning.logs.analyzers.GPUDetector import get_gpu_info
from ClassicLib.scanning.logs.analyzers.PluginAnalyzer import PluginAnalyzer
from ClassicLib.scanning.logs.analyzers.RecordScanner import RecordScanner
from ClassicLib.scanning.logs.analyzers.SettingsScanner import SettingsScannerFragments as SettingsScanner
from ClassicLib.scanning.logs.analyzers.SuspectScanner import SuspectScanner
from ClassicLib.scanning.logs.async_reformat import (
    batch_file_copy_async,
    batch_file_move_async,
    crashlogs_reformat_async,
    reformat_single_log_async,
)
from ClassicLib.scanning.logs.async_util import write_file_async
from ClassicLib.scanning.logs.detect_mods import (
    detect_mods_double,
    detect_mods_important,
    detect_mods_single,
)
from ClassicLib.scanning.logs.executor import ClassicScanLogs, ScanLogsExecutor
from ClassicLib.scanning.logs.fcx_mode_handler import FCXModeHandlerFragments as FCXModeHandler
from ClassicLib.scanning.logs.hybrid_orchestrator import HybridOrchestrator
from ClassicLib.scanning.logs.models import ScanConfig, ScanResult, ScanStatistics
from ClassicLib.scanning.logs.orchestrator_core import OrchestratorCore
from ClassicLib.scanning.logs.parser import (
    extract_module_names,
    extract_segments,
    find_segments,
    parse_crash_header,
)
from ClassicLib.scanning.logs.report_generator import ReportGeneratorFragments as ReportGenerator

# Reporting components
from ClassicLib.scanning.logs.reporting import ReportFragment
from ClassicLib.scanning.logs.reporting.async_crash_log_pipeline import AsyncCrashLogPipeline
from ClassicLib.scanning.logs.reporting.conditional_section import ConditionalSection
from ClassicLib.scanning.logs.reporting.section_composer import ReportComposer
from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo
from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo as ScanLogInfo
from ClassicLib.scanning.logs.util_legacy import (
    copy_files,
    crashlogs_get_files,
    ensure_directory_exists,
    get_entry,
    get_path_from_setting,
    is_valid_custom_scan_path,
    move_files,
)
from ClassicLib.scanning.logs.utils import (
    complete_scan_with_summary,
    crashlogs_scan,
    crashlogs_scan_async_pure,
    crashlogs_scan_async_pure_with_qt,
    move_unsolved_logs,
    write_report_to_file,
    write_report_to_file_async,
)

__all__ = [
    # New modular components
    "ScanConfig",
    "ScanResult",
    "ScanStatistics",
    "ScanLogsExecutor",
    "ClassicScanLogs",
    "HybridOrchestrator",
    "crashlogs_scan",
    "crashlogs_scan_async_pure",
    "crashlogs_scan_async_pure_with_qt",
    "write_report_to_file",
    "write_report_to_file_async",
    "move_unsolved_logs",
    "complete_scan_with_summary",
    # Async components
    "AsyncCrashLogPipeline",
    "AsyncDatabasePool",
    "FormIDAnalyzerCore",
    "OrchestratorCore",
    "batch_file_copy_async",
    "batch_file_move_async",
    "crashlogs_reformat_async",
    "reformat_single_log_async",
    "write_file_async",
    # Core scanner components
    "ClassicScanLogsInfo",
    "FCXModeHandler",
    "PluginAnalyzer",
    "RecordScanner",
    "ReportGenerator",
    "SettingsScanner",
    "SuspectScanner",
    # Detection functions
    "detect_mods_double",
    "detect_mods_important",
    "detect_mods_single",
    # GPU functions
    "get_gpu_info",
    # Parser functions
    "extract_module_names",
    "extract_segments",
    "find_segments",
    "parse_crash_header",
    # Utility functions
    "copy_files",
    "crashlogs_get_files",
    "ensure_directory_exists",
    "get_entry",
    "get_path_from_setting",
    "is_valid_custom_scan_path",
    "move_files",
    # Backward compatibility
    "ScanLogInfo",
    "ReportFragment",
    "ConditionalSection",
    "ReportComposer",
]
