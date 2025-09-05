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

try:
    from PySide6.QtCore import Qt
except ImportError:
    Qt = None  # type: ignore[assignment]

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

        def size(self) -> QSize: ...

        def windowState(self) -> Qt.WindowState: ...

        def showMaximized(self) -> None: ...

        def showNormal(self) -> None: ...

        def normalGeometry(self) -> object: ...

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

        Handles both normal and maximized window states, saving the appropriate
        geometry based on the current state.

        Args:
            tab_index: The index of the tab to save geometry for
        """
        if tab_index not in self.TAB_NAMES:
            return

        tab_name = self.TAB_NAMES[tab_index]

        # Check if window is maximized
        is_maximized = False
        if Qt is not None and hasattr(self, "windowState"):
            is_maximized = bool(self.windowState() & Qt.WindowState.WindowMaximized)  # type: ignore[attr-defined]

        # Save maximized state
        yaml_settings(bool, YAML.Settings, f"UI.window_geometry.{tab_name}.maximized", is_maximized)

        if is_maximized:
            # Window is maximized - save the normal geometry (pre-maximized size)
            # normalGeometry() returns the geometry the window will have when restored
            if hasattr(self, "normalGeometry"):
                normal_geom = self.normalGeometry()  # type: ignore[attr-defined]
                yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.width", normal_geom.width())
                yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.height", normal_geom.height())
                logger.debug(
                    f"Saved normal geometry for maximized {tab_name}: {normal_geom.width()}x{normal_geom.height()} (maximized=True)"
                )
            else:
                # Fallback if normalGeometry is not available
                current_size = self.size()
                yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.width", current_size.width())
                yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.height", current_size.height())
                logger.debug(f"Saved current size for {tab_name} (maximized, no normal geometry available)")
        else:
            # Window is not maximized - save current size as normal
            current_size = self.size()
            yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.width", current_size.width())
            yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.height", current_size.height())
            logger.debug(f"Saved geometry for {tab_name}: {current_size.width()}x{current_size.height()}")

    def restore_tab_geometry(self, tab_index: int) -> None:
        """
        Restore the saved window size for a specific tab.

        If no saved size exists, uses the default minimum size for that tab.
        Also restores the maximized state if the window was maximized when last saved.

        Args:
            tab_index: The index of the tab to restore geometry for
        """
        if tab_index not in self.TAB_NAMES:
            return

        tab_name = self.TAB_NAMES[tab_index]
        min_width, min_height = self.get_minimum_size_for_tab(tab_index)

        # Try to get saved dimensions and maximized state
        saved_width = yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.width", None)
        saved_height = yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.height", None)
        was_maximized = yaml_settings(bool, YAML.Settings, f"UI.window_geometry.{tab_name}.maximized", False)

        # Determine the size to use
        if saved_width is not None and saved_height is not None:
            # Use saved size, but ensure it's at least the minimum
            width = max(saved_width, min_width)
            height = max(saved_height, min_height)
            logger.debug(f"Restoring saved geometry for {tab_name}: {width}x{height} (maximized={was_maximized})")
        else:
            # No saved size, use minimum
            width = min_width
            height = min_height
            was_maximized = False  # Don't maximize if no saved state
            logger.debug(f"Using default minimum size for {tab_name}: {width}x{height}")

        # Update window minimum size
        self.setMinimumSize(min_width, min_height)  # type: ignore[attr-defined]

        # Restore window state based on whether it was maximized
        if was_maximized and Qt is not None and hasattr(self, "showMaximized"):
            # First set the normal size for when the window is un-maximized
            self.resize(width, height)  # type: ignore[attr-defined]
            # Then maximize the window
            self.showMaximized()  # type: ignore[attr-defined]
            logger.debug(f"Restored {tab_name} to maximized state with normal size {width}x{height}")
        else:
            # Just resize to the saved/default size
            self.resize(width, height)  # type: ignore[attr-defined]
            # Ensure window is shown in normal state if it was previously maximized
            if (
                Qt is not None
                and hasattr(self, "showNormal")
                and hasattr(self, "windowState")
                and self.windowState() & Qt.WindowState.WindowMaximized  # type: ignore[attr-defined]
            ):
                self.showNormal()  # type: ignore[attr-defined]

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
