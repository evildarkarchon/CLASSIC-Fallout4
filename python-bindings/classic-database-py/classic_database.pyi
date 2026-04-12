"""Type stubs for classic_database.

Python bindings for classic-database-core, providing high-performance async SQLite
database operations with connection pooling and TTL-based caching. This module
offers significant speedup over Python's sqlite3 for FormID lookups and batch queries.

Architecture:
    - classic-database-core: Business logic (connection pooling, query execution)
    - classic-database-py: Python bindings (this module - PyO3 adapters)

Features:
    - Thread-safe async connection pooling
    - TTL-based query result caching
    - Batch query optimization
    - Automatic connection management
    - Query statistics and monitoring
    - Async/await support with pyo3-async-runtimes

Usage:
    import asyncio
    from classic_database import DatabasePool

    async def main():
        # Create database pool
        pool = DatabasePool(max_connections=8, cache_ttl_seconds=300, game_table="Fallout4")

        # Initialize with database paths
        await pool.initialize(["path/to/db1.db", "path/to/db2.db"])

        # Single lookup
        entry = await pool.get_entry("00012E46", "MyPlugin.esp")

        # Batch lookup (optimized)
        pairs = [("00012E46", "Plugin1.esp"), ("FF000800", "Plugin2.esp")]
        results = await pool.get_entries_batch(pairs)

        # Get stats
        stats = pool.get_stats()
        print(f"Cache hit rate: {stats['cache_hit_rate']}%")

    asyncio.run(main())
"""

from typing import Any

__version__: str
DEFAULT_CACHE_TTL: int
BATCH_CACHE_TTL: int
MAX_CACHE_TTL: int
DEFAULT_QUERY_CACHE_CAPACITY: int
DEFAULT_CACHE_CLEANUP_THRESHOLD: int
DEFAULT_CACHE_CLEANUP_INTERVAL: int

def get_default_cache_ttl() -> int: ...
def get_batch_cache_ttl() -> int: ...
def get_max_cache_ttl() -> int: ...
def get_default_query_cache_capacity() -> int: ...
def get_default_cache_cleanup_threshold() -> int: ...
def get_default_cache_cleanup_interval() -> int: ...

class DatabasePool:
    """High-performance async database pool with TTL caching.

    Thread-safe SQLite connection pool optimized for FormID lookups and batch queries.
    Provides automatic connection management, query caching, and performance monitoring.
    All database operations are async and return coroutines that must be awaited.

    The DatabasePool manages multiple SQLite connections in a pool, allowing
    concurrent database access without blocking. It includes intelligent caching
    with configurable TTL to reduce redundant database queries.

    Key features:
    - Async connection pooling for concurrency
    - TTL-based query caching
    - Batch query optimization
    - Thread-safe operations
    - Automatic connection recycling
    - Query statistics tracking
    """

    def __init__(
        self,
        max_connections: int | None = None,
        cache_ttl_seconds: int | None = 300,
        game_table: str | None = None,
        cache_capacity: int | None = None,
        cleanup_threshold: int | None = None,
        cleanup_interval_seconds: int | None = None,
    ) -> None:
        """Create a new database pool.

        Initializes the connection pool configuration. Connections are created
        lazily when initialize() is called with database paths.

        Args:
            max_connections: Global connection budget shared across active database pools
                (default: auto-calculated based on CPU cores)
            cache_ttl_seconds: Cache TTL in seconds (default: 300). Set to None for default.
            game_table: Database table name for the game (default: "Fallout4")
            cache_capacity: Maximum number of cache entries before eviction policy applies.
            cleanup_threshold: Number of lookup operations before proactive cleanup is considered.
            cleanup_interval_seconds: Minimum interval between proactive cleanup runs.

        Example:
            >>> pool = DatabasePool(max_connections=8, cache_ttl_seconds=600, game_table="Skyrim")

        """

    async def initialize(self, db_paths: list[str]) -> None:
        """Initialize the database pool with database file paths.

        Opens the database files and creates the connection pool.
        Must be called before performing any database operations.

        Args:
            db_paths: List of paths to SQLite database files

        Raises:
            IOError: If database files cannot be opened
            sqlite3.Error: If database is corrupted or invalid

        Example:
            >>> pool = DatabasePool()
            >>> await pool.initialize(["formids.db", "extra.db"])

        """

    async def get_entry(
        self, formid: str, plugin: str, table: str | None = None
    ) -> dict[str, Any] | None:
        """Lookup a single FormID in the database.

        Queries the database for a FormID entry. Uses caching to avoid
        redundant database queries for recently accessed FormIDs.

        Args:
            formid: FormID to lookup (e.g., "00012E46", 8-character hex string)
            plugin: Plugin name (e.g., "MyPlugin.esp")
            table: Optional table name override (uses game_table if not specified)

        Returns:
            Database entry as dictionary with all fields, or None if not found

        Example:
            >>> pool = DatabasePool()
            >>> await pool.initialize(["formids.db"])
            >>> entry = await pool.get_entry("00012E46", "MyPlugin.esp")
            >>> if entry:
            ...     print(f"Found: {entry}")

        """

    async def get_entries_batch(
        self,
        formid_plugin_pairs: list[tuple[str, str]],
        table: str | None = None,
        batch_size: int | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Batch lookup multiple FormID-plugin pairs in optimized queries.

        Performs batch lookups using optimized SQL queries with proper batching.
        This is significantly faster than individual lookups for large batches.

        Args:
            formid_plugin_pairs: List of (formid, plugin) tuples to lookup
            table: Optional table name override (uses game_table if not specified)
            batch_size: Number of entries per batch (default: 100)

        Returns:
            Dictionary mapping "formid:plugin" keys to their database entries
            Missing entries will not appear in the result dictionary

        Example:
            >>> pool = DatabasePool()
            >>> await pool.initialize(["formids.db"])
            >>> pairs = [("00012E46", "Plugin1.esp"), ("FF000800", "Plugin2.esp")]
            >>> results = await pool.get_entries_batch(pairs, batch_size=100)
            >>> for key, entry in results.items():
            ...     print(f"{key}: {entry}")

        """

    def get_game_table(self) -> str:
        """Get the current game table name being queried.

        Returns:
            Current game table name (e.g., "Fallout4")

        Example:
            >>> pool = DatabasePool()
            >>> print(pool.get_game_table())
            'Fallout4'

        """

    def set_game_table(self, table: str) -> None:
        """Set the game table to query (e.g., "Fallout4", "Skyrim").

        Changes the database table used for all subsequent queries.

        Args:
            table: Database table name for the game

        Example:
            >>> pool = DatabasePool()
            >>> pool.set_game_table("Skyrim")  # Switch to Skyrim database

        """

    def clear_cache(self, expired_only: bool | None = None) -> int:
        """Clear the query cache to free memory.

        Removes cached query results. Can optionally clear only expired entries.

        Args:
            expired_only: If True, only clear expired entries. If False or None, clear all.

        Returns:
            Number of entries cleared from cache

        Example:
            >>> pool = DatabasePool()
            >>> await pool.initialize(["formids.db"])
            >>> # ... perform many queries ...
            >>> cleared = pool.clear_cache()  # Clear all cached results
            >>> print(f"Cleared {cleared} entries")

        """

    def set_cache_ttl(self, seconds: int) -> None:
        """Set cache entry time-to-live.

        Configures how long query results are cached before being
        automatically evicted. Set to 0 to disable caching.

        Args:
            seconds: Cache TTL in seconds (0 to disable caching)

        Example:
            >>> pool = DatabasePool()
            >>> pool.set_cache_ttl(120)  # Cache for 2 minutes

        """

    def get_cache_capacity(self) -> int:
        """Get the maximum number of entries allowed in the query cache."""

    def set_cache_capacity(self, capacity: int) -> None:
        """Set the maximum number of entries allowed in the query cache."""

    def get_cache_cleanup_threshold(self) -> int:
        """Get proactive cleanup trigger threshold (lookup operations)."""

    def set_cache_cleanup_threshold(self, threshold: int) -> None:
        """Set proactive cleanup trigger threshold (lookup operations)."""

    def get_cache_cleanup_interval(self) -> int:
        """Get proactive cleanup minimum interval in seconds."""

    def set_cache_cleanup_interval(self, seconds: int) -> None:
        """Set proactive cleanup minimum interval in seconds."""

    def get_max_connections(self) -> int | None:
        """Get the current global connection budget.

        Returns:
            Configured global connection budget, or None if auto-calculated

        Example:
            >>> pool = DatabasePool(max_connections=8)
            >>> print(pool.get_max_connections())
            8

        """

    def set_max_connections(self, max_connections: int) -> None:
        """Set the global connection budget.

        Updates configuration for the next initialize/rebalance cycle.
        Existing pools are not rebuilt automatically.

        Args:
            max_connections: New global connection budget

        Example:
            >>> pool = DatabasePool()
            >>> pool.set_max_connections(16)  # Update config only
            >>> await pool.rebalance_connections()  # Apply immediately

        """

    def recalculate_max_connections(self) -> None:
        """Recalculate optimal global connection budget based on CPU cores.

        Automatically determines the optimal connection budget based on
        the number of available CPU cores and updates the pool configuration.

        Example:
            >>> pool = DatabasePool()
            >>> pool.recalculate_max_connections()
            >>> await pool.rebalance_connections()

        """

    async def rebalance_connections(self) -> None:
        """Rebuild active pools using the current global connection budget.

        Applies budget updates immediately to all currently tracked databases.
        """

    def get_stats(self) -> dict[str, int]:
        """Get pool and cache statistics.

        Returns detailed statistics about connection pool usage and cache
        performance for monitoring and debugging.

        Returns:
            Dictionary with statistics:
                - 'total_queries': Total number of queries executed
                - 'cache_hits': Number of cache hits
                - 'cache_misses': Number of cache misses
                - 'total_connections': Total connections in pool
                - 'active_connections': Currently active connections
                - 'cache_evictions': Entries evicted due to capacity pressure
                - 'cleanup_runs': Number of proactive cleanup runs
                - 'cleanup_removed': Entries removed by proactive cleanup
                - 'configured_connection_budget': Configured global connection budget
                - 'effective_connection_budget': Effective budget applied to active pools
                - 'active_pool_count': Number of active database pools
                - 'min_pool_allocation': Smallest per-pool allocation
                - 'max_pool_allocation': Largest per-pool allocation
                - 'allocation_spread': Difference between max and min pool allocation
                - 'stable_shape_selections': Number of stable query-shape bucket selections
                - 'stable_shape_padding_pairs': Total padded pair slots used for stable shapes
                - 'stable_shape_bucket_8': Number of 8-slot bucket selections
                - 'stable_shape_bucket_16': Number of 16-slot bucket selections
                - 'stable_shape_bucket_32': Number of 32-slot bucket selections
                - 'stable_shape_bucket_64': Number of 64-slot bucket selections
                - 'stable_shape_bucket_128': Number of 128-slot bucket selections
                - 'stable_shape_bucket_256': Number of 256-slot bucket selections
                - 'stable_shape_bucket_512': Number of 512-slot bucket selections
                - 'stable_shape_bucket_1024': Number of 1024-slot bucket selections
                - 'cache_capacity': Current cache capacity
                - 'cleanup_threshold': Current proactive cleanup operation threshold
                - 'cleanup_interval_seconds': Current proactive cleanup interval in seconds
                - 'cache_hit_rate': Cache hit rate percentage (0-100)

        Example:
            >>> pool = DatabasePool()
            >>> await pool.initialize(["formids.db"])
            >>> # ... perform queries ...
            >>> stats = pool.get_stats()
            >>> print(f"Cache hit rate: {stats['cache_hit_rate']}%")
            >>> print(f"Active connections: {stats['active_connections']}")

        """

    async def optimize(self) -> None:
        """Optimize database connections (VACUUM and ANALYZE).

        Triggers database optimization routines to improve query performance.
        """

    async def close(self) -> None:
        """Close all database connections and clear caches.

        This method should be called before application exit to ensure proper
        cleanup of SQLite connections. This is especially important when using
        WAL mode, as it ensures the WAL file is checkpointed back to the main
        database and the .db-wal and .db-shm files are removed.

        After calling close(), the pool should not be used for queries.
        Call initialize() again to reopen connections if needed.

        Example:
            >>> pool = DatabasePool()
            >>> await pool.initialize(["formids.db"])
            >>> # ... perform queries ...
            >>> await pool.close()  # Proper cleanup before exit

        """

    def is_available(self) -> bool:
        """Check if the pool has any active connections.

        Returns True if the pool has been initialized and has active connections.
        Returns False if the pool has never been initialized or has been closed.

        Returns:
            True if pool is ready for queries, False otherwise

        Example:
            >>> pool = DatabasePool()
            >>> print(pool.is_available())  # False - not initialized
            >>> await pool.initialize(["formids.db"])
            >>> print(pool.is_available())  # True - ready
            >>> await pool.close()
            >>> print(pool.is_available())  # False - closed

        """
