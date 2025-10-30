"""
Report fragment system for functional report generation.

This module maintains backward compatibility by re-exporting components
from the refactored fragments submodule.

DEPRECATED: Import directly from ClassicLib.ScanLog.fragments instead.
"""

from __future__ import annotations

import warnings

# Re-export everything from the fragments module for backward compatibility
from .fragments import (
    FragmentCollector,
    ReportComposer,
    ReportFragment,
    ReportGeneratorFunctional,
    detect_mods_single_fragment,
    generate_mod_check_header_fragment,
)

__all__ = [
    "FragmentCollector",
    "ReportComposer",
    "ReportFragment",
    "ReportGeneratorFunctional",
    "detect_mods_single_fragment",
    "generate_mod_check_header_fragment",
]


def __getattr__(name: str):
    """
    Retrieves a global attribute dynamically by its name and provides a warning if it has been
    deprecated. The function primarily checks if the name exists in the specified attribute list
    (__all__) and provides an alternative path to import the attribute.

    If the specified name is not present in the globally defined attributes, it raises an
    AttributeError.

    Args:
        name (str): The name of the attribute to be retrieved.

    Returns:
        Any: The global object associated with the given name if it exists in the __all__ list.

    Raises:
        AttributeError: If the provided name does not exist within the module.
    """
    if name in __all__:
        warnings.warn(
            f"Importing {name} from ClassicLib.ScanLog.ReportFragment is deprecated. "
            f"Import from ClassicLib.ScanLog.fragments.{name.lower()} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
