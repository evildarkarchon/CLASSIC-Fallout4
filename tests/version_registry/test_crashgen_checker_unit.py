"""Unit tests for CrashgenVersionChecker module.

Tests the list-based crash generator version validation that supports
multiple valid versions per game version.
"""

import pytest
from packaging.version import Version

from ClassicLib.VersionRegistry import (
    CrashgenVersionResult,
    CrashgenVersionStatus,
    VersionRegistry,
    check_crashgen_version,
    check_crashgen_version_for_detected_game,
    get_version_registry,
)


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the registry singleton between tests."""
    VersionRegistry.reset_instance()
    yield
    VersionRegistry.reset_instance()


class TestCrashgenVersionStatus:
    """Test CrashgenVersionStatus enum values."""

    @pytest.mark.unit
    def test_status_enum_values(self):
        """Test that all expected status values exist."""
        assert CrashgenVersionStatus.VALID.value == "valid"
        assert CrashgenVersionStatus.OUTDATED.value == "outdated"
        assert CrashgenVersionStatus.NEWER_THAN_KNOWN.value == "newer_than_known"
        assert CrashgenVersionStatus.NO_SUPPORTED_VERSION.value == "no_supported_version"
        assert CrashgenVersionStatus.UNKNOWN_GAME_VERSION.value == "unknown_game_version"


class TestCrashgenVersionResult:
    """Test CrashgenVersionResult data class."""

    @pytest.mark.unit
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

    @pytest.mark.unit
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

    @pytest.mark.unit
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

    @pytest.mark.unit
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

    @pytest.mark.unit
    def test_valid_version_fo4_og_first_option(self):
        """Test valid version check for FO4_OG with first valid option."""
        result = check_crashgen_version(Version("1.28.6"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_OG"
        assert "valid" in result.message.lower()

    @pytest.mark.unit
    def test_valid_version_fo4_og_second_option(self):
        """Test valid version check for FO4_OG with second valid option."""
        result = check_crashgen_version(Version("1.37.0"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_OG"

    @pytest.mark.unit
    def test_valid_version_fo4_ng(self):
        """Test valid version check for FO4_NG."""
        result = check_crashgen_version(Version("1.37.0"), "FO4_NG")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_NG"

    @pytest.mark.unit
    def test_valid_version_fo4_vr(self):
        """Test valid version check for FO4_VR."""
        result = check_crashgen_version(Version("1.37.0"), "FO4_VR")
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_VR"

    @pytest.mark.unit
    def test_outdated_version_fo4_og(self):
        """Test outdated version check for FO4_OG."""
        result = check_crashgen_version(Version("1.26.0"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.OUTDATED
        assert "outdated" in result.message.lower()

    @pytest.mark.unit
    def test_outdated_version_fo4_ng(self):
        """Test outdated version check for FO4_NG."""
        result = check_crashgen_version(Version("1.28.6"), "FO4_NG")
        # 1.28.6 is valid for OG but not for NG (which only has 1.37.0)
        assert result.status == CrashgenVersionStatus.OUTDATED

    @pytest.mark.unit
    def test_newer_than_known_version(self):
        """Test version newer than all known valid versions."""
        result = check_crashgen_version(Version("1.40.0"), "FO4_OG")
        assert result.status == CrashgenVersionStatus.NEWER_THAN_KNOWN
        assert "newer" in result.message.lower()

    @pytest.mark.unit
    def test_no_supported_version_fo4_ae(self):
        """Test no supported version for FO4_AE."""
        result = check_crashgen_version(Version("1.28.6"), "FO4_AE")
        assert result.status == CrashgenVersionStatus.NO_SUPPORTED_VERSION
        assert result.valid_versions == ()

    @pytest.mark.unit
    def test_unknown_game_version_id(self):
        """Test with unknown game version ID."""
        result = check_crashgen_version(Version("1.28.6"), "NONEXISTENT")
        # Should return NO_SUPPORTED_VERSION since version ID not found
        assert result.status == CrashgenVersionStatus.NO_SUPPORTED_VERSION


class TestCheckCrashgenVersionForDetectedGame:
    """Test check_crashgen_version_for_detected_game function."""

    @pytest.mark.unit
    def test_detected_game_og_valid_crashgen(self):
        """Test detecting OG game version with valid crashgen."""
        result = check_crashgen_version_for_detected_game(
            detected_crashgen=Version("1.28.6"),
            detected_game_version=Version("1.10.163.0"),
            is_vr=False,
        )
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_OG"

    @pytest.mark.unit
    def test_detected_game_ng_valid_crashgen(self):
        """Test detecting NG game version with valid crashgen."""
        result = check_crashgen_version_for_detected_game(
            detected_crashgen=Version("1.37.0"),
            detected_game_version=Version("1.10.984.0"),
            is_vr=False,
        )
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_NG"

    @pytest.mark.unit
    def test_detected_game_vr_valid_crashgen(self):
        """Test detecting VR game version with valid crashgen."""
        result = check_crashgen_version_for_detected_game(
            detected_crashgen=Version("1.37.0"),
            detected_game_version=Version("1.2.72.0"),
            is_vr=True,
        )
        assert result.status == CrashgenVersionStatus.VALID
        assert result.game_version_id == "FO4_VR"

    @pytest.mark.unit
    def test_detected_game_og_outdated_crashgen(self):
        """Test detecting OG game version with outdated crashgen."""
        result = check_crashgen_version_for_detected_game(
            detected_crashgen=Version("1.26.0"),
            detected_game_version=Version("1.10.163.0"),
            is_vr=False,
        )
        assert result.status == CrashgenVersionStatus.OUTDATED

    @pytest.mark.unit
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

    @pytest.mark.unit
    def test_og_has_multiple_crashgen_versions(self):
        """Test that FO4_OG has multiple valid crashgen versions."""
        registry = get_version_registry()
        og = registry.get_by_id("FO4_OG")

        assert og is not None
        assert og.crashgen_versions is not None
        assert len(og.crashgen_versions) >= 2
        assert "1.28.6" in og.crashgen_versions
        assert "1.37.0" in og.crashgen_versions

    @pytest.mark.unit
    def test_ng_has_single_crashgen_version(self):
        """Test that FO4_NG has a single valid crashgen version."""
        registry = get_version_registry()
        ng = registry.get_by_id("FO4_NG")

        assert ng is not None
        assert ng.crashgen_versions is not None
        assert "1.37.0" in ng.crashgen_versions

    @pytest.mark.unit
    def test_ae_has_no_crashgen_versions(self):
        """Test that FO4_AE has no supported crashgen versions."""
        registry = get_version_registry()
        ae = registry.get_by_id("FO4_AE")

        assert ae is not None
        assert ae.crashgen_versions == ()

    @pytest.mark.unit
    def test_vr_has_crashgen_version(self):
        """Test that FO4_VR has valid crashgen version."""
        registry = get_version_registry()
        vr = registry.get_by_id("FO4_VR")

        assert vr is not None
        assert vr.crashgen_versions is not None
        assert "1.37.0" in vr.crashgen_versions


class TestRegistryGetCrashgenVersions:
    """Test VersionRegistry helper methods for crashgen versions."""

    @pytest.mark.unit
    def test_get_crashgen_versions_by_id(self):
        """Test getting crashgen versions by version ID."""
        registry = get_version_registry()

        og_versions = registry.get_crashgen_versions("FO4_OG")
        ng_versions = registry.get_crashgen_versions("FO4_NG")
        ae_versions = registry.get_crashgen_versions("FO4_AE")

        assert len(og_versions) >= 2
        assert len(ng_versions) >= 1
        assert len(ae_versions) == 0

    @pytest.mark.unit
    def test_get_crashgen_versions_nonexistent(self):
        """Test getting crashgen versions for non-existent version ID."""
        registry = get_version_registry()
        versions = registry.get_crashgen_versions("NONEXISTENT")

        assert versions == ()

    @pytest.mark.unit
    def test_get_crashgen_versions_for_detected(self):
        """Test getting crashgen versions for detected game version."""
        registry = get_version_registry()

        og_versions = registry.get_crashgen_versions_for_detected(Version("1.10.163.0"), "Fallout4", is_vr=False)
        assert len(og_versions) >= 2

        ng_versions = registry.get_crashgen_versions_for_detected(Version("1.10.984.0"), "Fallout4", is_vr=False)
        assert len(ng_versions) >= 1


class TestCustomCrashgenName:
    """Test custom crashgen names in messages."""

    @pytest.mark.unit
    def test_custom_crashgen_name_in_message(self):
        """Test that custom crashgen name appears in message."""
        result = check_crashgen_version(
            Version("1.28.6"),
            "FO4_OG",
            crashgen_name="Custom Crashgen",
        )
        assert "Custom Crashgen" in result.message

    @pytest.mark.unit
    def test_default_crashgen_name_in_message(self):
        """Test that default crashgen name (Buffout 4) appears in message."""
        result = check_crashgen_version(Version("1.28.6"), "FO4_OG")
        assert "Buffout 4" in result.message
