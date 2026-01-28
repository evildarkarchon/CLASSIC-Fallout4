"""YAML cache manager for async settings operations.

This module provides a caching system for YAML file data with file monitoring,
TTL-based expiration, and performance metrics tracking. It ensures thread-safety
for concurrent access in async contexts.

Classes:
    YamlCache: Utility class for caching YAML data with modification detection.

Example:
    >>> from ClassicLib.YamlSettings.async_.cache import YamlCache
    >>> cache = YamlCache()
    >>> is_modified = await cache.check_file_modification(Path("settings.yaml"))
    >>> if is_modified:
    ...     # Reload file from disk
    ...     pass

"""

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ClassicLib.core.constants import YAML


class YamlCache:
    """Manage YAML file caching with modification detection and metrics.

    This class optimizes file read performance by providing thread-safe
    in-memory caching with customizable time-to-live (TTL) and modification
    detection mechanisms. It tracks file states, manages cache entries,
    and supports performance-related metrics for cache usage analysis.

    Attributes:
        CACHE_TTL: Class variable for cache time-to-live in seconds (default 300.0).
        cache: In-memory cache for storing file or data objects.
        file_mod_times: Tracks last modification timestamps of files.
        path_cache: Cache for resolved file paths based on YAML objects.
        settings_cache: Cache for specific processed YAML file settings.
        last_check_time: Timestamp of the most recent cache TTL check.

    Example:
        >>> cache = YamlCache()
        >>> # Check if file was modified
        >>> modified = await cache.check_file_modification(Path("config.yaml"))
        >>> # Get metrics
        >>> metrics = cache.get_metrics()
        >>> print(f"Cache hits: {metrics['cache_hits']}")

    """

    # Cache TTL in seconds (5 minutes default)
    CACHE_TTL: ClassVar[float] = 300.0

    # Class-level locks for thread safety
    _cache_locks: ClassVar[dict[str, asyncio.Lock]] = {}
    _global_lock: ClassVar[asyncio.Lock | None] = None  # Lazy init to avoid creating Lock outside async context

    def __init__(self) -> None:
        """Initialize the cache with empty storage containers.

        Creates empty dictionaries for the main cache, file modification times,
        path cache, and settings cache. Also initializes metrics tracking for
        cache performance analysis.
        """
        self.cache: dict[str, Any] = {}
        self.file_mod_times: dict[str, float] = {}
        self.path_cache: dict[tuple[YAML, str | None], Path] = {}
        self.settings_cache: dict[tuple[type, YAML, str], Any] = {}
        self.last_check_time: float = 0

        # Metrics tracking
        self._metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "file_reloads": 0,
            "total_reads": 0,
        }

    async def get_file_lock(self, file_path: str) -> asyncio.Lock:
        """Get or create a file-specific lock for thread-safe operations.

        Ensures that operations on the same file path do not overlap and are
        thread-safe. If the lock for the file path does not exist yet, it is
        created and stored safely using a global lock to avoid race conditions.

        Args:
            file_path: The file path for which the lock needs to be obtained.

        Returns:
            The lock associated with the specified file path.

        Example:
            >>> lock = await cache.get_file_lock("/path/to/config.yaml")
            >>> async with lock:
            ...     # Safely access the file
            ...     pass

        """
        if file_path not in self._cache_locks:
            # Lazy initialize global lock on first use (inside async context)
            if self._global_lock is None:
                YamlCache._global_lock = asyncio.Lock()
            async with self._global_lock:  # pyright: ignore[reportOptionalContextManager]
                # Double-check after acquiring global lock
                if file_path not in self._cache_locks:
                    self._cache_locks[file_path] = asyncio.Lock()
        return self._cache_locks[file_path]

    async def check_file_modification(self, file_path: Path) -> bool:
        """Check if a file has been modified since last access.

        Compares the file's last modification time with the previously cached
        modification time. If the file has been modified, or if the cache TTL
        has expired, it updates the cached modification time and returns True.
        Otherwise, it returns False.

        Args:
            file_path: The path of the file to check.

        Returns:
            True if the file has been modified or the cache TTL has expired,
            False otherwise.

        Note:
            Returns True (indicating reload needed) if the file doesn't exist
            or cannot be accessed, to ensure fresh data is loaded when possible.

        Example:
            >>> if await cache.check_file_modification(Path("settings.yaml")):
            ...     # File changed, reload from disk
            ...     data = await load_file(path)

        """
        try:
            stat_result = await asyncio.to_thread(file_path.stat)
            current_mod_time = stat_result.st_mtime
        except (FileNotFoundError, OSError):
            # File doesn't exist or can't be accessed
            return True

        file_key = str(file_path)
        last_mod_time = self.file_mod_times.get(file_key, 0)

        if current_mod_time > last_mod_time:
            self.file_mod_times[file_key] = current_mod_time
            return True

        # Also check if cache TTL expired
        current_time = time.time()
        if current_time - self.last_check_time > self.CACHE_TTL:
            self.last_check_time = current_time
            return True

        return False

    def get_metrics(self) -> dict[str, int]:
        """Get a copy of the cache performance metrics.

        Returns:
            A dictionary containing cache metrics:
            - cache_hits: Number of successful cache lookups
            - cache_misses: Number of cache misses requiring file reads
            - file_reloads: Number of times files were reloaded due to changes
            - total_reads: Total number of read operations

        Example:
            >>> metrics = cache.get_metrics()
            >>> hit_rate = metrics["cache_hits"] / max(metrics["total_reads"], 1)

        """
        return self._metrics.copy()

    def update_metrics(self, metric: str, increment: int = 1) -> None:
        """Update a specific metric by incrementing its value.

        Args:
            metric: The name of the metric to update. Must be one of:
                "cache_hits", "cache_misses", "file_reloads", "total_reads".
            increment: The value by which to increase the metric. Defaults to 1.

        Example:
            >>> cache.update_metrics("cache_hits")
            >>> cache.update_metrics("total_reads", 5)

        """
        if metric in self._metrics:
            self._metrics[metric] += increment

    def clear_cache(self, store: str | None = None) -> None:
        """Clear cache entries for a specific store or all caches.

        If a store is specified, only the cache entries related to that store
        will be removed. This includes entries from the main cache and related
        settings cache. If no store is provided, all caches and related data
        will be cleared.

        Args:
            store: The store identifier for which the cache should be cleared.
                If None, all caches will be cleared.

        Example:
            >>> cache.clear_cache("CLASSIC_Settings")  # Clear specific store
            >>> cache.clear_cache()  # Clear all caches

        """
        if store:
            # Clear specific store
            keys_to_remove = [k for k in self.cache.keys() if k == store]  # noqa: SIM118
            for key in keys_to_remove:
                del self.cache[key]

            # Clear related settings cache entries
            settings_keys_to_remove = [
                k
                for k in self.settings_cache.keys()  # noqa: SIM118
                if str(k[1]) == store
            ]
            for key in settings_keys_to_remove:
                del self.settings_cache[key]
        else:
            # Clear all caches
            self.cache.clear()
            self.settings_cache.clear()
            self.path_cache.clear()
            self.file_mod_times.clear()
            self.last_check_time = 0


__all__ = ["YamlCache"]
