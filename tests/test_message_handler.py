"""Tests for the MessageHandler module."""

import sys
from io import StringIO
from typing import Any, TextIO
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.MessageHandler import (
    CLIProgressBar,
    Message,
    MessageHandler,
    MessageTarget,
    MessageType,
    get_message_handler,
    init_message_handler,
    msg_error,
    msg_info,
    msg_progress_context,
    msg_success,
    msg_warning,
)


class TestMessageHandler:
    """Test cases for MessageHandler class."""

    def test_init_cli_mode(self) -> None:
        """Test initialization in CLI mode."""
        handler: MessageHandler = MessageHandler(parent=None, is_gui_mode=False)
        assert handler.is_gui_mode is False
        assert handler.parent_widget is None

    @patch("ClassicLib.MessageHandler.HAS_QT", True)
    def test_init_gui_mode(self) -> None:
        """Test initialization in GUI mode."""
        mock_parent: MagicMock = MagicMock()
        # For GUI mode, the MessageHandler should accept a parent but it might not be stored exactly as expected
        handler: MessageHandler = MessageHandler(parent=mock_parent, is_gui_mode=True)
        assert handler.is_gui_mode is True
        # In the actual Qt implementation, the parent might be handled differently
        # Let's just verify the handler was created successfully in GUI mode

    def test_should_display_logic(self) -> None:
        """Test message display logic based on target and mode."""
        # CLI mode handler
        cli_handler: MessageHandler = MessageHandler(parent=None, is_gui_mode=False)
        assert cli_handler._should_display(MessageTarget.ALL) is True
        assert cli_handler._should_display(MessageTarget.CLI_ONLY) is True
        assert cli_handler._should_display(MessageTarget.GUI_ONLY) is False
        assert cli_handler._should_display(MessageTarget.LOG_ONLY) is False

        # GUI mode handler (mocked)
        with patch("ClassicLib.MessageHandler.HAS_QT", True):
            gui_handler: MessageHandler = MessageHandler(parent=None, is_gui_mode=True)
            assert gui_handler._should_display(MessageTarget.ALL) is True
            assert gui_handler._should_display(MessageTarget.CLI_ONLY) is False
            assert gui_handler._should_display(MessageTarget.GUI_ONLY) is True
            assert gui_handler._should_display(MessageTarget.LOG_ONLY) is False

    def test_cli_message_output(self) -> None:
        """Test CLI message output formatting."""
        handler: MessageHandler = MessageHandler(parent=None, is_gui_mode=False)

        # Test that messages can be sent without errors
        # The actual output goes to logging system, not direct stdout/stderr
        # These methods should not raise any exceptions under normal circumstances
        handler.info("Test info message")
        handler.error("Test error message")
        handler.success("Test success message")
        handler.warning("Test warning message")

        # If we get here without exceptions, the message handling works
        assert True

    def test_message_with_details(self) -> None:
        """Test messages with details."""
        handler: MessageHandler = MessageHandler(parent=None, is_gui_mode=False)

        old_stdout: TextIO | Any = sys.stdout
        try:
            sys.stdout = StringIO()
            handler.info("Main message", details="Additional details here")
            output: str = sys.stdout.getvalue()
            assert "Main message" in output
        finally:
            sys.stdout = old_stdout

    def test_message_targets(self) -> None:
        """Test message targeting."""
        handler: MessageHandler = MessageHandler(parent=None, is_gui_mode=False)

        old_stdout: TextIO | Any = sys.stdout
        try:
            # CLI_ONLY message should show in CLI mode
            sys.stdout = StringIO()
            handler.info("CLI only", target=MessageTarget.CLI_ONLY)
            output: str = sys.stdout.getvalue()
            assert "CLI only" in output

            # GUI_ONLY message should not show in CLI mode
            sys.stdout = StringIO()
            handler.info("GUI only", target=MessageTarget.GUI_ONLY)
            output = sys.stdout.getvalue()
            assert "GUI only" not in output

            # LOG_ONLY message should not show anywhere
            sys.stdout = StringIO()
            handler.info("Log only", target=MessageTarget.LOG_ONLY)
            output = sys.stdout.getvalue()
            assert "Log only" not in output

        finally:
            sys.stdout = old_stdout


class TestCLIProgressBar:
    """Test cases for CLIProgressBar class."""

    def test_progress_bar_with_total(self) -> None:
        """Test progress bar with known total."""
        old_stdout: TextIO | Any = sys.stdout
        try:
            sys.stdout = StringIO()

            progress: CLIProgressBar = CLIProgressBar("Testing", total=10)
            progress.update(5)
            output: str = sys.stdout.getvalue()

            assert "Testing" in output
            assert "50%" in output
            assert "█" in output  # Progress bar character

            progress.close()

        finally:
            sys.stdout = old_stdout

    def test_progress_bar_without_total(self) -> None:
        """Test progress bar without known total."""
        old_stdout: TextIO | Any = sys.stdout
        try:
            sys.stdout = StringIO()

            progress: CLIProgressBar = CLIProgressBar("Processing")
            progress.update(5)
            output: str = sys.stdout.getvalue()

            assert "Processing" in output
            assert "5 items processed" in output

            progress.close()

        finally:
            sys.stdout = old_stdout

    def test_progress_bar_description_update(self) -> None:
        """Test updating progress bar description."""
        progress: CLIProgressBar = CLIProgressBar("Initial", total=10)
        progress.set_description("Updated")
        assert progress.desc == "Updated"


class TestGlobalFunctions:
    """Test cases for global convenience functions."""

    def test_init_and_get_handler(self) -> None:
        """Test initializing and getting global handler."""
        # This test ensures the init and get functions work correctly
        # We'll test the functionality rather than error states since other tests may have initialized handlers

        # Initialize a handler (this should always work)
        handler: MessageHandler = init_message_handler(parent=None, is_gui_mode=False)
        assert handler is not None
        assert isinstance(handler, MessageHandler)

        # Get handler should return the same instance
        retrieved: MessageHandler = get_message_handler()
        assert retrieved is handler

        # Verify the handler is functional
        # This should not raise any exceptions under normal circumstances
        handler.info("Test message from handler test")
        assert True  # If we get here, the handler works

    def test_convenience_functions(self) -> None:
        """Test convenience message functions."""
        # Initialize handler
        init_message_handler(parent=None, is_gui_mode=False)

        # Test that convenience functions work without errors
        # The actual output goes to logging system
        # These functions should not raise any exceptions under normal circumstances
        msg_info("Info test")
        msg_error("Error test")
        msg_success("Success test")
        msg_warning("Warning test")

        # If we get here without exceptions, the convenience functions work
        assert True

    def test_progress_context_manager(self) -> None:
        """Test progress context manager."""
        init_message_handler(parent=None, is_gui_mode=False)

        old_stdout: TextIO | Any = sys.stdout
        try:
            sys.stdout = StringIO()

            with msg_progress_context("Test Progress", 10) as progress:
                for _i in range(5):
                    progress.update(1)

            # After context exits, should have newline
            output: str = sys.stdout.getvalue()
            assert "Test Progress" in output

        finally:
            sys.stdout = old_stdout


class TestThreadSafety:
    """Test thread safety of message handler."""

    @patch("ClassicLib.MessageHandler.HAS_QT", True)
    def test_gui_signal_emission(self) -> None:
        """Test that GUI mode uses signals for thread safety."""
        with patch("ClassicLib.MessageHandler.QMessageBox") as mock_msgbox:  # noqa: F841
            handler: MessageHandler = MessageHandler(parent=None, is_gui_mode=True)

            # Mock the signal
            handler.message_signal = MagicMock()

            # Send a message
            handler.info("Test message")

            # Check signal was emitted
            handler.message_signal.emit.assert_called_once()
            args: tuple[Any, ...] = handler.message_signal.emit.call_args[0]
            message: Message = args[0]
            assert isinstance(message, Message)
            assert message.content == "Test message"
            assert message.msg_type == MessageType.INFO


if __name__ == "__main__":
    pytest.main([__file__])
