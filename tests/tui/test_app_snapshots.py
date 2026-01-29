"""Snapshot tests for CLASSIC TUI application.

These tests capture visual snapshots of the TUI interface to detect
unintended visual regressions.

The tests use CLASSIC_TUI_TEST_MODE environment variable (set via conftest.py)
which the app checks at startup to use mock data for snapshot consistency.
"""

from pathlib import Path

import pytest

# Path to the app module for snapshot testing
APP_PATH = str(Path(__file__).parent.parent.parent / "ClassicLib" / "TUI" / "app.py")


class TestAppSnapshots:
    """Snapshot tests for the main CLASSICApp interface."""

    @pytest.mark.snapshot
    def test_initial_app_snapshot(self, snap_compare):
        """Capture initial app appearance with default tab."""
        assert snap_compare(APP_PATH, terminal_size=(120, 40))

    @pytest.mark.snapshot
    def test_app_main_tab(self, snap_compare):
        """Capture the main options tab layout."""
        assert snap_compare(
            APP_PATH,
            terminal_size=(120, 40),
            press=["1"],  # Switch to main tab
        )

    @pytest.mark.snapshot
    def test_app_backup_tab(self, snap_compare):
        """Capture the backup tab layout."""
        assert snap_compare(
            APP_PATH,
            terminal_size=(120, 40),
            press=["2"],  # Switch to backup tab
        )

    @pytest.mark.snapshot
    def test_app_articles_tab(self, snap_compare):
        """Capture the articles/resources tab layout."""
        assert snap_compare(
            APP_PATH,
            terminal_size=(120, 40),
            press=["3"],  # Switch to articles tab
        )

    @pytest.mark.snapshot
    def test_app_results_tab(self, snap_compare):
        """Capture the results tab layout."""
        assert snap_compare(
            APP_PATH,
            terminal_size=(120, 40),
            press=["4"],  # Switch to results tab
        )

    @pytest.mark.snapshot
    def test_app_help_screen(self, snap_compare):
        """Capture the help modal screen.

        NOTE: This test is stable because the help screen content is static
        and doesn't depend on external settings or dynamic data.
        """
        assert snap_compare(
            APP_PATH,
            terminal_size=(120, 40),
            press=["f1"],  # Open help screen
        )

    @pytest.mark.snapshot
    def test_app_compact_terminal(self, snap_compare):
        """Verify app appearance in a smaller terminal."""
        assert snap_compare(
            APP_PATH,
            terminal_size=(80, 24),
        )

    @pytest.mark.snapshot
    def test_app_wide_terminal(self, snap_compare):
        """Verify app appearance in a wider terminal."""
        assert snap_compare(
            APP_PATH,
            terminal_size=(200, 50),
        )
