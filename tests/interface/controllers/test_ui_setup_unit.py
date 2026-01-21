"""Unit tests for UISetupController.

This module tests the UISetupController class that orchestrates the setup
of all tabs and wires UI elements to their respective controllers.

All tests in this module require Qt and cannot run in parallel workers.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# Skip Qt-dependent tests in parallel workers
pytestmark = pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)


class TestUISetupController:
    """Tests for UISetupController class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.main_window = MagicMock()
        context.signal_hub = MagicMock()
        context.signal_hub.papyrus_button_style_update = MagicMock()
        context.signal_hub.papyrus_button_style_update.connect = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.main_tab = None
        context.ui_widgets.articles_tab = None
        context.ui_widgets.backups_tab = None
        context.ui_widgets.scan_button_group = None
        context.ui_widgets.papyrus_button = None
        context.ui_widgets.crash_logs_button = None
        context.ui_widgets.game_files_button = None
        context.ui_widgets.mods_folder_edit = None
        context.ui_widgets.scan_folder_edit = None
        return context

    @pytest.fixture
    def mock_controllers(self):
        """Create mock controllers for testing."""
        return {
            "scan": MagicMock(),
            "results": MagicMock(),
            "papyrus": MagicMock(),
            "backup": MagicMock(),
            "folder": MagicMock(),
            "help_about": MagicMock(),
            "update": MagicMock(),
            "pastebin": MagicMock(),
        }

    @pytest.mark.unit
    def test_controller_creation(self, mock_context, mock_controllers):
        """Test UISetupController can be created with proper initialization."""
        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        assert controller is not None
        assert controller._ctx is mock_context
        assert controller._scan is mock_controllers["scan"]
        assert controller._results is mock_controllers["results"]
        assert controller._papyrus is mock_controllers["papyrus"]
        assert controller._backup is mock_controllers["backup"]
        assert controller._folder is mock_controllers["folder"]
        assert controller._help_about is mock_controllers["help_about"]
        assert controller._update is mock_controllers["update"]
        assert controller._pastebin is mock_controllers["pastebin"]

    @pytest.mark.unit
    def test_signal_connection(self, mock_context, mock_controllers):
        """Test that controller connects to SignalHub signals."""
        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        mock_context.signal_hub.papyrus_button_style_update.connect.assert_called_once()

    @pytest.mark.unit
    def test_setup_all_tabs_calls_setup_methods(self, mock_context, mock_controllers):
        """Test setup_all_tabs calls all setup methods."""
        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        controller.setup_main_tab = MagicMock()
        controller.setup_articles_tab = MagicMock()
        controller.setup_backups_tab = MagicMock()

        controller.setup_all_tabs()

        controller.setup_main_tab.assert_called_once()
        controller.setup_articles_tab.assert_called_once()
        controller.setup_backups_tab.assert_called_once()
        mock_controllers["results"].setup_results_tab.assert_called_once()

    @pytest.mark.unit
    def test_setup_main_tab_no_widget(self, mock_context, mock_controllers):
        """Test setup_main_tab handles missing widget."""
        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        mock_context.ui_widgets.main_tab = None

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        # Should not raise
        controller.setup_main_tab()

    @pytest.mark.unit
    def test_setup_articles_tab_no_widget(self, mock_context, mock_controllers):
        """Test setup_articles_tab handles missing widget."""
        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        mock_context.ui_widgets.articles_tab = None

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        # Should not raise
        controller.setup_articles_tab()

    @pytest.mark.unit
    def test_setup_backups_tab_no_widget(self, mock_context, mock_controllers):
        """Test setup_backups_tab handles missing widget."""
        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        mock_context.ui_widgets.backups_tab = None

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        # Should not raise
        controller.setup_backups_tab()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.ui_setup.setup_folder_section")
    def test_setup_main_tab_creates_layout(self, mock_folder_section, mock_context, mock_controllers, qtbot):
        """Test setup_main_tab creates expected layout."""
        from PySide6.QtWidgets import QWidget

        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        main_tab = QWidget()
        mock_context.ui_widgets.main_tab = main_tab

        # Return mock edits
        mock_mods_edit = MagicMock()
        mock_scan_edit = MagicMock()
        mock_folder_section.side_effect = [mock_mods_edit, mock_scan_edit]

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        controller._setup_main_buttons = MagicMock()
        controller._setup_bottom_buttons = MagicMock()

        controller.setup_main_tab()

        # Verify folder sections were created
        assert mock_folder_section.call_count == 2
        controller._setup_main_buttons.assert_called_once()
        controller._setup_bottom_buttons.assert_called_once()

    @pytest.mark.unit
    def test_setup_articles_tab_creates_buttons(self, mock_context, mock_controllers, qtbot):
        """Test setup_articles_tab creates article buttons."""
        from PySide6.QtWidgets import QWidget

        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        articles_tab = QWidget()
        mock_context.ui_widgets.articles_tab = articles_tab

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        controller.setup_articles_tab()

        # Verify layout was created
        assert articles_tab.layout() is not None

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.ui_setup.create_separator")
    def test_setup_backups_tab_creates_sections(self, mock_separator, mock_context, mock_controllers, qtbot):
        """Test setup_backups_tab creates backup sections."""
        from PySide6.QtWidgets import QFrame, QWidget

        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        backups_tab = QWidget()
        mock_context.ui_widgets.backups_tab = backups_tab
        # Return a real QFrame for the separator
        mock_separator.return_value = QFrame()

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        controller.setup_backups_tab()

        # Verify backup sections were added (4 categories)
        assert mock_controllers["backup"].add_backup_section.call_count == 4
        mock_controllers["backup"].check_existing_backups.assert_called_once()

    @pytest.mark.unit
    def test_create_button_static(self, mock_context, mock_controllers, qtbot):
        """Test _create_button creates styled button."""
        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        callback = MagicMock()

        button = UISetupController._create_button("Test Button", "Test tooltip", callback)

        assert button.text() == "Test Button"
        assert button.toolTip() == "Test tooltip"

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.ui_setup.QDesktopServices")
    def test_open_url_static(self, mock_desktop, mock_context, mock_controllers):
        """Test _open_url opens URL in browser."""
        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        UISetupController._open_url("https://example.com")

        mock_desktop.openUrl.assert_called_once()

    @pytest.mark.unit
    def test_update_papyrus_button_style_monitoring_true(self, mock_context, mock_controllers):
        """Test _update_papyrus_button_style sets stop style when monitoring."""
        from PySide6.QtWidgets import QPushButton

        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        mock_button = QPushButton()
        mock_context.ui_widgets.papyrus_button = mock_button

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        controller._update_papyrus_button_style(True)

        assert "STOP" in mock_button.text()

    @pytest.mark.unit
    def test_update_papyrus_button_style_monitoring_false(self, mock_context, mock_controllers):
        """Test _update_papyrus_button_style sets start style when not monitoring."""
        from PySide6.QtWidgets import QPushButton

        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        mock_button = QPushButton()
        mock_context.ui_widgets.papyrus_button = mock_button

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        controller._update_papyrus_button_style(False)

        assert "START" in mock_button.text()

    @pytest.mark.unit
    def test_update_papyrus_button_style_no_button(self, mock_context, mock_controllers):
        """Test _update_papyrus_button_style handles missing button."""
        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        mock_context.ui_widgets.papyrus_button = None

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        # Should not raise
        controller._update_papyrus_button_style(True)

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.ui_setup.add_main_button")
    def test_setup_main_buttons(self, mock_add_button, mock_context, mock_controllers, qtbot):
        """Test _setup_main_buttons creates scan buttons."""
        from PySide6.QtWidgets import QVBoxLayout, QWidget

        from ClassicLib.Interface.controllers.ui_setup import UISetupController

        mock_crash_button = MagicMock()
        mock_game_button = MagicMock()
        mock_add_button.side_effect = [mock_crash_button, mock_game_button]

        controller = UISetupController(
            context=mock_context,
            scan=mock_controllers["scan"],
            results=mock_controllers["results"],
            papyrus=mock_controllers["papyrus"],
            backup=mock_controllers["backup"],
            folder=mock_controllers["folder"],
            help_about=mock_controllers["help_about"],
            update=mock_controllers["update"],
            pastebin=mock_controllers["pastebin"],
        )

        parent = QWidget()
        layout = QVBoxLayout(parent)

        controller._setup_main_buttons(layout)

        # Verify both buttons were created
        assert mock_add_button.call_count == 2
