"""Main application window for the CLASSIC GUI.

Initializes and sets up the main GUI, including tabs, threads, and event
handlers necessary for the application's functionality. The application utilizes
multiple mix-ins to manage separate components such as folder management, backup
operations, and style setup. The main interaction entry point includes an instance
of MainWindow.
"""

import sys
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QMutex, QThread, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.Interface.BackupOperations import BackupOperationsMixin
from ClassicLib.Interface.FolderManagementMixin import FolderManagementMixin
from ClassicLib.Interface.HelpAndAboutMixin import HelpAndAboutMixin
from ClassicLib.Interface.PapyrusManager import PapyrusManagerMixin
from ClassicLib.Interface.PastebinMixin import PastebinMixin
from ClassicLib.Interface.PathDialogMixin import PathDialogMixin
from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin
from ClassicLib.Interface.ScanOperations import ScanOperationsMixin
from ClassicLib.Interface.StyleSheets import DARK_MODE
from ClassicLib.Interface.TabSetupMixin import TabSetupMixin
from ClassicLib.Interface.ThreadManager import get_thread_manager
from ClassicLib.Interface.UpdateManager import UpdateManagerMixin
from ClassicLib.Interface.WindowGeometryMixin import WindowGeometryMixin
from ClassicLib.Logger import logger
from ClassicLib.MessageHandler import init_message_handler, msg_error
from ClassicLib.SetupCoordinator import SetupCoordinator
from ClassicLib.YamlSettings import classic_settings, yaml_settings

if TYPE_CHECKING:
    from ClassicLib.Interface.Papyrus import PapyrusMonitorWorker, PapyrusStats
    from ClassicLib.Interface.PapyrusDialog import PapyrusMonitorDialog
    from ClassicLib.Interface.Workers import (
        UpdateCheckWorker,
    )

CHECKBOX_STYLE = """
    QCheckBox {
        spacing: 10px;
    }
    QCheckBox::indicator {
        width: 25px;
        height: 25px;
    }
    QCheckBox::indicator:unchecked {
        image: url("CLASSIC Data/graphics/unchecked.svg");
    }
    QCheckBox::indicator:checked {
        image: url("CLASSIC Data/graphics/checked.svg");
     }
"""

# TabSetupMixin methods are now inherited from TabSetupMixin
# Add this as a class constant near other style constants
BOTTOM_BUTTON_STYLE = """
    QPushButton {
        color: white;
        background: rgba(60, 60, 60, 0.9);
        border-radius: 5px;
        border: 1px solid #5c5c5c;
        font-size: 11px;
        padding: 6px 10px;
        min-height: 30px;
    }
    QPushButton:hover { background-color: rgba(80, 80, 80, 0.9); }
    QPushButton:pressed { background-color: rgba(40, 40, 40, 0.9); }
"""


# noinspection DuplicatedCode
class MainWindow(
    QMainWindow,
    ScanOperationsMixin,
    UpdateManagerMixin,
    FolderManagementMixin,
    BackupOperationsMixin,
    PapyrusManagerMixin,
    PastebinMixin,
    PathDialogMixin,
    TabSetupMixin,
    ResultsViewerMixin,
    HelpAndAboutMixin,
    WindowGeometryMixin,
):
    """Main application window for the CLASSIC GUI interface."""

    # Style constants are now imported from UIHelpers

    def __init__(self) -> None:
        """Initialize the main application window and set up its elements and layout.

        This constructor initializes the main application window, setting up various visual
        components, tabs, and threads necessary for the application's functionality. It configures
        the window properties such as title, icon, size, and layout while preparing the widgets and
        their placement in the UI. Additional application setup, including initializing paths,
        message handling, and the optional update check, is also performed.

        Raises:
            None

        """
        super().__init__()
        self.thread_manager = get_thread_manager()
        self.scan_button_group = QButtonGroup()
        self.papyrus_monitor_thread: QThread | None = None
        self.papyrus_monitor_worker: PapyrusMonitorWorker | None = None
        self.papyrus_monitor_dialog: PapyrusMonitorDialog | None = None
        self._last_stats: PapyrusStats | None = None
        self.update_check_thread: QThread | None = None
        self.update_check_worker: UpdateCheckWorker | None = None
        self._scan_mutex = QMutex()
        self._running_scans: set[str] = set()
        self.setWindowTitle(f"Crash Log Auto Scanner & Setup Integrity Checker | {yaml_settings(str, YAML.Main, 'CLASSIC_Info.version')}")
        local_dir_path = GlobalRegistry.get_local_dir(as_string=True)
        self.setWindowIcon(QIcon(f"{local_dir_path}/CLASSIC Data/graphics/CLASSIC.ico"))
        self.setStyleSheet(DARK_MODE)
        # Initial size will be set by WindowGeometryMixin
        self.setMinimumSize(550, 350)  # Default minimum, will be adjusted per tab
        self.resize(650, 350)  # Default size, will be overridden by saved geometry
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        self.main_tab = QWidget()
        self.backups_tab = QWidget()
        self.articles_tab = QWidget()
        self.results_tab = QWidget()
        self.tab_widget.addTab(self.main_tab, "MAIN OPTIONS")
        self.tab_widget.addTab(self.backups_tab, "FILE BACKUP")
        self.tab_widget.addTab(self.articles_tab, "ARTICLES")
        self.tab_widget.addTab(self.results_tab, "RESULTS")
        self.setup_main_tab()
        self.setup_backups_tab()
        self.setup_articles_tab()
        self.setup_results_tab()

        # Initialize window geometry management after tabs are set up
        self.setup_window_geometry()
        self.initialize_folder_paths()
        # noinspection PyTypeChecker
        init_message_handler(parent=self, is_gui_mode=True)
        # Initial setup should be handled by the entry point, not here
        # setup_coordinator = SetupCoordinator()
        # setup_coordinator.run_initial_setup()
        if classic_settings(bool, "Update Check"):
            QTimer.singleShot(0, self.update_popup)
        self.update_check_timer = QTimer()
        self.update_check_timer.timeout.connect(self.perform_update_check)
        self.is_update_check_running = False
        self.crash_logs_thread: QThread | None = None

    # Help and About methods are now inherited from HelpAndAboutMixin

    # Folder management methods are now inherited from FolderManagementMixin
    # crash_logs_scan method is now inherited from ScanOperationsMixin

    # game_files_scan method is now inherited from ScanOperationsMixin

    # disable_scan_buttons method is now inherited from ScanOperationsMixin

    # enable_scan_buttons method is now inherited from ScanOperationsMixin

    # crash_logs_scan_finished method is now inherited from ScanOperationsMixin

    # game_files_scan_finished method is now inherited from ScanOperationsMixin

    def closeEvent(self, event: Any) -> None:
        """Override closeEvent to ensure proper cleanup of all running threads.

        This method is called when the main window is being closed. It ensures
        all worker threads are properly stopped and cleaned up before the
        application exits using the central ThreadManager.

        Args:
            event: The close event

        """
        logger.info("Application closing - cleaning up resources...")

        # Save current tab's window geometry
        self.save_current_tab_geometry()

        # Stop Papyrus monitoring first to ensure worker cleanup
        if self.papyrus_monitor_worker is not None:
            logger.debug("Stopping Papyrus monitoring...")
            self.stop_papyrus_monitoring()

        # Use thread manager to stop all threads gracefully
        # 3-second timeout (task cleanup has 2s timeout, +1s for overhead)
        logger.debug("Stopping all managed threads...")
        self.thread_manager.stop_all_threads(wait_ms=3000)

        # Stop update check timer
        if hasattr(self, "update_check_timer") and self.update_check_timer:
            self.update_check_timer.stop()

        logger.info("Resource cleanup completed")

        # Accept the close event
        event.accept()

    @staticmethod
    def open_url(url: str) -> None:
        """Open the specified URL in the default web browser.

        Args:
            url (str): The URL to open in the browser.

        """
        QDesktopServices.openUrl(QUrl(url))


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
    window: MainWindow | None = None  # Initialize window to ensure it's defined
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except KeyboardInterrupt:
        app.exit(1)
    except Exception as exc:  # pyrefly: ignore  # noqa: BLE001
        msg_error(f"Unhandled exception during application startup: {exc}")
        if QApplication.instance():
            # noinspection PyTypeChecker
            QMessageBox.critical(None, "Application Startup Error", f"An critical error occurred: {exc}")  # pyrefly: ignore
        sys.exit(1)


if __name__ == "__main__":
    main()

    # Backup operations methods are now inherited from BackupOperationsMixin

    # create_separator moved to UIHelpers

    # TabSetupMixin methods are now inherited from TabSetupMixin
    # Add this constant to the MainWindow class alongside other style constants

    # Folder management methods are now inherited from FolderManagementMixin
    # crash_logs_scan method is now inherited from ScanOperationsMixin

    # game_files_scan method is now inherited from ScanOperationsMixin

    # disable_scan_buttons method is now inherited from ScanOperationsMixin

    # enable_scan_buttons method is now inherited from ScanOperationsMixin

    # crash_logs_scan_finished method is now inherited from ScanOperationsMixin

    # game_files_scan_finished method is now inherited from ScanOperationsMixin
