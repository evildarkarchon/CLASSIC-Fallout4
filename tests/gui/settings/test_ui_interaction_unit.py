"""
Unit tests for ui_interaction - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

import os

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers"),
]

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
        checkboxes = [settings_dialog.vr_checkbox, settings_dialog.fcx_checkbox]
        for checkbox in checkboxes:
            assert not checkbox.isTristate()
            assert checkbox.checkState() in [Qt.CheckState.Checked, Qt.CheckState.Unchecked]


class TestComboBoxInteraction:
    """Test combo box interactions."""

    def test_combobox_interaction(self, settings_dialog, app):
        """Test that combo box selection works."""
        combo = settings_dialog.update_source_combo
        combo.setCurrentIndex(0)
        assert combo.currentText() == "Nexus"
        combo.setCurrentIndex(1)
        assert combo.currentText() == "GitHub"
        combo.setCurrentIndex(2)
        assert combo.currentText() == "Both"

    def test_combobox_selection_by_text(self, settings_dialog):
        """Test combo box selection by text."""
        combo = settings_dialog.update_source_combo
        combo.setCurrentText("GitHub")
        assert combo.currentText() == "GitHub"
        assert combo.currentIndex() == 1
        combo.setCurrentText("Nexus")
        assert combo.currentText() == "Nexus"
        assert combo.currentIndex() == 0
        combo.setCurrentText("Both")
        assert combo.currentText() == "Both"
        assert combo.currentIndex() == 2

    def test_combobox_invalid_selection(self, settings_dialog):
        """Test combo box behavior with invalid selection."""
        combo = settings_dialog.update_source_combo
        combo.currentIndex()
        combo.setCurrentText("InvalidOption")
        assert combo.currentText() in ["Nexus", "GitHub", "Both"]

    def test_combobox_item_count(self, settings_dialog):
        """Test that combo box has expected items."""
        combo = settings_dialog.update_source_combo
        assert combo.count() == 3
        items = [combo.itemText(i) for i in range(combo.count())]
        assert items == ["Nexus", "GitHub", "Both"]


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
