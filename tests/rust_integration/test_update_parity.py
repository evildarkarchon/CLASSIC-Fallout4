"""
Tests for classic_update Rust bindings, ensuring parity and correct functionality.

This module tests the `GithubClient` and `NexusClient` classes from `classic_update`,
verifying their async methods, error handling, and data structure correctness.
"""

import pytest

try:
    import classic_update

    RUST_UPDATE_AVAILABLE = True
except ImportError:
    RUST_UPDATE_AVAILABLE = False


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

    @pytest.mark.asyncio
    async def test_get_latest_release_structure(self):
        """
        Test structure of returned GithubRelease object.

        Note: This test hits the real GitHub API. In a CI environment without
        internet access or rate limits, this might be flaky. For robust testing,
        we should ideally mock the Rust-side HTTP client or usage of it, but
        mocking PyO3 classes deeply is complex. We'll test the structure validity.
        """
        client = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4")

        try:
            release = await client.get_latest_release()

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

        except OSError as e:
            pytest.skip(f"Network error or API limit: {e}")

    @pytest.mark.asyncio
    async def test_get_all_releases(self):
        """Test retrieving all releases."""
        client = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4")

        try:
            releases = await client.get_all_releases(include_prereleases=True)
            assert isinstance(releases, list)
            assert len(releases) > 0
            assert isinstance(releases[0], classic_update.GithubRelease)
        except OSError as e:
            pytest.skip(f"Network error or API limit: {e}")


@pytest.mark.rust
@pytest.mark.skipif(not RUST_UPDATE_AVAILABLE, reason="Rust update module not available")
class TestNexusClient:
    """Tests for the classic_update.NexusClient class."""

    @pytest.mark.asyncio
    async def test_get_mod_info_structure(self):
        """
        Test structure of returned NexusModInfo object.

        Note: Hits real Nexus Mods website.
        """
        client = classic_update.NexusClient()

        # Using a known stable mod ID (e.g., Unofficial Fallout 4 Patch)
        # Game: fallout4, Mod ID: 4598
        try:
            info = await client.get_mod_info("fallout4", 4598)

            assert isinstance(info, classic_update.NexusModInfo)
            assert isinstance(info.name, str)
            assert "Unofficial Fallout 4 Patch" in info.name
            assert isinstance(info.version, str)
            assert isinstance(info.author, str)
            assert isinstance(info.url, str)

        except (OSError, RuntimeError) as e:
            pytest.skip(f"Network error or Nexus scraping failed: {e}")

    @pytest.mark.asyncio
    async def test_has_update(self):
        """Test mod update check."""
        client = classic_update.NexusClient()

        try:
            # Check with a very old version to ensure update is detected
            has_update = await client.has_update("fallout4", 4598, "1.0.0")
            assert has_update is True

            # Check with a likely future version (or current if we knew it dynamically)
            # Hard to guarantee 'False' without knowing current version, but can test type
            # If we pass a nonsense version string, behavior depends on parsing logic

        except (OSError, RuntimeError) as e:
            pytest.skip(f"Network error or Nexus scraping failed: {e}")
