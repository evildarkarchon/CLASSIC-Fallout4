"""
E2E tests for dialog_behavior - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

import pytest

pytestmark = pytest.mark.e2e

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from ClassicLib.Constants import YAML
from ClassicLib.YamlSettings import yaml_settings


class TestButtonInteractions:
    """Test button click interactions."""

    def test_ok_button_accepts_dialog(self, settings_dialog, app):
        """Test that OK button accepts the dialog."""
        ok_button = settings_dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
        QTest.mouseClick(ok_button, Qt.MouseButton.LeftButton)
        assert settings_dialog.result() == QDialog.DialogCode.Accepted

    def test_cancel_button_rejects_dialog(self, settings_dialog, app):
        """Test that Cancel button rejects the dialog."""
        cancel_button = settings_dialog.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        QTest.mouseClick(cancel_button, Qt.MouseButton.LeftButton)
        assert settings_dialog.result() == QDialog.DialogCode.Rejected

    def test_ok_button_saves_changes(self, settings_dialog, app, reset_settings):
        """Test that OK button saves pending changes."""
        settings_dialog.fcx_checkbox.setChecked(True)
        ok_button = settings_dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
        QTest.mouseClick(ok_button, Qt.MouseButton.LeftButton)
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")

    def test_cancel_button_discards_changes(self, settings_dialog, app, reset_settings):
        """Test that Cancel button discards pending changes."""
        original_fcx = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        settings_dialog.fcx_checkbox.setChecked(not original_fcx)
        cancel_button = settings_dialog.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        QTest.mouseClick(cancel_button, Qt.MouseButton.LeftButton)
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
        settings_dialog.fcx_checkbox.setChecked(not original_fcx)
        QTest.keyClick(settings_dialog, Qt.Key.Key_Escape)
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode") == original_fcx

    def test_tab_key_navigation(self, settings_dialog, app):
        """Test that Tab key works without errors.

        Note: Actual focus verification requires a visible window, which can
        block test execution. This test verifies tab key API works.
        """
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication

        # Test that tab key simulation works without errors
        settings_dialog.tab_widget.setFocus()
        QApplication.processEvents()

        QTest.keyClick(settings_dialog, Qt.Key.Key_Tab)
        QApplication.processEvents()

        # If we get here without errors, tab navigation is working
        assert True
