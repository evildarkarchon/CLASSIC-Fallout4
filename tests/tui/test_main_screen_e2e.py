"""
E2E tests for main_screen - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

import pytest

from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.screens.main_screen import MainScreen

pytestmark = pytest.mark.e2e

class TestMainScreenScanButtons:
    """Test scan button functionality in MainScreen."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_papyrus_monitor_button(self):
        """Test Papyrus monitor button opens Papyrus screen."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            from ClassicLib.TUI.screens.papyrus_screen import PapyrusScreen
            await pilot.press('f7')
            await pilot.pause()
            papyrus_screen = app.screen
            assert isinstance(papyrus_screen, PapyrusScreen)
            await pilot.press('escape')
            await pilot.pause()
            assert isinstance(app.screen, MainScreen)
