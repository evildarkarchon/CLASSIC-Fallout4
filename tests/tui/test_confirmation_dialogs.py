"""Tests for confirmation dialog widgets."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841

import pytest
from textual.app import App
from textual.widgets import Button, Label

from ClassicLib.TUI.widgets.confirmation_dialog import (
    ConfirmationDialog,
    ErrorDialog,
    ProgressDialog,
)


class TestConfirmationDialog:
    """Test ConfirmationDialog functionality."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_confirmation_dialog(self):
        """Test ConfirmationDialog functionality."""
        async with App().run_test() as pilot:
            confirmed = False
            cancelled = False

            def on_confirm():
                nonlocal confirmed
                confirmed = True

            def on_cancel():
                nonlocal cancelled
                cancelled = True

            dialog = ConfirmationDialog(
                title="Test Confirm",
                message="Are you sure?",
                confirm_callback=on_confirm,
                cancel_callback=on_cancel
            )

            pilot.app.push_screen(dialog)

            # Wait for the screen to be pushed and composed
            await pilot.pause()

            # Test confirm button
            confirm_btn = dialog.query_one("#confirm", Button)
            assert confirm_btn.label == "Yes"

            # Test cancel button
            cancel_btn = dialog.query_one("#cancel", Button)
            assert cancel_btn.label == "No"


class TestErrorDialog:
    """Test ErrorDialog functionality."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_error_dialog(self):
        """Test ErrorDialog functionality."""
        async with App().run_test() as pilot:
            closed = False

            def on_close():
                nonlocal closed
                closed = True

            dialog = ErrorDialog(
                title="Test Error",
                message="An error occurred",
                details="Error details here",
                close_callback=on_close
            )

            pilot.app.push_screen(dialog)

            # Wait for the screen to be pushed and composed
            await pilot.pause()

            # Check title and message
            labels = dialog.query(Label)
            assert any("Test Error" in str(label.render()) for label in labels)
            assert any("An error occurred" in str(label.render()) for label in labels)
            assert any("Error details here" in str(label.render()) for label in labels)


class TestProgressDialog:
    """Test ProgressDialog functionality."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_progress_dialog(self):
        """Test ProgressDialog functionality."""
        async with App().run_test() as pilot:
            cancelled = False

            def on_cancel():
                nonlocal cancelled
                cancelled = True

            dialog = ProgressDialog(
                title="Processing",
                message="Please wait...",
                can_cancel=True,
                cancel_callback=on_cancel
            )

            pilot.app.push_screen(dialog)

            # Wait for the screen to be pushed and composed
            await pilot.pause()

            # Test progress update
            dialog.update_progress(50, "Halfway done")
            assert dialog.progress == 50

            # Test progress bounds
            dialog.update_progress(150)
            assert dialog.progress == 100

            dialog.update_progress(-10)
            assert dialog.progress == 0

            # Test cancel button exists
            cancel_btn = dialog.query_one("#cancel", Button)
            assert cancel_btn is not None
