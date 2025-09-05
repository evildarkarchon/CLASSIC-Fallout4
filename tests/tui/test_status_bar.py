"""Tests for the StatusBar widget."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841

import pytest
from textual.app import App

from ClassicLib.TUI.widgets.status_bar import StatusBar


class TestStatusBarInitialization:
    """Test StatusBar initialization."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_status_bar_initialization(self):
        """Test StatusBar initializes with correct default values."""
        async with App().run_test() as pilot:
            status_bar = StatusBar()
            pilot.app.mount(status_bar)

            assert status_bar.current_status == "Ready"
            assert status_bar.last_scan_time == ""
            assert status_bar.scan_folder == ""
            assert status_bar.is_scanning is False


class TestStatusBarUpdates:
    """Test StatusBar status updates."""

    @pytest.mark.asyncio
    @pytest.mark.gui
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
    @pytest.mark.gui
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
    @pytest.mark.gui
    async def test_status_bar_set_scan_folder(self):
        """Test setting scan folder."""
        async with App().run_test() as pilot:
            status_bar = StatusBar()
            pilot.app.mount(status_bar)

            test_folder = "/path/to/folder"
            status_bar.set_scan_folder(test_folder)
            assert status_bar.scan_folder == test_folder


class TestStatusBarPapyrusMonitoring:
    """Test Papyrus monitoring status in StatusBar."""

    @pytest.mark.asyncio
    @pytest.mark.gui
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
