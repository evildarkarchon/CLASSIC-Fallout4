"""Async utility modules.

This package provides utility functions for async/sync bridging and related operations.

Note: This package is intentionally placed directly under ClassicLib (as _async_utils)
rather than under ClassicLib/Utils to avoid circular import issues. The underscore
prefix indicates it's an internal package.

Functions are now defined directly in ClassicLib.core.async_bridge and re-exported
here for backward compatibility.
"""

from ClassicLib.core.async_bridge import (
    context_aware_sync,
    run_async,
    run_async_with_timeout,
    smart_await,
)

__all__ = [
    "context_aware_sync",
    "run_async",
    "run_async_with_timeout",
    "smart_await",
]
