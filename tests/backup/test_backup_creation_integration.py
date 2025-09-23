"""
Integration tests for backup_creation - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.BackupManager import BackupManager

pytestmark = pytest.mark.integration

class TestBackupFilesOperation:
    """Tests for backup file operations."""

    @patch('ClassicLib.Util.validate_path')
    @patch('shutil.copy2')
    @patch('ClassicLib.BackupManager.logger')
    def test_backup_files_skip_existing(self, mock_logger: MagicMock, mock_copy: MagicMock, mock_validate: MagicMock, manager: BackupManager, tmp_path: Path, monkeypatch) -> None:
        """Test that existing backup files are not overwritten."""
        monkeypatch.chdir(tmp_path)
        source_dir = tmp_path / 'Game'
        source_dir.mkdir()
        backup_dir = tmp_path / 'CLASSIC Backup' / 'Game Files' / '0.6.23'
        backup_dir.mkdir(parents=True)
        (source_dir / 'test.dll').write_text('new content')
        (backup_dir / 'test.dll').write_text('old backup')
        mock_validate.return_value = (True, '')
        manager.backup_files(str(source_dir), ['test.dll'], '0.6.23')
        mock_copy.assert_not_called()
