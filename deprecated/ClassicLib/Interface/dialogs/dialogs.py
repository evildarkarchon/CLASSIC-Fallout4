"""Provide custom dialog windows for displaying application information and errors.

This module defines two custom dialog classes: `CustomAboutDialog` and
`CustomErrorDialog`. `CustomAboutDialog` is used for showing an "About" window
with details about the application, contributors, and application icon.
`CustomErrorDialog` is used to show error messages with optional detailed
tracebacks, including functionality for copying error details to the clipboard.
"""

import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStyle,
    QTextEdit,
    QVBoxLayout,
)

from ClassicLib.core.logger import logger
from ClassicLib.core.registry import get_local_dir


class CustomAboutDialog(QDialog):
    """Display an "About" dialog box for application-specific information.

    This class is a custom QDialog implementation, designed to showcase
    information about the application, such as the application name, icon,
    author details, and contributors. The dialog includes a title, an icon,
    textual details, and a close button. Its purpose is to provide user-friendly
    information to the end-user about the software.

    Attributes:
        TITLE (str): Title of the dialog.
        MIN_WIDTH (int): Minimum width of the dialog.
        MIN_HEIGHT (int): Minimum height of the dialog.
        ICON_SIZE (int): Dimensions (width and height) for the icon in pixels.
        MARGIN (int): Margin size for the dialog layout.

    """

    TITLE = "About"
    MIN_WIDTH = 500
    MIN_HEIGHT = 200
    ICON_SIZE = 128
    MARGIN = 15

    def __init__(self, parent: QMainWindow | QDialog | None = None) -> None:
        """Initialize a new instance of the class.

        Sets up the specified attributes and parent window.

        Args:
            parent: The parent widget, which can be a QMainWindow, QDialog, or None.

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
        """Create the main vertical box layout with specified margins.

        Returns:
            QVBoxLayout: A vertical box layout with applied margins.

        """
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN)
        return layout

    def _create_icon_text_layout(self) -> QHBoxLayout:
        """Create a horizontal box layout containing an icon and text.

        This method creates a QHBoxLayout that includes a QLabel for displaying an
        icon and a QLabel for displaying a multi-line text message. The icon is
        retrieved from a specified file and displayed alongside the text, with
        predefined alignment and word wrapping for proper visualization.

        Returns:
            QHBoxLayout: A horizontal layout containing the icon and text QLabel
            widgets.

        """
        h_layout: QHBoxLayout = QHBoxLayout()

        # Add icon
        icon_label: QLabel = QLabel(self)
        icon_path: str = f"{get_local_dir(as_string=True)}/CLASSIC Data/graphics/CLASSIC.ico"
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
        """Create a "Close" button widget.

        This method creates and configures a QPushButton labeled "Close" which is connected
        to the `accept` method of the dialog or parent widget. The button can be used
        to close or confirm interactions with the dialog where it is used.

        Returns:
            QPushButton: The configured "Close" button widget.

        """
        close_button: QPushButton = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        return close_button


class CustomErrorDialog(QDialog):
    """CustomErrorDialog class.

    A custom dialog for displaying error messages with optional detailed
    information. This dialog includes an icon, message text, and optional
    details such as traceback information. It also provides a "Copy to
    Clipboard" button for copying details and an "OK" button to close the
    dialog. Users can utilize this class to present error information in a
    clear and organized format with customizable features.

    Attributes:
        MIN_WIDTH (int): The minimum width of the dialog.
        MIN_HEIGHT (int): The minimum height of the dialog.
        DETAILS_HEIGHT (int): The maximum height of the details section.
        MARGIN (int): The margin size for dialog content.

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
        """Initialize the error dialog.

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
        """Create a message section with an error icon and a text message for display in a layout.

        The method constructs a horizontal layout containing an error icon and a message label.
        The error icon visually indicates that an error has occurred, and the message label
        displays the associated text message. The label also supports text selection by the user.

        Returns:
            QHBoxLayout: A layout containing the configured error icon and text message.

        """
        h_layout = QHBoxLayout()

        # Add error icon
        icon_label = QLabel(self)
        icon_pixmap = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical).pixmap(48, 48)
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
        """Create and configures a read-only QTextEdit widget to display detailed information.

        The QTextEdit widget is initialized with specific settings for displaying a read-only
        text field with monospaced font. The text content is derived from the `details` attribute,
        and a maximum height is enforced.

        Returns:
            QTextEdit: A configured QTextEdit widget for displaying details.

        """
        details_edit = QTextEdit(self)
        details_edit.setPlainText(self.details or "")
        details_edit.setReadOnly(True)
        details_edit.setMaximumHeight(self.DETAILS_HEIGHT)
        details_edit.setStyleSheet("QTextEdit { font-family: 'Consolas', 'Courier New', monospace; }")
        return details_edit

    def _create_button_section(self) -> QHBoxLayout:
        """Create a button section layout containing interactive buttons.

        This method generates a horizontal layout with buttons designed for specific
        user interactions. It includes an "OK" button for confirming actions and,
        if applicable, a "Copy to Clipboard" button for copying details to the clipboard.

        Returns:
            QHBoxLayout: The layout containing the generated buttons.

        Raises:
            No exceptions are explicitly raised by this method.

        """
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
        """Copy the error details to the system clipboard and display a confirmation message.

        This method constructs a text representation of the error, including the title,
        message, and optional details. The constructed text is copied to the system
        clipboard for easy access. Additionally, a brief confirmation message is shown
        to the user to indicate the successful copy operation.

        The method includes robust error handling to prevent crashes when:
        - The clipboard access fails (permission or platform issues)
        - The dialog is invoked from cross-thread signal-slot connections
        - The QApplication is not properly initialized

        If the clipboard operation fails, appropriate feedback is provided to the user
        without causing application instability.

        Raises:
            None: This method handles all exceptions internally and does not propagate them.

        """
        # Log thread information for debugging cross-thread issues
        current_thread = threading.current_thread()
        is_main_thread = current_thread is threading.main_thread()
        logger.debug(f"_copy_to_clipboard called from thread: {current_thread.name}, is_main_thread: {is_main_thread}")

        try:
            # Verify QApplication exists before accessing clipboard
            app = QApplication.instance()
            if app is None or not isinstance(app, QApplication):
                logger.error("Cannot copy to clipboard: QApplication instance not found")
                self._show_copy_feedback(success=False, error_msg="Application not initialized")
                return

            clipboard = app.clipboard()
            if not clipboard:
                logger.error("Cannot copy to clipboard: clipboard() returned None")
                self._show_copy_feedback(success=False, error_msg="Clipboard not available")
                return

            # Build the full text to copy
            full_text = f"{self.title}\n\n{self.message}"
            if self.details and self.details.strip():
                full_text += f"\n\nDetails:\n{self.details}"

            # Perform the clipboard operation
            clipboard.setText(full_text)

            logger.debug(f"Successfully copied {len(full_text)} characters to clipboard")

            # Show success feedback using non-blocking method
            self._show_copy_feedback(success=True)

        except RuntimeError as e:
            # Qt-related runtime errors (e.g., invalid object state)
            logger.error(f"RuntimeError during clipboard operation: {e}")
            self._show_copy_feedback(success=False, error_msg=str(e))

        except OSError as e:
            # Platform-level clipboard access errors
            logger.error(f"OSError during clipboard operation: {e}")
            self._show_copy_feedback(success=False, error_msg=str(e))

        except Exception as e:  # noqa: BLE001
            # Catch-all for any unexpected errors to prevent crashes
            logger.error(f"Unexpected error during clipboard operation: {e}", exc_info=True)
            self._show_copy_feedback(success=False, error_msg="Unexpected error occurred")

    def _show_copy_feedback(self, *, success: bool, error_msg: str | None = None) -> None:
        """Show feedback to user about clipboard copy operation.

        Uses a non-blocking approach via QTimer.singleShot to avoid nested event loop
        issues that can occur when CustomErrorDialog is shown via cross-thread
        signal-slot connections.

        Args:
            success: Whether the clipboard operation succeeded.
            error_msg: Error message to display if operation failed (optional).

        """
        if success:
            # Update the copy button text temporarily to provide feedback
            # This avoids creating a nested event loop with a modal dialog
            copy_button = self.findChild(QPushButton, "")

            # Find the copy button by iterating through buttons
            for child in self.findChildren(QPushButton):
                if child.text() == "Copy to Clipboard":
                    copy_button = child
                    break

            if copy_button is not None:
                original_text = copy_button.text()
                copy_button.setText("✓ Copied!")
                copy_button.setEnabled(False)

                # Reset button text after a short delay
                def reset_button() -> None:
                    try:
                        if copy_button:
                            copy_button.setText(original_text)
                            copy_button.setEnabled(True)
                    except RuntimeError:
                        # Button may have been deleted if dialog was closed
                        pass

                QTimer.singleShot(1500, reset_button)
            else:
                logger.debug("Clipboard copy succeeded (copy button not found for visual feedback)")

        else:
            # Show error feedback - also non-blocking
            error_display = error_msg or "Unknown error"

            # Find the copy button and update its text to show error
            for child in self.findChildren(QPushButton):
                if child.text() in {"Copy to Clipboard", "✓ Copied!"}:
                    original_text = "Copy to Clipboard"
                    child.setText(f"✗ Failed: {error_display[:20]}")
                    child.setEnabled(False)

                    def reset_button_error(btn: QPushButton = child, orig: str = original_text) -> None:
                        try:
                            btn.setText(orig)
                            btn.setEnabled(True)
                        except RuntimeError:
                            pass

                    QTimer.singleShot(3000, reset_button_error)
                    break
