"""
Synchronous adapter functions for FileIOCore - Context-Aware.

These adapters automatically choose the appropriate async execution method:
- GUI mode: Uses AsyncBridge for Qt event loop integration
- CLI/TUI mode: Uses asyncio.run() for standard Python async execution

This allows sync adapters to work in all contexts:
    # GUI mode (uses AsyncBridge)
    content = read_file_sync(path)

    # CLI/TUI mode (uses asyncio.run())
    content = read_file_sync(path)  # Also works!

    # Or use async directly if preferred
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
