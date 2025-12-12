"""Synchronous adapter functions for FileIOCore - Context-Aware.

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

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ClassicLib.AsyncBridge import create_sync_wrapper
from ClassicLib.integration.factory import get_file_io
from ClassicLib.Utils.file_utils import open_file_with_encoding


# Helper to get core lazily
def _core() -> Any:
    return get_file_io()


# Define async delegates
async def _read_file(path: Path | str) -> str:
    return await _core().read_file(path)


async def _read_lines(path: Path | str) -> list[str]:
    return await _core().read_lines(path)


async def _read_bytes(path: Path | str) -> bytes:
    return await _core().read_bytes(path)


async def _write_file(path: Path | str, content: str) -> None:
    return await _core().write_file(path, content)


async def _write_lines(path: Path | str, lines: list[str]) -> None:
    return await _core().write_lines(path, lines)


async def _write_bytes(path: Path | str, content: bytes) -> None:
    return await _core().write_bytes(path, content)


async def _read_crash_log(path: Path | str) -> list[str]:
    return await _core().read_crash_log(path)


async def _write_crash_report(path: Path | str, lines: list[str]) -> None:
    return await _core().write_crash_report(path, lines)


async def _append_file(path: Path | str, content: str) -> None:
    return await _core().append_file(path, content)


# Create wrappers
read_file_sync = create_sync_wrapper(_read_file)
read_lines_sync = create_sync_wrapper(_read_lines)
read_bytes_sync = create_sync_wrapper(_read_bytes)
write_file_sync = create_sync_wrapper(_write_file)
write_lines_sync = create_sync_wrapper(_write_lines)
write_bytes_sync = create_sync_wrapper(_write_bytes)
read_crash_log_sync = create_sync_wrapper(_read_crash_log)
write_crash_report_sync = create_sync_wrapper(_write_crash_report)
append_file_sync = create_sync_wrapper(_append_file)


def stream_lines_sync(path: Path | str) -> Iterator[str]:
    """Stream synchronously the contents of a file line by line.

    This function yields lines from the file one by one, using automatic encoding
    detection. It is memory-efficient for large files and does NOT use the
    AsyncBridge or creating a new event loop, making it safe for simple sync loops.

    It attempts to use the Rust-accelerated implementation if available via
    get_file_io(), otherwise falls back to pure Python.

    Args:
        path (Path | str): The path to the file to be read.

    Yields:
        str: A single line from the file.

    """
    # Try to use FileIOCore (which might be Rust-accelerated)
    io_core = _core()
    if hasattr(io_core, "stream_lines_sync"):
        yield from io_core.stream_lines_sync(path)
    else:
        # Fallback for standard Python FileIOCore or generic IO
        with open_file_with_encoding(path) as f:
            yield from f
