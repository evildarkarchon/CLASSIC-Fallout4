"""Tests for the ScanButton widget."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841

import pytest
from textual.app import App

from ClassicLib.TUI.widgets.scan_buttons import ScanButton


class TestScanButtonInitialization:
    """Test ScanButton initialization."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_scan_button_initialization(self):
        """Test ScanButton initializes correctly."""
        async with App().run_test() as pilot:
            button = ScanButton(label="Test Scan", variant="primary")
            pilot.app.mount(button)

            # ScanButton IS a Button, not containing one
            assert button.label == "Test Scan"
            assert button.variant == "primary"


class TestScanButtonStateManagement:
    """Test ScanButton state management."""

    @pytest.mark.asyncio
    @pytest.mark.gui
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
