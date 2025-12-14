"""Pure Python async database pool implementation.

This module provides an asynchronous database connection pool using aiosqlite
for handling SQLite database operations. This is the fallback implementation
when Rust acceleration is not available.

Performance Note:
    The Rust implementation (RustAsyncDatabasePool) is approximately 25x faster.
    Use the factory function or DatabasePoolManager to automatically select
    the best available implementation.

Example:
    >>> from ClassicLib.Database import AsyncDatabasePool
    >>> async with AsyncDatabasePool() as pool:
    ...     result = await pool.get_entry("00012345", "Fallout4.esm")

"""

from __future__ import annotations

import asyncio
from pathlib import Path  # noqa: TC003 - used at runtime for dict keys
from typing import TYPE_CHECKING, Any

import aiosqlite

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import DB_PATHS
from ClassicLib.Logger import logger

if TYPE_CHECKING:
    from collections.abc import Sequence


class AsyncDatabasePool:
    """Asynchronous connection pool for handling database operations efficiently.

    Provides an interface for managing multiple SQLite database connections
    asynchronously using aiosqlite. Supports query caching to minimize
    database load.

    Attributes:
        max_connections: Maximum number of database connections allowed.
        connections: Mapping of database paths to their async connections.
        query_cache: Cache for storing query results to reduce redundant lookups.

    Example:
        >>> pool = AsyncDatabasePool(max_connections=10)
        >>> await pool.initialize()
        >>> result = await pool.get_entry("00012345", "Fallout4.esm")
        >>> await pool.close()

    """

    def __init__(self, max_connections: int = 5) -> None:
        """Initialize the connection pool.

        Args:
            max_connections: Maximum number of database connections allowed
                to be managed simultaneously. Defaults to 5.

        """
        self.max_connections = max_connections
        self.connections: dict[Path, aiosqlite.Connection] = {}
        self.query_cache: dict[tuple[str, str], str] = {}
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> AsyncDatabasePool:
        """Enter async context manager.

        Returns:
            The initialized database pool instance.

        """
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager, cleaning up resources.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_val: Exception instance if an exception was raised.
            exc_tb: Traceback if an exception was raised.

        """
        await self.close()

    async def initialize(self) -> None:
        """Initialize database connections.

        Opens async connections to all database files defined in DB_PATHS.
        Thread-safe initialization using an async lock.

        Raises:
            aiosqlite.Error: If database connection fails.
            OSError: If database file cannot be accessed.

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
            except Exception as e:  # noqa: BLE001 - Critical initialization error; must clean up and re-raise
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
        """Close all active database connections.

        Closes connections gracefully with a timeout to prevent indefinite
        hanging. Connections are closed outside the lock to prevent deadlock.

        Raises:
            Exception: Captured and returned in gathering if closure fails.

        """
        # Get a copy of connections to close without holding the lock
        async with self._lock:
            connections_to_close = list(self.connections.values())
            self.connections.clear()

        # Close connections outside the lock to prevent deadlock
        close_tasks = []
        for conn in connections_to_close:
            task = asyncio.create_task(self._close_connection_with_timeout(conn))
            close_tasks.append(task)

        # Wait for all connections to close (or timeout)
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

    @staticmethod
    async def _close_connection_with_timeout(conn: aiosqlite.Connection) -> None:
        """Close a database connection with a timeout.

        Args:
            conn: The SQLite database connection to close.

        """
        try:
            await asyncio.wait_for(conn.close(), timeout=5.0)
        except TimeoutError:
            logger.error("Timeout closing database connection after 5.0s")
        except (aiosqlite.Error, OSError, asyncio.CancelledError) as e:
            logger.error(f"Error closing database connection: {e}")

    async def get_entry(self, formid: str, plugin: str) -> str | None:
        """Fetch a specific entry from the database.

        Checks the cache first, then queries connected databases sequentially
        until the entry is found. Results are cached for future requests.

        Args:
            formid: The unique form ID to look up.
            plugin: The plugin name associated with the form ID.

        Returns:
            The database entry for the form ID and plugin, or None if not found.

        Raises:
            aiosqlite.Error: If a SQLite error occurs during database operations.
            OSError: If an operating system error occurs.

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

    async def get_entries_batch(
        self,
        formid_plugin_pairs: Sequence[tuple[str, str]],
        batch_size: int = 100,
    ) -> dict[tuple[str, str], str]:
        """Fetch entries in batch from the database.

        Retrieves data for multiple form ID/plugin pairs efficiently.
        Checks cache first, then queries databases in batches to minimize
        SQL query size.

        Args:
            formid_plugin_pairs: A sequence of (form ID, plugin) tuples.
            batch_size: Maximum number of pairs to process in a single
                batch when querying databases. Defaults to 100.

        Returns:
            A dictionary mapping (form ID, plugin) pairs to their entries.

        """
        results: dict[tuple[str, str], str] = {}

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
