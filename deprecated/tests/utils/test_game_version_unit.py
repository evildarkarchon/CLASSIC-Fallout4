"""
Test suite for game version detection utility functions.

This module contains tests for detecting game executable versions
using the Rust PE parser (classic_version).
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841
from pathlib import Path
from unittest.mock import patch

import pytest
from packaging.version import Version

from ClassicLib.core import constants as Constants
from ClassicLib.Utils.version_utils import read_game_exe_version

pytestmark = [pytest.mark.unit]


class TestGameVersionDetection:
    """Tests for game version detection functions."""

    def test_read_game_exe_version_invalid_path(self) -> None:
        """Test read_game_exe_version with invalid executable path."""
        nonexistent_exe = Path("nonexistent.exe")

        version = read_game_exe_version(nonexistent_exe)
        assert version == Constants.NULL_VERSION

    @patch("ClassicLib.Utils.version_utils.extract_pe_version")
    def test_read_game_exe_version_rust_success(self, mock_extract, tmp_path: Path) -> None:
        """Test read_game_exe_version with successful Rust extraction."""
        test_exe = tmp_path / "test.exe"
        test_exe.write_bytes(b"fake exe content")

        mock_extract.return_value = (1, 10, 163, 0)

        version = read_game_exe_version(test_exe)
        assert version == Version("1.10.163.0")
        mock_extract.assert_called_once_with(str(test_exe))

    @patch("ClassicLib.Utils.version_utils.extract_pe_version", side_effect=RuntimeError("PE parse failed"))
    def test_read_game_exe_version_rust_failure(self, mock_extract, tmp_path: Path) -> None:
        """Test read_game_exe_version returns NULL_VERSION when Rust extraction fails."""
        test_exe = tmp_path / "test.exe"
        test_exe.write_bytes(b"fake exe content")

        version = read_game_exe_version(test_exe)
        assert version == Constants.NULL_VERSION

    def test_read_game_exe_version_empty_file(self, tmp_path: Path) -> None:
        """Test read_game_exe_version with empty executable file."""
        test_exe = tmp_path / "empty.exe"
        test_exe.write_bytes(b"")

        version = read_game_exe_version(test_exe)
        assert version == Constants.NULL_VERSION

    def test_read_game_exe_version_with_path_object(self, tmp_path: Path) -> None:
        """Test read_game_exe_version with Path object."""
        test_exe = tmp_path / "test.exe"
        test_exe.write_bytes(b"fake exe content")

        # The function expects a Path object
        version = read_game_exe_version(test_exe)
        # Without mocking, it will return NULL_VERSION for a fake exe
        assert version == Constants.NULL_VERSION

    def test_read_game_exe_version_none_path(self) -> None:
        """Test read_game_exe_version with None path."""
        version = read_game_exe_version(None)  # type: ignore[arg-type]
        assert version == Constants.NULL_VERSION


if __name__ == "__main__":
    pytest.main([__file__])
