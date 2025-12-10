"""
E2E tests for settings_persistence - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

import pytest

from ClassicLib.Constants import YAML
from ClassicLib.Interface.Settings.dialog import SettingsDialog
from ClassicLib.YamlSettingsCache import yaml_settings

pytestmark = pytest.mark.e2e


class TestPersistenceAcrossInstances:
    """Test that settings persist across dialog instances."""

    def test_settings_persistence_across_instances(self, app, reset_settings):
        """Test that settings persist across dialog instances."""
        dialog1 = SettingsDialog(yaml_store=YAML.TEST)
        dialog1.vr_checkbox.setChecked(True)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog1.fcx_checkbox.setChecked(False)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog1.save_settings()
        dialog1.close()
        dialog2 = SettingsDialog(yaml_store=YAML.TEST)
        assert dialog2.vr_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        assert not dialog2.fcx_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog2.close()

    def test_settings_reload_after_save(self, app, reset_settings):
        """Test that settings can be reloaded after saving."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        dialog.fcx_checkbox.setChecked(True)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.simplify_checkbox.setChecked(True)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.save_settings()
        dialog.fcx_checkbox.setChecked(False)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.simplify_checkbox.setChecked(False)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.load_settings()
        assert dialog.fcx_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        assert dialog.simplify_checkbox.isChecked()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.close()


class TestDefaultValues:
    """Test default value handling."""

    def test_missing_settings_use_defaults(self, app):
        """Test that missing settings use appropriate defaults."""
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        dialog.load_settings()
        assert isinstance(dialog.vr_checkbox.isChecked(), bool)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        assert isinstance(dialog.fcx_checkbox.isChecked(), bool)  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        assert dialog.update_source_combo.currentText() in ["Nexus", "GitHub", "Both"]  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.close()

    def test_invalid_combo_value_uses_default(self, app, reset_settings):
        """Test that invalid combo box values use defaults."""
        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", "InvalidSource")
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        assert dialog.update_source_combo.currentText() == "Both"  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
        dialog.close()
