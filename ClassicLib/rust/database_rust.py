"""Python wrapper for Rust database pool.

Deprecated:
    This module is deprecated. Import from ClassicLib.Database instead:

    ```python
    from ClassicLib.Database import DatabasePoolManager, RustAsyncDatabasePool
    ```

This module now re-exports classes from the new canonical location
for backward compatibility.
"""

from __future__ import annotations

import warnings
from typing import Any

# Issue deprecation warning on module import
warnings.warn(
    "The ClassicLib.rust.database_rust module is deprecated. "
    "Import from ClassicLib.Database instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new canonical location (must be after deprecation warning)
from ClassicLib.Database.pool_manager import DatabasePoolManager  # noqa: E402
from ClassicLib.Database.rust_pool import (  # noqa: E402
    RUST_AVAILABLE,
    RustAsyncDatabasePool,
    is_rust_available,
)

# Backward compatibility alias
AsyncDatabasePool = RustAsyncDatabasePool

__all__ = [
    "DatabasePoolManager",
    "RustAsyncDatabasePool",
    "AsyncDatabasePool",
    "RUST_AVAILABLE",
    "is_rust_available",
    "get_database_pool_implementation",
]


def get_database_pool_implementation() -> type[Any]:
    """Get the appropriate database pool implementation.

    Deprecated:
        Use ClassicLib.integration.factory.get_database_pool() instead.

    Returns:
        The database pool implementation class.

    Raises:
        ImportError: If neither implementation is available.

    """
    warnings.warn(
        "get_database_pool_implementation() is deprecated. "
        "Use ClassicLib.integration.factory.get_database_pool() instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    if RUST_AVAILABLE:
        return RustAsyncDatabasePool
    # Fall back to Python implementation if available
    try:
        from ClassicLib.Database.async_pool import AsyncDatabasePool as PythonAsyncDatabasePool
    except ImportError as e:
        raise ImportError(
            "Neither Rust nor Python database pool implementation available. "
            "Please rebuild with maturin or check your installation."
        ) from e
    else:
        return PythonAsyncDatabasePool
