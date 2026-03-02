"""Integration tests for CrashgenVersionChecker and registry-backed version data.

These tests exercise real VersionRegistry loading/matching behavior and may
change as production version data evolves.
"""

import pytest
from packaging.version import Version

from ClassicLib.support.versions import (
    CrashgenConfig,
    CrashgenVersionResult,
    CrashgenVersionStatus,
    VersionRegistry,
    check_crashgen_version,
    check_crashgen_version_for_detected_game,
    get_matching_crashgen_config,
    get_version_registry,
)


class _StubRegistry:
    """Minimal registry stub used by targeted integration scenarios."""

    def __init__(self, by_id: dict[str, tuple[CrashgenConfig, ...]]) -> None:
        self._by_id = by_id

    def get_crashgen_configs(self, version_id: str) -> tuple[CrashgenConfig, ...]:
        return self._by_id.get(version_id, ())


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the registry singleton between tests."""
    VersionRegistry.reset_instance()
    yield
    VersionRegistry.reset_instance()


class TestCrashgenVersionStatus:
    """Test CrashgenVersionStatus enum values."""

    @pytest.mark.integration
    def test_status_enum_values(self):
        """Test that all expected status values exist."""
        assert CrashgenVersionStatus.VALID.value == "valid"
        assert CrashgenVersionStatus.OUTDATED.value == "outdated"
        assert CrashgenVersionStatus.NEWER_THAN_KNOWN.value == "newer_than_known"
        assert CrashgenVersionStatus.NO_SUPPORTED_VERSION.value == "no_supported_version"
        assert CrashgenVersionStatus.UNKNOWN_GAME_VERSION.value == "unknown_game_version"


class TestCrashgenVersionResult:
    """Test CrashgenVersionResult data class."""

    @pytest.mark.integration
    def test_result_is_valid_for_valid_status(self):
        """Test is_valid property for VALID status."""
        result = CrashgenVersionResult(
            status=CrashgenVersionStatus.VALID,
            detected_version=Version("1.28.6"),
            valid_versions=("1.28.6", "1.37.0"),
            game_version_id="FO4_OG",
            message="You have a valid version!",
        )
        assert result.is_valid is True
        assert result.needs_update is False

    @pytest.mark.integration
    def test_result_is_valid_for_newer_status(self):
        """Test is_valid property for NEWER_THAN_KNOWN status."""
        result = CrashgenVersionResult(
            status=CrashgenVersionStatus.NEWER_THAN_KNOWN,
            detected_version=Version("1.40.0"),
            valid_versions=("1.28.6", "1.37.0"),
            game_version_id="FO4_OG",
            message="Version is newer than known.",
        )
        assert result.is_valid is True
        assert result.needs_update is False

    @pytest.mark.integration
    def test_result_needs_update_for_outdated_status(self):
        """Test needs_update property for OUTDATED status."""
        result = CrashgenVersionResult(
            status=CrashgenVersionStatus.OUTDATED,
            detected_version=Version("1.26.0"),
            valid_versions=("1.28.6", "1.37.0"),
            game_version_id="FO4_OG",
            message="Your version is outdated!",
        )
        assert result.is_valid is False
        assert result.needs_update is True

    @pytest.mark.integration
    def test_result_for_no_supported_version(self):
        """Test result for NO_SUPPORTED_VERSION status."""
        result = CrashgenVersionResult(
            status=CrashgenVersionStatus.NO_SUPPORTED_VERSION,
            detected_version=Version("1.28.6"),
            valid_versions=(),
            game_version_id="FO4_AE",
            message="No supported version yet.",
        )
        assert result.is_valid is False
        assert result.needs_update is False


class TestCheckCrashgenVersion:
    """Test check_crashgen_version function."""

    @pytest.mark.integration
    def test_valid_version_fo4_og_first_option(self):
        """Test valid version check for FO4_OG with first valid option."""
        result = check_crashgen_version(Version("1.28.6"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_OG"
        assert "valid" in result.message.lower()

    @pytest.mark.integration
    def test_valid_version_fo4_og_second_option(self):
        """Test valid version check for FO4_OG with second valid option."""
        result = check_crashgen_version(Version("1.37.0"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_OG"

    @pytest.mark.integration
    def test_valid_version_fo4_ng(self):
        """Test valid version check for FO4_NG."""
        result = check_crashgen_version(Version("1.37.0"), "FO4_NG")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_NG"

    @pytest.mark.integration
    def test_valid_version_fo4_vr(self):
        """Test valid version check for FO4_VR."""
        result = check_crashgen_version(Version("1.37.0"), "FO4_VR")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_VR"

    @pytest.mark.integration
    def test_outdated_version_fo4_og(self):
        """Test outdated version check for FO4_OG."""
        result = check_crashgen_version(Version("1.26.0"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.OUTDATED
        assert "outdated" in result.message.lower()

    @pytest.mark.integration
    def test_outdated_version_fo4_ng(self):
        """Test outdated version check for FO4_NG."""
        result = check_crashgen_version(Version("1.28.6"), "FO4_NG")
        # 1.28.6 is valid for OG but not for NG (which only has 1.37.0)
        assert result.status == CrashgenVersionStatus.OUTDATED

    @pytest.mark.integration
    def test_newer_than_known_version(self):
        """Test version newer than all known valid versions."""
        result = check_crashgen_version(Version("1.40.0"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.NEWER_THAN_KNOWN
        assert "newer" in result.message.lower()

    @pytest.mark.integration
    def test_newer_than_known_with_synthetic_registry_data(self, monkeypatch: pytest.MonkeyPatch):
        """Test NEWER_THAN_KNOWN using synthetic crashgen config data."""
        stub_registry = _StubRegistry({
            "TEST_GAME": (
                CrashgenConfig(version="1.7.1", name="Test Crash Logger"),
                CrashgenConfig(version="1.0.0", name="Test Addictol"),
            )
        })
        monkeypatch.setattr("ClassicLib.support.versions.core.get_version_registry", lambda: stub_registry)

        result = check_crashgen_version(Version("1.28.6"), "TEST_GAME")
        assert result.status == CrashgenVersionStatus.NEWER_THAN_KNOWN
        assert result.valid_versions == ("1.7.1", "1.0.0")

    @pytest.mark.integration
    def test_valid_version_with_synthetic_registry_data(self, monkeypatch: pytest.MonkeyPatch):
        """Test VALID result using synthetic crashgen config data."""
        stub_registry = _StubRegistry({
            "TEST_GAME": (
                CrashgenConfig(version="1.7.1", name="Test Crash Logger"),
                CrashgenConfig(version="1.0.0", name="Test Addictol"),
            )
        })
        monkeypatch.setattr("ClassicLib.support.versions.core.get_version_registry", lambda: stub_registry)

        result = check_crashgen_version(Version("1.7.1"), "TEST_GAME")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "TEST_GAME"

    @pytest.mark.integration
    def test_unknown_game_version_id(self):
        """Test with unknown game version ID."""
        result = check_crashgen_version(Version("1.28.6"), "NONEXISTENT")
        # Should return NO_SUPPORTED_VERSION since version ID not found
        assert result.status == CrashgenVersionStatus.NO_SUPPORTED_VERSION


class TestCheckCrashgenVersionForDetectedGame:
    """Test check_crashgen_version_for_detected_game function."""

    @pytest.mark.integration
    def test_detected_game_og_valid_crashgen(self):
        """Test detecting OG game version with valid crashgen."""
        result = check_crashgen_version_for_detected_game(
            detected_crashgen=Version("1.28.6"),
            detected_game_version=Version("1.10.163.0"),
            is_vr=False,
        )
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_OG"

    @pytest.mark.integration
    def test_detected_game_ng_valid_crashgen(self):
        """Test detecting NG game version with valid crashgen."""
        result = check_crashgen_version_for_detected_game(
            detected_crashgen=Version("1.37.0"),
            detected_game_version=Version("1.10.984.0"),
            is_vr=False,
        )
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_NG"

    @pytest.mark.integration
    def test_detected_game_vr_valid_crashgen(self):
        """Test detecting VR game version with valid crashgen."""
        result = check_crashgen_version_for_detected_game(
            detected_crashgen=Version("1.37.0"),
            detected_game_version=Version("1.2.72.0"),
            is_vr=True,
        )
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_VR"

    @pytest.mark.integration
    def test_detected_game_og_outdated_crashgen(self):
        """Test detecting OG game version with outdated crashgen."""
        result = check_crashgen_version_for_detected_game(
            detected_crashgen=Version("1.26.0"),
            detected_game_version=Version("1.10.163.0"),
            is_vr=False,
        )
        assert result.status == CrashgenVersionStatus.OUTDATED

    @pytest.mark.integration
    def test_detected_game_ng_with_og_only_crashgen(self):
        """Test detecting NG game version with OG-only crashgen version."""
        # 1.28.6 is valid for OG but NG only supports 1.37.0
        result = check_crashgen_version_for_detected_game(
            detected_crashgen=Version("1.28.6"),
            detected_game_version=Version("1.10.984.0"),
            is_vr=False,
        )
        assert result.status == CrashgenVersionStatus.OUTDATED


class TestVersionInfoCrashgenVersions:
    """Test crashgen_versions field in VersionInfo."""

    @pytest.mark.integration
    def test_og_has_multiple_crashgen_versions(self):
        """Test that FO4_OG has multiple valid crashgen versions."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")

        assert og is not None
        assert og.crashgen_versions is not None
        assert len(og.crashgen_versions) >= 2
        # Use get_crashgen_version_strings() for simple version string access
        version_strings = og.get_crashgen_version_strings()
        assert "1.28.6" in version_strings
        assert "1.37.0" in version_strings

    @pytest.mark.integration
    def test_ng_has_single_crashgen_version(self):
        """Test that FO4_NG has a single valid crashgen version."""
        registry = get_version_registry()
        ng = registry.get_by_id("FO4_NG")

        assert ng is not None
        assert ng.crashgen_versions is not None
        # Use get_crashgen_version_strings() for simple version string access
        version_strings = ng.get_crashgen_version_strings()
        assert "1.37.0" in version_strings

    @pytest.mark.integration
    def test_ae_has_crashgen_version(self):
        """Test that FO4_AE has at least one crashgen version configured."""
        registry = get_version_registry()
        ae = registry.get_by_id("FO4_AE")

        assert ae is not None
        assert len(ae.crashgen_versions) >= 1
        version_strings = ae.get_crashgen_version_strings()
        assert all(version for version in version_strings)

    @pytest.mark.integration
    def test_vr_has_crashgen_version(self):
        """Test that FO4_VR has valid crashgen version."""
        registry = get_version_registry()
        vr = registry.get_by_id("FO4_VR")

        assert vr is not None
        assert vr.crashgen_versions is not None
        # Use get_crashgen_version_strings() for simple version string access
        version_strings = vr.get_crashgen_version_strings()
        assert "1.37.0" in version_strings


class TestRegistryGetCrashgenVersions:
    """Test VersionRegistry helper methods for crashgen versions."""

    @pytest.mark.integration
    def test_get_crashgen_versions_by_id(self):
        """Test getting crashgen versions by version ID."""
        registry = get_version_registry()

        og_versions = registry.get_crashgen_versions("FO4_OG")
        ng_versions = registry.get_crashgen_versions("FO4_NG")
        ae_versions = registry.get_crashgen_versions("FO4_AE")

        assert len(og_versions) >= 2
        assert len(ng_versions) >= 1
        assert len(ae_versions) >= 1  # AE now has MiniBuff AE Crash Logger

    @pytest.mark.integration
    def test_get_crashgen_versions_nonexistent(self):
        """Test getting crashgen versions for non-existent version ID."""
        registry = get_version_registry()
        versions = registry.get_crashgen_versions("NONEXISTENT")

        assert versions == ()

    @pytest.mark.integration
    def test_get_crashgen_versions_for_detected(self):
        """Test getting crashgen versions for detected game version."""
        registry = get_version_registry()

        og_versions = registry.get_crashgen_versions_for_detected(Version("1.10.163.0"), "Fallout4", is_vr=False)
        assert len(og_versions) >= 2

        ng_versions = registry.get_crashgen_versions_for_detected(Version("1.10.984.0"), "Fallout4", is_vr=False)
        assert len(ng_versions) >= 1


class TestCustomCrashgenName:
    """Test custom crashgen names in messages."""

    @pytest.mark.integration
    def test_custom_crashgen_name_in_outdated_message(self):
        """Test that custom crashgen name appears in outdated message (no matched config)."""
        # When version is outdated, there's no matched_config, so custom name is used
        result = check_crashgen_version(
            Version("1.26.0"),
            "FO4_OG",
            crashgen_name="Custom Crashgen",
        )
        assert result.status == CrashgenVersionStatus.OUTDATED
        assert "Custom Crashgen" in result.message

    @pytest.mark.integration
    def test_custom_crashgen_name_in_newer_than_known_message(self):
        """Test that custom crashgen name appears in newer_than_known message."""
        # When version is newer than known, there's no matched_config, so custom name is used
        result = check_crashgen_version(
            Version("1.40.0"),
            "FO4_OG",
            crashgen_name="Custom Crashgen",
        )
        assert result.status == CrashgenVersionStatus.NEWER_THAN_KNOWN
        assert "Custom Crashgen" in result.message

    @pytest.mark.integration
    def test_matched_config_name_takes_precedence_over_custom(self):
        """Test that matched config's name takes precedence over custom crashgen_name."""
        # When there's a matched config with a name, the config's name is used
        result = check_crashgen_version(
            Version("1.28.6"),
            "FO4_OG",
            crashgen_name="Custom Crashgen",
        )
        assert result.status == CrashgenVersionStatus.VALID
        assert result.matched_config is not None
        assert result.matched_config.name == "Buffout 4"
        # The message should use the matched config's name, not the custom name
        assert "Buffout 4" in result.message

    @pytest.mark.integration
    def test_default_crashgen_name_in_message(self):
        """Test that matched config's name (Buffout 4) appears in valid message."""
        result = check_crashgen_version(Version("1.28.6"), "FO4_OG")
        assert "Buffout 4" in result.message


class TestMatchedConfig:
    """Test matched_config field in CrashgenVersionResult."""

    @pytest.mark.integration
    def test_valid_version_has_matched_config(self):
        """Test that valid version result includes matched_config."""
        result = check_crashgen_version(Version("1.28.6"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.matched_config is not None
        assert result.matched_config.version == "1.28.6"
        # Name may be empty if loaded from simple YAML format
        # or populated if loaded from structured format or defaults

    @pytest.mark.integration
    def test_valid_version_matched_config_has_version(self):
        """Test that matched_config has version field populated."""
        result = check_crashgen_version(Version("1.28.6"), "FO4_OG")
        assert result.matched_config is not None
        assert result.matched_config.version == "1.28.6"

    @pytest.mark.integration
    def test_valid_ng_version_has_matched_config(self):
        """Test that valid NG version result includes matched_config."""
        result = check_crashgen_version(Version("1.37.0"), "FO4_NG")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.matched_config is not None
        assert result.matched_config.version == "1.37.0"

    @pytest.mark.integration
    def test_outdated_version_has_no_matched_config(self):
        """Test that outdated version result has no matched_config."""
        result = check_crashgen_version(Version("1.26.0"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.OUTDATED
        assert result.matched_config is None

    @pytest.mark.integration
    def test_newer_than_known_has_no_matched_config(self):
        """Test that newer_than_known result has no matched_config."""
        result = check_crashgen_version(Version("1.40.0"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.NEWER_THAN_KNOWN
        assert result.matched_config is None

    @pytest.mark.integration
    def test_no_supported_version_has_no_matched_config(self):
        """Test that no_supported_version result has no matched_config."""
        result = check_crashgen_version(Version("1.28.6"), "NONEXISTENT")
        assert result.status == CrashgenVersionStatus.NO_SUPPORTED_VERSION
        assert result.matched_config is None

    @pytest.mark.integration
    def test_matched_config_version_in_valid_versions(self):
        """Test that matched config's version is in valid_versions."""
        result = check_crashgen_version(Version("1.37.0"), "FO4_NG")
        assert result.matched_config is not None
        assert result.matched_config.version in result.valid_versions


class TestGetMatchingCrashgenConfig:
    """Test get_matching_crashgen_config function."""

    @pytest.mark.integration
    def test_get_config_for_buffout4(self):
        """Test getting config for Buffout 4 version."""
        config = get_matching_crashgen_config(Version("1.28.6"), "FO4_OG")
        assert config is not None
        assert config.version == "1.28.6"
        # Name/download_url may be empty if using simple YAML format

    @pytest.mark.integration
    def test_get_config_for_buffout4_ng(self):
        """Test getting config for Buffout 4 NG version."""
        config = get_matching_crashgen_config(Version("1.37.0"), "FO4_OG")
        assert config is not None
        assert config.version == "1.37.0"

    @pytest.mark.integration
    def test_get_config_for_ng_game(self):
        """Test getting config for NG game version."""
        config = get_matching_crashgen_config(Version("1.37.0"), "FO4_NG")
        assert config is not None
        assert config.version == "1.37.0"

    @pytest.mark.integration
    def test_get_config_for_vr_game(self):
        """Test getting config for VR game version."""
        config = get_matching_crashgen_config(Version("1.37.0"), "FO4_VR")
        assert config is not None
        assert config.version == "1.37.0"

    @pytest.mark.integration
    def test_get_config_returns_none_for_unknown_version(self):
        """Test that get_matching_crashgen_config returns None for unknown version."""
        config = get_matching_crashgen_config(Version("1.26.0"), "FO4_OG")
        assert config is None

    @pytest.mark.integration
    def test_get_config_returns_none_for_nonexistent_game(self):
        """Test that get_matching_crashgen_config returns None for nonexistent game."""
        config = get_matching_crashgen_config(Version("1.28.6"), "NONEXISTENT")
        assert config is None


class TestCrashgenConfigModel:
    """Test CrashgenConfig model functionality."""

    @pytest.mark.integration
    def test_crashgen_config_from_version_string(self):
        """Test creating CrashgenConfig from just a version string."""
        config = CrashgenConfig.from_version_string("1.28.6")
        assert config.version == "1.28.6"
        assert config.name == ""
        assert config.description == ""
        assert config.download_url == ""
        assert config.compatible_range is None

    @pytest.mark.integration
    def test_crashgen_config_is_compatible_with_no_range(self):
        """Test that CrashgenConfig without compatible_range is compatible with any version."""
        config = CrashgenConfig(version="1.37.0", name="Test")
        assert config.is_compatible_with(Version("1.10.163.0")) is True
        assert config.is_compatible_with(Version("1.10.984.0")) is True
        assert config.is_compatible_with(Version("1.2.72.0")) is True

    @pytest.mark.integration
    def test_crashgen_config_with_all_fields(self):
        """Test CrashgenConfig with all fields populated."""
        config = CrashgenConfig(
            version="1.28.6",
            name="Buffout 4",
            description="Legacy version for OG",
            download_url="https://www.nexusmods.com/fallout4/mods/47359",
        )
        assert config.version == "1.28.6"
        assert config.name == "Buffout 4"
        assert config.description == "Legacy version for OG"
        assert "47359" in config.download_url

    @pytest.mark.integration
    def test_registry_crashgen_configs_have_versions(self):
        """Test that registry crashgen configs have version field populated."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")
        assert og is not None
        assert len(og.crashgen_versions) >= 2

        for config in og.crashgen_versions:
            assert config.version != ""
            # Name/download_url may be empty if using simple YAML format


class TestCrashgenConfigWithCompatibleRange:
    """Test CrashgenConfig compatible_range functionality."""

    @pytest.mark.integration
    def test_crashgen_config_is_compatible_with_range_inside(self):
        """Test that CrashgenConfig with compatible_range returns True for version inside range."""
        from ClassicLib.support.versions.models import CompatibleRange

        og_range = CompatibleRange.from_strings("1.10.163.0", "1.10.163.999")
        config = CrashgenConfig(
            version="1.28.6",
            name="Buffout 4",
            compatible_range=og_range,
        )
        assert config.is_compatible_with(Version("1.10.163.0")) is True
        assert config.is_compatible_with(Version("1.10.163.500")) is True
        assert config.is_compatible_with(Version("1.10.163.999")) is True

    @pytest.mark.integration
    def test_crashgen_config_is_compatible_with_range_outside(self):
        """Test that CrashgenConfig with compatible_range returns False for version outside range."""
        from ClassicLib.support.versions.models import CompatibleRange

        og_range = CompatibleRange.from_strings("1.10.163.0", "1.10.163.999")
        config = CrashgenConfig(
            version="1.28.6",
            name="Buffout 4",
            compatible_range=og_range,
        )
        assert config.is_compatible_with(Version("1.10.984.0")) is False
        assert config.is_compatible_with(Version("1.2.72.0")) is False
        assert config.is_compatible_with(Version("1.10.162.0")) is False

    @pytest.mark.integration
    def test_crashgen_config_with_compatible_range_all_fields(self):
        """Test CrashgenConfig with all fields including compatible_range."""
        from ClassicLib.support.versions.models import CompatibleRange

        og_range = CompatibleRange.from_strings("1.10.163.0", "1.10.163.999")
        config = CrashgenConfig(
            version="1.28.6",
            name="Buffout 4",
            description="Legacy version for OG",
            download_url="https://www.nexusmods.com/fallout4/mods/47359",
            compatible_range=og_range,
        )
        assert config.version == "1.28.6"
        assert config.name == "Buffout 4"
        assert config.description == "Legacy version for OG"
        assert config.download_url == "https://www.nexusmods.com/fallout4/mods/47359"
        assert config.compatible_range is not None
        assert config.compatible_range.min_version == Version("1.10.163.0")
        assert config.compatible_range.max_version == Version("1.10.163.999")


class TestVersionInfoCrashgenMethods:
    """Test VersionInfo helper methods for crashgen versions."""

    @pytest.mark.integration
    def test_get_crashgen_version_strings(self):
        """Test get_crashgen_version_strings returns tuple of version strings."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")
        assert og is not None

        version_strings = og.get_crashgen_version_strings()
        assert isinstance(version_strings, tuple)
        assert "1.28.6" in version_strings
        assert "1.37.0" in version_strings

    @pytest.mark.integration
    def test_get_crashgen_for_version_found(self):
        """Test get_crashgen_for_version returns matching config."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")
        assert og is not None

        config = og.get_crashgen_for_version("1.28.6")
        assert config is not None
        assert config.version == "1.28.6"

    @pytest.mark.integration
    def test_get_crashgen_for_version_not_found(self):
        """Test get_crashgen_for_version returns None for unknown version."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")
        assert og is not None

        config = og.get_crashgen_for_version("1.26.0")
        assert config is None

    @pytest.mark.integration
    def test_get_compatible_crashgens_default(self):
        """Test get_compatible_crashgens returns all crashgens for version info's own version."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")
        assert og is not None

        # Without explicit version, uses the VersionInfo's own version
        compatible = og.get_compatible_crashgens()
        assert len(compatible) >= 1
        # At least one should be compatible with OG's version
        version_strings = [c.version for c in compatible]
        assert "1.28.6" in version_strings or "1.37.0" in version_strings

    @pytest.mark.integration
    def test_get_compatible_crashgens_with_specific_version(self):
        """Test get_compatible_crashgens filters by specific game version."""
        from ClassicLib.support.versions.models import CompatibleRange, VersionInfo

        # Create a test VersionInfo with crashgens that have compatible_range
        og_range = CompatibleRange.from_strings("1.10.163.0", "1.10.163.999")
        ng_range = CompatibleRange.from_strings("1.10.984.0", "1.10.999.999")

        crashgens = (
            CrashgenConfig(
                version="1.28.6",
                name="Buffout 4",
                compatible_range=og_range,
            ),
            CrashgenConfig(
                version="1.37.0",
                name="Buffout 4 NG",
                compatible_range=ng_range,
            ),
        )

        test_version = VersionInfo(
            id="TEST",
            game="Fallout4",
            is_vr=False,
            version=Version("1.10.163.0"),
            crashgen_versions=crashgens,
        )

        # Check OG game version - should only get 1.28.6
        og_compatible = test_version.get_compatible_crashgens(Version("1.10.163.0"))
        assert len(og_compatible) == 1
        assert og_compatible[0].version == "1.28.6"

        # Check NG game version - should only get 1.37.0
        ng_compatible = test_version.get_compatible_crashgens(Version("1.10.984.0"))
        assert len(ng_compatible) == 1
        assert ng_compatible[0].version == "1.37.0"

    @pytest.mark.integration
    def test_get_compatible_crashgens_no_range_means_all_compatible(self):
        """Test crashgens without compatible_range are compatible with all versions."""
        from ClassicLib.support.versions.models import VersionInfo

        crashgens = (
            CrashgenConfig(
                version="1.37.0",
                name="Universal Version",
                # No compatible_range - compatible with all
            ),
        )

        test_version = VersionInfo(
            id="TEST",
            game="Fallout4",
            is_vr=False,
            version=Version("1.10.163.0"),
            crashgen_versions=crashgens,
        )

        # Should be compatible with any version
        og_compatible = test_version.get_compatible_crashgens(Version("1.10.163.0"))
        assert len(og_compatible) == 1

        ng_compatible = test_version.get_compatible_crashgens(Version("1.10.984.0"))
        assert len(ng_compatible) == 1

        vr_compatible = test_version.get_compatible_crashgens(Version("1.2.72.0"))
        assert len(vr_compatible) == 1


class TestStructuredYamlParsing:
    """Test parsing of structured crashgen_versions from YAML."""

    @pytest.mark.integration
    def test_yaml_loaded_crashgen_has_name(self):
        """Test that YAML-loaded crashgen configs have name field."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")
        assert og is not None

        # Find the Buffout 4 config (1.28.6)
        config = og.get_crashgen_for_version("1.28.6")
        assert config is not None
        # Name should be populated from structured YAML
        assert config.name == "Buffout 4"

    @pytest.mark.integration
    def test_yaml_loaded_crashgen_has_description(self):
        """Test that YAML-loaded crashgen configs have description field."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")
        assert og is not None

        config = og.get_crashgen_for_version("1.28.6")
        assert config is not None
        assert config.description == "Legacy version for OG"

    @pytest.mark.integration
    def test_yaml_loaded_crashgen_has_download_url(self):
        """Test that YAML-loaded crashgen configs have download_url field."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")
        assert og is not None

        config = og.get_crashgen_for_version("1.28.6")
        assert config is not None
        assert "47359" in config.download_url

    @pytest.mark.integration
    def test_og_crashgen_128_has_expected_metadata(self):
        """Test that OG crashgen 1.28.6 has correct metadata from Rust defaults.

        The Rust registry loads from hardcoded defaults where crashgen configs
        include compatible_range matching the YAML definition.
        """
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")
        assert og is not None

        config = og.get_crashgen_for_version("1.28.6")
        assert config is not None
        assert config.name == "Buffout 4"
        assert config.description == "Legacy version for OG"
        # Rust defaults include compatible_range for OG's legacy Buffout 4
        assert config.compatible_range is not None
        assert config.compatible_range.min_version == Version("1.10.163.0")
        assert config.compatible_range.max_version == Version("1.10.163.999")

    @pytest.mark.integration
    def test_yaml_loaded_ng_crashgen_metadata(self):
        """Test that NG crashgen config has proper metadata including compatible_range."""
        registry = get_version_registry()
        ng = registry.get_by_id("FO4_NG")
        assert ng is not None

        config = ng.get_crashgen_for_version("1.37.0")
        assert config is not None
        # Name matches what appears in crash log output (no "NG" suffix)
        assert config.name == "Buffout 4"
        # Description identifies this as the NG version
        assert config.description == "Buffout 4 NG"
        assert "64880" in config.download_url
        # NG crashgen has compatible_range for NG game versions
        assert config.compatible_range is not None
        assert config.compatible_range.min_version == Version("1.10.984.0")
        assert config.compatible_range.max_version == Version("1.10.999.999")

    @pytest.mark.integration
    def test_yaml_loaded_vr_crashgen_metadata(self):
        """Test that VR crashgen config has proper metadata."""
        registry = get_version_registry()
        vr = registry.get_by_id("FO4_VR")
        assert vr is not None

        config = vr.get_crashgen_for_version("1.37.0")
        assert config is not None
        # Name matches what appears in crash log output (no "NG" suffix)
        assert config.name == "Buffout 4"
        assert "64880" in config.download_url

    @pytest.mark.integration
    def test_og_buffout4_ng_version_has_no_compatible_range(self):
        """Test that OG's Buffout 4 NG version (1.37.0) has no compatible_range (universal)."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")
        assert og is not None

        config = og.get_crashgen_for_version("1.37.0")
        assert config is not None
        # Name matches what appears in crash log output (no "NG" suffix)
        assert config.name == "Buffout 4"
        # This should not have a compatible_range (compatible with any OG version)
        assert config.compatible_range is None

    @pytest.mark.integration
    def test_ae_crashgen_has_compatible_range(self):
        """Test that AE has at least one crashgen with a valid compatible_range."""
        registry = get_version_registry()
        ae = registry.get_by_id("FO4_AE")
        assert ae is not None

        with_range = [config for config in ae.crashgen_versions if config.compatible_range is not None]
        assert with_range
        for config in with_range:
            assert config.compatible_range is not None
            assert config.compatible_range.min_version <= config.compatible_range.max_version

    @pytest.mark.integration
    def test_vr_crashgen_has_no_compatible_range(self):
        """Test that VR crashgen has no compatible_range (universal within VR)."""
        registry = get_version_registry()
        vr = registry.get_by_id("FO4_VR")
        assert vr is not None

        config = vr.get_crashgen_for_version("1.37.0")
        assert config is not None
        assert config.compatible_range is None

    @pytest.mark.integration
    def test_og_get_compatible_crashgens_filters_by_range(self):
        """Test that get_compatible_crashgens only returns entries compatible with input version."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")
        assert og is not None

        og_game_version = Version("1.10.163.0")
        ng_game_version = Version("1.10.984.0")
        known_versions = {cfg.version for cfg in og.crashgen_versions}

        og_compatible = og.get_compatible_crashgens(str(og_game_version))
        ng_compatible = og.get_compatible_crashgens(str(ng_game_version))

        assert og_compatible
        assert ng_compatible
        assert {cfg.version for cfg in og_compatible}.issubset(known_versions)
        assert {cfg.version for cfg in ng_compatible}.issubset(known_versions)
        assert all(cfg.is_compatible_with(og_game_version) for cfg in og_compatible)
        assert all(cfg.is_compatible_with(ng_game_version) for cfg in ng_compatible)


class TestRegistryGetCrashgenConfigs:
    """Test VersionRegistry methods for getting crashgen configs."""

    @pytest.mark.integration
    def test_get_crashgen_configs_by_id(self):
        """Test getting crashgen configs by version ID."""
        registry = get_version_registry()
        configs = registry.get_crashgen_configs("FO4_OG")

        assert len(configs) >= 2
        assert all(isinstance(c, CrashgenConfig) for c in configs)

    @pytest.mark.integration
    def test_get_crashgen_configs_for_detected_returns_configs(self):
        """Test getting crashgen configs for detected game version."""
        registry = get_version_registry()
        configs = registry.get_crashgen_configs_for_detected(Version("1.10.163.0"), "Fallout4", is_vr=False)

        assert len(configs) >= 2
        assert all(isinstance(c, CrashgenConfig) for c in configs)

    @pytest.mark.integration
    def test_get_crashgen_configs_nonexistent_returns_empty(self):
        """Test getting crashgen configs for non-existent version ID."""
        registry = get_version_registry()
        configs = registry.get_crashgen_configs("NONEXISTENT")

        assert configs == ()


class TestMatchedConfigDisplayName:
    """Test that matched_config uses proper display name in messages."""

    @pytest.mark.integration
    def test_valid_version_message_uses_config_name(self):
        """Test that valid version message uses the matched config's name."""
        result = check_crashgen_version(Version("1.28.6"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.matched_config is not None
        # Message should use the config's name (Buffout 4) if available
        assert "Buffout 4" in result.message

    @pytest.mark.integration
    def test_valid_ng_version_message_uses_config_name(self):
        """Test that valid NG version message uses the matched config's name."""
        result = check_crashgen_version(Version("1.37.0"), "FO4_NG")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.matched_config is not None
        # Message should use "Buffout 4" (name matches log output)
        assert "Buffout 4" in result.message
