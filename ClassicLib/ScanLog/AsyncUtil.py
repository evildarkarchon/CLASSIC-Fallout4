"""Async utilities for crash log scanning.

This module provides async versions of I/O-bound operations to improve
performance through concurrent execution.

Deprecated:
    The DatabasePoolManager and AsyncDatabasePool classes have been moved to
    ClassicLib.Database. Import from there instead:

    ```python
    from ClassicLib.Database import DatabasePoolManager, AsyncDatabasePool
    ```
"""

from __future__ import annotations

import asyncio
import warnings
from itertools import starmap
from pathlib import Path
from typing import Any

import aiofiles

from ClassicLib.Logger import logger

# Backward compatibility re-exports with deprecation warnings
# These will be removed in a future version


def __getattr__(name: str) -> Any:
    """Provide deprecated imports with warnings.

    Args:
        name: The attribute name being accessed.

    Returns:
        The requested class or raises AttributeError if not found.

    """
    if name == "DatabasePoolManager":
        warnings.warn(
            "Import DatabasePoolManager from ClassicLib.Database instead of "
            "ClassicLib.ScanLog.AsyncUtil. This import path will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        from ClassicLib.Database.pool_manager import DatabasePoolManager

        return DatabasePoolManager
    if name == "AsyncDatabasePool":
        warnings.warn(
            "Import AsyncDatabasePool from ClassicLib.Database instead of "
            "ClassicLib.ScanLog.AsyncUtil. This import path will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        from ClassicLib.Database.async_pool import AsyncDatabasePool

        return AsyncDatabasePool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


async def read_file_async(file_path: Path) -> list[str]:
    """Read the content of a file asynchronously and returns its lines as a list of strings.

    This function attempts to read the file content using an async encoding detection utility if
    available. If the utility is not available, it defaults to reading the file using UTF-8 encoding
    while ignoring errors. If the file cannot be read due to OS or decoding errors, an empty list is
    returned.

    Args:
        file_path (Path): The path of the file to be read.

    Returns:
        list[str]: A list of strings, where each string represents a line in the file. If an error
        occurs during file reading, an empty list is returned.

    """
    try:
        # Try to use async encoding detection if available
        try:
            from ClassicLib.FileIO.Async import read_lines_with_encoding_async  # pyright: ignore[reportUnknownVariableType]

            return await read_lines_with_encoding_async(file_path)
        except ImportError:
            # Fallback to UTF-8
            async with aiofiles.open(file_path, encoding="utf-8", errors="ignore") as f:
                content = await f.read()
                return content.splitlines()
    except (OSError, UnicodeDecodeError) as e:
        logger.error(f"Error reading {file_path}: {e}")
        return []


async def write_file_async(file_path: Path, content: str) -> None:
    """Write the specified content to a file asynchronously. This function utilizes
    asynchronous file operations to write the content into the designated file
    path efficiently. In case of an error during the file writing operation, it
    logs the error details.

    Arguments:
        file_path (Path): The path of the file to write content into.
        content (str): The string content to be written to the file.

    Raises:
        OSError: If there is an issue accessing or writing to the file.
        UnicodeEncodeError: If the content cannot be encoded properly in the
        specified encoding.

    """
    try:
        async with aiofiles.open(file_path, mode="w", encoding="utf-8", errors="ignore") as f:
            await f.write(content)
    except (OSError, UnicodeEncodeError) as e:
        logger.error(f"Error writing {file_path}: {e}")


async def load_crash_logs_async(crashlog_list: list[Path]) -> dict[str, list[str]]:
    """Load crash logs asynchronously and return a dictionary of contents.

    Each log file is read concurrently for improved performance when
    handling multiple files.

    Args:
        crashlog_list: List of Path objects to log files to be loaded.

    Returns:
        Dictionary mapping file names to lists of content lines.

    """
    cache: dict[str, list[str]] = {}

    async def load_single_log(file_path: Path) -> tuple[str, list[str]]:
        """Load a single log file asynchronously and retrieves its content as a tuple.

        The function reads the content of a specified log file asynchronously and
        returns the file name along with its content as a list of lines. The file
        is opened and processed in a non-blocking asynchronous manner to enable
        efficient handling of I/O-bound operations.

        Args:
            file_path (Path): The path of the log file to be read.

        Returns:
            tuple: A tuple where the first element is the file name as a string,
            and the second element is a list of strings containing the lines of
            the file.

        """
        lines = await read_file_async(file_path)
        return file_path.name, lines

    # Load all logs concurrently
    tasks = [load_single_log(log_path) for log_path in crashlog_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, BaseException):
            logger.error(f"Failed to load log: {result}")
        elif result:
            name, log_lines = result
            cache[name] = log_lines

    return cache


async def batch_file_operations(operations: list[tuple[str, Path, Any]]) -> None:
    """Perform batch file operations asynchronously.

    This function accepts a list of operations to perform on files asynchronously.
    Each operation is defined as a tuple containing the operation type, the file path,
    and any additional data required for that operation. Supported operations include
    read, write, move, and copy. File operations are executed in parallel to enhance
    performance.

    Args:
        operations (list[tuple[str, Path, Any]]): A list of tuples, where each tuple
            represents a file operation. The tuple consists of:
                - op_type (str): The type of operation to perform ("read", "write",
                  "move", "copy").
                - path (Path): The path to the file involved in the operation.
                - data (Any): Additional data required for the operation. For example,
                  file content for "write" or destination path for "move" or "copy".

    """

    async def execute_operation(op_type: str, path: Path, data: Any) -> None:
        """Execute a single file operation."""
        if op_type == "read":
            await read_file_async(path)
        elif op_type == "write":
            await write_file_async(path, data)
        elif op_type == "move" and isinstance(data, Path):
            # Use asyncio's thread pool for blocking operations
            await asyncio.to_thread(path.rename, data)
        elif op_type == "copy" and isinstance(data, Path):
            import shutil

            await asyncio.to_thread(shutil.copy2, path, data)

    tasks = list(starmap(execute_operation, operations))
    await asyncio.gather(*tasks, return_exceptions=True)
