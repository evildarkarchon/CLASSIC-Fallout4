"""
Async-first YAML settings management core for CLASSIC.

This module provides the primary async implementation for all YAML settings operations,
offering high-performance concurrent access with proper locking and caching strategies.
"""

import asyncio
import time
from functools import reduce
from io import StringIO
from pathlib import Path
from typing import Any, ClassVar, TypeVar

import ruamel.yaml

from ClassicLib import GlobalRegistry, MessageTarget, msg_error
from ClassicLib.Constants import SETTINGS_IGNORE_NONE, YAML
from ClassicLib.FileIOCore import FileIOCore
from ClassicLib.Logger import logger

# Import type definitions from YamlSettingsCache for consistency
type YAMLLiteral = str | int | bool
type YAMLSequence = list[str]
type YAMLMapping = dict[str, "YAMLValue"]
type YAMLValue = YAMLMapping | YAMLSequence | YAMLLiteral
type YAMLValueOptional = YAMLValue | None

T = TypeVar("T")


class AsyncYamlSettingsCore:
    """
    Async-first YAML settings management core.

    This class provides pure async implementations for all YAML configuration operations,
    including retrieving paths, loading YAML files with caching, and accessing or modifying
    settings in a structured YAML format. It uses per-file locks for fine-grained concurrency
    control and integrates with FileIOCore for consistent async I/O operations.

    Attributes:
        STATIC_YAML_STORES: Set of YAML stores considered static (won't change during execution)
        CACHE_TTL: Time-to-live for cache validity checks in seconds
    """

    # Static YAML stores that won't change during program execution
    STATIC_YAML_STORES: ClassVar[set[YAML]] = {YAML.Main, YAML.Game}

    # TTL for cache validity checks (in seconds)
    CACHE_TTL: ClassVar[float] = 5.0

    # Class-level locks for thread safety
    _cache_locks: ClassVar[dict[Path, asyncio.Lock]] = {}
    _global_lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __init__(self) -> None:
        """Initialize the async YAML settings core with metrics."""
        self.cache: dict[Path, YAMLMapping] = {}
        self.file_mod_times: dict[Path, float] = {}
        self.path_cache: dict[YAML, Path] = {}
        self.settings_cache: dict[tuple[YAML, str, type], Any] = {}
        self.last_check_time: dict[Path, float] = {}

        # FileIOCore instance for async file operations
        self.io_core = FileIOCore()

        # Add metrics tracking
        self._metrics = {"cache_hits": 0, "cache_misses": 0, "file_reads": 0, "file_writes": 0}

    async def _get_file_lock(self, path: Path) -> asyncio.Lock:
        """
        Get or create per-file lock for fine-grained locking.

        Args:
            path: Path to get lock for

        Returns:
            asyncio.Lock: Lock specific to this file path
        """
        async with self._global_lock:
            if path not in self._cache_locks:
                self._cache_locks[path] = asyncio.Lock()
            return self._cache_locks[path]

    async def get_path_for_store(self, yaml_store: YAML) -> Path:
        """
        Determines and returns the file path for a given YAML configuration type.

        Args:
            yaml_store: The identifier for the configuration type

        Returns:
            Path: The resolved file path corresponding to the provided YAML store

        Raises:
            NotImplementedError: If the provided yaml_store doesn't match predefined types
            FileNotFoundError: If no valid file path could be resolved
        """
        if yaml_store in self.path_cache:
            return self.path_cache[yaml_store]

        yaml_path: Path = Path.cwd()
        data_path: Path = Path("CLASSIC Data/")

        match yaml_store:
            case YAML.Main:
                yaml_path = data_path / "databases/CLASSIC Main.yaml"
            case YAML.Settings:
                yaml_path = Path("CLASSIC Settings.yaml")
            case YAML.Ignore:
                yaml_path = Path("CLASSIC Ignore.yaml")
            case YAML.Game:
                yaml_path = data_path / f"databases/CLASSIC {GlobalRegistry.get_game()}.yaml"
            case YAML.Game_Local:
                yaml_path = data_path / f"CLASSIC {GlobalRegistry.get_game()} Local.yaml"
            case YAML.TEST:
                yaml_path = Path("tests/test_settings.yaml")
            case other if other not in (YAML.Main, YAML.Settings, YAML.Ignore, YAML.Game, YAML.Game_Local, YAML.TEST):
                raise NotImplementedError

        if yaml_path != Path.cwd():
            self.path_cache[yaml_store] = yaml_path
        else:
            raise FileNotFoundError(f"No YAML file found for {yaml_store}")

        return yaml_path

    async def _check_file_modification(self, yaml_path: Path) -> bool:
        """
        Check if a file has been modified since last check.

        Args:
            yaml_path: Path to check for modifications

        Returns:
            bool: True if file has been modified, False otherwise
        """
        loop = asyncio.get_event_loop()

        try:
            # Run stat in executor to avoid blocking
            stat_result = await loop.run_in_executor(None, yaml_path.stat)
            last_mod_time = stat_result.st_mtime
        except (OSError, FileNotFoundError):
            return False

        if yaml_path not in self.file_mod_times:
            self.file_mod_times[yaml_path] = last_mod_time
            return True

        if self.file_mod_times[yaml_path] != last_mod_time:
            self.file_mod_times[yaml_path] = last_mod_time
            return True

        return False

    async def _parse_yaml_content(self, content: str) -> YAMLMapping:
        """
        Parse YAML content in executor to avoid blocking.

        Args:
            content: YAML string content to parse

        Returns:
            YAMLMapping: Parsed YAML data
        """
        loop = asyncio.get_event_loop()

        def parse_sync() -> YAMLMapping:
            yaml = ruamel.yaml.YAML()
            yaml.indent(offset=2)
            yaml.width = 300
            return yaml.load(StringIO(content))

        return await loop.run_in_executor(None, parse_sync)

    async def _dump_yaml_content(self, data: YAMLMapping) -> str:
        """
        Dump YAML data to string in executor to avoid blocking.

        Args:
            data: YAML data to dump

        Returns:
            str: YAML string representation
        """
        loop = asyncio.get_event_loop()

        def dump_sync() -> str:
            yaml = ruamel.yaml.YAML()
            yaml.indent(offset=2)
            yaml.width = 300
            output = StringIO()
            yaml.dump(data, output)
            return output.getvalue()

        return await loop.run_in_executor(None, dump_sync)

    async def _load_yaml_file(self, yaml_path: Path) -> YAMLMapping:
        """
        Load and parse YAML file using FileIOCore.

        Args:
            yaml_path: Path to YAML file

        Returns:
            YAMLMapping: Parsed YAML data
        """
        try:
            content = await self.io_core.read_file(yaml_path)
            loaded_data = await self._parse_yaml_content(content)

            # Validate settings file structure if it's the settings file
            if yaml_path.name == "CLASSIC Settings.yaml" and not self._validate_settings_structure(loaded_data):
                logger.warning(f"Invalid settings file structure detected in {yaml_path}, regenerating...")
                await self._regenerate_settings_file(yaml_path)
                # Reload after regeneration
                content = await self.io_core.read_file(yaml_path)
                loaded_data = await self._parse_yaml_content(content)

        except (ruamel.yaml.YAMLError, OSError) as e:
            logger.error(f"Failed to load YAML file {yaml_path}: {e}")

            # If it's the settings file and failed to load, regenerate it
            if yaml_path.name == "CLASSIC Settings.yaml":
                logger.warning(f"Corrupted settings file detected, regenerating {yaml_path}...")
                await self._regenerate_settings_file(yaml_path)
                # Reload after regeneration
                content = await self.io_core.read_file(yaml_path)
                return await self._parse_yaml_content(content)

            return {}
        else:
            return loaded_data

    @staticmethod
    def _validate_settings_structure(data: YAMLMapping) -> bool:
        """
        Validates that the settings file has the expected structure.

        Args:
            data: The loaded YAML data to validate

        Returns:
            bool: True if the structure is valid, False otherwise
        """
        # Check if data is None or not a dict
        if not isinstance(data, dict):
            return False

        # Check if CLASSIC_Settings key exists and is a dict
        if "CLASSIC_Settings" not in data:
            return False

        return isinstance(data["CLASSIC_Settings"], dict)

    async def _regenerate_settings_file(self, yaml_path: Path) -> None:
        """
        Regenerates the settings file from the default template.
        Creates a backup of the corrupted file if it exists.

        Args:
            yaml_path: Path to the settings file to regenerate
        """
        # Create backup of corrupted file if it exists and has content
        if await self.io_core.file_exists(yaml_path):
            try:
                content = await self.io_core.read_file(yaml_path)
                if content.strip():  # Only backup if not empty
                    backup_path = yaml_path.with_suffix(".corrupted.bak")
                    counter = 1
                    while await self.io_core.file_exists(backup_path):
                        backup_path = yaml_path.with_suffix(f".corrupted.{counter}.bak")
                        counter += 1
                    await self.io_core.write_file(backup_path, content)
                    logger.info(f"Backed up corrupted settings to {backup_path}")
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not backup corrupted settings file: {e}")

        # Get default settings from CLASSIC Main.yaml
        try:
            main_path = await self.get_path_for_store(YAML.Main)
            main_data = {}
            if await self.io_core.file_exists(main_path):
                content = await self.io_core.read_file(main_path)
                main_data = await self._parse_yaml_content(content)

            default_settings = main_data.get("CLASSIC_Info", {}).get("default_settings", "")
            if default_settings:
                await self.io_core.write_file(yaml_path, default_settings)
                logger.info(f"Successfully regenerated settings file at {yaml_path}")
            else:
                logger.error("Could not find default settings template in CLASSIC Main.yaml")
                # Create minimal valid structure
                minimal_settings = "CLASSIC_Settings:\n  Managed Game: Fallout 4\n"
                await self.io_core.write_file(yaml_path, minimal_settings)
                logger.info("Created minimal settings file")
        except (ruamel.yaml.YAMLError, OSError, PermissionError, KeyError) as e:
            logger.error(f"Failed to regenerate settings file: {e}")
            # Last resort: create minimal structure
            minimal_settings = "CLASSIC_Settings:\n  Managed Game: Fallout 4\n"
            await self.io_core.write_file(yaml_path, minimal_settings)

    async def load_yaml(self, yaml_path: Path) -> YAMLMapping:
        """
        Loads the content of a YAML file with caching.

        Supports static and dynamic YAML files with appropriate caching strategies:
        - Static files are cached permanently
        - Dynamic files use TTL-based cache invalidation

        Args:
            yaml_path: The path to the YAML file to be loaded

        Returns:
            YAMLMapping: The content of the YAML file from cache or freshly loaded
        """
        if not await self.io_core.file_exists(yaml_path):
            return {}

        # Determine if this is a static file by checking against static store paths
        is_static = False
        for store in self.STATIC_YAML_STORES:
            store_path = await self.get_path_for_store(store)
            if yaml_path == store_path:
                is_static = True
                break

        # Get file-specific lock
        file_lock = await self._get_file_lock(yaml_path)

        async with file_lock:
            if is_static:
                # For static files, just load once
                if yaml_path not in self.cache:
                    logger.debug(f"Loading static YAML file: {yaml_path}")
                    self.cache[yaml_path] = await self._load_yaml_file(yaml_path)
            else:
                # For dynamic files, use TTL-based checking
                current_time = time.time()

                # Check if we need to verify file modification
                should_check = False
                if yaml_path not in self.last_check_time:
                    # Never checked before
                    should_check = True
                elif current_time - self.last_check_time[yaml_path] >= self.CACHE_TTL:
                    # TTL expired, should check
                    should_check = True

                if should_check:
                    # Update check time
                    self.last_check_time[yaml_path] = current_time

                    # Check if file has been modified
                    if await self._check_file_modification(yaml_path):
                        logger.debug(f"Loading dynamic YAML file: {yaml_path}")
                        # Reload the YAML file
                        self.cache[yaml_path] = await self._load_yaml_file(yaml_path)
                    elif yaml_path not in self.cache:
                        # File hasn't been modified but we don't have it cached
                        self.cache[yaml_path] = await self._load_yaml_file(yaml_path)

        return self.cache.get(yaml_path, {})

    async def get_setting(self, _type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
        """
        Retrieves or updates a setting from a nested YAML data structure.

        This async method allows both read and write operations on YAML files with
        caching mechanisms for improved performance. If a new value is provided,
        the corresponding YAML file is updated and the cache is refreshed.

        Args:
            _type: The expected type of the setting value
            yaml_store: The YAML store from which the setting is retrieved or updated
            key_path: The dot-delimited path specifying the location of the setting
            new_value: The new value to update the setting with (None for read-only)

        Returns:
            The existing or updated setting value if successful, otherwise None

        Raises:
            ValueError: If attempting to modify a static YAML store
        """
        # If this is a read operation for a static store, check cache first
        cache_key: tuple[YAML, str, type[T]] = (yaml_store, key_path, _type)
        if new_value is None and yaml_store in self.STATIC_YAML_STORES and cache_key in self.settings_cache:
            return self.settings_cache[cache_key]

        yaml_path = await self.get_path_for_store(yaml_store)

        # Load YAML with caching logic
        data = await self.load_yaml(yaml_path)
        keys = key_path.split(".")

        def setdefault(dictionary: dict[str, YAMLValue], key: str) -> dict[str, YAMLValue]:
            """Ensure nested dictionary structure exists."""
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
            # If this is a static file and we're trying to modify it, raise a ValueError
            if yaml_store in self.STATIC_YAML_STORES:
                logger.error(f"Attempting to modify static YAML store {yaml_store} at {key_path}")
                raise ValueError(f"Attempted to modify static YAML store {yaml_store} at {key_path}")

            setting_container[keys[-1]] = new_value  # type: ignore[assignment]

            # Write changes back to the YAML file
            yaml_content = await self._dump_yaml_content(data)
            await self.io_core.write_file(yaml_path, yaml_content)

            # Update the cache
            file_lock = await self._get_file_lock(yaml_path)
            async with file_lock:
                self.cache[yaml_path] = data

            # Clear any cached results for this path
            if cache_key in self.settings_cache:
                del self.settings_cache[cache_key]

            return new_value

        # Traverse YAML structure to get value
        setting_value = setting_container.get(keys[-1])
        if setting_value is None and keys[-1] not in SETTINGS_IGNORE_NONE:
            msg_error(f"ERROR (yaml_settings) : Trying to grab a None value for : '{key_path}'", target=MessageTarget.CLI_ONLY)

        # Cache the result for static stores
        if yaml_store in self.STATIC_YAML_STORES:
            self.settings_cache[cache_key] = setting_value

        return setting_value  # type: ignore[return-value]

    # ==========================================
    # Batch Operations for Concurrent Access
    # ==========================================

    async def load_multiple_stores(self, stores: list[YAML]) -> dict[YAML, YAMLMapping]:
        """
        Load multiple YAML stores concurrently.

        Args:
            stores: List of YAML stores to load

        Returns:
            dict: Mapping of YAML store to loaded data
        """
        tasks = []
        for store in stores:
            path = await self.get_path_for_store(store)
            tasks.append(self.load_yaml(path))

        results = await asyncio.gather(*tasks)
        return dict(zip(stores, results, strict=True))

    async def batch_get_settings(self, requests: list[tuple[type, YAML, str]]) -> list[Any]:
        """
        Batch get multiple settings concurrently.

        Args:
            requests: List of tuples (type, yaml_store, key_path)

        Returns:
            list: List of setting values in the same order as requests
        """
        tasks = [self.get_setting(t, store, path) for t, store, path in requests]
        return await asyncio.gather(*tasks)

    async def prefetch_all_settings(self) -> None:
        """
        Prefetch all common settings at startup for better performance.

        This method loads all commonly used YAML stores concurrently to
        warm up the cache, reducing latency for subsequent operations.
        """
        common_stores = [YAML.Main, YAML.Settings, YAML.Game]
        await self.load_multiple_stores(common_stores)
        logger.info("Prefetched common YAML stores into cache")

    # ==========================================
    # Context Manager Support
    # ==========================================

    async def __aenter__(self) -> "AsyncYamlSettingsCore":
        """
        Support async context manager for batch operations.

        Prefetches common settings when entering the context.
        """
        await self.prefetch_all_settings()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Cleanup on context exit.

        Currently no cleanup needed, but placeholder for future enhancements.
        """

    # ==========================================
    # Performance Metrics
    # ==========================================

    async def get_metrics(self) -> dict[str, int]:
        """
        Get performance metrics.

        Returns:
            dict: Current performance metrics
        """
        return self._metrics.copy()


def get_async_yaml_core() -> AsyncYamlSettingsCore:
    """
    Get or create the global AsyncYamlSettingsCore instance.

    Returns:
        AsyncYamlSettingsCore: The global instance
    """
    # Check if already registered in GlobalRegistry
    instance = GlobalRegistry.get("ASYNC_YAML_CORE")
    if instance is None:
        instance = AsyncYamlSettingsCore()
        GlobalRegistry.register("ASYNC_YAML_CORE", instance)
    return instance


# ==========================================
# Async Convenience Functions
# ==========================================


async def yaml_settings_async(_type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
    """
    Async version of yaml_settings for use in async contexts.

    This function operates on YAML configuration data asynchronously. It retrieves
    or updates a setting based on the provided key path.

    Args:
        _type: The expected type of the setting value
        yaml_store: The YAML object where the settings are stored
        key_path: The key path in the YAML store pointing to the specific setting
        new_value: The new value to update (None for read-only)

    Returns:
        The value of the setting retrieved from the YAML store
    """
    core = get_async_yaml_core()
    setting = await core.get_setting(_type, yaml_store, key_path, new_value)

    if _type is Path:
        return Path(setting) if setting and isinstance(setting, str) else None  # type: ignore[return-value]
    return setting


async def classic_settings_async[T](_type: type[T], setting: str) -> T | None:
    """
    Async version of classic_settings for use in async contexts.

    Fetches a specific setting from the CLASSIC settings file asynchronously.

    Args:
        _type: The expected type of the setting value
        setting: The key of the setting to retrieve

    Returns:
        The value of the requested setting
    """
    return await yaml_settings_async(_type, YAML.Settings, f"CLASSIC_Settings.{setting}")
