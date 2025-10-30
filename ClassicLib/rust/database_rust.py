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
        """
        Creates and manages a singleton instance of DatabasePoolManager.

        This method overrides the default behavior of instance creation to ensure that
        only one instance of the DatabasePoolManager class is created across the
        application. If an instance already exists, it returns the existing instance;
        otherwise, it creates and returns a new instance.

        Args:
            cls (Type[DatabasePoolManager]): The class reference for which the singleton
            instance is created.

        Returns:
            DatabasePoolManager: The singleton instance of the DatabasePoolManager class.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = None
        return cls._instance

    async def get_pool(self) -> RustAsyncDatabasePool:
        """
        Retrieves the singleton instance of the Rust asynchronous database pool. Ensures that
        only one instance of the database pool is created using an asyncio lock for thread
        safety. If the pool is uninitialized, it initializes it before returning the instance.

        Returns:
            RustAsyncDatabasePool: The single, shared instance of the Rust asynchronous
            database pool.
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
        """
        Closes the singleton Rust database pool if it exists.

        This method ensures that the database connection pool is properly closed when
        it is no longer needed. It utilizes an asynchronous lock to ensure thread-safe
        operation. The pool is set to `None` after closure, and a debug message is
        logged upon successful closure.

        Returns:
            None: This function does not return any value.
        """
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
        """
        Asynchronous context manager entry point for the object.

        This method is invoked when the object is used with an `async
        with` statement, providing proper initialization before entering
        the context.

        Returns:
            RustAsyncDatabasePool: The initialized object, ready for use in
            the `async with` context.
        """
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Handles the exit of an asynchronous context manager.

        This method is part of the standard asynchronous context manager protocol and ensures that necessary cleanup
        or closing operations are performed when the context manager's execution completes, even if an exception occurred.

        Args:
            exc_type: The exception type being handled, if an exception occurred, otherwise None.
            exc_val: The exception instance being handled, if an exception occurred, otherwise None.
            exc_tb: The traceback associated with the exception, if an exception occurred, otherwise None.
        """
        await self.close()

    async def initialize(self) -> None:
        """
        Initializes the class by setting up database connections.

        This method performs initialization tasks by verifying the existing database paths,
        and if valid paths are detected, it establishes database connections using a Rust
        coroutine for high-performance, non-blocking asynchronous handling. Initialization
        status is tracked to ensure this method only executes once.

        Raises:
            NotImplementedError: If the Rust coroutine fails or encounters an issue
            during execution.
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
        """
        Closes the database connection pool.

        This method is used to clean up and mark the database connection pool as
        uninitialized. The connections themselves are automatically managed and
        cleaned up upon the destruction of the pool, ensuring compatibility with
        API expectations for manual resource cleanup.

        Raises:
            No exceptions are explicitly raised by this method, though it logs the
            action for debugging purposes.
        """
        if not self._initialized:
            return

        # Rust DatabasePool doesn't have a close() method
        # Connections are automatically cleaned up when the pool is dropped
        # Just mark as uninitialized for API compatibility
        self._initialized = False
        logger.debug("Rust database pool marked as closed (connections cleaned up on drop)")

    async def get_entry(self, formid: str, plugin: str) -> str | None:
        """
        Asynchronously retrieves an entry from the Rust pool.

        The method retrieves data corresponding to a specific `formid` and `plugin`.
        It ensures the component is initialized before execution and performs an
        asynchronous operation to interact with the Rust backend.

        Args:
            formid (str): The unique form identifier for the entry to retrieve.
            plugin (str): The plugin associated with the requested entry.

        Returns:
            str | None: The entry retrieved from the Rust pool if found, otherwise None.
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
        Fetches a batch of entries by querying an external Rust-based pool.

        This asynchronous method attempts to retrieve entries in batches using
        a provided list of (formid, plugin) pairs. It first attempts to use the
        `batch_lookup` method in the Rust pool for efficient querying. If that
        method is unavailable, it falls back to the `get_entries_batch` method.
        The operation ensures that the desired entries in the requested format
        are returned.

        Args:
            formid_plugin_pairs (list[tuple[str, str]]): A list of tuples where
                each tuple contains a form ID and a plugin name corresponding to
                the desired entries.
            batch_size (int): Optional; the size of the batch to retrieve in cases
                where the `batch_lookup` method isn't available. Default is 100.

        Returns:
            dict[tuple[str, str], str]: A dictionary mapping each (formid, plugin)
            pair to its corresponding result string.

        Raises:
            AttributeError: If methods necessary for querying the Rust pool
                are missing.

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
        Clears the cache entries based on the specified condition.

        This method interacts with the underlying rust-based pool to clear
        entries in the cache. The behavior of cache clearing depends on
        whether only expired entries are to be cleared or all entries.

        Args:
            expired_only (bool): If True, only expired entries in the
                cache will be cleared. If False, all entries will be cleared.

        Returns:
            int: The number of entries removed from the cache.
        """
        return self._rust_pool.clear_cache(expired_only)

    async def set_cache_ttl(self, seconds: int) -> None:
        """
        Sets the cache time-to-live (TTL) for the current instance.

        This method allows you to specify the duration that the cache entries
        will remain valid before being invalidated.

        Args:
            seconds (int): The duration in seconds for the cache TTL.

        Returns:
            None
        """
        self._rust_pool.set_cache_ttl(seconds)

    async def get_stats(self) -> dict[str, Any]:
        """
        Fetches and returns statistical information from the underlying rust pool.

        Provides detailed statistics about the state and performance of the rust pool
        when the method is called. The returned data includes a comprehensive snapshot
        of the pool's current metrics.

        Returns:
            dict[str, Any]: A dictionary containing various statistics and metrics
            related to the rust pool's performance and state.
        """
        return self._rust_pool.get_stats()

    async def optimize(self) -> None:
        """
        Optimizes the underlying system resources asynchronously.

        This method leverages an asynchronous operation to perform optimization
        on specified resources, ensuring improved system performance and efficiency.

        Raises:
            RuntimeError: If the operation fails or encounters issues.
        """
        await self._rust_pool.optimize()

    def set_game_table(self, table: str) -> None:
        """
        Sets the game table for the current instance.

        This method updates the game table configuration using the provided
        table name. It also logs the updated table name for debugging
        purposes. If the underlying `_rust_pool` has the method `set_game_table`,
        it will be invoked with the specified table name to propagate the
        change.

        Args:
            table (str): The name of the game table to be set.
        """
        if hasattr(self._rust_pool, 'set_game_table'):
            self._rust_pool.set_game_table(table)
            logger.debug(f"Set game table to: {table}")

    def get_game_table(self) -> str:
        """
        Gets and returns the current active game table.

        This function checks if an attribute 'get_game_table' is available in an
        existing resource pool (_rust_pool). If the attribute exists, it retrieves
        the game table from that source. Otherwise, it retrieves a global game
        table from the global registry.

        Returns:
            str: The current active game table.
        """
        if hasattr(self._rust_pool, 'get_game_table'):
            return self._rust_pool.get_game_table()
        return GlobalRegistry.get_game()


# Backward compatibility alias
AsyncDatabasePool = RustAsyncDatabasePool


def get_database_pool_implementation() -> type:
    """
    Determines and returns the appropriate database pool implementation based on
    the availability of Rust or Python modules. If neither implementation is
    available, raises an ImportError.

    Returns:
        type: The database pool implementation class used for managing database
        connections asynchronously.

    Raises:
        ImportError: If neither Rust nor Python database pool implementation is
        available.
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
