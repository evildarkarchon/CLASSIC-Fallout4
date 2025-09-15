"""Tests for the TuiScanHandler component."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913

from unittest.mock import Mock, patch

import pytest

from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.handlers.scan_handler import TuiScanHandler
from ClassicLib.TUI.widgets.output_viewer import OutputViewer


class TestScanHandlerBasicOperations:
    """Test basic TuiScanHandler operations."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_scan_handler_crash_scan(self):
        """Test scan handler performs crash scan."""
        app = CLASSICTuiApp()
        async with app.run_test():
            output_viewer = OutputViewer()
            app.mount(output_viewer)

            handler = TuiScanHandler(output_callback=output_viewer.append_output)

            # Mock the actual scan components
            with patch("ClassicLib.TUI.handlers.scan_handler.ClassicScanLogs") as mock_scanner:
                mock_instance = mock_scanner.return_value
                mock_instance.scan_logs = Mock(return_value=("Success", ["Result 1", "Result 2"]))

                await handler.perform_crash_scan()

                # Verify scan was called
                mock_scanner.assert_called_once()

                # Check output was written
                assert len(output_viewer._output_buffer) > 0

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_scan_handler_game_scan(self):
        """Test scan handler performs game scan."""
        app = CLASSICTuiApp()
        async with app.run_test():
            output_viewer = OutputViewer()
            app.mount(output_viewer)

            handler = TuiScanHandler(output_callback=output_viewer.append_output)

            # Mock the actual scan components
            with patch("CLASSIC_ScanGame.main") as mock_scan_main:
                mock_scan_main.return_value = None

                await handler.perform_game_scan()

                # Verify scan was called
                mock_scan_main.assert_called_once()

                # Check output was written
                assert len(output_viewer._output_buffer) > 0


class TestScanHandlerErrorHandling:
    """Test error handling in TuiScanHandler."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_scan_handler_error_handling(self):
        """Test scan handler handles errors gracefully."""
        app = CLASSICTuiApp()
        async with app.run_test():
            output_viewer = OutputViewer()
            app.mount(output_viewer)

            handler = TuiScanHandler(output_callback=output_viewer.append_output)

            # Mock scanner to raise an error (must be one of the expected exception types)
            with patch("ClassicLib.TUI.handlers.scan_handler.ClassicScanLogs") as mock_scanner:
                mock_scanner.side_effect = ImportError("Test error - simulated import failure")

                result = await handler.perform_crash_scan()

                # Handler should return False on error
                assert result is False

                # Check error was reported
                error_found = any("error" in line.lower() for line in output_viewer._output_buffer)
                assert error_found
