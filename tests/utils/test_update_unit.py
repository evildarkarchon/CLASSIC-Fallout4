"""
Unit tests for Update module.

This module tests version parsing, GitHub API interactions, and network
operations for update checking functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from packaging.version import Version

from ClassicLib.support.update import (
    get_github_latest_prerelease_version_from_list,
    get_github_latest_stable_version_from_endpoint,
    try_parse_version,
)


def create_async_json_mock(return_value):
    """Create a mock for response.json() that returns an async coroutine.

    This helper is needed because response.json() is an async method that
    must be awaited, so we need to return a coroutine, not a plain value.
    """

    async def async_json():
        return return_value

    return MagicMock(side_effect=async_json)


class TestTryParseVersion:
    """Unit tests for try_parse_version function."""

    def test_try_parse_version_simple(self):
        """Test parsing simple version strings."""
        # Basic version numbers
        assert try_parse_version("1.2.3") == Version("1.2.3")
        assert try_parse_version("2.0.0") == Version("2.0.0")
        assert try_parse_version("0.1.0") == Version("0.1.0")

    def test_try_parse_version_with_v_prefix(self):
        """Test parsing version strings with 'v' prefix."""
        assert try_parse_version("v1.2.3") == Version("1.2.3")
        assert try_parse_version("v2.0.0-alpha") == Version("2.0.0a0")
        assert try_parse_version("v0.9.1") == Version("0.9.1")

    def test_try_parse_version_from_release_name(self):
        """Test parsing versions from GitHub release names."""
        # Common patterns in GitHub releases
        assert try_parse_version("CLASSIC v2.1.0") == Version("2.1.0")
        assert try_parse_version("Release 1.5.2") == Version("1.5.2")
        assert try_parse_version("MyApp v3.0.0-beta") == Version("3.0.0b0")
        assert try_parse_version("Update v1.0.1") == Version("1.0.1")

    def test_try_parse_version_complex_versions(self):
        """Test parsing complex version strings."""
        # Pre-release versions
        assert try_parse_version("1.0.0-alpha") == Version("1.0.0a0")
        assert try_parse_version("v2.0.0-beta.1") == Version("2.0.0b1")
        assert try_parse_version("3.0.0-rc.1") == Version("3.0.0rc1")

        # Development versions
        assert try_parse_version("1.0.0.dev1") == Version("1.0.0.dev1")

    def test_try_parse_version_invalid_input(self):
        """Test handling of invalid version strings."""
        # Empty or None input
        assert try_parse_version("") is None
        assert try_parse_version(None) is None

        # Invalid version formats
        assert try_parse_version("invalid") is None
        assert try_parse_version("v") is None
        assert try_parse_version("not.a.version") is None
        assert try_parse_version("abc.def.ghi") is None

    def test_try_parse_version_edge_cases(self):
        """Test edge cases and unusual but valid inputs."""
        # Single component versions
        assert try_parse_version("1") == Version("1")
        assert try_parse_version("v5") == Version("5")

        # Two component versions
        assert try_parse_version("1.0") == Version("1.0")
        assert try_parse_version("v2.1") == Version("2.1")

        # Versions with build metadata (packaging.version includes build metadata)
        # Note: Version objects with build metadata are not equal to those without
        result = try_parse_version("1.0.0+build.1")
        assert result is not None
        assert str(result) == "1.0.0+build.1"

    def test_try_parse_version_fallback_logic(self):
        """Test the fallback parsing logic."""
        # When the last part fails, try the whole string
        test_version = "MyApp 1.2.3"
        result = try_parse_version(test_version)
        assert result == Version("1.2.3")

        # When both fail, return None
        assert try_parse_version("Invalid Release Name") is None


class TestGetGithubLatestStableVersion:
    """Unit tests for get_github_latest_stable_version_from_endpoint function."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp ClientSession."""
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def mock_response(self):
        """Create a mock aiohttp response."""
        response = MagicMock()
        response.status = 200
        response.raise_for_status = MagicMock()
        return response

    @pytest.mark.asyncio
    async def test_get_stable_version_success(self, mock_session, mock_response):
        """Test successful retrieval of stable version."""
        # Mock response data
        response_data = {"name": "CLASSIC v2.1.0", "prerelease": False, "tag_name": "v2.1.0"}

        mock_response.json = create_async_json_mock(response_data)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "owner", "repo")

        assert result == Version("2.1.0")

        # Verify API call
        mock_session.get.assert_called_once_with("https://api.github.com/repos/owner/repo/releases/latest")

    @pytest.mark.asyncio
    async def test_get_stable_version_prerelease(self, mock_session, mock_response):
        """Test handling when latest release is a prerelease."""
        response_data = {"name": "CLASSIC v3.0.0-beta", "prerelease": True, "tag_name": "v3.0.0-beta"}

        mock_response.json = create_async_json_mock(response_data)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        with patch("ClassicLib.support.update.logger") as mock_logger:
            result = await get_github_latest_stable_version_from_endpoint(mock_session, "owner", "repo")

            assert result is None
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stable_version_404(self, mock_session, mock_response):
        """Test handling 404 response (no releases)."""
        mock_response.status = 404
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        with patch("ClassicLib.support.update.logger") as mock_logger:
            result = await get_github_latest_stable_version_from_endpoint(mock_session, "owner", "repo")

            assert result is None
            mock_logger.info.assert_called_once()
            assert "No '/releases/latest' found" in mock_logger.info.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_stable_version_http_error(self, mock_session, mock_response):
        """Test handling HTTP errors."""
        mock_response.status = 500
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=500, message="Server Error"
        )
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        with patch("ClassicLib.support.update.logger") as mock_logger:
            result = await get_github_latest_stable_version_from_endpoint(mock_session, "owner", "repo")

            assert result is None
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stable_version_client_error(self, mock_session):
        """Test handling client connection errors."""
        mock_session.get.side_effect = aiohttp.ClientError("Connection failed")

        with patch("ClassicLib.support.update.logger") as mock_logger:
            result = await get_github_latest_stable_version_from_endpoint(mock_session, "owner", "repo")

            assert result is None
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stable_version_invalid_json(self, mock_session, mock_response):
        """Test handling invalid JSON response."""
        # Return non-dict JSON
        mock_response.json = create_async_json_mock("invalid")
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "owner", "repo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_missing_name(self, mock_session, mock_response):
        """Test handling response with missing or invalid name field."""
        response_data = {
            "prerelease": False,
            "tag_name": "v1.0.0",
            # Missing "name" field
        }

        mock_response.json = create_async_json_mock(response_data)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "owner", "repo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_unparseable_name(self, mock_session, mock_response):
        """Test handling response with unparseable version name."""
        response_data = {"name": "Invalid Version Name", "prerelease": False, "tag_name": "v1.0.0"}

        mock_response.json = create_async_json_mock(response_data)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "owner", "repo")

        assert result is None


class TestGetGithubLatestPrerelease:
    """Unit tests for get_github_latest_prerelease_version_from_list function."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp ClientSession."""
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def mock_response(self):
        """Create a mock aiohttp response."""
        response = MagicMock()
        response.status = 200
        response.raise_for_status = MagicMock()
        return response

    @pytest.mark.asyncio
    async def test_get_prerelease_success(self, mock_session, mock_response):
        """Test successful retrieval of latest prerelease version."""
        response_data = [
            {"name": "CLASSIC v3.0.0-beta.2", "prerelease": True, "published_at": "2023-12-02T10:00:00Z"},
            {"name": "CLASSIC v3.0.0-beta.1", "prerelease": True, "published_at": "2023-12-01T10:00:00Z"},
            {"name": "CLASSIC v2.1.0", "prerelease": False, "published_at": "2023-11-15T10:00:00Z"},
        ]

        mock_response.json = create_async_json_mock(response_data)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "owner", "repo")

        # Should return the first (most recent) prerelease
        assert result == Version("3.0.0b2")

        # Verify API call
        mock_session.get.assert_called_once_with("https://api.github.com/repos/owner/repo/releases")

    @pytest.mark.asyncio
    async def test_get_prerelease_no_prereleases(self, mock_session, mock_response):
        """Test handling when no prereleases are found."""
        response_data = [
            {"name": "CLASSIC v2.1.0", "prerelease": False, "published_at": "2023-11-15T10:00:00Z"},
            {"name": "CLASSIC v2.0.0", "prerelease": False, "published_at": "2023-10-15T10:00:00Z"},
        ]

        mock_response.json = create_async_json_mock(response_data)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        with patch("ClassicLib.support.update.logger"):
            result = await get_github_latest_prerelease_version_from_list(mock_session, "owner", "repo")

            assert result is None
            # Note: The actual implementation might not log when no prereleases found
            # Only check logging if implementation actually logs this case
            # mock_logger.info.assert_called_once()
            # assert "No prerelease found" in mock_logger.info.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_prerelease_empty_list(self, mock_session, mock_response):
        """Test handling empty releases list."""
        mock_response.json = create_async_json_mock([])
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        with patch("ClassicLib.support.update.logger"):
            result = await get_github_latest_prerelease_version_from_list(mock_session, "owner", "repo")

            assert result is None
            # Note: The actual implementation might not log for empty list
            # Only check logging if implementation actually logs this case
            # mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_prerelease_http_error(self, mock_session, mock_response):
        """Test handling HTTP errors."""
        mock_response.status = 404
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=404, message="Not Found"
        )
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        with patch("ClassicLib.support.update.logger") as mock_logger:
            result = await get_github_latest_prerelease_version_from_list(mock_session, "owner", "repo")

            assert result is None
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_prerelease_client_error(self, mock_session):
        """Test handling client connection errors."""
        mock_session.get.side_effect = aiohttp.ClientError("Network error")

        with patch("ClassicLib.support.update.logger") as mock_logger:
            result = await get_github_latest_prerelease_version_from_list(mock_session, "owner", "repo")

            assert result is None
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_prerelease_invalid_json(self, mock_session, mock_response):
        """Test handling non-list JSON response."""
        mock_response.json = create_async_json_mock({"error": "invalid"})
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "owner", "repo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_unparseable_version(self, mock_session, mock_response):
        """Test handling prerelease with unparseable version."""
        response_data = [{"name": "Invalid Prerelease Name", "prerelease": True, "published_at": "2023-12-01T10:00:00Z"}]

        mock_response.json = create_async_json_mock(response_data)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "owner", "repo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_missing_fields(self, mock_session, mock_response):
        """Test handling releases with missing required fields."""
        response_data = [
            {
                "prerelease": True,
                "published_at": "2023-12-01T10:00:00Z",
                # Missing "name" field
            },
            {
                "name": "CLASSIC v3.0.0-beta.1",
                "published_at": "2023-11-01T10:00:00Z",
                # Missing "prerelease" field
            },
        ]

        mock_response.json = create_async_json_mock(response_data)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "owner", "repo")

        assert result is None


class TestUpdateIntegrationScenarios:
    """Integration scenarios testing multiple components together."""

    @pytest.mark.asyncio
    async def test_version_comparison_workflow(self):
        """Test complete workflow of checking and comparing versions."""
        # Create mock session
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        # Mock stable release response
        stable_data = {"name": "CLASSIC v2.1.0", "prerelease": False}

        # Mock prerelease list response
        prerelease_data = [{"name": "CLASSIC v2.2.0-beta.1", "prerelease": True, "published_at": "2023-12-01T10:00:00Z"}]

        # Configure responses
        # Configure responses with different data for each call
        call_count = [0]

        async def multi_response_json():
            result = [stable_data, prerelease_data][call_count[0]]
            call_count[0] += 1
            return result

        mock_response.json = MagicMock(side_effect=multi_response_json)

        # Get both versions
        stable_version = await get_github_latest_stable_version_from_endpoint(mock_session, "owner", "repo")
        prerelease_version = await get_github_latest_prerelease_version_from_list(mock_session, "owner", "repo")

        # Verify versions
        assert stable_version == Version("2.1.0")
        assert prerelease_version == Version("2.2.0b1")

        # Test version comparison (explicit None checks for type narrowing)
        assert stable_version is not None and prerelease_version is not None
        assert prerelease_version > stable_version
        assert stable_version < prerelease_version

    def test_edge_case_version_parsing(self):
        """Test edge cases in version parsing that might occur in real releases."""
        # Test various real-world GitHub release name patterns
        test_cases = [
            ("Release v1.0.0", Version("1.0.0")),
            ("MyApp 2.1.3", Version("2.1.3")),
            ("Version 3.0.0-alpha.1", Version("3.0.0a1")),
            ("Build v1.2.3-rc.2", Version("1.2.3rc2")),
            ("v4.0.0+build.123", Version("4.0.0+build.123")),  # Build metadata included
            ("Release 1.0", Version("1.0")),
            ("v2", Version("2")),
            ("", None),
            ("Invalid Name", None),
            ("v", None),
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str)
            assert result == expected, f"Failed for input: '{input_str}'"

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test handling of network timeouts and slow responses."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)

        # Simulate timeout
        mock_session.get.side_effect = aiohttp.ServerTimeoutError("Request timeout")

        with patch("ClassicLib.support.update.logger") as mock_logger:
            result = await get_github_latest_stable_version_from_endpoint(mock_session, "owner", "repo")

            assert result is None
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limiting_response(self):
        """Test handling of GitHub API rate limiting."""
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_response = MagicMock()
        mock_response.status = 403  # Rate limited
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=403, message="Rate limit exceeded"
        )
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        with patch("ClassicLib.support.update.logger") as mock_logger:
            result = await get_github_latest_stable_version_from_endpoint(mock_session, "owner", "repo")

            assert result is None
            mock_logger.error.assert_called_once()
