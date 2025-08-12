"""
Folder management functionality for the CLASSIC interface.

This module contains a mixin class that handles folder selection, validation,
and path management functionality.
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
from ClassicLib.MessageHandler import msg_error
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class FolderManagementMixin:
    """
    Mixin class providing folder management functionality for the MainWindow.

    This class requires the following attributes to be present in the class it's mixed into:
    - scan_folder_edit: QLineEdit for custom scan folder path
    - mods_folder_edit: QLineEdit for mods folder path
    """

    if TYPE_CHECKING:
        scan_folder_edit: QLineEdit | None
        mods_folder_edit: QLineEdit | None

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
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        while True:
            folder: str = QFileDialog.getExistingDirectory(self, "Select Custom Scan Folder")
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
                self,
                "Invalid Custom Scan Path",
                "The selected directory cannot be used as a custom scan path.\n\n"
                "The 'Crash Logs' folder and its subfolders are managed by CLASSIC "
                "and cannot be set as custom scan directories.\n\n"
                "Please select a different directory.",
            )

    def validate_scan_folder_text(self) -> None:
        """
        Validates the manually entered scan folder path when the text field is edited.

        This method is called when the user finishes editing the scan folder text field
        (e.g., by pressing Enter or when the field loses focus). It validates the entered
        path and saves it if valid, or clears it if invalid.
        """
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        if self.scan_folder_edit is None:
            return

        folder_text = self.scan_folder_edit.text().strip()

        # If empty, clear the setting
        if not folder_text:
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", " ")
            return

        # Check if path exists
        path_obj = Path(folder_text)
        if not path_obj.exists() or not path_obj.is_dir():
            QMessageBox.warning(
                self,
                "Invalid Path",
                f"The path '{folder_text}' does not exist or is not a directory.\n\nThe custom scan path has been cleared.",
            )
            self.scan_folder_edit.clear()
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")
            return

        # Check if path is restricted
        if not is_valid_custom_scan_path(folder_text):
            QMessageBox.warning(
                self,
                "Invalid Custom Scan Path",
                "The entered directory cannot be used as a custom scan path.\n\n"
                "The 'Crash Logs' folder and its subfolders are managed by CLASSIC "
                "and cannot be set as custom scan directories.\n\n"
                "The custom scan path has been cleared.",
            )
            self.scan_folder_edit.clear()
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")
            return

        # Valid path, save it
        yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", str(path_obj.resolve()))

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
        if not settings_file.is_file():
            QMessageBox.critical(
                self,
                "Settings File Missing",
                "Settings file is missing. Please restart the application and the issue will be resolved.",
                QMessageBox.StandardButton.Ok,
            )
        else:
            self._open_file_with_notepadpp(settings_file)

    def open_backup_folder(self) -> None:
        """
        Opens the backup folder in a file explorer or displays an error if the folder
        is not found.

        This function attempts to open the backup folder using the system's default file
        explorer. If the folder exists, it will be opened, otherwise an error message
        will be displayed to inform the user that the folder has not been created yet.

        Returns:
            None
        """
        backup_folder: Path = cast("Path", GlobalRegistry.get_local_dir()) / "CLASSIC Backup"
        if backup_folder.is_dir():
            # noinspection PyUnresolvedReferences
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(backup_folder)))
        else:
            msg_error("Backup folder has not been created yet.")

    def open_crash_logs_folder(self) -> None:
        """
        Opens the crash logs folder in the system's file explorer. Creates the folder
        if it doesn't exist.

        Returns:
            None
        """
        crash_logs_folder: Path = cast("Path", GlobalRegistry.get_local_dir()) / "Crash Logs"
        if not crash_logs_folder.is_dir():
            crash_logs_folder.mkdir(parents=True, exist_ok=True)

        # noinspection PyUnresolvedReferences
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(crash_logs_folder)))

    @staticmethod
    def _open_file_with_notepadpp(file_path: Path) -> None:
        """
        Opens a file with Notepad++ if available, otherwise falls back to system default.

        Args:
            file_path: Path to the file to open
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
