"""
Unit tests for ui_structure - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

import pytest

pytestmark = [pytest.mark.gui, pytest.mark.unit]

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialogButtonBox


class TestDialogStructure:
    """Test the basic structure and UI elements of SettingsDialog."""

    def test_dialog_properties(self, settings_dialog):
        """Test that dialog has correct properties.

        Note: In test environments, the dialog is created as NonModal to prevent
        freezing when shown. In production, it defaults to ApplicationModal.
        """
        assert settings_dialog.windowTitle() == "CLASSIC Settings"
        assert settings_dialog.minimumWidth() == 600
        assert settings_dialog.minimumHeight() == 500
        # Dialog is NonModal in tests to prevent freezing
        assert settings_dialog.windowModality() == Qt.WindowModality.NonModal

    def test_tab_widget_exists(self, settings_dialog):
        """Test that tab widget is created with correct tabs."""
        assert settings_dialog.tab_widget is not None
        assert settings_dialog.tab_widget.count() == 4
        assert settings_dialog.tab_widget.tabText(0) == "General"
        assert settings_dialog.tab_widget.tabText(1) == "Scanning"
        assert settings_dialog.tab_widget.tabText(2) == "Paths"
        assert settings_dialog.tab_widget.tabText(3) == "Updates"

    def test_general_tab_widgets(self, settings_dialog):
        """Test that General tab has correct widgets."""
        from PySide6.QtWidgets import QComboBox

        assert hasattr(settings_dialog, "game_version_combo")
        assert isinstance(settings_dialog.game_version_combo, QComboBox)
        assert settings_dialog.game_version_combo.count() >= 4  # Auto, Original, NextGen, VR

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
            "game_version",
            "fcx_mode",
            "simplify_logs",
            "show_fid_values",
            "move_invalid_logs",
            "update_check",
            "update_source",
            "ini_folder_path",
        ]
        for key in expected_keys:
            assert key in settings_dialog.settings_widgets


class TestTooltips:
    """Test that tooltips are present and informative."""

    def test_tooltips_present(self, settings_dialog):
        """Test that all widgets have tooltips."""
        assert settings_dialog.game_version_combo.toolTip() != ""
        assert settings_dialog.fcx_checkbox.toolTip() != ""
        assert settings_dialog.simplify_checkbox.toolTip() != ""
        assert settings_dialog.show_fid_checkbox.toolTip() != ""
        assert settings_dialog.move_invalid_checkbox.toolTip() != ""
        assert settings_dialog.update_check_checkbox.toolTip() != ""
        assert settings_dialog.update_source_combo.toolTip() != ""
        assert settings_dialog.check_now_button.toolTip() != ""

    def test_tooltip_content_meaningful(self, settings_dialog):
        """Test that tooltips contain meaningful descriptions."""
        # Game Version combo tooltip should be longer than the current text
        assert len(settings_dialog.game_version_combo.toolTip()) > len(settings_dialog.game_version_combo.currentText())
        assert len(settings_dialog.fcx_checkbox.toolTip()) > len(settings_dialog.fcx_checkbox.text())


class TestGameVersionCombo:
    """Test Game Version combo box functionality."""

    def test_game_version_combo_items(self, settings_dialog):
        """Test Game Version combo has correct items."""
        combo = settings_dialog.game_version_combo
        assert combo.count() >= 4
        # First item should be Auto-detect
        first_item = combo.itemText(0)
        assert "Auto" in first_item or first_item == "Auto-detect"

    def test_game_version_combo_not_editable(self, settings_dialog):
        """Test Game Version combo is not editable."""
        assert not settings_dialog.game_version_combo.isEditable()
