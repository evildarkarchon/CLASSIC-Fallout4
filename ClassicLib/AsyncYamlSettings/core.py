"""Core AsyncYamlSettings implementation."""

import asyncio
from functools import reduce
from pathlib import Path
from typing import Any, ClassVar

from ClassicLib import GlobalRegistry, MessageTarget, msg_error
from ClassicLib.Constants import SETTINGS_IGNORE_NONE, YAML
from ClassicLib.FileIOCore import FileIOCore
from ClassicLib.Logger import logger

from .cache import YamlCache
from .file_operations import YamlFileOperations
from .types import T, YAMLValue, YAMLValueOptional
from .validators import coerce_setting_value, validate_setting_value, validate_settings_structure


class AsyncYamlSettingsCore:
    """
    Async-first YAML settings management with caching and concurrent access.

    This class provides high-performance YAML settings access with:
    - Automatic file change detection and reloading
    - TTL-based caching
    - Concurrent access with proper locking
    - Batch operations for efficiency
    """

    def __init__(self) -> None:
        """Initialize the async YAML settings core."""
        # Initialize components
        self.cache = YamlCache()
        self.file_ops = YamlFileOperations()

        # Use shared FileIOCore instance
        self.io_core = FileIOCore()
        self.file_ops.io_core = self.io_core

    async def load_yaml(self, yaml_store: YAML, force_reload: bool = False) -> dict[str, Any]:
        """
        Load a YAML file with caching and automatic reload on changes.

        Args:
            yaml_store: The YAML store to load
            force_reload: Force reload even if cached

        Returns:
            Loaded YAML data
        """
        store_key = str(yaml_store)

        # Get file path
        file_path = await self.file_ops.get_path_for_store(yaml_store)

        # Get file-specific lock
        file_lock = await self.cache.get_file_lock(str(file_path))

        async with file_lock:
            # Check if we need to reload
            needs_reload = (
                force_reload
                or store_key not in self.cache.cache
                or await self.cache.check_file_modification(file_path)
            )

            if needs_reload:
                # Load from file
                data = await self.file_ops.load_yaml_file(file_path)

                # Validate structure
                if data:
                    try:
                        validate_settings_structure(data, str(yaml_store))
                    except ValueError as e:
                        logger.error(f"Invalid {yaml_store} structure: {e}")
                        # Try to regenerate if it's a settings file
                        if yaml_store in self.file_ops.STATIC_YAML_STORES:
                            data = await self.file_ops.regenerate_settings_file(yaml_store)

                # Update cache
                self.cache.cache[store_key] = data
                self.cache.update_metrics("file_reloads")

                logger.debug(f"Loaded {yaml_store} from file")
            else:
                # Use cached data
                data = self.cache.cache[store_key]
                self.cache.update_metrics("cache_hits")

                logger.debug(f"Using cached {yaml_store}")

        self.cache.update_metrics("total_reads")
        return data

    async def get_setting(
        self,
        return_type: type[T],
        yaml_store: YAML,
        key_path: str,
        default: T | None = None,
    ) -> T | None:
        """
        Get a setting value from a YAML store.

        Args:
            return_type: Expected return type
            yaml_store: YAML store to read from
            key_path: Dot-separated path to the setting
            default: Default value if not found

        Returns:
            Setting value or default
        """
        # Check cache first
        cache_key = (return_type, yaml_store, key_path)
        if cache_key in self.cache.settings_cache:
            self.cache.update_metrics("cache_hits")
            return self.cache.settings_cache[cache_key]

        self.cache.update_metrics("cache_misses")

        # Load YAML data
        data = await self.load_yaml(yaml_store)

        if not data:
            logger.debug(f"No data in {yaml_store} for {key_path}")
            return default

        # Navigate to the key
        try:
            keys = key_path.split(".")
            value = reduce(lambda d, k: d.get(k, {}) if isinstance(d, dict) else {}, keys, data)

            if not value:
                logger.debug(f"Key {key_path} not found in {yaml_store}")
                return default

            # Validate and coerce type
            if not validate_setting_value(value, return_type):
                value = coerce_setting_value(value, return_type)

            # Handle None values
            if value is None and SETTINGS_IGNORE_NONE:
                return default

            # Cache the result
            self.cache.settings_cache[cache_key] = value

            return value

        except Exception as e:
            logger.error(f"Error getting {key_path} from {yaml_store}: {e}")
            msg_error(
                f"Failed to get setting {key_path}",
                details=str(e),
                target=MessageTarget.LOG_ONLY,
            )
            return default

    async def set_setting(
        self,
        yaml_store: YAML,
        key_path: str,
        value: Any,
    ) -> bool:
        """
        Set a setting value in a YAML store.

        Args:
            yaml_store: YAML store to write to
            key_path: Dot-separated path to the setting
            value: Value to set

        Returns:
            True if successful
        """
        # Load current data
        data = await self.load_yaml(yaml_store, force_reload=True)

        # Navigate to the parent key and set value
        keys = key_path.split(".")
        current = data

        # Create nested structure if needed
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

        # Save back to file
        file_path = await self.file_ops.get_path_for_store(yaml_store)
        success = await self.file_ops.save_yaml_file(file_path, data)

        if success:
            # Update cache
            self.cache.cache[str(yaml_store)] = data
            # Clear settings cache for this store
            keys_to_clear = [k for k in self.cache.settings_cache if k[1] == yaml_store]
            for k in keys_to_clear:
                del self.cache.settings_cache[k]

        return success

    async def load_multiple_stores(self, stores: list[YAML]) -> dict[YAML, dict[str, Any]]:
        """
        Load multiple YAML stores concurrently.

        Args:
            stores: List of stores to load

        Returns:
            Dictionary mapping stores to their data
        """
        tasks = [self.load_yaml(store) for store in stores]
        results = await asyncio.gather(*tasks)
        return dict(zip(stores, results))

    async def batch_get_settings(
        self,
        requests: list[tuple[type, YAML, str]],
    ) -> list[Any]:
        """
        Get multiple settings in a single batch operation.

        Args:
            requests: List of (return_type, yaml_store, key_path) tuples

        Returns:
            List of setting values
        """
        tasks = [self.get_setting(rt, store, key) for rt, store, key in requests]
        return await asyncio.gather(*tasks)

    async def prefetch_all_settings(self) -> None:
        """
        Prefetch all static YAML stores for faster access.

        Useful during application startup.
        """
        stores = list(self.file_ops.STATIC_YAML_STORES)
        await self.load_multiple_stores(stores)
        logger.info(f"Prefetched {len(stores)} YAML stores")

    async def clear_cache(self, store: YAML | None = None) -> None:
        """
        Clear cache for a specific store or all stores.

        Args:
            store: Optional store to clear, None for all
        """
        if store:
            self.cache.clear_cache(str(store))
        else:
            self.cache.clear_cache()

    def get_metrics(self) -> dict[str, int]:
        """Get cache performance metrics."""
        return self.cache.get_metrics()

    # Context manager support
    async def __aenter__(self) -> "AsyncYamlSettingsCore":
        """Enter async context - prefetch settings."""
        await self.prefetch_all_settings()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context - cleanup if needed."""
        # Could add cleanup logic here if needed
        pass


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
    return await core.get_setting(return_type, yaml_store, key_path, default)


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
