"""Util - Backwards compatibility wrapper.

This file maintains backwards compatibility by re-exporting the refactored
Utils module components.
"""

# Re-export everything from the refactored module for backwards compatibility
from ClassicLib.Utils import (
    # Version utilities
    VERSION_PATTERNS,
    # String utilities
    append_or_extend,
    # Web utilities
    async_pastebin_fetch,
    # File utilities
    calculate_file_hash,
    calculate_similarity,
    # Logging utilities
    configure_logging,
    crashgen_version_gen,
    create_version_from_info,
    extract_windows_version_info,
    get_game_version,
    get_version_fallback,
    get_version_from_pe_header,
    get_version_windows_api,
    get_version_with_pefile,
    is_valid_executable_path,
    normalize_list,
    open_file_with_encoding,
    pastebin_fetch,
    # Path utilities
    remove_readonly,
    validate_path,
)

# Create aliases for compatibility
pastebin_fetch_async = async_pastebin_fetch  # Old name -> new name

# These were private functions in original - expose them for compatibility
_is_valid_executable_path = is_valid_executable_path
_extract_windows_version_info = extract_windows_version_info
_create_version_from_info = create_version_from_info
_get_version_windows_api = get_version_windows_api
_get_version_from_pe_header = get_version_from_pe_header
_get_version_with_pefile = get_version_with_pefile
_get_version_fallback = get_version_fallback

__all__ = [
    # String utilities
    "normalize_list",
    "append_or_extend",
    "calculate_similarity",
    # Path utilities
    "validate_path",
    "remove_readonly",
    # File utilities
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
    # Private compatibility exports
    "_is_valid_executable_path",
    "_extract_windows_version_info",
    "_create_version_from_info",
    "_get_version_windows_api",
    "_get_version_from_pe_header",
    "_get_version_with_pefile",
    "_get_version_fallback",
    # Logging utilities
    "configure_logging",
    # Web utilities
    "pastebin_fetch",
    "async_pastebin_fetch",
    "pastebin_fetch_async",  # Alias for compatibility
]
