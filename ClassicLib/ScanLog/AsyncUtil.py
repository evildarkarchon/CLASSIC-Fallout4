"""
Async utilities for crash log scanning.

This module provides async versions of I/O-bound operations to improve
performance through concurrent execution.
"""

import asyncio
from itertools import starmap
from pathlib import Path
from typing import Any, ClassVar

import aiofiles
import aiosqlite

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import DB_PATHS
from ClassicLib.Logger import logger


class DatabasePoolManager:
    """
    Singleton manager for AsyncDatabasePool instances.

    This manager ensures that database connections are reused across multiple
    orchestrator instances, avoiding the overhead of recreating connections
    for each batch of logs. This provides significant performance improvements
    when processing multiple crash logs in sequence.
    """

    _instance: ClassVar["DatabasePoolManager | None"] = None
    _pool: "AsyncDatabasePool | None" = None
    _lock: ClassVar[asyncio.Lock | None] = None

    def __new__(cls) -> "DatabasePoolManager":
        """Ensure only one instance of DatabasePoolManager exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = None
        return cls._instance

    async def get_pool(self) -> "AsyncDatabasePool":
        """
        Get or create the singleton database pool.

        Returns:
            The singleton AsyncDatabasePool instance, initialized if necessary.
        """
        # Initialize the lock if needed (must be done in async context)
        if self._lock is None:
            self.__class__._lock = asyncio.Lock()

        async with self._lock:
            if self._pool is None:
                self._pool = AsyncDatabasePool()
                await self._pool.initialize()
                logger.debug("Created singleton database pool")
            return self._pool

    async def close_pool(self) -> None:
        """Close the singleton database pool if it exists."""
        if self._lock is None:
            return

        async with self._lock:
            if self._pool is not None:
                await self._pool.close()
                self._pool = None
                logger.debug("Closed singleton database pool")


class AsyncDatabasePool:
    """
    Represents an asynchronous connection pool for handling database operations efficiently.

    Provides an interface for managing multiple SQLite database connections asynchronously.
    Allows querying for specific entries or batches of entries while supporting caching
    to minimize database load.

    Attributes:
        max_connections (int): Maximum number of database connections allowed concurrently.
        connections (dict[Path, aiosqlite.Connection]): A mapping of database paths to their
            respective asynchronous SQLite connection objects.
        query_cache (dict[tuple[str, str], str]): A cache for storing query results to reduce
            redundant database lookups.
    """

    def __init__(self, max_connections: int = 5) -> None:
        """
        Initializes a connection manager for handling database connections and caching query results.

        This class is designed to manage a limited number of database connections, implement query
        caching for efficiency, and ensure thread safety when operating on internal data structures.

        Args:
            max_connections: The maximum number of database connections allowed to be managed
                simultaneously. Defaults to 5.
        """
        self.max_connections = max_connections
        self.connections: dict[Path, aiosqlite.Connection] = {}
        self.query_cache: dict[tuple[str, str], str] = {}
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "AsyncDatabasePool":
        """
        Handles the asynchronous context management protocol for the AsyncDatabasePool
        object. Ensures the pool is properly initialized upon entering the async context.

        Returns:
            AsyncDatabasePool: The initialized instance of the database pool.
        """
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Handles the asynchronous exit process for the context manager.
        Ensures proper cleanup of resources by invoking the `close` method.

        Args:
            exc_type: Exception type if an exception is raised inside the context.
            exc_val: Exception instance providing details about the raised exception.
            exc_tb: Traceback object representing the point at which
                the exception occurred.

        """
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
            try:
                for db_path in DB_PATHS:
                    if db_path.is_file():
                        try:
                            conn = await aiosqlite.connect(db_path)
                            self.connections[db_path] = conn
                            logger.debug(f"Opened async connection to {db_path}")
                        except (OSError, aiosqlite.Error) as e:
                            logger.error(f"Failed to open database {db_path}: {e}")
            except Exception as e:
                # Clean up any connections that were opened before the exception
                logger.error(f"Critical error during database initialization: {e}")
                for conn in self.connections.values():
                    try:
                        await conn.close()
                    except Exception as close_error:  # noqa: BLE001
                        logger.error(f"Error closing connection during cleanup: {close_error}")
                self.connections.clear()
                raise

    async def close(self) -> None:
        """
        Closes all active connections managed by the object in an asynchronous manner.

        This method ensures that all active connections are closed gracefully while
        avoiding potential deadlocks by managing the closure of connections outside the
        main locking mechanism. Each connection is closed with a defined timeout to
        prevent indefinite hanging.

        Raises:
            Exception: If an error occurs during the closure of any active connection,
                it is captured and returned as an exception in the gathering process.

        """
        # Get a copy of connections to close without holding the lock
        async with self._lock:
            connections_to_close = list(self.connections.values())
            self.connections.clear()

        # Close connections outside the lock to prevent deadlock
        close_tasks = []
        for conn in connections_to_close:
            # Create task with timeout for each connection close
            task = asyncio.create_task(self._close_connection_with_timeout(conn))
            close_tasks.append(task)

        # Wait for all connections to close (or timeout)
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

    @staticmethod
    async def _close_connection_with_timeout(conn: aiosqlite.Connection) -> None:
        """
        Closes the given SQLite database connection with a timeout.

        This method attempts to close the specified database connection within the
        defined timeout period. If the connection does not close within the given
        timeout, a TimeoutError is logged. Other potential errors during the closing
        process are also logged for debugging purposes.

        Args:
            conn (aiosqlite.Connection): The SQLite database connection to be closed.
        """
        try:
            await asyncio.wait_for(conn.close(), timeout=5.0)
        except TimeoutError:
            logger.error("Timeout closing database connection after 5.0s")
        except (aiosqlite.Error, OSError, asyncio.CancelledError) as e:
            logger.error(f"Error closing database connection: {e}")

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

    async def get_entries_batch(self, formid_plugin_pairs: list[tuple[str, str]], batch_size: int = 100) -> dict[tuple[str, str], str]:
        """
        Fetch entries from the cache or databases for given pairs of form IDs and plugins.

        This asynchronous method retrieves data associated with specified pairs of form IDs
        and plugin names. For each pair, it first checks an internal cache for pre-existing data.
        If any data is not found in the cache, the method queries the available databases in
        batches to minimize the potential SQL query size limits. The queried data is then stored
        in the cache for future usage.

        Args:
            formid_plugin_pairs (list[tuple[str, str]]): A list of (form ID, plugin) tuples to
                retrieve entries for.
            batch_size (int): The maximum number of pairs to process in a single batch
                when querying the databases. Defaults to 100.

        Returns:
            dict[tuple[str, str], str]: A dictionary mapping (form ID, plugin) pairs to their
                respective queried entries.
        """
        results = {}

        # First check cache for all pairs
        uncached_pairs = []
        for pair in formid_plugin_pairs:
            if pair in self.query_cache:
                results[pair] = self.query_cache[pair]
            else:
                uncached_pairs.append(pair)

        if not uncached_pairs:
            return results

        # Query databases for uncached pairs
        game_table = GlobalRegistry.get_game()

        # Process in batches to avoid SQL query size limits
        for i in range(0, len(uncached_pairs), batch_size):
            batch = uncached_pairs[i : i + batch_size]

            # Build parameterized query with OR conditions
            conditions = " OR ".join(["(formid=? AND plugin=?)"] * len(batch))
            query = f"SELECT formid, plugin, entry FROM {game_table} WHERE {conditions} COLLATE nocase"

            # Flatten parameters
            params = [item for pair in batch for item in pair]

            # Query each database
            for db_path, conn in self.connections.items():
                try:
                    async with conn.execute(query, params) as cursor:
                        async for row in cursor:
                            formid, plugin, entry = row
                            cache_key = (formid, plugin)
                            results[cache_key] = entry
                            self.query_cache[cache_key] = entry
                except (aiosqlite.Error, OSError) as e:
                    logger.error(f"Batch query error in {db_path}: {e}")

        return results


# noinspection PyUnusedImports
async def read_file_async(file_path: Path) -> list[str]:
    """Reads the content of a file asynchronously and returns its lines as a list of strings.

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
            from ClassicLib.AsyncUtil import read_lines_with_encoding_async

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
        """
        Loads a single log file asynchronously and retrieves its content as a tuple.

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
        elif isinstance(result, tuple):
            name, log_lines = result
            cache[name] = log_lines

    return cache


async def batch_file_operations(operations: list[tuple[str, Path, Any]]) -> None:
    """
    Perform batch file operations asynchronously.

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
