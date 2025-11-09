"""Utils package - Collection of utility functions.

This module maintains backwards compatibility for the refactored Util.py.
All functions are re-exported from their new locations.
"""

# String utilities
# File utilities
from ClassicLib.Utils.file_utils import calculate_file_hash, calculate_similarity, open_file_with_encoding

# Logging utilities
from ClassicLib.Utils.logging_utils import configure_logging

# Path utilities
from ClassicLib.Utils.path_utils import remove_readonly, validate_path
from ClassicLib.Utils.string_utils import append_or_extend, normalize_list

# Version utilities
from ClassicLib.Utils.version_utils import (
    VERSION_PATTERNS,
    crashgen_version_gen,
    create_version_from_info,
    extract_windows_version_info,
    get_game_version,
    get_version_fallback,
    get_version_from_pe_header,
    get_version_windows_api,
    get_version_with_pefile,
    is_valid_executable_path,
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
    "get_game_version",
    "crashgen_version_gen",
    "get_version_windows_api",
    "get_version_from_pe_header",
    "get_version_with_pefile",
    "get_version_fallback",
    "extract_windows_version_info",
    "create_version_from_info",
    "is_valid_executable_path",
    "VERSION_PATTERNS",
    # Logging utilities
    "configure_logging",
    # Web utilities
    "pastebin_fetch",
    "async_pastebin_fetch",
]
