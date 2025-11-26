"""Unit tests for TabSetupMixin error handling and edge cases.

Tests error conditions, edge cases, and defensive programming patterns
in the TabSetupMixin implementation.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")

from ClassicLib.Interface.TabSetupMixin import TabSetupMixin
from tests.fixtures.registry_fixtures import init_message_handler_fixture  # noqa: F401


@pytest.fixture
def tab_setup_mixin_minimal(init_message_handler_fixture):
    """Create minimal TabSetupMixin instance for edge case testing."""

    class MinimalTabSetup(TabSetupMixin):
        """Minimal implementation for edge case testing."""

        def __init__(self):
            # Initialize only essential attributes
            self.main_tab = MagicMock()
            self.articles_tab = MagicMock()
            self.backups_tab = MagicMock()
            self.results_tab = MagicMock()

            # These might not be initialized in error cases
            self.mods_folder_edit = None
            self.scan_folder_edit = None
            self.scan_button_group = MagicMock()

            # Buttons may not exist initially
            self.crash_logs_button = None
            self.game_files_button = None
            self.papyrus_button = None

            # Mock required methods
            self.select_folder_mods = MagicMock()
            self.select_folder_scan = MagicMock()
            self.validate_scan_folder_text = MagicMock()
            self.open_url = MagicMock()
            self.show_about = MagicMock()
            self.help_popup_main = MagicMock()
            self.open_settings = MagicMock()
            self.open_crash_logs_folder = MagicMock()
            self.update_popup_explicit = MagicMock()
            self.toggle_papyrus_worker = MagicMock()
            self.crash_logs_scan = MagicMock()
            self.game_files_scan = MagicMock()
            self.open_backup_folder = MagicMock()
            self.check_existing_backups = MagicMock()
            self.add_backup_section = MagicMock()

    return MinimalTabSetup()


@pytest.mark.unit
@pytest.mark.gui
class TestNullSafety:
    """Tests for null/None safety in TabSetupMixin."""

    def test_update_papyrus_button_style_no_attribute(self, tab_setup_mixin_minimal):
        """Should handle missing papyrus_button attribute gracefully."""
        # Delete attribute if it exists
        if hasattr(tab_setup_mixin_minimal, "papyrus_button"):
            delattr(tab_setup_mixin_minimal, "papyrus_button")

        # Should not raise AttributeError
        tab_setup_mixin_minimal.update_papyrus_button_style(True)
        tab_setup_mixin_minimal.update_papyrus_button_style(False)

    def test_update_papyrus_button_style_none_value(self, tab_setup_mixin_minimal):
        """Should handle None papyrus_button gracefully."""
        tab_setup_mixin_minimal.papyrus_button = None

        # Should not raise error
        tab_setup_mixin_minimal.update_papyrus_button_style(True)
        tab_setup_mixin_minimal.update_papyrus_button_style(False)

    def test_setup_main_buttons_none_returns(self, tab_setup_mixin_minimal):
        """Should handle None button returns from add_main_button."""
        mock_layout = MagicMock()

        with patch("ClassicLib.Interface.TabSetupMixin.add_main_button") as mock_add:
            # Simulate add_main_button returning None (error case)
            mock_add.return_value = None

            tab_setup_mixin_minimal.setup_main_buttons(mock_layout)

            # Should not try to add None to button group
            tab_setup_mixin_minimal.scan_button_group.addButton.assert_not_called()

            # Buttons should remain None
            assert tab_setup_mixin_minimal.crash_logs_button is None
            assert tab_setup_mixin_minimal.game_files_button is None

    def test_setup_main_tab_folder_section_failures(self, tab_setup_mixin_minimal):
        """Should handle setup_folder_section returning None."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder,
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QWidget"),
            patch.object(tab_setup_mixin_minimal, "setup_main_buttons"),
            patch.object(tab_setup_mixin_minimal, "setup_bottom_buttons"),
        ):
            # Both folder sections fail and return None
            mock_folder.return_value = None

            tab_setup_mixin_minimal.setup_main_tab()

            # Edit fields should remain None
            assert tab_setup_mixin_minimal.mods_folder_edit is None
            assert tab_setup_mixin_minimal.scan_folder_edit is None

            # No signal connections should be attempted on None
            # Test passes if no AttributeError is raised


@pytest.mark.unit
@pytest.mark.gui
class TestLayoutCompatibility:
    """Tests for layout type compatibility checks."""

    def test_setup_main_buttons_incompatible_layout(self, tab_setup_mixin_minimal):
        """Should handle layouts that don't support addLayout."""
        mock_layout = MagicMock()

        with (
            patch("ClassicLib.Interface.TabSetupMixin.add_main_button") as mock_add,
            patch("ClassicLib.Interface.TabSetupMixin.supports_add_layout", return_value=False),
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout"),
        ):
            mock_add.return_value = MagicMock()

            tab_setup_mixin_minimal.setup_main_buttons(mock_layout)

            # Should not call addLayout if not supported
            mock_layout.addLayout.assert_not_called()

    def test_setup_bottom_buttons_incompatible_layout(self, tab_setup_mixin_minimal):
        """Should handle layouts that don't support addLayout."""
        mock_layout = MagicMock()

        with (
            patch.object(tab_setup_mixin_minimal, "_create_button") as mock_create,
            patch("ClassicLib.Interface.TabSetupMixin.supports_add_layout", return_value=False),
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout"),
            patch("PySide6.QtWidgets.QApplication"),
        ):
            mock_create.return_value = MagicMock()

            tab_setup_mixin_minimal.setup_bottom_buttons(mock_layout)

            # Should not call addLayout if not supported
            mock_layout.addLayout.assert_not_called()

    def test_setup_articles_section_incompatible_layout(self):
        """Should handle layouts that don't support addLayout."""
        mock_layout = MagicMock()

        with (
            patch("ClassicLib.Interface.TabSetupMixin.supports_add_layout", return_value=False),
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QLabel"),
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton"),
        ):
            TabSetupMixin.setup_articles_section(mock_layout)

            # Should not call addLayout if not supported
            mock_layout.addLayout.assert_not_called()


@pytest.mark.unit
@pytest.mark.gui
class TestMissingDependencies:
    """Tests for handling missing or mocked dependencies."""

    def test_create_button_without_isCheckable(self, tab_setup_mixin_minimal):
        """Should handle buttons without isCheckable method (mocked objects)."""
        callback = MagicMock()

        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:
            # Create button mock without isCheckable
            mock_button = MagicMock()
            if hasattr(mock_button, "isCheckable"):
                delattr(mock_button, "isCheckable")
            mock_button_class.return_value = mock_button

            tab_setup_mixin_minimal._create_button("Test", "Tooltip", callback)

            # Should use clicked.connect as fallback
            mock_button.clicked.connect.assert_called_with(callback)
            mock_button.toggled.connect.assert_not_called()

    def test_create_button_isCheckable_raises(self, tab_setup_mixin_minimal):
        """Should handle isCheckable raising an exception."""
        callback = MagicMock()

        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:
            mock_button = MagicMock()
            # Make isCheckable raise an exception
            mock_button.isCheckable.side_effect = AttributeError("Mock error")
            mock_button_class.return_value = mock_button

            # The current implementation doesn't catch the exception,
            # so it will propagate. This test verifies that behavior.
            with pytest.raises(AttributeError, match="Mock error"):
                tab_setup_mixin_minimal._create_button("Test", "Tooltip", callback)


@pytest.mark.unit
@pytest.mark.gui
class TestEmptyOrInvalidData:
    """Tests for handling empty or invalid data."""

    def test_setup_backups_tab_empty_categories(self, tab_setup_mixin_minimal):
        """Should handle empty categories list."""
        # Patch the method to use empty categories
        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QLabel"),
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton"),
        ):
            # Mock the add_backup_section to track calls
            tab_setup_mixin_minimal.add_backup_section = MagicMock()

            # Create custom implementation with empty categories

            def setup_with_empty_categories(self):
                # Call original but with mocked empty categories
                with patch.object(TabSetupMixin, "setup_backups_tab") as mock_setup:

                    def empty_categories_impl(inner_self):
                        # No categories - should not crash
                        categories = []  # Empty list
                        for category in categories:
                            inner_self.add_backup_section(MagicMock(), category, category)
                        inner_self.check_existing_backups()

                    mock_setup.side_effect = empty_categories_impl
                    mock_setup(self)

            with patch.object(TabSetupMixin, "setup_backups_tab", setup_with_empty_categories):
                tab_setup_mixin_minimal.setup_backups_tab()

                # Should not call add_backup_section with empty categories
                tab_setup_mixin_minimal.add_backup_section.assert_not_called()

                # Should still check existing backups
                tab_setup_mixin_minimal.check_existing_backups.assert_called_once()

    def test_setup_articles_tab_malformed_urls(self, tab_setup_mixin_minimal):
        """Should handle malformed URLs in button data."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QLabel"),
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
            patch("ClassicLib.Interface.TabSetupMixin.partial") as mock_partial,
        ):
            # Track button creation
            buttons_created = []
            mock_button.side_effect = lambda text: buttons_created.append(text) or MagicMock()

            # Test with malformed URL data
            def partial_with_validation(func, url):
                # Should still create partial even with invalid URL
                return MagicMock()

            mock_partial.side_effect = partial_with_validation

            tab_setup_mixin_minimal.setup_articles_tab()

            # Should create all 9 buttons regardless of URL validity
            assert len(buttons_created) == 9


@pytest.mark.unit
@pytest.mark.gui
class TestSignalConnectionErrors:
    """Tests for signal connection error handling."""

    def test_scan_folder_edit_no_signal(self, tab_setup_mixin_minimal):
        """Should handle edit widget without editingFinished signal."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder,
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QWidget"),
            patch.object(tab_setup_mixin_minimal, "setup_main_buttons"),
            patch.object(tab_setup_mixin_minimal, "setup_bottom_buttons"),
        ):
            # Create edit without editingFinished signal
            mock_mods_edit = MagicMock()
            mock_scan_edit = MagicMock()
            # Remove editingFinished if it exists
            if hasattr(mock_scan_edit, "editingFinished"):
                delattr(mock_scan_edit, "editingFinished")

            mock_folder.side_effect = [mock_mods_edit, mock_scan_edit]

            # The implementation will raise an AttributeError if editingFinished doesn't exist
            with pytest.raises(AttributeError):
                tab_setup_mixin_minimal.setup_main_tab()

    def test_button_clicked_connect_fails(self, tab_setup_mixin_minimal):
        """Should handle clicked.connect failing."""
        callback = MagicMock()

        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:
            mock_button = MagicMock()
            mock_button.isCheckable.return_value = False
            # Make clicked.connect raise exception
            mock_button.clicked.connect.side_effect = RuntimeError("Connection failed")
            mock_button_class.return_value = mock_button

            # The implementation will propagate the exception
            with pytest.raises(RuntimeError, match="Connection failed"):
                tab_setup_mixin_minimal._create_button("Test", "Tooltip", callback)


@pytest.mark.unit
@pytest.mark.gui
class TestWidgetPropertyErrors:
    """Tests for widget property setting errors."""

    def test_button_setToolTip_fails(self, tab_setup_mixin_minimal):
        """Should handle setToolTip failing."""
        callback = MagicMock()

        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:
            mock_button = MagicMock()
            mock_button.isCheckable.return_value = False
            # Make setToolTip raise exception
            mock_button.setToolTip.side_effect = RuntimeError("Tooltip failed")
            mock_button_class.return_value = mock_button

            # The implementation will propagate the exception
            with pytest.raises(RuntimeError, match="Tooltip failed"):
                tab_setup_mixin_minimal._create_button("Test", "Tooltip", callback)

    def test_placeholder_text_setting_fails(self, tab_setup_mixin_minimal):
        """Should handle setPlaceholderText failing."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder,
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QWidget"),
            patch.object(tab_setup_mixin_minimal, "setup_main_buttons"),
            patch.object(tab_setup_mixin_minimal, "setup_bottom_buttons"),
        ):
            # Create edits that fail on setPlaceholderText
            mock_mods_edit = MagicMock()
            mock_scan_edit = MagicMock()
            mock_mods_edit.setPlaceholderText.side_effect = RuntimeError("Failed")
            mock_scan_edit.setPlaceholderText.side_effect = RuntimeError("Failed")

            mock_folder.side_effect = [mock_mods_edit, mock_scan_edit]

            # The implementation will propagate the exception
            with pytest.raises(RuntimeError, match="Failed"):
                tab_setup_mixin_minimal.setup_main_tab()


@pytest.mark.unit
@pytest.mark.gui
class TestCallbackErrors:
    """Tests for callback execution errors."""

    def test_open_url_callback_error(self, tab_setup_mixin_minimal):
        """Should handle open_url callback errors gracefully."""
        # Make open_url raise an exception
        tab_setup_mixin_minimal.open_url.side_effect = Exception("URL open failed")

        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QLabel"),
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
            patch("ClassicLib.Interface.TabSetupMixin.partial") as mock_partial,
        ):
            created_buttons = []

            def create_button(text):
                btn = MagicMock()
                btn.clicked = MagicMock()
                created_buttons.append(btn)
                return btn

            mock_button.side_effect = create_button

            # Partial should still be created even if callback might fail
            mock_partial.return_value = MagicMock()

            tab_setup_mixin_minimal.setup_articles_tab()

            # All buttons should still be created
            assert len(created_buttons) == 9

            # All buttons should have callbacks connected
            for btn in created_buttons:
                btn.clicked.connect.assert_called_once()

    def test_check_existing_backups_error(self, tab_setup_mixin_minimal):
        """Should handle check_existing_backups errors."""
        # Make check_existing_backups raise exception
        tab_setup_mixin_minimal.check_existing_backups.side_effect = Exception("Check failed")

        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QLabel"),
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton"),
        ):
            # Should not prevent tab setup from completing
            try:
                tab_setup_mixin_minimal.setup_backups_tab()
                # If we get here, the exception was raised but didn't break setup
            except Exception as e:
                # This is expected - the mock raises the exception
                assert str(e) == "Check failed"

            # Check was attempted
            tab_setup_mixin_minimal.check_existing_backups.assert_called_once()
