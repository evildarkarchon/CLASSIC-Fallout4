"""
Unit tests for CustomErrorDialog.

Tests the custom error dialog with clipboard copy functionality.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QTextEdit

from ClassicLib.Interface.Dialogs import CustomErrorDialog


@pytest.mark.unit
@pytest.mark.gui
class TestCustomErrorDialog:
    """Test CustomErrorDialog functionality."""

    @pytest.fixture
    def sample_error_data(self):
        """Sample error data for testing."""
        return {
            "title": "Test Error",
            "message": "An error occurred during testing",
            "details": "Traceback (most recent call last):\n  File 'test.py', line 10\n    raise ValueError('test')\nValueError: test",
        }

    def test_dialog_creation_with_all_parameters(self, qtbot, sample_error_data):
        """Test dialog is created with all parameters."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == sample_error_data["title"]
        assert dialog.title == sample_error_data["title"]
        assert dialog.message == sample_error_data["message"]
        assert dialog.details == sample_error_data["details"]

    def test_dialog_creation_without_details(self, qtbot):
        """Test dialog creation without details section."""
        dialog = CustomErrorDialog(title="Simple Error", message="This is a simple error message")
        qtbot.addWidget(dialog)

        assert dialog.title == "Simple Error"
        assert dialog.message == "This is a simple error message"
        assert dialog.details is None

    def test_copy_button_exists_when_details_provided(self, qtbot, sample_error_data):
        """Test that Copy to Clipboard button exists when details are provided."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Find copy button
        copy_buttons = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()]
        assert len(copy_buttons) == 1, "Should have exactly one Copy button"

    def test_copy_button_not_exists_without_details(self, qtbot):
        """Test that Copy to Clipboard button doesn't exist when no details."""
        dialog = CustomErrorDialog(title="Simple Error", message="No details here")
        qtbot.addWidget(dialog)

        # Find copy button
        copy_buttons = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()]
        assert len(copy_buttons) == 0, "Should not have Copy button without details"

    def test_ok_button_always_exists(self, qtbot, sample_error_data):
        """Test that OK button always exists."""
        # With details
        dialog_with_details = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog_with_details)
        ok_buttons = [btn for btn in dialog_with_details.findChildren(QPushButton) if btn.text() == "OK"]
        assert len(ok_buttons) == 1, "Should have OK button with details"

        # Without details
        dialog_without_details = CustomErrorDialog(title="Test", message="Test")
        qtbot.addWidget(dialog_without_details)
        ok_buttons = [btn for btn in dialog_without_details.findChildren(QPushButton) if btn.text() == "OK"]
        assert len(ok_buttons) == 1, "Should have OK button without details"

    def test_details_section_displayed(self, qtbot, sample_error_data):
        """Test that details section is displayed correctly."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Find QTextEdit (details section)
        text_edits = dialog.findChildren(QTextEdit)
        assert len(text_edits) == 1, "Should have one QTextEdit for details"

        details_edit = text_edits[0]
        assert details_edit.toPlainText() == sample_error_data["details"]
        assert details_edit.isReadOnly(), "Details should be read-only"

    def test_copy_to_clipboard_functionality(self, qtbot, sample_error_data):
        """Test that copy to clipboard works correctly."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Mock clipboard
        mock_clipboard = MagicMock()
        with patch.object(QApplication, "clipboard", return_value=mock_clipboard):
            # Mock the confirmation dialog
            with patch("ClassicLib.Interface.Dialogs.QMessageBox.information"):
                # Find and click copy button
                copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
                qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

        # Verify clipboard was called
        mock_clipboard.setText.assert_called_once()
        copied_text = mock_clipboard.setText.call_args[0][0]

        # Verify copied text contains all error information
        assert sample_error_data["title"] in copied_text
        assert sample_error_data["message"] in copied_text
        assert sample_error_data["details"] in copied_text
        assert "Details:" in copied_text

    def test_copy_confirmation_dialog_shown(self, qtbot, sample_error_data):
        """Test that confirmation dialog is shown after copying."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        mock_clipboard = MagicMock()
        with patch.object(QApplication, "clipboard", return_value=mock_clipboard):
            with patch("ClassicLib.Interface.Dialogs.QMessageBox.information") as mock_info:
                # Find and click copy button
                copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
                qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

                # Verify confirmation dialog was shown
                mock_info.assert_called_once()
                call_args = mock_info.call_args[0]
                assert "Copied" in call_args[1]  # Title
                assert "clipboard" in call_args[2].lower()  # Message

    def test_ok_button_closes_dialog(self, qtbot, sample_error_data):
        """Test that OK button closes the dialog."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Find OK button
        ok_button = [btn for btn in dialog.findChildren(QPushButton) if btn.text() == "OK"][0]

        # Show dialog non-modal for testing
        dialog.show()
        qtbot.waitExposed(dialog)

        # Click OK button
        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

    def test_message_is_selectable(self, qtbot, sample_error_data):
        """Test that error message text is selectable by mouse."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Find message label (should be a QLabel)
        from PySide6.QtWidgets import QLabel

        labels = dialog.findChildren(QLabel)
        message_labels = [lbl for lbl in labels if sample_error_data["message"] in lbl.text()]

        assert len(message_labels) > 0, "Should find message label"
        message_label = message_labels[0]

        # Verify text is selectable
        assert message_label.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse

    def test_minimum_size_constraints(self, qtbot, sample_error_data):
        """Test that dialog respects minimum size constraints."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() >= CustomErrorDialog.MIN_WIDTH
        assert dialog.minimumHeight() >= CustomErrorDialog.MIN_HEIGHT

    def test_dialog_with_empty_details_string(self, qtbot):
        """Test dialog handles empty details string gracefully."""
        dialog = CustomErrorDialog(
            title="Error",
            message="Message",
            details="   ",  # Whitespace only
        )
        qtbot.addWidget(dialog)

        # Should not show details section for empty/whitespace-only details
        text_edits = dialog.findChildren(QTextEdit)
        assert len(text_edits) == 0, "Should not show details section for whitespace-only details"

    def test_multiline_message_wrapping(self, qtbot):
        """Test that multiline messages wrap correctly."""
        long_message = "This is a very long error message " * 20
        dialog = CustomErrorDialog(title="Error", message=long_message)
        qtbot.addWidget(dialog)

        from PySide6.QtWidgets import QLabel

        labels = dialog.findChildren(QLabel)
        message_labels = [lbl for lbl in labels if long_message in lbl.text()]

        assert len(message_labels) > 0
        message_label = message_labels[0]
        assert message_label.wordWrap(), "Message should have word wrap enabled"
