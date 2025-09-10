"""
Data models for scan log operations.

This module maintains backward compatibility by re-exporting components
from the refactored models submodule.

DEPRECATED: Import directly from ClassicLib.ScanLog.models submodules instead.
"""

from __future__ import annotations

import warnings

# Re-export everything from the models module for backward compatibility
from .models import ScanConfig, ScanConfigDict, ScanResult, ScanResultDict, ScanStatistics

__all__ = [
    "ScanConfig",
    "ScanStatistics",
    "ScanResult",
    "ScanConfigDict",
    "ScanResultDict",
]


def __getattr__(name: str):
    """Provide deprecation warnings for imports."""
    if name in __all__:
        warnings.warn(
            f"Importing {name} from ClassicLib.ScanLog.models is deprecated. "
            f"Import from ClassicLib.ScanLog.models.{name.lower()} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
