"""
Test suite for ClassicLib/FileGeneration.py file generation functionality.

This module contains tests for the FileGenerator class which manages
generation of CLASSIC configuration files.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.FileGeneration import FileGenerator


class TestFileGenerator:
    """Tests for the FileGenerator class."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        """Set up test environment."""
        self.original_cwd = Path.cwd()
        # Change to temp directory for file operations
        import os

        os.chdir(tmp_path)

    def teardown_method(self) -> None:
        """Restore original working directory."""
        import os

        os.chdir(self.original_cwd)

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    def test_generate_ignore_file_creates_new_file(self, mock_yaml_settings: MagicMock) -> None:
        """Test generating CLASSIC Ignore.yaml when it doesn't exist."""
        # Mock yaml_settings to return default content
        expected_content = """# CLASSIC Ignore File
# Add patterns to ignore during scanning
*.tmp
*.log
"""
        mock_yaml_settings.return_value = expected_content

        # Ensure file doesn't exist
        ignore_path = Path("CLASSIC Ignore.yaml")
        assert not ignore_path.exists()

        # Generate the file
        FileGenerator.generate_ignore_file()

        # Verify file was created with correct content
        assert ignore_path.exists()
        assert ignore_path.read_text(encoding="utf-8") == expected_content

        # Verify yaml_settings was called correctly
        mock_yaml_settings.assert_called_once_with(str, YAML.Main, "CLASSIC_Info.default_ignorefile")

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    def test_generate_ignore_file_skips_existing(self, mock_yaml_settings: MagicMock) -> None:
        """Test that existing CLASSIC Ignore.yaml is not overwritten."""
        # Create existing file
        ignore_path = Path("CLASSIC Ignore.yaml")
        existing_content = "# Existing ignore file\n*.existing"
        ignore_path.write_text(existing_content, encoding="utf-8")

        # Try to generate (should skip)
        FileGenerator.generate_ignore_file()

        # Verify file wasn't changed
        assert ignore_path.read_text(encoding="utf-8") == existing_content

        # Verify yaml_settings wasn't called
        mock_yaml_settings.assert_not_called()

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    def test_generate_ignore_file_type_error(self, mock_yaml_settings: MagicMock) -> None:
        """Test that TypeError is raised when default content is not a string."""
        # Mock yaml_settings to return non-string
        mock_yaml_settings.return_value = {"invalid": "type"}

        # Should raise TypeError
        with pytest.raises(TypeError, match="Default ignore file content must be a string"):
            FileGenerator.generate_ignore_file()

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_local_yaml_creates_new_file(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test generating local YAML file when it doesn't exist."""
        # Mock yaml_settings to return default content
        expected_content = """# Local YAML Configuration
game_specific_setting: value
local_paths:
  - path1
  - path2
"""
        mock_yaml_settings.return_value = expected_content

        # Create CLASSIC Data directory
        data_dir = Path("CLASSIC Data")
        data_dir.mkdir(parents=True, exist_ok=True)

        # Ensure file doesn't exist
        local_path = data_dir / "CLASSIC Fallout4 Local.yaml"
        assert not local_path.exists()

        # Generate the file
        FileGenerator.generate_local_yaml()

        # Verify file was created with correct content
        assert local_path.exists()
        assert local_path.read_text(encoding="utf-8") == expected_content

        # Verify yaml_settings was called correctly
        mock_yaml_settings.assert_called_once_with(str, YAML.Main, "CLASSIC_Info.default_localyaml")

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="SkyrimSE")
    def test_generate_local_yaml_different_game(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test generating local YAML for different game."""
        expected_content = "# SkyrimSE Local Config"
        mock_yaml_settings.return_value = expected_content

        # Create CLASSIC Data directory
        data_dir = Path("CLASSIC Data")
        data_dir.mkdir(parents=True, exist_ok=True)

        # Generate the file
        FileGenerator.generate_local_yaml()

        # Verify correct filename for SkyrimSE
        local_path = data_dir / "CLASSIC SkyrimSE Local.yaml"
        assert local_path.exists()
        assert local_path.read_text(encoding="utf-8") == expected_content

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_local_yaml_skips_existing(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test that existing local YAML is not overwritten."""
        # Create CLASSIC Data directory and existing file
        data_dir = Path("CLASSIC Data")
        data_dir.mkdir(parents=True, exist_ok=True)
        local_path = data_dir / "CLASSIC Fallout4 Local.yaml"
        existing_content = "# Existing local config"
        local_path.write_text(existing_content, encoding="utf-8")

        # Try to generate (should skip)
        FileGenerator.generate_local_yaml()

        # Verify file wasn't changed
        assert local_path.read_text(encoding="utf-8") == existing_content

        # Verify yaml_settings wasn't called
        mock_yaml_settings.assert_not_called()

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_local_yaml_type_error(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test that TypeError is raised when default content is not a string."""
        # Mock yaml_settings to return non-string
        mock_yaml_settings.return_value = 12345

        # Create CLASSIC Data directory
        data_dir = Path("CLASSIC Data")
        data_dir.mkdir(parents=True, exist_ok=True)

        # Should raise TypeError
        with pytest.raises(TypeError, match="Default local YAML content must be a string"):
            FileGenerator.generate_local_yaml()

    @patch.object(FileGenerator, "generate_ignore_file")
    @patch.object(FileGenerator, "generate_local_yaml")
    def test_generate_all_files(self, mock_generate_local: MagicMock, mock_generate_ignore: MagicMock) -> None:
        """Test that generate_all_files calls both generation methods."""
        FileGenerator.generate_all_files()

        # Verify both methods were called
        mock_generate_ignore.assert_called_once()
        mock_generate_local.assert_called_once()

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch("ClassicLib.FileGeneration.logger")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_files_with_logging(self, mock_get_game: MagicMock, mock_logger: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test that file generation logs debug messages."""
        mock_yaml_settings.return_value = "test content"

        # Create CLASSIC Data directory
        data_dir = Path("CLASSIC Data")
        data_dir.mkdir(parents=True, exist_ok=True)

        # Generate ignore file
        FileGenerator.generate_ignore_file()

        # Generate local yaml
        FileGenerator.generate_local_yaml()

        # Verify debug logging was called
        assert mock_logger.debug.call_count == 2
        mock_logger.debug.assert_any_call("Generated CLASSIC Ignore.yaml at CLASSIC Ignore.yaml")

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_local_yaml_creates_parent_directory(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test that parent directory is created if it doesn't exist."""
        mock_yaml_settings.return_value = "test content"

        # Ensure CLASSIC Data directory doesn't exist
        data_dir = Path("CLASSIC Data")
        assert not data_dir.exists()

        # Generate the file (should create parent directory)
        FileGenerator.generate_local_yaml()

        # Verify directory and file were created
        assert data_dir.exists()
        local_path = data_dir / "CLASSIC Fallout4 Local.yaml"
        assert local_path.exists()

    @patch("ClassicLib.YamlSettingsCache.yaml_settings", side_effect=Exception("YAML error"))
    def test_generate_ignore_file_yaml_error(self, mock_yaml_settings: MagicMock) -> None:
        """Test that exceptions from yaml_settings are propagated."""
        # Should raise the exception from yaml_settings
        with pytest.raises(Exception, match="YAML error"):
            FileGenerator.generate_ignore_file()

    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    def test_generate_ignore_file_unicode_content(self, mock_yaml_settings: MagicMock) -> None:
        """Test generating file with Unicode content."""
        # Mock yaml_settings to return Unicode content
        unicode_content = "# CLASSIC Ignore File\n# 日本語テスト\n*.tmp\n"
        mock_yaml_settings.return_value = unicode_content

        # Generate the file
        FileGenerator.generate_ignore_file()

        # Verify file was created with correct Unicode content
        ignore_path = Path("CLASSIC Ignore.yaml")
        assert ignore_path.exists()
        assert ignore_path.read_text(encoding="utf-8") == unicode_content
