"""
Unit tests for Update module.

This module tests version parsing, GitHub API interactions (via Rust GithubClient),
and error handling for update checking functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from packaging.version import Version

from ClassicLib.support.update import (
    get_github_latest_prerelease_version,
    get_github_latest_stable_version,
    try_parse_version,
)


def _make_mock_release(*, name: str, tag_name: str, prerelease: bool = False) -> MagicMock:
    """Create a mock GithubRelease object."""
    release = MagicMock()
    release.name = name
    release.tag_name = tag_name
    release.prerelease = prerelease
    return release


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
    """Unit tests for get_github_latest_stable_version function."""

    @pytest.mark.asyncio
    async def test_get_stable_version_success(self):
        """Test successful retrieval of stable version."""
        mock_release = _make_mock_release(name="CLASSIC v2.1.0", tag_name="v2.1.0")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("owner", "repo")

        assert result == Version("2.1.0")

    @pytest.mark.asyncio
    async def test_get_stable_version_prerelease(self):
        """Test handling when latest release is a prerelease."""
        mock_release = _make_mock_release(name="CLASSIC v3.0.0-beta", tag_name="v3.0.0-beta", prerelease=True)
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with (
            patch("ClassicLib.support.update.GithubClient", return_value=mock_client),
            patch("ClassicLib.support.update.logger") as mock_logger,
        ):
            result = await get_github_latest_stable_version("owner", "repo")

        assert result is None
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stable_version_runtime_error(self):
        """Test handling RuntimeError from Rust GithubClient."""
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(side_effect=RuntimeError("GitHub API error: not found"))

        with (
            patch("ClassicLib.support.update.GithubClient", return_value=mock_client),
            patch("ClassicLib.support.update.logger") as mock_logger,
        ):
            result = await get_github_latest_stable_version("owner", "repo")

        assert result is None
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stable_version_unparseable_name(self):
        """Test handling release with unparseable version name."""
        mock_release = _make_mock_release(name="Invalid Version Name", tag_name="invalid-tag")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("owner", "repo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_version_falls_back_to_tag_name(self):
        """Test that version parsing falls back to tag_name when name is unparseable."""
        mock_release = _make_mock_release(name="Some Release", tag_name="v2.1.0")
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(return_value=mock_release)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_stable_version("owner", "repo")

        assert result == Version("2.1.0")


class TestGetGithubLatestPrerelease:
    """Unit tests for get_github_latest_prerelease_version function."""

    @pytest.mark.asyncio
    async def test_get_prerelease_success(self):
        """Test successful retrieval of latest prerelease version."""
        releases = [
            _make_mock_release(name="CLASSIC v3.0.0-beta.2", tag_name="v3.0.0-beta.2", prerelease=True),
            _make_mock_release(name="CLASSIC v3.0.0-beta.1", tag_name="v3.0.0-beta.1", prerelease=True),
            _make_mock_release(name="CLASSIC v2.1.0", tag_name="v2.1.0"),
        ]
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=releases)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("owner", "repo")

        # Should return the first (most recent) prerelease
        assert result == Version("3.0.0b2")

    @pytest.mark.asyncio
    async def test_get_prerelease_no_prereleases(self):
        """Test handling when no prereleases are found."""
        releases = [
            _make_mock_release(name="CLASSIC v2.1.0", tag_name="v2.1.0"),
            _make_mock_release(name="CLASSIC v2.0.0", tag_name="v2.0.0"),
        ]
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=releases)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("owner", "repo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_empty_list(self):
        """Test handling empty releases list."""
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=[])

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("owner", "repo")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_prerelease_runtime_error(self):
        """Test handling RuntimeError from Rust GithubClient."""
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(side_effect=RuntimeError("GitHub API error: rate limited"))

        with (
            patch("ClassicLib.support.update.GithubClient", return_value=mock_client),
            patch("ClassicLib.support.update.logger") as mock_logger,
        ):
            result = await get_github_latest_prerelease_version("owner", "repo")

        assert result is None
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_prerelease_unparseable_version(self):
        """Test handling prerelease with unparseable version."""
        releases = [
            _make_mock_release(name="Invalid Prerelease Name", tag_name="invalid-tag", prerelease=True),
        ]
        mock_client = MagicMock()
        mock_client.get_all_releases = AsyncMock(return_value=releases)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client):
            result = await get_github_latest_prerelease_version("owner", "repo")

        assert result is None


class TestUpdateIntegrationScenarios:
    """Integration scenarios testing multiple components together."""

    @pytest.mark.asyncio
    async def test_version_comparison_workflow(self):
        """Test complete workflow of checking and comparing versions."""
        stable_release = _make_mock_release(name="CLASSIC v2.1.0", tag_name="v2.1.0")
        prerelease_list = [
            _make_mock_release(name="CLASSIC v2.2.0-beta.1", tag_name="v2.2.0-beta.1", prerelease=True),
            _make_mock_release(name="CLASSIC v2.1.0", tag_name="v2.1.0"),
        ]

        mock_client_stable = MagicMock()
        mock_client_stable.get_latest_release = AsyncMock(return_value=stable_release)

        mock_client_prerelease = MagicMock()
        mock_client_prerelease.get_all_releases = AsyncMock(return_value=prerelease_list)

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client_stable):
            stable_version = await get_github_latest_stable_version("owner", "repo")

        with patch("ClassicLib.support.update.GithubClient", return_value=mock_client_prerelease):
            prerelease_version = await get_github_latest_prerelease_version("owner", "repo")

        # Verify versions
        assert stable_version == Version("2.1.0")
        assert prerelease_version == Version("2.2.0b1")

        # Test version comparison
        assert stable_version is not None and prerelease_version is not None
        assert prerelease_version > stable_version
        assert stable_version < prerelease_version

    def test_edge_case_version_parsing(self):
        """Test edge cases in version parsing that might occur in real releases."""
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
        """Test handling of network timeouts (RuntimeError from Rust)."""
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(side_effect=RuntimeError("GitHub API error: request timeout"))

        with (
            patch("ClassicLib.support.update.GithubClient", return_value=mock_client),
            patch("ClassicLib.support.update.logger") as mock_logger,
        ):
            result = await get_github_latest_stable_version("owner", "repo")

        assert result is None
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limiting_response(self):
        """Test handling of GitHub API rate limiting (RuntimeError from Rust)."""
        mock_client = MagicMock()
        mock_client.get_latest_release = AsyncMock(side_effect=RuntimeError("GitHub API error: rate limit exceeded"))

        with (
            patch("ClassicLib.support.update.GithubClient", return_value=mock_client),
            patch("ClassicLib.support.update.logger") as mock_logger,
        ):
            result = await get_github_latest_stable_version("owner", "repo")

        assert result is None
        mock_logger.error.assert_called_once()
