"""
Unit tests for CustomErrorDialog.

Tests the custom error dialog with clipboard copy functionality.
This module provides comprehensive coverage for:
- Basic dialog creation and configuration
- Clipboard operations and error handling
- Visual feedback mechanisms
- Edge cases and boundary conditions
- Parent widget handling
- Layout and structure verification
- Accessibility features
"""

import os
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMainWindow, QPushButton, QTextEdit

from ClassicLib.Interface.dialogs.Dialogs import CustomErrorDialog


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

    def test_copy_confirmation_feedback_shown(self, qtbot, sample_error_data):
        """Test that confirmation feedback is shown after copying via button text change."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        mock_clipboard = MagicMock()
        with patch.object(QApplication, "clipboard", return_value=mock_clipboard):
            # Find copy button
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            original_text = copy_button.text()

            # Click copy button
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Verify button text changed to show success feedback
            assert copy_button.text() == "✓ Copied!"
            assert not copy_button.isEnabled()

            # Verify clipboard was called
            mock_clipboard.setText.assert_called_once()

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


@pytest.mark.unit
@pytest.mark.gui
class TestClipboardErrorHandling:
    """Test clipboard operation error handling.

    Priority 1 tests covering all error handling paths in _copy_to_clipboard method.
    """

    @pytest.fixture
    def sample_error_data(self):
        """Sample error data for testing."""
        return {
            "title": "Test Error",
            "message": "An error occurred during testing",
            "details": "Traceback (most recent call last):\n  File 'test.py', line 10\n    raise ValueError('test')\nValueError: test",
        }

    def test_copy_handles_no_qapplication(self, qtbot, sample_error_data):
        """Test copy handles missing QApplication gracefully."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Mock QApplication.instance() to return None
        with patch.object(QApplication, "instance", return_value=None):
            # Find and click copy button - should not crash
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Button should show error feedback
            assert "Failed" in copy_button.text() or "Application not initialized" in copy_button.text()

    def test_copy_handles_null_clipboard(self, qtbot, sample_error_data):
        """Test copy handles null clipboard gracefully."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Mock clipboard() to return None
        mock_app = MagicMock()
        mock_app.clipboard.return_value = None

        with patch.object(QApplication, "instance", return_value=mock_app):
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Button should show error feedback
            assert "Failed" in copy_button.text() or "Clipboard not available" in copy_button.text()

    def test_copy_handles_runtime_error(self, qtbot, sample_error_data):
        """Test RuntimeError during clipboard operation."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Mock clipboard.setText to raise RuntimeError
        mock_clipboard = MagicMock()
        mock_clipboard.setText.side_effect = RuntimeError("Qt object deleted")

        with patch.object(QApplication, "clipboard", return_value=mock_clipboard):
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Should handle error gracefully - button shows error
            assert "Failed" in copy_button.text()

    def test_copy_handles_os_error(self, qtbot, sample_error_data):
        """Test OSError during clipboard operation (platform issues)."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Mock clipboard.setText to raise OSError
        mock_clipboard = MagicMock()
        mock_clipboard.setText.side_effect = OSError("Clipboard access denied")

        with patch.object(QApplication, "clipboard", return_value=mock_clipboard):
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Should handle error gracefully
            assert "Failed" in copy_button.text()

    def test_copy_handles_unexpected_exception(self, qtbot, sample_error_data):
        """Test generic exception handling in clipboard operation."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Mock clipboard.setText to raise unexpected exception
        mock_clipboard = MagicMock()
        mock_clipboard.setText.side_effect = Exception("Unexpected error")

        with patch.object(QApplication, "clipboard", return_value=mock_clipboard):
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Should handle error gracefully, showing "Unexpected error occurred"
            assert "Failed" in copy_button.text()


@pytest.mark.unit
@pytest.mark.gui
class TestCopyFeedback:
    """Test copy to clipboard feedback mechanism.

    Priority 2 tests covering the visual feedback system in _show_copy_feedback.
    """

    @pytest.fixture
    def sample_error_data(self):
        """Sample error data for testing."""
        return {
            "title": "Test Error",
            "message": "An error occurred during testing",
            "details": "Traceback (most recent call last):\n  File 'test.py', line 10\n    raise ValueError('test')\nValueError: test",
        }

    def test_success_feedback_button_text_changes(self, qtbot, sample_error_data):
        """Test button shows '✓ Copied!' on success."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        mock_clipboard = MagicMock()
        with patch.object(QApplication, "clipboard", return_value=mock_clipboard):
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Button text should change to "✓ Copied!"
            assert copy_button.text() == "✓ Copied!"

    def test_success_feedback_button_disabled(self, qtbot, sample_error_data):
        """Test button is temporarily disabled on success."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        mock_clipboard = MagicMock()
        with patch.object(QApplication, "clipboard", return_value=mock_clipboard):
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Button should be disabled
            assert not copy_button.isEnabled()

    def test_success_feedback_resets_after_delay(self, qtbot, sample_error_data):
        """Test button text resets after 1500ms delay."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        mock_clipboard = MagicMock()
        with patch.object(QApplication, "clipboard", return_value=mock_clipboard):
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            original_text = copy_button.text()
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Wait for the timer (1500ms + buffer)
            qtbot.wait(1600)

            # Button should be reset
            assert copy_button.text() == original_text
            assert copy_button.isEnabled()

    def test_failure_feedback_shows_error(self, qtbot, sample_error_data):
        """Test button shows truncated error message on failure."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Force failure by returning None clipboard
        mock_app = MagicMock()
        mock_app.clipboard.return_value = None

        with patch.object(QApplication, "instance", return_value=mock_app):
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Button should show error
            assert "✗ Failed:" in copy_button.text()

    def test_failure_feedback_error_truncation(self, qtbot, sample_error_data):
        """Test error messages are truncated to 20 characters."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Mock clipboard to raise a long error message
        mock_clipboard = MagicMock()
        long_error = "This is a very long error message that should be truncated"
        mock_clipboard.setText.side_effect = RuntimeError(long_error)

        with patch.object(QApplication, "clipboard", return_value=mock_clipboard):
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Error message should be truncated
            button_text = copy_button.text()
            # Remove prefix "✗ Failed: " and check length
            error_part = button_text.replace("✗ Failed: ", "")
            assert len(error_part) <= 20

    def test_feedback_handles_deleted_button(self, qtbot, sample_error_data):
        """Test feedback handles button deletion gracefully."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        mock_clipboard = MagicMock()
        with patch.object(QApplication, "clipboard", return_value=mock_clipboard):
            copy_button = [btn for btn in dialog.findChildren(QPushButton) if "Copy" in btn.text()][0]
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)

            # Verify feedback was shown
            assert copy_button.text() == "✓ Copied!"

            # Close dialog before timer fires (simulates button deletion)
            dialog.close()

            # Wait for timer and verify no crash occurs
            qtbot.wait(1600)  # Should not crash


@pytest.mark.unit
@pytest.mark.gui
class TestEdgeCases:
    """Test edge cases and boundary conditions.

    Priority 3 tests covering unusual inputs and boundary conditions.
    """

    def test_empty_title(self, qtbot):
        """Test dialog with empty title string."""
        dialog = CustomErrorDialog(title="", message="Test message")
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == ""
        assert dialog.title == ""

    def test_empty_message(self, qtbot):
        """Test dialog with empty message string."""
        dialog = CustomErrorDialog(title="Error", message="")
        qtbot.addWidget(dialog)

        assert dialog.message == ""

        # Find message label and verify it exists but is empty
        labels = dialog.findChildren(QLabel)
        message_labels = [lbl for lbl in labels if lbl.text() == ""]
        assert len(message_labels) >= 1

    def test_very_long_title(self, qtbot):
        """Test dialog with very long title (>100 chars)."""
        long_title = "A" * 150
        dialog = CustomErrorDialog(title=long_title, message="Test")
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == long_title
        assert dialog.title == long_title

    def test_very_long_message(self, qtbot):
        """Test dialog with very long message (>1000 chars)."""
        long_message = "Error message " * 100  # ~1400 chars
        dialog = CustomErrorDialog(title="Error", message=long_message)
        qtbot.addWidget(dialog)

        assert dialog.message == long_message

        # Verify message is displayed
        labels = dialog.findChildren(QLabel)
        message_labels = [lbl for lbl in labels if long_message in lbl.text()]
        assert len(message_labels) > 0

    def test_very_long_details(self, qtbot):
        """Test dialog with very long details (>10000 chars)."""
        long_details = "Stack trace line\n" * 1000  # ~17000 chars
        dialog = CustomErrorDialog(
            title="Error",
            message="Test",
            details=long_details,
        )
        qtbot.addWidget(dialog)

        assert dialog.details == long_details

        # Verify details are displayed
        text_edits = dialog.findChildren(QTextEdit)
        assert len(text_edits) == 1
        assert text_edits[0].toPlainText() == long_details

    def test_unicode_content(self, qtbot):
        """Test dialog with unicode characters."""
        unicode_title = "错误 - エラー - Ошибка"
        unicode_message = "An error occurred: 日本語テスト 🚨⚠️💥"
        unicode_details = "Unicode stacktrace: αβγδ → λμνξ\n中文字符\nЭто ошибка"

        dialog = CustomErrorDialog(
            title=unicode_title,
            message=unicode_message,
            details=unicode_details,
        )
        qtbot.addWidget(dialog)

        assert dialog.title == unicode_title
        assert dialog.message == unicode_message
        assert dialog.details == unicode_details

    def test_special_characters_in_content(self, qtbot):
        """Test dialog with special characters."""
        special_title = "Error <>&'\""
        special_message = "Message with\ttabs\nand\nnewlines"
        special_details = "Details: \x00\x01\x02 (control chars stripped)"

        dialog = CustomErrorDialog(
            title=special_title,
            message=special_message,
            details=special_details,
        )
        qtbot.addWidget(dialog)

        assert dialog.title == special_title
        assert dialog.message == special_message
        assert dialog.details == special_details

    def test_html_like_content_not_rendered(self, qtbot):
        """Test HTML-like content is displayed as plain text, not rendered."""
        html_message = "<script>alert('XSS')</script><b>Bold</b>"
        dialog = CustomErrorDialog(
            title="Error",
            message=html_message,
        )
        qtbot.addWidget(dialog)

        # Find message label
        labels = dialog.findChildren(QLabel)
        message_labels = [lbl for lbl in labels if html_message in lbl.text()]

        # The HTML should be displayed as-is, not rendered
        assert len(message_labels) > 0
        # The text should contain the raw HTML, not rendered HTML
        assert "<script>" in message_labels[0].text()


@pytest.mark.unit
@pytest.mark.gui
class TestParentWidget:
    """Test dialog with various parent widgets.

    Priority 4 tests covering parent widget handling.
    """

    def test_with_mainwindow_parent(self, qtbot):
        """Test dialog with QMainWindow parent."""
        main_window = QMainWindow()
        qtbot.addWidget(main_window)

        dialog = CustomErrorDialog(
            title="Error",
            message="Test",
            parent=main_window,
        )
        qtbot.addWidget(dialog)

        assert dialog.parent() is main_window

    def test_with_dialog_parent(self, qtbot):
        """Test dialog with QDialog parent."""
        parent_dialog = QDialog()
        qtbot.addWidget(parent_dialog)

        dialog = CustomErrorDialog(
            title="Error",
            message="Test",
            parent=parent_dialog,
        )
        qtbot.addWidget(dialog)

        assert dialog.parent() is parent_dialog

    def test_without_parent(self, qtbot):
        """Test dialog without parent widget."""
        dialog = CustomErrorDialog(
            title="Error",
            message="Test",
        )
        qtbot.addWidget(dialog)

        assert dialog.parent() is None


@pytest.mark.unit
@pytest.mark.gui
class TestDialogLayout:
    """Test dialog layout and visual structure.

    Priority 5 tests covering layout, styling, and visual elements.
    """

    @pytest.fixture
    def sample_error_data(self):
        """Sample error data for testing."""
        return {
            "title": "Test Error",
            "message": "An error occurred during testing",
            "details": "Traceback (most recent call last):\n  File 'test.py', line 10\n    raise ValueError('test')\nValueError: test",
        }

    def test_error_icon_displayed(self, qtbot, sample_error_data):
        """Test error icon is displayed."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Find labels and check for one with a pixmap (the icon)
        labels = dialog.findChildren(QLabel)
        icon_labels = [lbl for lbl in labels if not lbl.pixmap().isNull()]

        assert len(icon_labels) >= 1, "Should have an icon label with pixmap"

    def test_error_icon_alignment(self, qtbot, sample_error_data):
        """Test error icon is top-aligned."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Find labels with pixmap (icon)
        labels = dialog.findChildren(QLabel)
        icon_labels = [lbl for lbl in labels if not lbl.pixmap().isNull()]

        assert len(icon_labels) >= 1
        icon_label = icon_labels[0]

        # Check alignment includes AlignTop
        assert icon_label.alignment() & Qt.AlignmentFlag.AlignTop

    def test_details_section_readonly(self, qtbot, sample_error_data):
        """Test details section is read-only."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        text_edits = dialog.findChildren(QTextEdit)
        assert len(text_edits) == 1
        assert text_edits[0].isReadOnly()

    def test_details_section_monospace_font(self, qtbot, sample_error_data):
        """Test details section uses monospace font style."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        text_edits = dialog.findChildren(QTextEdit)
        assert len(text_edits) == 1

        # Check that stylesheet includes monospace font
        style = text_edits[0].styleSheet()
        assert "monospace" in style.lower() or "consolas" in style.lower() or "courier" in style.lower()

    def test_layout_margins(self, qtbot, sample_error_data):
        """Test layout margins are applied correctly."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        # Get the main layout
        layout = dialog.layout()
        assert layout is not None, "Dialog should have a layout"
        margins = layout.contentsMargins()

        expected_margin = CustomErrorDialog.MARGIN
        assert margins.left() == expected_margin
        assert margins.right() == expected_margin
        assert margins.top() == expected_margin
        assert margins.bottom() == expected_margin

    def test_ok_button_is_default(self, qtbot, sample_error_data):
        """Test OK button is the default button."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)

        ok_buttons = [btn for btn in dialog.findChildren(QPushButton) if btn.text() == "OK"]
        assert len(ok_buttons) == 1
        assert ok_buttons[0].isDefault()


@pytest.mark.unit
@pytest.mark.gui
class TestAccessibility:
    """Test dialog accessibility features.

    Priority 6 tests covering keyboard navigation and accessibility.
    """

    @pytest.fixture
    def sample_error_data(self):
        """Sample error data for testing."""
        return {
            "title": "Test Error",
            "message": "An error occurred during testing",
            "details": "Traceback (most recent call last):\n  File 'test.py', line 10\n    raise ValueError('test')\nValueError: test",
        }

    def test_keyboard_navigation(self, qtbot, sample_error_data):
        """Test keyboard navigation between buttons using Tab.

        Verifies that all buttons are focusable (have the right focus policy),
        which enables keyboard navigation.
        """
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)

        # Get all buttons
        buttons = dialog.findChildren(QPushButton)
        assert len(buttons) >= 2  # Copy and OK buttons

        # Verify all buttons have TabFocus or StrongFocus policy (are focusable via Tab)
        for btn in buttons:
            focus_policy = btn.focusPolicy()
            # Qt.FocusPolicy.TabFocus = 1, StrongFocus = 11, WheelFocus = 15
            assert focus_policy in (
                Qt.FocusPolicy.TabFocus,
                Qt.FocusPolicy.StrongFocus,
                Qt.FocusPolicy.WheelFocus,
            ), f"Button '{btn.text()}' should be focusable via keyboard"

        # Verify buttons are enabled and can receive focus
        for btn in buttons:
            assert btn.isEnabled(), f"Button '{btn.text()}' should be enabled"

    def test_escape_closes_dialog(self, qtbot, sample_error_data):
        """Test Escape key closes dialog (triggers reject)."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)

        # Press Escape - should trigger rejected signal
        with qtbot.waitSignal(dialog.rejected, timeout=1000):
            qtbot.keyClick(dialog, Qt.Key.Key_Escape)

    def test_enter_accepts_dialog(self, qtbot, sample_error_data):
        """Test Enter key accepts dialog when OK button is default."""
        dialog = CustomErrorDialog(**sample_error_data)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)

        # OK button should be default
        ok_button = [btn for btn in dialog.findChildren(QPushButton) if btn.text() == "OK"][0]
        assert ok_button.isDefault()

        # Press Enter - should trigger accepted signal
        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            qtbot.keyClick(dialog, Qt.Key.Key_Return)
