"""Module for interacting with the GitHub API for release version parsing and
retrieval.

This module provides functions to fetch and parse release versions from GitHub
repositories, including stable releases, prereleases, and detailed analysis of
latest and top release details. It leverages `aiohttp` for asynchronous HTTP
requests and `packaging.version` for version parsing.
"""

from typing import Any  # Added List and Dict for type hinting

import aiohttp
from bs4 import BeautifulSoup, Tag
from packaging.version import InvalidVersion, Version

from ClassicLib.Constants import NULL_VERSION, YAML

# Fixed circular import - import functions directly from modules
from ClassicLib.GlobalRegistry import get_game  # Import just the function we need
from ClassicLib.Logger import logger
from ClassicLib.MessageHandler import msg_error, msg_info, msg_success, msg_warning
from ClassicLib.YamlSettings import classic_settings, yaml_settings


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

    if isinstance(response_json, dict):
        if response_json.get("prerelease"):
            logger.warning(f"{url} returned a prerelease. Expected a stable release.")
            return None

        release_name = response_json.get("name")
        if release_name and isinstance(release_name, str):
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

    for release_data in releases_json:  # Iterates from newest to oldest
        if isinstance(release_data, dict) and release_data.get("prerelease") is True:
            prerelease_name = release_data.get("name")
            if prerelease_name and isinstance(prerelease_name, str):
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
            all_releases_json: list[dict[str, Any]] = await response.json()

            if not all_releases_json or not isinstance(all_releases_json, list):
                logger.warning(f"No releases found or unexpected format from {all_releases_url}")
            else:
                top_release_json: dict[str, Any] = all_releases_json[0]
                results["top_of_list_release"] = {
                    "id": top_release_json.get("id"),
                    "tag_name": top_release_json.get("tag_name"),
                    "name": top_release_json.get("name"),
                    "version": try_parse_version(top_release_json.get("name", "")),
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


async def get_nexus_version(session: aiohttp.ClientSession) -> Version | None:
    """Fetch the NexusMods version information for a specific Fallout 4 mod.

    Uses BeautifulSoup to parse the HTML content and extract the version metadata
    from specific meta tags in the page header.

    Args:
        session (aiohttp.ClientSession): An instance of aiohttp.ClientSession to send the HTTP
            request.

    Returns:
        Version | None: The parsed version of the mod if found and valid; otherwise, returns None.

    Raises:
        aiohttp.ClientError: May be raised during the HTTP request if an error in the connection
            or request occurs. However, the function catches this error internally and does not
            propagate it.

    """
    # Constants
    nexus_mod_url = "https://www.nexusmods.com/fallout4/mods/56255"
    version_property_name = "twitter:label1"
    version_property_value = "Version"
    version_data_property = "twitter:data1"

    try:
        async with session.get(nexus_mod_url) as response:
            if not response.ok:
                logger.warning(f"Failed to fetch Nexus mod page: HTTP {response.status}")
                return None

            html_content: str = await response.text()
            soup: BeautifulSoup = BeautifulSoup(html_content, "html.parser")

            # Find the meta tag that indicates version label
            version_label_tag = soup.find("meta", property=version_property_name, attrs={"content": version_property_value})

            if not version_label_tag:
                logger.debug("Version label meta tag not found")
                return None

            # Look for the next meta tag with version data
            version_data_tag = soup.find("meta", property=version_data_property)

            if not isinstance(version_data_tag, Tag) or not version_data_tag.get("content"):
                logger.debug("Version data meta tag not found, is not a Tag, or content is missing")
                return None

            version_str = version_data_tag.get("content")
            if isinstance(version_str, str):
                parsed_version: Version | None = try_parse_version(version_str)
            else:
                logger.debug("Version string from meta tag is not a string or is None.")
                parsed_version = NULL_VERSION

            if parsed_version:
                logger.debug(f"Successfully parsed Nexus version: {parsed_version}")
            else:
                logger.debug(f"Failed to parse version string: '{version_str}'")

            return parsed_version

    except aiohttp.ClientError as e:
        logger.error(f"Network error while fetching Nexus version: {e}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Unexpected error parsing Nexus version: {e}")

    return None


class VersionChecker:
    """Handle version checking for the CLASSIC application, including fetching the latest version
    information from various sources (e.g., GitHub, Nexus) and validating update requirements.

    This class is responsible for determining the currently installed version, comparing it
    against the latest available versions from configured sources, and reporting any mismatches.
    It also respects user settings from CLASSIC Settings.yaml, such as enabling or disabling update
    checks and specifying the preferred update source(s).

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

    def _check_update_enabled(self) -> bool:
        """Determine whether the update check feature is enabled by verifying specific
        settings and conditions.

        The method checks if the update check feature is enabled either by explicit
        GUI request or through corresponding classic settings. If disabled, it logs
        a notice message.

        Returns:
            bool: True if the update check feature is enabled, otherwise False.

        """
        if not (self.gui_request or classic_settings(bool, "Update Check")):
            self._log_if_not_quiet("\n❌ NOTICE: UPDATE CHECK IS DISABLED IN CLASSIC Settings.yaml \n\n" + "=" * 79)
            return False
        return True

    def _validate_update_source(self, update_source: str) -> bool:
        """Validate if the given update source is one of the allowed values.

        The function checks whether the provided `update_source` is valid by
        comparing it to the set of allowed values: "Both", "GitHub", or "Nexus".
        An invalid value will generate a notification if the system is not in
        quiet mode and return False.

        Args:
            update_source: The source of updates to validate. It must be one of:
                "Both", "GitHub", or "Nexus".

        Returns:
            bool: True if the `update_source` is valid, otherwise False.

        """
        if update_source not in {"Both", "GitHub", "Nexus"}:
            self._log_if_not_quiet("\n❌ NOTICE: INVALID VALUE FOR UPDATE SOURCE IN CLASSIC Settings.yaml \n\n" + "=" * 79)
            return False
        return True

    @staticmethod
    def _parse_local_version() -> Version | None:
        """Parse the local version from a YAML configuration file and returns it as a Version object.

        The method retrieves a version string from a given YAML configuration file. It ensures
        that the string is properly split and parsed into a valid `Version` object. If parsing
        fails or the version string is unavailable, it returns `None`.

        Returns:
            Version | None: The parsed version object if successful, otherwise `None`.

        """
        classic_local_str: str | None = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")  # type: ignore
        if not classic_local_str:
            return None

        parts: list[str] = classic_local_str.rsplit(maxsplit=1)
        if not parts:
            return None

        parsed_version_str = parts[-1]
        return try_parse_version(parsed_version_str) if parsed_version_str else None

    @staticmethod
    def _determine_update_sources(update_source: str) -> tuple[bool, bool]:
        """Determine the update sources based on the given update_source parameter and specific settings.

        This method evaluates whether updates should be sourced from GitHub, Nexus, or both, based
        on the input value and configuration stored in YAML settings.

        Args:
            update_source (str): Source of updates, which can be "Both", "GitHub", or "Nexus".

        Returns:
            tuple[bool, bool]: A tuple indicating whether to use GitHub and Nexus as update sources.

        """
        use_github = update_source in {"Both", "GitHub"}
        use_nexus = update_source in {"Both", "Nexus"} and not yaml_settings(bool, YAML.Main, "CLASSIC_Info.is_prerelease")
        return use_github, use_nexus

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

        candidate_versions = []
        for release_key in ["latest_endpoint_release", "top_of_list_release"]:
            release_info = github_details.get(release_key)
            if release_info and release_info.get("version") and not release_info.get("prerelease"):
                candidate_versions.append(release_info["version"])

        if candidate_versions:
            version = max(candidate_versions)
            logger.info(f"Determined latest stable GitHub version: {version}")
            return version
        return None

    @staticmethod
    async def _fetch_nexus_version(session: aiohttp.ClientSession) -> Version | None:
        """Fetch the Nexus version using the provided HTTP session.

        This asynchronous method communicates with the Nexus service to retrieve
        its current version. The version information is logged for debugging
        purposes. If unable to determine the version, it returns None.

        Args:
            session (aiohttp.ClientSession): The HTTP client session used to fetch
                the Nexus version.

        Returns:
            Version | None: The Nexus version if successfully determined;
                otherwise, None.

        """
        logger.debug("Fetching Nexus version")
        version = await get_nexus_version(session)
        if version:
            logger.info(f"Determined Nexus version: {version}")
        return version

    @staticmethod
    def _check_source_failures(use_github: bool, use_nexus: bool, github_version: Version | None, nexus_version: Version | None) -> None:
        """Check for failures in fetching version information from specified sources.

        This method evaluates failure conditions for fetching version information
        from GitHub and Nexus, based on the settings provided by the user. It raises
        an error with a descriptive message if such failures occur. The evaluation is
        performed according to the selected source(s) and their availability.

        Args:
            use_github (bool): Whether to use GitHub as a version information source.
            use_nexus (bool): Whether to use Nexus as a version information source.
            github_version (Version | None): The version information fetched from GitHub,
                or None if unavailable.
            nexus_version (Version | None): The version information fetched from Nexus,
                or None if unavailable.

        Raises:
            UpdateCheckError: If the version information could not be retrieved from
            the selected source(s) in one of the specified failure scenarios.

        """
        github_failed = use_github and github_version is None
        nexus_failed = use_nexus and nexus_version is None

        error_conditions = [
            (use_github and not use_nexus and github_failed, "Unable to fetch version information from GitHub (selected as only source)."),
            (use_nexus and not use_github and nexus_failed, "Unable to fetch version information from Nexus (selected as only source)."),
            (
                use_github and use_nexus and github_failed and nexus_failed,
                "Unable to fetch version information from both GitHub and Nexus.",
            ),
        ]

        for condition, message in error_conditions:
            if condition:
                raise UpdateCheckError(message)

    def _handle_error(self, error: Exception) -> bool:
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
            unable_msg = yaml_settings(str, YAML.Main, f"CLASSIC_Interface.update_unable_{get_game()}")  # type: ignore
            if unable_msg:
                msg_error(unable_msg)

        if self.gui_request:
            raise UpdateCheckError(error_msg) from error
        return False

    @staticmethod
    def _check_if_outdated(version_local: Version | None, github_version: Version | None, nexus_version: Version | None) -> bool:
        """Check if the local version is outdated compared to the remote sources: GitHub or Nexus.

        This method determines whether the provided local version is older than the versions
        available on GitHub or Nexus. If the local version is unknown or outdated compared
        to any of the remote versions, it signals that an update might be necessary.

        Args:
            version_local (Version | None): The local version of the software.
            github_version (Version | None): The version of the software retrieved from GitHub.
            nexus_version (Version | None): The version of the software retrieved from Nexus.

        Returns:
            bool: True if the local version is outdated or unknown compared to the provided
            remote versions. False otherwise.

        """
        if version_local is None:
            logger.debug("Local version is unknown")
            msg_warning("Local version is unknown. Assuming update is needed or there's an issue.")
            return bool(github_version or nexus_version)

        remote_versions = [(github_version, "GitHub"), (nexus_version, "Nexus")]

        for remote_version, source in remote_versions:
            if remote_version and version_local < remote_version:
                logger.info(f"Local version {version_local} is older than {source} version {remote_version}.")
                return True

        return False

    @staticmethod
    def _format_success_message(
        version_local: Version | None, use_github: bool, github_version: Version | None, use_nexus: bool, nexus_version: Version | None
    ) -> str:
        """Format a success message string indicating the current local version of CLASSIC and
        information about the latest versions available from various sources (GitHub or Nexus),
        if applicable. This message is intended to provide a clear status on the version
        synchronization and comparison.

        Args:
            version_local (Version | None): The current version of CLASSIC installed locally.
                If not found, it is set to `None`.
            use_github (bool): Specifies whether to check for the latest version from GitHub.
            github_version (Version | None): The latest version retrieved from GitHub. None
                if it could not be fetched or if GitHub source is not used.
            use_nexus (bool): Specifies whether to check for the latest version from Nexus.
            nexus_version (Version | None): The latest version retrieved from Nexus. None if
                it could not be fetched or if Nexus source is not used.

        Returns:
            str: A formatted message string summarizing the local version and, if applicable,
            the latest versions from GitHub and Nexus.

        """
        message_parts = [f"Your CLASSIC Version: {version_local or 'Unknown'}"]

        source_info = [(use_github, github_version, "GitHub"), (use_nexus, nexus_version, "Nexus")]

        for should_check, version, source in source_info:
            if should_check:
                if version:
                    message_parts.append(f"Latest {source} Version: {version}")
                else:
                    message_parts.append(f"Latest {source} Version: Not found/checked")

        message_parts.append("\n✔️ You have the latest version of CLASSIC!")
        return "\n".join(message_parts)


async def is_latest_version(quiet: bool = False, gui_request: bool = True) -> bool:
    """Asynchronously checks if the currently installed version of CLASSIC Fallout 4 is the latest
    version, comparing it against the latest releases from GitHub and Nexus. The function supports
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
            version details from GitHub and Nexus, or when an update is available in response
            to a GUI request.

    """
    checker = VersionChecker(quiet, gui_request)

    logger.debug("- - - INITIATED UPDATE CHECK")

    # Early exit if update check is disabled
    if not checker._check_update_enabled():
        return False

    # Validate update source configuration
    update_source = classic_settings(str, "Update Source") or "Both"
    if not checker._validate_update_source(update_source):
        return False

    # Parse local version
    version_local = checker._parse_local_version()

    # Show checking message
    checker._log_if_not_quiet(
        "❓ (Needs internet connection) CHECKING FOR NEW CLASSIC VERSIONS...\n"
        "   (You can disable this check in the EXE or CLASSIC Settings.yaml) \n"
    )

    # Determine which sources to check
    use_github, use_nexus = checker._determine_update_sources(update_source)

    # Fetch remote versions
    version_github = None
    version_nexus = None

    try:
        async with aiohttp.ClientSession() as session:
            if use_github:
                version_github = await checker._fetch_github_version(session)
            if use_nexus:
                version_nexus = await checker._fetch_nexus_version(session)

            checker._check_source_failures(use_github, use_nexus, version_github, version_nexus)

    except (aiohttp.ClientError, UpdateCheckError) as e:
        return checker._handle_error(e)
    except Exception as e:  # noqa: BLE001
        # Catch unexpected exceptions for proper error handling and graceful degradation
        logger.error(f"Unexpected error during version fetch: {e}", exc_info=True)
        return checker._handle_error(e)

    # Check if outdated
    is_outdated = checker._check_if_outdated(version_local, version_github, version_nexus)

    if is_outdated:
        # Show update warning
        if not quiet:
            warning_msg = str(yaml_settings(str, YAML.Main, f"CLASSIC_Interface.update_warning_{get_game()}"))  # type: ignore
            msg_warning(warning_msg)

        if gui_request:
            raise UpdateCheckError("A new version is available.")
        return False

    # Show success message
    if not quiet:
        success_msg = checker._format_success_message(version_local, use_github, version_github, use_nexus, version_nexus)
        msg_success(success_msg)

    return True


class UpdateCheckError(Exception):
    """Checking for updates failed."""
