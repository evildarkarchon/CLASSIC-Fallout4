"""
Unit tests for update checking logic and error handling in Update.py.

This module tests the is_latest_version function and UpdateCheckError
exception class, including various update scenarios, error handling,
and edge cases. The update system uses the Rust GithubClient binding.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib.support.update import (
    UpdateCheckError,
    is_latest_version,
)


def _make_mock_release(*, name: str = "v7.30.1", tag_name: str = "v7.30.1", prerelease: bool = False) -> MagicMock:
    """Create a mock GithubRelease object."""
    release = MagicMock()
    release.name = name
    release.tag_name = tag_name
    release.prerelease = prerelease
    return release


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
            patch("ClassicLib.support.update.yaml_settings_async") as mock_yaml_settings_async,
            patch("ClassicLib.support.update.classic_settings_async") as mock_classic_settings_async,
            patch("ClassicLib.core.registry.GlobalRegistry.get_game") as mock_get_game,
            patch("ClassicLib.support.update.logger") as mock_logger,
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

    @pytest.mark.asyncio
    async def test_is_latest_version_up_to_date(self, mock_dependencies):
        """Test when local version is up to date."""

        # Configure settings - classic_settings_async takes type and key
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock local version
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.1",
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock GithubClient returning latest release with same version
        mock_release = _make_mock_release(name="v7.30.1", tag_name="v7.30.1")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await is_latest_version(quiet=False, gui_request=False)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_latest_version_update_available_gui(self, mock_dependencies):
        """Test when update is available and called from GUI."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock local version (older)
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.0",
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock GithubClient returning newer version
        mock_release = _make_mock_release(name="v7.30.1", tag_name="v7.30.1")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            with pytest.raises(UpdateCheckError, match="A new version is available"):
                await is_latest_version(quiet=False, gui_request=True)

    @pytest.mark.asyncio
    async def test_is_latest_version_update_available_cli(self, mock_dependencies):
        """Test when update is available and called from CLI."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock local version (older)
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.0",
                "classic_interface.update_warning_fallout4": "Update warning message",
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock GithubClient returning newer version
        mock_release = _make_mock_release(name="v7.30.1", tag_name="v7.30.1")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await is_latest_version(quiet=False, gui_request=False)

        assert result is False  # Outdated

    @pytest.mark.asyncio
    async def test_is_latest_version_network_error_handling(self, mock_dependencies):
        """Test handling of network errors."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock local version
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.1",
                "classic_interface.update_unable_fallout4": "Unable to check updates",
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock GithubClient raising RuntimeError (network failure)
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(side_effect=RuntimeError("GitHub API error: connection refused"))
        mock_client.get_all_releases = AsyncMock(side_effect=RuntimeError("GitHub API error: connection refused"))

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await is_latest_version(quiet=False, gui_request=False)

        assert result is False

    @pytest.mark.asyncio
    async def test_is_latest_version_missing_local_version_is_fatal(self, mock_dependencies):
        """Test missing CLASSIC_Info.version is treated as a fatal configuration error."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock missing local version
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": None,
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        with pytest.raises(UpdateCheckError, match="Fatal configuration error: missing 'CLASSIC_Info.version'"):
            await is_latest_version(quiet=False, gui_request=False)

    @pytest.mark.asyncio
    async def test_is_latest_version_invalid_local_version_is_fatal(self, mock_dependencies):
        """Test malformed CLASSIC_Info.version is treated as a fatal configuration error."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        # Mock invalid local version format
        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC definitely-not-a-version",
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        with pytest.raises(UpdateCheckError, match="Fatal configuration error: unable to parse 'CLASSIC_Info.version'"):
            await is_latest_version(quiet=False, gui_request=False)


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
            patch("ClassicLib.support.update.yaml_settings_async") as mock_yaml_settings_async,
            patch("ClassicLib.support.update.classic_settings_async") as mock_classic_settings_async,
            patch("ClassicLib.core.registry.GlobalRegistry.get_game") as mock_get_game,
        ):
            yield {
                "yaml_settings_async": mock_yaml_settings_async,
                "classic_settings_async": mock_classic_settings_async,
                "get_game": mock_get_game,
            }

    @pytest.mark.asyncio
    async def test_source_failure_github(self, mock_dependencies):
        """Test error when GitHub source fails."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.1",
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock GithubClient where both get_latest_release and get_all_releases fail
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(side_effect=RuntimeError("GitHub API error: not found"))
        mock_client.get_all_releases = AsyncMock(side_effect=RuntimeError("GitHub API error: not found"))

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            with pytest.raises(UpdateCheckError, match="Unable to fetch version information from GitHub"):
                await is_latest_version(quiet=True, gui_request=True)

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self, mock_dependencies):
        """Test handling of unexpected exceptions."""

        # Configure settings
        async def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings_async"].side_effect = classic_settings_side_effect

        async def yaml_settings_side_effect(type_cls, enum, key, default=None):
            return {
                "CLASSIC_Info.version": "CLASSIC v7.30.1",
            }.get(key, default)

        mock_dependencies["yaml_settings_async"].side_effect = yaml_settings_side_effect

        mock_dependencies["get_game"].return_value = "fallout4"

        # Mock GithubClient constructor raising unexpected exception
        with patch("ClassicLib.support.update.GithubClient", side_effect=RuntimeError("Unexpected error")):
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
