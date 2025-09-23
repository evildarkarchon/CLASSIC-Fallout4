"""
Integration tests for workflows - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from unittest.mock import patch

import pytest

from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.screens.main_screen import MainScreen
from ClassicLib.TUI.widgets.output_viewer import OutputViewer

pytestmark = pytest.mark.integration

class TestErrorRecoveryWorkflow:
    """Test error recovery workflow."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_error_recovery_workflow(self):
        """Test error recovery workflow."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            output_viewer = main_screen.query_one('#output', OutputViewer)
            from ClassicLib.TUI.widgets.status_bar import StatusBar
            status_bar = app.query_one(StatusBar)
            with patch('ClassicLib.TUI.handlers.scan_handler.ClassicScanLogs') as mock_scanner:
                mock_scanner.side_effect = ImportError('Simulated error')
                result = await main_screen.perform_crash_scan()
                await pilot.pause()
                assert result is None or result is False
                error_found = any('error' in line.lower() for line in output_viewer._output_buffer)
                assert error_found
                output_viewer.clear()
                assert len(output_viewer._output_buffer) == 0
                output_viewer.append_output('Recovery successful', style='success')
                assert len(output_viewer._output_buffer) > 0
                assert 'success' in str(output_viewer._output_buffer).lower()
