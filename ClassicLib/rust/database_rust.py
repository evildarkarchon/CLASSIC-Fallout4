"""
Python wrapper for Rust database pool - Phase 4 implementation.

This module provides a backward-compatible interface for the high-performance
Rust database pool implementation, maintaining the same API as AsyncDatabasePool
while leveraging Rust's performance benefits.
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

try:
    import classic_core
    RustDatabasePool = classic_core.database.RustDatabasePool
    RUST_AVAILABLE = True
except (ImportError, AttributeError):
    RUST_AVAILABLE = False
    RustDatabasePool = None

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import DB_PATHS
from ClassicLib.Logger import logger


class DatabasePoolManager:
    """
    Singleton manager for RustDatabasePool instances.

    Provides backward compatibility with the existing AsyncDatabasePool
    interface while using the high-performance Rust implementation.
    """

    _instance: ClassVar[DatabasePoolManager | None] = None
    _pool: RustAsyncDatabasePool | None = None
    _lock: ClassVar[asyncio.Lock | None] = None

    def __new__(cls) -> DatabasePoolManager:
        """Ensure only one instance of DatabasePoolManager exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = None
        return cls._instance

    async def get_pool(self) -> RustAsyncDatabasePool:
        """
        Get or create the singleton database pool.

        Returns:
            The singleton RustAsyncDatabasePool instance, initialized if necessary.
        """
        # Initialize the lock if needed (must be done in async context)
        if self._lock is None:
            self.__class__._lock = asyncio.Lock()

        async with self._lock:
            if self._pool is None:
                self._pool = RustAsyncDatabasePool()
                await self._pool.initialize()
                logger.debug("Created singleton Rust database pool")
            return self._pool

    async def close_pool(self) -> None:
        """Close the singleton database pool if it exists."""
        if self._lock is None:
            return

        async with self._lock:
            if self._pool is not None:
                await self._pool.close()
                self._pool = None
                logger.debug("Closed singleton Rust database pool")


class RustAsyncDatabasePool:
    """
    Async wrapper around the Rust database pool implementation.

    Provides the same interface as AsyncDatabasePool but uses the
    high-performance Rust backend for all operations.
    """

    def __init__(self, max_connections: int = 10, cache_ttl_seconds: int = 300) -> None:
        """
        Initialize the Rust database pool wrapper.

        Args:
            max_connections: Maximum number of database connections.
            cache_ttl_seconds: TTL for cache entries in seconds.
        """
        self.max_connections = max_connections
        self.cache_ttl = cache_ttl_seconds

        if RUST_AVAILABLE:
            # Get game table from GlobalRegistry
            game_table = GlobalRegistry.get_game()
            self._rust_pool = RustDatabasePool(max_connections, cache_ttl_seconds, game_table)
            logger.debug(f"Initialized Rust database pool (max_conn={max_connections}, ttl={cache_ttl_seconds}s, table={game_table})")
        else:
            raise ImportError("Rust database module not available. Please rebuild with maturin.")

        # Compatibility attributes for existing code
        self.connections = {}  # Dummy for compatibility
        self.query_cache = {}  # Dummy for compatibility
        self._initialized = False

    async def __aenter__(self) -> RustAsyncDatabasePool:
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def initialize(self) -> None:
        """
        Initialize database connections.

        Now uses true async - Rust returns Python coroutine.
        """
        if self._initialized:
            return

        # Get database paths
        db_paths_str = [str(path) for path in DB_PATHS if path.is_file()]

        if db_paths_str:
            # Await Rust coroutine - true async, no blocking!
            await self._rust_pool.initialize(db_paths_str)
            logger.debug(f"Initialized {len(db_paths_str)} database connections in Rust pool")

        self._initialized = True

    async def close(self) -> None:
        """Close all database connections."""
        if not self._initialized:
            return

        # Await Rust coroutine - true async, no blocking!
        await self._rust_pool.close()
        self._initialized = False
        logger.debug("Closed Rust database pool connections")

    async def get_entry(self, formid: str, plugin: str) -> str | None:
        """
        Fetch a specific FormID entry from the database.

        Args:
            formid: The FormID to look up.
            plugin: The plugin name.

        Returns:
            The entry string if found, None otherwise.
        """
        if not self._initialized:
            await self.initialize()

        game_table = GlobalRegistry.get_game()

        # Await Rust coroutine - true async, no blocking!
        # Multiple operations can run concurrently via Python's event loop
        result = await self._rust_pool.get_entry(formid, plugin, game_table)

        return result

    async def get_entries_batch(
        self,
        formid_plugin_pairs: list[tuple[str, str]],
        batch_size: int = 100
    ) -> dict[tuple[str, str], str]:
        """
        Fetch multiple FormID entries in batch.

        Args:
            formid_plugin_pairs: List of (formid, plugin) tuples.
            batch_size: Maximum batch size for queries.

        Returns:
            Dictionary mapping (formid, plugin) tuples to entry strings.
        """
        if not self._initialized:
            await self.initialize()

        if not formid_plugin_pairs:
            return {}

        game_table = GlobalRegistry.get_game()

        # Await Rust coroutine - true async, no blocking!
        try:
            # Try the new batch_lookup method first
            rust_results = await self._rust_pool.batch_lookup(formid_plugin_pairs, game_table)
            return rust_results
        except AttributeError:
            # Fall back to get_entries_batch if batch_lookup doesn't exist
            rust_results = await self._rust_pool.get_entries_batch(
                formid_plugin_pairs,
                game_table,
                batch_size
            )

            # Convert results to expected format
            results = {}
            for (formid, plugin) in formid_plugin_pairs:
                key = f"{formid}:{plugin}"
                if key in rust_results:
                    results[formid, plugin] = rust_results[key]

            return results

    async def clear_cache(self, expired_only: bool = False) -> int:
        """
        Clear cache entries.

        Args:
            expired_only: If True, only clear expired entries.

        Returns:
            Number of entries cleared.
        """
        return self._rust_pool.clear_cache(expired_only)

    async def set_cache_ttl(self, seconds: int) -> None:
        """
        Set cache TTL in seconds.

        Args:
            seconds: New TTL value in seconds.
        """
        self._rust_pool.set_cache_ttl(seconds)

    async def get_stats(self) -> dict[str, Any]:
        """
        Get pool statistics.

        Returns:
            Dictionary containing pool statistics.
        """
        return self._rust_pool.get_stats()

    async def optimize(self) -> None:
        """Optimize database connections (VACUUM and ANALYZE)."""
        await self._rust_pool.optimize()

    def set_game_table(self, table: str) -> None:
        """
        Set the game table name dynamically.

        Args:
            table: The table name (e.g., 'Fallout4' or 'Skyrim').
        """
        if hasattr(self._rust_pool, 'set_game_table'):
            self._rust_pool.set_game_table(table)
            logger.debug(f"Set game table to: {table}")

    def get_game_table(self) -> str:
        """
        Get the current game table name.

        Returns:
            The current table name.
        """
        if hasattr(self._rust_pool, 'get_game_table'):
            return self._rust_pool.get_game_table()
        return GlobalRegistry.get_game()


# Backward compatibility alias
AsyncDatabasePool = RustAsyncDatabasePool


def get_database_pool_implementation() -> type:
    """
    Get the appropriate database pool implementation.

    Returns:
        RustAsyncDatabasePool if Rust is available, otherwise raises ImportError.
    """
    if RUST_AVAILABLE:
        return RustAsyncDatabasePool
    # Fall back to Python implementation if available
    try:
        from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool as PythonAsyncDatabasePool
        return PythonAsyncDatabasePool
    except ImportError:
        raise ImportError(
            "Neither Rust nor Python database pool implementation available. "
            "Please rebuild with maturin or check your installation."
        )
