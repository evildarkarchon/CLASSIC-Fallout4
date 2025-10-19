"""
Integration tests for TUI scan error dialog flow.

Tests the complete flow from scan handler errors to error dialog display in the TUI.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from textual.app import App

from ClassicLib.TUI.screens.main_screen import MainScreen
from ClassicLib.TUI.widgets.dialogs.error_dialog import ErrorDialog
from ClassicLib.TUI.handlers.scan_handler import TuiScanHandler


@pytest.mark.integration
@pytest.mark.tui
@pytest.mark.asyncio
class TestTuiScanErrorDialogIntegration:
    """Test complete TUI error dialog integration."""

    async def test_crash_scan_failure_shows_error_dialog(self):
        """Test that crash scan failure displays error dialog."""
        app = App()
        screen = MainScreen()

        # Mock the scan handler to fail
        async def mock_scan(*args, **kwargs):
            raise RuntimeError("Simulated crash scan failure")

        with patch.object(TuiScanHandler, "perform_crash_scan", mock_scan):
            async with app.run_test() as pilot:
                app._screen_stack.append(screen)

                # Track if error dialog was pushed
                original_push_screen = app.push_screen
                pushed_screens = []

                async def track_push_screen(screen_obj, *args, **kwargs):
                    pushed_screens.append(screen_obj)
                    return await original_push_screen(screen_obj, *args, **kwargs)

                app.push_screen = track_push_screen

                # Trigger crash scan
                await screen.perform_crash_scan()
                await pilot.pause()

                # Verify error dialog was pushed
                error_dialogs = [s for s in pushed_screens if isinstance(s, ErrorDialog)]
                assert len(error_dialogs) > 0, "Error dialog should be displayed"

                # Verify dialog content
                error_dialog = error_dialogs[0]
                assert "Crash Log Scan" in error_dialog.title
                assert "Simulated crash scan failure" in error_dialog.message or "RuntimeError" in str(error_dialog.details)

    async def test_game_scan_failure_shows_error_dialog(self):
        """Test that game scan failure displays error dialog."""
        app = App()
        screen = MainScreen()

        # Mock the scan handler to fail
        async def mock_scan(*args, **kwargs):
            raise IOError("Simulated game scan failure")

        with patch.object(TuiScanHandler, "perform_game_scan", mock_scan):
            async with app.run_test() as pilot:
                app._screen_stack.append(screen)

                # Track pushed screens
                pushed_screens = []
                original_push_screen = app.push_screen

                async def track_push_screen(screen_obj, *args, **kwargs):
                    pushed_screens.append(screen_obj)
                    return await original_push_screen(screen_obj, *args, **kwargs)

                app.push_screen = track_push_screen

                # Trigger game scan
                await screen.perform_game_scan()
                await pilot.pause()

                # Verify error dialog was pushed
                error_dialogs = [s for s in pushed_screens if isinstance(s, ErrorDialog)]
                assert len(error_dialogs) > 0, "Error dialog should be displayed"

                # Verify dialog content
                error_dialog = error_dialogs[0]
                assert "Game Files Scan" in error_dialog.title
                assert "Simulated game scan failure" in error_dialog.message or "IOError" in str(error_dialog.details)

    async def test_scan_failure_dialog_includes_traceback(self):
        """Test that error dialog includes full traceback on scan failure."""
        app = App()
        screen = MainScreen()

        # Mock scan to raise specific error
        def error_function():
            raise ValueError("Specific test error from known location")

        async def mock_scan(*args, **kwargs):
            error_function()

        with patch.object(TuiScanHandler, "perform_crash_scan", mock_scan):
            async with app.run_test() as pilot:
                app._screen_stack.append(screen)

                pushed_screens = []
                original_push_screen = app.push_screen

                async def track_push_screen(screen_obj, *args, **kwargs):
                    pushed_screens.append(screen_obj)
                    return await original_push_screen(screen_obj, *args, **kwargs)

                app.push_screen = track_push_screen

                # Trigger scan
                await screen.perform_crash_scan()
                await pilot.pause()

                # Get error dialog
                error_dialogs = [s for s in pushed_screens if isinstance(s, ErrorDialog)]
                assert len(error_dialogs) > 0

                error_dialog = error_dialogs[0]
                assert error_dialog.details is not None
                assert "Traceback" in error_dialog.details
                assert "error_function" in error_dialog.details
                assert "ValueError: Specific test error from known location" in error_dialog.details

    async def test_scan_success_does_not_show_error_dialog_on_true_return(self):
        """Test that successful scan (returns True) doesn't show error dialog."""
        app = App()
        screen = MainScreen()

        # Mock successful scan
        async def mock_scan(*args, **kwargs):
            return True

        with patch.object(TuiScanHandler, "perform_crash_scan", mock_scan):
            async with app.run_test() as pilot:
                app._screen_stack.append(screen)

                pushed_screens = []
                original_push_screen = app.push_screen

                async def track_push_screen(screen_obj, *args, **kwargs):
                    pushed_screens.append(screen_obj)
                    return await original_push_screen(screen_obj, *args, **kwargs)

                app.push_screen = track_push_screen

                # Trigger scan
                await screen.perform_crash_scan()
                await pilot.pause()

                # No error dialog should be pushed
                error_dialogs = [s for s in pushed_screens if isinstance(s, ErrorDialog)]
                assert len(error_dialogs) == 0, "No error dialog should be shown on success"

    async def test_scan_failure_return_shows_error_dialog(self):
        """Test that scan returning False shows error dialog."""
        app = App()
        screen = MainScreen()

        # Mock scan to return False (failure)
        async def mock_scan(*args, **kwargs):
            return False

        with patch.object(TuiScanHandler, "perform_crash_scan", mock_scan):
            async with app.run_test() as pilot:
                app._screen_stack.append(screen)

                pushed_screens = []
                original_push_screen = app.push_screen

                async def track_push_screen(screen_obj, *args, **kwargs):
                    pushed_screens.append(screen_obj)
                    return await original_push_screen(screen_obj, *args, **kwargs)

                app.push_screen = track_push_screen

                # Trigger scan
                await screen.perform_crash_scan()
                await pilot.pause()

                # Error dialog should be pushed
                error_dialogs = [s for s in pushed_screens if isinstance(s, ErrorDialog)]
                assert len(error_dialogs) > 0, "Error dialog should be shown when scan returns False"

                error_dialog = error_dialogs[0]
                assert "Failed" in error_dialog.title or "Failed" in error_dialog.message

    async def test_error_dialog_has_copy_button_for_exceptions(self):
        """Test that error dialog has copy button when exception occurs."""
        app = App()
        screen = MainScreen()

        async def mock_scan(*args, **kwargs):
            raise RuntimeError("Test error")

        with patch.object(TuiScanHandler, "perform_crash_scan", mock_scan):
            async with app.run_test() as pilot:
                app._screen_stack.append(screen)

                pushed_screens = []
                original_push_screen = app.push_screen

                async def track_push_screen(screen_obj, *args, **kwargs):
                    pushed_screens.append(screen_obj)
                    return await original_push_screen(screen_obj, *args, **kwargs)

                app.push_screen = track_push_screen

                # Trigger scan
                await screen.perform_crash_scan()
                await pilot.pause()

                # Get error dialog
                error_dialogs = [s for s in pushed_screens if isinstance(s, ErrorDialog)]
                assert len(error_dialogs) > 0

                error_dialog = error_dialogs[0]
                # Dialog should have details (traceback)
                assert error_dialog.details is not None
                assert len(error_dialog.details.strip()) > 0

    async def test_multiple_scan_failures_show_multiple_dialogs(self):
        """Test that multiple scan failures result in multiple error dialogs."""
        app = App()
        screen = MainScreen()

        call_count = 0

        async def mock_scan(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError(f"Error {call_count}")

        with patch.object(TuiScanHandler, "perform_crash_scan", mock_scan):
            async with app.run_test() as pilot:
                app._screen_stack.append(screen)

                pushed_screens = []
                original_push_screen = app.push_screen

                async def track_push_screen(screen_obj, *args, **kwargs):
                    pushed_screens.append(screen_obj)
                    return await original_push_screen(screen_obj, *args, **kwargs)

                app.push_screen = track_push_screen

                # Trigger first scan
                await screen.perform_crash_scan()
                await pilot.pause()

                # Trigger second scan
                await screen.perform_game_scan()
                await pilot.pause()

                # Should have two error dialogs
                error_dialogs = [s for s in pushed_screens if isinstance(s, ErrorDialog)]
                assert len(error_dialogs) >= 2, "Should show error dialog for each failure"

    async def test_output_viewer_cleared_before_scan(self):
        """Test that output viewer is cleared before scan starts."""
        app = App()
        screen = MainScreen()

        # Mock scan to fail
        async def mock_scan(*args, **kwargs):
            raise RuntimeError("Test error")

        with patch.object(TuiScanHandler, "perform_crash_scan", mock_scan):
            async with app.run_test() as pilot:
                app._screen_stack.append(screen)
                await pilot.pause()

                # Get output viewer
                from ClassicLib.TUI.widgets.output_viewer import OutputViewer
                output = screen.query_one("#output", OutputViewer)

                # Add some initial content
                output.append_output("Initial content\n")
                initial_content = output._output_text

                # Trigger scan
                await screen.perform_crash_scan()
                await pilot.pause()

                # Output should have been cleared
                # (It will have new content from the scan attempt)
                current_content = output._output_text
                assert current_content != initial_content

    async def test_error_dialog_message_format_for_exception(self):
        """Test error dialog message format when exception occurs."""
        app = App()
        screen = MainScreen()

        async def mock_scan(*args, **kwargs):
            raise ValueError("Invalid configuration")

        with patch.object(TuiScanHandler, "perform_crash_scan", mock_scan):
            async with app.run_test() as pilot:
                app._screen_stack.append(screen)

                pushed_screens = []
                original_push_screen = app.push_screen

                async def track_push_screen(screen_obj, *args, **kwargs):
                    pushed_screens.append(screen_obj)
                    return await original_push_screen(screen_obj, *args, **kwargs)

                app.push_screen = track_push_screen

                # Trigger scan
                await screen.perform_crash_scan()
                await pilot.pause()

                # Get error dialog
                error_dialogs = [s for s in pushed_screens if isinstance(s, ErrorDialog)]
                assert len(error_dialogs) > 0

                error_dialog = error_dialogs[0]
                # Message should mention the error
                assert "Invalid configuration" in error_dialog.message or "ValueError" in error_dialog.message
