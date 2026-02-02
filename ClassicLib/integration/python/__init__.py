"""Pure Python implementations serving as fallbacks.

This module contains pure Python implementations that serve as fallbacks
when Rust acceleration is not available for parser, mod detector, and
plugin analyzer components. Other components (database, file_io, formid,
record, report) now require Rust -- see factory.py.
"""

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

__all__ = [
    # Core classes
    "PythonPluginAnalyzer",
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
