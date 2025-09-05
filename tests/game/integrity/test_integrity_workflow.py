"""
Tests for complete integrity check workflow and report generation.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.GameIntegrity import GameIntegrityChecker


class TestFullIntegrityCheck:
    """Tests for running full integrity check workflow."""

    @patch.object(GameIntegrityChecker, "check_installation_location")
    @patch.object(GameIntegrityChecker, "check_executable_version")
    @patch.object(GameIntegrityChecker, "load_configuration")
    @patch("ClassicLib.GameIntegrity.logger")
    def test_run_full_check_all_messages(
        self,
        mock_logger: MagicMock,
        mock_load: MagicMock,
        mock_check_version: MagicMock,
        mock_check_location: MagicMock,
        checker: GameIntegrityChecker,
    ) -> None:
        """Test running full integrity check with all checks returning messages."""
        # Setup mocks
        mock_check_version.return_value = (True, "Version OK\n")
        mock_check_location.return_value = (True, "Location OK\n")

        # Run full check
        result = checker.run_full_check()

        # Verify all checks were called
        mock_load.assert_called_once()
        mock_check_version.assert_called_once()
        mock_check_location.assert_called_once()

        # Verify result contains both messages
        assert result == "Version OK\nLocation OK\n"

        # Verify logging
        mock_logger.debug.assert_called_with("- - - INITIATED GAME INTEGRITY CHECK")

    @patch.object(GameIntegrityChecker, "check_installation_location")
    @patch.object(GameIntegrityChecker, "check_executable_version")
    def test_run_full_check_no_config(
        self, mock_check_version: MagicMock, mock_check_location: MagicMock, checker: GameIntegrityChecker
    ) -> None:
        """Test running full check loads configuration if not present."""
        # Setup mocks
        mock_check_version.return_value = (False, "Version Bad")
        mock_check_location.return_value = (False, "")

        # Ensure no config is loaded
        assert not checker._config

        with patch.object(checker, "load_configuration") as mock_load:
            # Run full check
            result = checker.run_full_check()

            # Verify configuration was loaded
            mock_load.assert_called_once()

    @patch.object(GameIntegrityChecker, "check_installation_location")
    @patch.object(GameIntegrityChecker, "check_executable_version")
    def test_run_full_check_empty_messages(
        self, mock_check_version: MagicMock, mock_check_location: MagicMock, checker: GameIntegrityChecker
    ) -> None:
        """Test running full check with empty messages."""
        # Setup mocks to return empty messages
        mock_check_version.return_value = (True, "")
        mock_check_location.return_value = (True, "")

        # Set dummy config so load_configuration isn't called
        checker._config = {"dummy": "config"}

        # Run full check
        result = checker.run_full_check()

        # Should return empty string
        assert result == ""

    @patch("ClassicLib.GameIntegrity.logger")
    def test_run_full_check_logging(self, mock_logger: MagicMock, checker: GameIntegrityChecker) -> None:
        """Test that run_full_check logs debug message."""
        # Set dummy config
        checker._config = {"dummy": "config"}

        with patch.object(checker, "check_executable_version", return_value=(True, "")):
            with patch.object(checker, "check_installation_location", return_value=(True, "")):
                checker.run_full_check()

        # Verify debug logging
        mock_logger.debug.assert_called_with("- - - INITIATED GAME INTEGRITY CHECK")

    @patch.object(GameIntegrityChecker, "check_installation_location")
    @patch.object(GameIntegrityChecker, "check_executable_version")
    def test_run_full_check_mixed_results(
        self, mock_check_version: MagicMock, mock_check_location: MagicMock, checker: GameIntegrityChecker
    ) -> None:
        """Test running full check with mixed pass/fail results."""
        # Setup mocks - one passes, one fails
        mock_check_version.return_value = (True, "✔️ Version is good\n")
        mock_check_location.return_value = (False, "WARNING: Bad location\n")

        # Set dummy config
        checker._config = {"dummy": "config"}

        # Run full check
        result = checker.run_full_check()

        # Should contain both messages
        assert "✔️ Version is good" in result
        assert "WARNING: Bad location" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
