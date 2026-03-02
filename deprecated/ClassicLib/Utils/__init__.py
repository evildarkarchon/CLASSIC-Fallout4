"""Utils package - Collection of utility functions.

This module maintains backwards compatibility for the refactored Util.py.
All functions are re-exported from their new locations.
"""

# String utilities
# File utilities
from ClassicLib.Utils.file_utils import calculate_file_hash, calculate_similarity, open_file_with_encoding

# Logging utilities
from ClassicLib.Utils.logging_utils import configure_logging, enable_debug_logging

# Path utilities
from ClassicLib.Utils.path_utils import remove_readonly, validate_path
from ClassicLib.Utils.string_utils import append_or_extend, normalize_list

# Version utilities
from ClassicLib.Utils.version_utils import (
    crashgen_version_gen,
    is_valid_executable_path,
    read_game_exe_version,
)

# Web utilities
from ClassicLib.Utils.web_utils import async_pastebin_fetch, pastebin_fetch

__all__ = [
    # String utilities
    "normalize_list",
    "append_or_extend",
    # Path utilities
    "validate_path",
    "remove_readonly",
    # File utilities
    "calculate_similarity",
    "calculate_file_hash",
    "open_file_with_encoding",
    # Version utilities
    "read_game_exe_version",
    "crashgen_version_gen",
    "is_valid_executable_path",
    # Logging utilities
    "configure_logging",
    "enable_debug_logging",
    # Web utilities
    "pastebin_fetch",
    "async_pastebin_fetch",
]
