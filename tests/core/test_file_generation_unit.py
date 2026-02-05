"""
Test suite for ClassicLib/FileGeneration.py file generation functionality.

This module contains tests for the FileGenerator class which manages
generation of CLASSIC configuration files.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]

from ClassicLib.core.constants import YAML
from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.file_gen import FileGenerator


class TestFileGenerator:
    """Tests for the FileGenerator class."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path, monkeypatch) -> None:
        """Set up test environment with complete isolation.

        We mock ResourceLoader.get_data_directory() to return a path within tmp_path
        so that file generation happens in isolation. This simulates the real behavior
        where files are created relative to project root (not CWD).
        """
        # Change to temp directory for isolation
        monkeypatch.chdir(tmp_path)
        self.tmp_path = tmp_path

        # Create CLASSIC Data directory in tmp_path (simulates project structure)
        self.mock_data_dir = tmp_path / "CLASSIC Data"
        self.mock_data_dir.mkdir(parents=True, exist_ok=True)

        # Mock ResourceLoader.get_data_directory to return our test directory
        monkeypatch.setattr(
            "ClassicLib.support.resources.ResourceLoader.get_data_directory",
            lambda: self.mock_data_dir,
        )

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_generate_ignore_file_creates_new_file(self, mock_yaml_settings: MagicMock) -> None:
        """Test generating CLASSIC Ignore.yaml when it doesn't exist."""
        # Mock yaml_settings to return default content
        expected_content = """# CLASSIC Ignore File
# Add patterns to ignore during scanning
*.tmp
*.log
"""
        mock_yaml_settings.return_value = expected_content

        # File will be created at project root (tmp_path, parent of mock_data_dir)
        ignore_path = self.tmp_path / "CLASSIC Ignore.yaml"
        assert not ignore_path.exists()

        # Generate the file
        FileGenerator.generate_ignore_file()

        # Verify file was created with correct content
        assert ignore_path.exists()
        assert ignore_path.read_text(encoding="utf-8") == expected_content

        # Verify yaml_settings was called correctly
        mock_yaml_settings.assert_called_once_with(str, YAML.Main, "CLASSIC_Info.default_ignorefile")

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_generate_ignore_file_skips_existing(self, mock_yaml_settings: MagicMock) -> None:
        """Test that existing CLASSIC Ignore.yaml is not overwritten."""
        # Create existing file at project root (tmp_path)
        ignore_path = self.tmp_path / "CLASSIC Ignore.yaml"
        existing_content = "# Existing ignore file\n*.existing"
        ignore_path.write_text(existing_content, encoding="utf-8")

        # Try to generate (should skip)
        FileGenerator.generate_ignore_file()

        # Verify file wasn't changed
        assert ignore_path.read_text(encoding="utf-8") == existing_content

        # Verify yaml_settings wasn't called
        mock_yaml_settings.assert_not_called()

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_generate_ignore_file_type_error(self, mock_yaml_settings: MagicMock) -> None:
        """Test that TypeError is raised when default content is not a string."""
        # Mock yaml_settings to return non-string
        mock_yaml_settings.return_value = {"invalid": "type"}

        # Should raise TypeError
        with pytest.raises(TypeError, match="Default ignore file content must be a string"):
            FileGenerator.generate_ignore_file()

    @patch("ClassicLib.io.yaml.yaml_settings")
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

        # Create test directory structure in temp path
        data_dir = self.tmp_path / "CLASSIC Data"
        data_dir.mkdir(parents=True, exist_ok=True)
        local_path = data_dir / "CLASSIC Fallout4 Local.yaml"

        # Ensure file doesn't exist
        assert not local_path.exists()

        # Generate the file (will use current working directory which is tmp_path)
        FileGenerator.generate_local_yaml()

        # Verify file was created with correct content
        assert local_path.exists()
        assert local_path.read_text(encoding="utf-8") == expected_content

        # Verify yaml_settings was called correctly
        mock_yaml_settings.assert_called_once_with(str, YAML.Main, "CLASSIC_Info.default_localyaml")

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="SkyrimSE")
    def test_generate_local_yaml_different_game(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test generating local YAML for different game."""
        expected_content = "# SkyrimSE Local Config"
        mock_yaml_settings.return_value = expected_content

        # Create test directory structure in tmp_path
        data_dir = self.tmp_path / "CLASSIC Data"
        data_dir.mkdir(parents=True, exist_ok=True)

        # Generate the file
        FileGenerator.generate_local_yaml()

        # Verify correct filename for SkyrimSE
        local_path = data_dir / "CLASSIC SkyrimSE Local.yaml"
        assert local_path.exists()
        assert local_path.read_text(encoding="utf-8") == expected_content

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_local_yaml_skips_existing(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test that existing local YAML is not overwritten."""
        # Create test directory and existing file
        data_dir = self.tmp_path / "CLASSIC Data"
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

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_local_yaml_type_error(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test that TypeError is raised when default content is not a string."""
        # Mock yaml_settings to return non-string
        mock_yaml_settings.return_value = 12345

        # Create test directory
        data_dir = self.tmp_path / "CLASSIC Data"
        data_dir.mkdir(parents=True, exist_ok=True)

        # Should raise TypeError
        with pytest.raises(TypeError, match="Default local YAML content must be a string"):
            FileGenerator.generate_local_yaml()

    @patch("ClassicLib.core.async_bridge.AsyncBridge.get_instance")
    @patch.object(FileGenerator, "generate_all_files_async")
    def test_generate_all_files(self, mock_generate_async: MagicMock, mock_bridge_get_instance: MagicMock) -> None:
        """Test that generate_all_files calls the async implementation."""
        from unittest.mock import AsyncMock

        # Create async mock that doesn't need to be called
        async_mock = AsyncMock()
        mock_generate_async.return_value = async_mock

        # Mock the bridge to handle the async call
        mock_bridge = MagicMock()
        mock_bridge_get_instance.return_value = mock_bridge

        # We need to close the coroutine returned by mock_generate_async
        # because our mock run_async won't actually run it
        def run_async_side_effect(coro):
            coro.close()
            return None

        mock_bridge.run_async.side_effect = run_async_side_effect

        FileGenerator.generate_all_files()

        # Verify the async method was called
        mock_generate_async.assert_called_once()
        mock_bridge.run_async.assert_called_once()

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.file_gen.logger")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_files_with_logging(self, mock_get_game: MagicMock, mock_logger: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test that file generation logs debug messages."""
        mock_yaml_settings.return_value = "test content"

        # Ensure logger.debug is a regular MagicMock, not an AsyncMock
        mock_logger.debug = MagicMock()

        # Generate ignore file
        FileGenerator.generate_ignore_file()

        # Generate local yaml
        FileGenerator.generate_local_yaml()

        # Verify debug logging was called
        assert mock_logger.debug.call_count == 2
        # The path in the log message is now an absolute path
        expected_ignore_path = self.tmp_path / "CLASSIC Ignore.yaml"
        mock_logger.debug.assert_any_call(f"Generated CLASSIC Ignore.yaml at {expected_ignore_path}")

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_local_yaml_creates_parent_directory(self, mock_get_game: MagicMock, mock_yaml_settings: MagicMock) -> None:
        """Test that parent directory is created if it doesn't exist."""
        import shutil

        mock_yaml_settings.return_value = "test content"

        # Remove the CLASSIC Data directory that was created in fixture setup
        # to test that generate_local_yaml creates it
        data_dir = self.mock_data_dir
        if data_dir.exists():
            shutil.rmtree(data_dir)
        assert not data_dir.exists()

        # Generate the file (should create parent directory)
        FileGenerator.generate_local_yaml()

        # Verify directory and file were created
        assert data_dir.exists()
        local_path = data_dir / "CLASSIC Fallout4 Local.yaml"
        assert local_path.exists()

    @patch("ClassicLib.io.yaml.yaml_settings", side_effect=Exception("YAML error"))
    def test_generate_ignore_file_yaml_error(self, mock_yaml_settings: MagicMock) -> None:
        """Test that exceptions from yaml_settings are propagated."""
        # Ensure the ignore file doesn't exist (so yaml_settings gets called)
        ignore_path = self.tmp_path / "CLASSIC Ignore.yaml"
        if ignore_path.exists():
            ignore_path.unlink()

        # Should raise the exception from yaml_settings
        with pytest.raises(Exception, match="YAML error"):
            FileGenerator.generate_ignore_file()

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_generate_ignore_file_unicode_content(self, mock_yaml_settings: MagicMock) -> None:
        """Test generating file with Unicode content."""
        # Mock yaml_settings to return Unicode content
        unicode_content = "# CLASSIC Ignore File\n# 日本語テスト\n*.tmp\n"
        mock_yaml_settings.return_value = unicode_content

        # Generate the file
        FileGenerator.generate_ignore_file()

        # Verify file was created with correct Unicode content at project root
        ignore_path = self.tmp_path / "CLASSIC Ignore.yaml"
        assert ignore_path.exists()
        assert ignore_path.read_text(encoding="utf-8") == unicode_content


@pytest.mark.asyncio
class TestFileGeneratorAsync:
    """Tests for the async methods of FileGenerator."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path, monkeypatch) -> None:
        """Set up test environment with complete isolation.

        We mock ResourceLoader.get_data_directory() to return a path within tmp_path
        so that file generation happens in isolation.
        """
        monkeypatch.chdir(tmp_path)
        self.tmp_path = tmp_path

        # Create CLASSIC Data directory in tmp_path (simulates project structure)
        self.mock_data_dir = tmp_path / "CLASSIC Data"
        self.mock_data_dir.mkdir(parents=True, exist_ok=True)

        # Mock ResourceLoader.get_data_directory to return our test directory
        monkeypatch.setattr(
            "ClassicLib.support.resources.ResourceLoader.get_data_directory",
            lambda: self.mock_data_dir,
        )

    async def test_generate_ignore_file_async_creates_new_file(self) -> None:
        """Test async generation of CLASSIC Ignore.yaml."""
        from unittest.mock import AsyncMock

        expected_content = "# Async Ignore File\n*.tmp"

        # Mock async yaml_settings
        mock_yaml_settings_async = AsyncMock(return_value=expected_content)
        # Mock file I/O core
        mock_io_core = MagicMock()
        mock_io_core.file_exists.return_value = False
        mock_io_core.write_file = AsyncMock()

        with (
            patch("ClassicLib.io.yaml.yaml_settings_async", mock_yaml_settings_async),
            patch("ClassicLib.integration.factory.get_file_io", return_value=mock_io_core),
        ):
            await FileGenerator.generate_ignore_file_async()

            mock_io_core.file_exists.assert_called_once()
            mock_yaml_settings_async.assert_called_once_with(str, YAML.Main, "CLASSIC_Info.default_ignorefile")
            mock_io_core.write_file.assert_called_once()

    async def test_generate_ignore_file_async_skips_existing(self) -> None:
        """Test that async generation skips existing file."""
        from unittest.mock import AsyncMock

        mock_io_core = MagicMock()
        mock_io_core.file_exists.return_value = True

        with patch("ClassicLib.integration.factory.get_file_io", return_value=mock_io_core):
            await FileGenerator.generate_ignore_file_async()

            mock_io_core.file_exists.assert_called_once()
            # write_file should not be called
            assert not hasattr(mock_io_core.write_file, "assert_not_called") or not mock_io_core.write_file.called

    async def test_generate_ignore_file_async_type_error(self) -> None:
        """Test async generation raises TypeError for non-string content."""
        from unittest.mock import AsyncMock

        mock_yaml_settings_async = AsyncMock(return_value={"invalid": "type"})
        mock_io_core = MagicMock()
        mock_io_core.file_exists.return_value = False

        with (
            patch("ClassicLib.io.yaml.yaml_settings_async", mock_yaml_settings_async),
            patch("ClassicLib.integration.factory.get_file_io", return_value=mock_io_core),
            pytest.raises(TypeError, match="Default ignore file content must be a string"),
        ):
            await FileGenerator.generate_ignore_file_async()

    async def test_generate_local_yaml_async_creates_new_file(self) -> None:
        """Test async generation of local YAML file."""
        from unittest.mock import AsyncMock

        expected_content = "# Async Local Config"

        mock_yaml_settings_async = AsyncMock(return_value=expected_content)
        mock_io_core = MagicMock()
        mock_io_core.file_exists.return_value = False
        mock_io_core.write_file = AsyncMock()

        # Create parent directory so mkdir doesn't fail
        data_dir = self.tmp_path / "CLASSIC Data"
        data_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch("ClassicLib.io.yaml.yaml_settings_async", mock_yaml_settings_async),
            patch("ClassicLib.integration.factory.get_file_io", return_value=mock_io_core),
            patch.object(GlobalRegistry, "get_game", return_value="Fallout4"),
        ):
            await FileGenerator.generate_local_yaml_async()

            mock_io_core.file_exists.assert_called_once()
            mock_yaml_settings_async.assert_called_once_with(str, YAML.Main, "CLASSIC_Info.default_localyaml")
            mock_io_core.write_file.assert_called_once()

    async def test_generate_local_yaml_async_type_error(self) -> None:
        """Test async local YAML raises TypeError for non-string content."""
        from unittest.mock import AsyncMock

        mock_yaml_settings_async = AsyncMock(return_value=12345)
        mock_io_core = MagicMock()
        mock_io_core.file_exists.return_value = False

        with (
            patch("ClassicLib.io.yaml.yaml_settings_async", mock_yaml_settings_async),
            patch("ClassicLib.integration.factory.get_file_io", return_value=mock_io_core),
            patch.object(GlobalRegistry, "get_game", return_value="Fallout4"),
            pytest.raises(TypeError, match="Default local YAML content must be a string"),
        ):
            await FileGenerator.generate_local_yaml_async()

    async def test_generate_all_files_async_success(self) -> None:
        """Test successful async generation of all files."""
        from unittest.mock import AsyncMock

        expected_content = "# Test Content"

        mock_yaml_settings_async = AsyncMock(return_value=expected_content)
        mock_io_core = MagicMock()
        mock_io_core.file_exists.return_value = False
        mock_io_core.write_file = AsyncMock()

        # Create parent directory
        data_dir = self.tmp_path / "CLASSIC Data"
        data_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch("ClassicLib.io.yaml.yaml_settings_async", mock_yaml_settings_async),
            patch("ClassicLib.integration.factory.get_file_io", return_value=mock_io_core),
            patch.object(GlobalRegistry, "get_game", return_value="Fallout4"),
        ):
            await FileGenerator.generate_all_files_async()

            # Both files should have been generated (2 yaml_settings calls, 2 write_file calls)
            assert mock_yaml_settings_async.call_count == 2
            assert mock_io_core.write_file.call_count == 2

    async def test_generate_all_files_async_type_error_handling(self) -> None:
        """Test that generate_all_files_async handles TypeError properly."""
        from unittest.mock import AsyncMock

        mock_yaml_settings_async = AsyncMock(return_value={"invalid": "type"})
        mock_io_core = MagicMock()
        mock_io_core.file_exists.return_value = False

        with (
            patch("ClassicLib.io.yaml.yaml_settings_async", mock_yaml_settings_async),
            patch("ClassicLib.integration.factory.get_file_io", return_value=mock_io_core),
            patch.object(GlobalRegistry, "get_game", return_value="Fallout4"),
            pytest.raises(ExceptionGroup),
        ):
            await FileGenerator.generate_all_files_async()

    async def test_generate_all_files_async_oserror_handling(self) -> None:
        """Test that generate_all_files_async handles OSError properly."""
        from unittest.mock import AsyncMock

        mock_yaml_settings_async = AsyncMock(return_value="content")
        mock_io_core = MagicMock()
        mock_io_core.file_exists.return_value = False
        mock_io_core.write_file = AsyncMock(side_effect=OSError("Disk full"))

        with (
            patch("ClassicLib.io.yaml.yaml_settings_async", mock_yaml_settings_async),
            patch("ClassicLib.integration.factory.get_file_io", return_value=mock_io_core),
            patch.object(GlobalRegistry, "get_game", return_value="Fallout4"),
            pytest.raises(ExceptionGroup),
        ):
            await FileGenerator.generate_all_files_async()
