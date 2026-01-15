"""
Tests for classic_update Rust bindings, ensuring parity and correct functionality.

This module tests the `GithubClient` class from `classic_update`,
verifying its async methods, error handling, and data structure correctness.

Note:
    These tests hit the real GitHub API and may be rate limited.
    The GithubClient automatically uses the GITHUB_TOKEN environment variable
    if set, increasing the rate limit from 60/hour to 5,000/hour.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    import classic_update

try:
    import classic_update

    RUST_UPDATE_AVAILABLE = True
except ImportError:
    RUST_UPDATE_AVAILABLE = False


# Module-level cache for GitHub API responses to reduce API calls
_github_cache: dict[str, object] = {}


def _is_rate_limit_error(error: Exception) -> bool:
    """Check if an exception is a rate limit error.

    Args:
        error: The exception to check.

    Returns:
        True if the error indicates a rate limit was exceeded.
    """
    error_msg = str(error).lower()
    return "rate limit" in error_msg or "403" in error_msg


@pytest.fixture(scope="module")
def github_client():
    """Create a shared GithubClient for the test module.

    This fixture creates a single client that will be reused across all
    tests in the module. The client automatically uses GITHUB_TOKEN if set.

    Returns:
        A GithubClient instance.
    """
    return classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def cached_latest_release(github_client):
    """Fetch and cache the latest release for the test module.

    This fixture makes a single API call and caches the result for all tests
    that need the latest release data.

    Args:
        github_client: The shared GithubClient fixture.

    Returns:
        The latest GithubRelease or None if the API call failed.
    """
    cache_key = "latest_release"
    if cache_key in _github_cache:
        return _github_cache[cache_key]

    try:
        release = await github_client.get_latest_release()
        _github_cache[cache_key] = release
        return release
    except (OSError, RuntimeError) as e:
        if _is_rate_limit_error(e):
            _github_cache[cache_key] = None
        return None


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def cached_all_releases(github_client):
    """Fetch and cache all releases for the test module.

    This fixture makes a single API call and caches the result for all tests
    that need the releases list.

    Args:
        github_client: The shared GithubClient fixture.

    Returns:
        A list of GithubRelease objects or None if the API call failed.
    """
    cache_key = "all_releases"
    if cache_key in _github_cache:
        return _github_cache[cache_key]

    try:
        releases = await github_client.get_all_releases(include_prereleases=True)
        _github_cache[cache_key] = releases
        return releases
    except (OSError, RuntimeError) as e:
        if _is_rate_limit_error(e):
            _github_cache[cache_key] = None
        return None


@pytest.mark.rust
@pytest.mark.skipif(not RUST_UPDATE_AVAILABLE, reason="Rust update module not available")
class TestGithubClient:
    """Tests for the classic_update.GithubClient class."""

    def test_init_and_properties(self):
        """Test initialization and property access."""
        client = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4")
        assert client.owner == "evildarkarchon"
        assert client.repo == "CLASSIC-Fallout4"
        assert client.repo_url() == "https://github.com/evildarkarchon/CLASSIC-Fallout4"

    def test_init_with_token(self):
        """Test initialization with explicit token."""
        client = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4", token="test_token")
        assert client.owner == "evildarkarchon"
        assert client.repo == "CLASSIC-Fallout4"

    def test_has_update(self):
        """Test version comparison logic."""
        client = classic_update.GithubClient("owner", "repo")

        # Newer version available
        assert client.has_update("v7.0.0", "v8.0.0") is True
        assert client.has_update("7.0.0", "8.0.0") is True

        # Same version
        assert client.has_update("v8.0.0", "v8.0.0") is False

        # Older version (should not prompt update)
        assert client.has_update("v9.0.0", "v8.0.0") is False

    @pytest.mark.asyncio(loop_scope="module")
    async def test_get_latest_release_structure(self, cached_latest_release):
        """Test structure of returned GithubRelease object.

        Uses cached release data to minimize API calls. The cache is populated
        once per test module.

        Args:
            cached_latest_release: The cached latest release fixture.
        """
        release = cached_latest_release

        if release is None:
            pytest.skip("GitHub API rate limit exceeded or network error")

        assert isinstance(release, classic_update.GithubRelease)
        assert isinstance(release.tag_name, str)
        assert isinstance(release.name, str)
        assert isinstance(release.body, str)
        assert isinstance(release.assets, list)

        if release.assets:
            asset = release.assets[0]
            assert isinstance(asset, classic_update.GithubAsset)
            assert isinstance(asset.name, str)
            assert isinstance(asset.size, int)
            assert isinstance(asset.browser_download_url, str)

    @pytest.mark.asyncio(loop_scope="module")
    async def test_get_all_releases(self, cached_all_releases):
        """Test retrieving all releases.

        Uses cached releases data to minimize API calls. The cache is populated
        once per test module.

        Args:
            cached_all_releases: The cached releases list fixture.
        """
        releases = cached_all_releases

        if releases is None:
            pytest.skip("GitHub API rate limit exceeded or network error")

        assert isinstance(releases, list)
        assert len(releases) > 0
        assert isinstance(releases[0], classic_update.GithubRelease)
