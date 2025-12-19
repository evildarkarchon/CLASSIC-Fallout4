"""Path dialog controller for CLASSIC interface.

This module provides the PathDialogController class that handles path selection
dialogs for game installation and documentation directories.

Example:
    >>> from ClassicLib.Interface.controllers.path_dialog import PathDialogController
    >>> path_ctrl = PathDialogController(context)
    >>> path_ctrl.show_game_path_dialog()

"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog, QMessageBox

from ClassicLib import GlobalRegistry
from ClassicLib.Interface.PathDialog import ManualPathDialog
from ClassicLib.MessageHandler import msg_info

if TYPE_CHECKING:
    from ClassicLib.Interface.context import FeatureContext


class PathDialogController:
    """Controller for path selection dialog functionality.

    This controller handles displaying dialogs that allow users to select
    file paths for game installation directories and documentation locations.
    Selected paths are registered in GlobalRegistry for application-wide access.

    Attributes:
        _ctx: The FeatureContext providing access to shared dependencies.

    Example:
        >>> controller = PathDialogController(context)
        >>> controller.show_game_path_dialog()  # Shows game path selection
        >>> controller.show_manual_docs_path_dialog()  # Shows docs path selection

    """

    def __init__(self, context: FeatureContext) -> None:
        """Initialize the PathDialogController.

        Args:
            context: FeatureContext providing access to main_window and signal_hub.

        """
        self._ctx = context

    def show_manual_docs_path_dialog(self) -> None:
        """Open a dialog for selecting the manual documentation path.

        Displays a custom dialog that allows the user to browse for or manually
        enter the documentation path. If the user confirms their selection, the
        path is stored in GlobalRegistry for access by other components.
        """
        dialog = ManualPathDialog(
            parent=self._ctx.main_window,
            title="Set INI Path",
            label=f"Select the location of your {GlobalRegistry.get_game()} INI files",
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            manual_path: str = dialog.get_path()
            GlobalRegistry.register(GlobalRegistry.Keys.DOCS_PATH, manual_path)

    def show_game_path_dialog(self) -> None:
        """Open a dialog for selecting the game installation path.

        Displays a custom dialog that allows the user to browse for or manually
        enter the game installation directory. If the user confirms their selection,
        the path is stored in GlobalRegistry for access by other components.
        """
        dialog = ManualPathDialog(
            parent=self._ctx.main_window,
            title="Set Game Installation Path",
            label=f"Select the installation directory for {GlobalRegistry.get_game()}",
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            game_path: str = dialog.get_path()
            GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)


def show_game_path_dialog_static() -> Path | None:
    """Display a modal dialog to let the user select the game installation path.

    This standalone function repeatedly prompts the user to select a valid
    installation directory for the game until a valid path is provided or
    the user chooses to exit the application. It validates whether the
    directory contains the correct game executable.

    This function is used during initial application setup before the
    MainWindow and FeatureContext are created.

    Returns:
        Path to the validated game installation directory, or None if
        the user exits the application.

    Note:
        This function may call sys.exit(0) if the user chooses to exit
        after canceling the dialog.

    """
    exe_name: str = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"
    game_name: str = GlobalRegistry.get_game()

    dialog = ManualPathDialog(
        parent=None,
        title="Set Game Installation Path",
        label=f"Select the installation directory for {game_name}",
    )

    while True:
        if dialog.exec() == QDialog.DialogCode.Accepted:
            game_path = Path(dialog.get_path())

            # Validate that the directory contains the game executable
            if game_path and game_path.is_dir() and game_path.joinpath(exe_name).is_file():
                return game_path

            # Show error and continue loop to try again
            QMessageBox.critical(
                None,
                "Invalid Game Directory",
                f"No {exe_name} file found in '{game_path}'!\n\nPlease select the correct game directory.",
            )
        else:
            # User cancelled - show confirmation dialog
            reply = QMessageBox.question(
                None,
                "Exit Application?",
                "A valid game path is required to continue.\nDo you want to exit the application?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                msg_info("User chose to exit the application.")
                sys.exit(0)
            # If No, the loop continues and shows the dialog again
