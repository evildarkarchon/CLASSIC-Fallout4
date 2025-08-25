"""
Sync wrapper for AsyncYamlSettingsCore providing synchronous YAML settings access.

This module provides a synchronous interface to the async-first YAML settings system,
using AsyncBridge for efficient sync-to-async execution without event loop overhead.
"""

from pathlib import Path
from typing import Any, TypeVar

from ClassicLib import GlobalRegistry
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.AsyncYamlSettingsCore import (
    YAMLLiteral,
    YAMLMapping,
    YAMLSequence,
    YAMLValue,
    YAMLValueOptional,
    get_async_yaml_core,
)
from ClassicLib.Constants import YAML
from ClassicLib.Meta import SingletonMeta

T = TypeVar("T")


class YamlSettingsCache(metaclass=SingletonMeta):
    """
    Synchronous wrapper for AsyncYamlSettingsCore.

    This class provides a sync interface to the async YAML settings core,
    maintaining singleton behavior and using AsyncBridge for efficient
    sync-to-async execution.
    """

    def __init__(self) -> None:
        """Initialize the sync wrapper with async core and bridge."""
        self._async_core = get_async_yaml_core()
        self._bridge = AsyncBridge.get_instance()

    def get_path_for_store(self, yaml_store: YAML) -> Path:
        """
        Get the file path for a given YAML configuration type.

        Args:
            yaml_store: The identifier for the configuration type

        Returns:
            Path: The resolved file path for the YAML store
        """
        return self._bridge.run_async(self._async_core.get_path_for_store(yaml_store))

    def load_yaml(self, yaml_path: Path) -> YAMLMapping:
        """
        Load a YAML file with caching.

        Args:
            yaml_path: Path to the YAML file

        Returns:
            YAMLMapping: The loaded YAML data
        """
        return self._bridge.run_async(self._async_core.load_yaml(yaml_path))

    def get_setting(self, _type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
        """
        Get or set a setting in the YAML store.

        Args:
            _type: Expected type of the setting
            yaml_store: YAML store to access
            key_path: Dot-delimited path to the setting
            new_value: New value to set (None for read-only)

        Returns:
            The setting value or None
        """
        return self._bridge.run_async(self._async_core.get_setting(_type, yaml_store, key_path, new_value))

    def load_multiple_stores(self, stores: list[YAML]) -> dict[YAML, YAMLMapping]:
        """
        Load multiple YAML stores concurrently.

        Args:
            stores: List of YAML stores to load

        Returns:
            dict: Mapping of YAML store to loaded data
        """
        return self._bridge.run_async(self._async_core.load_multiple_stores(stores))

    def batch_get_settings(self, requests: list[tuple[type, YAML, str]]) -> list[Any]:
        """
        Get multiple settings in a single batch operation.

        Args:
            requests: List of (type, yaml_store, key_path) tuples

        Returns:
            list: Setting values in the same order as requests
        """
        return self._bridge.run_async(self._async_core.batch_get_settings(requests))

    def prefetch_all_settings(self) -> None:
        """Prefetch common settings into cache for better performance."""
        self._bridge.run_async(self._async_core.prefetch_all_settings())

    def get_metrics(self) -> dict[str, int]:
        """
        Get performance metrics from the async core.

        Returns:
            dict: Current performance metrics
        """
        return self._bridge.run_async(self._async_core.get_metrics())

    # Property accessors for direct cache access (if needed by existing code)
    @property
    def cache(self) -> dict[Path, YAMLMapping]:
        """Direct access to the cache dictionary."""
        return self._async_core.cache

    @property
    def path_cache(self) -> dict[YAML, Path]:
        """Direct access to the path cache."""
        return self._async_core.path_cache

    @property
    def settings_cache(self) -> dict[tuple[YAML, str, type], Any]:
        """Direct access to the settings cache."""
        return self._async_core.settings_cache


# Create singleton instance and register it
yaml_cache = YamlSettingsCache()
GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, yaml_cache)


# ==========================================
# Module-level convenience functions
# ==========================================


def yaml_settings[T](_type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
    """
    Manages YAML settings by retrieving or updating a specific setting.

    This function provides synchronous access to YAML configuration data.
    It retrieves or updates a setting based on the provided key path.

    Args:
        _type: The expected type of the setting value
        yaml_store: The YAML store to access
        key_path: The dot-delimited path to the setting
        new_value: Optional new value to set

    Returns:
        The setting value, properly typed
    """
    setting = yaml_cache.get_setting(_type, yaml_store, key_path, new_value)

    if _type is Path:
        return Path(setting) if setting and isinstance(setting, str) else None  # type: ignore[return-value]
    return setting


def classic_settings[T](_type: type[T], setting: str) -> T | None:
    """
    Fetches a specific setting from the CLASSIC settings file.

    This function ensures that a settings file exists and retrieves
    the requested setting from it.

    Args:
        _type: The expected type of the setting value
        setting: The key of the setting to retrieve

    Returns:
        The value of the requested setting
    """
    # Check if settings file exists, create if needed
    settings_path = Path("CLASSIC Settings.yaml")
    if not settings_path.exists():
        # Get default settings from Main YAML
        default_settings = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_settings")
        if not isinstance(default_settings, str):
            raise ValueError("Invalid Default Settings in 'CLASSIC Main.yaml'")

        # Use FileIOCore for consistency
        from ClassicLib.FileIOCore import write_file_sync

        write_file_sync(settings_path, default_settings)

    return yaml_settings(_type, YAML.Settings, f"CLASSIC_Settings.{setting}")


# Export all types for backward compatibility
__all__ = [
    "YAMLLiteral",
    "YAMLMapping",
    "YAMLSequence",
    "YAMLValue",
    "YAMLValueOptional",
    "YamlSettingsCache",
    "classic_settings",
    "yaml_cache",
    "yaml_settings",
]
