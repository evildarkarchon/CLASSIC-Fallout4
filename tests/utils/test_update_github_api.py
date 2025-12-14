"""
Unit tests for GitHub API interactions in Update.py.

This module tests GitHub API functionality including stable version
retrieval from endpoints, prerelease version listing, and release
details fetching.
"""

from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest

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


@pytest.mark.unit
class TestGitHubStableVersionEndpoint:
    """Test GitHub stable version endpoint functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        return AsyncMock(spec=aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_get_stable_version_success(self, mock_session):
        """Test successful retrieval of stable version."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = Mock()  # Ensure this is sync
        mock_response.json = AsyncMock(
            side_effect=create_async_json_mock({"name": "CLASSIC v7.30.1", "prerelease": False, "tag_name": "v7.30.1"})
        )
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is not None
        assert str(result) == "7.30.1"
        mock_session.get.assert_called_once_with("https://api.github.com/repos/evildarkarchon/CLASSIC-Fallout4/releases/latest")

    @pytest.mark.asyncio
    async def test_get_stable_version_prerelease_returned(self, mock_session):
        """Test when endpoint returns a prerelease instead of stable."""
        # Mock response with prerelease flag
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = Mock()  # Ensure this is sync
        mock_response.json = AsyncMock(
            side_effect=create_async_json_mock({"name": "CLASSIC v7.31.0-beta", "prerelease": True, "tag_name": "v7.31.0-beta"})
        )
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_404_not_found(self, mock_session):
        """Test handling of 404 response (no releases found)."""
        # Mock 404 response
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_network_error(self, mock_session):
        """Test handling of network errors."""
        # Mock network error
        mock_session.get.return_value.__aenter__.side_effect = aiohttp.ClientError("Connection failed")

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_http_error(self, mock_session):
        """Test handling of HTTP errors."""
        # Mock HTTP error response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.raise_for_status = Mock(side_effect=aiohttp.ClientResponseError(request_info=Mock(), history=Mock(), status=500))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_invalid_json(self, mock_session):
        """Test handling of invalid JSON response."""
        # Mock response with invalid JSON structure
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(side_effect=create_async_json_mock("not a dict"))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_missing_name(self, mock_session):
        """Test handling of response missing name field."""
        # Mock response without name field
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(side_effect=create_async_json_mock({"prerelease": False, "tag_name": "v7.30.1"}))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_unparseable_name(self, mock_session):
        """Test handling of unparseable version name."""
        # Mock response with unparseable version
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(
            side_effect=create_async_json_mock({"name": "Invalid Version Name", "prerelease": False, "tag_name": "invalid"})
        )
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None


@pytest.mark.unit
class TestGitHubPrereleaseVersionList:
    """Test GitHub prerelease version list functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        return AsyncMock(spec=aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_get_prerelease_version_success(self, mock_session):
        """Test successful retrieval of prerelease version."""
        # Mock successful response with prerelease
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(
            side_effect=create_async_json_mock([
                {"name": "CLASSIC v7.30.1", "prerelease": False, "tag_name": "v7.30.1"},
                {"name": "CLASSIC v7.31.0-beta", "prerelease": True, "tag_name": "v7.31.0-beta"},
                {"name": "CLASSIC v7.30.0", "prerelease": False, "tag_name": "v7.30.0"},
            ])
        )
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is not None
        assert str(result) == "7.31.0b0"  # First prerelease found

    @pytest.mark.asyncio
    async def test_get_prerelease_no_prereleases_found(self, mock_session):
        """Test when no prereleases are found."""
        # Mock response with only stable releases
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(
            side_effect=create_async_json_mock([
                {"name": "CLASSIC v7.30.1", "prerelease": False, "tag_name": "v7.30.1"},
                {"name": "CLASSIC v7.30.0", "prerelease": False, "tag_name": "v7.30.0"},
            ])
        )
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_network_error(self, mock_session):
        """Test handling of network errors."""
        # Mock network error
        mock_session.get.return_value.__aenter__.side_effect = aiohttp.ClientError("Connection failed")

        result = await get_github_latest_prerelease_version_from_list(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_invalid_json_structure(self, mock_session):
        """Test handling of invalid JSON structure."""
        # Mock response with non-list JSON
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(side_effect=create_async_json_mock({"not": "a list"}))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_empty_list(self, mock_session):
        """Test handling of empty releases list."""
        # Mock empty response
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(side_effect=create_async_json_mock([]))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_unparseable_versions(self, mock_session):
        """Test handling of unparseable prerelease versions."""
        # Mock response with unparseable prereleases
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = AsyncMock(
            side_effect=create_async_json_mock([
                {"name": "Invalid Prerelease Name", "prerelease": True, "tag_name": "invalid"},
                {"name": "Another Bad Name", "prerelease": True, "tag_name": "bad"},
            ])
        )
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None


@pytest.mark.unit
class TestGitHubReleaseDetails:
    """Test GitHub release details retrieval functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        return AsyncMock(spec=aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_get_release_details_success(self, mock_session):
        """Test successful retrieval of release details."""
        # Mock both endpoints returning data
        latest_response = AsyncMock()
        latest_response.status = 200
        latest_response.raise_for_status = Mock()
        latest_response.json = AsyncMock(
            side_effect=create_async_json_mock({
                "id": 123,
                "name": "CLASSIC v7.30.1",
                "tag_name": "v7.30.1",
                "prerelease": False,
                "published_at": "2024-01-01T00:00:00Z",
            })
        )

        list_response = AsyncMock()
        list_response.raise_for_status = Mock()
        list_response.json = AsyncMock(
            side_effect=create_async_json_mock([
                {"id": 123, "name": "CLASSIC v7.30.1", "tag_name": "v7.30.1", "prerelease": False, "published_at": "2024-01-01T00:00:00Z"}
            ])
        )

        # Mock session.get to return different responses based on URL
        def mock_get_side_effect(url):
            mock_context = AsyncMock()
            if "latest" in url:
                mock_context.__aenter__ = AsyncMock(return_value=latest_response)
            else:
                mock_context.__aenter__ = AsyncMock(return_value=list_response)
            return mock_context

        mock_session.get.side_effect = mock_get_side_effect

        result = await get_latest_and_top_release_details(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is not None
        assert result["are_same_release_by_id"] is True
        assert result["latest_endpoint_release"]["name"] == "CLASSIC v7.30.1"
        assert result["top_of_list_release"]["name"] == "CLASSIC v7.30.1"

    @pytest.mark.asyncio
    async def test_get_release_details_different_releases(self, mock_session):
        """Test when latest endpoint and top of list are different releases."""
        # Mock different releases
        latest_response = AsyncMock()
        latest_response.status = 200
        latest_response.raise_for_status = Mock()
        latest_response.json = AsyncMock(
            side_effect=create_async_json_mock({
                "id": 123,
                "name": "CLASSIC v7.30.1",
                "tag_name": "v7.30.1",
                "prerelease": False,
                "published_at": "2024-01-01T00:00:00Z",
            })
        )

        list_response = AsyncMock()
        list_response.raise_for_status = Mock()
        list_response.json = AsyncMock(
            side_effect=create_async_json_mock([
                {
                    "id": 456,  # Different ID
                    "name": "CLASSIC v7.31.0-beta",
                    "tag_name": "v7.31.0-beta",
                    "prerelease": True,
                    "published_at": "2024-01-02T00:00:00Z",
                }
            ])
        )

        def mock_get_side_effect(url):
            mock_context = AsyncMock()
            if "latest" in url:
                mock_context.__aenter__ = AsyncMock(return_value=latest_response)
            else:
                mock_context.__aenter__ = AsyncMock(return_value=list_response)
            return mock_context

        mock_session.get.side_effect = mock_get_side_effect

        result = await get_latest_and_top_release_details(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is not None
        assert result["are_same_release_by_id"] is False
        assert result["latest_endpoint_release"]["id"] == 123
        assert result["top_of_list_release"]["id"] == 456

    @pytest.mark.asyncio
    async def test_get_release_details_latest_404(self, mock_session):
        """Test when latest endpoint returns 404."""
        # Mock 404 for latest endpoint
        latest_response = AsyncMock()
        latest_response.status = 404
        # No raise_for_status needed for 404 in this test path logic

        list_response = AsyncMock()
        list_response.raise_for_status = Mock()
        list_response.json = AsyncMock(
            side_effect=create_async_json_mock([
                {"id": 456, "name": "CLASSIC v7.30.1", "tag_name": "v7.30.1", "prerelease": False, "published_at": "2024-01-01T00:00:00Z"}
            ])
        )

        def mock_get_side_effect(url):
            mock_context = AsyncMock()
            if "latest" in url:
                mock_context.__aenter__ = AsyncMock(return_value=latest_response)
            else:
                mock_context.__aenter__ = AsyncMock(return_value=list_response)
            return mock_context

        mock_session.get.side_effect = mock_get_side_effect

        result = await get_latest_and_top_release_details(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is not None
        assert result["latest_endpoint_release"] is None
        assert result["top_of_list_release"] is not None
        assert result["are_same_release_by_id"] is False

    @pytest.mark.asyncio
    async def test_get_release_details_network_error(self, mock_session):
        """Test handling of network errors."""
        # Mock network error
        mock_session.get.side_effect = aiohttp.ClientError("Connection failed")

        result = await get_latest_and_top_release_details(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_release_details_empty_list(self, mock_session):
        """Test when releases list is empty."""
        latest_response = AsyncMock()
        latest_response.status = 200
        latest_response.raise_for_status = Mock()
        latest_response.json = AsyncMock(
            side_effect=create_async_json_mock({
                "id": 123,
                "name": "CLASSIC v7.30.1",
                "tag_name": "v7.30.1",
                "prerelease": False,
                "published_at": "2024-01-01T00:00:00Z",
            })
        )

        list_response = AsyncMock()
        list_response.raise_for_status = Mock()
        list_response.json = AsyncMock(side_effect=create_async_json_mock([]))

        def mock_get_side_effect(url):
            mock_context = AsyncMock()
            if "latest" in url:
                mock_context.__aenter__ = AsyncMock(return_value=latest_response)
            else:
                mock_context.__aenter__ = AsyncMock(return_value=list_response)
            return mock_context

        mock_session.get.side_effect = mock_get_side_effect

        result = await get_latest_and_top_release_details(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is not None
        assert result["latest_endpoint_release"] is not None
        assert result["top_of_list_release"] is None
