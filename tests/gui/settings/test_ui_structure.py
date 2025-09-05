"""
Test suite for SettingsDialog UI structure and elements.

This module tests the basic structure, widgets, and layout of the SettingsDialog.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialogButtonBox

from ClassicLib.Constants import YAML
from ClassicLib.Interface.SettingsDialog import SettingsDialog


class TestDialogStructure:
    """Test the basic structure and UI elements of SettingsDialog."""

    def test_dialog_properties(self, settings_dialog):
        """Test that dialog has correct properties."""
        assert settings_dialog.windowTitle() == "CLASSIC Settings"
        assert settings_dialog.minimumWidth() == 600
        assert settings_dialog.minimumHeight() == 500
        assert settings_dialog.windowModality() == Qt.WindowModality.ApplicationModal

    def test_tab_widget_exists(self, settings_dialog):
        """Test that tab widget is created with correct tabs."""
        assert settings_dialog.tab_widget is not None
        assert settings_dialog.tab_widget.count() == 3
        assert settings_dialog.tab_widget.tabText(0) == "General"
        assert settings_dialog.tab_widget.tabText(1) == "Scanning"
        assert settings_dialog.tab_widget.tabText(2) == "Updates"

    def test_general_tab_widgets(self, settings_dialog):
        """Test that General tab has correct widgets."""
        assert hasattr(settings_dialog, "audio_checkbox")
        assert settings_dialog.audio_checkbox.text() == "Audio Notifications"
        assert hasattr(settings_dialog, "vr_checkbox")
        assert settings_dialog.vr_checkbox.text() == "VR Mode"

    def test_scanning_tab_widgets(self, settings_dialog):
        """Test that Scanning tab has correct widgets."""
        assert hasattr(settings_dialog, "fcx_checkbox")
        assert settings_dialog.fcx_checkbox.text() == "FCX Mode"
        assert hasattr(settings_dialog, "simplify_checkbox")
        assert settings_dialog.simplify_checkbox.text() == "Simplify Logs"
        assert hasattr(settings_dialog, "show_fid_checkbox")
        assert settings_dialog.show_fid_checkbox.text() == "Show FID Values"
        assert hasattr(settings_dialog, "move_invalid_checkbox")
        assert settings_dialog.move_invalid_checkbox.text() == "Move Invalid Logs"

    def test_updates_tab_widgets(self, settings_dialog):
        """Test that Updates tab has correct widgets."""
        assert hasattr(settings_dialog, "update_check_checkbox")
        assert settings_dialog.update_check_checkbox.text() == "Check for Updates"
        assert hasattr(settings_dialog, "update_source_combo")
        assert settings_dialog.update_source_combo.count() == 3
        assert settings_dialog.update_source_combo.itemText(0) == "Nexus"
        assert settings_dialog.update_source_combo.itemText(1) == "GitHub"
        assert settings_dialog.update_source_combo.itemText(2) == "Both"
        assert hasattr(settings_dialog, "check_now_button")
        assert settings_dialog.check_now_button.text() == "Check for Updates Now"

    def test_button_box_exists(self, settings_dialog):
        """Test that dialog has OK/Cancel buttons."""
        assert settings_dialog.button_box is not None
        buttons = settings_dialog.button_box.standardButtons()
        assert buttons & QDialogButtonBox.StandardButton.Ok
        assert buttons & QDialogButtonBox.StandardButton.Cancel

    def test_settings_widgets_dictionary(self, settings_dialog):
        """Test that settings_widgets dictionary is properly populated."""
        assert len(settings_dialog.settings_widgets) == 8
        expected_keys = [
            "audio_notifications",
            "vr_mode",
            "fcx_mode",
            "simplify_logs",
            "show_fid_values",
            "move_invalid_logs",
            "update_check",
            "update_source",
        ]
        for key in expected_keys:
            assert key in settings_dialog.settings_widgets


class TestTooltips:
    """Test that tooltips are present and informative."""

    def test_tooltips_present(self, settings_dialog):
        """Test that all widgets have tooltips."""
        # Check checkbox tooltips
        assert settings_dialog.audio_checkbox.toolTip() != ""
        assert settings_dialog.vr_checkbox.toolTip() != ""
        assert settings_dialog.fcx_checkbox.toolTip() != ""
        assert settings_dialog.simplify_checkbox.toolTip() != ""
        assert settings_dialog.show_fid_checkbox.toolTip() != ""
        assert settings_dialog.move_invalid_checkbox.toolTip() != ""
        assert settings_dialog.update_check_checkbox.toolTip() != ""

        # Check other widget tooltips
        assert settings_dialog.update_source_combo.toolTip() != ""
        assert settings_dialog.check_now_button.toolTip() != ""

    def test_tooltip_content_meaningful(self, settings_dialog):
        """Test that tooltips contain meaningful descriptions."""
        # Check that tooltips are longer than just the widget text
        assert len(settings_dialog.audio_checkbox.toolTip()) > len(settings_dialog.audio_checkbox.text())
        assert len(settings_dialog.fcx_checkbox.toolTip()) > len(settings_dialog.fcx_checkbox.text())


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

        # Modify different settings in each
        dialog1.audio_checkbox.setChecked(True)
        dialog2.audio_checkbox.setChecked(False)

        # Each dialog should maintain its own state until saved
        assert dialog1.audio_checkbox.isChecked()
        assert not dialog2.audio_checkbox.isChecked()

        dialog1.close()
        dialog2.close()

    def test_default_values_created(self, app):
        """Test that default values are created for missing settings."""
        from ClassicLib.YamlSettingsCache import yaml_settings

        # Clear a setting
        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", None)

        # Create dialog - should set default
        dialog = SettingsDialog(yaml_store=YAML.TEST)

        # Verify default was set
        assert dialog.update_source_combo.currentText() == "Both"
        dialog.close()


if __name__ == "__main__":
    pytest.main([__file__])
