"""Integration tests for classic-constants Rust module.

Tests the Rust-accelerated constants module, including version constants,
YAML file enumeration, game identifiers, and settings validation.
"""

import pytest

classic_constants = pytest.importorskip("classic_constants", reason="Rust classic_constants module not available")


@pytest.mark.rust
@pytest.mark.unit
class TestVersionConstants:
    """Test version constant values."""

    def test_null_version_exists(self):
        """Test NULL_VERSION constant is defined."""
        assert hasattr(classic_constants, "NULL_VERSION")
        assert isinstance(classic_constants.NULL_VERSION, str)
        assert classic_constants.NULL_VERSION == "0.0.0"

    def test_fallout4_versions(self):
        """Test Fallout 4 version constants."""
        # Individual version constants
        assert hasattr(classic_constants, "FALLOUT4_OG_VERSION")
        assert hasattr(classic_constants, "FALLOUT4_NG_VERSION")
        assert hasattr(classic_constants, "FALLOUT4_VR_VERSION")

        # All should be non-empty strings
        assert isinstance(classic_constants.FALLOUT4_OG_VERSION, str)
        assert isinstance(classic_constants.FALLOUT4_NG_VERSION, str)
        assert isinstance(classic_constants.FALLOUT4_VR_VERSION, str)

        assert len(classic_constants.FALLOUT4_OG_VERSION) > 0
        assert len(classic_constants.FALLOUT4_NG_VERSION) > 0
        assert len(classic_constants.FALLOUT4_VR_VERSION) > 0

    def test_f4se_versions(self):
        """Test F4SE version constants."""
        # Individual version constants
        assert hasattr(classic_constants, "F4SE_OG_VERSION")
        assert hasattr(classic_constants, "F4SE_NG_VERSION")

        # All should be non-empty strings
        assert isinstance(classic_constants.F4SE_OG_VERSION, str)
        assert isinstance(classic_constants.F4SE_NG_VERSION, str)

        assert len(classic_constants.F4SE_OG_VERSION) > 0
        assert len(classic_constants.F4SE_NG_VERSION) > 0

    def test_fallout4_versions_array(self):
        """Test FALLOUT4_VERSIONS array contains OG and NG versions."""
        versions = classic_constants.FALLOUT4_VERSIONS
        assert isinstance(versions, list)
        assert len(versions) == 3
        assert classic_constants.FALLOUT4_OG_VERSION in versions
        assert classic_constants.FALLOUT4_NG_VERSION in versions
        # Note: VR version exists separately but is not in FALLOUT4_VERSIONS array

    def test_f4se_versions_array(self):
        """Test F4SE_VERSIONS array contains all versions."""
        versions = classic_constants.F4SE_VERSIONS
        assert isinstance(versions, list)
        assert len(versions) == 3
        assert classic_constants.F4SE_OG_VERSION in versions
        assert classic_constants.F4SE_NG_VERSION in versions


@pytest.mark.rust
@pytest.mark.unit
class TestYamlFileEnum:
    """Test YamlFile enumeration."""

    def test_yaml_file_variants_exist(self):
        """Test all YamlFile variants are accessible."""
        assert hasattr(classic_constants.YamlFile, "Main")
        assert hasattr(classic_constants.YamlFile, "Settings")
        assert hasattr(classic_constants.YamlFile, "Ignore")
        assert hasattr(classic_constants.YamlFile, "Game")
        assert hasattr(classic_constants.YamlFile, "GameLocal")
        assert hasattr(classic_constants.YamlFile, "Test")
        assert hasattr(classic_constants.YamlFile, "Cache")

    def test_yaml_file_as_str(self):
        """Test YamlFile.as_str() returns correct strings."""
        assert classic_constants.YamlFile.Main.as_str() == "Main"
        assert classic_constants.YamlFile.Settings.as_str() == "Settings"
        assert classic_constants.YamlFile.Ignore.as_str() == "Ignore"
        assert classic_constants.YamlFile.Game.as_str() == "Game"
        assert classic_constants.YamlFile.GameLocal.as_str() == "GameLocal"
        assert classic_constants.YamlFile.Test.as_str() == "Test"
        assert classic_constants.YamlFile.Cache.as_str() == "Cache"

    def test_yaml_file_description(self):
        """Test YamlFile.description() returns meaningful descriptions."""
        # Check that descriptions are non-empty and contain file references
        assert "Main.yaml" in classic_constants.YamlFile.Main.description()
        assert "Settings.yaml" in classic_constants.YamlFile.Settings.description()
        assert "Ignore.yaml" in classic_constants.YamlFile.Ignore.description()

    def test_yaml_file_str(self):
        """Test YamlFile.__str__() returns variant name."""
        assert str(classic_constants.YamlFile.Main) == "Main"
        assert str(classic_constants.YamlFile.Settings) == "Settings"

    def test_yaml_file_repr(self):
        """Test YamlFile.__repr__() includes variant information."""
        repr_str = repr(classic_constants.YamlFile.Main)
        assert isinstance(repr_str, str)
        assert len(repr_str) > 0

    def test_yaml_file_equality(self):
        """Test YamlFile equality comparison."""
        # Same variants should be equal
        assert classic_constants.YamlFile.Main == classic_constants.YamlFile.Main
        assert classic_constants.YamlFile.Settings == classic_constants.YamlFile.Settings

        # Different variants should not be equal
        assert classic_constants.YamlFile.Main != classic_constants.YamlFile.Settings
        assert classic_constants.YamlFile.Ignore != classic_constants.YamlFile.Game

    def test_yaml_file_hashing(self):
        """Test YamlFile can be used in sets and dicts."""
        # Should be hashable
        yaml_set = {classic_constants.YamlFile.Main, classic_constants.YamlFile.Settings}
        assert len(yaml_set) == 2

        # Should work as dict keys
        yaml_dict = {
            classic_constants.YamlFile.Main: "main_value",
            classic_constants.YamlFile.Settings: "settings_value",
        }
        assert yaml_dict[classic_constants.YamlFile.Main] == "main_value"
        assert yaml_dict[classic_constants.YamlFile.Settings] == "settings_value"


@pytest.mark.rust
@pytest.mark.unit
class TestGameIdEnum:
    """Test GameId enumeration."""

    def test_game_id_variants_exist(self):
        """Test all GameId variants are accessible."""
        assert hasattr(classic_constants.GameId, "Fallout4")
        assert hasattr(classic_constants.GameId, "Fallout4VR")
        assert hasattr(classic_constants.GameId, "Skyrim")
        assert hasattr(classic_constants.GameId, "Starfield")

    def test_game_id_as_str(self):
        """Test GameId.as_str() returns correct game names."""
        assert classic_constants.GameId.Fallout4.as_str() == "Fallout4"
        assert classic_constants.GameId.Fallout4VR.as_str() == "Fallout4VR"
        assert classic_constants.GameId.Skyrim.as_str() == "Skyrim"
        assert classic_constants.GameId.Starfield.as_str() == "Starfield"

    def test_game_id_exe_name(self):
        """Test GameId.exe_name() returns correct executable names."""
        assert classic_constants.GameId.Fallout4.exe_name() == "Fallout4.exe"
        assert classic_constants.GameId.Fallout4VR.exe_name() == "Fallout4VR.exe"
        assert classic_constants.GameId.Skyrim.exe_name() == "SkyrimSE.exe"
        assert classic_constants.GameId.Starfield.exe_name() == "Starfield.exe"

    def test_game_id_is_vr(self):
        """Test GameId.is_vr() correctly identifies VR games."""
        # Fallout4VR should be VR
        assert classic_constants.GameId.Fallout4VR.is_vr() is True

        # Others should not be VR
        assert classic_constants.GameId.Fallout4.is_vr() is False
        assert classic_constants.GameId.Skyrim.is_vr() is False
        assert classic_constants.GameId.Starfield.is_vr() is False

    def test_game_id_str(self):
        """Test GameId.__str__() returns game name."""
        assert str(classic_constants.GameId.Fallout4) == "Fallout4"
        assert str(classic_constants.GameId.Fallout4VR) == "Fallout4VR"

    def test_game_id_repr(self):
        """Test GameId.__repr__() includes game information."""
        repr_str = repr(classic_constants.GameId.Fallout4)
        assert isinstance(repr_str, str)
        assert len(repr_str) > 0

    def test_game_id_equality(self):
        """Test GameId equality comparison."""
        # Same variants should be equal
        assert classic_constants.GameId.Fallout4 == classic_constants.GameId.Fallout4
        assert classic_constants.GameId.Skyrim == classic_constants.GameId.Skyrim

        # Different variants should not be equal
        assert classic_constants.GameId.Fallout4 != classic_constants.GameId.Fallout4VR
        assert classic_constants.GameId.Skyrim != classic_constants.GameId.Starfield

    def test_game_id_hashing(self):
        """Test GameId can be used in sets and dicts."""
        # Should be hashable
        game_set = {classic_constants.GameId.Fallout4, classic_constants.GameId.Skyrim}
        assert len(game_set) == 2

        # Should work as dict keys
        game_dict = {
            classic_constants.GameId.Fallout4: "fo4_data",
            classic_constants.GameId.Skyrim: "skyrim_data",
        }
        assert game_dict[classic_constants.GameId.Fallout4] == "fo4_data"
        assert game_dict[classic_constants.GameId.Skyrim] == "skyrim_data"


@pytest.mark.rust
@pytest.mark.unit
class TestSettingsValidation:
    """Test settings validation functions."""

    def test_must_not_be_none_function_exists(self):
        """Test must_not_be_none() function is available."""
        assert hasattr(classic_constants, "must_not_be_none")
        assert callable(classic_constants.must_not_be_none)

    def test_must_not_be_none_required_keys(self):
        """Test must_not_be_none() returns True for required settings keys."""
        # Keys that should not be None (from SETTINGS_IGNORE_NONE)
        required_keys = [
            "SCAN Custom Path",
            "Root_Folder_Game",
            "Root_Folder_Docs",
            "MODS Folder Path",
            "INI Folder Path",
        ]

        for key in required_keys:
            assert classic_constants.must_not_be_none(key) is True, f"{key} should be required"

    def test_must_not_be_none_optional_keys(self):
        """Test must_not_be_none() returns False for optional settings keys."""
        # Keys that can be None
        optional_keys = [
            "Some Random Setting",
            "Non Existent Key",
            "",
        ]

        for key in optional_keys:
            assert classic_constants.must_not_be_none(key) is False, f"{key} should be optional"

    def test_settings_ignore_none_list(self):
        """Test SETTINGS_IGNORE_NONE list exists and contains strings."""
        assert hasattr(classic_constants, "SETTINGS_IGNORE_NONE")
        ignore_list = classic_constants.SETTINGS_IGNORE_NONE
        assert isinstance(ignore_list, list)
        assert len(ignore_list) > 0
        assert all(isinstance(item, str) for item in ignore_list)


@pytest.mark.rust
@pytest.mark.unit
class TestModuleMetadata:
    """Test module-level metadata."""

    def test_module_version(self):
        """Test module __version__ is defined."""
        assert hasattr(classic_constants, "__version__")
        assert isinstance(classic_constants.__version__, str)
        assert len(classic_constants.__version__) > 0

    def test_module_all(self):
        """Test __all__ exports are defined."""
        assert hasattr(classic_constants, "__all__")
        all_exports = classic_constants.__all__

        # Should include major exports
        expected_exports = [
            "YamlFile",
            "GameId",
            "must_not_be_none",
            "FALLOUT4_VERSIONS",
            "F4SE_VERSIONS",
        ]

        for export in expected_exports:
            assert export in all_exports, f"{export} should be in __all__"
