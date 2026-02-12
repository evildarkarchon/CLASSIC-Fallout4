"""Crash log scanning and analysis.

This package provides functionality for scanning and analyzing crash logs
from Bethesda games (Fallout 4, Skyrim).

**IMPORTANT - Rust Acceleration**:
All analyzer components have been migrated to Rust. Import from the factory
module for automatic Rust acceleration (10-150x speedups):

```python
# Use factory functions for all analyzers
from ClassicLib.integration.factory import (
    get_formid_analyzer,
    get_gpu_detector,
    get_plugin_analyzer,
    get_record_scanner,
    get_settings_validator,
    get_suspect_scanner,
    get_fcx_handler,
)
```

Subpackages:
- analyzers: Package placeholder (implementations now in Rust)
- models: Data models for scan configuration and results
- reporting: Report generation and composition
"""

# Core scanning components
from ClassicLib.io.database import AsyncDatabasePool

# Async utilities
from ClassicLib.scanning.logs.async_reformat import (
    batch_file_copy_async,
    batch_file_move_async,
    crashlogs_reformat_async,
    reformat_single_log_async,
)
from ClassicLib.scanning.logs.async_util import write_file_async

# Mod detection (delegates to Rust classic_scanlog via integration layer)
from ClassicLib.scanning.logs.detect_mods import (
    detect_mods_double,
    detect_mods_important,
    detect_mods_single,
)

# Executor
from ClassicLib.scanning.logs.executor import ClassicScanLogs, ScanLogsExecutor

# Models
from ClassicLib.scanning.logs.models import ScanConfig, ScanResult, ScanStatistics

# Parser (Python utilities, may use Rust internally via factory)
from ClassicLib.scanning.logs.parser import (
    extract_module_names,
    extract_segments,
    find_segments,
    parse_crash_header,
)

# Report generator
from ClassicLib.scanning.logs.report_generator import ReportGeneratorFragments as ReportGenerator

# Reporting components
from ClassicLib.scanning.logs.reporting import ReportFragment
from ClassicLib.scanning.logs.reporting.async_crash_log_pipeline import AsyncCrashLogPipeline
from ClassicLib.scanning.logs.reporting.conditional_section import ConditionalSection
from ClassicLib.scanning.logs.reporting.section_composer import ReportComposer

# Scan log info
from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo
from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo as ScanLogInfo

# Legacy utilities
from ClassicLib.scanning.logs.util_legacy import (
    copy_files,
    crashlogs_get_files,
    ensure_directory_exists,
    get_entry,
    get_path_from_setting,
    is_valid_custom_scan_path,
    move_files,
)

# Scan utilities
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
    "batch_file_copy_async",
    "batch_file_move_async",
    "crashlogs_reformat_async",
    "reformat_single_log_async",
    "write_file_async",
    # Core scanner components
    "ClassicScanLogsInfo",
    "ReportGenerator",
    # Detection functions
    "detect_mods_double",
    "detect_mods_important",
    "detect_mods_single",
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
