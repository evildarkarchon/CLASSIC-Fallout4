"""
Synchronous adapter functions for FileIOCore - Phase 2 Context-Aware.

These adapters use Phase 2 utilities to automatically error in CLI/TUI mode
(where async should be used) while working in GUI mode via AsyncBridge.

IMPORTANT: These are for GUI mode ONLY. In CLI/TUI, use FileIOCore async methods directly:
    # GUI mode (works)
    content = read_file_sync(path)

    # CLI/TUI mode (use this instead)
    io_core = FileIOCore()
    content = await io_core.read_file(path)
"""

from pathlib import Path

from ClassicLib.AsyncBridge import create_sync_wrapper

from .core import FileIOCore

# Create a shared FileIOCore instance for sync adapters
_io_core = FileIOCore()

# Phase 2 Context-Aware Sync Adapters
# These error in CLI/TUI mode, work in GUI mode
read_file_sync = create_sync_wrapper(_io_core.read_file)
read_lines_sync = create_sync_wrapper(_io_core.read_lines)
read_bytes_sync = create_sync_wrapper(_io_core.read_bytes)
write_file_sync = create_sync_wrapper(_io_core.write_file)
write_lines_sync = create_sync_wrapper(_io_core.write_lines)
write_bytes_sync = create_sync_wrapper(_io_core.write_bytes)
read_crash_log_sync = create_sync_wrapper(_io_core.read_crash_log)
write_crash_report_sync = create_sync_wrapper(_io_core.write_crash_report)
append_file_sync = create_sync_wrapper(_io_core.append_file)
