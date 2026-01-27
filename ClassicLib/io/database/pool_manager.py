"""Unified database pool manager.

This module provides the singleton DatabasePoolManager which automatically
selects between Rust-accelerated and Python fallback database pool
implementations.

The manager prefers Rust when available (25x faster) and falls back to
Python's aiosqlite implementation transparently.

Example:
    >>> from ClassicLib.Database import DatabasePoolManager
    >>> manager = DatabasePoolManager()
    >>> pool = await manager.get_pool()  # Returns best available implementation
    >>> result = await pool.get_entry("00012345", "Fallout4.esm")
    >>> await manager.close_pool()

"""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, Any, ClassVar

from ClassicLib.core.logger import logger

if TYPE_CHECKING:
    from ClassicLib.io.database.async_pool import AsyncDatabasePool
    from ClassicLib.io.database.rust_pool import RustAsyncDatabasePool

    PoolType = AsyncDatabasePool | RustAsyncDatabasePool


class DatabasePoolManager:
    """Singleton manager for database pool instances.

    Automatically selects between Rust-accelerated and Python fallback
    implementations based on availability. Ensures database connections
    are reused across multiple orchestrator instances.

    Thread Safety:
        Uses threading.Lock for instance creation (synchronous) and
        asyncio.Lock for pool operations (asynchronous) to ensure
        thread-safe singleton behavior.

    Attributes:
        _instance: The singleton instance.
        _pool: The managed database pool instance.
        _using_rust: Whether the Rust implementation is in use.

    Example:
        >>> manager = DatabasePoolManager()
        >>> pool = await manager.get_pool()
        >>> # Use pool for database operations
        >>> await manager.close_pool()

    """

    _instance: ClassVar[DatabasePoolManager | None] = None
    _pool: Any = None  # Can be RustAsyncDatabasePool or AsyncDatabasePool
    _lock: ClassVar[asyncio.Lock | None] = None  # For async operations
    _creation_lock: ClassVar[threading.Lock] = threading.Lock()  # For __new__ thread safety
    _using_rust: bool = False

    def __new__(cls) -> DatabasePoolManager:
        """Ensure only one instance of DatabasePoolManager exists.

        Thread-safe singleton creation using a threading lock.

        Returns:
            The singleton DatabasePoolManager instance.

        """
        with cls._creation_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._lock = None
        return cls._instance

    async def get_pool(self) -> PoolType:
        """Get or create the singleton database pool.

        Uses Rust DatabasePool when available (25x faster), otherwise falls
        back to Python AsyncDatabasePool (aiosqlite).

        Returns:
            The singleton database pool instance (Rust or Python).

        Raises:
            ImportError: If neither implementation is available.

        """
        # Thread-safe async lock creation using the threading lock
        # This prevents race conditions when multiple coroutines try to
        # initialize the async lock simultaneously
        if self._lock is None:
            with self._creation_lock:
                if self._lock is None:
                    self.__class__._lock = asyncio.Lock()

        # Store in local variable for type checker
        lock = self._lock
        assert lock is not None, "Lock should be initialized"

        async with lock:
            if self._pool is None:
                # Try to use Rust DatabasePool first
                try:
                    from ClassicLib.integration.status import is_rust_accelerated

                    if is_rust_accelerated("database_pool"):
                        from ClassicLib.io.database.rust_pool import RustAsyncDatabasePool

                        # Match max_connections to max_concurrent for optimal performance
                        # Default scan config has max_concurrent=50, so use 50 connections
                        rust_pool = RustAsyncDatabasePool(max_connections=50, cache_ttl_seconds=300)
                        await rust_pool.initialize()
                        self._pool = rust_pool
                        self._using_rust = True
                        logger.debug("Created singleton Rust DatabasePool (25x acceleration, 50 connections)")
                        return self._pool
                except ImportError as e:
                    logger.debug(f"Rust DatabasePool not available, using Python: {e}")

                # Fallback to Python AsyncDatabasePool
                from ClassicLib.io.database.async_pool import AsyncDatabasePool

                self._pool = AsyncDatabasePool(max_connections=50)
                await self._pool.initialize()
                self._using_rust = False
                logger.debug("Created singleton Python database pool (aiosqlite, 50 connections)")
            return self._pool

    async def close_pool(self) -> None:
        """Close the singleton database pool if it exists.

        Safely closes the pool and resets the manager state.
        """
        if self._lock is None:
            return

        # Store in local variable for type checker
        lock = self._lock
        assert lock is not None, "Lock should exist after None check"

        async with lock:
            if self._pool is not None:
                await self._pool.close()
                self._pool = None
                logger.debug("Closed singleton database pool")

    @property
    def is_using_rust(self) -> bool:
        """Check if the manager is using the Rust implementation.

        Returns:
            True if Rust implementation is in use, False otherwise.

        """
        return self._using_rust

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance for testing purposes.

        Warning:
            This should only be used in test fixtures to ensure
            test isolation. Never use in production code.

        """
        with cls._creation_lock:
            if cls._pool is not None:
                # Note: Cannot close async pool from sync context
                # Tests should call close_pool() before reset
                cls._pool = None
            cls._instance = None
            cls._lock = None
            cls._using_rust = False
