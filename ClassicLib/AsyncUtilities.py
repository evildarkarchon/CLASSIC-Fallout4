"""
DEPRECATED: Use ClassicLib.Utils.Async instead.
"""

import warnings

from ClassicLib.Utils.Async import (
    AsyncLazyLoader,
    AsyncTimer,
    Throttler,
    async_filter,
    async_map,
    async_retry,
    async_timeout,
    batch_process,
    gather_with_concurrency,
    reset_throttlers,
    run_in_executor,
    run_with_timeout,
    throttle,
)

warnings.warn(
    "ClassicLib.AsyncUtilities is deprecated. Use ClassicLib.Utils.Async instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "gather_with_concurrency",
    "batch_process",
    "async_retry",
    "async_timeout",
    "run_with_timeout",
    "async_map",
    "async_filter",
    "AsyncTimer",
    "Throttler",
    "throttle",
    "reset_throttlers",
    "run_in_executor",
    "AsyncLazyLoader",
]