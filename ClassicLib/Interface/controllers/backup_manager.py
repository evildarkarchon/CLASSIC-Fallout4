"""Backup operations controller for CLASSIC interface.

This module provides the BackupManager class that handles backup, restore,
and removal operations for game files.

Example:
    >>> from ClassicLib.Interface.controllers.backup_manager import BackupManager
    >>> backup_mgr = BackupManager(context)
    >>> backup_mgr.check_existing_backups()

"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
)

from ClassicLib.Interface.widgets.UIHelpers import ENABLED_BUTTON_STYLE, create_separator
from ClassicLib.scanning.game import manage_game_files

if TYPE_CHECKING:
    from ClassicLib.Interface.shared.context import FeatureContext


class BackupManager:
    """Controller for game file backup operations.

    This controller manages backup-related operations including:
    - Checking for existing backups
    - Creating backup UI sections
    - Performing backup, restore, and remove operations

    The controller maintains references to restore buttons to enable/disable
    them based on backup availability.

    Attributes:
        _ctx: The FeatureContext providing access to shared dependencies.
        _restore_buttons: Dictionary mapping backup types to restore button references.

    Example:
        >>> manager = BackupManager(context)
        >>> manager.add_backup_section(layout, "XSE Files", "XSE")
        >>> manager.check_existing_backups()

    """

    # Valid backup types
    BACKUP_TYPES: tuple[str, ...] = ("XSE", "RESHADE", "VULKAN", "ENB")

    def __init__(self, context: FeatureContext) -> None:
        """Initialize the BackupManager.

        Args:
            context: FeatureContext providing access to main_window and ui_widgets.

        """
        self._ctx = context
        self._restore_buttons: dict[str, QPushButton] = {}

    def check_existing_backups(self) -> None:
        """Check for existing backup folders and enable restore buttons.

        Iterates through predefined backup category folders to determine
        if backups exist. For each existing backup with files, enables
        the corresponding restore button.
        """
        for category in self.BACKUP_TYPES:
            backup_path = Path(f"CLASSIC Backup/Game Files/Backup {category}")
            if backup_path.is_dir() and any(backup_path.iterdir()):
                restore_button = self._restore_buttons.get(category)
                if restore_button:
                    restore_button.setEnabled(True)
                    restore_button.setStyleSheet(ENABLED_BUTTON_STYLE)

    def add_backup_section(
        self,
        layout: QBoxLayout,
        title: str,
        backup_type: Literal["XSE", "RESHADE", "VULKAN", "ENB"],
    ) -> None:
        """Add a backup section with title and action buttons to a layout.

        Creates a section with:
        - A separator line
        - A title label
        - Backup, Restore, and Remove buttons

        The Restore button starts disabled and is enabled when backups exist.

        Args:
            layout: The layout to add the backup section to.
            title: The title text for the section.
            backup_type: The type of backup (XSE, RESHADE, VULKAN, or ENB).

        """
        separator = create_separator()
        separator.setMaximumWidth(480)

        # Center the separator
        separator_layout = QHBoxLayout()
        separator_layout.setContentsMargins(0, 12, 0, 6)
        separator_layout.addStretch(1)
        separator_layout.addWidget(separator)
        separator_layout.addStretch(1)
        layout.addLayout(separator_layout)

        # Title label
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # Button row - centered
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 6, 0, 0)
        buttons_layout.setSpacing(10)
        buttons_layout.addStretch(1)

        backup_button = QPushButton(f"BACKUP {backup_type}")
        restore_button = QPushButton(f"RESTORE {backup_type}")
        remove_button = QPushButton(f"REMOVE {backup_type}")

        # Store restore button reference
        self._restore_buttons[backup_type] = restore_button

        button_style_sheet = """
            QPushButton {
                color: white;
                background: rgba(60, 60, 60, 0.9);
                border-radius: 5px;
                border: 1px solid #5c5c5c;
                font-size: 12px;
                padding: 6px 12px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(40, 40, 40, 0.9);
            }
            QPushButton:disabled {
                color: grey;
                background-color: rgba(45, 45, 45, 0.75);
                border: 1px solid #444444;
            }
        """

        for button, action in [
            (backup_button, "BACKUP"),
            (restore_button, "RESTORE"),
            (remove_button, "REMOVE"),
        ]:
            # Use default arguments in lambda to capture current values
            button.clicked.connect(
                lambda _checked=False, b=backup_type, a=action: self.classic_files_manage(
                    f"Backup {b}",
                    a,  # type: ignore[arg-type]
                )
            )
            button.setStyleSheet(button_style_sheet)
            button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            button.setMaximumWidth(150)
            buttons_layout.addWidget(button)

        # Restore button starts disabled
        restore_button.setEnabled(False)

        buttons_layout.addStretch(1)
        layout.addLayout(buttons_layout)

    def classic_files_manage(
        self,
        selected_list: str,
        selected_mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP",
    ) -> None:
        """Manage game files based on the selected operation.

        Performs backup, restore, or removal operations on game files
        and updates the UI accordingly.

        Args:
            selected_list: The selected list in "Backup TYPE" format.
            selected_mode: The operation mode (BACKUP, RESTORE, or REMOVE).

        Raises:
            ValueError: If selected_list format is invalid.
            PermissionError: If file access is denied.

        """
        try:
            parts = self._validate_selected_list_format(selected_list)
            backup_type = parts[1]

            # Perform file operation
            manage_game_files(selected_list, selected_mode)

            # Update UI based on operation
            if selected_mode == "BACKUP":
                self._enable_restore_button_for_type(backup_type)

        except PermissionError:
            QMessageBox.critical(
                self._ctx.main_window,
                "Error",
                "Unable to access files from your game folder. Please run CLASSIC in admin mode to resolve this problem.",
                QMessageBox.StandardButton.NoButton,
                QMessageBox.StandardButton.NoButton,
            )
        except ValueError as e:
            QMessageBox.warning(
                self._ctx.main_window,
                "Warning",
                str(e),
                QMessageBox.StandardButton.NoButton,
                QMessageBox.StandardButton.NoButton,
            )

    @staticmethod
    def _validate_selected_list_format(selected_list: str) -> list[str]:
        """Validate the format of selected_list.

        Args:
            selected_list: String expected in "Backup TYPE" format.

        Returns:
            List of parts split from the input string.

        Raises:
            ValueError: If format doesn't match "Backup TYPE".

        """
        parts = selected_list.split()
        if len(parts) != 2 or parts[0] != "Backup":
            raise ValueError(f"Invalid format for selected_list: '{selected_list}'. Expected 'Backup TYPE'.")
        return parts

    def _enable_restore_button_for_type(self, backup_type: str) -> None:
        """Enable the restore button for a specific backup type.

        Args:
            backup_type: The backup type whose restore button to enable.

        """
        restore_button = self._restore_buttons.get(backup_type)
        if restore_button:
            restore_button.setEnabled(True)
            restore_button.setStyleSheet(ENABLED_BUTTON_STYLE)

    @staticmethod
    def open_backup_folder() -> None:
        """Open the CLASSIC Backup folder in the system file explorer.

        Creates the backup folder if it doesn't exist, then opens it
        using the platform-appropriate file manager.
        """
        backup_path = Path("CLASSIC Backup")
        backup_path.mkdir(parents=True, exist_ok=True)

        # Open folder in platform-appropriate file manager
        if sys.platform == "win32":
            os.startfile(backup_path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(backup_path)], check=False)
        else:
            subprocess.run(["xdg-open", str(backup_path)], check=False)
