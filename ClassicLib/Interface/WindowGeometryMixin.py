"""
Window geometry management for tab-specific sizing in CLASSIC interface.

This module provides functionality to save and restore window sizes for different tabs,
allowing each tab to have its own minimum size and remembered dimensions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.YamlSettingsCache import yaml_settings

if TYPE_CHECKING:
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QTabWidget


class WindowGeometryMixin:
    """
    Mixin class providing window geometry management for tab-specific sizing.

    This class handles saving and restoring window sizes when switching between tabs,
    with support for different minimum sizes per tab.
    """

    # Default minimum sizes for each tab
    DEFAULT_MIN_SIZES: ClassVar[dict[int, tuple[int, int]]] = {
        0: (550, 350),  # Main Options tab
        1: (750, 450),  # File Backup tab (larger)
        2: (550, 350),  # Articles tab
        3: (750, 450),  # Results tab
    }

    # Tab names for settings storage
    TAB_NAMES: ClassVar[dict[int, str]] = {0: "main_tab", 1: "backups_tab", 2: "articles_tab", 3: "results_tab"}

    # Type stubs for attributes that must be provided by the mixing class
    if TYPE_CHECKING:
        tab_widget: QTabWidget

        def resize(self, width: int, height: int) -> None: ...
        def setMinimumSize(self, width: int, height: int) -> None: ...
        def size(self) -> QSize: ...

    def __init__(self) -> None:
        """Initialize window geometry tracking."""
        super().__init__()
        self._last_tab_index: int | None = None
        self._geometry_initialized = False

    def setup_window_geometry(self) -> None:
        """
        Initialize window geometry management.

        Should be called after tab widget is created and tabs are added.
        """
        if not hasattr(self, "tab_widget"):
            logger.warning("Tab widget not found, skipping geometry setup")
            return

        # Connect to tab change signal
        self.tab_widget.currentChanged.connect(self.handle_tab_changed)

        # Set initial window size for the first tab
        initial_index = self.tab_widget.currentIndex()
        self.restore_tab_geometry(initial_index)
        self._last_tab_index = initial_index
        self._geometry_initialized = True

        logger.debug(f"Window geometry management initialized for tab {initial_index}")

    def handle_tab_changed(self, index: int) -> None:
        """
        Handle tab change event to save and restore window geometry.

        Args:
            index: The index of the newly selected tab
        """
        if not self._geometry_initialized:
            return

        # Save geometry for the previous tab
        if self._last_tab_index is not None:
            self.save_tab_geometry(self._last_tab_index)

        # Restore geometry for the new tab
        self.restore_tab_geometry(index)

        self._last_tab_index = index
        logger.debug(f"Switched to tab {index} ({self.TAB_NAMES.get(index, 'unknown')})")

    def save_tab_geometry(self, tab_index: int) -> None:
        """
        Save the current window size for a specific tab.

        Args:
            tab_index: The index of the tab to save geometry for
        """
        if tab_index not in self.TAB_NAMES:
            return

        tab_name = self.TAB_NAMES[tab_index]
        current_size = self.size()

        # Save width and height to YAML settings
        yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.width", current_size.width())
        yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.height", current_size.height())

        logger.debug(f"Saved geometry for {tab_name}: {current_size.width()}x{current_size.height()}")

    def restore_tab_geometry(self, tab_index: int) -> None:
        """
        Restore the saved window size for a specific tab.

        If no saved size exists, uses the default minimum size for that tab.

        Args:
            tab_index: The index of the tab to restore geometry for
        """
        if tab_index not in self.TAB_NAMES:
            return

        tab_name = self.TAB_NAMES[tab_index]
        min_width, min_height = self.get_minimum_size_for_tab(tab_index)

        # Try to get saved dimensions
        saved_width = yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.width", None)
        saved_height = yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.height", None)

        # Determine the size to use
        if saved_width is not None and saved_height is not None:
            # Use saved size, but ensure it's at least the minimum
            width = max(saved_width, min_width)
            height = max(saved_height, min_height)
            logger.debug(f"Restoring saved geometry for {tab_name}: {width}x{height}")
        else:
            # No saved size, use minimum
            width = min_width
            height = min_height
            logger.debug(f"Using default minimum size for {tab_name}: {width}x{height}")

        # Update window minimum size and actual size
        self.setMinimumSize(min_width, min_height)
        self.resize(width, height)

    def get_minimum_size_for_tab(self, tab_index: int) -> tuple[int, int]:
        """
        Get the minimum size for a specific tab.

        Args:
            tab_index: The index of the tab

        Returns:
            Tuple of (width, height) for the minimum size
        """
        return self.DEFAULT_MIN_SIZES.get(tab_index, (550, 350))

    def save_current_tab_geometry(self) -> None:
        """
        Save the geometry of the currently active tab.

        Should be called before the application closes.
        """
        if hasattr(self, "tab_widget") and self._geometry_initialized:
            current_index = self.tab_widget.currentIndex()
            self.save_tab_geometry(current_index)
            logger.debug(f"Saved final geometry for tab {current_index}")
