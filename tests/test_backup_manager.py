"""
Test suite for ClassicLib/BackupManager.py backup management functionality.

This module contains tests for the BackupManager class which manages
automatic backup of game files.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.BackupManager import BackupManager
from ClassicLib.Constants import YAML


class TestBackupManager:
    """Tests for the BackupManager class."""

    @pytest.fixture
    def manager(self) -> BackupManager:
        """Create a BackupManager instance for testing."""
        return BackupManager()

    @pytest.fixture
    def mock_backup_config(self) -> dict[str, str | list[str]]:
        """Create mock backup configuration."""
        return {
            "backup_list": ["*.dll", "*.exe", "*.ini"],
            "game_path": "C:/Games/Fallout4",
            "xse_log_file": "C:/Documents/My Games/Fallout4/F4SE/f4se.log",
            "xse_ver_latest": "0.6.23",
        }

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_backup_configuration_success(self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager) -> None:
        """Test successful loading of backup configuration."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [
            ["*.dll", "*.exe", "*.ini"],  # backup_list
            "C:/Games/Fallout4",  # game_path
            "C:/Documents/F4SE/f4se.log",  # xse_log_file
            "0.6.23",  # xse_ver_latest
        ]

        # Load configuration
        manager.load_backup_configuration()

        # Verify configuration was loaded
        assert manager._backup_config["backup_list"] == ["*.dll", "*.exe", "*.ini"]
        assert manager._backup_config["game_path"] == "C:/Games/Fallout4"
        assert manager._backup_config["xse_log_file"] == "C:/Documents/F4SE/f4se.log"
        assert manager._backup_config["xse_ver_latest"] == "0.6.23"

        # Verify yaml_settings was called correctly
        assert mock_yaml_settings.call_count == 4

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="VR")
    def test_load_backup_configuration_vr_mode(self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager) -> None:
        """Test loading configuration in VR mode."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [["*.dll"], "C:/Games/Fallout4VR", "C:/Documents/F4SEVR/f4sevr.log", "0.1.2"]

        # Load configuration
        manager.load_backup_configuration()

        # Verify VR suffix was used in calls
        calls = mock_yaml_settings.call_args_list
        assert calls[1][0] == (str, YAML.Game_Local, "GameVR_Info.Root_Folder_Game")
        assert calls[2][0] == (str, YAML.Game_Local, "GameVR_Info.Docs_File_XSE")
        assert calls[3][0] == (str, YAML.Game, "GameVR_Info.XSE_Ver_Latest")

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_backup_configuration_type_error_list(
        self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager
    ) -> None:
        """Test TypeError when backup_list is not a list."""
        # Setup mock to return non-list for backup_list
        mock_yaml_settings.side_effect = [
            "not_a_list",  # Invalid type for backup_list
            "C:/Games/Fallout4",
            "C:/Documents/F4SE/f4se.log",
            "0.6.23",
        ]

        # Should raise TypeError
        with pytest.raises(TypeError, match="Backup list must be a list of strings"):
            manager.load_backup_configuration()

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_backup_configuration_type_error_xse_log(
        self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager
    ) -> None:
        """Test TypeError when xse_log_file is not a string."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [
            ["*.dll"],
            "C:/Games/Fallout4",
            123,  # Invalid type for xse_log_file
            "0.6.23",
        ]

        # Should raise TypeError
        with pytest.raises(TypeError, match="XSE log file path must be a string"):
            manager.load_backup_configuration()

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_backup_configuration_type_error_xse_version(
        self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, manager: BackupManager
    ) -> None:
        """Test TypeError when xse_ver_latest is not a string."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [
            ["*.dll"],
            "C:/Games/Fallout4",
            "C:/Documents/F4SE/f4se.log",
            None,  # Invalid type for xse_ver_latest
        ]

        # Should raise TypeError
        with pytest.raises(TypeError, match="Latest XSE version must be a string"):
            manager.load_backup_configuration()

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

    @patch("ClassicLib.Util.validate_path")
    @patch("shutil.copy2")
    def test_backup_files_success(
        self, mock_copy: MagicMock, mock_validate: MagicMock, manager: BackupManager, tmp_path: Path, monkeypatch
    ) -> None:
        """Test successful backup of files."""
        # Change to temp directory using monkeypatch
        monkeypatch.chdir(tmp_path)

        source_dir = tmp_path / "Game"
        source_dir.mkdir()

        # Create test files
        (source_dir / "test.dll").write_text("dll content")
        (source_dir / "game.exe").write_text("exe content")
        (source_dir / "config.ini").write_text("ini content")
        (source_dir / "readme.txt").write_text("txt content")

        # Mock validation
        mock_validate.return_value = (True, "")

        # Perform backup
        backup_list = ["test.dll", "game.exe", "config.ini"]
        manager.backup_files(str(source_dir), backup_list, "0.6.23")

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
        self, mock_logger: MagicMock, mock_copy: MagicMock, mock_validate: MagicMock, manager: BackupManager, tmp_path: Path, monkeypatch
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

    @patch("ClassicLib.BackupManager.logger")
    def test_run_backup_no_xse_log_configured(self, mock_logger: MagicMock, manager: BackupManager) -> None:
        """Test run_backup when no XSE log file is configured."""
        manager._backup_config = {"xse_log_file": None}

        # Run backup
        manager.run_backup()

        # Verify warning was logged
        mock_logger.warning.assert_called_with("No XSE log file configured, skipping backup")

    @patch.object(BackupManager, "extract_xse_version")
    @patch("ClassicLib.BackupManager.logger")
    def test_run_backup_no_xse_version(self, mock_logger: MagicMock, mock_extract: MagicMock, manager: BackupManager) -> None:
        """Test run_backup when no XSE version can be extracted."""
        manager._backup_config = {"xse_log_file": "C:/xse.log"}
        mock_extract.return_value = None

        # Run backup
        manager.run_backup()

        # Verify debug message was logged
        mock_logger.debug.assert_called_with("No XSE version found, skipping backup")

    @patch.object(BackupManager, "extract_xse_version")
    @patch("ClassicLib.BackupManager.logger")
    def test_run_backup_missing_config(self, mock_logger: MagicMock, mock_extract: MagicMock, manager: BackupManager) -> None:
        """Test run_backup with missing game path or backup list."""
        manager._backup_config = {"xse_log_file": "C:/xse.log", "game_path": None, "backup_list": None}
        mock_extract.return_value = "0.6.23"

        # Run backup
        manager.run_backup()

        # Verify warning was logged
        mock_logger.warning.assert_called_with("Missing game path or backup list configuration")

    @patch("ClassicLib.BackupManager.logger")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_load_backup_configuration_with_logging(
        self, mock_get_vr: MagicMock, mock_yaml_settings: MagicMock, mock_logger: MagicMock, manager: BackupManager
    ) -> None:
        """Test that load_backup_configuration logs debug message."""
        # Setup mock returns
        mock_yaml_settings.side_effect = [["*.dll"], "C:/Games", "C:/xse.log", "0.6.23"]

        # Load configuration
        manager.load_backup_configuration()

        # Verify debug logging
        mock_logger.debug.assert_called_with("Loaded backup configuration")
