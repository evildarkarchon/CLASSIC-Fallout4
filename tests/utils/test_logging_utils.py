"""
Test suite for logging utility functions in ClassicLib/Util.py.

This module contains tests for logging configuration and management.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841
import logging
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.Utils.logging_utils import configure_logging


class TestLoggingUtilities:
    """Tests for logging configuration functions."""

    def test_configure_logging_new_logger(self) -> None:
        """Test configure_logging with a fresh logger."""
        test_logger = logging.getLogger("test_classic_logger")

        # Ensure logger starts clean
        test_logger.handlers.clear()

        with patch("ClassicLib.GlobalRegistry.get_local_dir", return_value="."):  # Mock to use current dir
            configure_logging(test_logger)

        assert test_logger.level == logging.DEBUG  # Updated to match implementation
        assert len(test_logger.handlers) == 2  # File handler + console handler
        # Check handler types
        handler_types = [type(h).__name__ for h in test_logger.handlers]
        assert "FileHandler" in handler_types
        assert "StreamHandler" in handler_types

    def test_configure_logging_existing_handlers(self) -> None:
        """Test configure_logging with logger that already has handlers."""
        test_logger = logging.getLogger("test_classic_logger_existing")

        # Add a handler first
        existing_handler = logging.StreamHandler()
        test_logger.addHandler(existing_handler)

        with patch("ClassicLib.GlobalRegistry.get_local_dir", return_value="."):
            configure_logging(test_logger)

        # Should replace existing handlers (implementation clears them)
        assert len(test_logger.handlers) == 2  # New file and console handlers

    @patch("ClassicLib.GlobalRegistry.get_local_dir")
    def test_configure_logging_creates_log_directory(self, mock_get_local_dir: MagicMock) -> None:
        """Test configure_logging creates log directory structure."""
        test_logger = logging.getLogger("test_classic_logger_logdir")
        test_logger.handlers.clear()

        mock_get_local_dir.return_value = "."

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            configure_logging(test_logger)
            # Verify log directory creation was attempted
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("ClassicLib.GlobalRegistry.get_local_dir")
    def test_configure_logging_file_handler_format(self, mock_get_local_dir: MagicMock) -> None:
        """Test configure_logging sets correct file handler format."""
        test_logger = logging.getLogger("test_classic_logger_file_format")
        test_logger.handlers.clear()

        mock_get_local_dir.return_value = "."
        configure_logging(test_logger)

        # Find file handler
        file_handler = None
        for handler in test_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                file_handler = handler
                break

        assert file_handler is not None
        assert file_handler.level == logging.DEBUG
        # Check formatter includes expected components
        assert file_handler.formatter is not None
        fmt = file_handler.formatter._fmt
        assert fmt is not None
        assert "%(asctime)s" in fmt
        assert "%(levelname)s" in fmt

    @patch("ClassicLib.GlobalRegistry.get_local_dir")
    def test_configure_logging_console_handler_level(self, mock_get_local_dir: MagicMock) -> None:
        """Test configure_logging sets correct console handler level."""
        test_logger = logging.getLogger("test_classic_logger_console_level")
        test_logger.handlers.clear()

        mock_get_local_dir.return_value = "."
        configure_logging(test_logger)

        # Find console handler
        console_handler = None
        for handler in test_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                console_handler = handler
                break

        assert console_handler is not None
        assert console_handler.level == logging.WARNING

    @patch("ClassicLib.GlobalRegistry.get_local_dir")
    @patch("sys.stderr")
    def test_configure_logging_handles_file_creation_error(self, mock_stderr: MagicMock, mock_get_local_dir: MagicMock) -> None:
        """Test configure_logging handles file creation errors gracefully."""
        test_logger = logging.getLogger("test_classic_logger_file_error")
        test_logger.handlers.clear()

        # Make get_local_dir raise an exception
        mock_get_local_dir.side_effect = Exception("Cannot access local dir")

        # Should not raise, but continue with console only
        configure_logging(test_logger)

        # Should have console handler only
        assert len(test_logger.handlers) == 1
        assert isinstance(test_logger.handlers[0], logging.StreamHandler)

    def test_configure_logging_formatter(self) -> None:
        """Test that configure_logging sets proper formatter."""
        test_logger = logging.getLogger("test_classic_logger_formatter")
        test_logger.handlers.clear()

        with patch("ClassicLib.GlobalRegistry.get_local_dir", return_value="."):
            configure_logging(test_logger)

        # Check both handlers have formatters
        for handler in test_logger.handlers:
            assert handler.formatter is not None
            fmt = handler.formatter._fmt
            assert fmt is not None
            if isinstance(handler, logging.FileHandler):
                # File handler should have detailed format
                assert "%(asctime)s" in fmt
                assert "%(name)s" in fmt
            else:
                # Console handler should have simple format
                assert "%(levelname)s" in fmt

    def test_configure_logging_multiple_calls(self) -> None:
        """Test multiple calls to configure_logging."""
        test_logger = logging.getLogger("test_classic_logger_multiple")
        test_logger.handlers.clear()

        with patch("ClassicLib.GlobalRegistry.get_local_dir", return_value="."):
            configure_logging(test_logger)
            first_call_count = len(test_logger.handlers)

            # Call again
            configure_logging(test_logger)

            # Should have same number of handlers (clears and recreates)
            assert len(test_logger.handlers) == first_call_count


if __name__ == "__main__":
    pytest.main([__file__])
