"""
ScanLog package initialization.

This package contains modules for scanning and analyzing crash logs.
"""

# Core scanning components
# Async components
from ClassicLib.ScanLog.AsyncFileIO import integrate_async_file_loading
from ClassicLib.ScanLog.AsyncFormIDAnalyzer import AsyncFormIDAnalyzer
from ClassicLib.ScanLog.AsyncIntegration import run_async_scan
from ClassicLib.ScanLog.AsyncPipeline import AsyncCrashLogPipeline
from ClassicLib.ScanLog.AsyncReformat import (
    batch_file_copy_async,
    batch_file_move_async,
    crashlogs_reformat_async,
    reformat_single_log_async,
)
from ClassicLib.ScanLog.AsyncScanOrchestrator import AsyncScanOrchestrator, write_reports_batch_async
from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool, write_file_async
from ClassicLib.ScanLog.DetectMods import detect_mods_double, detect_mods_important, detect_mods_single
from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandler
from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
from ClassicLib.ScanLog.GPUDetector import get_gpu_info
from ClassicLib.ScanLog.Parser import extract_module_names, extract_segments, find_segments, parse_crash_header
from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer
from ClassicLib.ScanLog.RecordScanner import RecordScanner
from ClassicLib.ScanLog.ReportGenerator import ReportGenerator
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache
from ClassicLib.ScanLog.ScanOrchestrator import ScanOrchestrator
from ClassicLib.ScanLog.SettingsScanner import SettingsScanner
from ClassicLib.ScanLog.SuspectScanner import SuspectScanner

# Utility functions
from ClassicLib.ScanLog.Util import (
    copy_files,
    crashlogs_get_files,
    crashlogs_reformat,
    ensure_directory_exists,
    get_entry,
    get_path_from_setting,
    is_valid_custom_scan_path,
    move_files,
)

__all__ = [
    # Async components
    "AsyncCrashLogPipeline",
    "AsyncDatabasePool",
    "AsyncFormIDAnalyzer",
    "AsyncScanOrchestrator",
    # Core components
    "ClassicScanLogsInfo",
    "FCXModeHandler",
    "FormIDAnalyzer",
    "PluginAnalyzer",
    "RecordScanner",
    "ReportGenerator",
    "ScanOrchestrator",
    "SettingsScanner",
    "SuspectScanner",
    "ThreadSafeLogCache",
    "batch_file_copy_async",
    "batch_file_move_async",
    # Utility functions
    "copy_files",
    "crashlogs_get_files",
    "crashlogs_reformat",
    "crashlogs_reformat_async",
    # Detection functions
    "detect_mods_double",
    "detect_mods_important",
    "detect_mods_single",
    "ensure_directory_exists",
    # Parser functions
    "extract_module_names",
    "extract_segments",
    "find_segments",
    "get_entry",
    # GPU functions
    "get_gpu_info",
    "get_path_from_setting",
    "integrate_async_file_loading",
    "is_valid_custom_scan_path",
    "move_files",
    "parse_crash_header",
    "reformat_single_log_async",
    "run_async_scan",
    "write_file_async",
    "write_reports_batch_async",
]
