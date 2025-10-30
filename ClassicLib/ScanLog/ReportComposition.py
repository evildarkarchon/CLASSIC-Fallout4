"""
Report composition utilities for combining fragments with conditional headers.

This module maintains backward compatibility by re-exporting components
from the refactored composition submodule.

DEPRECATED: Import directly from ClassicLib.ScanLog.composition instead.
"""

from __future__ import annotations

import warnings

# Re-export everything from the composition module for backward compatibility
from .composition import ConditionalSection, ReportComposer, conditional_mod_section

__all__ = [
    "ConditionalSection",
    "ReportComposer",
    "conditional_mod_section",
]


def __getattr__(name: str):
    """
    Handles attribute access within the module to provide compatibility for importing certain names from an updated
    location and raises an appropriate deprecation warning or an error for unrecognized attributes.

    Args:
        name (str): The name of the attribute being accessed.

    Raises:
        AttributeError: If the requested name is not recognized as a valid attribute.

    Returns:
        Any: The global object corresponding to the accessed name if it is listed in `__all__`, otherwise raises
            an exception.
    """
    if name in __all__:
        warnings.warn(
            f"Importing {name} from ClassicLib.ScanLog.ReportComposition is deprecated. "
            f"Import from ClassicLib.ScanLog.composition instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
