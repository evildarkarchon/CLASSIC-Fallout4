"""
Shared fixtures for settings dialog tests.

Note: These tests use YAML.TEST to avoid modifying production settings.
Due to concurrent file access on the test YAML file, these tests should be run:
- Without parallelization: pytest tests/gui/settings/
- Or with --dist=loadfile when using pytest-xdist to keep all tests on same worker
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QWidget

from ClassicLib.Constants import YAML
from ClassicLib.Interface.SettingsDialog import SettingsDialog
from ClassicLib.MessageHandler import init_message_handler
from ClassicLib.YamlSettingsCache import yaml_settings

# Note: MessageHandler initialization is now handled by standardized
# fixtures in tests/fixtures/registry_fixtures.py which provide:
# - message_handler: For non-GUI tests
# - gui_message_handler: For GUI tests (from qt_fixtures.py)
# - Automatic cleanup via ensure_message_handler_cleanup


@pytest.fixture
def app(qapp):
    """Provide QApplication instance for tests."""
    return qapp


@pytest.fixture
def settings_dialog(app):
    """Create a SettingsDialog instance for testing.

    The dialog is created as non-modal to prevent freezing when shown during tests.
    This allows tests to safely call show() without the dialog blocking or freezing.
    """
    # Initialize message handler for GUI mode
    handler = init_message_handler(parent=None, is_gui_mode=True)

    # Mock the message signal to prevent actual dialog creation
    # This prevents blocking dialogs during tests
    handler.message_signal = MagicMock()

    # Create dialog as NON-MODAL to prevent freezing in tests
    dialog = SettingsDialog(yaml_store=YAML.TEST, modal=False)
    yield dialog
    dialog.close()

    # Clean up message handler


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
