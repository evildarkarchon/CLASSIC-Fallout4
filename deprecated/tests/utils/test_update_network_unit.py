"""
Unit tests for Update module network operations.

This module tests GitHub API interactions via the Rust GithubClient binding,
error handling, and complex network scenarios for the Update module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib.support.update import (
    _parse_release_version,
    get_github_latest_prerelease_version,
    get_github_latest_stable_version,
)


def _make_mock_release(*, name: str, tag_name: str, prerelease: bool = False) -> MagicMock:
    """Create a mock GithubRelease object."""
    release = MagicMock()
    release.name = name
    release.tag_name = tag_name
    release.prerelease = prerelease
    return release


class TestGitHubLatestStableVersion:
    """Unit tests for get_github_latest_stable_version function."""

    @pytest.mark.asyncio
    async def test_get_stable_version_success(self):
        """Test successful retrieval of stable version."""
        mock_release = _make_mock_release(name="CLASSIC v2.1.0", tag_name="v2.1.0")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("testowner", "testrepo")

        assert result == Version("2.1.0")

    @pytest.mark.asyncio
    async def test_get_stable_version_prerelease_rejection(self):
        """Test rejection of prerelease versions."""
        mock_release = _make_mock_release(name="CLASSIC v2.1.0-beta", tag_name="v2.1.0-beta", prerelease=True)
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with (
            patch("ClassicLib.support.update.GithubClient", return_value=mock_client),
            patch("ClassicLib.support.update.logger") as mock_logger,
        ):
            result = await get_github_latest_stable_version("testowner", "testrepo")

        assert result is None
        mock_logger.warning.assert_called_once()
        assert "prerelease" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_stable_version_network_error(self):
        """Test handling of network errors (RuntimeError from Rust)."""
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(side_effect=RuntimeError("GitHub API error: connection refused"))

        with (
            patch("ClassicLib.support.update.GithubClient", return_value=mock_client),
            patch("ClassicLib.support.update.logger") as mock_logger,
        ):
            result = await get_github_latest_stable_version("testowner", "testrepo")

        assert result is None
        mock_logger.error.assert_called_once()
        assert "Error fetching latest stable release" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_stable_version_unparseable_name_and_tag(self):
        """Test handling of unparseable version name and tag."""
        mock_release = _make_mock_release(name="Invalid Version Name", tag_name="invalid-tag")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("testowner", "testrepo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_fallback_to_tag_name(self):
        """Test fallback to tag_name when name is unparseable."""
        mock_release = _make_mock_release(name="Some Release", tag_name="v2.1.0")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("testowner", "testrepo")

        assert result == Version("2.1.0")

    @pytest.mark.asyncio
    async def test_get_stable_version_v_prefix_tag(self):
        """Test parsing version from tag with v prefix."""
        mock_release = _make_mock_release(name="v2.1.0", tag_name="v2.1.0")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("testowner", "testrepo")

        assert result == Version("2.1.0")


class TestGitHubLatestPrereleaseVersion:
    """Unit tests for get_github_latest_prerelease_version function."""

    @pytest.mark.asyncio
    async def test_get_prerelease_version_success(self):
        """Test successful retrieval of prerelease version."""
        releases = [
            _make_mock_release(name="CLASSIC v2.2.0", tag_name="v2.2.0"),
            _make_mock_release(name="CLASSIC v2.2.0-beta.2", tag_name="v2.2.0-beta.2", prerelease=True),
            _make_mock_release(name="CLASSIC v2.1.0", tag_name="v2.1.0"),
            _make_mock_release(name="CLASSIC v2.2.0-beta.1", tag_name="v2.2.0-beta.1", prerelease=True),
        ]
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=releases)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("testowner", "testrepo")

        # Should return the first prerelease (most recent)
        assert result == Version("2.2.0b2")

    @pytest.mark.asyncio
    async def test_get_prerelease_no_prereleases_available(self):
        """Test when no prereleases are available."""
        releases = [
            _make_mock_release(name="CLASSIC v2.1.0", tag_name="v2.1.0"),
            _make_mock_release(name="CLASSIC v2.0.0", tag_name="v2.0.0"),
        ]
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=releases)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("testowner", "testrepo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_network_error(self):
        """Test handling of network errors (RuntimeError from Rust)."""
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(side_effect=RuntimeError("GitHub API error: connection failed"))

        with (
            patch("ClassicLib.support.update.GithubClient", return_value=mock_client),
            patch("ClassicLib.support.update.logger") as mock_logger,
        ):
            result = await get_github_latest_prerelease_version("testowner", "testrepo")

        assert result is None
        mock_logger.error.assert_called_once()
        assert "Error fetching releases list" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_prerelease_unparseable_versions_skipped(self):
        """Test handling of prereleases with unparseable version names."""
        releases = [
            _make_mock_release(name="Invalid Prerelease Name", tag_name="invalid", prerelease=True),
            _make_mock_release(name="CLASSIC v2.1.0-beta", tag_name="v2.1.0-beta", prerelease=True),
        ]
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=releases)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("testowner", "testrepo")

        # Should skip invalid version and find the valid one
        assert result == Version("2.1.0b0")

    @pytest.mark.asyncio
    async def test_get_prerelease_empty_release_list(self):
        """Test handling of empty releases list."""
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=[])

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("testowner", "testrepo")

        assert result is None


class TestParseReleaseVersion:
    """Unit tests for _parse_release_version helper."""

    def test_parse_from_name(self):
        """Test parsing version from release name."""
        release = _make_mock_release(name="CLASSIC v2.1.0", tag_name="v2.1.0")
        assert _parse_release_version(release) == Version("2.1.0")

    def test_parse_fallback_to_tag(self):
        """Test fallback to tag_name when name is unparseable."""
        release = _make_mock_release(name="Some Release", tag_name="v2.1.0")
        assert _parse_release_version(release) == Version("2.1.0")

    def test_parse_both_unparseable(self):
        """Test when both name and tag_name are unparseable."""
        release = _make_mock_release(name="Invalid", tag_name="also-invalid")
        assert _parse_release_version(release) is None

    def test_parse_name_preferred_over_tag(self):
        """Test that name is preferred over tag_name."""
        release = _make_mock_release(name="CLASSIC v2.1.0", tag_name="v2.0.0")
        # Name should be parsed first and used
        assert _parse_release_version(release) == Version("2.1.0")
