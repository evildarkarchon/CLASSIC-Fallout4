"""Rust-accelerated async database pool wrapper.

This module provides a Python wrapper around the high-performance Rust
DatabasePool implementation, maintaining API compatibility with
AsyncDatabasePool while leveraging Rust's performance benefits (25x faster).

Async/Sync Behavior:
    All database methods are TRUE ASYNC - they await Rust coroutines and
    do NOT block:
    - initialize() - Awaits Rust database connection setup
    - get_entry() - Awaits Rust database query
    - get_entries_batch() - Awaits parallel Rust batch queries

Usage in async context:
    ```python
    async def lookup_formid(formid: str, plugin: str):
        pool = RustAsyncDatabasePool()
        await pool.initialize()
        result = await pool.get_entry(formid, plugin)
        return result
    ```

CLI Usage:
    ```python
    import asyncio
    from ClassicLib.Database import RustAsyncDatabasePool

    async def main():
        pool = RustAsyncDatabasePool()
        await pool.initialize()
        result = await pool.get_entry(formid, plugin)
        print(result)

    asyncio.run(main())
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from ClassicLib.core.constants import get_all_db_paths_async
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.integration.exceptions import RustDatabaseError, RustError
from ClassicLib.integration.factory import get_component

if TYPE_CHECKING:
    import types
    from collections.abc import Sequence

    from classic_database import DatabasePool as DatabasePoolType
else:
    DatabasePoolType = None  # type: ignore[misc,assignment]

# Resolve required Rust DatabasePool binding
DatabasePool = get_component("classic_database", "DatabasePool")

# Detect Rust-specific exception types for classic_database
try:
    _rust_db_error = get_component("classic_database", "RustDatabaseError")
except ImportError:
    _rust_db_error = None
try:
    _rust_db_io_error = get_component("classic_database", "RustDatabaseIOError")
except ImportError:
    _rust_db_io_error = None
try:
    _rust_db_query_error = get_component("classic_database", "RustDatabaseQueryError")
except ImportError:
    _rust_db_query_error = None


def _get_rust_exception_types() -> tuple[tuple[type, ...], tuple[type, ...], tuple[type, ...]]:
    """Get tuple of Rust exception types to catch.

    Returns:
        A tuple containing three tuples of exception types:
        - DatabaseError types (RustDatabaseError and module-specific variants)
        - IOError types (RustError and RustDatabaseIOError variants)
        - QueryError types (RustError and RustDatabaseQueryError variants)

    """
    db_errors: tuple[type, ...] = (RustDatabaseError,)
    io_errors: tuple[type, ...] = (RustError,)
    query_errors: tuple[type, ...] = (RustError,)

    # Add module-specific exceptions if available
    if _rust_db_error:
        db_errors = (RustDatabaseError, _rust_db_error)
    if _rust_db_io_error:
        io_errors = (RustError, _rust_db_io_error)
    if _rust_db_query_error:
        query_errors = (RustError, _rust_db_query_error)

    return db_errors, io_errors, query_errors


# Get exception type tuples at module level for use in exception handlers
db_errors, io_errors, query_errors = _get_rust_exception_types()


class RustAsyncDatabasePool:
    """Async wrapper around the Rust database pool implementation.

    Provides the same interface as AsyncDatabasePool but uses the
    high-performance Rust backend for all operations. Approximately
    25x faster than the pure Python implementation.

    Attributes:
        max_connections: Global connection budget distributed across active databases.
        cache_ttl: Time-to-live for cache entries in seconds.
        connections: Dummy dict for API compatibility.
        query_cache: Dummy dict for API compatibility.

    Example:
        >>> pool = RustAsyncDatabasePool(max_connections=10, cache_ttl_seconds=300)
        >>> await pool.initialize()
        >>> result = await pool.get_entry("00012345", "Fallout4.esm")
        >>> await pool.close()

    Raises:
        ImportError: If the Rust database module is not available.

    """

    def __init__(
        self,
        max_connections: int = 10,
        cache_ttl_seconds: int = 300,
        cache_capacity: int | None = None,
        cleanup_threshold: int | None = None,
        cleanup_interval_seconds: int | None = None,
    ) -> None:
        """Initialize the Rust database pool wrapper.

        Args:
            max_connections: Global connection budget distributed across active databases.
            cache_ttl_seconds: TTL for cache entries in seconds.
            cache_capacity: Optional maximum number of cache entries.
            cleanup_threshold: Optional operation threshold for proactive cleanup.
            cleanup_interval_seconds: Optional minimum proactive cleanup interval in seconds.

        Raises:
            ImportError: If the Rust database module is not available.

        """
        self.max_connections = max_connections
        self.cache_ttl = cache_ttl_seconds
        self.cache_capacity = cache_capacity
        self.cleanup_threshold = cleanup_threshold
        self.cleanup_interval_seconds = cleanup_interval_seconds

        # Get game table from GlobalRegistry
        game_table = GlobalRegistry.get_game()
        self._rust_pool: DatabasePoolType = DatabasePool(  # pyright: ignore[reportInvalidTypeForm]
            max_connections,
            cache_ttl_seconds,
            game_table,
            cache_capacity,
            cleanup_threshold,
            cleanup_interval_seconds,
        )
        logger.debug(
            "Initialized Rust database pool "
            f"(global_budget={max_connections}, ttl={cache_ttl_seconds}s, "
            f"table={game_table}, cache_capacity={cache_capacity}, "
            f"cleanup_threshold={cleanup_threshold}, cleanup_interval_seconds={cleanup_interval_seconds})"
        )

        # Compatibility attributes for existing code
        self.connections: dict[Any, Any] = {}  # Dummy for compatibility
        self.query_cache: dict[tuple[str, str], Any] = {}  # Dummy for compatibility
        self._initialized = False

    async def __aenter__(self) -> Self:
        """Enter async context manager.

        Returns:
            The initialized database pool instance.

        """
        await self.initialize()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, _exc_val: BaseException | None, _exc_tb: types.TracebackType | None
    ) -> None:
        """Exit async context manager, cleaning up resources.

        Args:
            exc_type: Exception type if an exception was raised.
            _exc_val: Exception instance if an exception was raised.
            _exc_tb: Traceback if an exception was raised.

        """
        await self.close()

    async def initialize(self) -> None:
        """Initialize database connections.

        Sets up database connections using the Rust backend. This is a true
        async operation that does not block.

        Raises:
            RustDatabaseError: If database initialization fails.

        """
        if self._initialized:
            return

        # Get database paths
        db_paths_str = [str(path) for path in await get_all_db_paths_async() if path.is_file()]

        if db_paths_str:
            # Await Rust coroutine - true async, no blocking!
            await self._rust_pool.initialize(db_paths_str)
            logger.debug(f"Initialized {len(db_paths_str)} database connections in Rust pool")

        self._initialized = True

    async def close(self) -> None:
        """Close the database connection pool.

        Properly closes all SQLite connections and clears caches. This is
        important for WAL mode databases to ensure the WAL file is checkpointed
        back to the main database, removing .db-wal and .db-shm files.
        """
        if not self._initialized:
            return

        try:
            # Call Rust close() to properly close all SQLite connections
            # This ensures WAL mode checkpoints are performed
            await self._rust_pool.close()
            logger.debug("Rust database pool connections closed successfully")
        except (RustDatabaseError, RustError) as e:
            logger.warning(f"Error during Rust database pool close: {e}")
        finally:
            self._initialized = False

    async def get_entry(self, formid: str, plugin: str) -> dict[str, Any] | None:
        """Retrieve an entry from the database.

        Args:
            formid: The unique form identifier.
            plugin: The plugin associated with the entry.

        Returns:
            The entry dict if found, otherwise None.

        Raises:
            RustDatabaseError: If the query fails.

        """
        if not self._initialized:
            await self.initialize()

        game_table = GlobalRegistry.get_game()

        # Await Rust coroutine - true async, no blocking!
        return await self._rust_pool.get_entry(formid, plugin, game_table)

    async def get_entries_batch(
        self,
        formid_plugin_pairs: Sequence[tuple[str, str]],
        batch_size: int = 100,
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """Fetch entries in batch from the database.

        Args:
            formid_plugin_pairs: A sequence of (form ID, plugin) tuples.
            batch_size: Size of batches for querying (passed to Rust backend).

        Returns:
            A dictionary mapping (form ID, plugin) pairs to their entry dicts.

        Raises:
            RustDatabaseError: If the batch query fails.

        """
        if not self._initialized:
            await self.initialize()

        if not formid_plugin_pairs:
            return {}

        game_table = GlobalRegistry.get_game()

        # Convert to list for Rust
        pairs_list = list(formid_plugin_pairs)

        # Await Rust coroutine - true async, no blocking!
        try:
            # Try the new batch_lookup method first
            return await self._rust_pool.batch_lookup(pairs_list, game_table)
        except AttributeError:
            # Fall back to get_entries_batch if batch_lookup doesn't exist
            rust_results = await self._rust_pool.get_entries_batch(pairs_list, game_table, batch_size)
            # Convert results to expected format
            results: dict[tuple[str, str], dict[str, Any]] = {}
            for formid, plugin in pairs_list:
                key = f"{formid}:{plugin}"
                if key in rust_results:
                    results[formid, plugin] = rust_results[key]
            return results

    def clear_cache(self, expired_only: bool = False) -> int:
        """Clear cache entries.

        Args:
            expired_only: If True, only clear expired entries.

        Returns:
            The number of entries removed from the cache.

        """
        return self._rust_pool.clear_cache(expired_only)

    def set_cache_ttl(self, seconds: int) -> None:
        """Set the cache time-to-live.

        Args:
            seconds: The duration in seconds for the cache TTL.

        """
        self._rust_pool.set_cache_ttl(seconds)

    def get_cache_capacity(self) -> int:
        """Get configured cache capacity."""
        return self._rust_pool.get_cache_capacity()

    def set_cache_capacity(self, capacity: int) -> None:
        """Set cache capacity."""
        self._rust_pool.set_cache_capacity(capacity)

    def get_cache_cleanup_threshold(self) -> int:
        """Get proactive cleanup threshold (operation count)."""
        return self._rust_pool.get_cache_cleanup_threshold()

    def set_cache_cleanup_threshold(self, threshold: int) -> None:
        """Set proactive cleanup threshold (operation count)."""
        self._rust_pool.set_cache_cleanup_threshold(threshold)

    def get_cache_cleanup_interval(self) -> int:
        """Get proactive cleanup interval in seconds."""
        return self._rust_pool.get_cache_cleanup_interval()

    def set_cache_cleanup_interval(self, seconds: int) -> None:
        """Set proactive cleanup interval in seconds."""
        self._rust_pool.set_cache_cleanup_interval(seconds)

    def get_max_connections(self) -> int | None:
        """Get configured global connection budget."""
        return self._rust_pool.get_max_connections()

    def set_max_connections(self, max_connections: int) -> None:
        """Update global connection budget configuration.

        This is config-only until `rebalance_connections()` or next initialize.
        """
        self.max_connections = max_connections
        self._rust_pool.set_max_connections(max_connections)

    async def rebalance_connections(self) -> None:
        """Explicitly rebuild active pools with current global budget."""
        if hasattr(self._rust_pool, "rebalance_connections"):
            await self._rust_pool.rebalance_connections()
            return

        logger.debug("Rust pool does not expose rebalance_connections(); skipping explicit rebalance")

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics.

        Returns:
            A dictionary containing pool performance metrics.

        """
        return self._rust_pool.get_stats()

    async def optimize(self) -> None:
        """Optimize the underlying database.

        Runs VACUUM or ANALYZE commands to improve query performance.

        Raises:
            RustDatabaseError: If optimization fails.

        """
        await self._rust_pool.optimize()

    def set_game_table(self, table: str) -> None:
        """Set the game table for queries.

        Args:
            table: The name of the game table.

        """
        if hasattr(self._rust_pool, "set_game_table"):
            self._rust_pool.set_game_table(table)
            logger.debug(f"Set game table to: {table}")

    def get_game_table(self) -> str:
        """Get the current game table.

        Returns:
            The current game table name.

        """
        if hasattr(self._rust_pool, "get_game_table"):
            return self._rust_pool.get_game_table()
        return GlobalRegistry.get_game()


def is_rust_available() -> bool:
    """Check if Rust database pool is available.

    Returns:
        True if Rust implementation is available, False otherwise.

    """
    return True
