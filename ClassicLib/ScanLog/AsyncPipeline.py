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
    "run_async_crash_log_scan",
    "AsyncPerformanceMonitor",
    "benchmark_async_pipeline",
]


def __getattr__(name: str):
    """Provide deprecation warnings for imports."""
    if name in __all__:
        warnings.warn(
            f"Importing {name} from ClassicLib.ScanLog.AsyncPipeline is deprecated. "
            f"Import from ClassicLib.ScanLog.pipeline instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
