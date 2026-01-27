"""
GUI settings dialog fixtures for CLASSIC-Fallout4 test suite.

This module provides fixtures for testing the settings dialog and
related GUI components, including mock settings cache implementation.

Consolidated from:
- tests/gui/settings/conftest.py

Note: These tests use a mocked settings cache to avoid file I/O and ensure speed.
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QComboBox, QWidget

from ClassicLib.core.constants import YAML
from ClassicLib.Interface.Settings.dialog import SettingsDialog
from ClassicLib.io.yaml import yaml_settings
from ClassicLib.messaging import init_message_handler


def set_game_version_by_value(combo: QComboBox, value: str) -> bool:
    """Set the game version combo box to a specific value.

    Searches for the item whose stored value matches the given value
    and selects it.

    Args:
        combo: The game version QComboBox widget.
        value: The value to select (e.g., "VR", "Original", "NextGen", "auto").

    Returns:
        True if the value was found and selected, False otherwise.
    """
    from ClassicLib.Interface.Settings.tab_creators import ensure_game_version_options

    version_options = ensure_game_version_options()
    for i, (_, stored_value) in enumerate(version_options):
        if stored_value == value:
            combo.setCurrentIndex(i)
            return True
    return False


def get_game_version_value(combo: QComboBox) -> str:
    """Get the stored value for the current selection in the game version combo.

    Args:
        combo: The game version QComboBox widget.

    Returns:
        The stored value (e.g., "VR", "Original", "NextGen", "auto").
    """
    from ClassicLib.Interface.Settings.tab_creators import ensure_game_version_options

    version_options = ensure_game_version_options()
    current_index = combo.currentIndex()
    if 0 <= current_index < len(version_options):
        _, value = version_options[current_index]
        return value
    return "auto"


class MockSettingsCache:
    """Mock YAML settings cache for testing.

    Provides an in-memory implementation of the settings cache
    to avoid file I/O during tests.

    Attributes:
        store: Dictionary storing settings by (yaml_store, key_path) tuples.
    """

    def __init__(self) -> None:
        """Initialize the mock settings cache."""
        self.store: dict[tuple[Any, str], Any] = {}

    def async_yaml_settings(
        self,
        _type: type,
        yaml_store: Any,
        key_path: str,
        new_value: Any | None = None,
    ) -> Any:
        """Get or set a setting value.

        Args:
            _type: The expected type of the setting value.
            yaml_store: The YAML store identifier.
            key_path: The dot-separated path to the setting.
            new_value: Optional new value to set.

        Returns:
            The setting value, or None if not found.
        """
        key = (yaml_store, key_path)
        if new_value is not None:
            self.store[key] = new_value
            return new_value
        return self.store.get(key)

    def batch_get_settings(
        self,
        requests: list[tuple[type, Any, str]],
    ) -> list[Any]:
        """Batch retrieve settings.

        Args:
            requests: List of (type, yaml_store, key_path) tuples.

        Returns:
            List of setting values corresponding to each request.
        """
        return [self.store.get((req[1], req[2])) for req in requests]


class TestWindowMock(QWidget):
    """Mock window class for testing integration with mixins.

    Provides a minimal window implementation for testing
    settings dialog integration.

    Attributes:
        settings_applied: Flag indicating if apply_settings_changes was called.
    """

    def __init__(self) -> None:
        """Initialize the mock window."""
        super().__init__()
        self.settings_applied = False

    def apply_settings_changes(self) -> None:
        """Mock method for applying settings changes."""
        self.settings_applied = True


@pytest.fixture
def gui_settings_mock_cache(monkeypatch: pytest.MonkeyPatch) -> Generator[MockSettingsCache, None, None]:
    """Patch YamlSettingsCache to use in-memory storage.

    This fixture properly handles the module structure where YamlSettingsCache
    is a class with a class-level _instance attribute (singleton pattern),
    and yaml_cache is a proxy object in the convenience module.

    Also resets the GAME_VERSION_OPTIONS global and VersionRegistry to ensure
    test isolation. This is necessary because these globals are lazily populated
    and cached, and tests may run in different orders in CI.

    Args:
        monkeypatch: Pytest's monkeypatch fixture.

    Yields:
        The mock cache instance for test assertions.
    """
    mock_cache = MockSettingsCache()

    # Import the class to patch
    from ClassicLib.io.yaml import YamlSettingsCache

    # Save original instance for cleanup
    original_instance = YamlSettingsCache._instance

    # Reset the singleton instance to None so get_instance will use our mock
    YamlSettingsCache._instance = None

    # Mock the get_instance class method to return our mock cache
    monkeypatch.setattr(YamlSettingsCache, "get_instance", lambda: mock_cache)

    # Reset GAME_VERSION_OPTIONS global to ensure fresh population
    # This is necessary for test isolation when tests run in parallel
    import ClassicLib.Interface.Settings.tab_creators as tab_creators_module

    original_version_options = tab_creators_module.GAME_VERSION_OPTIONS
    tab_creators_module.GAME_VERSION_OPTIONS = []

    # Also reset VersionRegistry to ensure fresh version data
    # The registry uses YAML settings during initialization, so it needs
    # to be reset when the YAML cache is mocked
    from ClassicLib.support.versions.core import VersionRegistry

    original_registry_instance = VersionRegistry._instance
    VersionRegistry._instance = None

    yield mock_cache

    # Restore original states after test (cleanup)
    VersionRegistry._instance = original_registry_instance
    tab_creators_module.GAME_VERSION_OPTIONS = original_version_options
    YamlSettingsCache._instance = original_instance


@pytest.fixture
def gui_settings_app(qapp: Any) -> Any:
    """Provide QApplication instance for tests.

    Args:
        qapp: The Qt application fixture.

    Returns:
        The Qt application instance.
    """
    return qapp


@pytest.fixture
def gui_settings_dialog(
    gui_settings_app: Any,
    gui_settings_mock_cache: MockSettingsCache,
) -> Generator[SettingsDialog, None, None]:
    """Create a SettingsDialog instance for testing.

    The dialog is created as non-modal to prevent freezing when shown during tests.
    This allows tests to safely call show() without the dialog blocking or freezing.

    Args:
        gui_settings_app: The Qt application fixture.
        gui_settings_mock_cache: The mock settings cache.

    Yields:
        A configured SettingsDialog instance.
    """
    # Initialize message handler for GUI mode
    handler = init_message_handler(parent=None, is_gui_mode=True)

    # Mock the GUI backend's show method to prevent blocking QMessageBox
    handler._gui_backend.show = MagicMock()  # pyright: ignore[reportAttributeAccessIssue]

    # Create dialog as NON-MODAL to prevent freezing in tests
    # mock_settings_cache is active (autouse via dependency or singleton patch), so it will use memory
    dialog = SettingsDialog(yaml_store=YAML.TEST, modal=False)
    yield dialog
    dialog.close()


@pytest.fixture
def gui_settings_reset(gui_settings_mock_cache: MockSettingsCache) -> Generator[None, None, None]:
    """Reset settings to default values after test.

    Args:
        gui_settings_mock_cache: The mock settings cache.

    Yields:
        None (cleanup happens after test).
    """
    yield
    # Reset to defaults after test (updates the mock)
    yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Game Version", "auto")
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode", False)  # Legacy setting for migration
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Show FormID Values", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Move Unsolved Logs", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Update Check", False)
    yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", "Both")


# Backward compatibility aliases (deprecated - use prefixed names)
mock_settings_cache = gui_settings_mock_cache
app = gui_settings_app
settings_dialog = gui_settings_dialog
reset_settings = gui_settings_reset
