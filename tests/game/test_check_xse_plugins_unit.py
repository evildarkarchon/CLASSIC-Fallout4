"""Unit tests for ClassicLib.scanning.game.check_xse_plugins module.

This module tests the XSE plugins checking functionality including Address Library
validation, version detection, and compatibility verification between VR and non-VR modes.

The actual validation is now delegated to Rust XseChecker; these tests verify
the Python glue layer (YAML resolution, version mapping, type conversion).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib.scanning.game.check_xse_plugins import (
    AddressLibVersionInfo,
    _version_info_to_address_lib_info,
    check_xse_plugins,
    get_all_address_lib_info,
)

pytestmark = pytest.mark.unit


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
# check_xse_plugins Tests (Rust delegation)
# ==============================================================================


class TestCheckXsePlugins:
    """Tests for the check_xse_plugins function.

    check_xse_plugins now delegates to Rust XseChecker for the actual validation.
    These tests verify the Python glue logic: YAML settings resolution, version
    detection, and the Rust call chain.
    """

    @patch("ClassicLib.scanning.game.check_xse_plugins.yaml_settings")
    def test_returns_error_when_no_plugins_or_exe(
        self,
        mock_yaml_settings: MagicMock,
    ) -> None:
        """check_xse_plugins should return error when neither plugins path nor exe exist."""
        mock_yaml_settings.return_value = None

        result = check_xse_plugins()

        assert isinstance(result, str)
        assert "ERROR" in result

    @patch("classic_scangame.XseChecker")
    @patch("classic_scangame.GameVersion")
    @patch("ClassicLib.scanning.game.check_xse_plugins.classic_settings")
    @patch("ClassicLib.scanning.game.check_xse_plugins.read_game_exe_version")
    @patch("ClassicLib.scanning.game.check_xse_plugins.yaml_settings")
    def test_delegates_to_rust_xse_checker(
        self,
        mock_yaml_settings: MagicMock,
        mock_read_version: MagicMock,
        mock_classic_settings: MagicMock,
        mock_game_version: MagicMock,
        mock_xse_checker: MagicMock,
        tmp_path: Path,
    ) -> None:
        """check_xse_plugins should delegate validation to Rust XseChecker."""
        plugins_path = tmp_path / "plugins"
        plugins_path.mkdir()

        def yaml_side_effect(_type, _store, key_path, *_args):  # noqa: ARG001
            if "Game_File_EXE" in key_path:
                return str(tmp_path / "Fallout4.exe")
            if "Game_Folder_Plugins" in key_path:
                return plugins_path
            return None

        mock_yaml_settings.side_effect = yaml_side_effect
        mock_read_version.return_value = Version("1.10.163.0")
        mock_classic_settings.return_value = False
        mock_game_version.Original = "Original"

        mock_checker_instance = MagicMock()
        mock_checker_instance.validate.return_value = "Validation OK"
        mock_xse_checker.return_value = mock_checker_instance

        result = check_xse_plugins()

        assert result == "Validation OK"
        mock_xse_checker.assert_called_once()
        mock_checker_instance.validate.assert_called_once()
