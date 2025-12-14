"""A module for managing and comparing configuration files, including detecting duplicates
and loading file data into structured formats.

The module provides utilities for comparing INI files, managing configuration files
in a cache, detecting duplicates based on file properties, and applying heuristic
checks for similarity. It also defines a `ConfigFile` type for structured representation
of configuration data.
"""

import asyncio
import io
from collections.abc import ItemsView
from pathlib import Path
from typing import Any, TypedDict

import chardet
import iniparse
import tomlkit
from iniparse import configparser
from tomlkit import TOMLDocument

from ClassicLib import GlobalRegistry, msg_error
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.ScanGame.models.fcx_issue import ConfigIssueSeverity
from ClassicLib.Utils.file_utils import calculate_file_hash, calculate_similarity
from ClassicLib.YamlSettings import yaml_settings

TEST_MODE = False


def compare_ini_files(file1: Path, file2: Path) -> bool:
    """Compare two INI files to determine if they have identical sections and content.

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
        return config1.sections() == config2.sections() and all(config1[section] == config2[section] for section in config1.sections())
    return False


class ConfigFile(TypedDict):
    """A TypedDict for defining the configuration file structure in a strongly-typed
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
    """Cache and manage configuration files for game integrity scanning.

    This class scans the game's root directory for configuration files (INI, CONF),
    identifies duplicate files based on content hash and similarity, and provides
    methods to read and validate configuration settings. It optimizes performance by
    caching file contents and hashes to avoid redundant I/O operations.

    The cache supports both synchronous and asynchronous operations, with async methods
    preferred for use in async contexts to avoid blocking the event loop.

    Attributes:
        _config_files: Mapping of lowercase filenames to their Path objects.
        _config_file_cache: Cache of parsed ConfigFile objects for loaded files.
        duplicate_files: Mapping of lowercase filenames to lists of duplicate file paths.
        _game_root_path: Root directory of the game installation.
        _duplicate_whitelist: List of directory/filename prefixes to include in duplicate detection.
        _hash_cache: Cache of file hashes to avoid recalculation.

    Example:
        >>> cache = ConfigFileCache()
        >>> # Check if a config exists
        >>> if "fallout4.ini" in cache:
        ...     value = await cache.get_async(int, "fallout4.ini", "Display", "iSize W")
        ...     print(f"Screen width: {value}")
        >>> # Detect configuration issues
        >>> issue = await cache.detect_issue(
        ...     int, "fallout4prefs.ini", "Particles", "iMaxDesired", 5000,
        ...     "High particle count can cause crashes",
        ...     lambda val: val > 5000
        ... )
        >>> if issue:
        ...     print(issue.format_report())

    Note:
        - All file operations use UTF-8 encoding with automatic fallback detection.
        - Duplicate detection uses file hashes, similarity scores (≥90%), and INI comparison.
        - Prefer async methods (_load_config_async, get_async, detect_issue) over sync versions.

    """

    _config_files: dict[str, Path]
    _config_file_cache: dict[str, ConfigFile]
    duplicate_files: dict[str, list[Path]]
    _game_root_path: Path | None
    _duplicate_whitelist: list[str]
    _hash_cache: dict[Path, str]  # Cache for file hashes to avoid recalculation

    # noinspection PyUnresolvedReferences
    def __init__(self) -> None:
        """Initialize and scans the game's root directory for configuration files, identifying duplicates based on
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
        self._hash_cache = {}  # Initialize hash cache

        self._game_root_path = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")
        if self._game_root_path is None:
            # TODO: Check if this needs to raise or return an error message instead. (See also: TODO in scan_mod_inis)  # noqa: FIX002
            raise FileNotFoundError

        for path, dirs, files in self._game_root_path.walk():  # pyrefly: ignore
            for file in files:
                # Skip if _dirs do not intersect with the whitelist or no match in file name
                if not (set(self._duplicate_whitelist) & set(dirs)) and not any(
                    whitelist in file for whitelist in self._duplicate_whitelist
                ):
                    continue

                file_lower: str = file.lower()
                # Skip non-config files and files not matching specific criteria
                if not file_lower.endswith((".ini", ".conf")) and file_lower != "dxvk.conf":
                    continue

                file_path: Path = path / file
                file_hash: str = self._get_cached_hash(file_path)

                # Check for duplicates already stored
                if file_lower in self._config_files:
                    existing_file: Path = self._config_files[file_lower]
                    existing_hash: str = self._get_cached_hash(existing_file)

                    if file_hash == existing_hash:  # Exact duplicate
                        self.duplicate_files.setdefault(file_lower, [existing_file]).append(file_path)
                    else:  # Compare for similarity
                        is_similar: bool = (
                            calculate_similarity(existing_file, file_path) >= 0.90
                            or (
                                file_path.stat().st_size == existing_file.stat().st_size
                                and file_path.stat().st_mtime == existing_file.stat().st_mtime
                            )
                            or compare_ini_files(existing_file, file_path)
                        )
                        if is_similar:
                            self.duplicate_files.setdefault(file_lower, [existing_file]).append(file_path)
                else:
                    # Register new config file
                    self._config_files[file_lower] = file_path

    def _get_cached_hash(self, file_path: Path) -> str:
        """Get file hash with caching to avoid expensive recalculation.

        This method caches the hash of a file to prevent redundant calculations when
        checking for duplicates. The cache persists for the lifetime of the
        ConfigFileCache instance.

        Args:
            file_path: Path to the file to hash.

        Returns:
            str: The calculated or cached hash of the file.

        """
        # Check if we have a cached hash
        if file_path in self._hash_cache:
            return self._hash_cache[file_path]

        # Calculate and cache the hash
        file_hash = calculate_file_hash(file_path)
        self._hash_cache[file_path] = file_hash
        return file_hash

    def __contains__(self, file_name_lower: str) -> bool:
        """Check if a given file name is in the configuration files.

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

    # TODO: Useful for checking how many INIs found  # noqa: FIX002
    # def __bool__(self) -> bool:
    #     return bool(self._config_files)

    # def __len__(self) -> int:
    #     return len(self._config_files)

    def __getitem__(self, file_name_lower: str) -> Path:
        """Retrieve the file path associated with the given lowercase file name key.

        Args:
            file_name_lower (str): The lowercase string of the file name to look up in the
                configuration files mapping.

        Returns:
            Path: The file path corresponding to the given lowercase file name key.

        """
        return self._config_files[file_name_lower]

    async def _load_config_async(self, file_name_lower: str) -> None:
        """Asynchronously loads and parses a configuration file with optimized I/O.

        This method loads configuration files without blocking the event loop by
        running file I/O, encoding detection, and parsing operations in executors.
        The parsed configuration is cached for future use.

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

        file_path: Path = self._config_files[file_name_lower]

        # Read file in executor to avoid blocking
        loop = asyncio.get_running_loop()
        file_bytes = await loop.run_in_executor(None, file_path.read_bytes)

        # Detect encoding in executor to avoid blocking
        file_encoding = await loop.run_in_executor(None, lambda: chardet.detect(file_bytes)["encoding"] or "utf-8")

        # Parse in executor as configparser is synchronous
        def parse_config() -> tuple[iniparse.ConfigParser, str]:
            file_text = file_bytes.decode(file_encoding)
            config = iniparse.ConfigParser()
            config.readfp(io.StringIO(file_text, newline=None))
            return config, file_text

        config, file_text = await loop.run_in_executor(None, parse_config)

        config_entry: ConfigFile = {
            "encoding": file_encoding,
            "path": file_path,
            "settings": config,
            "text": file_text,
        }
        self._config_file_cache[file_name_lower] = config_entry

    def get[T](self, value_type: type[T], file_name_lower: str, section: str, setting: str) -> T | None:
        """Sync wrapper for get_async. GUI workers only.

        WARNING: This method uses AsyncBridge internally and creates additional event loop overhead.
        Not for CLI use.

        For CLI usage, use get_async() directly with await.

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
                # Use AsyncBridge to call async version for non-blocking I/O
                bridge = AsyncBridge.get_instance()
                bridge.run_async(self._load_config_async(file_name_lower))
            except FileNotFoundError:
                logger.debug(f"Config file not found: {file_name_lower}")
                msg_error(f"Config file not found: {file_name_lower}")
                return None

        config: iniparse.ConfigParser = self._config_file_cache[file_name_lower]["settings"]

        if not config.has_section(section):
            logger.debug(f"Section '{section}' not found in '{self._config_files[file_name_lower]}'")
            msg_error(f"Section '{section}' does not exist in config file")
            return None

        if not config.has_option(section, setting):
            logger.debug(f"Key '{setting}' not found in section '{section}' of '{self._config_files[file_name_lower]}'")
            msg_error(f"Setting '{setting}' not found in section '{section}'")
            return None

        try:
            if value_type is str:
                return config.get(section, setting)
            if value_type is bool:
                return config.getboolean(section, setting)  # pyright: ignore[reportReturnType]
            if value_type is int:
                return config.getint(section, setting)  # pyright: ignore[reportReturnType]
            if value_type is float:
                return config.getfloat(section, setting)  # pyright: ignore[reportReturnType]
            raise NotImplementedError
        except ValueError as e:
            logger.debug(f"Value type error: {e}")
            msg_error(f"Invalid value type in configuration: {e}")
            return None
        except (configparser.NoSectionError, configparser.NoOptionError):
            return None

    async def get_async[T](self, value_type: type[T], file_name_lower: str, section: str, setting: str) -> T | None:
        """Asynchronously retrieves a configuration value of the specified type from a configuration file.

        This is the async version of the get method that doesn't block the event loop
        when loading configuration files for the first time.

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
                await self._load_config_async(file_name_lower)
            except FileNotFoundError:
                logger.debug(f"Config file not found: {file_name_lower}")
                msg_error(f"Config file not found: {file_name_lower}")
                return None

        config: iniparse.ConfigParser = self._config_file_cache[file_name_lower]["settings"]

        if not config.has_section(section):
            logger.debug(f"Section '{section}' not found in '{self._config_files[file_name_lower]}'")
            msg_error(f"Section '{section}' does not exist in config file")
            return None

        if not config.has_option(section, setting):
            logger.debug(f"Key '{setting}' not found in section '{section}' of '{self._config_files[file_name_lower]}'")
            msg_error(f"Setting '{setting}' not found in section '{section}'")
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
        except ValueError as e:
            logger.debug(f"ValueError while parsing configuration: {e}")
            msg_error(f"Invalid value type in configuration: {e}")
            return None
        except (configparser.NoSectionError, configparser.NoOptionError):
            return None

    async def detect_issue[T](
        self,
        value_type: type[T],
        file_name_lower: str,
        section: str,
        setting: str,
        recommended_value: T,
        description: str,
        condition_check: Any,
        severity: ConfigIssueSeverity = "warning",
    ) -> Any | None:
        """Detect a configuration issue without modifying the file.

        This method checks if a configuration setting meets a specific condition
        and, if so, creates a ConfigIssue report with the current value,
        recommended value, and description.

        Args:
            value_type: The expected data type of the configuration value (str, bool, int, float).
            file_name_lower: The file name of the configuration file, in lowercase.
            section: The section of the configuration file where the setting is located.
            setting: The key of the configuration setting to check.
            recommended_value: The value that should be set to resolve the issue.
            description: Human-readable description of the issue.
            condition_check: A callable that takes the current value and returns True if
                there's an issue, False otherwise.
            severity: Issue severity level ("error", "warning", "info"). Defaults to "warning".

        Returns:
            ConfigIssue object if an issue is detected, None otherwise.

        Example:
            >>> issue = await config_cache.detect_issue(
            ...     int, "epo.ini", "Particles", "iMaxDesired", 5000,
            ...     "High particle count can cause crashes",
            ...     lambda val: int(val) > 5000
            ... )

        """
        from ClassicLib.ScanGame.models.fcx_issue import ConfigIssue

        # Get current value
        current_value = await self.get_async(value_type, file_name_lower, section, setting)

        if current_value is None:
            # Setting doesn't exist - not an issue to report
            return None

        # Check if condition is met (indicating an issue)
        if not condition_check(current_value):
            # No issue detected
            return None

        # Issue detected - create ConfigIssue object
        return ConfigIssue(
            file_path=self._config_files[file_name_lower],
            section=section,
            setting=setting,
            current_value=str(current_value),
            recommended_value=str(recommended_value),
            description=description,
            severity=severity,
        )

    def get_strict[T](self, value_type: type[T], file: str, section: str, setting: str) -> T:
        """Fetch a configuration value with strict type-based fallback.

        If the value is not found, return a default value based on the specified type.
        Default values are as follows:

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
        value: T | None = self.get(value_type, file, section, setting)
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

    def has(self, file_name_lower: str, section: str, setting: str) -> bool:
        """Check if a setting exists. GUI workers only.

        WARNING: This method uses AsyncBridge internally and creates additional event loop overhead.
        Not for CLI use. For CLI usage, use has_async() (to be implemented) or load the file
        beforehand with await _load_config_async().

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
                # Use AsyncBridge to call async version for non-blocking I/O
                bridge = AsyncBridge.get_instance()
                bridge.run_async(self._load_config_async(file_name_lower))
            config: iniparse.ConfigParser = self._config_file_cache[file_name_lower]["settings"]
            return config.has_option(section, setting)
        except (FileNotFoundError, configparser.NoSectionError):
            return False

    def items(self) -> ItemsView[str, Path]:
        """Return the items from the internal configuration files dictionary.

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
    """Modify a specific key in a TOML configuration file within a specified section if the key exists.
    If a new value is provided, the function updates the key with the given value. The current value
    of the key is returned, whether updated or not. If the specified section or key does not exist,
    the function returns None. The function handles file encoding and ensures the integrity of the
    TOML's structure during modifications.

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
    file_bytes: bytes = toml_path.read_bytes()
    file_encoding: str = chardet.detect(file_bytes)["encoding"] or "utf-8"
    file_text: str = file_bytes.decode(file_encoding)
    data: TOMLDocument = tomlkit.parse(file_text)

    if section not in data:
        return None

    section_item: Any = data[section]
    # section_item can be an Item or Container
    # Ensure section_item is a dict-like object (table) that supports key access
    # before checking for the key or trying to access section_item[key].
    if not hasattr(section_item, "__getitem__") or not hasattr(section_item, "__contains__"):
        # If the section exists but is not dict-like, it cannot contain the key as expected.
        return None

    if key not in section_item:  # Now section_item is known to be dict-like.
        # The key does not exist in the table.
        return None

    # If a new value is provided, update the key and return it
    if new_value is not None:
        section_item[key] = new_value  # section_item is dict-like, so assignment is valid.
        if not TEST_MODE:
            with toml_path.open("w", encoding=file_encoding, newline="") as toml_file:
                toml_file.write(data.as_string())
        return new_value

    # Otherwise, return the original value (which is an Item) from the TOML file
    return section_item[key]
