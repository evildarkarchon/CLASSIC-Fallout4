"""
Async utilities for crash log scanning.

This module provides async versions of I/O-bound operations to improve
performance through concurrent execution.
"""

import asyncio
from pathlib import Path
from typing import Any

import aiofiles
import aiosqlite

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import DB_PATHS
from ClassicLib.Logger import logger


class AsyncDatabasePool:
    """Manages a pool of async database connections for FormID lookups."""

    def __init__(self, max_connections: int = 5) -> None:
        """Initialize the database connection pool."""
        self.max_connections = max_connections
        self.connections: dict[Path, aiosqlite.Connection] = {}
        self.query_cache: dict[tuple[str, str], str] = {}
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "AsyncDatabasePool":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def initialize(self) -> None:
        """
        Initializes asynchronous database connections.

        This method ensures thread-safe initialization of database connections
        to files defined in `DB_PATHS`. It attempts to open an asynchronous
        connection for each valid database path and stores the connection
        in the `connections` dictionary. If an error occurs while opening any
        database, it logs the error for debugging purposes.

        Raises:
            KeyError: If the dictionary `connections` does not exist or cannot
                      be accessed.
            Any exceptions raised by `aiosqlite.connect` or file operations.

        """
        async with self._lock:
            for db_path in DB_PATHS:
                if db_path.is_file():
                    try:
                        conn = await aiosqlite.connect(db_path)
                        self.connections[db_path] = conn
                        logger.debug(f"Opened async connection to {db_path}")
                    except (OSError, aiosqlite.Error) as e:
                        logger.error(f"Failed to open database {db_path}: {e}")

    async def close(self) -> None:
        """Close all database connections."""
        async with self._lock:
            for conn in self.connections.values():
                await conn.close()
            self.connections.clear()

    async def get_entry(self, formid: str, plugin: str) -> str | None:
        """
        Fetch a specific entry from the database based on the given form ID and plugin name.
        The method first checks if the requested data is available in the cache. If not,
        it queries the connected databases sequentially until the entry is found or all
        databases are exhausted. The result is cached for future requests.

        Parameters:
        formid: str
            The unique form ID used to identify the entry in the database.
        plugin: str
            The plugin name associated with the form ID.

        Returns:
        str | None
            The entry corresponding to the specified form ID and plugin. Returns None
            if the entry is not found in the cache or any of the connected databases.

        Raises:
        aiosqlite.Error
            Raised if a SQLite error occurs during database operations.
        OSError
            Raised if an operating system-related error occurs during database operations.
        """
        # Check cache first
        cache_key = (formid, plugin)
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]

        # Query databases
        game_table = GlobalRegistry.get_game()
        query = f"SELECT entry FROM {game_table} WHERE formid=? AND plugin=? COLLATE nocase"

        for db_path, conn in self.connections.items():
            try:
                async with conn.execute(query, (formid, plugin)) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        entry = result[0]
                        self.query_cache[cache_key] = entry
                        return entry
            except (aiosqlite.Error, OSError) as e:
                logger.error(f"Database query error in {db_path}: {e}")

        return None


async def read_file_async(file_path: Path) -> list[str]:
    """
    Reads the contents of a file asynchronously and returns its lines as a list of strings.
    Handles file reading errors and logs them without raising exceptions.

    Parameters:
    file_path: Path
        The path to the file to be read. Must be a valid file path.

    Returns:
    list[str]
        A list of strings where each string corresponds to a line from the file. Returns an empty list
        if an error occurs during file reading.

    Raises:
    OSError
        Raised if there's an issue opening or reading the file.
    UnicodeDecodeError
        Raised if the file's content cannot be decoded using the specified encoding.
    """
    try:
        async with aiofiles.open(file_path, encoding="utf-8", errors="ignore") as f:
            content = await f.read()
            return content.splitlines()
    except (OSError, UnicodeDecodeError) as e:
        logger.error(f"Error reading {file_path}: {e}")
        return []


async def write_file_async(file_path: Path, content: str) -> None:
    """
    Writes the specified content to a file asynchronously. This function utilizes
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
    """
    Loads crash logs asynchronously and returns a dictionary mapping log file names
    to their respective content. Each log file is read concurrently to improve the
    performance when handling multiple files.

    Parameters:
    crashlog_list: list[Path]
        A list of Path objects representing the paths to log files to be loaded.

    Returns:
    dict[str, list[str]]
        A dictionary where the keys are file names and the values are lists of
        strings representing the content of each log file.
    """
    cache: dict[str, list[str]] = {}

    async def load_single_log(file_path: Path) -> tuple[str, list[str]]:
        """Load a single log file."""
        lines = await read_file_async(file_path)
        return file_path.name, lines

    # Load all logs concurrently
    tasks = [load_single_log(log_path) for log_path in crashlog_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, BaseException):
            logger.error(f"Failed to load log: {result}")
        elif isinstance(result, tuple):
            name, lines = result
            cache[name] = lines

    return cache


async def batch_file_operations(operations: list[tuple[str, Path, Any]]) -> None:
    """
    Perform a batch of asynchronous file operations.

    This function processes multiple file-related operations concurrently. Each operation
    must be specified as a tuple containing the type of operation, the target file path,
    and any associated data. Supported file operation types include reading, writing,
    moving, and copying files. For operations requiring blocking calls such as file moves
    or copies, the implementation ensures that these calls run in asyncio's thread pool
    to avoid blocking the event loop.

    Parameters:
    operations (list[tuple[str, Path, Any]]): A list where each item is a tuple representing
        a file operation. The tuple consists of three elements:
        - op_type (str): Specifies the operation type ('read', 'write', 'move', or 'copy').
        - path (Path): A Path object representing the target file.
        - data (Any): Additional information required for the operation.
            * For 'write', this is the content to write to the file.
            * For 'move' and 'copy', this is the destination Path for the operation.

    Returns:
    None
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

    tasks = [execute_operation(op_type, path, data) for op_type, path, data in operations]
    await asyncio.gather(*tasks, return_exceptions=True)
