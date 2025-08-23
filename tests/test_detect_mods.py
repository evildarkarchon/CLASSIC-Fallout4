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
        autoscan_report: list[Any] = []

        result: bool = detect_mods_single(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is False
        assert len(autoscan_report) == 0

    def test_single_mod_found(self) -> None:
        """Test when a single mod is found in the crash log plugins."""
        yaml_dict: dict[str, str] = {"mod1": "Warning for mod1", "mod2": "Warning for mod2"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "unrelated_plugin.esp": "01"}
        autoscan_report: list[Any] = []

        result: bool = detect_mods_single(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is True
        assert len(autoscan_report) == 4  # [!] FOUND + warning message + 2 newlines
        assert "[!] FOUND" in autoscan_report[0]
        assert "Warning for mod1" in autoscan_report[1]

    def test_multiple_mods_found(self) -> None:
        """Test when multiple mods are found in the crash log plugins."""
        yaml_dict: dict[str, str] = {"mod1": "Warning for mod1", "mod2": "Warning for mod2"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "mod2_plugin.esp": "01"}
        autoscan_report: list[Any] = []

        result: bool = detect_mods_single(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is True
        assert len(autoscan_report) >= 3  # [!] FOUND + 2 warnings
        assert "[!] FOUND" in autoscan_report[0]

    def test_case_insensitivity(self) -> None:
        """Test case insensitivity in mod detection."""
        yaml_dict: dict[str, str] = {"MOD1": "Warning for mod1", "mod2": "Warning for mod2"}
        crashlog_plugins: dict[str, str] = {"Mod1_Plugin.esp": "00", "unrelated_plugin.esp": "01"}
        autoscan_report: list[Any] = []

        result: bool = detect_mods_single(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is True
        assert len(autoscan_report) == 4  # [!] FOUND + warning message + 2 newlines
        assert "[!] FOUND" in autoscan_report[0]
        assert "Warning for mod1" in autoscan_report[1]

    def test_empty_yaml_dict(self) -> None:
        """Test with empty YAML dictionary."""
        yaml_dict: dict[Any, Any] = {}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00"}
        autoscan_report: list[Any] = []

        result: bool = detect_mods_single(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is False
        assert len(autoscan_report) == 0

    def test_empty_crashlog_plugins(self) -> None:
        """Test with empty crashlog plugins."""
        yaml_dict: dict[str, str] = {"mod1": "Warning for mod1"}
        crashlog_plugins: dict[str, str] = {}
        autoscan_report: list[Any] = []

        result: bool = detect_mods_single(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is False
        assert len(autoscan_report) == 0


class TestDetectModsDouble:
    """Tests for the detect_mods_double function."""

    def test_no_conflicts_found(self) -> None:
        """Test when no conflicting mods are found."""
        yaml_dict: dict[str, str] = {"mod1 | mod2": "Conflict warning"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "unrelated_plugin.esp": "01"}
        autoscan_report: list[Any] = []

        result: bool = detect_mods_double(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is False
        assert len(autoscan_report) == 0

    def test_single_conflict_found(self) -> None:
        """Test when a single conflicting mod pair is found."""
        yaml_dict: dict[str, str] = {"mod1 | mod2": "Conflict warning"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "mod2_plugin.esp": "01"}
        autoscan_report: list[Any] = []

        result: bool = detect_mods_double(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is True
        assert len(autoscan_report) == 4  # [!] CAUTION + warning message + 2 newlines
        assert "[!] CAUTION" in autoscan_report[0]
        assert "Conflict warning" in autoscan_report[1]

    def test_multiple_conflicts_found(self) -> None:
        """Test when multiple conflicting mod pairs are found."""
        yaml_dict: dict[str, str] = {"mod1 | mod2": "Conflict warning 1", "mod3 | mod4": "Conflict warning 2"}
        crashlog_plugins: dict[str, str] = {
            "mod1_plugin.esp": "00",
            "mod2_plugin.esp": "01",
            "mod3_plugin.esp": "02",
            "mod4_plugin.esp": "03",
        }
        autoscan_report: list[Any] = []

        result: bool = detect_mods_double(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is True
        assert len(autoscan_report) >= 3  # [!] FOUND + 2 warnings

    def test_case_insensitivity(self) -> None:
        """Test case insensitivity in conflicting mod detection."""
        yaml_dict: dict[str, str] = {"MOD1 | mod2": "Conflict warning"}
        crashlog_plugins: dict[str, str] = {"Mod1_Plugin.esp": "00", "Mod2_Plugin.esp": "01"}
        autoscan_report: list[Any] = []

        result: bool = detect_mods_double(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is True
        assert len(autoscan_report) == 4  # [!] CAUTION + warning message + 2 newlines
        assert "[!] CAUTION" in autoscan_report[0]
        assert "Conflict warning" in autoscan_report[1]

    def test_invalid_mod_pair_format(self) -> None:
        """Test error handling when mod pair format is invalid."""
        yaml_dict: dict[str, str] = {"mod1mod2": "Invalid format"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "mod2_plugin.esp": "01"}
        autoscan_report: list[Any] = []

        with pytest.raises(ValueError) as excinfo:  # type: ignore  # noqa: PT011
            detect_mods_double(yaml_dict, crashlog_plugins, autoscan_report)
        assert "not enough values to unpack" in str(excinfo.value)

    def test_empty_yaml_dict(self) -> None:
        """Test with empty YAML dictionary."""
        yaml_dict: dict[Any, Any] = {}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "mod2_plugin.esp": "01"}
        autoscan_report: list[Any] = []

        result: bool = detect_mods_double(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is False
        assert len(autoscan_report) == 0

    def test_empty_crashlog_plugins(self) -> None:
        """Test with empty crashlog plugins."""
        yaml_dict: dict[str, str] = {"mod1 | mod2": "Conflict warning"}
        crashlog_plugins: dict[str, str] = {}
        autoscan_report: list[Any] = []

        result: bool = detect_mods_double(yaml_dict, crashlog_plugins, autoscan_report)

        assert result is False
        assert len(autoscan_report) == 0


class TestDetectModsImportant:
    """Tests for the detect_mods_important function."""

    def test_mod_installed_with_matching_gpu(self) -> None:
        """Test when an important mod is installed and GPU matches."""
        yaml_dict: dict[str, str] = {"important_mod | Important Mod": "This is an important mod for nvidia GPUs"}
        crashlog_plugins: dict[str, str] = {"important_mod_plugin.esp": "00"}
        autoscan_report: list[Any] = []
        gpu_rival: str = "nvidia"

        detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, gpu_rival)  # type: ignore[arg-type]

        assert len(autoscan_report) >= 1
        # The actual output contains newlines and formatting, so check the entire output
        report_str = "".join(str(item) for item in autoscan_report)
        assert "Important Mod is installed" in report_str

    def test_nvidia_mod_with_amd_gpu(self) -> None:
        """Test when a NVIDIA mod is installed with an AMD GPU."""
        yaml_dict: dict[str, str] = {"nvidia_mod | NVIDIA Mod": "This mod requires an nvidia GPU"}
        crashlog_plugins: dict[str, str] = {"nvidia_mod_plugin.esp": "00"}
        autoscan_report: list[Any] = []
        gpu_rival: str = "amd"

        detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, gpu_rival)  # type: ignore[arg-type]

        assert len(autoscan_report) >= 1
        assert "NVIDIA Mod is installed" in autoscan_report[0]

    def test_amd_mod_with_nvidia_gpu(self) -> None:
        """Test when an AMD mod is installed with a NVIDIA GPU."""
        yaml_dict: dict[str, str] = {"amd_mod | AMD Mod": "This mod requires an amd GPU"}
        crashlog_plugins: dict[str, str] = {"amd_mod_plugin.esp": "00"}
        autoscan_report: list[Any] = []
        gpu_rival: str = "nvidia"

        detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, gpu_rival)  # type: ignore[arg-type]

        assert len(autoscan_report) >= 1
        assert "AMD Mod is installed" in autoscan_report[0]

    def test_missing_important_mod_with_matching_gpu(self) -> None:
        """Test when an important mod is missing and GPU matches."""
        yaml_dict: dict[str, str] = {"nvidia_mod | NVIDIA Mod": "This mod is important for nvidia GPUs"}
        crashlog_plugins: dict[str, str] = {"unrelated_plugin.esp": "00"}
        autoscan_report: list[Any] = []
        gpu_rival: str = "nvidia"

        detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, gpu_rival)  # type: ignore[arg-type]

        assert len(autoscan_report) == 0

    def test_missing_important_mod_with_nonmatching_gpu(self) -> None:
        """Test when an important mod is missing and GPU doesn't match."""
        yaml_dict: dict[str, str] = {"nvidia_mod | NVIDIA Mod": "This mod is important for nvidia GPUs"}
        crashlog_plugins: dict[str, str] = {"unrelated_plugin.esp": "00"}
        autoscan_report: list[Any] = []
        gpu_rival: str = "amd"

        detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, gpu_rival)  # type: ignore[arg-type]

        # The actual implementation adds warnings for important mods not installed
        assert "NVIDIA Mod is not installed" in str(autoscan_report)

    def test_no_gpu_rival_specified(self) -> None:
        """Test when no gpu_rival is specified."""
        yaml_dict: dict[str, str] = {"mod1 | Important Mod": "This is an important mod"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00"}
        autoscan_report: list[Any] = []

        detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, None)

        assert len(autoscan_report) >= 1
        # The actual output contains newlines and formatting, so check the entire output
        report_str = "".join(str(item) for item in autoscan_report)
        assert "Important Mod is installed" in report_str

    def test_empty_yaml_dict(self) -> None:
        """Test with empty YAML dictionary."""
        yaml_dict: dict[Any, Any] = {}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00"}
        autoscan_report: list[Any] = []

        detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, None)  # type: ignore[arg-type]

        assert len(autoscan_report) == 0

    def test_empty_crashlog_plugins(self) -> None:
        """Test with empty crashlog plugins."""
        yaml_dict: dict[str, str] = {"mod1 | Important Mod": "This is an important mod"}
        crashlog_plugins: dict[str, str] = {}
        autoscan_report: list[Any] = []

        detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, None)

        # The actual implementation doesn't add warnings for missing mods
        assert len(autoscan_report) == 0

    def test_malformed_mod_entry_format(self) -> None:
        """Test with malformed mod entry format (no separator)."""
        yaml_dict: dict[str, str] = {"ImportantMod": "This is an important mod"}
        crashlog_plugins: dict[str, str] = {"important_mod_plugin.esp": "00"}
        autoscan_report: list[Any] = []

        with pytest.raises(ValueError) as excinfo:  # type: ignore  # noqa: PT011
            detect_mods_important(yaml_dict, crashlog_plugins, autoscan_report, None)

        assert "not enough values to unpack" in str(excinfo.value)
        assert "not enough values to unpack" in str(excinfo.value)


if __name__ == "__main__":
    pytest.main()
