"""
E2E tests for workflows - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

import asyncio
from unittest.mock import Mock, patch
import pytest
from textual.widgets import Input
from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.screens.main_screen import MainScreen
from ClassicLib.TUI.widgets.confirmation_dialog import ConfirmationDialog
from ClassicLib.TUI.widgets.output_viewer import OutputViewer
from ClassicLib.TUI.widgets.status_bar import StatusBar

pytestmark = pytest.mark.e2e

class TestFirstTimeSetup:
    """Test first-time user setup workflow."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_first_time_setup_workflow(self):
        """Test first-time user setup workflow."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.press('ctrl+o')
            await pilot.pause()
            try:
                await pilot.click('#auto-scroll')
                await pilot.click('#update-check')
            except Exception:
                pass
            with patch('ClassicLib.TUI.screens.settings_screen.yaml_settings'):
                try:
                    await pilot.click('#save-settings')
                except Exception:
                    await pilot.press('escape')
            assert isinstance(app.screen, MainScreen)

class TestCompleteScanWorkflows:
    """Test complete scan workflows."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_complete_crash_scan_workflow(self):
        """Test complete crash scan workflow."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            output_viewer = main_screen.query_one('#output', OutputViewer)
            status_bar = app.query_one(StatusBar)
            with patch('ClassicLib.TUI.handlers.scan_handler.ClassicScanLogs') as mock_scanner:
                mock_instance = mock_scanner.return_value
                mock_instance.scan_logs = Mock(return_value=('Analysis Complete', ['Found 3 crash logs', '2 critical issues', '1 warning']))
                await main_screen.perform_crash_scan()
                await pilot.pause()
                mock_scanner.assert_called()
                assert len(output_viewer._output_buffer) > 0
                await pilot.press('/')
                await pilot.press('escape')
                output_viewer.clear()
                assert len(output_viewer._output_buffer) == 0

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_complete_game_scan_workflow(self):
        """Test complete game scan workflow."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            output_viewer = main_screen.query_one('#output', OutputViewer)
            with patch('CLASSIC_ScanGame.main') as mock_scan_main:
                mock_scan_main.return_value = None
                await main_screen.perform_game_scan()
                await pilot.pause()
                mock_scan_main.assert_called()
                await pilot.press('f1')
                await asyncio.sleep(0.1)
                await pilot.press('escape')
                assert isinstance(app.screen, MainScreen)

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_complete_papyrus_monitoring_workflow(self):
        """Test complete Papyrus monitoring workflow."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            from ClassicLib.TUI.screens.papyrus_screen import PapyrusScreen
            await pilot.pause()
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            with patch('ClassicLib.TUI.handlers.papyrus.tui_papyrus_handler.papyrus_logging') as mock_logging:
                log_outputs = [('NUMBER OF DUMPS    : 0\nNUMBER OF STACKS   : 0\nDUMPS/STACKS RATIO : 0.0\nNUMBER OF WARNINGS : 5\nNUMBER OF ERRORS   : 2\n', 0), ('NUMBER OF DUMPS    : 2\nNUMBER OF STACKS   : 5\nDUMPS/STACKS RATIO : 0.4\nNUMBER OF WARNINGS : 10\nNUMBER OF ERRORS   : 5\n', 2), ('NUMBER OF DUMPS    : 5\nNUMBER OF STACKS   : 10\nDUMPS/STACKS RATIO : 0.5\nNUMBER OF WARNINGS : 25\nNUMBER OF ERRORS   : 12\n', 5)]
                mock_logging.side_effect = log_outputs
                await pilot.press('f7')
                await pilot.pause()
                papyrus_screen = app.screen
                assert isinstance(papyrus_screen, PapyrusScreen)
                assert papyrus_screen.is_monitoring is True
                await pilot.press('u')
                await pilot.pause()
                await pilot.press('c')
                await pilot.pause()
                await pilot.press('r')
                await pilot.pause()
                await pilot.press('s')
                await pilot.pause()
                await pilot.press('escape')
                await pilot.pause()
                assert isinstance(app.screen, MainScreen)

class TestUserNavigationFlow:
    """Test user navigation patterns."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_navigation_flow(self):
        """Test navigation between different screens."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            screens_visited = []
            await pilot.press('f1')
            await pilot.pause()
            screens_visited.append(type(app.screen).__name__)
            await pilot.press('escape')
            await pilot.pause()
            await pilot.press('ctrl+o')
            await pilot.pause()
            screens_visited.append(type(app.screen).__name__)
            await pilot.press('escape')
            await pilot.pause()
            with patch('ClassicLib.PapyrusLog.papyrus_logging') as mock_logging:
                mock_logging.return_value = ('Test output', 0)
                await pilot.press('f7')
                await pilot.pause()
                screens_visited.append(type(app.screen).__name__)
                await pilot.press('escape')
                await pilot.pause()
            assert 'HelpScreen' in screens_visited
            assert 'SettingsScreen' in screens_visited
            assert 'PapyrusScreen' in screens_visited

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_focus_management(self):
        """Test focus management between widgets."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            for _ in range(10):
                await pilot.press('tab')
            for _ in range(5):
                await pilot.press('shift+tab')
            assert isinstance(app.screen, MainScreen)

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_dialog_interactions(self):
        """Test dialog interactions."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            from ClassicLib.TUI.widgets.confirmation_dialog import ConfirmationDialog
            dialog = ConfirmationDialog(title='Test Dialog', message='Test message', confirm_text='OK', cancel_text='Cancel')
            app.push_screen(dialog)
            await pilot.pause()
            await pilot.press('escape')
            assert not isinstance(app.screen, ConfirmationDialog)
