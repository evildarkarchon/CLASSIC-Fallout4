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
    """Provide deprecation warnings for imports."""
    if name in __all__:
        warnings.warn(
            f"Importing {name} from ClassicLib.ScanLog.ReportFragment is deprecated. "
            f"Import from ClassicLib.ScanLog.fragments.{name.lower()} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
