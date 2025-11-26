"""
DEPRECATED: Use ClassicLib.Utils.Async instead.
"""

import warnings

from ClassicLib.Utils.Async import (
    FAST_PATH_OPERATIONS,
    SIZE_DEPENDENT_OPERATIONS,
    ExecutorDecisionMaker,
    async_map_smart,
    batch_process_smart,
    smart_run_in_executor,
)

warnings.warn(
    "ClassicLib.AsyncUtilities_Enhanced is deprecated. Use ClassicLib.Utils.Async instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "smart_run_in_executor",
    "async_map_smart",
    "batch_process_smart",
    "ExecutorDecisionMaker",
    "FAST_PATH_OPERATIONS",
    "SIZE_DEPENDENT_OPERATIONS",
]
