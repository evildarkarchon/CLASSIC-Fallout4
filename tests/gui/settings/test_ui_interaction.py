"""
Test suite for SettingsDialog UI interactions.

This module tests user interactions with dialog widgets including
checkboxes, combo boxes, buttons, and tab navigation.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


class TestTabNavigation:
    """Test tab widget navigation."""

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

    def test_tab_programmatic_navigation(self, settings_dialog):
        """Test programmatic tab switching."""
        tab_widget = settings_dialog.tab_widget

        # Switch to each tab programmatically
        tab_widget.setCurrentIndex(1)
        assert tab_widget.currentIndex() == 1
        assert tab_widget.currentWidget() == tab_widget.widget(1)

        tab_widget.setCurrentIndex(2)
        assert tab_widget.currentIndex() == 2
        assert tab_widget.currentWidget() == tab_widget.widget(2)

        tab_widget.setCurrentIndex(0)
        assert tab_widget.currentIndex() == 0
        assert tab_widget.currentWidget() == tab_widget.widget(0)

    def test_tab_visibility(self, settings_dialog):
        """Test that all tabs are visible and enabled."""
        tab_widget = settings_dialog.tab_widget
        tab_bar = tab_widget.tabBar()

        for i in range(tab_widget.count()):
            assert tab_bar.isTabEnabled(i)
            assert tab_bar.isTabVisible(i)


class TestCheckboxInteraction:
    """Test checkbox widget interactions."""

    def test_checkbox_interaction(self, settings_dialog, app):
        """Test that checkboxes can be toggled."""
        # Test audio checkbox - set to known state first
        settings_dialog.audio_checkbox.setChecked(False)
        assert not settings_dialog.audio_checkbox.isChecked()
        settings_dialog.audio_checkbox.click()  # Use click() method directly
        assert settings_dialog.audio_checkbox.isChecked()

        # Test FCX checkbox - set to known state first
        settings_dialog.fcx_checkbox.setChecked(True)
        assert settings_dialog.fcx_checkbox.isChecked()
        settings_dialog.fcx_checkbox.click()  # Use click() method directly
        assert not settings_dialog.fcx_checkbox.isChecked()

    def test_all_checkboxes_toggle(self, settings_dialog):
        """Test that all checkboxes can be toggled."""
        checkboxes = [
            settings_dialog.audio_checkbox,
            settings_dialog.vr_checkbox,
            settings_dialog.fcx_checkbox,
            settings_dialog.simplify_checkbox,
            settings_dialog.show_fid_checkbox,
            settings_dialog.move_invalid_checkbox,
            settings_dialog.update_check_checkbox,
        ]

        for checkbox in checkboxes:
            # Set to unchecked
            checkbox.setChecked(False)
            assert not checkbox.isChecked()

            # Toggle to checked
            checkbox.click()
            assert checkbox.isChecked()

            # Toggle back to unchecked
            checkbox.click()
            assert not checkbox.isChecked()

    def test_checkbox_triple_state(self, settings_dialog):
        """Test that checkboxes are not tri-state."""
        # Ensure checkboxes are not tri-state (only True/False)
        checkboxes = [
            settings_dialog.audio_checkbox,
            settings_dialog.vr_checkbox,
            settings_dialog.fcx_checkbox,
        ]

        for checkbox in checkboxes:
            assert not checkbox.isTristate()
            assert checkbox.checkState() in [Qt.CheckState.Checked, Qt.CheckState.Unchecked]


class TestComboBoxInteraction:
    """Test combo box interactions."""

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

    def test_combobox_selection_by_text(self, settings_dialog):
        """Test combo box selection by text."""
        combo = settings_dialog.update_source_combo

        # Select by text
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
        original_index = combo.currentIndex()

        # Try to set invalid text
        combo.setCurrentText("InvalidOption")

        # Should remain at original selection or go to default
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

    def test_check_now_button_click(self, settings_dialog, app):
        """Test that Check Now button can be clicked."""
        from unittest.mock import patch

        button = settings_dialog.check_now_button

        # Mock the check_for_updates method
        with patch.object(settings_dialog, 'check_for_updates') as mock_check:
            # Click the button
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)

            # Verify the method was called
            mock_check.assert_called_once()

    def test_button_states(self, settings_dialog):
        """Test button enable/disable states."""
        button = settings_dialog.check_now_button

        # Initially should be enabled
        assert button.isEnabled()

        # Test disabling and enabling
        button.setEnabled(False)
        assert not button.isEnabled()

        button.setEnabled(True)
        assert button.isEnabled()


class TestWidgetFocus:
    """Test widget focus behavior."""

    def test_focus_traversal(self, settings_dialog, app):
        """Test that widgets can receive focus."""
        # Show dialog to enable focus
        settings_dialog.show()

        # Test that widgets can receive focus
        settings_dialog.audio_checkbox.setFocus()
        assert settings_dialog.audio_checkbox.hasFocus()

        settings_dialog.update_source_combo.setFocus()
        assert settings_dialog.update_source_combo.hasFocus()

        settings_dialog.check_now_button.setFocus()
        assert settings_dialog.check_now_button.hasFocus()

    def test_tab_order(self, settings_dialog, app):
        """Test that tab order is logical."""
        # Show dialog
        settings_dialog.show()

        # Set focus to first widget
        settings_dialog.audio_checkbox.setFocus()

        # Tab through several widgets
        for _ in range(3):
            QTest.keyClick(settings_dialog, Qt.Key.Key_Tab)

        # Should have moved focus (exact widget depends on tab order)
        assert not settings_dialog.audio_checkbox.hasFocus()


if __name__ == "__main__":
    pytest.main([__file__])
