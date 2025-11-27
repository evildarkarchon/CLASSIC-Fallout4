"""
FileIOCore - High-Performance File I/O with Rust Acceleration ⚡

DEPRECATED: Use ClassicLib.FileIO instead.
"""

import warnings

# Re-export everything from the refactored module for backwards compatibility
from ClassicLib.FileIO import (
    FileIOCore,
    append_file_sync,
    cached_path_conversion,
    ensure_path,
    read_bytes_sync,
    read_crash_log_sync,
    read_file_sync,
    read_lines_sync,
    write_bytes_sync,
    write_crash_report_sync,
    write_file_sync,
    write_lines_sync,
)

warnings.warn(
    "ClassicLib.FileIOCore is deprecated. Use ClassicLib.FileIO instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Also export the ensure_path function with underscore prefix for compatibility
_cached_path_conversion = cached_path_conversion

__all__ = [
    # Core class
    "FileIOCore",
    # Path utilities (including underscore version for compatibility)
    "ensure_path",
    "cached_path_conversion",
    "_cached_path_conversion",
    # Sync adapters
    "read_file_sync",
    "read_lines_sync",
    "read_bytes_sync",
    "write_file_sync",
    "write_lines_sync",
    "write_bytes_sync",
    "read_crash_log_sync",
    "write_crash_report_sync",
    "append_file_sync",
]
