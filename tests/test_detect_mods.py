"""
Tests for the DetectMods module.

This module focuses on testing the functionality in ClassicLib.ScanLog.DetectMods,
which handles detection of problematic mods in crash logs.
"""

from typing import Any

import pytest

from ClassicLib.ScanLog.DetectMods import (
    _convert_to_lowercase,
    _validate_warning,
    detect_mods_double,
    detect_mods_important,
    detect_mods_single,
)
from ClassicLib.ScanLog.ReportFragment import ReportFragment


class TestConvertToLowercase:
    """Tests for the _convert_to_lowercase function."""

    def test_empty_dict(self) -> None:
        """Test conversion of an empty dict."""
        result: dict[str, str] = _convert_to_lowercase({})
        assert result == {}

    def test_lowercase_keys(self) -> None:
        """Test conversion of dictionary with lowercase keys."""
        input_dict: dict[str, str] = {"key1": "value1", "key2": "value2"}
        result: dict[str, str] = _convert_to_lowercase(input_dict)
        assert result == input_dict

    def test_mixed_case_keys(self) -> None:
        """Test conversion of dictionary with mixed case keys."""
        input_dict: dict[str, str] = {"Key1": "value1", "KEY2": "value2", "key3": "value3"}
        result: dict[str, str] = _convert_to_lowercase(input_dict)
        assert result == {"key1": "value1", "key2": "value2", "key3": "value3"}

    def test_special_characters(self) -> None:
        """Test conversion of dictionary with special characters in keys."""
        input_dict: dict[str, str] = {"MOD-Name": "value1", "Mod_NAME": "value2"}
        result: dict[str, str] = _convert_to_lowercase(input_dict)
        assert result == {"mod-name": "value1", "mod_name": "value2"}


class TestValidateWarning:
    """Tests for the _validate_warning function."""

    def test_valid_warning(self) -> None:
        """Test validation of a valid warning message."""
        # This should not raise an error
        _validate_warning("test_mod", "This is a warning message")

    def test_empty_warning(self) -> None:
        """Test validation of an empty warning message."""
        with pytest.raises(ValueError) as excinfo:  # type: ignore  # noqa: PT011
            _validate_warning("test_mod", "")
        assert "test_mod has no warning" in str(excinfo.value)

    def test_none_warning(self) -> None:
        """Test validation with None as warning message."""
        with pytest.raises(ValueError) as excinfo:  # type: ignore  # noqa: PT011
            _validate_warning("test_mod", None)  # type: ignore[arg-type]
        assert "test_mod has no warning" in str(excinfo.value)


class TestDetectModsSingle:
    """Tests for the detect_mods_single function."""

    def test_no_mods_found(self) -> None:
        """Test when no mods are found in the crash log plugins."""
        yaml_dict: dict[str, str] = {"mod1": "Warning for mod1", "mod2": "Warning for mod2"}
        crashlog_plugins: dict[str, str] = {"unrelated_plugin.esp": "00", "another_plugin.esp": "01"}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)

        assert not result.has_content
        assert len(result.content) == 0

    def test_single_mod_found(self) -> None:
        """Test when a single mod is found in the crash log plugins."""
        yaml_dict: dict[str, str] = {"mod1": "Warning for mod1", "mod2": "Warning for mod2"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "unrelated_plugin.esp": "01"}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)

        assert result.has_content
        result_list = result.to_list()
        assert "[!] FOUND" in result_list[0]
        assert "Warning for mod1" in "".join(result_list)

    def test_multiple_mods_found(self) -> None:
        """Test when multiple mods are found in the crash log plugins."""
        yaml_dict: dict[str, str] = {"mod1": "Warning for mod1", "mod2": "Warning for mod2"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "mod2_plugin.esp": "01"}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)

        assert result.has_content
        result_list = result.to_list()
        assert "[!] FOUND" in result_list[0]

    def test_case_insensitivity(self) -> None:
        """Test case insensitivity in mod detection."""
        yaml_dict: dict[str, str] = {"MOD1": "Warning for mod1", "mod2": "Warning for mod2"}
        crashlog_plugins: dict[str, str] = {"Mod1_Plugin.esp": "00", "unrelated_plugin.esp": "01"}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)

        assert result.has_content
        result_list = result.to_list()
        assert "[!] FOUND" in result_list[0]
        assert "Warning for mod1" in "".join(result_list)

    def test_empty_yaml_dict(self) -> None:
        """Test with empty YAML dictionary."""
        yaml_dict: dict[Any, Any] = {}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00"}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)

        assert not result.has_content
        assert len(result.content) == 0

    def test_empty_crashlog_plugins(self) -> None:
        """Test with empty crashlog plugins."""
        yaml_dict: dict[str, str] = {"mod1": "Warning for mod1"}
        crashlog_plugins: dict[str, str] = {}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)

        assert not result.has_content
        assert len(result.content) == 0


class TestDetectModsDouble:
    """Tests for the detect_mods_double function."""

    def test_no_conflicts_found(self) -> None:
        """Test when no conflicting mods are found."""
        yaml_dict: dict[str, str] = {"mod1 | mod2": "Conflict warning"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "unrelated_plugin.esp": "01"}

        result: ReportFragment = detect_mods_double(yaml_dict, crashlog_plugins)

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

    def test_invalid_mod_pair_format(self) -> None:
        """Test error handling when mod pair format is invalid."""
        yaml_dict: dict[str, str] = {"mod1mod2": "Invalid format"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "mod2_plugin.esp": "01"}

        with pytest.raises(ValueError) as excinfo:  # type: ignore  # noqa: PT011
            detect_mods_double(yaml_dict, crashlog_plugins)
        assert "not enough values to unpack" in str(excinfo.value)

    def test_empty_yaml_dict(self) -> None:
        """Test with empty YAML dictionary."""
        yaml_dict: dict[Any, Any] = {}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "mod2_plugin.esp": "01"}

        result: ReportFragment = detect_mods_double(yaml_dict, crashlog_plugins)

        assert not result.has_content
        assert len(result.content) == 0

    def test_empty_crashlog_plugins(self) -> None:
        """Test with empty crashlog plugins."""
        yaml_dict: dict[str, str] = {"mod1 | mod2": "Conflict warning"}
        crashlog_plugins: dict[str, str] = {}

        result: ReportFragment = detect_mods_double(yaml_dict, crashlog_plugins)

        assert not result.has_content
        assert len(result.content) == 0


class TestDetectModsImportant:
    """Tests for the detect_mods_important function."""

    def test_mod_installed_with_matching_gpu(self) -> None:
        """Test when an important mod is installed and GPU matches."""
        yaml_dict: dict[str, str] = {"important_mod | Important Mod": "This is an important mod for nvidia GPUs"}
        crashlog_plugins: dict[str, str] = {"important_mod_plugin.esp": "00"}
        gpu_rival: str = "nvidia"

        result: ReportFragment = detect_mods_important(yaml_dict, crashlog_plugins, gpu_rival)  # type: ignore[arg-type]

        assert result.has_content
        # The actual output contains newlines and formatting, so check the entire output
        report_str = "".join(result.to_list())
        assert "Important Mod is installed" in report_str

    def test_nvidia_mod_with_amd_gpu(self) -> None:
        """Test when a NVIDIA mod is installed with an AMD GPU."""
        yaml_dict: dict[str, str] = {"nvidia_mod | NVIDIA Mod": "This mod requires an nvidia GPU"}
        crashlog_plugins: dict[str, str] = {"nvidia_mod_plugin.esp": "00"}
        gpu_rival: str = "amd"

        result: ReportFragment = detect_mods_important(yaml_dict, crashlog_plugins, gpu_rival)  # type: ignore[arg-type]

        assert result.has_content
        report_str = "".join(result.to_list())
        assert "NVIDIA Mod is installed" in report_str

    def test_amd_mod_with_nvidia_gpu(self) -> None:
        """Test when an AMD mod is installed with a NVIDIA GPU."""
        yaml_dict: dict[str, str] = {"amd_mod | AMD Mod": "This mod requires an amd GPU"}
        crashlog_plugins: dict[str, str] = {"amd_mod_plugin.esp": "00"}
        gpu_rival: str = "nvidia"

        result: ReportFragment = detect_mods_important(yaml_dict, crashlog_plugins, gpu_rival)  # type: ignore[arg-type]

        assert result.has_content
        report_str = "".join(result.to_list())
        assert "AMD Mod is installed" in report_str

    def test_missing_important_mod_with_matching_gpu(self) -> None:
        """Test when an important mod is missing and GPU matches."""
        yaml_dict: dict[str, str] = {"nvidia_mod | NVIDIA Mod": "This mod is important for nvidia GPUs"}
        crashlog_plugins: dict[str, str] = {"unrelated_plugin.esp": "00"}
        gpu_rival: str = "nvidia"

        result: ReportFragment = detect_mods_important(yaml_dict, crashlog_plugins, gpu_rival)  # type: ignore[arg-type]

        # When no important mods are found in plugins, returns empty fragment
        assert not result.has_content
        assert len(result.content) == 0

    def test_missing_important_mod_with_nonmatching_gpu(self) -> None:
        """Test when an important mod is missing and GPU doesn't match."""
        yaml_dict: dict[str, str] = {"nvidia_mod | NVIDIA Mod": "This mod is important for nvidia GPUs"}
        crashlog_plugins: dict[str, str] = {"unrelated_plugin.esp": "00"}
        gpu_rival: str = "amd"

        result: ReportFragment = detect_mods_important(yaml_dict, crashlog_plugins, gpu_rival)  # type: ignore[arg-type]

        assert result.has_content
        report_str = "".join(result.to_list())
        # The actual implementation adds warnings for important mods not installed
        assert "NVIDIA Mod is not installed" in report_str or "NVIDIA Mod is missing" in report_str

    def test_no_gpu_rival_specified(self) -> None:
        """Test when no gpu_rival is specified."""
        yaml_dict: dict[str, str] = {"mod1 | Important Mod": "This is an important mod"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00"}

        result: ReportFragment = detect_mods_important(yaml_dict, crashlog_plugins, None)

        assert result.has_content
        # The actual output contains newlines and formatting, so check the entire output
        report_str = "".join(result.to_list())
        assert "Important Mod is installed" in report_str

    def test_empty_yaml_dict(self) -> None:
        """Test with empty YAML dictionary."""
        yaml_dict: dict[Any, Any] = {}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00"}

        result: ReportFragment = detect_mods_important(yaml_dict, crashlog_plugins, None)  # type: ignore[arg-type]

        # With empty yaml, returns empty fragment
        assert not result.has_content
        assert len(result.content) == 0

    def test_empty_crashlog_plugins(self) -> None:
        """Test with empty crashlog plugins."""
        yaml_dict: dict[str, str] = {"mod1 | Important Mod": "This is an important mod"}
        crashlog_plugins: dict[str, str] = {}

        result: ReportFragment = detect_mods_important(yaml_dict, crashlog_plugins, None)

        # With empty plugins, returns empty fragment
        assert not result.has_content
        assert len(result.content) == 0

    def test_malformed_mod_entry_format(self) -> None:
        """Test with malformed mod entry format (no separator)."""
        yaml_dict: dict[str, str] = {"ImportantMod": "This is an important mod"}
        crashlog_plugins: dict[str, str] = {"important_mod_plugin.esp": "00"}

        with pytest.raises(ValueError) as excinfo:  # type: ignore  # noqa: PT011
            detect_mods_important(yaml_dict, crashlog_plugins, None)

        assert "not enough values to unpack" in str(excinfo.value)


if __name__ == "__main__":
    pytest.main()
