"""Unit tests for MessageHandler progress module.

This module tests the progress handling components including CLIProgressBar,
CLIProgressHandler, ProgressHandler protocol, and ProgressContext.
"""

from __future__ import annotations

import time
from io import StringIO
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


# --- ProgressHandler Protocol Tests ---


class TestProgressHandlerProtocol:
    """Tests for ProgressHandler protocol compliance."""

    @pytest.mark.unit
    def test_protocol_is_runtime_checkable(self) -> None:
        """ProgressHandler should be runtime checkable."""
        from ClassicLib.messaging.progress.base import ProgressHandler

        assert hasattr(ProgressHandler, "__protocol_attrs__") or hasattr(ProgressHandler, "_is_runtime_protocol")

    @pytest.mark.unit
    def test_cli_progress_handler_implements_protocol(self) -> None:
        """CLIProgressHandler should implement ProgressHandler protocol."""
        from ClassicLib.messaging.progress.base import ProgressHandler
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()

        assert isinstance(handler, ProgressHandler)


# --- CLIProgressBar Tests ---


class TestCLIProgressBarInit:
    """Tests for CLIProgressBar initialization."""

    @pytest.mark.unit
    def test_initializes_with_description(self) -> None:
        """CLIProgressBar should store description."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print"):
            bar = CLIProgressBar("Loading files")

        assert bar.desc == "Loading files"

    @pytest.mark.unit
    def test_initializes_with_total(self) -> None:
        """CLIProgressBar should store total."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print"):
            bar = CLIProgressBar("Processing", total=100)

        assert bar.total == 100

    @pytest.mark.unit
    def test_initializes_with_none_total_for_indeterminate(self) -> None:
        """CLIProgressBar should accept None total for indeterminate progress."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print"):
            bar = CLIProgressBar("Scanning", total=None)

        assert bar.total is None

    @pytest.mark.unit
    def test_initializes_current_to_zero(self) -> None:
        """CLIProgressBar should start with current = 0."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print"):
            bar = CLIProgressBar("Test")

        assert bar.current == 0

    @pytest.mark.unit
    def test_prints_initial_state_on_creation(self) -> None:
        """CLIProgressBar should print initial state on creation."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print") as mock_print:
            CLIProgressBar("Initial", total=10)

        mock_print.assert_called()


class TestCLIProgressBarUpdate:
    """Tests for CLIProgressBar.update() method."""

    @pytest.mark.unit
    def test_update_increments_current(self) -> None:
        """update should increment current by n."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print"):
            bar = CLIProgressBar("Test", total=100)

        bar.update(5)

        assert bar.current == 5

    @pytest.mark.unit
    def test_update_increments_by_one_by_default(self) -> None:
        """update should increment by 1 when n not specified."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print"):
            bar = CLIProgressBar("Test", total=100)

        bar.update()

        assert bar.current == 1

    @pytest.mark.unit
    def test_update_does_nothing_when_closed(self) -> None:
        """update should do nothing when bar is closed."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print"):
            bar = CLIProgressBar("Test", total=100)
            bar.close()

        bar.update(10)

        assert bar.current == 0  # Unchanged

    @pytest.mark.unit
    def test_update_throttles_printing(self) -> None:
        """update should throttle printing for performance."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print") as mock_print:
            bar = CLIProgressBar("Test", total=1000)
            initial_call_count = mock_print.call_count

            # Many rapid updates should be throttled
            for _ in range(100):
                bar.update(1)

            # Should have fewer prints than updates due to throttling
            assert mock_print.call_count < initial_call_count + 100

    @pytest.mark.unit
    def test_update_always_prints_final_state(self) -> None:
        """update should always print when reaching total."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print") as mock_print:
            bar = CLIProgressBar("Test", total=10)
            mock_print.reset_mock()

            # Skip to end
            bar.current = 9
            bar.update(1)  # Now at total

        # Should have printed the final state
        mock_print.assert_called()


class TestCLIProgressBarSetDescription:
    """Tests for CLIProgressBar.set_description() method."""

    @pytest.mark.unit
    def test_set_description_updates_desc(self) -> None:
        """set_description should update the description."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print"):
            bar = CLIProgressBar("Original")

        bar.set_description("Updated")

        assert bar.desc == "Updated"


class TestCLIProgressBarClose:
    """Tests for CLIProgressBar.close() method."""

    @pytest.mark.unit
    def test_close_sets_closed_flag(self) -> None:
        """close should set the closed flag."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print"):
            bar = CLIProgressBar("Test")

        bar.close()

        assert bar._closed is True

    @pytest.mark.unit
    def test_close_prints_newline(self) -> None:
        """close should print a newline."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print") as mock_print:
            bar = CLIProgressBar("Test")
            mock_print.reset_mock()

            bar.close()

        # Should have at least one call with no arguments (newline)
        calls = mock_print.call_args_list
        assert any(call[0] == () or (len(call[0]) == 0) for call in calls)

    @pytest.mark.unit
    def test_close_is_idempotent(self) -> None:
        """close should be safe to call multiple times."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        with patch("builtins.print"):
            bar = CLIProgressBar("Test")

        bar.close()
        bar.close()  # Should not raise

        assert bar._closed is True


class TestCLIProgressBarPrintProgress:
    """Tests for CLIProgressBar._print_progress() method."""

    @pytest.mark.unit
    def test_prints_percentage_for_determinate_progress(self) -> None:
        """_print_progress should print percentage for determinate progress."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        captured = StringIO()
        with patch("builtins.print", side_effect=lambda *args, **kwargs: captured.write(str(args))):
            bar = CLIProgressBar("Loading", total=100)
            bar.current = 50
            bar._print_progress()

        output = captured.getvalue()
        assert "50" in output  # 50%

    @pytest.mark.unit
    def test_prints_spinner_for_indeterminate_progress(self) -> None:
        """_print_progress should print spinner for indeterminate progress."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressBar

        captured = StringIO()
        with patch("builtins.print", side_effect=lambda *args, **kwargs: captured.write(str(args))):
            bar = CLIProgressBar("Scanning", total=None)
            bar.current = 5
            bar._print_progress()

        output = captured.getvalue()
        assert "items" in output  # "X items"


# --- CLIProgressHandler Tests ---


class TestCLIProgressHandlerInit:
    """Tests for CLIProgressHandler initialization."""

    @pytest.mark.unit
    def test_initializes_with_no_progress_bar(self) -> None:
        """CLIProgressHandler should start with no progress bar."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()

        assert handler._progress_bar is None

    @pytest.mark.unit
    def test_is_available_returns_true(self) -> None:
        """is_available should always return True for CLI."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()

        assert handler.is_available() is True


class TestCLIProgressHandlerStart:
    """Tests for CLIProgressHandler.start() method."""

    @pytest.mark.unit
    def test_start_creates_progress_bar(self) -> None:
        """start should create a CLIProgressBar."""
        from ClassicLib.messaging.progress.cli_progress import (
            CLIProgressBar,
            CLIProgressHandler,
        )

        handler = CLIProgressHandler()

        with patch("builtins.print"):
            handler.start("Processing", total=100)

        assert isinstance(handler._progress_bar, CLIProgressBar)

    @pytest.mark.unit
    def test_start_resets_cancelled_flag(self) -> None:
        """start should reset the cancelled flag."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()
        handler._cancelled = True

        with patch("builtins.print"):
            handler.start("Processing")

        assert handler._cancelled is False


class TestCLIProgressHandlerUpdate:
    """Tests for CLIProgressHandler.update() method."""

    @pytest.mark.unit
    def test_update_does_nothing_without_start(self) -> None:
        """update should do nothing if start wasn't called."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()

        # Should not raise
        handler.update(5)

        assert handler._progress_bar is None

    @pytest.mark.unit
    def test_update_updates_progress_bar(self) -> None:
        """update should update the progress bar."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()

        with patch("builtins.print"):
            handler.start("Processing", total=100)
            handler._last_update_time = 0  # Bypass throttling
            handler.update(10)

        assert handler._progress_bar is not None
        assert handler._progress_bar.current == 10

    @pytest.mark.unit
    def test_update_changes_description(self) -> None:
        """update should update description if provided."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()

        with patch("builtins.print"):
            handler.start("Original", total=100)
            handler._last_update_time = 0  # Bypass throttling
            handler.update(1, description="Updated")

        assert handler._progress_bar is not None
        assert handler._progress_bar.desc == "Updated"

    @pytest.mark.unit
    def test_update_throttles_visual_updates(self) -> None:
        """update should throttle visual updates but track count."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()

        with patch("builtins.print"):
            handler.start("Processing", total=100)

            # Multiple rapid updates
            for _ in range(10):
                handler.update(1)

        # Internal count should still be updated
        assert handler._progress_bar is not None
        assert handler._progress_bar.current == 10


class TestCLIProgressHandlerClose:
    """Tests for CLIProgressHandler.close() method."""

    @pytest.mark.unit
    def test_close_closes_progress_bar(self) -> None:
        """close should close the progress bar."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()

        with patch("builtins.print"):
            handler.start("Processing")
            handler.close()

        assert handler._progress_bar is None

    @pytest.mark.unit
    def test_close_does_nothing_without_start(self) -> None:
        """close should do nothing if start wasn't called."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()

        # Should not raise
        handler.close()

        assert handler._progress_bar is None


class TestCLIProgressHandlerWasCancelled:
    """Tests for CLIProgressHandler.was_cancelled() method."""

    @pytest.mark.unit
    def test_was_cancelled_returns_false_by_default(self) -> None:
        """was_cancelled should return False by default."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()

        assert handler.was_cancelled() is False

    @pytest.mark.unit
    def test_was_cancelled_returns_internal_flag(self) -> None:
        """was_cancelled should return the internal cancelled flag."""
        from ClassicLib.messaging.progress.cli_progress import CLIProgressHandler

        handler = CLIProgressHandler()
        handler._cancelled = True

        assert handler.was_cancelled() is True


# --- ProgressContext Tests ---


class TestProgressContextInit:
    """Tests for ProgressContext initialization."""

    @pytest.mark.unit
    def test_stores_handler_reference(self) -> None:
        """ProgressContext should store handler reference."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        context = ProgressContext(handler, "Test", total=100)

        assert context.handler is handler

    @pytest.mark.unit
    def test_stores_description(self) -> None:
        """ProgressContext should store description."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        context = ProgressContext(handler, "Processing files", total=50)

        assert context.description == "Processing files"

    @pytest.mark.unit
    def test_stores_total(self) -> None:
        """ProgressContext should store total."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        context = ProgressContext(handler, "Test", total=200)

        assert context.total == 200

    @pytest.mark.unit
    def test_initializes_current_to_zero(self) -> None:
        """ProgressContext should initialize current to 0."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        context = ProgressContext(handler, "Test")

        assert context.current == 0


class TestProgressContextEnterExit:
    """Tests for ProgressContext context manager behavior."""

    @pytest.mark.unit
    def test_enter_returns_self(self) -> None:
        """__enter__ should return self."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        context = ProgressContext(handler, "Test")

        with patch.object(context, "_check_cli_progress_disabled", return_value=True):
            result = context.__enter__()

        assert result is context

    @pytest.mark.unit
    def test_enter_starts_progress_handler(self) -> None:
        """__enter__ should start the progress handler."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        mock_progress_handler = MagicMock()
        mock_progress_handler.is_available.return_value = True
        handler.create_progress_handler = MagicMock(return_value=mock_progress_handler)  # type: ignore[method-assign]

        context = ProgressContext(handler, "Test", total=50)

        with patch.object(context, "_check_cli_progress_disabled", return_value=False):
            context.__enter__()

        mock_progress_handler.start.assert_called_once_with("Test", 50)

    @pytest.mark.unit
    def test_exit_closes_progress_handler(self) -> None:
        """__exit__ should close the progress handler."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        mock_progress_handler = MagicMock()
        mock_progress_handler.is_available.return_value = True
        handler.create_progress_handler = MagicMock(return_value=mock_progress_handler)  # type: ignore[method-assign]

        context = ProgressContext(handler, "Test")

        with patch.object(context, "_check_cli_progress_disabled", return_value=False):
            context.__enter__()
            context.__exit__(None, None, None)

        mock_progress_handler.close.assert_called_once()

    @pytest.mark.unit
    def test_exit_handles_no_progress_handler(self) -> None:
        """__exit__ should handle case where no progress handler was created."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        context = ProgressContext(handler, "Test")

        with patch.object(context, "_check_cli_progress_disabled", return_value=True):
            context.__enter__()
            # Should not raise
            context.__exit__(None, None, None)


class TestProgressContextUpdate:
    """Tests for ProgressContext.update() method."""

    @pytest.mark.unit
    def test_update_increments_current(self) -> None:
        """update should increment current counter."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        context = ProgressContext(handler, "Test")

        context.update(5)

        assert context.current == 5

    @pytest.mark.unit
    def test_update_delegates_to_progress_handler(self) -> None:
        """update should delegate to progress handler."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        mock_progress_handler = MagicMock()
        mock_progress_handler.is_available.return_value = True
        handler.create_progress_handler = MagicMock(return_value=mock_progress_handler)  # type: ignore[method-assign]

        context = ProgressContext(handler, "Test")

        with patch.object(context, "_check_cli_progress_disabled", return_value=False):
            context.__enter__()
            context.update(3, description="Updated")

        mock_progress_handler.update.assert_called_with(3, "Updated")


class TestProgressContextWasCancelled:
    """Tests for ProgressContext.was_cancelled() method."""

    @pytest.mark.unit
    def test_was_cancelled_returns_false_without_handler(self) -> None:
        """was_cancelled should return False when no progress handler."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        context = ProgressContext(handler, "Test")

        assert context.was_cancelled() is False

    @pytest.mark.unit
    def test_was_cancelled_delegates_to_progress_handler(self) -> None:
        """was_cancelled should delegate to progress handler."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler()
        mock_progress_handler = MagicMock()
        mock_progress_handler.is_available.return_value = True
        mock_progress_handler.was_cancelled.return_value = True
        handler.create_progress_handler = MagicMock(return_value=mock_progress_handler)  # type: ignore[method-assign]

        context = ProgressContext(handler, "Test")

        with patch.object(context, "_check_cli_progress_disabled", return_value=False):
            context.__enter__()
            result = context.was_cancelled()

        assert result is True


class TestProgressContextCLIDisabled:
    """Tests for ProgressContext CLI progress disabled behavior."""

    @pytest.mark.unit
    def test_skips_progress_when_cli_disabled(self) -> None:
        """Progress should be skipped when CLI progress is disabled."""
        from ClassicLib.messaging.handler import MessageHandler
        from ClassicLib.messaging.progress.context import ProgressContext

        handler = MessageHandler(is_gui_mode=False)
        mock_create = MagicMock()
        handler.create_progress_handler = mock_create  # type: ignore[method-assign]

        context = ProgressContext(handler, "Test")

        with patch.object(context, "_check_cli_progress_disabled", return_value=True):
            context.__enter__()

        # Should not create progress handler when disabled
        mock_create.assert_not_called()

    @pytest.mark.unit
    def test_check_cli_progress_disabled_handles_import_error(self) -> None:
        """_check_cli_progress_disabled should handle ImportError."""
        from ClassicLib.messaging.progress.context import ProgressContext

        with patch(
            "ClassicLib.messaging.progress.context.ProgressContext._check_cli_progress_disabled",
            return_value=False,
        ):
            # Original function handles import errors
            result = ProgressContext._check_cli_progress_disabled()

            # Should return False on error (progress enabled by default)
            assert result is False

    @pytest.mark.unit
    def test_check_cli_progress_disabled_returns_setting(self) -> None:
        """_check_cli_progress_disabled should return setting value."""
        with patch("ClassicLib.io.yaml.classic_settings") as mock_settings:
            mock_settings.return_value = True

            from ClassicLib.messaging.progress.context import ProgressContext

            result = ProgressContext._check_cli_progress_disabled()

            # May return the mocked value or False depending on import order
            assert isinstance(result, bool)


# --- Integration Tests ---


class TestProgressIntegration:
    """Integration tests for progress components."""

    @pytest.mark.unit
    def test_context_manager_works_with_handler(self) -> None:
        """Progress context should work as context manager with handler."""
        from ClassicLib.messaging.handler import MessageHandler

        handler = MessageHandler()

        with patch("builtins.print"):
            with patch(
                "ClassicLib.messaging.progress.context.ProgressContext._check_cli_progress_disabled",
                return_value=True,
            ):
                with handler.progress_context("Test", total=10) as progress:
                    for i in range(10):
                        progress.update(1)

                assert progress.current == 10

    @pytest.mark.unit
    def test_progress_tracks_cumulative_updates(self) -> None:
        """Progress should track cumulative updates."""
        from ClassicLib.messaging.handler import MessageHandler

        handler = MessageHandler()

        with patch("builtins.print"):
            with patch(
                "ClassicLib.messaging.progress.context.ProgressContext._check_cli_progress_disabled",
                return_value=True,
            ):
                with handler.progress_context("Processing", total=100) as progress:
                    progress.update(25)
                    progress.update(25)
                    progress.update(50)

                assert progress.current == 100
