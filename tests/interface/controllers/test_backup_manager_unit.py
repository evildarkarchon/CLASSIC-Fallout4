"""Unit tests for BackupManager controller.

This module tests the BackupManager class that handles backup, restore,
and removal operations for game files.

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


class TestBackupManager:
    """Tests for BackupManager class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.main_window = MagicMock()
        context.ui_widgets = MagicMock()
        return context

    @pytest.mark.unit
    def test_controller_creation(self, mock_context):
        """Test BackupManager can be created with proper initialization."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        manager = BackupManager(mock_context)

        assert manager is not None
        assert manager._ctx is mock_context
        assert manager._restore_buttons == {}

    @pytest.mark.unit
    def test_backup_types_constant(self, mock_context):
        """Test BACKUP_TYPES contains expected values."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        manager = BackupManager(mock_context)

        assert "XSE" in manager.BACKUP_TYPES
        assert "RESHADE" in manager.BACKUP_TYPES
        assert "VULKAN" in manager.BACKUP_TYPES
        assert "ENB" in manager.BACKUP_TYPES
        assert len(manager.BACKUP_TYPES) == 4

    @pytest.mark.unit
    def test_validate_selected_list_format_valid(self, mock_context):
        """Test _validate_selected_list_format with valid input."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        result = BackupManager._validate_selected_list_format("Backup XSE")

        assert result == ["Backup", "XSE"]

    @pytest.mark.unit
    def test_validate_selected_list_format_invalid_prefix(self, mock_context):
        """Test _validate_selected_list_format with invalid prefix."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        with pytest.raises(ValueError) as exc_info:
            BackupManager._validate_selected_list_format("Restore XSE")

        assert "Invalid format" in str(exc_info.value)

    @pytest.mark.unit
    def test_validate_selected_list_format_wrong_parts(self, mock_context):
        """Test _validate_selected_list_format with wrong number of parts."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        with pytest.raises(ValueError) as exc_info:
            BackupManager._validate_selected_list_format("Backup XSE Extra")

        assert "Invalid format" in str(exc_info.value)

    @pytest.mark.unit
    def test_validate_selected_list_format_single_word(self, mock_context):
        """Test _validate_selected_list_format with single word."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        with pytest.raises(ValueError) as exc_info:
            BackupManager._validate_selected_list_format("XSE")

        assert "Invalid format" in str(exc_info.value)

    @pytest.mark.unit
    def test_check_existing_backups_empty(self, mock_context):
        """Test check_existing_backups with no backup folders."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        manager = BackupManager(mock_context)

        # Patch Path to return non-existent paths
        with patch("ClassicLib.Interface.controllers.backup_manager.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.is_dir.return_value = False
            mock_path.return_value = mock_path_instance

            manager.check_existing_backups()

            # Nothing should crash
            assert manager._restore_buttons == {}

    @pytest.mark.unit
    def test_check_existing_backups_enables_restore(self, mock_context):
        """Test check_existing_backups enables restore button when backup exists."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        manager = BackupManager(mock_context)
        mock_button = MagicMock()
        manager._restore_buttons["XSE"] = mock_button

        # Patch Path to simulate existing backup with files
        with patch("ClassicLib.Interface.controllers.backup_manager.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.is_dir.return_value = True
            # Simulate directory has files
            mock_path_instance.iterdir.return_value = iter([MagicMock()])
            mock_path.return_value = mock_path_instance

            manager.check_existing_backups()

            mock_button.setEnabled.assert_called_once_with(True)

    @pytest.mark.unit
    def test_enable_restore_button_for_type(self, mock_context):
        """Test _enable_restore_button_for_type enables button."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        manager = BackupManager(mock_context)
        mock_button = MagicMock()
        manager._restore_buttons["XSE"] = mock_button

        manager._enable_restore_button_for_type("XSE")

        mock_button.setEnabled.assert_called_once_with(True)

    @pytest.mark.unit
    def test_enable_restore_button_for_type_missing(self, mock_context):
        """Test _enable_restore_button_for_type handles missing button."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        manager = BackupManager(mock_context)

        # Should not raise when button doesn't exist
        manager._enable_restore_button_for_type("NONEXISTENT")

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.backup_manager.manage_game_files")
    def test_classic_files_manage_backup(self, mock_manage, mock_context):
        """Test classic_files_manage performs backup operation."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        manager = BackupManager(mock_context)
        manager._enable_restore_button_for_type = MagicMock()

        manager.classic_files_manage("Backup XSE", "BACKUP")

        mock_manage.assert_called_once_with("Backup XSE", "BACKUP")
        manager._enable_restore_button_for_type.assert_called_once_with("XSE")

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.backup_manager.manage_game_files")
    def test_classic_files_manage_restore(self, mock_manage, mock_context):
        """Test classic_files_manage performs restore operation."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        manager = BackupManager(mock_context)

        manager.classic_files_manage("Backup ENB", "RESTORE")

        mock_manage.assert_called_once_with("Backup ENB", "RESTORE")

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.backup_manager.manage_game_files")
    def test_classic_files_manage_remove(self, mock_manage, mock_context):
        """Test classic_files_manage performs remove operation."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        manager = BackupManager(mock_context)

        manager.classic_files_manage("Backup VULKAN", "REMOVE")

        mock_manage.assert_called_once_with("Backup VULKAN", "REMOVE")

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.backup_manager.QMessageBox")
    @patch("ClassicLib.Interface.controllers.backup_manager.manage_game_files")
    def test_classic_files_manage_permission_error(self, mock_manage, mock_msgbox, mock_context):
        """Test classic_files_manage shows error on PermissionError."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        mock_manage.side_effect = PermissionError("Access denied")

        manager = BackupManager(mock_context)

        manager.classic_files_manage("Backup XSE", "BACKUP")

        mock_msgbox.critical.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.backup_manager.QMessageBox")
    def test_classic_files_manage_value_error(self, mock_msgbox, mock_context):
        """Test classic_files_manage shows warning on ValueError."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        manager = BackupManager(mock_context)

        manager.classic_files_manage("Invalid Format", "BACKUP")

        mock_msgbox.warning.assert_called_once()

    @pytest.mark.unit
    def test_open_backup_folder_static(self, mock_context):
        """Test open_backup_folder creates and opens folder."""
        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        # Patch both Path and os.startfile
        with patch("ClassicLib.Interface.controllers.backup_manager.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path.return_value = mock_path_instance

            with patch("os.startfile") as mock_startfile:
                BackupManager.open_backup_folder()

                # mkdir should be called
                mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)
                mock_startfile.assert_called_once()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.backup_manager.create_separator")
    def test_add_backup_section_creates_widgets(self, mock_separator, mock_context, qtbot):
        """Test add_backup_section creates all expected widgets."""
        from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

        from ClassicLib.Interface.controllers.backup_manager import BackupManager

        # Return a real QFrame for the separator
        separator_widget = QFrame()
        mock_separator.return_value = separator_widget

        manager = BackupManager(mock_context)

        parent_widget = QWidget()
        layout = QVBoxLayout(parent_widget)

        manager.add_backup_section(layout, "XSE Files", "XSE")

        # Verify restore button was stored
        assert "XSE" in manager._restore_buttons
        # Verify restore button starts disabled
        assert manager._restore_buttons["XSE"].isEnabled() is False
