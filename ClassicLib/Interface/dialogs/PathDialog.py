"""Define a dialog for manually setting the directory path to INI files.

This module provides the `ManualPathDialog` class, which allows users to input or
select a directory path for INI files associated with a game. It includes features
such as a text field for manual input, a "Browse" button for directory selection
via a file dialog, and an OK button to confirm the choice.

Primarily, the `ManualPathDialog` class is designed for use in GUI applications
where users may need to configure paths manually.
"""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton, QVBoxLayout

from ClassicLib.core.registry import GlobalRegistry


class ManualPathDialog(QDialog):
    """A dialog window for setting the directory path to INI files for a game.

    This class provides functionality to manually enter or browse for the directory where
    INI files are stored. The dialog is equipped with an input field, a "Browse" button for
    directory selection via a file browser, and an OK button to confirm the user’s choice.
    Primarily, this dialog is intended for scenarios where users need to configure paths
    manually in a GUI application.

    Attributes:
        input_field (QLineEdit): Input field where the user can manually enter the INI files directory path.

    """  # noqa: RUF002

    def __init__(self, parent: QMainWindow | None = None, title: str = "", label: str = "", placeholder: str = "") -> None:
        """Initialize a dialog for selecting an INI files directory. This dialog provides a text
        input field where the user can manually enter a directory path or use a "Browse" button
        to select it. The dialog also includes an OK button to confirm the selection.

        Args:
            parent (QMainWindow | None): The parent window of the dialog.
            title (str): The title of the dialog window. Defaults to an empty string,
                which sets a predefined title "Set INI Files Directory".
            label (str): The label text displayed in the dialog. Defaults to an empty string,
                which sets a predefined instruction based on the current game in the global registry.
            placeholder (str): The placeholder text for the input field. Defaults to an empty
                string, which sets a predefined placeholder text.

        """
        super().__init__(parent)
        self.setWindowTitle(title or "Set INI Files Directory")
        self.setFixedSize(700, 150)

        # Create layout and input field
        layout: QVBoxLayout = QVBoxLayout(self)
        self._game = GlobalRegistry.get_game()

        # Add a label
        info_label: QLabel = QLabel(
            label
            or f"Enter the path for the {self._game} INI files directory (Example: c:\\users\\<name>\\Documents\\My Games\\{self._game})",
            self,
        )
        layout.addWidget(info_label)

        inputlayout: QHBoxLayout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText(placeholder or "Enter the INI directory or click 'Browse'...")
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
        """Open a directory browser dialog to allow the user to select a directory and updates
        the input field with the chosen path.

        Args:
            caption (str): Optional. The caption text to display on the directory browser dialog.
                           Defaults to an empty string, which displays "Select Directory for INI Files".

        """
        # Open directory browser and update the input field
        manual_path: str = QFileDialog.getExistingDirectory(self, caption or "Select Directory for INI Files")
        if manual_path:
            self.input_field.setText(manual_path)

    def get_path(self) -> str:
        """Retrieve the text from the input field widget.

        Returns:
            str: The text retrieved from the input field.

        """
        return self.input_field.text()
