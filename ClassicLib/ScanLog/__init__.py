"""ScanLog package initialization.

This package contains modules for scanning and analyzing crash logs.

**IMPORTANT - Rust Acceleration**:
The classes and functions exported from this `__init__.py` are Python reference
implementations. For automatic Rust acceleration (10-150x speedups), import from
the factory module instead:

```python
# ❌ Python-only (no Rust acceleration)
from ClassicLib.ScanLog import FormIDAnalyzer, SuspectScanner

# ✅ Automatic Rust acceleration when available
from ClassicLib.integration.factory import get_formid_analyzer, get_suspect_scanner
```

Available factory functions with Rust acceleration:
- `get_plugin_analyzer()` - 30x speedup
- `get_formid_analyzer()` - 50x speedup
- `get_suspect_scanner()` - 40x speedup
- `get_record_scanner()` - 40x speedup
- `get_settings_validator()` - Rust wrapper
- `get_report_generator()` - 75x speedup
- `get_fcx_handler()` - Rust wrapper
- `get_gpu_detector()` - Rust wrapper
- `get_parser()` - 150x speedup
- `get_file_io()` - 10-20x speedup

See `ClassicLib.integration.factory` for complete documentation.
"""

# Core scanning components
# Modern async-first core components
from ClassicLib.ScanLog.AsyncReformat import (
    batch_file_copy_async,
    batch_file_move_async,
    crashlogs_reformat_async,
    reformat_single_log_async,
)
from ClassicLib.Database import AsyncDatabasePool
from ClassicLib.ScanLog.AsyncUtil import write_file_async
from ClassicLib.ScanLog.composition import ConditionalSection, ReportComposer
from ClassicLib.ScanLog.DetectMods import detect_mods_double, detect_mods_important, detect_mods_single
from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments as FCXModeHandler
from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
from ClassicLib.ScanLog.FormIDAnalyzerCore import FormIDAnalyzerCore
from ClassicLib.ScanLog.fragments import ReportFragment
from ClassicLib.ScanLog.GPUDetector import get_gpu_info

# New modular components
from ClassicLib.ScanLog.models import ScanConfig, ScanResult, ScanStatistics
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.ScanLog.Parser import extract_module_names, extract_segments, find_segments, parse_crash_header
from ClassicLib.ScanLog.pipeline import AsyncCrashLogPipeline
from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer
from ClassicLib.ScanLog.RecordScanner import RecordScanner
from ClassicLib.ScanLog.ReportGenerator import ReportGeneratorFragments as ReportGenerator
from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

# Backward compatibility imports for tests
from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo as ScanLogInfo  # For test imports
from ClassicLib.ScanLog.ScanLogsExecutor import ClassicScanLogs, ScanLogsExecutor
from ClassicLib.ScanLog.ScanLogsUtils import (
    complete_scan_with_summary,
    crashlogs_scan,
    crashlogs_scan_async_pure,
    crashlogs_scan_async_pure_with_qt,
    move_unsolved_logs,
    write_report_to_file,
    write_report_to_file_async,
)

# ScanOrchestrator removed - deprecated, no production usage
# Use OrchestratorCore directly for async operations
from ClassicLib.ScanLog.SettingsScanner import SettingsScannerFragments as SettingsScanner
from ClassicLib.ScanLog.SuspectScanner import SuspectScanner

# Utility functions
from ClassicLib.ScanLog.Util import (
    copy_files,
    crashlogs_get_files,
    ensure_directory_exists,
    get_entry,
    get_path_from_setting,
    is_valid_custom_scan_path,
    move_files,
)

__all__ = [
    # New modular components
    "ScanConfig",
    "ScanResult",
    "ScanStatistics",
    "ScanLogsExecutor",
    "ClassicScanLogs",  # Backward compatibility alias
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
    "FormIDAnalyzer",
    "PluginAnalyzer",
    "RecordScanner",
    "ReportGenerator",
    # "ScanOrchestrator" - REMOVED: deprecated, use OrchestratorCore
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
    # Backward compatibility exports for tests
    "ScanLogInfo",  # Alias for ClassicScanLogsInfo
    "ReportFragment",
    "ConditionalSection",
    "ReportComposer",
]
