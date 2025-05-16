from PySide6.QtWidgets import QDialogButtonBox, QPushButton, QHBoxLayout, QLineEdit, QLabel, QVBoxLayout, QMainWindow, \
    QDialog, QFileDialog

from ClassicLib import GlobalRegistry


class ManualPathDialog(QDialog):
    """
    A dialog window for setting the directory path to INI files for a game.

    This class provides functionality to manually enter or browse for the directory where
    INI files are stored. The dialog is equipped with an input field, a "Browse" button for
    directory selection via a file browser, and an OK button to confirm the user’s choice.
    Primarily, this dialog is intended for scenarios where users need to configure paths
    manually in a GUI application.

    Attributes:
        input_field (QLineEdit): Input field where the user can manually enter the INI files directory path.
    """  # noqa: RUF002

    def __init__(self, parent: QMainWindow | None = None, title: str = "", label: str = "",
                 placeholder: str = "") -> None:
        """
        Initializes a dialog window for setting the INI files directory for a game. The
        dialog allows the user to either enter the directory path manually or select
        it using a file browser. It also contains an OK button to confirm the directory
        choice.

        Args:
            parent (QMainWindow | None): The parent window of the dialog. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle("Set INI Files Directory" if not title else title)
        self.setFixedSize(700, 150)

        # Create layout and input field
        layout = QVBoxLayout(self)
        self._game = GlobalRegistry.get_game()

        # Add a label
        label = QLabel(
            f"Enter the path for the {self._game} INI files directory (Example: c:\\users\\<name>\\Documents\\My Games\\{self._game})" if not label else label,
            self)
        layout.addWidget(label)

        inputlayout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText(
            "Enter the INI directory or click 'Browse'..." if not placeholder else placeholder)
        inputlayout.addWidget(self.input_field)

        # Create the "Browse" button
        browse_button = QPushButton("Browse...", self)
        browse_button.clicked.connect(self.browse_directory)
        inputlayout.addWidget(browse_button)
        layout.addLayout(inputlayout)

        # Create standard OK button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse_directory(self, caption: str = "") -> None:
        """
        Opens a directory browser dialog to allow the user to select a directory and updates
        the input field with the selected directory's path.

        Raises:
            No specific exceptions are explicitly raised in this implementation; however, standard
            QFileDialog operations may fail under certain conditions such as lack of permissions
            or UI-related issues.
        """
        # Open directory browser and update the input field
        manual_path = QFileDialog.getExistingDirectory(self,
                                                       "Select Directory for INI Files" if not caption else caption)
        if manual_path:
            self.input_field.setText(manual_path)

    def get_path(self) -> str:
        """
        Retrieves the text content of the input field.

        This method is used to access the current text entered in the input field
        of the instance. It retrieves the value as a string and returns it to the
        caller. The function does not modify the text or the input field state.

        Returns:
            str: The content of the input field as a string.
        """
        return self.input_field.text()