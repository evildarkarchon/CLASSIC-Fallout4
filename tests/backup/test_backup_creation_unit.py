"""
Unit tests for backup_creation - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.BackupManager import BackupManager

pytestmark = pytest.mark.unit


class TestBackupDirectoryCreation:
    """Tests for backup directory creation."""

    def test_create_backup_directory(self, manager: BackupManager, tmp_path: Path, monkeypatch) -> None:
        """Test creating versioned backup directory."""
        monkeypatch.chdir(tmp_path)
        backup_path = manager.create_backup_directory("0.6.23")
        expected_path = Path("CLASSIC Backup/Game Files/0.6.23")
        assert backup_path == expected_path
        assert backup_path.exists()
        assert backup_path.is_dir()

    @patch("ClassicLib.BackupManager.logger")
    def test_create_backup_directory_with_logging(
        self, mock_logger: MagicMock, manager: BackupManager, tmp_path: Path, monkeypatch
    ) -> None:
        """Test that creating backup directory logs debug message."""
        monkeypatch.chdir(tmp_path)
        backup_path = manager.create_backup_directory("0.6.23")
        mock_logger.debug.assert_called_with(f"Created backup directory: {backup_path}")


class TestBackupFilesOperation:
    """Tests for backup file operations."""

    @patch("ClassicLib.Utils.path_utils.validate_path")
    @patch("shutil.copy2")
    def test_backup_files_success(
        self, mock_copy: MagicMock, mock_validate: MagicMock, manager: BackupManager, test_game_dir: Path, monkeypatch
    ) -> None:
        """Test successful backup of files."""
        monkeypatch.chdir(test_game_dir.parent)
        mock_validate.return_value = (True, "")
        backup_list = ["test.dll", "game.exe", "config.ini"]
        manager.backup_files(str(test_game_dir), backup_list, "0.6.23")
        assert mock_copy.call_count == 3

    @patch("ClassicLib.Utils.path_utils.validate_path")
    @patch("ClassicLib.BackupManager.logger")
    def test_backup_files_invalid_source(self, mock_logger: MagicMock, mock_validate: MagicMock, manager: BackupManager) -> None:
        """Test backup when source directory is invalid."""
        mock_validate.return_value = (False, "Directory doesn't exist")
        manager.backup_files("/invalid/path", ["*.dll"], "0.6.23")
        mock_logger.warning.assert_called_with("Cannot backup files - Directory doesn't exist")
