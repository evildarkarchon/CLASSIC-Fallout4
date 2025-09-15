"""
Unit tests for papyrus_screen - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from datetime import datetime
from unittest.mock import patch
import pytest
from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.handlers.papyrus_handler import PapyrusStats
from ClassicLib.TUI.screens.main_screen import MainScreen
from ClassicLib.TUI.screens.papyrus_screen import PapyrusScreen

pytestmark = pytest.mark.unit

class TestPapyrusScreenInitialization:
    """Test PapyrusScreen initialization."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_papyrus_screen_initialization(self):
        """Test Papyrus screen initializes correctly."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            screen = PapyrusScreen(use_unicode=True)
            app.push_screen(screen)
            await pilot.pause()
            assert screen.monitor_widget is not None
            assert screen.output_viewer is not None
            assert screen.use_unicode is True

class TestPapyrusScreenMonitoring:
    """Test monitoring functionality in PapyrusScreen."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_papyrus_screen_monitoring_toggle(self):
        """Test toggling monitoring in Papyrus screen."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            screen = PapyrusScreen()
            app.push_screen(screen)
            await pilot.pause()
            with patch('ClassicLib.TUI.handlers.papyrus_handler.papyrus_logging') as mock_logging:
                mock_logging.return_value = ('Test output', 0)
                assert screen.is_monitoring is True
                await screen.stop_monitoring()
                assert screen.is_monitoring is False
                await screen.action_toggle_monitoring()
                assert screen.is_monitoring is True

class TestPapyrusScreenUnicode:
    """Test Unicode handling in PapyrusScreen."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_papyrus_screen_unicode_toggle(self):
        """Test toggling Unicode mode in Papyrus screen."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            screen = PapyrusScreen(use_unicode=True)
            app.push_screen(screen)
            await pilot.pause()
            assert screen.use_unicode is True
            screen.action_toggle_unicode()
            assert screen.use_unicode is False
            screen.action_toggle_unicode()
            assert screen.use_unicode is True

class TestPapyrusScreenStatsUpdate:
    """Test stats updating in PapyrusScreen."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_papyrus_screen_stats_update(self):
        """Test stats updates in Papyrus screen."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            screen = PapyrusScreen()
            app.push_screen(screen)
            await pilot.pause()
            stats = PapyrusStats(timestamp=datetime.now(), dumps=10, stacks=20, warnings=30, errors=5, ratio=0.5, raw_output='Test output with stats')
            screen._on_stats_update(stats)
            assert screen.monitor_widget is not None, 'Monitor widget should be available'
            assert screen.monitor_widget.dumps == 10
            assert screen.monitor_widget.stacks == 20
            assert screen.monitor_widget.warnings == 30
            assert screen.monitor_widget.errors == 5
            assert screen.monitor_widget.ratio == 0.5
