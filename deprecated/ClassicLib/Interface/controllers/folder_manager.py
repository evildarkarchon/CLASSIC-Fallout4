"""Folder management controller for CLASSIC interface.

This module provides the FolderManager class that handles folder selection,
validation, and opening folder locations in the file explorer.

Example:
    >>> from ClassicLib.Interface.controllers.folder_manager import FolderManager
    >>> folder_mgr = FolderManager(context)
    >>> folder_mgr.select_folder_scan()

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from ClassicLib.core.constants import YAML
from ClassicLib.io.yaml import classic_settings, yaml_settings
from ClassicLib.scanning.logs.util_legacy import is_valid_custom_scan_path

if TYPE_CHECKING:
    from ClassicLib.Interface.shared.context import FeatureContext


class FolderManager:
    """Controller for folder management functionality.

    This controller handles folder-related operations including:
    - Selecting custom scan folders
    - Selecting mods staging folders
    - Validating folder paths
    - Opening backup and crash logs folders
    - Managing settings dialog

    All folder paths are persisted to YAML settings for future sessions.

    Attributes:
        _ctx: The FeatureContext providing access to shared dependencies.

    Example:
        >>> manager = FolderManager(context)
        >>> manager.select_folder_scan()  # Opens folder picker
        >>> manager.initialize_folder_paths()  # Load saved paths

    """

    def __init__(self, context: FeatureContext) -> None:
        """Initialize the FolderManager.

        Args:
            context: FeatureContext providing access to main_window and ui_widgets.

        """
        self._ctx = context

    def select_folder_scan(self) -> None:
        """Prompt the user to select a custom scan folder.

        Shows a folder selection dialog and validates the selected path.
        If the folder is invalid (e.g., within Crash Logs), shows a warning
        and allows retry. Valid paths are saved to settings.
        """
        while True:
            folder: str = QFileDialog.getExistingDirectory(
                self._ctx.main_window,
                "Select Custom Scan Folder",
            )
            if not folder:  # User clicked cancel
                break

            if is_valid_custom_scan_path(folder):
                # Valid path, update UI and save
                if self._ctx.ui_widgets.scan_folder_edit is not None:
                    self._ctx.ui_widgets.scan_folder_edit.setText(folder)
                yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", folder)
                break

            # Invalid path, show warning and continue loop
            QMessageBox.warning(
                self._ctx.main_window,
                "Invalid Custom Scan Path",
                "The selected directory cannot be used as a custom scan path.\n\n"
                "The 'Crash Logs' folder and its subfolders are managed by CLASSIC "
                "and cannot be set as custom scan directories.\n\n"
                "Please select a different directory.",
            )

    def validate_scan_folder_text(self) -> None:
        """Validate and process user-entered scan folder path.

        Called when the user finishes editing the scan folder text field.
        Handles empty input, non-existent paths, restricted paths, and
        valid paths appropriately.
        """
        scan_folder_edit = self._ctx.ui_widgets.scan_folder_edit
        if scan_folder_edit is None:
            return

        folder_text = scan_folder_edit.text().strip()

        # If empty, clear the setting
        if not folder_text:
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", " ")
            return

        # Check if path exists
        path_obj = Path(folder_text)
        if not path_obj.exists() or not path_obj.is_dir():
            QMessageBox.warning(
                self._ctx.main_window,
                "Invalid Path",
                f"The path '{folder_text}' does not exist or is not a directory.\n\nThe custom scan path has been cleared.",
            )
            scan_folder_edit.clear()
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")
            return

        # Check if path is restricted
        if not is_valid_custom_scan_path(folder_text):
            QMessageBox.warning(
                self._ctx.main_window,
                "Invalid Custom Scan Path",
                "The entered directory cannot be used as a custom scan path.\n\n"
                "The 'Crash Logs' folder and its subfolders are managed by CLASSIC "
                "and cannot be set as custom scan directories.\n\n"
                "The custom scan path has been cleared.",
            )
            scan_folder_edit.clear()
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")
            return

        # Valid path, save it
        yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", str(path_obj.resolve()))

    def select_folder_mods(self) -> None:
        """Prompt the user to select a mods staging folder.

        Shows a folder selection dialog. Selected path is saved to settings
        and displayed in the UI.
        """
        folder: str = QFileDialog.getExistingDirectory(
            self._ctx.main_window,
            "Select Staging Mods Folder",
        )
        if folder:
            if self._ctx.ui_widgets.mods_folder_edit is not None:
                self._ctx.ui_widgets.mods_folder_edit.setText(folder)
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", folder)

    def initialize_folder_paths(self) -> None:
        """Initialize folder path UI fields from saved settings.

        Loads previously saved scan and mods folder paths from settings
        and populates the corresponding UI text fields.
        """
        scan_folder: str | None = classic_settings(str, "SCAN Custom Path")
        mods_folder: str | None = classic_settings(str, "MODS Folder Path")

        if scan_folder and self._ctx.ui_widgets.scan_folder_edit is not None:
            self._ctx.ui_widgets.scan_folder_edit.setText(scan_folder)
        if mods_folder and self._ctx.ui_widgets.mods_folder_edit is not None:
            self._ctx.ui_widgets.mods_folder_edit.setText(mods_folder)

    def open_settings(self) -> None:
        """Open the settings dialog.

        Displays the settings dialog and applies any changes if the user
        accepts the dialog.
        """
        from ClassicLib.Interface.settings.dialog import SettingsDialog

        dialog = SettingsDialog(self._ctx.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_settings_changes()

    def apply_settings_changes(self) -> None:
        """Apply settings that affect the UI immediately.

        Called after the settings dialog is accepted to apply any changes
        that need to take effect immediately in the current session.
        """
        # Currently no immediate UI changes needed
        # This method is here for future use when settings might affect the UI

    def open_backup_folder(self) -> None:
        """Open the backup folder in the file explorer.

        Opens the CLASSIC Backup/Game Files folder if it exists.
        Shows an error dialog if the folder is not found.
        """
        local_dir: Path | str | None = self._ctx.local_dir
        if local_dir and (
            (isinstance(local_dir, Path) and local_dir.exists()) or (isinstance(local_dir, str) and Path(local_dir).exists())
        ):
            backup_path: Path = Path(local_dir) / "CLASSIC Backup/Game Files"
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(backup_path)))
        else:
            QMessageBox.critical(
                self._ctx.main_window,
                "Error",
                "Backup folder is missing or not registered. Please restart the program.",
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Ok,
            )

    def open_crash_logs_folder(self) -> None:
        """Open the Crash Logs folder in the file explorer.

        Opens the Crash Logs folder, creating it if it doesn't exist.
        Shows an error dialog if the local directory is not configured.
        """
        local_dir: Path | str | None = self._ctx.local_dir
        if local_dir and (
            (isinstance(local_dir, Path) and local_dir.exists()) or (isinstance(local_dir, str) and Path(local_dir).exists())
        ):
            crash_logs_path: Path = Path(local_dir) / "Crash Logs"
            crash_logs_path.mkdir(exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(crash_logs_path)))
        else:
            QMessageBox.critical(
                self._ctx.main_window,
                "Error",
                "Local directory is missing or not registered. Please restart the program.",
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Ok,
            )
