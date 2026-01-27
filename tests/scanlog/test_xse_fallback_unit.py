"""Unit tests for ClassicLib.ScanGame.core.xse_fallback module.

This module provides comprehensive tests for the Python fallback implementation
of XSE plugin validation, including GameVersion enum, ValidationResult enum,
AddressLibInfo class, and XseChecker class.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from ClassicLib.scanning.game.core.xse_fallback import (
    AddressLibInfo,
    GameVersion,
    ValidationResult,
    XseChecker,
)

# =============================================================================
# GameVersion Enum Tests
# =============================================================================


@pytest.mark.unit
class TestGameVersionEnum:
    """Test GameVersion enumeration."""

    def test_game_version_null_value(self):
        """GameVersion.Null should have value 'Null'."""
        assert GameVersion.Null.value == "Null"

    def test_game_version_original_value(self):
        """GameVersion.Original should have value 'Original'."""
        assert GameVersion.Original.value == "Original"

    def test_game_version_nextgen_value(self):
        """GameVersion.NextGen should have value 'NextGen'."""
        assert GameVersion.NextGen.value == "NextGen"

    def test_game_version_vr_value(self):
        """GameVersion.Vr should have value 'Vr'."""
        assert GameVersion.Vr.value == "Vr"

    def test_game_version_has_all_expected_members(self):
        """GameVersion should have exactly 4 members."""
        expected_members = {"Null", "Original", "NextGen", "Vr"}
        actual_members = {member.name for member in GameVersion}
        assert actual_members == expected_members

    def test_game_version_members_are_enum_instances(self):
        """All GameVersion members should be GameVersion instances."""
        for member in GameVersion:
            assert isinstance(member, GameVersion)


# =============================================================================
# ValidationResult Enum Tests
# =============================================================================


@pytest.mark.unit
class TestValidationResultEnum:
    """Test ValidationResult enumeration."""

    def test_validation_result_correct_version_value(self):
        """ValidationResult.CorrectVersion should have value 'CorrectVersion'."""
        assert ValidationResult.CorrectVersion.value == "CorrectVersion"

    def test_validation_result_wrong_version_value(self):
        """ValidationResult.WrongVersion should have value 'WrongVersion'."""
        assert ValidationResult.WrongVersion.value == "WrongVersion"

    def test_validation_result_not_found_value(self):
        """ValidationResult.NotFound should have value 'NotFound'."""
        assert ValidationResult.NotFound.value == "NotFound"

    def test_validation_result_version_not_detected_value(self):
        """ValidationResult.VersionNotDetected should have value 'VersionNotDetected'."""
        assert ValidationResult.VersionNotDetected.value == "VersionNotDetected"

    def test_validation_result_plugins_path_not_found_value(self):
        """ValidationResult.PluginsPathNotFound should have value 'PluginsPathNotFound'."""
        assert ValidationResult.PluginsPathNotFound.value == "PluginsPathNotFound"

    def test_validation_result_has_all_expected_members(self):
        """ValidationResult should have exactly 5 members."""
        expected_members = {
            "CorrectVersion",
            "WrongVersion",
            "NotFound",
            "VersionNotDetected",
            "PluginsPathNotFound",
        }
        actual_members = {member.name for member in ValidationResult}
        assert actual_members == expected_members

    def test_validation_result_members_are_enum_instances(self):
        """All ValidationResult members should be ValidationResult instances."""
        for member in ValidationResult:
            assert isinstance(member, ValidationResult)


# =============================================================================
# AddressLibInfo Class Tests
# =============================================================================


@pytest.mark.unit
class TestAddressLibInfoInit:
    """Test AddressLibInfo initialization."""

    def test_init_sets_version(self):
        """AddressLibInfo should store version attribute correctly."""
        info = AddressLibInfo(
            version=GameVersion.Original,
            filename="test.bin",
            description="Test description",
            url="https://example.com",
        )
        assert info.version == GameVersion.Original

    def test_init_sets_filename(self):
        """AddressLibInfo should store filename attribute correctly."""
        info = AddressLibInfo(
            version=GameVersion.NextGen,
            filename="version-1-10-984-0.bin",
            description="Test",
            url="https://example.com",
        )
        assert info.filename == "version-1-10-984-0.bin"

    def test_init_sets_description(self):
        """AddressLibInfo should store description attribute correctly."""
        info = AddressLibInfo(
            version=GameVersion.Vr,
            filename="test.csv",
            description="VR Version Address Library",
            url="https://example.com",
        )
        assert info.description == "VR Version Address Library"

    def test_init_sets_url(self):
        """AddressLibInfo should store url attribute correctly."""
        info = AddressLibInfo(
            version=GameVersion.Original,
            filename="test.bin",
            description="Test",
            url="https://www.nexusmods.com/fallout4/mods/12345",
        )
        assert info.url == "https://www.nexusmods.com/fallout4/mods/12345"

    def test_init_with_all_attributes(self):
        """AddressLibInfo should correctly initialize all attributes together."""
        info = AddressLibInfo(
            version=GameVersion.NextGen,
            filename="version-1-10-984-0.bin",
            description="Non-VR (New Game) version",
            url="https://www.nexusmods.com/fallout4/mods/47327?tab=files",
        )
        assert info.version == GameVersion.NextGen
        assert info.filename == "version-1-10-984-0.bin"
        assert info.description == "Non-VR (New Game) version"
        assert info.url == "https://www.nexusmods.com/fallout4/mods/47327?tab=files"


@pytest.mark.unit
class TestAddressLibInfoVrFactory:
    """Test AddressLibInfo.vr() static factory method."""

    def test_vr_returns_address_lib_info_instance(self):
        """AddressLibInfo.vr() should return an AddressLibInfo instance."""
        info = AddressLibInfo.vr()
        assert isinstance(info, AddressLibInfo)

    def test_vr_has_correct_version(self):
        """AddressLibInfo.vr() should have GameVersion.Vr."""
        info = AddressLibInfo.vr()
        assert info.version == GameVersion.Vr

    def test_vr_has_correct_filename(self):
        """AddressLibInfo.vr() should have VR-specific filename."""
        info = AddressLibInfo.vr()
        assert info.filename == "version-1-2-72-0.csv"

    def test_vr_has_description(self):
        """AddressLibInfo.vr() should have a non-empty description."""
        info = AddressLibInfo.vr()
        assert info.description
        assert "VR" in info.description

    def test_vr_has_nexus_url(self):
        """AddressLibInfo.vr() should have a Nexus Mods URL."""
        info = AddressLibInfo.vr()
        assert "nexusmods.com" in info.url


@pytest.mark.unit
class TestAddressLibInfoOriginalFactory:
    """Test AddressLibInfo.original() static factory method."""

    def test_original_returns_address_lib_info_instance(self):
        """AddressLibInfo.original() should return an AddressLibInfo instance."""
        info = AddressLibInfo.original()
        assert isinstance(info, AddressLibInfo)

    def test_original_has_correct_version(self):
        """AddressLibInfo.original() should have GameVersion.Original."""
        info = AddressLibInfo.original()
        assert info.version == GameVersion.Original

    def test_original_has_correct_filename(self):
        """AddressLibInfo.original() should have original version filename."""
        info = AddressLibInfo.original()
        assert info.filename == "version-1-10-163-0.bin"

    def test_original_has_description(self):
        """AddressLibInfo.original() should have a non-empty description."""
        info = AddressLibInfo.original()
        assert info.description
        assert "Regular" in info.description or "Non-VR" in info.description

    def test_original_has_nexus_url(self):
        """AddressLibInfo.original() should have a Nexus Mods URL."""
        info = AddressLibInfo.original()
        assert "nexusmods.com" in info.url


@pytest.mark.unit
class TestAddressLibInfoNextGenFactory:
    """Test AddressLibInfo.next_gen() static factory method."""

    def test_next_gen_returns_address_lib_info_instance(self):
        """AddressLibInfo.next_gen() should return an AddressLibInfo instance."""
        info = AddressLibInfo.next_gen()
        assert isinstance(info, AddressLibInfo)

    def test_next_gen_has_correct_version(self):
        """AddressLibInfo.next_gen() should have GameVersion.NextGen."""
        info = AddressLibInfo.next_gen()
        assert info.version == GameVersion.NextGen

    def test_next_gen_has_correct_filename(self):
        """AddressLibInfo.next_gen() should have next-gen version filename."""
        info = AddressLibInfo.next_gen()
        assert info.filename == "version-1-10-984-0.bin"

    def test_next_gen_has_description(self):
        """AddressLibInfo.next_gen() should have a non-empty description."""
        info = AddressLibInfo.next_gen()
        assert info.description
        assert "New Game" in info.description or "Non-VR" in info.description

    def test_next_gen_has_nexus_url(self):
        """AddressLibInfo.next_gen() should have a Nexus Mods URL."""
        info = AddressLibInfo.next_gen()
        assert "nexusmods.com" in info.url


@pytest.mark.unit
class TestAddressLibInfoFactoryComparison:
    """Test that factory methods return distinct AddressLibInfo instances."""

    def test_factory_methods_return_different_versions(self):
        """Each factory method should return a different GameVersion."""
        vr = AddressLibInfo.vr()
        original = AddressLibInfo.original()
        next_gen = AddressLibInfo.next_gen()

        versions = {vr.version, original.version, next_gen.version}
        assert len(versions) == 3

    def test_factory_methods_return_different_filenames(self):
        """Each factory method should return a different filename."""
        vr = AddressLibInfo.vr()
        original = AddressLibInfo.original()
        next_gen = AddressLibInfo.next_gen()

        filenames = {vr.filename, original.filename, next_gen.filename}
        assert len(filenames) == 3


# =============================================================================
# XseChecker Class Tests
# =============================================================================


@pytest.mark.unit
class TestXseCheckerInit:
    """Test XseChecker initialization."""

    def test_init_sets_plugins_path(self, tmp_path: Path):
        """XseChecker should store plugins_path attribute correctly."""
        plugins_path = tmp_path / "Data" / "F4SE" / "Plugins"
        checker = XseChecker(plugins_path)
        assert checker.plugins_path == plugins_path

    def test_init_sets_is_vr_mode_default_false(self, tmp_path: Path):
        """XseChecker should default is_vr_mode to False."""
        checker = XseChecker(tmp_path)
        assert checker.is_vr_mode is False

    def test_init_sets_is_vr_mode_when_provided(self, tmp_path: Path):
        """XseChecker should store is_vr_mode when explicitly provided."""
        checker = XseChecker(tmp_path, is_vr_mode=True)
        assert checker.is_vr_mode is True

    def test_init_sets_game_version_default_original(self, tmp_path: Path):
        """XseChecker should default game_version to GameVersion.Original."""
        checker = XseChecker(tmp_path)
        assert checker.game_version == GameVersion.Original

    def test_init_sets_game_version_when_provided(self, tmp_path: Path):
        """XseChecker should store game_version when explicitly provided."""
        checker = XseChecker(tmp_path, game_version=GameVersion.NextGen)
        assert checker.game_version == GameVersion.NextGen

    def test_init_with_all_parameters(self, tmp_path: Path):
        """XseChecker should correctly initialize all attributes together."""
        plugins_path = tmp_path / "Plugins"
        checker = XseChecker(
            plugins_path=plugins_path,
            is_vr_mode=True,
            game_version=GameVersion.Vr,
        )
        assert checker.plugins_path == plugins_path
        assert checker.is_vr_mode is True
        assert checker.game_version == GameVersion.Vr


@pytest.mark.unit
class TestXseCheckerCheck:
    """Test XseChecker.check() static method."""

    def test_check_returns_correct_version_on_success(self):
        """XseChecker.check() should return CorrectVersion when correct version found."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "✔️ You have the correct version of the Address Library file!"
            result = XseChecker.check()
            assert result == ValidationResult.CorrectVersion

    def test_check_returns_wrong_version_on_mismatch(self):
        """XseChecker.check() should return WrongVersion when wrong version detected."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "❌ CAUTION: You have installed the wrong version of the Address Library file!"
            result = XseChecker.check()
            assert result == ValidationResult.WrongVersion

    def test_check_returns_not_found_when_library_missing(self):
        """XseChecker.check() should return NotFound when library not found."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "❓ NOTICE: Address Library file not found"
            result = XseChecker.check()
            assert result == ValidationResult.NotFound

    def test_check_returns_version_not_detected_when_unable_to_locate(self):
        """XseChecker.check() should return VersionNotDetected when unable to locate."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "❓ NOTICE : Unable to locate Address Library"
            result = XseChecker.check()
            assert result == ValidationResult.VersionNotDetected

    def test_check_returns_plugins_path_not_found_when_no_plugins_folder(self):
        """XseChecker.check() should return PluginsPathNotFound when plugins folder missing."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "❌ ERROR: Could not locate plugins folder path in settings"
            result = XseChecker.check()
            assert result == ValidationResult.PluginsPathNotFound

    def test_check_returns_version_not_detected_for_unexpected_message(self):
        """XseChecker.check() should return VersionNotDetected for unexpected messages."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "Some unexpected message format"
            result = XseChecker.check()
            assert result == ValidationResult.VersionNotDetected


@pytest.mark.unit
class TestXseCheckerValidate:
    """Test XseChecker.validate() static method."""

    def test_validate_returns_string(self):
        """XseChecker.validate() should return a string message."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "Test validation message"
            result = XseChecker.validate()
            assert isinstance(result, str)

    def test_validate_returns_message_from_check_xse_plugins(self):
        """XseChecker.validate() should return the message from check_xse_plugins()."""
        expected_message = "✔️ You have the correct version of the Address Library file!\n-----\n"
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = expected_message
            result = XseChecker.validate()
            assert result == expected_message

    def test_validate_calls_check_xse_plugins_once(self):
        """XseChecker.validate() should call check_xse_plugins exactly once."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "Test message"
            XseChecker.validate()
            mock_check.assert_called_once()


@pytest.mark.unit
class TestXseCheckerCheckMessageParsing:
    """Test XseChecker.check() message parsing edge cases."""

    def test_check_handles_correct_version_case_insensitive(self):
        """XseChecker.check() should handle 'correct version' case-insensitively."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "✔️ You have the CORRECT VERSION of the Address Library!"
            result = XseChecker.check()
            assert result == ValidationResult.CorrectVersion

    def test_check_handles_wrong_version_case_insensitive(self):
        """XseChecker.check() should handle 'wrong version' case-insensitively."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "You have the WRONG VERSION installed"
            result = XseChecker.check()
            assert result == ValidationResult.WrongVersion

    def test_check_handles_not_found_case_insensitive(self):
        """XseChecker.check() should handle 'not found' case-insensitively."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "Address Library NOT FOUND"
            result = XseChecker.check()
            assert result == ValidationResult.NotFound

    def test_check_handles_unable_to_locate_case_insensitive(self):
        """XseChecker.check() should handle 'unable to locate' case-insensitively."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "UNABLE TO LOCATE Address Library"
            result = XseChecker.check()
            assert result == ValidationResult.VersionNotDetected

    def test_check_handles_plugins_folder_path_case_insensitive(self):
        """XseChecker.check() should handle 'plugins folder path' case-insensitively."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "Could not find PLUGINS FOLDER PATH"
            result = XseChecker.check()
            assert result == ValidationResult.PluginsPathNotFound

    def test_check_handles_empty_message(self):
        """XseChecker.check() should handle empty message gracefully."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = ""
            result = XseChecker.check()
            assert result == ValidationResult.VersionNotDetected


@pytest.mark.unit
class TestXseCheckerIsStaticMethod:
    """Test that XseChecker methods are static."""

    def test_check_is_static_method(self):
        """XseChecker.check should be callable without an instance."""
        # Should be callable as a class method
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "✔️ correct version"
            # Call on class, not instance
            result = XseChecker.check()
            assert result == ValidationResult.CorrectVersion

    def test_validate_is_static_method(self):
        """XseChecker.validate should be callable without an instance."""
        with patch("ClassicLib.scanning.game.CheckXsePlugins.check_xse_plugins") as mock_check:
            mock_check.return_value = "Test message"
            # Call on class, not instance
            result = XseChecker.validate()
            assert isinstance(result, str)
