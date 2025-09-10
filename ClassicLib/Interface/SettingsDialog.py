"""
Settings dialog for CLASSIC application configuration.

This module provides backwards compatibility for the refactored SettingsDialog
that has been moved to ClassicLib.Interface.Settings.dialog.
"""

from __future__ import annotations

import warnings

# Import from new location
from ClassicLib.Interface.Settings.dialog import SettingsDialog

# Show deprecation warning
warnings.warn(
    "Importing SettingsDialog from ClassicLib.Interface.SettingsDialog is deprecated. "
    "Import from ClassicLib.Interface.Settings.dialog instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["SettingsDialog"]
