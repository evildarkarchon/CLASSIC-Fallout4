"""Tests for the PapyrusMonitorWidget."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841

from datetime import datetime

import pytest
from textual.app import App

from ClassicLib.TUI.handlers.papyrus_handler import PapyrusStats
from ClassicLib.TUI.widgets.papyrus_monitor import PapyrusMonitorWidget


class TestPapyrusMonitorWidgetInitialization:
    """Test PapyrusMonitorWidget initialization."""

    @pytest.mark.asyncio
    @pytest.mark.gui
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


class TestPapyrusMonitorWidgetStats:
    """Test stats handling in PapyrusMonitorWidget."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_papyrus_monitor_update_stats(self):
        """Test updating statistics in PapyrusMonitorWidget."""
        async with App().run_test() as pilot:
            widget = PapyrusMonitorWidget()
            pilot.app.mount(widget)
            await pilot.pause()

            # Create test stats
            stats = PapyrusStats(
                timestamp=datetime.now(),
                dumps=10,
                stacks=20,
                warnings=30,
                errors=5,
                ratio=0.5,
                raw_output="Test output"
            )

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
    @pytest.mark.gui
    async def test_papyrus_monitor_clear_stats(self):
        """Test clearing statistics in PapyrusMonitorWidget."""
        async with App().run_test() as pilot:
            widget = PapyrusMonitorWidget()
            pilot.app.mount(widget)

            # Set some stats
            stats = PapyrusStats(
                timestamp=datetime.now(),
                dumps=10,
                stacks=20,
                warnings=30,
                errors=5,
                ratio=0.5,
                raw_output="Test"
            )
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


class TestPapyrusMonitorWidgetUnicode:
    """Test Unicode handling in PapyrusMonitorWidget."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_papyrus_monitor_unicode_fallback(self):
        """Test Unicode/ASCII fallback in PapyrusMonitorWidget."""
        async with App().run_test() as pilot:
            # Test Unicode mode
            widget_unicode = PapyrusMonitorWidget(use_unicode=True)
            pilot.app.mount(widget_unicode)

            stats = PapyrusStats(
                timestamp=datetime.now(),
                dumps=0,
                stacks=0,
                warnings=0,
                errors=0,
                ratio=0.0,
                raw_output=""
            )

            # Check Unicode symbols
            symbol = stats.get_status_symbol(True)
            assert symbol in ["✅", "✓", "⚠️", "❌"]

            # Test ASCII mode
            widget_ascii = PapyrusMonitorWidget(use_unicode=False)
            symbol_ascii = stats.get_status_symbol(False)
            assert symbol_ascii in ["[OK]", "[v]", "[!]", "[X]"]


class TestPapyrusMonitorWidgetState:
    """Test state management in PapyrusMonitorWidget."""

    @pytest.mark.asyncio
    @pytest.mark.gui
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


class TestPapyrusMonitorWidgetColorCoding:
    """Test color coding in PapyrusMonitorWidget."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_papyrus_monitor_color_coding(self):
        """Test color coding based on stats in PapyrusMonitorWidget."""
        async with App().run_test() as pilot:
            widget = PapyrusMonitorWidget()
            pilot.app.mount(widget)

            # Test normal state (green)
            stats_normal = PapyrusStats(
                timestamp=datetime.now(),
                dumps=0,
                stacks=0,
                warnings=5,
                errors=2,
                ratio=0.0,
                raw_output=""
            )
            assert stats_normal.get_status_color() == "green"

            # Test warning state (yellow)
            stats_warning = PapyrusStats(
                timestamp=datetime.now(),
                dumps=5,
                stacks=10,
                warnings=25,
                errors=8,
                ratio=0.5,
                raw_output=""
            )
            assert stats_warning.get_status_color() == "yellow"

            # Test error state (red)
            stats_error = PapyrusStats(
                timestamp=datetime.now(),
                dumps=20,
                stacks=30,
                warnings=100,
                errors=15,
                ratio=0.67,
                raw_output=""
            )
            assert stats_error.get_status_color() == "red"
