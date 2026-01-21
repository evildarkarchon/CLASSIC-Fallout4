"""Unit tests for MessageHandler output backends.

This module tests the output backend implementations including CLIBackend,
LogBackend, GUIBackend, and the OutputBackend protocol.
"""

from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

# --- OutputBackend Protocol Tests ---


class TestOutputBackendProtocol:
    """Tests for OutputBackend protocol compliance."""

    @pytest.mark.unit
    def test_protocol_is_runtime_checkable(self) -> None:
        """OutputBackend should be runtime checkable."""
        from ClassicLib.MessageHandler.output.base import OutputBackend

        assert hasattr(OutputBackend, "__protocol_attrs__") or hasattr(OutputBackend, "_is_runtime_protocol")

    @pytest.mark.unit
    def test_cli_backend_implements_protocol(self) -> None:
        """CLIBackend should implement OutputBackend protocol."""
        from ClassicLib.MessageHandler.output.base import OutputBackend
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        backend = CLIBackend()

        assert isinstance(backend, OutputBackend)

    @pytest.mark.unit
    def test_log_backend_implements_protocol(self) -> None:
        """LogBackend should implement OutputBackend protocol."""
        from ClassicLib.MessageHandler.output.base import OutputBackend
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        backend = LogBackend()

        assert isinstance(backend, OutputBackend)


# --- CLIBackend Tests ---


class TestCLIBackendInit:
    """Tests for CLIBackend initialization."""

    @pytest.mark.unit
    def test_cli_backend_has_prefix_map(self) -> None:
        """CLIBackend should have PREFIX_MAP class attribute."""
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        assert hasattr(CLIBackend, "PREFIX_MAP")
        assert isinstance(CLIBackend.PREFIX_MAP, dict)

    @pytest.mark.unit
    def test_prefix_map_contains_all_message_types(self) -> None:
        """PREFIX_MAP should contain entries for all message types."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        for msg_type in MessageType:
            assert msg_type in CLIBackend.PREFIX_MAP

    @pytest.mark.unit
    def test_is_available_returns_true(self) -> None:
        """is_available should always return True for CLI."""
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        backend = CLIBackend()

        assert backend.is_available() is True


class TestCLIBackendShow:
    """Tests for CLIBackend.show() method."""

    @pytest.mark.unit
    def test_show_prints_message_content(self) -> None:
        """show should print message content to stdout."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        backend = CLIBackend()
        message = Message("Test message content", MessageType.INFO)

        with patch("builtins.print") as mock_print:
            backend.show(message)

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Test message content" in call_args

    @pytest.mark.unit
    def test_show_appends_details_when_present(self) -> None:
        """show should append details with indentation."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        backend = CLIBackend()
        message = Message("Main content", MessageType.INFO, details="Extra details")

        with patch("builtins.print") as mock_print:
            backend.show(message)

        call_args = mock_print.call_args[0][0]
        assert "Main content" in call_args
        assert "Details:" in call_args
        assert "Extra details" in call_args

    @pytest.mark.unit
    def test_show_uses_stderr_for_errors(self) -> None:
        """show should use stderr for ERROR messages."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        backend = CLIBackend()
        message = Message("Error occurred", MessageType.ERROR)

        with patch("builtins.print") as mock_print:
            backend.show(message)

        mock_print.assert_called_once()
        call_kwargs = mock_print.call_args[1]
        assert call_kwargs.get("file") == sys.stderr

    @pytest.mark.unit
    def test_show_uses_stderr_for_warnings(self) -> None:
        """show should use stderr for WARNING messages."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        backend = CLIBackend()
        message = Message("Warning issued", MessageType.WARNING)

        with patch("builtins.print") as mock_print:
            backend.show(message)

        call_kwargs = mock_print.call_args[1]
        assert call_kwargs.get("file") == sys.stderr

    @pytest.mark.unit
    def test_show_uses_stderr_for_critical(self) -> None:
        """show should use stderr for CRITICAL messages."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        backend = CLIBackend()
        message = Message("Critical failure", MessageType.CRITICAL)

        with patch("builtins.print") as mock_print:
            backend.show(message)

        call_kwargs = mock_print.call_args[1]
        assert call_kwargs.get("file") == sys.stderr

    @pytest.mark.unit
    def test_show_uses_stdout_for_success(self) -> None:
        """show should use stdout for SUCCESS messages."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        backend = CLIBackend()
        message = Message("Operation succeeded", MessageType.SUCCESS)

        with patch("builtins.print") as mock_print:
            backend.show(message)

        # SUCCESS should not use stderr
        call_kwargs = mock_print.call_args[1]
        assert call_kwargs.get("file") is None or call_kwargs.get("file") == sys.stdout

    @pytest.mark.unit
    def test_show_falls_back_to_stdout_on_stderr_error(self) -> None:
        """show should fall back to stdout if stderr fails."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        backend = CLIBackend()
        message = Message("Error message", MessageType.ERROR)

        call_count = 0

        def mock_print_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("file") == sys.stderr:
                raise OSError("stderr unavailable")

        with patch("builtins.print", side_effect=mock_print_side_effect):
            backend.show(message)

        # Should have been called twice: once for stderr (failed), once for fallback
        assert call_count == 2


class TestCLIBackendEmojiHandling:
    """Tests for CLIBackend emoji stripping on Windows."""

    @pytest.mark.unit
    def test_strips_emojis_on_windows(self) -> None:
        """show should strip emojis on Windows platform."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        backend = CLIBackend()
        message = Message("Test 🎉 message", MessageType.INFO)

        # Mock as Windows platform
        with patch.object(CLIBackend, "_STRIP_EMOJI", True):
            with patch("builtins.print") as mock_print:
                backend.show(message)

                call_args = mock_print.call_args[0][0]
                assert "🎉" not in call_args

    @pytest.mark.unit
    def test_preserves_emojis_on_non_windows(self) -> None:
        """show should preserve emojis on non-Windows platforms."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.cli_backend import CLIBackend

        backend = CLIBackend()
        message = Message("Test 🎉 message", MessageType.INFO)

        # Mock as non-Windows platform
        with patch.object(CLIBackend, "_STRIP_EMOJI", False):
            with patch("builtins.print") as mock_print:
                backend.show(message)

                call_args = mock_print.call_args[0][0]
                assert "🎉" in call_args


# --- LogBackend Tests ---


class TestLogBackendInit:
    """Tests for LogBackend initialization."""

    @pytest.mark.unit
    def test_uses_default_logger(self) -> None:
        """LogBackend should use CLASSIC.MessageHandler logger by default."""
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        backend = LogBackend()

        assert backend._logger.name == "CLASSIC.MessageHandler"

    @pytest.mark.unit
    def test_accepts_custom_logger(self) -> None:
        """LogBackend should accept custom logger."""
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        custom_logger = logging.getLogger("Custom.Logger")
        backend = LogBackend(logger=custom_logger)

        assert backend._logger is custom_logger

    @pytest.mark.unit
    def test_has_level_map(self) -> None:
        """LogBackend should have LEVEL_MAP class attribute."""
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        assert hasattr(LogBackend, "LEVEL_MAP")
        assert isinstance(LogBackend.LEVEL_MAP, dict)

    @pytest.mark.unit
    def test_level_map_contains_all_message_types(self) -> None:
        """LEVEL_MAP should contain entries for all message types."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        for msg_type in MessageType:
            assert msg_type in LogBackend.LEVEL_MAP

    @pytest.mark.unit
    def test_is_available_returns_true(self) -> None:
        """is_available should always return True for logging."""
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        backend = LogBackend()

        assert backend.is_available() is True


class TestLogBackendShow:
    """Tests for LogBackend.show() method."""

    @pytest.mark.unit
    def test_show_logs_info_at_info_level(self) -> None:
        """show should log INFO messages at INFO level."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        mock_logger = MagicMock()
        backend = LogBackend(logger=mock_logger)
        message = Message("Test info", MessageType.INFO)

        backend.show(message)

        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.INFO

    @pytest.mark.unit
    def test_show_logs_warning_at_warning_level(self) -> None:
        """show should log WARNING messages at WARNING level."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        mock_logger = MagicMock()
        backend = LogBackend(logger=mock_logger)
        message = Message("Test warning", MessageType.WARNING)

        backend.show(message)

        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.WARNING

    @pytest.mark.unit
    def test_show_logs_error_at_error_level(self) -> None:
        """show should log ERROR messages at ERROR level."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        mock_logger = MagicMock()
        backend = LogBackend(logger=mock_logger)
        message = Message("Test error", MessageType.ERROR)

        backend.show(message)

        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.ERROR

    @pytest.mark.unit
    def test_show_logs_critical_at_critical_level(self) -> None:
        """show should log CRITICAL messages at CRITICAL level."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        mock_logger = MagicMock()
        backend = LogBackend(logger=mock_logger)
        message = Message("Test critical", MessageType.CRITICAL)

        backend.show(message)

        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.CRITICAL

    @pytest.mark.unit
    def test_show_logs_debug_at_debug_level(self) -> None:
        """show should log DEBUG messages at DEBUG level."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        mock_logger = MagicMock()
        backend = LogBackend(logger=mock_logger)
        message = Message("Test debug", MessageType.DEBUG)

        backend.show(message)

        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.DEBUG

    @pytest.mark.unit
    def test_show_logs_success_at_info_level(self) -> None:
        """show should log SUCCESS messages at INFO level."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        mock_logger = MagicMock()
        backend = LogBackend(logger=mock_logger)
        message = Message("Test success", MessageType.SUCCESS)

        backend.show(message)

        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.INFO

    @pytest.mark.unit
    def test_show_formats_message_with_details(self) -> None:
        """show should format message with details."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        mock_logger = MagicMock()
        backend = LogBackend(logger=mock_logger)
        message = Message("Main content", MessageType.INFO, details="Extra info")

        backend.show(message)

        call_args = mock_logger.log.call_args
        log_text = call_args[0][1]
        assert "Main content" in log_text
        assert "Extra info" in log_text


class TestLogBackendSetLogger:
    """Tests for LogBackend.set_logger() method."""

    @pytest.mark.unit
    def test_set_logger_updates_logger(self) -> None:
        """set_logger should update the internal logger."""
        from ClassicLib.MessageHandler.output.log_backend import LogBackend

        backend = LogBackend()
        new_logger = logging.getLogger("New.Logger")

        backend.set_logger(new_logger)

        assert backend._logger is new_logger


# --- GUIBackend Tests ---


class TestGUIBackendInit:
    """Tests for GUIBackend initialization."""

    @pytest.mark.unit
    def test_gui_backend_requires_qt(self) -> None:
        """GUIBackend should import PySide6."""
        # This test verifies the import exists
        from ClassicLib.MessageHandler.output.gui_backend import GUIBackend

        assert GUIBackend is not None

    @pytest.mark.unit
    def test_has_icon_map(self) -> None:
        """GUIBackend should have ICON_MAP class attribute."""
        from ClassicLib.MessageHandler.output.gui_backend import GUIBackend

        assert hasattr(GUIBackend, "ICON_MAP")
        assert isinstance(GUIBackend.ICON_MAP, dict)

    @pytest.mark.unit
    def test_icon_map_contains_all_message_types(self) -> None:
        """ICON_MAP should contain entries for all message types."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.output.gui_backend import GUIBackend

        for msg_type in MessageType:
            assert msg_type in GUIBackend.ICON_MAP


class TestGUIBackendShow:
    """Tests for GUIBackend.show() method."""

    @pytest.mark.unit
    def test_show_emits_message_signal(self) -> None:
        """show should emit message_signal."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.output.gui_backend import GUIBackend

        # Create backend with mocked signal
        backend = GUIBackend()
        backend.message_signal = MagicMock()

        message = Message("Test message", MessageType.INFO)
        backend.show(message)

        backend.message_signal.emit.assert_called_once_with(message)


class TestGUIBackendIsAvailable:
    """Tests for GUIBackend.is_available() method."""

    @pytest.mark.unit
    def test_is_available_true_when_qapp_exists(self) -> None:
        """is_available should return True when QApplication exists."""
        from ClassicLib.MessageHandler.output.gui_backend import GUIBackend

        backend = GUIBackend()

        # The import happens inside is_available, so we patch the import target
        with patch("PySide6.QtWidgets.QApplication") as mock_qapp:
            mock_qapp.instance.return_value = MagicMock()

            result = backend.is_available()

            assert result is True

    @pytest.mark.unit
    def test_is_available_false_when_no_qapp(self) -> None:
        """is_available should return False when no QApplication."""
        from ClassicLib.MessageHandler.output.gui_backend import GUIBackend

        backend = GUIBackend()

        with patch("PySide6.QtWidgets.QApplication") as mock_qapp:
            mock_qapp.instance.return_value = None

            result = backend.is_available()

            assert result is False


class TestGUIBackendSetParent:
    """Tests for GUIBackend.set_parent() method."""

    @pytest.mark.unit
    def test_set_parent_updates_parent(self) -> None:
        """set_parent should update the parent widget."""
        from ClassicLib.MessageHandler.output.gui_backend import GUIBackend

        backend = GUIBackend()
        mock_parent = MagicMock()

        backend.set_parent(mock_parent)

        assert backend._parent is mock_parent

    @pytest.mark.unit
    def test_set_parent_accepts_none(self) -> None:
        """set_parent should accept None."""
        from ClassicLib.MessageHandler.output.gui_backend import GUIBackend

        backend = GUIBackend()
        backend._parent = MagicMock()

        backend.set_parent(None)

        assert backend._parent is None


# --- Router Tests ---


class TestMessageRouter:
    """Tests for MessageRouter class."""

    @pytest.mark.unit
    def test_router_initializes_in_cli_mode_by_default(self) -> None:
        """MessageRouter should default to CLI mode."""
        from ClassicLib.MessageHandler.core.router import MessageRouter

        router = MessageRouter()

        assert router.is_gui_mode is False

    @pytest.mark.unit
    def test_router_initializes_in_gui_mode_when_specified(self) -> None:
        """MessageRouter should accept GUI mode flag."""
        from ClassicLib.MessageHandler.core.router import MessageRouter

        router = MessageRouter(is_gui_mode=True)

        assert router.is_gui_mode is True


class TestMessageRouterShouldDisplay:
    """Tests for MessageRouter.should_display() method."""

    @pytest.mark.unit
    def test_log_only_never_displays(self) -> None:
        """LOG_ONLY should never display."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget
        from ClassicLib.MessageHandler.core.router import MessageRouter

        cli_router = MessageRouter(is_gui_mode=False)
        gui_router = MessageRouter(is_gui_mode=True)

        assert cli_router.should_display(MessageTarget.LOG_ONLY) is False
        assert gui_router.should_display(MessageTarget.LOG_ONLY) is False

    @pytest.mark.unit
    def test_gui_target_displays_in_gui_mode_only(self) -> None:
        """GUI target should only display in GUI mode."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget
        from ClassicLib.MessageHandler.core.router import MessageRouter

        cli_router = MessageRouter(is_gui_mode=False)
        gui_router = MessageRouter(is_gui_mode=True)

        assert cli_router.should_display(MessageTarget.GUI) is False
        assert gui_router.should_display(MessageTarget.GUI) is True

    @pytest.mark.unit
    def test_console_target_displays_in_cli_mode_only(self) -> None:
        """CONSOLE target should only display in CLI mode."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget
        from ClassicLib.MessageHandler.core.router import MessageRouter

        cli_router = MessageRouter(is_gui_mode=False)
        gui_router = MessageRouter(is_gui_mode=True)

        assert cli_router.should_display(MessageTarget.CONSOLE) is True
        assert gui_router.should_display(MessageTarget.CONSOLE) is False

    @pytest.mark.unit
    def test_all_target_displays_in_both_modes(self) -> None:
        """ALL target should display in both modes."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget
        from ClassicLib.MessageHandler.core.router import MessageRouter

        cli_router = MessageRouter(is_gui_mode=False)
        gui_router = MessageRouter(is_gui_mode=True)

        assert cli_router.should_display(MessageTarget.ALL) is True
        assert gui_router.should_display(MessageTarget.ALL) is True


class TestMessageRouterGetDisplayMode:
    """Tests for MessageRouter.get_display_mode() method."""

    @pytest.mark.unit
    def test_log_only_returns_none(self) -> None:
        """LOG_ONLY should return None."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget
        from ClassicLib.MessageHandler.core.router import MessageRouter

        router = MessageRouter()

        assert router.get_display_mode(MessageTarget.LOG_ONLY) is None

    @pytest.mark.unit
    def test_gui_returns_gui(self) -> None:
        """GUI should return 'gui'."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget
        from ClassicLib.MessageHandler.core.router import MessageRouter

        router = MessageRouter()

        assert router.get_display_mode(MessageTarget.GUI) == "gui"

    @pytest.mark.unit
    def test_console_returns_cli(self) -> None:
        """CONSOLE should return 'cli'."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget
        from ClassicLib.MessageHandler.core.router import MessageRouter

        router = MessageRouter()

        assert router.get_display_mode(MessageTarget.CONSOLE) == "cli"

    @pytest.mark.unit
    def test_all_returns_both(self) -> None:
        """ALL should return 'both'."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget
        from ClassicLib.MessageHandler.core.router import MessageRouter

        router = MessageRouter()

        assert router.get_display_mode(MessageTarget.ALL) == "both"
