"""
ScanLog package initialization.

This package contains modules for scanning and analyzing crash logs.
"""

from ClassicLib.ScanLog.DetectMods import detect_mods_double, detect_mods_important, detect_mods_single
from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandler
from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
from ClassicLib.ScanLog.GPUDetector import scan_log_gpu, get_gpu_info
from ClassicLib.ScanLog.Parser import parse_crash_header, extract_segments, find_segments, extract_module_names
from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer
from ClassicLib.ScanLog.RecordScanner import RecordScanner
from ClassicLib.ScanLog.ReportGenerator import ReportGenerator
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache
from ClassicLib.ScanLog.ScanOrchestrator import ScanOrchestrator
from ClassicLib.ScanLog.SettingsScanner import SettingsScanner
from ClassicLib.ScanLog.SuspectScanner import SuspectScanner
from ClassicLib.ScanLog.Util import crashlogs_get_files, crashlogs_reformat, get_entry

__all__ = [
    # Original exports
    "ClassicScanLogsInfo",
    "ThreadSafeLogCache",
    "crashlogs_get_files",
    "crashlogs_reformat",
    "get_entry",
    "detect_mods_single",
    "detect_mods_double",
    "detect_mods_important",
    # New exports
    "FCXModeHandler",
    "FormIDAnalyzer",
    "scan_log_gpu",
    "get_gpu_info",
    "parse_crash_header",
    "extract_segments",
    "find_segments",
    "extract_module_names",
    "PluginAnalyzer",
    "RecordScanner",
    "ReportGenerator",
    "ScanOrchestrator",
    "SettingsScanner",
    "SuspectScanner",
]