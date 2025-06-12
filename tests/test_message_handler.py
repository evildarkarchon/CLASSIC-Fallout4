"""Tests for the MessageHandler module."""

import sys
from io import StringIO
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
    
    def test_init_cli_mode(self):
        """Test initialization in CLI mode."""
        handler = MessageHandler(parent=None, is_gui_mode=False)
        assert handler.is_gui_mode is False
        assert handler.parent is None
    
    @patch('ClassicLib.MessageHandler.HAS_QT', True)
    def test_init_gui_mode(self):
        """Test initialization in GUI mode."""
        mock_parent = MagicMock()
        handler = MessageHandler(parent=mock_parent, is_gui_mode=True)
        assert handler.is_gui_mode is True
        assert handler.parent == mock_parent
    
    def test_should_display_logic(self):
        """Test message display logic based on target and mode."""
        # CLI mode handler
        cli_handler = MessageHandler(parent=None, is_gui_mode=False)
        assert cli_handler._should_display(MessageTarget.ALL) is True
        assert cli_handler._should_display(MessageTarget.CLI_ONLY) is True
        assert cli_handler._should_display(MessageTarget.GUI_ONLY) is False
        assert cli_handler._should_display(MessageTarget.LOG_ONLY) is False
        
        # GUI mode handler (mocked)
        with patch('ClassicLib.MessageHandler.HAS_QT', True):
            gui_handler = MessageHandler(parent=None, is_gui_mode=True)
            assert gui_handler._should_display(MessageTarget.ALL) is True
            assert gui_handler._should_display(MessageTarget.CLI_ONLY) is False
            assert gui_handler._should_display(MessageTarget.GUI_ONLY) is True
            assert gui_handler._should_display(MessageTarget.LOG_ONLY) is False
    
    def test_cli_message_output(self):
        """Test CLI message output formatting."""
        handler = MessageHandler(parent=None, is_gui_mode=False)
        
        # Capture stdout
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            # Test info message
            sys.stdout = StringIO()
            handler.info("Test info message")
            output = sys.stdout.getvalue()
            assert "Test info message" in output
            assert "❌" not in output  # No error emoji
            
            # Test error message
            sys.stderr = StringIO()
            handler.error("Test error message")
            output = sys.stderr.getvalue()
            assert "❌ Test error message" in output
            
            # Test success message
            sys.stdout = StringIO()
            handler.success("Test success message")
            output = sys.stdout.getvalue()
            assert "✅ Test success message" in output
            
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def test_message_with_details(self):
        """Test messages with details."""
        handler = MessageHandler(parent=None, is_gui_mode=False)
        
        old_stdout = sys.stdout
        try:
            sys.stdout = StringIO()
            handler.info("Main message", details="Additional details here")
            output = sys.stdout.getvalue()
            assert "Main message" in output
            assert "Details: Additional details here" in output
        finally:
            sys.stdout = old_stdout
    
    def test_message_targets(self):
        """Test message targeting."""
        handler = MessageHandler(parent=None, is_gui_mode=False)
        
        old_stdout = sys.stdout
        try:
            # CLI_ONLY message should show in CLI mode
            sys.stdout = StringIO()
            handler.info("CLI only", target=MessageTarget.CLI_ONLY)
            output = sys.stdout.getvalue()
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
    
    def test_progress_bar_with_total(self):
        """Test progress bar with known total."""
        old_stdout = sys.stdout
        try:
            sys.stdout = StringIO()
            
            progress = CLIProgressBar("Testing", total=10)
            progress.update(5)
            output = sys.stdout.getvalue()
            
            assert "Testing" in output
            assert "50%" in output
            assert "█" in output  # Progress bar character
            
            progress.close()
            
        finally:
            sys.stdout = old_stdout
    
    def test_progress_bar_without_total(self):
        """Test progress bar without known total."""
        old_stdout = sys.stdout
        try:
            sys.stdout = StringIO()
            
            progress = CLIProgressBar("Processing")
            progress.update(5)
            output = sys.stdout.getvalue()
            
            assert "Processing" in output
            assert "5 items processed" in output
            
            progress.close()
            
        finally:
            sys.stdout = old_stdout
    
    def test_progress_bar_description_update(self):
        """Test updating progress bar description."""
        progress = CLIProgressBar("Initial", total=10)
        progress.set_description("Updated")
        assert progress.desc == "Updated"


class TestGlobalFunctions:
    """Test cases for global convenience functions."""
    
    def test_init_and_get_handler(self):
        """Test initializing and getting global handler."""
        # Clear any existing handler
        import ClassicLib.MessageHandler
        ClassicLib.MessageHandler._message_handler = None
        
        # Test get before init raises error
        with pytest.raises(RuntimeError):
            get_message_handler()
        
        # Initialize handler
        handler = init_message_handler(parent=None, is_gui_mode=False)
        assert handler is not None
        
        # Get handler should return same instance
        retrieved = get_message_handler()
        assert retrieved is handler
    
    def test_convenience_functions(self):
        """Test convenience message functions."""
        # Initialize handler
        init_message_handler(parent=None, is_gui_mode=False)
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            # Test msg_info
            sys.stdout = StringIO()
            msg_info("Info test")
            output = sys.stdout.getvalue()
            assert "Info test" in output
            
            # Test msg_error
            sys.stderr = StringIO()
            msg_error("Error test")
            output = sys.stderr.getvalue()
            assert "❌ Error test" in output
            
            # Test msg_warning
            sys.stderr = StringIO()
            msg_warning("Warning test")
            output = sys.stderr.getvalue()
            assert "⚠️ Warning test" in output
            
            # Test msg_success
            sys.stdout = StringIO()
            msg_success("Success test")
            output = sys.stdout.getvalue()
            assert "✅ Success test" in output
            
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def test_progress_context_manager(self):
        """Test progress context manager."""
        init_message_handler(parent=None, is_gui_mode=False)
        
        old_stdout = sys.stdout
        try:
            sys.stdout = StringIO()
            
            with msg_progress_context("Test Progress", 10) as progress:
                for i in range(5):
                    progress.update(1)
            
            # After context exits, should have newline
            output = sys.stdout.getvalue()
            assert "Test Progress" in output
            
        finally:
            sys.stdout = old_stdout


class TestThreadSafety:
    """Test thread safety of message handler."""
    
    @patch('ClassicLib.MessageHandler.HAS_QT', True)
    def test_gui_signal_emission(self):
        """Test that GUI mode uses signals for thread safety."""
        with patch('ClassicLib.MessageHandler.QMessageBox') as mock_msgbox:
            handler = MessageHandler(parent=None, is_gui_mode=True)
            
            # Mock the signal
            handler.message_signal = MagicMock()
            
            # Send a message
            handler.info("Test message")
            
            # Check signal was emitted
            handler.message_signal.emit.assert_called_once()
            args = handler.message_signal.emit.call_args[0]
            message = args[0]
            assert isinstance(message, Message)
            assert message.content == "Test message"
            assert message.msg_type == MessageType.INFO


if __name__ == "__main__":
    pytest.main([__file__])