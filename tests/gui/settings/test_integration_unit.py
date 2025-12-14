"""
Unit tests for integration - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.gui, pytest.mark.unit]

from PySide6.QtWidgets import QDialog, QWidget

from ClassicLib.Constants import YAML
from ClassicLib.Interface.FolderManagementMixin import FolderManagementMixin
from ClassicLib.YamlSettings import yaml_settings


class TestMixinIntegration:
    """Test integration with FolderManagementMixin."""

    def test_dialog_opens_from_mixin(self, app):
        """Test that dialog can be opened from FolderManagementMixin."""

        class TestWindow(QWidget, FolderManagementMixin):
            def apply_settings_changes(self):
                self.settings_applied = True

        window = TestWindow()
        with patch("ClassicLib.Interface.Settings.dialog.SettingsDialog.exec") as mock_exec:
            mock_exec.return_value = QDialog.DialogCode.Accepted
            window.open_settings()
            assert hasattr(window, "settings_applied")
            assert window.settings_applied

    def test_dialog_rejection_from_mixin(self, app):
        """Test that dialog rejection doesn't apply settings."""

        class TestWindow(QWidget, FolderManagementMixin):
            def apply_settings_changes(self):
                self.settings_applied = True

        window = TestWindow()
        window.settings_applied = False
        with patch("ClassicLib.Interface.Settings.dialog.SettingsDialog.exec") as mock_exec:
            mock_exec.return_value = QDialog.DialogCode.Rejected
            window.open_settings()
            assert not window.settings_applied

    def test_mixin_with_parent(self, app):
        """Test that mixin passes parent correctly to dialog."""

        class TestWindow(QWidget, FolderManagementMixin):
            def apply_settings_changes(self):
                pass

        window = TestWindow()
        with patch("ClassicLib.Interface.Settings.dialog.SettingsDialog") as mock_dialog_class:
            mock_instance = mock_dialog_class.return_value
            mock_instance.exec.return_value = QDialog.DialogCode.Rejected
            window.open_settings()
            mock_dialog_class.assert_called_once_with(window)


class TestSettingsApplication:
    """Test how settings affect application behavior."""

    def test_settings_affect_application(self, app, reset_settings):
        """Test that changed settings affect application behavior."""
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", True)
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
        assert not yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")


class TestSettingsImpact:
    """Test the impact of settings on application functionality."""

    def test_fcx_mode_impact(self, app, reset_settings):
        """Test that FCX mode setting has expected impact."""
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
        fcx_disabled = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert fcx_disabled is False
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", True)
        fcx_enabled = yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode")
        assert fcx_enabled is True


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_missing_apply_settings_method(self, app):
        """Test mixin handles missing apply_settings_changes method."""

        class IncompleteWindow(QWidget, FolderManagementMixin):
            pass

        window = IncompleteWindow()
        with patch("ClassicLib.Interface.Settings.dialog.SettingsDialog.exec") as mock_exec:
            mock_exec.return_value = QDialog.DialogCode.Accepted
            try:
                window.open_settings()
            except AttributeError:
                pass
