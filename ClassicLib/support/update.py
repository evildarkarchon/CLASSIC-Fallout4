"""Module for interacting with the GitHub API for release version parsing and
retrieval.

This module provides functions to fetch and parse release versions from GitHub
repositories, including stable releases, prereleases, and detailed analysis of
latest and top release details. It leverages `aiohttp` for asynchronous HTTP
requests and `packaging.version` for version parsing.
"""

from typing import Any  # Added List and Dict for type hinting

import aiohttp
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


async def get_github_latest_stable_version_from_endpoint(session: aiohttp.ClientSession, owner: str, repo: str) -> Version | None:
    """Fetch the latest stable release version of a GitHub repository using the GitHub API.

    This function sends an asynchronous GET request to the GitHub API to fetch data about
    the latest release of a specified repository. It checks for the release type, ensuring
    it is stable and not a prerelease. If a stable release is found, the release name is
    parsed into a version object. If the release is a prerelease or cannot be fetched, the
    function returns None.

    Args:
        session (aiohttp.ClientSession): The aiohttp session object used for making HTTP requests.
        owner (str): The name of the repository owner or organization.
        repo (str): The name of the GitHub repository.

    Returns:
        Version | None: The version object representing the latest stable release,
        or None if no stable release is found or an error occurs.

    """
    url: str = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        async with session.get(url) as response:
            if response.status == 404:
                logger.info(f"No '/releases/latest' found for {owner}/{repo} (status 404).")
                return None
            response.raise_for_status()
            response_json: Any = await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error fetching latest stable release from {url}: {e}")
        return None

    if not isinstance(response_json, dict):
        logger.warning(f"Expected a dict from {url}, got {type(response_json)}")
        return None

    if response_json.get("prerelease"):
        logger.warning(f"{url} returned a prerelease. Expected a stable release.")
        return None

    release_name: str | None = response_json.get("name")  # pyright: ignore[reportUnknownVariableType]
    if isinstance(release_name, str):
        return try_parse_version(release_name)
    return None


async def get_github_latest_prerelease_version_from_list(session: aiohttp.ClientSession, owner: str, repo: str) -> Version | None:
    """Fetch the latest prerelease version from a GitHub repository's releases list.

    This function retrieves the list of releases from the GitHub API for a specified
    repository and identifies the most recent release marked as a prerelease.
    It attempts to parse the prerelease name into a `Version` object and returns it.
    If no valid prerelease is found, it returns `None`.

    Args:
        session: An instance of `aiohttp.ClientSession` used to make the HTTP request.
        owner: Repository owner's username or organization name.
        repo: Repository name.

    Returns:
        The parsed `Version` object of the latest prerelease, or `None` if no valid
        prerelease is found or an error occurs.

    """
    url: str = f"https://api.github.com/repos/{owner}/{repo}/releases"
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            releases_json: Any = await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error fetching releases list from {url}: {e}")
        return None

    if not isinstance(releases_json, list):
        logger.warning(f"Expected a list of releases from {url}, got {type(releases_json)}")
        return None

    for release_data in releases_json:  # Iterates from newest to oldest  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(release_data, dict):
            continue
        if release_data.get("prerelease") is True:
            prerelease_name: str | None = release_data.get("name")  # pyright: ignore[reportUnknownVariableType]
            if isinstance(prerelease_name, str):
                parsed_version: Version | None = try_parse_version(prerelease_name)
                if parsed_version:
                    return parsed_version
    return None


async def get_latest_and_top_release_details(session: aiohttp.ClientSession, owner: str, repo: str) -> dict[str, Any] | None:
    """Fetch details of the latest release and the top release from the repository's
    releases list on the GitHub API, compares their IDs, and returns a
    structured dictionary with release data.

    This function interacts with two GitHub API endpoints:
    1. `/releases/latest`: To fetch the repository's latest release from the
       "latest" endpoint.
    2. `/releases`: To fetch the first release from the repository's list
       of releases.

    The function attempts to retrieve relevant release information and determine
    if the releases fetched from both endpoints represent the same release by
    comparing their IDs.

    Args:
        session: An instance of `aiohttp.ClientSession` to perform the HTTP
            requests.
        owner: The owner of the GitHub repository. Typically the username or
            organization name as a string.
        repo: The name of the GitHub repository as a string.

    Returns:
        A dictionary containing:
        - "latest_endpoint_release": A nested dictionary with details of the
          "latest" release (from `/releases/latest`) or `None` if not available.
        - "top_of_list_release": A nested dictionary with details of the top
          release from `/releases` or `None` if not available.
        - "are_same_release_by_id": A boolean indicating whether the IDs of
          "latest_endpoint_release" and "top_of_list_release" are identical.
        Returns `None` if no valid release data is fetched.

    """
    latest_url: str = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    all_releases_url: str = f"https://api.github.com/repos/{owner}/{repo}/releases"

    results: dict[str, Any] = {
        "latest_endpoint_release": None,
        "top_of_list_release": None,
        "are_same_release_by_id": False,
    }

    try:
        # 1. Get release from /releases/latest
        async with session.get(latest_url) as response:
            if response.status == 404:
                logger.info(f"No '/releases/latest' found for {owner}/{repo} (status 404).")
            else:
                response.raise_for_status()
                latest_json: dict[str, Any] = await response.json()
                results["latest_endpoint_release"] = {
                    "id": latest_json.get("id"),
                    "tag_name": latest_json.get("tag_name"),
                    "name": latest_json.get("name"),
                    "version": try_parse_version(latest_json.get("name", "")),
                    "prerelease": latest_json.get("prerelease"),
                    "published_at": latest_json.get("published_at"),
                }

        # 2. Get all releases and take the top one
        async with session.get(all_releases_url) as response:
            response.raise_for_status()
            all_releases_json: Any = await response.json()

            if not isinstance(all_releases_json, list) or not all_releases_json:
                logger.warning(f"No releases found or unexpected format from {all_releases_url}")
            else:
                top_release_json = all_releases_json[0]  # pyright: ignore[reportUnknownVariableType]
                if isinstance(top_release_json, dict):
                    results["top_of_list_release"] = {
                        "id": top_release_json.get("id"),
                        "tag_name": top_release_json.get("tag_name"),
                        "name": top_release_json.get("name"),
                        "version": try_parse_version(top_release_json.get("name", "")),  # pyright: ignore[reportUnknownArgumentType]
                        "prerelease": top_release_json.get("prerelease"),
                        "published_at": top_release_json.get("published_at"),
                    }

        if results["latest_endpoint_release"] and results["top_of_list_release"]:
            results["are_same_release_by_id"] = results["latest_endpoint_release"]["id"] == results["top_of_list_release"]["id"]
        return results  # noqa: TRY300

    except aiohttp.ClientError as e:
        logger.error(f"GitHub API ClientError for {owner}/{repo}: {e}")
        return results if results["latest_endpoint_release"] or results["top_of_list_release"] else None
    except Exception as e:  # noqa: BLE001
        logger.error(f"Unexpected error fetching release details for {owner}/{repo}: {e}")
        return None


class VersionChecker:
    """Handle version checking for the CLASSIC application by fetching the latest
    version from GitHub and comparing it to the installed version.

    This class is responsible for determining the currently installed version,
    comparing it against the latest available version from GitHub, and reporting
    any updates available.

    Attributes:
        quiet (bool): Determines whether logging should be suppressed.
        gui_request (bool): Specifies if the request was triggered by the GUI.
        repo_owner (str): The owner of the GitHub repository to fetch updates from.
        repo_name (str): The name of the GitHub repository to fetch updates from.

    """

    def __init__(self, quiet: bool, gui_request: bool) -> None:
        """Initialize the class with the given parameters.

        Args:
            quiet: A boolean indicating whether the operation should run in quiet
                mode without verbose output.
            gui_request: A boolean indicating whether the initialization is
                triggered by a GUI request.

        """
        self.quiet = quiet
        self.gui_request = gui_request
        self.repo_owner = "evildarkarchon"
        self.repo_name = "CLASSIC-Fallout4"

    def _log_if_not_quiet(self, message: str, log_func: Any = msg_info) -> None:
        """Log a message using the provided logging function if the `quiet` attribute is not set to True.

        Args:
            message (str): The message to be logged.
            log_func (Callable): A function to handle logging the message. Defaults to `msg_info`.

        """
        if not self.quiet:
            log_func(message)

    async def _check_update_enabled(self) -> bool:
        """Determine whether the update check feature is enabled by verifying specific
        settings and conditions.

        The method checks if the update check feature is enabled either by explicit
        GUI request or through corresponding classic settings. If disabled, it logs
        a notice message.

        Returns:
            bool: True if the update check feature is enabled, otherwise False.

        """
        if not (self.gui_request or await classic_settings_async(bool, "Update Check")):
            self._log_if_not_quiet("\n❌ NOTICE: UPDATE CHECK IS DISABLED IN CLASSIC Settings.yaml \n\n" + "=" * 79)
            return False
        return True

    @staticmethod
    async def _parse_local_version() -> Version | None:
        """Parse the local version from a YAML configuration file and returns it as a Version object.

        The method retrieves a version string from a given YAML configuration file. It ensures
        that the string is properly split and parsed into a valid `Version` object. If parsing
        fails or the version string is unavailable, it returns `None`.

        Returns:
            Version | None: The parsed version object if successful, otherwise `None`.

        """
        classic_local_str: str | None = await yaml_settings_async(str, YAML.Main, "CLASSIC_Info.version")  # type: ignore[arg-type]  # yaml_settings_async handles type conversion
        if not classic_local_str:
            return None

        parts: list[str] = classic_local_str.rsplit(maxsplit=1)
        if not parts:
            return None

        parsed_version_str = parts[-1]
        return try_parse_version(parsed_version_str) if parsed_version_str else None

    async def _fetch_github_version(self, session: aiohttp.ClientSession) -> Version | None:
        """Fetch the latest stable GitHub version of the repository.

        This asynchronous method contacts the GitHub API to retrieve the latest release
        and top of the list release details for the specified repository, evaluates them,
        and determines the latest non-prerelease version. If no valid version is found,
        None is returned.

        Args:
            session (aiohttp.ClientSession): The aiohttp session used to interact with
                the GitHub API.

        Returns:
            Version | None: The latest stable release version if available, or None if
            no valid version is determined.

        """
        logger.debug(f"Fetching GitHub release details for {self.repo_owner}/{self.repo_name}")
        github_details = await get_latest_and_top_release_details(session, self.repo_owner, self.repo_name)

        if not github_details:
            return None

        candidate_versions: list[Version] = []
        for release_key in ["latest_endpoint_release", "top_of_list_release"]:
            release_info = github_details.get(release_key)
            if release_info and release_info.get("version") and not release_info.get("prerelease"):
                candidate_versions.append(release_info["version"])

        if candidate_versions:
            version: Version | None = max(candidate_versions)  # pyright: ignore[reportUnknownArgumentType]
            logger.info(f"Determined latest stable GitHub version: {version}")
            return version
        return None

    async def _handle_error(self, error: Exception) -> bool:
        """Handle an error encountered during the update check process.

        This method identifies the type of error that occurred during the update check,
        logs appropriate messages, and displays a user-facing message if applicable.
        It also raises the error if necessary, provided certain conditions are met.

        Args:
            error (Exception): The exception that was encountered during the update
                check process.

        Returns:
            bool: Always returns `False` to indicate the update check process failed.

        Raises:
            UpdateCheckError: If `gui_request` is set and the error is not suppressed,
                this exception is raised with the error message.

        """
        error_msg = str(error)

        if isinstance(error, (aiohttp.ClientError, UpdateCheckError)):
            logger.debug(f"Update check failed during version fetching: {error_msg}")
        else:
            logger.error(f"Unexpected error during update check: {error_msg}", exc_info=True)
            error_msg = f"An unexpected error occurred: {error_msg}"

        self._log_if_not_quiet(f"Update check failed: {error_msg}", msg_error)

        # Get and display unable message if available
        if not self.quiet and isinstance(error, (aiohttp.ClientError, UpdateCheckError)):
            unable_msg = await yaml_settings_async(str, YAML.Main, f"CLASSIC_Interface.update_unable_{get_game()}")  # type: ignore[arg-type]  # yaml_settings_async handles type conversion
            if unable_msg:
                msg_error(unable_msg)

        if self.gui_request:
            raise UpdateCheckError(error_msg) from error
        return False

    @staticmethod
    def _check_if_outdated(version_local: Version | None, github_version: Version | None) -> bool:
        """Check if the local version is outdated compared to the GitHub version.

        This method determines whether the provided local version is older than the version
        available on GitHub. If the local version is unknown or outdated compared
        to the GitHub version, it signals that an update might be necessary.

        Args:
            version_local (Version | None): The local version of the software.
            github_version (Version | None): The version of the software retrieved from GitHub.

        Returns:
            bool: True if the local version is outdated or unknown compared to the GitHub
            version. False otherwise.

        """
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
        """Format a success message string indicating the current local version of CLASSIC and
        information about the latest version available from GitHub.

        Args:
            version_local (Version | None): The current version of CLASSIC installed locally.
                If not found, it is set to `None`.
            github_version (Version | None): The latest version retrieved from GitHub. None
                if it could not be fetched.

        Returns:
            str: A formatted message string summarizing the local version and the latest
            version from GitHub.

        """
        message_parts = [f"Your CLASSIC Version: {version_local or 'Unknown'}"]

        if github_version:
            message_parts.append(f"Latest GitHub Version: {github_version}")
        else:
            message_parts.append("Latest GitHub Version: Not found/checked")

        message_parts.append("\n✔️ You have the latest version of CLASSIC!")
        return "\n".join(message_parts)

    async def check(self) -> bool:
        """Check if the currently installed version of CLASSIC is the latest version.

        Compares the installed version against the latest release from GitHub.
        The function supports GUI-based requests and logs the update-check results in detail.

        Returns:
            bool: True if the installed version is the latest; otherwise, False. For GUI-based
                requests, this can raise an error instead of returning.

        Raises:
            UpdateCheckError: Raised under different circumstances, such as errors in fetching
                version details from GitHub, or when an update is available in response
                to a GUI request.

        """
        logger.debug("- - - INITIATED UPDATE CHECK")

        # Early exit if update check is disabled
        if not await self._check_update_enabled():
            return False

        # Parse local version
        version_local = await self._parse_local_version()

        # Show checking message
        self._log_if_not_quiet(
            "❓ (Needs internet connection) CHECKING FOR NEW CLASSIC VERSIONS...\n"
            "   (You can disable this check in the EXE or CLASSIC Settings.yaml) \n"
        )

        # Fetch GitHub version
        version_github = None

        def _validate_version(version: Version | None) -> Version:
            """Validate that version was fetched successfully."""
            if version is None:
                raise UpdateCheckError("Unable to fetch version information from GitHub.")
            return version

        try:
            async with aiohttp.ClientSession() as session:
                version_github = _validate_version(await self._fetch_github_version(session))

        except (aiohttp.ClientError, UpdateCheckError) as e:
            return await self._handle_error(e)
        except Exception as e:  # noqa: BLE001
            # Catch unexpected exceptions for proper error handling and graceful degradation
            logger.error(f"Unexpected error during version fetch: {e}", exc_info=True)
            return await self._handle_error(e)

        # Check if outdated
        is_outdated = self._check_if_outdated(version_local, version_github)

        if is_outdated:
            # Show update warning
            if not self.quiet:
                warning_msg = str(await yaml_settings_async(str, YAML.Main, f"CLASSIC_Interface.update_warning_{get_game()}"))  # type: ignore[arg-type]  # yaml_settings_async handles type conversion
                msg_warning(warning_msg)

            if self.gui_request:
                raise UpdateCheckError("A new version is available.")
            return False

        # Show success message
        if not self.quiet:
            success_msg = self._format_success_message(version_local, version_github)
            msg_success(success_msg)

        return True


async def is_latest_version(quiet: bool = False, gui_request: bool = True) -> bool:
    """Asynchronously checks if the currently installed version of CLASSIC Fallout 4 is the latest
    version by comparing it against the latest release from GitHub. The function supports
    GUI-based requests and logs the update-check results in detail.

    Args:
        quiet: Determines whether to suppress detailed output to the console/logs. If False,
            informational messages related to the update check process will be printed.
        gui_request: Indicates if the request originates from the GUI. If True, a detected
            update or failure would raise an error to notify the GUI.

    Returns:
        bool: True if the installed version is the latest; otherwise, False. For GUI-based
            requests, this can raise an error instead of returning.

    Raises:
        UpdateCheckError: Raised under different circumstances, such as errors in fetching
            version details from GitHub, or when an update is available in response
            to a GUI request.

    """
    checker = VersionChecker(quiet, gui_request)
    return await checker.check()


class UpdateCheckError(Exception):
    """Checking for updates failed."""
