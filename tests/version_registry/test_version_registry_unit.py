"""Unit tests for VersionRegistry module.

Tests the data-driven version registry that manages game version metadata.
"""

import pytest
from packaging.version import Version

from ClassicLib.support.versions import (
    AddressLibraryConfig,
    CompatibleRange,
    CrashgenConfig,
    MatchConfidence,
    MatchResult,
    VersionInfo,
    VersionMatcher,
    VersionRegistry,
    XseConfig,
    get_version_registry,
)


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the registry singleton between tests."""
    VersionRegistry.reset_instance()
    yield
    VersionRegistry.reset_instance()


class TestVersionInfoModel:
    """Test VersionInfo data model."""

    @pytest.mark.unit
    def test_version_info_creation(self):
        """Test creating a VersionInfo object."""
        info = VersionInfo(
            id="TEST_VERSION",
            game="Fallout4",
            is_vr=False,
            version=Version("1.10.163.0"),
            display_name="Test Version",
            short_name="TEST",
        )

        assert info.id == "TEST_VERSION"
        assert info.game == "Fallout4"
        assert info.is_vr is False
        assert info.version == Version("1.10.163.0")
        assert info.version_string == "1.10.163.0"

    @pytest.mark.unit
    def test_version_info_docs_name(self):
        """Test VersionInfo docs_name property."""
        info = VersionInfo(
            id="TEST_VERSION",
            game="Fallout4",
            is_vr=False,
            version=Version("1.10.163.0"),
            docs_name="Fallout4 OG",
        )

        assert info.docs_name == "Fallout4 OG"

    @pytest.mark.unit
    def test_version_info_docs_name_default(self):
        """Test VersionInfo docs_name defaults to empty string."""
        info = VersionInfo(id="TEST", game="Fallout4", version=Version("1.0.0"))

        assert info.docs_name == ""

    @pytest.mark.unit
    def test_version_info_steam_id(self):
        """Test VersionInfo steam_id property."""
        info = VersionInfo(
            id="TEST_VERSION",
            game="Fallout4",
            is_vr=False,
            version=Version("1.10.163.0"),
            steam_id=377160,
        )

        assert info.steam_id == 377160

    @pytest.mark.unit
    def test_version_info_steam_id_default(self):
        """Test VersionInfo steam_id defaults to 0."""
        info = VersionInfo(id="TEST", game="Fallout4", version=Version("1.0.0"))

        assert info.steam_id == 0

    @pytest.mark.unit
    def test_version_info_with_address_library(self):
        """Test VersionInfo with AddressLibraryConfig."""
        addr_lib = AddressLibraryConfig(
            filename="version-1-10-163-0.bin",
            format="bin",
            nexus_url="https://example.com",
        )

        info = VersionInfo(
            id="TEST",
            game="Fallout4",
            is_vr=False,
            version=Version("1.10.163.0"),
            address_library=addr_lib,
        )

        assert info.address_library is not None
        assert info.address_library.filename == "version-1-10-163-0.bin"
        assert info.address_library.format == "bin"

    @pytest.mark.unit
    def test_version_info_compatibility_exact_match(self):
        """Test is_compatible_with for exact version match."""
        info = VersionInfo(
            id="TEST",
            game="Fallout4",
            is_vr=False,
            version=Version("1.10.163.0"),
        )

        assert info.is_compatible_with(Version("1.10.163.0"))
        assert not info.is_compatible_with(Version("1.10.984.0"))

    @pytest.mark.unit
    def test_version_info_compatibility_range_match(self):
        """Test is_compatible_with for range matching."""
        compat_range = CompatibleRange(
            min_version=Version("1.10.163.0"),
            max_version=Version("1.10.163.999"),
        )

        info = VersionInfo(
            id="TEST",
            game="Fallout4",
            is_vr=False,
            version=Version("1.10.163.0"),
            compatible_range=compat_range,
        )

        assert info.is_compatible_with(Version("1.10.163.0"))
        assert info.is_compatible_with(Version("1.10.163.500"))
        assert not info.is_compatible_with(Version("1.10.984.0"))


class TestCompatibleRange:
    """Test CompatibleRange data model."""

    @pytest.mark.unit
    def test_range_contains(self):
        """Test range containment check."""
        range_obj = CompatibleRange(
            min_version=Version("1.10.0.0"),
            max_version=Version("1.10.999.999"),
        )

        assert range_obj.contains(Version("1.10.163.0"))
        assert range_obj.contains(Version("1.10.984.0"))
        assert not range_obj.contains(Version("1.2.72.0"))

    @pytest.mark.unit
    def test_range_from_strings(self):
        """Test creating range from strings."""
        range_obj = CompatibleRange.from_strings("1.10.163.0", "1.10.163.999")

        assert range_obj.min_version == Version("1.10.163.0")
        assert range_obj.max_version == Version("1.10.163.999")


class TestVersionRegistry:
    """Test VersionRegistry singleton and operations."""

    @pytest.mark.unit
    def test_registry_singleton(self):
        """Test that registry is a singleton."""
        registry1 = get_version_registry()
        registry2 = get_version_registry()

        assert registry1 is registry2

    @pytest.mark.unit
    def test_registry_has_default_versions(self):
        """Test that registry loads default versions."""
        registry = get_version_registry()

        # Should have at least OG, NG, and VR versions
        og = registry.get_by_id("FO4_OG")
        ng = registry.get_by_id("FO4_NG")
        vr = registry.get_by_id("FO4_VR")

        assert og is not None
        assert ng is not None
        assert vr is not None

    @pytest.mark.unit
    def test_get_by_id_og_version(self):
        """Test getting OG version by ID."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")

        assert og is not None
        assert og.version == Version("1.10.163.0")
        assert og.short_name == "OG"
        assert og.is_vr is False

    @pytest.mark.unit
    def test_get_by_id_ng_version(self):
        """Test getting NG version by ID."""
        registry = get_version_registry()
        ng = registry.get_by_id("FO4_NG")

        assert ng is not None
        assert ng.version == Version("1.10.984.0")
        assert ng.short_name == "NG"
        assert ng.is_vr is False

    @pytest.mark.unit
    def test_get_by_id_vr_version(self):
        """Test getting VR version by ID."""
        registry = get_version_registry()
        vr = registry.get_by_id("FO4_VR")

        assert vr is not None
        assert vr.version == Version("1.2.72.0")
        assert vr.short_name == "VR"
        assert vr.is_vr is True

    @pytest.mark.unit
    def test_get_by_id_not_found(self):
        """Test getting non-existent version by ID."""
        registry = get_version_registry()
        result = registry.get_by_id("NONEXISTENT")

        assert result is None

    @pytest.mark.unit
    def test_get_by_version_exact_match(self):
        """Test getting version by exact Version object."""
        registry = get_version_registry()
        og = registry.get_by_version(Version("1.10.163.0"))

        assert og is not None
        assert og.id == "FO4_OG"

    @pytest.mark.unit
    def test_get_by_short_name(self):
        """Test getting version by short name."""
        registry = get_version_registry()

        og = registry.get_by_short_name("OG")
        ng = registry.get_by_short_name("NG")
        vr = registry.get_by_short_name("VR")

        assert og is not None and og.id == "FO4_OG"
        assert ng is not None and ng.id == "FO4_NG"
        assert vr is not None and vr.id == "FO4_VR"

    @pytest.mark.unit
    def test_get_all_for_game(self):
        """Test getting all versions for a game."""
        registry = get_version_registry()
        all_fo4 = registry.get_all_for_game("Fallout4")

        assert len(all_fo4) >= 3  # OG, NG, VR

    @pytest.mark.unit
    def test_get_all_for_game_non_vr(self):
        """Test getting non-VR versions for a game."""
        registry = get_version_registry()
        non_vr = registry.get_all_for_game("Fallout4", is_vr=False)

        assert len(non_vr) >= 2  # OG, NG
        assert all(not v.is_vr for v in non_vr)

    @pytest.mark.unit
    def test_get_all_for_game_vr(self):
        """Test getting VR versions for a game."""
        registry = get_version_registry()
        vr_only = registry.get_all_for_game("Fallout4", is_vr=True)

        assert len(vr_only) >= 1  # VR
        assert all(v.is_vr for v in vr_only)

    @pytest.mark.unit
    def test_get_correct_versions_vr_mode(self):
        """Test getting correct versions for VR mode."""
        registry = get_version_registry()
        correct = registry.get_correct_versions(is_vr=True)

        assert len(correct) >= 1
        assert all(v.is_vr for v in correct)

    @pytest.mark.unit
    def test_get_correct_versions_non_vr_mode(self):
        """Test getting correct versions for non-VR mode."""
        registry = get_version_registry()
        correct = registry.get_correct_versions(is_vr=False)

        assert len(correct) >= 2
        assert all(not v.is_vr for v in correct)

    @pytest.mark.unit
    def test_get_wrong_versions_vr_mode(self):
        """Test getting wrong versions for VR mode."""
        registry = get_version_registry()
        wrong = registry.get_wrong_versions(is_vr=True)

        assert len(wrong) >= 2
        assert all(not v.is_vr for v in wrong)

    @pytest.mark.unit
    def test_address_library_has_filename(self):
        """Test that all versions have address library filenames."""
        registry = get_version_registry()

        for version_id in ["FO4_OG", "FO4_NG", "FO4_VR"]:
            info = registry.get_by_id(version_id)
            assert info is not None
            assert info.address_library is not None
            assert info.address_library.filename


class TestVersionMatcher:
    """Test version matching with fallback strategies."""

    @pytest.mark.unit
    def test_exact_match(self):
        """Test exact version matching."""
        registry = get_version_registry()
        result = registry.match_version(Version("1.10.163.0"), "Fallout4", is_vr=False)

        assert result.confidence == MatchConfidence.EXACT
        assert result.version_info is not None
        assert result.version_info.id == "FO4_OG"
        assert result.is_exact
        assert not result.should_warn

    @pytest.mark.unit
    def test_exact_match_ng(self):
        """Test exact version matching for NG."""
        registry = get_version_registry()
        result = registry.match_version(Version("1.10.984.0"), "Fallout4", is_vr=False)

        assert result.confidence == MatchConfidence.EXACT
        assert result.version_info is not None
        assert result.version_info.id == "FO4_NG"

    @pytest.mark.unit
    def test_exact_match_vr(self):
        """Test exact version matching for VR."""
        registry = get_version_registry()
        result = registry.match_version(Version("1.2.72.0"), "Fallout4", is_vr=True)

        assert result.confidence == MatchConfidence.EXACT
        assert result.version_info is not None
        assert result.version_info.id == "FO4_VR"

    @pytest.mark.unit
    def test_nearest_match_unknown_version(self):
        """Test nearest matching for unknown version."""
        registry = get_version_registry()
        # Unknown version in 1.10.x range should match to NG (higher priority)
        result = registry.match_version(Version("1.10.500.0"), "Fallout4", is_vr=False)

        assert result.confidence in (MatchConfidence.RANGE, MatchConfidence.NEAREST)
        assert result.version_info is not None
        assert result.should_warn
        assert result.is_valid

    @pytest.mark.unit
    def test_fallback_for_completely_unknown_version(self):
        """Test fallback for completely unknown version."""
        registry = get_version_registry()
        # Completely unknown major version
        result = registry.match_version(Version("99.99.99.0"), "Fallout4", is_vr=False)

        # Should still return something (default fallback)
        assert result.version_info is not None or result.confidence == MatchConfidence.UNKNOWN

    @pytest.mark.unit
    def test_match_result_properties(self):
        """Test MatchResult property methods."""
        registry = get_version_registry()
        result = registry.match_version(Version("1.10.163.0"), "Fallout4", is_vr=False)

        assert result.is_exact
        assert not result.is_fallback
        assert not result.should_warn
        assert result.is_valid


class TestAddressLibraryConfig:
    """Test AddressLibraryConfig data model."""

    @pytest.mark.unit
    def test_address_library_config_creation(self):
        """Test creating AddressLibraryConfig."""
        config = AddressLibraryConfig(
            filename="version-1-10-163-0.bin",
            format="bin",
            nexus_url="https://www.nexusmods.com/fallout4/mods/47327",
        )

        assert config.filename == "version-1-10-163-0.bin"
        assert config.format == "bin"
        assert "nexusmods.com" in config.nexus_url

    @pytest.mark.unit
    def test_address_library_config_csv_format(self):
        """Test AddressLibraryConfig with CSV format (VR)."""
        config = AddressLibraryConfig(
            filename="version-1-2-72-0.csv",
            format="csv",
        )

        assert config.format == "csv"


class TestXseConfig:
    """Test XseConfig data model."""

    @pytest.mark.unit
    def test_xse_config_creation(self):
        """Test creating XseConfig."""
        config = XseConfig(
            acronym="F4SE",
            compatible_version="0.6.23",
            loader="f4se_loader.exe",
        )

        assert config.acronym == "F4SE"
        assert config.compatible_version == "0.6.23"
        assert config.loader == "f4se_loader.exe"

    @pytest.mark.unit
    def test_xse_config_full_name(self):
        """Test XseConfig full_name property."""
        config = XseConfig(
            acronym="F4SE",
            compatible_version="0.6.23",
            loader="f4se_loader.exe",
            full_name="Fallout 4 Script Extender",
        )

        assert config.full_name == "Fallout 4 Script Extender"

    @pytest.mark.unit
    def test_xse_config_full_name_default(self):
        """Test XseConfig full_name defaults to empty string."""
        config = XseConfig(acronym="F4SE")

        assert config.full_name == ""

    @pytest.mark.unit
    def test_xse_config_file_count(self):
        """Test XseConfig file_count property."""
        config = XseConfig(
            acronym="F4SE",
            compatible_version="0.6.23",
            file_count=5,
        )

        assert config.file_count == 5

    @pytest.mark.unit
    def test_xse_config_file_count_default(self):
        """Test XseConfig file_count defaults to 0."""
        config = XseConfig(acronym="F4SE")

        assert config.file_count == 0

    @pytest.mark.unit
    def test_xse_config_parsed_version(self):
        """Test XseConfig compatible_version_parsed property."""
        config = XseConfig(
            acronym="F4SE",
            compatible_version="0.6.23",
        )

        parsed = config.compatible_version_parsed
        assert parsed == Version("0.6.23")


class TestCrashgenConfig:
    """Test CrashgenConfig data model."""

    @pytest.mark.unit
    def test_crashgen_config_creation(self):
        """Test creating CrashgenConfig."""
        config = CrashgenConfig(
            version="1.26.6",
            name="Buffout 4",
            description="Crash logger for Fallout 4",
            download_url="https://example.com/buffout4",
        )

        assert config.version == "1.26.6"
        assert config.name == "Buffout 4"
        assert config.description == "Crash logger for Fallout 4"
        assert config.download_url == "https://example.com/buffout4"

    @pytest.mark.unit
    def test_crashgen_config_acronym(self):
        """Test CrashgenConfig acronym property."""
        config = CrashgenConfig(
            version="1.26.6",
            name="Buffout 4",
            acronym="B4",
        )

        assert config.acronym == "B4"

    @pytest.mark.unit
    def test_crashgen_config_acronym_default(self):
        """Test CrashgenConfig acronym defaults to empty string."""
        config = CrashgenConfig(version="1.26.6")

        assert config.acronym == ""

    @pytest.mark.unit
    def test_crashgen_config_dll_file(self):
        """Test CrashgenConfig dll_file property."""
        config = CrashgenConfig(
            version="1.26.6",
            name="Buffout 4",
            dll_file="Buffout4.dll",
        )

        assert config.dll_file == "Buffout4.dll"

    @pytest.mark.unit
    def test_crashgen_config_dll_file_default(self):
        """Test CrashgenConfig dll_file defaults to empty string."""
        config = CrashgenConfig(version="1.26.6")

        assert config.dll_file == ""


class TestGetAddressLibraryFilename:
    """Test convenience method for getting Address Library filename."""

    @pytest.mark.unit
    def test_get_address_library_filename_og(self):
        """Test getting Address Library filename for OG version."""
        registry = get_version_registry()
        filename = registry.get_address_library_filename(Version("1.10.163.0"), is_vr=False)

        assert filename == "version-1-10-163-0.bin"

    @pytest.mark.unit
    def test_get_address_library_filename_ng(self):
        """Test getting Address Library filename for NG version."""
        registry = get_version_registry()
        filename = registry.get_address_library_filename(Version("1.10.984.0"), is_vr=False)

        assert filename == "version-1-10-984-0.bin"

    @pytest.mark.unit
    def test_get_address_library_filename_vr(self):
        """Test getting Address Library filename for VR version."""
        registry = get_version_registry()
        filename = registry.get_address_library_filename(Version("1.2.72.0"), is_vr=True)

        assert filename == "version-1-2-72-0.csv"
