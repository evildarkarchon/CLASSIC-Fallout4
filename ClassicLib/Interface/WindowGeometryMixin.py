"""
Window geometry management for tab-specific sizing in CLASSIC interface.

This module provides functionality to save and restore window sizes for different tabs,
allowing each tab to have its own minimum size and remembered dimensions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Any

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

        def size(self) -> QSize: ...  # noqa: D102

        def windowState(self) -> Qt.WindowState: ...  # noqa: D102

        def showMaximized(self) -> None: ...  # noqa: D102

        def showNormal(self) -> None: ...  # noqa: D102

        def normalGeometry(self) -> Any: ...  # noqa: D102

    def __init__(self) -> None:
        """
        Initializes an instance of the class.

        The constructor is responsible for initializing the object and setting the
        attributes used internally by the class. It ensures proper setup for subsequent usage.
        """
        super().__init__()
        self._last_tab_index: int | None = None
        self._geometry_initialized = False

    def setup_window_geometry(self) -> None:
        """
        Sets up the window geometry and connects tab change events if a tab widget
        exists within the instance. This ensures window size and state are managed
        when switching tabs.

        Raises:
            None

        Returns:
            None
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
        Handles the event of changing tabs in the application.

        This method ensures the geometry state of the current tab is saved before
        switching, and the geometry of the new tab is restored after switching.
        It also updates the internal state to reflect the tab change.

        Args:
            index (int): The index of the new tab being switched to.
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
        Saves the geometry of a specified tab, including its size and maximized state,
        into a persistent storage. If the window is maximized, it saves both the
        maximized state and the geometry the window had before maximization. Otherwise,
        the current size of the window is saved.

        Args:
            tab_index (int): The index of the tab for which the geometry should be saved.

        Raises:
            KeyError: If the tab_index is not found in the list of tab names.
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
                yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.width", normal_geom.width())  # type: ignore[attr-defined]
                yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.height", normal_geom.height())  # type: ignore[attr-defined]
                logger.debug(
                    f"Saved normal geometry for maximized {tab_name}: {normal_geom.width()}x{normal_geom.height()} (maximized=True)"  # type: ignore[attr-defined]
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
        Restores the geometry of a tab based on saved settings. This includes its size
        and maximized state, ensuring either restored or minimum dimensions are met.

        Args:
            tab_index (int): Index of the tab whose geometry is to be restored. The
                index must exist in `self.TAB_NAMES`.

        Raises:
            TypeError: If the provided `tab_index` is not an integer.
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
        Retrieves the minimum size for a specified tab.

        This method returns the width and height of the minimum size for the
        tab identified by its index. If the specified tab index does not exist,
        it provides a default size.

        Args:
            tab_index (int): The index of the tab to retrieve the minimum size for.

        Returns:
            tuple[int, int]: A tuple containing the width and height of the
            minimum size for the tab.
        """
        return self.DEFAULT_MIN_SIZES.get(tab_index, (550, 350))

    def save_current_tab_geometry(self) -> None:
        """
        Saves the current geometry of the tab.

        This method checks if the object has a `tab_widget` attribute and if the
        geometry has been initialized. If both conditions are met, it retrieves
        the current tab index of the tab widget and saves the geometry for that
        specific tab. A debug message is logged indicating the tab for which the
        geometry has been saved.

        Raises:
            AttributeError: If the `tab_widget` attribute is not found.
        """
        if hasattr(self, "tab_widget") and self._geometry_initialized:
            current_index = self.tab_widget.currentIndex()
            self.save_tab_geometry(current_index)
            logger.debug(f"Saved final geometry for tab {current_index}")
