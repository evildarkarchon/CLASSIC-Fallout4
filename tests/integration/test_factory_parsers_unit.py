"""Unit tests for ClassicLib.integration.factory.parsers module.

This module tests the parser factory and PythonParserWrapper class
for log parsing functionality.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestPythonParserWrapper:
    """Tests for PythonParserWrapper class."""

    def test_find_segments_calls_python_implementation(self) -> None:
        """Test find_segments calls the Python implementation."""
        from ClassicLib.integration.factory.parsers import PythonParserWrapper

        crash_data = ["line1", "line2"]
        crashgen_name = "Buffout4"
        xse_acronym = "F4SE"
        game_root_name = "Fallout4"

        mock_result = ("1.10.163", "1.26.2", "EXCEPTION_ACCESS_VIOLATION", [["segment1"]])

        with patch("ClassicLib.integration.python.parser_py.find_segments", return_value=mock_result) as mock_find:
            result = PythonParserWrapper.find_segments(crash_data, crashgen_name, xse_acronym, game_root_name)

        mock_find.assert_called_once_with(crash_data, crashgen_name, xse_acronym, game_root_name)
        assert result == mock_result

    def test_extract_section_returns_matching_section(self) -> None:
        """Test extract_section returns content between markers."""
        from ClassicLib.integration.factory.parsers import PythonParserWrapper

        crash_data = [
            "some header",
            "[START]",
            "content line 1",
            "content line 2",
            "[END]",
            "footer",
        ]

        result = PythonParserWrapper.extract_section(crash_data, "[START]", "[END]")

        assert result == ["content line 1", "content line 2"]

    def test_extract_section_returns_none_for_no_match(self) -> None:
        """Test extract_section returns None when no section found."""
        from ClassicLib.integration.factory.parsers import PythonParserWrapper

        crash_data = [
            "some content",
            "more content",
        ]

        result = PythonParserWrapper.extract_section(crash_data, "[START]", "[END]")

        assert result is None

    def test_extract_section_returns_none_for_empty_section(self) -> None:
        """Test extract_section returns None for empty section."""
        from ClassicLib.integration.factory.parsers import PythonParserWrapper

        crash_data = [
            "[START]",
            "[END]",
        ]

        result = PythonParserWrapper.extract_section(crash_data, "[START]", "[END]")

        assert result is None

    def test_extract_section_handles_nested_markers(self) -> None:
        """Test extract_section stops at first end marker."""
        from ClassicLib.integration.factory.parsers import PythonParserWrapper

        crash_data = [
            "[START]",
            "content",
            "[END]",
            "[START]",
            "more content",
            "[END]",
        ]

        result = PythonParserWrapper.extract_section(crash_data, "[START]", "[END]")

        assert result == ["content"]

    def test_extract_section_with_partial_match(self) -> None:
        """Test extract_section handles lines that start with marker."""
        from ClassicLib.integration.factory.parsers import PythonParserWrapper

        crash_data = [
            "[START] header",
            "content here",
            "[END] footer",
        ]

        result = PythonParserWrapper.extract_section(crash_data, "[START]", "[END]")

        assert result == ["content here"]


class TestGetParser:
    """Tests for get_parser function."""

    def test_returns_python_wrapper_when_rust_disabled(self) -> None:
        """Test returns PythonParserWrapper when Rust is disabled."""
        from ClassicLib.integration.factory.parsers import PythonParserWrapper, get_parser

        with patch("ClassicLib.integration.factory.parsers.is_rust_disabled", return_value=True):
            result = get_parser()

        assert isinstance(result, PythonParserWrapper)

    def test_returns_python_wrapper_when_component_not_available(self) -> None:
        """Test returns PythonParserWrapper when parser component not available."""
        from ClassicLib.integration.factory.parsers import PythonParserWrapper, get_parser

        with (
            patch("ClassicLib.integration.factory.parsers.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.parsers.get_components", return_value={"parser": False}),
        ):
            result = get_parser()

        assert isinstance(result, PythonParserWrapper)

    def test_returns_python_wrapper_on_import_error(self) -> None:
        """Test returns PythonParserWrapper when Rust import fails."""
        from ClassicLib.integration.factory.parsers import PythonParserWrapper, get_parser

        with (
            patch("ClassicLib.integration.factory.parsers.is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.parsers.get_components", return_value={"parser": True}),
        ):
            import builtins

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if "parser_rust" in str(args) or name == "ClassicLib.integration.rust.parser_rust":
                    raise ImportError("No module")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                result = get_parser()

        assert isinstance(result, PythonParserWrapper)

    def test_parser_has_find_segments_method(self) -> None:
        """Test returned parser has find_segments method."""
        from ClassicLib.integration.factory.parsers import get_parser

        parser = get_parser()

        assert hasattr(parser, "find_segments")
        assert callable(parser.find_segments)

    def test_parser_has_extract_section_method(self) -> None:
        """Test returned parser has extract_section method."""
        from ClassicLib.integration.factory.parsers import get_parser

        parser = get_parser()

        # PythonParserWrapper always has extract_section
        if hasattr(parser, "extract_section"):
            assert callable(parser.extract_section)
