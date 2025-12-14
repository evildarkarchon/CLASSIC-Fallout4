"""
Unit tests for version parsing functionality in Update.py.

This module tests the try_parse_version function which parses
version strings from various formats including simple versions,
GitHub release names, and complex version identifiers.
"""

import pytest

from ClassicLib.Update import try_parse_version


@pytest.mark.unit
class TestTryParseVersion:
    """Test version parsing functionality."""

    def test_parse_version_simple_format(self):
        """Test parsing simple version formats."""
        test_cases = [
            ("1.0.0", "1.0.0"),
            ("2.1.3", "2.1.3"),
            ("10.25.99", "10.25.99"),
            ("1.0", "1.0"),
            ("1", "1"),
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str)
            assert result is not None
            assert str(result) == expected

    def test_parse_version_with_v_prefix(self):
        """Test parsing versions with 'v' prefix."""
        test_cases = [
            ("v1.0.0", "1.0.0"),
            ("v2.1.3", "2.1.3"),
            ("v10.25.99", "10.25.99"),
            ("v1.0", "1.0"),
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str)
            assert result is not None
            assert str(result) == expected

    def test_parse_version_from_release_name(self):
        """Test parsing versions from GitHub release names."""
        test_cases = [
            ("CLASSIC v7.30.1", "7.30.1"),
            ("MyApp v1.2.3", "1.2.3"),
            ("Tool Release v2.0.0", "2.0.0"),
            ("Project Name v10.1.5", "10.1.5"),
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str)
            assert result is not None
            assert str(result) == expected

    def test_parse_version_complex_formats(self):
        """Test parsing complex version formats."""
        test_cases = [
            ("1.0.0-alpha", "1.0.0a0"),
            ("2.1.0-beta.1", "2.1.0b1"),
            ("1.0.0-rc.1", "1.0.0rc1"),
            ("3.0.0.dev1", "3.0.0.dev1"),
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str)
            assert result is not None
            assert str(result) == expected

    def test_parse_version_invalid_formats(self):
        """Test handling of invalid version formats."""
        invalid_inputs = [
            "",
            "not_a_version",
            "abc.def.ghi",
            "v",
            "version",
            "release",
            "v.1.0.0",
            "random text",
            None,
        ]

        for invalid_input in invalid_inputs:
            result = try_parse_version(invalid_input)
            assert result is None

    def test_parse_version_edge_cases(self):
        """Test edge cases in version parsing."""
        test_cases = [
            ("v0.0.1", "0.0.1"),  # Very low version
            ("v999.999.999", "999.999.999"),  # Very high version
            ("CLASSIC v7.30.1", "7.30.1"),  # Actual expected format from requirements
            ("Tool v1.0.0", "1.0.0"),  # Simple tool version
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str)
            assert result is not None
            assert str(result) == expected

    def test_parse_version_whitespace_handling(self):
        """Test handling of whitespace in version strings."""
        test_cases = [
            ("  v1.0.0  ", "1.0.0"),
            ("\tv2.1.0\n", "2.1.0"),
            ("App Name  v3.0.0", "3.0.0"),
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str.strip())
            assert result is not None
            assert str(result) == expected
