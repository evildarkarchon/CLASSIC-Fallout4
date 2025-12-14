"""Folder management functionality for the CLASSIC interface.

This module contains a mixin class that handles folder selection, validation,
and path management functionality with optional Rust acceleration for path operations.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QLineEdit, QMessageBox

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML

# Try to import Rust path validator for faster path operations
from ClassicLib.integration.factory import get_path_operations
from ClassicLib.Logger import logger
from ClassicLib.MessageHandler import msg_error
from ClassicLib.YamlSettings import classic_settings, yaml_settings

classic_path = get_path_operations()
_RUST_PATH_AVAILABLE = classic_path is not None

if _RUST_PATH_AVAILABLE:
    logger.debug("FolderManagement: Using Rust PathValidator for path operations (10-20x faster)")
else:
    logger.debug("FolderManagement: Using Python pathlib for path operations")


def _normalize_path(path: str | Path) -> Path:
    """Normalize and validate a path using Rust if available, otherwise Python.

    Args:
        path: Path to normalize (string or Path object)

    Returns:
        Path: Normalized path object

    """
    path_str = str(path)

    if _RUST_PATH_AVAILABLE:
        try:
            # Use Rust for path validation (handles Windows quirks better)
            if classic_path.PathValidator.is_valid_path(path_str):  # pyright: ignore[reportOptionalMemberAccess]
                # Path is valid, use Python Path for normalization
                # (Rust PathValidator focuses on validation, not normalization)
                return Path(path_str).resolve()
        except (AttributeError, TypeError, ValueError, OSError) as e:
            logger.debug(f"Rust path validation failed, using Python: {e}")

    # Fall back to Python pathlib
    return Path(path_str).resolve()


def _is_valid_directory(path: str | Path) -> bool:
    """Check if path exists and is a directory using Rust if available.

    Args:
        path: Path to check

    Returns:
        True if path exists and is a directory, False otherwise.

    """
    path_str = str(path)

    # Handle empty string explicitly (invalid)
    if not path_str:
        return False

    if _RUST_PATH_AVAILABLE:
        try:
            # Use Rust for faster validation
            # is_valid_path checks existence and basic validity
            if not classic_path.PathValidator.is_valid_path(path_str):  # pyright: ignore[reportOptionalMemberAccess]
                return False
            # Then check if it's a directory using Python (since PathValidator doesn't have is_directory)
            return Path(path_str).is_dir()
        except (AttributeError, TypeError, ValueError, OSError) as e:
            logger.debug(f"Rust path validation failed, using Python: {e}")

    # Fall back to Python pathlib
    path_obj = Path(path_str)
    return path_obj.exists() and path_obj.is_dir()


class FolderManagementMixin:
    """Provide folder management features for selecting, validating, and initializing paths in a GUI application.

    This mixin class includes methods to handle folder-related tasks such as selecting folders via dialog boxes,
    validating folder paths, initializing default paths from settings, and opening specific directories for user
    interaction. The paths managed by this class are tailored for specific application functionalities such as
    custom scans, staging mods, and logs.

    Attributes:
        scan_folder_edit (QLineEdit | None): Editable text field in the GUI for the scan folder path.
        mods_folder_edit (QLineEdit | None): Editable text field in the GUI for the mods folder path.

    """

    if TYPE_CHECKING:
        scan_folder_edit: QLineEdit | None
        mods_folder_edit: QLineEdit | None

    def select_folder_scan(self) -> None:
        """Handle selecting and validating a custom folder for scanning.

        Ensures that the selected folder meets required conditions. If the path is
        valid, updates the UI and saves the configuration. Displays a warning
        message if the selected path is invalid.

        Raises:
            QMessageBox: Displays a warning dialog when the selected directory is
            invalid.

        """
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        while True:
            folder: str = QFileDialog.getExistingDirectory(self, "Select Custom Scan Folder")  # pyright: ignore[reportArgumentType]
            if not folder:  # User clicked cancel
                break

            if is_valid_custom_scan_path(folder):
                # Valid path, update and save
                if self.scan_folder_edit is not None:
                    self.scan_folder_edit.setText(folder)
                yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", folder)
                break
            # Invalid path, show warning and continue loop
            QMessageBox.warning(
                self,  # pyright: ignore[reportArgumentType]
                "Invalid Custom Scan Path",
                "The selected directory cannot be used as a custom scan path.\n\n"
                "The 'Crash Logs' folder and its subfolders are managed by CLASSIC "
                "and cannot be set as custom scan directories.\n\n"
                "Please select a different directory.",
            )

    def validate_scan_folder_text(self) -> None:
        """Validate the input text from a folder selection field and updates the application settings accordingly.

        This method ensures that the entered path is valid, exists, is a directory, and is not restricted
        for usage as a custom scan path. If the folder text is invalid or restricted, appropriate warnings
        are displayed, and the setting is cleared. Otherwise, the valid custom scan path is saved to the
        application's settings.

        Raises:
            Displays warning message boxes to the user if the folder path is invalid or restricted.

        """
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        if self.scan_folder_edit is None:
            return

        folder_text = self.scan_folder_edit.text().strip()

        # If empty, clear the setting
        if not folder_text:
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", " ")
            return

        # Check if path exists using Rust if available
        if not _is_valid_directory(folder_text):
            QMessageBox.warning(
                self,  # pyright: ignore[reportArgumentType]
                "Invalid Path",
                f"The path '{folder_text}' does not exist or is not a directory.\n\nThe custom scan path has been cleared.",
            )
            self.scan_folder_edit.clear()
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")
            return

        # Check if path is restricted
        if not is_valid_custom_scan_path(folder_text):
            QMessageBox.warning(
                self,  # pyright: ignore[reportArgumentType]
                "Invalid Custom Scan Path",
                "The entered directory cannot be used as a custom scan path.\n\n"
                "The 'Crash Logs' folder and its subfolders are managed by CLASSIC "
                "and cannot be set as custom scan directories.\n\n"
                "The custom scan path has been cleared.",
            )
            self.scan_folder_edit.clear()
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")
            return

        # Valid path, normalize and save it (use Rust if available)
        normalized_path = _normalize_path(folder_text)
        yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", str(normalized_path))

    def select_folder_mods(self) -> None:
        """Select a folder for staging mods and updates the settings configuration, if applicable.

        If a folder is selected, it updates the associated text field with the selected
        folder's path and saves the folder path to the corresponding YAML settings
        key for future use.
        """
        folder: str = QFileDialog.getExistingDirectory(self, "Select Staging Mods Folder")  # pyright: ignore[reportArgumentType]
        if folder:
            if self.mods_folder_edit is not None:
                self.mods_folder_edit.setText(folder)
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", folder)

    def initialize_folder_paths(self) -> None:
        """Set the text of folder path input fields based on retrieved settings.

        This method initializes the folder paths for 'SCAN Custom Path' and 'MODS Folder Path'
        by fetching their values from the settings and, if they exist, updates the corresponding
        text fields in the user interface.
        """
        scan_folder: str | None = classic_settings(str, "SCAN Custom Path")
        mods_folder: str | None = classic_settings(str, "MODS Folder Path")

        if scan_folder and self.scan_folder_edit is not None:
            self.scan_folder_edit.setText(scan_folder)
        if mods_folder and self.mods_folder_edit is not None:
            self.mods_folder_edit.setText(mods_folder)

    def select_folder_ini(self) -> None:
        """Select a directory and updates the INI folder path setting.

        Displays a dialog for the user to choose a directory. Once a folder is selected, updates
        the INI folder path in the specified YAML settings and informs the user of the updated path
        through a message box.

        Raises:
            QMessageBox: Displays a message to confirm the update of the INI folder path.

        """
        folder: str = QFileDialog.getExistingDirectory(self)  # pyright: ignore[reportArgumentType]
        if folder:
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.INI Folder Path", folder)
            QMessageBox.information(self, "New INI Path Set", f"You have set the new path to: \n{folder}", QMessageBox.StandardButton.Ok)  # pyright: ignore[reportArgumentType]

    def open_settings(self) -> None:
        """Open the settings file for the application.

        This method checks if the settings file exists in the local directory.
        If the file does not exist, a critical error dialog is shown to inform
        the user that the settings file is missing and the application needs
        to be restarted. If the file exists, it will be opened using
        Notepad++.
        """
        settings_file: Path = cast("Path", GlobalRegistry.get_local_dir()) / "CLASSIC Settings.yaml"
        if not settings_file.is_file():
            QMessageBox.critical(
                self,  # pyright: ignore[reportArgumentType]
                "Settings File Missing",
                "Settings file is missing. Please restart the application and the issue will be resolved.",
                QMessageBox.StandardButton.Ok,
            )
        else:
            self._open_file_with_notepadpp(settings_file)

    @staticmethod
    def open_backup_folder() -> None:
        """Open the backup folder if it exists, otherwise displays an error message.

        This method attempts to locate and open the backup folder located within the
        local directory registered in the `GlobalRegistry`. If the folder exists, it
        will be opened using the default file explorer. If the folder does not exist,
        an error message is displayed.
        """
        backup_folder: Path = cast("Path", GlobalRegistry.get_local_dir()) / "CLASSIC Backup"
        if backup_folder.is_dir():
            # noinspection PyUnresolvedReferences
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(backup_folder)))
        else:
            msg_error("Backup folder has not been created yet.")

    @staticmethod
    def open_crash_logs_folder() -> None:
        """Open the crash logs folder. If the folder does not exist, it creates it.

        The method ensures that the "Crash Logs" directory exists within the local directory retrieved
        from the GlobalRegistry. If the directory does not exist, it is created with all necessary
        parent directories. After ensuring the existence of the folder, it is opened using the default
        system method for handling folder URLs.
        """
        crash_logs_folder: Path = cast("Path", GlobalRegistry.get_local_dir()) / "Crash Logs"
        if not crash_logs_folder.is_dir():
            crash_logs_folder.mkdir(parents=True, exist_ok=True)

        # noinspection PyUnresolvedReferences
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(crash_logs_folder)))

    @staticmethod
    def _open_file_with_notepadpp(file_path: Path) -> None:
        """Open a file using Notepad++ if installed, or fall back to system default.

        First checks if the Notepad++ executable exists at the specified path.
        If Notepad++ is not available or an error occurs while trying to open
        the file with it, uses the default system editor to open the file.

        Args:
            file_path (Path): The path to the file that needs to be opened.

        """
        notepadpp_path = Path("C:/Program Files/Notepad++/notepad++.exe")
        file_url: QUrl = QUrl.fromLocalFile(str(file_path))

        if notepadpp_path.exists():
            try:
                subprocess.Popen([str(notepadpp_path), str(file_path)])
            except (OSError, subprocess.SubprocessError):
                # Fallback to system default
                QDesktopServices.openUrl(file_url)
        else:
            # Use system default editor
            QDesktopServices.openUrl(file_url)
