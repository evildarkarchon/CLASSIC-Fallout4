"""
Dialog classes for the CLASSIC interface.

This module contains custom dialog implementations used throughout the application.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
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


class CustomErrorDialog(QDialog):
    """
    A custom error dialog with copy-to-clipboard functionality.

    This dialog displays error information with a title, message, and optional
    detailed traceback. Users can copy the full error details to clipboard for
    easy reporting and debugging.
    """

    MIN_WIDTH = 500
    MIN_HEIGHT = 200
    DETAILS_HEIGHT = 300
    MARGIN = 15

    def __init__(
        self,
        title: str,
        message: str,
        details: str | None = None,
        parent: QMainWindow | QDialog | None = None,
    ) -> None:
        """
        Initialize the error dialog.

        Args:
            title: The title of the error dialog
            message: The main error message to display
            details: Optional detailed error information (e.g., traceback)
            parent: Optional parent widget
        """
        super().__init__(parent)
        self.title = title
        self.message = message
        self.details = details

        self.setWindowTitle(title)
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN)

        # Add icon and message section
        message_layout = self._create_message_section()
        layout.addLayout(message_layout)

        # Add details section if provided
        if details and details.strip():
            details_widget = self._create_details_section()
            layout.addWidget(details_widget)

        # Add buttons
        button_layout = self._create_button_section()
        layout.addLayout(button_layout)

    def _create_message_section(self) -> QHBoxLayout:
        """Create the message section with icon and text."""
        h_layout = QHBoxLayout()

        # Add error icon
        icon_label = QLabel(self)
        icon_pixmap = self.style().standardIcon(QMessageBox.StandardButton.Critical.value).pixmap(48, 48)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        h_layout.addWidget(icon_label)

        # Add message text
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        h_layout.addWidget(message_label, 1)

        return h_layout

    def _create_details_section(self) -> QTextEdit:
        """Create the details section with traceback information."""
        details_edit = QTextEdit(self)
        details_edit.setPlainText(self.details or "")
        details_edit.setReadOnly(True)
        details_edit.setMaximumHeight(self.DETAILS_HEIGHT)
        details_edit.setStyleSheet("QTextEdit { font-family: 'Consolas', 'Courier New', monospace; }")
        return details_edit

    def _create_button_section(self) -> QHBoxLayout:
        """Create the button section with Copy and OK buttons."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Copy to Clipboard button (only if details exist)
        if self.details and self.details.strip():
            copy_button = QPushButton("Copy to Clipboard", self)
            copy_button.clicked.connect(self._copy_to_clipboard)
            button_layout.addWidget(copy_button)

        # OK button
        ok_button = QPushButton("OK", self)
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)

        return button_layout

    def _copy_to_clipboard(self) -> None:
        """Copy error details to clipboard."""
        clipboard = QApplication.clipboard()
        full_text = f"{self.title}\n\n{self.message}"
        if self.details and self.details.strip():
            full_text += f"\n\nDetails:\n{self.details}"

        clipboard.setText(full_text)

        # Show brief confirmation
        QMessageBox.information(
            self,
            "Copied",
            "Error details copied to clipboard.",
            QMessageBox.StandardButton.Ok,
        )
