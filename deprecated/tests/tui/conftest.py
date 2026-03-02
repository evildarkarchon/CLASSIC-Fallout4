"""TUI test fixtures and configuration.

This module provides fixtures specifically for testing the Textual TUI.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from ClassicLib.TUI.app import CLASSICApp


@pytest.fixture(scope="session", autouse=True)
def enable_tui_test_mode():
    """Enable TUI test mode for all tests in this directory.

    This sets CLASSIC_TUI_TEST_MODE=1 which the TUI checks at startup
    to use mock data instead of real settings. Setting this at session
    scope ensures it's inherited by subprocesses spawned by snapshot tests.
    """
    original_value = os.environ.get("CLASSIC_TUI_TEST_MODE")
    os.environ["CLASSIC_TUI_TEST_MODE"] = "1"
    yield
    # Restore original value
    if original_value is None:
        os.environ.pop("CLASSIC_TUI_TEST_MODE", None)
    else:
        os.environ["CLASSIC_TUI_TEST_MODE"] = original_value


@pytest.fixture
def mock_settings():
    """Mock YAML settings to prevent file I/O during tests."""
    with patch("ClassicLib.io.yaml.classic_settings") as mock:
        mock.return_value = None
        yield mock


@pytest.fixture
def mock_yaml_settings():
    """Mock yaml_settings function for write operations."""
    with patch("ClassicLib.io.yaml.yaml_settings") as mock:
        yield mock


@pytest.fixture
def mock_global_registry():
    """Mock GlobalRegistry to provide safe test paths."""
    mock_registry = MagicMock()
    mock_registry.get_local_dir.return_value = Path.home() / ".classic-test"
    with patch("ClassicLib.core.registry.GlobalRegistry", mock_registry):
        yield mock_registry


@pytest.fixture
def app() -> "CLASSICApp":
    """Create a fresh CLASSICApp instance for testing."""
    from ClassicLib.TUI.app import CLASSICApp

    return CLASSICApp()
