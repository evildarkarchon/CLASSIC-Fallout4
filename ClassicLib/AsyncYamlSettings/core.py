"""Core AsyncYamlSettings implementation."""

import asyncio
from functools import reduce
from pathlib import Path
from typing import Any, ClassVar, cast

from ClassicLib import GlobalRegistry, MessageTarget, msg_error
from ClassicLib.Constants import SETTINGS_IGNORE_NONE, YAML
from ClassicLib.FileIOCore import FileIOCore
from ClassicLib.Logger import logger

from .cache import YamlCache
from .file_operations import YamlFileOperations
from .types import T, YAMLValue, YAMLValueOptional
from .validators import coerce_setting_value, validate_setting_value, validate_settings_structure


class AsyncYamlSettingsCore:
    """Core async YAML settings manager with caching and validation."""

    def __init__(self, settings_dir: Path | None = None):
        """Initialize the async YAML settings manager."""
        self.settings_dir = Path(settings_dir) if settings_dir else Path("CLASSIC Data")
        self.cache = YamlCache()
        self.file_ops = YamlFileOperations()
        self._lock = asyncio.Lock()
        self._file_locks: dict[Path, asyncio.Lock] = {}

    def _get_file_lock(self, file_path: Path) -> asyncio.Lock:
        """Get or create a lock for a specific file."""
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
        Read or write a setting in a YAML file asynchronously.

        Args:
            variable_type: The expected type of the value
            yaml_store: Which YAML store to use
            key: The key path in dot notation (e.g., "CLASSIC_Settings.MaxOutputLines")
            value: If provided, write this value; otherwise read

        Returns:
            The value from the YAML file, or None if not found

        Raises:
            yaml.YAMLError: If the YAML file is invalid
            OSError: If the file cannot be accessed
        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            # Check cache first for reads
            if value is None:
                cache_key = (variable_type, yaml_store, key)
                if cache_key in self.cache.settings_cache:
                    return cast(T, self.cache.settings_cache[cache_key])

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
                return cast(T, current)
            else:
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

    async def batch_get_settings(
        self, requests: list[tuple[type, YAML, str]]
    ) -> list[Any]:
        """
        Get multiple settings in a batch operation.

        Args:
            requests: List of tuples (variable_type, yaml_store, key)

        Returns:
            List of values corresponding to each request
        """
        tasks = [
            self.async_yaml_settings(var_type, store, key)
            for var_type, store, key in requests
        ]
        return await asyncio.gather(*tasks)

    async def batch_set_settings(
        self, updates: list[tuple[type, YAML, str, Any]]
    ) -> list[Any]:
        """
        Set multiple settings in a batch operation.

        Args:
            updates: List of tuples (variable_type, yaml_store, key, value)

        Returns:
            List of values that were set
        """
        tasks = [
            self.async_yaml_settings(var_type, store, key, value)
            for var_type, store, key, value in updates
        ]
        return await asyncio.gather(*tasks)

    async def clear_cache(self, yaml_store: YAML | None = None) -> None:
        """Clear the cache for a specific store or all stores."""
        if yaml_store:
            # Clear entries for specific store from settings cache
            keys_to_remove = [k for k in self.cache.settings_cache if k[1] == yaml_store]
            for key in keys_to_remove:
                del self.cache.settings_cache[key]
        else:
            # Clear all caches
            self.cache.cache.clear()
            self.cache.settings_cache.clear()
            self.cache.path_cache.clear()

    async def reload_settings(self, yaml_store: YAML) -> dict[str, Any]:
        """
        Reload settings from disk, bypassing cache.

        Args:
            yaml_store: Which YAML store to reload

        Returns:
            The reloaded settings dictionary
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
        """Ensure that a YAML file exists, creating it if necessary."""
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            await self.file_ops.ensure_file_exists(file_path)

    async def backup_file(self, yaml_store: YAML, backup_suffix: str = ".bak") -> Path:
        """
        Create a backup of a YAML file.

        Args:
            yaml_store: Which YAML store to backup
            backup_suffix: Suffix to append to the backup file

        Returns:
            Path to the backup file
        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            return await self.file_ops.backup_file(file_path, backup_suffix)

    async def validate_file(self, yaml_store: YAML) -> bool:
        """
        Validate that a YAML file can be loaded without errors.

        Args:
            yaml_store: Which YAML store to validate

        Returns:
            True if the file is valid, False otherwise
        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            try:
                await self.file_ops.load_yaml_file(file_path)
                return True
            except Exception:
                return False

    async def get_all_settings(self, yaml_store: YAML) -> dict[str, Any]:
        """
        Get all settings from a YAML store.

        Args:
            yaml_store: Which YAML store to read

        Returns:
            Dictionary of all settings
        """
        file_path = self.file_ops.get_path_for_store(yaml_store)
        file_lock = self._get_file_lock(file_path)

        async with file_lock:
            return await self.file_ops.load_yaml_file(file_path)

    async def update_settings(
        self, yaml_store: YAML, updates: dict[str, Any]
    ) -> None:
        """
        Update multiple settings in a single file operation.

        Args:
            yaml_store: Which YAML store to update
            updates: Dictionary of key-value pairs to update
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
    Get or create the global AsyncYamlSettingsCore instance.

    Returns:
        The global instance
    """
    global _async_yaml_core

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
    Async convenience function to get a YAML setting.

    Args:
        return_type: Expected return type
        yaml_store: YAML store to read from
        key_path: Dot-separated path to the setting
        default: Default value if not found

    Returns:
        Setting value or default
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
    Async convenience function to get a CLASSIC setting.

    Args:
        return_type: Expected return type
        key_path: Dot-separated path to the setting (without CLASSIC_Settings prefix)
        default: Default value if not found

    Returns:
        Setting value or default
    """
    # Prepend CLASSIC_Settings to the key path
    full_path = f"CLASSIC_Settings.{key_path}"
    return await yaml_settings_async(return_type, YAML.Settings, full_path, default)
