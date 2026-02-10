"""Pure Python async database pool implementation.

This module provides an asynchronous database connection pool using aiosqlite
for handling SQLite database operations. This is the fallback implementation
when Rust acceleration is not available.

Performance Note:
    The Rust implementation (RustAsyncDatabasePool) is approximately 25x faster.
    Use the factory function or DatabasePoolManager to automatically select
    the best available implementation.

Optimizations (v8.1+):
    - Parallel database queries using asyncio.gather
    - UNION ALL query pattern for better index utilization
    - Extended cache TTL (30 min) for cross-log persistence
    - Adaptive batch sizing

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

from ClassicLib.core.constants import get_all_db_paths_async
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import GlobalRegistry

if TYPE_CHECKING:
    from collections.abc import Sequence

# Cache TTL constants (in seconds)
DEFAULT_CACHE_TTL_SECS: int = 300
"""Default cache TTL for single log scanning (5 minutes)."""

BATCH_CACHE_TTL_SECS: int = 1800
"""Extended cache TTL for batch log scanning (30 minutes)."""

MAX_CACHE_TTL_SECS: int = 3600
"""Maximum recommended cache TTL (60 minutes)."""


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

    async def __aexit__(self, exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Exit async context manager, cleaning up resources.

        Args:
            exc_type: Exception type if an exception was raised.
            _exc_val: Exception instance if an exception was raised.
            _exc_tb: Traceback if an exception was raised.

        """
        await self.close()

    async def initialize(self) -> None:
        """Initialize database connections.

        Opens async connections to all database files from get_all_db_paths().
        Thread-safe initialization using an async lock.

        Raises:
            aiosqlite.Error: If database connection fails.
            OSError: If database file cannot be accessed.

        """
        async with self._lock:
            try:
                for db_path in await get_all_db_paths_async():
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
            await asyncio.gather(*close_tasks, return_exceptions=True)  # pyright: ignore[reportUnknownArgumentType]

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
        # Check cache first (use lowercase plugin for case-insensitive matching)
        cache_key = (formid, plugin.lower())
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

    @staticmethod
    def _build_union_all_query(game_table: str, batch_len: int) -> str:
        """Build a UNION ALL query for better index utilization.

        SQLite's optimizer handles UNION ALL queries more efficiently than
        OR-based conditions, especially when an index is available.

        Args:
            game_table: The table name to query.
            batch_len: Number of pairs to include in the query.

        Returns:
            A SQL query string using UNION ALL pattern.

        """
        if batch_len == 0:
            return ""

        # Build UNION ALL query - each SELECT uses the covering index
        selects = [f"SELECT formid, plugin, entry FROM {game_table} WHERE formid=? AND plugin=? COLLATE nocase" for _ in range(batch_len)]
        return " UNION ALL ".join(selects)

    @staticmethod
    async def _query_single_database(
        db_path: Path,
        conn: aiosqlite.Connection,
        query: str,
        params: list[str],
    ) -> list[tuple[str, str, str]]:
        """Query a single database and return results.

        Args:
            db_path: Path to the database file.
            conn: Active database connection.
            query: SQL query to execute.
            params: Query parameters.

        Returns:
            List of (formid, plugin, entry) tuples.

        """
        results: list[tuple[str, str, str]] = []
        try:
            async with conn.execute(query, params) as cursor:
                async for row in cursor:
                    formid, plugin, entry = row
                    results.append((formid, plugin, entry))
        except (aiosqlite.Error, OSError) as e:
            logger.error(f"Query error in {db_path}: {e}")
        return results

    def _merge_batch_results(
        self,
        all_db_results: list[list[tuple[str, str, str]] | BaseException],
        original_key_lookup: dict[tuple[str, str], list[tuple[str, str]]],
        results: dict[tuple[str, str], str],
    ) -> None:
        """Merge database query results into the results dictionary.

        Maps database-returned values back to the caller's original keys
        to ensure consistent casing in result dictionary keys. Handles multiple
        input keys that normalize to the same case-insensitive key.

        Args:
            all_db_results: Results from parallel database queries.
            original_key_lookup: Map from (formid, lowercase_plugin) to list of original keys.
            results: Dictionary to populate with results (modified in place).

        """
        for db_result in all_db_results:
            if isinstance(db_result, BaseException):
                logger.warning(f"Database query failed: {db_result}")
                continue

            entries: list[tuple[str, str, str]] = db_result
            for db_formid, db_plugin, entry in entries:
                # Look up the original caller's keys using case-insensitive match
                lookup_key = (db_formid, db_plugin.lower())
                original_keys = original_key_lookup.get(lookup_key)

                if original_keys is None:
                    logger.warning(f"No original key found for database result: {db_formid}:{db_plugin}")
                    continue

                # Cache the result once using the normalized key (only if not already cached)
                # This ensures consistency with "first match wins" logic used for results
                if lookup_key not in self.query_cache:
                    self.query_cache[lookup_key] = entry

                # Insert result for ALL original keys that normalized to this lookup key
                for original_key in original_keys:
                    if original_key not in results:
                        results[original_key] = entry

    async def get_entries_batch(
        self,
        formid_plugin_pairs: Sequence[tuple[str, str]],
        batch_size: int = 100,
    ) -> dict[tuple[str, str], str]:
        """Fetch entries in batch from the database with optimized parallel queries.

        Retrieves data for multiple form ID/plugin pairs efficiently using:
        - Cache-first approach to maximize cache hits
        - UNION ALL queries for better SQLite index utilization
        - Parallel queries across all database files using asyncio.gather
        - Adaptive batch sizing based on input size

        Args:
            formid_plugin_pairs: A sequence of (form ID, plugin) tuples.
            batch_size: Maximum number of pairs to process in a single
                batch when querying databases. Defaults to 100.

        Returns:
            A dictionary mapping (form ID, plugin) pairs to their entries.

        """
        results: dict[tuple[str, str], str] = {}

        # First check cache for all pairs (case-insensitive plugin matching)
        uncached_pairs: list[tuple[str, str]] = []
        for formid, plugin in formid_plugin_pairs:
            # Normalize cache key with lowercase plugin for case-insensitive matching
            cache_key = (formid, plugin.lower())
            if cache_key in self.query_cache:
                results[formid, plugin] = self.query_cache[cache_key]
            else:
                uncached_pairs.append((formid, plugin))

        if not uncached_pairs:
            return results

        # Query databases for uncached pairs
        game_table = GlobalRegistry.get_game()

        # Adaptive batch sizing: smaller batches for small inputs
        if len(uncached_pairs) < 50:
            effective_batch_size = len(uncached_pairs)
        elif len(uncached_pairs) > 500:
            effective_batch_size = max(batch_size, 200)
        else:
            effective_batch_size = batch_size

        # Process in batches with parallel database queries
        for i in range(0, len(uncached_pairs), effective_batch_size):
            batch = uncached_pairs[i : i + effective_batch_size]

            # Build lookup map: (formid, lowercase_plugin) -> list of original (formid, plugin) keys
            # Multiple input pairs may normalize to the same case-insensitive key
            # (e.g., "Fallout4.esm" and "FALLOUT4.ESM"), so we track all of them
            original_key_lookup: dict[tuple[str, str], list[tuple[str, str]]] = {}
            for fid, plug in batch:
                normalized_key = (fid, plug.lower())
                if normalized_key not in original_key_lookup:
                    original_key_lookup[normalized_key] = []
                original_key_lookup[normalized_key].append((fid, plug))

            # Build optimized UNION ALL query
            query = self._build_union_all_query(game_table, len(batch))

            # Flatten parameters
            params = [item for pair in batch for item in pair]

            # Query ALL databases in PARALLEL using asyncio.gather
            query_tasks = [
                AsyncDatabasePool._query_single_database(db_path, conn, query, params) for db_path, conn in self.connections.items()
            ]

            # Execute all database queries concurrently
            all_db_results = await asyncio.gather(*query_tasks, return_exceptions=True)

            # Merge results from all databases using helper method
            self._merge_batch_results(all_db_results, original_key_lookup, results)

        return results
