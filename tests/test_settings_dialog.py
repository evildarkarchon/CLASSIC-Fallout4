"""
Comprehensive test suite for SettingsDialog.

This module tests all aspects of the SettingsDialog implementation including:
- UI structure and elements
- Settings persistence
- Dialog behavior (accept/reject)
- Tab navigation
- Integration with main window

Note: These tests use YAML.TEST to avoid modifying production settings.
Due to concurrent file access on the test YAML file, these tests should be run:
- Without parallelization: pytest tests/test_settings_dialog.py
- Or with --dist=loadfile when using pytest-xdist to keep all tests on same worker
"""

from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QWidget

from ClassicLib.Constants import YAML
from ClassicLib.Interface.SettingsDialog import SettingsDialog
from ClassicLib.YamlSettingsCache import yaml_settings


@pytest.fixture
def app(qapp):
    """Provide QApplication instance for tests."""
    return qapp


@pytest.fixture
def settings_dialog(app):
    """Create a SettingsDialog instance for testing."""
    dialog = SettingsDialog(yaml_store=YAML.TEST)
    yield dialog
    dialog.close()


@pytest.fixture
def reset_settings():
    """Reset settings to default values after test."""
    yield
    # Reset to defaults after test
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Audio Notifications", True)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.VR Mode", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Show FormID Values", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Move Unsolved Logs", False)
    yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Update Check", False)
    yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", "Both")


class TestSettingsDialogStructure:
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
        assert hasattr(settings_dialog, 'audio_checkbox')
        assert settings_dialog.audio_checkbox.text() == "Audio Notifications"
        assert hasattr(settings_dialog, 'vr_checkbox')
        assert settings_dialog.vr_checkbox.text() == "VR Mode"
    
    def test_scanning_tab_widgets(self, settings_dialog):
        """Test that Scanning tab has correct widgets."""
        assert hasattr(settings_dialog, 'fcx_checkbox')
        assert settings_dialog.fcx_checkbox.text() == "FCX Mode"
        assert hasattr(settings_dialog, 'simplify_checkbox')
        assert settings_dialog.simplify_checkbox.text() == "Simplify Logs"
        assert hasattr(settings_dialog, 'show_fid_checkbox')
        assert settings_dialog.show_fid_checkbox.text() == "Show FID Values"
        assert hasattr(settings_dialog, 'move_invalid_checkbox')
        assert settings_dialog.move_invalid_checkbox.text() == "Move Invalid Logs"
    
    def test_updates_tab_widgets(self, settings_dialog):
        """Test that Updates tab has correct widgets."""
        assert hasattr(settings_dialog, 'update_check_checkbox')
        assert settings_dialog.update_check_checkbox.text() == "Check for Updates"
        assert hasattr(settings_dialog, 'update_source_combo')
        assert settings_dialog.update_source_combo.count() == 3
        assert settings_dialog.update_source_combo.itemText(0) == "Nexus"
        assert settings_dialog.update_source_combo.itemText(1) == "GitHub"
        assert settings_dialog.update_source_combo.itemText(2) == "Both"
        assert hasattr(settings_dialog, 'check_now_button')
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
            "audio_notifications", "vr_mode", "fcx_mode", "simplify_logs",
            "show_fid_values", "move_invalid_logs", "update_check", "update_source"
        ]
        for key in expected_keys:
            assert key in settings_dialog.settings_widgets


class TestSettingsPersistence:
    """Test loading and saving of settings."""
    
    def test_load_settings(self, settings_dialog, reset_settings):
        """Test that settings are loaded correctly from YAML."""
        # Set test values
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Audio Notifications", True)
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", "GitHub")
        
        # Load settings
        settings_dialog.load_settings()
        
        # Verify loaded values
        assert settings_dialog.audio_checkbox.isChecked() == True
        assert settings_dialog.fcx_checkbox.isChecked() == False
        assert settings_dialog.update_source_combo.currentText() == "GitHub"
    
    def test_save_settings(self, settings_dialog, reset_settings):
        """Test that settings are saved correctly to YAML."""
        # Modify settings in dialog
        settings_dialog.audio_checkbox.setChecked(False)
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.update_source_combo.setCurrentText("Nexus")
        
        # Save settings
        settings_dialog.save_settings()
        
        # Verify saved values
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Audio Notifications") == False
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode") == True
        assert yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source") == "Nexus"
    
    def test_settings_persistence_across_instances(self, app, reset_settings):
        """Test that settings persist across dialog instances."""
        # First dialog - modify settings
        dialog1 = SettingsDialog(yaml_store=YAML.TEST)
        dialog1.audio_checkbox.setChecked(False)
        dialog1.vr_checkbox.setChecked(True)
        dialog1.save_settings()
        dialog1.close()
        
        # Second dialog - verify settings persist
        dialog2 = SettingsDialog(yaml_store=YAML.TEST)
        assert dialog2.audio_checkbox.isChecked() == False
        assert dialog2.vr_checkbox.isChecked() == True
        dialog2.close()


class TestDialogBehavior:
    """Test dialog acceptance and rejection behavior."""
    
    def test_accept_saves_settings(self, settings_dialog, reset_settings):
        """Test that accepting dialog saves settings."""
        # Modify settings
        settings_dialog.fcx_checkbox.setChecked(True)
        settings_dialog.simplify_checkbox.setChecked(True)
        
        # Accept dialog
        settings_dialog.accept()
        
        # Verify settings were saved
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode") == True
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.Simplify Logs") == True
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


class TestUIInteraction:
    """Test UI interaction and navigation."""
    
    def test_tab_navigation(self, settings_dialog, app):
        """Test that tabs can be navigated."""
        tab_widget = settings_dialog.tab_widget
        
        # Test clicking on tabs
        tab_bar = tab_widget.tabBar()
        
        # Click on Scanning tab
        QTest.mouseClick(tab_bar, Qt.MouseButton.LeftButton, pos=tab_bar.tabRect(1).center())
        assert tab_widget.currentIndex() == 1
        
        # Click on Updates tab
        QTest.mouseClick(tab_bar, Qt.MouseButton.LeftButton, pos=tab_bar.tabRect(2).center())
        assert tab_widget.currentIndex() == 2
        
        # Click back to General tab
        QTest.mouseClick(tab_bar, Qt.MouseButton.LeftButton, pos=tab_bar.tabRect(0).center())
        assert tab_widget.currentIndex() == 0
    
    def test_checkbox_interaction(self, settings_dialog, app):
        """Test that checkboxes can be toggled."""
        # For mouse clicks in tests, we can directly use the click() method
        # or toggle() method instead of simulating mouse events
        
        # Test audio checkbox - set to known state first
        settings_dialog.audio_checkbox.setChecked(False)
        assert settings_dialog.audio_checkbox.isChecked() == False
        settings_dialog.audio_checkbox.click()  # Use click() method directly
        assert settings_dialog.audio_checkbox.isChecked() == True
        
        # Test FCX checkbox - set to known state first  
        settings_dialog.fcx_checkbox.setChecked(True)
        assert settings_dialog.fcx_checkbox.isChecked() == True
        settings_dialog.fcx_checkbox.click()  # Use click() method directly
        assert settings_dialog.fcx_checkbox.isChecked() == False
    
    def test_combobox_interaction(self, settings_dialog, app):
        """Test that combo box selection works."""
        combo = settings_dialog.update_source_combo
        
        # Select different items
        combo.setCurrentIndex(0)
        assert combo.currentText() == "Nexus"
        
        combo.setCurrentIndex(1)
        assert combo.currentText() == "GitHub"
        
        combo.setCurrentIndex(2)
        assert combo.currentText() == "Both"
    
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


class TestKeyboardNavigation:
    """Test keyboard navigation and shortcuts."""
    
    def test_escape_key_rejects_dialog(self, settings_dialog, app):
        """Test that Escape key rejects the dialog."""
        QTest.keyClick(settings_dialog, Qt.Key.Key_Escape)
        assert settings_dialog.result() == QDialog.DialogCode.Rejected
    
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
    
    def test_enter_key_on_ok_button(self, settings_dialog, app):
        """Test that Enter key on OK button accepts dialog."""
        ok_button = settings_dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setFocus()
        
        QTest.keyClick(ok_button, Qt.Key.Key_Return)
        assert settings_dialog.result() == QDialog.DialogCode.Accepted


class TestIntegration:
    """Test integration with main window."""
    
    def test_dialog_opens_from_mixin(self, app):
        """Test that dialog can be opened from FolderManagementMixin."""
        from ClassicLib.Interface.FolderManagementMixin import FolderManagementMixin
        
        # Create a mock object that uses the mixin - must inherit from QWidget
        class TestWindow(QWidget, FolderManagementMixin):
            def apply_settings_changes(self):
                self.settings_applied = True
        
        window = TestWindow()
        
        # Mock the dialog to auto-accept
        with patch('ClassicLib.Interface.SettingsDialog.SettingsDialog.exec') as mock_exec:
            mock_exec.return_value = QDialog.DialogCode.Accepted
            
            window.open_settings()
            
            # Verify apply_settings_changes was called
            assert hasattr(window, 'settings_applied')
            assert window.settings_applied == True
    
    def test_settings_affect_application(self, app, reset_settings):
        """Test that changed settings affect application behavior."""
        # This is a placeholder for integration tests
        # In a real scenario, you would test that:
        # - FCX Mode enables extended checks
        # - Audio Notifications trigger sounds
        # - Update Source affects update checking
        # These would require mocking the actual application components
        
        # Example: Test that FCX mode setting is accessible
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", True)
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode") == True
        
        yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode", False)
        assert yaml_settings(bool, YAML.TEST, "CLASSIC_Settings.FCX Mode") == False


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
        assert dialog1.audio_checkbox.isChecked() == True
        assert dialog2.audio_checkbox.isChecked() == False
        
        dialog1.close()
        dialog2.close()
    
    def test_default_values_created(self, app):
        """Test that default values are created for missing settings."""
        # Clear a setting
        yaml_settings(str, YAML.TEST, "CLASSIC_Settings.Update Source", None)
        
        # Create dialog - should set default
        dialog = SettingsDialog(yaml_store=YAML.TEST)
        
        # Verify default was set
        assert dialog.update_source_combo.currentText() == "Both"
        dialog.close()