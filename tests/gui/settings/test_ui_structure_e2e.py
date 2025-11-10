"""
E2E tests for ui_structure - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

import pytest

from ClassicLib.Constants import YAML
from ClassicLib.Interface.Settings.dialog import SettingsDialog

pytestmark = pytest.mark.e2e


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_dialog_with_no_parent(self, app):
        """Test that dialog works without a parent widget."""
        dialog = SettingsDialog(None, yaml_store=YAML.TEST)
        assert dialog is not None
        assert dialog.windowTitle() == "CLASSIC Settings"
        dialog.close()

    def test_multiple_dialog_instances(self, app):
        """Test that multiple dialog instances don't interfere."""
        dialog1 = SettingsDialog(yaml_store=YAML.TEST)
        dialog2 = SettingsDialog(yaml_store=YAML.TEST)
        dialog1.audio_checkbox.setChecked(True)
        dialog2.audio_checkbox.setChecked(False)
        assert dialog1.audio_checkbox.isChecked()
        assert not dialog2.audio_checkbox.isChecked()
        dialog1.close()
        dialog2.close()

    def test_default_values_created(self, app):
        """Test that default values are created for missing settings."""
        from ClassicLib.YamlSettingsCache import yaml_settings

        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", None)
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        assert dialog.update_source_combo.currentText() == "Both"
        dialog.close()
