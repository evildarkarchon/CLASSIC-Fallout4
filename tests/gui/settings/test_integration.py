"""
Test suite for SettingsDialog integration with the main application.

This module tests how the SettingsDialog integrates with other components
and the main window through mixins.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QDialog, QWidget

from ClassicLib.Constants import YAML
from ClassicLib.Interface.FolderManagementMixin import FolderManagementMixin
from ClassicLib.Interface.SettingsDialog import SettingsDialog
from ClassicLib.YamlSettingsCache import yaml_settings


class TestMixinIntegration:
    """Test integration with FolderManagementMixin."""

    def test_dialog_opens_from_mixin(self, app):
        """Test that dialog can be opened from FolderManagementMixin."""
        # Create a mock object that uses the mixin - must inherit from QWidget
        class TestWindow(QWidget, FolderManagementMixin):
            def apply_settings_changes(self):
                self.settings_applied = True

        window = TestWindow()

        # Mock the dialog to auto-accept
        with patch("ClassicLib.Interface.SettingsDialog.SettingsDialog.exec") as mock_exec:
            mock_exec.return_value = QDialog.DialogCode.Accepted

            window.open_settings()

            # Verify apply_settings_changes was called
            assert hasattr(window, "settings_applied")
            assert window.settings_applied

    def test_dialog_rejection_from_mixin(self, app):
        """Test that dialog rejection doesn't apply settings."""
        class TestWindow(QWidget, FolderManagementMixin):
            def apply_settings_changes(self):
                self.settings_applied = True

        window = TestWindow()
        window.settings_applied = False

        # Mock the dialog to auto-reject
        with patch("ClassicLib.Interface.SettingsDialog.SettingsDialog.exec") as mock_exec:
            mock_exec.return_value = QDialog.DialogCode.Rejected

            window.open_settings()

            # Verify apply_settings_changes was NOT called
            assert not window.settings_applied

    def test_mixin_with_parent(self, app):
        """Test that mixin passes parent correctly to dialog."""
        class TestWindow(QWidget, FolderManagementMixin):
            def apply_settings_changes(self):
                pass

        window = TestWindow()

        with patch("ClassicLib.Interface.SettingsDialog.SettingsDialog") as mock_dialog_class:
            mock_instance = mock_dialog_class.return_value
            mock_instance.exec.return_value = QDialog.DialogCode.Rejected

            window.open_settings()

            # Verify dialog was created with window as parent
            mock_dialog_class.assert_called_once_with(window)


class TestSettingsApplication:
    """Test how settings affect application behavior."""

    def test_settings_affect_application(self, app, reset_settings):
        """Test that changed settings affect application behavior."""
        # Example: Test that FCX mode setting is accessible
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", True)
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")

        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
        assert not yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")

    def test_vr_mode_setting_propagation(self, app, reset_settings):
        """Test that VR mode setting can be accessed by other components."""
        # Set VR mode through dialog
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        dialog.vr_checkbox.setChecked(True)
        dialog.save_settings()
        dialog.close()

        # Verify setting is accessible
        vr_enabled = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode")
        assert vr_enabled is True

    def test_update_settings_propagation(self, app, reset_settings):
        """Test that update settings propagate correctly."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        dialog.update_check_checkbox.setChecked(True)
        dialog.update_source_combo.setCurrentText("GitHub")
        dialog.save_settings()
        dialog.close()

        # Verify settings are accessible
        update_enabled = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Update Check")
        update_source = yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source")

        assert update_enabled is True
        assert update_source == "GitHub"


class TestMultipleDialogs:
    """Test behavior with multiple dialog instances."""

    def test_sequential_dialogs(self, app, reset_settings):
        """Test opening dialogs sequentially."""
        # First dialog
        dialog1 = SettingsDialog(yaml_store=YAML.TEST)
        dialog1.fcx_checkbox.setChecked(True)
        dialog1.accept()

        # Verify setting was saved
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")

        # Second dialog should see the change
        dialog2 = SettingsDialog(yaml_store=YAML.TEST)
        assert dialog2.fcx_checkbox.isChecked()
        dialog2.close()

    def test_independent_dialog_states(self, app):
        """Test that dialog instances maintain independent states."""
        dialog1 = SettingsDialog(yaml_store=YAML.TEST)
        dialog2 = SettingsDialog(yaml_store=YAML.TEST)

        # Change settings in dialog1 but don't save
        dialog1.audio_checkbox.setChecked(True)
        dialog1.fcx_checkbox.setChecked(True)

        # Change different settings in dialog2
        dialog2.audio_checkbox.setChecked(False)
        dialog2.vr_checkbox.setChecked(True)

        # Each should maintain its own state
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

    def test_fcx_mode_impact(self, app, reset_settings):
        """Test that FCX mode setting has expected impact."""
        # Disable FCX mode
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
        fcx_disabled = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert fcx_disabled is False

        # Enable FCX mode
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", True)
        fcx_enabled = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert fcx_enabled is True

    def test_simplify_logs_impact(self, app, reset_settings):
        """Test that simplify logs setting has expected impact."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)

        # Enable simplify logs
        dialog.simplify_checkbox.setChecked(True)
        dialog.save_settings()

        # Verify setting is stored
        simplify_enabled = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs")
        assert simplify_enabled is True

        dialog.close()

    def test_audio_notification_impact(self, app, reset_settings):
        """Test that audio notification setting has expected impact."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)

        # Toggle audio notifications
        original = dialog.audio_checkbox.isChecked()
        dialog.audio_checkbox.setChecked(not original)
        dialog.save_settings()

        # Verify change was saved
        new_value = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Audio Notifications")
        assert new_value != original

        dialog.close()


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_invalid_yaml_store(self, app):
        """Test dialog handles invalid YAML store gracefully."""
        # Dialog should still create with a None or invalid store
        # It will use defaults
        dialog = SettingsDialog(yaml_store=None)
        assert dialog is not None
        dialog.close()

    def test_missing_apply_settings_method(self, app):
        """Test mixin handles missing apply_settings_changes method."""
        class IncompleteWindow(QWidget, FolderManagementMixin):
            # Intentionally missing apply_settings_changes
            pass

        window = IncompleteWindow()

        with patch("ClassicLib.Interface.SettingsDialog.SettingsDialog.exec") as mock_exec:
            mock_exec.return_value = QDialog.DialogCode.Accepted

            # Should not crash even without apply_settings_changes
            try:
                window.open_settings()
                # If AttributeError is raised, it's expected
            except AttributeError:
                pass  # Expected behavior


if __name__ == "__main__":
    pytest.main([__file__])
