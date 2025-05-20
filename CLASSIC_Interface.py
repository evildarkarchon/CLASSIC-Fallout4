import asyncio
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, cast

import regex as re
from PySide6.QtCore import QObject, Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from CLASSIC_Main import initialize, main_generate_required
from CLASSIC_ScanGame import game_files_manage, write_combined_results
from CLASSIC_ScanLogs import crashlogs_scan
from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.Interface.Audio import AudioPlayer
from ClassicLib.Interface.Papyrus import PapyrusMonitorWorker, PapyrusStats
from ClassicLib.Interface.Pastebin import PastebinFetchWorker
from ClassicLib.Interface.PathDialog import ManualPathDialog
from ClassicLib.Interface.StyleSheets import DARK_MODE
from ClassicLib.Logger import logger
from ClassicLib.Update import UpdateCheckError, is_latest_version
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


# noinspection PyTypeChecker
def show_game_path_dialog_static() -> Path | None:
    """
    Shows a dialog for selecting the game installation path without requiring an instance.
    Allows the user to cancel, which will exit the application.

    Returns:
        Path to the selected valid game directory if successful, None if user cancels
    """
    from ClassicLib.Interface.PathDialog import ManualPathDialog

    exe_name: str = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"
    game_name: str = GlobalRegistry.get_game()
    # Create a dialog with appropriate title and descriptive label
    dialog: ManualPathDialog = ManualPathDialog(
        parent=None,  # No parent since this is static
        title="Set Game Installation Path",
        label=f"Select the installation directory for {game_name}",
    )
    while True:
        # Process the dialog result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            game_path: Path = Path(dialog.get_path())

            # Validate that the directory contains the game executable
            if game_path and game_path.is_dir() and game_path.joinpath(exe_name).is_file():
                return game_path
            # Show error and continue loop to try again
            QMessageBox.critical(
                None,  # pyrefly: ignore
                "Invalid Game Directory",
                f"❌ ERROR: No {exe_name} file found in '{game_path}'!\n\nPlease select the correct game directory.",
            )
        else:
            # User cancelled - show confirmation dialog
            reply = QMessageBox.question(
                None,  # pyrefly: ignore
                "Exit Application?",
                "A valid game path is required to continue.\nDo you want to exit the application?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Exit the application
                print("User chose to exit the application.")
                sys.exit(0)  # Exit with success code
            # If No, the loop continues and shows the dialog again


class CustomAboutDialog(QDialog):
    """
    A class representing an "About" dialog window, providing information about the application,
    icon, contributors, and a close button for dismissing the dialog. The dialog is designed
    to have similar style and layout to a QMessageBox's "About" dialog, with custom text and
    an application-specific icon.
    """

    TITLE = "About"
    MIN_WIDTH = 500
    MIN_HEIGHT = 200
    ICON_SIZE = 128
    MARGIN = 15

    def __init__(self, parent: QMainWindow | QDialog | None = None) -> None:
        """
        Initialize the About dialog.

        Args:
            parent: Optional parent widget to associate the "About" dialog with. It can be an
                instance of QMainWindow, QDialog, or None if no parent is provided.
        """
        super().__init__(parent)
        self.setWindowTitle(self.TITLE)
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # Create main layout
        layout: QVBoxLayout = self._create_main_layout()

        # Create and add horizontal layout with icon and text
        h_layout: QHBoxLayout = self._create_icon_text_layout()
        layout.addLayout(h_layout)

        # Add close button
        close_button: QPushButton = self._create_close_button()
        layout.addWidget(close_button)
        layout.setAlignment(close_button, Qt.AlignmentFlag.AlignRight)

    def _create_main_layout(self) -> QVBoxLayout:
        """Create and return the main layout with proper margins."""
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN)
        return layout

    def _create_icon_text_layout(self) -> QHBoxLayout:
        """Create and return the horizontal layout with icon and text."""
        h_layout: QHBoxLayout = QHBoxLayout()

        # Add icon
        icon_label: QLabel = QLabel(self)
        icon_path: str = f"{GlobalRegistry.get_local_dir(as_string=True)}/CLASSIC Data/graphics/CLASSIC.ico"
        pixmap: QPixmap = QIcon(icon_path).pixmap(self.ICON_SIZE, self.ICON_SIZE)

        if not pixmap.isNull():
            icon_label.setPixmap(pixmap)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        h_layout.addWidget(icon_label)

        # Add text
        text = (
            "Crash Log Auto Scanner & Setup Integrity Checker\n\n"
            "Made by: Poet\n"
            "Contributors: evildarkarchon | kittivelae | AtomicFallout757 | wxMichael"
        )

        text_label: QLabel = QLabel(text)
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        text_label.setWordWrap(True)

        h_layout.addWidget(text_label)
        return h_layout

    def _create_close_button(self) -> QPushButton:
        """Create and return the close button."""
        close_button: QPushButton = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        return close_button


class OutputRedirector(QObject):
    """
    Acts as a redirector for output, allowing text to be emitted through a signal.

    This class provides functionality to intercept and redirect standard output or any textual
    messages to a custom signal (`outputWritten`). It is particularly useful for capturing and
    managing output in a graphical user interface or other similar contexts where direct use
    of standard output is not ideal.

    Attributes:
        outputWritten (Signal): A signal emitted when text is written, carrying the emitted text as a string.
    """

    outputWritten: Signal = Signal(str)

    def write(self, text: str) -> None:
        """
        Emits the given text as a signal.

        Args:
            text (str): The text to be emitted.
        """
        self.outputWritten.emit(str(text))

    def flush(self) -> None:
        """
        Flushes the current state. This method is a placeholder and does not perform any operations.
        """


class CrashLogsScanWorker(QObject):
    """
    CrashLogsScanWorker is a QObject-based worker class responsible for scanning crash logs and emitting signals based on the scan's outcome.
    Methods:
        run(): Executes the crash logs scan and emits appropriate signals based on the outcome.
    """

    finished: Signal = Signal()
    notify_sound_signal: Signal = Signal()
    error_sound_signal: Signal = Signal()
    custom_sound_signal: Signal = Signal(str)  # In case a custom sound needs to be played

    # noinspection PyBroadException

    @Slot()
    def run(self) -> None:
        """
        Triggers a scan process, determines appropriate audio notification based on the outcome,
        and emits corresponding signals. Upon completion, it ensures the finished signal is emitted
        regardless of the outcome.

        Slot:
            Decorates the method to indicate that it is callable as a slot in the context
            of PyQt/PySide signal-slot mechanism.

        Raises:
            Exception: Propagates any raised exception if audio notifications are disabled.
        """
        # noinspection PyShadowingNames
        try:
            self._perform_crash_logs_scan()
            self._play_success_notification()
        except Exception as e:  # noqa: BLE001
            self._handle_scan_error(e)
        finally:
            self.finished.emit()  # type: ignore

    @staticmethod
    def _perform_crash_logs_scan() -> None:
        """Executes the crash logs scan operation."""
        logger.debug("Starting crash logs scan")
        crashlogs_scan()
        logger.debug("Crash logs scan completed successfully")

    def _play_success_notification(self) -> None:
        """Plays a notification sound for successful scan."""
        self.notify_sound_signal.emit()  # type: ignore

    def _handle_scan_error(self, error: Exception) -> None:
        """
        Handles errors during the scan process based on user settings.

        Args:
            error: The exception that occurred during scanning

        Raises:
            Exception: Re-raises the exception if audio notifications are disabled
        """
        logger.error(f"Crash logs scan failed: {error!s}")

        audio_notifications_enabled: bool | None = classic_settings(bool, "Audio Notifications")
        if audio_notifications_enabled:
            self.error_sound_signal.emit()  # type: ignore
        else:
            raise error


# noinspection PyBroadException
class GameFilesScanWorker(QObject):
    """
    A worker class responsible for scanning game files in a separate thread.

    This class processes game results and provides audio notifications based on
    the outcome of the scanning process.

    Signals:
        scan_finished: Emitted when the scanning process completes (success or failure)
        play_success_sound: Emitted when processing completes successfully
        play_error_sound: Emitted when an error occurs during processing
        play_custom_sound: Emitted with a path to a custom sound to play
    """

    scan_finished: Signal = Signal()
    play_success_sound: Signal = Signal()
    play_error_sound: Signal = Signal()
    play_custom_sound: Signal = Signal(str)

    @Slot()
    def run(self) -> None:
        """
        Executes the game files scanning process.

        Processes game result data and handles appropriate audio notifications
        based on the outcome and user settings. Always emits the scan_finished
        signal when complete.
        """
        try:
            self._process_game_results()
            self._notify_success()
        except Exception as e:  # noqa: BLE001
            self._handle_error(e)
        finally:
            self.scan_finished.emit()  # type: ignore

    @staticmethod
    def _process_game_results() -> None:
        """Process and write the combined game results data."""
        write_combined_results()

    def _notify_success(self) -> None:
        """Play success notification sound."""
        self.play_success_sound.emit()  # type: ignore

    def _handle_error(self, error: Exception) -> None:
        """Handle exceptions based on user audio notification settings."""
        if classic_settings(bool, "Audio Notifications"):
            self.play_error_sound.emit()  # type: ignore
        else:
            raise error


# noinspection DuplicatedCode
class MainWindow(QMainWindow):
    # Style constants for the class
    ENABLED_BUTTON_STYLE = """
            QPushButton {
                color: black;
                background: rgb(250, 250, 250);
                border-radius: 10px;
                border: 2px solid black;
            }
        """

    def __init__(self) -> None:
        """
        Represents the main application GUI for managing crash log scanning, game file integrity checking,
        and manual document retrieval. This class handles initialization of UI components, worker threads,
        and various functionalities pertaining to application settings and external services like Pastebin.
        It also includes custom exception handling, style configuration, and dynamic update checking for
        the application.
        """
        super().__init__()
        self.pastebin_worker: PastebinFetchWorker | None = None
        self.pastebin_thread = QThread()
        self.game_files_worker: GameFilesScanWorker | None = None
        self.crash_logs_worker: CrashLogsScanWorker | None = None
        self.papyrus_button: QPushButton | None = None
        self.game_files_button: QPushButton | None = None
        self.crash_logs_button: QPushButton | None = None
        self.output_redirector: OutputRedirector | None = None
        self.output_text_box: QTextEdit | None = None
        self.scan_folder_edit: QLineEdit | None = None
        self.mods_folder_edit: QLineEdit | None = None
        self.pastebin_fetch_button: QPushButton | None = None
        self.pastebin_id_input: QLineEdit | None = None
        self.pastebin_label: QLabel | None = None
        self.papyrus_monitor_thread: QThread | None = None
        self.papyrus_monitor_worker: PapyrusMonitorWorker | None = None
        self._last_stats: PapyrusStats | None = None
        self.pastebin_url_regex: re.Pattern = re.compile(r"^https?://pastebin\.com/(\w+)$")

        self.setWindowTitle(f"Crash Log Auto Scanner & Setup Integrity Checker | {yaml_settings(str, YAML.Main, 'CLASSIC_Info.version')}")
        # Ensure GlobalRegistry.get_local_dir() returns a Path or string
        local_dir_path = GlobalRegistry.get_local_dir(as_string=True)
        self.setWindowIcon(QIcon(f"{local_dir_path}/CLASSIC Data/graphics/CLASSIC.ico"))

        self.setStyleSheet(DARK_MODE)
        self.setMinimumSize(350, 475)
        # self.setMaximumSize(700, 950) # Keep this commented or removed for resizability
        # self.setFixedSize(700, 950)  # Set fixed size to prevent resizing, for now.

        # --- Set preferred initial size ---
        self.resize(750, 950)  # <<< SET YOUR DESIRED STARTUP SIZE HERE

        self.audio_player = AudioPlayer()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        self.main_tab = QWidget()
        self.backups_tab = QWidget()
        self.tab_widget.addTab(self.main_tab, "MAIN OPTIONS")
        self.tab_widget.addTab(self.backups_tab, "FILE BACKUP")
        self.scan_button_group = QButtonGroup()
        self.setup_main_tab()
        self.setup_backups_tab()

        self.initialize_folder_paths()
        self.setup_output_redirection()
        self.output_buffer = ""  # Initialize output_buffer
        main_generate_required()

        if classic_settings(bool, "Update Check"):
            QTimer.singleShot(0, self.update_popup)

        self.update_check_timer = QTimer()
        self.update_check_timer.timeout.connect(self.perform_update_check)
        self.is_update_check_running = False

        self.crash_logs_thread: QThread | None = None
        self.game_files_thread: QThread | None = None

        # self.manual_docs_gui = ManualPathDialog(self)
        # self.game_path_gui = ManualPathDialog(self)
        GlobalRegistry.register(GlobalRegistry.Keys.MANUAL_DOCS_GUI, self.show_manual_docs_path_dialog)
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH_GUI, self.show_game_path_dialog)

    def setup_pastebin_elements(self, layout: QVBoxLayout) -> None:
        """
        Set up the UI elements to fetch logs from Pastebin and add them to the provided layout.

        This method initializes and configures UI components, including a QLabel for Pastebin
        instructions, a QLineEdit for Pastebin URL or ID input, and a QPushButton to trigger
        the fetch operation. These components are arranged in a horizontal layout before
        being added to the parent vertical layout.

        Args:
            layout (QVBoxLayout): The parent layout to which the Pastebin elements are added.
        """
        pastebin_layout: QHBoxLayout = QHBoxLayout()

        self.pastebin_label = QLabel("PASTEBIN LOG FETCH", self)
        self.pastebin_label.setToolTip("Fetch a log file from Pastebin. Can be used more than once.")
        pastebin_layout.addWidget(self.pastebin_label)

        pastebin_layout.addSpacing(50)

        self.pastebin_id_input = QLineEdit(self)
        self.pastebin_id_input.setPlaceholderText("Enter Pastebin URL or ID")
        self.pastebin_id_input.setToolTip("Enter the Pastebin URL or ID to fetch the log. Can be used more than once.")
        pastebin_layout.addWidget(self.pastebin_id_input)

        self.pastebin_fetch_button = QPushButton("Fetch Log", self)
        self.pastebin_fetch_button.clicked.connect(self.fetch_pastebin_log)
        if self.pastebin_id_input:  # Ensure pastebin_id_input is not None
            self.pastebin_fetch_button.clicked.connect(self.pastebin_id_input.clear)
        self.pastebin_fetch_button.setToolTip("Fetch the log file from Pastebin. Can be used more than once.")
        pastebin_layout.addWidget(self.pastebin_fetch_button)

        layout.addLayout(pastebin_layout)

    def fetch_pastebin_log(self) -> None:
        """
            Fetches a log from a Pastebin URL or ID provided by the user and processes it in a separate thread
            using asynchronous operations.

            This method retrieves the text from a user input field, verifies if it matches a Pastebin URL pattern,
            or formats it into a valid Pastebin URL if an ID is provided. It then sets up a separate thread and a
            worker object to handle the fetching process asynchronously using the pastebin_fetch_async function,
            ensuring the main application's UI remains responsive. User feedback is provided through message boxes
            based on the success or failure of the log retrieval process.

        Raises:
            SignalErrors: Raised when the worker encounters an error during network operations or data processing.

        Returns:
            None
        """
        if self.pastebin_id_input is None:
            return  # Should not happen if UI is setup correctly

        input_text: str = self.pastebin_id_input.text().strip()
        url: str = input_text if self.pastebin_url_regex.match(input_text) else f"https://pastebin.com/{input_text}"

        # Create thread and worker
        # Store the thread and worker as instance attributes to prevent them from being garbage collected prematurely
        self.pastebin_worker = PastebinFetchWorker(url)
        self.pastebin_worker.moveToThread(self.pastebin_thread)

        # Connect signals
        self.pastebin_thread.started.connect(self.pastebin_worker.run)
        self.pastebin_worker.finished.connect(self.pastebin_thread.quit)
        self.pastebin_worker.finished.connect(self.pastebin_worker.deleteLater)
        self.pastebin_thread.finished.connect(self.pastebin_thread.deleteLater)

        # Use lambdas or functools.partial if arguments need to be passed to slots
        self.pastebin_worker.success.connect(lambda pb_source: QMessageBox.information(self, "Success", f"Log fetched from: {pb_source}"))
        self.pastebin_worker.error.connect(lambda err: QMessageBox.warning(self, "Error", f"Failed to fetch log: {err}"))

        self.pastebin_thread.start()

    def show_manual_docs_path_dialog(self) -> None:
        """
        Opens a dialog for selecting the manual documentation path.

        Displays a custom dialog that allows the user to browse for or manually enter
        the documentation path. If the user confirms their selection, the path is stored
        in the GlobalRegistry for access by other components.
        """
        # Create a dialog with appropriate title and descriptive label
        dialog: ManualPathDialog = ManualPathDialog(
            parent=self, title="Set INI Path", label=f"Select the location of your {GlobalRegistry.get_game()} INI files"
        )

        # Process the dialog result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            manual_path: str = dialog.get_path()
            # Store the path in the GlobalRegistry for access by other components
            GlobalRegistry.register(GlobalRegistry.Keys.DOCS_PATH, manual_path)

    def show_game_path_dialog(self) -> None:
        """
        Opens a dialog for selecting the game installation path.

        Displays a custom dialog that allows the user to browse for or manually enter
        the game installation directory. If the user confirms their selection, the path
        is stored in the GlobalRegistry for access by other components.
        """
        # Create a dialog with appropriate title and descriptive label
        dialog: ManualPathDialog = ManualPathDialog(
            parent=self, title="Set Game Installation Path", label=f"Select the installation directory for {GlobalRegistry.get_game()}"
        )

        # Process the dialog result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            game_path: str = dialog.get_path()
            # Store the path in the GlobalRegistry for access by other components
            GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)

    # noinspection PyUnresolvedReferences
    def update_popup(self) -> None:
        """
        Starts the update check process when the update popup is invoked.

        This method initiates the update checking process by setting the
        `is_update_check_running` flag to True and starting the
        `update_check_timer` with immediate execution.

        Attributes:
            is_update_check_running (bool): Tracks if the update check process is currently running.
            update_check_timer (QTimer): Timer object used to schedule and manage the update checks.

        """
        if not self.is_update_check_running:
            self.is_update_check_running = True
            self.update_check_timer.start(0)  # Start immediately

    # noinspection PyUnresolvedReferences
    def update_popup_explicit(self) -> None:
        """
        Executes an explicit popup update by modifying the update timer's behavior and
        initiating the update process, ensuring the check occurs immediately.

        This function disconnects the timer's default slot for performing an update
        check and reconnects it to a more immediate update check method. If no update
        is currently in progress, it sets the appropriate flag and starts the timer
        with no delay, triggering the explicit check process.

        Attributes:
            update_check_timer (QTimer): Timer used for managing periodic update
                checks in the application.
            is_update_check_running (bool): Flag indicating whether an update check
                is currently in progress.
        """
        self.update_check_timer.timeout.disconnect(self.perform_update_check)
        self.update_check_timer.timeout.connect(self.force_update_check)
        if not self.is_update_check_running:
            self.is_update_check_running = True
            self.update_check_timer.start(0)

    def perform_update_check(self) -> None:
        """
        Stops the update check timer and performs an asynchronous update check.

        This method is responsible for stopping the ongoing update check timer and
        invokes the asynchronous update check function to ensure that updates are
        checked in an orderly and non-blocking manner. It ensures the checking
        process is executed correctly using asyncio.

        Raises:
            RuntimeError: If there is any issue in running the coroutine due to
                an improper event loop state.

        """
        self.update_check_timer.stop()
        asyncio.run(self.async_update_check())

    def force_update_check(self) -> None:
        """
        Directly initiates an update check process, bypassing any saved settings or
        scheduled events to trigger the process immediately. This function ensures that
        any update checking mechanism will execute explicitly without user configuration
        intervention.

        Args:
            self: Refers to the current object instance where the method is called.

        Raises:
            Any exceptions raised during the execution of the asynchronous update
            checking routine initiated by `asyncio.run`.
        """
        # Directly perform the update check without reading from settings
        self.is_update_check_running = True
        self.update_check_timer.stop()
        asyncio.run(self.async_update_check_explicit())  # Perform async check

    async def async_update_check(self) -> None:
        """
        Checks for updates asynchronously to determine whether the software is up to date.

        This method performs an asynchronous operation to check if the current version is
        the latest version available. If an update is available or an error occurs during
        the check, appropriate methods are called to handle these scenarios. Additionally,
        a timer that monitors the update check process is stopped once the operation concludes,
        ensuring no unnecessary resources are consumed.

        Raises:
            UpdateCheckError: If an error occurs during the version check process.
        """
        if GlobalRegistry.get(GlobalRegistry.Keys.IS_PRERELEASE):
            return
        # noinspection PyShadowingNames
        try:
            is_up_to_date: bool = await is_latest_version(quiet=True)
            self.show_update_result(is_up_to_date)
        except UpdateCheckError as e:
            self.show_update_error(str(e))
        finally:
            self.is_update_check_running = False
            self.update_check_timer.stop()  # Ensure the timer is always stopped

    async def async_update_check_explicit(self) -> None:
        """
        Asynchronously checks for software updates explicitly by calling an external
        update-checking service and handles the results or errors appropriately.

        This function ensures the application's update status is verified by querying
        whether the current version is the latest one or not. It provides feedback on
        the result or errors encountered during the process and ensures cleanup in
        case of failures or exceptions.

        Raises:
            UpdateCheckError: If an error occurs when checking for updates.

        Returns:
            None: This function has no return value.
        """
        if GlobalRegistry.get(GlobalRegistry.Keys.IS_PRERELEASE):
            self.show_update_error("Software is in pre-release stage, update check skipped.")
            return
        # noinspection PyShadowingNames
        try:
            is_up_to_date: bool = await is_latest_version(quiet=True, gui_request=True)
            self.show_update_result(is_up_to_date)
        except UpdateCheckError as e:
            self.show_update_error(str(e))
        finally:
            self.is_update_check_running = False
            self.update_check_timer.stop()  # Ensure the timer is always stopped

    def show_update_result(self, is_up_to_date: bool) -> None:
        """
        Displays update result to the user in a message box and handles further actions based
        on the user's response if an update is available.

        Args:
            is_up_to_date: Indicates whether the application is already up to date. If True,
                a message box informs the user that they have the latest version. If False, the
                user is prompted with a choice to visit the update page.
        """
        if is_up_to_date:
            QMessageBox.information(self, "CLASSIC UPDATE", "You have the latest version of CLASSIC!", QMessageBox.StandardButton.Ok)
        else:
            update_popup_text: str = yaml_settings(str, YAML.Main, "CLASSIC_Interface.update_popup_text") or ""
            result = QMessageBox.question(
                self,
                "CLASSIC UPDATE",
                update_popup_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.NoButton,
            )
            if result == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl("https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/latest"))

    def show_update_error(self, error_message: str) -> None:
        """
        Displays a warning message with an error description when the application fails to check
        for updates. This method provides user feedback in case of an update failure by showing
        a warning dialog box with the specified error details.

        Args:
            error_message: The error message describing the reason for the update check failure.
        """
        QMessageBox.warning(
            self,
            "Update Check Failed",
            f"Failed to check for updates: {error_message}",
            QMessageBox.StandardButton.NoButton,
            QMessageBox.StandardButton.NoButton,
        )

    # noinspection PyUnresolvedReferences
    def setup_main_tab(self) -> None:
        """Sets up the main UI elements for the main tab.

        This method initializes and organizes various UI components on the main tab, including
        folder selection sections, buttons, checkboxes, articles, and output sections. The layout
        is configured with specific margins, spacing, and separator widgets to provide a structured
        and user-friendly interface.

        Attributes:
            mods_folder_edit (QWidget): The input widget for the staging mods folder selection.
            scan_folder_edit (QWidget): The input widget for the custom scan folder selection.
            output_text_box (QWidget or None): The widget for the output text box, if initialized.

        Returns:
            None
        """
        layout: QVBoxLayout = QVBoxLayout(self.main_tab)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        # Top section
        self.mods_folder_edit = self.setup_folder_section(
            layout,
            "STAGING MODS FOLDER",
            "Box_SelectedMods",
            self.select_folder_mods,
            tooltip="Select the folder where your mod manager (e.g., MO2) stages your mods.",
        )
        if self.mods_folder_edit:  # Check if it was created
            self.mods_folder_edit.setPlaceholderText("Optional: Select your mod staging folder (e.g., MO2/mods)")

        self.scan_folder_edit = self.setup_folder_section(
            layout,
            "CUSTOM SCAN FOLDER",
            "Box_SelectedScan",
            self.select_folder_scan,
            tooltip="Select a custom folder containing crash logs to scan.",
        )
        if self.scan_folder_edit:  # Check if it was created
            self.scan_folder_edit.setPlaceholderText("Optional: Select a custom folder with crash logs")

        # self.setup_pastebin_elements(layout)  # Re-enabled Pastebin elements

        layout.addWidget(self.create_separator())
        self.setup_main_buttons(layout)
        layout.addWidget(self.create_separator())
        self.setup_checkboxes(layout)
        # Articles section - No separator before it if checkboxes are directly above
        self.setup_articles_section(layout)
        layout.addWidget(self.create_separator())
        self.setup_bottom_buttons(layout)
        self.setup_output_text_box(layout)

    def setup_backups_tab(self) -> None:
        """
        Configures the user interface layout and behavior for the "Backups" tab. This includes
        adding explanatory labels, dynamically created category buttons for managing backups,
        and additional functionality such as enabling/disabling restore buttons based on the
        existence of backups. The tab provides capabilities to backup, restore, and remove files
        related to specific categories such as XSE, RESHADE, VULKAN, and ENB.

        Returns:
            None
        """
        layout: QVBoxLayout = QVBoxLayout(self.backups_tab)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        layout.addWidget(QLabel("BACKUP > Backup files from the game folder into the CLASSIC Backup folder."))
        layout.addWidget(QLabel("RESTORE > Restore file backup from the CLASSIC Backup folder into the game folder."))
        layout.addWidget(QLabel("REMOVE > Remove files only from the game folder without removing existing backups."))

        categories: list[str] = ["XSE", "RESHADE", "VULKAN", "ENB"]
        for category in categories:
            self.add_backup_section(layout, category, category)  # type: ignore

        layout.addStretch(1)  # Push content to the top

        bottom_layout: QHBoxLayout = QHBoxLayout()
        open_backups_button: QPushButton = QPushButton("OPEN CLASSIC BACKUPS")
        open_backups_button.clicked.connect(self.open_backup_folder)
        bottom_layout.addWidget(open_backups_button)
        bottom_layout.addStretch(1)  # Keep button to the left
        layout.addLayout(bottom_layout)

        self.check_existing_backups()

    def check_existing_backups(self) -> None:
        """
        Checks the existence of backup directories for specific categories and updates
        UI restore buttons accordingly.

        This method assesses whether backup folders for particular categories exist and
        contain any files. If such conditions are met, corresponding restore buttons in
        the UI are enabled and visually updated with a specific stylesheet. The process
        is automated for the predefined categories.

        Returns:
            None
        """
        for category in ["XSE", "RESHADE", "VULKAN", "ENB"]:
            backup_path: Path = Path(f"CLASSIC Backup/Game Files/Backup {category}")
            if backup_path.is_dir() and any(backup_path.iterdir()):
                restore_button: Any | None = getattr(self, f"RestoreButton_{category}", None)
                if restore_button:
                    restore_button.setEnabled(True)
                    restore_button.setStyleSheet(
                        """
                        QPushButton {
                            color: black;
                            background: rgb(250, 250, 250);
                            border-radius: 10px;
                            border: 2px solid black;
                        }
                    """
                    )

    def add_backup_section(self, layout: QBoxLayout, title: str, backup_type: Literal["XSE", "RESHADE", "VULKAN", "ENB"]) -> None:
        """
        Adds a backup section to the given layout with a specified title
        and backup type. The section includes a title label and three buttons
        for backup, restore, and remove actions related to the specified
        backup type.

        Args:
            layout (QBoxLayout): Layout where the backup section will be added.
            title (str): Title to display at the top of the backup section.
            backup_type (Literal["XSE", "RESHADE", "VULKAN", "ENB"]):
                Type of backup for which the section is being created.

        """
        layout.addWidget(self.create_separator())

        title_label: QLabel = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        buttons_layout: QHBoxLayout = QHBoxLayout()
        buttons_layout.setSpacing(10)  # Add spacing between buttons

        backup_button: QPushButton = QPushButton(f"BACKUP {backup_type}")
        restore_button: QPushButton = QPushButton(f"RESTORE {backup_type}")
        remove_button: QPushButton = QPushButton(f"REMOVE {backup_type}")

        # Store restore button for later enabling/disabling
        setattr(self, f"RestoreButton_{backup_type}", restore_button)

        button_style_sheet = """
            QPushButton {{
                color: white;
                background: rgba(60, 60, 60, 0.9); /* Slightly lighter than main background */
                border-radius: 5px; /* Softer corners */
                border: 1px solid #5c5c5c;
                font-size: 12px; /* Slightly larger font */
                padding: 8px; /* Add some padding */
                min-height: 40px; /* Adjust height */
            }}
            QPushButton:hover {{
                background-color: rgba(80, 80, 80, 0.9);
            }}
            QPushButton:pressed {{
                background-color: rgba(40, 40, 40, 0.9);
            }}
            QPushButton:disabled {{
                color: grey;
                background-color: rgba(45, 45, 45, 0.75); /* Darker for disabled */
                border: 1px solid #444444;
            }}
        """

        for button, action in [
            (backup_button, "BACKUP"),
            (restore_button, "RESTORE"),
            (remove_button, "REMOVE"),
        ]:
            button.clicked.connect(
                lambda b=backup_type, a=action: self.classic_files_manage(  # checked arg for signal
                    f"Backup {b}",
                    a,  # type: ignore
                )
            )
            button.setStyleSheet(button_style_sheet)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # Allow horizontal expansion
            buttons_layout.addWidget(button)

            restore_button.setEnabled(False)  # Initially disabled

        layout.addLayout(buttons_layout)

    def _validate_selected_list_format(self, selected_list: str) -> list[str]:
        """
        Validates the format of the selected list string.

        Args:
            selected_list (str): The string to validate, expected format "Backup TYPE".

        Returns:
            list[str]: A list containing the parts of the string if valid.

        Raises:
            ValueError: If the selected_list format is invalid.
        """
        parts: list[str] = selected_list.split()
        if len(parts) != 2 or parts[0] != "Backup":
            raise ValueError(f"Invalid format for selected_list: '{selected_list}'. Expected 'Backup TYPE'.")
        return parts

    def classic_files_manage(self, selected_list: str, selected_mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
        """
        Manages game files by performing operations such as backup, restore, or removal
             based on the selected mode. This function interacts with the game files and
             updates the GUI to reflect the changes.
             Args:
                 selected_list (str): The selected list containing game file references, with
                     entries separated by a space.
                 selected_mode (Literal["BACKUP", "RESTORE", "REMOVE"], optional): The mode
                     of operation to perform on the game files. Defaults to "BACKUP".
             Raises:
                 PermissionError: If the function is unable to access files in the game folder
                     due to insufficient permissions.
        """
        # noinspection PyShadowingNames
        try:
            # Extract backup type from the selected list (format: "Backup TYPE")
            parts: list[str] = self._validate_selected_list_format(selected_list)

            backup_type: str = parts[1]
            # Perform file operation
            game_files_manage(selected_list, selected_mode)

            # Update UI based on operation performed
            if selected_mode == "BACKUP":
                self._enable_restore_button_for_type(backup_type)

        except PermissionError:
            QMessageBox.critical(
                self,
                "Error",
                "Unable to access files from your game folder. Please run CLASSIC in admin mode to resolve this problem.",
                QMessageBox.StandardButton.NoButton,
                QMessageBox.StandardButton.NoButton,
            )
        except ValueError as e:
            QMessageBox.warning(
                self,
                "Warning",
                str(e),
                QMessageBox.StandardButton.NoButton,
                QMessageBox.StandardButton.NoButton,
            )

    def _enable_restore_button_for_type(self, backup_type: str) -> None:
        """
        Enables the restore button for the specified backup type and updates its style.

        Args:
            backup_type (str): The type of backup (XSE, RESHADE, VULKAN, ENB, etc.)
        """
        restore_button: Any | None = getattr(self, f"RestoreButton_{backup_type}", None)
        if restore_button:
            restore_button.setEnabled(True)
            restore_button.setStyleSheet(self.ENABLED_BUTTON_STYLE)

    def help_popup_backup(self) -> None:
        """
        Displays a help popup with relevant backup assistance information to the user.

        The method retrieves the help text from the YAML settings and displays it
        in a message box titled "NEED HELP?".

        Args:
            self: Instance of the class where the method is defined.

        Returns:
            None
        """
        help_popup_text: str = yaml_settings(str, YAML.Main, "CLASSIC_Interface.help_popup_backup") or ""
        QMessageBox.information(self, "NEED HELP?", help_popup_text, QMessageBox.StandardButton.Ok)

    def open_backup_folder(self) -> None:
        """
        Opens the backup folder if it exists and is registered.

        This method checks if the local directory is registered in the
        GlobalRegistry. If registered, it attempts to open the backup folder
        named "CLASSIC Backup/Game Files" within the directory. If the
        registration or directory is missing, an error message is displayed
        to the user.

        Raises:
            QMessageBox: Displays an error dialog if the backup folder is
            not registered or missing.
        """
        local_dir: Path = cast("Path", GlobalRegistry.get_local_dir())
        if local_dir.exists():
            backup_path: Path = local_dir / "CLASSIC Backup/Game Files"
            QDesktopServices.openUrl(QUrl.fromLocalFile(backup_path))
        else:
            QMessageBox.critical(
                self,
                "Error",
                "Backup folder is missing or not registered. Please restart the program.",
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Ok,
            )

    # Add this constant to the MainWindow class alongside other style constants
    OUTPUT_TEXT_BOX_STYLE = """
        QTextEdit {
            color: white;
            font-family: "Cascadia Mono", Consolas, monospace;
            background: rgba(10, 10, 10, 0.75);
            border-radius: 10px;
            border: 1px solid white;
            font-size: 13px;
        }
    """

    def setup_output_text_box(self, layout: QLayout, min_height: int = 150) -> None:
        """
        Sets up a read-only output text box within the specified layout.

        Creates and configures a QTextEdit widget to display output text with custom
        styling. The widget is added to the provided layout and an internal buffer
        is initialized to store output data.

        Args:
            layout (QLayout): The layout where the output text box will be added.
            min_height (int, optional): Minimum height for the text box. Defaults to 150px.
        """
        self.output_text_box = QTextEdit(self)
        self._configure_output_text_box(min_height)
        layout.addWidget(self.output_text_box)
        self.output_buffer = ""

    def _configure_output_text_box(self, min_height: int) -> None:
        """
        Configures properties of the output text box.

             Args:
            min_height (int): Minimum height to set for the text box.
        """
        if self.output_text_box is not None:
            self.output_text_box.setReadOnly(True)
            self.output_text_box.setStyleSheet(self.OUTPUT_TEXT_BOX_STYLE)
            self.output_text_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.output_text_box.setMinimumHeight(min_height)

    # noinspection PyBroadException
    def update_output_text_box(self, text: str | bytes) -> None:
        """
        Updates the content of the output text box by appending new text. Handles both string and
        bytes input types, ensuring proper encoding and appending. Manages incomplete lines in
        a buffer and updates only when a complete line is formed.

        Args:
            text: Input text to be appended to the output text box. Can be a string or bytes.
        """
        if self.output_text_box is None:
            return

        # noinspection PyShadowingNames
        try:
            text_str: str = text.decode("utf-8", errors="replace") if isinstance(text, bytes) else str(text)
            self.output_buffer += text_str

            if "\n" in self.output_buffer:
                lines_to_append, self.output_buffer = self.output_buffer.rsplit("\n", 1)
                self.output_text_box.append(lines_to_append)  # Append adds a newline, so pass lines_to_append + '\n' if needed
                self.output_text_box.verticalScrollBar().setValue(self.output_text_box.verticalScrollBar().maximum())

            # If buffer gets too large without a newline, append it anyway to prevent memory issues
            # Or consider a timer to flush the buffer periodically
            if len(self.output_buffer) > 4096:  # Example threshold
                self.output_text_box.append(self.output_buffer)
                self.output_buffer = ""
                self.output_text_box.verticalScrollBar().setValue(self.output_text_box.verticalScrollBar().maximum())

        except Exception as e:  # noqa: BLE001
            # Fallback to simple append if complex logic fails, to avoid losing output
            try:
                self.output_text_box.append(str(text))
            except Exception:  # If even simple append fails, log to console  # noqa: BLE001
                print(f"Error updating output text box: {e}, Original text: {text}", file=sys.__stderr__)

    def process_lines(self, lines: list[str]) -> None:
        """
        Processes a list of lines, appending each stripped line to an output text box if it exists, and
        scrolls the text box to the bottom.

        The method iterates through the given list of lines, removes trailing whitespace from each line,
        and appends it to the output text box. If the line ends with a newline character or the stripped
        line is non-empty, it will be appended to the output text box, provided the text box exists. Once
        all lines have been processed, the output text box is scrolled to its bottom.

        Args:
            lines: A list of strings that represents the input lines to process.
        """
        if self.output_text_box is None:
            return

        for line in lines:
            stripped_line: str = line.rstrip()
            if stripped_line or line.endswith("\n"):
                self.output_text_box.append(stripped_line)  # pyrefly: ignore

        self.output_text_box.verticalScrollBar().setValue(self.output_text_box.verticalScrollBar().maximum())

    def setup_output_redirection(self) -> None:
        """
        Sets up redirection of standard output and standard error streams.

        This method initializes an instance of `OutputRedirector`, connects its
        `outputWritten` signal to the `update_output_text_box` method, and redirects the
        `sys.stdout` and `sys.stderr` streams to the `output_redirector`.
        """
        self.output_redirector = OutputRedirector()
        self.output_redirector.outputWritten.connect(self.update_output_text_box)
        sys.stdout = self.output_redirector  # type: ignore
        sys.stderr = self.output_redirector  # type: ignore

    @staticmethod
    def create_separator() -> QFrame:
        """
        Creates a horizontal line separator widget.

        Returns:
            QFrame: A QFrame object configured as a horizontal line separator with a sunken shadow.
        """
        separator: QFrame = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        return separator

    def setup_checkboxes(self, layout: QBoxLayout) -> None:
        """
        Initializes and configures the checkbox and drop-down sections within the given layout for
        user interface settings. This involves creating a group of checkboxes for various settings
        and a combo box for selecting the update source. Checkbox settings are arranged in a grid
        layout, and the combo box is included below the checkboxes with proper spacing and alignment.

        Args:
            layout (QBoxLayout): The parent layout to which the checkbox section, update source
                section, and separator will be added.
        """
        checkbox_section_layout: QVBoxLayout = QVBoxLayout()  # Main layout for this section

        title_label: QLabel = QLabel("CLASSIC SETTINGS")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        checkbox_section_layout.addWidget(title_label)

        grid_layout: QGridLayout = QGridLayout()
        grid_layout.setHorizontalSpacing(20)
        grid_layout.setVerticalSpacing(10)

        checkboxes: list[tuple[str, str, str]] = [
            ("FCX MODE", "FCX Mode", "Enable extended file integrity checks."),
            ("SIMPLIFY LOGS", "Simplify Logs", "Remove redundant lines from crash logs."),
            ("UPDATE CHECK", "Update Check", "Automatically check for CLASSIC updates."),
            ("VR MODE", "VR Mode", "Prioritize settings for VR version of the game."),
            ("SHOW FID VALUES", "Show FormID Values", "Look up FormID names (slower scans)."),
            ("MOVE INVALID LOGS", "Move Unsolved Logs", "Move incomplete/unscannable logs to a separate folder."),
            ("AUDIO NOTIFICATIONS", "Audio Notifications", "Play sounds for scan completion/errors."),
        ]

        for index, (label, setting, tooltip) in enumerate(checkboxes):
            checkbox: QCheckBox = self.create_checkbox(label, setting)
            checkbox.setToolTip(tooltip)
            row: int = index // 2  # Arrange in 2 columns
            col: int = index % 2
            grid_layout.addWidget(checkbox, row, col, Qt.AlignmentFlag.AlignLeft)

        checkbox_section_layout.addLayout(grid_layout)
        checkbox_section_layout.addSpacing(15)  # Space before update source

        # Update Source ComboBox
        update_source_hbox: QHBoxLayout = QHBoxLayout()
        update_source_label: QLabel = QLabel("Update Source:")
        update_source_combo: QComboBox = QComboBox()
        update_sources: tuple[str, str, str] = ("Nexus", "GitHub", "Both")
        update_source_combo.addItems(update_sources)
        update_source_combo.setToolTip("Select where CLASSIC checks for updates (Nexus for stable, GitHub for latest).")

        current_update_source: str = classic_settings(str, "Update Source") or "Both"  # Default to Both if not set
        if current_update_source in update_sources:
            update_source_combo.setCurrentText(current_update_source)
        else:  # If invalid value in settings, default to "Both" and save it
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.Update Source", "Both")
            update_source_combo.setCurrentText("Both")

        update_source_combo.currentTextChanged.connect(
            lambda value: yaml_settings(str, YAML.Settings, "CLASSIC_Settings.Update Source", value)
        )

        update_source_hbox.addWidget(update_source_label)
        update_source_hbox.addWidget(update_source_combo)
        update_source_hbox.addStretch(1)  # Push to left
        checkbox_section_layout.addLayout(update_source_hbox)

        layout.addLayout(checkbox_section_layout)  # Add this section's layout to the main tab layout
        # Separator is added after this section in setup_main_tab

    # Add this constant to the MainWindow class alongside other style constants
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

    def create_checkbox(self, label_text: str, setting: str) -> QCheckBox:
        """
        Creates a styled QCheckBox widget linked to a specific setting and its state.

        Args:
            label_text (str): The text label to display next to the checkbox.
            setting (str): The name of the setting to bind with the checkbox.

        Returns:
            QCheckBox: A QCheckBox widget connected to the specified setting's state.
        """
        checkbox: QCheckBox = QCheckBox(label_text)

        # Initialize checkbox state from settings or create default
        value: bool | None = classic_settings(bool, setting)
        if value is None:
            value = False
            yaml_settings(bool, YAML.Settings, f"CLASSIC_Settings.{setting}", False)

        checkbox.setChecked(value)

        # Connect setting update to checkbox state
        checkbox.stateChanged.connect(lambda state: yaml_settings(bool, YAML.Settings, f"CLASSIC_Settings.{setting}", bool(state)))

        # Special handling for Audio Notifications
        if setting == "Audio Notifications":
            checkbox.stateChanged.connect(lambda state: self.audio_player.toggle_audio(state))

        # Apply custom style sheet
        checkbox.setStyleSheet(self.CHECKBOX_STYLE)

        return checkbox

    @staticmethod
    def setup_folder_section(
        layout: QBoxLayout, title: str, box_name: str, browse_callback: Callable[[], None], tooltip: str = ""
    ) -> QLineEdit | None:
        """
        Sets up a folder selection section within a provided layout. This method creates a section
        consisting of a label, a QLineEdit for folder path input, and a browse button. Clicking the
        browse button triggers a callback function specified by the user.

        Args:
            layout (QBoxLayout): The layout to which the folder section will be added.
            title (str): The text to display in the label.
            box_name (str): The object name of the QLineEdit, used for identification.
            browse_callback (Callable[[], None]): The function to execute when the browse button is clicked.
            tooltip (str, optional): The tooltip text to display when hovering over the browse button. Defaults to an empty string.

        Returns:
            QLineEdit: The QLineEdit widget created for folder input.
        """
        section_layout: QHBoxLayout = QHBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5)

        label: QLabel = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # label.setFixedWidth(180) # Avoid fixed width for better scaling
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        section_layout.addWidget(label)

        line_edit: QLineEdit = QLineEdit()
        line_edit.setObjectName(box_name)
        line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # Allow horizontal expansion
        section_layout.addWidget(line_edit)

        browse_button: QPushButton = QPushButton("Browse...")  # Shorter text
        browse_button.setToolTip(tooltip if tooltip else f"Browse for {title.lower()}")
        browse_button.clicked.connect(browse_callback)
        browse_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        section_layout.addWidget(browse_button)

        # Add the QHBoxLayout to the parent QVBoxLayout (or other QBoxLayout)
        if isinstance(layout, QVBoxLayout | QHBoxLayout):
            layout.addLayout(section_layout)
        else:
            # Fallback if layout type is unexpected, though typically it's one of these.
            # This might indicate a need to adjust how sections are added.
            print(f"Warning: Unexpected layout type ({type(layout)}) for folder section '{title}'")

        return line_edit

    def setup_main_buttons(self, layout: QBoxLayout) -> None:
        """
        Sets up the main buttons and bottom row buttons within the provided layout.
        This method initializes the layout for two groups of buttons: main action buttons
        and bottom row buttons. It organizes them in horizontal layouts, with spacing configured
        as specified. Main buttons include "SCAN CRASH LOGS" and "SCAN GAME FILES," which are
        added to the scan button group. Bottom row buttons feature options such as "CHANGE INI PATH,"
        "OPEN CLASSIC SETTINGS," and "CHECK UPDATES."

        Args:
            layout: QBoxLayout instance where the main buttons and bottom row buttons
                are to be arranged and added.
        """
        main_buttons_layout: QHBoxLayout = QHBoxLayout()
        main_buttons_layout.setSpacing(10)
        self.crash_logs_button = self.add_main_button(
            main_buttons_layout, "SCAN CRASH LOGS", self.crash_logs_scan, "Scan all detected crash logs for issues."
        )
        if self.crash_logs_button:
            self.scan_button_group.addButton(self.crash_logs_button)

        self.game_files_button = self.add_main_button(
            main_buttons_layout,
            "SCAN GAME FILES",
            self.game_files_scan,
            "Scan game and mod files for potential problems (FCX Mode dependent).",
        )
        if self.game_files_button:
            self.scan_button_group.addButton(self.game_files_button)

        if isinstance(layout, QVBoxLayout | QHBoxLayout):  # Ensure layout supports addLayout
            layout.addLayout(main_buttons_layout)

    @staticmethod
    def setup_articles_section(layout: QBoxLayout) -> None:
        """
        Sets up an "Articles/Links" section in the specified layout with a descriptive
        title label, and populates it with buttons directing users to various helpful
        resources. Each button links to a specific external resource or webpage.

        This method creates a layout containing a title label aligned at the center,
        followed by a grid of buttons arranged in rows and columns. Each button is
        styled uniformly and can open a corresponding URL when clicked. After arranging
        the buttons, additional vertical spacing is added to visually separate the
        articles section from other content in the layout.

        Args:
            layout (QBoxLayout): The parent layout where the articles section will be
                added.
        """
        articles_section_layout: QVBoxLayout = QVBoxLayout()  # Main layout for this section
        articles_section_layout.setSpacing(10)

        title_label: QLabel = QLabel("USEFUL RESOURCES & LINKS")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        articles_section_layout.addWidget(title_label)

        grid_layout: QGridLayout = QGridLayout()
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(10)

        button_data: list[dict[str, str]] = [
            {"text": "BUFFOUT 4 INSTALLATION", "url": "https://www.nexusmods.com/fallout4/articles/3115"},
            {"text": "FALLOUT 4 SETUP TIPS", "url": "https://www.nexusmods.com/fallout4/articles/4141"},
            {"text": "IMPORTANT PATCHES LIST", "url": "https://www.nexusmods.com/fallout4/articles/3769"},
            {"text": "BUFFOUT 4 NEXUS", "url": "https://www.nexusmods.com/fallout4/mods/47359"},
            {"text": "CLASSIC NEXUS", "url": "https://www.nexusmods.com/fallout4/mods/56255"},
            {"text": "CLASSIC GITHUB", "url": "https://github.com/evildarkarchon/CLASSIC-Fallout4"},  # Updated URL
            {"text": "DDS TEXTURE SCANNER", "url": "https://www.nexusmods.com/fallout4/mods/71588"},
            {"text": "BETHINI PIE", "url": "https://www.nexusmods.com/site/mods/631"},
            {"text": "WRYE BASH", "url": "https://www.nexusmods.com/fallout4/mods/20032"},
        ]

        button_style = """
            QPushButton {
                color: white;
                background-color: rgba(60, 60, 60, 0.9);
                border: 1px solid #5c5c5c;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px; /* Adjusted for potentially longer text */
                font-weight: bold;
                min-height: 40px; /* Ensure buttons are not too small */
            }
            QPushButton:hover { background-color: rgba(80, 80, 80, 0.9); }
            QPushButton:disabled { color: gray; background-color: rgba(45, 45, 45, 0.75); }
        """

        for i, data in enumerate(button_data):
            button: QPushButton = QPushButton(data["text"])
            button.setStyleSheet(button_style)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # Allow horizontal expansion
            button.setToolTip(f"Open {data['url']} in your browser.")
            button.clicked.connect(lambda url=data["url"]: QDesktopServices.openUrl(QUrl(url)))
            row, col = divmod(i, 3)  # Arrange in 3 columns
            grid_layout.addWidget(button, row, col)

        articles_section_layout.addLayout(grid_layout)
        if isinstance(layout, QVBoxLayout | QHBoxLayout):
            layout.addLayout(articles_section_layout)

    def setup_bottom_buttons(self, layout: QBoxLayout) -> None:
        """
        Configures and adds a set of bottom buttons to a given layout. The buttons include
        "ABOUT", "HELP", "START PAPYRUS MONITORING", and "EXIT", each of which performs
        specific actions when clicked. Each button is styled, and some include tooltips
        and specific behavioral properties such as being checkable.
        Args:
            layout (QBoxLayout): The main layout to which the bottom button layout will
                be added.
        """
        # First row of utility buttons
        bottom_buttons_hbox: QHBoxLayout = QHBoxLayout()
        bottom_buttons_hbox.setSpacing(10)

        # Create first row of buttons
        buttons_config: list[tuple[str, str, Callable]] = [
            ("ABOUT", "Show application information.", self.show_about),
            ("HELP", "Show help information for main options.", self.help_popup_main),
            ("CHANGE INI PATH", "Manually set the path to your game's INI files folder.", self.select_folder_ini),
            ("OPEN SETTINGS", "Open CLASSIC Settings.yaml file.", self.open_settings),
            ("CHECK UPDATES", "Manually check for CLASSIC updates.", self.update_popup_explicit),
        ]

        utility_buttons: list[QPushButton] = []
        for text, tooltip, callback in buttons_config:
            button: QPushButton = self._create_button(text, tooltip, callback)
            bottom_buttons_hbox.addWidget(button)
            utility_buttons.append(button)

        # Second row with main action buttons
        main_actions_hbox: QHBoxLayout = QHBoxLayout()
        main_actions_hbox.setSpacing(10)

        # Papyrus monitoring button (special handling for checkable button)
        self.papyrus_button = self._create_button(
            "START PAPYRUS MONITORING", "Toggle Papyrus log monitoring. Displays stats in the output window.", self.toggle_papyrus_worker
        )
        self.papyrus_button.setCheckable(True)
        self.update_papyrus_button_style(False)  # Initial style for "START"
        main_actions_hbox.addWidget(self.papyrus_button, 1)  # Allow to expand

        # Exit button
        exit_button: QPushButton = self._create_button("EXIT", "Close CLASSIC.", QApplication.quit)
        main_actions_hbox.addWidget(exit_button)

        # Add both layouts to the main layout
        if isinstance(layout, QVBoxLayout | QHBoxLayout):
            layout.addLayout(bottom_buttons_hbox)
            layout.addLayout(main_actions_hbox)

    def _create_button(self, text: str, tooltip: str, callback: Callable) -> QPushButton:
        """
        Creates and configures a button with common styling and properties.

        Args:
            text: The button text
            tooltip: The button tooltip
            callback: Function to call when button is clicked

        Returns:
            Configured QPushButton instance
        """
        button: QPushButton = QPushButton(text)
        button.setToolTip(tooltip)

        # Connect appropriate signal based on whether it's a toggle button or regular
        if isinstance(button, QPushButton) and button.isCheckable():
            button.toggled.connect(callback)
        else:
            button.clicked.connect(callback)

        # Apply common styling
        button.setStyleSheet(self.BOTTOM_BUTTON_STYLE)
        button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        return button

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

    def show_about(self) -> None:
        """
        Displays the "About" dialog for the application by initializing and executing
        a custom dialog window.

        This method creates an instance of the `CustomAboutDialog` class, passing the
        current instance (self) as an argument. It then displays the dialog window
        modally by invoking the `exec()` method on the dialog instance.

        Returns:
            None
        """
        dialog: CustomAboutDialog = CustomAboutDialog(self)
        dialog.exec()

    def help_popup_main(self) -> None:
        """
        Displays a help popup with information retrieved from the YAML settings.

        The method retrieves the help text from the YAML configuration file under
        the specified key. It then displays the retrieved text in a message box
        with a title and an "OK" button.

        Returns:
            None
        """
        help_popup_text: str = yaml_settings(str, YAML.Main, "CLASSIC_Interface.help_popup_main") or ""
        QMessageBox.information(self, "NEED HELP?", help_popup_text, QMessageBox.StandardButton.Ok)

    @staticmethod
    def add_main_button(layout: QLayout, text: str, callback: Callable[[], None], tooltip: str = "") -> QPushButton:
        """
        Adds a main button to the specified layout with the given text, click callback, and optional tooltip.

        This method creates a QPushButton with a specific style and behavior. The button's text, callback, and optional
        tooltip can be customized. It is then added to the provided layout and returned.

        Args:
            layout (QLayout): The layout to which the button will be added.
            text (str): The text to display on the button.
            callback (Callable[[], None]): The function to be called when the button is clicked.
            tooltip (str, optional): The tooltip text to display on hover. Defaults to an empty string.

        Returns:
            QPushButton: The created button that has been added to the layout.
        """
        button: QPushButton = QPushButton(text)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setStyleSheet(
            """
            QPushButton {
                color: black;
                background: rgba(250, 250, 250, 0.90);
                border-radius: 10px;
                border: 1px solid white;
                font-size: 17px;
                font-weight: bold;  /* Add this line to make the text bold */
                min-height: 48px;
                max-height: 48px;
            }
            QPushButton:disabled {
                color: gray;
                background-color: rgba(10, 10, 10, 0.75);
            }
        """
        )
        if tooltip:
            button.setToolTip(tooltip)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    @staticmethod
    def add_bottom_button(layout: QLayout, text: str, callback: Callable[[], None], tooltip: str = "") -> None:
        """
        Adds a configurable button to the bottom of a given layout. The button adopts a specific
        styling, size policy, and allows optional tooltip text. A callback function is associated
        with the button's "clicked" event to define its behavior when clicked.

        Args:
            layout (QLayout): The layout where the button should be added.
            text (str): The text to display on the button.
            callback (Callable[[], None]): The function to invoke when the button is clicked.
            tooltip (str, optional): The tooltip text to display when hovering over the button.
                Defaults to an empty string.
        """
        button: QPushButton = QPushButton(text)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setStyleSheet(
            """
            color: white;
            background: rgba(10, 10, 10, 0.75);
            border-radius: 10px;
            border: 1px solid white;
            font-size: 11px;
            min-height: 32px;
            max-height: 32px;
        """
        )
        if tooltip:
            button.setToolTip(tooltip)
        button.clicked.connect(callback)
        layout.addWidget(button)

    def update_papyrus_button_style(self, monitoring: bool) -> None:
        """Updates the style and text of the Papyrus button based on monitoring state."""
        if self.papyrus_button is None:
            return
        if monitoring:
            self.papyrus_button.setText("STOP PAPYRUS MONITORING")
            self.papyrus_button.setStyleSheet(
                """
                QPushButton {
                    color: white; /* Changed to white for better contrast on red */
                    background: rgb(180, 45, 45);  /* Darker Red background */
                    border-radius: 5px;
                    border: 1px solid #FF6347; /* Lighter red border */
                    font-weight: bold;
                    font-size: 12px; /* Consistent font size */
                    padding: 6px 10px;
                    min-height: 30px;
                }
                QPushButton:hover { background-color: rgb(200, 50, 50); }
                QPushButton:pressed { background-color: rgb(160, 40, 40); }
                """
            )
        else:
            self.papyrus_button.setText("START PAPYRUS MONITORING")
            self.papyrus_button.setStyleSheet(
                """
                QPushButton {
                    color: white; /* Changed to white for better contrast on green */
                    background: rgb(45, 150, 100);  /* Darker Green background */
                    border-radius: 5px;
                    border: 1px solid #32CD32; /* Lighter green border */
                    font-weight: bold;
                    font-size: 12px;
                    padding: 6px 10px;
                    min-height: 30px;
                }
                QPushButton:hover { background-color: rgb(50, 170, 110); }
                QPushButton:pressed { background-color: rgb(40, 130, 90); }
                """
            )

    def select_folder_scan(self) -> None:
        """
        Prompts the user to select a folder for scanning and updates the scan folder
        path in both the GUI and application settings.

        Tracks and updates the path of a folder chosen by the user for custom
        scans. If the user selects a valid folder, the GUI field associated with
        scan folder input is updated, and the folder path is stored in the
        application's settings configuration.

        Returns:
            None
        """
        folder: str = QFileDialog.getExistingDirectory(self, "Select Custom Scan Folder")
        if folder:
            if self.scan_folder_edit is not None:
                self.scan_folder_edit.setText(folder)
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", folder)

    def select_folder_mods(self) -> None:
        """
        Handles the folder selection process for staging mods and updates the respective
        UI component and settings configuration.

        The function opens a directory selection dialog to allow the user to select a folder
        for staging mods. If a valid folder is selected, it updates a text field in the UI with
        the selected folder path and writes the chosen path to a YAML configuration file.

        Returns:
            None
        """
        folder: str = QFileDialog.getExistingDirectory(self, "Select Staging Mods Folder")
        if folder:
            if self.mods_folder_edit is not None:
                self.mods_folder_edit.setText(folder)
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", folder)

    def initialize_folder_paths(self) -> None:
        """
        Initializes the folder paths by retrieving settings for specific folders and updating the
        corresponding user interface fields if available.

        This method retrieves the folder paths for "SCAN Custom Path" and "MODS Folder Path"
        from the application settings and, if applicable, populates the respective input fields
        with the retrieved values.

        Returns:
            None
        """
        scan_folder: str | None = classic_settings(str, "SCAN Custom Path")
        mods_folder: str | None = classic_settings(str, "MODS Folder Path")

        if scan_folder and self.scan_folder_edit is not None:
            self.scan_folder_edit.setText(scan_folder)
        if mods_folder and self.mods_folder_edit is not None:
            self.mods_folder_edit.setText(mods_folder)

    def select_folder_ini(self) -> None:
        """
        Prompts the user to select a folder path via a directory selection dialog and updates
        the INI settings path accordingly. Displays a confirmation message after the path
        is successfully set.
        """
        folder: str = QFileDialog.getExistingDirectory(self)
        if folder:
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.INI Folder Path", folder)
            QMessageBox.information(self, "New INI Path Set", f"You have set the new path to: \n{folder}", QMessageBox.StandardButton.Ok)

    def open_settings(self) -> None:
        """
        Opens the settings file for the application.

        If the local directory is registered in the global registry, attempts to open the
        "CLASSIC Settings.yaml" file from that directory. If the file is missing, a critical
        error message is displayed, instructing the user to restart the application to resolve
        the issue.

        Raises:
            Displays a QMessageBox with a critical error if the settings file is missing.

        Returns:
            None
        """
        settings_file: Path = cast("Path", GlobalRegistry.get_local_dir()) / "CLASSIC Settings.yaml"
        if settings_file.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(settings_file))
        else:
            QMessageBox.critical(
                self,
                "Settings File Missing",
                "The settings file is missing. Please restart the application to resolve this issue.",
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Ok,
            )

    def crash_logs_scan(self) -> None:
        """
        Initializes and starts the crash logs scanning process by setting up a worker thread.

        This function is responsible for scanning crash logs asynchronously through a worker
        handled in a separate thread. The worker emits signals when certain events occur,
        like notifying or error alerts, which are connected to appropriate handlers. Upon
        completion, the worker and thread are cleaned up, and a callback is invoked to indicate
        the end of the scanning process. Additionally, the UI elements related to scanning
        are disabled during the operation to prevent multiple concurrent scans.

        Returns:
            None
        """
        if self.crash_logs_thread is None:
            self.crash_logs_thread = QThread()
            self.crash_logs_worker = CrashLogsScanWorker()
            self.crash_logs_worker.moveToThread(self.crash_logs_thread)

            self.crash_logs_worker.notify_sound_signal.connect(self.audio_player.play_notify_signal.emit)  # type: ignore
            self.crash_logs_worker.error_sound_signal.connect(self.audio_player.play_error_signal.emit)  # type: ignore

            self.crash_logs_thread.started.connect(self.crash_logs_worker.run)
            self.crash_logs_worker.finished.connect(self.crash_logs_thread.quit)  # type: ignore
            self.crash_logs_worker.finished.connect(self.crash_logs_worker.deleteLater)  # type: ignore
            self.crash_logs_thread.finished.connect(self.crash_logs_thread.deleteLater)
            self.crash_logs_thread.finished.connect(self.crash_logs_scan_finished)

            # Disable buttons and update text
            self.disable_scan_buttons()

            self.crash_logs_thread.start()

    def game_files_scan(self) -> None:
        """
        Scans game files using a separate thread and handles thread setup, worker connections, and signal
        communication to ensure non-blocking UI updates during the operation.

        Starts a scanning process by initializing a worker and a thread if they are not already created.
        The worker emits signals for notifying or handling errors in the scanning process. The scanning
        process disables UI scan buttons until the operation is complete.
        """
        if self.game_files_thread is None:
            self.game_files_thread = QThread()
            self.game_files_worker = GameFilesScanWorker()
            self.game_files_worker.moveToThread(self.game_files_thread)

            self.game_files_worker.error_sound_signal.connect(self.audio_player.play_error_signal.emit)  # type: ignore

            self.game_files_thread.started.connect(self.game_files_worker.run)
            self.game_files_worker.finished.connect(self.game_files_thread.quit)  # type: ignore
            self.game_files_worker.finished.connect(self.game_files_worker.deleteLater)  # type: ignore
            self.game_files_thread.finished.connect(self.game_files_thread.deleteLater)
            self.game_files_thread.finished.connect(self.game_files_scan_finished)

            # Disable buttons and update text
            self.disable_scan_buttons()

            self.game_files_thread.start()

    def disable_scan_buttons(self) -> None:
        """
        Disables all buttons in the scan button group.

        This method iterates through the buttons in the scan button group and
        disables them, ensuring they cannot be clicked or interacted with.

        Returns:
            None
        """
        for button_id in self.scan_button_group.buttons():
            button_id.setEnabled(False)

    def enable_scan_buttons(self) -> None:
        """
        Enables all scan buttons within a button group.

        This method iterates through all the scan buttons in a specified button group
        and enables them, allowing user interaction. It can be used to reset the
        disabled state of any buttons in the group.

        Returns:
            None
        """
        for button_id in self.scan_button_group.buttons():
            button_id.setEnabled(True)

    def crash_logs_scan_finished(self) -> None:
        """
        Marks the completion of the crash logs scanning process and resets the relevant UI components.

        This method is executed when the scan for crash logs is finished. It ensures the reset of
        internal state and re-enables UI buttons that were disabled during the scan process.

        Returns:
            None: This method does not return any value.
        """
        self.crash_logs_thread = None
        self.enable_scan_buttons()

    # noinspection PyUnresolvedReferences
    def game_files_scan_finished(self) -> None:
        """
        Marks the completion of the game files scanning process.

        This method is invoked when the game files scanning operation is finished. It appropriately
        resets the state by clearing the scanning thread reference and re-enables the buttons
        associated with scanning operations.

        Attributes:
            game_files_thread: Represents the thread used for scanning game files. Set to None
                after the scan is completed.

        Returns:
            None
        """
        self.game_files_thread = None
        self.enable_scan_buttons()

    def toggle_papyrus_worker(self) -> None:
        """
        Toggles the state of the Papyrus worker based on the state of the `papyrus_button`.

        If the `papyrus_button` is checked, the Papyrus monitoring process is started.
        Otherwise, it stops the Papyrus monitoring process. This function is intended
        to manage the lifecycle of the Papyrus worker efficiently.
        """
        if self.papyrus_button and self.papyrus_button.isChecked():
            self.start_papyrus_monitoring()
        else:
            self.stop_papyrus_monitoring()

    def start_papyrus_monitoring(self) -> None:
        """
        Initializes and starts the Papyrus monitoring process using a separate thread and worker. This allows
        asynchronous monitoring of the Papyrus system, ensuring that updates, errors, and other signals are
        handled efficiently without blocking the main application. The method configures the worker, connects
        necessary signals, updates the user interface to reflect the monitoring status, and starts the
        monitoring thread.

        Raises:
            Any exception or error handling will be caught and managed by connected signals
            such as `error`.

        """
        if self.papyrus_monitor_thread is None:
            # Create new thread and worker
            self.papyrus_monitor_thread = QThread()
            self.papyrus_monitor_worker = PapyrusMonitorWorker()
            self.papyrus_monitor_worker.moveToThread(self.papyrus_monitor_thread)

            # Connect signals
            self.papyrus_monitor_thread.started.connect(self.papyrus_monitor_worker.run)
            self.papyrus_monitor_worker.statsUpdated.connect(self.update_papyrus_stats)
            self.papyrus_monitor_worker.error.connect(self.handle_papyrus_error)

            # Start monitoring
            if self.papyrus_button:
                self.papyrus_button.setText("STOP PAPYRUS MONITORING")
                self.papyrus_button.setStyleSheet(
                    """
                    QPushButton {
                        color: black;
                        background: rgb(237, 45, 45);  /* Red background */
                        border-radius: 10px;
                        border: 1px solid black;
                        font-weight: bold;
                        font-size: 14px;
                    }
                    """
                )
            self.papyrus_monitor_thread.start()

    def stop_papyrus_monitoring(self) -> None:
        """
        Stops the papyrus monitoring process and performs necessary cleanup.

        This function terminates the papyrus monitoring by halting the monitor worker and
        its associated thread. It also updates the user interface components, such as the
        button and text box, to reflect the stopped state.

        Returns:
            None
        """
        if self.papyrus_monitor_worker:
            self.papyrus_monitor_worker.stop()

        if self.papyrus_monitor_thread:
            self.papyrus_monitor_thread.quit()
            self.papyrus_monitor_thread.wait()

            # Reset thread and worker
            self.papyrus_monitor_thread = None
            self.papyrus_monitor_worker = None

            # Update UI
            if self.papyrus_button:
                self.papyrus_button.setText("START PAPYRUS MONITORING")
                self.papyrus_button.setStyleSheet(
                    """
                    QPushButton {
                        color: black;
                        background: rgb(45, 237, 138);  /* Green background */
                        border-radius: 10px;
                        border: 1px solid black;
                        font-weight: bold;
                        font-size: 14px;
                    }
                    """
                )
                self.papyrus_button.setChecked(False)
            if self.output_text_box:
                self.output_text_box.append("\n=== Papyrus monitoring stopped ===\n")

    def update_papyrus_stats(self, stats: PapyrusStats) -> None:
        """Update the UI with new Papyrus statistics.

        Updates the output text box in the UI with the statistics provided in
        the `stats` object. Displays information such as timestamp, number
        of dumps, stacks, warnings, errors, and dumps/stacks ratio. Ensures
        the text box automatically scrolls to the most recent entry. Stores
        the last statistics for further reference.

        Args:
            stats: Instance of PapyrusStats containing the statistics data to
                be displayed. Includes attributes such as timestamp, dumps,
                stacks, ratio, warnings, and errors.
        """
        """Update the UI with new Papyrus statistics"""
        message = (
            f"\n=== Papyrus Log Stats [{stats.timestamp.strftime('%H:%M:%S')}] ===\n"
            f"Number of Dumps: {stats.dumps}\n"
            f"Number of Stacks: {stats.stacks}\n"
            f"Dumps/Stacks Ratio: {stats.ratio:.3f}\n"
            f"Number of Warnings: {stats.warnings}\n"
            f"Number of Errors: {stats.errors}\n"
        )
        if self.output_text_box:
            self.output_text_box.append(message)

            # Scroll to the bottom after adding the new message
            self.output_text_box.verticalScrollBar().setValue(self.output_text_box.verticalScrollBar().maximum())

        self._last_stats = stats

    def handle_papyrus_error(self, error_msg: str) -> None:
        """
        Handle errors from the Papyrus monitor.

        This method appends an error message to the output text box, unchecks the
        Papyrus button, plays an error sound if it hasn't been played already, and
        stops the Papyrus monitoring process.

        Args:
            error_msg (str): The error message to be handled.
        """
        if self.output_text_box:
            self.output_text_box.append(f"\n❌ ERROR IN PAPYRUS MONITORING: {error_msg}\n")
        if self.papyrus_button:
            self.papyrus_button.setChecked(False)
        if self.papyrus_monitor_worker and not self.papyrus_monitor_worker.error_sound_played:
            self.audio_player.play_error_signal.emit()
            self.papyrus_monitor_worker.error_sound_played = True
        self.stop_papyrus_monitoring()


if __name__ == "__main__":
    app: QApplication = QApplication(sys.argv)
    initialize(is_gui=True)
    manual_docs_gui: Any = GlobalRegistry.get_manual_docs_gui()
    game_path_gui: Any = GlobalRegistry.get_game_path_gui()
    window: MainWindow | None = None  # Initialize window to ensure it's defined
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except KeyboardInterrupt:
        app.exit(1)
    except Exception as exc:  # pyrefly: ignore  # noqa: BLE001
        print(f"Unhandled exception during application startup: {exc}", file=sys.stderr)
        if QApplication.instance():
            # noinspection PyTypeChecker
            QMessageBox.critical(None, "Application Startup Error", f"An critical error occurred: {exc}")  # pyrefly: ignore
        sys.exit(1)
