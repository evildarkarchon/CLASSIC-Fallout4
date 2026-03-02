"""Tests for the complete backup workflow and run operations."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.support.backup import BackupManager

pytestmark = [pytest.mark.unit]


class TestBackupWorkflow:
    """Tests for the complete backup workflow."""

    @patch.object(BackupManager, "load_backup_configuration")
    @patch.object(BackupManager, "extract_xse_version")
    @patch.object(BackupManager, "backup_files")
    def test_run_backup_success(
        self, mock_backup: MagicMock, mock_extract: MagicMock, mock_load: MagicMock, manager: BackupManager
    ) -> None:
        """Test successful execution of complete backup process."""
        # Setup configuration
        manager._backup_config = {"xse_log_file": "C:/xse.log", "game_path": "C:/Games/Fallout4", "backup_list": ["*.dll", "*.exe"]}

        # Mock version extraction
        mock_extract.return_value = "0.6.23"

        # Run backup
        manager.run_backup()

        # Verify methods were called
        mock_extract.assert_called_once_with("C:/xse.log")
        mock_backup.assert_called_once_with("C:/Games/Fallout4", ["*.dll", "*.exe"], "0.6.23")

    @patch.object(BackupManager, "load_backup_configuration")
    def test_run_backup_loads_config_if_missing(self, mock_load: MagicMock, manager: BackupManager) -> None:
        """Test that run_backup loads configuration if not present."""
        # Ensure no config
        assert not manager._backup_config

        # Set up minimal config after load
        def setup_config():
            manager._backup_config = {"xse_log_file": None}

        mock_load.side_effect = setup_config

        # Run backup
        manager.run_backup()

        # Verify configuration was loaded
        mock_load.assert_called_once()

    @patch("ClassicLib.support.backup.logger")
    def test_run_backup_no_xse_log_configured(self, mock_logger: MagicMock, manager: BackupManager) -> None:
        """Test run_backup when no XSE log file is configured."""
        manager._backup_config = {"xse_log_file": None}

        # Run backup
        manager.run_backup()

        # Verify warning was logged
        mock_logger.warning.assert_called_with("No XSE log file configured, skipping backup")

    @patch.object(BackupManager, "extract_xse_version")
    @patch("ClassicLib.support.backup.logger")
    def test_run_backup_no_xse_version(self, mock_logger: MagicMock, mock_extract: MagicMock, manager: BackupManager) -> None:
        """Test run_backup when no XSE version can be extracted."""
        manager._backup_config = {"xse_log_file": "C:/xse.log"}
        mock_extract.return_value = None

        # Run backup
        manager.run_backup()

        # Verify debug message was logged
        mock_logger.debug.assert_called_with("No XSE version found, skipping backup")

    @patch.object(BackupManager, "extract_xse_version")
    @patch("ClassicLib.support.backup.logger")
    def test_run_backup_missing_config(self, mock_logger: MagicMock, mock_extract: MagicMock, manager: BackupManager) -> None:
        """Test run_backup with missing game path or backup list."""
        manager._backup_config = {"xse_log_file": "C:/xse.log", "game_path": None, "backup_list": None}
        mock_extract.return_value = "0.6.23"

        # Run backup
        manager.run_backup()

        # Verify warning was logged
        mock_logger.warning.assert_called_with("Missing game path or backup list configuration")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
