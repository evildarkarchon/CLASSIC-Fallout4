"""Backward compatibility module for ScanLog.

This package has been moved to ClassicLib.scanning.logs.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.scanning.logs instead.
"""

import warnings

warnings.warn(
    "ClassicLib.ScanLog is deprecated, import from ClassicLib.scanning.logs instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.scanning.logs import *  # noqa: F403, E402, I001
from ClassicLib.scanning.logs import (  # noqa: E402
    AsyncCrashLogPipeline as AsyncCrashLogPipeline,
    AsyncDatabasePool as AsyncDatabasePool,
    ClassicScanLogs as ClassicScanLogs,
    ClassicScanLogsInfo as ClassicScanLogsInfo,
    ConditionalSection as ConditionalSection,
    FCXModeHandler as FCXModeHandler,
    FormIDAnalyzer as FormIDAnalyzer,
    FormIDAnalyzerCore as FormIDAnalyzerCore,
    HybridOrchestrator as HybridOrchestrator,
    OrchestratorCore as OrchestratorCore,
    PluginAnalyzer as PluginAnalyzer,
    RecordScanner as RecordScanner,
    ReportComposer as ReportComposer,
    ReportFragment as ReportFragment,
    ReportGenerator as ReportGenerator,
    ScanConfig as ScanConfig,
    ScanLogInfo as ScanLogInfo,
    ScanLogsExecutor as ScanLogsExecutor,
    ScanResult as ScanResult,
    ScanStatistics as ScanStatistics,
    SettingsScanner as SettingsScanner,
    SuspectScanner as SuspectScanner,
    batch_file_copy_async as batch_file_copy_async,
    batch_file_move_async as batch_file_move_async,
    complete_scan_with_summary as complete_scan_with_summary,
    copy_files as copy_files,
    crashlogs_get_files as crashlogs_get_files,
    crashlogs_reformat_async as crashlogs_reformat_async,
    crashlogs_scan as crashlogs_scan,
    crashlogs_scan_async_pure as crashlogs_scan_async_pure,
    crashlogs_scan_async_pure_with_qt as crashlogs_scan_async_pure_with_qt,
    detect_mods_double as detect_mods_double,
    detect_mods_important as detect_mods_important,
    detect_mods_single as detect_mods_single,
    ensure_directory_exists as ensure_directory_exists,
    extract_module_names as extract_module_names,
    extract_segments as extract_segments,
    find_segments as find_segments,
    get_entry as get_entry,
    get_gpu_info as get_gpu_info,
    get_path_from_setting as get_path_from_setting,
    is_valid_custom_scan_path as is_valid_custom_scan_path,
    move_files as move_files,
    move_unsolved_logs as move_unsolved_logs,
    parse_crash_header as parse_crash_header,
    reformat_single_log_async as reformat_single_log_async,
    write_file_async as write_file_async,
    write_report_to_file as write_report_to_file,
    write_report_to_file_async as write_report_to_file_async,
)
