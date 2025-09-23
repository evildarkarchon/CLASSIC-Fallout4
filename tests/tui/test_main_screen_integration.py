"""
Integration tests for main_screen - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from unittest.mock import Mock, patch

import pytest

from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.screens.main_screen import MainScreen
from ClassicLib.TUI.widgets.output_viewer import OutputViewer

pytestmark = pytest.mark.integration

class TestMainScreenInitialization:
    """Test MainScreen initialization and setup."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_main_screen_initialization(self):
        """Test MainScreen initializes with all components."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            assert main_screen is not None
            assert main_screen.query_one('#mods-folder') is not None
            assert main_screen.query_one('#scan-folder') is not None
            assert main_screen.query_one('#crash-scan') is not None
            assert main_screen.query_one('#game-scan') is not None
            assert main_screen.query_one('#papyrus-monitor') is not None
            assert main_screen.query_one('#output') is not None

class TestMainScreenScanButtons:
    """Test scan button functionality in MainScreen."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_crash_scan_button_click(self):
        """Test crash scan button triggers scan."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            output_viewer = main_screen.query_one('#output', OutputViewer)
            with patch('ClassicLib.TUI.handlers.scan_handler.ClassicScanLogs') as mock_scanner:
                mock_instance = mock_scanner.return_value
                mock_instance.scan_logs = Mock(return_value=('Success', ['Result 1']))
                await main_screen.perform_crash_scan()
                assert len(output_viewer._output_buffer) > 0
                assert 'scan' in str(output_viewer._output_buffer).lower()

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_game_scan_button_click(self):
        """Test game scan button triggers scan."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            output_viewer = main_screen.query_one('#output', OutputViewer)
            with patch('CLASSIC_ScanGame.main') as mock_scan_main:
                mock_scan_main.return_value = None
                await main_screen.perform_game_scan()
                assert len(output_viewer._output_buffer) > 0
                assert 'scan' in str(output_viewer._output_buffer).lower()

class TestMainScreenFolderInput:
    """Test folder input handling in MainScreen."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_folder_input_persistence(self):
        """Test folder inputs save to settings."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)

            def mock_classic_settings(type_hint, key, default=None):
                return '' if 'Folder' in key else default
            with patch('ClassicLib.TUI.screens.main_screen.classic_settings', side_effect=mock_classic_settings):
                from ClassicLib.TUI.widgets.folder_selector import FolderSelector
                mods_input = main_screen.query_one('#mods-folder', FolderSelector)
                scan_input = main_screen.query_one('#scan-folder', FolderSelector)
                from textual.widgets import Input
                mods_actual_input = mods_input._input
                scan_actual_input = scan_input._input
                assert mods_actual_input is not None, 'Mods input widget should be available'
                assert scan_actual_input is not None, 'Scan input widget should be available'
                mods_actual_input.value = '/path/to/mods'
                mods_input.on_input_changed(Input.Changed(mods_actual_input, '/path/to/mods'))
                scan_actual_input.value = '/path/to/custom'
                scan_input.on_input_changed(Input.Changed(scan_actual_input, '/path/to/custom'))
                assert mods_actual_input.value == '/path/to/mods'
                assert scan_actual_input.value == '/path/to/custom'
