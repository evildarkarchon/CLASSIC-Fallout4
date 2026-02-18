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
    from ClassicLib.io.database import DatabasePoolManager

    manager = DatabasePoolManager()
    pool = await manager.get_pool()
    ```

Example:
    >>> from ClassicLib.io.database import DatabasePoolManager
    >>> manager = DatabasePoolManager()
    >>> pool = await manager.get_pool()  # Returns best available implementation
    >>> result = await pool.get_entry("00012345", "Fallout4.esm")

"""

import asyncio
import atexit
import contextlib
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any

from ClassicLib.core.constants import get_all_db_paths
from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.io.database.async_pool import AsyncDatabasePool
from ClassicLib.io.database.pool_manager import DatabasePoolManager

logger = logging.getLogger(__name__)

# Set to hold strong references to background tasks to prevent garbage collection
_background_tasks: set[asyncio.Task[None]] = set()


def _close_legacy_sync_pool(*, use_stderr: bool) -> None:
    """Close legacy SyncDatabasePool connections if initialized.

    Args:
        use_stderr: When True, write cleanup errors to stderr (safe at shutdown).

    """
    try:
        from ClassicLib.scanning.logs.util_legacy import SyncDatabasePool

        if SyncDatabasePool._instance is not None:  # pyright: ignore[reportPrivateUsage]
            SyncDatabasePool._instance.close_all()  # pyright: ignore[reportPrivateUsage]
            logger.debug("Closed SyncDatabasePool connections")
    except Exception as e:  # noqa: BLE001 - Must not fail during cleanup
        if use_stderr:
            print(f"Warning: Error closing SyncDatabasePool: {e}", file=sys.stderr)
        else:
            logger.warning(f"Error closing SyncDatabasePool: {e}")


def query_legacy_entry_sync(
    formid: str,
    plugin: str,
    *,
    query_cache: dict[tuple[str, str], str],
    db_paths: list[Path] | None = None,
    get_pool: Any = None,
    game_table: str | None = None,
) -> str | None:
    """Lookup a legacy FormID entry using shared database-layer behavior.

    This keeps util_legacy compatibility while consolidating lookup logic in
    the unified database package.

    Args:
        formid: Form ID to query.
        plugin: Plugin name to query.
        query_cache: Caller-owned cache dictionary.
        db_paths: Optional explicit database path list for testing.
        get_pool: Optional callable returning a sync pool instance.
        game_table: Optional explicit game table name for testing.

    Returns:
        Matching entry string, or None when no match is found.

    """
    cache_key = (formid, plugin)
    if (entry := query_cache.get(cache_key)) is not None:
        return entry

    if get_pool is None:
        from ClassicLib.scanning.logs.util_legacy import SyncDatabasePool

        get_pool = SyncDatabasePool.get_instance

    pool = get_pool()
    game_table_name = game_table if isinstance(game_table, str) and game_table else GlobalRegistry.get_game()
    sql_query = f"SELECT entry FROM {game_table_name} WHERE formid=? AND plugin=? COLLATE nocase"
    search_paths = db_paths if db_paths is not None else get_all_db_paths()

    for db_path in search_paths:
        if not db_path.is_file():
            continue

        try:
            conn = pool.get_connection(db_path)
            cursor = conn.cursor()
            cursor.execute(sql_query, (formid, plugin))
            db_entry = cursor.fetchone()
            if db_entry:
                value = db_entry[0]
                query_cache[cache_key] = value
                return value
        except sqlite3.Error as e:
            logger.error(f"Database query error in {db_path}: {e}")

    return None


# Import RustAsyncDatabasePool conditionally
try:
    from ClassicLib.io.database.rust_pool import RustAsyncDatabasePool

    __all__ = [
        "DatabasePoolManager",
        "AsyncDatabasePool",
        "RustAsyncDatabasePool",
        "cleanup_database_pools",
        "cleanup_database_pools_async",
        "query_legacy_entry_sync",
    ]
except ImportError:
    # Rust not available - only export Python pool
    __all__ = [
        "DatabasePoolManager",
        "AsyncDatabasePool",
        "cleanup_database_pools",
        "cleanup_database_pools_async",
        "query_legacy_entry_sync",
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

    _close_legacy_sync_pool(use_stderr=False)

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

    _close_legacy_sync_pool(use_stderr=True)

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
