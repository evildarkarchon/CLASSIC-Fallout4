"""
Tests for mod metadata extraction and important mod detection.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from typing import Any

import pytest

from ClassicLib.ScanLog.DetectMods import detect_mods_important
from ClassicLib.ScanLog.ReportFragment import ReportFragment


class TestImportantModDetection:
    """Tests for important mod detection with GPU compatibility."""

    def test_mod_installed_with_matching_gpu(self, sample_important_dict: dict[str, str]) -> None:
        """Test when an important mod is installed and GPU matches."""
        crashlog_plugins: dict[str, str] = {"important_mod_plugin.esp": "00"}
        gpu_rival: str = "nvidia"

        result: ReportFragment = detect_mods_important(sample_important_dict, crashlog_plugins, gpu_rival)  # type: ignore[arg-type]

        assert result.has_content
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

        # The implementation always adds a header, so it has content
        assert result.has_content
        report_str = "".join(result.to_list())
        # Should just have header with no specific mod warnings
        assert "### Checking for Important Mods" in report_str

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

        # The implementation always adds a header
        assert result.has_content
        report_str = "".join(result.to_list())
        assert "### Checking for Important Mods" in report_str

    def test_empty_crashlog_plugins(self, sample_important_dict: dict[str, str]) -> None:
        """Test with empty crashlog plugins."""
        crashlog_plugins: dict[str, str] = {}

        result: ReportFragment = detect_mods_important(sample_important_dict, crashlog_plugins, None)

        # The implementation always adds a header
        assert result.has_content
        report_str = "".join(result.to_list())
        assert "### Checking for Important Mods" in report_str

    def test_malformed_mod_entry_format(self) -> None:
        """Test with malformed mod entry format (no separator)."""
        yaml_dict: dict[str, str] = {"ImportantMod": "This is an important mod"}
        crashlog_plugins: dict[str, str] = {"important_mod_plugin.esp": "00"}

        with pytest.raises(ValueError) as excinfo:  # type: ignore  # noqa: PT011
            detect_mods_important(yaml_dict, crashlog_plugins, None)

        assert "not enough values to unpack" in str(excinfo.value)

    def test_multiple_important_mods(self, sample_important_dict: dict[str, str]) -> None:
        """Test detecting multiple important mods."""
        crashlog_plugins: dict[str, str] = {
            "important_mod_plugin.esp": "00",
            "nvidia_mod_plugin.esp": "01",
            "amd_mod_plugin.esp": "02",
        }
        gpu_rival: str = "nvidia"

        result: ReportFragment = detect_mods_important(sample_important_dict, crashlog_plugins, gpu_rival)  # type: ignore[arg-type]

        assert result.has_content
        report_str = "".join(result.to_list())
        # Should detect all three important mods
        assert "Important Mod is installed" in report_str
        assert "NVIDIA Mod is installed" in report_str
        assert "AMD Mod is installed" in report_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
