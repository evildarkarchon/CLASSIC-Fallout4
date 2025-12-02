"""
Shared fixtures for settings dialog tests.

Note: These tests use a mocked settings cache to avoid file I/O and ensure speed.
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QWidget

from ClassicLib.Constants import YAML
from ClassicLib.Interface.Settings.dialog import SettingsDialog
from ClassicLib.MessageHandler import init_message_handler
from ClassicLib.YamlSettingsCache import yaml_settings

# Mock Cache Implementation
class MockSettingsCache:
    def __init__(self):
        self.store = {}  # (yaml_store, key_path) -> value

    def async_yaml_settings(self, _type, yaml_store, key_path, new_value=None):
        key = (yaml_store, key_path)
        if new_value is not None:
            self.store[key] = new_value
            return new_value
        return self.store.get(key)

    def batch_get_settings(self, requests):
        # requests: list of (type, yaml_store, key_path)
        return [self.store.get((req[1], req[2])) for req in requests]

@pytest.fixture
def mock_settings_cache(monkeypatch):
    """Patches YamlSettingsCache to use in-memory storage."""
    mock_cache = MockSettingsCache()
    
    # Import the class to patch
    from ClassicLib.YamlSettingsCache import YamlSettingsCache
    import sys
    
    # Ensure module is loaded
    import ClassicLib.YamlSettingsCache

    # Mock the get_instance class method
    monkeypatch.setattr(
        YamlSettingsCache,
        "get_instance",
        lambda: mock_cache
    )
    
    # Reset the singleton in the module to force usage of our mock
    # Use sys.modules to ensure we get the module object, not the class if shadowed
    module = sys.modules["ClassicLib.YamlSettingsCache"]
    monkeypatch.setattr(module, "_yaml_cache", None)
    
    return mock_cache

@pytest.fixture
def app(qapp):
    """Provide QApplication instance for tests."""
    return qapp


@pytest.fixture
def settings_dialog(app, mock_settings_cache):
    """Create a SettingsDialog instance for testing.

    The dialog is created as non-modal to prevent freezing when shown during tests.
    This allows tests to safely call show() without the dialog blocking or freezing.
    """
    # Initialize message handler for GUI mode
    handler = init_message_handler(parent=None, is_gui_mode=True)

    # Mock the GUI backend's show method to prevent blocking QMessageBox.exec()
    handler._gui_backend.show = MagicMock()

    # Create dialog as NON-MODAL to prevent freezing in tests
    # mock_settings_cache is active (autouse via dependency or singleton patch), so it will use memory
    dialog = SettingsDialog(yaml_store=YAML.TEST, modal=False)
    yield dialog
    dialog.close()


@pytest.fixture
def reset_settings(mock_settings_cache):
    """Reset settings to default values after test."""
    yield
    # Reset to defaults after test (updates the mock)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Show FormID Values", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Move Unsolved Logs", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Update Check", False)
    yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", "Both")


class TestWindowMock(QWidget):
    """Mock window class for testing integration with mixins."""

    def __init__(self):
        super().__init__()
        self.settings_applied = False

    def apply_settings_changes(self):
        """Mock method for applying settings changes."""
        self.settings_applied = True