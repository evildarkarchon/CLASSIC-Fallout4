"""
Unit tests for GitHub API interactions via Rust GithubClient in Update.py.

This module tests GitHub API functionality including stable version
retrieval, prerelease version listing, and the VersionChecker's
fetch_github_version logic using mock GithubClient objects.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib.support.update import (
    VersionChecker,
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


@pytest.mark.unit
class TestGitHubStableVersionEndpoint:
    """Test GitHub stable version retrieval via Rust GithubClient."""

    @pytest.mark.asyncio
    async def test_get_stable_version_success(self):
        """Test successful retrieval of stable version."""
        mock_release = _make_mock_release(name="CLASSIC v7.30.1", tag_name="v7.30.1")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result is not None
        assert str(result) == "7.30.1"

    @pytest.mark.asyncio
    async def test_get_stable_version_prerelease_returned(self):
        """Test when endpoint returns a prerelease instead of stable."""
        mock_release = _make_mock_release(name="CLASSIC v7.31.0-beta", tag_name="v7.31.0-beta", prerelease=True)
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_network_error(self):
        """Test handling of network errors."""
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(side_effect=RuntimeError("GitHub API error: connection failed"))

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_api_error(self):
        """Test handling of HTTP/API errors."""
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(side_effect=RuntimeError("GitHub API error: 500 Internal Server Error"))

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_unparseable_name(self):
        """Test handling of unparseable version name."""
        mock_release = _make_mock_release(name="Invalid Version Name", tag_name="invalid")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_fallback_to_tag(self):
        """Test fallback to tag_name when name is unparseable."""
        mock_release = _make_mock_release(name="Missing Name", tag_name="v7.30.1")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result == Version("7.30.1")

    @pytest.mark.asyncio
    async def test_get_stable_version_multi_word_release_name(self):
        """Test parsing version from multi-word release name."""
        mock_release = _make_mock_release(name="CLASSIC Fallout4 v7.30.1", tag_name="v7.30.1")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result == Version("7.30.1")


@pytest.mark.unit
class TestGitHubPrereleaseVersionList:
    """Test GitHub prerelease version list via Rust GithubClient."""

    @pytest.mark.asyncio
    async def test_get_prerelease_version_success(self):
        """Test successful retrieval of prerelease version."""
        releases = [
            _make_mock_release(name="CLASSIC v7.30.1", tag_name="v7.30.1"),
            _make_mock_release(name="CLASSIC v7.31.0-beta", tag_name="v7.31.0-beta", prerelease=True),
            _make_mock_release(name="CLASSIC v7.30.0", tag_name="v7.30.0"),
        ]
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=releases)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result is not None
        assert str(result) == "7.31.0b0"  # First prerelease found

    @pytest.mark.asyncio
    async def test_get_prerelease_no_prereleases_found(self):
        """Test when no prereleases are found."""
        releases = [
            _make_mock_release(name="CLASSIC v7.30.1", tag_name="v7.30.1"),
            _make_mock_release(name="CLASSIC v7.30.0", tag_name="v7.30.0"),
        ]
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=releases)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_network_error(self):
        """Test handling of network errors."""
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(side_effect=RuntimeError("GitHub API error: connection failed"))

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_empty_list(self):
        """Test handling of empty releases list."""
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=[])

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_unparseable_versions(self):
        """Test handling of unparseable prerelease versions."""
        releases = [
            _make_mock_release(name="Invalid Prerelease Name", tag_name="invalid", prerelease=True),
            _make_mock_release(name="Another Bad Name", tag_name="bad", prerelease=True),
        ]
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=releases)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("evildarkarchon", "CLASSIC-Fallout4")

        assert result is None


@pytest.mark.unit
class TestVersionCheckerFetchGithubVersion:
    """Test VersionChecker._fetch_github_version method directly."""

    @pytest.mark.asyncio
    async def test_fetch_stable_latest(self):
        """Test fetching when latest release is stable."""
        mock_release = _make_mock_release(name="CLASSIC v7.30.1", tag_name="v7.30.1")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        checker = VersionChecker(quiet=True, gui_request=False)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await checker._fetch_github_version()

        assert result == Version("7.30.1")
        # get_all_releases should NOT be called since latest was stable
        mock_client.get_all_releases.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_falls_back_to_all_releases(self):
        """Test fallback to all releases when latest is prerelease."""
        prerelease = _make_mock_release(name="CLASSIC v7.31.0-beta", tag_name="v7.31.0-beta", prerelease=True)
        stable_release = _make_mock_release(name="CLASSIC v7.30.1", tag_name="v7.30.1")
        all_releases = [prerelease, stable_release]

        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=prerelease)
        mock_client.get_all_releases = AsyncMock(return_value=all_releases)

        checker = VersionChecker(quiet=True, gui_request=False)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await checker._fetch_github_version()

        assert result == Version("7.30.1")
        mock_client.get_all_releases.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_returns_none_on_total_failure(self):
        """Test returns None when all API calls fail."""
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(side_effect=RuntimeError("API error"))
        mock_client.get_all_releases = AsyncMock(side_effect=RuntimeError("API error"))

        checker = VersionChecker(quiet=True, gui_request=False)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await checker._fetch_github_version()

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_no_stable_in_all_releases(self):
        """Test returns None when all releases are prereleases."""
        prerelease1 = _make_mock_release(name="CLASSIC v7.31.0-beta", tag_name="v7.31.0-beta", prerelease=True)
        prerelease2 = _make_mock_release(name="CLASSIC v7.31.0-alpha", tag_name="v7.31.0-alpha", prerelease=True)

        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=prerelease1)
        mock_client.get_all_releases = AsyncMock(return_value=[prerelease1, prerelease2])

        checker = VersionChecker(quiet=True, gui_request=False)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await checker._fetch_github_version()

        assert result is None
