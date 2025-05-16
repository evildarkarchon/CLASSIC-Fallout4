import aiohttp
from packaging.version import InvalidVersion, Version

from ClassicLib import Constants, GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


def try_parse_version(version_string: str) -> Version | None:
    """
    Parses a version string into a Version object. If parsing fails due to an invalid
    version format, returns None.

    Args:
        version_string: A string representing the version to be parsed.

    Returns:
        A Version object if the string is successfully parsed, or None if the
        string is not a valid version format.
    """
    try:
        return Version(version_string)
    except InvalidVersion:
        return None


async def get_github_version(session: aiohttp.ClientSession) -> Version | None:
    """
    Fetches the latest release version of the CLASSIC-Fallout4 repository from
    GitHub using the provided aiohttp ClientSession.

    The function performs a GET request to the GitHub API to retrieve the latest
    release information of the specified repository. It extracts and parses the
    version number from the release name. If the request fails or the response
    does not contain a valid version, the function returns None.

    Args:
        session (aiohttp.ClientSession): An instance of aiohttp.ClientSession used
            for making asynchronous HTTP requests.

    Returns:
        Version | None: A Version object representing the parsed release version
            if successful, or None if the version cannot be determined or the
            request fails.
    """
    try:
        async with session.get(
                "https://api.github.com/repos/evildarkarchon/CLASSIC-Fallout4/releases/latest") as response:
            response_json = await response.json()
    except aiohttp.ClientError:
        return None

    # The JSON should have this field with the title of the latest release:
    # "name": "CLASSIC v7.30.3"
    if isinstance(response_json, dict):
        release_name = response_json.get("name")
        if release_name and isinstance(release_name, str):
            return try_parse_version(release_name.rsplit(maxsplit=1)[-1])
    return None


async def get_nexus_version(session: aiohttp.ClientSession) -> Version | None:
    """
    Fetches the NexusMods version information for a specific Fallout 4 mod.

    This function asynchronously requests the web page for a Fallout 4 mod on NexusMods
    to determine its current version. It looks for specific HTML meta tags to extract
    the version. The method is designed to handle potential changes in the HTML
    structure by looking for specific markers.

    Args:
        session (aiohttp.ClientSession): The active HTTP session used to fetch the
            NexusMods webpage.

    Returns:
        Version | None: The parsed version information as a `Version` object if found,
            or `None` if the version cannot be determined or if an error occurs during
            the request.

    Raises:
        aiohttp.ClientError: Raised if there is an issue with the HTTP request made
            using the session.

    """

    try:
        async with session.get("https://www.nexusmods.com/fallout4/mods/56255") as response:
            use_next = False
            async for line in response.content:
                # We're looking for these lines:
                #    <meta property="twitter:label1" content="Version" />
                #    <meta property="twitter:data1" content="7.30.3" />
                # We'll find the label and then use the next line.
                # If we hit the stylesheet tags we've gone too far.
                # The HTML likely changed and this needs updating.
                line_text = line.decode("utf-8")
                if line_text.startswith('<meta property="twitter:label1" content="Version"'):
                    use_next = True
                    continue
                if use_next:
                    # [ '<meta property="twitter:data1" content=',
                    #   '7.30.3',
                    #   ' />' ]
                    split = line_text.rsplit('"', 2)
                    if len(split) == 3:
                        return try_parse_version(split[1])
                    break
                if line_text.startswith('<link rel="stylesheet"'):
                    break
    except aiohttp.ClientError:
        pass
    return None


async def is_latest_version(quiet: bool = False, gui_request: bool = True) -> bool:
    """
    Checks whether the current local version of the software is the latest version
    available from GitHub and/or Nexus. This function communicates with remote
    servers, validates configuration options, and reports the results of the update
    check.

    Args:
        quiet (bool): If set to True, suppresses print statements providing feedback
            about the update check process.
        gui_request (bool): Indicates whether the function is triggered by a GUI-based
            request. If True and an update check fails, errors will propagate instead
            of being handled gracefully.

    Returns:
        bool: True if the local version is the latest or if the update check is
            disabled, otherwise False.

    Raises:
        UpdateCheckError: If the update check fails for any of the chosen data
            sources (GitHub/Nexus) or an issue with the configuration exists when
            triggered by a GUI request.
    """

    logger.debug("- - - INITIATED UPDATE CHECK")
    if not (gui_request or classic_settings(bool, "Update Check")):
        if not quiet:
            print(
                "\n❌ NOTICE: UPDATE CHECK IS DISABLED IN CLASSIC Settings.yaml \n",
                "\n===============================================================================",
                flush=True
            )
        return False

    update_source = classic_settings(str, "Update Source") or "Both"
    if update_source not in {"Both", "GitHub", "Nexus"}:
        if not quiet:
            print(
                "\n❌ NOTICE: INVALID VALUE FOR UPDATE SOURCE IN CLASSIC Settings.yaml \n",
                "\n===============================================================================",
                flush=True,
            )
        return False

    classic_local = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
    if not quiet:
        print(
            "❓ (Needs internet connection) CHECKING FOR NEW CLASSIC VERSIONS...",
            "\n   (You can disable this check in the EXE or CLASSIC Settings.yaml) \n",
            flush=True
        )

    use_github = update_source in {"Both", "GitHub"}
    use_nexus = update_source in {"Both", "Nexus"}
    no_data: set[None | Version] = {None, Constants.NULL_VERSION}
    try:
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            version_github = await get_github_version(session) if use_github else Constants.NULL_VERSION
            version_nexus = await get_nexus_version(session) if use_nexus else Constants.NULL_VERSION
        if version_github in no_data and version_nexus in no_data:
            # Unable to check any chosen sources
            raise UpdateCheckError  # noqa: TRY301

    except (ValueError, OSError, aiohttp.ClientError, UpdateCheckError) as err:
        if not quiet:
            print(err)
            print(yaml_settings(str, YAML.Main, f"CLASSIC_Interface.update_unable_{GlobalRegistry.get_game()}"))
        if gui_request:
            # GUI catches exceptions to detect update failures.
            raise UpdateCheckError from err
        return False

    # Split "CLASSIC" from the version for YAML and GitHub; "CLASSIC v7.30.3"
    version_local = try_parse_version(classic_local.rsplit(maxsplit=1)[-1]) if classic_local else Constants.NULL_VERSION

    if (
            version_local is None  # Local version unknown; updating may fix
            or (version_github is not None and version_local < version_github)
            or (version_nexus is not None and version_local < version_nexus)
    ):
        if not quiet:
            print(yaml_settings(str, YAML.Main, f"CLASSIC_Interface.update_warning_{GlobalRegistry.get_game()}"),
                  flush=True)
        if gui_request:
            raise UpdateCheckError
        return False

    if not quiet:
        print(
            f"Your CLASSIC Version: {version_local}",
            f"\nLatest GitHub Version: {version_github}" if use_github else "",
            f"\nLatest Nexus Version: {version_nexus}" if use_nexus else "",
            "\n\n✔️ You have the latest version of CLASSIC!\n",
            sep="",
            flush=True,
        )
    return True


class UpdateCheckError(Exception):
    """Checking for updates failed."""
