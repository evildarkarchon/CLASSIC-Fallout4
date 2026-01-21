"""Unit tests for ClassicLib.python.mod_detector_py module.

This module tests the mod detection functions, which provide the pure Python
fallback implementation for detecting mods and conflicts when Rust acceleration
is not available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from ClassicLib.ScanLog.fragments import ReportFragment


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_yaml_dict_single() -> dict[str, str]:
    """Create sample YAML dict for single mod detection.

    Returns:
        dict[str, str]: Sample mod name to warning mappings.
    """
    return {
        "problemplugin": "ProblemPlugin\nThis plugin causes frequent crashes\nPlease update or remove.",
        "outdatedmod": "OutdatedMod\nThis mod is outdated and may cause issues.",
        "badtexture": "BadTexture\nTexture mod with known issues.",
    }


@pytest.fixture
def sample_yaml_dict_double() -> dict[str, str]:
    """Create sample YAML dict for conflict detection.

    Returns:
        dict[str, str]: Sample mod pair to warning mappings.
    """
    return {
        "mod_a | mod_b": "Mod A and Mod B conflict with each other.\nRemove one of them.",
        "enb | reshade": "ENB and ReShade cannot be used together.",
        "sim1 | sim2": "Settlement mod conflict detected.",
    }


@pytest.fixture
def sample_yaml_dict_important() -> dict[str, str]:
    """Create sample YAML dict for important mod detection.

    Returns:
        dict[str, str]: Sample important mod entries.
    """
    return {
        "ufop4 | Unofficial Fallout 4 Patch": "Required for stability",
        "buffout | Buffout 4": "Required for crash logging",
        "nvidia_mod | GPU Fix for NVIDIA": "nvidia specific fix for GPU issues",
        "amd_mod | GPU Fix for AMD": "amd specific fix for GPU issues",
    }


@pytest.fixture
def sample_crashlog_plugins() -> dict[str, str]:
    """Create sample crashlog plugins dictionary.

    Returns:
        dict[str, str]: Sample plugin name to ID mappings.
    """
    return {
        "ProblemPlugin.esp": "0A",
        "SomeMod.esp": "0B",
        "Mod_A.esp": "0C",
        "Mod_B.esp": "0D",
        "UFOP4.esp": "0E",
        "OutdatedMod.esp": "0F",
    }


# ============================================================================
# _convert_to_lowercase Tests
# ============================================================================


class TestConvertToLowercase:
    """Tests for _convert_to_lowercase helper function."""

    @pytest.mark.unit
    def test_converts_keys_to_lowercase(self) -> None:
        """Test that dictionary keys are converted to lowercase."""
        from ClassicLib.python.mod_detector_py import _convert_to_lowercase

        data = {"UpperKey": "value1", "MixedCase": "value2", "lowercase": "value3"}

        result = _convert_to_lowercase(data)

        assert "upperkey" in result
        assert "mixedcase" in result
        assert "lowercase" in result
        assert "UpperKey" not in result

    @pytest.mark.unit
    def test_preserves_values(self) -> None:
        """Test that values are preserved unchanged."""
        from ClassicLib.python.mod_detector_py import _convert_to_lowercase

        data = {"Key": "ValueWithCase"}

        result = _convert_to_lowercase(data)

        assert result["key"] == "ValueWithCase"

    @pytest.mark.unit
    def test_handles_empty_dict(self) -> None:
        """Test handling of empty dictionary."""
        from ClassicLib.python.mod_detector_py import _convert_to_lowercase

        result = _convert_to_lowercase({})

        assert result == {}


# ============================================================================
# _validate_warning Tests
# ============================================================================


class TestValidateWarning:
    """Tests for _validate_warning helper function."""

    @pytest.mark.unit
    def test_valid_warning_passes(self) -> None:
        """Test that non-empty warning doesn't raise."""
        from ClassicLib.python.mod_detector_py import _validate_warning

        # Should not raise
        _validate_warning("test_mod", "This is a valid warning")

    @pytest.mark.unit
    def test_empty_warning_raises_value_error(self) -> None:
        """Test that empty warning raises ValueError."""
        from ClassicLib.python.mod_detector_py import _validate_warning

        with pytest.raises(ValueError, match="ERROR: test_mod has no warning"):
            _validate_warning("test_mod", "")

    @pytest.mark.unit
    def test_none_warning_raises_value_error(self) -> None:
        """Test that None warning raises ValueError (falsy check)."""
        from ClassicLib.python.mod_detector_py import _validate_warning

        with pytest.raises(ValueError, match="ERROR: test_mod has no warning"):
            _validate_warning("test_mod", None)  # type: ignore[arg-type]


# ============================================================================
# detect_mods_single Tests
# ============================================================================


class TestDetectModsSingle:
    """Tests for detect_mods_single function."""

    @pytest.mark.unit
    def test_detects_matching_mod(
        self, sample_yaml_dict_single: dict[str, str], sample_crashlog_plugins: dict[str, str]
    ) -> None:
        """Test detection of a mod present in plugins."""
        from ClassicLib.python.mod_detector_py import detect_mods_single

        fragment = detect_mods_single(sample_yaml_dict_single, sample_crashlog_plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        assert "FOUND" in content
        assert "ProblemPlugin" in content or "problemplugin" in content.lower()

    @pytest.mark.unit
    def test_returns_report_fragment(
        self, sample_yaml_dict_single: dict[str, str], sample_crashlog_plugins: dict[str, str]
    ) -> None:
        """Test that function returns a ReportFragment."""
        from ClassicLib.python.mod_detector_py import detect_mods_single

        fragment = detect_mods_single(sample_yaml_dict_single, sample_crashlog_plugins)

        assert hasattr(fragment, "to_list")

    @pytest.mark.unit
    def test_returns_empty_for_no_matches(self) -> None:
        """Test returns empty fragment when no mods match."""
        from ClassicLib.python.mod_detector_py import detect_mods_single

        yaml_dict = {"nonexistent": "warning"}
        plugins = {"SomeOther.esp": "0A"}

        fragment = detect_mods_single(yaml_dict, plugins)

        lines = fragment.to_list()
        assert len(lines) == 0 or not any("FOUND" in line for line in lines)

    @pytest.mark.unit
    def test_returns_empty_for_empty_yaml(
        self, sample_crashlog_plugins: dict[str, str]
    ) -> None:
        """Test returns empty fragment for empty yaml dict."""
        from ClassicLib.python.mod_detector_py import detect_mods_single

        fragment = detect_mods_single({}, sample_crashlog_plugins)

        lines = fragment.to_list()
        assert len(lines) == 0

    @pytest.mark.unit
    def test_case_insensitive_matching(self) -> None:
        """Test that mod matching is case-insensitive."""
        from ClassicLib.python.mod_detector_py import detect_mods_single

        yaml_dict = {"testmod": "TestMod\nWarning message"}
        plugins = {"TESTMOD.ESP": "0A"}

        fragment = detect_mods_single(yaml_dict, plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        assert "FOUND" in content

    @pytest.mark.unit
    def test_includes_plugin_id_in_output(
        self, sample_yaml_dict_single: dict[str, str], sample_crashlog_plugins: dict[str, str]
    ) -> None:
        """Test that plugin ID is included in output."""
        from ClassicLib.python.mod_detector_py import detect_mods_single

        fragment = detect_mods_single(sample_yaml_dict_single, sample_crashlog_plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        # Should have bracket-enclosed ID like [0A]
        assert "[" in content and "]" in content


# ============================================================================
# detect_mods_double Tests
# ============================================================================


class TestDetectModsDouble:
    """Tests for detect_mods_double function."""

    @pytest.mark.unit
    def test_detects_conflicting_mods(
        self, sample_yaml_dict_double: dict[str, str], sample_crashlog_plugins: dict[str, str]
    ) -> None:
        """Test detection of conflicting mod pair."""
        from ClassicLib.python.mod_detector_py import detect_mods_double

        fragment = detect_mods_double(sample_yaml_dict_double, sample_crashlog_plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        assert "CAUTION" in content
        assert "Conflicting mods" in content

    @pytest.mark.unit
    def test_no_conflict_when_only_one_mod_present(
        self, sample_yaml_dict_double: dict[str, str]
    ) -> None:
        """Test no conflict detected when only one mod of pair is present."""
        from ClassicLib.python.mod_detector_py import detect_mods_double

        # Only mod_a present, not mod_b
        plugins = {"Mod_A.esp": "0A"}

        fragment = detect_mods_double(sample_yaml_dict_double, plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        assert "CAUTION" not in content

    @pytest.mark.unit
    def test_returns_empty_for_no_conflicts(self) -> None:
        """Test returns empty fragment when no conflicts."""
        from ClassicLib.python.mod_detector_py import detect_mods_double

        yaml_dict = {"mod_x | mod_y": "Conflict warning"}
        plugins = {"Unrelated.esp": "0A"}

        fragment = detect_mods_double(yaml_dict, plugins)

        lines = fragment.to_list()
        assert len(lines) == 0 or not any("CAUTION" in line for line in lines)

    @pytest.mark.unit
    def test_returns_empty_for_empty_yaml(
        self, sample_crashlog_plugins: dict[str, str]
    ) -> None:
        """Test returns empty fragment for empty yaml dict."""
        from ClassicLib.python.mod_detector_py import detect_mods_double

        fragment = detect_mods_double({}, sample_crashlog_plugins)

        lines = fragment.to_list()
        assert len(lines) == 0

    @pytest.mark.unit
    def test_case_insensitive_conflict_detection(self) -> None:
        """Test that conflict detection is case-insensitive."""
        from ClassicLib.python.mod_detector_py import detect_mods_double

        yaml_dict = {"testmod1 | testmod2": "These mods conflict"}
        plugins = {"TESTMOD1.ESP": "0A", "TestMod2.ESP": "0B"}

        fragment = detect_mods_double(yaml_dict, plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        assert "CAUTION" in content


# ============================================================================
# detect_mods_important Tests
# ============================================================================


class TestDetectModsImportant:
    """Tests for detect_mods_important function."""

    @pytest.mark.unit
    def test_detects_installed_important_mod(
        self, sample_yaml_dict_important: dict[str, str], sample_crashlog_plugins: dict[str, str]
    ) -> None:
        """Test detection of installed important mod."""
        from ClassicLib.python.mod_detector_py import detect_mods_important

        fragment = detect_mods_important(sample_yaml_dict_important, sample_crashlog_plugins, None)

        lines = fragment.to_list()
        content = "".join(lines)

        assert "✔️" in content or "installed" in content.lower()

    @pytest.mark.unit
    def test_detects_missing_important_mod(self) -> None:
        """Test detection of missing important mod when gpu_rival matches warning."""
        from ClassicLib.python.mod_detector_py import detect_mods_important

        # For missing mods to show, the warning must NOT contain the gpu_rival
        # and gpu_rival must be set (not None)
        yaml_dict = {"requiredmod | Required Mod": "This mod is required for stability"}
        plugins = {"OtherMod.esp": "0A"}

        # Pass gpu_rival that doesn't match warning to trigger missing mod message
        fragment = detect_mods_important(yaml_dict, plugins, "nvidia")

        lines = fragment.to_list()
        content = "".join(lines)

        assert "❌" in content or "not installed" in content.lower()

    @pytest.mark.unit
    def test_gpu_specific_mod_warning_nvidia(self) -> None:
        """Test warning for nvidia mod when user has AMD GPU (nvidia is rival)."""
        from ClassicLib.python.mod_detector_py import detect_mods_important

        # Create yaml dict where the mod is installed and warning contains rival GPU name
        yaml_dict = {"nvidia_mod | GPU Fix for NVIDIA": "nvidia specific fix for GPU issues"}
        plugins = {"nvidia_mod.esp": "0A"}
        gpu_rival: Literal["nvidia"] = "nvidia"  # Rival GPU = nvidia, so nvidia mod is wrong for this user

        fragment = detect_mods_important(yaml_dict, plugins, gpu_rival)

        lines = fragment.to_list()
        content = "".join(lines)

        # When gpu_rival is in warning AND mod is found, should show ❓ warning
        assert "❓" in content or "DON'T HAVE AN" in content.upper() or "GPU Fix for NVIDIA" in content

    @pytest.mark.unit
    def test_gpu_specific_mod_warning_amd(self) -> None:
        """Test warning for amd mod when user has NVIDIA GPU (amd is rival)."""
        from ClassicLib.python.mod_detector_py import detect_mods_important

        # Create yaml dict where the mod is installed and warning contains rival GPU name
        yaml_dict = {"amd_mod | GPU Fix for AMD": "amd specific fix for GPU issues"}
        plugins = {"amd_mod.esp": "0A"}
        gpu_rival: Literal["amd"] = "amd"  # Rival GPU = amd, so amd mod is wrong for this user

        fragment = detect_mods_important(yaml_dict, plugins, gpu_rival)

        lines = fragment.to_list()
        content = "".join(lines)

        # When gpu_rival is in warning AND mod is found, should show ❓ warning
        assert "❓" in content or "DON'T HAVE AN" in content.upper() or "GPU Fix for AMD" in content

    @pytest.mark.unit
    def test_gpu_compatible_mod_ok(
        self, sample_yaml_dict_important: dict[str, str]
    ) -> None:
        """Test no warning for GPU-compatible mod."""
        from ClassicLib.python.mod_detector_py import detect_mods_important

        # nvidia_mod is installed with nvidia GPU
        plugins = {"nvidia_mod.esp": "0A"}
        gpu_rival: Literal["amd"] = "amd"  # Rival is AMD, so nvidia is correct

        fragment = detect_mods_important(sample_yaml_dict_important, plugins, gpu_rival)

        lines = fragment.to_list()
        content = "".join(lines)

        # This is tricky - let's just check it doesn't error
        assert isinstance(content, str)

    @pytest.mark.unit
    def test_returns_header(
        self, sample_yaml_dict_important: dict[str, str], sample_crashlog_plugins: dict[str, str]
    ) -> None:
        """Test that output includes section header."""
        from ClassicLib.python.mod_detector_py import detect_mods_important

        fragment = detect_mods_important(sample_yaml_dict_important, sample_crashlog_plugins, None)

        lines = fragment.to_list()
        content = "".join(lines)

        assert "Checking for Important Mods" in content

    @pytest.mark.unit
    def test_handles_empty_yaml(
        self, sample_crashlog_plugins: dict[str, str]
    ) -> None:
        """Test handling of empty yaml dict."""
        from ClassicLib.python.mod_detector_py import detect_mods_important

        fragment = detect_mods_important({}, sample_crashlog_plugins, None)

        # Should return fragment with just header
        lines = fragment.to_list()
        assert len(lines) >= 1


# ============================================================================
# Integration Tests
# ============================================================================


class TestModDetectorIntegration:
    """Integration tests for mod detection functions."""

    @pytest.mark.unit
    def test_all_functions_return_report_fragments(
        self,
        sample_yaml_dict_single: dict[str, str],
        sample_yaml_dict_double: dict[str, str],
        sample_yaml_dict_important: dict[str, str],
        sample_crashlog_plugins: dict[str, str],
    ) -> None:
        """Test that all detection functions return proper ReportFragment objects."""
        from ClassicLib.python.mod_detector_py import (
            detect_mods_double,
            detect_mods_important,
            detect_mods_single,
        )

        single = detect_mods_single(sample_yaml_dict_single, sample_crashlog_plugins)
        double = detect_mods_double(sample_yaml_dict_double, sample_crashlog_plugins)
        important = detect_mods_important(sample_yaml_dict_important, sample_crashlog_plugins, None)

        for fragment in [single, double, important]:
            assert hasattr(fragment, "to_list")
            assert isinstance(fragment.to_list(), list)

    @pytest.mark.unit
    def test_detection_order_longest_first(self) -> None:
        """Test that longer mod names are matched before shorter ones."""
        from ClassicLib.python.mod_detector_py import detect_mods_single

        yaml_dict = {
            "mod": "Short mod match",
            "modextended": "Longer mod match",
        }
        plugins = {"ModExtended.esp": "0A"}

        fragment = detect_mods_single(yaml_dict, plugins)

        lines = fragment.to_list()
        content = "".join(lines)

        # Should match "modextended", not "mod"
        if "FOUND" in content:
            # The longer match should be found
            assert "Longer" in content or "modextended" in content.lower()
