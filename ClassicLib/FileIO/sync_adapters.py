"""
Synchronous adapter functions for FileIOCore - Context-Aware.

These adapters automatically choose the appropriate async execution method:
- GUI mode: Uses AsyncBridge for Qt event loop integration
- CLI/TUI mode: Uses asyncio.run() for standard Python async execution

IMPORTANT - Appropriate Usage:
✅ GUI workers (Qt threads, PySide6 slots) - PRIMARY USE CASE
✅ Testing and benchmarking file operations
✅ One-off file operations in sync contexts (initialization)

❌ DO NOT USE in production CLI main flow
❌ DO NOT USE for repeated file operations in CLI (inefficient)
❌ DO NOT USE when already in async context

Best Practices:
- Production CLI code should use FileIOCore async methods directly
- GUI contexts should use these sync adapters for thread safety
- Each sync call in CLI mode creates a new event loop (overhead)

Usage Examples:
    # Example 1: GUI context (CORRECT)
    class LogScanWorker(QThread):
        def run(self):
            content = read_file_sync(path)  # Uses AsyncBridge

    # Example 2: Testing (CORRECT)
    def test_file_reading():
        content = read_file_sync(path)  # Works via asyncio.run()

    # Example 3: CLI production (INCORRECT)
    def main():
        content1 = read_file_sync(path1)  # New event loop
        content2 = read_file_sync(path2)  # New event loop (slow!)

    # Example 4: CLI production (CORRECT - do this instead)
    async def main():
        io_core = FileIOCore()
        content1 = await io_core.read_file(path1)  # Same event loop
        content2 = await io_core.read_file(path2)  # Much faster!

    if __name__ == "__main__":
        asyncio.run(main())  # Single event loop at entry point

Reference Implementation:
    See CLASSIC_ScanLogs.py for async-first CLI pattern
    See ClassicLib/Interface/Workers.py for GUI worker pattern

Note:
    The CLI/TUI mode asyncio.run() fallback is intentional for testing
    and benchmarking. Production CLI code should use async methods directly
    with FileIOCore for optimal performance.
"""

from ClassicLib.AsyncBridge import create_sync_wrapper
from ClassicLib.FileIO.core import FileIOCore

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
