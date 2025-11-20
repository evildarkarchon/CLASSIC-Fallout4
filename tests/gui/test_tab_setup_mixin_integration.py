"""Integration tests for TabSetupMixin.

Tests TabSetupMixin with minimal mocking to verify component interactions.
"""

from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ClassicLib.Interface.TabSetupMixin import TabSetupMixin

# Note: MessageHandler initialization is now handled by standardized
# fixtures in tests/fixtures/registry_fixtures.py which provide:
# - message_handler: For non-GUI tests
# - gui_message_handler: For GUI tests (from qt_fixtures.py)
# - Automatic cleanup via ensure_message_handler_cleanup
from tests.gui.qt_mock_helpers import (
    create_qt_widget_mock,
)


@pytest.fixture
def integrated_tab_setup(init_message_handler_fixture, qt_application):
    """Create TabSetupMixin with minimal mocking for integration testing."""

    class IntegratedTabSetup(TabSetupMixin):
        """Test class with minimal mocking."""

        def __init__(self):
            # Create real widgets where possible
            self.main_tab = MagicMock(spec=QWidget)
            self.articles_tab = MagicMock(spec=QWidget)
            self.backups_tab = MagicMock(spec=QWidget)
            self.results_tab = MagicMock(spec=QWidget)

            # Initialize button group
            self.scan_button_group = MagicMock(spec=QButtonGroup)

            # Initialize as None - will be set during setup
            self.mods_folder_edit = None
            self.scan_folder_edit = None
            self.crash_logs_button = None
            self.game_files_button = None
            self.papyrus_button = None

            # Mock callbacks
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

            # Track created components
            self.created_buttons = []
            self.created_layouts = []

    return IntegratedTabSetup()


@pytest.mark.integration
@pytest.mark.gui
class TestMainTabIntegration:
    """Integration tests for main tab setup."""

    def test_complete_main_tab_setup(self, integrated_tab_setup, gui_message_handler):
        """Test complete main tab setup workflow."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class,
            patch("ClassicLib.Interface.UIHelpers.supports_add_layout", return_value=True),
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout") as mock_hbox,
        ):
            # Mock layout creation
            mock_vbox.return_value = MagicMock()
            mock_hbox.return_value = MagicMock()

            # Track button creation
            created_buttons = []

            def create_button(text):
                btn = MagicMock(spec=QPushButton)
                btn.text = text
                btn.isCheckable.return_value = text == "START PAPYRUS MONITORING"
                created_buttons.append(btn)
                return btn

            mock_button_class.side_effect = create_button

            # Mock folder sections
            mock_folder.side_effect = [MagicMock(), MagicMock()]

            # Setup main tab
            integrated_tab_setup.setup_main_tab()

            # Verify folder sections created
            assert mock_folder.call_count == 2

            # Verify buttons created (should have main scan buttons and utility buttons)
            assert len(created_buttons) > 0

            # Find papyrus button
            papyrus_buttons = [b for b in created_buttons if b.text == "START PAPYRUS MONITORING"]
            assert len(papyrus_buttons) == 1
            assert integrated_tab_setup.papyrus_button is not None

    def test_main_buttons_workflow(self, integrated_tab_setup, gui_message_handler):
        """Test main button creation and interaction."""
        with patch("ClassicLib.Interface.TabSetupMixin.add_main_button") as mock_add_main:
            # Simulate button creation
            crash_button = MagicMock(spec=QPushButton)
            game_button = MagicMock(spec=QPushButton)
            mock_add_main.side_effect = [crash_button, game_button]

            layout = MagicMock()
            integrated_tab_setup.setup_main_buttons(layout)

            # Verify buttons created and stored
            assert integrated_tab_setup.crash_logs_button == crash_button
            assert integrated_tab_setup.game_files_button == game_button

            # Verify callbacks configured
            calls = mock_add_main.call_args_list
            assert calls[0][0][1] == "SCAN CRASH LOGS"
            assert calls[0][0][2] == integrated_tab_setup.crash_logs_scan
            assert calls[1][0][1] == "SCAN GAME FILES"
            assert calls[1][0][2] == integrated_tab_setup.game_files_scan

    def test_papyrus_button_state_transitions(self, integrated_tab_setup, gui_message_handler):
        """Test papyrus button state transitions."""
        # Create a mock button
        papyrus_button = MagicMock(spec=QPushButton)
        integrated_tab_setup.papyrus_button = papyrus_button

        # Test transition to monitoring state
        integrated_tab_setup.update_papyrus_button_style(True)
        papyrus_button.setText.assert_called_with("STOP PAPYRUS MONITORING")

        # Verify red style applied
        style_call = papyrus_button.setStyleSheet.call_args[0][0]
        assert "rgb(237, 45, 45)" in style_call

        # Test transition back to idle state
        integrated_tab_setup.update_papyrus_button_style(False)
        papyrus_button.setText.assert_called_with("START PAPYRUS MONITORING")

        # Verify green style applied
        style_call = papyrus_button.setStyleSheet.call_args[0][0]
        assert "rgb(45, 237, 138)" in style_call


@pytest.mark.integration
@pytest.mark.gui
class TestArticlesTabIntegration:
    """Integration tests for articles tab."""

    def test_articles_tab_button_interactions(self, integrated_tab_setup, gui_message_handler):
        """Test article buttons are created with proper URL handling."""
        captured_configs = []

        # Create a proper mock widget for articles_tab
        integrated_tab_setup.articles_tab = create_qt_widget_mock()

        with (
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class,
            patch("ClassicLib.Interface.TabSetupMixin.partial") as mock_partial,
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout") as mock_grid_class,
            patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label,
        ):

            def capture_button_config(text):
                btn = MagicMock(spec=QPushButton)
                btn.text = text
                captured_configs.append({"text": text, "button": btn})
                return btn

            mock_button_class.side_effect = capture_button_config

            # Track partial calls to capture URLs
            url_mappings = {}

            def capture_partial(func, url):
                # Store URL mapping
                url_mappings[len(url_mappings)] = url
                return MagicMock()

            mock_partial.side_effect = capture_partial

            def create_vbox(*args, **kwargs):
                m = MagicMock()
                m.__class__ = QVBoxLayout
                return m

            mock_vbox.side_effect = create_vbox
            mock_vbox.__or__ = lambda self, other: (QVBoxLayout, QHBoxLayout)

            # Create mocks for grid and label
            mock_grid = MagicMock()
            mock_grid.addWidget = MagicMock()
            mock_grid_class.return_value = mock_grid
            mock_label.return_value = MagicMock()

            integrated_tab_setup.setup_articles_tab()

            # Verify 9 buttons created
            assert len(captured_configs) == 9

            # Verify button texts
            expected_texts = [
                "BUFFOUT 4 INSTALLATION",
                "FALLOUT 4 SETUP TIPS",
                "IMPORTANT PATCHES LIST",
                "BUFFOUT 4 NEXUS",
                "CLASSIC NEXUS",
                "CLASSIC GITHUB",
                "DDS TEXTURE SCANNER",
                "BETHINI PIE",
                "WRYE BASH",
            ]

            actual_texts = [cfg["text"] for cfg in captured_configs]
            assert actual_texts == expected_texts

            # Verify all buttons have style and tooltip
            for cfg in captured_configs:
                cfg["button"].setStyleSheet.assert_called()
                cfg["button"].setToolTip.assert_called()

    def test_articles_grid_layout_arrangement(self, integrated_tab_setup, gui_message_handler):
        """Test articles are arranged correctly in grid."""
        # Create a proper mock widget for articles_tab
        integrated_tab_setup.articles_tab = create_qt_widget_mock()

        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout") as mock_grid_class,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class,
        ):
            mock_grid = MagicMock()
            mock_grid_class.return_value = mock_grid

            # Track grid positions
            grid_positions = {}

            def track_grid_add(widget, row, col):
                grid_positions[row, col] = widget

            mock_grid.addWidget.side_effect = track_grid_add
            mock_button_class.return_value = MagicMock(spec=QPushButton)

            def create_vbox(*args, **kwargs):
                m = MagicMock()
                m.__class__ = QVBoxLayout
                return m

            mock_vbox.side_effect = create_vbox
            mock_vbox.__or__ = lambda self, other: (QVBoxLayout, QHBoxLayout)

            integrated_tab_setup.setup_articles_tab()

            # Verify 3x3 grid layout
            assert len(grid_positions) == 9

            # Verify positions are sequential
            for i in range(9):
                row, col = divmod(i, 3)
                assert (row, col) in grid_positions


@pytest.mark.integration
@pytest.mark.gui
class TestBackupsTabIntegration:
    """Integration tests for backups tab."""

    def test_backups_tab_complete_setup(self, integrated_tab_setup, gui_message_handler):
        """Test complete backups tab setup."""
        # Create a proper mock widget for backups_tab
        integrated_tab_setup.backups_tab = create_qt_widget_mock()

        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout") as mock_hbox,
            patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label_class,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class,
        ):
            labels_created = []
            buttons_created = []

            mock_label_class.side_effect = lambda text: labels_created.append(text) or MagicMock()
            mock_button_class.side_effect = lambda text: buttons_created.append(text) or MagicMock()

            def create_vbox(*args, **kwargs):
                m = MagicMock()
                m.__class__ = QVBoxLayout
                return m

            def create_hbox(*args, **kwargs):
                m = MagicMock()
                m.__class__ = QHBoxLayout
                return m

            mock_vbox.side_effect = create_vbox
            mock_hbox.side_effect = create_hbox
            mock_vbox.__or__ = lambda self, other: (QVBoxLayout, QHBoxLayout)
            mock_hbox.__or__ = lambda self, other: (QVBoxLayout, QHBoxLayout)

            integrated_tab_setup.setup_backups_tab()

            # Verify info labels created
            assert len(labels_created) == 3
            assert "BACKUP >" in labels_created[0]
            assert "RESTORE >" in labels_created[1]
            assert "REMOVE >" in labels_created[2]

            # Verify backup sections for each category
            categories = ["XSE", "RESHADE", "VULKAN", "ENB"]
            for category in categories:
                integrated_tab_setup.add_backup_section.assert_any_call(mock.ANY, category, category)

            # Verify open backups button
            assert "OPEN CLASSIC BACKUPS" in buttons_created

            # Verify backup check called
            integrated_tab_setup.check_existing_backups.assert_called_once()


@pytest.mark.integration
@pytest.mark.gui
class TestButtonBehaviorIntegration:
    """Integration tests for button behaviors."""

    def test_button_callback_connections(self, integrated_tab_setup, gui_message_handler):
        """Test that buttons properly connect to callbacks."""
        callbacks_tested = []

        def track_callback(name):
            def callback():
                callbacks_tested.append(name)

            return callback

        # Replace callbacks with tracking versions
        integrated_tab_setup.show_about = track_callback("about")
        integrated_tab_setup.help_popup_main = track_callback("help")
        integrated_tab_setup.open_settings = track_callback("settings")

        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:
            buttons = {}

            def create_button(text):
                btn = MagicMock(spec=QPushButton)
                btn.text = text
                btn.isCheckable.return_value = False
                buttons[text] = btn
                return btn

            mock_button_class.side_effect = create_button

            # Create a button using _create_button
            about_btn = integrated_tab_setup._create_button("ABOUT", "About tooltip", integrated_tab_setup.show_about)

            # Verify button created
            assert about_btn is not None
            about_btn.setToolTip.assert_called_with("About tooltip")

    def test_checkable_button_behavior(self, integrated_tab_setup, gui_message_handler):
        """Test checkable button uses toggled signal."""
        toggle_callback = MagicMock()

        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:
            mock_button = MagicMock(spec=QPushButton)
            mock_button.isCheckable.return_value = True
            mock_button_class.return_value = mock_button

            integrated_tab_setup._create_button("TOGGLE", "Toggle tooltip", toggle_callback)

            # Should use toggled for checkable buttons
            mock_button.toggled.connect.assert_called_with(toggle_callback)
            mock_button.clicked.connect.assert_not_called()


@pytest.mark.integration
@pytest.mark.gui
class TestURLHandlingIntegration:
    """Integration tests for URL handling in articles tab."""

    def test_url_callback_binding(self, integrated_tab_setup, gui_message_handler):
        """Test that URLs are properly bound to button callbacks."""
        url_bindings = {}

        # Create a proper mock widget for articles_tab
        integrated_tab_setup.articles_tab = create_qt_widget_mock()

        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class,
            patch("ClassicLib.Interface.TabSetupMixin.partial") as mock_partial,
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout") as mock_grid_class,
            patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label,
        ):
            button_index = 0

            def create_button(text):
                nonlocal button_index
                btn = MagicMock(spec=QPushButton)
                btn.text = text
                btn.index = button_index
                button_index += 1
                return btn

            mock_button_class.side_effect = create_button

            def create_partial(func, url):
                # Map button index to URL
                url_bindings[button_index - 1] = url
                return MagicMock()

            mock_partial.side_effect = create_partial

            def create_vbox(*args, **kwargs):
                m = MagicMock()
                m.__class__ = QVBoxLayout
                return m

            mock_vbox.side_effect = create_vbox
            mock_vbox.__or__ = lambda self, other: (QVBoxLayout, QHBoxLayout)

            # Create mocks for grid and label
            mock_grid = MagicMock()
            mock_grid.addWidget = MagicMock()
            mock_grid_class.return_value = mock_grid
            mock_label.return_value = MagicMock()

            integrated_tab_setup.setup_articles_tab()

            # Verify URL mappings
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

            for i, expected_url in enumerate(expected_urls):
                assert url_bindings[i] == expected_url


@pytest.mark.integration
@pytest.mark.gui
class TestCompleteWorkflowIntegration:
    """Integration tests for complete tab setup workflow."""

    def test_all_tabs_setup_workflow(self, integrated_tab_setup, gui_message_handler):
        """Test setting up all tabs in sequence."""
        # Create proper mock widgets for all tabs
        integrated_tab_setup.articles_tab = create_qt_widget_mock()
        integrated_tab_setup.backups_tab = create_qt_widget_mock()

        with (
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section"),
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
            patch("ClassicLib.Interface.TabSetupMixin.QLabel"),
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout"),
            patch("ClassicLib.Interface.UIHelpers.supports_add_layout", return_value=True),
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout") as mock_hbox,
        ):
            # Mock layout creation
            mock_vbox.return_value = MagicMock()
            mock_hbox.return_value = MagicMock()
            mock_button.return_value = MagicMock(spec=QPushButton)

            # Setup all tabs
            integrated_tab_setup.setup_main_tab()
            integrated_tab_setup.setup_articles_tab()
            integrated_tab_setup.setup_backups_tab()

            # Verify key callbacks were set up
            assert integrated_tab_setup.crash_logs_scan is not None
            assert integrated_tab_setup.game_files_scan is not None
            assert integrated_tab_setup.open_backup_folder is not None

            # Verify required checks called
            integrated_tab_setup.check_existing_backups.assert_called_once()
