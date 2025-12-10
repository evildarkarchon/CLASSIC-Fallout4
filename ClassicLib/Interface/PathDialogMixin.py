"""
Module providing dialog functionality for selecting paths in a user-friendly way.

This module includes mixin classes and standalone functions to integrate dialogs
for selecting paths such as game installation directories or manual documentation
directories. These paths can be stored and managed globally for further access
throughout the application.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QDialog, QMessageBox

from ClassicLib import GlobalRegistry
from ClassicLib.Interface.PathDialog import ManualPathDialog
from ClassicLib.MessageHandler import msg_info


class PathDialogMixin:
    """
    Provides mixin methods for showing custom file path selection dialogs.

    This class is used to add functionality for displaying dialogs that allow
    users to select file paths, such as manual documentation paths or game
    installation directories. The selected paths can then be registered in a
    global registry for further use.

    Methods defined in this mixin should be invoked from a parent class and are
    designed to handle both dialog creation and result processing.
    """

    def show_manual_docs_path_dialog(self) -> None:
        """
        Opens a dialog for selecting the manual documentation path.

        Displays a custom dialog that allows the user to browse for or manually enter
        the documentation path. If the user confirms their selection, the path is stored
        in the GlobalRegistry for access by other components.
        """
        # Create a dialog with appropriate title and descriptive label
        dialog: ManualPathDialog = ManualPathDialog(
            parent=self, title="Set INI Path", label=f"Select the location of your {GlobalRegistry.get_game()} INI files" # pyright: ignore[reportArgumentType]
        )

        # Process the dialog result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            manual_path: str = dialog.get_path()
            # Store the path in the GlobalRegistry for access by other components
            GlobalRegistry.register(GlobalRegistry.Keys.DOCS_PATH, manual_path)

    def show_game_path_dialog(self) -> None:
        """
        Opens a dialog for selecting the game installation path.

        Displays a custom dialog that allows the user to browse for or manually enter
        the game installation directory. If the user confirms their selection, the path
        is stored in the GlobalRegistry for access by other components.
        """
        # Create a dialog with appropriate title and descriptive label
        dialog: ManualPathDialog = ManualPathDialog(
            parent=self, title="Set Game Installation Path", label=f"Select the installation directory for {GlobalRegistry.get_game()}" # pyright: ignore[reportArgumentType]
        )

        # Process the dialog result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            game_path: str = dialog.get_path()
            # Store the path in the GlobalRegistry for access by other components
            GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)


def show_game_path_dialog_static() -> Path | None:
    """
    Displays a modal dialog to let the user select the installation path of the game.

    This function repeatedly prompts the user to select a valid installation directory for the game
    until a valid path is provided or the user chooses to exit the application. It validates whether
    the directory selected by the user contains the correct game executable. If an invalid directory
    is chosen, an error is shown, and the dialog is re-displayed. If the user cancels and opts to
    exit, the application exits immediately.

    Returns:
        Path | None: The validated path to the game's installation directory, or None in the case of an
        unrecoverable error or user cancellation followed by exiting the application.
    """
    from ClassicLib.Interface.PathDialog import ManualPathDialog

    exe_name: str = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"
    game_name: str = GlobalRegistry.get_game()
    # Create a dialog with appropriate title and descriptive label
    dialog: ManualPathDialog = ManualPathDialog(
        parent=None,  # No parent since this is static
        title="Set Game Installation Path",
        label=f"Select the installation directory for {game_name}",
    )
    while True:
        # Process the dialog result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            game_path: Path = Path(dialog.get_path())

            # Validate that the directory contains the game executable
            if game_path and game_path.is_dir() and game_path.joinpath(exe_name).is_file():
                return game_path
            # Show error and continue loop to try again
            QMessageBox.critical(
                None,  # pyrefly: ignore
                "Invalid Game Directory",
                f"❌ ERROR: No {exe_name} file found in '{game_path}'!\n\nPlease select the correct game directory.",
            )
        else:
            # User cancelled - show confirmation dialog
            reply: QMessageBox.StandardButton = QMessageBox.question(
                None,  # pyrefly: ignore
                "Exit Application?",
                "A valid game path is required to continue.\nDo you want to exit the application?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Exit the application
                msg_info("User chose to exit the application.")
                sys.exit(0)  # Exit with success code
            # If No, the loop continues and shows the dialog again
