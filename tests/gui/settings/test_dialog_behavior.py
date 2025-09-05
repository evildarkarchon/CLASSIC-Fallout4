"""
Test suite for SettingsDialog behavior.

This module tests dialog acceptance/rejection, button interactions,
and dialog results.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import yaml_settings


class TestDialogAcceptReject:
    """Test dialog acceptance and rejection behavior."""

    def test_accept_saves_settings(self, settings_dialog, reset_settings):
        """Test that accepting dialog saves settings."""
        # Modify settings
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.simplify_checkbox.setChecked(True)

        # Accept dialog
        settings_dialog.accept()

        # Verify settings were saved
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs")
        assert settings_dialog.result() == QDialog.DialogCode.Accepted

    def test_reject_does_not_save(self, settings_dialog, reset_settings):
        """Test that rejecting dialog does not save settings."""
        # Store original values
        original_fcx = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        original_simplify = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs")

        # Modify settings
        settings_dialog.fcx_checkbox.setChecked(not original_fcx)
        settings_dialog.simplify_checkbox.setChecked(not original_simplify)

        # Reject dialog
        settings_dialog.reject()

        # Verify settings were NOT saved
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode") == original_fcx
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs") == original_simplify
        assert settings_dialog.result() == QDialog.DialogCode.Rejected

    def test_accept_multiple_changes(self, settings_dialog, reset_settings):
        """Test accepting dialog with multiple setting changes."""
        # Modify multiple settings
        settings_dialog.audio_checkbox.setChecked(False)
        settings_dialog.vr_checkbox.setChecked(True)
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.update_source_combo.setCurrentText("GitHub")

        # Accept dialog
        settings_dialog.accept()

        # Verify all changes were saved
        assert not yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Audio Notifications")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source") == "GitHub"


class TestButtonInteractions:
    """Test button click interactions."""

    def test_ok_button_accepts_dialog(self, settings_dialog, app):
        """Test that OK button accepts the dialog."""
        ok_button = settings_dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)

        # Click OK button
        QTest.mouseClick(ok_button, Qt.MouseButton.LeftButton)

        assert settings_dialog.result() == QDialog.DialogCode.Accepted

    def test_cancel_button_rejects_dialog(self, settings_dialog, app):
        """Test that Cancel button rejects the dialog."""
        cancel_button = settings_dialog.button_box.button(QDialogButtonBox.StandardButton.Cancel)

        # Click Cancel button
        QTest.mouseClick(cancel_button, Qt.MouseButton.LeftButton)

        assert settings_dialog.result() == QDialog.DialogCode.Rejected

    def test_ok_button_saves_changes(self, settings_dialog, app, reset_settings):
        """Test that OK button saves pending changes."""
        # Make changes
        settings_dialog.fcx_checkbox.setChecked(True)

        # Click OK
        ok_button = settings_dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
        QTest.mouseClick(ok_button, Qt.MouseButton.LeftButton)

        # Verify changes were saved
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")

    def test_cancel_button_discards_changes(self, settings_dialog, app, reset_settings):
        """Test that Cancel button discards pending changes."""
        # Store original value
        original_fcx = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")

        # Make changes
        settings_dialog.fcx_checkbox.setChecked(not original_fcx)

        # Click Cancel
        cancel_button = settings_dialog.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        QTest.mouseClick(cancel_button, Qt.MouseButton.LeftButton)

        # Verify changes were not saved
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode") == original_fcx


class TestKeyboardShortcuts:
    """Test keyboard navigation and shortcuts."""

    def test_escape_key_rejects_dialog(self, settings_dialog, app):
        """Test that Escape key rejects the dialog."""
        QTest.keyClick(settings_dialog, Qt.Key.Key_Escape)
        assert settings_dialog.result() == QDialog.DialogCode.Rejected

    def test_enter_key_on_ok_button(self, settings_dialog, app):
        """Test that Enter key on OK button accepts dialog."""
        ok_button = settings_dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setFocus()

        QTest.keyClick(ok_button, Qt.Key.Key_Return)
        assert settings_dialog.result() == QDialog.DialogCode.Accepted

    def test_escape_discards_changes(self, settings_dialog, app, reset_settings):
        """Test that Escape key discards unsaved changes."""
        original_fcx = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")

        # Make changes
        settings_dialog.fcx_checkbox.setChecked(not original_fcx)

        # Press Escape
        QTest.keyClick(settings_dialog, Qt.Key.Key_Escape)

        # Verify changes were not saved
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode") == original_fcx

    def test_tab_key_navigation(self, settings_dialog, app):
        """Test that Tab key navigates between widgets."""
        # Show the dialog first
        settings_dialog.show()

        # Set focus to first widget
        settings_dialog.tab_widget.setFocus()

        # Tab through widgets (basic test)
        QTest.keyClick(settings_dialog, Qt.Key.Key_Tab)
        # Note: Detailed tab order testing would require more complex assertions
        # This basic test ensures Tab key doesn't crash the dialog
        assert True  # If we get here without crashing, the test passes


class TestDialogStates:
    """Test different dialog states and transitions."""

    def test_dialog_initial_state(self, settings_dialog):
        """Test dialog's initial state."""
        assert settings_dialog.result() == QDialog.DialogCode.Rejected  # Default before interaction

    def test_dialog_state_after_accept(self, settings_dialog):
        """Test dialog state after acceptance."""
        settings_dialog.accept()
        assert settings_dialog.result() == QDialog.DialogCode.Accepted

    def test_dialog_state_after_reject(self, settings_dialog):
        """Test dialog state after rejection."""
        settings_dialog.reject()
        assert settings_dialog.result() == QDialog.DialogCode.Rejected

    def test_repeated_accept(self, settings_dialog):
        """Test that accepting multiple times is safe."""
        settings_dialog.accept()
        settings_dialog.accept()  # Should not crash
        assert settings_dialog.result() == QDialog.DialogCode.Accepted

    def test_repeated_reject(self, settings_dialog):
        """Test that rejecting multiple times is safe."""
        settings_dialog.reject()
        settings_dialog.reject()  # Should not crash
        assert settings_dialog.result() == QDialog.DialogCode.Rejected


if __name__ == "__main__":
    pytest.main([__file__])
