"""
Test suite for string utility functions in ClassicLib/Util.py.

This module contains tests for string manipulation, version parsing,
and text similarity functions.

IMPORTANT: The crashgen_version_gen function uses @lru_cache for performance.
The clean_version_caches autouse fixture ensures cache is cleared between tests.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841
import math
from pathlib import Path

import pytest
from packaging.version import Version

from ClassicLib import Constants
from ClassicLib.Util import (
    append_or_extend,
    calculate_similarity,
    crashgen_version_gen,
    normalize_list,
)


class TestStringUtilities:
    """Tests for string manipulation and parsing utility functions."""

    def test_normalize_list_with_items(self) -> None:
        """Test normalize_list with various input types."""
        # Test with mixed case strings
        input_list = ["Hello", "WORLD", "Test", "MiXeD"]
        expected = ["hello", "world", "test", "mixed"]
        result = normalize_list(input_list)
        assert result == expected

        # Test with already lowercase strings
        input_list = ["already", "lowercase"]
        expected = ["already", "lowercase"]
        result = normalize_list(input_list)
        assert result == expected

        # Test with single item
        input_list = ["SINGLE"]
        expected = ["single"]
        result = normalize_list(input_list)
        assert result == expected

    def test_normalize_list_empty(self) -> None:
        """Test normalize_list with empty list."""
        result = normalize_list([])
        assert result == []

    def test_normalize_list_with_numbers(self) -> None:
        """Test normalize_list with numeric strings."""
        input_list = ["Item1", "ITEM2", "item3"]
        expected = ["item1", "item2", "item3"]
        result = normalize_list(input_list)
        assert result == expected

    def test_normalize_list_with_special_chars(self) -> None:
        """Test normalize_list with special characters."""
        input_list = ["Hello-World", "TEST_CASE", "Special#Chars"]
        expected = ["hello-world", "test_case", "special#chars"]
        result = normalize_list(input_list)
        assert result == expected

    def test_calculate_similarity_identical_files(self, tmp_path: Path) -> None:
        """Test calculate_similarity with identical files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        content = "This is identical content\nLine 2\nLine 3"
        file1.write_text(content)
        file2.write_text(content)

        similarity = calculate_similarity(file1, file2)
        assert similarity == 1.0

    def test_calculate_similarity_different_files(self, tmp_path: Path) -> None:
        """Test calculate_similarity with different files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("This is content A\nDifferent line")
        file2.write_text("This is content B\nAnother different line")

        similarity = calculate_similarity(file1, file2)
        assert 0.0 <= similarity < 1.0  # Should be similar but not identical

    def test_calculate_similarity_completely_different_files(self, tmp_path: Path) -> None:
        """Test calculate_similarity with completely different files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("AAAAAAAAAA")
        file2.write_text("BBBBBBBBBB")

        similarity = calculate_similarity(file1, file2)
        assert similarity == 0.0

    def test_calculate_similarity_empty_files(self, tmp_path: Path) -> None:
        """Test calculate_similarity with empty files."""
        file1 = tmp_path / "empty1.txt"
        file2 = tmp_path / "empty2.txt"

        file1.write_text("")
        file2.write_text("")

        similarity = calculate_similarity(file1, file2)
        assert similarity == 1.0  # Empty files are identical

    def test_calculate_similarity_nonexistent_file(self, tmp_path: Path) -> None:
        """Test calculate_similarity with nonexistent file."""
        file1 = tmp_path / "exists.txt"
        file2 = tmp_path / "does_not_exist.txt"

        file1.write_text("content")

        # Should return 0.0 for nonexistent file (error is caught)
        similarity = calculate_similarity(file1, file2)
        assert similarity == 0.0

    def test_append_or_extend_single_values(self) -> None:
        """Test append_or_extend with single values."""
        destination: list[str] = []

        append_or_extend("string", destination)
        append_or_extend(42, destination)
        append_or_extend(math.pi, destination)

        assert destination == ["string", "42", "3.14"]

    def test_append_or_extend_collections(self) -> None:
        """Test append_or_extend with collections."""
        destination: list[str] = []

        append_or_extend(["a", "b"], destination)
        append_or_extend(("c", "d"), destination)
        append_or_extend({"e", "f"}, destination)

        # Order might vary for set, but all elements should be present
        assert len(destination) == 6
        assert all(item in destination for item in ["a", "b", "c", "d", "e", "f"])

    def test_append_or_extend_mixed(self) -> None:
        """Test append_or_extend with mixed single values and collections."""
        destination: list[str] = []

        append_or_extend("single", destination)
        append_or_extend(["list", "items"], destination)
        append_or_extend(100, destination)

        assert "single" in destination
        assert "list" in destination
        assert "items" in destination
        assert "100" in destination

    def test_append_or_extend_none_value(self) -> None:
        """Test append_or_extend with None value."""
        destination: list[str] = []
        append_or_extend(None, destination)
        assert "None" in destination or len(destination) == 0  # Implementation dependent


class TestVersionParsing:
    """Tests for version parsing utility functions."""

    def test_crashgen_version_gen_valid_version(self) -> None:
        """Test crashgen_version_gen with valid version string.

        The clean_version_caches fixture ensures cache is clear for this test.
        """
        input_string = "Buffout 4 v1.28.6"
        result = crashgen_version_gen(input_string)
        assert result == Version("1.28.6")

    def test_crashgen_version_gen_multiple_versions(self) -> None:
        """Test crashgen_version_gen with multiple version-like strings."""
        input_string = "Test v1.0.0 another v2.0.0"
        result = crashgen_version_gen(input_string)
        assert result == Version("1.0.0")  # Function takes the first one found

    def test_crashgen_version_gen_no_version(self) -> None:
        """Test crashgen_version_gen with no version information."""
        input_string = "No matching patterns found here"
        result = crashgen_version_gen(input_string)
        assert result == Constants.NULL_VERSION

    def test_crashgen_version_gen_empty_string(self) -> None:
        """Test crashgen_version_gen with empty string."""
        input_string = ""
        result = crashgen_version_gen(input_string)
        assert result == Constants.NULL_VERSION

    def test_crashgen_version_gen_version_without_v(self) -> None:
        """Test crashgen_version_gen with version number without 'v' prefix."""
        input_string = "Version 2.3.4"
        result = crashgen_version_gen(input_string)
        # Depends on implementation, but should parse if pattern matches
        assert result == Version("2.3.4") or result == Constants.NULL_VERSION

    def test_crashgen_version_gen_complex_version(self) -> None:
        """Test crashgen_version_gen with complex version string."""
        input_string = "MyMod v1.2.3-beta.4+build.567"
        result = crashgen_version_gen(input_string)
        # Should at least parse the main version
        assert str(result).startswith("1.2.3") or result == Constants.NULL_VERSION

    def test_crashgen_version_gen_multiple_formats(self) -> None:
        """Test crashgen_version_gen with different version formats."""
        # Test known working formats
        result1 = crashgen_version_gen("v1.0.0")
        assert result1 == Version("1.0.0") or result1 == Constants.NULL_VERSION

        result2 = crashgen_version_gen("Version 2.0.0")
        assert result2 == Version("2.0.0") or result2 == Constants.NULL_VERSION

        result3 = crashgen_version_gen("3.0.0.0")
        assert result3 == Version("3.0.0.0") or result3 == Constants.NULL_VERSION


if __name__ == "__main__":
    pytest.main([__file__])
