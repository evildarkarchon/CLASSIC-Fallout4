"""
E2E tests for integration - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

import pytest

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

from ClassicLib.Constants import YAML
from ClassicLib.Interface.Settings.dialog import SettingsDialog
from ClassicLib.YamlSettings import yaml_settings

# Note: MessageHandler initialization is now handled by standardized
# fixtures in tests/fixtures/registry_fixtures.py which provide:
# - message_handler: For non-GUI tests
# - gui_message_handler: For GUI tests (from qt_fixtures.py)
# - Automatic cleanup via ensure_message_handler_cleanup


class TestSettingsApplication:
    """Test how settings affect application behavior."""

    def test_vr_mode_setting_propagation(self, app, reset_settings, gui_message_handler, async_bridge):
        """Test that VR mode setting can be accessed by other components."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        dialog.vr_checkbox.setChecked(True)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.save_settings()
        dialog.close()
        vr_enabled = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode")
        assert vr_enabled is True

    def test_update_settings_propagation(self, app, reset_settings, gui_message_handler, async_bridge):
        """Test that update settings propagate correctly."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        dialog.update_check_checkbox.setChecked(True)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.update_source_combo.setCurrentText("GitHub")  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.save_settings()
        dialog.close()
        update_enabled = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Update Check")
        update_source = yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source")
        assert update_enabled is True
        assert update_source == "GitHub"


class TestMultipleDialogs:
    """Test behavior with multiple dialog instances."""

    def test_sequential_dialogs(self, app, reset_settings, gui_message_handler, async_bridge):
        """Test opening dialogs sequentially."""
        dialog1 = SettingsDialog(yaml_store=YAML.TEST)
        dialog1.fcx_checkbox.setChecked(True)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog1.accept()
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        dialog2 = SettingsDialog(yaml_store=YAML.TEST)
        assert dialog2.fcx_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog2.close()

    def test_independent_dialog_states(self, app, gui_message_handler):
        """Test that dialog instances maintain independent states."""
        dialog1 = SettingsDialog(yaml_store=YAML.TEST)
        dialog2 = SettingsDialog(yaml_store=YAML.TEST)
        dialog1.vr_checkbox.setChecked(True)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog1.fcx_checkbox.setChecked(True)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog2.vr_checkbox.setChecked(False)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog2.simplify_checkbox.setChecked(True)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        assert dialog1.vr_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        assert dialog1.fcx_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        assert not dialog1.simplify_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        assert not dialog2.vr_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        assert not dialog2.fcx_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        assert dialog2.simplify_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog1.close()
        dialog2.close()


class TestSettingsImpact:
    """Test the impact of settings on application functionality."""

    def test_simplify_logs_impact(self, app, reset_settings, gui_message_handler, async_bridge):
        """Test that simplify logs setting has expected impact."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        dialog.simplify_checkbox.setChecked(True)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.save_settings()
        simplify_enabled = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs")
        assert simplify_enabled is True
        dialog.close()

    def test_vr_mode_impact(self, app, reset_settings, gui_message_handler, async_bridge):
        """Test that VR mode setting has expected impact."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        original = dialog.vr_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.vr_checkbox.setChecked(not original)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.save_settings()
        new_value = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode")
        assert new_value != original
        dialog.close()


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_invalid_yaml_store(self, app, gui_message_handler):
        """Test dialog handles invalid YAML store gracefully."""
        dialog = SettingsDialog(yaml_store=None)  # pyright: ignore[reportArgumentType]
        assert dialog is not None
        dialog.close()
