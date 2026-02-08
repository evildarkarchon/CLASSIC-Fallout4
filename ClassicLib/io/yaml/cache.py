"""Synchronous YAML settings cache with singleton support.

This module provides the YamlSettingsCache class, a sync wrapper around
the async YAML settings system. It handles AsyncBridge integration for
GUI contexts and provides a singleton pattern for efficient settings access.

The cache operations delegate to Rust classic_settings module for performance
and thread-safety via DashMap-based caching.

Classes:
    YamlSettingsCache: Singleton sync wrapper for YAML settings.

Example:
    >>> from ClassicLib.io.yaml.cache import YamlSettingsCache
    >>> cache = YamlSettingsCache.get_instance()
    >>> value = cache.get(str, "CLASSIC_Settings.VR Mode")

"""

import asyncio
import logging
import os
import threading
from pathlib import Path
from typing import Any, ClassVar, TypeVar

import classic_settings

from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.core.constants import YAML
from ClassicLib.io.yaml.async_.core import (
    AsyncYamlSettingsCore,
    get_async_yaml_core,
)
from ClassicLib.io.yaml.types import YAMLMapping

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

        >>> from ClassicLib.io.yaml.cache import YamlSettingsCache
        >>> cache = YamlSettingsCache.get_instance()
        >>> value = cache.async_yaml_settings(str, YAML.Main, "CLASSIC_Info.version")

        Using with yaml_cache proxy:

        >>> from ClassicLib.io.yaml import yaml_cache
        >>> cache = yaml_cache()
        >>> value = cache.async_yaml_settings(str, YAML.Main, "CLASSIC_Info.version")

    """

    # Class-level storage for singleton instance
    _instance: ClassVar["YamlSettingsCache | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()
    # Async lock for async core initialization (lazily created)
    # Stored as tuple of (lock, event_loop) to detect event loop changes
    _async_init_lock: ClassVar[tuple[asyncio.Lock, asyncio.AbstractEventLoop] | None] = None

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

        Raises:
            RuntimeError: If called from an async context with a running event loop,
                which would cause a deadlock.

        """
        # Detect if called from async context - this would cause deadlock
        try:
            asyncio.get_running_loop()
            # If we get here, there's a running event loop
            msg = (
                "Cannot call sync methods from async context. Use async methods (e.g., load_yaml_async, batch_get_settings_async) instead."
            )
            raise RuntimeError(msg)  # noqa: TRY301 - Intentional: raise inside try to detect async context
        except RuntimeError as e:
            # Check if this is our own exception or the "no running loop" exception
            if "Cannot call sync methods" in str(e):
                raise
            # No running loop - safe to proceed with sync operation

        if self._async_core is None:
            with self._init_lock:
                # Double-check pattern
                if self._async_core is None:
                    # Use AsyncBridge to run async initialization
                    # This works in sync contexts (GUI)
                    self._async_core = self._get_bridge().run_async(get_async_yaml_core())
        return self._async_core

    @classmethod
    def _get_async_init_lock(cls) -> asyncio.Lock:
        """Get or create the async initialization lock lazily.

        This lock protects async core initialization from race conditions
        when multiple concurrent async tasks attempt initialization.

        The lock is bound to the current event loop. If the event loop changes
        (e.g., after asyncio.run() completes and a new one starts), a new lock
        is created for the new event loop to avoid "Lock object is bound to a
        different loop" errors.

        Returns:
            The asyncio.Lock instance for async core initialization.

        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop - this shouldn't happen in async context
            # but handle gracefully by always creating a new lock
            current_loop = None

        # Check if we have a valid lock for the current event loop
        if cls._async_init_lock is not None:
            cached_lock, cached_loop = cls._async_init_lock
            # Reuse lock if event loop matches
            if current_loop is not None and cached_loop is current_loop:
                return cached_lock
            # Event loop changed or no current loop - need a new lock

        # Use threading lock for thread-safe creation of the async lock
        with cls._lock:
            # Double-check after acquiring lock
            if cls._async_init_lock is not None:
                cached_lock, cached_loop = cls._async_init_lock
                if current_loop is not None and cached_loop is current_loop:
                    return cached_lock

            # Check for running event loop before creating lock
            # In Python 3.12+, creating asyncio.Lock() without a running event loop
            # raises RuntimeError or DeprecationWarning (will become error in future)
            if current_loop is None:
                msg = (
                    "_get_async_init_lock() must be called from an async context "
                    "with a running event loop. This method is intended for use "
                    "within _ensure_async_core_async()."
                )
                raise RuntimeError(msg)

            # Create new lock and store with current event loop reference
            new_lock = asyncio.Lock()
            cls._async_init_lock = (new_lock, current_loop)
            return new_lock

    async def _ensure_async_core_async(self) -> AsyncYamlSettingsCore:
        """Get or create AsyncYamlSettingsCore instance lazily (async contexts).

        This method initializes the async core without using AsyncBridge,
        making it suitable for async contexts (CLI, tests) where an event
        loop is already running. Uses an async lock for thread-safety when
        multiple concurrent async tasks attempt initialization.

        Returns:
            The async core instance for this cache.

        """
        # Fast path - already initialized
        if self._async_core is not None:
            return self._async_core

        # Slow path - use async lock for safe initialization
        async with self._get_async_init_lock():
            # Double-check pattern
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

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance - test environments only.

        This method is intended for test isolation to ensure each test starts
        with a fresh instance. It is guarded to only work in pytest environments.
        Also resets the async initialization lock.

        Raises:
            RuntimeError: If called outside of a pytest testing context.

        """
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            msg = "reset_instance() is only allowed in testing contexts"
            raise RuntimeError(msg)
        with cls._lock:
            cls._instance = None
            cls._async_init_lock = None

    def get_path_for_store(self, yaml_store: YAML) -> Path:
        """Get the file path for a given YAML store.

        Args:
            yaml_store: The YAML store object for which the file path is required.

        Returns:
            The file system path corresponding to the given YAML store.

        """
        return self._get_async_core().file_ops.get_path_for_store(yaml_store)

    @staticmethod
    async def load_yaml_async(yaml_path: Path) -> YAMLMapping:
        """Asynchronously load a YAML file using Rust cache.

        Delegates to Rust classic_settings.load_settings_async() for caching.

        Args:
            yaml_path: The path to the YAML file to be loaded.

        Returns:
            The parsed contents of the YAML file as a mapping.

        Raises:
            RuntimeError: If Rust cache loading fails.

        """
        key = str(yaml_path.resolve())  # noqa: ASYNC240
        logger.debug("Loading YAML async via Rust: %s", key)
        try:
            docs = await classic_settings.load_settings_async(key, str(yaml_path))
            return docs[0] if docs else {}
        except Exception as e:
            msg = f"Rust cache load failed for {yaml_path}: {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e

    @staticmethod
    def load_yaml(yaml_path: Path) -> YAMLMapping:
        """Load a YAML file synchronously using Rust cache.

        Delegates to Rust classic_settings.load_settings_sync() for caching.

        Note:
            For CLI production code, use load_yaml_async() directly instead.

        Args:
            yaml_path: The file path of the YAML file to be loaded.

        Returns:
            The parsed YAML content as a mapping.

        Raises:
            RuntimeError: If Rust cache loading fails.

        """
        key = str(yaml_path.resolve())
        logger.debug("Loading YAML sync via Rust: %s", key)
        try:
            docs = classic_settings.load_settings_sync(key, str(yaml_path))
            return docs[0] if docs else {}
        except Exception as e:
            msg = f"Rust cache load failed for {yaml_path}: {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e

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
        return results  # pyright: ignore[reportUnknownVariableType]

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
        """Load and cache the main YAML stores using Rust batch loading.

        Prefetches Main, Settings, and Game YAML stores into the Rust cache.
        Uses Rust load_batch_sync() for efficient batch loading.
        Errors are logged but don't stop the process.

        Note:
            This is typically called during GUI initialization. For CLI,
            consider using async prefetching with load_batch_async().

        """
        # Load the three main YAML stores into Rust cache
        stores_to_prefetch = [YAML.Main, YAML.Settings, YAML.Game]
        paths_to_load: list[str] = []

        for store in stores_to_prefetch:
            try:
                file_path = self._get_async_core().file_ops.get_path_for_store(store)
                paths_to_load.append(str(file_path))
            except (OSError, FileNotFoundError, ValueError, RuntimeError, AttributeError) as e:
                logger.debug("Could not get path for %s: %s", store, e)

        if paths_to_load:
            try:
                count = classic_settings.load_batch_sync(paths_to_load)
                logger.debug("Prefetched %d/%d YAML stores via Rust batch loading", count, len(paths_to_load))
            except Exception as e:  # noqa: BLE001
                # Prefetch is best-effort: errors are logged but don't crash
                logger.debug("Rust batch prefetch failed: %s", e)

    @staticmethod
    def get_metrics() -> dict[str, int]:
        """Get cache metrics.

        Returns:
            An empty dictionary (metrics not currently implemented).

        """
        return {}

    @staticmethod
    def debug_info() -> dict[str, Any]:
        """Return cache debugging information from Rust.

        Provides visibility into the Rust DashMap-based cache state for
        debugging and performance monitoring.

        Returns:
            Dictionary with cache state:
            - cache_size: Number of entries in Rust cache
            - cache_keys: List of all cached keys

        Example:
            >>> info = YamlSettingsCache.debug_info()
            >>> print(f"Cache has {info['cache_size']} entries")

        """
        return {
            "cache_size": classic_settings.cache_size(),
            "cache_keys": classic_settings.cache_keys(),
        }

    @staticmethod
    def invalidate(key: str) -> bool:
        """Invalidate specific cache entry in Rust.

        Removes a single entry from the Rust DashMap cache by key.
        Use this for targeted invalidation after settings changes.

        Args:
            key: Cache key to invalidate (typically str(path.resolve())).

        Returns:
            True if the key was removed, False if it didn't exist.

        Example:
            >>> cache = YamlSettingsCache.get_instance()
            >>> cache.invalidate(str(settings_path.resolve()))

        """
        logger.debug("Invalidating cache key: %s", key)
        return classic_settings.invalidate(key)

    @property
    def cache(self) -> Any:
        """Get the cache instance from the async core.

        Returns:
            The cache instance from the async core.

        """
        return self._get_async_core().cache

    @property
    def path_cache(self) -> dict[str, Path]:
        """Get the current path cache.

        Returns:
            A dictionary containing the cached path data.

        """
        return self._get_async_core().cache.path_cache

    @property
    def settings_cache(self) -> dict[tuple[type, YAML, str], Any]:
        """Get the current settings cache.

        Returns:
            A dictionary containing the cached settings.

        """
        return self._get_async_core().cache.settings_cache

    @property
    def file_mod_times(self) -> dict[Path, float]:
        """Get file modification times from the cache.

        Returns:
            A dictionary mapping file paths to modification timestamps.

        """
        return self._get_async_core().cache.file_mod_times


__all__ = ["YamlSettingsCache"]
