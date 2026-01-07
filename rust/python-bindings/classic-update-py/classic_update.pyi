"""Type stubs for classic_update.

Python bindings for classic-update-core, providing Rust-accelerated update checking
with GitHub API integration and Nexus Mods web scraping.

Architecture:
    - classic-update-core: Business logic (GitHub API, Nexus scraping, version comparison)
    - classic-update-py: Python bindings (this module - PyO3 adapters)

Features:
    - GitHub API integration for release monitoring (5-10x faster)
    - Nexus Mods web scraping for mod updates (3-5x faster)
    - Version comparison and change detection (20x faster)
    - Async I/O for concurrent checks

Usage:
    import classic_update
    import asyncio

    async def check_updates():
        # Check GitHub
        github = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4")
        latest = await github.get_latest_release()
        if github.has_update("v8.0.0", latest.tag_name):
            print(f"Update to {latest.tag_name} available!")
            for asset in latest.assets:
                print(f"  - {asset.name} ({asset.size} bytes)")

        # Check Nexus
        nexus = classic_update.NexusClient()
        info = await nexus.get_mod_info("fallout4", 1234)
        print(f"Mod: {info.name} v{info.version}")

    asyncio.run(check_updates())
"""

from __future__ import annotations

__version__: str

class GithubAsset:
    """GitHub release asset information.

    Represents a downloadable file attached to a GitHub release.

    Attributes:
        name: Asset name.
        size: Asset size in bytes.
        browser_download_url: Download URL.
        content_type: MIME type.
        download_count: Number of downloads.

    """

    name: str
    size: int
    browser_download_url: str
    content_type: str
    download_count: int

class GithubRelease:
    """GitHub release information.

    Contains all relevant information about a GitHub release.

    Attributes:
        tag_name: Release tag name (e.g., "v8.0.0").
        name: Release name/title.
        body: Release notes in Markdown format.
        prerelease: Whether this is a pre-release.
        draft: Whether this is a draft release.
        html_url: URL to the release page.
        assets: List of downloadable files.
        created_at: Release creation timestamp.
        published_at: Release publication timestamp (optional).

    Example:
        >>> client = GithubClient("evildarkarchon", "CLASSIC-Fallout4")
        >>> release = await client.get_latest_release()
        >>> print(f"Version: {release.tag_name}")
        >>> print(f"Notes: {release.body}")

    """

    tag_name: str
    name: str
    body: str
    prerelease: bool
    draft: bool
    html_url: str
    assets: list[GithubAsset]
    created_at: str
    published_at: str | None

class GithubClient:
    """GitHub API client for release monitoring.

    Provides access to GitHub API for checking releases and updates.
    5-10x faster than Python requests with native async.

    Authentication:
        Automatically loads environment variables from a `.env` file
        (if present in the current directory) and uses the `GITHUB_TOKEN` variable.
        This increases the rate limit from 60 requests/hour (unauthenticated)
        to 5,000 requests/hour (authenticated).

        Create a `.env` file with::

            GITHUB_TOKEN=ghp_your_token_here

    Example:
        >>> import asyncio
        >>> async def check_updates():
        ...     # Uses GITHUB_TOKEN from .env file or environment
        ...     client = GithubClient("evildarkarchon", "CLASSIC-Fallout4")
        ...     # Or provide a token explicitly
        ...     client = GithubClient("evildarkarchon", "CLASSIC-Fallout4", token="ghp_xxx")
        ...     latest = await client.get_latest_release()
        ...     print(f"Latest version: {latest.tag_name}")
        ...     if client.has_update("v8.0.0", latest.tag_name):
        ...         print("Update available!")
        >>> asyncio.run(check_updates())

    """

    def __init__(self, owner: str, repo: str, token: str | None = None) -> None:
        """Create a new GitHub client.

        Automatically loads environment variables from a `.env` file if present,
        then uses the `GITHUB_TOKEN` environment variable if set.

        Args:
            owner: Repository owner (username or organization).
            repo: Repository name.
            token: Optional GitHub personal access token. If not provided,
                   uses the GITHUB_TOKEN from `.env` file or environment.

        Example:
            >>> # Uses GITHUB_TOKEN from .env file or environment
            >>> client = GithubClient("evildarkarchon", "CLASSIC-Fallout4")
            >>> # Or provide a token explicitly
            >>> client = GithubClient("evildarkarchon", "CLASSIC-Fallout4", token="ghp_xxx")

        """

    @property
    def owner(self) -> str:
        """Get the repository owner."""

    @property
    def repo(self) -> str:
        """Get the repository name."""

    async def get_latest_release(self) -> GithubRelease:
        """Get the latest release from GitHub.

        Returns:
            GithubRelease containing release information.

        Raises:
            IOError: If the API request fails.

        Example:
            >>> latest = await client.get_latest_release()
            >>> print(latest.tag_name)

        """

    async def get_all_releases(self, include_prereleases: bool = False, include_drafts: bool = False) -> list[GithubRelease]:
        """Get all releases from GitHub.

        Args:
            include_prereleases: Whether to include pre-releases (default: False).
            include_drafts: Whether to include draft releases (default: False).

        Returns:
            List of GithubRelease objects.

        Raises:
            IOError: If the API request fails.

        Example:
            >>> releases = await client.get_all_releases()
            >>> for release in releases:
            ...     print(f"{release.tag_name}: {release.name}")

        """

    def has_update(self, current_version: str, latest_version: str) -> bool:
        """Check if an update is available.

        Compares two version strings to determine if an update is available.

        Args:
            current_version: Current version string.
            latest_version: Latest version string from release.

        Returns:
            True if latest_version is newer than current_version.

        Example:
            >>> if client.has_update("v8.0.0", "v8.1.0"):
            ...     print("Update available!")

        """

    def repo_url(self) -> str:
        """Construct the full repository URL.

        Returns:
            The full GitHub repository URL.

        Example:
            >>> print(client.repo_url())
            https://github.com/evildarkarchon/CLASSIC-Fallout4

        """

class NexusModInfo:
    """Nexus Mods mod information.

    Contains basic information about a mod on Nexus Mods.

    Attributes:
        name: Mod name.
        version: Current version string.
        description: Mod description (truncated).
        author: Author username.
        endorsements: Number of endorsements (optional).
        downloads: Number of downloads (optional).
        last_updated: Last update date string.
        url: Mod page URL.

    Example:
        >>> client = NexusClient()
        >>> info = await client.get_mod_info("fallout4", 1234)
        >>> print(f"{info.name} by {info.author}")
        >>> print(f"Version: {info.version}")

    """

    name: str
    version: str
    description: str
    author: str
    endorsements: int | None
    downloads: int | None
    last_updated: str
    url: str

class NexusClient:
    """Nexus Mods client for mod information.

    Provides access to Nexus Mods via web scraping (3-5x faster than Python).

    Warning:
        Web scraping is fragile and may break if Nexus changes their site structure.
        Use with caution and implement proper error handling.

    Example:
        >>> import asyncio
        >>> async def check_mods():
        ...     client = NexusClient()
        ...     info = await client.get_mod_info("fallout4", 1234)
        ...     print(f"Mod: {info.name}")
        ...     print(f"Version: {info.version}")
        ...     if await client.has_update("fallout4", 1234, "1.0"):
        ...         print("Mod has been updated!")
        >>> asyncio.run(check_mods())

    """

    def __init__(self) -> None:
        """Create a new Nexus Mods client.

        Example:
            >>> client = NexusClient()

        """

    async def get_mod_info(self, game: str, mod_id: int) -> NexusModInfo:
        """Get mod information from Nexus Mods.

        Args:
            game: Game identifier (e.g., "fallout4", "skyrimspecialedition").
            mod_id: Nexus Mods mod ID.

        Returns:
            NexusModInfo containing mod details.

        Raises:
            IOError: If scraping fails or mod not found.

        Example:
            >>> info = await client.get_mod_info("fallout4", 1234)
            >>> print(f"Mod: {info.name}")

        """

    async def has_update(self, game: str, mod_id: int, current_version: str) -> bool:
        """Check if a mod has been updated.

        Args:
            game: Game identifier.
            mod_id: Nexus Mods mod ID.
            current_version: Current version string.

        Returns:
            True if the mod version on Nexus is newer.

        Raises:
            IOError: If scraping fails or mod not found.

        Example:
            >>> if await client.has_update("fallout4", 1234, "1.0"):
            ...     print("Mod has been updated!")

        """
