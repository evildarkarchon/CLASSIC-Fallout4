import configparser
import contextlib
import datetime
import hashlib
import logging
import os
import platform
import shutil
import stat
from collections.abc import Iterator
from enum import Enum, auto
from io import TextIOWrapper
from pathlib import Path
from typing import Literal, TypedDict, cast

import aiohttp
import chardet
from PySide6.QtCore import QObject, Signal
from packaging.version import InvalidVersion, Version

import ClassicLib.Constants as Constants
from ClassicLib.YamlSettingsCache import YamlSettingsCache

with contextlib.suppress(ImportError):
    import winreg

    import win32api  # type: ignore[import]

""" AUTHOR NOTES (POET): ❓ ❌ ✔️
    ❓ REMINDER: 'shadows x from outer scope' means the variable name repeats both in the func and outside all other func.
    ❓ Comments marked as RESERVED in all scripts are intended for future updates or tests, do not edit / move / remove.
    ❓ (..., encoding="utf-8", errors="ignore") needs to go with every opened file because of unicode & charmap errors.
    ❓ import shelve if you want to store persistent data that you do not want regular users to access or modify.
    ❓ Globals are generally used to standardize game paths and INI files naming conventions.
"""


def get_game_version(game_exe_path: Path) -> Version:
    """
    Gets the version information of a specified game executable file.

    This function retrieves the version of a game executable file by using system-level
    API calls to fetch version information. It is specifically supported for systems running
    on Windows. If the path provided does not exist, is invalid, or is not a Windows
    executable file, a default null version is returned. Any unexpected errors during
    processing are gracefully handled and logged.

    Args:
        game_exe_path (Path): The file path to the target game executable.

    Returns:
        Version: The version of the game executable in the format "major.minor.patch.build".
        If detection fails, a null version is returned.
    """

    if platform.system() != "Windows":
        logger.warning("Game version detection is only supported on Windows")
        return Constants.NULL_VERSION

    # Check if path exists and is a file
    if not game_exe_path or not game_exe_path.is_file():
        logger.warning("Game executable not found or path is invalid")
        return Constants.NULL_VERSION

    try:
        # Get file version info using win32api
        version_info = win32api.GetFileVersionInfo(str(game_exe_path), "\\")  # type: ignore[attr-defined]

        # Extract version components
        major = version_info["FileVersionMS"] >> 16
        minor = version_info["FileVersionMS"] & 0xFFFF
        patch = version_info["FileVersionLS"] >> 16
        build = version_info["FileVersionLS"] & 0xFFFF

        version = Version(f"{major}.{minor}.{patch}.{build}")
        logger.debug(f"Game version detected: {version}")

    except FileNotFoundError:
        logger.error(f"Game executable not found at: {game_exe_path}")
        return Constants.NULL_VERSION
    except (AttributeError, UnboundLocalError):
        logger.error("win32api module not properly loaded")
        return Constants.NULL_VERSION
    except (OSError, ValueError) as e:
        logger.error(f"Error retrieving version info: {e}")
        return Constants.NULL_VERSION
    except Exception as e:  # noqa: BLE001
        logger.error(f"Unexpected error getting game version: {e}")
        return Constants.NULL_VERSION
    else:
        return version


class YAML(Enum):
    Main = auto()
    """CLASSIC Data/databases/CLASSIC Main.yaml"""
    Settings = auto()
    """CLASSIC Settings.yaml"""
    Ignore = auto()
    """CLASSIC Ignore.yaml"""
    Game = auto()
    """CLASSIC Data/databases/CLASSIC Fallout4.yaml"""
    Game_Local = auto()
    """CLASSIC Data/CLASSIC Fallout4 Local.yaml"""
    TEST = auto()
    """tests/test_settings.yaml"""


class GameVars(TypedDict):
    game: Constants.GameID
    vr: Literal["VR", ""]


gamevars: GameVars = {
    "game": "Fallout4",
    "vr": "",
}


class UpdateCheckError(Exception):
    """Checking for updates failed."""


SETTINGS_IGNORE_NONE = {
    "SCAN Custom Path",
    "MODS Folder Path",
    "Root_Folder_Game",
    "Root_Folder_Docs",
}

logger = logging.getLogger()


# noinspection DuplicatedCode
class ManualDocsPath(QObject):
    manual_docs_path_signal = Signal()

    def __init__(self) -> None:
        super().__init__()

    def get_manual_docs_path_gui(self, path: str) -> None:
        """
        Validates the provided path to ensure it is a directory and updates settings accordingly. Emits a
        signal if the path is invalid.

        Args:
            path: The directory path input by the user. This is validated to ensure it is an existing
                directory.
        """
        if Path(path).is_dir():
            print(f"You entered: '{path}' | This path will be automatically added to CLASSIC Settings.yaml")
            manual_docs = Path(path.strip())
            yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs", str(manual_docs))
        else:
            print(f"'{path}' is not a valid or existing directory path. Please try again.")
            self.manual_docs_path_signal.emit()


# noinspection DuplicatedCode
class GamePathEntry(QObject):
    game_path_signal = Signal()

    def __init__(self) -> None:
        super().__init__()

    def get_game_path_gui(self, path: str) -> None:
        """
        Processes the provided directory path to configure the game settings via GUI.

        This function checks if the path entered by the user is a valid directory. If it
        is valid, it saves the path to the settings.yaml file for the CLASSIC application.
        Otherwise, it alerts the user about the invalid directory and emits a signal
        to re-prompt for the input.

        Args:
            path: The directory path entered by the user as a string. This should be the
                intended path for the game's root folder.
        """
        if Path(path).is_dir():
            print(f"You entered: '{path}' | This path will be automatically added to CLASSIC Settings.yaml")
            game_path = Path(path.strip())
            yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Game", str(game_path))
        else:
            print(f"'{path}' is not a valid or existing directory path. Please try again.")
            self.game_path_signal.emit()


@contextlib.contextmanager
def open_file_with_encoding(file_path: Path | str | os.PathLike) -> Iterator[TextIOWrapper]:
    """
    Opens a file with its detected encoding as a context manager.

    This function detects the encoding of the specified file and opens the file using
    that encoding. It allows working with files having unknown or varied encodings
    to ensure the correct reading of the content. The function ensures that the file
    is properly closed after processing, even if exceptions are raised during the
    execution of the code block that uses the context manager.

    Args:
        file_path: The path to the file to be opened. It can be provided as a Path,
            string, or os.PathLike object.

    Yields:
        TextIOWrapper: An open text file object for reading the file's content using
        the detected encoding.

    """
    if not isinstance(file_path, Path):
        file_path = Path(file_path)
    raw_data = file_path.read_bytes()
    encoding = chardet.detect(raw_data)["encoding"]

    file_handle = cast("Iterator[TextIOWrapper]", file_path.open(encoding=encoding, errors="ignore"))
    try:
        yield cast("TextIOWrapper", file_handle)
    finally:
        cast("TextIOWrapper", file_handle).close()


def configure_logging() -> None:
    """
    Configures the logging system for the application.

    This function checks the existence and age of a log file named "CLASSIC Journal.log".
    If the log file is older than 7 days, it deletes the file and generates a new one.
    The function also ensures that logging is configured only once for the logger named
    "CLASSIC". The logs are stored in "CLASSIC Journal.log" using a specific format that
    includes timestamp, log level, and the log message.

    Raises:
        ValueError: If an error occurs while deleting the log file.
        OSError: If there is an operating system-related error during log file deletion.
    """
    global logger  # noqa: PLW0603

    journal_path = Path("CLASSIC Journal.log")
    if journal_path.exists():
        logger.debug("- - - INITIATED LOGGING CHECK")
        log_time = datetime.datetime.fromtimestamp(journal_path.stat().st_mtime)
        current_time = datetime.datetime.now()
        log_age = current_time - log_time
        if log_age.days > 7:
            try:
                journal_path.unlink(missing_ok=True)
                print("CLASSIC Journal.log has been deleted and regenerated due to being older than 7 days.")
            except (ValueError, OSError) as err:
                print(f"An error occurred while deleting {journal_path.name}: {err}")

    # Make sure we only configure the handler once
    if "CLASSIC" not in logging.Logger.manager.loggerDict:
        logger = logging.getLogger("CLASSIC")
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename="CLASSIC Journal.log",
            mode="a",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(handler)


# ================================================
# DEFINE FILE / YAML FUNCTIONS
# ================================================
def remove_readonly(file_path: Path) -> None:
    """
    Removes the read-only attribute or permission from the specified file path.
    On Windows, it clears the read-only file attribute. On other operating
    systems, it adds the write permission for the user if not already set.

    In case the file does not exist or an error occurs during the operation,
    appropriate error messages are logged.

    Args:
        file_path (Path): The path of the file from which the read-only
            attribute or permission is to be removed.
    """
    try:
        if platform.system() == "Windows":
            # Check if read-only attribute is set
            if file_path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:
                file_path.chmod(stat.S_IWRITE)
                logger.debug(f"- - - '{file_path}' is no longer Read-Only.")
            else:
                logger.debug(f"- - - '{file_path}' is not set to Read-Only.")
        else:
            # Get current file permissions
            current_mode = file_path.stat().st_mode
            # Check if user write permission is not set (file is read-only)
            if not (current_mode & stat.S_IWUSR):
                # Add write permission for user
                file_path.chmod(current_mode | stat.S_IWUSR)
                logger.debug(f"- - - '{file_path}' is no longer Read-Only.")
            else:
                logger.debug(f"- - - '{file_path}' is not set to Read-Only.")

    except FileNotFoundError:
        logger.error(f"> > > ERROR (remove_readonly) : '{file_path}' not found.")
    except (ValueError, OSError) as err:
        logger.error(f"> > > ERROR (remove_readonly) : {err}")


def yaml_settings[T](_type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
    """
    Updates or retrieves a setting value from a given YAML store. The method
    handles type-specific processing for the retrieved or updated value, such
    as converting to a `Path` object when appropriate.

    Args:
        _type: The type of setting to retrieve or update. Supports generic
            type hinting.
        yaml_store: The YAML store object representing the settings data.
        key_path: The key path in the YAML store where the setting resides.
        new_value: The new value to be set in the YAML store at the given key
            path. This value must match the specified `_type`. Defaults to None.

    Returns:
        T | None: If `new_value` is provided, returns the updated setting value
        from the YAML store of the specified `_type`. If no `new_value` is
        provided, it retrieves and returns the current setting value in the
        YAML store of the given `_type`. Returns None if the setting does not
        exist or a type mismatch occurs.

    Raises:
        TypeError: If the YAML cache is not initialized.
    """
    if yaml_cache is None:
        raise TypeError("CMain not initialized")
    setting = yaml_cache.get_setting(_type, yaml_store, key_path, new_value)
    if _type is Path:
        return Path(setting) if setting and isinstance(setting, str) else None  # type: ignore[return-value]
    return setting


def classic_settings[T](_type: type[T], setting: str) -> T | None:
    """
    Fetches a specific setting from a CLASSIC settings file or creates the settings file
    if it does not exist.

    This function ensures that a settings file named "CLASSIC Settings.yaml" exists in the
    current directory. If the file does not exist, it creates the file based on default
    settings specified in another YAML configuration. The function then retrieves and
    returns the requested setting based on the provided type and setting key.

    Args:
        _type: The expected type of the setting value. This helps ensure the retrieved
            setting is appropriately cast to the desired type.
        setting: The key of the setting to retrieve from the "CLASSIC Settings.yaml"
            file.

    Returns:
        The value of the requested setting, cast to the specified type `_type`. If the
        setting is not found, or if an error occurs, it returns `None`.
    """
    settings_path = Path("CLASSIC Settings.yaml")
    if not settings_path.exists():
        default_settings = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_settings")
        if not isinstance(default_settings, str):
            raise ValueError("Invalid Default Settings in 'CLASSIC Main.yaml'")

        settings_path.write_text(default_settings, encoding="utf-8")

    return yaml_settings(_type, YAML.Settings, f"CLASSIC_Settings.{setting}")


# ================================================
# CREATE REQUIRED FILES, SETTINGS & UPDATE CHECK
# ================================================
def classic_generate_files() -> None:
    """Generate necessary CLASSIC YAML files.

    This function generates the following files if they do not already exist:
    - `CLASSIC Ignore.yaml`: Uses a default ignore file string specified in
      the YAML settings. Ensures the file content is written in UTF-8 encoding.
    - `CLASSIC Data/CLASSIC <GAME> Local.yaml`: Uses a default local YAML
      string specified in the YAML settings, where `<GAME>` is dynamically
      determined from `gamevars["game"]`. Ensures the file content is written
      in UTF-8 encoding.

    Raises:
        TypeError: If the default content retrieved for either the ignore file
            or the local YAML file is not of type `str`.
    """
    """Generate `CLASSIC Ignore.yaml` and `CLASSIC Data/CLASSIC <GAME> Local.yaml`."""
    ignore_path = Path("CLASSIC Ignore.yaml")
    if not ignore_path.exists():
        default_ignorefile = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_ignorefile")
        if not isinstance(default_ignorefile, str):
            raise TypeError
        ignore_path.write_text(default_ignorefile, encoding="utf-8")

    local_path = Path(f"CLASSIC Data/CLASSIC {gamevars["game"]} Local.yaml")
    if not local_path.exists():
        default_yaml = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_localyaml")
        if not isinstance(default_yaml, str):
            raise TypeError
        local_path.write_text(default_yaml, encoding="utf-8")


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
            print(yaml_settings(str, YAML.Main, f"CLASSIC_Interface.update_unable_{gamevars["game"]}"))
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
            print(yaml_settings(str, YAML.Main, f"CLASSIC_Interface.update_warning_{gamevars["game"]}"), flush=True)
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


# ================================================
# CHECK DEFAULT DOCUMENTS & GAME FOLDERS / FILES
# ================================================
# =========== CHECK DOCUMENTS FOLDER PATH -> GET GAME DOCUMENTS FOLDER ===========
# noinspection PyUnresolvedReferences
def docs_path_find() -> None:
    """
    Provides utility functions to locate and configure the path to a game's documents folder across different platforms.

    The module includes functionality to:
    - Locate the Documents folder on Windows using the system registry.
    - Locate the equivalent folder for Linux when run through Steam.
    - Allow manual user input for specifying the path when automated detection fails.

    Raises:
        OSError: If there is an error accessing the Windows registry.
        UnboundLocalError: If the required registry key is not found.
        TypeError: If the retrieved Steam ID is not an integer or if a required GUI component is uninitialized.
        FileNotFoundError: If a manual input path is provided but does not exist.

    Attributes:
        logger (Logger): Logger instance for debug-level messages.
        winreg (module): Windows registry access used for retrieving the user's documents path.
        Path (Path): Used for handling file and directory paths.
        yaml_settings (function): Utility function for reading and writing configuration from YAML files.
        YAML (enum): Enumerator for YAML configuration sections.
        gamevars (dict): Dictionary storing configuration values related to the current game context.
        gui_mode (bool): Indicator if the program is running in GUI mode.
        manual_docs_gui (object): GUI object for managing manual path inputs or directory selection.

    Defines:
        docs_path_find: Function to initialize the process of finding and validating the game's documents folder path.

    Sub-functions:
        get_windows_docs_path: Retrieves the Documents folder path for Windows systems.
        get_linux_docs_path: Retrieves the equivalent documents path for Linux systems when using Steam.
        get_manual_docs_path: Prompts the user for manual input to specify the documents folder path.
    """
    logger.debug("- - - INITIATED DOCS PATH CHECK")

    # Retrieve the document name from YAML settings
    docs_name = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.Main_Docs_Name")
    if not isinstance(docs_name, str):
        docs_name = gamevars["game"]

    def get_windows_docs_path() -> None:
        """
        Find and update the path of the user's My Documents folder on Windows and save
        it in the game's specific YAML configuration. This function uses the Windows
        Registry to retrieve the target path and falls back to defaults in case of
        errors.

        Raises:
            OSError: If there is an issue accessing the Windows Registry.
            UnboundLocalError: If the registry access results in unbound variable usage.
        """
        try:
            # Open the registry key to get the user's documents path
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:  # pyright: ignore[reportPossiblyUnboundVariable]
                documents_path = Path(
                    winreg.QueryValueEx(key, "Personal")[0])  # pyright: ignore[reportPossiblyUnboundVariable]
        except (OSError, UnboundLocalError):
            # Fallback to a default path if registry key is not found
            documents_path = Path.home() / "Documents"

        # Construct the full path to the game's documents folder
        win_docs = str(documents_path / "My Games" / cast("str", docs_name))

        # Update the YAML settings with the documents path
        yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs", win_docs)

    def get_linux_docs_path() -> None:
        """
        Retrieves and sets the path to the Linux-compatible game documents directory using the Steam
        library configuration file. This function reads the Steam library folders configuration, looks
        for the appropriate folder associated with the game's Steam ID, and constructs the path to the
        game's "My Documents" folder. It then sets this information into the YAML settings.

        Raises:
            TypeError: If the retrieved Steam ID is not of the expected integer type.
        """
        # Retrieve the Steam ID from YAML settings
        game_sid = yaml_settings(int, YAML.Game, f"Game{gamevars["vr"]}_Info.Main_SteamID")
        if not isinstance(game_sid, int):
            raise TypeError

        # Path to the Steam library folders configuration file
        libraryfolders_path = Path.home() / ".local/share/Steam/steamapps/common/libraryfolders.vdf"

        if libraryfolders_path.is_file():
            library_path = Path()
            with libraryfolders_path.open(encoding="utf-8", errors="ignore") as steam_library_raw:
                steam_library = steam_library_raw.readlines()

            for library_line in steam_library:
                if "path" in library_line:
                    library_path = Path(library_line.split('"')[3])
                if str(game_sid) in library_line:
                    library_path = library_path / "steamapps"
                    linux_docs = library_path / "compatdata" / str(
                        game_sid) / "pfx/drive_c/users/steamuser/My Documents/My Games" / cast("str", docs_name)
                    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs", str(linux_docs))

    def get_manual_docs_path() -> None:
        """
        Locates the path for manual documentation files and updates the application's YAML settings with the
        path provided by the user. Allows repeated attempts until a valid directory path is entered.

        Functions:
            get_manual_docs_path: Prompts the user for a directory path, validates the input, and updates the
                settings file with the path if valid. Displays guidance messages for user input validation.

        Raises:
            None
        """
        print(f"> > > PLEASE ENTER THE FULL DIRECTORY PATH WHERE YOUR {docs_name}.ini IS LOCATED < < <")
        while True:
            input_str = input(
                f"(EXAMPLE: C:/Users/Zen/Documents/My Games/{docs_name} | Press ENTER to confirm.)\n> ").strip()
            input_path = Path(input_str)
            if input_str and input_path.is_dir():
                print(f"You entered: '{input_str}' | This path will be automatically added to CLASSIC Settings.yaml")
                yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs", str(input_path))
                break

            print(f"'{input_str}' is not a valid or existing directory path. Please try again.")

    # =========== CHECK IF GAME DOCUMENTS FOLDER PATH WAS GENERATED AND FOUND ===========
    docs_path = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs")
    if not isinstance(docs_path, str):
        docs_path = None

    if docs_path is None:
        if platform.system() == "Windows":
            get_windows_docs_path()
        else:
            get_linux_docs_path()

    docs_path = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs")
    if not isinstance(docs_path, str):
        docs_path = None

    if docs_path and not Path(docs_path).is_dir():
        if gui_mode:
            if manual_docs_gui is None:
                raise TypeError("CMain not initialized")
            manual_docs_gui.manual_docs_path_signal.emit()
        else:
            get_manual_docs_path()


def get_manual_docs_path_gui(path: str) -> None:
    """
    Handles the selection of a manual documentation path through the
    graphical user interface (GUI). This function validates the given
    path, searches for a specific configuration file in the directory,
    and updates settings if the required file is found. If the validation
    fails or the required file is not found, an error message is
    displayed and the user is prompted to try again.

    Args:
        path: A string representing the directory path entered by the
            user through the GUI. The function expects this path to be
            validated as an existing directory containing the necessary
            game-specific configuration file (e.g., `{game}.ini`).
    """
    if manual_docs_gui is None:
        raise TypeError("CMain not initialized")

    path = path.strip()
    if Path(path).is_dir():
        file_found: bool = False
        for file in Path(path).rglob("*.ini"):
            if f"{gamevars["game"]}.ini" in file.name:
                print(f"You entered: '{path}' | This path will be automatically added to CLASSIC Settings.yaml")
                manual_docs = Path(path)
                yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs", str(manual_docs))
                file_found = True
                break
        if not file_found:
            print(f"❌ ERROR : NO {gamevars["game"]}.ini FILE FOUND IN '{path}'! Please try again.")
            manual_docs_gui.manual_docs_path_signal.emit()
    else:
        print(f"'{path}' is not a valid or existing directory path. Please try again.")
        manual_docs_gui.manual_docs_path_signal.emit()


def docs_generate_paths() -> None:
    """
    Generates and configures paths for documentation files based on various game-specific
    yaml settings. Integrates configuration with specific folders and file paths required
    for documentation purposes. Validates the types of fetched data and applies the
    appropriate yaml updates for local game documentation settings.

    Raises:
        TypeError: Raised if any of the key yaml retrieved settings are not of
            expected types as str.
    """
    logger.debug("- - - INITIATED DOCS PATH GENERATION")
    xse_acronym = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.XSE_Acronym")
    xse_acronym_base = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
    docs_path_str = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs")
    if not (isinstance(xse_acronym, str) and isinstance(xse_acronym_base, str) and isinstance(docs_path_str, str)):
        raise TypeError
    docs_path = Path(docs_path_str)

    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_Folder_XSE",
                  str(docs_path.joinpath(xse_acronym_base)))
    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_File_PapyrusLog",
                  str(docs_path.joinpath("Logs/Script/Papyrus.0.log")))
    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_File_WryeBashPC",
                  str(docs_path.joinpath("ModChecker.html")))
    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_File_XSE",
                  str(docs_path.joinpath(xse_acronym_base, f"{xse_acronym.lower()}.log")))


# =========== CHECK DOCUMENTS XSE FILE -> GET GAME ROOT FOLDER PATH ===========
def game_path_find() -> None:
    """
    Performs game path verification and ensures that the game executable is
    correctly located. It checks for the installation path in the Windows
    Registry and verifies the game directory using log files or user input.
    The method also updates the YAML settings for future reference.

    Raises:
        TypeError: If the XSE loader log file or game-related YAML settings are
            not of the expected type.
    """
    logger.debug("- - - INITIATED GAME PATH CHECK")

    path: str | None
    game_path: Path | None

    try:
        # Open the registry key
        reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 rf"SOFTWARE\WOW6432Node\Bethesda Softworks\{gamevars["game"]}{gamevars["vr"]}")  # pyright: ignore[reportPossiblyUnboundVariable]
        # Query the 'installed path' value
        path, _ = winreg.QueryValueEx(reg_key, "installed path")  # pyright: ignore[reportPossiblyUnboundVariable]
        winreg.CloseKey(reg_key)  # pyright: ignore[reportPossiblyUnboundVariable]
    except FileNotFoundError:
        try:
            reg_key_gog = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                         r"SOFTWARE\WOW6432Node\GOG.com\Games\1998527297")  # pyright: ignore[reportPossiblyUnboundVariable]
            path, _ = winreg.QueryValueEx(reg_key_gog, "path")  # pyright: ignore[reportPossiblyUnboundVariable]
            winreg.CloseKey(reg_key_gog)  # pyright: ignore[reportPossiblyUnboundVariable]
        except (FileNotFoundError, UnboundLocalError, OSError):
            game_path = None
        else:
            game_path = Path(path) if path else None
    except (UnboundLocalError, OSError):
        game_path = None
    else:
        game_path = Path(path) if path else None

    exe_name = f"{gamevars["game"]}{gamevars["vr"]}.exe"

    if game_path and game_path.is_dir() and game_path.joinpath(exe_name).is_file():
        yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Game", str(game_path))
        return

    xse_file = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_File_XSE")
    xse_acronym = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.XSE_Acronym")
    xse_acronym_base = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
    game_name = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.Main_Root_Name")
    if not (isinstance(xse_file, str) or xse_file is None):
        raise TypeError
    if not (isinstance(xse_acronym, str) and isinstance(xse_acronym_base, str) and isinstance(game_name, str)):
        raise TypeError

    if not xse_file or not Path(cast("str", xse_file)).is_file():
        print(f"❌ CAUTION : THE {xse_acronym.lower()}.log FILE IS MISSING FROM YOUR GAME DOCUMENTS FOLDER! \n")
        print(f"   You need to run the game at least once with {xse_acronym.lower()}_loader.exe \n")
        print("    After that, try running CLASSIC again! \n-----\n")
        return

    with open_file_with_encoding(cast("str", xse_file)) as LOG_Check:
        path_check = LOG_Check.readlines()
    for logline in path_check:
        if logline.startswith("plugin directory"):
            logline = logline.split("=", maxsplit=1)[1].strip().replace(f"\\Data\\{xse_acronym_base}\\Plugins",
                                                                        "").replace("\n", "")
            game_path = Path(logline)
            break
    if game_path and game_path.is_dir() and game_path.joinpath(exe_name).is_file():
        yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Game", str(game_path))
        return

    if gui_mode:
        if game_path_gui is None:
            raise TypeError("CMain not initialized")
        game_path_gui.game_path_signal.emit()
        return

    while True:
        print(f"> > PLEASE ENTER THE FULL DIRECTORY PATH WHERE YOUR {game_name} IS LOCATED < <")
        path_input = input(fr"(EXAMPLE: C:\Steam\steamapps\common\{game_name} | Press ENTER to confirm.)\n> ")
        print(f"You entered: {path_input} | This path will be automatically added to CLASSIC Settings.yaml")
        game_path = Path(path_input.strip())
        if game_path and game_path.joinpath(exe_name).is_file():
            yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Game", str(game_path))
            return
        print(f"❌ ERROR : NO {gamevars["game"]}{gamevars["vr"]}.exe FILE FOUND IN '{game_path}'! Please try again.")


def game_generate_paths() -> None:
    """
    Generates and updates file paths for game configurations based on game variant and version.

    This function reads game-specific configurations and dynamically constructs essential
    file paths required for game execution. The paths are stored in a configuration YAML
    file for local game settings. Additionally, it handles version-specific file naming
    in certain cases such as "AddressLib" files for different versions of Fallout 4. The
    function also ensures appropriate types for necessary variables, raising errors
    if validations fail.

    Raises:
        TypeError: If `game_path` or `xse_acronym_base` are not strings.
        ValueError: If an unsupported or invalid `game_version` is detected for Fallout 4.

    Returns:
        None
    """
    logger.debug("- - - INITIATED GAME PATH GENERATION")

    game_path = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Game")
    yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.XSE_Acronym")
    xse_acronym_base = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
    if not (isinstance(game_path, str) and isinstance(xse_acronym_base, str)):
        raise TypeError

    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_Folder_Data", rf"{game_path}\Data")
    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_Folder_Scripts", rf"{game_path}\Data\Scripts")
    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_Folder_Plugins",
                  fr"{game_path}\Data\{xse_acronym_base}\Plugins")
    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_File_SteamINI", rf"{game_path}\steam_api.ini")
    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_File_EXE",
                  fr"{game_path}\{gamevars["game"]}{gamevars["vr"]}.exe")
    game_version = get_game_version(
        Path(cast("str", yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_File_EXE"))))
    match gamevars["game"]:
        case "Fallout4" if not gamevars["vr"]:
            if (not game_version or game_version not in Constants.FO4_VERSIONS) and game_version != Constants.NULL_VERSION:
                raise ValueError("Unsupported or invalid game version")
            if game_version in (Constants.OG_VERSION, Constants.NULL_VERSION):
                yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_AddressLib",
                              fr"{game_path}\Data\{xse_acronym_base}\plugins\version-1-10-163-0.bin")
            elif game_version == Constants.NG_VERSION:
                yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_AddressLib",
                              fr"{game_path}\Data\{xse_acronym_base}\plugins\version-1-10-984-0.bin")
        case "Fallout4" if gamevars["vr"]:
            yaml_settings(str, YAML.Game_Local, "GameVR_Info.Game_File_AddressLib",
                          fr"{game_path}\Data\{xse_acronym_base}\plugins\version-1-2-72-0.csv")


# =========== CHECK GAME EXE FILE -> GET PATH AND HASHES ===========
# noinspection DuplicatedCode
def game_check_integrity() -> str:
    """
    Checks the integrity of the game files, including executable file version and Steam
    INI file existence, and generates a summary message on the validity and installation
    status of the game. It ensures that the local game files match the hashes stored in
    the database and assesses proper installation directories.

    Returns:
        str: A detailed message indicating the integrity status of game files.

    Raises:
        TypeError: If any of the settings loaded from the configuration files is not of the
            expected type.
    """
    message_list = []
    logger.debug("- - - INITIATED GAME INTEGRITY CHECK")

    steam_ini_local = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_File_SteamINI")
    exe_hash_old = yaml_settings(str, YAML.Game, "Game_Info.EXE_HashedOLD")  # The VR check is not needed here.
    exe_hash_new = yaml_settings(str, YAML.Game,
                                 "Game_Info.EXE_HashedNEW")  # ...or here. VR hashes are not available at this time.
    game_exe_local = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_File_EXE")
    root_name = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.Main_Root_Name")
    if not (isinstance(exe_hash_old, str) and isinstance(root_name, str)):
        raise TypeError
    if not (isinstance(steam_ini_local, str) or steam_ini_local is None):
        raise TypeError
    if not (isinstance(game_exe_local, str) or game_exe_local is None):
        raise TypeError

    game_exe_path = Path(game_exe_local) if game_exe_local else None
    steam_ini_path = Path(steam_ini_local) if steam_ini_local else None
    if game_exe_path and game_exe_path.is_file():
        with game_exe_path.open("rb") as f:
            file_contents = f.read()
            # Algo should match the one used for Database YAML!
            exe_hash_local = hashlib.sha256(file_contents).hexdigest()
        # print(f"LOCAL: {exe_hash_local}\nDATABASE: {exe_hash_old}")
        if (exe_hash_local in (exe_hash_old, exe_hash_new)) and not (steam_ini_path and steam_ini_path.exists()):
            message_list.append(f"✔️ You have the latest version of {root_name}! \n-----\n")
        elif steam_ini_path and steam_ini_path.exists():
            message_list.append(f"\U0001F480 CAUTION : YOUR {root_name} GAME / EXE VERSION IS OUT OF DATE \n-----\n")
        else:
            message_list.append(f"❌ CAUTION : YOUR {root_name} GAME / EXE VERSION IS OUT OF DATE \n-----\n")

        if "Program Files" not in str(game_exe_path):
            message_list.append(
                f"✔️ Your {root_name} game files are installed outside of the Program Files folder! \n-----\n")
        else:
            root_warn = yaml_settings(str, YAML.Main, "Warnings_GAME.warn_root_path")
            if not isinstance(root_warn, str):
                raise TypeError
            message_list.append(root_warn)

    return "".join(message_list)


# =========== CHECK GAME XSE SCRIPTS -> GET PATH AND HASHES ===========
# noinspection DuplicatedCode
def xse_check_integrity() -> str:  # RESERVED | NEED VR HASH/FILE CHECK
    """
    Checks the integrity of the XSE (Script Extender) installation, files, and logs.

    This function performs an integrity check for the Script Extender (XSE) by verifying the existence of
    required files, ensuring compatibility with the latest version, and analyzing log files for potential
    errors. It also generates informative messages or warnings based on the state of the XSE components
    and captures any issues identified in the log file.

    Raises:
        TypeError: If expected settings or file paths are not of the correct type or are invalid.

    Returns:
        str: A concatenated string of messages and warnings indicating the results of the integrity check.
    """
    failed_list: list[str] = []
    message_list: list[str] = []
    logger.debug("- - - INITIATED XSE INTEGRITY CHECK")

    catch_errors = yaml_settings(list[str], YAML.Main, "catch_log_errors")
    xse_acronym = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.XSE_Acronym")
    xse_log_file = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_File_XSE")
    xse_full_name = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.XSE_FullName")
    xse_ver_latest = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.XSE_Ver_Latest")
    adlib_file_str = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_File_AddressLib")
    if not isinstance(catch_errors, list):
        raise TypeError
    if not (isinstance(xse_acronym, str) and isinstance(xse_full_name, str) and isinstance(xse_ver_latest, str)):
        raise TypeError
    if not (isinstance(xse_log_file, str) or xse_log_file is None):
        raise TypeError
    if not (isinstance(adlib_file_str, str) or adlib_file_str is None):
        raise TypeError
    adlib_file = Path(adlib_file_str) if adlib_file_str else None

    match adlib_file:
        case str() | Path():
            if Path(adlib_file).exists():
                message_list.append("✔️ REQUIRED: *Address Library* for Script Extender is installed! \n-----\n")
            else:
                warn_adlib = yaml_settings(str, YAML.Game, "Warnings_MODS.Warn_ADLIB_Missing")
                if not isinstance(warn_adlib, str):
                    raise TypeError
                message_list.append(warn_adlib)
        case _:
            message_list.append(
                f"❌ Value for Address Library is invalid or missing from CLASSIC {gamevars["game"]} Local.yaml!\n-----\n")

    match xse_log_file:
        case str() | Path():
            if Path(cast("str", xse_log_file)).exists():
                message_list.append(f"✔️ REQUIRED: *{xse_full_name}* is installed! \n-----\n")
                with open_file_with_encoding(cast("str", xse_log_file)) as xse_log:
                    xse_data = xse_log.readlines()
                if str(xse_ver_latest) in xse_data[0]:
                    message_list.append(f"✔️ You have the latest version of *{xse_full_name}*! \n-----\n")
                else:
                    warn_outdated = yaml_settings(str, YAML.Game, "Warnings_XSE.Warn_Outdated")
                    if not isinstance(warn_outdated, str):
                        raise TypeError
                    message_list.append(warn_outdated)
                failed_list.extend([
                    line for line in xse_data if any(item.lower() in line.lower() for item in catch_errors)
                ])

                if failed_list:
                    message_list.append(f"#❌ CAUTION : {xse_acronym}.log REPORTS THE FOLLOWING ERRORS #\n")
                    message_list.extend([f"ERROR > {elem.strip()} \n-----\n" for elem in failed_list])
            else:
                message_list.extend(
                    [f"❌ CAUTION : *{xse_acronym.lower()}.log* FILE IS MISSING FROM YOUR DOCUMENTS FOLDER! \n",
                     f"   You need to run the game at least once with {xse_acronym.lower()}_loader.exe \n",
                     "    After that, try running CLASSIC again! \n-----\n"])
        case _:
            message_list.append(
                f"❌ Value for {xse_acronym.lower()}.log is invalid or missing from CLASSIC {gamevars["game"]} Local.yaml!\n-----\n")

    return "".join(message_list)


def xse_check_hashes() -> str:
    """
    Performs integrity checks for Script Extender (XSE) files by validating their hashes against the expected ones
    stored in the game YAML configuration. Reports missing or mismatched files and generates appropriate warning
    messages based on the configuration. Ensures that the scripts are intact and not overridden by external modifications.

    Raises:
        TypeError: If configuration data types retrieved from YAML settings do not match the expected types.

    Returns:
        str: Consolidated message summarizing the results of the integrity check, including warnings about missing or
        mismatched files, or confirmation that all scripts are correctly validated.
    """
    message_list: list[str] = []
    logger.debug("- - - INITIATED XSE FILE HASH CHECK")

    xse_script_missing = xse_script_mismatch = False
    xse_hashedscripts = yaml_settings(dict[str, str], YAML.Game, f"Game{gamevars["vr"]}_Info.XSE_HashedScripts")
    game_folder_scripts = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_Folder_Scripts")
    if not isinstance(xse_hashedscripts, dict):
        raise TypeError
    if not (isinstance(game_folder_scripts, str) or game_folder_scripts is None):
        raise TypeError

    xse_hashedscripts_local = dict.fromkeys(xse_hashedscripts)
    for key in xse_hashedscripts_local:
        script_path = Path(rf"{game_folder_scripts}\{key!s}")
        if script_path.is_file():
            with script_path.open("rb") as f:
                file_contents = f.read()
                # Algo should match the one used for Database YAML!
                file_hash = hashlib.sha256(file_contents).hexdigest()
                xse_hashedscripts_local[key] = str(file_hash)

    for key in xse_hashedscripts:
        if key in xse_hashedscripts_local:
            hash1 = xse_hashedscripts[key]
            hash2 = xse_hashedscripts_local[key]
            if hash1 == hash2:
                pass
            elif hash2 is None:  # Can only be None if not hashed in the first place, meaning it is missing.
                message_list.append(
                    f"❌ CAUTION : {key} Script Extender file is missing from your game Scripts folder! \n-----\n")
                xse_script_missing = True
            else:
                message_list.append(
                    f"[!] CAUTION : {key} Script Extender file is outdated or overriden by another mod! \n-----\n")
                xse_script_mismatch = True

    if xse_script_missing:
        warn_missing = yaml_settings(str, YAML.Game, "Warnings_XSE.Warn_Missing")
        if not isinstance(warn_missing, str):
            raise TypeError
        message_list.append(warn_missing)
    if xse_script_mismatch:
        warn_mismatch = yaml_settings(str, YAML.Game, "Warnings_XSE.Warn_Mismatch")
        if not isinstance(warn_mismatch, str):
            raise TypeError
        message_list.append(warn_mismatch)
    if not xse_script_missing and not xse_script_mismatch:
        message_list.append("✔️ All Script Extender files have been found and accounted for! \n-----\n")

    return "".join(message_list)


# ================================================
# CHECK DOCUMENTS GAME INI FILES & INI SETTINGS
# ================================================
def docs_check_folder() -> str:
    """
    Checks the folder configuration for game documentation and returns any warnings if applicable.

    This function verifies the documentation path and checks for specific keywords like "onedrive"
    in the documentation path name. If the specific condition is met, it appends a warning
    message to a list and returns the concatenated string of warnings.

    Returns:
        str: A concatenated string of all warnings, if applicable; otherwise, an empty string.

    Raises:
        TypeError: If the `docs_name` or `docs_warn` obtained from YAML settings is not of type str.
    """
    message_list = []
    docs_name = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.Main_Docs_Name")
    if not isinstance(docs_name, str):
        raise TypeError
    if "onedrive" in docs_name.lower():
        docs_warn = yaml_settings(str, YAML.Main, "Warnings_GAME.warn_docs_path")
        if not isinstance(docs_warn, str):
            raise TypeError
        message_list.append(docs_warn)
    return "".join(message_list)


# =========== CHECK DOCS MAIN INI -> CHECK EXISTENCE & CORRUPTION ===========
def docs_check_ini(ini_name: str) -> str:
    """
    Performs a series of validation and configuration updates on the provided INI file to ensure it conforms to
    the required settings for proper functionality of the associated game. It checks for file existence, corruption,
    and specific configuration settings, making appropriate changes and logging messages during the process.

    Args:
        ini_name (str): The name of the INI file to validate and process.

    Returns:
        str: A concatenated string of messages detailing the checks performed and any corrective actions taken.

    Raises:
        TypeError: Raised when provided values for key configurations or paths are not of the expected type.
        PermissionError: Occurs when the INI file is set to read-only and cannot be modified.
        configparser.MissingSectionHeaderError: If the INI file lacks section headers, indicating a corrupted file.
        configparser.ParsingError: Triggered when the INI file has parsing issues.
        configparser.DuplicateOptionError: Raised when duplicate configuration options are detected in the file.
        ValueError: Raised when file operations or content validation fail unexpectedly.
        OSError: Raised during file system access or writing errors.
    """
    message_list: list[str] = []
    logger.info(f"- - - INITIATED {ini_name} CHECK")
    folder_docs = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs")
    docs_name = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.Main_Docs_Name")
    if not isinstance(docs_name, str):
        raise TypeError
    if not (isinstance(folder_docs, str) or folder_docs is None):
        raise TypeError

    ini_file_list = list(Path(folder_docs).glob("*.ini")) if folder_docs else []
    ini_path = Path(folder_docs).joinpath(ini_name) if folder_docs else None
    if ini_path is None:
        raise TypeError
    if any(ini_name.lower() in file.name.lower() for file in ini_file_list):
        try:
            remove_readonly(ini_path)

            ini_config = configparser.ConfigParser()
            ini_config.optionxform = str  # type: ignore[method-assign, assignment]
            ini_config.read(ini_path)
            message_list.append(f"✔️ No obvious corruption detected in {ini_name}, file seems OK! \n-----\n")

            if ini_name.lower() == f"{docs_name.lower()}custom.ini":
                if "Archive" not in ini_config.sections():
                    message_list.extend(["❌ WARNING : Archive Invalidation / Loose Files setting is not enabled. \n",
                                         "  CLASSIC will now enable this setting automatically in the game INI files. \n-----\n"])
                    with contextlib.suppress(configparser.DuplicateSectionError):
                        ini_config.add_section("Archive")
                else:
                    message_list.append("✔️ Archive Invalidation / Loose Files setting is already enabled! \n-----\n")

                ini_config.set("Archive", "bInvalidateOlderFiles", "1")
                ini_config.set("Archive", "sResourceDataDirsFinal", "")

                with ini_path.open("w+", encoding="utf-8", errors="ignore") as ini_file:
                    ini_config.write(cast("TextIOWrapper", ini_file), space_around_delimiters=False)

        except PermissionError:
            message_list.extend([f"[!] CAUTION : YOUR {ini_name} FILE IS SET TO READ ONLY. \n",
                                 "     PLEASE REMOVE THE READ ONLY PROPERTY FROM THIS FILE, \n",
                                 "     SO CLASSIC CAN MAKE THE REQUIRED CHANGES TO IT. \n-----\n"])

        except (configparser.MissingSectionHeaderError, configparser.ParsingError, ValueError, OSError):
            message_list.extend(
                [f"[!] CAUTION : YOUR {ini_name} FILE IS VERY LIKELY BROKEN, PLEASE CREATE A NEW ONE \n",
                 f"    Delete this file from your Documents/My Games/{docs_name} folder, then press \n",
                 f"    *Scan Game Files* in CLASSIC to generate a new {ini_name} file. \n-----\n"])
        except configparser.DuplicateOptionError as e:
            message_list.extend([f"[!] ERROR : Your {ini_name} file has duplicate options! \n",
                                 f"    {e} \n-----\n"])
    else:
        if ini_name.lower() == f"{docs_name.lower()}.ini":
            message_list.extend([f"❌ CAUTION : {ini_name} FILE IS MISSING FROM YOUR DOCUMENTS FOLDER! \n",
                                 f"   You need to run the game at least once with {docs_name}Launcher.exe \n",
                                 "    This will create files and INI settings required for the game to run. \n-----\n"])

        if ini_name.lower() == f"{docs_name.lower()}custom.ini":
            with ini_path.open("a", encoding="utf-8", errors="ignore") as ini_file:
                message_list.extend(["❌ WARNING : Archive Invalidation / Loose Files setting is not enabled. \n",
                                     "  CLASSIC will now enable this setting automatically in the game INI files. \n-----\n"])
                customini_config = yaml_settings(str, YAML.Game, "Default_CustomINI")
                if not isinstance(customini_config, str):
                    raise TypeError
                ini_file.write(customini_config)

    return "".join(message_list)


# =========== GENERATE FILE BACKUPS ===========
# noinspection DuplicatedCode
def main_files_backup() -> None:
    """
    Backs up game files specified in the YAML configuration to a versioned directory.

    The function reads a list of files to back up from the YAML configuration, the game
    path, and the current game-specific log file. It determines the current game
    version, creates a backup directory for that version if it does not exist, and
    copies files from the game directory to the backup directory, provided the files
    are listed in the backup configuration and do not already exist in the backup.

    Raises:
        TypeError: If the YAML settings do not provide the required data types.
        FileNotFoundError: If the game log file specified in the YAML settings is not found
          during attempt to read it.
    """
    # Got an expired certificate warning after a few tries, maybe there's a better way?
    backup_list = yaml_settings(list[str], YAML.Main, "CLASSIC_AutoBackup")
    game_path = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Game")
    xse_log_file = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_File_XSE")
    xse_ver_latest = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.XSE_Ver_Latest")

    if not (isinstance(backup_list, list) and isinstance(xse_ver_latest, str)):
        raise TypeError
    if not (isinstance(game_path, str) or game_path is None):
        raise TypeError
    if not isinstance(xse_log_file, str):
        raise TypeError

    try:
        with open_file_with_encoding(xse_log_file) as xse_log:
            xse_data = xse_log.readlines()
            xse_data_lower = [line.lower() for line in xse_data]
    except FileNotFoundError:
        xse_data_lower = []

    # Grab current xse version to create a folder with that name.
    if len(xse_data_lower) > 0:
        line_xse = next(line for _, line in enumerate(xse_data_lower) if "version = " in line)
        split_xse = line_xse.split(" ")
        version_xse = xse_ver_latest

        for index, item in enumerate(split_xse):
            if "version" in item:
                index_xse = int(index + 2)
                version_xse = split_xse[index_xse]
                break

        # If there is no folder for current xse version, create it.
        backup_path = Path(f"CLASSIC Backup/Game Files/{version_xse}") if version_xse else None
        if backup_path:
            backup_path.mkdir(parents=True, exist_ok=True)

            # Backup the file if backup of file does not already exist.
            game_files = list(Path(game_path).glob("*.*")) if game_path else []
            backup_files = [file.name for file in backup_path.glob("*.*")]

            for file in game_files:
                if file.name not in backup_files and any(file.name in item for item in backup_list):
                    destination_file = backup_path / file.name
                    shutil.copy2(file, destination_file)


# =========== GENERATE MAIN RESULTS ===========
def main_combined_result() -> str:
    """
    Combines and executes multiple integrity and configuration checks.

    This function executes a series of integrity checks that include game
    integrity validation, hash verification, and validation of specific
    configuration files. The results from all the checks are aggregated
    and returned as a single concatenated string representing the combined
    outcome of all checks.

    Returns:
        str: A concatenated string containing the results of all executed
        checks.
    """
    combined_return = [game_check_integrity(), xse_check_integrity(), xse_check_hashes(), docs_check_folder(),
                       docs_check_ini(f"{gamevars["game"]}.ini"), docs_check_ini(f"{gamevars["game"]}Custom.ini"),
                       docs_check_ini(f"{gamevars["game"]}Prefs.ini")]
    return "".join(combined_return)


def main_generate_required() -> None:
    """
    Executes the main logic for generating required settings and verifying the game setup integrity.

    This function configures logging, generates files, and validates game and classic version
    info. It provides an initial check and feedback for compatibility of crash logs and game
    settings. Depending on whether the game path is found within the settings, the function
    either runs path generation procedures or backs up main files. Displays relevant messages
    to the user regarding progress and outcomes.

    Raises:
        TypeError: If the classic version or game name settings are not of type `str`.

    """
    configure_logging()
    classic_generate_files()
    classic_ver = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
    game_name = yaml_settings(str, YAML.Game, "Game_Info.Main_Root_Name")
    if not (isinstance(classic_ver, str) and isinstance(game_name, str)):
        raise TypeError
    print(f"Hello World! | Crash Log Auto Scanner & Setup Integrity Checker | {classic_ver} | {game_name}")
    print("REMINDER: COMPATIBLE CRASH LOGS MUST START WITH 'crash-' AND MUST HAVE .log EXTENSION \n")
    print("❓ PLEASE WAIT WHILE CLASSIC CHECKS YOUR SETTINGS AND GAME SETUP...")
    logger.debug(f"> > > STARTED {classic_ver}")

    game_path = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Game")

    if not game_path:
        docs_path_find()
        docs_generate_paths()
        game_path_find()
        game_generate_paths()
    else:
        main_files_backup()

    print("✔️ ALL CLASSIC AND GAME SETTINGS CHECKS HAVE BEEN PERFORMED!")
    print("    YOU CAN NOW SCAN YOUR CRASH LOGS, GAME AND/OR MOD FILES \n")


yaml_cache: YamlSettingsCache | None = None
manual_docs_gui: ManualDocsPath | None = None
game_path_gui: GamePathEntry | None = None
gui_mode: bool = False


def initialize(is_gui: bool = False) -> None:
    """
    Initializes the application state, sets up the YAML settings cache, and optionally enables GUI mode.

    This function initializes the necessary components required for the application's operation, such
    as loading static YAML files into a settings cache. It also determines whether the application
    should operate in GUI mode and sets up related resources accordingly.

    Args:
        is_gui (bool): Indicates whether the application should operate in GUI mode. If True,
            GUI-related resources are initialized.
    """
    global gui_mode, yaml_cache, manual_docs_gui, game_path_gui  # noqa: PLW0603

    yaml_cache = YamlSettingsCache()

    # Pre-load static YAML files
    for store in YamlSettingsCache.STATIC_YAML_STORES:
        path = yaml_cache.get_path_for_store(store)
        yaml_cache.load_yaml(path)

    # noinspection PyTypedDict
    gamevars["vr"] = "" if not classic_settings(bool, "VR Mode") else cast('Literal["VR", ""]', "VR")
    gui_mode = is_gui
    if gui_mode:
        manual_docs_gui = ManualDocsPath()
        game_path_gui = GamePathEntry()


if __name__ == "__main__":  # AKA only autorun / do the following when NOT imported.
    raise RuntimeError("""This module is not meant to be run directly. 
Please use it as part of the CLASSIC application.""")
