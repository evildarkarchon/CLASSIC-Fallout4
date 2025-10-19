"""
Unit tests for TUI ErrorDialog clipboard functionality.

Tests the clipboard copy feature in the Textual error dialog.
"""

import pytest
from unittest.mock import MagicMock, patch
from textual.widgets import Button

from ClassicLib.TUI.widgets.dialogs.error_dialog import ErrorDialog


@pytest.mark.unit
@pytest.mark.tui
class TestErrorDialogClipboard:
    """Test ErrorDialog clipboard functionality."""

    @pytest.fixture
    def sample_error_data(self):
        """Sample error data for testing."""
        return {
            "title": "Test Error",
            "message": "An error occurred during testing",
            "details": "Traceback (most recent call last):\n  File 'test.py', line 10\n    raise ValueError('test')\nValueError: test"
        }

    @pytest.mark.asyncio
    async def test_copy_button_exists_with_details(self, sample_error_data):
        """Test that copy button is created when details are provided."""
        dialog = ErrorDialog(**sample_error_data)

        # Mount dialog to compose widgets
        async with dialog.app.run_test() as pilot:
            await pilot.pause()

            # Check for copy button
            try:
                copy_button = dialog.query_one("#copy", Button)
                assert copy_button is not None
                assert "Copy" in copy_button.label
            except Exception:
                pytest.fail("Copy button should exist when details are provided")

    @pytest.mark.asyncio
    async def test_copy_button_not_exists_without_details(self):
        """Test that copy button is not created when details are not provided."""
        dialog = ErrorDialog(
            title="Simple Error",
            message="This is a simple error message"
        )

        async with dialog.app.run_test() as pilot:
            await pilot.pause()

            # Copy button should not exist
            with pytest.raises(Exception):  # query_one raises if not found
                dialog.query_one("#copy", Button)

    @pytest.mark.asyncio
    async def test_close_button_always_exists(self, sample_error_data):
        """Test that close button always exists."""
        # With details
        dialog_with_details = ErrorDialog(**sample_error_data)
        async with dialog_with_details.app.run_test() as pilot:
            await pilot.pause()
            close_button = dialog_with_details.query_one("#close", Button)
            assert close_button is not None

        # Without details
        dialog_without_details = ErrorDialog(title="Test", message="Test")
        async with dialog_without_details.app.run_test() as pilot:
            await pilot.pause()
            close_button = dialog_without_details.query_one("#close", Button)
            assert close_button is not None

    @pytest.mark.asyncio
    async def test_copy_to_clipboard_copies_full_error(self, sample_error_data):
        """Test that copy to clipboard includes all error information."""
        dialog = ErrorDialog(**sample_error_data)

        with patch("ClassicLib.TUI.widgets.dialogs.error_dialog.pyperclip.copy") as mock_copy:
            async with dialog.app.run_test() as pilot:
                await pilot.pause()

                # Trigger copy
                copy_button = dialog.query_one("#copy", Button)
                await pilot.click("#copy")

                # Verify pyperclip.copy was called
                mock_copy.assert_called_once()
                copied_text = mock_copy.call_args[0][0]

                # Verify all error information is included
                assert sample_error_data["title"] in copied_text
                assert sample_error_data["message"] in copied_text
                assert sample_error_data["details"] in copied_text
                assert "Details:" in copied_text

    @pytest.mark.asyncio
    async def test_copy_button_shows_confirmation(self, sample_error_data):
        """Test that copy button shows visual confirmation after copying."""
        dialog = ErrorDialog(**sample_error_data)

        with patch("ClassicLib.TUI.widgets.dialogs.error_dialog.pyperclip.copy"):
            async with dialog.app.run_test() as pilot:
                await pilot.pause()

                copy_button = dialog.query_one("#copy", Button)
                original_label = copy_button.label

                # Click copy button
                await pilot.click("#copy")
                await pilot.pause()

                # Button label should change
                assert copy_button.label != original_label
                assert "Copied" in copy_button.label or "✓" in copy_button.label

    @pytest.mark.asyncio
    async def test_copy_button_resets_after_delay(self, sample_error_data):
        """Test that copy button label resets after delay."""
        dialog = ErrorDialog(**sample_error_data)

        with patch("ClassicLib.TUI.widgets.dialogs.error_dialog.pyperclip.copy"):
            async with dialog.app.run_test() as pilot:
                await pilot.pause()

                copy_button = dialog.query_one("#copy", Button)
                original_label = copy_button.label

                # Click copy button
                await pilot.click("#copy")
                await pilot.pause()

                # Wait for timer (2 seconds)
                await pilot.pause(2.1)

                # Button label should reset
                assert copy_button.label == original_label

    @pytest.mark.asyncio
    async def test_copy_failure_shows_notification(self, sample_error_data):
        """Test that copy failure shows error notification."""
        dialog = ErrorDialog(**sample_error_data)

        # Mock pyperclip to raise an exception
        with patch("ClassicLib.TUI.widgets.dialogs.error_dialog.pyperclip.copy", side_effect=Exception("Clipboard error")):
            async with dialog.app.run_test() as pilot:
                await pilot.pause()

                # Mock notify method to track calls
                dialog.notify = MagicMock()

                # Click copy button
                await pilot.click("#copy")
                await pilot.pause()

                # Verify notification was shown
                dialog.notify.assert_called_once()
                call_args = dialog.notify.call_args
                assert "Failed to copy" in call_args[0][0]
                assert call_args[1].get("severity") == "error"

    @pytest.mark.asyncio
    async def test_close_button_dismisses_dialog(self, sample_error_data):
        """Test that close button dismisses the dialog."""
        dialog = ErrorDialog(**sample_error_data)

        async with dialog.app.run_test() as pilot:
            # Push the dialog as a screen
            await dialog.app.push_screen(dialog)
            await pilot.pause()

            # Click close button
            await pilot.click("#close")
            await pilot.pause()

            # Dialog should be dismissed (no longer in screen stack)
            assert dialog not in dialog.app.screen_stack

    @pytest.mark.asyncio
    async def test_escape_key_closes_dialog(self, sample_error_data):
        """Test that escape key closes the dialog."""
        dialog = ErrorDialog(**sample_error_data)

        async with dialog.app.run_test() as pilot:
            await dialog.app.push_screen(dialog)
            await pilot.pause()

            # Press escape key
            await pilot.press("escape")
            await pilot.pause()

            # Dialog should be dismissed
            assert dialog not in dialog.app.screen_stack

    @pytest.mark.asyncio
    async def test_enter_key_closes_dialog(self, sample_error_data):
        """Test that enter key closes the dialog."""
        dialog = ErrorDialog(**sample_error_data)

        async with dialog.app.run_test() as pilot:
            await dialog.app.push_screen(dialog)
            await pilot.pause()

            # Press enter key
            await pilot.press("enter")
            await pilot.pause()

            # Dialog should be dismissed
            assert dialog not in dialog.app.screen_stack

    @pytest.mark.asyncio
    async def test_callback_invoked_on_close(self):
        """Test that close callback is invoked when dialog closes."""
        callback_invoked = False

        def close_callback():
            nonlocal callback_invoked
            callback_invoked = True

        dialog = ErrorDialog(
            title="Test",
            message="Test message",
            close_callback=close_callback
        )

        async with dialog.app.run_test() as pilot:
            await dialog.app.push_screen(dialog)
            await pilot.pause()

            # Click close button
            await pilot.click("#close")
            await pilot.pause()

            # Callback should be invoked
            assert callback_invoked

    @pytest.mark.asyncio
    async def test_clipboard_copy_format(self, sample_error_data):
        """Test the exact format of copied text."""
        dialog = ErrorDialog(**sample_error_data)

        with patch("ClassicLib.TUI.widgets.dialogs.error_dialog.pyperclip.copy") as mock_copy:
            async with dialog.app.run_test() as pilot:
                await pilot.pause()
                await pilot.click("#copy")

                copied_text = mock_copy.call_args[0][0]

                # Verify format
                lines = copied_text.split("\n")
                assert lines[0] == sample_error_data["title"]
                assert lines[1] == ""  # Blank line
                assert sample_error_data["message"] in copied_text
                assert "Details:" in copied_text

    @pytest.mark.asyncio
    async def test_copy_without_details_field(self):
        """Test copy behavior when details is None."""
        dialog = ErrorDialog(
            title="Test Error",
            message="Test message",
            details=None
        )

        # Should not have copy button
        async with dialog.app.run_test() as pilot:
            await pilot.pause()

            with pytest.raises(Exception):
                dialog.query_one("#copy", Button)
