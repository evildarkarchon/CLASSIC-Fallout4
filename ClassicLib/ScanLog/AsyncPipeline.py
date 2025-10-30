"""
Async crash log processing pipeline.

This module maintains backward compatibility by re-exporting components
from the refactored pipeline submodule.

DEPRECATED: Import directly from ClassicLib.ScanLog.pipeline instead.
"""

from __future__ import annotations

import warnings

# Re-export everything from the pipeline module for backward compatibility
from .pipeline import (
    AsyncCrashLogPipeline,
    AsyncPerformanceMonitor,
    benchmark_async_pipeline,
    run_async_crash_log_scan,
)

__all__ = [
    "AsyncCrashLogPipeline",
    "AsyncPerformanceMonitor",
    "benchmark_async_pipeline",
    "run_async_crash_log_scan",
]


def __getattr__(name: str):
    """
    Gets the attribute from the module with deprecation warning for specific cases.

    This function is invoked when an attribute lookup has not found the attribute in the usual places
    (e.g., in an instance attribute or a class attribute).

    Args:
        name (str): The name of the attribute being accessed.

    Returns:
        Any: The value of the attribute if found.

    Raises:
        AttributeError: If the attribute does not exist in the module.
    """
    if name in __all__:
        warnings.warn(
            f"Importing {name} from ClassicLib.ScanLog.AsyncPipeline is deprecated. "
            f"Import from ClassicLib.ScanLog.pipeline instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
