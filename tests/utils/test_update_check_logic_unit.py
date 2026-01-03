"""
Unit tests for update checking logic and error handling in Update.py.

This module tests the is_latest_version function and UpdateCheckError
exception class, including various update scenarios, error handling,
and edge cases.
"""

from unittest.mock import AsyncMock, patch

import pytest
from packaging.version import Version

from ClassicLib.Update import (
    UpdateCheckError,
    is_latest_version,
)


@pytest.mark.unit
class TestUpdateChecking:
    """Test update checking functionality."""

    @pytest.fixture
    def mock_dependencies(self, init_message_handler_fixture):
        """Mock all dependencies for update checking.

        This fixture ensures MessageHandler is initialized before tests run,
        preventing RuntimeError about uninitialized message handler.
        """
        with (
            patch("ClassicLib.Update.yaml_settings_async") as mock_yaml_settings_async,
            patch("ClassicLib.Update.classic_settings_async") as mock_classic_settings_async,
            patch("ClassicLib.GlobalRegistry.get_game") as mock_get_game,
            patch("ClassicLib.Update.logger") as mock_logger,
        ):
            # Don't mock the message functions since MessageHandler is initialized
            from ClassicLib import msg_error, msg_success, msg_warning

            yield {
                "yaml_settings_async": mock_yaml_settings_async,
                "classic_settings_async": mock_classic_settings_async,
                "get_game": mock_get_game,
                "msg_warning": msg_warning,
                "msg_success": msg_success,
                "msg_error": msg_error,
                "logger": mock_logger,
            }

    @pytest.mark.asyncio
    async def test_is_latest_version_disabled_check(self, mock_dependencies):
        """Test when update check is disabled."""

        async def classic_settings_side_effect(type_arg, key, default=None):
            # Return False for Update Check
            if key == "Update Check":
                return False
            return default

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect  # Update check disabled

        result = await is_latest_version(quiet=False, gui_request=False)

        assert result is False
        # Message would be logged via the real msg_info function
        # We're testing the result, not the message logging

    @pytest.mark.asyncio
    async def test_is_latest_version_invalid_source(self, mock_dependencies):
        """Test with invalid update source setting."""

        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "InvalidSource"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        result = await is_latest_version(quiet=False, gui_request=False)

        assert result is False
        # Message would be logged via the real msg_info function
        # We're testing the result, not the message logging

    @pytest.mark.asyncio
    async def test_is_latest_version_up_to_date(self, mock_dependencies):
        """Test when local version is up to date."""

        # Configure settings - classic_settings_async takes type and key
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock local version
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.1",
                "CLASSIC_Info.is_prerelease": False,
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock GitHub returning same version
        # We need to patch aiohttp.ClientSession to control the network calls
        with patch("ClassicLib.Update.aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock()

            # Mock the get_latest_and_top_release_details function
            with patch("ClassicLib.Update.get_latest_and_top_release_details") as mock_github:
                # Create a coroutine for the async function
                async def mock_get_details(*args, **kwargs):
                    return {
                        "latest_endpoint_release": {"version": Version("7.30.1"), "prerelease": False},
                        "top_of_list_release": {"version": Version("7.30.1"), "prerelease": False},
                    }

                mock_github.side_effect = mock_get_details

                result = await is_latest_version(quiet=False, gui_request=False)

            assert result is True
            # Success message would be logged via the real msg_success function

    @pytest.mark.asyncio
    async def test_is_latest_version_update_available_gui(self, mock_dependencies):
        """Test when update is available and called from GUI."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock local version (older)
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.0",
                "CLASSIC_Info.is_prerelease": False,
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock GitHub returning newer version
        with patch("ClassicLib.Update.get_latest_and_top_release_details") as mock_github:
            mock_github.return_value = {
                "latest_endpoint_release": {"version": Version("7.30.1"), "prerelease": False},
                "top_of_list_release": {"version": Version("7.30.1"), "prerelease": False},
            }

            # Should raise UpdateCheckError for GUI
            with pytest.raises(UpdateCheckError, match="A new version is available"):
                await is_latest_version(quiet=False, gui_request=True)

    @pytest.mark.asyncio
    async def test_is_latest_version_update_available_cli(self, mock_dependencies):
        """Test when update is available and called from CLI."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock local version (older)
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.0",
                "CLASSIC_Info.is_prerelease": False,
                "CLASSIC_Interface.update_warning_fallout4": "Update warning message",
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock GitHub returning newer version
        with patch("ClassicLib.Update.get_latest_and_top_release_details") as mock_github:
            mock_github.return_value = {
                "latest_endpoint_release": {"version": Version("7.30.1"), "prerelease": False},
                "top_of_list_release": {"version": Version("7.30.1"), "prerelease": False},
            }

            result = await is_latest_version(quiet=False, gui_request=False)

            assert result is False  # Outdated
            # Warning message would be logged via the real msg_warning function

    @pytest.mark.asyncio
    async def test_is_latest_version_both_sources(self, mock_dependencies):
        """Test checking both GitHub and Nexus sources."""

        # Configure settings for both sources
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "Both"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock local version
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.0",
                "CLASSIC_Info.is_prerelease": False,
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock both sources
        with (
            patch("ClassicLib.Update.get_latest_and_top_release_details") as mock_github,
            patch("ClassicLib.Update.get_nexus_version") as mock_nexus,
        ):
            mock_github.return_value = {
                "latest_endpoint_release": {"version": Version("7.30.1"), "prerelease": False},
                "top_of_list_release": {"version": Version("7.30.1"), "prerelease": False},
            }
            mock_nexus.return_value = Version("7.30.2")  # Newer on Nexus

            result = await is_latest_version(quiet=False, gui_request=False)

            assert result is False  # Outdated (Nexus has newer)

    @pytest.mark.asyncio
    async def test_is_latest_version_network_error_handling(self, mock_dependencies):
        """Test handling of network errors."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock local version
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.1",
                "CLASSIC_Info.is_prerelease": False,
                "CLASSIC_Interface.update_unable_fallout4": "Unable to check updates",
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock get_latest_and_top_release_details to return None (simulating network failure)
        with patch("ClassicLib.Update.get_latest_and_top_release_details") as mock_github:
            # Return None to simulate network failure
            async def mock_get_details(*args, **kwargs):
                return None

            mock_github.side_effect = mock_get_details

            result = await is_latest_version(quiet=False, gui_request=False)

            assert result is False
            # Error message would be logged via the real msg_error function

    @pytest.mark.asyncio
    async def test_is_latest_version_nexus_only_prerelease_skip(self, mock_dependencies):
        """Test that Nexus is skipped for prerelease versions."""

        # Configure settings for Nexus only
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "Nexus"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock prerelease version
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.31.0-beta",
                "CLASSIC_Info.is_prerelease": True,  # Prerelease
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        result = await is_latest_version(quiet=False, gui_request=False)

        # Should be treated as up to date since Nexus check is skipped for prereleases
        assert result is True

    @pytest.mark.asyncio
    async def test_is_latest_version_unknown_local_version(self, mock_dependencies):
        """Test when local version is unknown."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock unknown local version
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": None,  # Unknown version
                "CLASSIC_Info.is_prerelease": False,
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock GitHub returning a version
        with patch("ClassicLib.Update.get_latest_and_top_release_details") as mock_github:
            mock_github.return_value = {
                "latest_endpoint_release": {"version": Version("7.30.1"), "prerelease": False},
                "top_of_list_release": {"version": Version("7.30.1"), "prerelease": False},
            }

            result = await is_latest_version(quiet=False, gui_request=False)

            assert result is False  # Assume outdated when local version unknown
            # Warning message would be logged via the real msg_warning function


@pytest.mark.unit
class TestUpdateCheckErrorHandling:
    """Test update checking error handling and edge cases."""

    @pytest.fixture
    def mock_dependencies(self, init_message_handler_fixture):
        """Mock all dependencies for error testing.

        This fixture ensures MessageHandler is initialized before tests run,
        preventing RuntimeError about uninitialized message handler.
        """
        with (
            patch("ClassicLib.Update.yaml_settings_async") as mock_yaml_settings_async,
            patch("ClassicLib.Update.classic_settings_async") as mock_classic_settings_async,
            patch("ClassicLib.GlobalRegistry.get_game") as mock_get_game,
        ):
            yield {
                "yaml_settings_async": mock_yaml_settings_async,
                "classic_settings_async": mock_classic_settings_async,
                "get_game": mock_get_game,
            }

    @pytest.mark.asyncio
    async def test_source_failure_github_only(self, mock_dependencies):
        """Test error when GitHub-only source fails."""

        # Configure settings for GitHub only
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.1",
                "CLASSIC_Info.is_prerelease": False,
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock GitHub failure
        with patch("ClassicLib.Update.get_latest_and_top_release_details") as mock_github:
            mock_github.return_value = None  # Failed

            # Should raise UpdateCheckError for GUI
            with pytest.raises(UpdateCheckError, match="Unable to fetch version information from GitHub"):
                await is_latest_version(quiet=True, gui_request=True)

    @pytest.mark.asyncio
    async def test_source_failure_nexus_only(self, mock_dependencies):
        """Test error when Nexus-only source fails."""

        # Configure settings for Nexus only
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "Nexus"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.1",
                "CLASSIC_Info.is_prerelease": False,
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock Nexus failure
        with patch("ClassicLib.Update.get_nexus_version") as mock_nexus:
            mock_nexus.return_value = None  # Failed

            # Should raise UpdateCheckError for GUI
            with pytest.raises(UpdateCheckError, match="Unable to fetch version information from Nexus"):
                await is_latest_version(quiet=True, gui_request=True)

    @pytest.mark.asyncio
    async def test_source_failure_both_sources(self, mock_dependencies):
        """Test error when both sources fail."""

        # Configure settings for both sources
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "Both"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.1",
                "CLASSIC_Info.is_prerelease": False,
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock both sources failing
        with (
            patch("ClassicLib.Update.get_latest_and_top_release_details") as mock_github,
            patch("ClassicLib.Update.get_nexus_version") as mock_nexus,
        ):
            mock_github.return_value = None  # Failed
            mock_nexus.return_value = None  # Failed

            # Should raise UpdateCheckError for GUI
            with pytest.raises(UpdateCheckError, match="Unable to fetch version information from both GitHub and Nexus"):
                await is_latest_version(quiet=True, gui_request=True)

    @pytest.mark.asyncio
    async def test_partial_source_failure_both_sources(self, mock_dependencies):
        """Test when one source fails but other succeeds (Both mode)."""

        # Configure settings for both sources
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "Both"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.0",  # Older version
                "CLASSIC_Info.is_prerelease": False,
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock partial failure - GitHub succeeds, Nexus fails
        with (
            patch("ClassicLib.Update.get_latest_and_top_release_details") as mock_github,
            patch("ClassicLib.Update.get_nexus_version") as mock_nexus,
            patch("ClassicLib.Update.msg_warning"),
        ):
            mock_github.return_value = {
                "latest_endpoint_release": {"version": Version("7.30.1"), "prerelease": False},
                "top_of_list_release": {"version": Version("7.30.1"), "prerelease": False},
            }
            mock_nexus.return_value = None  # Failed

            # Should continue with GitHub data and not raise error
            result = await is_latest_version(quiet=True, gui_request=False)

            # Should detect update based on GitHub
            assert result is False

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self, mock_dependencies):
        """Test handling of unexpected exceptions."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.1",
                "CLASSIC_Info.is_prerelease": False,
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock unexpected exception
        with patch("ClassicLib.Update.aiohttp.ClientSession") as mock_session_class:
            mock_session_class.side_effect = RuntimeError("Unexpected error")

            # Should raise UpdateCheckError for GUI
            with pytest.raises(UpdateCheckError, match="An unexpected error occurred"):
                await is_latest_version(quiet=True, gui_request=True)

    @pytest.mark.asyncio
    async def test_quiet_mode_suppresses_output(self, mock_dependencies):
        """Test that quiet mode suppresses output."""

        async def classic_settings_side_effect(type_arg, key, default=None):
            # Return False for Update Check
            if key == "Update Check":
                return False
            return default

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect  # Update check disabled

        # In quiet mode, messages are suppressed by the _log_if_not_quiet method
        result = await is_latest_version(quiet=True, gui_request=False)

        assert result is False
        # Messages would be suppressed in quiet mode


class TestUpdateCheckErrorClass:
    """Test UpdateCheckError exception class."""

    def test_update_check_error_inheritance(self):
        """Test that UpdateCheckError inherits from Exception."""
        assert issubclass(UpdateCheckError, Exception)

    def test_update_check_error_message(self):
        """Test UpdateCheckError with custom message."""
        message = "Test error message"
        error = UpdateCheckError(message)
        assert str(error) == message

    def test_update_check_error_empty_message(self):
        """Test UpdateCheckError with no message."""
        error = UpdateCheckError()
        assert str(error) == ""

    def test_update_check_error_docstring(self):
        """Test UpdateCheckError has proper docstring."""
        assert UpdateCheckError.__doc__ == "Checking for updates failed."
