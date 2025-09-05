"""Tests for the SettingsScreen component."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913

from unittest.mock import patch

import pytest
from textual.widgets import Input

from ClassicLib.Constants import YAML
from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.TUI.screens.main_screen import MainScreen
from ClassicLib.TUI.screens.settings_screen import SettingsScreen


class TestSettingsScreenDisplay:
    """Test SettingsScreen display and initialization."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_settings_screen_display(self):
        """Test settings screen displays correctly."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Press Ctrl+O to open settings
            await pilot.press("ctrl+o")

            # Check settings screen is displayed
            settings_screen = app.screen
            assert isinstance(settings_screen, SettingsScreen)

            # Check input fields exist
            assert settings_screen.query_one("#staging-folder") is not None
            assert settings_screen.query_one("#custom-folder") is not None
            assert settings_screen.query_one("#auto-scroll") is not None
            assert settings_screen.query_one("#update-check") is not None


class TestSettingsScreenSave:
    """Test saving settings in SettingsScreen."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_settings_save(self):
        """Test saving settings."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Mock yaml_cache.batch_get_settings to return proper values
            def mock_batch_get_settings(requests):
                # Return values in the same order as requested
                return [
                    "/mock/staging",  # MODS Folder Path
                    "/mock/custom",  # SCAN Custom Path
                    True,  # Update Check
                    True,  # AutoScroll
                    True,  # ShowTimestamps
                    10000,  # MaxOutputLines
                    "Fallout4",  # Game
                ]

            with (
                patch("ClassicLib.TUI.screens.settings_screen.yaml_cache.batch_get_settings", side_effect=mock_batch_get_settings),
                patch("ClassicLib.TUI.screens.settings_screen.yaml_settings") as mock_yaml_settings,
            ):
                # Open settings
                await pilot.press("ctrl+o")
                await pilot.pause()

                # Get the settings screen
                settings_screen = app.screen
                assert isinstance(settings_screen, SettingsScreen)

                # Get an input field and modify it
                staging_input = settings_screen.query_one("#staging-folder", Input)
                staging_input.value = "/new/path"

                # Save settings - directly call the method
                settings_screen._save_settings()

                # Verify settings were saved (yaml_settings was called)
                assert mock_yaml_settings.call_count > 0
                # Verify the correct value was written with proper key
                mock_yaml_settings.assert_any_call(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", "/new/path")


class TestSettingsScreenCancel:
    """Test cancelling settings in SettingsScreen."""

    @pytest.mark.asyncio
    @pytest.mark.gui
    async def test_settings_cancel(self):
        """Test cancelling settings changes."""
        app = CLASSICTuiApp()
        async with app.run_test() as pilot:
            # Open settings
            await pilot.press("ctrl+o")
            await pilot.pause()

            settings_screen = app.screen
            assert isinstance(settings_screen, SettingsScreen)

            # Cancel without saving - press escape or dismiss
            settings_screen.dismiss(False)
            await pilot.pause()

            # Check we're back to main screen
            assert isinstance(app.screen, MainScreen)
