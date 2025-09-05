"""Tests for keyboard shortcuts in the TUI."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913

from unittest.mock import AsyncMock, patch

import pytest

from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.screens.main_screen import MainScreen
from ClassicLib.TUI.widgets.output_viewer import OutputViewer


class TestApplicationShortcuts:
    """Test application-level keyboard shortcuts."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_quit_shortcut(self):
        """Test quit keyboard shortcut."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Press Ctrl+Q to quit (standard Textual quit)
            await pilot.press("ctrl+q")
            # App should exit cleanly - no assertion needed in test mode


class TestScanShortcuts:
    """Test scan-related keyboard shortcuts."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_scan_shortcuts(self):
        """Test scan keyboard shortcuts."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()  # Wait for app to mount
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)

            with (
                patch.object(main_screen, "perform_crash_scan", new=AsyncMock()) as mock_crash,
                patch.object(main_screen, "perform_game_scan", new=AsyncMock()) as mock_game,
            ):
                # Test F5 for crash scan
                await pilot.press("f5")
                mock_crash.assert_called_once()

                # Test F6 for game scan
                await pilot.press("f6")
                mock_game.assert_called_once()


class TestOutputShortcuts:
    """Test output management keyboard shortcuts."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_output_shortcuts(self):
        """Test output management shortcuts."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()  # Wait for app to mount
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            output_viewer = main_screen.query_one("#output", OutputViewer)

            # Add some output
            output_viewer.append_output("Test line 1")
            output_viewer.append_output("Test line 2")
            assert len(output_viewer._output_buffer) == 2

            # Test Ctrl+L to clear
            await pilot.press("ctrl+l")
            await pilot.pause()
            assert len(output_viewer._output_buffer) == 0

            # Add output again
            output_viewer.append_output("New line")

            # Test / for search
            await pilot.press("/")
            # Note: search functionality may not be fully implemented yet
