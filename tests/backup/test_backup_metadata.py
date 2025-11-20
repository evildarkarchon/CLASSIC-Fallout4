"""Tests for backup metadata and versioning."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.BackupManager import BackupManager


class TestXSEVersionExtraction:
    """Tests for XSE version extraction from log files."""

    @patch("ClassicLib.BackupManager.open_file_with_encoding")
    @patch("ClassicLib.BackupManager.normalize_list")
    def test_extract_xse_version_success(self, mock_normalize: MagicMock, mock_open_file: MagicMock, manager: BackupManager) -> None:
        """Test successful extraction of XSE version from log file."""
        # Setup mock log content
        log_content = [
            "F4SE runtime: initialize (version = 0.6.21 010A08A0 01D969114D8F69AA, os = 6.2 (9200))\n",
            "imagebase = 00007FF614C70000\n",
            "reloc mgr imagebase = 00007FF614C70000\n",
        ]

        mock_file = MagicMock()
        mock_file.readlines.return_value = log_content
        mock_open_file.return_value.__enter__.return_value = mock_file

        # Normalize returns lowercase
        mock_normalize.return_value = [line.lower() for line in log_content]

        # Set config with default version
        manager._backup_config = {"xse_ver_latest": "0.6.23"}

        # Extract version
        version = manager.extract_xse_version("test.log")

        # Should extract version from log
        assert version == "0.6.21"

    @patch("ClassicLib.BackupManager.open_file_with_encoding", side_effect=FileNotFoundError)
    @patch("ClassicLib.BackupManager.logger")
    def test_extract_xse_version_file_not_found(self, mock_logger: MagicMock, mock_open: MagicMock, manager: BackupManager) -> None:
        """Test extracting version when log file doesn't exist."""
        manager._backup_config = {"xse_ver_latest": "0.6.23"}

        # Extract version
        version = manager.extract_xse_version("nonexistent.log")

        # Should return None
        assert version is None

        # Verify logging
        mock_logger.debug.assert_called_with("XSE log file not found: nonexistent.log")

    @patch("ClassicLib.BackupManager.open_file_with_encoding")
    @patch("ClassicLib.BackupManager.normalize_list")
    def test_extract_xse_version_no_version_in_log(
        self, mock_normalize: MagicMock, mock_open_file: MagicMock, manager: BackupManager
    ) -> None:
        """Test extracting version when log doesn't contain version info."""
        # Setup mock log content without version
        log_content = ["some other log line\n", "no version here\n"]

        mock_file = MagicMock()
        mock_file.readlines.return_value = log_content
        mock_open_file.return_value.__enter__.return_value = mock_file
        mock_normalize.return_value = [line.lower() for line in log_content]

        manager._backup_config = {"xse_ver_latest": "0.6.23"}

        # Extract version
        version = manager.extract_xse_version("test.log")

        # Should return default version
        assert version == "0.6.23"

    @patch("ClassicLib.BackupManager.open_file_with_encoding")
    @patch("ClassicLib.BackupManager.normalize_list")
    def test_extract_xse_version_empty_log(self, mock_normalize: MagicMock, mock_open_file: MagicMock, manager: BackupManager) -> None:
        """Test extracting version from empty log file."""
        mock_file = MagicMock()
        mock_file.readlines.return_value = []
        mock_open_file.return_value.__enter__.return_value = mock_file
        mock_normalize.return_value = []

        manager._backup_config = {}

        # Extract version
        version = manager.extract_xse_version("test.log")

        # Should return None for empty log
        assert version is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
