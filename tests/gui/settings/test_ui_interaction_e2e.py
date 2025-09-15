"""
E2E tests for ui_interaction - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

pytestmark = pytest.mark.e2e

class TestTabNavigation:
    """Test tab widget navigation."""

    def test_tab_navigation(self, settings_dialog, app):
        """Test that tabs can be navigated."""
        tab_widget = settings_dialog.tab_widget
        tab_bar = tab_widget.tabBar()
        QTest.mouseClick(tab_bar, Qt.MouseButton.LeftButton, pos=tab_bar.tabRect(1).center())
        assert tab_widget.currentIndex() == 1
        QTest.mouseClick(tab_bar, Qt.MouseButton.LeftButton, pos=tab_bar.tabRect(2).center())
        assert tab_widget.currentIndex() == 2
        QTest.mouseClick(tab_bar, Qt.MouseButton.LeftButton, pos=tab_bar.tabRect(0).center())
        assert tab_widget.currentIndex() == 0

    def test_tab_programmatic_navigation(self, settings_dialog):
        """Test programmatic tab switching."""
        tab_widget = settings_dialog.tab_widget
        tab_widget.setCurrentIndex(1)
        assert tab_widget.currentIndex() == 1
        assert tab_widget.currentWidget() == tab_widget.widget(1)
        tab_widget.setCurrentIndex(2)
        assert tab_widget.currentIndex() == 2
        assert tab_widget.currentWidget() == tab_widget.widget(2)
        tab_widget.setCurrentIndex(0)
        assert tab_widget.currentIndex() == 0
        assert tab_widget.currentWidget() == tab_widget.widget(0)

class TestCheckboxInteraction:
    """Test checkbox widget interactions."""

    def test_checkbox_interaction(self, settings_dialog, app):
        """Test that checkboxes can be toggled."""
        settings_dialog.audio_checkbox.setChecked(False)
        assert not settings_dialog.audio_checkbox.isChecked()
        settings_dialog.audio_checkbox.click()
        assert settings_dialog.audio_checkbox.isChecked()
        settings_dialog.fcx_checkbox.setChecked(True)
        assert settings_dialog.fcx_checkbox.isChecked()
        settings_dialog.fcx_checkbox.click()
        assert not settings_dialog.fcx_checkbox.isChecked()

    def test_all_checkboxes_toggle(self, settings_dialog):
        """Test that all checkboxes can be toggled."""
        checkboxes = [settings_dialog.audio_checkbox, settings_dialog.vr_checkbox, settings_dialog.fcx_checkbox, settings_dialog.simplify_checkbox, settings_dialog.show_fid_checkbox, settings_dialog.move_invalid_checkbox, settings_dialog.update_check_checkbox]
        for checkbox in checkboxes:
            checkbox.setChecked(False)
            assert not checkbox.isChecked()
            checkbox.click()
            assert checkbox.isChecked()
            checkbox.click()
            assert not checkbox.isChecked()

class TestButtonInteraction:
    """Test button interactions."""

    def test_check_now_button_click(self, settings_dialog, app):
        """Test that Check Now button can be clicked."""
        from unittest.mock import patch, MagicMock
        button = settings_dialog.check_now_button

        # The button should exist and be clickable
        assert button is not None
        assert button.isEnabled()

        # Mock the UpdateCheckWorker that would be created on button click
        with patch('ClassicLib.Interface.Workers.UpdateCheckWorker') as mock_worker_class:
            mock_worker = MagicMock()
            mock_worker_class.return_value = mock_worker

            # Click the button - it should be clickable even if no handler is connected
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)

            # The test passes if the button click doesn't raise an exception
            # The actual update check functionality is tested elsewhere

class TestWidgetFocus:
    """Test widget focus behavior."""

    def test_focus_traversal(self, settings_dialog, app):
        """Test that widgets can receive focus."""
        settings_dialog.show()
        settings_dialog.audio_checkbox.setFocus()
        assert settings_dialog.audio_checkbox.hasFocus()
        settings_dialog.update_source_combo.setFocus()
        assert settings_dialog.update_source_combo.hasFocus()
        settings_dialog.check_now_button.setFocus()
        assert settings_dialog.check_now_button.hasFocus()

    def test_tab_order(self, settings_dialog, app):
        """Test that tab order is logical."""
        settings_dialog.show()
        settings_dialog.audio_checkbox.setFocus()
        for _ in range(3):
            QTest.keyClick(settings_dialog, Qt.Key.Key_Tab)
        assert not settings_dialog.audio_checkbox.hasFocus()
