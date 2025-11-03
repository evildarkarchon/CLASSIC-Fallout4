"""
Module facilitating backup and management of game files through a graphical interface.

This module provides backup, restore, and removal functionality for predefined game file
categories. It integrates with a graphical interface using the PySide6 framework to manage
UI elements and user interactions.
"""

from __future__ import annotations

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

from ClassicLib.Interface.UIHelpers import ENABLED_BUTTON_STYLE, create_separator
from ClassicLib.ScanGame import manage_game_files

if TYPE_CHECKING:
    from typing import Any


class BackupOperationsMixin:
    """
    Mixin class providing utility methods and UI components for managing backups.

    This mixin contains methods for managing backup-related operations including checking
    the existence of backups, adding backup sections to UI layouts, and performing specific
    backup actions such as backup, restore, and removal. The class also provides mechanisms
    to update UI components based on the backup state.
    """

    def check_existing_backups(self) -> None:
        """
        Checks for existing backup folders and updates corresponding restore buttons.

        This method iterates through predefined backup category folders to determine if backups
        exist for each category. It examines the folder's existence and checks if the folder
        contains any files or subdirectories. If backups are found for a category, the associated
        restore button is enabled and styled with the defined enabled button style.

        Returns:
            None
        """
        for category in ["XSE", "RESHADE", "VULKAN", "ENB"]:
            backup_path: Path = Path(f"CLASSIC Backup/Game Files/Backup {category}")
            if backup_path.is_dir() and any(backup_path.iterdir()):
                restore_button: Any | None = getattr(self, f"RestoreButton_{category}", None)
                if restore_button:
                    restore_button.setEnabled(True)
                    restore_button.setStyleSheet(ENABLED_BUTTON_STYLE)

    def add_backup_section(self, layout: QBoxLayout, title: str, backup_type: Literal["XSE", "RESHADE", "VULKAN", "ENB"]) -> None:
        """
        Adds a backup section to the provided layout. This section includes a title label and buttons for
        backup, restore, and remove actions, styled consistently for a user interface. Each button is
        connected to a click event handler that triggers the managed file operation for the given
        backup type.

        Args:
            layout (QBoxLayout): The layout to which the backup section will be added.
            title (str): The title text displayed in the backup section.
            backup_type (Literal["XSE", "RESHADE", "VULKAN", "ENB"]): The type of backup to configure
                the section for. This determines the labeling of buttons and their associated actions.
        """
        layout.addWidget(create_separator())

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

    @staticmethod
    def _validate_selected_list_format(selected_list: str) -> list[str]:
        """
        Validates the format of the selected_list to ensure it adheres to the expected structure of 'Backup TYPE'.

        This method checks if the input string matches the required format. It splits the string into parts and verifies
        that the first part is "Backup" and that there are exactly two parts. If the format is invalid, it raises a
        ValueError.

        Args:
            selected_list (str): The input string to validate, expected in the format 'Backup TYPE'.

        Returns:
            list[str]: A list containing the parts of the validated input string.

        Raises:
            ValueError: If the format of the selected_list does not match the required structure.
        """
        parts: list[str] = selected_list.split()
        if len(parts) != 2 or parts[0] != "Backup":
            raise ValueError(f"Invalid format for selected_list: '{selected_list}'. Expected 'Backup TYPE'.")
        return parts

    def classic_files_manage(self, selected_list: str, selected_mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
        """
        Manages game files based on the selected list and operation mode. This function handles file operations
        like backup, restore, or removal of game files and updates the UI accordingly. It also validates
        the format of the selected list for the operation and provides error messages in case of failures.

        Args:
            selected_list (str): The selected list in a specific format which determines the game files
                to manage.
            selected_mode (Literal["BACKUP", "RESTORE", "REMOVE"], optional): The operation mode specifying
                the action to be performed on the files. Defaults to "BACKUP".

        Raises:
            PermissionError: Raised if the application doesn't have the required permissions to access
                the game folder.
            ValueError: Raised if the selected list format is invalid.
        """
        # noinspection PyShadowingNames
        try:
            # Extract backup type from the selected list (format: "Backup TYPE")
            parts: list[str] = self._validate_selected_list_format(selected_list)

            backup_type: str = parts[1]
            # Perform file operation
            manage_game_files(selected_list, selected_mode)

            # Update UI based on operation performed
            if selected_mode == "BACKUP":
                self._enable_restore_button_for_type(backup_type)

        except PermissionError:
            QMessageBox.critical(
                self,  # type: ignore[arg-type]  # Mixin used in QWidget subclass
                "Error",
                "Unable to access files from your game folder. Please run CLASSIC in admin mode to resolve this problem.",
                QMessageBox.StandardButton.NoButton,
                QMessageBox.StandardButton.NoButton,
            )
        except ValueError as e:
            QMessageBox.warning(
                self,  # type: ignore[arg-type]  # Mixin used in QWidget subclass
                "Warning",
                str(e),
                QMessageBox.StandardButton.NoButton,
                QMessageBox.StandardButton.NoButton,
            )

    def _enable_restore_button_for_type(self, backup_type: str) -> None:
        """
        Enables the restore button for a specific backup type, if the corresponding restore
        button for the provided backup type exists. This method also applies the enabled
        button style to the restore button.

        Args:
            backup_type (str): The type of backup for which the restore button should be
                enabled.
        """
        restore_button: Any | None = getattr(self, f"RestoreButton_{backup_type}", None)
        if restore_button:
            restore_button.setEnabled(True)
            restore_button.setStyleSheet(ENABLED_BUTTON_STYLE)
