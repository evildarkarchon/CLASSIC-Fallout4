"""Type stubs for classic_update.

Python bindings for classic-update-core, providing Rust-accelerated update checking
with GitHub API integration.

Architecture:
    - classic-update-core: Business logic (GitHub API, version comparison)
    - classic-update-py: Python bindings (this module - PyO3 adapters)

Features:
    - GitHub API integration for release monitoring (5-10x faster)
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

    asyncio.run(check_updates())
"""

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

    async def get_all_releases(
        self, include_prereleases: bool = False, include_drafts: bool = False
    ) -> list[GithubRelease]:
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

# ----------------------------------------------------------------------------
# YAML update delivery (yaml-update-delivery change)
# ----------------------------------------------------------------------------

class YamlClientSchemaEntry:
    """One per-file schema entry fed into `check_yaml_update` / `apply_yaml_update`.

    Callers build one entry per shippable file (e.g. ``CLASSIC Main.yaml``)
    carrying (a) the accepted MAJOR.MINOR range the client binary is built
    to parse, and optionally (b) the currently-installed MAJOR.MINOR on
    disk. When ``has_installed`` is ``False``, the orchestrator treats every
    compatible manifest entry as "newer".

    Attributes:
        name: Canonical file name (e.g. ``"CLASSIC Main.yaml"``).
        accepted_major: MAJOR the client is built to parse.
        accepted_minimum_minor: Minimum MINOR the client still supports
            at ``accepted_major``.
        has_installed: Whether ``installed_major`` / ``installed_minor``
            are meaningful.
        installed_major: Currently-installed MAJOR (ignored when
            ``has_installed`` is False).
        installed_minor: Currently-installed MINOR (ignored when
            ``has_installed`` is False).
    """

    name: str
    accepted_major: int
    accepted_minimum_minor: int
    has_installed: bool
    installed_major: int
    installed_minor: int

    def __init__(
        self,
        name: str,
        accepted_major: int,
        accepted_minimum_minor: int,
        has_installed: bool = False,
        installed_major: int = 0,
        installed_minor: int = 0,
    ) -> None: ...

class YamlUpdateFile:
    """One file entry inside `YamlUpdateStatus` or `YamlUpdateReport`.

    Attributes:
        name: Canonical file name.
        schema_version: ``"MAJOR.MINOR"`` string from the manifest.
        sha256: Hex-encoded SHA-256 of the file bytes.
        size_bytes: Size in bytes.
        download_url: Absolute HTTPS URL of the release asset.
    """

    name: str
    schema_version: str
    sha256: str
    size_bytes: int
    download_url: str

class YamlRejectedFile:
    """One rejection inside `YamlUpdateStatus.incompatible_files`."""

    file: YamlUpdateFile
    reason: str

class YamlUpdateStatus:
    """Discriminated status DTO returned by `check_yaml_update`.

    Inspect ``tag`` first. Value is one of:

    - ``"disabled"`` — ``Update Check: false``; nothing fetched.
    - ``"updateAvailable"`` — ``compatible_files`` + ``incompatible_files``
      populated.
    - ``"upToDate"`` — ``release_tag`` + ``published_at`` populated.
    - ``"unknown"`` — ``unknown_reason`` populated.
    """

    tag: str
    release_tag: str
    published_at: str
    compatible_files: list[YamlUpdateFile]
    incompatible_files: list[YamlRejectedFile]
    unknown_reason: str

class YamlUpdateFileOutcome:
    """Per-file install outcome inside `YamlUpdateReport`.

    When ``installed`` is ``True``, ``schema_version`` + ``created_prev``
    are populated. When ``installed`` is ``False``, ``failure_reason`` is
    populated.
    """

    name: str
    installed: bool
    schema_version: str
    created_prev: bool
    failure_reason: str

class YamlUpdateReport:
    """Aggregate result of `apply_yaml_update`."""

    installed: list[YamlUpdateFileOutcome]
    failed: list[YamlUpdateFileOutcome]

class YamlRollbackOutcome:
    """Result of `rollback_yaml_update`.

    ``rolled_back == False`` with no exception means the file has no
    ``.prev`` sibling (steady state after a fresh install, NOT an error).
    """

    rolled_back: bool
    file_name: str

def check_yaml_update(
    pages_url: str,
    tag_prefix: str,
    entries: list[YamlClientSchemaEntry],
    enabled: bool,
    bundled_yaml_dir: str | None = None,
) -> YamlUpdateStatus:
    """Check for a YAML data update.

    Drives the Pages-first manifest fetch with anonymous API fallback,
    then classifies the manifest against ``entries``. When ``enabled`` is
    ``False``, short-circuits with ``YamlUpdateStatus(tag="disabled")``
    without any HTTP call.

    Args:
        pages_url: Absolute HTTPS URL of the Pages manifest (normally
            ``https://<owner>.github.io/<repo>/yaml-data/manifest-latest.json``).
        tag_prefix: Release-tag prefix for the anonymous API fallback
            (e.g. ``"yaml-data-v"``).
        entries: Per-file accepted-range + currently-installed schema.
        enabled: When ``False``, short-circuit with ``tag="disabled"``.
        bundled_yaml_dir: Install-tree directory containing the bundled
            shippable YAML files (``CLASSIC Data/databases``). **Python
            callers should always pass this.** The core fallback probes
            ``current_exe()``, which points at ``python.exe`` for this
            host — so without an explicit path the orchestrator cannot
            resolve the bundled copy on a clean install and every
            compatible manifest entry is misclassified as
            ``updateAvailable``. Pass the package-local path (e.g. the
            parent of ``__file__`` joined with
            ``"CLASSIC Data/databases"``).

    Raises:
        RuntimeError: on network failure the fallback cannot recover from.
    """

def apply_yaml_update(
    pages_url: str,
    tag_prefix: str,
    entries: list[YamlClientSchemaEntry],
    enabled: bool,
    approved_release_tag: str,
    approved_file_names: list[str],
    bundled_yaml_dir: str | None = None,
) -> YamlUpdateReport:
    """Fetch + download + atomically install the reviewed set of files.

    This is the reviewed-decision form of apply. It takes three extra
    arguments beyond the check inputs:

    - ``enabled`` mirrors the ``Update Check`` settings toggle. Pass
      ``False`` to refuse the apply without issuing any HTTP — the user's
      opt-out survives between check and apply.
    - ``approved_release_tag`` is the ``release_tag`` field of the
      ``YamlUpdateStatus`` the user reviewed.
    - ``approved_file_names`` is the ``name`` of each entry in that
      status's ``compatible_files``.

    When the live manifest has rotated to a different tag since the user's
    review, the call raises ``RuntimeError`` (``"approved release ... does
    not match current manifest release ...; re-check required"``) instead
    of silently installing the newer release.

    Args:
        pages_url: Absolute HTTPS URL of the Pages manifest.
        tag_prefix: Release-tag prefix for the anonymous API fallback.
        entries: Per-file schema entries.
        enabled: Honors ``Update Check: false`` end-to-end.
        approved_release_tag: Release tag the user reviewed.
        approved_file_names: File names the user reviewed.
        bundled_yaml_dir: Install-tree directory containing the bundled
            shippable YAML files. Same semantics as on
            :func:`check_yaml_update` — Python callers should pass the
            package-local path so the pre-install classification step can
            find the bundled copy even when the host exe is ``python.exe``.

    Raises:
        RuntimeError: when the whole batch fails (manifest fetch, cache
            dir), when the update check is disabled, or when the approved
            decision is stale.
    """

def rollback_yaml_update(file_name: str) -> YamlRollbackOutcome:
    """Swap the cached YAML file with its ``.prev`` sibling (if any).

    Returns ``YamlRollbackOutcome(rolled_back=False)`` with no exception
    when the file has no ``.prev`` (steady state after a fresh install).

    Args:
        file_name: Canonical file name (e.g. ``"CLASSIC Main.yaml"``).
    """
