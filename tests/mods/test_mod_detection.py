"""
Tests for finding and identifying mods in crash logs.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from typing import Any

import pytest
from ClassicLib.ScanLog.ReportFragment import ReportFragment

from ClassicLib.ScanLog.DetectMods import _convert_to_lowercase, _validate_warning, detect_mods_single


class TestHelperFunctions:
    """Tests for helper functions used in mod detection."""

    def test_convert_to_lowercase_empty_dict(self) -> None:
        """Test conversion of an empty dict."""
        result: dict[str, str] = _convert_to_lowercase({})
        assert result == {}

    def test_convert_to_lowercase_keys(self) -> None:
        """Test conversion of dictionary with lowercase keys."""
        input_dict: dict[str, str] = {"key1": "value1", "key2": "value2"}
        result: dict[str, str] = _convert_to_lowercase(input_dict)
        assert result == input_dict

    def test_convert_to_lowercase_mixed_case_keys(self) -> None:
        """Test conversion of dictionary with mixed case keys."""
        input_dict: dict[str, str] = {"Key1": "value1", "KEY2": "value2", "key3": "value3"}
        result: dict[str, str] = _convert_to_lowercase(input_dict)
        assert result == {"key1": "value1", "key2": "value2", "key3": "value3"}

    def test_convert_to_lowercase_special_characters(self) -> None:
        """Test conversion of dictionary with special characters in keys."""
        input_dict: dict[str, str] = {"MOD-Name": "value1", "Mod_NAME": "value2"}
        result: dict[str, str] = _convert_to_lowercase(input_dict)
        assert result == {"mod-name": "value1", "mod_name": "value2"}

    def test_validate_warning_valid(self) -> None:
        """Test validation of a valid warning message."""
        # This should not raise an error
        _validate_warning("test_mod", "This is a warning message")

    def test_validate_warning_empty(self) -> None:
        """Test validation of an empty warning message."""
        with pytest.raises(ValueError) as excinfo:  # type: ignore  # noqa: PT011
            _validate_warning("test_mod", "")
        assert "test_mod has no warning" in str(excinfo.value)

    def test_validate_warning_none(self) -> None:
        """Test validation with None as warning message."""
        with pytest.raises(ValueError) as excinfo:  # type: ignore  # noqa: PT011
            _validate_warning("test_mod", None)  # type: ignore[arg-type]
        assert "test_mod has no warning" in str(excinfo.value)


class TestSingleModDetection:
    """Tests for single mod detection functionality."""

    def test_no_mods_found(self, sample_yaml_dict: dict[str, str]) -> None:
        """Test when no mods are found in the crash log plugins."""
        crashlog_plugins: dict[str, str] = {"unrelated_plugin.esp": "00", "another_plugin.esp": "01"}

        result: ReportFragment = detect_mods_single(sample_yaml_dict, crashlog_plugins)

        assert not result.has_content
        assert len(result.content) == 0

    def test_single_mod_found(self) -> None:
        """Test when a single mod is found in the crash log plugins."""
        yaml_dict: dict[str, str] = {"mod1": "Warning for mod1", "mod2": "Warning for mod2"}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00", "unrelated_plugin.esp": "01"}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)

        assert result.has_content
        result_text = "".join(result.to_list())
        assert "[!] FOUND" in result_text
        assert "Warning for mod1" in result_text

    def test_multiple_mods_found(self, sample_yaml_dict: dict[str, str], sample_crashlog_plugins: dict[str, str]) -> None:
        """Test when multiple mods are found in the crash log plugins."""
        result: ReportFragment = detect_mods_single(sample_yaml_dict, sample_crashlog_plugins)

        assert result.has_content
        result_text = "".join(result.to_list())
        assert "[!] FOUND" in result_text

    def test_case_insensitivity(self) -> None:
        """Test case insensitivity in mod detection."""
        yaml_dict: dict[str, str] = {"MOD1": "Warning for mod1", "mod2": "Warning for mod2"}
        crashlog_plugins: dict[str, str] = {"Mod1_Plugin.esp": "00", "unrelated_plugin.esp": "01"}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)

        assert result.has_content
        result_text = "".join(result.to_list())
        assert "[!] FOUND" in result_text
        assert "Warning for mod1" in result_text

    def test_empty_yaml_dict(self) -> None:
        """Test with empty YAML dictionary."""
        yaml_dict: dict[Any, Any] = {}
        crashlog_plugins: dict[str, str] = {"mod1_plugin.esp": "00"}

        result: ReportFragment = detect_mods_single(yaml_dict, crashlog_plugins)

        assert not result.has_content
        assert len(result.content) == 0

    def test_empty_crashlog_plugins(self, sample_yaml_dict: dict[str, str], empty_crashlog_plugins: dict[str, str]) -> None:
        """Test with empty crashlog plugins."""
        result: ReportFragment = detect_mods_single(sample_yaml_dict, empty_crashlog_plugins)

        assert not result.has_content
        assert len(result.content) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
