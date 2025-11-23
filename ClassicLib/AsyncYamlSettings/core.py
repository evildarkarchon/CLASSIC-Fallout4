"""
Core functionality for managing asynchronous YAML settings, featuring caching
and validation mechanisms.

This module provides the `AsyncYamlSettingsCore` class designed for managing
YAML-based settings in asynchronous Python applications. It supports operations
such as reading, writing, batch processing, cache management, file validation,
and backups.

Imported classes and utility functions:
- YamlCache: Handles caching of YAML settings.
- YamlFileOperations: Provides methods for I/O operations on YAML files.
- validate_setting_value: Validates the value of a specific setting.

Dependencies:
- asyncio: Enables asynchronous operations.
- starmap: Used for batch processing of settings.
- pathlib.Path: Handles file and directory paths.
- typing: Provides type hints for better static type checking.
"""

import asyncio
import logging
from itertools import starmap
from pathlib import Path
from typing import Any, cast

from ClassicLib.AsyncYamlSettings.cache import YamlCache
from ClassicLib.AsyncYamlSettings.file_operations import YamlFileOperations
from ClassicLib.AsyncYamlSettings.types import T
from ClassicLib.AsyncYamlSettings.validators import validate_setting_value
from ClassicLib.Constants import YAML

logger = logging.getLogger(__name__)


class AsyncYamlSettingsCore:
    """
    Manage asynchronous operations for YAML settings and files.

    The `AsyncYamlSettingsCore` class provides a set of methods to asynchronously
    read, write, cache, and manage settings stored in YAML files. It supports batch
    operations and file validation, along with capabilities for backing up files and
    ensuring file existence. Caching mechanisms are implemented to optimize performance
    by avoiding redundant file access. This class offers tools for thread-safe access
    to YAML files through asynchronous locks.

    Attributes:
        settings_dir (Path): The directory where YAML settings are stored.
        cache (YamlCache): Cache manager for YAML settings.
        file_ops (YamlFileOperations): Helper for file operations.
    """

    def __init__(self, settings_dir: Path | None = None) -> None:
        """
        Initializes an instance of the class with specified settings directory, cache, and file
        operations.

        Args:
            settings_dir (Path | None): The directory where settings files are stored. Defaults
                to "CLASSIC Data" if not provided.
        """
        self.settings_dir = Path(settings_dir) if settings_dir else Path("CLASSIC Data")
        self.cache = YamlCache()
        self.file_ops = YamlFileOperations()
        self._lock = asyncio.Lock()
        self._file_locks: dict[Path, asyncio.Lock] = {}

    def _get_file_lock(self, file_path: Path) -> asyncio.Lock:
        """
        Generates or retrieves an asyncio lock for a specified file path to ensure
        synchronous access to file-specific operations.

        This method maintains a dictionary of locks keyed by file paths. If a lock
        for the given file path already exists, it retrieves the existing lock;
        otherwise, it creates a new lock and stores it for future use.

        Args:
            file_path (Path): The path of the file for which the lock is required.

        Returns:
            asyncio.Lock: An asyncio lock instance associated with the specified
                file path.
        """
        if file_path not in self._file_locks:
            self._file_locks[file_path] = asyncio.Lock()
        return self._file_locks[file_path]

    async def async_yaml_settings(
        self,
        variable_type: type[T],
        yaml_store: YAML,
        key: str,
        value: T | None = None,
    ) -> T | None:
        """
        Handles asynchronous retrieval and update of settings stored in YAML files. This
        method supports caching for read operations and allows type validation of retrieved
        values. When invoked for reading, it fetches the specified setting either from a
        memory cache or from the YAML file. For write operations, it updates the specified
        setting and persists the changes to the relevant file while also updating the cache.

        Args:
            variable_type (type[T]): Expected type of the setting value. Used for
                type validation when retrieving settings.
            yaml_store (YAML): YAML configuration or storage reference. Determines the
                target YAML file for the operation.
            key (str): Dot-separated key path to the specific setting within the YAML structure.
            value (T | None, optional): New value to set for the specified key. If None,
                the method performs a read operation. Defaults to None.

        Returns:
            T | None: Returns the retrieved value if performing a read operation and the key
                exists. For write operations, returns the value that was written. If the
                key does not exist during a read, returns None.
        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            # Check cache first for reads
            if value is None:
                cache_key = (variable_type, yaml_store, key)
                if cache_key in self.cache.settings_cache:
                    return cast("T", self.cache.settings_cache[cache_key])

            # Load the YAML file
            data = await self.file_ops.load_yaml_file(file_path)

            # Parse the key path
            keys = key.split(".")
            current = data

            if value is None:
                # Read operation
                for k in keys:
                    if isinstance(current, dict) and k in current:
                        current = current[k]
                    else:
                        return None

                # Validate type using imported function
                if not validate_setting_value(current, variable_type):
                    return None

                # Cache the result
                cache_key = (variable_type, yaml_store, key)
                self.cache.settings_cache[cache_key] = current
                return cast("T", current)
            # Write operation
            # Navigate to the parent of the target key
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]

            # Set the value
            current[keys[-1]] = value

            # Save the file
            await self.file_ops.save_yaml_file(file_path, data)

            # Update cache
            cache_key = (variable_type, yaml_store, key)
            self.cache.settings_cache[cache_key] = value
            return value

    async def batch_get_settings(self, requests: list[tuple[type, YAML, str]]) -> list[Any]:
        """
        Executes asynchronous batched settings retrieval based on provided requests.

        This function receives a list of requests, where each request is a tuple
        consisting of a type, a YAML object, and a string. It processes these
        requests asynchronously using a predefined method (`async_yaml_settings`),
        and collects the results as a list.

        Args:
            requests (list[tuple[type, YAML, str]]): A list of tuples representing
                the batched requests. Each tuple contains:
                    - A type object that specifies a type to handle.
                    - A YAML object to be processed.
                    - A string that contains additional information for
                      processing the configuration.

        Returns:
            list[Any]: A list containing the results of processing each request
                in the input list.
        """
        tasks = list(starmap(self.async_yaml_settings, requests))
        return await asyncio.gather(*tasks)

    async def batch_set_settings(self, updates: list[tuple[type, YAML, str, Any]]) -> list[Any]:
        """
        Updates the settings of multiple YAML configuration files asynchronously.

        This method processes a batch of configuration updates by invoking
        `self.async_yaml_settings` for each set of parameters. The updates are
        executed concurrently, and their results are returned as a list.

        Args:
            updates (list[tuple[type, YAML, str, Any]]): A list of tuples where each
                tuple contains the type of the configuration, a YAML object, a key
                within the configuration, and the new value to assign.

        Returns:
            list[Any]: A list of results from the `self.async_yaml_settings` calls.
                Each result corresponds to the outcome of applying a configuration
                update.
        """
        tasks = list(starmap(self.async_yaml_settings, updates))
        return await asyncio.gather(*tasks)

    async def clear_cache(self, yaml_store: YAML | None = None) -> None:
        """
        Clears cached settings, paths, and other relevant data either for a specific YAML
        store or entirely. This method is useful for refreshing cached data when there are
        changes in the configuration or to reset all caches.

        Args:
            yaml_store (YAML | None): The YAML store whose related cache entries need
                to be cleared. If None, all cached entries are cleared.
        """
        if yaml_store:
            # Clear entries for specific store from settings cache
            keys_to_remove = [k for k in self.cache.settings_cache if k[1] == yaml_store]
            for key in keys_to_remove:
                del self.cache.settings_cache[key]

            # Also clear file ops cache for specific file if possible
            # Note: This assumes file_ops exposes a way to clear specific files,
            # or we rely on full clear. For now, we only have global clear for file_ops.
        else:
            # Clear all caches
            self.cache.cache.clear()
            self.cache.settings_cache.clear()
            self.cache.path_cache.clear()

            # Clear file operations cache if it exists
            if hasattr(self.file_ops, "cache") and hasattr(self.file_ops.cache, "clear"):
                self.file_ops.cache.clear()
            elif hasattr(self.file_ops, "clear_cache"):
                self.file_ops.clear_cache()

    async def reload_settings(self, yaml_store: YAML) -> dict[str, Any]:
        """
        Reloads configuration settings from a YAML file source.

        This method retrieves the file path associated with a given YAML store,
        removes any cached data for that file if it exists, and reloads the data
        from the file on disk. The operation is thread-safe within an asynchronous
        context using file-specific locks.

        Args:
            yaml_store (YAML): The YAML data store object to fetch and reload
                configuration settings from.

        Returns:
            dict[str, Any]: A dictionary containing the reloaded settings from the
                YAML file.

        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            # Clear cache for this file
            if str(file_path) in self.cache.cache:
                del self.cache.cache[str(file_path)]

            # Load fresh from disk
            return await self.file_ops.load_yaml_file(file_path)

    async def ensure_file_exists(self, yaml_store: YAML) -> None:
        """
        Ensures that the file associated with the given YAML store exists. This method
        acquires an asynchronous lock for the file path to prevent concurrent access
        issues during file creation.

        Args:
            yaml_store (YAML): The YAML store object for which the corresponding file's
                existence is to be ensured.
        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            await self.file_ops.ensure_file_exists(file_path)

    async def backup_file(self, yaml_store: YAML, backup_suffix: str = ".bak") -> Path:
        """
        Backs up a YAML file by creating a duplicate with a specified suffix.

        The method acquires a file lock to ensure the file's safety during the
        backup process. The backup file will have the same name as the original
        file but with the specified suffix appended. The operation is performed
        asynchronously.

        Args:
            yaml_store: YAML store object to identify the target file for backup.
            backup_suffix: Suffix to append to the backup file. Default is ".bak".

        Returns:
            Path: The file path of the created backup file.
        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            return await self.file_ops.backup_file(file_path, backup_suffix)

    async def validate_file(self, yaml_store: YAML) -> bool:
        """
        Validates the specified YAML file for its existence and loadability.

        This function checks if the YAML file associated with the given YAML store
        exists at the designated path and can be successfully loaded. If the
        file is accessible and loadable, it returns True. Otherwise, it returns False.

        Args:
            yaml_store: YAML
                YAML store instance for which the file validation is to be performed.

        Returns:
            bool
                True if the file exists and is successfully loadable, False otherwise.
        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            try:
                await self.file_ops.load_yaml_file(file_path)
            except Exception:  # noqa: BLE001 - Validation method: catch all loading failures
                return False
            else:
                return True

    async def get_all_settings(self, yaml_store: YAML) -> dict[str, Any]:
        """
        Fetches all settings from a YAML store asynchronously.

        This method retrieves all settings from a specified YAML store by obtaining
        the file's path, acquiring a lock for thread-safe access, and then loading
        the YAML file to return its content as a dictionary.

        Args:
            yaml_store (YAML): The YAML store object referencing the target store.

        Returns:
            dict[str, Any]: A dictionary containing all settings from the YAML store.
        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            return await self.file_ops.load_yaml_file(file_path)

    async def update_settings(self, yaml_store: YAML, updates: dict[str, Any]) -> None:
        """
        Updates the settings in a YAML configuration file.

        This asynchronous function modifies a YAML configuration file by applying the
        provided updates. It ensures that changes are written safely to the file
        by acquiring a lock, and also updates an internal settings cache.

        Args:
            yaml_store (YAML): The YAML store object representing the configuration
                file.
            updates (dict[str, Any]): A dictionary containing updates to apply to the
                configuration file. Each key is a dot-separated path to a setting,
                and the corresponding value is the new value to assign.
        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            data = await self.file_ops.load_yaml_file(file_path)

            # Apply updates
            for key, value in updates.items():
                keys = key.split(".")
                current = data

                # Navigate to parent
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]

                # Set value
                current[keys[-1]] = value

                # Update cache
                cache_key = (type(value), yaml_store, key)
                self.cache.settings_cache[cache_key] = value

            # Save once
            await self.file_ops.save_yaml_file(file_path, data)


# Global instance management
_async_yaml_core: AsyncYamlSettingsCore | None = None
_core_lock = asyncio.Lock()


async def get_async_yaml_core() -> AsyncYamlSettingsCore:
    """
    Asynchronously retrieves an instance of `AsyncYamlSettingsCore`.

    This function initializes and provides a global instance of the
    `AsyncYamlSettingsCore` class. It ensures thread-safety by using an
    asynchronous lock to prevent multiple concurrent initializations. The
    singleton pattern is implemented to create only one instance of
    `AsyncYamlSettingsCore`, which will be reused on subsequent calls.

    Returns:
        AsyncYamlSettingsCore: The global instance of the asynchronous YAML
        settings core.
    """
    global _async_yaml_core  # noqa: PLW0603

    if _async_yaml_core is None:
        async with _core_lock:
            # Double-check after acquiring lock
            if _async_yaml_core is None:
                _async_yaml_core = AsyncYamlSettingsCore()

    return _async_yaml_core


# Convenience functions
async def yaml_settings_async(
    return_type: type[T],
    yaml_store: YAML,
    key_path: str,
    default: T | None = None,
) -> T | None:
    """
    Asynchronously retrieves a setting from a YAML store using a specified key path. If the requested
    setting does not exist in the store, a default value is returned.

    Args:
        return_type (type[T]): The expected type of the returned setting value.
        yaml_store (YAML): The YAML store from which the setting will be retrieved.
        key_path (str): The key path used to locate the setting within the YAML store.
        default (T | None): The default value to return if the specified setting is not found
            in the YAML store.

    Returns:
        T | None: The value retrieved from the YAML store corresponding to the given key path,
        or the specified default value if the key does not exist.
    """
    core = await get_async_yaml_core()
    result = await core.async_yaml_settings(return_type, yaml_store, key_path)
    return result if result is not None else default


async def classic_settings_async(
    return_type: type[T],
    key_path: str,
    default: T | None = None,
) -> T | None:
    """
    Asynchronously retrieves settings using the specified key path by combining it
    with a predefined prefix ("CLASSIC_Settings.") and delegates the fetching to
    `yaml_settings_async`.

    Args:
        return_type (type[T]): The expected type of the returned value.
        key_path (str): The key path used to fetch the setting.
        default (T | None, optional): The default value returned if the key is not
            found. Defaults to None.

    Returns:
        T | None: The fetched value converted to the specified type, or the default
            value if the key is not found.
    """
    # Prepend CLASSIC_Settings to the key path
    full_path = f"CLASSIC_Settings.{key_path}"
    return await yaml_settings_async(return_type, YAML.Settings, full_path, default)
