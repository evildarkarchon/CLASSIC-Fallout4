"""
Folder management functionality for the CLASSIC interface.

This module contains a mixin class that handles folder selection and validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

if TYPE_CHECKING:
    from PySide6.QtWidgets import QLineEdit

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.ScanLog.Util import is_valid_custom_scan_path
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class FolderManagementMixin:
    """
    Mixin providing folder management utilities.

    This mixin is designed to handle folder-related operations such as selecting
    folders, validating folder paths, and initializing folder paths from settings.
    It also provides methods for opening specific system folders such as backup
    and crash logs directories. These utilities are intended to interact with
    application-wide settings and enhance folder management functionality within
    the application.

    Attributes:
        scan_folder_edit (QLineEdit | None): Input field reference for the custom
            scan folder path used in the user interface.
        mods_folder_edit (QLineEdit | None): Input field reference for the mods
            folder path used in the user interface.
    """

    if TYPE_CHECKING:
        # Attributes expected from other mixins (TabSetupMixin)
        scan_folder_edit: QLineEdit | None
        mods_folder_edit: QLineEdit | None

    def select_folder_scan(self) -> None:
        """
        Prompts the user to select a folder for custom scan functionality, validates the selected folder,
        and updates the application settings accordingly. If the folder is invalid, a warning dialog is
        shown, and the user can retry until a valid folder is chosen or the dialog is canceled.

        Raises:
            Warning: If the selected folder is not valid for a custom scan path.
        """
        while True:
            # noinspection PyTypeChecker
            folder: str = QFileDialog.getExistingDirectory(self, "Select Custom Scan Folder") # pyright: ignore[reportArgumentType]
            if not folder:  # User clicked cancel
                break

            if is_valid_custom_scan_path(folder):
                # Valid path, update and save
                if self.scan_folder_edit is not None:
                    self.scan_folder_edit.setText(folder)
                yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", folder)
                break
            # Invalid path, show warning and continue loop
            # noinspection PyTypeChecker
            QMessageBox.warning(
                self, # pyright: ignore[reportArgumentType]
                "Invalid Custom Scan Path",
                "The selected directory cannot be used as a custom scan path.\n\n"
                "The 'Crash Logs' folder and its subfolders are managed by CLASSIC "
                "and cannot be set as custom scan directories.\n\n"
                "Please select a different directory.",
            )

    def validate_scan_folder_text(self) -> None:
        """
        Validates and processes the user-provided scan folder path entered in a text field.
        Handles scenarios like empty input, non-existent paths, restricted paths, and valid paths,
        updating the application settings and notifying the user accordingly.

        Raises:
            Warning: A QMessageBox warning is raised if the provided path is invalid
            or restricted, suggesting corrective actions to the user.
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
            # noinspection PyTypeChecker
            QMessageBox.warning(
                self, # pyright: ignore[reportArgumentType]
                "Invalid Path",
                f"The path '{folder_text}' does not exist or is not a directory.\n\nThe custom scan path has been cleared.",
            )
            self.scan_folder_edit.clear()
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")
            return

        # Check if path is restricted
        if not is_valid_custom_scan_path(folder_text):
            # noinspection PyTypeChecker
            QMessageBox.warning(
                self, # pyright: ignore[reportArgumentType]
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
        Selects a folder for staging mods and updates the relevant settings.

        This function allows the user to select a directory using a dialog for staging mods, updates the
        text field with the chosen directory, and saves the folder path to a YAML settings file.

        Raises:
            OSError: If there is an issue accessing the selected directory.
        """
        # noinspection PyTypeChecker
        folder: str = QFileDialog.getExistingDirectory(self, "Select Staging Mods Folder") # pyright: ignore[reportArgumentType]
        if folder:
            if self.mods_folder_edit is not None:
                self.mods_folder_edit.setText(folder)
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", folder)

    def initialize_folder_paths(self) -> None:
        """
        Initializes folder paths for scanning and mods based on user settings.

        This method retrieves folder paths for scanning and mods from user-defined
        settings and applies them to corresponding UI elements if they exist.

        Raises:
            None
        """
        scan_folder: str | None = classic_settings(str, "SCAN Custom Path")
        mods_folder: str | None = classic_settings(str, "MODS Folder Path")

        if scan_folder and self.scan_folder_edit is not None:
            self.scan_folder_edit.setText(scan_folder)
        if mods_folder and self.mods_folder_edit is not None:
            self.mods_folder_edit.setText(mods_folder)

    def open_settings(self) -> None:
        """
        Opens the settings dialog and applies changes if accepted.

        This method creates an instance of `SettingsDialog` and displays it to
        the user. If the user accepts the changes in the dialog, immediate
        setting changes are applied using the `apply_settings_changes` method.

        Raises:
            Any errors from the creation or execution of the `SettingsDialog`
            instance.

        """
        from ClassicLib.Interface.Settings.dialog import SettingsDialog

        # noinspection PyTypeChecker
        dialog = SettingsDialog(self) # pyright: ignore[reportArgumentType]
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply any settings that need immediate effect
            self.apply_settings_changes()

    def apply_settings_changes(self) -> None:
        """
        Apply settings that affect the UI immediately.

        This method is called after the settings dialog is accepted to apply
        any changes that need to take effect immediately in the current session.
        """
        # Currently no immediate UI changes needed
        # This method is here for future use when settings might affect the UI

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
            # noinspection PyTypeChecker
            QMessageBox.critical(
                self, # pyright: ignore[reportArgumentType]
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
            # noinspection PyTypeChecker
            QMessageBox.critical(
                self, # pyright: ignore[reportArgumentType]
                "Error",
                "Local directory is missing or not registered. Please restart the program.",
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Ok,
            )
