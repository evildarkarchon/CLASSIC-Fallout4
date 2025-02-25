import asyncio
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Literal

import regex as re
from PySide6.QtCore import QEvent, QObject, Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFontMetrics, QIcon, QPixmap
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


@dataclass
class PapyrusStats:
    """
    A class to represent Papyrus script statistics.
    Attributes:
        timestamp (datetime): The timestamp of the statistics.
        dumps (int): The number of dumps.
        stacks (int): The number of stacks.
        warnings (int): The number of warnings.
        errors (int): The number of errors.
        ratio (float): The ratio of some relevant metric.
    Methods:
        __eq__(other: object) -> bool:
            Compares this PapyrusStats instance with another for equality.
    """

    timestamp: datetime
    dumps: int
    stacks: int
    warnings: int
    errors: int
    ratio: float

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PapyrusStats):
            return NotImplemented
        return self.dumps == other.dumps and self.stacks == other.stacks and self.warnings == other.warnings and self.errors == other.errors


class PapyrusMonitorWorker(QObject):
    """PapyrusMonitorWorker is a QObject-based class designed to monitor and process Papyrus stats in a loop, emitting signals for updates and errors.
    Attributes:
        statsUpdated (Signal): Signal emitted when new stats are available.
        error (Signal): Signal emitted when an error occurs.
    Methods:
        __init__() -> None:
            Initializes the PapyrusMonitorWorker instance, setting up initial state variables and configurations.
        stop() -> None:
            Stops the monitoring loop by setting the `_should_run` flag to False.
        run() -> None:
            Executes the core monitoring logic in a loop, processing stats and emitting signals for updates and errors.
        _parse_stats(message: str, dump_count: int) -> PapyrusStats:
            Parses the provided message to extract statistical information and calculates the ratio of dumps to stacks."""

    # Signal when new stats are available
    statsUpdated = Signal(PapyrusStats)

    # Signal for errors
    error = Signal(str)

    def __init__(self) -> None:
        """
        Represents a class with initialization, state management, and session-related
        attribute handling capabilities.

        This class sets up initial state variables and manages internal configurations.
        It also tracks the state of error sound playback during a session.

        """
        super().__init__()
        self._should_run = True
        self._last_stats: PapyrusStats | None = None
        self.error_sound_played = False  # Track if error sound has played this session

    def stop(self) -> None:
        """Stop the monitoring loop"""
        self._should_run = False

    @Slot()
    def run(self) -> None:
        """
        Continuously runs a loop that checks for updates in game stats and emits
        signals when changes are detected.
        The method performs the following steps:
        1. Continuously runs while `self._should_run` is True.
        2. Calls `CGame.papyrus_logging()` to retrieve a message and count.
        3. Parses the message to extract current stats using `self._parse_stats`.
        4. Emits `statsUpdated` signal if the current stats differ from the last stats.
        5. Updates `self._last_stats` with the current stats.
        6. Sleeps for 1 second to prevent excessive CPU usage.
        7. Emits an error signal and breaks the loop if an `OSError` or `ValueError` occurs.
        Raises:
            OSError: If an OS-related error occurs during execution.
            ValueError: If a value-related error occurs during execution.
        """

        while self._should_run:
            try:
                message, count = CGame.papyrus_logging()

                # Parse the message to extract stats
                current_stats = self._parse_stats(message, count)

                # Only emit if stats have changed
                if self._last_stats != current_stats:
                    self.statsUpdated.emit(current_stats)
                    self._last_stats = current_stats

                # Sleep for a short interval to prevent excessive CPU usage
                QThread.msleep(1000)  # Check every second

            except (OSError, ValueError) as e:
                self.error.emit(str(e))
                break

    # noinspection GrazieInspection
    @staticmethod
    def _parse_stats(message: str, dump_count: int) -> PapyrusStats:
        """
        Parses the given message to extract Papyrus statistics and returns a PapyrusStats object.
        Args:
            message (str): The message containing the statistics to parse.
            dump_count (int): The number of dumps to include in the statistics.
        Returns:
            PapyrusStats: An object containing the parsed statistics, including the number of dumps, stacks, warnings, errors, and the ratio of dumps to stacks.
        """

        stats = {"dumps": dump_count, "stacks": 0, "warnings": 0, "errors": 0}

        for line in message.splitlines():
            if ": " in line:
                key, value = line.split(": ")
                key = key.strip().lower()
                if key == "number of stacks":
                    stats["stacks"] = int(value)
                elif key == "number of warnings":
                    stats["warnings"] = int(value)
                elif key == "number of errors":
                    stats["errors"] = int(value)

        ratio = 0.0 if stats["dumps"] == 0 else stats["dumps"] / stats["stacks"]

        return PapyrusStats(
            timestamp=datetime.now(),
            dumps=stats["dumps"],
            stacks=stats["stacks"],
            warnings=stats["warnings"],
            errors=stats["errors"],
            ratio=ratio,
        )


# Example fix for pastebin fetch
class PastebinFetchWorker(QObject):
    """The PastebinFetchWorker class is responsible for fetching data from a given Pastebin URL
    and emitting signals based on the result of the operation.
    Attributes:
        finished (Signal): Signal emitted when the fetch operation is finished.
        error (Signal): Signal emitted when an error occurs during the fetch operation, with the error message.
        success (Signal): Signal emitted when the fetch operation is successful, with the URL.
    Methods:
        __init__(url: str) -> None:
            Initializes the PastebinFetchWorker with the given URL.
        run() -> None:
            Initiates the process of fetching data from a Pastebin URL and emits signals based on the result of the operation."""

    finished = Signal()
    error = Signal(str)
    success = Signal(str)

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url

    @Slot()
    def run(self) -> None:
        """
        Executes the main logic of the method, handling success and error cases.

        This method attempts to fetch data from a URL using the `pastebin_fetch` method
        from the `CLogs` class. If the fetch is successful, it emits a success signal
        with the URL. If an `OSError` or `ValueError` occurs, it emits an error signal
        with the error message. Regardless of the outcome, it emits a finished signal
        when the process is complete.

        Raises:
            OSError: If an OS-related error occurs during the fetch.
            ValueError: If a value-related error occurs during the fetch.
        """
        try:
            CLogs.pastebin_fetch(self.url)
            self.success.emit(self.url)
        except (OSError, ValueError) as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class CustomAboutDialog(QDialog):
    """
    A custom dialog that displays information about the application.
    This dialog includes an icon, descriptive text, and a Close button. It is designed
    to provide information about the application, including the name, contributors, and
    other relevant details.
    Attributes:
        parent (QMainWindow | QDialog | None): The parent widget of the dialog.
    Methods:
        __init__(parent: QMainWindow | QDialog | None = None) -> None:
            Initializes the dialog, sets up the layout, and populates it with an icon,
            text, and a Close button.
    """
    def __init__(self, parent: QMainWindow | QDialog | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setFixedSize(600, 200)  # Adjust size for icon and text

        # Create a layout with margins similar to QMessageBox.about
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)  # Adjust margins (left, top, right, bottom)

        # Horizontal layout for icon and text
        h_layout: QHBoxLayout = QHBoxLayout()

        # Add the icon
        icon_label: QLabel = QLabel(self)
        icon: QIcon = QIcon("CLASSIC Data/graphics/CLASSIC.ico")
        pixmap: QPixmap = icon.pixmap(128, 128)  # Request the 64x64 icon size
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)  # Align icon at the top
        h_layout.addWidget(icon_label)

        # Add the text next to the icon
        text_label: QLabel = QLabel(
            "Crash Log Auto Scanner & Setup Integrity Checker\n\n"
            "Made by: Poet\n"
            "Contributors: evildarkarchon | kittivelae | AtomicFallout757 | wxMichael"
        )
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)  # Align text to top-left
        text_label.setWordWrap(True)  # Allow text wrapping for better formatting
        h_layout.addWidget(text_label)

        layout.addLayout(h_layout)

        # Add a Close button at the bottom
        close_button: QPushButton = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        # Align the Close button to the right and add some space at the bottom
        layout.setAlignment(close_button, Qt.AlignmentFlag.AlignRight)


class ErrorDialog(QDialog):
    """
    A dialog window that displays an error message and provides an option to copy the message to the clipboard.
    Attributes:
        text_edit (QPlainTextEdit): A text edit widget to display the error message.
    Methods:
        copy_to_clipboard(): Copies the error message to the system clipboard.
    """
    def __init__(self, error_dialog_text: str) -> None:
        super().__init__()
        self.setWindowTitle("Error")
        self.setMinimumSize(600, 300)
        layout = QVBoxLayout(self)

        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(error_dialog_text)
        layout.addWidget(self.text_edit)

        copy_button = QPushButton("Copy to Clipboard", self)
        copy_button.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(copy_button)

    def copy_to_clipboard(self) -> None:
        """
        Copies the current text from the text editor to the system clipboard.

        This method retrieves the text content from the text editor widget and sets it as the current text in the system clipboard.
        """
        QApplication.clipboard().setText(self.text_edit.toPlainText())


def show_exception_box(exception_text: str) -> None:
    """
    Displays an error dialog with the provided exception text.

    Args:
        exception_text (str): The text of the exception to display in the dialog.

    Returns:
        None
    """
    dialog = ErrorDialog(exception_text)
    dialog.show()
    dialog.exec()


def custom_excepthook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType | None) -> None:
    """
    Custom exception hook to handle uncaught exceptions.

    This function formats the exception information and prints it to the console.
    Additionally, it displays the formatted exception text in a custom exception box.

    Args:
        exc_type (type[BaseException]): The type of the exception.
        exc_value (BaseException): The exception instance.
        exc_traceback (TracebackType | None): The traceback object. If None, only the exception type and value are formatted.

    Returns:
        None
    """
    if exc_traceback is None:
        custom_except_text = "".join(traceback.format_exception_only(exc_type, exc_value))
    else:
        custom_except_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(custom_except_text)  # Still print to console
    show_exception_box(custom_except_text)


sys.excepthook = custom_excepthook

import CLASSIC_Main as CMain  # noqa: E402
import CLASSIC_ScanGame as CGame  # noqa: E402
import CLASSIC_ScanLogs as CLogs  # noqa: E402


class AudioPlayer(QObject):
    """
    A class to handle audio playback for error, notification, and custom sounds.
    Attributes:
        play_error_signal (Signal): Signal to trigger error sound playback.
        play_notify_signal (Signal): Signal to trigger notification sound playback.
        play_custom_signal (Signal): Signal to trigger custom sound playback with a specified path.
        audio_enabled (bool): Flag to enable or disable audio playback.
        error_sound (QSoundEffect): QSoundEffect object for error sound.
        notify_sound (QSoundEffect): QSoundEffect object for notification sound.
    Methods:
        __init__() -> None:
            Initializes the AudioPlayer instance, sets up sounds, and connects signals to slots.
        play_error_sound() -> None:
            Plays the error sound if audio is enabled and the sound is loaded.
        play_notify_sound() -> None:
            Plays the notification sound if audio is enabled and the sound is loaded.
        play_custom_sound(sound_path: str, volume: float = 1.0) -> None:
            Plays a custom sound from the specified path at the given volume.
        toggle_audio(state: bool) -> None:
            Enables or disables audio playback based on the given state.
    """
    # Define signals for different sounds
    play_error_signal = Signal()
    play_notify_signal = Signal()
    play_custom_signal = Signal(str)  # Signal to play a custom sound with a path

    def __init__(self) -> None:
        """
        Initializes the AudioPlayer class.
        This constructor sets up audio notifications based on the CLASSIC settings.
        If the audio notifications setting is not found, it initializes it to True.
        It also sets up QSoundEffect objects for error and notification sounds,
        and connects the appropriate signals to their respective slots.
        Attributes:
            audio_enabled (bool): Indicates if audio notifications are enabled.
            error_sound (QSoundEffect): Sound effect for error notifications.
            notify_sound (QSoundEffect): Sound effect for general notifications.
        Signals:
            play_error_signal: Signal to play the error sound.
            play_notify_signal: Signal to play the notification sound.
            play_custom_signal: Signal to play a custom sound from a specified file path.
        """
        super().__init__()
        self.audio_enabled = CMain.classic_settings(bool, "Audio Notifications")
        if self.audio_enabled is None:
            CMain.yaml_settings(bool, CMain.YAML.Settings, "CLASSIC_Settings.Audio Notifications", True)
            self.audio_enabled = True

        # Setup QSoundEffect objects for the preset sounds
        self.error_sound = QSoundEffect()
        self.error_sound.setSource(QUrl.fromLocalFile("CLASSIC Data/sounds/classic_error.wav"))
        self.error_sound.setVolume(0.5)  # Set max volume

        self.notify_sound = QSoundEffect()
        self.notify_sound.setSource(QUrl.fromLocalFile("CLASSIC Data/sounds/classic_notify.wav"))
        self.notify_sound.setVolume(0.5)  # Set max volume

        # Connect signals to respective slots
        if self.audio_enabled:
            self.play_error_signal.connect(self.play_error_sound)
            self.play_notify_signal.connect(self.play_notify_sound)
            self.play_custom_signal.connect(lambda file: self.play_custom_sound(file))  # Use custom path

    def play_error_sound(self) -> None:
        """
        Plays an error sound if audio is enabled and the error sound is loaded.

        This method checks if the audio is enabled and if the error sound is loaded.
        If both conditions are met, it plays the error sound.
        """
        if self.audio_enabled and self.error_sound.isLoaded():
            self.error_sound.play()

    def play_notify_sound(self) -> None:
        """
        Plays a notification sound if audio is enabled and the notification sound is loaded.

        This method checks if the audio is enabled and if the notification sound is loaded.
        If both conditions are met, it plays the notification sound.
        """
        if self.audio_enabled and self.notify_sound.isLoaded():
            self.notify_sound.play()

    @staticmethod
    def play_custom_sound(sound_path: str, volume: float = 1.0) -> None:
        """
        Plays a custom sound from the specified file path with the given volume.

        Args:
            sound_path (str): The file path to the sound file to be played.
            volume (float, optional): The volume at which to play the sound. Defaults to 1.0.

        Returns:
            None
        """
        custom_sound = QSoundEffect()
        custom_sound.setSource(QUrl.fromLocalFile(sound_path))
        custom_sound.setVolume(volume)
        custom_sound.play()

    def toggle_audio(self, state: bool) -> None:
        """
        Toggles the audio state of the interface.

        Args:
            state (bool): If True, enables audio; if False, disables audio.

        Returns:
            None
        """
        self.audio_enabled = state
        if not state:
            self.play_notify_signal.disconnect()
            self.play_error_signal.disconnect()
            self.play_custom_signal.disconnect()
        else:
            self.play_notify_signal.connect(self.play_notify_sound)
            self.play_error_signal.connect(self.play_error_sound)
            self.play_custom_signal.connect(lambda file: self.play_custom_sound(file))


class ManualPathDialog(QDialog):
    def __init__(self, parent: QMainWindow | None = None) -> None:
        """
        Initializes the ManualPathDialog class.
        Args:
            parent (QMainWindow | None): The parent window of the dialog. Defaults to None.
        Sets up the dialog window with a fixed size and title, creates a layout with a label,
        input field, and a "Browse" button for selecting the INI files directory.
        Also includes standard OK and Cancel buttons.
        """
        super().__init__(parent)
        self.setWindowTitle("Set INI Files Directory")
        self.setFixedSize(700, 150)

        # Create layout and input field
        layout = QVBoxLayout(self)

        # Add a label
        label = QLabel(
            f"Enter the path for the {CMain.gamevars['game']} INI files directory (Example: c:\\users\\<name>\\Documents\\My Games\\{CMain.gamevars['game']})",
            self,
        )
        layout.addWidget(label)

        inputlayout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Enter the INI directory or click 'Browse'...")
        inputlayout.addWidget(self.input_field)

        # Create the "Browse" button
        browse_button = QPushButton("Browse...", self)
        browse_button.clicked.connect(self.browse_directory)
        inputlayout.addWidget(browse_button)
        layout.addLayout(inputlayout)

        # Create standard OK button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse_directory(self) -> None:
        """
        Opens a dialog for the user to select a directory. If a directory is selected,
        sets the text of the input field to the selected directory path.

        Returns:
            None
        """
        manual_path = QFileDialog.getExistingDirectory(self, "Select Directory for INI Files")
        if manual_path:
            self.input_field.setText(manual_path)

    def get_path(self) -> str:
        return self.input_field.text()


class GamePathDialog(QDialog):
    def __init__(self, parent: QMainWindow | None = None) -> None:
        """
        Initializes the GamePathDialog class.
        Args:
            parent (QMainWindow | None): The parent window of the dialog. Defaults to None.
        Sets up the dialog window with a fixed size, title, input field for directory path,
        a browse button to select the directory, and standard OK and Cancel buttons.
        """
        super().__init__(parent)
        self.setWindowTitle("Set INI Files Directory")
        self.setFixedSize(700, 150)

        # Create layout and input field
        layout = QVBoxLayout(self)

        # Add a label
        label = QLabel(
            f"Enter the path for the {CMain.gamevars['game']} directory (example: C:\\Steam\\steamapps\\common\\{CMain.gamevars['game']})",
            self,
        )
        layout.addWidget(label)

        inputlayout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Enter the Game's directory or click 'Browse'...")
        inputlayout.addWidget(self.input_field)

        # Create the "Browse" button
        browse_button = QPushButton("Browse...", self)
        browse_button.clicked.connect(self.browse_directory)
        inputlayout.addWidget(browse_button)
        layout.addLayout(inputlayout)

        # Create standard OK button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse_directory(self) -> None:
        """
        Opens a dialog for the user to select a directory and sets the selected
        directory path to the input field.

        This method uses QFileDialog to open a directory selection dialog. The
        dialog's title includes the name of the game from CMain.gamevars. If the
        user selects a directory, the path of the selected directory is set as the
        text of the input field.

        Returns:
            None
        """
        manual_path = QFileDialog.getExistingDirectory(self, f"Select Directory for {CMain.gamevars['game']}")
        if manual_path:
            self.input_field.setText(manual_path)

    def get_path(self) -> str:
        return self.input_field.text()


class OutputRedirector(QObject):
    outputWritten = Signal(str)

    def write(self, text: str) -> None:
        self.outputWritten.emit(str(text))

    def flush(self) -> None:
        pass


class CrashLogsScanWorker(QObject):
    """CrashLogsScanWorker is a QObject-based worker class responsible for scanning crash logs
    and emitting signals to trigger sound notifications based on the scan results.
    Attributes:
        finished (Signal): Signal emitted when the task is complete.
        notify_sound_signal (Signal): Signal emitted to trigger a notification sound.
        error_sound_signal (Signal): Signal emitted to trigger an error sound.
        custom_sound_signal (Signal): Signal emitted to trigger a custom sound, with the sound file path as a parameter.
    Methods:
        run() -> None:"""

    finished = Signal()
    notify_sound_signal = Signal()
    error_sound_signal = Signal()
    custom_sound_signal = Signal(str)  # In case a custom sound needs to be played

    @Slot()
    def run(self) -> None:
        """
        Executes the main logic of the method, including scanning for crash logs and emitting signals for notifications.

        This method performs the following steps:
        1. Scans for crash logs using `CLogs.crashlogs_scan()`.
        2. Emits a signal to play a notification sound.
        3. If an exception occurs:
            - Checks if audio notifications are enabled in the settings.
            - Emits a signal to play an error sound if audio notifications are enabled.
            - Otherwise, displays an error dialog with the exception message.
        4. Emits a signal indicating that the process has finished.

        Raises:
            Exception: If an error occurs during the execution of the method.
        """
        try:
            CLogs.crashlogs_scan()
            self.notify_sound_signal.emit()  # Emit signal to play notify sound
        except Exception as e:  # noqa: BLE001
            if CMain.classic_settings(bool, "Audio Notifications"):
                self.error_sound_signal.emit()  # Emit signal to play error sound in case of exception
            else:
                ErrorDialog(str(e)).exec()
        finally:
            self.finished.emit()


class GameFilesScanWorker(QObject):
    """GameFilesScanWorker is a QObject-based worker class designed to handle the scanning
    and processing of game files. It emits signals to notify the completion of tasks,
    play notification sounds, and handle errors.
    Attributes:
        finished (Signal): Signal emitted when the task is finished.
        notify_sound_signal (Signal): Signal emitted to play a notification sound.
        error_sound_signal (Signal): Signal emitted to play an error sound.
        custom_sound_signal (Signal): Signal emitted to play a custom sound with a string argument.
    Methods:
        run(): Executes the main logic of the function, handling potential exceptions."""
    finished = Signal()
    notify_sound_signal = Signal()
    error_sound_signal = Signal()
    custom_sound_signal = Signal(str)

    @Slot()
    def run(self) -> None:
        """
        Executes the main logic of the method, handling notifications and errors.

        This method attempts to write combined results using the CGame class and emits a notification sound signal.
        If an exception occurs, it checks the classic settings for audio notifications and either emits an error sound signal
        or displays an error dialog with the exception message. Finally, it emits a finished signal.

        Raises:
            Exception: If an error occurs during the execution of the method.
        """
        try:
            CGame.write_combined_results()
            self.notify_sound_signal.emit()  # Emit signal to play notify sound
        except Exception as e:  # noqa: BLE001
            if CMain.classic_settings(bool, "Audio Notifications"):
                self.error_sound_signal.emit()  # Emit signal to play error sound in case of exception
            else:
                ErrorDialog(str(e)).exec()
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        """
        Represents the main window for the Crash Log Auto Scanner & Setup Integrity Checker application. This
        class is responsible for initializing the main user interface components, managing its layout, worker
        threads, and the application's general file handling and operations.

        Raises
        ------
        TypeError
            If essential GUI components in CMain (`CMain.manual_docs_gui` or `CMain.game_path_gui`)
            are not initialized correctly.
        """
        super().__init__()
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

        CMain.initialize(is_gui=True)

        self.setWindowTitle(
            f"Crash Log Auto Scanner & Setup Integrity Checker | {CMain.yaml_settings(str, CMain.YAML.Main, 'CLASSIC_Info.version')}"
        )
        self.setWindowIcon(QIcon("CLASSIC Data/graphics/CLASSIC.ico"))
        dark_style = """
QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #5c5c5c;
    color: #ffffff;
}

/* ComboBox Styling */
QComboBox {
    background-color: #3c3c3c;
    border: 1px solid #5c5c5c;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 24px;
    color: #ffffff;
}

QComboBox:hover {
    background-color: #444444;
    border-color: #666666;
}

QComboBox:focus {
    border-color: #0078d4;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: pb_source(CLASSIC Data/graphics/arrow-down.svg);
    width: 12px;
    height: 12px;
}

QComboBox:disabled {
    background-color: #2b2b2b;
    color: #666666;
}

/* ScrollBar Styling */
QScrollBar:vertical {
    background-color: #202020;
    width: 14px;
    border: none;
    border-radius: 7px;
    margin: 0;
}

QScrollBar::groove:vertical {
    background-color: #202020;
    border: none;
    border-radius: 7px;
}

QScrollBar::handle:vertical {
    background-color: #686868;
    min-height: 30px;
    border-radius: 5px;
    margin: 2px 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #7f7f7f;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: #202020;
    border: none;
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #202020;
    height: 14px;
    border: none;
    border-radius: 7px;
    margin: 0;
}

QScrollBar::groove:horizontal {
    background-color: #202020;
    border: none;
    border-radius: 7px;
}

QScrollBar::handle:horizontal {
    background-color: #686868;
    min-width: 30px;
    border-radius: 5px;
    margin: 2px 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #7f7f7f;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: #202020;
    border: none;
    width: 0px;
}

QScrollBar::corner {
    background: #202020;
}

/* Tab Widget Styling */
QTabWidget::pane {
    border: 1px solid #444444;
}

QTabBar::tab {
    background-color: #3c3c3c;
    border: 1px solid #5c5c5c;
    color: #ffffff;
    padding: 5px;
}

QTabBar::tab:selected {
    background-color: #2b2b2b;
    color: #ffffff;
}

/* Button Styling */
QPushButton {
    background-color: #3c3c3c;
    border: 1px solid #5c5c5c;
    color: #ffffff;
    padding: 5px;
}

QPushButton:hover {
    background-color: #444444;
}

QPushButton:pressed {
    background-color: #222222;
}

/* Label Styling */
QLabel {
    color: #ffffff;
}
    """
        self.setStyleSheet(dark_style)
        # self.setMinimumSize(700, 950)  # Increase minimum width from 650 to 700
        self.setFixedSize(700, 950)  # Set fixed size to prevent resizing, for now.

        # Set up the custom exception handler for the main window
        self.installEventFilter(self)

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
        # In __init__ method, after setting up the main tab:
        self.initialize_folder_paths()
        self.setup_output_redirection()
        self.output_buffer = ""
        CMain.main_generate_required()
        # Perform initial update check
        if CMain.classic_settings(bool, "Update Check"):
            QTimer.singleShot(0, self.update_popup)

        self.update_check_timer = QTimer()
        self.update_check_timer.timeout.connect(self.perform_update_check)
        self.is_update_check_running = False

        # Initialize thread attributes
        self.crash_logs_thread: QThread | None = None
        self.game_files_thread: QThread | None = None

        if CMain.manual_docs_gui is None or CMain.game_path_gui is None:
            raise TypeError("CMain not initialized")
        CMain.manual_docs_gui.manual_docs_path_signal.connect(self.show_manual_docs_path_dialog)
        CMain.game_path_gui.game_path_signal.connect(self.show_game_path_dialog)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """
        Filters events for the watched object.

        This method is called to filter events before they reach the watched object.
        It can be used to intercept and handle events before they are processed by the
        target object.

        Args:
            watched (QObject): The object being watched for events.
            event (QEvent): The event that occurred.

        Returns:
            bool: True if the event should be filtered out and not passed to the watched object,
                  False otherwise.
        """
        return super().eventFilter(watched, event)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handles the close event for the window.

        This method is called when the window receives a close event. It stops
        the Papyrus monitoring process before calling the parent class's
        closeEvent method to ensure proper cleanup.

        Args:
            event (QCloseEvent): The close event that triggered this method.
        """
        self.stop_papyrus_monitoring()
        super().closeEvent(event)

    def setup_pastebin_elements(self, layout: QVBoxLayout) -> None:
        """
        Sets up the Pastebin elements in the provided layout.
        This method creates a horizontal layout containing a label, an input field, and a button
        for fetching logs from Pastebin. The elements are added to the provided vertical layout.
        Args:
            layout (QVBoxLayout): The main layout to which the Pastebin elements will be added.
        Returns:
            None
        """
        pastebin_layout = QHBoxLayout()

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
        self.pastebin_fetch_button.clicked.connect(self.pastebin_id_input.clear)
        self.pastebin_fetch_button.setToolTip("Fetch the log file from Pastebin. Can be used more than once.")
        pastebin_layout.addWidget(self.pastebin_fetch_button)

        # Add the layout to the main layout (add it to an appropriate tab or section)
        layout.addLayout(pastebin_layout)

    def fetch_pastebin_log(self) -> None:
        """
        Fetches a log from Pastebin based on the input provided in the pastebin_id_input field.
        This method creates a new thread and worker to fetch the log from Pastebin. It connects the necessary signals
        to handle the success and error cases, displaying appropriate message boxes to the user.
        Returns:
            None
        """
        if self.pastebin_id_input is None or self:
            return
        input_text = self.pastebin_id_input.text().strip()
        url = input_text if self.pastebin_url_regex.match(input_text) else f"https://pastebin.com/{input_text}"

        # Create thread and worker
        pastebin_thread = QThread()
        pastebin_worker = PastebinFetchWorker(url)
        pastebin_worker.moveToThread(pastebin_thread)

        # Connect signals
        pastebin_thread.started.connect(pastebin_worker.run)
        pastebin_worker.finished.connect(pastebin_thread.quit)
        pastebin_worker.success.connect(
            lambda pb_source: QMessageBox.information(self, "Success", f"Log fetched from: {pb_source}",
                                                      QMessageBox.StandardButton.Ok)
        )
        pastebin_worker.error.connect(
            lambda err: QMessageBox.warning(
                self, "Error", f"Failed to fetch log: {err}", QMessageBox.StandardButton.NoButton,
                QMessageBox.StandardButton.NoButton
            )
        )

        # Start thread
        pastebin_thread.start()

    def show_manual_docs_path_dialog(self) -> None:
        """
        Opens a dialog for the user to select the manual documentation path.

        This method creates an instance of ManualPathDialog and displays it to the user.
        If the user accepts the dialog, the selected path is retrieved and passed to
        CMain.get_manual_docs_path_gui() for further processing.
        """
        dialog = ManualPathDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            manual_path = dialog.get_path()
            CMain.get_manual_docs_path_gui(manual_path)

    def show_game_path_dialog(self) -> None:
        """
        Displays a dialog for the user to select the game path.
        If the game path GUI is not initialized, raises a TypeError.
        Opens a GamePathDialog for the user to input the game path. If the user accepts the dialog,
        retrieves the path from the dialog and sets it in the game path GUI.
        Raises:
            TypeError: If CMain.game_path_gui is None.
        """
        if CMain.game_path_gui is None:
            raise TypeError("CMain not initialized")

        dialog = GamePathDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            manual_path = dialog.get_path()
            CMain.game_path_gui.get_game_path_gui(manual_path)

    def update_popup(self) -> None:
        """
        Initiates the update check process by starting the update check timer
        immediately if it is not already running.

        This method sets the `is_update_check_running` flag to True and starts
        the `update_check_timer` with no delay.

        Returns:
            None
        """
        if not self.is_update_check_running:
            self.is_update_check_running = True
            self.update_check_timer.start(0)  # Start immediately

    def update_popup_explicit(self) -> None:
        """
        Updates the popup explicitly by disconnecting the current update check
        and connecting a forced update check. If an update check is not already
        running, it starts the update check timer immediately.

        This method performs the following steps:
        1. Disconnects the `perform_update_check` method from the `timeout` signal of `update_check_timer`.
        2. Connects the `force_update_check` method to the `timeout` signal of `update_check_timer`.
        3. If an update check is not currently running, sets `is_update_check_running` to True and starts the `update_check_timer` with no delay.

        Returns:
            None
        """
        self.update_check_timer.timeout.disconnect(self.perform_update_check)
        self.update_check_timer.timeout.connect(self.force_update_check)
        if not self.is_update_check_running:
            self.is_update_check_running = True
            self.update_check_timer.start(0)

    def perform_update_check(self) -> None:
        """
        Stops the update check timer and performs an asynchronous update check.

        This method stops the `update_check_timer` and then runs the
        `async_update_check` coroutine using `asyncio.run`.

        Returns:
            None
        """
        self.update_check_timer.stop()
        asyncio.run(self.async_update_check())

    def force_update_check(self) -> None:
        """
        Force an update check by directly performing the update check without reading from settings.

        This method sets the `is_update_check_running` flag to True, stops the update check timer,
        and performs an asynchronous update check explicitly.

        Returns:
            None
        """
        # Directly perform the update check without reading from settings
        self.is_update_check_running = True
        self.update_check_timer.stop()
        asyncio.run(self.async_update_check_explicit())  # Perform async check

    async def async_update_check(self) -> None:
        """
        Asynchronously checks for updates and handles the result.

        This method performs an asynchronous update check by calling the
        `CMain.is_latest_version` method. If the check is successful, it
        displays the result using `self.show_update_result`. If an error
        occurs during the update check, it catches the `CMain.UpdateCheckError`
        exception and displays the error using `self.show_update_error`.
        Regardless of the outcome, it ensures that the update check flag
        (`self.is_update_check_running`) is set to False and stops the
        `self.update_check_timer`.

        Returns:
            None
        """
        try:
            is_up_to_date = await CMain.is_latest_version(quiet=True)
            self.show_update_result(is_up_to_date)
        except CMain.UpdateCheckError as e:
            self.show_update_error(str(e))
        finally:
            self.is_update_check_running = False
            self.update_check_timer.stop()  # Ensure the timer is always stopped

    async def async_update_check_explicit(self) -> None:
        """
        Asynchronously checks for updates explicitly and handles the result.

        This method performs an asynchronous update check by calling the
        `is_latest_version` method of the `CMain` class. It then displays the
        result using `show_update_result` if the check is successful. If an
        `UpdateCheckError` is raised, it displays the error using
        `show_update_error`. Finally, it ensures that the update check timer
        is stopped and the `is_update_check_running` flag is set to False.

        Returns:
            None
        """
        try:
            is_up_to_date = await CMain.is_latest_version(quiet=True, gui_request=True)
            self.show_update_result(is_up_to_date)
        except CMain.UpdateCheckError as e:
            self.show_update_error(str(e))
        finally:
            self.is_update_check_running = False
            self.update_check_timer.stop()  # Ensure the timer is always stopped

    def show_update_result(self, is_up_to_date: bool) -> None:
        """
        Displays a message box to inform the user about the update status of the CLASSIC application.

        Args:
            is_up_to_date (bool): A flag indicating whether the application is up to date.

        Returns:
            None
        """
        if is_up_to_date:
            QMessageBox.information(self, "CLASSIC UPDATE", "You have the latest version of CLASSIC!",
                                    QMessageBox.StandardButton.Ok)
        else:
            update_popup_text = CMain.yaml_settings(str, CMain.YAML.Main, "CLASSIC_Interface.update_popup_text") or ""
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
        Displays a warning message box indicating that the update check has failed.

        Args:
            error_message (str): The error message to display in the warning message box.
        """
        QMessageBox.warning(
            self,
            "Update Check Failed",
            f"Failed to check for updates: {error_message}",
            QMessageBox.StandardButton.NoButton,
            QMessageBox.StandardButton.NoButton,
        )

    def setup_main_tab(self) -> None:
        """
        Sets up the main tab layout and its components.
        This method initializes and arranges various UI elements on the main tab,
        including folder selection sections, buttons, checkboxes, articles, and
        output text box. It also adds separators and spacing to organize the layout.
        The components set up in this method include:
        - Folder selection sections for staging mods and custom scan folders.
        - Main buttons section.
        - Checkboxes section.
        - Articles section.
        - Bottom buttons section.
        - Output text box.
        The layout is configured with specific margins, spacing, and stretch factors
        to ensure a consistent and user-friendly interface.
        """
        layout = QVBoxLayout(self.main_tab)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        # Top section
        self.mods_folder_edit = self.setup_folder_section(layout, "STAGING MODS FOLDER", "Box_SelectedMods",
                                                          self.select_folder_mods)
        self.mods_folder_edit.setToolTip("Select the folder where you stage your mods.")
        self.mods_folder_edit.setPlaceholderText("Optional: Select the folder where you stage your mods.")

        self.scan_folder_edit = self.setup_folder_section(layout, "CUSTOM SCAN FOLDER", "Box_SelectedScan",
                                                          self.select_folder_scan)
        self.scan_folder_edit.setToolTip("Select a custom folder to scan for log files.")
        self.scan_folder_edit.setPlaceholderText("Optional: Select a custom folder to scan for log files.")

        # self.setup_pastebin_elements(layout)

        # Add first separator
        layout.addWidget(self.create_separator())

        # Main buttons section
        self.setup_main_buttons(layout)

        # Add second separator
        layout.addWidget(self.create_separator())

        # Checkbox section
        self.setup_checkboxes(layout)

        # Articles section
        self.setup_articles_section(layout)

        # Add a separator before bottom buttons
        layout.addWidget(self.create_separator())

        # Bottom buttons
        self.setup_bottom_buttons(layout)

        # Add output text box
        self.setup_output_text_box(layout)

        # Add some spacing
        layout.addSpacing(10)

        # Set the layout to be stretchable
        layout.setStretchFactor(self.output_text_box, 1)  # type: ignore

    def setup_backups_tab(self) -> None:
        """
        Sets up the backups tab in the user interface.
        This method configures the layout and widgets for the backups tab, including
        explanation labels, category buttons for backup, restore, and remove actions,
        and a button to open the backups folder. It also checks for existing backups
        to enable or disable the restore buttons accordingly.
        The categories included are:
        - XSE
        - RESHADE
        - VULKAN
        - ENB
        The method performs the following actions:
        1. Sets up the layout with margins and spacing.
        2. Adds explanation labels for backup, restore, and remove actions.
        3. Adds category labels and buttons for each category.
        4. Connects button click events to the appropriate methods.
        5. Checks for existing backups to enable/disable restore buttons.
        6. Adds a button to open the backups folder.
        """
        layout = QVBoxLayout(self.backups_tab)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        # Add explanation labels
        layout.addWidget(QLabel("BACKUP > Backup files from the game folder into the CLASSIC Backup folder."))
        layout.addWidget(QLabel("RESTORE > Restore file backup from the CLASSIC Backup folder into the game folder."))
        layout.addWidget(QLabel("REMOVE > Remove files only from the game folder without removing existing backups."))

        # Add separators and category buttons
        categories = ["XSE", "RESHADE", "VULKAN", "ENB"]
        for category in categories:
            layout.addWidget(self.create_separator())
            category_label = QLabel(category)
            category_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(category_label)

            button_layout = QHBoxLayout()

            backup_button = QPushButton(f"BACKUP {category}")
            backup_button.clicked.connect(lambda _, c=category: self.classic_files_manage(f"Backup {c}", "BACKUP"))
            button_layout.addWidget(backup_button)

            restore_button = QPushButton(f"RESTORE {category}")
            restore_button.clicked.connect(lambda _, c=category: self.classic_files_manage(f"Backup {c}", "RESTORE"))
            restore_button.setEnabled(False)  # Initially disabled
            setattr(self, f"RestoreButton_{category}", restore_button)  # Store reference to the button
            button_layout.addWidget(restore_button)

            remove_button = QPushButton(f"REMOVE {category}")
            remove_button.clicked.connect(lambda _, c=category: self.classic_files_manage(f"Backup {c}", "REMOVE"))
            button_layout.addWidget(remove_button)

            layout.addLayout(button_layout)

        # Check if backups exist and enable restore buttons accordingly
        self.check_existing_backups()

        # Add a button to open the backups folder
        open_backups_button = QPushButton("OPEN CLASSIC BACKUPS")
        open_backups_button.clicked.connect(self.open_backup_folder)
        layout.addWidget(open_backups_button)

    def check_existing_backups(self) -> None:
        """Checks for existing backups in specified categories and enables corresponding restore buttons if backups are found.

        This method iterates over a predefined list of backup categories ("XSE", "RESHADE", "VULKAN", "ENB").
        For each category, it constructs the backup path and checks if the directory exists and contains any files.
        If backups are found, it enables the corresponding restore button and applies a specific style to it.

        Returns:
            None"""
        for category in ["XSE", "RESHADE", "VULKAN", "ENB"]:
            backup_path = Path(f"CLASSIC Backup/Game Files/Backup {category}")
            if backup_path.is_dir() and any(backup_path.iterdir()):
                restore_button = getattr(self, f"RestoreButton_{category}", None)
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
        """Adds a backup section to the given layout with specified title and backup type.
        Args:
            layout (QBoxLayout): The layout to which the backup section will be added.
            title (str): The title of the backup section.
            backup_type (Literal["XSE", "RESHADE", "VULKAN", "ENB"]): The type of backup to be managed.
        Returns:
            None"""
        layout.addWidget(self.create_separator())

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        buttons_layout = QHBoxLayout()
        backup_button = QPushButton(f"BACKUP {backup_type}")
        restore_button = QPushButton(f"RESTORE {backup_type}")
        remove_button = QPushButton(f"REMOVE {backup_type}")

        for button, action in [
            (backup_button, "BACKUP"),
            (restore_button, "RESTORE"),
            (remove_button, "REMOVE"),
        ]:
            button.clicked.connect(
                lambda _, b=backup_type, a=action: self.classic_files_manage(
                    f"Backup {b}",
                    a,  # type: ignore
                )
            )
            button.setStyleSheet(
                """
                QPushButton {
                    color: white;
                    background: rgba(10, 10, 10, 0.75);
                    border-radius: 10px;
                    border: 1px solid white;
                    font-size: 11px;
                    min-height: 48px;
                    max-height: 48px;
                    min-width: 180px;
                    max-width: 180px;
                }
            """
            )
            buttons_layout.addWidget(button)

        layout.addLayout(buttons_layout)

    def classic_files_manage(self, selected_list: str, selected_mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
        """Manages game files based on the selected mode.

        Args:
            selected_list (str): The name of the list to manage.
            selected_mode (Literal["BACKUP", "RESTORE", "REMOVE"], optional): The mode of operation. Defaults to "BACKUP".

        Raises:
            PermissionError: If the application does not have permission to access the game files.

        This method performs different actions based on the selected mode:
        - "BACKUP": Backs up the selected list and enables the corresponding restore button.
        - "RESTORE": Restores the selected list.
        - "REMOVE": Removes the selected list."""
        list_name = selected_list.split(" ", 1)
        try:
            CGame.game_files_manage(selected_list, selected_mode)
            if selected_mode == "BACKUP":
                # Enable the corresponding restore button
                restore_button = getattr(self, f"RestoreButton_{list_name[1]}", None)
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
        except PermissionError:
            QMessageBox.critical(
                self,
                "Error",
                "Unable to access files from your game folder. Please run CLASSIC in admin mode to resolve this problem.",
                QMessageBox.StandardButton.NoButton,
                QMessageBox.StandardButton.NoButton,
            )

    def help_popup_backup(self) -> None:
        """
        Displays a help popup with information retrieved from the YAML settings.

        This method retrieves the help text from the YAML settings using the key
        "CLASSIC_Interface.help_popup_backup" and displays it in an information
        message box with the title "NEED HELP?".

        Returns:
            None
        """
        help_popup_text = CMain.yaml_settings(str, CMain.YAML.Main, "CLASSIC_Interface.help_popup_backup") or ""
        QMessageBox.information(self, "NEED HELP?", help_popup_text, QMessageBox.StandardButton.Ok)

    @staticmethod
    def open_backup_folder() -> None:
        """
        Opens the CLASSIC Backup/Game Files folder in the default file explorer.

        This function constructs the path to the "CLASSIC Backup/Game Files" folder
        relative to the current working directory and opens it using the system's
        default file explorer.

        Returns:
            None
        """
        backup_path = Path.cwd() / "CLASSIC Backup/Game Files"
        QDesktopServices.openUrl(QUrl.fromLocalFile(backup_path))

    def setup_output_text_box(self, layout: QLayout) -> None:
        """Sets up the output text box widget with specified properties and adds it to the given layout.
        Args:
            layout (QLayout): The layout to which the output text box will be added.
        Returns:
            None"""
        self.output_text_box = QTextEdit(self)
        self.output_text_box.setReadOnly(True)
        self.output_text_box.setStyleSheet(
            """
            QTextEdit {
                color: white;
                font-family: "Cascadia Mono", Consolas, monospace;
                background: rgba(10, 10, 10, 0.75);
                border-radius: 10px;
                border: 1px solid white;
                font-size: 13px;
            }
        """
        )  # Have to use alternate font here because the default font doesn't support some characters.

        self.output_text_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.output_text_box.setMinimumHeight(150)
        layout.addWidget(self.output_text_box)

        self.output_buffer = ""

    def update_output_text_box(self, text: str | bytes) -> None:
        """
        Updates the output text box with the provided text.
        This method processes the incoming text, appends it to an internal buffer,
        and updates the output text box with complete lines from the buffer. If the
        text is in bytes, it is decoded to a string using UTF-8 encoding. The method
        ensures that the output text box is scrolled to the bottom after updating.
        Args:
            text (str | bytes): The text to be added to the output text box. It can
                                be either a string or bytes.
        Raises:
            Exception: If an error occurs during the update process, it is caught
                       and printed to the console.
        """
        try:
            # If the incoming text is bytes, decode it
            text = text.decode("utf-8", errors="replace") if isinstance(text, bytes) else str(text)

            # Append the incoming text to the buffer
            self.output_buffer += text

            # Split the buffer into lines, keeping newlines
            lines = self.output_buffer.splitlines(True)

            # Initialize flag to track if the last line ended with a newline
            ends_with_newline = self.output_buffer.endswith("\n")

            # Process all complete lines
            complete_lines = lines[:-1] if not ends_with_newline else lines

            if complete_lines:
                current_text = self.output_text_box.toPlainText() if self.output_text_box is not None else ""

                # Append complete lines without extra newlines
                new_text = current_text + "".join(complete_lines)
                if self.output_text_box is not None:
                    self.output_text_box.setPlainText(new_text)

                # Scroll to the bottom
                if self.output_text_box is not None:
                    scrollbar = self.output_text_box.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())

            # Keep the last incomplete line in the buffer if it's not complete
            self.output_buffer = lines[-1] if not ends_with_newline else ""

        except Exception as e:  # noqa: BLE001
            print(f"Error in update_output_text_box: {e}")

    def process_lines(self, lines: list[str]) -> None:
        """
        Processes a list of lines, appending each stripped line to the output text box.
        Args:
            lines (list[str]): A list of strings to be processed.
        Returns:
            None
        """
        for line in lines:
            stripped_line = line.rstrip()
            if (stripped_line or line.endswith("\n")) and self.output_text_box is not None:
                self.output_text_box.append(stripped_line)

        # Scroll to the bottom of the text box
        if self.output_text_box is not None:
            scrollbar = self.output_text_box.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def setup_output_redirection(self) -> None:
        """
        Sets up the redirection of standard output and error streams to a custom output redirector.

        This method initializes an instance of OutputRedirector and connects its outputWritten signal
        to the update_output_text_box method. It then redirects sys.stdout and sys.stderr to the
        output_redirector, ensuring that all standard output and error messages are captured and
        handled by the custom redirector.
        """
        self.output_redirector = OutputRedirector()
        self.output_redirector.outputWritten.connect(self.update_output_text_box)
        sys.stdout = self.output_redirector
        sys.stderr = self.output_redirector  # Redirect stderr as well

    @staticmethod
    def create_separator() -> QFrame:
        """
        Creates a horizontal line separator using QFrame.

        Returns:
            QFrame: A QFrame object configured as a horizontal line separator with a sunken shadow.
        """
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        return separator

    def setup_checkboxes(self, layout: QBoxLayout) -> None:
        """
        Sets up the checkboxes and update source combo box in the provided layout.
        Args:
            layout (QBoxLayout): The layout to which the checkboxes and update source combo box will be added.
        This method performs the following tasks:
        - Creates a vertical layout for the checkboxes section.
        - Adds a title label for the checkbox section.
        - Creates a grid layout for the checkboxes with increased horizontal and vertical spacing.
        - Adds checkboxes for various settings to the grid layout.
        - Adds some vertical spacing after the checkboxes.
        - Adds a horizontal layout for the update source combo box.
        - Configures the update source combo box with options ("Nexus", "GitHub", "Both").
        - Sets the size policy and alignment for the update source combo box and label.
        - Sets the default value of the combo box based on stored settings.
        - Connects the combo box's currentTextChanged signal to update the settings.
        - Adds the update source layout below the checkboxes.
        - Adds a separator after the checkboxes.
        """
        checkbox_layout = QVBoxLayout()

        # Title for the checkbox section
        title_label = QLabel("CLASSIC SETTINGS")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        checkbox_layout.addWidget(title_label)

        # Grid for checkboxes
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(40)  # Increased spacing
        grid_layout.setVerticalSpacing(20)  # Increased spacing

        checkboxes = [
            ("FCX MODE", "FCX Mode"),
            ("SIMPLIFY LOGS", "Simplify Logs"),
            ("UPDATE CHECK", "Update Check"),
            ("VR MODE", "VR Mode"),
            ("SHOW FID VALUES", "Show FormID Values"),
            ("MOVE INVALID LOGS", "Move Unsolved Logs"),
            ("AUDIO NOTIFICATIONS", "Audio Notifications"),
        ]

        for index, (label, setting) in enumerate(checkboxes):
            checkbox = self.create_checkbox(label, setting)
            row = index // 3
            col = index % 3
            grid_layout.addWidget(checkbox, row, col, Qt.AlignmentFlag.AlignLeft)

        checkbox_layout.addLayout(grid_layout)

        # Add some vertical spacing
        checkbox_layout.addSpacing(20)

        layout.addLayout(checkbox_layout)

        update_source_layout = QHBoxLayout()

        update_source_label = QLabel("Update Source")
        update_source_combo = QComboBox()
        update_sources = ("Nexus", "GitHub", "Both")
        update_source_combo.addItems(update_sources)

        # Set the ComboBox to adjust size based on content
        update_source_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        # Optionally, reduce the spacing between the label and ComboBox
        update_source_layout.setSpacing(10)  # Adjust the spacing between label and combo box

        # Set layout margins to 0 to bring the label and combo box closer
        update_source_layout.setContentsMargins(0, 0, 0, 0)

        # Set the layout alignment to align left
        update_source_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Set the size policy to prevent expanding
        update_source_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        update_source_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Calculate the width of the longest item and set the ComboBox width accordingly
        font_metrics = QFontMetrics(update_source_combo.font())
        combo_width = max(font_metrics.horizontalAdvance(item) for item in update_sources) + 30
        update_source_combo.setFixedWidth(combo_width)

        # Set the default value if stored in settings
        current_value = CMain.classic_settings(str, "Update Source")
        if current_value is not None:
            update_source_combo.setCurrentText(current_value)
        else:
            CMain.yaml_settings(str, CMain.YAML.Settings, "CLASSIC_Settings.Update Source", "Nexus")

        update_source_combo.setToolTip("Select the source to check for updates. Nexus = stable, GitHub = latest, Both = check both")

        update_source_combo.currentTextChanged.connect(
            lambda value: CMain.yaml_settings(str, CMain.YAML.Settings, "CLASSIC_Settings.Update Source", value)
        )

        update_source_layout.addWidget(update_source_label)
        update_source_layout.addWidget(update_source_combo)

        # Add the update source layout below the checkboxes
        layout.addLayout(update_source_layout)

        # Add a separator after the checkboxes
        layout.addWidget(self.create_separator())

    def create_checkbox(self, label_text: str, setting: str) -> QCheckBox:
        """Creates a QCheckBox widget with a custom label and setting.
        Args:
            label_text (str): The text label for the checkbox.
            setting (str): The setting key associated with the checkbox.
        Returns:
            QCheckBox: The created checkbox widget.
        The checkbox state is initialized based on the value retrieved from
        `CMain.classic_settings`. If the value is not found, it defaults to False
        and updates the `CMain.yaml_settings`. The checkbox state change is
        connected to update the `CMain.yaml_settings` accordingly. Additionally,
        if the setting is "Audio Notifications", it connects to toggle the audio
        player state.
        The checkbox is styled with a custom stylesheet to define spacing and
        indicator images for checked and unchecked states."""
        checkbox = QCheckBox(label_text)
        value = CMain.classic_settings(bool, setting)
        if value is not None:
            checkbox.setChecked(value)
        else:
            CMain.yaml_settings(bool, CMain.YAML.Settings, f"CLASSIC_Settings.{setting}", False)
            checkbox.setChecked(False)

        checkbox.stateChanged.connect(
            lambda state: CMain.yaml_settings(bool, CMain.YAML.Settings, f"CLASSIC_Settings.{setting}", bool(state))
        )
        if setting == "Audio Notifications":
            checkbox.stateChanged.connect(lambda state: self.audio_player.toggle_audio(state))

        # Apply custom style sheet
        checkbox.setStyleSheet(
            """
            QCheckBox {
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 25px;
                height: 25px;
            }
            QCheckBox::indicator:unchecked {
                image: pb_source(CLASSIC Data/graphics/unchecked.png);
            }
            QCheckBox::indicator:checked {
                image: pb_source(CLASSIC Data/graphics/checked.png);
            }
        """
        )

        return checkbox

    @staticmethod
    def setup_folder_section(
            layout: QBoxLayout, title: str, box_name: str, browse_callback: Callable[[], None], tooltip: str = ""
    ) -> QLineEdit:
        """
        Sets up a folder selection section within a given layout.
        Args:
            layout (QBoxLayout): The layout to which the folder section will be added.
            title (str): The title of the folder section.
            box_name (str): The object name for the QLineEdit.
            browse_callback (Callable[[], None]): The callback function to be called when the browse button is clicked.
            tooltip (str, optional): The tooltip text for the browse button. Defaults to "".
        Returns:
            QLineEdit: The QLineEdit widget created for the folder path input.
        """
        section_layout = QHBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(5)

        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setFixedWidth(180)
        section_layout.addWidget(label)

        line_edit = QLineEdit()
        line_edit.setObjectName(box_name)
        section_layout.addWidget(line_edit, 1)

        browse_button = QPushButton("Browse Folder")
        if tooltip:
            browse_button.setToolTip(tooltip)
        browse_button.clicked.connect(browse_callback)
        section_layout.addWidget(browse_button)

        layout.addLayout(section_layout)
        return line_edit  # Return the created QLineEdit

    def setup_main_buttons(self, layout: QBoxLayout) -> None:
        """
        Sets up the main and bottom row buttons in the provided layout.
        This method creates two horizontal layouts: one for the main action buttons
        and one for the bottom row buttons. It adds buttons to these layouts and
        associates them with their respective callback functions.
        Args:
            layout (QBoxLayout): The layout to which the button layouts will be added.
        Returns:
            None
        """
        # Main action buttons
        main_buttons_layout = QHBoxLayout()
        main_buttons_layout.setSpacing(10)
        self.crash_logs_button = self.add_main_button(main_buttons_layout, "SCAN CRASH LOGS", self.crash_logs_scan)
        self.scan_button_group.addButton(self.crash_logs_button)
        self.game_files_button = self.add_main_button(main_buttons_layout, "SCAN GAME FILES", self.game_files_scan)
        self.scan_button_group.addButton(self.game_files_button)
        layout.addLayout(main_buttons_layout)

        # Bottom row buttons
        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.setSpacing(5)
        self.add_bottom_button(bottom_buttons_layout, "CHANGE INI PATH", self.select_folder_ini)
        self.add_bottom_button(bottom_buttons_layout, "OPEN CLASSIC SETTINGS", self.open_settings)
        self.add_bottom_button(bottom_buttons_layout, "CHECK UPDATES", self.update_popup_explicit)
        layout.addLayout(bottom_buttons_layout)

    @staticmethod
    def setup_articles_section(layout: QBoxLayout) -> None:
        """Sets up the articles section in the given layout.
        This function adds a title label and a grid of buttons to the provided layout.
        Each button corresponds to an article, website, or Nexus link related to Fallout 4.
        Clicking a button will open the associated URL in the default web browser.
        Args:
            layout (QBoxLayout): The layout to which the articles section will be added.
        Returns:
            None"""
        # Title for the articles section
        title_label = QLabel("ARTICLES / WEBSITES / NEXUS LINKS")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Grid layout for article buttons
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(10)

        button_data = [
            {
                "text": "BUFFOUT 4 INSTALLATION",
                "pb_source": "https://www.nexusmods.com/fallout4/articles/3115",
            },
            {
                "text": "FALLOUT 4 SETUP TIPS",
                "pb_source": "https://www.nexusmods.com/fallout4/articles/4141",
            },
            {
                "text": "IMPORTANT PATCHES LIST",
                "pb_source": "https://www.nexusmods.com/fallout4/articles/3769",
            },
            {
                "text": "BUFFOUT 4 NEXUS PAGE",
                "pb_source": "https://www.nexusmods.com/fallout4/mods/47359",
            },
            {
                "text": "CLASSIC NEXUS PAGE",
                "pb_source": "https://www.nexusmods.com/fallout4/mods/56255",
            },
            {
                "text": "CLASSIC GITHUB",
                "pb_source": "https://github.com/GuidanceOfGrace/CLASSIC-Fallout4",
            },
            {
                "text": "DDS TEXTURE SCANNER",
                "pb_source": "https://www.nexusmods.com/fallout4/mods/71588",
            },
            {"text": "BETHINI PIE", "pb_source": "https://www.nexusmods.com/site/mods/631"},
            {
                "text": "WRYE BASH TOOL",
                "pb_source": "https://www.nexusmods.com/fallout4/mods/20032",
            },
        ]

        for i, data in enumerate(button_data):
            button = QPushButton(data["text"])
            button.setFixedSize(180, 50)  # Set fixed size for buttons
            button.setStyleSheet(
                """
                QPushButton {
                    color: white;
                    background-color: rgba(10, 10, 10, 0.75);
                    border: 1px solid white;
                    border-radius: 5px;
                    padding: 5px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(50, 50, 50, 0.75);
                }
                QPushButton:disabled {
                    color: gray;
                    background-color: rgba(10, 10, 10, 0.75);
                }
            """
            )
            button.clicked.connect(lambda _, url=data["pb_source"]: QDesktopServices.openUrl(QUrl(url)))
            row = i // 3
            col = i % 3
            grid_layout.addWidget(button, row, col, Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(grid_layout)

        # Add some vertical spacing after the articles section
        layout.addSpacing(20)

    def setup_bottom_buttons(self, layout: QBoxLayout) -> None:
        """Sets up the bottom buttons in the given layout.
        This method creates and configures the following buttons:
        - ABOUT: Displays information about the application.
        - HELP: Opens the help popup.
        - START PAPYRUS MONITORING: Toggles the Papyrus log monitoring feature.
        - EXIT: Closes the application.
        Each button is styled and added to a horizontal layout, which is then added to the provided layout.
        Args:
            layout (QBoxLayout): The layout to which the bottom buttons will be added."""
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(5)

        # ABOUT button
        about_button = QPushButton("ABOUT")
        about_button.setFixedSize(80, 30)
        about_button.clicked.connect(self.show_about)
        about_button.setStyleSheet(
            """
            QPushButton {
                color: white;
                background: rgba(10, 10, 10, 0.75);
                border-radius: 10px;
                border: 1px solid white;
                font-size: 11px;
            }
        """
        )
        bottom_layout.addWidget(about_button)

        # HELP button
        help_button = QPushButton("HELP")
        help_button.setFixedSize(80, 30)
        help_button.clicked.connect(self.help_popup_main)
        help_button.setStyleSheet(
            """
            QPushButton {
                color: white;
                background: rgba(10, 10, 10, 0.75);
                border-radius: 10px;
                border: 1px solid white;
                font-size: 11px;
            }
        """
        )
        bottom_layout.addWidget(help_button)

        # PAPYRUS MONITORING button
        self.papyrus_button = QPushButton("START PAPYRUS MONITORING")
        self.papyrus_button.setFixedHeight(30)
        self.papyrus_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.papyrus_button.clicked.connect(self.toggle_papyrus_worker)
        self.papyrus_button.setEnabled(True)  # Enable the button since monitoring is now implemented
        self.papyrus_button.setStyleSheet(
            """
            QPushButton {
                color: black;
                background: rgb(45, 237, 138);
                border-radius: 10px;
                border: 1px solid black;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:disabled {
                color: gray;
                background: rgba(10, 10, 10, 0.75);
            }
        """
        )
        self.papyrus_button.setToolTip(
            """Start monitoring the Papyrus logs for new errors.
This feature is not fully implemented."""
        )
        self.papyrus_button.setCheckable(True)
        bottom_layout.addWidget(self.papyrus_button)

        # EXIT button
        exit_button = QPushButton("EXIT")
        exit_button.setFixedSize(80, 30)
        exit_button.clicked.connect(QApplication.quit)
        exit_button.setStyleSheet(
            """
            QPushButton {
                color: white;
                background: rgba(10, 10, 10, 0.75);
                border-radius: 10px;
                border: 1px solid white;
                font-size: 11px;
            }
        """
        )
        bottom_layout.addWidget(exit_button)

        layout.addLayout(bottom_layout)

    def show_about(self) -> None:
        """
        Displays the 'About' dialog.

        This method creates an instance of the CustomAboutDialog class and executes it,
        showing the 'About' dialog to the user.
        """
        dialog = CustomAboutDialog(self)
        dialog.exec()

    def help_popup_main(self) -> None:
        """
        Displays a help popup with information retrieved from the YAML settings.

        This method fetches the help text from the YAML settings using the key
        "CLASSIC_Interface.help_popup_main". If the help text is not found, it defaults
        to an empty string. The help text is then displayed in a QMessageBox with an
        "Ok" button.

        Returns:
            None
        """
        help_popup_text = CMain.yaml_settings(str, CMain.YAML.Main, "CLASSIC_Interface.help_popup_main") or ""
        QMessageBox.information(self, "NEED HELP?", help_popup_text, QMessageBox.StandardButton.Ok)

    @staticmethod
    def add_main_button(layout: QLayout, text: str, callback: Callable[[], None], tooltip: str = "") -> QPushButton:
        """Adds a main button to the given layout with specified text, callback, and optional tooltip.

        Args:
            layout (QLayout): The layout to which the button will be added.
            text (str): The text to display on the button.
            callback (Callable[[], None]): The function to call when the button is clicked.
            tooltip (str, optional): The tooltip text to display when hovering over the button. Defaults to "".

        Returns:
            QPushButton: The created button."""
        button = QPushButton(text)
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
        """Adds a button to the bottom of the given layout with specified text, callback, and optional tooltip.

        Args:
            layout (QLayout): The layout to which the button will be added.
            text (str): The text to display on the button.
            callback (Callable[[], None]): The function to call when the button is clicked.
            tooltip (str, optional): The tooltip text to display when hovering over the button. Defaults to an empty string.

        Returns:
            None"""
        button = QPushButton(text)
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

    def select_folder_scan(self) -> None:
        """
        Opens a dialog to select a custom scan folder and updates the scan folder path.

        This method opens a QFileDialog to allow the user to select a directory. If a directory
        is selected and the scan_folder_edit widget is not None, it sets the text of the
        scan_folder_edit widget to the selected directory path. Additionally, it updates the
        YAML settings with the selected folder path.

        Returns:
            None
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Custom Scan Folder")
        if folder:
            if self.scan_folder_edit is not None:
                self.scan_folder_edit.setText(folder)
            CMain.yaml_settings(str, CMain.YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", folder)

    def select_folder_mods(self) -> None:
        """
        Opens a dialog to select a directory for staging mods and updates the mods folder path setting.

        This method uses QFileDialog to prompt the user to select a directory. If a directory is selected,
        it updates the text of the mods_folder_edit widget with the selected folder path and saves the path
        to the YAML settings under "CLASSIC_Settings.MODS Folder Path".

        Returns:
            None
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Staging Mods Folder")
        if folder:
            if self.mods_folder_edit is not None:
                self.mods_folder_edit.setText(folder)
            CMain.yaml_settings(str, CMain.YAML.Settings, "CLASSIC_Settings.MODS Folder Path", folder)

    def initialize_folder_paths(self) -> None:
        """
        Initializes the folder paths for scan and mods folders by retrieving the paths
        from the classic settings and setting the text of the corresponding edit fields.
        This method retrieves the "SCAN Custom Path" and "MODS Folder Path" from the
        classic settings using the CMain.classic_settings method. If the retrieved paths
        are not empty and the corresponding edit fields (self.scan_folder_edit and
        self.mods_folder_edit) are not None, it sets the text of these edit fields to
        the retrieved paths.
        """
        scan_folder = CMain.classic_settings(str, "SCAN Custom Path")
        mods_folder = CMain.classic_settings(str, "MODS Folder Path")

        if scan_folder and self.scan_folder_edit is not None:
            self.scan_folder_edit.setText(scan_folder)
        if mods_folder and self.mods_folder_edit is not None:
            self.mods_folder_edit.setText(mods_folder)

    def select_folder_ini(self) -> None:
        """
        Opens a dialog for the user to select a folder and sets the selected folder path
        in the YAML settings under "CLASSIC_Settings.INI Folder Path". Displays a message
        box to inform the user of the new path.

        Returns:
            None
        """
        folder = QFileDialog.getExistingDirectory(self)
        if folder:
            CMain.yaml_settings(str, CMain.YAML.Settings, "CLASSIC_Settings.INI Folder Path", folder)
            QMessageBox.information(self, "New INI Path Set", f"You have set the new path to: \n{folder}",
                                    QMessageBox.StandardButton.Ok)

    @staticmethod
    def open_settings() -> None:
        settings_file = "CLASSIC Settings.yaml"
        QDesktopServices.openUrl(QUrl.fromLocalFile(settings_file))

    def crash_logs_scan(self) -> None:
        """Initializes and starts a background thread to scan for crash logs.
        This method sets up a QThread and a CrashLogsScanWorker to perform the
        crash log scanning in a separate thread. It connects various signals
        between the worker and the main application to handle notifications,
        errors, and cleanup after the scan is complete.
        The method performs the following steps:
        1. Checks if the crash logs thread is already running.
        2. Initializes the QThread and CrashLogsScanWorker if not already running.
        3. Moves the worker to the thread.
        4. Connects the worker's notification and error signals to the audio player.
        5. Connects the thread's started signal to the worker's run method.
        6. Connects the worker's finished signal to the thread's quit method and
           to the worker's deleteLater method.
        7. Connects the thread's finished signal to its own deleteLater method and
           to the crash_logs_scan_finished method.
        8. Disables scan buttons and updates the UI text.
        9. Starts the thread."""
        if self.crash_logs_thread is None:
            self.crash_logs_thread = QThread()
            self.crash_logs_worker = CrashLogsScanWorker()
            self.crash_logs_worker.moveToThread(self.crash_logs_thread)

            self.crash_logs_worker.notify_sound_signal.connect(self.audio_player.play_notify_signal.emit)
            self.crash_logs_worker.error_sound_signal.connect(self.audio_player.play_error_signal.emit)

            self.crash_logs_thread.started.connect(self.crash_logs_worker.run)
            self.crash_logs_worker.finished.connect(self.crash_logs_thread.quit)
            self.crash_logs_worker.finished.connect(self.crash_logs_worker.deleteLater)
            self.crash_logs_thread.finished.connect(self.crash_logs_thread.deleteLater)
            self.crash_logs_thread.finished.connect(self.crash_logs_scan_finished)

            # Disable buttons and update text
            self.disable_scan_buttons()

            self.crash_logs_thread.start()

    def game_files_scan(self) -> None:
        """
        Initiates a scan of game files in a separate thread.
        This method sets up a QThread and a GameFilesScanWorker to perform the scan
        in the background. It connects various signals and slots to handle notifications,
        errors, and cleanup after the scan is complete. The method also disables scan
        buttons and updates the UI text accordingly.
        Signals:
            notify_sound_signal: Emitted to play a notification sound.
            error_sound_signal: Emitted to play an error sound.
            finished: Emitted when the scan is finished.
        Note:
            This method should only be called if `self.game_files_thread` is None.
        """
        if self.game_files_thread is None:
            self.game_files_thread = QThread()
            self.game_files_worker = GameFilesScanWorker()
            self.game_files_worker.moveToThread(self.game_files_thread)

            self.game_files_worker.notify_sound_signal.connect(self.audio_player.play_notify_signal.emit)
            self.game_files_worker.error_sound_signal.connect(self.audio_player.play_error_signal.emit)

            self.game_files_thread.started.connect(self.game_files_worker.run)
            self.game_files_worker.finished.connect(self.game_files_thread.quit)
            self.game_files_worker.finished.connect(self.game_files_worker.deleteLater)
            self.game_files_thread.finished.connect(self.game_files_thread.deleteLater)
            self.game_files_thread.finished.connect(self.game_files_scan_finished)

            # Disable buttons and update text
            self.disable_scan_buttons()

            self.game_files_thread.start()

    def disable_scan_buttons(self) -> None:
        """
        Disables all buttons in the scan_button_group.

        This method iterates through all buttons in the scan_button_group and
        sets their enabled state to False, effectively disabling them.
        """
        for button_id in self.scan_button_group.buttons():
            button_id.setEnabled(False)

    def enable_scan_buttons(self) -> None:
        """
        Enables all buttons in the scan_button_group.

        This method iterates through all buttons in the scan_button_group and
        sets their enabled state to True, allowing them to be interacted with.
        """
        for button_id in self.scan_button_group.buttons():
            button_id.setEnabled(True)

    def crash_logs_scan_finished(self) -> None:
        """
        Callback method to be called when the crash logs scanning process is finished.

        This method performs the following actions:
        1. Sets the crash_logs_thread attribute to None, indicating that the scanning thread has completed.
        2. Calls the enable_scan_buttons method to re-enable any buttons or UI elements related to scanning.

        Returns:
            None
        """
        self.crash_logs_thread = None
        self.enable_scan_buttons()

    def game_files_scan_finished(self) -> None:
        """
        Callback function to be called when the game files scan is finished.

        This method performs the following actions:
        1. Sets the game_files_thread attribute to None.
        2. Enables the scan buttons by calling the enable_scan_buttons method.

        Returns:
            None
        """
        self.game_files_thread = None
        self.enable_scan_buttons()

    def toggle_papyrus_worker(self) -> None:
        """
        Toggles the Papyrus monitoring based on the state of the papyrus_button.

        If the papyrus_button is checked, it starts the Papyrus monitoring.
        Otherwise, it stops the Papyrus monitoring.

        Returns:
            None
        """
        if self.papyrus_button and self.papyrus_button.isChecked():
            self.start_papyrus_monitoring()
        else:
            self.stop_papyrus_monitoring()

    def start_papyrus_monitoring(self) -> None:
        """Starts the Papyrus monitoring process in a separate thread.
        This method initializes a new QThread and a PapyrusMonitorWorker, moves the worker to the thread,
        connects the necessary signals for monitoring, and starts the thread. It also updates the text
        and style of the Papyrus monitoring button if it exists.
        Signals connected:
            - self.papyrus_monitor_thread.started: Connects to self.papyrus_monitor_worker.run to start the worker.
            - self.papyrus_monitor_worker.statsUpdated: Connects to self.update_papyrus_stats to update stats.
            - self.papyrus_monitor_worker.error: Connects to self.handle_papyrus_error to handle errors.
        Button update:
            If self.papyrus_button is not None, updates the button text to "STOP PAPYRUS MONITORING" and changes
            its style to have a red background, black text, and other specified styles.
        Returns:
            None"""
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
            if self.papyrus_button is not None:
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
        """Stops the Papyrus monitoring process.
        This method stops the Papyrus monitor worker and thread if they are running,
        resets them to None, and updates the UI elements accordingly. Specifically,
        it changes the text and style of the Papyrus button to indicate that monitoring
        has stopped and appends a message to the output text box.
        Returns:
            None"""
        if self.papyrus_monitor_worker:
            self.papyrus_monitor_worker.stop()

        if self.papyrus_monitor_thread:
            self.papyrus_monitor_thread.quit()
            self.papyrus_monitor_thread.wait()

            # Reset thread and worker
            self.papyrus_monitor_thread = None
            self.papyrus_monitor_worker = None

            # Update UI
            if self.papyrus_button is not None:
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
            if self.output_text_box is not None:
                self.output_text_box.append("\n=== Papyrus monitoring stopped ===\n")

    def update_papyrus_stats(self, stats: PapyrusStats) -> None:
        """
        Updates the Papyrus log statistics display with the provided stats.
        This method formats the given PapyrusStats object into a readable message
        and appends it to the output text box. If the output text box is present,
        it will automatically scroll to the bottom to show the latest message.
        The stats are also stored in the instance variable `_last_stats`.
        Args:
            stats (PapyrusStats): An object containing the Papyrus log statistics.
        """
        message = (
            f"\n=== Papyrus Log Stats [{stats.timestamp.strftime('%H:%M:%S')}] ===\n"
            f"Number of Dumps: {stats.dumps}\n"
            f"Number of Stacks: {stats.stacks}\n"
            f"Dumps/Stacks Ratio: {stats.ratio:.3f}\n"
            f"Number of Warnings: {stats.warnings}\n"
            f"Number of Errors: {stats.errors}\n"
        )
        if self.output_text_box is not None:
            self.output_text_box.append(message)

            # Scroll to the bottom after adding the new message
            self.output_text_box.verticalScrollBar().setValue(self.output_text_box.verticalScrollBar().maximum())

        self._last_stats = stats

    def handle_papyrus_error(self, error_msg: str) -> None:
        """
        Handles errors that occur during Papyrus monitoring.

        This method performs the following actions when an error occurs:
        1. Appends an error message to the output text box, if it exists.
        2. Unchecks the Papyrus button, if it exists.
        3. Plays an error sound if it hasn't been played already.
        4. Stops the Papyrus monitoring process.

        Args:
            error_msg (str): The error message to be displayed and logged.
        """
        if self.output_text_box is not None:
            self.output_text_box.append(f"\n❌ ERROR IN PAPYRUS MONITORING: {error_msg}\n")
        if self.papyrus_button is not None:
            self.papyrus_button.setChecked(False)
        if self.papyrus_monitor_worker and not self.papyrus_monitor_worker.error_sound_played:
            self.audio_player.play_error_signal.emit()
            self.papyrus_monitor_worker.error_sound_played = True
        self.stop_papyrus_monitoring()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # noinspection PyBroadException
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except KeyboardInterrupt:
        app.exit(1)
    except Exception as _:  # noqa: BLE001
        error_text = traceback.format_exc()
        show_exception_box(error_text)
