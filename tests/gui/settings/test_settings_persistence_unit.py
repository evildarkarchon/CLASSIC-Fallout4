"""
Unit tests for settings_persistence - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

import pytest

from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import yaml_settings

pytestmark = pytest.mark.unit


class TestSettingsLoading:
    """Test loading of settings from YAML."""

    def test_load_settings(self, settings_dialog, reset_settings):
        """Test that settings are loaded correctly from YAML."""
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode", True)
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", "GitHub")
        settings_dialog.load_settings()
        assert settings_dialog.vr_checkbox.isChecked()
        assert not settings_dialog.fcx_checkbox.isChecked()
        assert settings_dialog.update_source_combo.currentText() == "GitHub"

    def test_load_all_settings(self, settings_dialog, reset_settings):
        """Test that all settings are loaded correctly."""
        test_values = {
            "CLASSIC_Settings.VR Mode": True,
            "CLASSIC_Settings.FCX Mode": True,
            "CLASSIC_Settings.Simplify Logs": True,
            "CLASSIC_Settings.Show FormID Values": False,
            "CLASSIC_Settings.Move Unsolved Logs": True,
            "CLASSIC_Settings.Update Check": True,
        }
        for key, value in test_values.items():
            yaml_settings(bool, YAML.TEST, key, value)
        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", "Nexus")
        settings_dialog.load_settings()
        assert settings_dialog.vr_checkbox.isChecked()
        assert settings_dialog.fcx_checkbox.isChecked()
        assert settings_dialog.simplify_checkbox.isChecked()
        assert not settings_dialog.show_fid_checkbox.isChecked()
        assert settings_dialog.move_invalid_checkbox.isChecked()
        assert settings_dialog.update_check_checkbox.isChecked()
        assert settings_dialog.update_source_combo.currentText() == "Nexus"


class TestSettingsSaving:
    """Test saving of settings to YAML."""

    def test_save_settings(self, settings_dialog, reset_settings):
        """Test that settings are saved correctly to YAML."""
        settings_dialog.vr_checkbox.setChecked(False)
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.update_source_combo.setCurrentText("Nexus")
        settings_dialog.save_settings()
        assert not yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source") == "Nexus"

    def test_save_all_settings(self, settings_dialog, reset_settings):
        """Test that all settings are saved correctly."""
        settings_dialog.vr_checkbox.setChecked(True)
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.simplify_checkbox.setChecked(True)
        settings_dialog.show_fid_checkbox.setChecked(False)
        settings_dialog.move_invalid_checkbox.setChecked(True)
        settings_dialog.update_check_checkbox.setChecked(True)
        settings_dialog.update_source_combo.setCurrentText("GitHub")
        settings_dialog.save_settings()
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs")
        assert not yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Show FormID Values")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Move Unsolved Logs")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Update Check")
        assert yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source") == "GitHub"
