"""FileIO module - Async-first unified file I/O operations.

This module provides high-performance file I/O with:
- Automatic encoding detection
- Concurrent batch operations
- Crash log specific handling
- Sync adapters for backwards compatibility
"""

# Import core class and utilities
from .core import FileIOCore
from .path_utils import cached_path_conversion, ensure_path
from .sync_adapters import (
    append_file_sync,
    read_bytes_sync,
    read_crash_log_sync,
    read_file_sync,
    read_lines_sync,
    write_bytes_sync,
    write_crash_report_sync,
    write_file_sync,
    write_lines_sync,
)

__all__ = [
    # Core class
    "FileIOCore",
    # Path utilities
    "ensure_path",
    "cached_path_conversion",
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
