"""
A utility module for managing cached YAML file data with file monitoring.

This module provides a caching system that manages YAML file reads efficiently
by maintaining an in-memory cache. It supports features like file modification
detection, time-to-live management, and performance tracking using metrics.
Thread-safety is ensured for concurrent access.

Classes:
    YamlCache: Utility class to handle YAML caching, file modification checks,
    and performance analytics.
"""

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ClassicLib.Constants import YAML


class YamlCache:
    """
    YamlCache is a utility class to manage YAML file caching efficiently.

    This class is designed to optimize the performance of file reads and lookups
    by providing thread-safe in-memory caching with customizable time-to-live (TTL)
    and modification detection mechanisms. It tracks file states, manages cache
    entries, and supports performance-related metrics for cache usage analysis.

    Attributes:
        CACHE_TTL (float): Cache time-to-live in seconds (default is 300.0).
        cache (dict[str, Any]): In-memory cache for storing file or data objects.
        file_mod_times (dict[str, float]): Tracks the last modification timestamps
            of files.
        path_cache (dict[tuple[YAML, str | None], Path]): Cache for resolved file
            paths based on YAML objects and optional base paths.
        settings_cache (dict[tuple[type, YAML, str], Any]): Cache for specific
            processed YAML file settings.
        last_check_time (float): Timestamp of the most recent cache TTL check.
    """

    # Cache TTL in seconds (5 minutes default)
    CACHE_TTL: ClassVar[float] = 300.0

    # Class-level locks for thread safety
    _cache_locks: ClassVar[dict[str, asyncio.Lock]] = {}
    _global_lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __init__(self) -> None:
        # noinspection PyUnresolvedReferences
        """
                Represents a caching mechanism for storing and tracking the modification times
                of files, as well as maintaining paths and settings cache. This class is
                designed to handle caching required in scenarios where frequent reads or
                updates may occur to reduce redundant operations.

                Attributes:
                    cache (dict[str, Any]): Stores cached data with string keys and their
                        respective values of any type.
                    file_mod_times (dict[str, float]): Tracks the modification times of files
                        using their file paths as keys and the corresponding modification
                        times as floating-point values.
                    path_cache (dict[tuple[YAML, str | None], Path]): Caches relationships
                        between tuple keys (containing YAML and an optional string) and their
                        corresponding file paths.
                    settings_cache (dict[tuple[type, YAML, str], Any]): Caches settings data
                        mapped by a tuple key containing the type, YAML, and string identifiers.
                    last_check_time (float): The timestamp of the last file or cache check,
                        represented as a floating-point value.
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
        """
        Asynchronously obtains a lock for a specific file path. This ensures that operations on the same file path
        do not overlap and are thread-safe. If the lock for the file path does not exist yet, it is created and
        stored safely using a global lock to avoid race conditions.

        Args:
            file_path (str): The file path for which the lock needs to be obtained.

        Returns:
            asyncio.Lock: The lock associated with the specified file path.
        """
        if file_path not in self._cache_locks:
            async with self._global_lock:
                # Double-check after acquiring global lock
                if file_path not in self._cache_locks:
                    self._cache_locks[file_path] = asyncio.Lock()
        return self._cache_locks[file_path]

    async def check_file_modification(self, file_path: Path) -> bool:
        """
        Checks if a file has been modified since the last recorded check or if the
        cache time-to-live (TTL) has expired.

        This function compares the file's last modification time with the previously
        cached modification time. If the file has been modified, or if the cache TTL
        has expired, it updates the cached modification time and returns True.
        Otherwise, it returns False.

        Args:
            file_path (Path): The path of the file to check.

        Returns:
            bool: True if the file has been modified or the cache TTL has expired,
            otherwise False.

        Raises:
            FileNotFoundError: If the file doesn't exist or cannot be accessed.
            OSError: If the file is inaccessible for other reasons.
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
        """
        Retrieves a copy of the metrics dictionary.

        Returns:
            dict[str, int]: A dictionary containing the metrics as key-value pairs
            where keys are strings representing metric names, and values are integers
            representing metric values.
        """
        return self._metrics.copy()

    def update_metrics(self, metric: str, increment: int = 1) -> None:
        """
        Updates the specified metric by incrementing its value.

        This method increases the value of a metric by a specified increment. If the
        metric exists in the underlying collection, its value is incremented.

        Args:
            metric (str): The name of the metric to update.
            increment (int, optional): The value by which to increase the metric. Defaults to 1.
        """
        if metric in self._metrics:
            self._metrics[metric] += increment

    def clear_cache(self, store: str | None = None) -> None:
        """
        Clears the cache for a specific store or all caches.

        If a store is specified, only the cache entries related to that store will
        be removed. This includes entries from the main cache and related settings
        cache. If no store is provided, all caches and related data will be cleared.

        Args:
            store: The store identifier for which the cache should be cleared. If None,
                all caches will be cleared.

        """
        if store:
            # Clear specific store
            keys_to_remove = [k for k in self.cache.keys() if k == store]  # noqa: SIM118
            for key in keys_to_remove:
                del self.cache[key]

            # Clear related settings cache entries
            settings_keys_to_remove = [
                k for k in self.settings_cache.keys()  # noqa: SIM118
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
