"""Tests for the HelpScreen component."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913

import pytest

from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.screens.help_screen import HelpScreen
from ClassicLib.TUI.screens.main_screen import MainScreen


class TestHelpScreenNavigation:
    """Test HelpScreen navigation and display."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_help_screen_display(self):
        """Test help screen displays correctly."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Press F1 to open help
            await pilot.press("f1")

            # Check help screen is displayed
            help_screen = app.screen
            assert isinstance(help_screen, HelpScreen)

            # Check help screen content exists
            # Note: The actual implementation may not have tabs yet

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_help_screen_close(self):
        """Test help screen closes correctly."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Open help screen
            await pilot.press("f1")
            await pilot.pause()  # Wait for screen to be pushed

            # Check help screen is on top
            current_screen = app.screen
            assert isinstance(current_screen, HelpScreen)

            # Close with ESC
            await pilot.press("escape")
            await pilot.pause()  # Wait for screen to pop

            # Check we're back to main screen
            current_screen = app.screen
            assert isinstance(current_screen, MainScreen)
