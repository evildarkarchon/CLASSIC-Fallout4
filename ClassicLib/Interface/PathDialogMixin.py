import sys
from pathlib import Path

from PySide6.QtWidgets import QDialog, QMessageBox

from ClassicLib import GlobalRegistry
from ClassicLib.Interface.PathDialog import ManualPathDialog
from ClassicLib.MessageHandler import msg_info


class PathDialogMixin:
    def show_manual_docs_path_dialog(self) -> None:
        """
        Opens a dialog for selecting the manual documentation path.

        Displays a custom dialog that allows the user to browse for or manually enter
        the documentation path. If the user confirms their selection, the path is stored
        in the GlobalRegistry for access by other components.
        """
        # Create a dialog with appropriate title and descriptive label
        dialog: ManualPathDialog = ManualPathDialog(
            parent=self, title="Set INI Path", label=f"Select the location of your {GlobalRegistry.get_game()} INI files"
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
            parent=self, title="Set Game Installation Path", label=f"Select the installation directory for {GlobalRegistry.get_game()}"
        )

        # Process the dialog result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            game_path: str = dialog.get_path()
            # Store the path in the GlobalRegistry for access by other components
            GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, game_path)


def show_game_path_dialog_static() -> Path | None:
    """
    Shows a dialog for selecting the game installation path without requiring an instance.
    Allows the user to cancel, which will exit the application.

    Returns:
        Path to the selected valid game directory if successful, None if user cancels
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
