"""
E2E tests for papyrus_screen - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

from datetime import datetime
from unittest.mock import patch
import pytest
from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.handlers.papyrus_handler import PapyrusStats
from ClassicLib.TUI.screens.main_screen import MainScreen
from ClassicLib.TUI.screens.papyrus_screen import PapyrusScreen

pytestmark = pytest.mark.e2e

class TestPapyrusScreenKeyboardShortcuts:
    """Test keyboard shortcuts in PapyrusScreen."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_papyrus_screen_keyboard_shortcuts(self):
        """Test keyboard shortcuts in Papyrus screen."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('f7')
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, PapyrusScreen)
            with patch('ClassicLib.TUI.handlers.papyrus.tui_papyrus_handler.papyrus_logging') as mock_logging:
                mock_logging.return_value = ('Test output', 0)
                await pilot.press('s')
                await pilot.pause()
                await pilot.press('r')
                await pilot.pause()
                await pilot.press('c')
                await pilot.pause()
                await pilot.press('u')
                await pilot.pause()
                await pilot.press('escape')
                await pilot.pause()
                assert isinstance(app.screen, MainScreen)
