"""Database connection pool management.

This module provides database pool management for CLASSIC, with automatic
selection between Rust-accelerated and Python fallback implementations.

Public API:
    DatabasePoolManager: Singleton manager for pool lifecycle management
    AsyncDatabasePool: Pure Python implementation (aiosqlite fallback)
    RustAsyncDatabasePool: Rust-accelerated implementation (25x faster)

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

from ClassicLib.Database.async_pool import AsyncDatabasePool
from ClassicLib.Database.pool_manager import DatabasePoolManager

# Import RustAsyncDatabasePool conditionally
try:
    from ClassicLib.Database.rust_pool import RustAsyncDatabasePool

    __all__ = ["DatabasePoolManager", "AsyncDatabasePool", "RustAsyncDatabasePool"]
except ImportError:
    # Rust not available - only export Python pool
    __all__ = ["DatabasePoolManager", "AsyncDatabasePool"]
