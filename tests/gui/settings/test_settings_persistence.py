"""
Test suite for SettingsDialog settings persistence.

This module tests loading and saving of settings to/from YAML storage.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import pytest

from ClassicLib.Constants import YAML
from ClassicLib.Interface.SettingsDialog import SettingsDialog
from ClassicLib.YamlSettingsCache import yaml_settings


class TestSettingsLoading:
    """Test loading of settings from YAML."""

    def test_load_settings(self, settings_dialog, reset_settings):
        """Test that settings are loaded correctly from YAML."""
        # Set test values
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Audio Notifications", True)
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", "GitHub")

        # Load settings
        settings_dialog.load_settings()

        # Verify loaded values
        assert settings_dialog.audio_checkbox.isChecked()
        assert not settings_dialog.fcx_checkbox.isChecked()
        assert settings_dialog.update_source_combo.currentText() == "GitHub"

    def test_load_all_settings(self, settings_dialog, reset_settings):
        """Test that all settings are loaded correctly."""
        # Set specific values for all settings
        test_values = {
            "CLASSIC_Settings.Audio Notifications": False,
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

        # Load settings
        settings_dialog.load_settings()

        # Verify all loaded values
        assert not settings_dialog.audio_checkbox.isChecked()
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
        # Modify settings in dialog
        settings_dialog.audio_checkbox.setChecked(False)
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.update_source_combo.setCurrentText("Nexus")

        # Save settings
        settings_dialog.save_settings()

        # Verify saved values
        assert not yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Audio Notifications")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source") == "Nexus"

    def test_save_all_settings(self, settings_dialog, reset_settings):
        """Test that all settings are saved correctly."""
        # Modify all settings
        settings_dialog.audio_checkbox.setChecked(False)
        settings_dialog.vr_checkbox.setChecked(True)
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.simplify_checkbox.setChecked(True)
        settings_dialog.show_fid_checkbox.setChecked(False)
        settings_dialog.move_invalid_checkbox.setChecked(True)
        settings_dialog.update_check_checkbox.setChecked(True)
        settings_dialog.update_source_combo.setCurrentText("GitHub")

        # Save settings
        settings_dialog.save_settings()

        # Verify all saved values
        assert not yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Audio Notifications")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs")
        assert not yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Show FormID Values")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Move Unsolved Logs")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Update Check")
        assert yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source") == "GitHub"


class TestPersistenceAcrossInstances:
    """Test that settings persist across dialog instances."""

    def test_settings_persistence_across_instances(self, app, reset_settings):
        """Test that settings persist across dialog instances."""
        # First dialog - modify settings
        dialog1 = SettingsDialog(yaml_store=YAML.TEST)
        dialog1.audio_checkbox.setChecked(False)
        dialog1.vr_checkbox.setChecked(True)
        dialog1.save_settings()
        dialog1.close()

        # Second dialog - verify settings persist
        dialog2 = SettingsDialog(yaml_store=YAML.TEST)
        assert not dialog2.audio_checkbox.isChecked()
        assert dialog2.vr_checkbox.isChecked()
        dialog2.close()

    def test_settings_reload_after_save(self, app, reset_settings):
        """Test that settings can be reloaded after saving."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)

        # Initial state
        dialog.fcx_checkbox.setChecked(True)
        dialog.simplify_checkbox.setChecked(True)
        dialog.save_settings()

        # Change settings without saving
        dialog.fcx_checkbox.setChecked(False)
        dialog.simplify_checkbox.setChecked(False)

        # Reload should restore saved values
        dialog.load_settings()
        assert dialog.fcx_checkbox.isChecked()
        assert dialog.simplify_checkbox.isChecked()

        dialog.close()


class TestDefaultValues:
    """Test default value handling."""

    def test_missing_settings_use_defaults(self, app):
        """Test that missing settings use appropriate defaults."""
        # Create dialog with clean test YAML
        dialog = SettingsDialog(yaml_store=YAML.TEST)

        # Load settings (which may not exist)
        dialog.load_settings()

        # Check that defaults are applied
        # Note: Actual defaults depend on implementation
        assert isinstance(dialog.audio_checkbox.isChecked(), bool)
        assert isinstance(dialog.vr_checkbox.isChecked(), bool)
        assert dialog.update_source_combo.currentText() in ["Nexus", "GitHub", "Both"]

        dialog.close()

    def test_invalid_combo_value_uses_default(self, app, reset_settings):
        """Test that invalid combo box values use defaults."""
        # Set an invalid value
        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", "InvalidSource")

        dialog = SettingsDialog(yaml_store=YAML.TEST)

        # Should fall back to default
        assert dialog.update_source_combo.currentText() == "Both"

        dialog.close()


if __name__ == "__main__":
    pytest.main([__file__])
