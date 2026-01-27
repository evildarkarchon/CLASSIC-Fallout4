"""Unit tests for ClassicLib.scanning.game.WryeCheck module.

This module tests the Wrye Bash plugin checker report parsing functionality,
including HTML parsing, section extraction, and message formatting.

Following TDD methodology - tests written to define expected behavior.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup
from ClassicLib.scanning.game.WryeCheck import (
    extract_plugins_from_section,
    format_section_header,
    parse_wrye_report,
    scan_wryecheck,
)

pytestmark = pytest.mark.unit


# ==============================================================================
# format_section_header Tests
# ==============================================================================


class TestFormatSectionHeader:
    """Tests for the format_section_header function."""

    def test_format_section_header_returns_string(self) -> None:
        """format_section_header should return a string."""
        result = format_section_header("Test")

        assert isinstance(result, str)

    def test_format_section_header_adds_padding_for_short_titles(self) -> None:
        """format_section_header should add equal sign padding for short titles."""
        result = format_section_header("Test")

        assert "=" in result
        assert "Test" in result

    def test_format_section_header_centers_title(self) -> None:
        """format_section_header should center the title between equal signs."""
        result = format_section_header("Short")

        # Should have equal signs on both sides
        parts = result.split("Short")
        assert len(parts) == 2
        # Both sides should have equal signs
        assert "=" in parts[0]
        assert "=" in parts[1]

    def test_format_section_header_returns_title_unchanged_when_32_chars_or_more(self) -> None:
        """format_section_header should return title unchanged when >= 32 chars."""
        long_title = "A" * 35
        result = format_section_header(long_title)

        assert result == long_title

    def test_format_section_header_handles_empty_string(self) -> None:
        """format_section_header should handle empty string."""
        result = format_section_header("")

        assert isinstance(result, str)
        assert "=" in result

    def test_format_section_header_has_correct_padding_calculation(self) -> None:
        """format_section_header should correctly calculate left and right padding."""
        title = "X" * 10  # 10 chars
        result = format_section_header(title)

        # diff = 32 - 10 = 22
        # left = 11, right = 11
        # Pattern: \n   ={left} {title} ={right}\n
        assert "=" * 11 in result

    def test_format_section_header_handles_odd_length_padding(self) -> None:
        """format_section_header should handle odd length padding correctly."""
        title = "X" * 11  # diff = 21, left = 10, right = 11
        result = format_section_header(title)

        assert title in result
        assert "=" in result

    def test_format_section_header_includes_newlines(self) -> None:
        """format_section_header should include newlines for formatting."""
        result = format_section_header("Test")

        assert "\n" in result


# ==============================================================================
# extract_plugins_from_section Tests
# ==============================================================================


class TestExtractPluginsFromSection:
    """Tests for the extract_plugins_from_section function."""

    def test_extract_plugins_returns_list(self) -> None:
        """extract_plugins_from_section should return a list."""
        html = "<html><h3>Section</h3></html>"
        soup = BeautifulSoup(html, "html.parser")
        section = soup.find("h3")

        result = extract_plugins_from_section(section)

        assert isinstance(result, list)

    def test_extract_plugins_finds_esp_files(self) -> None:
        """extract_plugins_from_section should find .esp files."""
        html = """<html>
            <h3>Section</h3>
            <p>• TestMod.esp</p>
        </html>"""
        soup = BeautifulSoup(html, "html.parser")
        section = soup.find("h3")

        result = extract_plugins_from_section(section)

        assert len(result) == 1
        assert "TestMod.esp" in result[0]

    def test_extract_plugins_finds_esm_files(self) -> None:
        """extract_plugins_from_section should find .esm files."""
        html = """<html>
            <h3>Section</h3>
            <p>• TestMaster.esm</p>
        </html>"""
        soup = BeautifulSoup(html, "html.parser")
        section = soup.find("h3")

        result = extract_plugins_from_section(section)

        assert len(result) == 1
        assert "TestMaster.esm" in result[0]

    def test_extract_plugins_finds_esl_files(self) -> None:
        """extract_plugins_from_section should find .esl files."""
        html = """<html>
            <h3>Section</h3>
            <p>• TestLight.esl</p>
        </html>"""
        soup = BeautifulSoup(html, "html.parser")
        section = soup.find("h3")

        result = extract_plugins_from_section(section)

        assert len(result) == 1
        assert "TestLight.esl" in result[0]

    def test_extract_plugins_ignores_non_plugin_paragraphs(self) -> None:
        """extract_plugins_from_section should ignore paragraphs without plugin extensions."""
        html = """<html>
            <h3>Section</h3>
            <p>This is just text without plugins</p>
            <p>• TestMod.esp</p>
        </html>"""
        soup = BeautifulSoup(html, "html.parser")
        section = soup.find("h3")

        result = extract_plugins_from_section(section)

        assert len(result) == 1
        assert "TestMod.esp" in result[0]

    def test_extract_plugins_stops_at_next_section(self) -> None:
        """extract_plugins_from_section should stop at the next h3 section."""
        html = """<html>
            <h3>Section1</h3>
            <p>• First.esp</p>
            <h3>Section2</h3>
            <p>• Second.esp</p>
        </html>"""
        soup = BeautifulSoup(html, "html.parser")
        sections = soup.find_all("h3")
        section1 = sections[0]

        result = extract_plugins_from_section(section1)

        # Should only include First.esp, not Second.esp
        assert len(result) == 1
        assert "First.esp" in result[0]

    def test_extract_plugins_strips_bullet_formatting(self) -> None:
        """extract_plugins_from_section should strip bullet point formatting."""
        html = """<html>
            <h3>Section</h3>
            <p>•\xa0 TestMod.esp</p>
        </html>"""
        soup = BeautifulSoup(html, "html.parser")
        section = soup.find("h3")

        result = extract_plugins_from_section(section)

        assert len(result) == 1
        assert result[0] == "TestMod.esp"

    def test_extract_plugins_handles_multiple_plugins(self) -> None:
        """extract_plugins_from_section should handle multiple plugins."""
        html = """<html>
            <h3>Section</h3>
            <p>• First.esp</p>
            <p>• Second.esm</p>
            <p>• Third.esl</p>
        </html>"""
        soup = BeautifulSoup(html, "html.parser")
        section = soup.find("h3")

        result = extract_plugins_from_section(section)

        assert len(result) == 3

    def test_extract_plugins_returns_empty_for_no_plugins(self) -> None:
        """extract_plugins_from_section should return empty list when no plugins found."""
        html = """<html>
            <h3>Section</h3>
            <p>No plugins here</p>
        </html>"""
        soup = BeautifulSoup(html, "html.parser")
        section = soup.find("h3")

        result = extract_plugins_from_section(section)

        assert len(result) == 0


# ==============================================================================
# parse_wrye_report Tests
# ==============================================================================


class TestParseWryeReport:
    """Tests for the parse_wrye_report function."""

    @patch("ClassicLib.scanning.game.WryeCheck.read_file_sync")
    def test_parse_wrye_report_returns_list(self, mock_read: MagicMock, tmp_path: Path) -> None:
        """parse_wrye_report should return a list of strings."""
        report_path = tmp_path / "report.html"
        report_path.touch()
        mock_read.return_value = "<html></html>"

        result = parse_wrye_report(report_path, {})

        assert isinstance(result, list)

    @patch("ClassicLib.scanning.game.WryeCheck.read_file_sync")
    def test_parse_wrye_report_processes_h3_sections(self, mock_read: MagicMock, tmp_path: Path) -> None:
        """parse_wrye_report should process h3 sections."""
        report_path = tmp_path / "report.html"
        report_path.touch()
        mock_read.return_value = """<html>
            <h3>Test Section</h3>
            <p>• TestMod.esp</p>
        </html>"""

        result = parse_wrye_report(report_path, {})

        # Should contain section header and plugin
        result_text = "".join(result)
        assert "Test Section" in result_text
        assert "TestMod.esp" in result_text

    @patch("ClassicLib.scanning.game.WryeCheck.read_file_sync")
    def test_parse_wrye_report_skips_active_plugins_section(self, mock_read: MagicMock, tmp_path: Path) -> None:
        """parse_wrye_report should skip the Active Plugins section header."""
        report_path = tmp_path / "report.html"
        report_path.touch()
        mock_read.return_value = """<html>
            <h3>Active Plugins:</h3>
            <p>• TestMod.esp</p>
        </html>"""

        result = parse_wrye_report(report_path, {})

        # Should not list plugins from Active Plugins section
        result_text = "".join(result)
        # The section header should be skipped, but we shouldn't have the formatted header
        assert "=" not in result_text or "Active Plugins" not in result_text

    @patch("ClassicLib.scanning.game.WryeCheck.read_file_sync")
    def test_parse_wrye_report_handles_esl_capable_section(self, mock_read: MagicMock, tmp_path: Path) -> None:
        """parse_wrye_report should add special message for ESL Capable section."""
        report_path = tmp_path / "report.html"
        report_path.touch()
        mock_read.return_value = """<html>
            <h3>ESL Capable</h3>
            <p>• Mod1.esp</p>
            <p>• Mod2.esp</p>
        </html>"""

        result = parse_wrye_report(report_path, {})

        result_text = "".join(result)
        assert "ESL flag" in result_text
        assert "SimpleESLify" in result_text
        assert "2" in result_text  # Number of plugins

    @patch("ClassicLib.scanning.game.WryeCheck.read_file_sync")
    def test_parse_wrye_report_includes_matching_warnings(self, mock_read: MagicMock, tmp_path: Path) -> None:
        """parse_wrye_report should include warnings that match section titles."""
        report_path = tmp_path / "report.html"
        report_path.touch()
        mock_read.return_value = """<html>
            <h3>Merged Patches</h3>
            <p>• TestMod.esp</p>
        </html>"""
        wrye_warnings = {"Merged": "Warning about merged patches!"}

        result = parse_wrye_report(report_path, wrye_warnings)

        result_text = "".join(result)
        assert "Warning about merged patches!" in result_text

    @patch("ClassicLib.scanning.game.WryeCheck.read_file_sync")
    def test_parse_wrye_report_lists_plugins_in_non_special_sections(self, mock_read: MagicMock, tmp_path: Path) -> None:
        """parse_wrye_report should list plugins in non-special sections."""
        report_path = tmp_path / "report.html"
        report_path.touch()
        mock_read.return_value = """<html>
            <h3>Dirty Plugins</h3>
            <p>• DirtyMod.esp</p>
        </html>"""

        result = parse_wrye_report(report_path, {})

        result_text = "".join(result)
        # The output includes the plugin name with formatting
        assert "DirtyMod.esp" in result_text
        assert ">" in result_text  # Plugin is listed with > prefix


# ==============================================================================
# scan_wryecheck Tests
# ==============================================================================


class TestScanWryecheck:
    """Tests for the scan_wryecheck function."""

    @patch("ClassicLib.scanning.game.WryeCheck.GlobalRegistry")
    @patch("ClassicLib.scanning.game.WryeCheck.yaml_settings")
    def test_scan_wryecheck_returns_string(self, mock_yaml: MagicMock, mock_registry: MagicMock) -> None:
        """scan_wryecheck should return a string."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Warn_WRYE_MissingHTML" in key_path:
                return "Missing HTML warning"
            if "Docs_File_WryeBashPC" in key_path:
                return None  # No report path - triggers missing warning
            if "Warnings_WRYE" in key_path:
                return {}
            return None

        mock_yaml.side_effect = yaml_side_effect

        result = scan_wryecheck()

        assert isinstance(result, str)

    @patch("ClassicLib.scanning.game.WryeCheck.GlobalRegistry")
    @patch("ClassicLib.scanning.game.WryeCheck.yaml_settings")
    def test_scan_wryecheck_returns_warning_when_report_missing(self, mock_yaml: MagicMock, mock_registry: MagicMock) -> None:
        """scan_wryecheck should return warning when report file is missing."""
        mock_registry.get_vr.return_value = ""
        mock_registry.get_game.return_value = "Fallout4"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Warn_WRYE_MissingHTML" in key_path:
                return "⚠️ Wrye Bash report not found!"
            if "Docs_File_WryeBashPC" in key_path:
                return None  # No report path
            if "Warnings_WRYE" in key_path:
                return {}
            return None

        mock_yaml.side_effect = yaml_side_effect

        result = scan_wryecheck()

        assert "not found" in result

    @patch("ClassicLib.scanning.game.WryeCheck.yaml_settings")
    def test_scan_wryecheck_raises_value_error_when_warning_missing(self, mock_yaml: MagicMock) -> None:
        """scan_wryecheck should raise ValueError when warning setting is missing."""

        def yaml_side_effect(_type, _store, key_path, *args):
            if "Warn_WRYE_MissingHTML" in key_path:
                return None  # Missing HTML warning
            if "Docs_File_WryeBashPC" in key_path:
                return None  # No report path
            if "Warnings_WRYE" in key_path:
                return None  # No warnings dict
            return None

        mock_yaml.side_effect = yaml_side_effect

        with pytest.raises(ValueError, match="Warnings_WRYE missing"):
            scan_wryecheck()

    @patch("ClassicLib.scanning.game.WryeCheck.parse_wrye_report")
    @patch("ClassicLib.scanning.game.WryeCheck.yaml_settings")
    def test_scan_wryecheck_analyzes_report_when_found(self, mock_yaml: MagicMock, mock_parse: MagicMock, tmp_path: Path) -> None:
        """scan_wryecheck should analyze the report when it exists."""
        report_path = tmp_path / "ModChecker.html"
        report_path.write_text("<html></html>")

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Warn_WRYE_MissingHTML" in key_path:
                return "Missing HTML warning"
            if "Docs_File_WryeBashPC" in key_path:
                return report_path
            if "Warnings_WRYE" in key_path:
                return {}
            return None

        mock_yaml.side_effect = yaml_side_effect
        mock_parse.return_value = ["Parsed content"]

        result = scan_wryecheck()

        mock_parse.assert_called_once()
        assert "WRYE BASH PLUGIN CHECKER REPORT WAS FOUND" in result

    @patch("ClassicLib.scanning.game.WryeCheck.parse_wrye_report")
    @patch("ClassicLib.scanning.game.WryeCheck.yaml_settings")
    def test_scan_wryecheck_includes_resource_links(self, mock_yaml: MagicMock, mock_parse: MagicMock, tmp_path: Path) -> None:
        """scan_wryecheck should include resource links in output."""
        report_path = tmp_path / "ModChecker.html"
        report_path.write_text("<html></html>")

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Warn_WRYE_MissingHTML" in key_path:
                return "Missing HTML warning"
            if "Docs_File_WryeBashPC" in key_path:
                return report_path
            if "Warnings_WRYE" in key_path:
                return {}
            return None

        mock_yaml.side_effect = yaml_side_effect
        mock_parse.return_value = []

        result = scan_wryecheck()

        assert "nexusmods.com" in result
        assert "wrye-bash.github.io" in result

    @patch("ClassicLib.scanning.game.WryeCheck.GlobalRegistry")
    @patch("ClassicLib.scanning.game.WryeCheck.parse_wrye_report")
    @patch("ClassicLib.scanning.game.WryeCheck.yaml_settings")
    def test_scan_wryecheck_includes_game_name_in_message(
        self, mock_yaml: MagicMock, mock_parse: MagicMock, mock_registry: MagicMock, tmp_path: Path
    ) -> None:
        """scan_wryecheck should include game name in output message."""
        report_path = tmp_path / "ModChecker.html"
        report_path.write_text("<html></html>")
        mock_registry.get_game.return_value = "Fallout4"
        mock_registry.get_vr.return_value = ""

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Warn_WRYE_MissingHTML" in key_path:
                return "Missing HTML warning"
            if "Docs_File_WryeBashPC" in key_path:
                return report_path
            if "Warnings_WRYE" in key_path:
                return {}
            return None

        mock_yaml.side_effect = yaml_side_effect
        mock_parse.return_value = []

        result = scan_wryecheck()

        assert "Fallout4" in result
