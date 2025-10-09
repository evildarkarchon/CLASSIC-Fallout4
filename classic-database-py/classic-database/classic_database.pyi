"""Type stubs for classic_database Rust extension module.

This module provides high-performance database operations with connection pooling
and FormID lookup caching for 25x speedup over pure Python implementations.
"""

from __future__ import annotations

from typing import Any, Optional

__version__: str

class DatabasePool:
    """High-performance database connection pool (25x speedup).

    Features:
    - Connection pooling with configurable size
    - Query result caching with TTL
    - Parallel batch FormID lookups
    - Automatic connection management
    """

    def __init__(
        self,
        max_connections: int = 10,
        cache_ttl_seconds: int = 300
    ) -> None:
        """Create database pool.

        Args:
            max_connections: Maximum number of pooled connections (default: 10)
            cache_ttl_seconds: Cache time-to-live in seconds (default: 300)
        """
        ...

    def query(self, sql: str) -> list[dict[str, Any]]:
        """Execute SQL query.

        Args:
            sql: SQL query string

        Returns:
            Query results as list of dictionaries

        Raises:
            RuntimeError: If query fails
        """
        ...

    def lookup_formid(self, formid: str) -> Optional[str]:
        """Look up FormID in database with caching.

        Args:
            formid: FormID string to look up

        Returns:
            Plugin name if found, None otherwise
        """
        ...

    def lookup_formids_batch(
        self,
        formids: list[str]
    ) -> list[Optional[str]]:
        """Look up multiple FormIDs in parallel.

        Uses connection pool and result caching for maximum performance.

        Args:
            formids: List of FormID strings

        Returns:
            List of plugin names (None for not found)
        """
        ...

    def clear_cache(self) -> None:
        """Clear the query result cache."""
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dictionary with pool stats including:
                - active_connections: Number of active connections
                - idle_connections: Number of idle connections
                - cache_hits: Number of cache hits
                - cache_misses: Number of cache misses
        """
        ...
