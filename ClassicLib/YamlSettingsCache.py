"""
Sync wrapper for AsyncYamlSettingsCore providing synchronous YAML settings access.

This module provides both synchronous and asynchronous interfaces to the async-first
YAML settings system:

- Sync methods (e.g., batch_get_settings) use AsyncBridge for sync-to-async bridging
- Async methods (e.g., batch_get_settings_async) can be used directly in async contexts
- Module-level async functions (yaml_settings_async, classic_settings_async) provide
  convenient async access without needing the cache instance

Usage:
    # Sync context (e.g., __init__, __post_init__)
    from ClassicLib.YamlSettingsCache import yaml_cache, yaml_settings
    result = yaml_cache.batch_get_settings(requests)
    value = yaml_settings(str, YAML.Main, "key")

    # Async context (e.g., async def functions)
    from ClassicLib.YamlSettingsCache import yaml_cache, yaml_settings_async
    result = await yaml_cache.batch_get_settings_async(requests)
    value = await yaml_settings_async(str, YAML.Main, "key")
"""

import asyncio
import threading
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.AsyncYamlSettings.core import (
    classic_settings_async,
    get_async_yaml_core,
    yaml_settings_async,
)
from ClassicLib.AsyncYamlSettings.types import (
    YAMLLiteral,
    YAMLMapping,
    YAMLSequence,
    YAMLValue,
    YAMLValueOptional,
)
from ClassicLib.Constants import YAML

# Fixed circular import - import directly from module
from ClassicLib.GlobalRegistry import Keys, is_registered, register

T = TypeVar("T")


class YamlSettingsCache:
    """
    Handles settings stored in YAML files with caching, singleton support, and both synchronous and asynchronous methods.

    This class provides functionalities to manage YAML-based configurations efficiently. It offers methods to load YAML
    files, fetch or set specific settings, batch operations, and cache prefetching for performance optimization. The class
    is implemented as a singleton to ensure only a single instance manages the YAML settings and maintains thread safety.
    """

    # Class-level storage for singleton instance
    _instance: ClassVar["YamlSettingsCache | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        """Initialize the sync wrapper with async core and bridge."""
        self._bridge = AsyncBridge.get_instance()
        # Get the async core instance using the bridge
        self._async_core = self._bridge.run_async(get_async_yaml_core())
        self._init_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "YamlSettingsCache":
        """
        Creates or retrieves the singleton instance of the YamlSettingsCache class.

        This method implements the Singleton design pattern with thread safety. It
        ensures that only one instance of the YamlSettingsCache class is created
        throughout the application's lifecycle. The singleton instance is lazily
        initialized and double-checked for performance optimization in a multithreaded
        environment.

        Args:
            cls (Type[YamlSettingsCache]): The class for which the singleton instance
                is managed.

        Returns:
            YamlSettingsCache: The single instance of YamlSettingsCache.
        """
        # Fast path - instance already exists
        if cls._instance is not None:
            return cls._instance

        # Slow path - need to create new instance
        with cls._lock:
            # Double-check pattern
            if cls._instance is not None:
                return cls._instance

            # Create new instance
            cls._instance = cls()
            return cls._instance

    def get_path_for_store(self, yaml_store: YAML) -> Path:
        """
        Gets the file path for a given YAML store.

        This method retrieves the file path associated with the provided YAML store
        via file operations.

        Args:
            yaml_store: The YAML store object for which the file path is required.

        Returns:
            Path: The file system path corresponding to the given YAML store.
        """
        # Get path through file_ops
        return self._async_core.file_ops.get_path_for_store(yaml_store)

    async def load_yaml_async(self, yaml_path: Path) -> YAMLMapping:
        """
        Asynchronously loads a YAML file and returns its contents as a mapping.

        This method reads the contents of a YAML file provided by the specified file path
        and parses it into a YAML mapping using the asynchronous file operations.

        Args:
            yaml_path (Path): The path to the YAML file to be loaded.

        Returns:
            YAMLMapping: The parsed contents of the YAML file as a mapping.

        Raises:
            Exception: If an error occurs during file operations or parsing.
        """
        return await self._async_core.file_ops.load_yaml_file(yaml_path)

    def load_yaml(self, yaml_path: Path) -> YAMLMapping:
        """
        Loads a YAML file asynchronously and returns its parsed content.

        This function uses the AsyncBridge to execute the asynchronous file
        operation for loading a YAML file in a synchronous context. It reads
        the YAML file specified by the provided path and returns its contents
        as a mapping.

        Args:
            yaml_path (Path): The file path of the YAML file to be loaded.

        Returns:
            YAMLMapping: The parsed YAML content as a mapping.
        """
        # Load through file_ops using AsyncBridge
        return self._bridge.run_async(self._async_core.file_ops.load_yaml_file(yaml_path))

    def async_yaml_settings(self, _type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
        """
        Updates or retrieves a value from a YAML configuration asynchronously.

        This method allows for either updating a specific value in a YAML file or
        retrieving its current value. It leverages asynchronous processing to ensure
        efficiency and non-blocking behavior. The method interacts with a provided
        YAML object, modifies or fetches the value based on the key path provided,
        and optionally takes a new value for updating.

        Args:
            _type: The type hint for the value to be retrieved or updated.
            yaml_store: A `YAML` instance representing the YAML configuration store.
            key_path: The path within the YAML structure where the desired value
                is located.
            new_value: Optional; the new value to set at the specified key path.
                Defaults to None if no update is required.

        Returns:
            The value retrieved from the YAML configuration, or the updated value
            after modification. Returns `None` if no value is found or no update
            is performed.
        """
        return self._bridge.run_async(self._async_core.async_yaml_settings(_type, yaml_store, key_path, new_value))

    async def load_multiple_stores_async(self, stores: list[YAML]) -> dict[YAML, YAMLMapping]:
        """
        Loads multiple YAML stores asynchronously and returns their mappings.

        This function processes a list of YAML stores, resolves their respective file
        paths using the provided asynchronous core operations, loads the YAML content
        for each store asynchronously, and returns a dictionary mapping each store to
        its loaded YAML content.

        Args:
            stores (list[YAML]): A list of YAML store identifiers to load.

        Returns:
            dict[YAML, YAMLMapping]: A dictionary mapping each input YAML store to its
            corresponding loaded YAML content.
        """
        results = {}
        for store in stores:
            path = self._async_core.file_ops.get_path_for_store(store)
            results[store] = await self._async_core.file_ops.load_yaml_file(path)
        return results

    def load_multiple_stores(self, stores: list[YAML]) -> dict[YAML, YAMLMapping]:
        """
        Loads multiple YAML stores synchronously.

        This method takes a list of YAML stores and loads them synchronously,
        returning a dictionary that maps each input YAML store to its
        corresponding YAML mapping.

        Args:
            stores (list[YAML]): A list of YAML store objects to be loaded.

        Returns:
            dict[YAML, YAMLMapping]: A dictionary mapping each input YAML store
                to its respective YAML mapping.
        """
        return self._bridge.run_async(self.load_multiple_stores_async(stores))

    async def batch_get_settings_async(self, requests: list[tuple[type, YAML, str]]) -> list[Any]:
        """
        Executes batch asynchronous retrieval of settings based on provided requests.

        This method facilitates asynchronous fetching of multiple settings, allowing you
        to retrieve a batch of data simultaneously based on a list of requests.

        Args:
            requests (list[tuple[type, YAML, str]]): A list of tuples where each tuple
                contains three elements:
                  - The first element represents the type.
                  - The second element is the YAML configuration.
                  - The third element is a string identifying the setting to fetch.

        Returns:
            list[Any]: A list containing the results for each of the provided requests.
        """
        return await self._async_core.batch_get_settings(requests)

    def batch_get_settings(self, requests: list[tuple[type, YAML, str]]) -> list[Any]:
        """
        Retrieves a batch of settings asynchronously using the provided requests.

        This method processes a list of requests, where each request is a tuple containing
        a type identifier, a YAML object, and a string. It returns the results of these
        settings requests encapsulated in a list.

        Args:
            requests (list[tuple[type, YAML, str]]): A list of tuples representing the
                settings requests to process. Each tuple contains a type, configuration
                details as a YAML object, and a string identifier.

        Returns:
            list[Any]: A list containing the results of the processed settings requests.
        """
        return self._bridge.run_async(self._async_core.batch_get_settings(requests))

    def prefetch_all_settings(self) -> None:
        """
        Loads and caches specified YAML stores in a file cache for the application.

        This method prefetches the main YAML stores (Main, Settings, and Game) by invoking
        the file loading mechanism. If any of these stores do not exist or cause an
        exception during loading, the method gracefully logs the error without stopping
        the process. It ensures the file contents are cached for future access.

        Raises:
            Exception: If any unexpected error occurs during the file loading process. However,
                       the error is logged, and the process continues for other stores.
        """
        from ClassicLib.Constants import YAML

        # Load the three main YAML stores into file cache
        stores_to_prefetch = [YAML.Main, YAML.Settings, YAML.Game]

        for store in stores_to_prefetch:
            try:
                file_path = self._async_core.file_ops.get_path_for_store(store)
                # Trigger file load which will cache it
                self._bridge.run_async(self._async_core.file_ops.load_yaml_file(file_path, use_cache=True))
            except Exception as e:
                # Log but don't fail - some stores might not exist
                from ClassicLib.Logger import logger
                logger.debug(f"Could not prefetch {store}: {e}")

    def get_metrics(self) -> dict[str, int]:
        """
        Retrieves metrics information as a dictionary.

        This method is currently not implemented and always returns an empty dictionary. It
        is a placeholder for potential future implementation to gather metrics.

        Returns:
            dict[str, int]: An empty dictionary since the metrics are not implemented.
        """
        # Metrics not implemented - return empty dict
        return {}

    # Property accessors for cache compatibility
    @property
    def cache(self) -> Any:
        """
        Gets the cache instance associated with the asynchronous core.

        The `cache` property provides access to the underlying cache instance from the
        asynchronous core object. The cache can be used for various operations related
        to data storage and retrieval. Note that the cache functionality is fully
        dependent on the implementation within the associated asynchronous core.

        Returns:
            Any: The cache instance retrieved from the asynchronous core.
        """
        return self._async_core.cache

    @property
    def path_cache(self) -> dict:
        """
        Gets the current path cache from the async core.

        This property retrieves the cached path data managed by the _async_core,
        specifically focusing on the cache related to paths. It provides an
        efficient mechanism to access previously stored path information.

        Returns:
            dict: A dictionary containing the cached path data.
        """
        return self._async_core.cache.path_cache

    @property
    def settings_cache(self) -> dict:
        """
        Gets the current settings cache.

        The method provides access to a dictionary that represents
        the cached settings. It allows retrieval of the cached
        configuration state.

        Returns:
            dict: A dictionary containing the cached settings.
        """
        return self._async_core.cache.settings_cache

    @property
    def file_mod_times(self) -> dict:
        """
        Gets the file modification times stored in the cache.

        The `file_mod_times` property provides access to a dictionary containing
        file modification times, which is maintained within the asynchronous
        core's cache. The dictionary maps file paths to their respective last
        modification timestamps.

        Returns:
            dict: A dictionary where keys are file paths (str) and values are
            their respective last modification times (str or datetime, based on
            implementation).
        """
        return self._async_core.cache.file_mod_times


# Lazy initialization - don't create at module load time
_yaml_cache = None


def _get_yaml_cache():
    """
    Retrieves or initializes the singleton instance of the YAML settings cache.

    This function manages a global cache for YAML settings, ensuring that only
    a single instance of the cache is created and reused. It initializes the
    cache if it does not already exist and registers it with the appropriate
    keys.

    Returns:
        YamlSettingsCache: The singleton instance of the YAML settings cache.
    """
    global _yaml_cache
    if _yaml_cache is None:
        _yaml_cache = YamlSettingsCache.get_instance()
        register(Keys.YAML_CACHE, _yaml_cache)
    return _yaml_cache


# For backward compatibility - create a callable that returns the singleton
class _YamlCacheProxy:
    """Proxy class for managing YAML cache interactions.

    This class acts as a proxy for a YAML cache system. It allows for deferred
    initialization of the cache and forwards all attribute and function calls
    to the actual YAML cache once it has been created. It also registers the
    cache with a key upon first access, ensuring functionality for systems
    reliant on the YAML cache.
    """

    def __init__(self):
        """
        Initializes the class with a placeholder for the YAML cache singleton.

        This constructor registers a placeholder for the YAML cache singleton
        so that `is_registered()` detects it as registered immediately. However,
        the actual singleton instance is not created until it is accessed for
        the first time.
        """
        # Register a placeholder immediately so is_registered() returns True
        # but don't actually create the singleton until first access
        if not is_registered(Keys.YAML_CACHE):
            register(Keys.YAML_CACHE, self)

    def __getattr__(self, name):
        """
        Handles attribute retrieval for lazy initialization of the YAML cache. This method
        is used to create the actual YAML cache instance on the first access and ensures
        subsequent attribute accesses are delegated to this real cache.

        Args:
            name: Name of the attribute being accessed.

        Returns:
            The value of the requested attribute from the initialized YAML cache.
        """
        # On first attribute access, create real cache and re-register it
        real_cache = _get_yaml_cache()
        # Re-register with the actual cache instance
        register(Keys.YAML_CACHE, real_cache)
        return getattr(real_cache, name)

    def __call__(self):
        """
        Callable class instance method that retrieves and returns a cached YAML object.
        This method is intended to provide quick access to preprocessed YAML data
        from a private cache.

        Returns:
            object: Cached YAML data.
        """
        return _get_yaml_cache()

# Create module-level instance that acts like the original yaml_cache
yaml_cache = _YamlCacheProxy()


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
    cache = _get_yaml_cache()
    setting = cache.async_yaml_settings(_type, yaml_store, key_path, new_value)

    if _type is Path:
        return Path(setting) if setting and isinstance(setting, str) else None  # type: ignore[return-value]
    return setting


def classic_settings[T](_type: type[T], setting: str) -> T | None:
    """
    Fetches a specific setting as a given type from the CLASSIC Settings YAML file.
    If the settings file does not exist, it is created with default settings from
    'CLASSIC Main.yaml' file. Ensures consistent file writing using FileIOCore library.

    Args:
        _type (Type[T]): The expected type of the setting to be returned. It must
            match the type of the requested setting for correct casting.
        setting (str): The name or path of the specific setting to retrieve from
            the CLASSIC Settings YAML file. This path should reference the location
            within the YAML structure.

    Returns:
        T | None: The requested setting cast to the provided type if successful;
        otherwise, returns None.

    Raises:
        ValueError: If the default settings extracted from 'CLASSIC Main.yaml' file
        are not a valid string.
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
    "classic_settings_async",
    "yaml_cache",
    "yaml_settings",
    "yaml_settings_async",
]
