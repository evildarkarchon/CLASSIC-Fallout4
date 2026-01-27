"""Unit tests for PathManager INI folder path management.

This module tests the PathManager class that handles INI folder path
browsing, resetting, and autodetection for game configuration.

All tests in this module mock Qt dialogs and YAML settings to prevent
UI popups and file system changes during testing.
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


class TestPathManagerInit:
    """Tests for PathManager initialization."""

    @pytest.mark.unit
    def test_init_with_default_yaml_store(self, qt_parent_widget):
        """Test PathManager initializes with default YAML.Settings store."""
        from ClassicLib.core.constants import YAML
        from ClassicLib.Interface.Settings.path_manager import PathManager

        manager = PathManager(qt_parent_widget)

        assert manager.parent is qt_parent_widget
        assert manager.yaml_store is YAML.Settings
        assert manager.ini_folder_input is None

    @pytest.mark.unit
    def test_init_with_custom_yaml_store(self, qt_parent_widget):
        """Test PathManager initializes with custom YAML store."""
        from ClassicLib.core.constants import YAML
        from ClassicLib.Interface.Settings.path_manager import PathManager

        manager = PathManager(qt_parent_widget, yaml_store=YAML.Game_Local)

        assert manager.yaml_store is YAML.Game_Local

    @pytest.mark.unit
    def test_set_ini_folder_input(self, qt_parent_widget):
        """Test set_ini_folder_input stores the widget reference."""
        from PySide6.QtWidgets import QLineEdit

        from ClassicLib.Interface.Settings.path_manager import PathManager

        manager = PathManager(qt_parent_widget)
        line_edit = QLineEdit()

        manager.set_ini_folder_input(line_edit)

        assert manager.ini_folder_input is line_edit


class TestPathManagerBrowse:
    """Tests for browse_ini_folder method."""

    @pytest.fixture
    def manager_with_input(self, qt_parent_widget):
        """Create PathManager with a mock line edit input."""
        from ClassicLib.Interface.Settings.path_manager import PathManager

        manager = PathManager(qt_parent_widget)
        mock_input = MagicMock()
        mock_input.text.return_value = "/existing/path"
        manager.ini_folder_input = mock_input
        return manager

    @pytest.mark.unit
    def test_browse_returns_early_without_input(self, qt_parent_widget):
        """Test browse_ini_folder returns early when no input widget set."""
        from ClassicLib.Interface.Settings.path_manager import PathManager

        manager = PathManager(qt_parent_widget)
        # ini_folder_input is None by default

        # Should not raise and should return early
        manager.browse_ini_folder()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.QFileDialog")
    @patch("ClassicLib.core.registry.GlobalRegistry.get_game")
    def test_browse_sets_selected_folder(self, mock_get_game, mock_dialog, manager_with_input):
        """Test browse_ini_folder sets selected folder to input widget."""
        mock_get_game.return_value = "Fallout4"
        mock_dialog.getExistingDirectory.return_value = "/new/selected/path"
        mock_dialog.Option.ShowDirsOnly = 0x1

        manager_with_input.browse_ini_folder()

        manager_with_input.ini_folder_input.setText.assert_called_once_with("/new/selected/path")

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.QFileDialog")
    @patch("ClassicLib.core.registry.GlobalRegistry.get_game")
    def test_browse_handles_cancelled_dialog(self, mock_get_game, mock_dialog, manager_with_input):
        """Test browse_ini_folder handles cancelled dialog (empty string)."""
        mock_get_game.return_value = "Fallout4"
        mock_dialog.getExistingDirectory.return_value = ""  # User cancelled

        manager_with_input.browse_ini_folder()

        manager_with_input.ini_folder_input.setText.assert_not_called()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.QFileDialog")
    @patch("ClassicLib.core.registry.GlobalRegistry.get_game")
    def test_browse_uses_game_name_from_registry(self, mock_get_game, mock_dialog, manager_with_input):
        """Test browse_ini_folder uses game name from GlobalRegistry for dialog title."""
        mock_get_game.return_value = "Skyrim"
        mock_dialog.getExistingDirectory.return_value = ""
        mock_dialog.Option.ShowDirsOnly = 0x1

        manager_with_input.browse_ini_folder()

        call_args = mock_dialog.getExistingDirectory.call_args
        dialog_title = call_args[0][1]
        assert "Skyrim" in dialog_title

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.QFileDialog")
    @patch("ClassicLib.core.registry.GlobalRegistry.get_game")
    def test_browse_fallback_to_game_on_registry_error(self, mock_get_game, mock_dialog, manager_with_input):
        """Test browse_ini_folder falls back to 'Game' when registry raises."""
        mock_get_game.side_effect = ValueError("No game configured")
        mock_dialog.getExistingDirectory.return_value = ""
        mock_dialog.Option.ShowDirsOnly = 0x1

        manager_with_input.browse_ini_folder()

        call_args = mock_dialog.getExistingDirectory.call_args
        dialog_title = call_args[0][1]
        assert "Game" in dialog_title


class TestPathManagerReset:
    """Tests for reset_ini_folder method."""

    @pytest.fixture
    def manager_with_mock_input(self, qt_parent_widget):
        """Create PathManager with a mock line edit input."""
        from ClassicLib.Interface.Settings.path_manager import PathManager

        manager = PathManager(qt_parent_widget)
        mock_input = MagicMock()
        manager.ini_folder_input = mock_input
        return manager

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.msg_success")
    @patch("ClassicLib.support.docs_path.docs_path_find")
    @patch("ClassicLib.Interface.Settings.path_manager.yaml_settings")
    @patch("ClassicLib.core.registry.GlobalRegistry.get_vr")
    def test_reset_clears_settings_and_runs_autodetect(
        self,
        mock_get_vr,
        mock_yaml,
        mock_docs_find,
        mock_msg_success,
        manager_with_mock_input,
    ):
        """Test reset_ini_folder clears YAML settings and runs autodetection."""
        mock_get_vr.return_value = ""
        mock_yaml.side_effect = [None, None, "/detected/path"]

        manager_with_mock_input.reset_ini_folder()

        # Should have called yaml_settings 3 times:
        # 1. Clear INI Folder Path
        # 2. Clear Root_Folder_Docs
        # 3. Read detected path in autodetect
        assert mock_yaml.call_count == 3

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.msg_error")
    @patch("ClassicLib.Interface.Settings.path_manager.yaml_settings")
    def test_reset_handles_import_error(self, mock_yaml, mock_msg_error, manager_with_mock_input):
        """Test reset_ini_folder handles ImportError gracefully."""
        mock_yaml.side_effect = ImportError("Module not found")

        manager_with_mock_input.reset_ini_folder()

        mock_msg_error.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.msg_error")
    @patch("ClassicLib.Interface.Settings.path_manager.yaml_settings")
    def test_reset_handles_os_error(self, mock_yaml, mock_msg_error, manager_with_mock_input):
        """Test reset_ini_folder handles OSError gracefully."""
        mock_yaml.side_effect = OSError("File system error")

        manager_with_mock_input.reset_ini_folder()

        mock_msg_error.assert_called_once()
        assert "File system error" in str(mock_msg_error.call_args)


class TestPathManagerAutodetect:
    """Tests for autodetect_ini_folder method."""

    @pytest.fixture
    def manager_with_mock_input(self, qt_parent_widget):
        """Create PathManager with a mock line edit input."""
        from ClassicLib.Interface.Settings.path_manager import PathManager

        manager = PathManager(qt_parent_widget)
        mock_input = MagicMock()
        manager.ini_folder_input = mock_input
        return manager

    @pytest.mark.unit
    def test_autodetect_returns_early_without_input(self, qt_parent_widget):
        """Test autodetect_ini_folder returns early when no input widget set."""
        from ClassicLib.Interface.Settings.path_manager import PathManager

        manager = PathManager(qt_parent_widget)
        # ini_folder_input is None by default

        # Should not raise and should return early
        manager.autodetect_ini_folder()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.msg_success")
    @patch("ClassicLib.Interface.Settings.path_manager.yaml_settings")
    @patch("ClassicLib.support.docs_path.docs_path_find")
    @patch("ClassicLib.core.registry.GlobalRegistry.get_vr")
    def test_autodetect_updates_input_on_success(
        self,
        mock_get_vr,
        mock_docs_find,
        mock_yaml,
        mock_msg_success,
        manager_with_mock_input,
    ):
        """Test autodetect_ini_folder updates input widget with detected path."""
        mock_get_vr.return_value = ""
        mock_yaml.return_value = "/detected/ini/folder"

        manager_with_mock_input.autodetect_ini_folder()

        manager_with_mock_input.ini_folder_input.setText.assert_called_once_with("/detected/ini/folder")
        mock_msg_success.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.msg_warning")
    @patch("ClassicLib.Interface.Settings.path_manager.yaml_settings")
    @patch("ClassicLib.support.docs_path.docs_path_find")
    @patch("ClassicLib.core.registry.GlobalRegistry.get_vr")
    def test_autodetect_clears_input_when_detection_fails(
        self,
        mock_get_vr,
        mock_docs_find,
        mock_yaml,
        mock_msg_warning,
        manager_with_mock_input,
    ):
        """Test autodetect_ini_folder clears input when detection returns empty."""
        mock_get_vr.return_value = ""
        mock_yaml.return_value = ""  # Empty = detection failed

        manager_with_mock_input.autodetect_ini_folder()

        manager_with_mock_input.ini_folder_input.clear.assert_called_once()
        mock_msg_warning.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.msg_warning")
    @patch("ClassicLib.Interface.Settings.path_manager.yaml_settings")
    @patch("ClassicLib.support.docs_path.docs_path_find")
    @patch("ClassicLib.core.registry.GlobalRegistry.get_vr")
    def test_autodetect_clears_input_when_detection_returns_none(
        self,
        mock_get_vr,
        mock_docs_find,
        mock_yaml,
        mock_msg_warning,
        manager_with_mock_input,
    ):
        """Test autodetect_ini_folder clears input when detection returns None."""
        mock_get_vr.return_value = ""
        mock_yaml.return_value = None

        manager_with_mock_input.autodetect_ini_folder()

        manager_with_mock_input.ini_folder_input.clear.assert_called_once()
        mock_msg_warning.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.msg_error")
    @patch("ClassicLib.support.docs_path.docs_path_find")
    @patch("ClassicLib.core.registry.GlobalRegistry.get_vr")
    def test_autodetect_handles_type_error(
        self,
        mock_get_vr,
        mock_docs_find,
        mock_msg_error,
        manager_with_mock_input,
    ):
        """Test autodetect_ini_folder handles TypeError gracefully."""
        mock_get_vr.side_effect = TypeError("Invalid type")

        manager_with_mock_input.autodetect_ini_folder()

        mock_msg_error.assert_called_once()
        assert "Invalid type" in str(mock_msg_error.call_args)

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.msg_error")
    @patch("ClassicLib.support.docs_path.docs_path_find")
    @patch("ClassicLib.core.registry.GlobalRegistry.get_vr")
    def test_autodetect_handles_value_error(
        self,
        mock_get_vr,
        mock_docs_find,
        mock_msg_error,
        manager_with_mock_input,
    ):
        """Test autodetect_ini_folder handles ValueError gracefully."""
        mock_get_vr.side_effect = ValueError("Invalid value")

        manager_with_mock_input.autodetect_ini_folder()

        mock_msg_error.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.Settings.path_manager.msg_success")
    @patch("ClassicLib.Interface.Settings.path_manager.yaml_settings")
    @patch("ClassicLib.support.docs_path.docs_path_find")
    @patch("ClassicLib.core.registry.GlobalRegistry.get_vr")
    def test_autodetect_handles_vr_suffix(
        self,
        mock_get_vr,
        mock_docs_find,
        mock_yaml,
        mock_msg_success,
        manager_with_mock_input,
    ):
        """Test autodetect_ini_folder handles VR suffix correctly."""
        mock_get_vr.return_value = "VR"
        mock_yaml.return_value = "/detected/vr/folder"

        manager_with_mock_input.autodetect_ini_folder()

        # Verify the yaml_settings call uses correct VR key
        yaml_call_args = mock_yaml.call_args[0]
        assert "GameVR_Info.Root_Folder_Docs" == yaml_call_args[2]
