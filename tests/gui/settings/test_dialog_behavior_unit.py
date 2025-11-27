"""
Unit tests for dialog_behavior - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

import os

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers"),
]

from PySide6.QtWidgets import QDialog

from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import yaml_settings


class TestDialogAcceptReject:
    """Test dialog acceptance and rejection behavior."""

    def test_accept_saves_settings(self, settings_dialog, reset_settings):
        """Test that accepting dialog saves settings."""
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.simplify_checkbox.setChecked(True)
        settings_dialog.accept()
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs")
        assert settings_dialog.result() == QDialog.DialogCode.Accepted

    def test_reject_does_not_save(self, settings_dialog, reset_settings):
        """Test that rejecting dialog does not save settings."""
        original_fcx = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        original_simplify = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs")
        settings_dialog.fcx_checkbox.setChecked(not original_fcx)
        settings_dialog.simplify_checkbox.setChecked(not original_simplify)
        settings_dialog.reject()
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode") == original_fcx
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs") == original_simplify
        assert settings_dialog.result() == QDialog.DialogCode.Rejected

    def test_accept_multiple_changes(self, settings_dialog, reset_settings):
        """Test accepting dialog with multiple setting changes."""
        settings_dialog.vr_checkbox.setChecked(True)
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.update_source_combo.setCurrentText("GitHub")
        settings_dialog.accept()
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode")
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source") == "GitHub"


class TestDialogStates:
    """Test different dialog states and transitions."""

    def test_dialog_initial_state(self, settings_dialog):
        """Test dialog's initial state."""
        assert settings_dialog.result() == QDialog.DialogCode.Rejected

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
        settings_dialog.accept()
        assert settings_dialog.result() == QDialog.DialogCode.Accepted

    def test_repeated_reject(self, settings_dialog):
        """Test that rejecting multiple times is safe."""
        settings_dialog.reject()
        settings_dialog.reject()
        assert settings_dialog.result() == QDialog.DialogCode.Rejected
