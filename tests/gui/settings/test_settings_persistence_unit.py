"""
Unit tests for settings_persistence - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

import pytest

pytestmark = [pytest.mark.gui, pytest.mark.unit]

from ClassicLib.Constants import YAML
from ClassicLib.YamlSettings import yaml_settings


class TestSettingsLoading:
    """Test loading of settings from YAML."""

    def test_load_settings(self, settings_dialog, reset_settings):
        """Test that settings are loaded correctly from YAML."""
        from tests.fixtures.gui_settings_fixtures import get_game_version_value

        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Game Version", "VR")
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
        settings_dialog.load_settings()
        assert get_game_version_value(settings_dialog.game_version_combo) == "VR"
        assert not settings_dialog.fcx_checkbox.isChecked()

    def test_load_all_settings(self, settings_dialog, reset_settings):
        """Test that all settings are loaded correctly."""
        from tests.fixtures.gui_settings_fixtures import get_game_version_value

        # Boolean settings (checkboxes)
        test_values = {
            "CLASSIC_Settings.FCX Mode": True,
            "CLASSIC_Settings.Simplify Logs": True,
            "CLASSIC_Settings.Show FormID Values": False,
            "CLASSIC_Settings.Move Unsolved Logs": True,
            "CLASSIC_Settings.Update Check": True,
        }
        for key, value in test_values.items():
            yaml_settings(bool, YAML.TEST, key, value)
        # String settings (dropdowns)
        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Game Version", "NextGen")
        settings_dialog.load_settings()
        assert get_game_version_value(settings_dialog.game_version_combo) == "NextGen"
        assert settings_dialog.fcx_checkbox.isChecked()
        assert settings_dialog.simplify_checkbox.isChecked()
        assert not settings_dialog.show_fid_checkbox.isChecked()
        assert settings_dialog.move_invalid_checkbox.isChecked()
        assert settings_dialog.update_check_checkbox.isChecked()


class TestSettingsSaving:
    """Test saving of settings to YAML."""

    def test_save_settings(self, settings_dialog, reset_settings):
        """Test that settings are saved correctly to YAML."""
        settings_dialog.game_version_combo.setCurrentIndex(0)  # Auto-detect
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.save_settings()
        assert yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Game Version") == "auto"
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")

    def test_save_all_settings(self, settings_dialog, reset_settings):
        """Test that all settings are saved correctly."""
        from tests.fixtures.gui_settings_fixtures import set_game_version_by_value

        set_game_version_by_value(settings_dialog.game_version_combo, "VR")
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.simplify_checkbox.setChecked(True)
        settings_dialog.show_fid_checkbox.setChecked(False)
        settings_dialog.move_invalid_checkbox.setChecked(True)
        settings_dialog.update_check_checkbox.setChecked(True)
        settings_dialog.save_settings()
        assert yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Game Version") == "VR"
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs")
        assert not yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Show FormID Values")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Move Unsolved Logs")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Update Check")


class TestLegacyMigration:
    """Test migration from legacy VR Mode to Game Version."""

    def test_legacy_vr_mode_migrates(self, settings_dialog, reset_settings):
        """Test legacy VR Mode True migrates to Game Version VR."""
        from tests.fixtures.gui_settings_fixtures import get_game_version_value

        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode", True)
        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Game Version", "auto")
        settings_dialog.load_settings()
        assert get_game_version_value(settings_dialog.game_version_combo) == "VR"

    def test_legacy_vr_mode_false_no_migration(self, settings_dialog, reset_settings):
        """Test legacy VR Mode False does not override Game Version."""
        from tests.fixtures.gui_settings_fixtures import get_game_version_value

        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode", False)
        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Game Version", "Original")
        settings_dialog.load_settings()
        assert get_game_version_value(settings_dialog.game_version_combo) == "Original"
