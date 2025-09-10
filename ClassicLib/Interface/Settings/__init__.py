"""
Settings module for CLASSIC interface.

This module provides backwards compatibility for the refactored SettingsDialog.
"""

from ClassicLib.Interface.Settings.dialog import SettingsDialog
from ClassicLib.Interface.Settings.path_manager import PathManager
from ClassicLib.Interface.Settings.tab_creators import TabCreator

__all__ = ["SettingsDialog", "PathManager", "TabCreator"]
