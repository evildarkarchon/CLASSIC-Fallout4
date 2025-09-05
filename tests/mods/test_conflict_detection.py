"""
Tests for detecting conflicts between mods.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from typing import Any

import pytest

from ClassicLib.ScanLog.DetectMods import detect_mods_double
from ClassicLib.ScanLog.ReportFragment import ReportFragment


class TestConflictDetection:
    """Tests for mod conflict detection functionality."""

    def test_no_conflicts_found(self, sample_conflict_dict: dict[str, str]) -> None:
        """Test when no conflicting mods are found."""
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "unrelated_plugin.esp": "01"}

        result: ReportFragment = detect_mods_double(sample_conflict_dict, crashlog_plugins)

        assert not result.has_content
        assert len(result.content) == 0

    def test_single_conflict_found(self) -> None:
        """Test when a single conflicting mod pair is found."""
        yaml_dict: dict[str, str] = {"mod1 | mod2": "Conflict warning"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "mod2_plugin.esp": "01"}

        result: ReportFragment = detect_mods_double(yaml_dict, crashlog_plugins)

        assert result.has_content
        result_list = result.to_list()
        assert "[!] CAUTION" in result_list[0]
        assert "Conflict warning" in "".join(result_list)

    def test_multiple_conflicts_found(self) -> None:
        """Test when multiple conflicting mod pairs are found."""
        yaml_dict: dict[str, str] = {"mod1 | mod2": "Conflict warning 1", "mod3 | mod4": "Conflict warning 2"}
        crashlog_plugins: dict[str, str] = {
            "mod1_plugin.esp": "00",
            "mod2_plugin.esp": "01",
            "mod3_plugin.esp": "02",
            "mod4_plugin.esp": "03",
        }

        result: ReportFragment = detect_mods_double(yaml_dict, crashlog_plugins)

        assert result.has_content
        result_list = result.to_list()
        assert "[!] CAUTION" in result_list[0]

    def test_case_insensitivity(self) -> None:
        """Test case insensitivity in conflicting mod detection."""
        yaml_dict: dict[str, str] = {"MOD1 | mod2": "Conflict warning"}
        crashlog_plugins: dict[str, str] = {"Mod1_Plugin.esp": "00", "Mod2_Plugin.esp": "01"}

        result: ReportFragment = detect_mods_double(yaml_dict, crashlog_plugins)

        assert result.has_content
        result_list = result.to_list()
        assert "[!] CAUTION" in result_list[0]
        assert "Conflict warning" in "".join(result_list)

    def test_partial_conflict_pair_present(self) -> None:
        """Test when only one mod from a conflict pair is present."""
        yaml_dict: dict[str, str] = {"mod1 | mod2": "Conflict warning"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "unrelated_plugin.esp": "01"}

        result: ReportFragment = detect_mods_double(yaml_dict, crashlog_plugins)

        # Should not detect conflict if only one mod is present
        assert not result.has_content
        assert len(result.content) == 0

    def test_invalid_mod_pair_format(self) -> None:
        """Test error handling when mod pair format is invalid."""
        yaml_dict: dict[str, str] = {"mod1mod2": "Invalid format"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "mod2_plugin.esp": "01"}

        with pytest.raises(ValueError) as excinfo:  # type: ignore  # noqa: PT011
            detect_mods_double(yaml_dict, crashlog_plugins)
        assert "not enough values to unpack" in str(excinfo.value)

    def test_empty_yaml_dict(self, empty_crashlog_plugins: dict[str, str]) -> None:
        """Test with empty YAML dictionary."""
        yaml_dict: dict[Any, Any] = {}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "mod2_plugin.esp": "01"}

        result: ReportFragment = detect_mods_double(yaml_dict, crashlog_plugins)

        assert not result.has_content
        assert len(result.content) == 0

    def test_empty_crashlog_plugins(self, sample_conflict_dict: dict[str, str], empty_crashlog_plugins: dict[str, str]) -> None:
        """Test with empty crashlog plugins."""
        result: ReportFragment = detect_mods_double(sample_conflict_dict, empty_crashlog_plugins)

        assert not result.has_content
        assert len(result.content) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
