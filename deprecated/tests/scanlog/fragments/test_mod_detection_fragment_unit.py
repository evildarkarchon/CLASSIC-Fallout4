"""Unit tests for ClassicLib.scanning.logs.reporting.mod_detection module.

This module tests the mod detection fragment generation utilities:
- detect_mods_single_fragment
- generate_mod_check_header_fragment
"""

import pytest

pytestmark = [pytest.mark.unit]

from ClassicLib.scanning.logs.reporting.mod_detection import (
    detect_mods_single_fragment,
    generate_mod_check_header_fragment,
)


class TestDetectModsSingleFragment:
    """Tests for detect_mods_single_fragment function."""

    def test_returns_empty_fragment_when_no_mods_found(self) -> None:
        """Test returns empty fragment when no matching mods are found."""
        yaml_dict = {"ModA": "Warning for ModA", "ModB": "Warning for ModB"}
        crashlog_plugins = {"unrelated.esp": "00", "other.esp": "01"}

        result = detect_mods_single_fragment(yaml_dict, crashlog_plugins)

        assert not result.has_content

    def test_detects_single_mod(self) -> None:
        """Test detects a single matching mod."""
        yaml_dict = {"TestMod": "Warning: TestMod may cause issues"}
        crashlog_plugins = {"TestMod.esp": "00", "other.esp": "01"}

        result = detect_mods_single_fragment(yaml_dict, crashlog_plugins)

        assert result.has_content
        content = "".join(result.to_list())
        assert "Warning: TestMod may cause issues" in content

    def test_detects_multiple_mods(self) -> None:
        """Test detects multiple matching mods."""
        yaml_dict = {
            "ModA": "Warning for ModA",
            "ModB": "Warning for ModB",
            "ModC": "Warning for ModC",
        }
        crashlog_plugins = {"ModA.esp": "00", "ModB.esp": "01", "unrelated.esp": "02"}

        result = detect_mods_single_fragment(yaml_dict, crashlog_plugins)

        assert result.has_content
        content = "".join(result.to_list())
        assert "Warning for ModA" in content
        assert "Warning for ModB" in content
        assert "Warning for ModC" not in content

    def test_case_insensitive_matching(self) -> None:
        """Test case insensitive mod matching."""
        yaml_dict = {"TESTMOD": "Warning for TESTMOD"}
        crashlog_plugins = {"testmod.esp": "00"}

        result = detect_mods_single_fragment(yaml_dict, crashlog_plugins)

        assert result.has_content

    def test_partial_name_matching(self) -> None:
        """Test partial name matching works."""
        yaml_dict = {"TestMod": "Warning for TestMod"}
        crashlog_plugins = {"TestMod_Extended_v2.esp": "00"}

        result = detect_mods_single_fragment(yaml_dict, crashlog_plugins)

        assert result.has_content

    def test_pipe_separated_key_not_matched_as_literal(self) -> None:
        """Test pipe-separated key is treated as literal in single detection.

        The Rust detect_mods_single treats the entire key as a literal pattern
        (not splitting on ' | '). So 'PluginA | PluginB' is never matched
        against individual plugin names.
        """
        yaml_dict = {"PluginA | PluginB": "Warning: Both plugins required"}
        crashlog_plugins = {"PluginA.esp": "00", "PluginB.esp": "01"}

        result = detect_mods_single_fragment(yaml_dict, crashlog_plugins)

        # Rust treats the full key as a single pattern -- no plugin name contains "plugina | pluginb"
        assert not result.has_content

    def test_empty_yaml_dict(self) -> None:
        """Test with empty YAML dictionary."""
        yaml_dict: dict[str, str] = {}
        crashlog_plugins = {"SomeMod.esp": "00"}

        result = detect_mods_single_fragment(yaml_dict, crashlog_plugins)

        assert not result.has_content

    def test_empty_crashlog_plugins(self) -> None:
        """Test with empty crashlog plugins."""
        yaml_dict = {"TestMod": "Warning for TestMod"}
        crashlog_plugins: dict[str, str] = {}

        result = detect_mods_single_fragment(yaml_dict, crashlog_plugins)

        assert not result.has_content

    def test_warning_format(self) -> None:
        """Test that warnings include Rust formatting.

        The Rust implementation uses '[!] FOUND' format instead of emoji.
        """
        yaml_dict = {"TestMod": "Test warning message"}
        crashlog_plugins = {"TestMod.esp": "00"}

        result = detect_mods_single_fragment(yaml_dict, crashlog_plugins)

        content = "".join(result.to_list())
        assert "[!] FOUND" in content
        assert "Test warning message" in content


class TestGenerateModCheckHeaderFragment:
    """Tests for generate_mod_check_header_fragment function."""

    def test_generates_header_with_check_type(self) -> None:
        """Test generates correct header with check type."""
        result = generate_mod_check_header_fragment("Cause Crashes")

        assert len(result) == 1
        assert "### Checking For Mods That Cause Crashes" in result[0]

    def test_header_is_markdown_format(self) -> None:
        """Test header uses markdown heading format."""
        result = generate_mod_check_header_fragment("Have Known Issues")

        assert result[0].startswith("### ")

    def test_header_ends_with_double_newline(self) -> None:
        """Test header ends with double newline for markdown spacing."""
        result = generate_mod_check_header_fragment("Are Outdated")

        assert result[0].endswith("\n\n")

    def test_returns_tuple(self) -> None:
        """Test returns a tuple."""
        result = generate_mod_check_header_fragment("Test")

        assert isinstance(result, tuple)
        assert len(result) == 1

    def test_different_check_types(self) -> None:
        """Test various check type values."""
        check_types = [
            "May Cause Crashes",
            "Are Incompatible",
            "Need Updates",
            "Should Be Removed",
        ]

        for check_type in check_types:
            result = generate_mod_check_header_fragment(check_type)
            assert f"That {check_type}" in result[0]
