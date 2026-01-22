"""
Unit tests for path_validator - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.PathValidator import PathValidator

pytestmark = pytest.mark.unit


class TestPathValidator:
    """Tests for the PathValidator class."""

    def test_is_valid_path_existing_string(self, tmp_path: Path) -> None:
        """Test is_valid_path with existing path as string."""
        test_dir = tmp_path / "test_directory"
        test_dir.mkdir()
        assert PathValidator.is_valid_path(str(test_dir)) is True

    def test_is_valid_path_existing_pathobj(self, tmp_path: Path) -> None:
        """Test is_valid_path with existing path as Path object."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("content")
        assert PathValidator.is_valid_path(test_file) is True

    def test_is_valid_path_nonexistent(self) -> None:
        """Test is_valid_path with non-existent path."""
        assert PathValidator.is_valid_path("/nonexistent/path/to/nowhere") is False

    def test_is_valid_path_invalid_string(self) -> None:
        """Test is_valid_path with invalid path string."""
        assert PathValidator.is_valid_path("") is False
        assert PathValidator.is_valid_path(":::invalid:::") is False

    def test_is_valid_path_none(self) -> None:
        """Test is_valid_path with None value."""
        assert PathValidator.is_valid_path(None) is False  # pyright: ignore[reportArgumentType]

    @patch("ClassicLib.ScanLog.Util.is_valid_custom_scan_path")
    @patch("ClassicLib.PathValidator._HAS_RUST_PATH", False)
    def test_is_restricted_path_unrestricted(self, mock_is_valid: MagicMock) -> None:
        """Test is_restricted_path with unrestricted path."""
        mock_is_valid.return_value = True
        assert PathValidator.is_restricted_path("C:/Users/Test/Documents") is False
        mock_is_valid.assert_called_once_with("C:/Users/Test/Documents")

    @patch("ClassicLib.ScanLog.Util.is_valid_custom_scan_path")
    @patch("ClassicLib.PathValidator._HAS_RUST_PATH", False)
    def test_is_restricted_path_restricted(self, mock_is_valid: MagicMock) -> None:
        """Test is_restricted_path with restricted path."""
        mock_is_valid.return_value = False
        assert PathValidator.is_restricted_path("C:/Windows/System32") is True

    @patch("ClassicLib.ScanLog.Util.is_valid_custom_scan_path", side_effect=Exception("Check failed"))
    @patch("ClassicLib.PathValidator._HAS_RUST_PATH", False)
    def test_is_restricted_path_exception(self, mock_is_valid: MagicMock) -> None:
        """Test is_restricted_path when exception occurs."""
        assert PathValidator.is_restricted_path("C:/SomePath") is True

    @patch("ClassicLib.ScanLog.Util.is_valid_custom_scan_path")
    @patch("ClassicLib.PathValidator._HAS_RUST_PATH", False)
    def test_is_restricted_path_with_pathobj(self, mock_is_valid: MagicMock) -> None:
        """Test is_restricted_path with Path object."""
        mock_is_valid.return_value = True
        test_path = Path("C:/Users/Test/Documents")
        assert PathValidator.is_restricted_path(test_path) is False
        # The implementation passes the Path object directly
        mock_is_valid.assert_called_once_with(test_path)

    @patch.object(PathValidator, "validate_custom_scan_path")
    @patch("ClassicLib.PathValidator.logger")
    def test_validate_all_settings_paths(
        self, mock_logger: MagicMock, mock_validate_custom: MagicMock, init_message_handler_fixture: MagicMock
    ) -> None:
        """Test validate_all_settings_paths calls all validation methods."""
        PathValidator.validate_all_settings_paths()
        mock_validate_custom.assert_called_once()
        mock_logger.debug.assert_any_call("Validating all settings paths")
        mock_logger.debug.assert_any_call("Path validation complete")

    @patch.object(PathValidator, "validate_custom_scan_path", side_effect=Exception("Validation failed"))
    @patch("ClassicLib.PathValidator.logger")
    def test_validate_all_settings_paths_exception(
        self, mock_logger: MagicMock, mock_validate_custom: MagicMock, init_message_handler_fixture: MagicMock
    ) -> None:
        """Test that exceptions in validate_all_settings_paths are propagated."""
        with pytest.raises(Exception, match="Validation failed"):
            PathValidator.validate_all_settings_paths()

    def test_is_valid_path_special_chars(self, tmp_path: Path) -> None:
        """Test is_valid_path with special characters in path."""
        special_dir = tmp_path / "Dir with Spaces & Chars"
        special_dir.mkdir()
        assert PathValidator.is_valid_path(special_dir) is True
        assert PathValidator.is_valid_path(str(special_dir)) is True

    @patch("ClassicLib.ScanLog.Util.is_valid_custom_scan_path")
    def test_is_restricted_path_empty_string(self, mock_is_valid: MagicMock) -> None:
        """Test is_restricted_path with empty string."""
        mock_is_valid.return_value = False
        assert PathValidator.is_restricted_path("") is True

    def test_is_restricted_path_none(self) -> None:
        """Test is_restricted_path with None value."""
        assert PathValidator.is_restricted_path(None) is True

    def test_is_restricted_path_whitespace(self) -> None:
        """Test is_restricted_path with whitespace-only string."""
        assert PathValidator.is_restricted_path("   ") is True


class TestPathValidatorValidation:
    """Tests for the path validation methods."""

    @patch("ClassicLib.YamlSettings.classic_settings")
    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.ScanLog.Util.is_valid_custom_scan_path")
    def test_validate_custom_scan_path_valid_path(
        self, mock_is_valid: MagicMock, mock_yaml: MagicMock, mock_classic: MagicMock, tmp_path: Path
    ) -> None:
        """Test validate_custom_scan_path with valid path."""
        # Create a valid directory
        valid_dir = tmp_path / "custom_scans"
        valid_dir.mkdir()

        mock_classic.return_value = str(valid_dir)
        mock_is_valid.return_value = True

        PathValidator.validate_custom_scan_path()

        # yaml_settings should not be called to clear the path
        mock_yaml.assert_not_called()

    @patch("ClassicLib.YamlSettings.classic_settings")
    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_validate_custom_scan_path_nonexistent(self, mock_warning: MagicMock, mock_yaml: MagicMock, mock_classic: MagicMock) -> None:
        """Test validate_custom_scan_path with non-existent path."""
        mock_classic.return_value = "/nonexistent/path"

        PathValidator.validate_custom_scan_path()

        # Should clear the setting
        mock_yaml.assert_called()
        mock_warning.assert_called()

    @patch("ClassicLib.YamlSettings.classic_settings")
    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.ScanLog.Util.is_valid_custom_scan_path")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_validate_custom_scan_path_restricted(
        self, mock_warning: MagicMock, mock_is_valid: MagicMock, mock_yaml: MagicMock, mock_classic: MagicMock, tmp_path: Path
    ) -> None:
        """Test validate_custom_scan_path with restricted path."""
        # Create a valid directory that is restricted
        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir()

        mock_classic.return_value = str(restricted_dir)
        mock_is_valid.return_value = False  # Mark as restricted

        PathValidator.validate_custom_scan_path()

        # Should clear the setting
        mock_yaml.assert_called()
        mock_warning.assert_called()

    @patch("ClassicLib.YamlSettings.classic_settings")
    def test_validate_custom_scan_path_empty(self, mock_classic: MagicMock) -> None:
        """Test validate_custom_scan_path with no path set."""
        mock_classic.return_value = None

        # Should not raise
        PathValidator.validate_custom_scan_path()

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.GlobalRegistry.get_vr")
    @patch("ClassicLib.GlobalRegistry.get_game")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_validate_game_root_path_valid(
        self, mock_warning: MagicMock, mock_game: MagicMock, mock_vr: MagicMock, mock_yaml: MagicMock, tmp_path: Path
    ) -> None:
        """Test validate_game_root_path with valid path and exe."""
        mock_vr.return_value = ""
        mock_game.return_value = "Fallout4"

        # Create directory with exe
        game_dir = tmp_path / "Fallout4"
        game_dir.mkdir()
        (game_dir / "Fallout4.exe").write_text("dummy exe")

        mock_yaml.return_value = game_dir

        PathValidator.validate_game_root_path()

        # msg_warning should not be called for valid path
        mock_warning.assert_not_called()

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.GlobalRegistry.get_vr")
    @patch("ClassicLib.GlobalRegistry.get_game")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_validate_game_root_path_missing_exe(
        self, mock_warning: MagicMock, mock_game: MagicMock, mock_vr: MagicMock, mock_yaml: MagicMock, tmp_path: Path
    ) -> None:
        """Test validate_game_root_path with missing exe."""
        mock_vr.return_value = ""
        mock_game.return_value = "Fallout4"

        # Create directory without exe
        game_dir = tmp_path / "Fallout4_NoExe"
        game_dir.mkdir()

        mock_yaml.return_value = game_dir

        PathValidator.validate_game_root_path()

        # Should warn about missing file
        mock_warning.assert_called()

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.GlobalRegistry.get_vr")
    @patch("ClassicLib.GlobalRegistry.get_game")
    def test_validate_game_root_path_none(self, mock_game: MagicMock, mock_vr: MagicMock, mock_yaml: MagicMock) -> None:
        """Test validate_game_root_path with no path set."""
        mock_vr.return_value = ""
        mock_game.return_value = "Fallout4"
        mock_yaml.return_value = None

        # Should not raise
        PathValidator.validate_game_root_path()

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.GlobalRegistry.get_vr")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_validate_documents_path_valid(self, mock_warning: MagicMock, mock_vr: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test validate_documents_path with valid path."""
        mock_vr.return_value = ""

        docs_dir = tmp_path / "My Games" / "Fallout4"
        docs_dir.mkdir(parents=True)

        mock_yaml.return_value = docs_dir

        PathValidator.validate_documents_path()

        mock_warning.assert_not_called()

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.GlobalRegistry.get_vr")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_validate_documents_path_nonexistent(self, mock_warning: MagicMock, mock_vr: MagicMock, mock_yaml: MagicMock) -> None:
        """Test validate_documents_path with non-existent path."""
        mock_vr.return_value = ""
        mock_yaml.return_value = Path("/nonexistent/docs")

        PathValidator.validate_documents_path()

        mock_warning.assert_called()

    @patch("ClassicLib.YamlSettings.classic_settings")
    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_validate_mods_folder_path_valid(
        self, mock_warning: MagicMock, mock_yaml: MagicMock, mock_classic: MagicMock, tmp_path: Path
    ) -> None:
        """Test validate_mods_folder_path with valid path."""
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()

        mock_classic.return_value = str(mods_dir)

        PathValidator.validate_mods_folder_path()

        mock_warning.assert_not_called()

    @patch("ClassicLib.YamlSettings.classic_settings")
    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_validate_mods_folder_path_nonexistent(self, mock_warning: MagicMock, mock_yaml: MagicMock, mock_classic: MagicMock) -> None:
        """Test validate_mods_folder_path with non-existent path."""
        mock_classic.return_value = "/nonexistent/mods"

        PathValidator.validate_mods_folder_path()

        mock_warning.assert_called()

    @patch("ClassicLib.YamlSettings.classic_settings")
    def test_validate_mods_folder_path_none(self, mock_classic: MagicMock) -> None:
        """Test validate_mods_folder_path with no path set."""
        mock_classic.return_value = None

        # Should not raise
        PathValidator.validate_mods_folder_path()

    @patch("ClassicLib.YamlSettings.classic_settings")
    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_validate_ini_folder_path_valid(
        self, mock_warning: MagicMock, mock_yaml: MagicMock, mock_classic: MagicMock, tmp_path: Path
    ) -> None:
        """Test validate_ini_folder_path with valid path."""
        ini_dir = tmp_path / "INI"
        ini_dir.mkdir()

        mock_classic.return_value = str(ini_dir)

        PathValidator.validate_ini_folder_path()

        mock_warning.assert_not_called()

    @patch("ClassicLib.YamlSettings.classic_settings")
    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_validate_ini_folder_path_is_file(
        self, mock_warning: MagicMock, mock_yaml: MagicMock, mock_classic: MagicMock, tmp_path: Path
    ) -> None:
        """Test validate_ini_folder_path when path is a file, not directory."""
        ini_file = tmp_path / "notadir.ini"
        ini_file.write_text("content")

        mock_classic.return_value = str(ini_file)

        PathValidator.validate_ini_folder_path()

        # Should warn since it's not a directory
        mock_warning.assert_called()


class TestValidatePathSetting:
    """Tests for _validate_path_setting helper method."""

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_validates_existing_directory(self, mock_warning: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test that valid directory path returns True."""
        from ClassicLib.Constants import YAML

        valid_dir = tmp_path / "valid_dir"
        valid_dir.mkdir()

        result = PathValidator._validate_path_setting(
            path=valid_dir,
            setting_name="test setting",
            yaml_type=YAML.Settings,
            setting_key="test.key",
        )

        assert result is True
        mock_warning.assert_not_called()

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_returns_false_for_nonexistent_path(self, mock_warning: MagicMock, mock_yaml: MagicMock) -> None:
        """Test that non-existent path returns False and clears setting."""
        from ClassicLib.Constants import YAML

        result = PathValidator._validate_path_setting(
            path="/nonexistent/path",
            setting_name="test setting",
            yaml_type=YAML.Settings,
            setting_key="test.key",
        )

        assert result is False
        mock_yaml.assert_called()
        mock_warning.assert_called()

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_returns_false_for_file_when_dir_expected(self, mock_warning: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test that file path returns False when directory expected."""
        from ClassicLib.Constants import YAML

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = PathValidator._validate_path_setting(
            path=test_file,
            setting_name="test setting",
            yaml_type=YAML.Settings,
            setting_key="test.key",
        )

        assert result is False
        mock_warning.assert_called()

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_checks_required_files(self, mock_warning: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test that missing required files returns False."""
        from ClassicLib.Constants import YAML

        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        result = PathValidator._validate_path_setting(
            path=test_dir,
            setting_name="test setting",
            yaml_type=YAML.Settings,
            setting_key="test.key",
            required_files=["required.txt", "also_needed.txt"],
        )

        assert result is False
        mock_warning.assert_called()

    @patch("ClassicLib.YamlSettings.yaml_settings")
    @patch("ClassicLib.PathValidator.msg_warning")
    def test_passes_with_required_files_present(self, mock_warning: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test that required files present returns True."""
        from ClassicLib.Constants import YAML

        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "required.txt").write_text("content")

        result = PathValidator._validate_path_setting(
            path=test_dir,
            setting_name="test setting",
            yaml_type=YAML.Settings,
            setting_key="test.key",
            required_files=["required.txt"],
        )

        assert result is True
        mock_warning.assert_not_called()

    def test_returns_false_for_none(self) -> None:
        """Test that None path returns False."""
        from ClassicLib.Constants import YAML

        result = PathValidator._validate_path_setting(
            path=None,
            setting_name="test setting",
            yaml_type=YAML.Settings,
            setting_key="test.key",
        )

        assert result is False

    def test_returns_false_for_empty_string(self) -> None:
        """Test that empty string path returns False."""
        from ClassicLib.Constants import YAML

        result = PathValidator._validate_path_setting(
            path="",
            setting_name="test setting",
            yaml_type=YAML.Settings,
            setting_key="test.key",
        )

        assert result is False
