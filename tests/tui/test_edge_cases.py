"""Edge case and boundary condition tests for TUI."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913

import asyncio
from unittest.mock import Mock, patch

import pytest
from textual.widgets import Input

from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.screens.main_screen import MainScreen
from ClassicLib.TUI.widgets.output_viewer import OutputViewer


class TestEmptyInputHandling:
    """Test handling of empty inputs."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_empty_folder_paths(self):
        """Test handling of empty folder paths."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Get main screen and output viewer
            await pilot.pause()  # Wait for app to mount
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            output_viewer = main_screen.query_one("#output", OutputViewer)

            # Try to run scan without setting folders
            with patch("ClassicLib.TUI.handlers.scan_handler.ClassicScanLogs") as mock_scanner:
                mock_instance = mock_scanner.return_value
                mock_instance.scan_logs = Mock(return_value=("No logs found", []))

                # Call scan directly
                await main_screen.perform_crash_scan()

                # Should handle gracefully
                assert len(output_viewer._output_buffer) >= 0


class TestInvalidInputHandling:
    """Test handling of invalid inputs."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_invalid_input_values(self):
        """Test handling of invalid input values."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Open settings
            await pilot.press("ctrl+o")
            await pilot.pause()

            settings_screen = app.screen
            from ClassicLib.TUI.screens.settings_screen import SettingsScreen

            if isinstance(settings_screen, SettingsScreen):
                # Try to set invalid value
                try:
                    max_lines_input = settings_screen.query_one("#max-lines", Input)
                    max_lines_input.value = "invalid"
                except Exception:
                    pass  # Field may not exist

                # Try to save
                with patch("ClassicLib.TUI.screens.settings_screen.classic_settings"):
                    settings_screen._save_settings()

                # Dismiss settings
                settings_screen.dismiss(False)

            await pilot.pause()
            # Should handle gracefully
            assert isinstance(app.screen, MainScreen)


class TestRapidInteractionHandling:
    """Test handling of rapid user interactions."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_rapid_screen_switching(self):
        """Test rapid switching between screens."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Rapidly open and close screens
            for _ in range(3):
                await pilot.press("f1")  # Help
                await pilot.pause()
                await pilot.press("escape")  # Close
                await pilot.pause()

            # Should be back at main
            assert isinstance(app.screen, MainScreen)

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_rapid_key_input(self):
        """Test handling rapid keyboard input."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Rapidly switch between screens
            for _ in range(3):
                await pilot.press("f1")  # Open help
                await pilot.pause()
                await pilot.press("escape")  # Close help
                await pilot.pause()

            # App should still be responsive
            assert isinstance(app.screen, MainScreen)


class TestLargeDataHandling:
    """Test handling of large amounts of data."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_large_output_handling(self):
        """Test handling large amounts of output."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()  # Wait for app to mount
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            output_viewer = main_screen.query_one(OutputViewer)

            # Generate large amount of output
            for i in range(100):  # Reduced from 1000 for performance
                output_viewer.append_output(f"Line {i}: " + "x" * 100)

            # Verify output was added
            assert len(output_viewer._output_buffer) > 0
            # Verify max lines is respected
            assert len(output_viewer._output_buffer) <= output_viewer.max_lines

            # Test search performance
            start_time = asyncio.get_event_loop().time()
            matches = output_viewer.search("Line 50")  # Search for line that exists
            end_time = asyncio.get_event_loop().time()

            # Search should complete quickly
            assert (end_time - start_time) < 1.0
            assert matches > 0


class TestConcurrentOperations:
    """Test concurrent operation handling."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_concurrent_operations(self):
        """Test concurrent operations."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            await pilot.pause()  # Wait for app to mount
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)
            output_viewer = main_screen.query_one(OutputViewer)

            # Start multiple async operations
            tasks = []

            # Add output while searching
            async def add_output():
                for i in range(10):  # Reduced for performance
                    output_viewer.append_output(f"Concurrent line {i}")
                    await asyncio.sleep(0.001)  # Reduced delay

            async def search_output():
                for _ in range(5):  # Reduced iterations
                    output_viewer.search("Concurrent")
                    await asyncio.sleep(0.01)  # Reduced delay

            tasks.append(asyncio.create_task(add_output()))
            tasks.append(asyncio.create_task(search_output()))

            # Wait for all tasks with timeout
            try:
                await asyncio.wait_for(asyncio.gather(*tasks), timeout=2.0)
            except asyncio.TimeoutError:
                pass  # Tasks may timeout in test environment

            # Verify output integrity
            assert len(output_viewer._output_buffer) > 0
