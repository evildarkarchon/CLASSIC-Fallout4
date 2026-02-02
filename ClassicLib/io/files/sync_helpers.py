"""Pure synchronous file I/O helper functions.

This module contains synchronous helper functions that do NOT use create_sync_wrapper
or AsyncBridge. These are genuinely synchronous operations that work directly with
the filesystem.

Functions:
    stream_lines_sync: Stream file contents line by line using pure sync I/O.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ClassicLib.integration.factory import get_file_io
from ClassicLib.Utils.file_utils import open_file_with_encoding


# Helper to get core lazily
def _core() -> Any:
    """Get the FileIOCore instance lazily.

    Returns:
        The FileIOCore instance from the integration factory.

    """
    return get_file_io()


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
