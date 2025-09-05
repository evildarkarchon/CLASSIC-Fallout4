"""Shared fixtures and configuration for TUI tests."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.widgets.output_viewer import OutputViewer


@pytest.fixture
def tui_app():
    """Create a TUI app instance for testing."""
    return CLASSICTuiApp()


@pytest.fixture
def output_viewer():
    """Create an OutputViewer instance for testing."""
    return OutputViewer()


@pytest.fixture
def mock_message_handler():
    """Mock the MessageHandler for TUI tests."""
    with patch("ClassicLib.MessageHandler.get_message_handler") as mock_handler:
        mock_msg_handler = MagicMock()
        mock_handler.return_value = mock_msg_handler
        yield mock_msg_handler


@pytest.fixture
def mock_classic_settings():
    """Mock classic_settings for TUI tests."""
    with patch("ClassicLib.TUI.screens.main_screen.classic_settings") as mock_settings:
        # Return empty strings for folder paths by default
        def settings_side_effect(type_hint, key, default=None):
            if "Folder" in key or "Path" in key:
                return ""
            return default

        mock_settings.side_effect = settings_side_effect
        yield mock_settings


@pytest.fixture
def mock_yaml_cache():
    """Mock yaml_cache for TUI tests."""
    with patch("ClassicLib.TUI.screens.settings_screen.yaml_cache") as mock_cache:
        # Return default values for batch_get_settings
        def batch_get_side_effect(requests):
            return [
                "/mock/staging",  # MODS Folder Path
                "/mock/custom",  # SCAN Custom Path
                True,  # Update Check
                True,  # AutoScroll
                True,  # ShowTimestamps
                10000,  # MaxOutputLines
                "Fallout4",  # Game
            ]

        mock_cache.batch_get_settings.side_effect = batch_get_side_effect
        yield mock_cache


@pytest.fixture
def mock_scan_logs():
    """Mock ClassicScanLogs for testing scans."""
    with patch("ClassicLib.TUI.handlers.scan_handler.ClassicScanLogs") as mock_scanner:
        mock_instance = MagicMock()
        mock_instance.scan_logs.return_value = ("Success", ["Result 1", "Result 2"])
        mock_instance.yamldata = MagicMock()
        mock_instance.crashlogs = []
        mock_instance.fcx_mode = False
        mock_instance.show_formid_values = False
        mock_instance.formid_db_exists = False
        mock_instance.crashlog_list = ["test.log"]
        mock_scanner.return_value = mock_instance
        yield mock_scanner


@pytest.fixture
def mock_game_scan():
    """Mock CLASSIC_ScanGame.main for testing game scans."""
    with patch("CLASSIC_ScanGame.main") as mock_main:
        mock_main.return_value = None
        yield mock_main


@pytest.fixture
def mock_papyrus_logging():
    """Mock papyrus_logging for testing Papyrus monitoring."""
    with patch("ClassicLib.TUI.handlers.papyrus_handler.papyrus_logging") as mock_logging:
        # Return basic output by default
        mock_logging.return_value = (
            "NUMBER OF DUMPS    : 0\nNUMBER OF STACKS   : 0\nDUMPS/STACKS RATIO : 0.0\nNUMBER OF WARNINGS : 5\nNUMBER OF ERRORS   : 2\n",
            0
        )
        yield mock_logging


@pytest.fixture
async def tui_pilot(tui_app):
    """Create a test pilot for TUI app testing."""
    async with tui_app.run_test() as pilot:
        await pilot.pause()  # Wait for app to mount
        yield pilot
