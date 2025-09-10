"""Caching utilities for AsyncYamlSettings."""

import asyncio
import time
from pathlib import Path
from typing import Any, ClassVar

from ClassicLib.Constants import YAML


class YamlCache:
    """Manages caching for YAML settings with TTL and file modification tracking."""

    # Cache TTL in seconds (5 minutes default)
    CACHE_TTL: ClassVar[float] = 300.0

    # Class-level locks for thread safety
    _cache_locks: ClassVar[dict[str, asyncio.Lock]] = {}
    _global_lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __init__(self) -> None:
        """Initialize cache structures."""
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
        Get or create a lock for a specific file path.

        Uses double-checked locking pattern for thread safety.
        """
        if file_path not in self._cache_locks:
            async with self._global_lock:
                # Double-check after acquiring global lock
                if file_path not in self._cache_locks:
                    self._cache_locks[file_path] = asyncio.Lock()
        return self._cache_locks[file_path]

    async def check_file_modification(self, file_path: Path) -> bool:
        """
        Check if a file has been modified since last check.

        Args:
            file_path: Path to check

        Returns:
            True if file was modified, False otherwise
        """
        try:
            current_mod_time = file_path.stat().st_mtime
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
        Get cache performance metrics.

        Returns:
            Dictionary containing cache statistics
        """
        return self._metrics.copy()

    def update_metrics(self, metric: str, increment: int = 1) -> None:
        """
        Update a specific metric.

        Args:
            metric: Metric name to update
            increment: Amount to increment by
        """
        if metric in self._metrics:
            self._metrics[metric] += increment

    def clear_cache(self, store: str | None = None) -> None:
        """
        Clear cache for a specific store or all caches.

        Args:
            store: Optional store name to clear, or None for all
        """
        if store:
            # Clear specific store
            keys_to_remove = [k for k in self.cache.keys() if k == store]
            for key in keys_to_remove:
                del self.cache[key]

            # Clear related settings cache entries
            settings_keys_to_remove = [
                k for k in self.settings_cache.keys()
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
