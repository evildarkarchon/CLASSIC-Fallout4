"""Tests for the TuiPapyrusHandler component."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913

from datetime import datetime
from unittest.mock import patch

import pytest

from ClassicLib.TUI.handlers.papyrus_handler import PapyrusStats, TuiPapyrusHandler


class TestPapyrusHandlerInitialization:
    """Test TuiPapyrusHandler initialization."""

    @pytest.mark.asyncio
    async def test_papyrus_handler_initialization(self):
        """Test Papyrus handler initializes correctly."""
        handler = TuiPapyrusHandler(use_unicode=True)

        assert handler.use_unicode is True
        assert handler.is_monitoring is False
        assert handler.last_stats is None


class TestPapyrusHandlerUnicode:
    """Test Unicode handling in TuiPapyrusHandler."""

    @pytest.mark.asyncio
    async def test_papyrus_handler_unicode_detection(self):
        """Test Unicode detection in Papyrus handler."""
        handler = TuiPapyrusHandler()

        # Test manual setting
        handler.set_unicode_mode(False)
        assert handler.use_unicode is False

        handler.set_unicode_mode(True)
        assert handler.use_unicode is True


class TestPapyrusHandlerParsing:
    """Test output parsing in TuiPapyrusHandler."""

    @pytest.mark.asyncio
    async def test_papyrus_handler_parse_output(self):
        """Test parsing Papyrus log output."""
        handler = TuiPapyrusHandler()

        test_output = """
        NUMBER OF DUMPS    : 5
        NUMBER OF STACKS   : 10
        DUMPS/STACKS RATIO : 0.500
        NUMBER OF WARNINGS : 20
        NUMBER OF ERRORS   : 3
        """

        stats = handler._parse_papyrus_output(test_output, 5)

        assert stats.dumps == 5
        assert stats.stacks == 10
        assert stats.ratio == 0.5
        assert stats.warnings == 20
        assert stats.errors == 3


class TestPapyrusHandlerMonitoring:
    """Test monitoring functionality in TuiPapyrusHandler."""

    @pytest.mark.asyncio
    async def test_papyrus_handler_monitoring(self):
        """Test Papyrus monitoring start/stop."""
        handler = TuiPapyrusHandler()

        # Mock papyrus_logging (patch where it's imported in the actual handler)
        with patch("ClassicLib.TUI.handlers.papyrus.tui_papyrus_handler.papyrus_logging") as mock_logging:
            mock_logging.return_value = ("Test output", 0)

            # Start monitoring
            success = await handler.start_monitoring()
            assert success is True
            assert handler.is_monitoring is True

            # Stop monitoring
            await handler.stop_monitoring()
            assert handler.is_monitoring is False


class TestPapyrusHandlerCallbacks:
    """Test callback functionality in TuiPapyrusHandler."""

    @pytest.mark.asyncio
    async def test_papyrus_handler_callbacks(self):
        """Test Papyrus handler callbacks."""
        stats_received = []
        errors_received = []

        def stats_callback(stats):
            stats_received.append(stats)

        def error_callback(error):
            errors_received.append(error)

        handler = TuiPapyrusHandler(stats_callback=stats_callback, error_callback=error_callback)

        # Test stats callback
        test_stats = PapyrusStats(
            timestamp=datetime.now(),
            dumps=5,
            stacks=10,
            warnings=15,
            errors=2,
            ratio=0.5,
            raw_output="Test"
        )

        # Manually trigger callback
        if handler.stats_callback:
            handler.stats_callback(test_stats)

        assert len(stats_received) == 1
        assert stats_received[0] == test_stats

        # Test error callback
        if handler.error_callback:
            handler.error_callback("Test error")

        assert len(errors_received) == 1
        assert errors_received[0] == "Test error"
