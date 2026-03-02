"""Widget-level unit tests for CLASSIC TUI components.

These tests verify individual widget behavior in isolation.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult


class FolderInputTestApp(App):
    """Minimal app for testing FolderInput widget in isolation."""

    def compose(self) -> ComposeResult:
        from ClassicLib.TUI.widgets.folder_input import FolderInput

        yield FolderInput(
            placeholder="Test folder path...",
            setting_key="Test Path",
            widget_id="test-folder",
        )


class TestFolderInput:
    """Tests for FolderInput widget."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings I/O."""
        with (
            patch("ClassicLib.io.yaml.classic_settings", return_value=None),
            patch("ClassicLib.io.yaml.yaml_settings"),
        ):
            yield

    @pytest.mark.asyncio
    async def test_folder_input_renders(self, mock_settings):
        """Verify FolderInput widget renders correctly."""
        app = FolderInputTestApp()
        async with app.run_test() as pilot:
            from textual.widgets import Button, Input

            # Should have an input field
            input_field = app.query_one("#path-input", Input)
            assert input_field is not None

            # Should have a browse button
            browse_btn = app.query_one("#browse-btn", Button)
            assert browse_btn is not None

    @pytest.mark.asyncio
    async def test_folder_input_validation_valid_path(self, mock_settings, tmp_path):
        """Verify validation shows checkmark for valid paths."""
        app = FolderInputTestApp()
        async with app.run_test() as pilot:
            from textual.widgets import Input

            from ClassicLib.TUI.widgets.folder_input import FolderInput

            folder_input = app.query_one(FolderInput)
            input_field = app.query_one("#path-input", Input)

            # Type a valid directory path using the proper method
            await pilot.click("#path-input")
            input_field.value = str(tmp_path)
            await pilot.pause()
            await pilot.pause()  # Extra pause for validation to run

            # Check that is_valid is True
            assert folder_input.is_valid is True

    @pytest.mark.asyncio
    async def test_folder_input_validation_invalid_path(self, mock_settings):
        """Verify validation marks invalid paths correctly."""
        app = FolderInputTestApp()
        async with app.run_test() as pilot:
            from textual.widgets import Input

            from ClassicLib.TUI.widgets.folder_input import FolderInput

            folder_input = app.query_one(FolderInput)
            input_field = app.query_one("#path-input", Input)

            # Type an invalid path
            await pilot.click("#path-input")
            input_field.value = "/nonexistent/path/that/does/not/exist"
            await pilot.pause()
            await pilot.pause()  # Extra pause for validation to run

            # Check that is_valid is False
            assert folder_input.is_valid is False

    @pytest.mark.asyncio
    async def test_folder_input_empty_is_valid(self, mock_settings):
        """Verify empty input is considered valid (optional field)."""
        app = FolderInputTestApp()
        async with app.run_test() as pilot:
            from ClassicLib.TUI.widgets.folder_input import FolderInput

            folder_input = app.query_one(FolderInput)

            # Empty should be valid - this is the initial state
            assert folder_input.is_valid is True
            assert folder_input.folder_path == ""


class PapyrusMonitorTestApp(App):
    """Minimal app for testing PapyrusMonitor widget."""

    def compose(self) -> ComposeResult:
        from ClassicLib.TUI.widgets.papyrus_monitor import PapyrusMonitor

        yield PapyrusMonitor(id="papyrus-monitor")


class TestPapyrusMonitor:
    """Tests for PapyrusMonitor widget."""

    @pytest.fixture
    def mock_papyrus_deps(self):
        """Mock Papyrus monitoring dependencies."""
        with (
            patch("ClassicLib.io.yaml.classic_settings", return_value=None),
        ):
            yield

    @pytest.mark.asyncio
    async def test_papyrus_monitor_renders(self, mock_papyrus_deps):
        """Verify PapyrusMonitor widget renders."""
        app = PapyrusMonitorTestApp()
        async with app.run_test() as pilot:
            from ClassicLib.TUI.widgets.papyrus_monitor import PapyrusMonitor

            monitor = app.query_one(PapyrusMonitor)
            assert monitor is not None

    @pytest.mark.asyncio
    async def test_papyrus_monitor_starts_stopped(self, mock_papyrus_deps):
        """Verify monitor starts in stopped state."""
        app = PapyrusMonitorTestApp()
        async with app.run_test() as pilot:
            from ClassicLib.TUI.widgets.papyrus_monitor import PapyrusMonitor

            monitor = app.query_one(PapyrusMonitor)
            # Use the actual private attribute as that's how the widget works
            assert monitor._monitoring is False
            assert monitor.stats.is_active is False

    @pytest.mark.asyncio
    async def test_papyrus_monitor_start_stop_cycle(self, mock_papyrus_deps):
        """Verify monitoring can be started and stopped."""
        app = PapyrusMonitorTestApp()
        async with app.run_test() as pilot:
            from ClassicLib.TUI.widgets.papyrus_monitor import PapyrusMonitor

            monitor = app.query_one(PapyrusMonitor)

            # Start monitoring
            monitor.start_monitoring()
            await pilot.pause()
            assert monitor._monitoring is True
            assert monitor.stats.is_active is True

            # Stop monitoring
            monitor.stop_monitoring()
            await pilot.pause()
            assert monitor._monitoring is False
            assert monitor.stats.is_active is False
