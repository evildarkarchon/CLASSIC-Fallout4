"""
Unit tests for ui_interaction - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

import pytest

pytestmark = [pytest.mark.gui, pytest.mark.unit]

from PySide6.QtCore import Qt


class TestTabNavigation:
    """Test tab widget navigation."""

    def test_tab_visibility(self, settings_dialog):
        """Test that all tabs are visible and enabled."""
        tab_widget = settings_dialog.tab_widget
        tab_bar = tab_widget.tabBar()
        for i in range(tab_widget.count()):
            assert tab_bar.isTabEnabled(i)
            assert tab_bar.isTabVisible(i)


class TestCheckboxInteraction:
    """Test checkbox widget interactions."""

    def test_checkbox_triple_state(self, settings_dialog):
        """Test that checkboxes are not tri-state."""
        # Note: game_version is now a combo box, not a checkbox
        checkboxes = [settings_dialog.fcx_checkbox, settings_dialog.simplify_checkbox]
        for checkbox in checkboxes:
            assert not checkbox.isTristate()
            assert checkbox.checkState() in [Qt.CheckState.Checked, Qt.CheckState.Unchecked]


class TestComboBoxInteraction:
    """Test combo box interactions."""

    def test_game_version_combobox_interaction(self, settings_dialog, app):
        """Test that game version combo box selection works."""
        combo = settings_dialog.game_version_combo
        # First item should be Auto-detect
        combo.setCurrentIndex(0)
        assert "Auto" in combo.currentText()

    def test_game_version_combobox_item_count(self, settings_dialog):
        """Test that game version combo box has expected items."""
        combo = settings_dialog.game_version_combo
        # Should have at least Auto-detect, Original, NextGen, VR
        assert combo.count() >= 4


class TestButtonInteraction:
    """Test button interactions."""

    def test_check_now_button_exists(self, settings_dialog):
        """Test that Check Now button exists and is configured."""
        button = settings_dialog.check_now_button
        assert button is not None
        assert button.text() == "Check for Updates Now"
        assert button.isEnabled()

    def test_button_states(self, settings_dialog):
        """Test button enable/disable states."""
        button = settings_dialog.check_now_button
        assert button.isEnabled()
        button.setEnabled(False)
        assert not button.isEnabled()
        button.setEnabled(True)
        assert button.isEnabled()
