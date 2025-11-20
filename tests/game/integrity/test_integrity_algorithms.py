"""Tests for checksum and hash verification algorithms."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.GameIntegrity import GameIntegrityChecker


class TestHashVerification:
    """Tests for file hash verification and version detection."""

    @patch("ClassicLib.GameIntegrity.calculate_file_hash")
    def test_check_executable_version_latest(
        self, mock_hash: MagicMock, checker: GameIntegrityChecker, mock_config: dict[str, str], test_game_exe: Path
    ) -> None:
        """Test checking executable when it's the latest version."""
        # Update config with test path
        mock_config["game_exe_path"] = str(test_game_exe)
        mock_config["steam_ini_path"] = str(test_game_exe.parent / "steam_api.ini")
        checker._config = mock_config

        # Mock hash calculation to return new version hash
        mock_hash.return_value = "hash_new_version"

        # Check version
        is_valid, message = checker.check_executable_version()

        # Should be valid and have success message
        assert is_valid is True
        assert "✔️ You have the latest version" in message
        assert "Fallout4" in message

    @patch("ClassicLib.GameIntegrity.calculate_file_hash")
    def test_check_executable_version_outdated_with_steam_ini(
        self,
        mock_hash: MagicMock,
        checker: GameIntegrityChecker,
        mock_config: dict[str, str],
        test_game_exe: Path,
        test_steam_ini: Path,
    ) -> None:
        """Test checking executable when outdated with Steam INI present."""
        # Update config with test paths
        mock_config["game_exe_path"] = str(test_game_exe)
        mock_config["steam_ini_path"] = str(test_steam_ini)
        checker._config = mock_config

        # Mock hash calculation to return outdated hash
        mock_hash.return_value = "hash_outdated"

        # Check version
        is_valid, message = checker.check_executable_version()

        # Should be invalid with skull emoji
        assert is_valid is False
        assert "💀 CAUTION" in message
        assert "OUT OF DATE" in message

    @patch("ClassicLib.GameIntegrity.calculate_file_hash")
    def test_check_executable_version_outdated_no_steam_ini(
        self, mock_hash: MagicMock, checker: GameIntegrityChecker, mock_config: dict[str, str], test_game_exe: Path
    ) -> None:
        """Test checking executable when outdated without Steam INI."""
        # Update config with test path (steam ini doesn't exist)
        mock_config["game_exe_path"] = str(test_game_exe)
        mock_config["steam_ini_path"] = str(test_game_exe.parent / "steam_api.ini")
        checker._config = mock_config

        # Mock hash calculation to return outdated hash
        mock_hash.return_value = "hash_outdated"

        # Check version
        is_valid, message = checker.check_executable_version()

        # Should be invalid with X emoji
        assert is_valid is False
        assert "❌ CAUTION" in message
        assert "OUT OF DATE" in message

    @patch("ClassicLib.GameIntegrity.calculate_file_hash")
    def test_check_executable_version_old_but_expected(
        self, mock_hash: MagicMock, checker: GameIntegrityChecker, mock_config: dict[str, str], test_game_exe: Path
    ) -> None:
        """Test checking executable when it matches the old expected version."""
        # Update config with test path
        mock_config["game_exe_path"] = str(test_game_exe)
        mock_config["steam_ini_path"] = str(test_game_exe.parent / "steam_api.ini")
        checker._config = mock_config

        # Mock hash calculation to return old version hash
        mock_hash.return_value = "hash_old_version"

        # Check version
        is_valid, message = checker.check_executable_version()

        # Old version is still considered valid (just not latest)
        # The implementation seems to return True for old version
        assert is_valid is True
        assert "Fallout4" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
