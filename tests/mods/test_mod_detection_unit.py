"""Tests for finding and identifying mods in crash logs."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from typing import Any

import pytest

from ClassicLib.scanning.logs.detect_mods import detect_mods_single
from ClassicLib.scanning.logs.reporting import ReportFragment

pytestmark = [pytest.mark.unit]


class TestSingleModDetection:
    """Tests for single mod detection functionality."""

    def test_no_mods_found(self, sample_yaml_dict: dict[str, str]) -> None:
        """Test when no mods are found in the crash log plugins."""
        crashlog_plugins: dict[str, str] = {"unrelated_plugin.esp": "00", "another_plugin.esp": "01"}

        result: ReportFragment = detect_mods_single(sample_yaml_dict, crashlog_plugins)  # pyright: ignore[reportAssignmentType]

        assert not result.has_content
        assert len(result.content) == 0

    def test_single_mod_found(self) -> None:
        """Test when a single mod is found in the crash log plugins."""
        yaml_dict: dict[str, str] = {"mod1": "Warning for mod1", "mod2": "Warning for mod2"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "unrelated_plugin.esp": "01"}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)  # pyright: ignore[reportAssignmentType]

        assert result.has_content
        result_text = "".join(result.to_list())
        assert "[!] FOUND" in result_text
        assert "Warning for mod1" in result_text

    def test_multiple_mods_found(self, sample_yaml_dict: dict[str, str], sample_crashlog_plugins: dict[str, str]) -> None:
        """Test when multiple mods are found in the crash log plugins."""
        result: ReportFragment = detect_mods_single(sample_yaml_dict, sample_crashlog_plugins)  # pyright: ignore[reportAssignmentType]

        assert result.has_content
        result_text = "".join(result.to_list())
        assert "[!] FOUND" in result_text

    def test_case_insensitivity(self) -> None:
        """Test case insensitivity in mod detection."""
        yaml_dict: dict[str, str] = {"MOD1": "Warning for mod1", "mod2": "Warning for mod2"}
        crashlog_plugins: dict[str, str] = {"Mod1_Plugin.esp": "00", "unrelated_plugin.esp": "01"}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)  # pyright: ignore[reportAssignmentType]

        assert result.has_content
        result_text = "".join(result.to_list())
        assert "[!] FOUND" in result_text
        assert "Warning for mod1" in result_text

    def test_empty_yaml_dict(self) -> None:
        """Test with empty YAML dictionary."""
        yaml_dict: dict[Any, Any] = {}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00"}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)  # pyright: ignore[reportAssignmentType]

        assert not result.has_content
        assert len(result.content) == 0

    def test_empty_crashlog_plugins(self, sample_yaml_dict: dict[str, str], empty_crashlog_plugins: dict[str, str]) -> None:
        """Test with empty crashlog plugins."""
        result: ReportFragment = detect_mods_single(sample_yaml_dict, empty_crashlog_plugins)  # pyright: ignore[reportAssignmentType]

        assert not result.has_content
        assert len(result.content) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
