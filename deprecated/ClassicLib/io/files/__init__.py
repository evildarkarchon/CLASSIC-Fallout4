"""FileIO module - Async-first unified file I/O operations.

This module provides high-performance file I/O with:
- Automatic encoding detection
- Concurrent batch operations
- Crash log specific handling
- Pure sync helpers (stream_lines_sync)
"""

# Import core class and utilities
from ClassicLib.io.files.core import FileIOCore
from ClassicLib.io.files.path_utils import cached_path_conversion, ensure_path
from ClassicLib.io.files.sync_helpers import stream_lines_sync

__all__ = [
    # Core class
    "FileIOCore",
    # Path utilities
    "ensure_path",
    "cached_path_conversion",
    # Pure sync helpers
    "stream_lines_sync",
]
