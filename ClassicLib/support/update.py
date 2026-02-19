"""Module for checking CLASSIC version updates via the GitHub API.

This module uses the Rust GithubClient binding (classic_update) for all GitHub
API interactions, replacing the previous aiohttp-based implementation. Local
version parsing still uses packaging.version.
"""

from typing import Any

from classic_update import GithubClient, GithubRelease
from packaging.version import InvalidVersion, Version

from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import get_game
from ClassicLib.io.yaml import classic_settings_async, yaml_settings_async
from ClassicLib.messaging import msg_error, msg_info, msg_success, msg_warning


def try_parse_version(version_str: str | None) -> Version | None:
    """Attempt to parse a version string into a `Version` object. This function is
    designed to handle common formats of version strings, such as those commonly
    encountered in release names. If the parsing fails, the function returns None.

    Args:
        version_str: The version string to be parsed. This could represent a
            version number directly or be a part of a larger name. Can be None.

    Returns:
        Version: A `Version` object representing the parsed version, if parsing
            was successful.
        None: Returns None if the input is None, empty, or parsing was not successful.

    """
    if not version_str:
        return None

    # Extracts the last part after a space, common for "Name v1.2.3"
    potential_version_part: str = version_str.rsplit(maxsplit=1)[-1]

    try:
        # Remove a leading 'v' if present, as packaging.version handles it
        if potential_version_part.startswith("v") and len(potential_version_part) > 1:
            return Version(potential_version_part[1:])
        return Version(potential_version_part)
    except InvalidVersion:
        # Fallback: if the above fails, try the original string if it was simple
        # (e.g. name field was just "1.2.3")
        if version_str == potential_version_part:
            return None
        try:
            if version_str.startswith("v") and len(version_str) > 1:
                return Version(version_str[1:])
            return Version(version_str)
        except InvalidVersion:
            logger.debug(f"Could not parse version from GitHub release name: {version_str}")
            return None


def _parse_release_version(release: GithubRelease) -> Version | None:
    """Parse a Version from a GithubRelease's name, falling back to tag_name."""
    version = try_parse_version(release.name)
    if version is None:
        version = try_parse_version(release.tag_name)
    return version


async def get_github_latest_stable_version(owner: str, repo: str) -> Version | None:
    """Fetch the latest stable release version using the Rust GithubClient.

    Args:
        owner: The name of the repository owner or organization.
        repo: The name of the GitHub repository.

    Returns:
        The version of the latest stable release, or None if unavailable.

    """
    client = GithubClient(owner, repo)
    try:
        release: GithubRelease = await client.get_latest_release()
    except RuntimeError as e:
        logger.error(f"Error fetching latest stable release for {owner}/{repo}: {e}")
        return None

    if release.prerelease:
        logger.warning(f"Latest release for {owner}/{repo} is a prerelease. Expected stable.")
        return None

    return _parse_release_version(release)


async def get_github_latest_prerelease_version(owner: str, repo: str) -> Version | None:
    """Fetch the latest prerelease version using the Rust GithubClient.

    Args:
        owner: Repository owner's username or organization name.
        repo: Repository name.

    Returns:
        The parsed Version of the latest prerelease, or None if not found.

    """
    client = GithubClient(owner, repo)
    try:
        releases: list[GithubRelease] = await client.get_all_releases(include_prereleases=True)
    except RuntimeError as e:
        logger.error(f"Error fetching releases list for {owner}/{repo}: {e}")
        return None

    for release in releases:
        if release.prerelease:
            parsed = _parse_release_version(release)
            if parsed is not None:
                return parsed
    return None


class VersionChecker:
    """Handle version checking for the CLASSIC application by fetching the latest
    version from GitHub and comparing it to the installed version.

    Attributes:
        quiet (bool): Determines whether logging should be suppressed.
        gui_request (bool): Specifies if the request was triggered by the GUI.
        repo_owner (str): The owner of the GitHub repository to fetch updates from.
        repo_name (str): The name of the GitHub repository to fetch updates from.

    """

    def __init__(self, quiet: bool, gui_request: bool) -> None:
        self.quiet = quiet
        self.gui_request = gui_request
        self.repo_owner = "evildarkarchon"
        self.repo_name = "CLASSIC-Fallout4"

    def _log_if_not_quiet(self, message: str, log_func: Any = msg_info) -> None:
        if not self.quiet:
            log_func(message)

    async def _check_update_enabled(self) -> bool:
        if not (self.gui_request or await classic_settings_async(bool, "Update Check")):
            self._log_if_not_quiet("\n❌ NOTICE: UPDATE CHECK IS DISABLED IN CLASSIC Settings.yaml \n\n" + "=" * 79)
            return False
        return True

    @staticmethod
    def _main_yaml_path_for_error() -> str:
        """Return a best-effort path to CLASSIC Main.yaml for diagnostics."""
        try:
            from ClassicLib.support.resources import ResourceLoader

            return str(ResourceLoader.get_data_directory() / "databases" / "CLASSIC Main.yaml")
        except (ImportError, OSError, ValueError, TypeError):
            return "CLASSIC Data/databases/CLASSIC Main.yaml"

    @staticmethod
    async def _parse_local_version() -> Version:
        classic_local_str: str | None = await yaml_settings_async(str, YAML.Main, "CLASSIC_Info.version")  # type: ignore[arg-type]  # yaml_settings_async handles type conversion
        if not classic_local_str:
            main_yaml_path = VersionChecker._main_yaml_path_for_error()
            raise UpdateCheckError(
                "Fatal configuration error: missing 'CLASSIC_Info.version' in "
                f"'{main_yaml_path}'. CLASSIC Main.yaml is the single source of truth for the app version."
            )

        parts: list[str] = classic_local_str.rsplit(maxsplit=1)
        if not parts:
            main_yaml_path = VersionChecker._main_yaml_path_for_error()
            raise UpdateCheckError(
                "Fatal configuration error: malformed 'CLASSIC_Info.version' in "
                f"'{main_yaml_path}'. Expected a value like 'CLASSIC v9.0.0'."
            )

        parsed_version_str = parts[-1]
        parsed_version = try_parse_version(parsed_version_str) if parsed_version_str else None
        if parsed_version is None:
            main_yaml_path = VersionChecker._main_yaml_path_for_error()
            raise UpdateCheckError(
                f"Fatal configuration error: unable to parse 'CLASSIC_Info.version' from '{main_yaml_path}'. Found '{classic_local_str}'."
            )

        return parsed_version

    async def _fetch_github_version(self) -> Version | None:
        """Fetch the latest stable GitHub version using Rust GithubClient.

        Returns:
            The latest stable release version, or None if not found.

        """
        logger.debug(f"Fetching GitHub release details for {self.repo_owner}/{self.repo_name}")
        client = GithubClient(self.repo_owner, self.repo_name)

        try:
            latest: GithubRelease = await client.get_latest_release()
        except RuntimeError as e:
            logger.error(f"Error fetching latest release for {self.repo_owner}/{self.repo_name}: {e}")
            return None

        if not latest.prerelease:
            version = _parse_release_version(latest)
            if version is not None:
                logger.info(f"Determined latest stable GitHub version: {version}")
                return version

        # Latest release endpoint returned a prerelease; check all releases for a stable one
        try:
            all_releases: list[GithubRelease] = await client.get_all_releases()
        except RuntimeError as e:
            logger.error(f"Error fetching all releases for {self.repo_owner}/{self.repo_name}: {e}")
            return None

        for release in all_releases:
            if not release.prerelease:
                version = _parse_release_version(release)
                if version is not None:
                    logger.info(f"Determined latest stable GitHub version: {version}")
                    return version

        return None

    async def _handle_error(self, error: Exception) -> bool:
        error_msg = str(error)

        if isinstance(error, UpdateCheckError):
            logger.debug(f"Update check failed during version fetching: {error_msg}")
        else:
            logger.error(f"Unexpected error during update check: {error_msg}", exc_info=True)
            error_msg = f"An unexpected error occurred: {error_msg}"

        self._log_if_not_quiet(f"Update check failed: {error_msg}", msg_error)

        if not self.quiet and isinstance(error, (RuntimeError, UpdateCheckError)):
            unable_msg = await yaml_settings_async(str, YAML.Main, f"CLASSIC_Interface.update_unable_{get_game()}")  # type: ignore[arg-type]  # yaml_settings_async handles type conversion
            if unable_msg:
                msg_error(unable_msg)

        if self.gui_request:
            raise UpdateCheckError(error_msg) from error
        return False

    @staticmethod
    def _check_if_outdated(version_local: Version | None, github_version: Version | None) -> bool:
        if version_local is None:
            logger.debug("Local version is unknown")
            msg_warning("Local version is unknown. Assuming update is needed or there's an issue.")
            return github_version is not None

        if github_version and version_local < github_version:
            logger.info(f"Local version {version_local} is older than GitHub version {github_version}.")
            return True

        return False

    @staticmethod
    def _format_success_message(version_local: Version | None, github_version: Version | None) -> str:
        message_parts = [f"Your CLASSIC Version: {version_local or 'Unknown'}"]

        if github_version:
            message_parts.append(f"Latest GitHub Version: {github_version}")
        else:
            message_parts.append("Latest GitHub Version: Not found/checked")

        message_parts.append("\n✔️ You have the latest version of CLASSIC!")
        return "\n".join(message_parts)

    async def check(self) -> bool:
        """Check if the currently installed version of CLASSIC is the latest version.

        Returns:
            bool: True if the installed version is the latest; otherwise, False.

        Raises:
            UpdateCheckError: When an update is available or fetch fails (GUI mode).

        """
        logger.debug("- - - INITIATED UPDATE CHECK")

        if not await self._check_update_enabled():
            return False

        version_local = await self._parse_local_version()

        self._log_if_not_quiet(
            "❓ (Needs internet connection) CHECKING FOR NEW CLASSIC VERSIONS...\n"
            "   (You can disable this check in the EXE or CLASSIC Settings.yaml) \n"
        )

        try:
            version_github = await self._fetch_github_version()
            if version_github is None:
                raise UpdateCheckError("Unable to fetch version information from GitHub.")  # noqa: TRY301

        except UpdateCheckError as e:
            return await self._handle_error(e)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Unexpected error during version fetch: {e}", exc_info=True)
            return await self._handle_error(e)

        is_outdated = self._check_if_outdated(version_local, version_github)

        if is_outdated:
            if not self.quiet:
                warning_msg = str(await yaml_settings_async(str, YAML.Main, f"CLASSIC_Interface.update_warning_{get_game()}"))  # type: ignore[arg-type]  # yaml_settings_async handles type conversion
                msg_warning(warning_msg)

            if self.gui_request:
                raise UpdateCheckError("A new version is available.")
            return False

        if not self.quiet:
            success_msg = self._format_success_message(version_local, version_github)
            msg_success(success_msg)

        return True


async def is_latest_version(quiet: bool = False, gui_request: bool = True) -> bool:
    """Check if the installed version of CLASSIC is the latest.

    Args:
        quiet: Suppress detailed output.
        gui_request: If True, raises UpdateCheckError on update/failure.

    Returns:
        True if the installed version is the latest; otherwise, False.

    Raises:
        UpdateCheckError: On update available or fetch failure (GUI mode).

    """
    checker = VersionChecker(quiet, gui_request)
    return await checker.check()


class UpdateCheckError(Exception):
    """Checking for updates failed."""
