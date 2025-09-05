"""
Shared fixtures for settings dialog tests.

Note: These tests use YAML.TEST to avoid modifying production settings.
Due to concurrent file access on the test YAML file, these tests should be run:
- Without parallelization: pytest tests/gui/settings/
- Or with --dist=loadfile when using pytest-xdist to keep all tests on same worker
"""

import pytest
from PySide6.QtWidgets import QWidget

from ClassicLib.Constants import YAML
from ClassicLib.Interface.SettingsDialog import SettingsDialog
from ClassicLib.YamlSettingsCache import yaml_settings


@pytest.fixture
def app(qapp):
    """Provide QApplication instance for tests."""
    return qapp


@pytest.fixture
def settings_dialog(app):
    """Create a SettingsDialog instance for testing."""
    dialog = SettingsDialog(yaml_store=YAML.TEST)
    yield dialog
    dialog.close()


@pytest.fixture
def reset_settings():
    """Reset settings to default values after test."""
    yield
    # Reset to defaults after test
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Audio Notifications", True)
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
