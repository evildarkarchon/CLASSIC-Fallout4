"""Tests for SetupCoordinator integrity checking and results generation."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.SetupCoordinator import SetupCoordinator

pytestmark = [pytest.mark.unit]


class TestIntegrityChecks:
    """Test suite for integrity checking functionality."""

    @pytest.fixture
    def coordinator(self) -> SetupCoordinator:
        """Create a SetupCoordinator instance for testing."""
        return SetupCoordinator()

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up after tests."""
        yield
        # Reset registry state
        GlobalRegistry._registry = {}

    @patch("ClassicLib.GameIntegrity.GameIntegrityChecker.run_full_check")
    @patch("ClassicLib.SetupCoordinator.xse_check_integrity")
    @patch("ClassicLib.SetupCoordinator.xse_check_hashes")
    @patch("ClassicLib.DocumentsChecker.DocumentsChecker.run_all_checks")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_combined_results(
        self,
        mock_get_game: MagicMock,
        mock_docs_checks: MagicMock,
        mock_xse_hashes: MagicMock,
        mock_xse_integrity: MagicMock,
        mock_game_check: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test generate_combined_results combines all check results."""
        # Mock return values
        mock_game_check.return_value = "Game OK\n"
        mock_xse_integrity.return_value = "XSE OK\n"
        mock_xse_hashes.return_value = "Hashes OK\n"
        mock_docs_checks.return_value = ["Docs OK\n"]

        # Generate results
        result = coordinator.generate_combined_results()

        # Verify all checks were called
        mock_game_check.assert_called_once()
        mock_xse_integrity.assert_called_once()
        mock_xse_hashes.assert_called_once()
        mock_docs_checks.assert_called_once()

        # Verify result contains all outputs
        assert "Game OK" in result
        assert "XSE OK" in result
        assert "Hashes OK" in result
        assert "Docs OK" in result

    @patch("ClassicLib.GameIntegrity.GameIntegrityChecker.run_full_check")
    @patch("ClassicLib.SetupCoordinator.xse_check_integrity")
    @patch("ClassicLib.SetupCoordinator.xse_check_hashes")
    @patch("ClassicLib.DocumentsChecker.DocumentsChecker.run_all_checks")
    @patch.object(GlobalRegistry, "get_game", return_value="SkyrimSE")
    def test_generate_combined_results_different_game(
        self,
        mock_get_game: MagicMock,
        mock_docs_checks: MagicMock,
        mock_xse_hashes: MagicMock,
        mock_xse_integrity: MagicMock,
        mock_game_check: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test generate_combined_results with different game."""
        # Mock return values
        mock_game_check.return_value = "Skyrim OK\n"
        mock_xse_integrity.return_value = ""
        mock_xse_hashes.return_value = ""
        mock_docs_checks.return_value = []

        # Generate results
        result = coordinator.generate_combined_results()

        # Verify game name was used
        mock_get_game.assert_called_once()
        assert "Skyrim OK" in result

    @patch("ClassicLib.GameIntegrity.GameIntegrityChecker.run_full_check", side_effect=Exception("Check failed"))
    @patch("ClassicLib.SetupCoordinator.xse_check_integrity")
    @patch("ClassicLib.SetupCoordinator.xse_check_hashes")
    @patch("ClassicLib.DocumentsChecker.DocumentsChecker.run_all_checks")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_combined_results_exception(
        self,
        mock_get_game: MagicMock,
        mock_docs_checks: MagicMock,
        mock_xse_hashes: MagicMock,
        mock_xse_integrity: MagicMock,
        mock_game_check: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test that exceptions in generate_combined_results are propagated."""
        # Should raise the exception from game check
        with pytest.raises(Exception, match="Check failed"):
            coordinator.generate_combined_results()
