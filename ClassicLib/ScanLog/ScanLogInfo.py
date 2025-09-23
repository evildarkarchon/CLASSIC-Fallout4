"""
Scan log information and caching components.

This module maintains backward compatibility by re-exporting components
from the refactored scanloginfo submodule.

DEPRECATED: Import directly from ClassicLib.ScanLog.scanloginfo instead.
"""

from __future__ import annotations

import warnings

# Re-export everything from the scanloginfo module for backward compatibility
from .scanloginfo import ClassicScanLogsInfo, ThreadSafeLogCache

__all__ = [
    "ClassicScanLogsInfo",
    "ThreadSafeLogCache",
]


def __getattr__(name: str):
    """Provide deprecation warnings for imports."""
    if name in __all__:
        warnings.warn(
            f"Importing {name} from ClassicLib.ScanLog.ScanLogInfo is deprecated. "
            f"Import from ClassicLib.ScanLog.scanloginfo instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
