"""Unit tests for TUI widgets."""

from datetime import datetime
from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Button, Label

from ClassicLib.TUI.handlers.papyrus_handler import PapyrusStats
from ClassicLib.TUI.widgets.confirmation_dialog import (
    ConfirmationDialog,
    ErrorDialog,
    ProgressDialog,
)
from ClassicLib.TUI.widgets.folder_selector import FolderSelector
from ClassicLib.TUI.widgets.output_viewer import OutputViewer
from ClassicLib.TUI.widgets.papyrus_monitor import PapyrusMonitorWidget
from ClassicLib.TUI.widgets.scan_buttons import ScanButton
from ClassicLib.TUI.widgets.status_bar import StatusBar


class TestStatusBar:
    """Test StatusBar widget functionality."""

    @pytest.mark.asyncio
    async def test_status_bar_initialization(self):
        """Test StatusBar initializes with correct default values."""
        async with App().run_test() as pilot:
            status_bar = StatusBar()
            pilot.app.mount(status_bar)

            assert status_bar.current_status == "Ready"
            assert status_bar.last_scan_time == ""
            assert status_bar.scan_folder == ""
            assert status_bar.is_scanning is False

    @pytest.mark.asyncio
    async def test_status_bar_update_status(self):
        """Test updating status text."""
        async with App().run_test() as pilot:
            status_bar = StatusBar()
            pilot.app.mount(status_bar)

            status_bar.update_status("Scanning...", is_error=False)
            assert status_bar.current_status == "Scanning..."
            assert status_bar.is_scanning is True

            status_bar.update_status("Error occurred", is_error=True)
            assert status_bar.current_status == "Error occurred"

    @pytest.mark.asyncio
    async def test_status_bar_mark_scan_complete(self):
        """Test marking scan as complete."""
        async with App().run_test() as pilot:
            status_bar = StatusBar()
            pilot.app.mount(status_bar)

            status_bar.mark_scan_complete(success=True)
            assert status_bar.current_status == "Ready"
            assert status_bar.last_scan_time != ""

            status_bar.mark_scan_complete(success=False)
            assert status_bar.current_status == "Ready (Last scan had errors)"

    @pytest.mark.asyncio
    async def test_status_bar_set_scan_folder(self):
        """Test setting scan folder."""
        async with App().run_test() as pilot:
            status_bar = StatusBar()
            pilot.app.mount(status_bar)

            test_folder = "/path/to/folder"
            status_bar.set_scan_folder(test_folder)
            assert status_bar.scan_folder == test_folder

    @pytest.mark.asyncio
    async def test_status_bar_papyrus_monitoring(self):
        """Test Papyrus monitoring status in StatusBar."""
        async with App().run_test() as pilot:
            status_bar = StatusBar()
            pilot.app.mount(status_bar)

            # Test initial state
            assert status_bar.papyrus_monitoring is False
            assert status_bar.papyrus_stats == ""

            # Test setting monitoring state
            status_bar.set_papyrus_monitoring(True, "(D:5 E:10 W:20)")
            assert status_bar.papyrus_monitoring is True
            assert status_bar.papyrus_stats == "(D:5 E:10 W:20)"

            # Test updating stats
            status_bar.update_papyrus_stats(dumps=10, errors=5, warnings=15)
            assert status_bar.papyrus_stats == "(D:10 E:5 W:15)"

            # Test clearing stats
            status_bar.update_papyrus_stats(0, 0, 0)
            assert status_bar.papyrus_stats == ""


class TestOutputViewer:
    """Test OutputViewer widget functionality."""

    @pytest.mark.asyncio
    async def test_output_viewer_initialization(self):
        """Test OutputViewer initializes correctly."""
        async with App().run_test() as pilot:
            viewer = OutputViewer(max_lines=100, auto_scroll=True)
            pilot.app.mount(viewer)

            assert viewer.max_lines == 100
            assert viewer.auto_scroll is True
            assert viewer.show_timestamps is True
            assert len(viewer._output_buffer) == 0

    @pytest.mark.asyncio
    async def test_output_viewer_append_output(self):
        """Test appending output to viewer."""
        async with App().run_test() as pilot:
            viewer = OutputViewer()
            pilot.app.mount(viewer)

            viewer.append_output("Test message", style="info")
            assert len(viewer._output_buffer) == 1
            assert "Test message" in viewer._output_buffer[0]

            viewer.append_output("Error message", style="error")
            assert len(viewer._output_buffer) == 2

    @pytest.mark.asyncio
    async def test_output_viewer_clear(self):
        """Test clearing output viewer."""
        async with App().run_test() as pilot:
            viewer = OutputViewer()
            pilot.app.mount(viewer)

            viewer.append_output("Message 1")
            viewer.append_output("Message 2")
            assert len(viewer._output_buffer) == 2

            viewer.clear()
            assert len(viewer._output_buffer) == 0

    @pytest.mark.asyncio
    async def test_output_viewer_search(self):
        """Test search functionality."""
        async with App().run_test() as pilot:
            viewer = OutputViewer()
            pilot.app.mount(viewer)

            viewer.append_output("First message")
            viewer.append_output("Second message")
            viewer.append_output("Third message")

            matches = viewer.search("message")
            assert matches == 3

            matches = viewer.search("Second")
            assert matches == 1

            matches = viewer.search("nonexistent")
            assert matches == 0

    @pytest.mark.asyncio
    async def test_output_viewer_toggle_auto_scroll(self):
        """Test toggling auto-scroll."""
        async with App().run_test() as pilot:
            viewer = OutputViewer()
            pilot.app.mount(viewer)

            initial_state = viewer.auto_scroll
            viewer.toggle_auto_scroll()
            assert viewer.auto_scroll != initial_state

            viewer.toggle_auto_scroll()
            assert viewer.auto_scroll == initial_state


class TestFolderSelector:
    """Test FolderSelector widget functionality."""

    @pytest.mark.asyncio
    async def test_folder_selector_initialization(self):
        """Test FolderSelector initializes correctly."""
        async with App().run_test() as pilot:
            selector = FolderSelector(placeholder="Select folder", initial_path="/initial/path")
            pilot.app.mount(selector)

            # Wait for the widget to be composed
            await pilot.pause()

            # The Input widget is internal to FolderSelector
            assert selector._input is not None
            assert selector._input.placeholder == "Select folder"
            assert selector._input.value == "/initial/path"

    @pytest.mark.asyncio
    async def test_folder_selector_validation(self):
        """Test folder path validation."""
        async with App().run_test() as pilot:
            selector = FolderSelector()
            pilot.app.mount(selector)

            # Wait for the widget to be composed
            await pilot.pause()

            # Test valid path
            valid_path = str(Path.home())
            selector.set_path(valid_path)

            # Should accept valid path
            assert selector.valid is True

            # Test invalid path
            invalid_path = "/nonexistent/path/that/does/not/exist"
            selector.set_path(invalid_path)
            assert selector.valid is False


class TestScanButton:
    """Test ScanButton widget functionality."""

    @pytest.mark.asyncio
    async def test_scan_button_initialization(self):
        """Test ScanButton initializes correctly."""
        async with App().run_test() as pilot:
            button = ScanButton(label="Test Scan", variant="primary")
            pilot.app.mount(button)

            # ScanButton IS a Button, not containing one
            assert button.label == "Test Scan"
            assert button.variant == "primary"

    @pytest.mark.asyncio
    async def test_scan_button_state_management(self):
        """Test scan button state changes."""
        async with App().run_test() as pilot:
            button = ScanButton("Test Scan")
            pilot.app.mount(button)

            # Test setting scanning state
            button.start_scan()
            assert button.scanning is True
            assert button.disabled is True

            # Test resetting state
            button.complete_scan(True)
            assert button.scanning is False
            assert button.disabled is False


class TestConfirmationDialogs:
    """Test confirmation dialog widgets."""

    @pytest.mark.asyncio
    async def test_confirmation_dialog(self):
        """Test ConfirmationDialog functionality."""
        async with App().run_test() as pilot:
            confirmed = False
            cancelled = False

            def on_confirm():
                nonlocal confirmed
                confirmed = True

            def on_cancel():
                nonlocal cancelled
                cancelled = True

            dialog = ConfirmationDialog(
                title="Test Confirm", message="Are you sure?", confirm_callback=on_confirm, cancel_callback=on_cancel
            )

            pilot.app.push_screen(dialog)

            # Wait for the screen to be pushed and composed
            await pilot.pause()

            # Test confirm button
            confirm_btn = dialog.query_one("#confirm", Button)
            assert confirm_btn.label == "Yes"

            # Test cancel button
            cancel_btn = dialog.query_one("#cancel", Button)
            assert cancel_btn.label == "No"

    @pytest.mark.asyncio
    async def test_error_dialog(self):
        """Test ErrorDialog functionality."""
        async with App().run_test() as pilot:
            closed = False

            def on_close():
                nonlocal closed
                closed = True

            dialog = ErrorDialog(title="Test Error", message="An error occurred", details="Error details here", close_callback=on_close)

            pilot.app.push_screen(dialog)

            # Wait for the screen to be pushed and composed
            await pilot.pause()

            # Check title and message
            labels = dialog.query(Label)
            assert any("Test Error" in str(label.render()) for label in labels)
            assert any("An error occurred" in str(label.render()) for label in labels)
            assert any("Error details here" in str(label.render()) for label in labels)

    @pytest.mark.asyncio
    async def test_progress_dialog(self):
        """Test ProgressDialog functionality."""
        async with App().run_test() as pilot:
            cancelled = False

            def on_cancel():
                nonlocal cancelled
                cancelled = True

            dialog = ProgressDialog(title="Processing", message="Please wait...", can_cancel=True, cancel_callback=on_cancel)

            pilot.app.push_screen(dialog)

            # Wait for the screen to be pushed and composed
            await pilot.pause()

            # Test progress update
            dialog.update_progress(50, "Halfway done")
            assert dialog.progress == 50

            # Test progress bounds
            dialog.update_progress(150)
            assert dialog.progress == 100

            dialog.update_progress(-10)
            assert dialog.progress == 0

            # Test cancel button exists
            cancel_btn = dialog.query_one("#cancel", Button)
            assert cancel_btn is not None


class TestPapyrusMonitorWidget:
    """Test PapyrusMonitorWidget functionality."""

    @pytest.mark.asyncio
    async def test_papyrus_monitor_initialization(self):
        """Test PapyrusMonitorWidget initializes correctly."""
        async with App().run_test() as pilot:
            widget = PapyrusMonitorWidget(use_unicode=True, show_controls=True)
            pilot.app.mount(widget)

            # Test initial values
            assert widget.dumps == 0
            assert widget.stacks == 0
            assert widget.warnings == 0
            assert widget.errors == 0
            assert widget.ratio == 0.0
            assert widget.is_monitoring is False
            assert widget.use_unicode is True

    @pytest.mark.asyncio
    async def test_papyrus_monitor_update_stats(self):
        """Test updating statistics in PapyrusMonitorWidget."""
        async with App().run_test() as pilot:
            widget = PapyrusMonitorWidget()
            pilot.app.mount(widget)
            await pilot.pause()

            # Create test stats
            stats = PapyrusStats(timestamp=datetime.now(), dumps=10, stacks=20, warnings=30, errors=5, ratio=0.5, raw_output="Test output")

            # Update widget with stats
            widget.update_stats(stats)

            # Verify stats were updated
            assert widget.dumps == 10
            assert widget.stacks == 20
            assert widget.warnings == 30
            assert widget.errors == 5
            assert widget.ratio == 0.5
            assert widget.last_stats == stats

    @pytest.mark.asyncio
    async def test_papyrus_monitor_unicode_fallback(self):
        """Test Unicode/ASCII fallback in PapyrusMonitorWidget."""
        async with App().run_test() as pilot:
            # Test Unicode mode
            widget_unicode = PapyrusMonitorWidget(use_unicode=True)
            pilot.app.mount(widget_unicode)

            stats = PapyrusStats(timestamp=datetime.now(), dumps=0, stacks=0, warnings=0, errors=0, ratio=0.0, raw_output="")

            # Check Unicode symbols
            symbol = stats.get_status_symbol(True)
            assert symbol in ["✅", "✓", "⚠️", "❌"]

            # Test ASCII mode
            widget_ascii = PapyrusMonitorWidget(use_unicode=False)
            symbol_ascii = stats.get_status_symbol(False)
            assert symbol_ascii in ["[OK]", "[v]", "[!]", "[X]"]

    @pytest.mark.asyncio
    async def test_papyrus_monitor_state_management(self):
        """Test monitoring state management in PapyrusMonitorWidget."""
        async with App().run_test() as pilot:
            widget = PapyrusMonitorWidget(show_controls=True)
            pilot.app.mount(widget)
            await pilot.pause()

            # Test setting monitoring state
            widget.set_monitoring_state(True)
            assert widget.is_monitoring is True

            widget.set_monitoring_state(False)
            assert widget.is_monitoring is False

    @pytest.mark.asyncio
    async def test_papyrus_monitor_clear_stats(self):
        """Test clearing statistics in PapyrusMonitorWidget."""
        async with App().run_test() as pilot:
            widget = PapyrusMonitorWidget()
            pilot.app.mount(widget)

            # Set some stats
            stats = PapyrusStats(timestamp=datetime.now(), dumps=10, stacks=20, warnings=30, errors=5, ratio=0.5, raw_output="Test")
            widget.update_stats(stats)

            # Clear stats
            widget.clear_stats()

            # Verify stats were cleared
            assert widget.dumps == 0
            assert widget.stacks == 0
            assert widget.warnings == 0
            assert widget.errors == 0
            assert widget.ratio == 0.0
            assert widget.last_stats is None

    @pytest.mark.asyncio
    async def test_papyrus_monitor_color_coding(self):
        """Test color coding based on stats in PapyrusMonitorWidget."""
        async with App().run_test() as pilot:
            widget = PapyrusMonitorWidget()
            pilot.app.mount(widget)

            # Test normal state (green)
            stats_normal = PapyrusStats(timestamp=datetime.now(), dumps=0, stacks=0, warnings=5, errors=2, ratio=0.0, raw_output="")
            assert stats_normal.get_status_color() == "green"

            # Test warning state (yellow)
            stats_warning = PapyrusStats(timestamp=datetime.now(), dumps=5, stacks=10, warnings=25, errors=8, ratio=0.5, raw_output="")
            assert stats_warning.get_status_color() == "yellow"

            # Test error state (red)
            stats_error = PapyrusStats(timestamp=datetime.now(), dumps=20, stacks=30, warnings=100, errors=15, ratio=0.67, raw_output="")
            assert stats_error.get_status_color() == "red"
