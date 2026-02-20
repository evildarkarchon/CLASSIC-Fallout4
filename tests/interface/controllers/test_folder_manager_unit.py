"""Unit tests for FolderManager controller.

This module tests the FolderManager class that handles folder selection,
validation, and opening folder locations in the file explorer.

All tests in this module require Qt and cannot run in parallel workers.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip Qt-dependent tests in parallel workers
pytestmark = pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)


class TestFolderManager:
    """Tests for FolderManager class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.main_window = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.scan_folder_edit = MagicMock()
        context.ui_widgets.mods_folder_edit = MagicMock()
        context.local_dir = None
        return context

    @pytest.mark.unit
    def test_controller_creation(self, mock_context):
        """Test FolderManager can be created with proper initialization."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        manager = FolderManager(mock_context)

        assert manager is not None
        assert manager._ctx is mock_context

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.QFileDialog")
    @patch("ClassicLib.Interface.controllers.folder_manager.yaml_settings")
    @patch("ClassicLib.Interface.controllers.folder_manager.is_valid_custom_scan_path")
    def test_select_folder_scan_valid_path(self, mock_valid, mock_yaml, mock_dialog, mock_context):
        """Test select_folder_scan saves valid path."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_dialog.getExistingDirectory.return_value = "/valid/path"
        mock_valid.return_value = True

        manager = FolderManager(mock_context)
        manager.select_folder_scan()

        mock_context.ui_widgets.scan_folder_edit.setText.assert_called_once_with("/valid/path")
        mock_yaml.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.QFileDialog")
    def test_select_folder_scan_cancelled(self, mock_dialog, mock_context):
        """Test select_folder_scan handles user cancel."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_dialog.getExistingDirectory.return_value = ""  # User cancelled

        manager = FolderManager(mock_context)
        manager.select_folder_scan()

        mock_context.ui_widgets.scan_folder_edit.setText.assert_not_called()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.QMessageBox")
    @patch("ClassicLib.Interface.controllers.folder_manager.QFileDialog")
    @patch("ClassicLib.Interface.controllers.folder_manager.is_valid_custom_scan_path")
    def test_select_folder_scan_invalid_shows_warning(self, mock_valid, mock_dialog, mock_msgbox, mock_context):
        """Test select_folder_scan shows warning for invalid path."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        # First call returns invalid path, second call user cancels
        mock_dialog.getExistingDirectory.side_effect = ["/crash/logs", ""]
        mock_valid.return_value = False

        manager = FolderManager(mock_context)
        manager.select_folder_scan()

        mock_msgbox.warning.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.QFileDialog")
    @patch("ClassicLib.Interface.controllers.folder_manager.yaml_settings")
    def test_select_folder_mods_saves_path(self, mock_yaml, mock_dialog, mock_context):
        """Test select_folder_mods saves selected path."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_dialog.getExistingDirectory.return_value = "/mods/folder"

        manager = FolderManager(mock_context)
        manager.select_folder_mods()

        mock_context.ui_widgets.mods_folder_edit.setText.assert_called_once_with("/mods/folder")
        mock_yaml.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.QFileDialog")
    def test_select_folder_mods_cancelled(self, mock_dialog, mock_context):
        """Test select_folder_mods handles user cancel."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_dialog.getExistingDirectory.return_value = ""

        manager = FolderManager(mock_context)
        manager.select_folder_mods()

        mock_context.ui_widgets.mods_folder_edit.setText.assert_not_called()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.yaml_settings")
    def test_validate_scan_folder_text_empty_clears(self, mock_yaml, mock_context):
        """Test validate_scan_folder_text clears setting for empty input."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_context.ui_widgets.scan_folder_edit.text.return_value = "  "

        manager = FolderManager(mock_context)
        manager.validate_scan_folder_text()

        mock_yaml.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.QMessageBox")
    @patch("ClassicLib.Interface.controllers.folder_manager.yaml_settings")
    def test_validate_scan_folder_text_nonexistent_path(self, mock_yaml, mock_msgbox, mock_context):
        """Test validate_scan_folder_text shows warning for nonexistent path."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_context.ui_widgets.scan_folder_edit.text.return_value = "/nonexistent/path"

        manager = FolderManager(mock_context)
        manager.validate_scan_folder_text()

        mock_msgbox.warning.assert_called_once()
        mock_context.ui_widgets.scan_folder_edit.clear.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.is_valid_custom_scan_path")
    @patch("ClassicLib.Interface.controllers.folder_manager.yaml_settings")
    def test_validate_scan_folder_text_valid_path(self, mock_yaml, mock_valid, mock_context):
        """Test validate_scan_folder_text saves valid path."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_context.ui_widgets.scan_folder_edit.text.return_value = tmpdir
            mock_valid.return_value = True

            manager = FolderManager(mock_context)
            manager.validate_scan_folder_text()

            mock_yaml.assert_called_once()
            # Verify the path was resolved
            call_args = mock_yaml.call_args
            assert Path(tmpdir).resolve() == Path(call_args[0][3])

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.QMessageBox")
    @patch("ClassicLib.Interface.controllers.folder_manager.is_valid_custom_scan_path")
    @patch("ClassicLib.Interface.controllers.folder_manager.yaml_settings")
    def test_validate_scan_folder_text_restricted_path(self, mock_yaml, mock_valid, mock_msgbox, mock_context):
        """Test validate_scan_folder_text shows warning for restricted path."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_context.ui_widgets.scan_folder_edit.text.return_value = tmpdir
            mock_valid.return_value = False

            manager = FolderManager(mock_context)
            manager.validate_scan_folder_text()

            mock_msgbox.warning.assert_called_once()
            mock_context.ui_widgets.scan_folder_edit.clear.assert_called_once()

    @pytest.mark.unit
    def test_validate_scan_folder_text_no_edit_widget(self, mock_context):
        """Test validate_scan_folder_text handles missing edit widget."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_context.ui_widgets.scan_folder_edit = None

        manager = FolderManager(mock_context)
        # Should not raise
        manager.validate_scan_folder_text()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.classic_settings")
    def test_initialize_folder_paths_loads_settings(self, mock_settings, mock_context):
        """Test initialize_folder_paths loads paths from settings."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_settings.side_effect = lambda t, key: {
            "SCAN Custom Path": "/scan/path",
            "MODS Folder Path": "/mods/path",
        }.get(key)

        manager = FolderManager(mock_context)
        manager.initialize_folder_paths()

        mock_context.ui_widgets.scan_folder_edit.setText.assert_called_once_with("/scan/path")
        mock_context.ui_widgets.mods_folder_edit.setText.assert_called_once_with("/mods/path")

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.classic_settings")
    def test_initialize_folder_paths_empty_settings(self, mock_settings, mock_context):
        """Test initialize_folder_paths handles empty settings."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_settings.return_value = None

        manager = FolderManager(mock_context)
        manager.initialize_folder_paths()

        mock_context.ui_widgets.scan_folder_edit.setText.assert_not_called()
        mock_context.ui_widgets.mods_folder_edit.setText.assert_not_called()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.settings.dialog.SettingsDialog")
    def test_open_settings_creates_dialog(self, mock_dialog_class, mock_context):
        """Test open_settings creates and shows settings dialog."""
        from PySide6.QtWidgets import QDialog

        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
        mock_dialog_class.return_value = mock_dialog

        manager = FolderManager(mock_context)
        manager.open_settings()

        mock_dialog_class.assert_called_once_with(mock_context.main_window)
        mock_dialog.exec.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.settings.dialog.SettingsDialog")
    def test_open_settings_applies_changes_on_accept(self, mock_dialog_class, mock_context):
        """Test open_settings applies changes when accepted."""
        from PySide6.QtWidgets import QDialog

        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
        mock_dialog_class.return_value = mock_dialog

        manager = FolderManager(mock_context)
        manager.apply_settings_changes = MagicMock()

        manager.open_settings()

        manager.apply_settings_changes.assert_called_once()

    @pytest.mark.unit
    def test_apply_settings_changes_no_op(self, mock_context):
        """Test apply_settings_changes currently does nothing."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        manager = FolderManager(mock_context)
        # Should not raise
        manager.apply_settings_changes()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.QDesktopServices")
    def test_open_backup_folder_with_valid_local_dir(self, mock_desktop, mock_context):
        """Test open_backup_folder opens folder when local_dir exists."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_context.local_dir = tmpdir

            manager = FolderManager(mock_context)
            manager.open_backup_folder()

            mock_desktop.openUrl.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.QMessageBox")
    def test_open_backup_folder_missing_local_dir(self, mock_msgbox, mock_context):
        """Test open_backup_folder shows error when local_dir missing."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_context.local_dir = None

        manager = FolderManager(mock_context)
        manager.open_backup_folder()

        mock_msgbox.critical.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.QDesktopServices")
    def test_open_crash_logs_folder_creates_dir(self, mock_desktop, mock_context):
        """Test open_crash_logs_folder creates folder if missing."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_context.local_dir = tmpdir

            manager = FolderManager(mock_context)
            manager.open_crash_logs_folder()

            # Folder should be created
            assert (Path(tmpdir) / "Crash Logs").exists()
            mock_desktop.openUrl.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.folder_manager.QMessageBox")
    def test_open_crash_logs_folder_missing_local_dir(self, mock_msgbox, mock_context):
        """Test open_crash_logs_folder shows error when local_dir missing."""
        from ClassicLib.Interface.controllers.folder_manager import FolderManager

        mock_context.local_dir = None

        manager = FolderManager(mock_context)
        manager.open_crash_logs_folder()

        mock_msgbox.critical.assert_called_once()
