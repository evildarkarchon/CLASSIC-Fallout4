"""Window geometry management controller for CLASSIC interface.

This module provides the WindowGeometryManager class that handles per-tab
window sizing, saving, and restoring window dimensions.

Example:
    >>> from ClassicLib.Interface.controllers.window_geometry import WindowGeometryManager
    >>> geometry_mgr = WindowGeometryManager(context)
    >>> geometry_mgr.setup()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.YamlSettings import yaml_settings

try:
    from PySide6.QtCore import Qt
except ImportError:
    Qt = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from ClassicLib.Interface.context import FeatureContext


class WindowGeometryManager:
    """Controller for window geometry management with per-tab sizing.

    This controller handles saving and restoring window sizes when switching
    between tabs, with support for different minimum sizes per tab and
    maximized window state persistence.

    Attributes:
        _ctx: The FeatureContext providing access to shared dependencies.
        _last_tab_index: Index of the previously active tab.
        _geometry_initialized: Whether geometry management has been set up.

    Class Attributes:
        DEFAULT_MIN_SIZES: Default minimum window sizes for each tab.
        TAB_NAMES: Mapping of tab indices to setting key names.

    Example:
        >>> manager = WindowGeometryManager(context)
        >>> manager.setup()  # Initialize and connect signals
        >>> manager.handle_tab_changed(1)  # Save/restore on tab switch
    """

    # Default minimum sizes for each tab (width, height)
    DEFAULT_MIN_SIZES: ClassVar[dict[int, tuple[int, int]]] = {
        0: (550, 350),  # Main Options tab
        1: (750, 450),  # File Backup tab (larger)
        2: (550, 350),  # Articles tab
        3: (750, 450),  # Results tab
    }

    # Tab names for settings storage
    TAB_NAMES: ClassVar[dict[int, str]] = {
        0: "main_tab",
        1: "backups_tab",
        2: "articles_tab",
        3: "results_tab",
    }

    def __init__(self, context: FeatureContext) -> None:
        """Initialize the WindowGeometryManager.

        Args:
            context: FeatureContext providing access to main_window, signal_hub,
                and ui_widgets.
        """
        self._ctx = context
        self._last_tab_index: int | None = None
        self._geometry_initialized = False

    def setup(self) -> None:
        """Set up window geometry management.

        Connects to tab change signals and initializes window size
        for the current tab.
        """
        tab_widget = self._ctx.ui_widgets.tab_widget
        if tab_widget is None:
            logger.warning("Tab widget not found, skipping geometry setup")
            return

        # Connect to tab change signal
        tab_widget.currentChanged.connect(self.handle_tab_changed)

        # Connect to SignalHub for refresh requests on tab change
        self._ctx.signal_hub.tab_changed.connect(self._on_tab_changed_signal)

        # Set initial window size for the first tab
        initial_index = tab_widget.currentIndex()
        self.restore_tab_geometry(initial_index)
        self._last_tab_index = initial_index
        self._geometry_initialized = True

        logger.debug(f"Window geometry management initialized for tab {initial_index}")

    def _on_tab_changed_signal(self, index: int) -> None:
        """Handle tab changed signal from SignalHub.

        Args:
            index: The new tab index.
        """
        # Request reports refresh when switching to results tab
        if index == 3:
            self._ctx.signal_hub.refresh_reports_requested.emit()
            logger.debug("Requested reports refresh after switching to results tab")

    def handle_tab_changed(self, index: int) -> None:
        """Handle tab change events.

        Saves geometry for the previous tab and restores geometry for
        the new tab. Also emits tab_changed signal for other controllers.

        Args:
            index: Index of the newly active tab.
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

        # Emit signal for other controllers
        self._ctx.signal_hub.tab_changed.emit(index)

    def save_tab_geometry(self, tab_index: int) -> None:
        """Save geometry for a specific tab.

        Saves the window size and maximized state to settings.

        Args:
            tab_index: Index of the tab to save geometry for.
        """
        if tab_index not in self.TAB_NAMES:
            return

        tab_name = self.TAB_NAMES[tab_index]
        window = self._ctx.main_window

        # Check if window is maximized
        is_maximized = False
        if Qt is not None and hasattr(window, "windowState"):
            is_maximized = bool(window.windowState() & Qt.WindowState.WindowMaximized)

        # Save maximized state
        yaml_settings(bool, YAML.Settings, f"UI.window_geometry.{tab_name}.maximized", is_maximized)

        if is_maximized:
            # Save normal geometry (pre-maximized size)
            if hasattr(window, "normalGeometry"):
                normal_geom = window.normalGeometry()
                yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.width", normal_geom.width())
                yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.height", normal_geom.height())
                logger.debug(
                    f"Saved normal geometry for maximized {tab_name}: "
                    f"{normal_geom.width()}x{normal_geom.height()} (maximized=True)"
                )
            else:
                # Fallback if normalGeometry is not available
                current_size = window.size()
                yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.width", current_size.width())
                yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.height", current_size.height())
        else:
            # Save current size as normal
            current_size = window.size()
            yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.width", current_size.width())
            yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.height", current_size.height())
            logger.debug(f"Saved geometry for {tab_name}: {current_size.width()}x{current_size.height()}")

    def restore_tab_geometry(self, tab_index: int) -> None:
        """Restore geometry for a specific tab.

        Restores window size and maximized state from settings.

        Args:
            tab_index: Index of the tab to restore geometry for.
        """
        if tab_index not in self.TAB_NAMES:
            return

        tab_name = self.TAB_NAMES[tab_index]
        min_width, min_height = self.get_minimum_size_for_tab(tab_index)
        window = self._ctx.main_window

        # Get saved dimensions and state
        saved_width = yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.width", None)
        saved_height = yaml_settings(int, YAML.Settings, f"UI.window_geometry.{tab_name}.height", None)
        was_maximized = yaml_settings(bool, YAML.Settings, f"UI.window_geometry.{tab_name}.maximized", False)

        # Determine size to use
        if saved_width is not None and saved_height is not None:
            width = max(saved_width, min_width)
            height = max(saved_height, min_height)
            logger.debug(f"Restoring saved geometry for {tab_name}: {width}x{height} (maximized={was_maximized})")
        else:
            width = min_width
            height = min_height
            was_maximized = False
            logger.debug(f"Using default minimum size for {tab_name}: {width}x{height}")

        # Update window minimum size
        window.setMinimumSize(min_width, min_height)

        # Restore window state
        if was_maximized and Qt is not None and hasattr(window, "showMaximized"):
            window.resize(width, height)
            window.showMaximized()
            logger.debug(f"Restored {tab_name} to maximized state with normal size {width}x{height}")
        else:
            window.resize(width, height)
            if (
                Qt is not None
                and hasattr(window, "showNormal")
                and hasattr(window, "windowState")
                and window.windowState() & Qt.WindowState.WindowMaximized
            ):
                window.showNormal()

    def get_minimum_size_for_tab(self, tab_index: int) -> tuple[int, int]:
        """Get the minimum window size for a specific tab.

        Args:
            tab_index: Index of the tab.

        Returns:
            Tuple of (width, height) minimum size.
        """
        return self.DEFAULT_MIN_SIZES.get(tab_index, (550, 350))

    def save_current_tab_geometry(self) -> None:
        """Save geometry for the current tab.

        Called during application shutdown to persist window state.
        """
        tab_widget = self._ctx.ui_widgets.tab_widget
        if tab_widget is not None and self._geometry_initialized:
            current_index = tab_widget.currentIndex()
            self.save_tab_geometry(current_index)
            logger.debug(f"Saved final geometry for tab {current_index}")
