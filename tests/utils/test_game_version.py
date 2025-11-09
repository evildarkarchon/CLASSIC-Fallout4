"""
Test suite for game version detection utility functions in ClassicLib/Util.py.

This module contains tests for detecting game executable versions across
different platforms.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib import Constants
from ClassicLib.Utils.version_utils import get_game_version


class TestGameVersionDetection:
    """Tests for game version detection functions."""

    def test_get_game_version_invalid_path(self) -> None:
        """Test get_game_version with invalid executable path."""
        nonexistent_exe = Path("nonexistent.exe")

        version = get_game_version(nonexistent_exe)
        assert version == Constants.NULL_VERSION

    @patch("platform.system", return_value="Windows")
    @patch("ClassicLib.Utils.version_utils.get_version_windows_api")
    def test_get_game_version_windows_success(self, mock_windows_api: MagicMock, mock_platform: MagicMock, tmp_path: Path) -> None:  # noqa: ARG002
        """Test get_game_version on Windows with successful API call."""
        test_exe = tmp_path / "test.exe"
        test_exe.write_bytes(b"fake exe content")

        expected_version = Version("1.10.163.0")
        mock_windows_api.return_value = expected_version

        version = get_game_version(test_exe)
        assert version == expected_version
        mock_windows_api.assert_called_once_with(test_exe)

    @patch("platform.system", return_value="Linux")
    @patch("ClassicLib.Utils.version_utils.get_version_from_pe_header")
    def test_get_game_version_linux_fallback(self, mock_pe_header: MagicMock, mock_platform: MagicMock, tmp_path: Path) -> None:  # noqa: ARG002
        """Test get_game_version on Linux using PE header fallback."""
        test_exe = tmp_path / "test.exe"
        test_exe.write_bytes(b"fake exe content")

        expected_version = Version("1.10.163.0")
        mock_pe_header.return_value = expected_version

        version = get_game_version(test_exe)
        assert version == expected_version
        mock_pe_header.assert_called_once_with(test_exe)

    @patch("platform.system", return_value="Windows")
    @patch("ClassicLib.Utils.version_utils.get_version_from_pe_header")
    @patch("ClassicLib.Utils.version_utils.get_version_windows_api", return_value=Constants.NULL_VERSION)
    def test_get_game_version_windows_fallback_on_error(
        self, mock_windows_api: MagicMock, mock_pe_header: MagicMock, mock_platform: MagicMock, tmp_path: Path
    ) -> None:  # noqa: ARG002
        """Test get_game_version falls back to PE header when Windows API fails."""
        test_exe = tmp_path / "test.exe"
        test_exe.write_bytes(b"fake exe content")

        expected_version = Version("1.10.162.0")
        mock_pe_header.return_value = expected_version

        version = get_game_version(test_exe)
        assert version == expected_version
        mock_pe_header.assert_called_once_with(test_exe)

    @patch("platform.system", return_value="Darwin")  # macOS
    @patch("ClassicLib.Utils.version_utils.get_version_from_pe_header")
    def test_get_game_version_macos(self, mock_pe_header: MagicMock, mock_platform: MagicMock, tmp_path: Path) -> None:  # noqa: ARG002
        """Test get_game_version on macOS."""
        test_exe = tmp_path / "test.exe"
        test_exe.write_bytes(b"fake exe content")

        expected_version = Version("1.10.163.0")
        mock_pe_header.return_value = expected_version

        version = get_game_version(test_exe)
        assert version == expected_version

    def test_get_game_version_empty_file(self, tmp_path: Path) -> None:
        """Test get_game_version with empty executable file."""
        test_exe = tmp_path / "empty.exe"
        test_exe.write_bytes(b"")

        version = get_game_version(test_exe)
        assert version == Constants.NULL_VERSION

    @patch("platform.system", return_value="Windows")
    @patch("ClassicLib.Utils.version_utils.get_version_windows_api", return_value=Constants.NULL_VERSION)
    @patch("ClassicLib.Utils.version_utils.get_version_from_pe_header", return_value=Constants.NULL_VERSION)
    def test_get_game_version_both_methods_fail(
        self, mock_pe_header: MagicMock, mock_windows_api: MagicMock, mock_platform: MagicMock, tmp_path: Path
    ) -> None:  # noqa: ARG002
        """Test get_game_version when both detection methods fail."""
        test_exe = tmp_path / "test.exe"
        test_exe.write_bytes(b"fake exe content")

        version = get_game_version(test_exe)
        assert version == Constants.NULL_VERSION

    def test_get_game_version_with_path_object(self, tmp_path: Path) -> None:
        """Test get_game_version with Path object."""
        test_exe = tmp_path / "test.exe"
        test_exe.write_bytes(b"fake exe content")

        # The function expects a Path object
        version = get_game_version(test_exe)
        # Without mocking, it will return NULL_VERSION for a fake exe
        assert version == Constants.NULL_VERSION


if __name__ == "__main__":
    pytest.main([__file__])
