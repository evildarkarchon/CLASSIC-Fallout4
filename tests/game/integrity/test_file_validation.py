"""Tests for individual file validation and location checking."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from pathlib import Path
from unittest.mock import patch

import pytest

from ClassicLib.GameIntegrity import GameIntegrityChecker


class TestInstallationLocation:
    """Tests for game installation location checking."""

    def test_check_installation_location_good(self, checker: GameIntegrityChecker, mock_config: dict[str, str], tmp_path: Path) -> None:
        """Test checking installation when NOT in Program Files."""
        # Create fake exe in good location
        exe_path = tmp_path / "Games" / "Fallout4" / "Fallout4.exe"
        exe_path.parent.mkdir(parents=True, exist_ok=True)
        exe_path.write_text("fake exe")

        mock_config["game_exe_path"] = str(exe_path)
        checker._config = mock_config # pyright: ignore[reportAttributeAccessIssue]

        # Check location
        is_valid, message = checker.check_installation_location()

        # Should be valid
        assert is_valid is True
        assert "✔️" in message
        assert "outside of the Program Files folder" in message

    def test_check_installation_location_bad(self, checker: GameIntegrityChecker, mock_config: dict[str, str]) -> None:
        """Test checking installation when IN Program Files."""
        # Set exe path in Program Files
        mock_config["game_exe_path"] = "C:/Program Files/Steam/Fallout4/Fallout4.exe"
        checker._config = mock_config # pyright: ignore[reportAttributeAccessIssue]

        # Mock file existence check
        with patch("pathlib.Path.is_file", return_value=True):
            # Check location
            is_valid, message = checker.check_installation_location()

        # Should be invalid with warning
        assert is_valid is False
        assert message == "WARNING: Game installed in Program Files!"

    def test_check_installation_location_no_exe(self, checker: GameIntegrityChecker, mock_config: dict[str, str]) -> None:
        """Test checking installation when exe doesn't exist."""
        mock_config["game_exe_path"] = "/nonexistent/Fallout4.exe"
        checker._config = mock_config # pyright: ignore[reportAttributeAccessIssue]

        # Check location
        is_valid, message = checker.check_installation_location()

        # Should return invalid with empty message
        assert is_valid is False
        assert message == ""

    def test_check_installation_location_no_warning_configured(self, checker: GameIntegrityChecker, mock_config: dict[str, str]) -> None:
        """Test checking installation with no warning message configured."""
        mock_config["game_exe_path"] = "C:/Program Files/Fallout4/Fallout4.exe"
        mock_config["root_warn"] = ""
        checker._config = mock_config # pyright: ignore[reportAttributeAccessIssue]

        with patch("pathlib.Path.is_file", return_value=True):
            is_valid, message = checker.check_installation_location()

        assert is_valid is False
        assert message == ""


class TestExecutableVersion:
    """Tests for game executable version checking."""

    def test_check_executable_version_no_exe(self, checker: GameIntegrityChecker, mock_config: dict[str, str]) -> None:
        """Test checking executable when exe file doesn't exist."""
        # Set non-existent exe path
        mock_config["game_exe_path"] = "/nonexistent/Fallout4.exe"
        checker._config = mock_config # pyright: ignore[reportAttributeAccessIssue]

        # Check version
        is_valid, message = checker.check_executable_version()

        # Should be invalid
        assert is_valid is False
        assert message == "Game executable not found"

    def test_check_executable_version_no_path_configured(self, checker: GameIntegrityChecker) -> None:
        """Test checking executable when no path is configured."""
        checker._config = {"game_exe_path": None}

        # Check version
        is_valid, message = checker.check_executable_version()

        # Should be invalid
        assert is_valid is False
        assert message == "Game executable not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
