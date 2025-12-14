"""
Unit tests for Nexus version scraping functionality in Update.py.

This module tests the Nexus version retrieval functionality which
scrapes version information from Nexus Mods pages.
"""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from ClassicLib.Update import get_nexus_version


def create_async_text_mock(return_value):
    """Create a mock for response.text that returns an async coroutine.

    This helper is needed because response.text is an async property that
    must be awaited, so we need to return a coroutine, not a plain value.
    """

    async def async_text():
        return return_value

    return async_text


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
