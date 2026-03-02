"""Tests for complete integrity check workflow and report generation.

These tests verify the Python-to-Rust delegation in run_full_check().
Since run_full_check() delegates to the Rust GameIntegrityChecker
(via _build_rust_checker), we mock at that boundary.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.support.integrity import GameIntegrityChecker


class TestFullIntegrityCheck:
    """Tests for running full integrity check workflow."""

    @patch("ClassicLib.support.integrity.logger")
    def test_run_full_check_delegates_to_rust(
        self,
        mock_logger: MagicMock,
        checker: GameIntegrityChecker,
    ) -> None:
        """Test that run_full_check delegates to Rust checker and returns its result."""
        mock_rust_checker = MagicMock()
        mock_rust_checker.run_full_check.return_value = "Version OK\nLocation OK\n"

        with patch.object(checker, "_build_rust_checker", return_value=mock_rust_checker):
            checker._config = {"game_exe_path": "C:/Games/Fallout4.exe"}
            result = checker.run_full_check()

        mock_rust_checker.run_full_check.assert_called_once()
        assert result == "Version OK\nLocation OK\n"
        mock_logger.debug.assert_called_with("- - - INITIATED GAME INTEGRITY CHECK")

    def test_run_full_check_loads_config_when_empty(self, checker: GameIntegrityChecker) -> None:
        """Test that run_full_check loads configuration if not present."""
        assert not checker._config

        with patch.object(checker, "load_configuration") as mock_load:
            with patch.object(checker, "_build_rust_checker") as mock_build:
                mock_build.return_value.run_full_check.return_value = ""
                checker.run_full_check()
                mock_load.assert_called_once()

    def test_run_full_check_skips_config_when_present(self, checker: GameIntegrityChecker) -> None:
        """Test that run_full_check skips loading config if already present."""
        checker._config = {"game_exe_path": "C:/Games/Fallout4.exe"}

        with patch.object(checker, "load_configuration") as mock_load:
            with patch.object(checker, "_build_rust_checker") as mock_build:
                mock_build.return_value.run_full_check.return_value = ""
                checker.run_full_check()
                mock_load.assert_not_called()

    def test_run_full_check_empty_result(self, checker: GameIntegrityChecker) -> None:
        """Test that run_full_check returns empty string when Rust returns empty."""
        checker._config = {"game_exe_path": "C:/Games/Fallout4.exe"}

        mock_rust_checker = MagicMock()
        mock_rust_checker.run_full_check.return_value = ""

        with patch.object(checker, "_build_rust_checker", return_value=mock_rust_checker):
            result = checker.run_full_check()

        assert result == ""

    def test_run_full_check_handles_rust_error(self, checker: GameIntegrityChecker) -> None:
        """Test that run_full_check gracefully handles Rust errors."""
        checker._config = {"game_exe_path": "C:/Games/Fallout4.exe"}

        with patch.object(checker, "_build_rust_checker", side_effect=RuntimeError("config error")):
            result = checker.run_full_check()

        assert result == ""

    @patch("ClassicLib.support.integrity.logger")
    def test_run_full_check_logging(self, mock_logger: MagicMock, checker: GameIntegrityChecker) -> None:
        """Test that run_full_check logs debug message."""
        checker._config = {"game_exe_path": "C:/Games/Fallout4.exe"}

        with patch.object(checker, "_build_rust_checker") as mock_build:
            mock_build.return_value.run_full_check.return_value = ""
            checker.run_full_check()

        mock_logger.debug.assert_called_with("- - - INITIATED GAME INTEGRITY CHECK")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
