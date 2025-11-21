"""
Sync wrapper for AsyncYamlSettingsCore providing synchronous YAML settings access.

This module provides both synchronous and asynchronous interfaces to the async-first
YAML settings system with conditional AsyncBridge usage based on context.

Interface Selection:
- Sync methods (e.g., batch_get_settings) use AsyncBridge for GUI contexts
- Async methods (e.g., batch_get_settings_async) should be used directly in CLI/async contexts
- Module-level async functions (yaml_settings_async, classic_settings_async) provide
  convenient async access without needing the cache instance

Usage Patterns:
    # GUI context (Qt workers, GUI initialization)
    from ClassicLib.YamlSettingsCache import yaml_cache, yaml_settings
    result = yaml_cache.batch_get_settings(requests)  # Uses AsyncBridge
    value = yaml_settings(str, YAML.Main, "key")

    # CLI/TUI async context (production async code)
    from ClassicLib.YamlSettingsCache import yaml_cache, yaml_settings_async
    result = await yaml_cache.batch_get_settings_async(requests)  # Direct async
    value = await yaml_settings_async(str, YAML.Main, "key")

    # Testing/benchmarking (sync context, CLI mode)
    from ClassicLib.YamlSettingsCache import yaml_cache
    result = yaml_cache.batch_get_settings(requests)  # Works via asyncio.run() fallback

Performance Notes:
- CLI production code should use async methods directly for best performance
- GUI contexts automatically use AsyncBridge (lazy initialized)
- Sync methods in CLI mode use asyncio.run() fallback (valid for testing only)
"""

import asyncio
import logging
import threading
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.AsyncYamlSettings.core import (
    AsyncYamlSettingsCore,
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

logger = logging.getLogger(__name__)

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
        """Initialize the sync wrapper with lazy AsyncBridge and async core.

        Both AsyncBridge and async core are initialized lazily only when needed.
        This prevents event loop conflicts in testing contexts.
        """
        self._bridge: AsyncBridge | None = None
        self._async_core: AsyncYamlSettingsCore | None = None
        self._init_lock = threading.RLock()

    def _get_bridge(self) -> AsyncBridge:
        """Get or create AsyncBridge instance lazily.

        AsyncBridge is only created when needed (GUI contexts or sync methods).
        This avoids unnecessary event loop creation in pure async contexts.

        Returns:
            AsyncBridge: The AsyncBridge instance for this cache.
        """
        if self._bridge is None:
            with self._init_lock:
                # Double-check pattern
                if self._bridge is None:
                    self._bridge = AsyncBridge.get_instance()
        return self._bridge

    def _get_async_core(self) -> AsyncYamlSettingsCore:
        """Get or create AsyncYamlSettingsCore instance lazily (sync contexts only).

        This method initializes the async core on first access, using AsyncBridge
        to handle event loop management. Use this ONLY from sync methods (GUI contexts).
        For async contexts, use _ensure_async_core_async() instead.

        Returns:
            AsyncYamlSettingsCore: The async core instance for this cache.
        """
        if self._async_core is None:
            with self._init_lock:
                # Double-check pattern
                if self._async_core is None:
                    # Use AsyncBridge to run async initialization
                    # This works in sync contexts (GUI)
                    self._async_core = self._get_bridge().run_async(get_async_yaml_core())
        return self._async_core

    async def _ensure_async_core_async(self) -> AsyncYamlSettingsCore:
        """Get or create AsyncYamlSettingsCore instance lazily (async contexts).

        This method initializes the async core on first access without using AsyncBridge,
        making it suitable for async contexts (CLI, tests) where an event loop is already running.

        Returns:
            AsyncYamlSettingsCore: The async core instance for this cache.
        """
        # No lock needed in async context - await is atomic enough
        # and we're running in single-threaded async context
        if self._async_core is None:
            # Directly await initialization without AsyncBridge
            self._async_core = await get_async_yaml_core()
        return self._async_core

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
        return self._get_async_core().file_ops.get_path_for_store(yaml_store)

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
        core = await self._ensure_async_core_async()
        return await core.file_ops.load_yaml_file(yaml_path)

    def load_yaml(self, yaml_path: Path) -> YAMLMapping:
        """
        Loads a YAML file asynchronously and returns its parsed content.

        This function uses the AsyncBridge to execute the asynchronous file
        operation for loading a YAML file in a synchronous context. It reads
        the YAML file specified by the provided path and returns its contents
        as a mapping.

        Note: For CLI production code, use load_yaml_async() directly instead.

        Args:
            yaml_path (Path): The file path of the YAML file to be loaded.

        Returns:
            YAMLMapping: The parsed YAML content as a mapping.
        """
        # Load through file_ops using AsyncBridge (lazy initialization)
        return self._get_bridge().run_async(self._get_async_core().file_ops.load_yaml_file(yaml_path))

    def async_yaml_settings(self, _type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
        """
        Updates or retrieves a value from a YAML configuration asynchronously.

        This method allows for either updating a specific value in a YAML file or
        retrieving its current value. It leverages asynchronous processing to ensure
        efficiency and non-blocking behavior. The method interacts with a provided
        YAML object, modifies or fetches the value based on the key path provided,
        and optionally takes a new value for updating.

        Note: For CLI production code, use the async core methods directly with await.

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
        return self._get_bridge().run_async(self._get_async_core().async_yaml_settings(_type, yaml_store, key_path, new_value))

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
        core = await self._ensure_async_core_async()
        results = {}
        for store in stores:
            path = core.file_ops.get_path_for_store(store)
            results[store] = await core.file_ops.load_yaml_file(path)
        return results

    def load_multiple_stores(self, stores: list[YAML]) -> dict[YAML, YAMLMapping]:
        """
        Loads multiple YAML stores synchronously.

        This method takes a list of YAML stores and loads them synchronously,
        returning a dictionary that maps each input YAML store to its
        corresponding YAML mapping.

        Note: For CLI production code, use load_multiple_stores_async() directly.

        Args:
            stores (list[YAML]): A list of YAML store objects to be loaded.

        Returns:
            dict[YAML, YAMLMapping]: A dictionary mapping each input YAML store
                to its respective YAML mapping.
        """
        return self._get_bridge().run_async(self.load_multiple_stores_async(stores))

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
        core = await self._ensure_async_core_async()
        return await core.batch_get_settings(requests)

    def batch_get_settings(self, requests: list[tuple[type, YAML, str]]) -> list[Any]:
        """
        Retrieves a batch of settings asynchronously using the provided requests.

        This method processes a list of requests, where each request is a tuple containing
        a type identifier, a YAML object, and a string. It returns the results of these
        settings requests encapsulated in a list.

        Note: For CLI production code, use batch_get_settings_async() directly.

        Args:
            requests (list[tuple[type, YAML, str]]): A list of tuples representing the
                settings requests to process. Each tuple contains a type, configuration
                details as a YAML object, and a string identifier.

        Returns:
            list[Any]: A list containing the results of the processed settings requests.
        """
        return self._get_bridge().run_async(self._get_async_core().batch_get_settings(requests))

    def prefetch_all_settings(self) -> None:
        """
        Loads and caches specified YAML stores in a file cache for the application.

        This method prefetches the main YAML stores (Main, Settings, and Game) by invoking
        the file loading mechanism. If any of these stores do not exist or cause an
        exception during loading, the method gracefully logs the error without stopping
        the process. It ensures the file contents are cached for future access.

        Note: This is typically called during GUI initialization. For CLI, consider using
        async prefetching if available.

        Raises:
            Exception: If any unexpected error occurs during the file loading process. However,
                       the error is logged, and the process continues for other stores.
        """
        from ClassicLib.Constants import YAML

        # Load the three main YAML stores into file cache
        stores_to_prefetch = [YAML.Main, YAML.Settings, YAML.Game]

        for store in stores_to_prefetch:
            try:
                file_path = self._get_async_core().file_ops.get_path_for_store(store)
                # Trigger file load which will cache it (uses lazy bridge initialization)
                self._get_bridge().run_async(self._get_async_core().file_ops.load_yaml_file(file_path, use_cache=True))
            except Exception as e:  # noqa: BLE001
                # Broad catch is intentional: prefetch is best-effort and should never crash.
                # Possible exceptions: FileNotFoundError, PermissionError, YAML parse errors, etc.
                # Log but don't fail - some stores might not exist
                from ClassicLib.Logger import logger

                logger.debug(f"Could not prefetch {store}: {e}")

    @staticmethod
    def get_metrics() -> dict[str, int]:
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
        return self._get_async_core().cache

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
        return self._get_async_core().cache.path_cache

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
        return self._get_async_core().cache.settings_cache

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
        return self._get_async_core().cache.file_mod_times


# Lazy initialization - don't create at module load time
_yaml_cache = None


def _get_yaml_cache() -> YamlSettingsCache:
    """
    Retrieves or initializes the singleton instance of the YAML settings cache.

    This function manages a global cache for YAML settings, ensuring that only
    a single instance of the cache is created and reused. It initializes the
    cache if it does not already exist and registers it with the appropriate
    keys.

    Returns:
        YamlSettingsCache: The singleton instance of the YAML settings cache.
    """
    global _yaml_cache  # noqa: PLW0603
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

    def __init__(self) -> None:
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

    def __getattr__(self, name: str) -> Any:
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

    def __call__(self) -> YamlSettingsCache:
        """
        Callable class instance method that retrieves and returns a cached YAML object.
        This method is intended to provide quick access to preprocessed YAML data
        from a private cache.

        Returns:
            YamlSettingsCache: The singleton YAML cache instance.
        """
        return _get_yaml_cache()


# Create module-level instance that acts like the original yaml_cache
yaml_cache = _YamlCacheProxy()


# ==========================================
# Module-level convenience functions
# ==========================================


def _raise_async_context_error(yaml_store: YAML, key_path: str) -> None:
    """
    Raises a RuntimeError when yaml_settings is called from an async context.

    Args:
        yaml_store: The YAML store being accessed.
        key_path: The key path being requested.

    Raises:
        RuntimeError: Always raises with details about the invalid call.
    """
    raise RuntimeError(
        "yaml_settings() called from async context. Use 'await yaml_settings_async()' instead.\n"
        f"Location: yaml_store={yaml_store}, key_path={key_path}"
    )


def yaml_settings[T](_type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
    """
    Manages YAML settings by retrieving or updating a specific setting.

    This function provides synchronous access to YAML configuration data.
    It retrieves or updates a setting based on the provided key path.

    Note: If called from an async context, this will raise a RuntimeError.
    Use yaml_settings_async() instead in async contexts.

    Args:
        _type: The expected type of the setting value
        yaml_store: The YAML store to access
        key_path: The dot-delimited path to the setting
        new_value: Optional new value to set

    Returns:
        The setting value, properly typed

    Raises:
        RuntimeError: If called from within an async context
    """
    # Check if we're in an async context
    try:
        asyncio.get_running_loop()
        # If we get here, we're in an async context
        _raise_async_context_error(yaml_store, key_path)
    except RuntimeError as e:
        # Re-raise our custom error
        if "yaml_settings() called from async context" in str(e):
            raise
        # If it's the "no running event loop" RuntimeError, we're in sync context - continue

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
