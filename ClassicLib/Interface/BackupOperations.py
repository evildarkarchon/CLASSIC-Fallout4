"""
Backup operations functionality for the CLASSIC interface.

This module contains a mixin class that handles backup, restore, and removal
operations for game files.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
)

from CLASSIC_ScanGame import game_files_manage
from ClassicLib.Interface.UIHelpers import ENABLED_BUTTON_STYLE, create_separator

if TYPE_CHECKING:
    from typing import Any


class BackupOperationsMixin:
    """
    Mixin class providing backup operations functionality for the MainWindow.

    This class handles backup, restore, and removal operations for various
    game file categories (XSE, RESHADE, VULKAN, ENB).
    """

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
                    restore_button.setStyleSheet(ENABLED_BUTTON_STYLE)

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
        Enables the restore button for a specific backup type category.

        Args:
            backup_type (str): The type of backup category for which to enable
                the restore button (e.g., "XSE", "RESHADE", "VULKAN", "ENB").
        """
        restore_button: Any | None = getattr(self, f"RestoreButton_{backup_type}", None)
        if restore_button:
            restore_button.setEnabled(True)
            restore_button.setStyleSheet(ENABLED_BUTTON_STYLE)
