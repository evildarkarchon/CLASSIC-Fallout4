"""Unit tests for TabSetupMixin.

Tests tab setup functionality in isolation with mocked Qt components.
"""

from functools import partial
from typing import Callable
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ClassicLib.Interface.TabSetupMixin import TabSetupMixin
from tests.fixtures.registry_fixtures import init_message_handler_fixture  # noqa: F401


@pytest.fixture
def mock_qt_layouts():
    """Mock Qt layout components."""
    with patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox, \
         patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout") as mock_hbox, \
         patch("ClassicLib.Interface.TabSetupMixin.QGridLayout") as mock_grid:

        mock_vbox_instance = MagicMock(spec=QVBoxLayout)
        mock_hbox_instance = MagicMock(spec=QHBoxLayout)
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
            "grid_class": mock_grid
        }


@pytest.fixture
def tab_setup_mixin(mock_qt_layouts, init_message_handler_fixture):
    """Create TabSetupMixin instance with mocked dependencies."""

    class TestTabSetup(TabSetupMixin):
        """Test class that includes the mixin."""

        def __init__(self):
            # Mock tab widgets
            self.main_tab = MagicMock(spec=QWidget)
            self.articles_tab = MagicMock(spec=QWidget)
            self.backups_tab = MagicMock(spec=QWidget)
            self.results_tab = MagicMock(spec=QWidget)

            # Mock edit widgets
            self.mods_folder_edit = None
            self.scan_folder_edit = None

            # Mock button groups
            self.scan_button_group = MagicMock(spec=QButtonGroup)

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

    return TestTabSetup()


class TestMainTabSetup:
    """Tests for main tab setup."""

    def test_setup_main_tab_creates_layout(self, tab_setup_mixin):
        """Should create proper layout structure for main tab."""
        with patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder_section, \
             patch.object(tab_setup_mixin, "setup_main_buttons") as mock_main_buttons, \
             patch.object(tab_setup_mixin, "setup_bottom_buttons") as mock_bottom_buttons:

            # Mock folder section returns
            mock_mods_edit = MagicMock(spec=QLineEdit)
            mock_scan_edit = MagicMock(spec=QLineEdit)
            mock_folder_section.side_effect = [mock_mods_edit, mock_scan_edit]

            tab_setup_mixin.setup_main_tab()

            # Verify folder sections created
            assert mock_folder_section.call_count == 2

            # Verify edits assigned
            assert tab_setup_mixin.mods_folder_edit == mock_mods_edit
            assert tab_setup_mixin.scan_folder_edit == mock_scan_edit

            # Verify signal connected for scan folder validation
            mock_scan_edit.editingFinished.connect.assert_called_with(
                tab_setup_mixin.validate_scan_folder_text
            )

            # Verify button sections called
            mock_main_buttons.assert_called_once()
            mock_bottom_buttons.assert_called_once()

    def test_setup_main_buttons_creates_scan_buttons(self, tab_setup_mixin):
        """Should create main scan buttons and add to button group."""
        mock_layout = MagicMock()

        with patch.object(tab_setup_mixin, "add_main_button") as mock_add_button:
            mock_crash_button = MagicMock(spec=QPushButton)
            mock_game_button = MagicMock(spec=QPushButton)
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
        mock_layout = MagicMock(spec=QVBoxLayout)

        with patch.object(tab_setup_mixin, "_create_button") as mock_create_button, \
             patch("ClassicLib.Interface.TabSetupMixin.QApplication") as mock_app:

            mock_buttons = [MagicMock(spec=QPushButton) for _ in range(7)]
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
        mock_button = MagicMock(spec=QPushButton)
        tab_setup_mixin.papyrus_button = mock_button

        tab_setup_mixin.update_papyrus_button_style(True)

        mock_button.setText.assert_called_with("STOP PAPYRUS MONITORING")
        mock_button.setStyleSheet.assert_called()
        # Should have red background in style
        style_call = mock_button.setStyleSheet.call_args[0][0]
        assert "rgb(237, 45, 45)" in style_call

    def test_update_papyrus_button_style_monitoring_inactive(self, tab_setup_mixin):
        """Should update button style when monitoring is inactive."""
        mock_button = MagicMock(spec=QPushButton)
        tab_setup_mixin.papyrus_button = mock_button

        tab_setup_mixin.update_papyrus_button_style(False)

        mock_button.setText.assert_called_with("START PAPYRUS MONITORING")
        mock_button.setStyleSheet.assert_called()
        # Should have green background in style
        style_call = mock_button.setStyleSheet.call_args[0][0]
        assert "rgb(45, 237, 138)" in style_call


class TestArticlesTabSetup:
    """Tests for articles tab setup."""

    def test_setup_articles_tab_creates_resource_buttons(self, tab_setup_mixin):
        """Should create grid of resource buttons."""
        with patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label, \
             patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button, \
             patch("ClassicLib.Interface.TabSetupMixin.partial") as mock_partial:

            mock_button_instances = [MagicMock(spec=QPushButton) for _ in range(9)]
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

        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button, \
             patch("ClassicLib.Interface.TabSetupMixin.partial") as mock_partial:

            def capture_partial(func, url):
                captured_urls.append(url)
                return MagicMock()

            mock_partial.side_effect = capture_partial
            mock_button.return_value = MagicMock(spec=QPushButton)

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


class TestBackupsTabSetup:
    """Tests for backups tab setup."""

    def test_setup_backups_tab_creates_backup_sections(self, tab_setup_mixin):
        """Should create backup sections for each category."""
        with patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label, \
             patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button:

            mock_button_instance = MagicMock(spec=QPushButton)
            mock_button.return_value = mock_button_instance

            tab_setup_mixin.setup_backups_tab()

            # Verify info labels created
            assert mock_label.call_count == 3

            # Verify backup sections created for each category
            expected_categories = ["XSE", "RESHADE", "VULKAN", "ENB"]
            for category in expected_categories:
                tab_setup_mixin.add_backup_section.assert_any_call(
                    mock.ANY, category, category
                )

            # Verify open backups button created
            mock_button.assert_called_with("OPEN CLASSIC BACKUPS")
            mock_button_instance.clicked.connect.assert_called_with(
                tab_setup_mixin.open_backup_folder
            )

            # Verify existing backups checked
            tab_setup_mixin.check_existing_backups.assert_called_once()


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

    def test_add_main_button_wrapper(self, tab_setup_mixin):
        """Should wrap add_main_button from UIHelpers."""
        mock_layout = MagicMock()
        callback = MagicMock()

        with patch("ClassicLib.Interface.TabSetupMixin.add_main_button") as mock_add_main:
            mock_button = MagicMock(spec=QPushButton)
            mock_add_main.return_value = mock_button

            result = tab_setup_mixin.add_main_button(
                mock_layout, "Text", callback, "Tooltip"
            )

            assert result == mock_button
            mock_add_main.assert_called_with(mock_layout, "Text", callback, "Tooltip")


class TestLayoutStructure:
    """Tests for layout structure and organization."""

    def test_main_tab_layout_structure(self, tab_setup_mixin):
        """Should create proper layout hierarchy for main tab."""
        with patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox_class, \
             patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout") as mock_hbox_class, \
             patch("ClassicLib.Interface.TabSetupMixin.QWidget") as mock_widget_class, \
             patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section"):

            # Track layout creation
            layouts_created = {"vbox": [], "hbox": []}

            def track_vbox(*args, **kwargs):
                layout = MagicMock(spec=QVBoxLayout)
                layouts_created["vbox"].append(layout)
                return layout

            def track_hbox(*args, **kwargs):
                layout = MagicMock(spec=QHBoxLayout)
                layouts_created["hbox"].append(layout)
                return layout

            mock_vbox_class.side_effect = track_vbox
            mock_hbox_class.side_effect = track_hbox

            with patch.object(tab_setup_mixin, "setup_main_buttons"), \
                 patch.object(tab_setup_mixin, "setup_bottom_buttons"):

                tab_setup_mixin.setup_main_tab()

                # Should create main vertical layout
                assert len(layouts_created["vbox"]) >= 1

                # Main layout should have proper margins
                main_layout = layouts_created["vbox"][0]
                main_layout.setContentsMargins.assert_called_with(15, 5, 15, 10)
                main_layout.setSpacing.assert_called_with(0)

    def test_articles_tab_grid_layout(self, tab_setup_mixin):
        """Should arrange article buttons in grid."""
        with patch("ClassicLib.Interface.TabSetupMixin.QGridLayout") as mock_grid_class, \
             patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:

            mock_grid = MagicMock()
            mock_grid_class.return_value = mock_grid

            button_positions = []

            def track_add_widget(widget, row, col):
                button_positions.append((row, col))

            mock_grid.addWidget.side_effect = track_add_widget
            mock_button_class.return_value = MagicMock(spec=QPushButton)

            tab_setup_mixin.setup_articles_tab()

            # Should arrange 9 buttons in 3x3 grid
            expected_positions = [
                (0, 0), (0, 1), (0, 2),
                (1, 0), (1, 1), (1, 2),
                (2, 0), (2, 1), (2, 2)
            ]

            assert button_positions == expected_positions
