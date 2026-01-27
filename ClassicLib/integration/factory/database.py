"""Database factory functions.

Provides factory functions for database pool implementations,
selecting between Rust and Python implementations.

Functions:
    get_database_pool: Retrieve the database pool implementation.
"""

from __future__ import annotations

import logging
from typing import Any

from ClassicLib.integration.factory.core import get_components, is_rust_disabled

logger = logging.getLogger(__name__)


def get_database_pool(max_connections: int = 10, cache_ttl_seconds: int = 300) -> Any:
    """Retrieve a database connection pool.

    The function prioritizes a Rust-based implementation if available, which
    provides significant performance improvements (25x faster). If the Rust
    implementation is not available, it falls back to the Python implementation.

    Args:
        max_connections: Maximum number of connections allowed to be managed
            by the database pool. Defaults to 10.
        cache_ttl_seconds: Time-to-live of the connection cache in seconds.
            Defaults to 300.

    Returns:
        Any: The database pool instance, which can either be RustAsyncDatabasePool
        or AsyncDatabasePool depending on the availability of the Rust module.

    """
    components = get_components()

    if not is_rust_disabled() and components.get("database_pool", False):
        try:
            from ClassicLib.io.database.rust_pool import RustAsyncDatabasePool

            logger.debug("Using Rust DatabasePool (25x speedup)")
            return RustAsyncDatabasePool(max_connections, cache_ttl_seconds)
        except ImportError as e:
            logger.warning(f"Failed to import Rust DatabasePool: {e}")

    # Fall back to Python implementation
    from ClassicLib.io.database.async_pool import AsyncDatabasePool

    logger.debug("Using Python AsyncDatabasePool implementation")
    return AsyncDatabasePool(max_connections)
