"""
Folder management functionality for the CLASSIC interface.

This module contains a mixin class that handles folder selection and validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox

if TYPE_CHECKING:
    from PySide6.QtWidgets import QLineEdit

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.ScanLog.Util import is_valid_custom_scan_path
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class FolderManagementMixin:
    """
    Mixin class providing folder management functionality for the MainWindow.
    """

    if TYPE_CHECKING:
        # Attributes expected from other mixins (TabSetupMixin)
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

    def open_crash_logs_folder(self) -> None:
        """
        Opens the Crash Logs directory in the system's file explorer.

        This method checks if the local directory is registered in the
        GlobalRegistry. If registered, it attempts to open the Crash Logs folder
        within the local directory. If the folder doesn't exist, it creates it
        before opening. If the registration is missing, an error message is displayed.

        Raises:
            QMessageBox: Displays an error dialog if the local directory is not registered.
        """
        local_dir: Path = cast("Path", GlobalRegistry.get_local_dir())
        if local_dir.exists():
            crash_logs_path: Path = local_dir / "Crash Logs"
            # Ensure the directory exists
            crash_logs_path.mkdir(exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(crash_logs_path))
        else:
            QMessageBox.critical(
                self,
                "Error",
                "Local directory is missing or not registered. Please restart the program.",
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Ok,
            )
