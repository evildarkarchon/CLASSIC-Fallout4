"""Unit tests for ClassicLib.scanning.game.wrye_check module.

This module tests the Wrye Bash plugin checker report scanning functionality.
The HTML parsing is delegated to Rust WryeBashParser; these tests verify the
Python glue layer (YAML settings resolution, file reading, message assembly).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.scanning.game.wrye_check import scan_wryecheck

pytestmark = pytest.mark.unit


# ==============================================================================
# scan_wryecheck Tests
# ==============================================================================


class TestScanWryecheck:
    """Tests for the scan_wryecheck function."""

    @patch("ClassicLib.scanning.game.wrye_check.yaml_settings")
    @patch("ClassicLib.scanning.game.wrye_check.get_game", return_value="Fallout4")
    @patch("ClassicLib.scanning.game.wrye_check.get_vr", return_value="")
    def test_returns_string(self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock) -> None:
        """scan_wryecheck should return a string."""

        def yaml_side_effect(type_arg, _store, key_path, *args):  # noqa: ARG001
            if "Warn_WRYE_MissingHTML" in key_path:
                return "Missing HTML warning"
            if "Docs_File_WryeBashPC" in key_path:
                return None  # No report path - triggers missing warning
            return None

        mock_yaml.side_effect = yaml_side_effect

        result = scan_wryecheck()

        assert isinstance(result, str)

    @patch("ClassicLib.scanning.game.wrye_check.yaml_settings")
    @patch("ClassicLib.scanning.game.wrye_check.get_game", return_value="Fallout4")
    @patch("ClassicLib.scanning.game.wrye_check.get_vr", return_value="")
    def test_returns_warning_when_report_missing(self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock) -> None:
        """scan_wryecheck should return warning when report file is missing."""

        def yaml_side_effect(type_arg, _store, key_path, *args):  # noqa: ARG001
            if "Warn_WRYE_MissingHTML" in key_path:
                return "Missing HTML warning"
            if "Docs_File_WryeBashPC" in key_path:
                return None  # No report path
            return None

        mock_yaml.side_effect = yaml_side_effect

        result = scan_wryecheck()

        assert "Missing HTML warning" in result

    @patch("ClassicLib.scanning.game.wrye_check.yaml_settings")
    def test_raises_value_error_when_warning_missing(self, mock_yaml: MagicMock) -> None:
        """scan_wryecheck should raise ValueError when warning setting is missing."""

        def yaml_side_effect(_type, _store, key_path, *args):  # noqa: ARG001
            return None

        mock_yaml.side_effect = yaml_side_effect

        with pytest.raises(ValueError, match="Warnings_WRYE missing"):
            scan_wryecheck()

    @patch("classic_scangame.WryeBashParser")
    @patch("ClassicLib.scanning.game.wrye_check._read_file")
    @patch("ClassicLib.scanning.game.wrye_check.yaml_settings")
    @patch("ClassicLib.scanning.game.wrye_check.get_game", return_value="Fallout4")
    @patch("ClassicLib.scanning.game.wrye_check.get_vr", return_value="")
    def test_delegates_to_rust_parser_when_report_found(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_read_file: MagicMock,
        mock_parser_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        """scan_wryecheck should delegate HTML parsing to Rust WryeBashParser."""
        report_path = tmp_path / "ModChecker.html"
        report_path.write_text("<html></html>")

        def yaml_side_effect(type_arg, _store, key_path, *args):  # noqa: ARG001
            if "Warn_WRYE_MissingHTML" in key_path:
                return "Missing HTML warning"
            if "Docs_File_WryeBashPC" in key_path:
                return report_path
            if "Warnings_WRYE" in key_path:
                return {"Merged": "Warning about merged patches"}
            return None

        mock_yaml.side_effect = yaml_side_effect
        mock_read_file.return_value = "<html><h3>Test</h3></html>"

        mock_parser = MagicMock()
        mock_parser.parse.return_value = []
        mock_parser_cls.return_value = mock_parser
        mock_parser_cls.format_report.return_value = "Parsed report body"

        result = scan_wryecheck()

        # Verify Rust parser was called
        mock_parser_cls.assert_called_once_with({"Merged": "Warning about merged patches"})
        mock_parser.parse.assert_called_once_with("<html><h3>Test</h3></html>")

        # Verify message structure
        assert "WRYE BASH PLUGIN CHECKER REPORT WAS FOUND" in result
        assert "Fallout4" in result

    @patch("classic_scangame.WryeBashParser")
    @patch("ClassicLib.scanning.game.wrye_check._read_file")
    @patch("ClassicLib.scanning.game.wrye_check.yaml_settings")
    @patch("ClassicLib.scanning.game.wrye_check.get_game", return_value="Fallout4")
    @patch("ClassicLib.scanning.game.wrye_check.get_vr", return_value="")
    def test_includes_resource_links(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml: MagicMock,
        mock_read_file: MagicMock,
        mock_parser_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        """scan_wryecheck should include resource links in output."""
        report_path = tmp_path / "ModChecker.html"
        report_path.write_text("<html></html>")

        def yaml_side_effect(type_arg, _store, key_path, *args):  # noqa: ARG001
            if "Warn_WRYE_MissingHTML" in key_path:
                return "Missing HTML warning"
            if "Docs_File_WryeBashPC" in key_path:
                return report_path
            if "Warnings_WRYE" in key_path:
                return {}
            return None

        mock_yaml.side_effect = yaml_side_effect
        mock_read_file.return_value = "<html></html>"

        mock_parser = MagicMock()
        mock_parser.parse.return_value = []
        mock_parser_cls.return_value = mock_parser
        mock_parser_cls.format_report.return_value = ""

        result = scan_wryecheck()

        assert "nexusmods.com" in result
        assert "wrye-bash.github.io" in result
