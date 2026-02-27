"""Main application window for the CLASSIC GUI.

Initializes and sets up the main GUI, including tabs, threads, and event
handlers necessary for the application's functionality. The application utilizes
a composition-based architecture with controller classes managing separate
components such as folder management, backup operations, and scan operations.
"""

import sys
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import ClassicLib.startup_validation as _startup_validation  # noqa: F401
from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.Interface.controllers.backup_manager import BackupManager
from ClassicLib.Interface.controllers.folder_manager import FolderManager
from ClassicLib.Interface.controllers.help_about import HelpAboutController
from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager
from ClassicLib.Interface.controllers.pastebin_controller import PastebinController
from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController
from ClassicLib.Interface.controllers.scan_controller import ScanController
from ClassicLib.Interface.controllers.ui_setup import UISetupController
from ClassicLib.Interface.controllers.update_manager import UpdateManager
from ClassicLib.Interface.controllers.window_geometry import WindowGeometryManager
from ClassicLib.Interface.shared.context import FeatureContext
from ClassicLib.Interface.shared.signal_hub import SignalHub
from ClassicLib.Interface.shared.style_sheets import DARK_MODE
from ClassicLib.Interface.workers.thread_manager import get_thread_manager
from ClassicLib.io.yaml import classic_settings, yaml_settings
from ClassicLib.messaging import init_message_handler, msg_error
from ClassicLib.support.setup import SetupCoordinator


class MainWindow(QMainWindow):
    """Main application window for the CLASSIC GUI interface.

    This class uses a composition-based architecture where functionality is
    delegated to controller classes rather than inherited from mixins.

    Attributes:
        thread_manager: Central thread lifecycle manager.
        signal_hub: Central hub for inter-component Qt signals.
        context: Dependency injection container for controllers.
        scan_controller: Handles crash logs and game files scanning.
        update_manager: Manages application update checking.
        papyrus_manager: Controls Papyrus log monitoring.
        pastebin_controller: Handles Pastebin log fetching.
        results_viewer: Manages results tab and report display.
        backup_manager: Handles backup/restore operations.
        folder_manager: Manages folder selection and validation.
        help_about: Provides help and about dialogs.
        window_geometry: Handles per-tab window sizing.
        ui_setup: Orchestrates UI tab setup.

    """

    def __init__(self) -> None:
        """Initialize the main application window and set up its elements.

        Creates the infrastructure (SignalHub, FeatureContext) and all
        controller instances, then sets up the UI through UISetupController.
        """
        super().__init__()

        # Create thread manager
        self.thread_manager = get_thread_manager()

        # Create central signal hub for inter-component communication
        self.signal_hub = SignalHub(self)

        # Create feature context for dependency injection
        self.context = FeatureContext(
            main_window=self,
            thread_manager=self.thread_manager,
            signal_hub=self.signal_hub,
        )

        # Set up window properties
        self.setWindowTitle(f"Crash Log Auto Scanner & Setup Integrity Checker | {yaml_settings(str, YAML.Main, 'CLASSIC_Info.version')}")
        local_dir_path = GlobalRegistry.get_local_dir(as_string=True)
        self.setWindowIcon(QIcon(f"{local_dir_path}/CLASSIC Data/graphics/CLASSIC.ico"))
        self.setStyleSheet(DARK_MODE)
        self.setMinimumSize(550, 580)
        self.resize(650, 580)

        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Create tab widgets
        self.main_tab = QWidget()
        self.backups_tab = QWidget()
        self.articles_tab = QWidget()
        self.results_tab = QWidget()
        self.tab_widget.addTab(self.main_tab, "MAIN OPTIONS")
        self.tab_widget.addTab(self.backups_tab, "FILE BACKUP")
        self.tab_widget.addTab(self.articles_tab, "ARTICLES")
        self.tab_widget.addTab(self.results_tab, "RESULTS")

        # Create scan button group and register with context
        self.scan_button_group = QButtonGroup()
        self.context.ui_widgets.scan_button_group = self.scan_button_group

        # Register tab widgets with context
        self.context.ui_widgets.tab_widget = self.tab_widget
        self.context.ui_widgets.main_tab = self.main_tab
        self.context.ui_widgets.backups_tab = self.backups_tab
        self.context.ui_widgets.articles_tab = self.articles_tab
        self.context.ui_widgets.results_tab = self.results_tab

        # Create controllers (order matters for dependencies)
        self.help_about = HelpAboutController(self.context)
        self.folder_manager = FolderManager(self.context)
        self.backup_manager = BackupManager(self.context)
        self.results_viewer = ResultsViewerController(self.context)
        self.papyrus_manager = PapyrusManager(self.context)
        self.pastebin_controller = PastebinController(self.context)
        self.update_manager = UpdateManager(self.context)
        self.scan_controller = ScanController(self.context)
        self.window_geometry = WindowGeometryManager(self.context)

        # Create UI setup controller with references to all other controllers
        self.ui_setup = UISetupController(
            context=self.context,
            scan=self.scan_controller,
            results=self.results_viewer,
            papyrus=self.papyrus_manager,
            backup=self.backup_manager,
            folder=self.folder_manager,
            help_about=self.help_about,
            update=self.update_manager,
            pastebin=self.pastebin_controller,
        )

        # Set up all tabs
        self.ui_setup.setup_all_tabs()

        # Initialize window geometry management after tabs are set up
        self.window_geometry.setup()

        # Initialize folder paths
        self.folder_manager.initialize_folder_paths()

        # Initialize message handler for GUI mode
        init_message_handler(parent=self, is_gui_mode=True)

        # Start update check if enabled
        if classic_settings(bool, "Update Check"):
            QTimer.singleShot(0, self.update_manager.update_popup)

    def closeEvent(self, event: Any) -> None:
        """Handle window close event with proper cleanup.

        Ensures all worker threads are properly stopped and cleaned up
        before the application exits using the central ThreadManager.
        Also properly closes database connections to ensure SQLite WAL
        files are checkpointed.

        Args:
            event: The close event.

        """
        logger.info("Application closing - cleaning up resources...")

        # Save current tab's window geometry
        self.window_geometry.save_current_tab_geometry()

        # Stop Papyrus monitoring
        if self.papyrus_manager.is_monitoring():
            logger.debug("Stopping Papyrus monitoring...")
            self.papyrus_manager.stop_monitoring()

        # Use thread manager to stop all threads gracefully
        logger.debug("Stopping all managed threads...")
        self.thread_manager.stop_all_threads(wait_ms=3000)

        # Stop update check timer
        self.update_manager.stop_timer()

        # Close database connections to ensure WAL files are properly checkpointed
        # This prevents .db-wal and .db-shm files from persisting after exit
        logger.debug("Closing database connections...")
        from ClassicLib.io.database import cleanup_database_pools

        cleanup_database_pools()

        logger.info("Resource cleanup completed")

        # Accept the close event
        event.accept()


def main() -> None:
    """Serve as main entry point for the CLASSIC GUI application.

    Initializes the Qt application, runs the setup coordinator to prepare
    the environment, creates the main window, and starts the event loop.
    Handles top-level exceptions and keyboard interrupts.
    """
    app: QApplication = QApplication(sys.argv)
    # Initialize application using SetupCoordinator
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=True)
    _manual_docs_gui: Any = GlobalRegistry.get_manual_docs_gui()
    _game_path_gui: Any = GlobalRegistry.get_game_path_gui()
    window: MainWindow | None = None
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except KeyboardInterrupt:
        app.exit(1)
    except Exception as exc:  # noqa: BLE001
        msg_error(f"Unhandled exception during application startup: {exc}")
        if QApplication.instance():
            QMessageBox.critical(None, "Application Startup Error", f"A critical error occurred: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
