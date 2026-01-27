"""Crash log analyzers for different aspects of log analysis.

This package contains specialized analyzers:
- FormIDAnalyzer: Analyzes FormID references in crash logs
- FormIDAnalyzerCore: Core FormID analysis functionality
- GPUDetector: Detects GPU-related issues
- PluginAnalyzer: Analyzes plugin-related issues
- RecordScanner: Scans for record-related problems
- SuspectScanner: Identifies suspect entries
- SettingsScanner: Scans for settings-related issues
"""

from ClassicLib.scanning.logs.analyzers.FormIDAnalyzer import FormIDAnalyzer
from ClassicLib.scanning.logs.analyzers.FormIDAnalyzerCore import FormIDAnalyzerCore
from ClassicLib.scanning.logs.analyzers.GPUDetector import get_gpu_info
from ClassicLib.scanning.logs.analyzers.PluginAnalyzer import PluginAnalyzer
from ClassicLib.scanning.logs.analyzers.RecordScanner import RecordScanner
from ClassicLib.scanning.logs.analyzers.SettingsScanner import SettingsScannerFragments as SettingsScanner
from ClassicLib.scanning.logs.analyzers.SuspectScanner import SuspectScanner

__all__ = [
    "FormIDAnalyzer",
    "FormIDAnalyzerCore",
    "get_gpu_info",
    "PluginAnalyzer",
    "RecordScanner",
    "SettingsScanner",
    "SuspectScanner",
]
