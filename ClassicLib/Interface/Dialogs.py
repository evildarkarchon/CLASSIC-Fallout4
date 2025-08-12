"""
Dialog classes for the CLASSIC interface.

This module contains custom dialog implementations used throughout the application.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
)

from ClassicLib import GlobalRegistry


class CustomAboutDialog(QDialog):
    """
    A class representing an "About" dialog window, providing information about the application,
    icon, contributors, and a close button for dismissing the dialog. The dialog is designed
    to have similar style and layout to a QMessageBox's "About" dialog, with custom text and
    an application-specific icon.
    """

    TITLE = "About"
    MIN_WIDTH = 500
    MIN_HEIGHT = 200
    ICON_SIZE = 128
    MARGIN = 15

    def __init__(self, parent: QMainWindow | QDialog | None = None) -> None:
        """
        Initialize the About dialog.

        Args:
            parent: Optional parent widget to associate the "About" dialog with. It can be an
                instance of QMainWindow, QDialog, or None if no parent is provided.
        """
        super().__init__(parent)
        self.setWindowTitle(self.TITLE)
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # Create main layout
        layout: QVBoxLayout = self._create_main_layout()

        # Create and add horizontal layout with icon and text
        h_layout: QHBoxLayout = self._create_icon_text_layout()
        layout.addLayout(h_layout)

        # Add close button
        close_button: QPushButton = self._create_close_button()
        layout.addWidget(close_button)
        layout.setAlignment(close_button, Qt.AlignmentFlag.AlignRight)

    def _create_main_layout(self) -> QVBoxLayout:
        """Create and return the main layout with proper margins."""
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN)
        return layout

    def _create_icon_text_layout(self) -> QHBoxLayout:
        """Create and return the horizontal layout with icon and text."""
        h_layout: QHBoxLayout = QHBoxLayout()

        # Add icon
        icon_label: QLabel = QLabel(self)
        icon_path: str = f"{GlobalRegistry.get_local_dir(as_string=True)}/CLASSIC Data/graphics/CLASSIC.ico"
        pixmap: QPixmap = QIcon(icon_path).pixmap(self.ICON_SIZE, self.ICON_SIZE)

        if not pixmap.isNull():
            icon_label.setPixmap(pixmap)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        h_layout.addWidget(icon_label)

        # Add text
        text = (
            "Crash Log Auto Scanner & Setup Integrity Checker\n\n"
            "Made by: Poet\n"
            "Contributors: evildarkarchon | kittivelae | AtomicFallout757 | wxMichael"
        )

        text_label: QLabel = QLabel(text)
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        text_label.setWordWrap(True)

        h_layout.addWidget(text_label)
        return h_layout

    def _create_close_button(self) -> QPushButton:
        """Create and return the close button."""
        close_button: QPushButton = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        return close_button
