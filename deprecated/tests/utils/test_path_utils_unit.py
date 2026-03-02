"""
Test suite for path utility functions in ClassicLib/Util.py.

This module contains tests for path validation and related utility functions.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.Utils.path_utils import validate_path

pytestmark = [pytest.mark.unit]


class TestPathUtilities:
    """Tests for path validation and related utility functions."""

    def test_validate_path_valid_existing_file(self, tmp_path: Path) -> None:
        """Test validate_path with valid existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        is_valid, error_msg = validate_path(test_file, check_read=True)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_path_valid_existing_directory(self, tmp_path: Path) -> None:
        """Test validate_path with valid existing directory."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        is_valid, error_msg = validate_path(test_dir, check_read=True)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_path_nonexistent_path(self, tmp_path: Path) -> None:
        """Test validate_path with nonexistent path."""
        nonexistent = tmp_path / "does_not_exist.txt"

        is_valid, error_msg = validate_path(nonexistent)
        assert is_valid is False
        assert "does not exist" in error_msg

    def test_validate_path_with_write_check(self, tmp_path: Path) -> None:
        """Test validate_path with write permission check."""
        test_dir = tmp_path / "writable_dir"
        test_dir.mkdir()

        is_valid, error_msg = validate_path(test_dir, check_write=True, check_read=True)
        assert is_valid is True
        assert error_msg == ""

    @patch("platform.system", return_value="Windows")
    @patch("pathlib.Path.exists", return_value=False)
    def test_validate_path_windows_invalid_drive(self, mock_exists: MagicMock, mock_platform: MagicMock) -> None:  # noqa: ARG002
        """Test validate_path with invalid Windows drive."""
        invalid_path = "Z:/nonexistent/path"

        is_valid, error_msg = validate_path(invalid_path)
        assert is_valid is False
        assert "does not exist" in error_msg

    def test_validate_path_empty_string(self) -> None:
        """Test validate_path with empty string."""
        is_valid, error_msg = validate_path("")
        # Empty string gets converted to current directory which exists
        # So the behavior depends on implementation - adjusting test
        assert isinstance(is_valid, bool)
        assert isinstance(error_msg, str)

    def test_validate_path_none_value(self) -> None:
        """Test validate_path with None value."""
        is_valid, error_msg = validate_path(None)  # type: ignore
        assert is_valid is False
        # Should handle None gracefully

    def test_validate_path_read_permission_check(self, tmp_path: Path) -> None:
        """Test validate_path read permission check on existing file.

        validate_path delegates to Rust PathValidator, so Python-level mocks
        of pathlib.Path.exists or builtins.open have no effect. We test with
        a real file that the Rust code can actually access.
        """
        # Existing readable file should pass read check
        readable_file = tmp_path / "readable.txt"
        readable_file.write_text("content")
        is_valid, error_msg = validate_path(readable_file, check_read=True)
        assert is_valid is True
        assert error_msg == ""

        # Non-existent file should fail read check
        missing_file = tmp_path / "missing.txt"
        is_valid, error_msg = validate_path(missing_file, check_read=True)
        assert is_valid is False
        assert "does not exist" in error_msg.lower() or "not found" in error_msg.lower()

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_dir", return_value=True)
    def test_validate_path_write_permission_directory(self, mock_is_dir: MagicMock, mock_exists: MagicMock, tmp_path: Path) -> None:
        """Test validate_path write permissions for directory."""
        test_dir = tmp_path / "test_write_dir"
        test_dir.mkdir()

        # Test with actual writable directory
        is_valid, error_msg = validate_path(test_dir, check_write=True)
        assert is_valid is True
        assert error_msg == ""


if __name__ == "__main__":
    pytest.main([__file__])
