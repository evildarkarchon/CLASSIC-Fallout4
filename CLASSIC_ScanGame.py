import configparser
import hashlib
import io
import os
import shutil
import struct
import subprocess
from collections.abc import ItemsView
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

import chardet
import iniparse
import tomlkit
from bs4 import BeautifulSoup
from packaging.version import Version  # noqa: TC002

try:
    from bs4 import PageElement
except ImportError:
    from bs4.element import PageElement  # noqa: TC002

import CLASSIC_Main as CMain
import ClassicLib.Constants as Constants

# For comparing results across runs.
# Skips moving/editing files; outputs to 'CLASSIC GFS Report.md' instead of console.
TEST_MODE = False


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculates the SHA-256 hash of a file's contents.

    This function reads the contents of a file in binary mode in chunks of 4096
    bytes and computes its SHA-256 hash incrementally. It returns the final
    hash value as a hexadecimal string representation.

    Args:
        file_path: Path object representing the location of the file whose
            hash needs to be computed.

    Returns:
        str: The hexadecimal SHA-256 hash of the file's contents.
    """
    hash_sha256 = hashlib.sha256()
    with file_path.open("rb") as file:
        for block in iter(lambda: file.read(4096), b""):
            hash_sha256.update(block)
    return hash_sha256.hexdigest()


def calculate_similarity(file1: Path, file2: Path) -> float:
    """
    Compares the content of two files and calculates the similarity ratio based
    on their sequences. The similarity ratio is a floating-point number between
    0 and 1, where 0 indicates no similarity and 1 indicates identical content.

    Args:
        file1 (Path): The path to the first file to be compared.
        file2 (Path): The path to the second file to be compared.

    Returns:
        float: A similarity ratio between 0 and 1, indicating the degree of
        similarity between the content of the two files.
    """
    with file1.open("r") as f1, file2.open("r") as f2:
        return SequenceMatcher(None, f1.read(), f2.read()).ratio()


def compare_ini_files(file1: Path, file2: Path) -> bool:
    """
    Compares two INI files to determine if they have identical sections and content.

    This function verifies if both input files have a ".ini" extension, reads their
    contents using the `configparser` library, and compares their sections and
    values to check for equality. If the files have non-matching extensions, the
    function immediately returns False.

    Args:
        file1 (Path): The path of the first INI file to compare.
        file2 (Path): The path of the second INI file to compare.

    Returns:
        bool: True if both INI files have identical sections and content,
        False otherwise.
    """
    if file1.suffix == ".ini" and file2.suffix == ".ini":
        config1, config2 = configparser.ConfigParser(), configparser.ConfigParser()
        config1.read(file1)
        config2.read(file2)
        return config1.sections() == config2.sections() and all(
            config1[section] == config2[section] for section in config1.sections()
        )
    return False


# ================================================
# DEFINE MAIN FILE / YAML FUNCTIONS
# ================================================
class ConfigFile(TypedDict):
    """
    A TypedDict for defining the configuration file structure in a strongly-typed
    manner.

    This class is used to ensure type safety and clear structure when dealing
    with configuration-related data.

    Attributes:
        encoding (str): The text encoding used for the configuration file.
        path (Path): The file path for the configuration file.
        settings (iniparse.ConfigParser): The configuration parser object
            containing settings parsed from the config file.
        text (str): The raw text content of the configuration file.
    """
    encoding: str
    path: Path
    settings: iniparse.ConfigParser
    text: str


class ConfigFileCache:
    _config_files: dict[str, Path]
    _config_file_cache: dict[str, ConfigFile]
    duplicate_files: dict[str, list[Path]]
    _game_root_path: Path | None
    _duplicate_whitelist: list[str]

    # noinspection PyUnresolvedReferences
    def __init__(self) -> None:
        """
        Initializes and scans the game's root directory for configuration files, identifying duplicates based on
        file hash, similarity, and specific comparison rules.

        The initialization sets up paths and attributes necessary for the operation, loads configuration
        files from the specified game root folder, and identifies duplicates by comparing hashed content,
        similarity thresholds, file properties, and specific configuration file comparison methods.

        Attributes:
            _config_files (dict): A dictionary that maps lowercase filenames to their corresponding file paths.
            _config_file_cache (dict): A dictionary reserved for caching file-related data, left unpopulated.
            duplicate_files (dict): A dictionary mapping lowercase filenames to lists of file paths that are
                considered duplicate or similar based on the comparison logic.
            _duplicate_whitelist (list): A list of strings that defines prefixes or terms of interest for
                filtering directories and filenames when scanning for configuration files.
            _game_root_path (Path): The root path of the game's directory, which is loaded from specific
                YAML settings and verified for presence; raises FileNotFoundError if the path cannot be loaded.

        Raises:
            FileNotFoundError: Raised if the game's root directory is not found or fails to be resolved via
                the YAML settings.

        Notes:
            - Configuration file scanning and duplicate identification rely on file extensions
              (.ini, .conf, dxvk.conf) and specific file name matching conditions.
            - Files are compared based on content hash, similarity threshold (≥90%), and additional
              heuristic checks such as file size, modification time, or a detailed INI file comparison.
            - The duplicate detection logic is case-insensitive for filenames.

        Todo:
            - Determine if a specific exception should be raised or a message returned when the game's
              root path is missing (observed in scan_mod_inis).
        """
        self._config_files = {}
        self._config_file_cache = {}
        self.duplicate_files = {}
        self._duplicate_whitelist = ["F4EE"]

        self._game_root_path = CMain.yaml_settings(Path, CMain.YAML.Game_Local,
                                                   f"Game{CMain.gamevars['vr']}_Info.Root_Folder_Game")
        if self._game_root_path is None:
            # TODO: Check if this needs to raise or return an error message instead. (See also: TODO in scan_mod_inis)
            raise FileNotFoundError

        for path, _dirs, files in self._game_root_path.walk():
            for file in files:
                # Skip if _dirs do not intersect with the whitelist or no match in file name
                if not (set(self._duplicate_whitelist) & set(_dirs)) and not any(
                        whitelist in file for whitelist in self._duplicate_whitelist):
                    continue

                file_lower = file.lower()
                # Skip non-config files and files not matching specific criteria
                if not file_lower.endswith((".ini", ".conf")) and file_lower != "dxvk.conf":
                    continue

                file_path = path / file
                file_hash = calculate_file_hash(file_path)

                # Check for duplicates already stored
                if file_lower in self._config_files:
                    existing_file = self._config_files[file_lower]
                    existing_hash = calculate_file_hash(existing_file)

                    if file_hash == existing_hash:  # Exact duplicate
                        self.duplicate_files.setdefault(file_lower, [existing_file]).append(file_path)
                    else:  # Compare for similarity
                        is_similar = (
                                calculate_similarity(existing_file, file_path) >= 0.90
                                or (
                                        file_path.stat().st_size == existing_file.stat().st_size and file_path.stat().st_mtime == existing_file.stat().st_mtime)
                                or compare_ini_files(existing_file, file_path)
                        )
                        if is_similar:
                            self.duplicate_files.setdefault(file_lower, [existing_file]).append(file_path)
                else:
                    # Register new config file
                    self._config_files[file_lower] = file_path

    def __contains__(self, file_name_lower: str) -> bool:
        """
        Checks if a given file name is in the configuration files.

        This method determines if a specific file name is present within the
        internal collection of configuration files. The check is case-sensitive
        and depends on the provided file name's exact match with entries in
        the configuration files.

        Args:
            file_name_lower: The name of the file (in lowercase) that is
                being checked for presence in the configuration files.

        Returns:
            bool: True if the file name exists in the configuration files,
                False otherwise.
        """
        return file_name_lower in self._config_files

    # TODO: Useful for checking how many INIs found
    # def __bool__(self) -> bool:
    #     return bool(self._config_files)

    # def __len__(self) -> int:
    #     return len(self._config_files)

    def __getitem__(self, file_name_lower: str) -> Path:
        """
        Retrieves the file path associated with the given lowercase file name key.

        Args:
            file_name_lower (str): The lowercase string of the file name to look up in the
                configuration files mapping.

        Returns:
            Path: The file path corresponding to the given lowercase file name key.
        """
        return self._config_files[file_name_lower]

    def _load_config(self, file_name_lower: str) -> None:
        """
        Loads and parses a configuration file, caching its contents. If the file has
        already been loaded and cached, the cache will be invalidated and reloaded.
        The method ensures the file exists in the configuration mapping before
        processing.

        Args:
            file_name_lower (str): The lowercase name of the configuration file to be
                loaded. Must correspond to a key in the internal `_config_files`
                mapping.

        Raises:
            FileNotFoundError: If the specified `file_name_lower` does not exist in
                the `_config_files` mapping.
        """
        if file_name_lower not in self._config_files:
            raise FileNotFoundError

        if file_name_lower in self._config_file_cache:
            # Delete the cache and reload the file
            del self._config_file_cache[file_name_lower]

        file_path = self._config_files[file_name_lower]
        file_bytes = file_path.read_bytes()
        file_encoding = chardet.detect(file_bytes)["encoding"] or "utf-8"
        file_text = file_bytes.decode(file_encoding)
        config = iniparse.ConfigParser()
        config.readfp(io.StringIO(file_text, newline=None))

        self._config_file_cache[file_name_lower] = {
            "encoding": file_encoding,
            "path": file_path,
            "settings": config,
            "text": file_text,
        }

    def get[T](self, value_type: type[T], file_name_lower: str, section: str, setting: str) -> T | None:
        """
        Retrieves a configuration value of the specified type from a configuration file. The method
        accesses the given configuration section and retrieves the value associated with the provided key.

        Args:
            value_type: The expected data type of the configuration value. Must be one of: str, bool,
                int, or float. Raises NotImplementedError for unsupported types.
            file_name_lower: The file name of the configuration file, in lowercase. This is used to
                identify the configuration file in the cache.
            section: The section of the configuration file where the desired setting is located.
            setting: The key of the desired configuration value within the specified section.

        Returns:
            The value of the requested configuration key, cast to the specified type. Returns None if the
            configuration file is not found, the requested section or key does not exist, or the value
            cannot be retrieved or cast to the specified type.
        """
        if value_type is not str and value_type is not bool and value_type is not int and value_type is not float:
            raise NotImplementedError

        if file_name_lower not in self._config_files:
            return None

        if file_name_lower not in self._config_file_cache:
            try:
                self._load_config(file_name_lower)
            except FileNotFoundError:
                CMain.logger.error(f"ERROR: Config file not found - {file_name_lower}")
                return None

        config = self._config_file_cache[file_name_lower]["settings"]

        if not config.has_section(section):
            CMain.logger.error(f"ERROR: Section '{section}' does not exist in '{self._config_files[file_name_lower]}'")
            return None

        if not config.has_option(section, setting):
            CMain.logger.error(
                f"ERROR: Key '{setting}' does not exist in section '{section}' of '{self._config_files[file_name_lower]}'")
            return None

        try:
            if value_type is str:
                return config.get(section, setting)
            if value_type is bool:
                return config.getboolean(section, setting)  # type: ignore[no-any-return]
            if value_type is int:
                return config.getint(section, setting)  # type: ignore[no-any-return]
            if value_type is float:
                return config.getfloat(section, setting)  # type: ignore[no-any-return]
            raise NotImplementedError
        except ValueError as e:
            CMain.logger.error(f"ERROR: Unexpected value type - {e}")
            return None
        except (configparser.NoSectionError, configparser.NoOptionError):
            return None

    def get_strict[T](self, value_type: type[T], file: str, section: str, setting: str) -> T:
        """
        Fetches a configuration value with a strict fallback mechanism. If the value is not found, returns
        a default value based on the specified type. Default values are as follows:

        - str: An empty string.
        - bool: False.
        - int: 0.
        - float: 0.0.

        If the type is unhandled, a `NotImplementedError` will be raised.

        This method is generic and enforces type consistency for the returned value matching `value_type`.

        Args:
            value_type: The type of the expected configuration value. Determines the fallback value
                if the specified configuration is not found.
            file: The name of the configuration file where the setting is to be retrieved from.
            section: The section inside the configuration file containing the desired setting.
            setting: The specific key for the value that needs to be fetched.

        Returns:
            The fetched configuration value if it exists. If the value does not exist, returns a default
            value determined by `value_type`.

        Raises:
            NotImplementedError: If `value_type` is not handled for default fallback values.
        """
        value = self.get(value_type, file, section, setting)
        if value is not None:
            return value
        if value_type is str:
            return ""  # type: ignore[return-value]
        if value_type is bool:
            return False  # type: ignore[return-value]
        if value_type is int:
            return 0  # type: ignore[return-value]
        if value_type is float:
            return 0.0  # type: ignore[return-value]
        raise NotImplementedError

    def set[T](self, value_type: type[T], file_name_lower: str, section: str, setting: str, value: T) -> None:
        """
        Sets a configuration value in a specified section and setting with a given type, and writes it to
        the corresponding configuration file.

        Processes the configuration value based on its type, checks the existence of the configuration
        file in cache or loads it if not present, and updates or adds a new setting within the
        specified section of the configuration. The updated configuration is saved unless the system
        is in test mode.

        Args:
            value_type: The type of the value to be set. It must be one of the supported types:
                str, bool, int, or float.
            file_name_lower: The lowercased name of the configuration file to be updated.
            section: The name of the configuration section where the setting resides.
            setting: The specific setting to be updated or added within the section.
            value: The value to set for the specified setting. The type of the value must correspond
                to the provided value_type.

        Raises:
            NotImplementedError: If the provided value_type is not one of the supported types.
        """
        if value_type is not str and value_type is not bool and value_type is not int and value_type is not float:
            raise NotImplementedError

        if file_name_lower not in self._config_file_cache:
            try:
                self._load_config(file_name_lower)
            except FileNotFoundError:
                CMain.logger.error(f"ERROR: Config file not found - {file_name_lower}")
                return

        cache = self._config_file_cache[file_name_lower]
        config = cache["settings"]
        value = ("true" if value else "false") if value_type is bool else str(value)  # type: ignore[assignment]
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, setting, value)

        if not TEST_MODE:
            with cache["path"].open("w", encoding=cache["encoding"], newline="") as f:
                config.write(f)

    def has(self, file_name_lower: str, section: str, setting: str) -> bool:
        """
        Determines if a given setting exists under a specific section in the configuration
        file specified by its lower-cased file name. It checks the cache for previously
        loaded configurations and loads the file if not already cached.

        Args:
            file_name_lower (str): The lower-cased name of the configuration file to check.
            section (str): The section in the configuration file to look for.
            setting (str): The setting within the specified section to verify existence.

        Returns:
            bool: True if the setting exists in the specified section of the configuration
            file; otherwise, False.
        """
        if file_name_lower not in self._config_files:
            return False
        try:
            if file_name_lower not in self._config_file_cache:
                self._load_config(file_name_lower)
            config = self._config_file_cache[file_name_lower]["settings"]
            return config.has_option(section, setting)
        except (FileNotFoundError, configparser.NoSectionError):
            return False

    def items(self) -> ItemsView[str, Path]:
        """
        Returns the items from the internal configuration files dictionary.

        This method provides access to the key-value pairs stored in the
        configuration files dictionary. It can be used to iterate over or
        inspect the directory path mappings associated with their keys.

        Returns:
            ItemsView[str, Path]: A view object that displays a list of
            dictionary's key-value tuple pairs. Keys are of type `str` and
            represent names or identifiers, while values are of type `Path`
            and represent corresponding directory or file paths.
        """
        return self._config_files.items()


def mod_toml_config(toml_path: Path, section: str, key: str, new_value: str | bool | int | None = None) -> Any | None:
    """
    Modifies a specific key in a TOML configuration file within a specified section if the key exists.
    If a new value is provided, the function updates the key with the given value. The current value
    of the key is returned, whether updated or not. If the specified section or key does not exist,
    the function returns None. The function handles file encoding and ensures the integrity of the
    TOML’s structure during modifications.

    Args:
        toml_path (Path): Path to the TOML file to be modified.
        section (str): Section in the TOML file where the key resides.
        key (str): Key within the section to modify or retrieve.
        new_value (str | bool | int | None, optional): New value to assign to the key. If None, no
            update is applied, and the current value is retrieved. Defaults to None.

    Returns:
        Any | None: The current value of the key (either the existing or updated value if changed).
        Returns None if the specified section or key does not exist.
    """

    file_bytes = toml_path.read_bytes()
    file_encoding = chardet.detect(file_bytes)["encoding"] or "utf-8"
    file_text = file_bytes.decode(file_encoding)
    data = tomlkit.parse(file_text)

    if section not in data or key not in data[section]:  # pyright: ignore[reportOperatorIssue]
        return None
    current_value = data[section][key]  # pyright: ignore[reportIndexIssue]

    # If a new value is provided, update the key
    if new_value is not None:
        current_value = new_value
        data[section][key] = new_value  # pyright: ignore[reportIndexIssue]
        if not TEST_MODE:
            with toml_path.open("w", encoding=file_encoding, newline="") as toml_file:
                toml_file.write(data.as_string())
    return current_value


# ================================================
# CHECK BUFFOUT CONFIG SETTINGS
# ================================================
def check_crashgen_settings() -> str:
    """
    Checks and validates the settings for Crash Generator (CRASHGEN) based on the configuration
    files and the presence of certain plugins or mods in the system.

    This function performs the following checks:
    - Ensures the appropriate CRASHGEN configuration file exists and is being used.
    - Verifies the plugins directory for specific installed mods or DLL files.
    - Evaluates patch and compatibility settings in the CRASHGEN configuration file based
      on detected plugins or mods, and provides warnings or recommendations when
      configurations do not meet the desired conditions.

    Returns:
        str: A summary of any issues found, warnings, or necessary actions related to the
        CRASHGEN configuration and system setup.
    """
    message_list: list[str] = []

    # Get plugins path and ensure it's a Path object
    plugins_path = CMain.yaml_settings(Path, CMain.YAML.Game_Local,
                                       f"Game{CMain.gamevars['vr']}_Info.Game_Folder_Plugins")
    if plugins_path and not isinstance(plugins_path, Path):
        plugins_path = Path(cast("str", plugins_path))

    # Get crash generator name from settings
    crashgen_name_setting = CMain.yaml_settings(str, CMain.YAML.Game,
                                                f"Game{CMain.gamevars['vr']}_Info.CRASHGEN_LogName")
    crashgen_name = crashgen_name_setting if isinstance(crashgen_name_setting, str) else "Buffout4"

    # Define paths to possible config files
    crashgen_toml_og = plugins_path / "Buffout4/config.toml" if plugins_path else None
    crashgen_toml_vr = plugins_path / "Buffout4.toml" if plugins_path else None

    # Determine which config file to use
    crashgen_toml_main = None
    if crashgen_toml_og and crashgen_toml_og.is_file():
        crashgen_toml_main = crashgen_toml_og
    elif crashgen_toml_vr and crashgen_toml_vr.is_file():
        crashgen_toml_main = crashgen_toml_vr
    elif (crashgen_toml_og and not crashgen_toml_og.exists()) or (crashgen_toml_vr and not crashgen_toml_vr.exists()):
        message_list.extend((
            f"# ❌ CAUTION : {crashgen_name.upper()} TOML SETTINGS FILE NOT FOUND! #\n",
            f"Please recheck your {crashgen_name} installation and delete any obsolete files.\n-----\n",
        ))

    # Check if both versions of config exist and warn user
    if (crashgen_toml_og and crashgen_toml_og.is_file()) and (crashgen_toml_vr and crashgen_toml_vr.is_file()):
        message_list.extend((
            f"# ❌ CAUTION : BOTH VERSIONS OF {crashgen_name.upper()} TOML SETTINGS FILES WERE FOUND! #\n",
            f"When editing {crashgen_name} toml settings, make sure you are editing the correct file.\n",
            f"Please recheck your {crashgen_name} installation and delete any obsolete files.\n-----\n",
        ))

    # Check for installed mods by examining DLL files in the plugins directory
    xse_files: set[str] = set()
    if plugins_path and plugins_path.exists():
        try:
            xse_files = {file.name.lower() for file in plugins_path.iterdir()}
        except (PermissionError, OSError) as e:
            CMain.logger.error(f"Error accessing plugins directory: {e}")

    has_xcell = any(xcell_file in xse_files for xcell_file in ["x-cell-fo4.dll", "x-cell-og.dll", "x-cell-ng2.dll"])
    has_bakascrapheap = "bakascrapheap.dll" in xse_files
    has_achievements = any(
        ach_file in xse_files for ach_file in ["achievements.dll", "achievementsmodsenablerloader.dll"])
    has_looksmenu = any("f4ee" in file for file in xse_files)

    # If no config file found, return message without raising exception
    if not crashgen_toml_main:
        message_list.extend((
            f"# [!] NOTICE : Unable to find the {crashgen_name} config file, settings check will be skipped. #\n",
            f"  To ensure this check doesn't get skipped, {crashgen_name} has to be installed manually.\n",
            "  [ If you are using Mod Organizer 2, you need to run CLASSIC through a shortcut in MO2. ]\n-----\n",
        ))
        return "".join(message_list)

    CMain.logger.info(f"Checking {crashgen_name} settings in {crashgen_toml_main}")

    # Define configuration settings to check, with their requirements and desired states
    settings_to_check = [
        # Patches section settings
        {
            "section": "Patches",
            "key": "Achievements",
            "name": "Achievements",
            "condition": has_achievements,
            "desired_value": False,
            "description": "The Achievements Mod and/or Unlimited Survival Mode is installed",
            "reason": f"to prevent conflicts with {crashgen_name}",
        },
        {
            "section": "Patches",
            "key": "MemoryManager",
            "name": "Memory Manager",
            "condition": has_xcell,
            "desired_value": False,
            "description": "The X-Cell Mod is installed",
            "reason": "to prevent conflicts with X-Cell",
            "special_case": "bakascrapheap",
        },
        {
            "section": "Patches",
            "key": "HavokMemorySystem",
            "name": "Havok Memory System",
            "condition": has_xcell,
            "desired_value": False,
            "description": "The X-Cell Mod is installed",
            "reason": "to prevent conflicts with X-Cell",
        },
        {
            "section": "Patches",
            "key": "BSTextureStreamerLocalHeap",
            "name": "BS Texture Streamer Local Heap",
            "condition": has_xcell,
            "desired_value": False,
            "description": "The X-Cell Mod is installed",
            "reason": "to prevent conflicts with X-Cell",
        },
        {
            "section": "Patches",
            "key": "ScaleformAllocator",
            "name": "Scaleform Allocator",
            "condition": has_xcell,
            "desired_value": False,
            "description": "The X-Cell Mod is installed",
            "reason": "to prevent conflicts with X-Cell",
        },
        {
            "section": "Patches",
            "key": "SmallBlockAllocator",
            "name": "Small Block Allocator",
            "condition": has_xcell,
            "desired_value": False,
            "description": "The X-Cell Mod is installed",
            "reason": "to prevent conflicts with X-Cell",
        },
        {
            "section": "Patches",
            "key": "ArchiveLimit",
            "name": "Archive Limit",
            "condition": crashgen_toml_main == crashgen_toml_og,  # Always check this setting
            "desired_value": False,
            "description": "Archive Limit is enabled",
            "reason": "to prevent crashes",
        },
        {
            "section": "Patches",
            "name": "MaxStdIO",
            "key": "MaxStdIO",
            "condition": False,  # This is a placeholder, this may or may not be enabled in the future
            "desired_value": 2048,
            "description": "MaxStdIO is set to a low value",
            "reason": "to improve performance",
        },
        # Compatibility section settings
        {
            "section": "Compatibility",
            "key": "F4EE",
            "name": "F4EE (Looks Menu)",
            "condition": has_looksmenu,
            "desired_value": True,
            "description": "Looks Menu is installed, but F4EE parameter is set to FALSE",
            "reason": "to prevent bugs and crashes from Looks Menu",
        },
    ]

    # Process each setting
    for setting in settings_to_check:
        # Get current setting value
        current_value = mod_toml_config(crashgen_toml_main, cast("str", setting["section"]),
                                        cast("str", setting["key"]))

        # Special case for BakaScrapHeap with MemoryManager
        if setting.get("special_case") == "bakascrapheap" and has_bakascrapheap and current_value:
            message_list.extend((
                f"# ❌ CAUTION : The Baka ScrapHeap Mod is installed, but is redundant with {crashgen_name} #\n",
                f" FIX: Uninstall the Baka ScrapHeap Mod, this prevents conflicts with {crashgen_name}.\n-----\n",
            ))

            continue

        # Check if condition is met and setting needs changing
        if setting["condition"] and current_value != setting["desired_value"]:
            message_list.extend((
                f"# ❌ CAUTION : {setting['description']}, but {setting['name']} parameter is set to {current_value} #\n",
                f"    Auto Scanner will change this parameter to {setting['desired_value']} {setting['reason']}.\n-----\n",
            ))
            # Apply the change
            mod_toml_config(crashgen_toml_main, cast("str", setting["section"]), cast("str", setting["key"]),
                            cast("str | bool | int | None", setting["desired_value"]))
            CMain.logger.info(f"Changed {setting['name']} from {current_value} to {setting['desired_value']}")
        else:
            # Setting is already correctly configured
            message_list.append(
                f"✔️ {setting['name']} parameter is correctly configured in your {crashgen_name} settings!\n-----\n")

    return "".join(message_list)


# ================================================
# CHECK ERRORS IN LOG FILES FOR GIVEN FOLDER
# ================================================
def check_log_errors(folder_path: Path | str) -> str:
    """
    Inspects log files within a specified folder for recorded errors. Errors matching the provided
    catch criteria are highlighted, whereas those designated to be ignored in the settings or from
    specific files are omitted. The function aggregates error messages and provides a detailed
    report string containing relevant log error data.

    Args:
        folder_path (Path | str): Path to the folder containing log files for error inspection.

    Returns:
        str: A detailed report of all detected errors in the relevant log files, if any.
    """
    if isinstance(folder_path, str):
        folder_path = Path(folder_path)
    catch_errors_setting = CMain.yaml_settings(list[str], CMain.YAML.Main, "catch_log_errors")
    ignore_logs_list_setting = CMain.yaml_settings(list[str], CMain.YAML.Main, "exclude_log_files")
    ignore_logs_errors_setting = CMain.yaml_settings(list[str], CMain.YAML.Main, "exclude_log_errors")

    catch_errors = catch_errors_setting if isinstance(catch_errors_setting, list) else []
    catch_errors_lower = [item.lower() for item in catch_errors] if catch_errors else []
    ignore_logs_list = ignore_logs_list_setting if isinstance(ignore_logs_list_setting, list) else []
    ignore_logs_list_lower = [item.lower() for item in ignore_logs_list] if ignore_logs_list else []
    ignore_logs_errors = ignore_logs_errors_setting if isinstance(ignore_logs_errors_setting, list) else []
    ignore_logs_errors_lower = [item.lower() for item in ignore_logs_errors] if ignore_logs_errors else []
    message_list: list[str] = []

    valid_log_files = [file for file in folder_path.glob("*.log") if "crash-" not in file.name]
    for file in valid_log_files:
        if all(part not in str(file).lower() for part in ignore_logs_list_lower):
            try:
                with CMain.open_file_with_encoding(file) as log_file:
                    log_data = log_file.readlines()
                    log_data_lower = (line.lower() for line in log_data)
                    errors_list = [
                        f"ERROR > {line}"
                        for line in log_data_lower
                        if any(item in line for item in catch_errors_lower) and all(
                            elem not in line for elem in ignore_logs_errors_lower)
                    ]

                if errors_list:
                    message_list.extend((
                        "[!] CAUTION : THE FOLLOWING LOG FILE REPORTS ONE OR MORE ERRORS!\n",
                        "[ Errors do not necessarily mean that the mod is not working. ]\n",
                        f"\nLOG PATH > {file}\n",
                        *errors_list,
                        f"\n* TOTAL NUMBER OF DETECTED LOG ERRORS * : {len(errors_list)}\n",
                    ))

            except OSError:
                message_list.append(f"❌ ERROR : Unable to scan this log file :\n  {file}")
                CMain.logger.warning(f"> ! > DETECT LOG ERRORS > UNABLE TO SCAN : {file}")
                continue

    return "".join(message_list)


def check_xse_plugins() -> str:
    """
    Checks the plugins folder for the correct version of Address Library files needed for the game.

    This function verifies the existence and version of the Address Library files based on the game type
    and mode, such as Virtual Reality (VR) or Non-VR modes. It uses game configurations to locate the plugins
    path and checks for specific file versions in the directory. If the correct version exists, it notifies
    the user; otherwise, it raises alerts about potential mismatches or missing files. Links are provided
    for downloading the appropriate files if needed.

    Returns:
        str: A detailed message about the status of the Address Library files, including errors, warnings,
        or success notifications.
    """
    message_list: list[str] = []
    plugins_path = CMain.yaml_settings(Path, CMain.YAML.Game_Local,
                                       f"Game{CMain.gamevars['vr']}_Info.Game_Folder_Plugins")

    # Version information organized by game type
    version_info = {
        "VR": {
            "version": Constants.VR_VERSION,
            "filename": "version-1-2-72-0.csv",
            "description": "Virtual Reality (VR) version",
            "url": "https://www.nexusmods.com/fallout4/mods/64879?tab=files"
        },
        "OG": {
            "version": Constants.OG_VERSION,
            "filename": "version-1-10-163-0.bin",
            "description": "Non-VR (Regular) version",
            "url": "https://www.nexusmods.com/fallout4/mods/47327?tab=files"
        },
        "NG": {
            "version": Constants.NG_VERSION,
            "filename": "version-1-10-984-0.bin",
            "description": "Non-VR (New Game) version",
            "url": "https://www.nexusmods.com/fallout4/mods/47327?tab=files"
        }
    }

    game_version: Version = CMain.get_game_version(Path(
        cast("str", CMain.yaml_settings(str, CMain.YAML.Game_Local, f"Game{CMain.gamevars['vr']}_Info.Game_File_EXE"))))

    # Check if we can detect the game version
    if game_version == Constants.NULL_VERSION:
        message_list.extend((
            "❓ NOTICE : Unable to locate Address Library\n",
            "  If you have Address Library installed, please check the path in your settings.\n",
            "  If you don't have it installed, you can find it on the Nexus.\n",
            f"  Link: Regular: {version_info['OG']['url']} or VR: {version_info['VR']['url']}\n-----\n",
        ))
        return "".join(message_list)

    # Determine correct version based on game mode
    is_vr_mode = CMain.classic_settings(bool, "VR Mode")

    if is_vr_mode:
        correct_versions = [version_info["VR"]]
        wrong_versions = [version_info["OG"], version_info["NG"]]
    else:
        correct_versions = [version_info["OG"], version_info["NG"]]
        wrong_versions = [version_info["VR"]]

    # Check if plugins_path exists
    if not plugins_path:
        message_list.append("❌ ERROR: Could not locate plugins folder path in settings\n-----\n")
        return "".join(message_list)

    # Check if correct version(s) exist
    correct_version_exists = any(
        plugins_path.joinpath(cast("str", version["filename"])).exists() for version in correct_versions)
    wrong_version_exists = any(
        plugins_path.joinpath(cast("str", version["filename"])).exists() for version in wrong_versions)

    if correct_version_exists:
        message_list.append("✔️ You have the correct version of the Address Library file!\n-----\n")
    elif wrong_version_exists:
        message_list.extend((
            "❌ CAUTION: You have installed the wrong version of the Address Library file!\n",
            f"  Remove the current Address Library file and install the {correct_versions[0]['description']}.\n",
            f"  Link: {correct_versions[0]['url']}\n-----\n",
        ))
    else:
        message_list.extend((
            "❓ NOTICE: Address Library file not found\n",
            f"  Please install the {correct_versions[0]['description']} for proper functionality.\n",
            f"  Link: {correct_versions[0]['url']}\n-----\n",
        ))

    return "".join(message_list)


# ================================================
# PAPYRUS MONITORING / LOGGING
# ================================================
def papyrus_logging() -> tuple[str, int]:
    """
    Analyzes Papyrus log files, extracting various statistics and compiling a summary.

    This function reads a Papyrus log file, if available, and computes key data such
    as the total number of dumps, stacks, warnings, and errors present in the log.
    It also calculates the ratio of dumps to stacks. If the log file is not found,
    the function provides user guidance on enabling and locating Papyrus logging.

    Returns:
        tuple[str, int]: A tuple containing a formatted string with log analysis
        details and the total count of dumps extracted from the log.

    Raises:
        ValueError: If encoding detection fails or returns a None value from the
        chardet library when reading the log file's bytes.
    """
    message_list: list[str] = []
    papyrus_path = CMain.yaml_settings(Path, CMain.YAML.Game_Local,
                                       f"Game{CMain.gamevars['vr']}_Info.Docs_File_PapyrusLog")

    count_dumps = count_stacks = count_warnings = count_errors = 0
    if papyrus_path and papyrus_path.exists():
        papyrus_encoding = chardet.detect(papyrus_path.read_bytes())["encoding"]
        with papyrus_path.open(encoding=papyrus_encoding, errors="ignore") as papyrus_log:
            papyrus_data = papyrus_log.readlines()
        for line in papyrus_data:
            if "Dumping Stacks" in line:
                count_dumps += 1
            elif "Dumping Stack" in line:
                count_stacks += 1
            elif " warning: " in line:
                count_warnings += 1
            elif " error: " in line:
                count_errors += 1

        ratio = 0 if count_dumps == 0 else count_dumps / count_stacks

        message_list.extend((
            f"NUMBER OF DUMPS    : {count_dumps}\n",
            f"NUMBER OF STACKS   : {count_stacks}\n",
            f"DUMPS/STACKS RATIO : {round(ratio, 3)}\n",
            f"NUMBER OF WARNINGS : {count_warnings}\n",
            f"NUMBER OF ERRORS   : {count_errors}\n",
        ))
    else:
        message_list.extend((
            "[!] ERROR : UNABLE TO FIND *Papyrus.0.log* (LOGGING IS DISABLED OR YOU DIDN'T RUN THE GAME)\n",
            "ENABLE PAPYRUS LOGGING MANUALLY OR WITH BETHINI AND START THE GAME TO GENERATE THE LOG FILE\n",
            "BethINI Link | Use Manual Download : https://www.nexusmods.com/site/mods/631?tab=files\n",
        ))

    message_output = "".join(message_list)  # Debug print
    return message_output, count_dumps


# ================================================
# WRYE BASH - PLUGIN CHECKER
# ================================================
def scan_wryecheck() -> str:
    """
    Analyzes Wrye Bash plugin checker report and generates a detailed message containing plugin-related warnings,
    recommendations, and additional resources based on the report content and predefined settings.

    The function handles the presence or absence of the Wrye Bash plugin checker report (HTML file). When the report
    is found, its contents are parsed using BeautifulSoup to extract categorized plugin information and
    diagnostic messages. It integrates custom plugin warnings from predefined settings and formats the output for clarity.

    If the report is not found, it either provides a missing report warning or raises an error based on the YAML settings.

    Returns:
        str: A formatted multi-line string containing analysis and recommendations based on the Wrye Bash plugin
        checker report.
    """
    message_list: list[str] = []
    wrye_missinghtml_setting = CMain.yaml_settings(str, CMain.YAML.Game, "Warnings_MODS.Warn_WRYE_MissingHTML")
    wrye_plugincheck = CMain.yaml_settings(Path, CMain.YAML.Game_Local,
                                           f"Game{CMain.gamevars['vr']}_Info.Docs_File_WryeBashPC")
    wrye_warnings_setting = CMain.yaml_settings(dict[str, str], CMain.YAML.Main, "Warnings_WRYE")

    wrye_missinghtml = wrye_missinghtml_setting if isinstance(wrye_missinghtml_setting, str) else None
    wrye_warnings = wrye_warnings_setting if isinstance(wrye_warnings_setting, dict) else {}

    if wrye_plugincheck and wrye_plugincheck.is_file():
        message_list.extend((
            "\n✔️ WRYE BASH PLUGIN CHECKER REPORT WAS FOUND! ANALYZING CONTENTS...\n",
            f"  [This report is located in your Documents/My Games/{CMain.gamevars['game']} folder.]\n",
            "  [To hide this report, remove *ModChecker.html* from the same folder.]\n",
        ))
        with CMain.open_file_with_encoding(wrye_plugincheck) as WB_Check:
            wb_html = WB_Check.read()

        # Parse the HTML code using BeautifulSoup.
        soup = BeautifulSoup(wb_html, "html.parser")

        h3: PageElement
        for h3 in soup.find_all("h3"):  # Find all <h3> elems and loop through them.
            title = h3.get_text()  # Get title of current <h3> and create plugin list.
            plugin_list: list[str] = []

            for p in h3.find_next_siblings("p"):  # Find all <p> elements that come after current <h3> element.
                if p.find_previous_sibling(
                        "h3") == h3:  # Check if current <p> elem is under same <h3> elem as previous <p>.
                    text = p.get_text().strip().replace("•\xa0 ", "")
                    if any(ext in text for ext in
                           (".esp", ".esl", ".esm")):  # Get text of <p> elem and check plugin extensions.
                        plugin_list.append(text)
                else:  # If current <p> elem is under a different <h3> elem, break loop.
                    break
            # Format title and list of plugins.
            if title != "Active Plugins:":
                if len(title) < 32:
                    diff = 32 - len(title)
                    left = diff // 2
                    right = diff - left
                    message_list.append(f"\n   {'=' * left} {title} {'=' * right}\n")
                else:
                    message_list.append(title)

            if title == "ESL Capable":
                message_list.extend((
                    f"❓ There are {len(plugin_list)} plugins that can be given the ESL flag. This can be done with\n",
                    "  the SimpleESLify script to avoid reaching the plugin limit (254 esm/esp).\n",
                    "  SimpleESLify: https://www.nexusmods.com/skyrimspecialedition/mods/27568\n  -----\n",
                ))

            message_list.extend([warn_desc for warn_name, warn_desc in wrye_warnings.items() if warn_name in title])

            if title not in {"ESL Capable", "Active Plugins:"}:
                message_list.extend([f"    > {elem}\n" for elem in plugin_list])

        message_list.extend((
            "\n❔ For more info about the above detected problems, see the WB Advanced Readme\n",
            "  For more details about solutions, read the Advanced Troubleshooting Article\n",
            "  Advanced Troubleshooting: https://www.nexusmods.com/fallout4/articles/4141\n",
            "  Wrye Bash Advanced Readme Documentation: https://wrye-bash.github.io/docs/\n",
            "  [ After resolving any problems, run Plugin Checker in Wrye Bash again! ]\n\n",
        ))
    elif wrye_missinghtml is not None:
        message_list.append(wrye_missinghtml)
    else:
        raise ValueError("ERROR: Warnings_WRYE missing from the database!")

    return "".join(message_list)


# ================================================
# CHECK MOD INI FILES
# ================================================
def scan_mod_inis() -> str:
    """
    Check INI files for mods and perform necessary fixes or notify about potential issues.

    This function analyzes INI configuration files associated with a game, looking for specific settings or
    conditions that can potentially impact game performance, startup time, or user settings. If specific
    conditions or discrepancies are found, it performs updates to the INI files, logs the changes, and collects
    notices for the user. The function also identifies duplicate INI files and verifies the presence of VSync
    settings across several configuration files.

    Returns:
        str: A concatenated string of messages highlighting changes, issues, or notices for the user regarding
        the analyzed INI files.
    """
    """Check INI files for mods."""
    message_list: list[str] = []
    vsync_list: list[str] = []

    config_files = ConfigFileCache()
    # TODO: Maybe return a message that no ini files were found? (See also: TODO in ConfigFileCache)
    # if not config_files:
    #     pass

    game_lower = CMain.gamevars["game"].lower()

    for file_lower, file_path in config_files.items():
        if file_lower.startswith(game_lower) and config_files.has(file_lower, "General", "sStartingConsoleCommand"):
            message_list.extend((
                f"[!] NOTICE: {file_path} contains the *sStartingConsoleCommand* setting.\n",
                "In rare cases, this setting can slow down the initial game startup time for some players.\n",
                "You can test your initial startup time difference by removing this setting from the INI file.\n-----\n",
            ))

    # TODO: Support for other exe file names
    if config_files.get(bool, "dxvk.conf", f"{CMain.gamevars['game']}.exe", "dxgi.syncInterval"):
        vsync_list.append(f"{config_files['dxvk.conf']} | SETTING: dxgi.syncInterval\n")
    if config_files.get(bool, "enblocal.ini", "ENGINE", "ForceVSync"):
        vsync_list.append(f"{config_files['enblocal.ini']} | SETTING: ForceVSync\n")
    if config_files.get(bool, "longloadingtimesfix.ini", "Limiter", "EnableVSync"):
        vsync_list.append(f"{config_files['longloadingtimesfix.ini']} | SETTING: EnableVSync\n")
    if config_files.get(bool, "reshade.ini", "APP", "ForceVsync"):
        vsync_list.append(f"{config_files['reshade.ini']} | SETTING: ForceVsync\n")
    if config_files.get(bool, "fallout4_test.ini", "CreationKit", "VSyncRender"):
        vsync_list.append(f"{config_files['fallout4_test.ini']} | SETTING: VSyncRender\n")

    if "; F10" in config_files.get_strict(str, "espexplorer.ini", "General", "HotKey"):
        config_files.set(str, "espexplorer.ini", "General", "HotKey", "0x79")
        CMain.logger.info(f"> > > PERFORMED INI HOTKEY FIX FOR {config_files['espexplorer.ini']}")
        message_list.append(f"> Performed INI Hotkey Fix For : {config_files['espexplorer.ini']}\n")

    if config_files.get_strict(int, "epo.ini", "Particles", "iMaxDesired") > 5000:
        config_files.set(int, "epo.ini", "Particles", "iMaxDesired", 5000)
        CMain.logger.info(f"> > > PERFORMED INI PARTICLE COUNT FIX FOR {config_files['epo.ini']}")
        message_list.append(f"> Performed INI Particle Count Fix For : {config_files['epo.ini']}\n")

    if "f4ee.ini" in config_files:
        if config_files.get(int, "f4ee.ini", "CharGen", "bUnlockHeadParts") == 0:
            config_files.set(int, "f4ee.ini", "CharGen", "bUnlockHeadParts", 1)
            CMain.logger.info(f"> > > PERFORMED INI HEAD PARTS UNLOCK FOR {config_files['f4ee.ini']}")
            message_list.append(f"> Performed INI Head Parts Unlock For : {config_files['f4ee.ini']}\n")

        if config_files.get(int, "f4ee.ini", "CharGen", "bUnlockTints") == 0:
            config_files.set(int, "f4ee.ini", "CharGen", "bUnlockTints", 1)
            CMain.logger.info(f"> > > PERFORMED INI FACE TINTS UNLOCK FOR {config_files['f4ee.ini']}")
            message_list.append(f"> Performed INI Face Tints Unlock For : {config_files['f4ee.ini']}\n")

    if "highfpsphysicsfix.ini" in config_files:
        if config_files.get(bool, "highfpsphysicsfix.ini", "Main", "EnableVSync"):
            vsync_list.append(f"{config_files['highfpsphysicsfix.ini']} | SETTING: EnableVSync\n")

        if config_files.get_strict(float, "highfpsphysicsfix.ini", "Limiter", "LoadingScreenFPS") < 600.0:
            config_files.set(float, "highfpsphysicsfix.ini", "Limiter", "LoadingScreenFPS", 600.0)
            CMain.logger.info(f"> > > PERFORMED INI LOADING SCREEN FPS FIX FOR {config_files['highfpsphysicsfix.ini']}")
            message_list.append(
                f"> Performed INI Loading Screen FPS Fix For : {config_files['highfpsphysicsfix.ini']}\n")

    if vsync_list:
        message_list.extend((
            "* NOTICE : VSYNC IS CURRENTLY ENABLED IN THE FOLLOWING FILES *\n",
            *vsync_list,
        ))

    if config_files.duplicate_files:
        all_duplicates: list[Path] = []
        for paths in config_files.duplicate_files.values():
            all_duplicates.extend(paths)
        all_duplicates.extend([fp for f, fp in config_files.items() if f in config_files.duplicate_files])
        message_list.extend((
            "* NOTICE : DUPLICATES FOUND OF THE FOLLOWING FILES *\n",
            *[f"{p!s}\n" for p in sorted(all_duplicates, key=lambda p: p.name)],
        ))
    return "".join(message_list)


# ================================================
# CHECK ALL UNPACKED / LOOSE MOD FILES
# ================================================
# noinspection DuplicatedCode
def scan_mods_unpacked() -> str:
    """
    Scans and processes mod files within a specified mods folder. The function performs
    initial cleanup, analyzes loose files, and categorizes potential issues related to
    the mod files' folder content or specific file types, formats, and configurations.

    During execution, the function:
    - Detects and processes redundant files and folders, such as README or changelog
      files, and relocates them to a backup path.
    - Identifies problematic file attributes, such as invalid dimensions for DDS files,
      incorrect file formats for textures and sounds, or the presence of loose precombine/
      previs files.
    - Examines directories for specific types of files, including animation-related data
      and modified Script Extender files, which might pose issues like crashes or
      incompatibilities.

    Returns:
        str: Detailed scan results assembled into a structured report.

    Raises:
        No errors are described as part of the docstring. Ensure developer review of the
        function's implementation for potential raised exceptions.
    """
    message_list: list[str] = [
        "=================== MOD FILES SCAN ====================\n",
        "========= RESULTS FROM UNPACKED / LOOSE FILES =========\n",
    ]
    cleanup_list: set[str] = set()
    animdata_list: set[str] = set()
    tex_dims_list: set[str] = set()
    tex_frmt_list: set[str] = set()
    snd_frmt_list: set[str] = set()
    xse_file_list: set[str] = set()
    previs_list: set[str] = set()
    xse_acronym_setting = CMain.yaml_settings(str, CMain.YAML.Game, f"Game{CMain.gamevars['vr']}_Info.XSE_Acronym")
    xse_scriptfiles_setting = CMain.yaml_settings(dict[str, str], CMain.YAML.Game,
                                                  f"Game{CMain.gamevars['vr']}_Info.XSE_HashedScripts")

    xse_acronym = xse_acronym_setting if isinstance(xse_acronym_setting, str) else "XSE"
    xse_scriptfiles = xse_scriptfiles_setting if isinstance(xse_scriptfiles_setting, dict) else {}

    backup_path = Path("CLASSIC Backup/Cleaned Files")
    if not TEST_MODE:
        backup_path.mkdir(parents=True, exist_ok=True)

    mod_path = CMain.classic_settings(Path, "MODS Folder Path")
    if not mod_path:
        return str(CMain.yaml_settings(str, CMain.YAML.Main, "Mods_Warn.Mods_Path_Missing"))

    if not mod_path.is_dir():
        return str(CMain.yaml_settings(str, CMain.YAML.Main, "Mods_Warn.Mods_Path_Invalid"))

    print("✔️ MODS FOLDER PATH FOUND! PERFORMING INITIAL MOD FILES CLEANUP...")

    filter_names = ("readme", "changes", "changelog", "change log")
    for root, dirs, files in mod_path.walk(top_down=False):
        root_main = root.relative_to(mod_path).parent
        has_anim_data = False
        for dirname in dirs:
            dirname_lower = dirname.lower()
            # ================================================
            # DETECT MODS WITH AnimationFileData
            if not has_anim_data and dirname_lower == "animationfiledata":
                has_anim_data = True
                animdata_list.add(f"  - {root_main}\n")
            # ================================================
            # (RE)MOVE REDUNDANT FOMOD FOLDERS
            elif dirname_lower == "fomod":
                fomod_folder_path = root / dirname
                relative_path = fomod_folder_path.relative_to(mod_path)
                new_folder_path = backup_path / relative_path

                if not TEST_MODE:
                    shutil.move(fomod_folder_path, new_folder_path)
                cleanup_list.add(f"  - {relative_path}\n")

        for filename in files:
            filename_lower = filename.lower()
            # ================================================
            # (RE)MOVE REDUNDANT README / CHANGELOG FILES
            if filename_lower.endswith(".txt") and any(name in filename_lower for name in filter_names):
                file_path = root / filename
                relative_path = file_path.relative_to(mod_path)
                new_file_path = backup_path / relative_path
                if not TEST_MODE:
                    new_file_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(file_path, new_file_path)
                cleanup_list.add(f"  - {relative_path}\n")

    print("✔️ CLEANUP COMPLETE! NOW ANALYZING ALL UNPACKED/LOOSE MOD FILES...")

    for root, _, files in mod_path.walk(top_down=False):
        root_main = root.relative_to(mod_path).parent

        has_previs_files = False
        has_xse_files = False
        for filename in files:
            filename_lower = filename.lower()
            file_path = root / filename
            relative_path = file_path.relative_to(mod_path)
            file_ext = file_path.suffix.lower()
            # ================================================
            # DETECT DDS FILES WITH INCORRECT DIMENSIONS
            if file_ext == ".dds":
                with file_path.open("rb") as dds_file:
                    dds_data = dds_file.read(20)
                if dds_data[:4] == b"DDS ":
                    # TODO: Warn if magic bytes differ
                    width = struct.unpack("<I", dds_data[12:16])[0]
                    height = struct.unpack("<I", dds_data[16:20])[0]
                    if width % 2 != 0 or height % 2 != 0:
                        tex_dims_list.add(f"  - {relative_path} ({width}x{height})")
            # ================================================
            # DETECT INVALID TEXTURE FILE FORMATS
            elif file_ext in {".tga", ".png"} and "BodySlide" not in file_path.parts:
                tex_frmt_list.add(f"  - {file_ext[1:].upper()} : {relative_path}\n")
            # ================================================
            # DETECT INVALID SOUND FILE FORMATS
            elif file_ext in {".mp3", ".m4a"}:
                snd_frmt_list.add(f"  - {file_ext[1:].upper()} : {relative_path}\n")
            # ================================================
            # DETECT MODS WITH SCRIPT EXTENDER FILE COPIES
            elif (
                    not has_xse_files
                    and any(filename_lower == key.lower() for key in xse_scriptfiles)
                    and "workshop framework" not in str(root).lower()
                    and f"Scripts\\{filename}" in str(file_path)
            ):
                has_xse_files = True
                xse_file_list.add(f"  - {root_main}\n")
            # ================================================
            # DETECT MODS WITH PRECOMBINE / PREVIS FILES
            elif not has_previs_files and filename_lower.endswith((".uvd", "_oc.nif")):
                has_previs_files = True
                previs_list.add(f"  - {root_main}\n")

    if xse_file_list:
        message_list.extend([
            f"\n# ⚠️ FOLDERS CONTAIN COPIES OF *{xse_acronym}* SCRIPT FILES ⚠️\n",
            "▶️ Any mods with copies of original Script Extender files\n",
            "  may cause script related problems or crashes.\n\n",
            *sorted(xse_file_list),
        ])
    if previs_list:
        message_list.extend([
            "\n# ⚠️ FOLDERS CONTAIN LOOSE PRECOMBINE / PREVIS FILES ⚠️\n",
            "▶️ Any mods that contain custom precombine/previs files\n",
            "  should load after the PRP.esp plugin from Previs Repair Pack (PRP).\n",
            "  Otherwise, see if there is a PRP patch available for these mods.\n\n",
            *sorted(previs_list),
        ])
    if tex_dims_list:
        message_list.extend([
            "\n# ⚠️ DDS DIMENSIONS ARE NOT DIVISIBLE BY 2 ⚠️\n",
            "▶️ Any mods that have texture files with incorrect dimensions\n",
            "  are very likely to cause a *Texture (DDS) Crash*. For further details,\n",
            "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
            *sorted(tex_dims_list),
        ])
    if tex_frmt_list:
        message_list.extend([
            "\n# ❓ TEXTURE FILES HAVE INCORRECT FORMAT, SHOULD BE DDS ❓\n",
            "▶️ Any files with an incorrect file format will not work.\n",
            "  Mod authors should convert these files to their proper game format.\n",
            "  If possible, notify the original mod authors about these problems.\n\n",
            *sorted(tex_frmt_list),
        ])
    if snd_frmt_list:
        message_list.extend([
            "\n# ❓ SOUND FILES HAVE INCORRECT FORMAT, SHOULD BE XWM OR WAV ❓\n",
            "▶️ Any files with an incorrect file format will not work.\n",
            "  Mod authors should convert these files to their proper game format.\n",
            "  If possible, notify the original mod authors about these problems.\n\n",
            *sorted(snd_frmt_list),
        ])
    if animdata_list:
        message_list.extend([
            "\n# ❓ FOLDERS CONTAIN CUSTOM ANIMATION FILE DATA ❓\n",
            "▶️ Any mods that have their own custom Animation File Data\n",
            "  may rarely cause an *Animation Corruption Crash*. For further details,\n",
            "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
            *sorted(animdata_list),
        ])
    if cleanup_list:
        message_list.extend([
            "\n# 📄 DOCUMENTATION FILES MOVED TO 'CLASSIC Backup\\Cleaned Files' 📄\n",
            *sorted(cleanup_list),
        ])

    return "".join(message_list)


# ================================================
# CHECK ALL ARCHIVED / BA2 MOD FILES
# ================================================
# noinspection DuplicatedCode
def scan_mods_archived() -> str:
    """
    Scans and analyzes BA2 mod archive files for various issues or invalid data.

    This function processes mod archive files with BA2 format and validates their structure,
    contents, and file formats. It identifies potential issues such as invalid texture dimensions,
    incorrect file formats, presence of unauthorized files, and problem-specific data like script
    extender script files or previs/precombine files. The results of the scan are compiled into
    a string message containing a detailed summary.

    Returns:
        str: A summary report detailing the results of the mod archive scan, including detected
            issues or warnings.

    Raises:
        Does not raise explicit exceptions but handles issues within the function to provide meaningful
        error feedback.

    """
    message_list: list[str] = [
        "\n========== RESULTS FROM ARCHIVED / BA2 FILES ==========\n",
    ]
    ba2_frmt_list: set[str] = set()
    animdata_list: set[str] = set()
    tex_dims_list: set[str] = set()
    tex_frmt_list: set[str] = set()
    snd_frmt_list: set[str] = set()
    xse_file_list: set[str] = set()
    previs_list: set[str] = set()

    xse_acronym_setting = CMain.yaml_settings(str, CMain.YAML.Game, f"Game{CMain.gamevars['vr']}_Info.XSE_Acronym")
    xse_scriptfiles_setting = CMain.yaml_settings(dict[str, str], CMain.YAML.Game,
                                                  f"Game{CMain.gamevars['vr']}_Info.XSE_HashedScripts")

    xse_acronym = xse_acronym_setting if isinstance(xse_acronym_setting, str) else ""
    xse_scriptfiles = xse_scriptfiles_setting if isinstance(xse_scriptfiles_setting, dict) else {}

    bsarch_path = Path.cwd() / "CLASSIC Data/BSArch.exe"
    mod_path = CMain.classic_settings(Path, "MODS Folder Path")
    if not mod_path:
        return str(CMain.yaml_settings(str, CMain.YAML.Main, "Mods_Warn.Mods_Path_Missing"))

    if not mod_path.exists():
        return str(CMain.yaml_settings(str, CMain.YAML.Main, "Mods_Warn.Mods_Path_Invalid"))

    if not bsarch_path.exists():
        return str(CMain.yaml_settings(str, CMain.YAML.Main, "Mods_Warn.Mods_BSArch_Missing"))

    print("✔️ ALL REQUIREMENTS SATISFIED! NOW ANALYZING ALL BA2 MOD ARCHIVES...")

    for root, _, files in mod_path.walk(top_down=False):
        for filename in files:
            filename_lower = filename.lower()
            if not filename_lower.endswith(".ba2") or filename_lower == "prp - main.ba2":
                continue
            file_path = root / filename

            try:
                with file_path.open("rb") as f:
                    header = f.read(12)
            except OSError:
                print("Failed to read file:", filename)
                continue

            if header[:4] != b"BTDX" or header[8:] not in {b"DX10", b"GNRL"}:
                ba2_frmt_list.add(f"  - {filename} : {header!s}\n")
                continue

            if header[8:] == b"DX10":
                # Texture-format BA2
                command_dump = (bsarch_path, file_path, "-dump")
                archive_dump = subprocess.run(command_dump, shell=True, capture_output=True, text=True, check=False)
                if archive_dump.returncode != 0:
                    print("BSArch command failed:", archive_dump.returncode, archive_dump.stderr)
                    continue

                output_split = archive_dump.stdout.split("\n\n")
                error_check = output_split[-1]
                if error_check.startswith("Error:"):
                    print("BSArch command failed:", error_check, archive_dump.stderr)
                    continue

                for file_block in output_split[4:]:
                    if not file_block:
                        continue

                    block_split = file_block.split("\n", 3)
                    # Textures\Props\NukaColaQuantum_d.DDS
                    #   DirHash: E10CD7B7  NameHash: ECE5A99C  Ext: dds
                    #   Width:  512  Height:  512  CubeMap: No  Format: DXGI_FORMAT_BC1_UNORM

                    # ================================================
                    # DETECT INVALID TEXTURE FILE FORMATS
                    if "Ext: dds" not in block_split[1]:
                        tex_frmt_list.add(
                            f"  - {block_split[0].rsplit('.', 1)[-1].upper()} : {filename} > {block_split[0]}\n")
                        continue

                    # ================================================
                    # DETECT DDS FILES WITH INCORRECT DIMENSIONS
                    _, width, _, height, _ = block_split[2].split(maxsplit=4)
                    if (width.isdecimal() and int(width) % 2 != 0) or (height.isdecimal() and int(height) % 2 != 0):
                        tex_dims_list.add(f"  - {width}x{height} : {filename} > {block_split[0]}")

            else:
                # General-format BA2
                command_list = (bsarch_path, file_path, "-list")
                archive_list = subprocess.run(command_list, shell=True, capture_output=True, text=True, check=False)
                if archive_list.returncode != 0:
                    print("BSArch command failed:", archive_list.returncode, archive_list.stderr)
                    continue

                output_split = archive_list.stdout.lower().split("\n")
                # Output is a simple list of file paths
                # Textures\Props\NukaColaQuantum_d.DDS

                has_previs_files = False
                has_anim_data = False
                has_xse_files = False
                for file in output_split[15:]:
                    # ================================================
                    # DETECT INVALID SOUND FILE FORMATS
                    if file.endswith((".mp3", ".m4a")):
                        snd_frmt_list.add(f"  - {file[-3:].upper()} : {filename} > {file}\n")
                    # ================================================
                    # DETECT MODS WITH AnimationFileData
                    elif not has_anim_data and "animationfiledata" in file:
                        has_anim_data = True
                        animdata_list.add(f"  - {filename}\n")
                    # ================================================
                    # DETECT MODS WITH SCRIPT EXTENDER FILE COPIES
                    elif (
                            not has_xse_files
                            and any(f"scripts\\{key.lower()}" in file for key in xse_scriptfiles)
                            and "workshop framework" not in str(root).lower()
                    ):
                        has_xse_files = True
                        xse_file_list.add(f"  - {filename}\n")
                    # ================================================
                    # DETECT MODS WITH PRECOMBINE / PREVIS FILES
                    elif not has_previs_files and file.endswith((".uvd", "_oc.nif")):
                        has_previs_files = True
                        previs_list.add(f"  - {filename}\n")

    if xse_file_list:
        message_list.extend([
            f"\n# ⚠️ BA2 ARCHIVES CONTAIN COPIES OF *{xse_acronym}* SCRIPT FILES ⚠️\n",
            "▶️ Any mods with copies of original Script Extender files\n",
            "  may cause script related problems or crashes.\n\n",
            *sorted(xse_file_list),
        ])
    if previs_list:
        message_list.extend([
            "\n# ⚠️ BA2 ARCHIVES CONTAIN CUSTOM PRECOMBINE / PREVIS FILES ⚠️\n",
            "▶️ Any mods that contain custom precombine/previs files\n",
            "  should load after the PRP.esp plugin from Previs Repair Pack (PRP).\n",
            "  Otherwise, see if there is a PRP patch available for these mods.\n\n",
            *sorted(previs_list),
        ])
    if tex_dims_list:
        message_list.extend([
            "\n# ⚠️ DDS DIMENSIONS ARE NOT DIVISIBLE BY 2 ⚠️\n",
            "▶️ Any mods that have texture files with incorrect dimensions\n",
            "  are very likely to cause a *Texture (DDS) Crash*. For further details,\n",
            "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
            *sorted(tex_dims_list),
        ])
    if tex_frmt_list:
        message_list.extend([
            "\n# ❓ TEXTURE FILES HAVE INCORRECT FORMAT, SHOULD BE DDS ❓\n",
            "▶️ Any files with an incorrect file format will not work.\n",
            "  Mod authors should convert these files to their proper game format.\n",
            "  If possible, notify the original mod authors about these problems.\n\n",
            *sorted(tex_frmt_list),
        ])
    if snd_frmt_list:
        message_list.extend([
            "\n# ❓ SOUND FILES HAVE INCORRECT FORMAT, SHOULD BE XWM OR WAV ❓\n",
            "▶️ Any files with an incorrect file format will not work.\n",
            "  Mod authors should convert these files to their proper game format.\n",
            "  If possible, notify the original mod authors about these problems.\n\n",
            *sorted(snd_frmt_list),
        ])
    if animdata_list:
        message_list.extend([
            "\n# ❓ BA2 ARCHIVES CONTAIN CUSTOM ANIMATION FILE DATA ❓\n",
            "▶️ Any mods that have their own custom Animation File Data\n",
            "  may rarely cause an *Animation Corruption Crash*. For further details,\n",
            "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
            *sorted(animdata_list),
        ])
    if ba2_frmt_list:
        message_list.extend([
            "\n# ❓ BA2 ARCHIVES HAVE INCORRECT FORMAT, SHOULD BE BTDX-GNRL OR BTDX-DX10 ❓\n",
            "▶️ Any files with an incorrect file format will not work.\n",
            "  Mod authors should convert these files to their proper game format.\n",
            "  If possible, notify the original mod authors about these problems.\n\n",
            *sorted(ba2_frmt_list),
        ])

    return "".join(message_list)


# ================================================
# BACKUP / RESTORE / REMOVE
# ================================================
def game_files_manage(classic_list: str, mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
    """
    Manages game files by supporting operations like backup, restore, and removal. The behavior of
    the operation depends on the specified mode. The function interacts with the game folder and performs
    the requested action on files or directories matching the criteria in a specified list, which is loaded
    from the settings.

    Args:
        classic_list (str): Name of the list specifying files or directories to be managed. It is a key
            to retrieve the actual list from the configuration settings.
        mode (Literal["BACKUP", "RESTORE", "REMOVE"], optional): Determines the type of operation to
            be performed on the game files. Defaults to "BACKUP".

    Raises:
        FileNotFoundError: If the game path could not be located or is not a valid directory.
    """
    game_path = CMain.yaml_settings(Path, CMain.YAML.Game_Local, f"Game{CMain.gamevars['vr']}_Info.Root_Folder_Game")
    manage_list_setting = CMain.yaml_settings(list[str], CMain.YAML.Game, classic_list)
    manage_list = manage_list_setting if isinstance(manage_list_setting, list) else []

    if game_path is None or not game_path.is_dir():
        raise FileNotFoundError

    backup_path = Path(f"CLASSIC Backup/Game Files/{classic_list}")
    backup_path.mkdir(parents=True, exist_ok=True)
    list_name = classic_list.split(maxsplit=1)[-1]

    if mode == "BACKUP":
        print(f"CREATING A BACKUP OF {list_name} FILES, PLEASE WAIT...")
        try:
            for file in game_path.glob("*"):
                if any(item.lower() in file.name.lower() for item in manage_list):
                    destination_file = backup_path / file.name
                    if file.is_file():
                        shutil.copy2(file, destination_file)
                    elif file.is_dir():
                        if destination_file.is_dir():
                            shutil.rmtree(destination_file)
                        elif destination_file.is_file():
                            destination_file.unlink(missing_ok=True)
                        shutil.copytree(file, destination_file)
            print(f"✔️ SUCCESSFULLY CREATED A BACKUP OF {list_name} FILES\n")
        except PermissionError:
            print(f"❌ ERROR : UNABLE TO BACKUP {list_name} FILES DUE TO FILE PERMISSIONS!")
            print("    TRY RUNNING CLASSIC.EXE IN ADMIN MODE TO RESOLVE THIS PROBLEM.\n")

    elif mode == "RESTORE":
        print(f"RESTORING {list_name} FILES FROM A BACKUP, PLEASE WAIT...")
        try:
            for file in game_path.glob("*"):
                if any(item.lower() in file.name.lower() for item in manage_list):
                    destination_file = backup_path / file.name
                    if destination_file.is_file():
                        shutil.copy2(destination_file, file)
                    elif destination_file.is_dir():
                        if file.is_dir():
                            shutil.rmtree(file)
                        elif file.exists():
                            file.unlink(missing_ok=True)
                        shutil.copytree(destination_file, file)
            print(f"✔️ SUCCESSFULLY RESTORED {list_name} FILES TO THE GAME FOLDER\n")
        except PermissionError:
            print(f"❌ ERROR : UNABLE TO RESTORE {list_name} FILES DUE TO FILE PERMISSIONS!")
            print("    TRY RUNNING CLASSIC.EXE IN ADMIN MODE TO RESOLVE THIS PROBLEM.\n")

    elif mode == "REMOVE":
        print(f"REMOVING {list_name} FILES FROM YOUR GAME FOLDER, PLEASE WAIT...")
        try:
            for file in game_path.glob("*"):
                if any(item.lower() in file.name.lower() for item in manage_list):
                    if file.is_file():
                        file.unlink(missing_ok=True)
                    elif file.is_dir():
                        os.removedirs(file)
            print(f"✔️ SUCCESSFULLY REMOVED {list_name} FILES FROM THE GAME FOLDER\n")
        except PermissionError:
            print(f"❌ ERROR : UNABLE TO REMOVE {list_name} FILES DUE TO FILE PERMISSIONS!")
            print("  TRY RUNNING CLASSIC.EXE IN ADMIN MODE TO RESOLVE THIS PROBLEM.\n")


# ================================================
# COMBINED RESULTS
# ================================================
def game_combined_result() -> str:
    """
    Combines and returns the result of various game-related checks and scans.

    This function aggregates the output from multiple checks and scans related to the
    game's setup, plugins, logs, and configuration files. It retrieves specific game-related
    settings from YAML configuration and determines directories for game documents and
    resources. If these directories are not found, it returns an empty string. Otherwise,
    it processes the checks and accumulates their results into a single string.

    Returns:
        str: A string combining the results of all checks and scans. Returns an
        empty string if game directories are not found.
    """
    docs_path = CMain.yaml_settings(Path, CMain.YAML.Game_Local, f"Game{CMain.gamevars['vr']}_Info.Root_Folder_Docs")
    game_path = CMain.yaml_settings(Path, CMain.YAML.Game_Local, f"Game{CMain.gamevars['vr']}_Info.Root_Folder_Game")

    if not (game_path and docs_path):
        return ""
    return "".join((
        check_xse_plugins(),
        check_crashgen_settings(),
        check_log_errors(docs_path),
        check_log_errors(game_path),
        scan_wryecheck(),
        scan_mod_inis(),
    ))


def mods_combined_result() -> str:  # KEEP THESE SEPARATE SO THEY ARE NOT INCLUDED IN AUTOSCAN REPORTS
    """
    Combines and returns the result of the outputs of `scan_mods_unpacked` and
    `scan_mods_archived`. If the unpacked mods scan indicates that the mods folder
    path is not provided, returns the corresponding unpacked result directly without
    proceeding to retrieve the archived mods results. Otherwise, concatenates the
    unpackaged and archived mods scan results and returns the combination.

    Returns:
        str: Concatenation of the results from `scan_mods_unpacked` and
             `scan_mods_archived`, or the `scan_mods_unpacked` result directly if
             the mods folder path is not provided.
    """
    unpacked = scan_mods_unpacked()
    if unpacked.startswith("❌ MODS FOLDER PATH NOT PROVIDED"):
        return unpacked
    return unpacked + scan_mods_archived()


def write_combined_results() -> None:
    """
    Writes combined results of two processes into a markdown report file.

    This function aggregates results from two distinct processes, namely
    `game_combined_result()` and `mods_combined_result()`. The results are
    retrieved as strings and are then appended to create a combined string.
    This combined string is subsequently written to a markdown file named
    "CLASSIC GFS Report.md". The output file is encoded in UTF-8, and any
    encoding errors are ignored during the write operation.

    Raises:
        FileNotFoundError: If the file path "CLASSIC GFS Report.md" cannot
            be accessed or created.
        UnicodeEncodeError: If there is an issue encoding the content in
            UTF-8 and the error cannot be ignored.
    """
    game_result = game_combined_result()
    mods_result = mods_combined_result()
    gfs_report = Path("CLASSIC GFS Report.md")
    with gfs_report.open("w", encoding="utf-8", errors="ignore") as scan_report:
        scan_report.write(game_result + mods_result)


if __name__ == "__main__":
    CMain.initialize()
    CMain.main_generate_required()
    if TEST_MODE:
        write_combined_results()
    else:
        print(game_combined_result())
        print(mods_combined_result())
        game_files_manage("Backup ENB")
        os.system("pause")
