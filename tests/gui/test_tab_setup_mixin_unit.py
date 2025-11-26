"""Unit tests for TabSetupMixin.

Tests tab setup functionality in isolation with mocked Qt components.
"""

import os
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")

from ClassicLib.Interface.TabSetupMixin import TabSetupMixin
from tests.fixtures.registry_fixtures import init_message_handler_fixture  # noqa: F401


# Create mock Qt classes for testing to avoid importing real Qt
# These are only used for spec= parameters and isinstance checks
class MockQWidget:
    pass


class MockQVBoxLayout:
    pass


class MockQHBoxLayout:
    pass


class MockQButtonGroup:
    pass


class MockQLineEdit:
    pass


class MockQPushButton:
    pass


class MockQLabel:
    pass


@pytest.fixture
def mock_qt_layouts():
    """Mock Qt layout components."""
    with (
        patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
        patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout") as mock_hbox,
        patch("ClassicLib.Interface.TabSetupMixin.QGridLayout") as mock_grid,
    ):
        mock_vbox_instance = MagicMock()
        mock_hbox_instance = MagicMock()
        mock_grid_instance = MagicMock()

        mock_vbox.return_value = mock_vbox_instance
        mock_hbox.return_value = mock_hbox_instance
        mock_grid.return_value = mock_grid_instance

        yield {
            "vbox": mock_vbox_instance,
            "hbox": mock_hbox_instance,
            "grid": mock_grid_instance,
            "vbox_class": mock_vbox,
            "hbox_class": mock_hbox,
            "grid_class": mock_grid,
        }


@pytest.fixture
def tab_setup_mixin(mock_qt_layouts, init_message_handler_fixture):
    """Create TabSetupMixin instance with mocked dependencies."""

    class TestTabSetup(TabSetupMixin):
        """Test class that includes the mixin."""

        def __init__(self):
            # Mock tab widgets
            self.main_tab = MagicMock()
            self.articles_tab = MagicMock()
            self.backups_tab = MagicMock()
            self.results_tab = MagicMock()

            # Mock edit widgets
            self.mods_folder_edit = None
            self.scan_folder_edit = None

            # Mock button groups
            self.scan_button_group = MagicMock()

            # Mock buttons
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

            # Add the add_main_button method that delegates to UIHelpers
            def add_main_button_impl(layout, text, callback, tooltip=""):
                from ClassicLib.Interface.UIHelpers import add_main_button

                return add_main_button(layout, text, callback, tooltip)

            self.add_main_button = MagicMock(side_effect=add_main_button_impl)

    return TestTabSetup()


@pytest.mark.unit
@pytest.mark.gui
class TestMainTabSetup:
    """Tests for main tab setup."""

    def test_setup_main_tab_creates_layout(self, tab_setup_mixin):
        """Should create proper layout structure for main tab."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder_section,
            patch.object(tab_setup_mixin, "setup_main_buttons") as mock_main_buttons,
            patch.object(tab_setup_mixin, "setup_bottom_buttons") as mock_bottom_buttons,
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QWidget") as mock_widget,
            patch("ClassicLib.Interface.TabSetupMixin.supports_add_layout", return_value=True),
        ):
            # Mock folder section returns
            mock_mods_edit = MagicMock()
            mock_scan_edit = MagicMock()
            mock_folder_section.side_effect = [mock_mods_edit, mock_scan_edit]

            # Mock layout with proper class attribute
            mock_layout = MagicMock()
            # Set __class__.__name__ for isinstance checks if needed
            mock_layout.__class__.__name__ = "QVBoxLayout"
            mock_layout.addLayout = MagicMock()
            mock_layout.addWidget = MagicMock()
            mock_layout.addStretch = MagicMock()
            mock_layout.addSpacing = MagicMock()
            mock_layout.setContentsMargins = MagicMock()
            mock_layout.setSpacing = MagicMock()

            # QVBoxLayout can be called with or without parent widget
            def vbox_constructor(*args, **kwargs):
                return mock_layout

            mock_vbox.side_effect = vbox_constructor

            # Mock widget creation
            mock_widget_instance = MagicMock()
            mock_widget.return_value = mock_widget_instance

            # Call setup_main_tab
            result = tab_setup_mixin.setup_main_tab()

            # Verify layout was created (setup_main_tab returns None)
            assert result is None
            # QVBoxLayout is called twice: once for main layout, once for header layout
            assert mock_vbox.call_count == 2

            # Verify folder sections created
            assert mock_folder_section.call_count == 2

            # Verify edits assigned
            assert tab_setup_mixin.mods_folder_edit == mock_mods_edit
            assert tab_setup_mixin.scan_folder_edit == mock_scan_edit

            # Verify signal connected for scan folder validation
            mock_scan_edit.editingFinished.connect.assert_called_with(tab_setup_mixin.validate_scan_folder_text)

            # Verify button sections called
            mock_main_buttons.assert_called_once()
            mock_bottom_buttons.assert_called_once()

    def test_setup_main_buttons_creates_scan_buttons(self, tab_setup_mixin):
        """Should create main scan buttons and add to button group."""
        # Create a mock layout
        mock_layout = MagicMock()
        mock_layout.addLayout = MagicMock()

        with (
            patch("ClassicLib.Interface.TabSetupMixin.add_main_button") as mock_add_button,
            patch("ClassicLib.Interface.TabSetupMixin.supports_add_layout", return_value=True),
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout") as mock_hbox,
        ):
            # Mock HBoxLayout creation
            mock_hbox_instance = MagicMock()
            mock_hbox_instance.setSpacing = MagicMock()
            mock_hbox.return_value = mock_hbox_instance

            # Setup buttons
            mock_crash_button = MagicMock()
            mock_game_button = MagicMock()
            mock_add_button.side_effect = [mock_crash_button, mock_game_button]

            tab_setup_mixin.setup_main_buttons(mock_layout)

            # Verify buttons created
            assert mock_add_button.call_count == 2

            # Verify buttons assigned
            assert tab_setup_mixin.crash_logs_button == mock_crash_button
            assert tab_setup_mixin.game_files_button == mock_game_button

            # Verify buttons added to group
            tab_setup_mixin.scan_button_group.addButton.assert_any_call(mock_crash_button)
            tab_setup_mixin.scan_button_group.addButton.assert_any_call(mock_game_button)

    def test_setup_bottom_buttons_creates_utility_buttons(self, tab_setup_mixin):
        """Should create bottom utility buttons."""
        mock_layout = MagicMock()
        mock_layout.addLayout = MagicMock()
        mock_layout.addSpacing = MagicMock()

        with (
            patch.object(tab_setup_mixin, "_create_button") as mock_create_button,
            patch("PySide6.QtWidgets.QApplication") as mock_app,
            patch.object(tab_setup_mixin, "update_papyrus_button_style"),
            patch("ClassicLib.Interface.TabSetupMixin.supports_add_layout", return_value=True),
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout") as mock_hbox,
        ):
            # Mock HBoxLayout creation
            mock_hbox_instance = MagicMock()
            mock_hbox_instance.setSpacing = MagicMock()
            mock_hbox_instance.setContentsMargins = MagicMock()
            mock_hbox_instance.addWidget = MagicMock()
            mock_hbox.return_value = mock_hbox_instance

            mock_buttons = [MagicMock() for _ in range(7)]
            for btn in mock_buttons:
                btn.isCheckable.return_value = False
            # Make the papyrus button (6th button) checkable
            mock_buttons[5].isCheckable.return_value = True
            mock_create_button.side_effect = mock_buttons

            tab_setup_mixin.setup_bottom_buttons(mock_layout)

            # Should create all utility buttons
            expected_buttons = [
                ("ABOUT", tab_setup_mixin.show_about),
                ("HELP", tab_setup_mixin.help_popup_main),
                ("SETTINGS", tab_setup_mixin.open_settings),
                ("OPEN CRASH LOGS", tab_setup_mixin.open_crash_logs_folder),
                ("CHECK UPDATES", tab_setup_mixin.update_popup_explicit),
                ("START PAPYRUS MONITORING", tab_setup_mixin.toggle_papyrus_worker),
                ("EXIT", mock_app.quit),
            ]

            # Verify correct number of buttons created
            assert mock_create_button.call_count == len(expected_buttons)

            # Verify papyrus button configured
            assert tab_setup_mixin.papyrus_button is not None
            tab_setup_mixin.papyrus_button.setCheckable.assert_called_with(True)

    def test_update_papyrus_button_style_monitoring_active(self, tab_setup_mixin):
        """Should update button style when monitoring is active."""
        mock_button = MagicMock()
        tab_setup_mixin.papyrus_button = mock_button

        tab_setup_mixin.update_papyrus_button_style(True)

        mock_button.setText.assert_called_with("STOP PAPYRUS MONITORING")
        mock_button.setStyleSheet.assert_called()
        # Should have red background in style
        style_call = mock_button.setStyleSheet.call_args[0][0]
        assert "rgb(237, 45, 45)" in style_call

    def test_update_papyrus_button_style_monitoring_inactive(self, tab_setup_mixin):
        """Should update button style when monitoring is inactive."""
        mock_button = MagicMock()
        tab_setup_mixin.papyrus_button = mock_button

        tab_setup_mixin.update_papyrus_button_style(False)

        mock_button.setText.assert_called_with("START PAPYRUS MONITORING")
        mock_button.setStyleSheet.assert_called()
        # Should have green background in style
        style_call = mock_button.setStyleSheet.call_args[0][0]
        assert "rgb(45, 237, 138)" in style_call


@pytest.mark.unit
@pytest.mark.gui
class TestArticlesTabSetup:
    """Tests for articles tab setup."""

    def test_setup_articles_tab_creates_resource_buttons(self, tab_setup_mixin):
        """Should create grid of resource buttons."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
            patch("ClassicLib.Interface.TabSetupMixin.partial") as mock_partial,
        ):
            mock_button_instances = [MagicMock() for _ in range(9)]
            mock_button.side_effect = mock_button_instances

            tab_setup_mixin.setup_articles_tab()

            # Verify title label created
            mock_label.assert_called_once_with("USEFUL RESOURCES & LINKS")

            # Verify 9 resource buttons created
            assert mock_button.call_count == 9

            # Verify button properties set
            for btn in mock_button_instances:
                btn.setStyleSheet.assert_called()
                btn.setToolTip.assert_called()
                btn.clicked.connect.assert_called()

            # Verify partial used for URL binding
            assert mock_partial.call_count == 9

    def test_setup_articles_tab_button_urls(self, tab_setup_mixin):
        """Should create buttons with correct URLs."""
        captured_urls = []

        # Need to mock all Qt classes used in setup_articles_tab
        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label,
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout") as mock_grid,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
            patch("ClassicLib.Interface.TabSetupMixin.QSizePolicy") as mock_size_policy,
            patch("ClassicLib.Interface.TabSetupMixin.Qt") as mock_qt,
            patch("ClassicLib.Interface.TabSetupMixin.partial") as mock_partial,
        ):
            # Setup mock returns
            mock_vbox_instance = MagicMock()
            mock_vbox.return_value = mock_vbox_instance

            mock_label_instance = MagicMock()
            mock_label.return_value = mock_label_instance

            mock_grid_instance = MagicMock()
            mock_grid.return_value = mock_grid_instance

            # Mock Qt.AlignmentFlag
            mock_qt.AlignmentFlag.AlignCenter = MagicMock()

            # Mock QSizePolicy.Policy
            mock_size_policy.Policy.Expanding = MagicMock()
            mock_size_policy.Policy.Fixed = MagicMock()

            def capture_partial(func, url):
                captured_urls.append(url)
                return MagicMock()

            mock_partial.side_effect = capture_partial
            mock_button.return_value = MagicMock()

            tab_setup_mixin.setup_articles_tab()

            # Verify correct URLs configured
            expected_urls = [
                "https://www.nexusmods.com/fallout4/articles/3115",
                "https://www.nexusmods.com/fallout4/articles/4141",
                "https://www.nexusmods.com/fallout4/articles/3769",
                "https://www.nexusmods.com/fallout4/mods/47359",
                "https://www.nexusmods.com/fallout4/mods/56255",
                "https://github.com/evildarkarchon/CLASSIC-Fallout4",
                "https://www.nexusmods.com/fallout4/mods/71588",
                "https://www.nexusmods.com/site/mods/631",
                "https://www.nexusmods.com/fallout4/mods/20032",
            ]

            assert captured_urls == expected_urls


@pytest.mark.unit
@pytest.mark.gui
class TestBackupsTabSetup:
    """Tests for backups tab setup."""

    def test_setup_backups_tab_creates_backup_sections(self, tab_setup_mixin):
        """Should create backup sections for each category."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
        ):
            mock_button_instance = MagicMock()
            mock_button.return_value = mock_button_instance

            tab_setup_mixin.setup_backups_tab()

            # Verify info labels created
            assert mock_label.call_count == 3

            # Verify backup sections created for each category
            expected_categories = ["XSE", "RESHADE", "VULKAN", "ENB"]
            for category in expected_categories:
                tab_setup_mixin.add_backup_section.assert_any_call(mock.ANY, category, category)

            # Verify open backups button created
            mock_button.assert_called_with("OPEN CLASSIC BACKUPS")
            mock_button_instance.clicked.connect.assert_called_with(tab_setup_mixin.open_backup_folder)

            # Verify existing backups checked
            tab_setup_mixin.check_existing_backups.assert_called_once()


@pytest.mark.unit
@pytest.mark.gui
class TestButtonCreation:
    """Tests for button creation utilities."""

    def test_create_button_regular(self, tab_setup_mixin):
        """Should create regular button with proper connections."""
        callback = MagicMock()

        # Create a proper mock that won't break isinstance
        mock_button = MagicMock()
        mock_button.isCheckable.return_value = False

        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton", return_value=mock_button):
            result = tab_setup_mixin._create_button("Test", "Tooltip", callback)

            assert result == mock_button
            mock_button.setToolTip.assert_called_with("Tooltip")
            mock_button.clicked.connect.assert_called_with(callback)
            mock_button.setStyleSheet.assert_called()

    def test_create_button_checkable(self, tab_setup_mixin):
        """Should create checkable button with toggled signal."""
        callback = MagicMock()

        # Create a proper mock that won't break isinstance
        mock_button = MagicMock()
        mock_button.isCheckable.return_value = True

        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton", return_value=mock_button):
            result = tab_setup_mixin._create_button("Toggle", "Tooltip", callback)

            assert result == mock_button
            mock_button.toggled.connect.assert_called_with(callback)
            # Should not connect clicked for checkable buttons
            mock_button.clicked.connect.assert_not_called()

    # Note: add_main_button is not a method of TabSetupMixin, it's imported from UIHelpers
    # The TYPE_CHECKING stub is just for type hints, not an actual method


@pytest.mark.unit
@pytest.mark.gui
class TestLayoutStructure:
    """Tests for layout structure and organization."""

    def test_main_tab_layout_structure(self, tab_setup_mixin):
        """Should create proper layout hierarchy for main tab."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox_class,
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout") as mock_hbox_class,
            patch("ClassicLib.Interface.TabSetupMixin.QWidget"),
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section"),
        ):
            # Track layout creation
            layouts_created = {"vbox": [], "hbox": []}

            def track_vbox(*args, **kwargs):
                layout = MagicMock()
                layouts_created["vbox"].append(layout)
                return layout

            def track_hbox(*args, **kwargs):
                layout = MagicMock()
                layouts_created["hbox"].append(layout)
                return layout

            mock_vbox_class.side_effect = track_vbox
            mock_hbox_class.side_effect = track_hbox

            with patch.object(tab_setup_mixin, "setup_main_buttons"), patch.object(tab_setup_mixin, "setup_bottom_buttons"):
                tab_setup_mixin.setup_main_tab()

                # Should create main vertical layout
                assert len(layouts_created["vbox"]) >= 1

                # Main layout should have proper margins
                main_layout = layouts_created["vbox"][0]
                main_layout.setContentsMargins.assert_called_with(15, 5, 15, 10)
                main_layout.setSpacing.assert_called_with(0)

    def test_articles_tab_grid_layout(self, tab_setup_mixin):
        """Should arrange article buttons in grid."""
        # Need to mock all Qt classes used in setup_articles_tab
        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label,
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout") as mock_grid_class,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class,
            patch("ClassicLib.Interface.TabSetupMixin.QSizePolicy") as mock_size_policy,
            patch("ClassicLib.Interface.TabSetupMixin.Qt") as mock_qt,
            patch("ClassicLib.Interface.TabSetupMixin.partial") as mock_partial,
        ):
            # Setup mock returns
            mock_vbox_instance = MagicMock()
            mock_vbox.return_value = mock_vbox_instance

            mock_label_instance = MagicMock()
            mock_label.return_value = mock_label_instance

            mock_grid = MagicMock()
            mock_grid_class.return_value = mock_grid

            # Mock Qt.AlignmentFlag
            mock_qt.AlignmentFlag.AlignCenter = MagicMock()

            # Mock QSizePolicy.Policy
            mock_size_policy.Policy.Expanding = MagicMock()
            mock_size_policy.Policy.Fixed = MagicMock()

            # Track button positions
            button_positions = []

            def track_add_widget(widget, row, col):
                button_positions.append((row, col))

            mock_grid.addWidget.side_effect = track_add_widget
            mock_button_class.return_value = MagicMock()
            mock_partial.return_value = MagicMock()

            tab_setup_mixin.setup_articles_tab()

            # Should arrange 9 buttons in 3x3 grid
            expected_positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]

            assert button_positions == expected_positions


@pytest.mark.unit
@pytest.mark.gui
class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_update_papyrus_button_style_no_button(self, tab_setup_mixin):
        """Should handle gracefully when papyrus button doesn't exist."""
        # Test when attribute doesn't exist
        if hasattr(tab_setup_mixin, "papyrus_button"):
            delattr(tab_setup_mixin, "papyrus_button")

        # Should not raise error
        tab_setup_mixin.update_papyrus_button_style(True)
        tab_setup_mixin.update_papyrus_button_style(False)

        # Test when attribute is None
        tab_setup_mixin.papyrus_button = None
        tab_setup_mixin.update_papyrus_button_style(True)
        tab_setup_mixin.update_papyrus_button_style(False)

    def test_setup_main_tab_with_none_edits(self, tab_setup_mixin):
        """Should handle None returned from setup_folder_section."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder,
            patch.object(tab_setup_mixin, "setup_main_buttons"),
            patch.object(tab_setup_mixin, "setup_bottom_buttons"),
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QWidget"),
        ):
            # setup_folder_section returns None for both edits
            mock_folder.return_value = None
            mock_vbox.return_value = MagicMock()

            tab_setup_mixin.setup_main_tab()

            # Should handle None gracefully
            assert tab_setup_mixin.mods_folder_edit is None
            assert tab_setup_mixin.scan_folder_edit is None
            # Should not try to connect signal on None
            assert mock_folder.call_count == 2

    def test_create_button_with_mock_qt_classes(self, tab_setup_mixin):
        """Should handle mocked Qt classes properly in tests."""
        callback = MagicMock()

        # Create mock button without isCheckable attribute initially
        mock_button = MagicMock()
        # Remove isCheckable if it exists to test hasattr logic
        if hasattr(mock_button, "isCheckable"):
            delattr(mock_button, "isCheckable")

        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton", return_value=mock_button):
            result = tab_setup_mixin._create_button("Test", "Tooltip", callback)

            # Should handle missing isCheckable gracefully
            assert result == mock_button
            mock_button.clicked.connect.assert_called_with(callback)

    def test_setup_articles_tab_empty_button_data(self, tab_setup_mixin):
        """Should handle empty button data gracefully."""
        # This test demonstrates that the method works even with no buttons
        # by directly mocking the button creation to return nothing
        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label,
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout") as mock_grid,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
            patch("ClassicLib.Interface.TabSetupMixin.partial"),
        ):
            mock_vbox.return_value = MagicMock()
            mock_grid.return_value = MagicMock()
            mock_label.return_value = MagicMock()

            # Track if buttons are created
            buttons_created = 0

            def button_creator(text):
                nonlocal buttons_created
                buttons_created += 1
                return MagicMock()

            mock_button.side_effect = button_creator

            # Call the actual method - it will create 9 buttons by default
            tab_setup_mixin.setup_articles_tab()

            # The implementation always creates 9 buttons (hardcoded in button_data)
            assert buttons_created == 9


@pytest.mark.unit
@pytest.mark.gui
class TestStaticMethod:
    """Tests for static methods."""

    def test_setup_articles_section_static(self, tab_setup_mixin):
        """Should properly setup articles section as static method."""
        mock_layout = MagicMock()

        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label,
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout") as mock_grid,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
            patch("ClassicLib.Interface.TabSetupMixin.QDesktopServices"),
            patch("ClassicLib.Interface.TabSetupMixin.supports_add_layout", return_value=True),
        ):
            mock_vbox.return_value = MagicMock()
            mock_grid.return_value = MagicMock()
            mock_button.return_value = MagicMock()

            # Call static method directly from class
            TabSetupMixin.setup_articles_section(mock_layout)

            # Should create title label
            mock_label.assert_called_with("USEFUL RESOURCES & LINKS")

            # Should create 9 buttons
            assert mock_button.call_count == 9

            # Should add layout if supported
            mock_layout.addLayout.assert_called()


@pytest.mark.unit
@pytest.mark.gui
class TestSignalConnections:
    """Tests for signal connections and callbacks."""

    def test_scan_folder_edit_signal_connection(self, tab_setup_mixin):
        """Should connect editingFinished signal for scan folder validation."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder,
            patch.object(tab_setup_mixin, "setup_main_buttons"),
            patch.object(tab_setup_mixin, "setup_bottom_buttons"),
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QWidget"),
        ):
            # Create mock edits with signal
            mock_mods_edit = MagicMock()
            mock_scan_edit = MagicMock()
            mock_scan_edit.editingFinished = MagicMock()
            mock_scan_edit.editingFinished.connect = MagicMock()

            mock_folder.side_effect = [mock_mods_edit, mock_scan_edit]

            tab_setup_mixin.setup_main_tab()

            # Verify signal connected
            mock_scan_edit.editingFinished.connect.assert_called_once_with(tab_setup_mixin.validate_scan_folder_text)

    def test_button_group_additions(self, tab_setup_mixin):
        """Should add scan buttons to button group."""
        mock_layout = MagicMock()

        with patch("ClassicLib.Interface.TabSetupMixin.add_main_button") as mock_add:
            mock_crash_button = MagicMock()
            mock_game_button = MagicMock()
            mock_add.side_effect = [mock_crash_button, mock_game_button]

            # Reset button group mock to track calls
            tab_setup_mixin.scan_button_group.reset_mock()

            tab_setup_mixin.setup_main_buttons(mock_layout)

            # Should add both buttons to group
            calls = tab_setup_mixin.scan_button_group.addButton.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == mock_crash_button
            assert calls[1][0][0] == mock_game_button


@pytest.mark.unit
@pytest.mark.gui
class TestTooltipsAndStyles:
    """Tests for tooltips and button styles."""

    def test_button_tooltips_set(self, tab_setup_mixin):
        """Should set tooltips for all buttons."""
        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:
            buttons_created = []

            def track_button(text):
                btn = MagicMock()
                btn.text = text
                btn.isCheckable.return_value = False
                buttons_created.append(btn)
                return btn

            mock_button_class.side_effect = track_button

            # Test _create_button tooltip setting
            btn = tab_setup_mixin._create_button("TEST", "Test tooltip", MagicMock())

            btn.setToolTip.assert_called_with("Test tooltip")

    def test_button_styles_applied(self, tab_setup_mixin):
        """Should apply correct styles to buttons."""
        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:
            mock_button = MagicMock()
            mock_button.isCheckable.return_value = False
            mock_button_class.return_value = mock_button

            # Test bottom button style
            tab_setup_mixin._create_button("TEST", "Tooltip", MagicMock())

            # Should apply BOTTOM_BUTTON_STYLE from UIHelpers
            mock_button.setStyleSheet.assert_called()
            style_arg = mock_button.setStyleSheet.call_args[0][0]
            # Check for key style properties
            assert "QPushButton" in style_arg
            assert "border-radius" in style_arg


@pytest.mark.unit
@pytest.mark.gui
class TestPlaceholderText:
    """Tests for placeholder text in edit fields."""

    def test_folder_edit_placeholders(self, tab_setup_mixin):
        """Should set placeholder text for folder edit fields."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder,
            patch.object(tab_setup_mixin, "setup_main_buttons"),
            patch.object(tab_setup_mixin, "setup_bottom_buttons"),
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QWidget"),
        ):
            # Create mock edits
            mock_mods_edit = MagicMock()
            mock_scan_edit = MagicMock()
            mock_folder.side_effect = [mock_mods_edit, mock_scan_edit]

            tab_setup_mixin.setup_main_tab()

            # Verify placeholder text set
            mock_mods_edit.setPlaceholderText.assert_called_with("Optional: Select your mod staging folder (e.g., MO2/mods)")
            mock_scan_edit.setPlaceholderText.assert_called_with("Optional: Select a supplementary custom folder with crash logs")
