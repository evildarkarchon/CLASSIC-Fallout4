"""Type stubs for classic_database.

Python bindings for classic-database-core, providing high-performance SQLite
database operations with connection pooling and TTL-based caching. This module
offers 25x speedup over Python's sqlite3 for FormID lookups and batch queries.

Architecture:
    - classic-database-core: Business logic (connection pooling, query execution)
    - classic-database-py: Python bindings (this module - PyO3 adapters)

Features:
    - Thread-safe connection pooling
    - TTL-based query result caching
    - Batch query optimization
    - Automatic connection management
    - Query statistics and monitoring
    - 25x speedup over Python SQLite

Usage:
    from classic_database import RustDatabasePool

    # Create database pool
    pool = RustDatabasePool("formids.db", max_connections=4)
    pool.initialize()

    # Single lookup
    entry = pool.get_entry("00012E46")

    # Batch lookup (optimized)
    results = pool.batch_lookup(["00012E46", "FF000800", "00014D11"])

    # Cleanup
    pool.close()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__version__: str

class RustDatabasePool:
    """High-performance database pool with TTL caching.

    Thread-safe SQLite connection pool optimized for FormID lookups and batch queries.
    Provides automatic connection management, query caching, and performance monitoring.

    The RustDatabasePool manages multiple SQLite connections in a pool, allowing
    concurrent database access without blocking. It includes intelligent caching
    with configurable TTL to reduce redundant database queries.

    Key features:
    - Connection pooling for concurrency
    - TTL-based query caching
    - Batch query optimization
    - Thread-safe operations
    - Automatic connection recycling
    - Query statistics tracking
    """

    def __init__(self, db_path: str | Path, max_connections: int = 4) -> None:
        """Create a new database pool.

        Initializes the connection pool with the specified maximum number of
        connections. Connections are created lazily as needed.

        Args:
            db_path: Path to the SQLite database file (string or pathlib.Path)
            max_connections: Maximum number of pooled connections (default: 4)
                           Recommended: Number of CPU cores for optimal performance

        Example:
            >>> pool = RustDatabasePool("formids.db", max_connections=8)
            >>> pool.initialize()
        """

    def initialize(self) -> None:
        """Initialize the database pool and prepare connections.

        Opens the database file and creates the initial connection pool.
        Must be called before performing any database operations.

        Raises:
            IOError: If database file cannot be opened
            sqlite3.Error: If database is corrupted or invalid

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
        """

    def close(self) -> None:
        """Close all database connections and clear cache.

        Closes all pooled connections and clears the query cache. Should be
        called when the pool is no longer needed to release resources.

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> # ... use pool ...
            >>> pool.close()
        """

    def get_entry(self, formid: str) -> dict[str, Any] | None:
        """Lookup a single FormID in the database.

        Queries the database for a FormID entry. Uses caching to avoid
        redundant database queries for recently accessed FormIDs.

        Args:
            formid: FormID to lookup (e.g., "00012E46", 8-character hex string)

        Returns:
            Database entry as dictionary with all fields, or None if not found
            Typical fields: 'formid', 'plugin', 'record_type', 'editor_id', etc.

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> entry = pool.get_entry("00012E46")
            >>> if entry:
            ...     print(f"Plugin: {entry['plugin']}")
        """

    def batch_lookup(self, formids: list[str]) -> dict[str, dict[str, Any]]:
        """Lookup multiple FormIDs in a single optimized query.

        Performs a batch lookup of multiple FormIDs using a single SQL query
        with IN clause. This is significantly faster than individual lookups
        for large batches.

        Args:
            formids: List of FormIDs to lookup (8-character hex strings)

        Returns:
            Dictionary mapping FormIDs to their database entries
            Missing FormIDs will not appear in the result dictionary

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> results = pool.batch_lookup(["00012E46", "FF000800", "00014D11"])
            >>> for formid, entry in results.items():
            ...     print(f"{formid}: {entry['plugin']}")
        """

    def get_entries_batch(self, formids: list[str]) -> list[dict[str, Any] | None]:
        """Get entries for multiple FormIDs, preserving order.

        Similar to batch_lookup but returns results in the same order as the
        input FormID list. Missing FormIDs are represented as None.

        Args:
            formids: List of FormIDs to lookup (preserves order)

        Returns:
            List of database entries (None for missing FormIDs)
            Length matches input list, order preserved

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> formids = ["00012E46", "INVALID", "00014D11"]
            >>> entries = pool.get_entries_batch(formids)
            >>> for formid, entry in zip(formids, entries):
            ...     if entry:
            ...         print(f"{formid}: {entry['plugin']}")
            ...     else:
            ...         print(f"{formid}: Not found")
        """

    def get_game_table(self) -> str:
        """Get the current game table name being queried.

        Returns the name of the database table currently used for queries.
        Different games use different tables (e.g., 'fallout4', 'skyrim').

        Returns:
            Current game table name (e.g., 'fallout4')

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> print(pool.get_game_table())
            'fallout4'
        """

    def set_game_table(self, table_name: str) -> None:
        """Set the game table to query (e.g., 'fallout4', 'skyrim').

        Changes the database table used for all subsequent queries.
        Clears the cache when changing tables.

        Args:
            table_name: Database table name for the game

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> pool.set_game_table("skyrim")  # Switch to Skyrim database
        """

    def clear_cache(self) -> None:
        """Clear the query cache to free memory.

        Removes all cached query results. Useful for freeing memory or
        forcing fresh database queries.

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> # ... perform many queries ...
            >>> pool.clear_cache()  # Clear cached results
        """

    def set_cache_ttl(self, ttl_seconds: int) -> None:
        """Set cache entry time-to-live.

        Configures how long query results are cached before being
        automatically evicted. Set to 0 to disable caching.

        Args:
            ttl_seconds: Cache TTL in seconds (0 to disable caching)
                        Default: 300 seconds (5 minutes)
                        Recommended: 60-600 seconds depending on use case

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> pool.set_cache_ttl(120)  # Cache for 2 minutes
        """

    def optimize(self) -> None:
        """Run database optimization (VACUUM, ANALYZE).

        Performs SQLite VACUUM and ANALYZE operations to optimize database
        performance. Should be run periodically on large databases.

        Note: This operation may take significant time on large databases
              and will block other operations.

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> pool.optimize()  # Optimize database
        """

    def get_stats(self) -> dict[str, Any]:
        """Get pool and cache statistics.

        Returns detailed statistics about connection pool usage and cache
        performance for monitoring and debugging.

        Returns:
            Dictionary with statistics:
                - 'active_connections': Currently active connections
                - 'total_connections': Total connections in pool
                - 'cache_size': Number of cached entries
                - 'cache_hits': Number of cache hits
                - 'cache_misses': Number of cache misses
                - 'cache_hit_rate': Cache hit rate (0.0-1.0)

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> # ... perform queries ...
            >>> stats = pool.get_stats()
            >>> print(f"Cache hit rate: {stats['cache_hit_rate']:.1%}")
            >>> print(f"Active connections: {stats['active_connections']}")
        """

    def get_max_connections(self) -> int:
        """Get the current maximum number of connections.

        Returns:
            Maximum number of connections in the pool

        Example:
            >>> pool = RustDatabasePool("formids.db", max_connections=8)
            >>> pool.initialize()
            >>> print(pool.get_max_connections())
            8
        """

    def set_max_connections(self, max_connections: int) -> None:
        """Set the maximum number of connections.

        Adjusts the connection pool size. New connections are created as
        needed up to the new limit. Excess connections are closed gracefully.

        Args:
            max_connections: New maximum number of connections
                           Recommended: Number of CPU cores

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> pool.set_max_connections(16)  # Increase pool size
        """

    def recalculate_max_connections(self) -> int:
        """Recalculate optimal maximum connections based on CPU cores.

        Automatically determines the optimal connection pool size based on
        the number of available CPU cores and updates the pool configuration.

        Returns:
            New maximum connections value

        Example:
            >>> pool = RustDatabasePool("formids.db")
            >>> pool.initialize()
            >>> optimal = pool.recalculate_max_connections()
            >>> print(f"Optimal connections: {optimal}")
        """
