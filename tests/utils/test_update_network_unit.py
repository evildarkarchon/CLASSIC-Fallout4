"""
Unit tests for Update module network operations.

This module tests GitHub API interactions, error handling, and complex
network scenarios for the Update module's network functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from packaging.version import Version

from ClassicLib.Update import (
    get_github_latest_prerelease_version_from_list,
    get_github_latest_stable_version_from_endpoint,
    get_latest_and_top_release_details,
)


def create_async_json_mock(return_value):
    """Create a mock for response.json() that returns an async coroutine.

    This helper is needed because response.json() is an async method that
    must be awaited, so we need to return a coroutine, not a plain value.
    """

    async def async_json():
        return return_value

    return async_json


class TestGitHubLatestStableVersion:
    """Unit tests for get_github_latest_stable_version_from_endpoint function."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp ClientSession."""
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def mock_response_context(self):
        """Create a mock response context manager."""
        mock_response = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock()
        return mock_context, mock_response

    @pytest.mark.asyncio
    async def test_get_stable_version_success(self, mock_session, mock_response_context):
        """Test successful retrieval of stable version."""
        mock_context, mock_response = mock_response_context
        mock_session.get.return_value = mock_context

        # Configure successful response
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(
            side_effect=create_async_json_mock({"name": "CLASSIC v2.1.0", "prerelease": False, "tag_name": "v2.1.0"})
        )

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "testowner", "testrepo")

        # Verify correct API call
        mock_session.get.assert_called_once_with("https://api.github.com/repos/testowner/testrepo/releases/latest")

        # Verify version parsing
        assert result == Version("2.1.0")
        mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stable_version_404_not_found(self, mock_session, mock_response_context):
        """Test handling of 404 response (no releases)."""
        mock_context, mock_response = mock_response_context
        mock_session.get.return_value = mock_context

        # Configure 404 response
        mock_response.status = 404

        with patch("ClassicLib.Update.logger") as mock_logger:
            result = await get_github_latest_stable_version_from_endpoint(mock_session, "testowner", "testrepo")

            assert result is None
            mock_logger.info.assert_called_once()
            assert "No '/releases/latest' found" in mock_logger.info.call_args[0][0]

            # Should not call raise_for_status on 404
            mock_response.raise_for_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_stable_version_prerelease_rejection(self, mock_session, mock_response_context):
        """Test rejection of prerelease versions."""
        mock_context, mock_response = mock_response_context
        mock_session.get.return_value = mock_context

        # Configure prerelease response
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(
            side_effect=create_async_json_mock({"name": "CLASSIC v2.1.0-beta", "prerelease": True, "tag_name": "v2.1.0-beta"})
        )

        with patch("ClassicLib.Update.logger") as mock_logger:
            result = await get_github_latest_stable_version_from_endpoint(mock_session, "testowner", "testrepo")

            assert result is None
            mock_logger.warning.assert_called_once()
            assert "returned a prerelease" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_stable_version_network_error(self, mock_session):
        """Test handling of network errors."""
        # Configure the session.get to raise an exception directly
        mock_session.get.side_effect = aiohttp.ClientError("Network error")

        with patch("ClassicLib.Update.logger") as mock_logger:
            result = await get_github_latest_stable_version_from_endpoint(mock_session, "testowner", "testrepo")

            assert result is None
            mock_logger.error.assert_called_once()
            assert "Error fetching latest stable release" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_stable_version_invalid_json(self, mock_session, mock_response_context):
        """Test handling of invalid JSON response."""
        mock_context, mock_response = mock_response_context
        mock_session.get.return_value = mock_context

        # Configure invalid JSON response
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = create_async_json_mock("not a dict")

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "testowner", "testrepo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_missing_name(self, mock_session, mock_response_context):
        """Test handling of response without release name."""
        mock_context, mock_response = mock_response_context
        mock_session.get.return_value = mock_context

        # Configure response without name
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(
            side_effect=create_async_json_mock({
                "prerelease": False,
                "tag_name": "v2.1.0",
                # Missing "name" field
            })
        )

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "testowner", "testrepo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_unparseable_name(self, mock_session, mock_response_context):
        """Test handling of unparseable version name."""
        mock_context, mock_response = mock_response_context
        mock_session.get.return_value = mock_context

        # Configure response with unparseable name
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(side_effect=create_async_json_mock({"name": "Invalid Version Name", "prerelease": False}))

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "testowner", "testrepo")

        assert result is None


class TestGitHubLatestPrereleaseVersion:
    """Unit tests for get_github_latest_prerelease_version_from_list function."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp ClientSession."""
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def mock_response_context(self):
        """Create a mock response context manager."""
        mock_response = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock()
        return mock_context, mock_response

    @pytest.mark.asyncio
    async def test_get_prerelease_version_success(self, mock_session, mock_response_context):
        """Test successful retrieval of prerelease version."""
        mock_context, mock_response = mock_response_context
        mock_session.get.return_value = mock_context

        # Configure successful response with multiple releases
        releases_data = [
            {"name": "CLASSIC v2.2.0", "prerelease": False, "tag_name": "v2.2.0"},
            {"name": "CLASSIC v2.2.0-beta.2", "prerelease": True, "tag_name": "v2.2.0-beta.2"},
            {"name": "CLASSIC v2.1.0", "prerelease": False, "tag_name": "v2.1.0"},
            {"name": "CLASSIC v2.2.0-beta.1", "prerelease": True, "tag_name": "v2.2.0-beta.1"},
        ]

        mock_response.raise_for_status = MagicMock()
        mock_response.json = create_async_json_mock(releases_data)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "testowner", "testrepo")

        # Should return the first prerelease (most recent)
        assert result == Version("2.2.0b2")
        mock_session.get.assert_called_once_with("https://api.github.com/repos/testowner/testrepo/releases")

    @pytest.mark.asyncio
    async def test_get_prerelease_no_prereleases_available(self, mock_session, mock_response_context):
        """Test when no prereleases are available."""
        mock_context, mock_response = mock_response_context
        mock_session.get.return_value = mock_context

        # Configure response with only stable releases
        releases_data = [
            {"name": "CLASSIC v2.1.0", "prerelease": False, "tag_name": "v2.1.0"},
            {"name": "CLASSIC v2.0.0", "prerelease": False, "tag_name": "v2.0.0"},
        ]

        mock_response.raise_for_status = MagicMock()
        mock_response.json = create_async_json_mock(releases_data)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "testowner", "testrepo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_network_error(self, mock_session):
        """Test handling of network errors."""
        # Configure the session.get to raise an exception directly
        mock_session.get.side_effect = aiohttp.ClientConnectionError("Connection failed")

        with patch("ClassicLib.Update.logger") as mock_logger:
            result = await get_github_latest_prerelease_version_from_list(mock_session, "testowner", "testrepo")

            assert result is None
            mock_logger.error.assert_called_once()
            assert "Error fetching releases list" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_prerelease_invalid_response_format(self, mock_session, mock_response_context):
        """Test handling of invalid response format."""
        mock_context, mock_response = mock_response_context
        mock_session.get.return_value = mock_context

        # Configure response that's not a list
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(side_effect=create_async_json_mock({"error": "Not Found"}))

        with patch("ClassicLib.Update.logger") as mock_logger:
            result = await get_github_latest_prerelease_version_from_list(mock_session, "testowner", "testrepo")

            assert result is None
            mock_logger.warning.assert_called_once()
            assert "Expected a list of releases" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_prerelease_unparseable_versions(self, mock_session, mock_response_context):
        """Test handling of prereleases with unparseable version names."""
        mock_context, mock_response = mock_response_context
        mock_session.get.return_value = mock_context

        # Configure response with unparseable prerelease names
        releases_data = [
            {"name": "Invalid Prerelease Name", "prerelease": True, "tag_name": "invalid"},
            {"name": "CLASSIC v2.1.0-beta", "prerelease": True, "tag_name": "v2.1.0-beta"},
        ]

        mock_response.raise_for_status = MagicMock()
        mock_response.json = create_async_json_mock(releases_data)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "testowner", "testrepo")

        # Should skip invalid version and find the valid one
        assert result == Version("2.1.0b0")

    @pytest.mark.asyncio
    async def test_get_prerelease_empty_release_list(self, mock_session, mock_response_context):
        """Test handling of empty releases list."""
        mock_context, mock_response = mock_response_context
        mock_session.get.return_value = mock_context

        mock_response.raise_for_status = MagicMock()
        mock_response.json = create_async_json_mock([])

        result = await get_github_latest_prerelease_version_from_list(mock_session, "testowner", "testrepo")

        assert result is None


class TestGetLatestAndTopReleaseDetails:
    """Unit tests for get_latest_and_top_release_details function."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp ClientSession."""
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def mock_response_contexts(self):
        """Create multiple mock response context managers."""
        contexts = []
        responses = []
        for _i in range(2):
            mock_response = AsyncMock()
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock()
            contexts.append(mock_context)
            responses.append(mock_response)
        return contexts, responses

    @pytest.mark.asyncio
    async def test_get_release_details_same_release(self, mock_session, mock_response_contexts):
        """Test when latest and top release are the same."""
        contexts, responses = mock_response_contexts
        mock_session.get.side_effect = contexts

        # Configure responses for both endpoints
        latest_release = {"id": 12345, "name": "CLASSIC v2.1.0", "tag_name": "v2.1.0", "prerelease": False}

        releases_list = [latest_release]  # Same release at top of list

        # Latest endpoint response
        responses[0].status = 200
        responses[0].raise_for_status = MagicMock()
        responses[0].json = create_async_json_mock(latest_release)

        # Releases list endpoint response
        responses[1].raise_for_status = MagicMock()
        responses[1].json = create_async_json_mock(releases_list)

        result = await get_latest_and_top_release_details(mock_session, "testowner", "testrepo")

        assert result is not None
        # The function returns processed results with version objects
        assert result["latest_endpoint_release"]["id"] == 12345
        assert result["latest_endpoint_release"]["name"] == "CLASSIC v2.1.0"
        assert result["top_of_list_release"]["id"] == 12345
        assert result["are_same_release_by_id"] is True

        # Verify both API calls were made
        assert mock_session.get.call_count == 2
        mock_session.get.assert_any_call("https://api.github.com/repos/testowner/testrepo/releases/latest")
        mock_session.get.assert_any_call("https://api.github.com/repos/testowner/testrepo/releases")

    @pytest.mark.asyncio
    async def test_get_release_details_different_releases(self, mock_session, mock_response_contexts):
        """Test when latest and top release are different."""
        contexts, responses = mock_response_contexts
        mock_session.get.side_effect = contexts

        # Configure different releases
        latest_release = {"id": 12345, "name": "CLASSIC v2.0.0", "tag_name": "v2.0.0", "prerelease": False}

        top_release = {"id": 12346, "name": "CLASSIC v2.1.0-beta", "tag_name": "v2.1.0-beta", "prerelease": True}

        releases_list = [top_release, latest_release]

        # Latest endpoint response
        responses[0].status = 200
        responses[0].raise_for_status = MagicMock()
        responses[0].json = create_async_json_mock(latest_release)

        # Releases list endpoint response
        responses[1].raise_for_status = MagicMock()
        responses[1].json = create_async_json_mock(releases_list)

        result = await get_latest_and_top_release_details(mock_session, "testowner", "testrepo")

        assert result is not None
        assert result["latest_endpoint_release"]["id"] == 12345
        assert result["top_of_list_release"]["id"] == 12346
        assert result["are_same_release_by_id"] is False

    @pytest.mark.asyncio
    async def test_get_release_details_latest_404(self, mock_session, mock_response_contexts):
        """Test when latest endpoint returns 404."""
        contexts, responses = mock_response_contexts
        mock_session.get.side_effect = contexts

        top_release = {"id": 12346, "name": "CLASSIC v2.1.0", "tag_name": "v2.1.0", "prerelease": False}

        # Latest endpoint 404
        responses[0].status = 404

        # Releases list endpoint success
        responses[1].raise_for_status = MagicMock()
        responses[1].json = create_async_json_mock([top_release])

        with patch("ClassicLib.Update.logger") as mock_logger:
            result = await get_latest_and_top_release_details(mock_session, "testowner", "testrepo")

            assert result is not None
            assert result["latest_endpoint_release"] is None
            assert result["top_of_list_release"]["id"] == 12346
            assert result["are_same_release_by_id"] is False

            mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_release_details_both_endpoints_fail(self, mock_session, mock_response_contexts):
        """Test when both endpoints fail."""
        contexts, responses = mock_response_contexts
        mock_session.get.side_effect = contexts

        # Both endpoints fail
        responses[0].raise_for_status = MagicMock(side_effect=aiohttp.ClientError("Latest endpoint failed"))
        responses[0].status = 500

        responses[1].raise_for_status = MagicMock(side_effect=aiohttp.ClientError("Releases endpoint failed"))

        with patch("ClassicLib.Update.logger"):
            result = await get_latest_and_top_release_details(mock_session, "testowner", "testrepo")

            # When both endpoints fail, the function returns a structure with None values
            assert result is not None
            assert result["latest_endpoint_release"] is None
            assert result["top_of_list_release"] is None
            assert result["are_same_release_by_id"] is False

            # When both endpoints fail with raise_for_status, errors are caught internally
            # The function returns a result structure rather than logging errors

    @pytest.mark.asyncio
    async def test_get_release_details_empty_releases_list(self, mock_session, mock_response_contexts):
        """Test when releases list is empty."""
        contexts, responses = mock_response_contexts
        mock_session.get.side_effect = contexts

        latest_release = {"id": 12345, "name": "CLASSIC v2.1.0", "tag_name": "v2.1.0", "prerelease": False}

        # Latest endpoint success
        responses[0].status = 200
        responses[0].raise_for_status = MagicMock()
        responses[0].json = create_async_json_mock(latest_release)

        # Empty releases list
        responses[1].raise_for_status = MagicMock()
        responses[1].json = AsyncMock(side_effect=create_async_json_mock([]))

        result = await get_latest_and_top_release_details(mock_session, "testowner", "testrepo")

        assert result is not None
        assert result["latest_endpoint_release"]["id"] == 12345
        assert result["top_of_list_release"] is None
        assert result["are_same_release_by_id"] is False

    @pytest.mark.asyncio
    async def test_get_release_details_invalid_releases_list_format(self, mock_session, mock_response_contexts):
        """Test when releases list has invalid format."""
        contexts, responses = mock_response_contexts
        mock_session.get.side_effect = contexts

        latest_release = {"id": 12345, "name": "CLASSIC v2.1.0", "prerelease": False}

        # Latest endpoint success
        responses[0].status = 200
        responses[0].raise_for_status = MagicMock()
        responses[0].json = create_async_json_mock(latest_release)

        # Invalid releases list format (not a list)
        responses[1].raise_for_status = MagicMock()
        responses[1].json = create_async_json_mock({"error": "Not Found"})

        with patch("ClassicLib.Update.logger") as mock_logger:
            result = await get_latest_and_top_release_details(mock_session, "testowner", "testrepo")

            assert result is not None
            assert result["latest_endpoint_release"]["id"] == 12345
            assert result["top_of_list_release"] is None
            assert result["are_same_release_by_id"] is False

            # Warning is logged with a different message about no releases found
            mock_logger.warning.assert_called_once()
            assert "No releases found" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_release_details_no_valid_data(self, mock_session, mock_response_contexts):
        """Test when no valid release data is obtained from either endpoint."""
        contexts, responses = mock_response_contexts
        mock_session.get.side_effect = contexts

        # Latest endpoint returns invalid data
        responses[0].status = 200
        responses[0].raise_for_status = MagicMock()
        responses[0].json = AsyncMock(side_effect=create_async_json_mock("invalid"))

        # Releases list endpoint returns empty
        responses[1].raise_for_status = MagicMock()
        responses[1].json = AsyncMock(side_effect=create_async_json_mock([]))

        result = await get_latest_and_top_release_details(mock_session, "testowner", "testrepo")

        # When API returns invalid data, the function should still return basic structure with None values
        assert result is not None
        assert result["latest_endpoint_release"] is None
        assert result["top_of_list_release"] is None
        assert result["are_same_release_by_id"] is False
