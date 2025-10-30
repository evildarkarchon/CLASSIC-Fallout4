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
    "ScanConfigDict",
    "ScanResult",
    "ScanResultDict",
    "ScanStatistics",
]


def __getattr__(name: str):
    """
    Handles attribute access for the module. This function checks if an attribute
    (name) is present in the `__all__` list. If it exists, it raises a deprecation
    warning, indicating the preferred import location, and returns the global
    definition of that attribute. If the attribute does not exist, an
    AttributeError is raised.

    Args:
        name (str): The name of the attribute being accessed.

    Raises:
        AttributeError: If the attribute is not found in the module.

    Returns:
        Any: The global definition of the requested attribute if it exists.
    """
    if name in __all__:
        warnings.warn(
            f"Importing {name} from ClassicLib.ScanLog.models is deprecated. "
            f"Import from ClassicLib.ScanLog.models.{name.lower()} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
