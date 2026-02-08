"""Core async YAML settings management.

This module provides the AsyncYamlSettingsCore class for managing YAML-based
settings in asynchronous Python applications. It supports reading, writing,
batch processing, cache management, file validation, and backups.

YAML content caching is delegated to Rust classic_settings module for
performance via DashMap-based lock-free concurrent access.

Classes:
    AsyncYamlSettingsCore: Main class for async YAML settings operations.

Functions:
    get_async_yaml_core: Get the singleton AsyncYamlSettingsCore instance.
    yaml_settings_async: Convenience function for async settings access.
    classic_settings_async: Convenience function for CLASSIC_Settings access.

Example:
    >>> from ClassicLib.YamlSettings.async_ import AsyncYamlSettingsCore
    >>> core = await get_async_yaml_core()
    >>> value = await core.async_yaml_settings(str, YAML.Main, "key.path")

"""

import asyncio
import logging
from collections import OrderedDict
from collections.abc import Mapping
from itertools import starmap
from pathlib import Path
from typing import Any, cast

import classic_settings

from ClassicLib.core.constants import YAML
from ClassicLib.io.yaml.async_.cache import YamlCache
from ClassicLib.io.yaml.async_.file_operations import YamlFileOperations
from ClassicLib.io.yaml.types import T
from ClassicLib.io.yaml.validators import validate_setting_value

logger = logging.getLogger(__name__)


class AsyncYamlSettingsCore:
    """Manage asynchronous operations for YAML settings and files.

    This class provides methods to asynchronously read, write, cache, and manage
    settings stored in YAML files. It supports batch operations and file validation,
    along with capabilities for backing up files and ensuring file existence.
    Caching mechanisms are implemented to optimize performance by avoiding redundant
    file access. Thread-safe access to YAML files is provided through async locks.

    Attributes:
        settings_dir: The directory where YAML settings are stored.
        cache: Cache manager for YAML settings.
        file_ops: Helper for file operations.

    Example:
        >>> core = AsyncYamlSettingsCore()
        >>> # Read a setting
        >>> value = await core.async_yaml_settings(str, YAML.Main, "key.path")
        >>> # Write a setting
        >>> await core.async_yaml_settings(str, YAML.Settings, "key.path", "new_value")
        >>> # Batch read multiple settings
        >>> results = await core.batch_get_settings([
        ...     (str, YAML.Main, "key1"),
        ...     (int, YAML.Main, "key2"),
        ... ])

    """

    # Maximum number of file locks to cache (LRU eviction beyond this)
    _MAX_FILE_LOCKS: int = 64

    def __init__(self, settings_dir: Path | None = None) -> None:
        """Initialize AsyncYamlSettingsCore with directory and components.

        Args:
            settings_dir: The directory where settings files are stored.
                Defaults to "CLASSIC Data" if not provided.

        Example:
            >>> core = AsyncYamlSettingsCore()
            >>> core = AsyncYamlSettingsCore(Path("/custom/settings"))

        """
        self.settings_dir = Path(settings_dir) if settings_dir else Path("CLASSIC Data")
        self.cache = YamlCache()
        self.file_ops = YamlFileOperations()
        # Use OrderedDict for LRU-style eviction of file locks
        self._file_locks: OrderedDict[Path, asyncio.Lock] = OrderedDict()
        # Track which event loop the cached locks belong to, so we can
        # invalidate them when the event loop changes (e.g., AsyncBridge
        # creates a new loop in a background thread).
        self._locks_event_loop: asyncio.AbstractEventLoop | None = None

    def _get_file_lock(self, file_path: Path) -> asyncio.Lock:
        """Get or create a file-specific async lock with LRU eviction.

        Ensures synchronous access to file-specific operations by maintaining
        a bounded dictionary of locks keyed by file paths. Uses LRU eviction
        to prevent unbounded memory growth.

        Detects event loop changes (e.g., when AsyncBridge creates a new
        background loop) and invalidates stale locks to prevent
        "bound to a different event loop" errors in Python 3.12+.

        Args:
            file_path: The path of the file for which the lock is required.

        Returns:
            An asyncio lock instance associated with the specified file path.

        """
        # Detect event loop changes and invalidate stale locks.
        # asyncio.Lock binds to the loop on first acquire; if the loop
        # changes (AsyncBridge restart, different thread), old locks raise
        # RuntimeError: "bound to a different event loop".
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop is not None and self._locks_event_loop is not current_loop:
            if self._file_locks:
                logger.debug(
                    "Event loop changed, clearing %d stale file locks",
                    len(self._file_locks),
                )
                self._file_locks.clear()
            self._locks_event_loop = current_loop

        if file_path in self._file_locks:
            # Move to end (most recently used)
            self._file_locks.move_to_end(file_path)
            return self._file_locks[file_path]

        # Evict oldest entry if at capacity
        while len(self._file_locks) >= self._MAX_FILE_LOCKS:
            # Remove the oldest (first) item - but only if the lock isn't held
            oldest_path, oldest_lock = next(iter(self._file_locks.items()))
            if oldest_lock.locked():
                # Don't evict a lock that's currently held - move to end and try next
                self._file_locks.move_to_end(oldest_path)
            else:
                self._file_locks.pop(oldest_path)

        # Create new lock and add to end
        new_lock = asyncio.Lock()
        self._file_locks[file_path] = new_lock
        return new_lock

    async def async_yaml_settings(
        self,
        variable_type: type[T],
        yaml_store: YAML,
        key: str,
        value: T | None = None,
    ) -> T | None:
        """Read or write a setting in a YAML store.

        Handles asynchronous retrieval and update of settings stored in YAML files.
        Uses Rust classic_settings cache for reads. For write operations, it updates
        the file and invalidates the Rust cache to ensure consistency.

        Args:
            variable_type: Expected type of the setting value. Used for type
                validation when retrieving settings.
            yaml_store: YAML configuration or storage reference. Determines the
                target YAML file for the operation.
            key: Dot-separated key path to the specific setting within the YAML
                structure (e.g., "CLASSIC_Info.version").
            value: New value to set for the specified key. If None, the method
                performs a read operation. Defaults to None.

        Returns:
            The retrieved value if performing a read operation and the key exists.
            For write operations, returns the value that was written.
            Returns None if the key does not exist during a read.

        Example:
            >>> # Read a string setting
            >>> version = await core.async_yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
            >>> # Write a boolean setting
            >>> await core.async_yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.VR Mode", True)

        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)
        cache_key_rust = str(file_path.resolve())

        async with file_lock:
            if value is None:
                # READ operation - check Rust cache first
                cached_docs = classic_settings.get_cached(cache_key_rust)
                if cached_docs is not None:
                    logger.debug("Rust cache hit for %s", cache_key_rust)
                    data = cached_docs[0] if cached_docs else {}
                else:
                    # Cache miss - load via Rust async
                    logger.debug("Rust cache miss for %s, loading async", cache_key_rust)
                    docs = await classic_settings.load_settings_async(cache_key_rust, str(file_path))
                    data = docs[0] if docs else {}

                # Navigate key path
                keys = key.split(".")
                current: Any = data
                for k in keys:
                    if isinstance(current, Mapping) and k in current:
                        current = current[k]
                    else:
                        return None

                # Validate type
                if not validate_setting_value(current, variable_type):
                    return None

                return cast("T", current)

            # WRITE operation
            # Load current data (use Rust cache if available)
            cached_docs = classic_settings.get_cached(cache_key_rust)
            if cached_docs is not None:
                data = cached_docs[0] if cached_docs else {}
            else:
                docs = await classic_settings.load_settings_async(cache_key_rust, str(file_path))
                data = docs[0] if docs else {}

            # Navigate to parent and set value
            keys = key.split(".")
            current = data
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value

            # Save file (remains in Python per CONTEXT.md)
            await self.file_ops.save_yaml_file(file_path, data)

            # Invalidate Rust cache after write to ensure next read gets fresh data
            logger.debug("Invalidating Rust cache after write: %s", cache_key_rust)
            classic_settings.invalidate(cache_key_rust)

            return value

    async def batch_get_settings(self, requests: list[tuple[type, YAML, str]]) -> list[Any]:
        """Execute batch asynchronous retrieval of settings.

        Processes multiple setting requests concurrently using asyncio.gather.

        Args:
            requests: A list of tuples where each tuple contains:
                - A type object specifying the expected value type
                - A YAML store enum value
                - A string key path to the setting

        Returns:
            A list containing the results for each request in order.

        Example:
            >>> results = await core.batch_get_settings([
            ...     (str, YAML.Main, "CLASSIC_Info.version"),
            ...     (bool, YAML.Settings, "CLASSIC_Settings.VR Mode"),
            ...     (int, YAML.Main, "CLASSIC_Info.build"),
            ... ])
            >>> version, vr_mode, build = results

        """
        tasks = list(starmap(self.async_yaml_settings, requests))
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def batch_set_settings(self, updates: list[tuple[type, YAML, str, Any]]) -> list[Any]:
        """Execute batch asynchronous update of settings.

        Processes multiple setting updates concurrently.

        Args:
            updates: A list of tuples where each tuple contains:
                - A type object specifying the value type
                - A YAML store enum value
                - A string key path to the setting
                - The new value to assign

        Returns:
            A list of results from each update operation.

        Example:
            >>> results = await core.batch_set_settings([
            ...     (bool, YAML.Settings, "CLASSIC_Settings.VR Mode", True),
            ...     (str, YAML.Settings, "CLASSIC_Settings.Theme", "dark"),
            ... ])

        """
        tasks = list(starmap(self.async_yaml_settings, updates))
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def clear_cache(self, yaml_store: YAML | None = None) -> None:
        """Clear cached settings and data.

        Delegates to Rust classic_settings for YAML content cache clearing.
        Also clears Python-side caches (path_cache, legacy settings_cache).

        Args:
            yaml_store: The YAML store whose related cache entries need to be
                cleared. If None, all cached entries are cleared.

        Example:
            >>> await core.clear_cache(YAML.Settings)  # Clear specific store
            >>> await core.clear_cache()  # Clear all caches

        """
        if yaml_store:
            # Clear specific store from Rust cache
            file_path = self.file_ops.get_path_for_store(yaml_store)
            cache_key = str(file_path.resolve())
            logger.debug("Invalidating Rust cache for store %s: %s", yaml_store, cache_key)
            classic_settings.invalidate(cache_key)

            # Clear legacy Python caches for backward compatibility
            keys_to_remove = [k for k in self.cache.settings_cache if k[1] == yaml_store]
            for key in keys_to_remove:
                del self.cache.settings_cache[key]
        else:
            # Clear all Rust cache
            logger.debug("Clearing all Rust cache entries")
            classic_settings.clear_cache()

            # Clear all Python-side caches
            self.cache.cache.clear()
            self.cache.settings_cache.clear()
            self.cache.path_cache.clear()

            # Clear file operations cache
            self.file_ops.clear_cache()

    async def reload_settings(self, yaml_store: YAML) -> dict[str, Any]:
        """Reload configuration settings from disk.

        Invalidates the Rust cache for the file and reloads fresh data.

        Args:
            yaml_store: The YAML data store to reload.

        Returns:
            A dictionary containing the reloaded settings.

        Example:
            >>> data = await core.reload_settings(YAML.Settings)
            >>> print(data.get("CLASSIC_Settings", {}).get("VR Mode"))

        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)
        cache_key = str(file_path.resolve())

        async with file_lock:
            # Invalidate Rust cache for this file
            logger.debug("Invalidating Rust cache for reload: %s", cache_key)
            classic_settings.invalidate(cache_key)

            # Clear legacy Python cache
            if str(file_path) in self.cache.cache:
                del self.cache.cache[str(file_path)]

            # Load fresh via Rust async
            docs = await classic_settings.load_settings_async(cache_key, str(file_path))
            return docs[0] if docs else {}

    async def ensure_file_exists(self, yaml_store: YAML) -> None:
        """Ensure a YAML store file exists.

        Acquires an async lock for the file path to prevent concurrent access
        issues during file creation.

        Args:
            yaml_store: The YAML store whose file existence is to be ensured.

        Example:
            >>> await core.ensure_file_exists(YAML.Settings)

        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            await self.file_ops.ensure_file_exists(file_path)

    async def backup_file(self, yaml_store: YAML, backup_suffix: str = ".bak") -> Path:
        """Create a backup of a YAML store file.

        Acquires a file lock to ensure file safety during the backup process.

        Args:
            yaml_store: YAML store object identifying the file to backup.
            backup_suffix: Suffix to append to the backup file. Default is ".bak".

        Returns:
            The file path of the created backup file.

        Example:
            >>> backup_path = await core.backup_file(YAML.Settings)
            >>> print(f"Backup created at: {backup_path}")

        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            return await self.file_ops.backup_file(file_path, backup_suffix)

    async def validate_file(self, yaml_store: YAML) -> bool:
        """Validate a YAML file for existence and loadability.

        Checks if the YAML file exists and can be successfully loaded.

        Args:
            yaml_store: YAML store instance to validate.

        Returns:
            True if the file exists and is loadable, False otherwise.

        Example:
            >>> if await core.validate_file(YAML.Settings):
            ...     print("Settings file is valid")

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
        """Get all settings from a YAML store.

        Fetches all settings by loading the entire YAML file.

        Args:
            yaml_store: The YAML store object referencing the target store.

        Returns:
            A dictionary containing all settings from the YAML store.

        Example:
            >>> all_settings = await core.get_all_settings(YAML.Settings)
            >>> print(all_settings.keys())

        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            return await self.file_ops.load_yaml_file(file_path)

    async def update_settings(self, yaml_store: YAML, updates: dict[str, Any]) -> None:
        """Update multiple settings in a YAML store.

        Applies multiple updates to a YAML file in a single operation,
        writing only once after all updates are applied. Invalidates Rust
        cache after write to ensure consistency.

        Args:
            yaml_store: The YAML store to update.
            updates: A dictionary where each key is a dot-separated path
                to a setting, and the value is the new value to assign.

        Example:
            >>> await core.update_settings(YAML.Settings, {
            ...     "CLASSIC_Settings.VR Mode": True,
            ...     "CLASSIC_Settings.Theme": "dark",
            ... })

        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)
        rust_cache_key = str(file_path.resolve())

        async with file_lock:
            # Load via Rust cache
            cached_docs = classic_settings.get_cached(rust_cache_key)
            if cached_docs is not None:
                data = cached_docs[0] if cached_docs else {}
            else:
                docs = await classic_settings.load_settings_async(rust_cache_key, str(file_path))
                data = docs[0] if docs else {}

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

            # Save once (remains in Python per CONTEXT.md)
            await self.file_ops.save_yaml_file(file_path, data)

            # Invalidate Rust cache after write
            logger.debug("Invalidating Rust cache after update_settings: %s", rust_cache_key)
            classic_settings.invalidate(rust_cache_key)


# Global instance management
_async_yaml_core: AsyncYamlSettingsCore | None = None

# Use threading.Lock for synchronization of lazy asyncio.Lock creation
# This prevents the issue where asyncio.Lock created at module level
# gets bound to a different event loop than where it's used
import threading  # noqa: E402 - Intentional late import for lazy lock creation

_core_lock_threading = threading.Lock()
_core_lock: asyncio.Lock | None = None
_core_lock_loop: asyncio.AbstractEventLoop | None = None


def _get_core_lock() -> asyncio.Lock:
    """Get or create the asyncio.Lock lazily within an async context.

    This ensures the lock is created in the correct event loop context,
    preventing "bound to a different event loop" errors when AsyncBridge
    runs coroutines in its background thread.

    Recreates the lock if the event loop has changed since last creation.
    """
    global _core_lock, _core_lock_loop  # noqa: PLW0603 - Intentional lazy initialization pattern

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    needs_new = _core_lock is None or (current_loop is not None and _core_lock_loop is not current_loop)

    if needs_new:
        with _core_lock_threading:
            # Re-check after acquiring threading lock
            needs_new = _core_lock is None or (current_loop is not None and _core_lock_loop is not current_loop)
            if needs_new:
                _core_lock = asyncio.Lock()
                _core_lock_loop = current_loop

    return _core_lock  # type: ignore[return-value]


async def get_async_yaml_core() -> AsyncYamlSettingsCore:
    """Get the singleton AsyncYamlSettingsCore instance.

    Initializes and provides a global instance of the AsyncYamlSettingsCore class.
    Uses an async lock to prevent concurrent initialization. The singleton pattern
    ensures only one instance exists, which is reused on subsequent calls.

    Returns:
        The global AsyncYamlSettingsCore instance.

    Example:
        >>> core = await get_async_yaml_core()
        >>> value = await core.async_yaml_settings(str, YAML.Main, "key")

    """
    global _async_yaml_core  # noqa: PLW0603

    if _async_yaml_core is None:
        # Use lazy lock getter to ensure lock is created in correct event loop
        lock = _get_core_lock()
        async with lock:
            # Double-check after acquiring lock
            if _async_yaml_core is None:
                _async_yaml_core = AsyncYamlSettingsCore()

    return _async_yaml_core


async def yaml_settings_async(
    return_type: type[T],
    yaml_store: YAML,
    key_path: str,
    default: T | None = None,
) -> T | None:
    """Provide convenience wrapper for async settings retrieval.

    Retrieves a setting from a YAML store using a specified key path.
    Returns the default value if the setting doesn't exist.

    Args:
        return_type: The expected type of the returned setting value.
        yaml_store: The YAML store from which to retrieve the setting.
        key_path: The key path used to locate the setting (e.g., "key.subkey").
        default: The default value to return if the setting is not found.

    Returns:
        The value from the YAML store, or the default value if not found.

    Example:
        >>> version = await yaml_settings_async(str, YAML.Main, "CLASSIC_Info.version")
        >>> vr_mode = await yaml_settings_async(bool, YAML.Settings, "CLASSIC_Settings.VR Mode", False)

    """
    core = await get_async_yaml_core()
    result = await core.async_yaml_settings(return_type, yaml_store, key_path)
    return result if result is not None else default


async def classic_settings_async(
    return_type: type[T],
    key_path: str,
    default: T | None = None,
) -> T | None:
    """Provide convenience wrapper for CLASSIC_Settings access.

    Retrieves settings from the CLASSIC_Settings section of the Settings
    YAML store. Automatically prepends "CLASSIC_Settings." to the key path.

    Args:
        return_type: The expected type of the returned value.
        key_path: The key path within CLASSIC_Settings (without the prefix).
        default: The default value if the key is not found.

    Returns:
        The fetched value, or the default value if not found.

    Example:
        >>> vr_mode = await classic_settings_async(bool, "VR Mode", False)
        >>> # Equivalent to: yaml_settings_async(bool, YAML.Settings, "CLASSIC_Settings.VR Mode", False)

    """
    # Prepend CLASSIC_Settings to the key path
    full_path = f"CLASSIC_Settings.{key_path}"
    return await yaml_settings_async(return_type, YAML.Settings, full_path, default)


__all__ = [
    "AsyncYamlSettingsCore",
    "classic_settings_async",
    "get_async_yaml_core",
    "yaml_settings_async",
]
