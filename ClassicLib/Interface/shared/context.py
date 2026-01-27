"""Feature context and dependency injection for CLASSIC interface controllers.

This module provides the FeatureContext class for dependency injection and
UIWidgets dataclass for managing shared UI widget references across controllers.

Example:
    >>> from ClassicLib.Interface.context import FeatureContext, UIWidgets
    >>> context = FeatureContext(main_window, thread_manager, signal_hub)
    >>> context.ui_widgets.papyrus_button = some_button

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from PySide6.QtWidgets import (
        QButtonGroup,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QTabWidget,
        QWidget,
    )

    from ClassicLib.Interface.shared.signal_hub import SignalHub
    from ClassicLib.Interface.workers.ThreadManager import ThreadManager


@dataclass
class UIWidgets:
    """Container for shared UI widget references across controllers.

    This dataclass holds references to commonly accessed UI widgets that
    multiple controllers need to interact with. It provides a single source
    of truth for widget references, avoiding the need for controllers to
    hold individual references.

    All widget references are optional (defaulting to None) to support
    incremental initialization during MainWindow setup.

    Attributes:
        main_window: The main application window.
        tab_widget: The tab widget containing all tabs.
        main_tab: The main options tab widget.
        backups_tab: The file backup management tab widget.
        articles_tab: The useful resources/links tab widget.
        results_tab: The scan results viewer tab widget.
        scan_button_group: Button group for scan action buttons.
        papyrus_button: Toggle button for Papyrus monitoring.
        crash_logs_button: Button to trigger crash logs scan.
        game_files_button: Button to trigger game files scan.
        mods_folder_edit: Line edit for mods staging folder path.
        scan_folder_edit: Line edit for custom scan folder path.
        pastebin_id_input: Line edit for Pastebin URL/ID input.
        pastebin_fetch_button: Button to fetch Pastebin content.

    Example:
        >>> widgets = UIWidgets(main_window=window, tab_widget=tabs)
        >>> widgets.papyrus_button = papyrus_btn
        >>> print(widgets.papyrus_button.text())
        START PAPYRUS MONITORING

    """

    # Required widgets (set during construction)
    main_window: QMainWindow | None = None
    tab_widget: QTabWidget | None = None

    # Tab widgets
    main_tab: QWidget | None = None
    backups_tab: QWidget | None = None
    articles_tab: QWidget | None = None
    results_tab: QWidget | None = None

    # Button groups and scan buttons
    scan_button_group: QButtonGroup | None = None
    crash_logs_button: QPushButton | None = None
    game_files_button: QPushButton | None = None
    papyrus_button: QPushButton | None = None

    # Folder input widgets
    mods_folder_edit: QLineEdit | None = None
    scan_folder_edit: QLineEdit | None = None

    # Pastebin widgets
    pastebin_id_input: QLineEdit | None = None
    pastebin_fetch_button: QPushButton | None = None
    pastebin_label: QWidget | None = None


class FeatureContext:
    """Dependency injection container for all UI controllers.

    FeatureContext provides a single object through which controllers can
    access all their dependencies. This enables:
    - Constructor-based dependency injection
    - Easy mocking for testing
    - Clear documentation of what each controller needs
    - Decoupled component architecture

    The context is created once by MainWindow and passed to all controllers
    at construction time. Controllers should not create their own contexts.

    Attributes:
        main_window: The main application window (QMainWindow).
        thread_manager: ThreadManager for thread lifecycle management.
        signal_hub: SignalHub for inter-component communication.
        ui_widgets: UIWidgets container for shared widget references.

    Example:
        >>> context = FeatureContext(window, thread_mgr, signal_hub)
        >>> scan_ctrl = ScanController(context)
        >>> results_ctrl = ResultsViewerController(context)

    """

    def __init__(
        self,
        main_window: QMainWindow,
        thread_manager: ThreadManager,
        signal_hub: SignalHub,
    ) -> None:
        """Initialize the FeatureContext with required dependencies.

        Args:
            main_window: The main application window.
            thread_manager: ThreadManager instance for thread lifecycle.
            signal_hub: SignalHub instance for inter-component signals.

        """
        self._main_window = main_window
        self._thread_manager = thread_manager
        self._signal_hub = signal_hub
        self._ui_widgets = UIWidgets(main_window=main_window)

    @property
    def main_window(self) -> QMainWindow:
        """Get the main application window.

        Returns:
            The QMainWindow instance.

        """
        return self._main_window

    @property
    def thread_manager(self) -> ThreadManager:
        """Get the thread manager for thread lifecycle operations.

        Returns:
            The ThreadManager instance.

        """
        return self._thread_manager

    @property
    def signal_hub(self) -> SignalHub:
        """Get the signal hub for inter-component communication.

        Returns:
            The SignalHub instance.

        """
        return self._signal_hub

    @property
    def ui_widgets(self) -> UIWidgets:
        """Get the UI widgets container.

        Returns:
            The UIWidgets instance containing shared widget references.

        """
        return self._ui_widgets

    @property
    def local_dir(self) -> Path | str | None:
        """Get the application local directory.

        This is a convenience property that retrieves the local directory
        from GlobalRegistry, commonly used by multiple controllers.

        Returns:
            Path to the local directory, or None if not configured.

        """
        from ClassicLib import GlobalRegistry

        return GlobalRegistry.get_local_dir()
