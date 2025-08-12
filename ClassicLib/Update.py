from typing import Any  # Added List and Dict for type hinting

import aiohttp
from bs4 import BeautifulSoup, Tag
from packaging.version import InvalidVersion, Version

from ClassicLib import GlobalRegistry, msg_error, msg_info, msg_success, msg_warning
from ClassicLib.Constants import NULL_VERSION, YAML
from ClassicLib.Logger import logger
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


def try_parse_version(version_str: str) -> Version | None:
    """
    Attempts to parse a version string into a `Version` object. This function is
    designed to handle common formats of version strings, such as those commonly
    encountered in release names. If the parsing fails, the function returns None.

    Args:
        version_str: The version string to be parsed. This could represent a
            version number directly or be a part of a larger name.

    Returns:
        Version: A `Version` object representing the parsed version, if parsing
            was successful.
        None: Returns None if the parsing was not successful.
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
    """
    Fetches the latest stable release version of a GitHub repository using the GitHub API.

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
    """
    Fetches the latest prerelease version from a GitHub repository's releases list.

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
    """
    Fetches details of the latest release and the top release from the repository's
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
    """
    Fetches the NexusMods version information for a specific Fallout 4 mod.

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


async def is_latest_version(quiet: bool = False, gui_request: bool = True) -> bool:
    """
    Asynchronously checks if the currently installed version of CLASSIC Fallout 4 is the latest
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

    def _check_source_failures_and_raise(
        use_github_flag: bool, use_nexus_flag: bool, github_fetch_failed: bool, nexus_fetch_failed: bool
    ) -> None:
        """Helper to raise UpdateCheckError if source fetching failed based on configuration."""
        if use_github_flag and not use_nexus_flag and github_fetch_failed:
            raise UpdateCheckError("Unable to fetch version information from GitHub (selected as only source).")
        if use_nexus_flag and not use_github_flag and nexus_fetch_failed:
            raise UpdateCheckError("Unable to fetch version information from Nexus (selected as only source).")
        if use_github_flag and use_nexus_flag and github_fetch_failed and nexus_fetch_failed:
            raise UpdateCheckError("Unable to fetch version information from both GitHub and Nexus.")

    # Hardcoded repository for CLASSIC Fallout 4
    repo_owner = "evildarkarchon"
    repo_name = "CLASSIC-Fallout4"

    logger.debug("- - - INITIATED UPDATE CHECK")
    if not (gui_request or classic_settings(bool, "Update Check")):
        if not quiet:
            msg_info(
                "\n❌ NOTICE: UPDATE CHECK IS DISABLED IN CLASSIC Settings.yaml \n\n==============================================================================="
            )
        return False  # False because it's not the "latest" if checks are off (unless for GUI)

    update_source: str = classic_settings(str, "Update Source") or "Both"
    if update_source not in {"Both", "GitHub", "Nexus"}:
        if not quiet:
            msg_info(
                "\n❌ NOTICE: INVALID VALUE FOR UPDATE SOURCE IN CLASSIC Settings.yaml \n\n==============================================================================="
            )
        return False  # Invalid source, cannot determine if latest

    classic_local_str: str | None = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")  # type: ignore

    # Parse local version string (e.g., "CLASSIC v7.30.3" -> "7.30.3")
    parsed_local_version_str = None
    if classic_local_str:
        parts: list[str] = classic_local_str.rsplit(maxsplit=1)
        if parts:
            parsed_local_version_str = parts[-1]

    version_local: Version | None = try_parse_version(parsed_local_version_str) if parsed_local_version_str else None

    if not quiet:
        msg_info(
            "❓ (Needs internet connection) CHECKING FOR NEW CLASSIC VERSIONS...\n   (You can disable this check in the EXE or CLASSIC Settings.yaml) \n"
        )

    use_github: bool = update_source in {"Both", "GitHub"}
    use_nexus: bool = update_source in {"Both", "Nexus"} and not yaml_settings(bool, YAML.Main, "CLASSIC_Info.is_prerelease")

    version_github_to_compare: Version | None = None
    version_nexus_to_compare: Version | None = None

    try:
        # It's good practice to create the session once if making multiple requests
        async with aiohttp.ClientSession() as session:  # Removed raise_for_status from here, handled in funcs
            if use_github:
                logger.debug(f"Fetching GitHub release details for {repo_owner}/{repo_name}")
                github_details: dict[str, Any] | None = await get_latest_and_top_release_details(session, repo_owner, repo_name)
                if github_details:
                    latest_ep_info: Any | None = github_details.get("latest_endpoint_release")
                    top_list_info: Any | None = github_details.get("top_of_list_release")

                    candidate_stable_versions: list[Version] = []
                    if latest_ep_info and latest_ep_info.get("version") is not None and not latest_ep_info.get("prerelease"):
                        candidate_stable_versions.append(latest_ep_info["version"])

                    if top_list_info and top_list_info.get("version") is not None and not top_list_info.get("prerelease"):
                        candidate_stable_versions.append(top_list_info["version"])

                    if candidate_stable_versions:
                        version_github_to_compare = max(candidate_stable_versions)
                        logger.info(f"Determined latest stable GitHub version: {version_github_to_compare}")
            if use_nexus:
                logger.debug("Fetching Nexus version")
                version_nexus_to_compare = await get_nexus_version(session)
                if version_nexus_to_compare:
                    logger.info(f"Determined Nexus version: {version_nexus_to_compare}")

            nexus_source_failed: bool = use_nexus and (version_nexus_to_compare is None)
            github_source_failed: bool = use_github and (version_github_to_compare is None)

            _check_source_failures_and_raise(use_github, use_nexus, github_source_failed, nexus_source_failed)
            # If 'Both' were chosen and one succeeded, we can proceed.

    except (aiohttp.ClientError, UpdateCheckError) as err:  # Removed ValueError, OSError as ClientError covers network issues
        logger.debug(f"Update check failed during version fetching: {err}")
        if not quiet:
            msg_error(f"Update check failed: {err}")
            # Get the unable message from YAML
            unable_msg: str | None = yaml_settings(str, YAML.Main, f"CLASSIC_Interface.update_unable_{GlobalRegistry.get_game()}")  # type: ignore
            if unable_msg:
                msg_error(unable_msg)
        if gui_request:
            raise UpdateCheckError(str(err)) from err  # Pass the original error message
        return False
    except Exception as e:  # Catch any other unexpected error during setup or calls
        logger.error(f"Unexpected error during update check: {e}", exc_info=True)
        if not quiet:
            msg_error(f"An unexpected error occurred during update check: {e}")
        if gui_request:
            raise UpdateCheckError(f"An unexpected error occurred: {e}") from e
        return False

    is_outdated = False
    if version_local is None:
        logger.debug("Local version is unknown")
        msg_warning("Local version is unknown. Assuming update is needed or there's an issue.")
        # Depending on desired behavior, this could be True (outdated) or False (cannot determine)
        # For safety, if local version is unknown, and remote versions exist, consider it outdated.
        if version_github_to_compare or version_nexus_to_compare:
            is_outdated = True
    else:
        if version_github_to_compare and version_local < version_github_to_compare:
            logger.info(f"Local version {version_local} is older than GitHub version {version_github_to_compare}.")
            is_outdated = True

        if not is_outdated and version_nexus_to_compare and version_local < version_nexus_to_compare:
            logger.info(f"Local version {version_local} is older than Nexus version {version_nexus_to_compare}.")
            is_outdated = True

    if is_outdated:
        if not quiet:
            # Assuming yaml_settings returns a string for the message
            warning_msg: str = str(yaml_settings(str, YAML.Main, f"CLASSIC_Interface.update_warning_{GlobalRegistry.get_game()}"))  # type: ignore
            msg_warning(warning_msg)
        if gui_request:
            # GUI catches this to indicate an update is available.
            raise UpdateCheckError("A new version is available.")
        return False  # Outdated

    # If not outdated
    if not quiet:
        msg_success(
            f"Your CLASSIC Version: {version_local or 'Unknown'}"
            + (
                f"\nLatest GitHub Version: {version_github_to_compare}"
                if use_github and version_github_to_compare
                else ("\nLatest GitHub Version: Not found/checked" if use_github else "")
            )
            + (
                f"\nLatest Nexus Version: {version_nexus_to_compare}"
                if use_nexus and version_nexus_to_compare
                else ("\nLatest Nexus Version: Not found/checked" if use_nexus else "")
            )
            + "\n\n✔️ You have the latest version of CLASSIC!\n"
        )
    return True


class UpdateCheckError(Exception):
    """Checking for updates failed."""
