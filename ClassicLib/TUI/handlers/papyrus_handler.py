"""Papyrus log monitoring handler for TUI.

This module maintains backward compatibility by re-exporting components
from the refactored papyrus submodule.

DEPRECATED: Import directly from ClassicLib.TUI.handlers.papyrus instead.
"""

from __future__ import annotations

import warnings

# Re-export everything from the papyrus module for backward compatibility
from .papyrus import PapyrusStats, TuiPapyrusHandler

# Also re-export the helper functions for full compatibility
from .papyrus.tui_papyrus_handler import (
    _UNICODE_SUPPORT_CACHE,
    _detect_unicode_support_impl,
    _get_unicode_support_cached,
)

__all__ = [
    "PapyrusStats",
    "TuiPapyrusHandler",
    "_UNICODE_SUPPORT_CACHE",
    "_detect_unicode_support_impl",
    "_get_unicode_support_cached",
]


def __getattr__(name: str):
    """Provide deprecation warnings for imports."""
    if name in __all__:
        warnings.warn(
            f"Importing {name} from ClassicLib.TUI.handlers.papyrus_handler is deprecated. "
            f"Import from ClassicLib.TUI.handlers.papyrus instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
