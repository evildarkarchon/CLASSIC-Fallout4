"""Settings module for CLASSIC interface.

This module provides backwards compatibility for the refactored SettingsDialog.
"""

from ClassicLib.Interface.settings.dialog import SettingsDialog
from ClassicLib.Interface.settings.path_manager import PathManager
from ClassicLib.Interface.settings.tab_creators import TabCreator

__all__ = ["PathManager", "SettingsDialog", "TabCreator"]
