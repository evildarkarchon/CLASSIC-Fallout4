"""Pure Python implementations serving as fallbacks.

This module contains pure Python implementations that serve as fallbacks
when Rust acceleration is not available. These implementations maintain
full API compatibility with their Rust counterparts and ensure the
application works in all environments.

These components are also used for development and testing scenarios
where deterministic Python behavior is required.
"""

from ClassicLib.integration.python.database_py import PythonDatabasePool
from ClassicLib.integration.python.file_io_py import PythonFileIO
from ClassicLib.integration.python.formid_py import PythonFormIDAnalyzer
from ClassicLib.integration.python.mod_detector_py import (
    detect_mods_double,
    detect_mods_important,
    detect_mods_single,
)
from ClassicLib.integration.python.parser_py import (
    extract_module_names,
    extract_segments,
    find_segments,
    parse_crash_header,
)
from ClassicLib.integration.python.plugin_py import PythonPluginAnalyzer
from ClassicLib.integration.python.record_py import PythonRecordScanner
from ClassicLib.integration.python.report_py import PythonReportGenerator

__all__ = [
    # Core classes
    "PythonDatabasePool",
    "PythonFileIO",
    "PythonFormIDAnalyzer",
    "PythonPluginAnalyzer",
    "PythonRecordScanner",
    "PythonReportGenerator",
    # Parser functions
    "parse_crash_header",
    "extract_segments",
    "find_segments",
    "extract_module_names",
    # Mod detector functions
    "detect_mods_single",
    "detect_mods_double",
    "detect_mods_important",
]
