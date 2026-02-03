"""Unit tests for parser factory functions in ClassicLib.integration.factory.

This module tests the get_parser factory function which requires Rust.
"""

from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit]


class TestGetParser:
    """Tests for get_parser function."""

    def test_raises_runtime_error_on_import_error(self) -> None:
        """Test raises RuntimeError when Rust import fails."""
        import builtins

        from ClassicLib.integration.factory import get_parser

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "parser_rust" in str(args) or name == "ClassicLib.integration.rust.parser_rust":
                raise ImportError("No module")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(RuntimeError, match="Required Rust module for parser"):
                get_parser()

    def test_parser_has_find_segments_method(self) -> None:
        """Test returned parser has find_segments method."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        assert hasattr(parser, "find_segments")
        assert callable(parser.find_segments)

    def test_parser_has_extract_section_method(self) -> None:
        """Test returned parser has extract_section method."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        assert hasattr(parser, "extract_section")
        assert callable(parser.extract_section)

    def test_parser_is_rust_accelerated(self) -> None:
        """Test returned parser reports Rust acceleration."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        assert parser.is_rust_accelerated is True
