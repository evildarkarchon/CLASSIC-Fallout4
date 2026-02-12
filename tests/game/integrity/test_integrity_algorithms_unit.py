"""Tests for checksum and hash verification algorithms.

These tests verify the Rust-backed executable version checking via
classic_scangame.GameIntegrityChecker. Test files with known content
are used so real SHA-256 hashes can be validated.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import hashlib
from pathlib import Path

import pytest

from ClassicLib.support.integrity import GameIntegrityChecker

# Pre-computed hash for the test file content ("fake exe content")
_TEST_EXE_CONTENT = b"fake exe content"
_TEST_EXE_HASH = hashlib.sha256(_TEST_EXE_CONTENT).hexdigest()


class TestHashVerification:
    """Tests for file hash verification and version detection."""

    def test_check_executable_version_latest(self, checker: GameIntegrityChecker, mock_config: dict[str, str], test_game_exe: Path) -> None:
        """Test checking executable when it's the latest version."""
        mock_config["game_exe_path"] = str(test_game_exe)
        mock_config["steam_ini_path"] = str(test_game_exe.parent / "nonexistent_steam_api.ini")
        checker._config = mock_config  # pyright: ignore[reportAttributeAccessIssue]
        # Set valid exe hashes to include the real hash of test file content
        checker._valid_exe_hashes = {_TEST_EXE_HASH}  # pyright: ignore[reportAttributeAccessIssue]

        is_valid, message = checker.check_executable_version()

        assert is_valid is True
        assert "You have the latest version" in message
        assert "Fallout4" in message

    def test_check_executable_version_outdated_with_steam_ini(
        self,
        checker: GameIntegrityChecker,
        mock_config: dict[str, str],
        test_game_exe: Path,
        test_steam_ini: Path,
    ) -> None:
        """Test checking executable when outdated with Steam INI present."""
        mock_config["game_exe_path"] = str(test_game_exe)
        mock_config["steam_ini_path"] = str(test_steam_ini)
        checker._config = mock_config  # pyright: ignore[reportAttributeAccessIssue]
        # No matching hashes -- exe is "outdated"
        checker._valid_exe_hashes = {"some_other_hash"}  # pyright: ignore[reportAttributeAccessIssue]

        is_valid, message = checker.check_executable_version()

        assert is_valid is False
        assert "CAUTION" in message
        assert "OUT OF DATE" in message

    def test_check_executable_version_outdated_no_steam_ini(
        self, checker: GameIntegrityChecker, mock_config: dict[str, str], test_game_exe: Path
    ) -> None:
        """Test checking executable when outdated without Steam INI."""
        mock_config["game_exe_path"] = str(test_game_exe)
        mock_config["steam_ini_path"] = str(test_game_exe.parent / "nonexistent_steam_api.ini")
        checker._config = mock_config  # pyright: ignore[reportAttributeAccessIssue]
        # No matching hashes
        checker._valid_exe_hashes = {"some_other_hash"}  # pyright: ignore[reportAttributeAccessIssue]

        is_valid, message = checker.check_executable_version()

        assert is_valid is False
        assert "CAUTION" in message
        assert "OUT OF DATE" in message

    def test_check_executable_version_valid_hash_match(
        self, checker: GameIntegrityChecker, mock_config: dict[str, str], test_game_exe: Path
    ) -> None:
        """Test checking executable when it matches a known valid version hash."""
        mock_config["game_exe_path"] = str(test_game_exe)
        mock_config["steam_ini_path"] = str(test_game_exe.parent / "nonexistent_steam_api.ini")
        checker._config = mock_config  # pyright: ignore[reportAttributeAccessIssue]
        # Include the test file's hash as a valid hash
        checker._valid_exe_hashes = {_TEST_EXE_HASH, "another_valid_hash"}  # pyright: ignore[reportAttributeAccessIssue]

        is_valid, message = checker.check_executable_version()

        assert is_valid is True
        assert "Fallout4" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
