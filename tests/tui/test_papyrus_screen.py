"""Tests for the PapyrusScreen component."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913

from datetime import datetime
from unittest.mock import patch

import pytest

from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.handlers.papyrus_handler import PapyrusStats
from ClassicLib.TUI.screens.main_screen import MainScreen
from ClassicLib.TUI.screens.papyrus_screen import PapyrusScreen


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

            # Check screen components exist
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

            # Mock papyrus_logging
            with patch("ClassicLib.TUI.handlers.papyrus_handler.papyrus_logging") as mock_logging:
                mock_logging.return_value = ("Test output", 0)

                # Start monitoring (should auto-start on mount)
                assert screen.is_monitoring is True

                # Stop monitoring
                await screen.stop_monitoring()
                assert screen.is_monitoring is False

                # Toggle back on
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

            # Initial state
            assert screen.use_unicode is True

            # Toggle Unicode
            screen.action_toggle_unicode()
            assert screen.use_unicode is False

            # Toggle back
            screen.action_toggle_unicode()
            assert screen.use_unicode is True


class TestPapyrusScreenKeyboardShortcuts:
    """Test keyboard shortcuts in PapyrusScreen."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_papyrus_screen_keyboard_shortcuts(self):
        """Test keyboard shortcuts in Papyrus screen."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Open main screen first
            await pilot.pause()

            # Open Papyrus screen with F7
            await pilot.press("f7")
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, PapyrusScreen)

            # Mock papyrus_logging for testing
            with patch("ClassicLib.TUI.handlers.papyrus_handler.papyrus_logging") as mock_logging:
                mock_logging.return_value = ("Test output", 0)

                # Test S key for start/stop
                await pilot.press("s")
                await pilot.pause()

                # Test R key for refresh
                await pilot.press("r")
                await pilot.pause()

                # Test C key for clear
                await pilot.press("c")
                await pilot.pause()

                # Test U key for Unicode toggle
                await pilot.press("u")
                await pilot.pause()

                # Test Escape to close
                await pilot.press("escape")
                await pilot.pause()

                # Should be back to main screen
                assert isinstance(app.screen, MainScreen)


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

            # Create test stats
            stats = PapyrusStats(
                timestamp=datetime.now(),
                dumps=10,
                stacks=20,
                warnings=30,
                errors=5,
                ratio=0.5,
                raw_output="Test output with stats"
            )

            # Update screen with stats
            screen._on_stats_update(stats)

            # Verify monitor widget was updated
            assert screen.monitor_widget is not None, "Monitor widget should be available"
            assert screen.monitor_widget.dumps == 10
            assert screen.monitor_widget.stacks == 20
            assert screen.monitor_widget.warnings == 30
            assert screen.monitor_widget.errors == 5
            assert screen.monitor_widget.ratio == 0.5
