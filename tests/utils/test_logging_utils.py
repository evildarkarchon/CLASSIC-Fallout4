"""
Test suite for logging utility functions in ClassicLib/Util.py.

This module contains tests for logging configuration and management.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841
import logging
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.Util import configure_logging


class TestLoggingUtilities:
    """Tests for logging configuration functions."""

    def test_configure_logging_new_logger(self) -> None:
        """Test configure_logging with a fresh logger."""
        test_logger = logging.getLogger("test_classic_logger")

        # Ensure logger starts clean
        test_logger.handlers.clear()

        with patch("ClassicLib.Util.msg_info"):  # Mock msg_info to avoid MessageHandler dependency
            configure_logging(test_logger)

        assert test_logger.level == logging.INFO
        assert len(test_logger.handlers) == 1
        assert isinstance(test_logger.handlers[0], logging.FileHandler)

    def test_configure_logging_existing_handlers(self) -> None:
        """Test configure_logging with logger that already has handlers."""
        test_logger = logging.getLogger("test_classic_logger_existing")

        # Add a handler first
        existing_handler = logging.StreamHandler()
        test_logger.addHandler(existing_handler)
        original_handler_count = len(test_logger.handlers)

        with patch("ClassicLib.Util.msg_info"):  # Mock msg_info to avoid MessageHandler dependency
            configure_logging(test_logger)

        # Should not add another handler
        assert len(test_logger.handlers) == original_handler_count

    @patch("ClassicLib.Util.msg_info")  # Mock msg_info to avoid MessageHandler dependency
    @patch("ClassicLib.Util.msg_error")  # Mock msg_error as well
    def test_configure_logging_old_log_file(self, mock_msg_error: MagicMock, mock_msg_info: MagicMock) -> None:  # noqa: ARG002
        """Test configure_logging removes old log file."""
        test_logger = logging.getLogger("test_classic_logger_old")
        test_logger.handlers.clear()
        test_logger.setLevel(logging.DEBUG)  # Enable DEBUG level for the test

        # Mock Path class to intercept Path("CLASSIC Journal.log") call
        with patch("ClassicLib.Util.Path") as mock_path_class:
            mock_journal_path = MagicMock()
            mock_path_class.return_value = mock_journal_path
            mock_journal_path.exists.return_value = True

            # Mock old file (8 days old)
            import time

            old_time = time.time() - (8 * 24 * 60 * 60)  # 8 days ago
            mock_stat = MagicMock()
            mock_stat.st_mtime = old_time
            mock_journal_path.stat.return_value = mock_stat

            configure_logging(test_logger)

            # Verify Path was called with the correct argument
            mock_path_class.assert_called_with("CLASSIC Journal.log")
            mock_journal_path.unlink.assert_called_once_with(missing_ok=True)

    @patch("ClassicLib.Util.msg_info")
    def test_configure_logging_recent_log_file(self, mock_msg_info: MagicMock) -> None:
        """Test configure_logging keeps recent log file."""
        test_logger = logging.getLogger("test_classic_logger_recent")
        test_logger.handlers.clear()

        with patch("ClassicLib.Util.Path") as mock_path_class:
            mock_journal_path = MagicMock()
            mock_path_class.return_value = mock_journal_path
            mock_journal_path.exists.return_value = True

            # Mock recent file (1 day old)
            import time

            recent_time = time.time() - (1 * 24 * 60 * 60)  # 1 day ago
            mock_stat = MagicMock()
            mock_stat.st_mtime = recent_time
            mock_journal_path.stat.return_value = mock_stat

            configure_logging(test_logger)

            # Should not delete recent file
            mock_journal_path.unlink.assert_not_called()

    @patch("ClassicLib.Util.msg_info")
    def test_configure_logging_no_existing_log(self, mock_msg_info: MagicMock) -> None:
        """Test configure_logging when no log file exists."""
        test_logger = logging.getLogger("test_classic_logger_no_file")
        test_logger.handlers.clear()

        with patch("ClassicLib.Util.Path") as mock_path_class:
            mock_journal_path = MagicMock()
            mock_path_class.return_value = mock_journal_path
            mock_journal_path.exists.return_value = False

            configure_logging(test_logger)

            # Should not try to delete non-existent file
            mock_journal_path.unlink.assert_not_called()

    @patch("ClassicLib.Util.msg_info")
    @patch("ClassicLib.Util.msg_error")
    def test_configure_logging_log_deletion_error(self, mock_msg_error: MagicMock, mock_msg_info: MagicMock) -> None:
        """Test configure_logging handles log deletion errors gracefully."""
        test_logger = logging.getLogger("test_classic_logger_delete_error")
        test_logger.handlers.clear()
        test_logger.setLevel(logging.DEBUG)

        with patch("ClassicLib.Util.Path") as mock_path_class:
            mock_journal_path = MagicMock()
            mock_path_class.return_value = mock_journal_path
            mock_journal_path.exists.return_value = True

            # Mock old file
            import time

            old_time = time.time() - (8 * 24 * 60 * 60)
            mock_stat = MagicMock()
            mock_stat.st_mtime = old_time
            mock_journal_path.stat.return_value = mock_stat

            # Make unlink raise an error
            mock_journal_path.unlink.side_effect = PermissionError("Access denied")

            # Should not raise, but continue
            configure_logging(test_logger)

            # Error should be logged
            mock_msg_error.assert_called()

    def test_configure_logging_formatter(self) -> None:
        """Test that configure_logging sets proper formatter."""
        test_logger = logging.getLogger("test_classic_logger_formatter")
        test_logger.handlers.clear()

        with patch("ClassicLib.Util.msg_info"):
            configure_logging(test_logger)

        handler = test_logger.handlers[0]
        formatter = handler.formatter

        assert formatter is not None
        # Check formatter pattern includes expected components
        assert "%(asctime)s" in formatter._fmt  # type: ignore
        assert "%(levelname)s" in formatter._fmt  # type: ignore

    def test_configure_logging_multiple_calls(self) -> None:
        """Test multiple calls to configure_logging."""
        test_logger = logging.getLogger("test_classic_logger_multiple")
        test_logger.handlers.clear()

        with patch("ClassicLib.Util.msg_info"):
            configure_logging(test_logger)
            initial_handler_count = len(test_logger.handlers)

            # Call again
            configure_logging(test_logger)

            # Should not add duplicate handlers
            assert len(test_logger.handlers) == initial_handler_count


if __name__ == "__main__":
    pytest.main([__file__])
