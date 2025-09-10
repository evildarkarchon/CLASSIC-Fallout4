"""
Path management functionality for CLASSIC settings dialog.

This module handles INI folder path detection, browsing, and resetting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QLineEdit

from ClassicLib.Constants import YAML
from ClassicLib.MessageHandler import msg_error, msg_success, msg_warning
from ClassicLib.YamlSettingsCache import yaml_settings

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class PathManager:
    """Manages path-related settings and operations."""

    def __init__(self, parent: QWidget, yaml_store: YAML = YAML.Settings) -> None:
        """
        Initialize the path manager.

        Args:
            parent: Parent widget for dialogs
            yaml_store: YAML store to use for settings
        """
        self.parent = parent
        self.yaml_store = yaml_store
        self.ini_folder_input: QLineEdit | None = None

    def set_ini_folder_input(self, input_widget: QLineEdit) -> None:
        """Set the INI folder input widget reference."""
        self.ini_folder_input = input_widget

    def browse_ini_folder(self) -> None:
        """Open a folder browser dialog for selecting the INI folder."""
        from ClassicLib import GlobalRegistry

        if not self.ini_folder_input:
            return

        try:
            game = GlobalRegistry.get_game()
        except (TypeError, ValueError, AttributeError):
            game = "Game"

        folder = QFileDialog.getExistingDirectory(
            self.parent,
            f"Select INI Folder for {game}",
            self.ini_folder_input.text() or "",
            QFileDialog.Option.ShowDirsOnly,
        )

        if folder:
            self.ini_folder_input.setText(folder)

    def reset_ini_folder(self) -> None:
        """Reset the INI folder path to auto-detected value."""
        from ClassicLib import GlobalRegistry
        from ClassicLib.Logger import logger

        try:
            # Clear the INI Folder Path setting in CLASSIC Settings.yaml
            yaml_settings(str, self.yaml_store, "CLASSIC_Settings.INI Folder Path", "")
            logger.info("Cleared INI Folder Path setting for autodetection")

            # Clear the Root_Folder_Docs in Game_Local YAML to trigger fresh detection
            vr_suffix = GlobalRegistry.get_vr()
            root_docs_key = f"Game{vr_suffix}_Info.Root_Folder_Docs"
            yaml_settings(str, YAML.Game_Local, root_docs_key, "")
            logger.info("Cleared Root_Folder_Docs for fresh autodetection")

            # Run the autodetection
            self.autodetect_ini_folder()

        except (ImportError, TypeError, ValueError, OSError) as e:
            logger.error(f"Failed to reset INI folder path: {e}")
            # Show error to user
            msg_error(f"Failed to reset INI folder path: {e!s}\n\nPlease try again or set the path manually.")

    def autodetect_ini_folder(self) -> None:
        """Trigger autodetection of the INI folder path and update the UI."""
        from ClassicLib import GlobalRegistry
        from ClassicLib.DocsPath import docs_path_find
        from ClassicLib.Logger import logger

        if not self.ini_folder_input:
            return

        try:
            # Run the autodetection logic (same as first run)
            docs_path_find(is_gui_mode=True)
            logger.info("Ran INI folder autodetection")

            # Retrieve the newly detected path from Game_Local YAML
            vr_suffix = GlobalRegistry.get_vr()
            root_docs_key = f"Game{vr_suffix}_Info.Root_Folder_Docs"
            detected_path = yaml_settings(str, YAML.Game_Local, root_docs_key)

            # Update the UI with the detected path
            if detected_path:
                self.ini_folder_input.setText(detected_path)
                logger.info(f"Updated INI folder path to: {detected_path}")
                # Show success message to user
                msg_success(f"INI folder path reset successfully!\n\nDetected path: {detected_path}")
            else:
                # If autodetection failed, clear the input field
                self.ini_folder_input.clear()
                logger.warning("Autodetection did not find a valid INI folder path")
                # Show warning to user
                msg_warning(
                    "Could not auto-detect INI folder path.\n\n"
                    "Please use the Browse button to manually select your game's INI folder.\n"
                    "This is typically located in Documents/My Games/[Game Name]"
                )

        except (ImportError, TypeError, ValueError, OSError) as e:
            logger.error(f"Failed to autodetect INI folder path: {e}")
            # Show error to user
            msg_error(f"Failed to auto-detect INI folder path: {e!s}\n\nPlease set the path manually using the Browse button.")
