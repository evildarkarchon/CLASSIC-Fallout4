from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton, QVBoxLayout

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

    def __init__(self, parent: QMainWindow | None = None, title: str = "", label: str = "", placeholder: str = "") -> None:
        """
        Initializes a dialog window for setting the INI files directory for a game. The
        dialog allows the user to either enter the directory path manually or select
        it using a file browser. It also contains an OK button to confirm the directory
        choice.

        Args:
            parent (QMainWindow | None): The parent window of the dialog. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle(title if title else "Set INI Files Directory")
        self.setFixedSize(700, 150)

        # Create layout and input field
        layout: QVBoxLayout = QVBoxLayout(self)
        self._game = GlobalRegistry.get_game()

        # Add a label
        info_label: QLabel = QLabel(
            label
            if label
            else f"Enter the path for the {self._game} INI files directory (Example: c:\\users\\<name>\\Documents\\My Games\\{self._game})",
            self,
        )
        layout.addWidget(info_label)

        inputlayout: QHBoxLayout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText(placeholder if placeholder else "Enter the INI directory or click 'Browse'...")
        inputlayout.addWidget(self.input_field)

        # Create the "Browse" button
        browse_button: QPushButton = QPushButton("Browse...", self)
        browse_button.clicked.connect(self.browse_directory)
        inputlayout.addWidget(browse_button)
        layout.addLayout(inputlayout)

        # Create standard OK button
        buttons: QDialogButtonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse_directory(self, caption: str = "") -> None:
        """
        Browse a directory using a dialog and update the input field with the selected path.

        This method opens a directory browser dialog. If the user selects a directory, the input
        field will be updated with the selected directory path.

        Args:
            caption: str
                An optional caption for the directory browser dialog. Defaults to an empty
                string, which will use the default caption "Select Directory for INI Files".

        Returns:
            None
        """
        # Open directory browser and update the input field
        manual_path: str = QFileDialog.getExistingDirectory(self, caption if caption else "Select Directory for INI Files")
        if manual_path:
            self.input_field.setText(manual_path)

    def get_path(self) -> str:
        """
        Returns the text from the input field.

        This method retrieves the current text from the input field and returns it as
        a string. It is useful for accessing user-provided input data.

        Returns:
            str: The text retrieved from the input field.
        """
        return self.input_field.text()
