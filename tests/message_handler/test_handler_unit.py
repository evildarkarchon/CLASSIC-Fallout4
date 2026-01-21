"""Unit tests for MessageHandler handler module.

This module tests the MessageHandler class, including message routing,
convenience functions, global handler management, and cancellation state.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


# --- Fixtures ---


@pytest.fixture
def fresh_handler_state() -> Generator[None, None, None]:
    """Ensure fresh MessageHandler state before and after each test.

    Yields:
        None after resetting the global handler state.

    """
    from ClassicLib.MessageHandler import handler as handler_module

    # Reset before test
    with handler_module._message_handler_lock:
        handler_module._message_handler = None

    yield

    # Reset after test
    with handler_module._message_handler_lock:
        handler_module._message_handler = None


@pytest.fixture
def mock_log_backend() -> MagicMock:
    """Create a mock log backend.

    Returns:
        A MagicMock configured as a log backend.

    """
    mock = MagicMock()
    mock.show = MagicMock()
    mock.is_available.return_value = True
    return mock


@pytest.fixture
def mock_cli_backend() -> MagicMock:
    """Create a mock CLI backend.

    Returns:
        A MagicMock configured as a CLI backend.

    """
    mock = MagicMock()
    mock.show = MagicMock()
    mock.is_available.return_value = True
    return mock


# --- MessageHandler Class Tests ---


class TestMessageHandlerInit:
    """Tests for MessageHandler initialization."""

    @pytest.mark.unit
    def test_handler_initializes_in_cli_mode_by_default(self) -> None:
        """MessageHandler should initialize in CLI mode by default."""
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()

        assert handler.is_gui_mode is False
        assert handler.parent_widget is None

    @pytest.mark.unit
    def test_handler_initializes_in_gui_mode_when_specified(self) -> None:
        """MessageHandler should set gui mode flag when requested."""
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler(is_gui_mode=True)

        assert handler.is_gui_mode is True

    @pytest.mark.unit
    def test_handler_stores_main_thread_reference(self) -> None:
        """MessageHandler should store reference to current thread."""
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()

        assert handler.main_thread == threading.current_thread()

    @pytest.mark.unit
    def test_handler_creates_internal_logger(self) -> None:
        """MessageHandler should create CLASSIC.MessageHandler logger."""
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()

        assert handler._logger.name == "CLASSIC.MessageHandler"


class TestMessageHandlerShow:
    """Tests for MessageHandler.show() method."""

    @pytest.mark.unit
    def test_show_logs_message_always(self, mock_log_backend: MagicMock) -> None:
        """show() should always log messages regardless of target."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget, MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()
        handler._log_backend = mock_log_backend

        message = Message("Test content", MessageType.INFO, target=MessageTarget.CONSOLE)
        handler.show(message)

        mock_log_backend.show.assert_called_once_with(message)

    @pytest.mark.unit
    def test_show_routes_to_cli_backend_in_cli_mode(
        self, mock_log_backend: MagicMock, mock_cli_backend: MagicMock
    ) -> None:
        """show() should route to CLI backend when in CLI mode."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget, MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler(is_gui_mode=False)
        handler._log_backend = mock_log_backend
        handler._cli_backend = mock_cli_backend

        message = Message("Test content", MessageType.INFO, target=MessageTarget.ALL)
        handler.show(message)

        mock_cli_backend.show.assert_called_once_with(message)

    @pytest.mark.unit
    def test_show_skips_display_for_log_only_target(
        self, mock_log_backend: MagicMock, mock_cli_backend: MagicMock
    ) -> None:
        """show() should not display LOG_ONLY messages."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget, MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()
        handler._log_backend = mock_log_backend
        handler._cli_backend = mock_cli_backend

        message = Message("Test content", MessageType.INFO, target=MessageTarget.LOG_ONLY)
        handler.show(message)

        # Log should be called
        mock_log_backend.show.assert_called_once()
        # CLI should NOT be called
        mock_cli_backend.show.assert_not_called()

    @pytest.mark.unit
    def test_show_skips_gui_target_in_cli_mode(
        self, mock_log_backend: MagicMock, mock_cli_backend: MagicMock
    ) -> None:
        """show() should not display GUI-targeted messages in CLI mode."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget, MessageType
        from ClassicLib.MessageHandler.core.message import Message
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler(is_gui_mode=False)
        handler._log_backend = mock_log_backend
        handler._cli_backend = mock_cli_backend

        message = Message("Test content", MessageType.INFO, target=MessageTarget.GUI)
        handler.show(message)

        # CLI should NOT be called for GUI-targeted messages
        mock_cli_backend.show.assert_not_called()


class TestMessageHandlerConvenienceMethods:
    """Tests for MessageHandler convenience methods (info, warning, error, etc.)."""

    @pytest.mark.unit
    def test_info_creates_info_message(self) -> None:
        """info() should create and show INFO message."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()
        handler.show = MagicMock()  # type: ignore[method-assign]

        handler.info("Test info")

        handler.show.assert_called_once()
        message = handler.show.call_args[0][0]
        assert message.content == "Test info"
        assert message.msg_type == MessageType.INFO

    @pytest.mark.unit
    def test_warning_creates_warning_message(self) -> None:
        """warning() should create and show WARNING message."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()
        handler.show = MagicMock()  # type: ignore[method-assign]

        handler.warning("Test warning")

        message = handler.show.call_args[0][0]
        assert message.msg_type == MessageType.WARNING

    @pytest.mark.unit
    def test_error_creates_error_message(self) -> None:
        """error() should create and show ERROR message."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()
        handler.show = MagicMock()  # type: ignore[method-assign]

        handler.error("Test error")

        message = handler.show.call_args[0][0]
        assert message.msg_type == MessageType.ERROR

    @pytest.mark.unit
    def test_success_creates_success_message(self) -> None:
        """success() should create and show SUCCESS message."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()
        handler.show = MagicMock()  # type: ignore[method-assign]

        handler.success("Test success")

        message = handler.show.call_args[0][0]
        assert message.msg_type == MessageType.SUCCESS

    @pytest.mark.unit
    def test_debug_creates_debug_message(self) -> None:
        """debug() should create and show DEBUG message."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()
        handler.show = MagicMock()  # type: ignore[method-assign]

        handler.debug("Test debug")

        message = handler.show.call_args[0][0]
        assert message.msg_type == MessageType.DEBUG

    @pytest.mark.unit
    def test_critical_creates_critical_message(self) -> None:
        """critical() should create and show CRITICAL message."""
        from ClassicLib.MessageHandler.core.enums import MessageType
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()
        handler.show = MagicMock()  # type: ignore[method-assign]

        handler.critical("Test critical")

        message = handler.show.call_args[0][0]
        assert message.msg_type == MessageType.CRITICAL

    @pytest.mark.unit
    def test_convenience_methods_pass_kwargs_to_message(self) -> None:
        """Convenience methods should pass kwargs to Message."""
        from ClassicLib.MessageHandler.core.enums import MessageTarget
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()
        handler.show = MagicMock()  # type: ignore[method-assign]

        handler.info("Test", target=MessageTarget.CONSOLE, title="Custom Title")

        message = handler.show.call_args[0][0]
        assert message.target == MessageTarget.CONSOLE
        assert message.title == "Custom Title"


class TestMessageHandlerCancellation:
    """Tests for MessageHandler cancellation state."""

    @pytest.mark.unit
    def test_is_cancelled_returns_false_by_default(self) -> None:
        """is_cancelled() should return False initially."""
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()

        assert handler.is_cancelled() is False

    @pytest.mark.unit
    def test_set_cancelled_updates_state(self) -> None:
        """_set_cancelled() should update the cancellation state."""
        from ClassicLib.MessageHandler.handler import MessageHandler

        handler = MessageHandler()

        handler._set_cancelled(True)
        assert handler.is_cancelled() is True

        handler._set_cancelled(False)
        assert handler.is_cancelled() is False


class TestMessageHandlerProgressContext:
    """Tests for MessageHandler.progress_context()."""

    @pytest.mark.unit
    def test_progress_context_returns_progress_context_instance(self) -> None:
        """progress_context() should return a ProgressContext instance."""
        from ClassicLib.MessageHandler.handler import MessageHandler
        from ClassicLib.MessageHandler.progress.context import ProgressContext

        handler = MessageHandler()

        context = handler.progress_context("Testing", total=100)

        assert isinstance(context, ProgressContext)
        assert context.description == "Testing"
        assert context.total == 100

    @pytest.mark.unit
    def test_create_progress_handler_returns_cli_handler(self) -> None:
        """create_progress_handler() should return CLIProgressHandler."""
        from ClassicLib.MessageHandler.handler import MessageHandler
        from ClassicLib.MessageHandler.progress.cli_progress import CLIProgressHandler

        handler = MessageHandler()

        progress_handler = handler.create_progress_handler()

        assert isinstance(progress_handler, CLIProgressHandler)


# --- Global Handler Management Tests ---


class TestInitMessageHandler:
    """Tests for init_message_handler function."""

    @pytest.mark.unit
    def test_init_creates_base_handler_for_cli_mode(
        self, fresh_handler_state: None
    ) -> None:
        """init_message_handler should create base MessageHandler for CLI mode."""
        from ClassicLib.MessageHandler.handler import MessageHandler, init_message_handler

        handler = init_message_handler(is_gui_mode=False)

        assert isinstance(handler, MessageHandler)
        assert handler.is_gui_mode is False

    @pytest.mark.unit
    def test_init_creates_qt_handler_for_gui_mode(
        self, fresh_handler_state: None
    ) -> None:
        """init_message_handler should create QtMessageHandler for GUI mode."""
        from ClassicLib.MessageHandler.handler import init_message_handler

        # Mock the QtMessageHandler import since it requires Qt
        with patch(
            "ClassicLib.MessageHandler.qt_handler.QtMessageHandler"
        ) as mock_qt_handler:
            mock_instance = MagicMock()
            mock_qt_handler.return_value = mock_instance

            handler = init_message_handler(parent=None, is_gui_mode=True)

            mock_qt_handler.assert_called_once_with(None)
            assert handler is mock_instance


class TestGetMessageHandler:
    """Tests for get_message_handler function."""

    @pytest.mark.unit
    def test_get_handler_raises_when_not_initialized(
        self, fresh_handler_state: None
    ) -> None:
        """get_message_handler should raise RuntimeError when not initialized."""
        from ClassicLib.MessageHandler.handler import get_message_handler

        with pytest.raises(RuntimeError, match="Message handler not initialized"):
            get_message_handler()

    @pytest.mark.unit
    def test_get_handler_returns_initialized_handler(
        self, fresh_handler_state: None
    ) -> None:
        """get_message_handler should return the initialized handler."""
        from ClassicLib.MessageHandler.handler import (
            get_message_handler,
            init_message_handler,
        )

        initialized = init_message_handler(is_gui_mode=False)
        retrieved = get_message_handler()

        assert retrieved is initialized


# --- Convenience Function Tests ---


class TestGlobalConvenienceFunctions:
    """Tests for global convenience functions (msg_info, msg_warning, etc.)."""

    @pytest.mark.unit
    def test_msg_info_calls_handler_info(self, fresh_handler_state: None) -> None:
        """msg_info should call the handler's info method."""
        from ClassicLib.MessageHandler.handler import init_message_handler, msg_info

        handler = init_message_handler(is_gui_mode=False)
        handler.info = MagicMock()  # type: ignore[method-assign]

        msg_info("Test message", title="Test Title")

        handler.info.assert_called_once_with("Test message", title="Test Title")

    @pytest.mark.unit
    def test_msg_warning_calls_handler_warning(self, fresh_handler_state: None) -> None:
        """msg_warning should call the handler's warning method."""
        from ClassicLib.MessageHandler.handler import init_message_handler, msg_warning

        handler = init_message_handler(is_gui_mode=False)
        handler.warning = MagicMock()  # type: ignore[method-assign]

        msg_warning("Test warning")

        handler.warning.assert_called_once_with("Test warning")

    @pytest.mark.unit
    def test_msg_error_calls_handler_error(self, fresh_handler_state: None) -> None:
        """msg_error should call the handler's error method."""
        from ClassicLib.MessageHandler.handler import init_message_handler, msg_error

        handler = init_message_handler(is_gui_mode=False)
        handler.error = MagicMock()  # type: ignore[method-assign]

        msg_error("Test error")

        handler.error.assert_called_once_with("Test error")

    @pytest.mark.unit
    def test_msg_success_calls_handler_success(self, fresh_handler_state: None) -> None:
        """msg_success should call the handler's success method."""
        from ClassicLib.MessageHandler.handler import init_message_handler, msg_success

        handler = init_message_handler(is_gui_mode=False)
        handler.success = MagicMock()  # type: ignore[method-assign]

        msg_success("Test success")

        handler.success.assert_called_once_with("Test success")

    @pytest.mark.unit
    def test_msg_debug_calls_handler_debug(self, fresh_handler_state: None) -> None:
        """msg_debug should call the handler's debug method."""
        from ClassicLib.MessageHandler.handler import init_message_handler, msg_debug

        handler = init_message_handler(is_gui_mode=False)
        handler.debug = MagicMock()  # type: ignore[method-assign]

        msg_debug("Test debug")

        handler.debug.assert_called_once_with("Test debug")

    @pytest.mark.unit
    def test_msg_critical_calls_handler_critical(
        self, fresh_handler_state: None
    ) -> None:
        """msg_critical should call the handler's critical method."""
        from ClassicLib.MessageHandler.handler import (
            init_message_handler,
            msg_critical,
        )

        handler = init_message_handler(is_gui_mode=False)
        handler.critical = MagicMock()  # type: ignore[method-assign]

        msg_critical("Test critical")

        handler.critical.assert_called_once_with("Test critical")


class TestMsgProgressContext:
    """Tests for msg_progress_context function."""

    @pytest.mark.unit
    def test_msg_progress_context_yields_progress_context(
        self, fresh_handler_state: None
    ) -> None:
        """msg_progress_context should yield a ProgressContext."""
        from ClassicLib.MessageHandler.handler import (
            init_message_handler,
            msg_progress_context,
        )
        from ClassicLib.MessageHandler.progress.context import ProgressContext

        init_message_handler(is_gui_mode=False)

        # Mock settings to avoid file access
        with patch(
            "ClassicLib.MessageHandler.progress.context.ProgressContext._check_cli_progress_disabled",
            return_value=True,
        ):
            with msg_progress_context("Testing", total=50) as progress:
                assert isinstance(progress, ProgressContext)
                assert progress.description == "Testing"
                assert progress.total == 50


# --- Thread Safety Tests ---


class TestMessageHandlerThreadSafety:
    """Tests for MessageHandler thread safety."""

    @pytest.mark.unit
    def test_init_handler_is_thread_safe(self, fresh_handler_state: None) -> None:
        """init_message_handler should be thread-safe."""
        from ClassicLib.MessageHandler.handler import (
            get_message_handler,
            init_message_handler,
        )

        handlers: list = []
        errors: list = []

        def init_and_get():
            try:
                init_message_handler(is_gui_mode=False)
                handlers.append(get_message_handler())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=init_and_get) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

        assert len(errors) == 0, f"Thread errors: {errors}"
        # All threads should get a handler (the same one or new ones)
        assert len(handlers) == 5
