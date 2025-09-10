"""Dialog widgets for user interactions.

This module maintains backward compatibility by re-exporting components
from the refactored dialogs submodule.

DEPRECATED: Import directly from ClassicLib.TUI.widgets.dialogs instead.
"""

from __future__ import annotations

import warnings

# Re-export everything from the dialogs module for backward compatibility
from .dialogs import ConfirmationDialog, ErrorDialog, ProgressDialog

__all__ = [
    "ConfirmationDialog",
    "ErrorDialog",
    "ProgressDialog",
]


def __getattr__(name: str):
    """Provide deprecation warnings for imports."""
    if name in __all__:
        warnings.warn(
            f"Importing {name} from ClassicLib.TUI.widgets.confirmation_dialog is deprecated. "
            f"Import from ClassicLib.TUI.widgets.dialogs instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
