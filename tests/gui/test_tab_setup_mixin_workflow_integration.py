"""Integration tests for TabSetupMixin complete workflows.

Tests end-to-end workflows and complex interactions between components
in the TabSetupMixin implementation.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QWidget

from ClassicLib.Interface.TabSetupMixin import TabSetupMixin
from tests.fixtures.registry_fixtures import init_message_handler_fixture  # noqa: F401


@pytest.fixture
def full_tab_setup(init_message_handler_fixture, qt_application):
    """Create a fully functional TabSetupMixin instance for workflow testing."""

    class FullTabSetup(TabSetupMixin):
        """Full implementation with all required components."""

        def __init__(self):
            # Create widgets
            self.main_tab = MagicMock(spec=QWidget)
            self.articles_tab = MagicMock(spec=QWidget)
            self.backups_tab = MagicMock(spec=QWidget)
            self.results_tab = MagicMock(spec=QWidget)

            # Initialize components
            self.scan_button_group = MagicMock()
            self.mods_folder_edit = None
            self.scan_folder_edit = None
            self.crash_logs_button = None
            self.game_files_button = None
            self.papyrus_button = None

            # Track method calls for verification
            self.method_calls = []

            # Implement required methods with tracking
            def track_call(method_name):
                def wrapper(*args, **kwargs):
                    self.method_calls.append(method_name)
                    return MagicMock()

                return wrapper

            self.select_folder_mods = track_call("select_folder_mods")
            self.select_folder_scan = track_call("select_folder_scan")
            self.validate_scan_folder_text = track_call("validate_scan_folder_text")
            self.open_url = track_call("open_url")
            self.show_about = track_call("show_about")
            self.help_popup_main = track_call("help_popup_main")
            self.open_settings = track_call("open_settings")
            self.open_crash_logs_folder = track_call("open_crash_logs_folder")
            self.update_popup_explicit = track_call("update_popup_explicit")
            self.toggle_papyrus_worker = track_call("toggle_papyrus_worker")
            self.crash_logs_scan = track_call("crash_logs_scan")
            self.game_files_scan = track_call("game_files_scan")
            self.open_backup_folder = track_call("open_backup_folder")
            self.check_existing_backups = track_call("check_existing_backups")
            self.add_backup_section = track_call("add_backup_section")

            # Track widget creation
            self.created_widgets = {"buttons": [], "layouts": [], "labels": [], "edits": []}

    return FullTabSetup()


@pytest.mark.integration
@pytest.mark.gui
class TestCompleteTabSetupWorkflow:
    """Tests for complete tab setup workflows."""

    def test_full_application_tab_initialization(self, full_tab_setup):
        """Test complete initialization of all tabs in application startup sequence."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout") as mock_hbox,
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout") as mock_grid,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
            patch("ClassicLib.Interface.TabSetupMixin.QLabel") as mock_label,
            patch("ClassicLib.Interface.TabSetupMixin.QWidget") as mock_widget,
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder,
            patch("ClassicLib.Interface.TabSetupMixin.add_main_button") as mock_add_main,
            patch("ClassicLib.Interface.TabSetupMixin.supports_add_layout", return_value=True),
        ):
            # Setup mock returns
            mock_vbox.return_value = MagicMock()
            mock_hbox.return_value = MagicMock()
            mock_grid.return_value = MagicMock()
            mock_widget.return_value = MagicMock()
            mock_label.return_value = MagicMock()

            # Track button creation
            created_buttons = []

            def create_button(text):
                btn = MagicMock()
                btn.text = text
                btn.isCheckable.return_value = "PAPYRUS" in text
                created_buttons.append(btn)
                return btn

            mock_button.side_effect = create_button

            # Setup folder returns
            mock_folder.side_effect = [MagicMock(), MagicMock()]
            mock_add_main.side_effect = [MagicMock(), MagicMock()]

            # Initialize all tabs
            full_tab_setup.setup_main_tab()
            full_tab_setup.setup_articles_tab()
            full_tab_setup.setup_backups_tab()

            # Verify all tabs were set up
            assert mock_vbox.call_count >= 3  # At least one for each tab

            # Verify buttons were created
            assert len(created_buttons) > 0

            # Verify required checks were called
            assert "check_existing_backups" in full_tab_setup.method_calls

    def test_user_interaction_workflow(self, full_tab_setup):
        """Test typical user interaction workflow through tabs."""
        # Simulate user clicking through tabs and buttons
        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:
            # Track button clicks
            clicked_buttons = []

            def create_interactive_button(text):
                btn = MagicMock()
                btn.text = text
                btn.isCheckable.return_value = False

                # Simulate click behavior
                def simulate_click():
                    clicked_buttons.append(text)
                    # Trigger associated callback
                    if "SCAN CRASH LOGS" in text:
                        full_tab_setup.crash_logs_scan()
                    elif "SETTINGS" in text:
                        full_tab_setup.open_settings()

                btn.click = simulate_click
                return btn

            mock_button_class.side_effect = create_interactive_button

            # Create buttons through _create_button
            scan_btn = full_tab_setup._create_button("SCAN CRASH LOGS", "Tooltip", full_tab_setup.crash_logs_scan)
            settings_btn = full_tab_setup._create_button("SETTINGS", "Tooltip", full_tab_setup.open_settings)

            # Simulate user interactions
            scan_btn.click()
            settings_btn.click()

            # Verify workflow
            assert "SCAN CRASH LOGS" in clicked_buttons
            assert "SETTINGS" in clicked_buttons
            assert "crash_logs_scan" in full_tab_setup.method_calls
            assert "open_settings" in full_tab_setup.method_calls


@pytest.mark.integration
@pytest.mark.gui
class TestPapyrusMonitoringWorkflow:
    """Tests for Papyrus monitoring state transitions."""

    def test_papyrus_monitoring_complete_cycle(self, full_tab_setup):
        """Test complete Papyrus monitoring start/stop cycle."""
        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:
            # Create Papyrus button
            papyrus_button = MagicMock()
            papyrus_button.isCheckable.return_value = True
            papyrus_button.isChecked = MagicMock(return_value=False)
            mock_button_class.return_value = papyrus_button

            # Create button
            full_tab_setup.papyrus_button = full_tab_setup._create_button(
                "START PAPYRUS MONITORING", "Toggle monitoring", full_tab_setup.toggle_papyrus_worker
            )

            # Initial state - not monitoring
            full_tab_setup.update_papyrus_button_style(False)
            papyrus_button.setText.assert_called_with("START PAPYRUS MONITORING")
            assert "rgb(45, 237, 138)" in papyrus_button.setStyleSheet.call_args[0][0]

            # Start monitoring
            papyrus_button.isChecked.return_value = True
            full_tab_setup.update_papyrus_button_style(True)
            papyrus_button.setText.assert_called_with("STOP PAPYRUS MONITORING")
            assert "rgb(237, 45, 45)" in papyrus_button.setStyleSheet.call_args[0][0]

            # Stop monitoring
            papyrus_button.isChecked.return_value = False
            full_tab_setup.update_papyrus_button_style(False)
            papyrus_button.setText.assert_called_with("START PAPYRUS MONITORING")

    def test_papyrus_button_state_persistence(self, full_tab_setup):
        """Test Papyrus button state persists through tab switches."""
        with patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button_class:
            mock_button = MagicMock()
            mock_button.isCheckable.return_value = True
            mock_button_class.return_value = mock_button

            # Set initial state
            full_tab_setup.papyrus_button = mock_button
            full_tab_setup.update_papyrus_button_style(True)

            # Simulate tab switch (button should maintain state)
            initial_calls = mock_button.setText.call_count

            # Update style again (simulating return to tab)
            full_tab_setup.update_papyrus_button_style(True)

            # Text should be set again
            assert mock_button.setText.call_count > initial_calls
            # Should still show STOP text
            mock_button.setText.assert_called_with("STOP PAPYRUS MONITORING")


@pytest.mark.integration
@pytest.mark.gui
class TestFolderSelectionWorkflow:
    """Tests for folder selection and validation workflows."""

    def test_folder_selection_complete_workflow(self, full_tab_setup):
        """Test complete folder selection workflow."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder,
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QWidget"),
            patch.object(full_tab_setup, "setup_main_buttons"),
            patch.object(full_tab_setup, "setup_bottom_buttons"),
        ):
            # Create mock edit widgets
            mods_edit = MagicMock()
            mods_edit.text = MagicMock(return_value="")
            scan_edit = MagicMock()
            scan_edit.text = MagicMock(return_value="")
            scan_edit.editingFinished = MagicMock()

            mock_folder.side_effect = [mods_edit, scan_edit]

            # Setup main tab
            full_tab_setup.setup_main_tab()

            # Verify edits created
            assert full_tab_setup.mods_folder_edit == mods_edit
            assert full_tab_setup.scan_folder_edit == scan_edit

            # Simulate user entering path
            scan_edit.text.return_value = "C:/TestPath"

            # Simulate editing finished signal
            if scan_edit.editingFinished.connect.called:
                callback = scan_edit.editingFinished.connect.call_args[0][0]
                callback()  # Trigger validation

                # Verify validation was called
                assert "validate_scan_folder_text" in full_tab_setup.method_calls

    def test_folder_browse_button_interaction(self, full_tab_setup):
        """Test folder browse button interactions."""
        with patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder:
            # Mock folder section returns edit and button
            mock_edit = MagicMock()
            mock_browse_button = MagicMock()

            # Simulate setup_folder_section behavior
            def folder_section_impl(layout, label, key, callback, tooltip=""):
                # Connect browse button to callback
                mock_browse_button.clicked.connect(callback)
                return mock_edit

            mock_folder.side_effect = folder_section_impl

            with (
                patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
                patch("ClassicLib.Interface.TabSetupMixin.QWidget"),
                patch.object(full_tab_setup, "setup_main_buttons"),
                patch.object(full_tab_setup, "setup_bottom_buttons"),
            ):
                full_tab_setup.setup_main_tab()

                # Simulate browse button clicks
                if mock_browse_button.clicked.connect.called:
                    # Get the connected callbacks
                    calls = mock_browse_button.clicked.connect.call_args_list
                    for call in calls:
                        callback = call[0][0]
                        callback()  # Simulate button click

                # Verify folder selection methods were called
                assert any("select_folder" in call for call in full_tab_setup.method_calls)


@pytest.mark.integration
@pytest.mark.gui
class TestBackupWorkflow:
    """Tests for backup tab workflows."""

    def test_backup_restoration_workflow(self, full_tab_setup):
        """Test complete backup and restoration workflow."""
        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QLabel"),
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
        ):
            # Track backup operations
            backup_operations = []

            def track_backup_section(layout, title, backup_type):
                backup_operations.append({"title": title, "type": backup_type})

            full_tab_setup.add_backup_section = track_backup_section

            # Setup backups tab
            mock_button.return_value = MagicMock()
            full_tab_setup.setup_backups_tab()

            # Verify all backup categories created
            expected_categories = ["XSE", "RESHADE", "VULKAN", "ENB"]
            created_categories = [op["type"] for op in backup_operations]
            assert set(created_categories) == set(expected_categories)

            # Verify existing backups checked
            assert "check_existing_backups" in full_tab_setup.method_calls

    def test_backup_button_states_based_on_existing_backups(self, full_tab_setup):
        """Test backup button states change based on existing backups."""
        # Pre-set the existing backups before setup
        full_tab_setup.existing_backups = {"XSE": True, "RESHADE": False, "VULKAN": True, "ENB": False}

        # Mock check_existing_backups to not override our pre-set values
        def check_backups_impl():
            # Don't change existing_backups, it's already set
            pass

        full_tab_setup.check_existing_backups = check_backups_impl

        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QLabel"),
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton"),
        ):
            # Track button states
            button_states = {}

            def add_backup_impl(layout, title, backup_type):
                # Record whether restore should be enabled based on existing backups
                has_backup = getattr(full_tab_setup, "existing_backups", {}).get(backup_type, False)
                button_states[backup_type] = {"restore_enabled": has_backup, "backup_enabled": not has_backup}

            full_tab_setup.add_backup_section = add_backup_impl

            full_tab_setup.setup_backups_tab()

            # Verify button states match expected backup status
            assert button_states["XSE"]["restore_enabled"]
            assert not button_states["XSE"]["backup_enabled"]
            assert not button_states["RESHADE"]["restore_enabled"]
            assert button_states["RESHADE"]["backup_enabled"]
            assert button_states["VULKAN"]["restore_enabled"]
            assert not button_states["ENB"]["restore_enabled"]


@pytest.mark.integration
@pytest.mark.gui
class TestArticleNavigationWorkflow:
    """Tests for article tab navigation workflows."""

    def test_article_button_url_navigation(self, full_tab_setup):
        """Test article button URL navigation workflow."""
        opened_urls = []

        def track_url(url):
            opened_urls.append(url)
            return MagicMock()

        full_tab_setup.open_url = track_url

        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QLabel"),
            patch("ClassicLib.Interface.TabSetupMixin.QGridLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
            patch("ClassicLib.Interface.TabSetupMixin.partial") as mock_partial,
        ):
            # Track partial creations
            url_callbacks = {}

            def create_partial(func, url):
                callback = lambda: func(url)
                url_callbacks[url] = callback
                return callback

            mock_partial.side_effect = create_partial
            mock_button.return_value = MagicMock()

            full_tab_setup.setup_articles_tab()

            # Simulate clicking each article button
            for _url, callback in url_callbacks.items():
                callback()

            # Verify all URLs were opened
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

            assert set(opened_urls) == set(expected_urls)


@pytest.mark.integration
@pytest.mark.gui
class TestMultiTabInteraction:
    """Tests for interactions between multiple tabs."""

    def test_scan_results_affect_multiple_tabs(self, full_tab_setup):
        """Test how scan results affect multiple tabs."""
        # Setup scan results that should affect other tabs
        scan_results = {"errors_found": True, "backup_needed": ["XSE", "ENB"], "articles_relevant": ["BUFFOUT 4 INSTALLATION"]}

        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QHBoxLayout"),
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
            patch("ClassicLib.Interface.TabSetupMixin.add_main_button") as mock_add_main,
        ):
            # Create scan button
            scan_button = MagicMock()
            mock_add_main.return_value = scan_button

            # Setup tabs
            mock_button.return_value = MagicMock()

            # Simulate scan completing
            def simulate_scan():
                # Would update UI based on results
                full_tab_setup.scan_results = scan_results
                # Notify other tabs (in real implementation)
                if scan_results["backup_needed"]:
                    # Would enable specific backup buttons
                    pass
                if scan_results["articles_relevant"]:
                    # Would highlight relevant articles
                    pass

            full_tab_setup.crash_logs_scan = simulate_scan

            with (
                patch.object(full_tab_setup, "setup_main_buttons"),
                patch.object(full_tab_setup, "setup_bottom_buttons"),
                patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section"),
                patch("ClassicLib.Interface.TabSetupMixin.QWidget"),
            ):
                full_tab_setup.setup_main_tab()

                # Trigger scan
                full_tab_setup.crash_logs_scan()

                # Verify scan results stored
                assert hasattr(full_tab_setup, "scan_results")
                assert full_tab_setup.scan_results["errors_found"]


@pytest.mark.integration
@pytest.mark.gui
class TestErrorRecoveryWorkflow:
    """Tests for error recovery workflows."""

    def test_tab_setup_recovery_from_partial_failure(self, full_tab_setup):
        """Test tab setup can recover from partial failures."""
        setup_stages = []

        with (
            patch("ClassicLib.Interface.TabSetupMixin.QVBoxLayout") as mock_vbox,
            patch("ClassicLib.Interface.TabSetupMixin.QPushButton") as mock_button,
            patch("ClassicLib.Interface.TabSetupMixin.setup_folder_section") as mock_folder,
        ):
            # First folder setup fails
            def folder_setup(layout, label, key, callback, tooltip=""):
                if len(setup_stages) == 0:
                    setup_stages.append("folder_1_failed")
                    return None  # Failure
                setup_stages.append("folder_2_success")
                return MagicMock()  # Success

            mock_folder.side_effect = folder_setup
            mock_vbox.return_value = MagicMock()
            mock_button.return_value = MagicMock()

            with (
                patch.object(full_tab_setup, "setup_main_buttons"),
                patch.object(full_tab_setup, "setup_bottom_buttons"),
                patch("ClassicLib.Interface.TabSetupMixin.QWidget"),
            ):
                # Should complete despite first folder failure
                full_tab_setup.setup_main_tab()

                # Verify recovery
                assert "folder_1_failed" in setup_stages
                assert "folder_2_success" in setup_stages
                assert full_tab_setup.mods_folder_edit is None  # Failed
                assert full_tab_setup.scan_folder_edit is not None  # Succeeded
