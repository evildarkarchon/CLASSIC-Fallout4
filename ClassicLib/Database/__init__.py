"""Database connection pool management.

This module provides database pool management for CLASSIC, with automatic
selection between Rust-accelerated and Python fallback implementations.

Public API:
    DatabasePoolManager: Singleton manager for pool lifecycle management
    AsyncDatabasePool: Pure Python implementation (aiosqlite fallback)
    RustAsyncDatabasePool: Rust-accelerated implementation (25x faster)
    cleanup_database_pools: Synchronous cleanup function for application shutdown
    cleanup_database_pools_async: Async cleanup function for proper pool closure

Factory Usage (Recommended):
    The preferred way to get a database pool is through the factory:

    ```python
    from ClassicLib.integration.factory import get_database_pool

    pool = get_database_pool()
    await pool.initialize()
    result = await pool.get_entry(formid, plugin)
    ```

Direct Import Usage:
    For singleton management:

    ```python
    from ClassicLib.Database import DatabasePoolManager

    manager = DatabasePoolManager()
    pool = await manager.get_pool()
    ```

Example:
    >>> from ClassicLib.Database import DatabasePoolManager
    >>> manager = DatabasePoolManager()
    >>> pool = await manager.get_pool()  # Returns best available implementation
    >>> result = await pool.get_entry("00012345", "Fallout4.esm")

"""

import asyncio
import atexit
import contextlib
import logging
import sys

from ClassicLib.Database.async_pool import AsyncDatabasePool
from ClassicLib.Database.pool_manager import DatabasePoolManager

logger = logging.getLogger(__name__)

# Set to hold strong references to background tasks to prevent garbage collection
_background_tasks: set[asyncio.Task[None]] = set()

# Import RustAsyncDatabasePool conditionally
try:
    from ClassicLib.Database.rust_pool import RustAsyncDatabasePool

    __all__ = [
        "DatabasePoolManager",
        "AsyncDatabasePool",
        "RustAsyncDatabasePool",
        "cleanup_database_pools",
        "cleanup_database_pools_async",
    ]
except ImportError:
    # Rust not available - only export Python pool
    __all__ = [
        "DatabasePoolManager",
        "AsyncDatabasePool",
        "cleanup_database_pools",
        "cleanup_database_pools_async",
    ]


async def cleanup_database_pools_async() -> None:
    """Asynchronously close all database pools.

    This function properly closes all database connections, which is important
    for SQLite WAL mode databases to ensure the WAL file is checkpointed
    back to the main database and .db-wal/.db-shm files are removed.

    Should be called before application exit in async contexts.

    Example:
        >>> await cleanup_database_pools_async()

    """
    logger.debug("Starting async database pool cleanup")

    # Close the DatabasePoolManager singleton pool
    try:
        manager = DatabasePoolManager()
        await manager.close_pool()
        logger.debug("Closed DatabasePoolManager pool")
    except Exception as e:  # noqa: BLE001 - Must not fail during cleanup
        logger.warning(f"Error closing DatabasePoolManager pool: {e}")

    # Close the SyncDatabasePool singleton
    try:
        from ClassicLib.ScanLog.Util import SyncDatabasePool

        if SyncDatabasePool._instance is not None:  # pyright: ignore[reportPrivateUsage]
            SyncDatabasePool._instance.close_all()  # pyright: ignore[reportPrivateUsage]
            logger.debug("Closed SyncDatabasePool connections")
    except Exception as e:  # noqa: BLE001 - Must not fail during cleanup
        logger.warning(f"Error closing SyncDatabasePool: {e}")

    logger.debug("Async database pool cleanup complete")


def cleanup_database_pools() -> None:
    """Synchronously close all database pools.

    This function attempts to close database pools in a synchronous context.
    It handles both async and sync pools appropriately.

    For the async pool (DatabasePoolManager), it tries to run the cleanup
    in an existing event loop or creates a new one if necessary.

    This function is safe to call during application shutdown and is
    registered as an atexit handler automatically.

    Example:
        >>> cleanup_database_pools()

    """  # noqa: D401
    logger.debug("Starting sync database pool cleanup")

    # Close the SyncDatabasePool singleton first (always safe)
    try:
        from ClassicLib.ScanLog.Util import SyncDatabasePool

        if SyncDatabasePool._instance is not None:  # pyright: ignore[reportPrivateUsage]
            SyncDatabasePool._instance.close_all()  # pyright: ignore[reportPrivateUsage]
            logger.debug("Closed SyncDatabasePool connections")
    except Exception as e:  # noqa: BLE001 - Must not fail during cleanup
        # Use print during shutdown since logger may be unavailable
        print(f"Warning: Error closing SyncDatabasePool: {e}", file=sys.stderr)

    # Try to close the async DatabasePoolManager pool
    try:
        manager = DatabasePoolManager()
        if manager._pool is not None:  # pyright: ignore[reportPrivateUsage]
            # Try to get an existing event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context - schedule cleanup
                # Store task reference to prevent garbage collection before completion
                task = loop.create_task(manager.close_pool())
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
                logger.debug("Scheduled async pool cleanup in running loop")
            except RuntimeError:
                # No running loop - create a new one for cleanup
                try:
                    asyncio.run(manager.close_pool())
                    logger.debug("Closed async pool via new event loop")
                except RuntimeError as e:
                    # Can happen during interpreter shutdown
                    logger.debug(f"Could not run async cleanup: {e}")
    except Exception as e:  # noqa: BLE001 - Must not fail during cleanup
        print(f"Warning: Error closing async database pool: {e}", file=sys.stderr)

    logger.debug("Sync database pool cleanup complete")


def _atexit_cleanup() -> None:
    """Internal atexit handler for database cleanup.

    This is a fallback to ensure database connections are closed even if
    the application doesn't explicitly call cleanup functions.
    """  # noqa: D401
    with contextlib.suppress(Exception):
        cleanup_database_pools()


# Register atexit handler as a fallback for database cleanup
atexit.register(_atexit_cleanup)
