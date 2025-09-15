"""
E2E tests for integration - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

from unittest.mock import patch
import pytest
from PySide6.QtWidgets import QDialog, QWidget
from ClassicLib.Constants import YAML
from ClassicLib.Interface.FolderManagementMixin import FolderManagementMixin
from ClassicLib.Interface.SettingsDialog import SettingsDialog
from ClassicLib.YamlSettingsCache import yaml_settings

pytestmark = pytest.mark.e2e

class TestSettingsApplication:
    """Test how settings affect application behavior."""

    def test_vr_mode_setting_propagation(self, app, reset_settings):
        """Test that VR mode setting can be accessed by other components."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        dialog.vr_checkbox.setChecked(True)
        dialog.save_settings()
        dialog.close()
        vr_enabled = yaml_settings(bool, YAML.TEST, 'CLASSIC_Settings.VR Mode')
        assert vr_enabled is True

    def test_update_settings_propagation(self, app, reset_settings):
        """Test that update settings propagate correctly."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        dialog.update_check_checkbox.setChecked(True)
        dialog.update_source_combo.setCurrentText('GitHub')
        dialog.save_settings()
        dialog.close()
        update_enabled = yaml_settings(bool, YAML.TEST, 'CLASSIC_Settings.Update Check')
        update_source = yaml_settings(str, YAML.TEST, 'CLASSIC_Settings.Update Source')
        assert update_enabled is True
        assert update_source == 'GitHub'

class TestMultipleDialogs:
    """Test behavior with multiple dialog instances."""

    def test_sequential_dialogs(self, app, reset_settings):
        """Test opening dialogs sequentially."""
        dialog1 = SettingsDialog(yaml_store=YAML.TEST)
        dialog1.fcx_checkbox.setChecked(True)
        dialog1.accept()
        assert yaml_settings(bool, YAML.TEST, 'CLASSIC_Settings.FCX Mode')
        dialog2 = SettingsDialog(yaml_store=YAML.TEST)
        assert dialog2.fcx_checkbox.isChecked()
        dialog2.close()

    def test_independent_dialog_states(self, app):
        """Test that dialog instances maintain independent states."""
        dialog1 = SettingsDialog(yaml_store=YAML.TEST)
        dialog2 = SettingsDialog(yaml_store=YAML.TEST)
        dialog1.audio_checkbox.setChecked(True)
        dialog1.fcx_checkbox.setChecked(True)
        dialog2.audio_checkbox.setChecked(False)
        dialog2.vr_checkbox.setChecked(True)
        assert dialog1.audio_checkbox.isChecked()
        assert dialog1.fcx_checkbox.isChecked()
        assert not dialog1.vr_checkbox.isChecked()
        assert not dialog2.audio_checkbox.isChecked()
        assert not dialog2.fcx_checkbox.isChecked()
        assert dialog2.vr_checkbox.isChecked()
        dialog1.close()
        dialog2.close()

class TestSettingsImpact:
    """Test the impact of settings on application functionality."""

    def test_simplify_logs_impact(self, app, reset_settings):
        """Test that simplify logs setting has expected impact."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        dialog.simplify_checkbox.setChecked(True)
        dialog.save_settings()
        simplify_enabled = yaml_settings(bool, YAML.TEST, 'CLASSIC_Settings.Simplify Logs')
        assert simplify_enabled is True
        dialog.close()

    def test_audio_notification_impact(self, app, reset_settings):
        """Test that audio notification setting has expected impact."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        original = dialog.audio_checkbox.isChecked()
        dialog.audio_checkbox.setChecked(not original)
        dialog.save_settings()
        new_value = yaml_settings(bool, YAML.TEST, 'CLASSIC_Settings.Audio Notifications')
        assert new_value != original
        dialog.close()

class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_invalid_yaml_store(self, app):
        """Test dialog handles invalid YAML store gracefully."""
        dialog = SettingsDialog(yaml_store=None)
        assert dialog is not None
        dialog.close()
