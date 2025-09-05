"""
Tests for backup creation and path generation.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.BackupManager import BackupManager


class TestBackupDirectoryCreation:
    """Tests for backup directory creation."""

    def test_create_backup_directory(self, manager: BackupManager, tmp_path: Path, monkeypatch) -> None:
        """Test creating versioned backup directory."""
        # Change to temp directory using monkeypatch
        monkeypatch.chdir(tmp_path)

        # Create backup directory
        backup_path = manager.create_backup_directory("0.6.23")

        # Verify directory was created
        expected_path = Path("CLASSIC Backup/Game Files/0.6.23")
        assert backup_path == expected_path
        assert backup_path.exists()
        assert backup_path.is_dir()

    @patch("ClassicLib.BackupManager.logger")
    def test_create_backup_directory_with_logging(
        self, mock_logger: MagicMock, manager: BackupManager, tmp_path: Path, monkeypatch
    ) -> None:
        """Test that creating backup directory logs debug message."""
        # Change to temp directory using monkeypatch
        monkeypatch.chdir(tmp_path)

        backup_path = manager.create_backup_directory("0.6.23")
        mock_logger.debug.assert_called_with(f"Created backup directory: {backup_path}")


class TestBackupFilesOperation:
    """Tests for backup file operations."""

    @patch("ClassicLib.Util.validate_path")
    @patch("shutil.copy2")
    def test_backup_files_success(
        self,
        mock_copy: MagicMock,
        mock_validate: MagicMock,
        manager: BackupManager,
        test_game_dir: Path,
        monkeypatch,
    ) -> None:
        """Test successful backup of files."""
        # Change to parent of test_game_dir
        monkeypatch.chdir(test_game_dir.parent)

        # Mock validation
        mock_validate.return_value = (True, "")

        # Perform backup
        backup_list = ["test.dll", "game.exe", "config.ini"]
        manager.backup_files(str(test_game_dir), backup_list, "0.6.23")

        # Verify copy was called for matching files
        assert mock_copy.call_count == 3

    @patch("ClassicLib.Util.validate_path")
    @patch("ClassicLib.BackupManager.logger")
    def test_backup_files_invalid_source(self, mock_logger: MagicMock, mock_validate: MagicMock, manager: BackupManager) -> None:
        """Test backup when source directory is invalid."""
        # Mock validation failure
        mock_validate.return_value = (False, "Directory doesn't exist")

        # Attempt backup
        manager.backup_files("/invalid/path", ["*.dll"], "0.6.23")

        # Verify warning was logged
        mock_logger.warning.assert_called_with("Cannot backup files - Directory doesn't exist")

    @patch("ClassicLib.Util.validate_path")
    @patch("shutil.copy2")
    @patch("ClassicLib.BackupManager.logger")
    def test_backup_files_skip_existing(
        self,
        mock_logger: MagicMock,
        mock_copy: MagicMock,
        mock_validate: MagicMock,
        manager: BackupManager,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        """Test that existing backup files are not overwritten."""
        # Change to temp directory using monkeypatch
        monkeypatch.chdir(tmp_path)

        source_dir = tmp_path / "Game"
        source_dir.mkdir()
        backup_dir = tmp_path / "CLASSIC Backup" / "Game Files" / "0.6.23"
        backup_dir.mkdir(parents=True)

        # Create source file and existing backup
        (source_dir / "test.dll").write_text("new content")
        (backup_dir / "test.dll").write_text("old backup")

        mock_validate.return_value = (True, "")

        # Perform backup
        manager.backup_files(str(source_dir), ["test.dll"], "0.6.23")

        # Verify copy was NOT called (file already exists)
        mock_copy.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
