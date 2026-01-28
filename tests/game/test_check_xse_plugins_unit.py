"""Unit tests for ClassicLib.scanning.game.check_xse_plugins module.

This module tests the XSE plugins checking functionality including Address Library
validation, version detection, and compatibility verification between VR and non-VR modes.

Following TDD methodology - tests written first to define expected behavior.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib.scanning.game.check_xse_plugins import (
    AddressLibVersionInfo,
    _determine_relevant_versions,
    _format_address_lib_not_found_message,
    _format_correct_address_lib_message,
    _format_game_version_not_detected_message,
    _format_plugins_path_not_found_message,
    _format_wrong_address_lib_message,
    _version_info_to_address_lib_info,
    check_xse_plugins,
    get_all_address_lib_info,
)

pytestmark = pytest.mark.unit


# ==============================================================================
# _format_game_version_not_detected_message Tests
# ==============================================================================


class TestFormatGameVersionNotDetectedMessage:
    """Tests for the _format_game_version_not_detected_message function."""

    @patch("ClassicLib.scanning.game.check_xse_plugins.get_version_registry")
    def test_returns_list_of_strings(self, mock_get_registry: MagicMock) -> None:
        """_format_game_version_not_detected_message should return a list of strings."""
        mock_og_info = MagicMock()
        mock_og_info.address_library.nexus_url = "https://nexusmods.com/og"
        mock_vr_info = MagicMock()
        mock_vr_info.address_library.nexus_url = "https://nexusmods.com/vr"

        mock_registry = MagicMock()
        mock_registry.get_by_short_name.side_effect = lambda name: mock_og_info if name == "OG" else mock_vr_info
        mock_get_registry.return_value = mock_registry

        result = _format_game_version_not_detected_message()

        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    @patch("ClassicLib.scanning.game.check_xse_plugins.get_version_registry")
    def test_contains_notice_message(self, mock_get_registry: MagicMock) -> None:
        """_format_game_version_not_detected_message should contain notice about Address Library."""
        mock_og_info = MagicMock()
        mock_og_info.address_library.nexus_url = "https://nexusmods.com/og"
        mock_vr_info = MagicMock()
        mock_vr_info.address_library.nexus_url = "https://nexusmods.com/vr"

        mock_registry = MagicMock()
        mock_registry.get_by_short_name.side_effect = lambda name: mock_og_info if name == "OG" else mock_vr_info
        mock_get_registry.return_value = mock_registry

        result = _format_game_version_not_detected_message()

        combined = "".join(result)
        assert "NOTICE" in combined
        assert "Address Library" in combined

    @patch("ClassicLib.scanning.game.check_xse_plugins.get_version_registry")
    def test_includes_nexus_urls(self, mock_get_registry: MagicMock) -> None:
        """_format_game_version_not_detected_message should include Nexus URLs for OG and VR."""
        mock_og_info = MagicMock()
        mock_og_info.address_library.nexus_url = "https://nexusmods.com/og"
        mock_vr_info = MagicMock()
        mock_vr_info.address_library.nexus_url = "https://nexusmods.com/vr"

        mock_registry = MagicMock()
        mock_registry.get_by_short_name.side_effect = lambda name: mock_og_info if name == "OG" else mock_vr_info
        mock_get_registry.return_value = mock_registry

        result = _format_game_version_not_detected_message()

        combined = "".join(result)
        assert "https://nexusmods.com/og" in combined
        assert "https://nexusmods.com/vr" in combined


# ==============================================================================
# _format_plugins_path_not_found_message Tests
# ==============================================================================


class TestFormatPluginsPathNotFoundMessage:
    """Tests for the _format_plugins_path_not_found_message function."""

    def test_returns_list_of_strings(self) -> None:
        """_format_plugins_path_not_found_message should return a list of strings."""
        result = _format_plugins_path_not_found_message()

        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_contains_error_message(self) -> None:
        """_format_plugins_path_not_found_message should contain error indicator."""
        result = _format_plugins_path_not_found_message()

        combined = "".join(result)
        assert "ERROR" in combined
        assert "plugins folder" in combined


# ==============================================================================
# _format_correct_address_lib_message Tests
# ==============================================================================


class TestFormatCorrectAddressLibMessage:
    """Tests for the _format_correct_address_lib_message function."""

    def test_returns_list_of_strings(self) -> None:
        """_format_correct_address_lib_message should return a list of strings."""
        result = _format_correct_address_lib_message()

        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_contains_success_message(self) -> None:
        """_format_correct_address_lib_message should contain success indicator."""
        result = _format_correct_address_lib_message()

        combined = "".join(result)
        assert "✔️" in combined
        assert "correct version" in combined


# ==============================================================================
# _format_wrong_address_lib_message Tests
# ==============================================================================


class TestFormatWrongAddressLibMessage:
    """Tests for the _format_wrong_address_lib_message function."""

    def test_returns_list_of_strings(self) -> None:
        """_format_wrong_address_lib_message should return a list of strings."""
        correct_version: AddressLibVersionInfo = {
            "version_const": Version("1.10.163.0"),
            "filename": "version-1-10-163-0.bin",
            "description": "Fallout 4 Original",
            "url": "https://nexusmods.com/fallout4/mods/47327",
        }

        result = _format_wrong_address_lib_message(correct_version)

        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_contains_caution_message(self) -> None:
        """_format_wrong_address_lib_message should contain caution indicator."""
        correct_version: AddressLibVersionInfo = {
            "version_const": Version("1.10.163.0"),
            "filename": "version-1-10-163-0.bin",
            "description": "Fallout 4 Original",
            "url": "https://nexusmods.com/fallout4/mods/47327",
        }

        result = _format_wrong_address_lib_message(correct_version)

        combined = "".join(result)
        assert "CAUTION" in combined
        assert "wrong version" in combined

    def test_includes_correct_version_info(self) -> None:
        """_format_wrong_address_lib_message should include correct version description and URL."""
        correct_version: AddressLibVersionInfo = {
            "version_const": Version("1.10.163.0"),
            "filename": "version-1-10-163-0.bin",
            "description": "Fallout 4 Original",
            "url": "https://nexusmods.com/fallout4/mods/47327",
        }

        result = _format_wrong_address_lib_message(correct_version)

        combined = "".join(result)
        assert "Fallout 4 Original" in combined
        assert "https://nexusmods.com/fallout4/mods/47327" in combined


# ==============================================================================
# _format_address_lib_not_found_message Tests
# ==============================================================================


class TestFormatAddressLibNotFoundMessage:
    """Tests for the _format_address_lib_not_found_message function."""

    def test_returns_list_of_strings(self) -> None:
        """_format_address_lib_not_found_message should return a list of strings."""
        correct_version: AddressLibVersionInfo = {
            "version_const": Version("1.10.163.0"),
            "filename": "version-1-10-163-0.bin",
            "description": "Fallout 4 Original",
            "url": "https://nexusmods.com/fallout4/mods/47327",
        }

        result = _format_address_lib_not_found_message(correct_version)

        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_contains_notice_message(self) -> None:
        """_format_address_lib_not_found_message should contain notice indicator."""
        correct_version: AddressLibVersionInfo = {
            "version_const": Version("1.10.163.0"),
            "filename": "version-1-10-163-0.bin",
            "description": "Fallout 4 Original",
            "url": "https://nexusmods.com/fallout4/mods/47327",
        }

        result = _format_address_lib_not_found_message(correct_version)

        combined = "".join(result)
        assert "NOTICE" in combined
        assert "not found" in combined

    def test_includes_install_instructions(self) -> None:
        """_format_address_lib_not_found_message should include install instructions."""
        correct_version: AddressLibVersionInfo = {
            "version_const": Version("1.10.163.0"),
            "filename": "version-1-10-163-0.bin",
            "description": "Fallout 4 Original",
            "url": "https://nexusmods.com/fallout4/mods/47327",
        }

        result = _format_address_lib_not_found_message(correct_version)

        combined = "".join(result)
        assert "Fallout 4 Original" in combined
        assert "https://nexusmods.com/fallout4/mods/47327" in combined


# ==============================================================================
# _version_info_to_address_lib_info Tests
# ==============================================================================


class TestVersionInfoToAddressLibInfo:
    """Tests for the _version_info_to_address_lib_info function."""

    def test_converts_version_info_correctly(self) -> None:
        """_version_info_to_address_lib_info should correctly convert VersionInfo."""
        mock_version_info = MagicMock()
        mock_version_info.version = Version("1.10.163.0")
        mock_version_info.display_name = "Fallout 4 Original"
        mock_version_info.description = "Pre-Next-Gen Update version"
        mock_version_info.address_library.filename = "version-1-10-163-0.bin"
        mock_version_info.address_library.nexus_url = "https://nexusmods.com/fallout4/mods/47327"

        result = _version_info_to_address_lib_info(mock_version_info)

        assert result["version_const"] == Version("1.10.163.0")
        assert result["filename"] == "version-1-10-163-0.bin"
        assert result["description"] == "Fallout 4 Original"
        assert result["url"] == "https://nexusmods.com/fallout4/mods/47327"

    def test_handles_missing_address_library(self) -> None:
        """_version_info_to_address_lib_info should handle None address_library."""
        mock_version_info = MagicMock()
        mock_version_info.version = Version("1.10.163.0")
        mock_version_info.display_name = None
        mock_version_info.description = "Test description"
        mock_version_info.address_library = None

        result = _version_info_to_address_lib_info(mock_version_info)

        assert result["version_const"] == Version("1.10.163.0")
        assert result["filename"] == ""
        assert result["description"] == "Test description"
        assert result["url"] == ""

    def test_uses_description_when_display_name_is_none(self) -> None:
        """_version_info_to_address_lib_info should fallback to description when display_name is None."""
        mock_version_info = MagicMock()
        mock_version_info.version = Version("1.10.163.0")
        mock_version_info.display_name = None
        mock_version_info.description = "Fallback description"
        mock_version_info.address_library.filename = "test.bin"
        mock_version_info.address_library.nexus_url = "https://example.com"

        result = _version_info_to_address_lib_info(mock_version_info)

        assert result["description"] == "Fallback description"


# ==============================================================================
# get_all_address_lib_info Tests
# ==============================================================================


class TestGetAllAddressLibInfo:
    """Tests for the get_all_address_lib_info function."""

    @patch("ClassicLib.scanning.game.check_xse_plugins.get_version_registry")
    def test_returns_dict(self, mock_get_registry: MagicMock) -> None:
        """get_all_address_lib_info should return a dictionary."""
        mock_version = MagicMock()
        mock_version.short_name = "OG"
        mock_version.version = Version("1.10.163.0")
        mock_version.display_name = "Fallout 4 Original"
        mock_version.description = "Test"
        mock_version.address_library.filename = "version.bin"
        mock_version.address_library.nexus_url = "https://example.com"

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = [mock_version]
        mock_get_registry.return_value = mock_registry

        result = get_all_address_lib_info()

        assert isinstance(result, dict)

    @patch("ClassicLib.scanning.game.check_xse_plugins.get_version_registry")
    def test_filters_versions_without_address_library(self, mock_get_registry: MagicMock) -> None:
        """get_all_address_lib_info should filter out versions without address_library."""
        mock_version_with = MagicMock()
        mock_version_with.short_name = "OG"
        mock_version_with.version = Version("1.10.163.0")
        mock_version_with.display_name = "Fallout 4 Original"
        mock_version_with.description = "Test"
        mock_version_with.address_library.filename = "version.bin"
        mock_version_with.address_library.nexus_url = "https://example.com"

        mock_version_without = MagicMock()
        mock_version_without.short_name = "NOLIB"
        mock_version_without.address_library = None

        mock_registry = MagicMock()
        mock_registry.get_all.return_value = [mock_version_with, mock_version_without]
        mock_get_registry.return_value = mock_registry

        result = get_all_address_lib_info()

        assert "OG" in result
        assert "NOLIB" not in result


# ==============================================================================
# _determine_relevant_versions Tests
# ==============================================================================


class TestDetermineRelevantVersions:
    """Tests for the _determine_relevant_versions function."""

    @patch("ClassicLib.scanning.game.check_xse_plugins.get_version_registry")
    def test_returns_tuple_of_two_lists(self, mock_get_registry: MagicMock) -> None:
        """_determine_relevant_versions should return tuple of two lists."""
        mock_correct = MagicMock()
        mock_correct.version = Version("1.10.163.0")
        mock_correct.display_name = "Correct"
        mock_correct.description = "Test"
        mock_correct.address_library.filename = "correct.bin"
        mock_correct.address_library.nexus_url = "https://example.com/correct"

        mock_wrong = MagicMock()
        mock_wrong.version = Version("1.2.72.0")
        mock_wrong.display_name = "Wrong"
        mock_wrong.description = "VR Test"
        mock_wrong.address_library.filename = "wrong.csv"
        mock_wrong.address_library.nexus_url = "https://example.com/wrong"

        mock_registry = MagicMock()
        mock_registry.get_correct_versions.return_value = [mock_correct]
        mock_registry.get_wrong_versions.return_value = [mock_wrong]
        mock_get_registry.return_value = mock_registry

        correct, wrong = _determine_relevant_versions(is_vr_mode=False)

        assert isinstance(correct, list)
        assert isinstance(wrong, list)

    @patch("ClassicLib.scanning.game.check_xse_plugins.get_version_registry")
    def test_calls_registry_with_vr_mode_parameter(self, mock_get_registry: MagicMock) -> None:
        """_determine_relevant_versions should call registry with is_vr_mode parameter."""
        mock_version = MagicMock()
        mock_version.version = Version("1.10.163.0")
        mock_version.display_name = "Fallout 4"
        mock_version.description = "Test"
        mock_version.address_library.filename = "version.bin"
        mock_version.address_library.nexus_url = "https://example.com"

        mock_registry = MagicMock()
        mock_registry.get_correct_versions.return_value = [mock_version]
        mock_registry.get_wrong_versions.return_value = []
        mock_get_registry.return_value = mock_registry

        correct, _ = _determine_relevant_versions(is_vr_mode=False)

        mock_registry.get_correct_versions.assert_called_once_with(False)
        assert len(correct) == 1

    @patch("ClassicLib.scanning.game.check_xse_plugins.get_version_registry")
    def test_filters_versions_without_address_library(self, mock_get_registry: MagicMock) -> None:
        """_determine_relevant_versions should filter out versions without address_library."""
        mock_with_lib = MagicMock()
        mock_with_lib.version = Version("1.10.163.0")
        mock_with_lib.display_name = "With Lib"
        mock_with_lib.description = "Test"
        mock_with_lib.address_library.filename = "with.bin"
        mock_with_lib.address_library.nexus_url = "https://example.com"

        mock_without_lib = MagicMock()
        mock_without_lib.address_library = None

        mock_registry = MagicMock()
        mock_registry.get_correct_versions.return_value = [mock_with_lib, mock_without_lib]
        mock_registry.get_wrong_versions.return_value = []
        mock_get_registry.return_value = mock_registry

        correct, _ = _determine_relevant_versions(is_vr_mode=False)

        assert len(correct) == 1


# ==============================================================================
# check_xse_plugins Tests
# ==============================================================================


class TestCheckXsePlugins:
    """Tests for the check_xse_plugins function."""

    @patch("ClassicLib.scanning.game.check_xse_plugins.classic_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.yaml_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.read_game_exe_version")
    @patch("ClassicLib.scanning.game.check_xse_plugins.get_vr", return_value="")
    def test_returns_string(
        self,
        mock_get_vr: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml_settings: MagicMock,
        mock_classic_settings: MagicMock,
    ) -> None:
        """check_xse_plugins should return a string."""
        mock_yaml_settings.return_value = None

        result = check_xse_plugins()

        assert isinstance(result, str)

    @patch("ClassicLib.scanning.game.check_xse_plugins.classic_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.yaml_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.read_game_exe_version")
    @patch("ClassicLib.scanning.game.check_xse_plugins.get_vr", return_value="")
    def test_returns_version_not_detected_when_exe_path_not_found(
        self,
        mock_get_vr: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml_settings: MagicMock,
        mock_classic_settings: MagicMock,
    ) -> None:
        """check_xse_plugins should return version not detected message when exe path is None."""
        mock_yaml_settings.return_value = None

        result = check_xse_plugins()

        assert "NOTICE" in result
        assert "Address Library" in result

    @patch("ClassicLib.scanning.game.check_xse_plugins.classic_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.yaml_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.read_game_exe_version")
    @patch("ClassicLib.scanning.game.check_xse_plugins.get_vr", return_value="")
    @patch("ClassicLib.scanning.game.check_xse_plugins.get_version_registry")
    def test_returns_version_not_detected_when_null_version(
        self,
        mock_get_registry: MagicMock,
        mock_get_vr: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml_settings: MagicMock,
        mock_classic_settings: MagicMock,
    ) -> None:
        """check_xse_plugins should return version not detected message when version is NULL."""
        from ClassicLib.core.constants import NULL_VERSION

        def yaml_side_effect(_type, _store, key_path, *_args):
            if "Game_File_EXE" in key_path:
                return "C:\\Game\\Fallout4.exe"
            return None

        mock_yaml_settings.side_effect = yaml_side_effect
        mock_get_version.return_value = NULL_VERSION

        # Setup mock registry for the format function
        mock_og_info = MagicMock()
        mock_og_info.address_library.nexus_url = "https://nexusmods.com/og"
        mock_vr_info = MagicMock()
        mock_vr_info.address_library.nexus_url = "https://nexusmods.com/vr"
        mock_registry = MagicMock()
        mock_registry.get_by_short_name.side_effect = lambda name: mock_og_info if name == "OG" else mock_vr_info
        mock_get_registry.return_value = mock_registry

        result = check_xse_plugins()

        assert "NOTICE" in result

    @patch("ClassicLib.scanning.game.check_xse_plugins.classic_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.yaml_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.read_game_exe_version")
    @patch("ClassicLib.scanning.game.check_xse_plugins.get_vr", return_value="")
    @patch("ClassicLib.scanning.game.check_xse_plugins.get_version_registry")
    def test_returns_plugins_path_not_found_when_plugins_path_none(
        self,
        mock_get_registry: MagicMock,
        mock_get_vr: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml_settings: MagicMock,
        mock_classic_settings: MagicMock,
    ) -> None:
        """check_xse_plugins should return plugins path error when plugins_path is None."""
        mock_get_version.return_value = Version("1.10.163.0")

        def yaml_side_effect(_type, _store, key_path, *_args):
            if "Game_File_EXE" in key_path:
                return "C:\\Game\\Fallout4.exe"
            if "Game_Folder_Plugins" in key_path:
                return None
            return None

        mock_yaml_settings.side_effect = yaml_side_effect

        result = check_xse_plugins()

        assert "ERROR" in result
        assert "plugins folder" in result

    @patch("ClassicLib.scanning.game.check_xse_plugins.classic_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.yaml_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.read_game_exe_version")
    @patch("ClassicLib.scanning.game.check_xse_plugins.get_vr", return_value="")
    @patch("ClassicLib.scanning.game.check_xse_plugins._determine_relevant_versions")
    def test_returns_correct_message_when_correct_version_exists(
        self,
        mock_determine: MagicMock,
        mock_get_vr: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml_settings: MagicMock,
        mock_classic_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """check_xse_plugins should return success when correct version file exists."""
        mock_get_version.return_value = Version("1.10.163.0")
        mock_classic_settings.return_value = False

        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()
        (plugins_path / "version-1-10-163-0.bin").touch()

        def yaml_side_effect(_type, _store, key_path, *_args):
            if "Game_File_EXE" in key_path:
                return str(tmp_path / "Fallout4.exe")
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml_settings.side_effect = yaml_side_effect

        correct_version: AddressLibVersionInfo = {
            "version_const": Version("1.10.163.0"),
            "filename": "version-1-10-163-0.bin",
            "description": "Fallout 4 Original",
            "url": "https://nexusmods.com/fallout4/mods/47327",
        }
        mock_determine.return_value = ([correct_version], [])

        result = check_xse_plugins()

        assert "✔️" in result
        assert "correct version" in result

    @patch("ClassicLib.scanning.game.check_xse_plugins.classic_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.yaml_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.read_game_exe_version")
    @patch("ClassicLib.scanning.game.check_xse_plugins.get_vr", return_value="")
    @patch("ClassicLib.scanning.game.check_xse_plugins._determine_relevant_versions")
    def test_returns_wrong_message_when_wrong_version_exists(
        self,
        mock_determine: MagicMock,
        mock_get_vr: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml_settings: MagicMock,
        mock_classic_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """check_xse_plugins should return wrong version warning when wrong file exists."""
        mock_get_version.return_value = Version("1.10.163.0")
        mock_classic_settings.return_value = False

        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()
        (plugins_path / "version-1-2-72-0.csv").touch()  # VR version file

        def yaml_side_effect(_type, _store, key_path, *_args):
            if "Game_File_EXE" in key_path:
                return str(tmp_path / "Fallout4.exe")
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml_settings.side_effect = yaml_side_effect

        correct_version: AddressLibVersionInfo = {
            "version_const": Version("1.10.163.0"),
            "filename": "version-1-10-163-0.bin",
            "description": "Fallout 4 Original",
            "url": "https://nexusmods.com/fallout4/mods/47327",
        }
        wrong_version: AddressLibVersionInfo = {
            "version_const": Version("1.2.72.0"),
            "filename": "version-1-2-72-0.csv",
            "description": "Fallout 4 VR",
            "url": "https://nexusmods.com/fallout4/mods/64879",
        }
        mock_determine.return_value = ([correct_version], [wrong_version])

        result = check_xse_plugins()

        assert "CAUTION" in result
        assert "wrong version" in result

    @patch("ClassicLib.scanning.game.check_xse_plugins.classic_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.yaml_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.read_game_exe_version")
    @patch("ClassicLib.scanning.game.check_xse_plugins.get_vr", return_value="")
    @patch("ClassicLib.scanning.game.check_xse_plugins._determine_relevant_versions")
    def test_returns_not_found_message_when_no_version_exists(
        self,
        mock_determine: MagicMock,
        mock_get_vr: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml_settings: MagicMock,
        mock_classic_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """check_xse_plugins should return not found when no Address Library file exists."""
        mock_get_version.return_value = Version("1.10.163.0")
        mock_classic_settings.return_value = False

        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()  # No Address Library files

        def yaml_side_effect(_type, _store, key_path, *_args):
            if "Game_File_EXE" in key_path:
                return str(tmp_path / "Fallout4.exe")
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml_settings.side_effect = yaml_side_effect

        correct_version: AddressLibVersionInfo = {
            "version_const": Version("1.10.163.0"),
            "filename": "version-1-10-163-0.bin",
            "description": "Fallout 4 Original",
            "url": "https://nexusmods.com/fallout4/mods/47327",
        }
        mock_determine.return_value = ([correct_version], [])

        result = check_xse_plugins()

        assert "NOTICE" in result
        assert "not found" in result
