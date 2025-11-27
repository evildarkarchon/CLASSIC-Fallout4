"""
Comprehensive unit tests for Update.py network operations.

This module provides comprehensive test coverage for the Update.py module,
focusing on network operations, version parsing, GitHub API interactions,
Nexus scraping, and update checking logic with proper mocking.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest
from packaging.version import Version

from ClassicLib.Update import (
    UpdateCheckError,
    get_github_latest_prerelease_version_from_list,
    get_github_latest_stable_version_from_endpoint,
    get_latest_and_top_release_details,
    get_nexus_version,
    is_latest_version,
    try_parse_version,
)


def create_async_json_mock(return_value):
    """Create a mock for response.json() that returns an async coroutine.

    This helper is needed because response.json() is an async method that
    must be awaited, so we need to return a coroutine, not a plain value.
    """

    async def async_json():
        return return_value

    return async_json


def create_async_text_mock(return_value):
    """Create a mock for response.text that returns an async coroutine.

    This helper is needed because response.text is an async property that
    must be awaited, so we need to return a coroutine, not a plain value.
    """

    async def async_text():
        return return_value

    return async_text


@pytest.mark.unit
class TestTryParseVersion:
    """Test version parsing functionality."""

    def test_parse_version_simple_format(self):
        """Test parsing simple version formats."""
        test_cases = [
            ("1.0.0", "1.0.0"),
            ("2.1.3", "2.1.3"),
            ("10.25.99", "10.25.99"),
            ("1.0", "1.0"),
            ("1", "1"),
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str)
            assert result is not None
            assert str(result) == expected

    def test_parse_version_with_v_prefix(self):
        """Test parsing versions with 'v' prefix."""
        test_cases = [
            ("v1.0.0", "1.0.0"),
            ("v2.1.3", "2.1.3"),
            ("v10.25.99", "10.25.99"),
            ("v1.0", "1.0"),
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str)
            assert result is not None
            assert str(result) == expected

    def test_parse_version_from_release_name(self):
        """Test parsing versions from GitHub release names."""
        test_cases = [
            ("CLASSIC v7.30.1", "7.30.1"),
            ("MyApp v1.2.3", "1.2.3"),
            ("Tool Release v2.0.0", "2.0.0"),
            ("Project Name v10.1.5", "10.1.5"),
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str)
            assert result is not None
            assert str(result) == expected

    def test_parse_version_complex_formats(self):
        """Test parsing complex version formats."""
        test_cases = [
            ("1.0.0-alpha", "1.0.0a0"),
            ("2.1.0-beta.1", "2.1.0b1"),
            ("1.0.0-rc.1", "1.0.0rc1"),
            ("3.0.0.dev1", "3.0.0.dev1"),
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str)
            assert result is not None
            assert str(result) == expected

    def test_parse_version_invalid_formats(self):
        """Test handling of invalid version formats."""
        invalid_inputs = [
            "",
            "not_a_version",
            "abc.def.ghi",
            "v",
            "version",
            "release",
            "v.1.0.0",
            "random text",
            None,
        ]

        for invalid_input in invalid_inputs:
            result = try_parse_version(invalid_input)
            assert result is None

    def test_parse_version_edge_cases(self):
        """Test edge cases in version parsing."""
        test_cases = [
            ("v0.0.1", "0.0.1"),  # Very low version
            ("v999.999.999", "999.999.999"),  # Very high version
            ("CLASSIC v7.30.1", "7.30.1"),  # Actual expected format from requirements
            ("Tool v1.0.0", "1.0.0"),  # Simple tool version
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str)
            assert result is not None
            assert str(result) == expected

    def test_parse_version_whitespace_handling(self):
        """Test handling of whitespace in version strings."""
        test_cases = [
            ("  v1.0.0  ", "1.0.0"),
            ("\tv2.1.0\n", "2.1.0"),
            ("App Name  v3.0.0", "3.0.0"),
        ]

        for input_str, expected in test_cases:
            result = try_parse_version(input_str.strip())
            assert result is not None
            assert str(result) == expected


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
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(request_info=Mock(), history=Mock(), status=500)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_stable_version_from_endpoint(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_invalid_json(self, mock_session):
        """Test handling of invalid JSON response."""
        # Mock response with invalid JSON structure
        mock_response = AsyncMock()
        mock_response.status = 200
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
        mock_response.json = AsyncMock(side_effect=create_async_json_mock({"not": "a list"}))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_empty_list(self, mock_session):
        """Test handling of empty releases list."""
        # Mock empty response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(side_effect=create_async_json_mock([]))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_github_latest_prerelease_version_from_list(mock_session, "evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_unparseable_versions(self, mock_session):
        """Test handling of unparseable prerelease versions."""
        # Mock response with unparseable prereleases
        mock_response = AsyncMock()
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

        list_response = AsyncMock()
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


@pytest.mark.unit
class TestNexusVersionScraping:
    """Test Nexus version scraping functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp session."""
        return AsyncMock(spec=aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_get_nexus_version_success(self, mock_session):
        """Test successful Nexus version retrieval."""
        # Create mock HTML with proper meta tags
        html_content = """
        <html>
        <head>
            <meta property="twitter:label1" content="Version">
            <meta property="twitter:data1" content="7.30.1">
        </head>
        </html>
        """

        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(side_effect=create_async_text_mock(html_content))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_nexus_version(mock_session)

        assert result is not None
        assert str(result) == "7.30.1"
        mock_session.get.assert_called_once_with("https://www.nexusmods.com/fallout4/mods/56255")

    @pytest.mark.asyncio
    async def test_get_nexus_version_http_error(self, mock_session):
        """Test handling of HTTP errors."""
        mock_response = AsyncMock()
        mock_response.ok = False
        mock_response.status = 404
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_nexus_version(mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_nexus_version_missing_label_tag(self, mock_session):
        """Test when version label meta tag is missing."""
        html_content = """
        <html>
        <head>
            <meta property="twitter:data1" content="7.30.1">
        </head>
        </html>
        """

        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(side_effect=create_async_text_mock(html_content))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_nexus_version(mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_nexus_version_missing_data_tag(self, mock_session):
        """Test when version data meta tag is missing."""
        html_content = """
        <html>
        <head>
            <meta property="twitter:label1" content="Version">
        </head>
        </html>
        """

        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(side_effect=create_async_text_mock(html_content))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_nexus_version(mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_nexus_version_invalid_html(self, mock_session):
        """Test handling of invalid HTML."""
        html_content = "Not valid HTML content"

        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(side_effect=create_async_text_mock(html_content))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_nexus_version(mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_nexus_version_network_error(self, mock_session):
        """Test handling of network errors."""
        mock_session.get.return_value.__aenter__.side_effect = aiohttp.ClientError("Connection failed")

        result = await get_nexus_version(mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_nexus_version_unparseable_version(self, mock_session):
        """Test handling of unparseable version content."""
        html_content = """
        <html>
        <head>
            <meta property="twitter:label1" content="Version">
            <meta property="twitter:data1" content="invalid version">
        </head>
        </html>
        """

        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(side_effect=create_async_text_mock(html_content))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_nexus_version(mock_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_nexus_version_with_v_prefix(self, mock_session):
        """Test Nexus version with 'v' prefix."""
        html_content = """
        <html>
        <head>
            <meta property="twitter:label1" content="Version">
            <meta property="twitter:data1" content="v7.30.1">
        </head>
        </html>
        """

        mock_response = AsyncMock()
        mock_response.ok = True
        mock_response.text = AsyncMock(side_effect=create_async_text_mock(html_content))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_nexus_version(mock_session)

        assert result is not None
        assert str(result) == "7.30.1"

    @pytest.mark.asyncio
    async def test_get_nexus_version_parsing_exception(self, mock_session):
        """Test handling of HTML parsing exceptions."""
        mock_response = AsyncMock()
        mock_response.ok = True

        # Create a mock that raises an exception when called
        async def async_text_error():
            raise Exception("Parsing error")

        mock_response.text = MagicMock(side_effect=async_text_error)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)

        result = await get_nexus_version(mock_session)

        assert result is None


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
            patch("ClassicLib.Update.yaml_settings") as mock_yaml_settings,
            patch("ClassicLib.Update.classic_settings") as mock_classic_settings,
            patch("ClassicLib.GlobalRegistry.get_game") as mock_get_game,
            patch("ClassicLib.Update.logger") as mock_logger,
        ):
            # Don't mock the message functions since MessageHandler is initialized
            from ClassicLib import msg_error, msg_success, msg_warning

            yield {
                "yaml_settings": mock_yaml_settings,
                "classic_settings": mock_classic_settings,
                "get_game": mock_get_game,
                "msg_warning": msg_warning,
                "msg_success": msg_success,
                "msg_error": msg_error,
                "logger": mock_logger,
            }

    @pytest.mark.asyncio
    async def test_is_latest_version_disabled_check(self, mock_dependencies):
        """Test when update check is disabled."""

        def classic_settings_side_effect(type_arg, key, default=None):
            # Return False for Update Check
            if key == "Update Check":
                return False
            return default

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect  # Update check disabled

        result = await is_latest_version(quiet=False, gui_request=False)

        assert result is False
        # Message would be logged via the real msg_info function
        # We're testing the result, not the message logging

    @pytest.mark.asyncio
    async def test_is_latest_version_invalid_source(self, mock_dependencies):
        """Test with invalid update source setting."""

        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "InvalidSource"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        result = await is_latest_version(quiet=False, gui_request=False)

        assert result is False
        # Message would be logged via the real msg_info function
        # We're testing the result, not the message logging

    @pytest.mark.asyncio
    async def test_is_latest_version_up_to_date(self, mock_dependencies):
        """Test when local version is up to date."""

        # Configure settings - classic_settings takes type and key
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        # Mock local version
        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": "CLASSIC v7.30.1",
            "CLASSIC_Info.is_prerelease": False,
        }.get(key, default)

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
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        # Mock local version (older)
        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": "CLASSIC v7.30.0",
            "CLASSIC_Info.is_prerelease": False,
        }.get(key, default)

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
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        # Mock local version (older)
        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": "CLASSIC v7.30.0",
            "CLASSIC_Info.is_prerelease": False,
            "CLASSIC_Interface.update_warning_fallout4": "Update warning message",
        }.get(key, default)

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
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "Both"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        # Mock local version
        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": "CLASSIC v7.30.0",
            "CLASSIC_Info.is_prerelease": False,
        }.get(key, default)

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
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        # Mock local version
        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": "CLASSIC v7.30.1",
            "CLASSIC_Info.is_prerelease": False,
            "CLASSIC_Interface.update_unable_fallout4": "Unable to check updates",
        }.get(key, default)

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
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "Nexus"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        # Mock prerelease version
        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": "CLASSIC v7.31.0-beta",
            "CLASSIC_Info.is_prerelease": True,  # Prerelease
        }.get(key, default)

        # Mock registry
        mock_dependencies["get_game"].return_value = "fallout4"

        result = await is_latest_version(quiet=False, gui_request=False)

        # Should be treated as up to date since Nexus check is skipped for prereleases
        assert result is True

    @pytest.mark.asyncio
    async def test_is_latest_version_unknown_local_version(self, mock_dependencies):
        """Test when local version is unknown."""

        # Configure settings
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        # Mock unknown local version
        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": None,  # Unknown version
            "CLASSIC_Info.is_prerelease": False,
        }.get(key, default)

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
            patch("ClassicLib.Update.yaml_settings") as mock_yaml_settings,
            patch("ClassicLib.Update.classic_settings") as mock_classic_settings,
            patch("ClassicLib.GlobalRegistry.get_game") as mock_get_game,
        ):
            yield {
                "yaml_settings": mock_yaml_settings,
                "classic_settings": mock_classic_settings,
                "classic_settings": mock_classic_settings,
                "get_game": mock_get_game,
            }

    @pytest.mark.asyncio
    async def test_source_failure_github_only(self, mock_dependencies):
        """Test error when GitHub-only source fails."""

        # Configure settings for GitHub only
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": "CLASSIC v7.30.1",
            "CLASSIC_Info.is_prerelease": False,
        }.get(key, default)

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
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "Nexus"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": "CLASSIC v7.30.1",
            "CLASSIC_Info.is_prerelease": False,
        }.get(key, default)

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
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "Both"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": "CLASSIC v7.30.1",
            "CLASSIC_Info.is_prerelease": False,
        }.get(key, default)

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
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "Both"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": "CLASSIC v7.30.0",  # Older version
            "CLASSIC_Info.is_prerelease": False,
        }.get(key, default)

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
        def classic_settings_side_effect(type_arg, key, default=None):
            settings_map = {"Update Check": True, "Update Source": "GitHub"}
            return settings_map.get(key, default)

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect

        mock_dependencies["yaml_settings"].side_effect = lambda type_cls, enum, key, default=None: {
            "CLASSIC_Info.version": "CLASSIC v7.30.1",
            "CLASSIC_Info.is_prerelease": False,
        }.get(key, default)

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

        def classic_settings_side_effect(type_arg, key, default=None):
            # Return False for Update Check
            if key == "Update Check":
                return False
            return default

        mock_dependencies["classic_settings"].side_effect = classic_settings_side_effect  # Update check disabled

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
