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
from functools import reduce
from io import TextIOWrapper
from pathlib import Path
from typing import Literal, TypedDict, cast, Any

import aiohttp
import chardet
import ruamel.yaml
from packaging.version import InvalidVersion, Version
from PySide6.QtCore import QObject, Signal

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
NULL_VERSION = Version("0.0.0.0")
OG_VERSION = Version("1.10.163.0")
NG_VERSION = Version("1.10.984.0")
VR_VERSION = Version("1.2.72.0")
OG_F4SE_VERSION = Version("0.6.23")
NG_F4SE_VERSION = Version("0.7.2")
FO4_VERSIONS = (OG_VERSION, NG_VERSION)
F4SE_VERSIONS = (OG_F4SE_VERSION, NG_F4SE_VERSION)
type YAMLLiteral = str | int | bool
type YAMLSequence = list[str]
type YAMLMapping = dict[str, "YAMLValue"]
type YAMLValue = YAMLMapping | YAMLSequence | YAMLLiteral
type YAMLValueOptional = YAMLValue | None
type GameID = Literal[
    "Fallout4", "Fallout4VR", "Skyrim", "Starfield"]  # Entries must correspond to the game's Main ESM or EXE file name.


def get_game_version(game_exe_path: Path) -> Version:
    """
    Get the game version from the game's executable file.

    Returns:
        Version: A Version object containing the game's version information.
                 Returns Version("0.0.0.0") if the game executable cannot be found
                 or if the version information cannot be retrieved.
    """
    
    if platform.system() != "Windows":
        logger.warning("Game version detection is only supported on Windows")
        return NULL_VERSION

    # Check if path exists and is a file
    if not game_exe_path or not game_exe_path.is_file():
        logger.warning("Game executable not found or path is invalid")
        return NULL_VERSION

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
        return NULL_VERSION
    except (AttributeError, UnboundLocalError):
        logger.error("win32api module not properly loaded")
        return NULL_VERSION
    except (OSError, ValueError) as e:
        logger.error(f"Error retrieving version info: {e}")
        return NULL_VERSION
    except Exception as e:  # noqa: BLE001
        logger.error(f"Unexpected error getting game version: {e}")
        return NULL_VERSION
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
    game: GameID
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
    Opens a text file with automatic encoding detection.
    Args:
        file_path (Path | str | os.PathLike): The path to the file to be opened.
    Yields:
        Iterator[TextIOWrapper]: A file object opened in read mode with the detected encoding.
    Notes:
        - This function reads the file as bytes to detect the encoding using the `chardet` library.
        - The file is opened with the detected encoding and errors are ignored during reading.
        - The file is automatically closed after the context is exited.
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
    Configure logging for the application.
    This function sets up logging to a file named `CLASSIC Journal.log`. If the log file
    exists and is older than 7 days, it will be deleted and a new log file will be created.
    The logging levels available are: debug, info, warning, error, and critical.
    Global Variables:
        logger (logging.Logger): The logger instance used for logging messages.
    Raises:
        ValueError: If an error occurs while deleting the old log file.
        OSError: If an error occurs while deleting the old log file.
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
    Remove the read-only flag from a given file, if present.
    Parameters:
        file_path (Path): The path to the file from which the read-only flag should be removed.
    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If there is an issue with the file path or permissions.
        OSError: If there is an operating system-related error.
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


class YamlSettingsCache:
    """
    A class to handle caching of YAML settings with optimizations for static files.
    
    Static files (YAML.Main and YAML.Game) are loaded once and not checked for changes.
    Dynamic files are monitored for modifications and reloaded as needed.
    """
    # Static YAML stores that won't change during program execution
    STATIC_YAML_STORES = {YAML.Main, YAML.Game}

    def __init__(self) -> None:
        self.cache: dict[Path, YAMLMapping] = {}
        self.file_mod_times: dict[Path, float] = {}
        self.path_cache: dict[YAML, Path] = {}  # Cache for YAML store to Path mapping
        self.settings_cache: dict[tuple[YAML, str, type], Any] = {}  # Cache for frequently accessed settings

    def get_path_for_store(self, yaml_store: YAML) -> Path:
        """Get the file path for a YAML store, with caching."""
        if yaml_store in self.path_cache:
            return self.path_cache[yaml_store]

        data_path = Path("CLASSIC Data/")
        match yaml_store:
            case YAML.Main:
                yaml_path = data_path / "databases/CLASSIC Main.yaml"
            case YAML.Settings:
                yaml_path = Path("CLASSIC Settings.yaml")
            case YAML.Ignore:
                yaml_path = Path("CLASSIC Ignore.yaml")
            case YAML.Game:
                yaml_path = data_path / f"databases/CLASSIC {gamevars['game']}.yaml"
            case YAML.Game_Local:
                yaml_path = data_path / f"CLASSIC {gamevars['game']} Local.yaml"
            case YAML.TEST:
                yaml_path = Path("tests/test_settings.yaml")
            case _:
                raise NotImplementedError

        self.path_cache[yaml_store] = yaml_path
        return yaml_path

    def load_yaml(self, yaml_path: Path) -> YAMLMapping:
        """
        Load a YAML file with caching based on whether it's static or dynamic.
        
        Static files are loaded once, while dynamic files are checked for modifications.
        """
        if not yaml_path.exists():
            return {}

        # Determine if this is a static file
        is_static = any(yaml_path == self.get_path_for_store(store) for store in self.STATIC_YAML_STORES)

        if is_static:
            # For static files, just load once
            if yaml_path not in self.cache:
                logger.debug(f"Loading static YAML file: {yaml_path}")
                with yaml_path.open(encoding="utf-8") as yaml_file:
                    yaml = ruamel.yaml.YAML()
                    yaml.indent(offset=2)
                    yaml.width = 300
                    self.cache[yaml_path] = yaml.load(yaml_file)
        else:
            # For dynamic files, check modification time
            last_mod_time = yaml_path.stat().st_mtime
            if (yaml_path not in self.file_mod_times or
                    self.file_mod_times[yaml_path] != last_mod_time):
                # Update the file modification time
                self.file_mod_times[yaml_path] = last_mod_time

                logger.debug(f"Loading dynamic YAML file: {yaml_path}")
                # Reload the YAML file
                with yaml_path.open(encoding="utf-8") as yaml_file:
                    yaml = ruamel.yaml.YAML()
                    yaml.indent(offset=2)
                    yaml.width = 300
                    self.cache[yaml_path] = yaml.load(yaml_file)

        return self.cache.get(yaml_path, {})

    def get_setting[T](self, _type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
        """
        Retrieve or update a setting from a specified YAML store.
        
        For static stores, results are cached to avoid repeated YAML traversal.
        """
        # If this is a read operation for a static store, check cache first
        cache_key = (yaml_store, key_path, _type)
        if new_value is None and yaml_store in self.STATIC_YAML_STORES and cache_key in self.settings_cache:
            return self.settings_cache[cache_key]

        yaml_path = self.get_path_for_store(yaml_store)

        # Load YAML with caching logic
        data = self.load_yaml(yaml_path)
        keys = key_path.split(".")

        def setdefault(dictionary: dict[str, YAMLValue], key: str) -> dict[str, YAMLValue]:
            if key not in dictionary:
                dictionary[key] = {}
            next_value = dictionary[key]
            if not isinstance(next_value, dict):
                raise TypeError
            return next_value

        try:
            setting_container = reduce(setdefault, keys[:-1], data)
        except TypeError:
            # Handle the case where a non-dictionary value is encountered
            logger.error(f"Invalid path structure for {key_path} in {yaml_store}")
            return None

        # If new_value is provided, update the value
        if new_value is not None:
            # If this is a static file and we're trying to modify it, warn about this
            if yaml_store in self.STATIC_YAML_STORES:
                logger.warning(f"Attempting to modify static YAML store {yaml_store} at {key_path}")

            setting_container[keys[-1]] = new_value  # type: ignore[assignment]

            # Write changes back to the YAML file
            with yaml_path.open("w", encoding="utf-8") as yaml_file:
                yaml = ruamel.yaml.YAML()
                yaml.indent(offset=2)
                yaml.width = 300
                yaml.dump(data, yaml_file)

            # Update the cache
            self.cache[yaml_path] = data

            # Clear any cached results for this path
            if cache_key in self.settings_cache:
                del self.settings_cache[cache_key]

            return new_value

        # Traverse YAML structure to get value
        setting_value = setting_container.get(keys[-1])
        if setting_value is None and keys[-1] not in SETTINGS_IGNORE_NONE:
            print(f"❌ ERROR (yaml_settings) : Trying to grab a None value for : '{key_path}'")

        # Cache the result for static stores
        if yaml_store in self.STATIC_YAML_STORES:
            self.settings_cache[cache_key] = setting_value

        return setting_value  # type: ignore[return-value]


def yaml_settings[T](_type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
    """
    Retrieve or update a setting from a YAML store.

    Args:
        _type (type[T]): The expected type of the setting.
        yaml_store (YAML): The YAML store object to retrieve the setting from.
        key_path (str): The key path to the setting in the YAML store.
        new_value (T | None, optional): The new value to set for the setting. Defaults to None.

    Returns:
        T | None: The retrieved setting value, or None if the setting is not found or if the type is Path and the setting is not a string.

    Raises:
        TypeError: If the yaml_cache is not initialized.
    """
    if yaml_cache is None:
        raise TypeError("CMain not initialized")
    setting = yaml_cache.get_setting(_type, yaml_store, key_path, new_value)
    if _type is Path:
        return Path(setting) if setting and isinstance(setting, str) else None  # type: ignore[return-value]
    return setting


def classic_settings[T](_type: type[T], setting: str) -> T | None:
    """
    Retrieves a specific setting from the "CLASSIC Settings.yaml" file.
    If the settings file does not exist, it creates one using default settings
    from "CLASSIC_Info.default_settings".
    Args:
        _type (type[T]): The expected type of the setting value.
        setting (str): The key of the setting to retrieve.
    Returns:
        T | None: The value of the setting if found and correctly typed, otherwise None.
    Raises:
        ValueError: If the default settings are invalid.
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
    """
    Generate `CLASSIC Ignore.yaml` and `CLASSIC Data/CLASSIC <GAME> Local.yaml` files if they do not exist.
    This function checks for the existence of the `CLASSIC Ignore.yaml` file and the
    `CLASSIC Data/CLASSIC <GAME> Local.yaml` file. If either file does not exist, it creates
    the file with default content retrieved from the YAML settings.
    Raises:
        TypeError: If the default content retrieved from the YAML settings is not a string.
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
    Attempts to parse a version string into a Version object.

    Args:
        version_string (str): The version string to parse.

    Returns:
        Version | None: A Version object if the parsing is successful,
                        otherwise None if the version string is invalid.
    """
    try:
        return Version(version_string)
    except InvalidVersion:
        return None


async def get_github_version(session: aiohttp.ClientSession) -> Version | None:
    """Check the latest CLASSIC version on GitHub.

    Args:
        session (aiohttp.ClientSession): The aiohttp session to use for the request.

    Returns:
        Version | None: The latest version of CLASSIC if successful, otherwise None.
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
    Check the latest CLASSIC version on Nexus Mods.
    Args:
        session (aiohttp.ClientSession): The aiohttp client session to use for making the HTTP request.
    Returns:
        Version | None: The Version on the mod page if successful, otherwise None if the check fails or the HTML structure has changed.
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
    Check if the CLASSIC mod is the latest version by querying GitHub and Nexus Mods.
    This function checks for newer versions of the CLASSIC mod based on the settings provided in the CLASSIC Settings.yaml file.
    It can query both GitHub and Nexus Mods for the latest version information.
    Args:
        quiet (bool): If True, suppresses print statements. Defaults to False.
        gui_request (bool): If True, indicates that the request is coming from a GUI, which may handle exceptions differently. Defaults to True.
    Returns:
        bool: Returns True if CLASSIC is already the latest version, False otherwise.
    Raises:
        UpdateCheckError: If there is an error checking for updates or if the local version is outdated and the request is from a GUI.
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
    no_data: set[None | Version] = {None, NULL_VERSION}
    try:
        async with aiohttp.ClientSession(raise_for_status=True) as session:
            version_github = await get_github_version(session) if use_github else NULL_VERSION
            version_nexus = await get_nexus_version(session) if use_nexus else NULL_VERSION
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
    version_local = try_parse_version(classic_local.rsplit(maxsplit=1)[-1]) if classic_local else NULL_VERSION

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
def docs_path_find() -> None:
    """
    Checks and sets the path to the game's documents folder based on the operating system and user settings.
    This function performs the following steps:
    1. Retrieves the document name from YAML settings.
    2. Defines nested functions to get the documents path for Windows, Linux, and manual input:
        - `get_windows_docs_path`: Retrieves the path from the Windows registry or defaults to the user's Documents folder.
        - `get_linux_docs_path`: Retrieves the path from Steam library folders configuration.
        - `get_manual_docs_path`: Prompts the user to manually enter the path.
    3. Checks if the game documents folder path is already set in YAML settings.
    4. If the path is not set, it determines the operating system and calls the appropriate nested function.
    5. If the path is set but invalid, it prompts the user to manually enter the path or uses a GUI if available.
    Raises:
        TypeError: If the Steam ID is not an integer or if the GUI mode is enabled but not initialized.
    """
    logger.debug("- - - INITIATED DOCS PATH CHECK")

    # Retrieve the document name from YAML settings
    docs_name = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.Main_Docs_Name")
    if not isinstance(docs_name, str):
        docs_name = gamevars["game"]

    
    def get_windows_docs_path() -> None:
        """
        Retrieves the path to the user's Documents folder on a Windows system.
        This function attempts to read the path from the Windows registry. If the registry key is not found,
        it falls back to the default Documents path in the user's home directory. The function then constructs
        the full path to the game's documents folder and updates the YAML settings with this path.
        Raises:
            OSError: If there is an error accessing the registry.
            UnboundLocalError: If the registry key is not found.
        Returns:
            None
        """
        try:
            # Open the registry key to get the user's documents path
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:  # pyright: ignore[reportPossiblyUnboundVariable]
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
        Retrieves the path to the My Documents folder for a game running on Linux through Steam.
        This function reads the Steam library folders configuration file to find the path to the
        game's compatibility data directory. It then constructs the path to the My Documents folder
        within that directory and updates the YAML settings with this path.
        Raises:
            TypeError: If the retrieved Steam ID is not an integer.
        Updates:
            YAML settings with the path to the My Documents folder for the game.
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
        Prompts the user to enter the full directory path where a specific .ini file is located.
        The function continuously prompts the user until a valid directory path is provided.
        Once a valid path is entered, it prints a confirmation message and updates the CLASSIC Settings.yaml file with the provided path.
        Returns:
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
    Processes the given path to locate and validate the manual documentation files for the game.
    Args:
        path (str): The directory path where the manual documentation files are expected to be found.
    Raises:
        TypeError: If the manual_docs_gui is not initialized.
    Behavior:
        - Strips any leading or trailing whitespace from the provided path.
        - Checks if the path is a valid directory.
        - Searches recursively within the directory for an .ini file matching the game's name.
        - If found, updates the CLASSIC Settings.yaml with the path.
        - Emits a signal if no matching .ini file is found or if the path is invalid.
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
    Generates and sets various documentation paths in the YAML settings.
    This function retrieves the XSE acronym and base acronym from the YAML settings,
    constructs the documentation path, and updates the YAML settings with paths for
    various documentation files including the XSE log, Papyrus log, and Wrye Bash PC log.
    Raises:
        TypeError: If any of the retrieved YAML settings are not of type str.
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
    Checks and sets the game installation path for CLASSIC Fallout 4.
    This function attempts to find the game installation path by:
    1. Checking the Windows registry for the installation path.
    2. Verifying the existence of the game executable in the found path.
    3. If the registry check fails, it looks for a log file in the game documents folder.
    4. If the log file is found, it extracts the game path from the log.
    5. If all automated checks fail, it prompts the user to manually input the game path.
    The function updates the CLASSIC settings with the found or provided game path.
    Raises:
        TypeError: If the expected types for certain variables are not met.
        TypeError: If the GUI mode is enabled but the game path GUI is not initialized.
    """
    logger.debug("- - - INITIATED GAME PATH CHECK")

    path: str | None
    game_path: Path | None

    try:
        # Open the registry key
        reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Bethesda Softworks\{gamevars["game"]}{gamevars["vr"]}")  # pyright: ignore[reportPossiblyUnboundVariable]
        # Query the 'installed path' value
        path, _ = winreg.QueryValueEx(reg_key, "installed path")  # pyright: ignore[reportPossiblyUnboundVariable]
        winreg.CloseKey(reg_key)  # pyright: ignore[reportPossiblyUnboundVariable]
    except FileNotFoundError:
        try:
            reg_key_gog = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\GOG.com\Games\1998527297")  # pyright: ignore[reportPossiblyUnboundVariable]
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
    Generates and sets various game paths in the YAML settings based on the game version and type.
    This function retrieves the root game path and XSE acronym from the YAML settings, validates them,
    and then sets several other paths related to game data, scripts, plugins, and executable files.
    It also handles specific cases for different game versions and VR settings.
    Raises:
        TypeError: If the retrieved game path or XSE acronym is not a string.
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
            if (not game_version or game_version not in FO4_VERSIONS) and game_version != NULL_VERSION:
                raise ValueError("Unsupported or invalid game version")
            if game_version in (OG_VERSION, NULL_VERSION):
                yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_AddressLib",
                              fr"{game_path}\Data\{xse_acronym_base}\plugins\version-1-10-163-0.bin")
            elif game_version == NG_VERSION:
                yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_AddressLib",
                              fr"{game_path}\Data\{xse_acronym_base}\plugins\version-1-10-984-0.bin")
        case "Fallout4" if gamevars["vr"]:
            yaml_settings(str, YAML.Game_Local, "GameVR_Info.Game_File_AddressLib",
                          fr"{game_path}\Data\{xse_acronym_base}\plugins\version-1-2-72-0.csv")


# =========== CHECK GAME EXE FILE -> GET PATH AND HASHES ===========
# noinspection DuplicatedCode
def game_check_integrity() -> str:
    """
    Checks the integrity of the game installation by verifying the hash of the game executable
    and the presence of specific files. It compares the local hash with the expected hash stored
    in the YAML configuration and provides messages regarding the integrity and installation path
    of the game.
    Returns:
        str: A concatenated string of messages indicating the status of the game integrity check.
    Raises:
        TypeError: If any of the expected YAML settings are not of the correct type.
    """
    message_list = []
    logger.debug("- - - INITIATED GAME INTEGRITY CHECK")

    steam_ini_local = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Game_File_SteamINI")
    exe_hash_old = yaml_settings(str, YAML.Game, "Game_Info.EXE_HashedOLD") # The VR check is not needed here.
    exe_hash_new = yaml_settings(str, YAML.Game, "Game_Info.EXE_HashedNEW") # ...or here. VR hashes are not available at this time.
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
    Checks the integrity of the Script Extender (XSE) installation and logs any issues found.
    This function performs the following checks:
    1. Verifies the presence and validity of the Address Library file.
    2. Checks if the XSE log file exists and reads its contents.
    3. Compares the version in the log file with the latest version.
    4. Searches the log file for any errors specified in the settings.
    Returns:
        str: A message detailing the results of the integrity check, including any errors or warnings found.
    Raises:
        TypeError: If any of the settings values are of incorrect type.
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
    Checks the hashes of Script Extender (XSE) files against expected values and returns a message indicating the status.
    This function performs the following steps:
    1. Initializes a list to store messages and logs the initiation of the hash check.
    2. Retrieves the expected hashes of XSE scripts and the path to the game folder scripts from YAML settings.
    3. Computes the hashes of the local XSE scripts found in the game folder.
    4. Compares the computed hashes with the expected hashes and appends appropriate messages to the message list.
    5. Checks for missing or mismatched scripts and appends warning messages from YAML settings if necessary.
    6. Returns a concatenated string of all messages.
    Returns:
        str: A concatenated string of messages indicating the status of the XSE file hash check.
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
    Checks the folder path for the game documentation and returns any warnings if applicable.

    This function retrieves the documentation folder name from the YAML settings. If the folder name
    contains "onedrive" (case-insensitive), it appends a warning message to the message list.

    Returns:
        str: A concatenated string of warning messages, if any.

    Raises:
        TypeError: If the retrieved documentation name or warning message is not a string.
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
    Checks the integrity of a specified INI file and ensures necessary settings are enabled.
    Args:
        ini_name (str): The name of the INI file to check.
    Returns:
        str: A message detailing the results of the INI file check.
    Raises:
        TypeError: If the `docs_name` or `folder_docs` is not a string or None.
        PermissionError: If the INI file is set to read-only and cannot be modified.
        configparser.MissingSectionHeaderError: If the INI file is missing section headers.
        configparser.ParsingError: If there is an error parsing the INI file.
        ValueError: If there is a value error while processing the INI file.
        OSError: If there is an OS-related error while processing the INI file.
        configparser.DuplicateOptionError: If the INI file contains duplicate options.
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
    Backs up game files to a specified directory based on the current XSE version.
    This function reads the backup list, game path, XSE log file, and the latest XSE version
    from a YAML configuration. It then reads the XSE log file to determine the current XSE version.
    If a backup directory for the current XSE version does not exist, it creates one. It then
    copies game files to the backup directory if they are listed in the backup list and do not
    already exist in the backup directory.
    Raises:
        TypeError: If the types of the configuration values are not as expected.
        FileNotFoundError: If the XSE log file is not found.
    Notes:
        - The function assumes that the YAML configuration and the `open_file_with_encoding` function
          are defined elsewhere in the codebase.
        - The function uses `shutil.copy2` to preserve file metadata during the copy process.
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
    Combines the results of various integrity checks into a single string.

    This function performs the following checks:
    - Game integrity check
    - XSE integrity check
    - XSE hashes check
    - Documentation folder check
    - INI file checks for game, game custom, and game preferences

    Returns:
        str: A concatenated string of the results from all the checks.
    """
    combined_return = [game_check_integrity(), xse_check_integrity(), xse_check_hashes(), docs_check_folder(),
                       docs_check_ini(f"{gamevars["game"]}.ini"), docs_check_ini(f"{gamevars["game"]}Custom.ini"),
                       docs_check_ini(f"{gamevars["game"]}Prefs.ini")]
    return "".join(combined_return)


def main_generate_required() -> None:
    """
    Main function to generate required settings and paths for the CLASSIC tool.
    This function performs the following tasks:
    1. Configures logging.
    2. Generates necessary files for CLASSIC.
    3. Retrieves the CLASSIC version and game name from YAML settings.
    4. Prints initial setup messages and reminders.
    5. Logs the start of the process.
    6. Retrieves the game path from YAML settings.
    7. If the game path is not found, it attempts to find and generate paths for documents and the game.
    8. If the game path is found, it performs a backup of main files.
    9. Prints a completion message indicating that all checks have been performed.
    Raises:
        TypeError: If the CLASSIC version or game name is not a string.
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
    Initialize the application settings and GUI components.
    
    Pre-loads static YAML files for better performance.
    
    Args:
        is_gui (bool): A flag indicating whether the GUI mode is enabled.
                       Defaults to False.
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
    initialize()
    main_generate_required()
    os.system("pause")
