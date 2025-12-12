"""Synchronous YAML settings cache with singleton support.

This module provides the YamlSettingsCache class, a sync wrapper around
the async YAML settings system. It handles AsyncBridge integration for
GUI contexts and provides a singleton pattern for efficient settings access.

Classes:
    YamlSettingsCache: Singleton sync wrapper for YAML settings.

Example:
    >>> from ClassicLib.YamlSettings.sync.cache import YamlSettingsCache
    >>> cache = YamlSettingsCache.get_instance()
    >>> value = cache.get(str, "CLASSIC_Settings.VR Mode")

"""

import logging
import threading
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.Constants import YAML
from ClassicLib.YamlSettings.async_.core import (
    AsyncYamlSettingsCore,
    get_async_yaml_core,
)
from ClassicLib.YamlSettings.types import YAMLMapping

logger = logging.getLogger(__name__)

T = TypeVar("T")


class YamlSettingsCache:
    """Synchronous wrapper for async YAML settings with singleton support.

    This class provides synchronous access to the async-first YAML settings
    system, with conditional AsyncBridge usage based on context. It implements
    the singleton pattern to ensure only one instance manages YAML settings.

    Attributes:
        _instance: Class-level singleton instance (or None if not yet created).
        _lock: Class-level lock for thread-safe singleton creation.
        _bridge: AsyncBridge instance for sync-to-async bridging (lazily created).
        _async_core: AsyncYamlSettingsCore for actual YAML operations (lazily created).
        _init_lock: Instance-level lock for lazy initialization.

    Interface Selection:
        - Sync methods (e.g., batch_get_settings) use AsyncBridge for GUI contexts
        - Async methods (e.g., batch_get_settings_async) should be used directly in
          CLI/async contexts
        - For CLI production code, use async methods directly with await

    Example:
        Using the singleton instance:

        >>> from ClassicLib.YamlSettings.sync.cache import YamlSettingsCache
        >>> cache = YamlSettingsCache.get_instance()
        >>> value = cache.async_yaml_settings(str, YAML.Main, "CLASSIC_Info.version")

        Using with yaml_cache proxy:

        >>> from ClassicLib.YamlSettings import yaml_cache
        >>> cache = yaml_cache()
        >>> value = cache.async_yaml_settings(str, YAML.Main, "CLASSIC_Info.version")

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
            The AsyncBridge instance for this cache.

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
            The async core instance for this cache.

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

        This method initializes the async core without using AsyncBridge,
        making it suitable for async contexts (CLI, tests) where an event
        loop is already running.

        Returns:
            The async core instance for this cache.

        """
        # No lock needed in async context - await is atomic enough
        # and we're running in single-threaded async context
        if self._async_core is None:
            # Directly await initialization without AsyncBridge
            self._async_core = await get_async_yaml_core()
        return self._async_core

    @classmethod
    def get_instance(cls) -> "YamlSettingsCache":
        """Get or create the singleton instance.

        Implements the Singleton design pattern with thread safety using
        double-checked locking for performance optimization.

        Returns:
            The singleton YamlSettingsCache instance.

        Example:
            >>> cache = YamlSettingsCache.get_instance()
            >>> # Same instance returned on subsequent calls
            >>> cache2 = YamlSettingsCache.get_instance()
            >>> assert cache is cache2

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
        """Get the file path for a given YAML store.

        Args:
            yaml_store: The YAML store object for which the file path is required.

        Returns:
            The file system path corresponding to the given YAML store.

        """
        return self._get_async_core().file_ops.get_path_for_store(yaml_store)

    async def load_yaml_async(self, yaml_path: Path) -> YAMLMapping:
        """Asynchronously load a YAML file.

        Args:
            yaml_path: The path to the YAML file to be loaded.

        Returns:
            The parsed contents of the YAML file as a mapping.

        Raises:
            Exception: If an error occurs during file operations or parsing.

        """
        core = await self._ensure_async_core_async()
        return await core.file_ops.load_yaml_file(yaml_path)

    def load_yaml(self, yaml_path: Path) -> YAMLMapping:
        """Load a YAML file synchronously.

        Uses AsyncBridge to execute the async file operation in a sync context.

        Note:
            For CLI production code, use load_yaml_async() directly instead.

        Args:
            yaml_path: The file path of the YAML file to be loaded.

        Returns:
            The parsed YAML content as a mapping.

        """
        return self._get_bridge().run_async(self._get_async_core().file_ops.load_yaml_file(yaml_path))

    def async_yaml_settings(self, _type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
        """Read or write a YAML setting synchronously.

        Updates or retrieves a value from a YAML configuration. Uses AsyncBridge
        to execute async operations in sync contexts.

        Note:
            For CLI production code, use the async core methods directly with await.

        Args:
            _type: The type hint for the value to be retrieved or updated.
            yaml_store: A YAML instance representing the configuration store.
            key_path: The path within the YAML structure (e.g., "section.key").
            new_value: Optional new value to set. Defaults to None for read operations.

        Returns:
            The value retrieved or the updated value, or None if not found.

        """
        return self._get_bridge().run_async(self._get_async_core().async_yaml_settings(_type, yaml_store, key_path, new_value))

    async def load_multiple_stores_async(self, stores: list[YAML]) -> dict[YAML, YAMLMapping]:
        """Asynchronously load multiple YAML stores.

        Args:
            stores: A list of YAML store identifiers to load.

        Returns:
            A dictionary mapping each input YAML store to its loaded content.

        """
        core = await self._ensure_async_core_async()
        results = {}
        for store in stores:
            path = core.file_ops.get_path_for_store(store)
            results[store] = await core.file_ops.load_yaml_file(path)
        return results

    def load_multiple_stores(self, stores: list[YAML]) -> dict[YAML, YAMLMapping]:
        """Load multiple YAML stores synchronously.

        Note:
            For CLI production code, use load_multiple_stores_async() directly.

        Args:
            stores: A list of YAML store objects to be loaded.

        Returns:
            A dictionary mapping each input YAML store to its mapping.

        """
        return self._get_bridge().run_async(self.load_multiple_stores_async(stores))

    async def batch_get_settings_async(self, requests: list[tuple[type, YAML, str]]) -> list[Any]:
        """Execute batch async retrieval of settings.

        Args:
            requests: A list of tuples (type, YAML store, key path).

        Returns:
            A list containing the results for each request.

        """
        core = await self._ensure_async_core_async()
        return await core.batch_get_settings(requests)

    def batch_get_settings(self, requests: list[tuple[type, YAML, str]]) -> list[Any]:
        """Retrieve a batch of settings synchronously.

        Note:
            For CLI production code, use batch_get_settings_async() directly.

        Args:
            requests: A list of tuples (type, YAML store, key path).

        Returns:
            A list containing the results for each request.

        """
        return self._get_bridge().run_async(self._get_async_core().batch_get_settings(requests))

    def prefetch_all_settings(self) -> None:
        """Load and cache the main YAML stores.

        Prefetches Main, Settings, and Game YAML stores into the cache.
        Errors are logged but don't stop the process.

        Note:
            This is typically called during GUI initialization. For CLI,
            consider using async prefetching if available.

        """
        # Load the three main YAML stores into file cache
        stores_to_prefetch = [YAML.Main, YAML.Settings, YAML.Game]

        for store in stores_to_prefetch:
            try:
                file_path = self._get_async_core().file_ops.get_path_for_store(store)
                # Trigger file load which will cache it
                self._get_bridge().run_async(self._get_async_core().file_ops.load_yaml_file(file_path, use_cache=True))
            except (OSError, FileNotFoundError, ValueError, RuntimeError, AttributeError) as e:
                # Prefetch is best-effort: file system, parsing, or initialization errors are logged but don't crash
                logger.debug(f"Could not prefetch {store}: {e}")

    @staticmethod
    def get_metrics() -> dict[str, int]:
        """Get cache metrics.

        Returns:
            An empty dictionary (metrics not currently implemented).

        """
        return {}

    @property
    def cache(self) -> Any:
        """Get the cache instance from the async core.

        Returns:
            The cache instance from the async core.

        """
        return self._get_async_core().cache

    @property
    def path_cache(self) -> dict:
        """Get the current path cache.

        Returns:
            A dictionary containing the cached path data.

        """
        return self._get_async_core().cache.path_cache

    @property
    def settings_cache(self) -> dict:
        """Get the current settings cache.

        Returns:
            A dictionary containing the cached settings.

        """
        return self._get_async_core().cache.settings_cache

    @property
    def file_mod_times(self) -> dict:
        """Get file modification times from the cache.

        Returns:
            A dictionary mapping file paths to modification timestamps.

        """
        return self._get_async_core().cache.file_mod_times


__all__ = ["YamlSettingsCache"]
