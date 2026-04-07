"""Type stubs for classic_settings.

Python bindings for classic-settings-core, providing Rust-accelerated YAML settings
caching with both synchronous and asynchronous APIs.

Architecture:
    - classic-settings-core: Business logic (YAML caching, batch loading)
    - classic-settings-py: Python bindings (this module - PyO3 adapters)

Features:
    - Thread-safe settings cache with DashMap
    - Synchronous and asynchronous loading
    - Batch loading for multiple files
    - Cache invalidation and management

Usage:
    import classic_settings

    # Synchronous API
    docs = classic_settings.load_settings_sync("config", "config.yaml")
    print(docs[0]["key"])

    # Asynchronous API
    import asyncio
    async def load_async():
        docs = await classic_settings.load_settings_async("config", "config.yaml")
        print(docs[0]["key"])
    asyncio.run(load_async())

    # Cache management
    if classic_settings.is_cached("config"):
        cached = classic_settings.get_cached("config")
"""

from typing import Any, TypedDict

__version__: str

class SettingsCacheStats(TypedDict):
    """Canonical settings cache statistics contract."""

    hits: int
    misses: int
    hit_rate: float
    size: int
    capacity: int

def load_settings_sync(key: str, path: str) -> list[dict[str, Any]]:
    """Load YAML settings synchronously.

    Loads a YAML file, caches it with the given key, and returns the parsed
    documents as Python objects (dicts/lists).

    Args:
        key: Cache key (typically the file path or a logical name).
        path: Path to the YAML file.

    Returns:
        List of parsed YAML documents as Python objects.

    Raises:
        IOError: If the file cannot be read.
        ValueError: If the YAML is invalid.

    Example:
        >>> docs = load_settings_sync("config", "config.yaml")
        >>> print(docs[0]["key"])
        'value'

    """

async def load_settings_async(key: str, path: str) -> list[dict[str, Any]]:
    """Load YAML settings asynchronously.

    Loads a YAML file asynchronously, caches it with the given key, and returns
    the parsed documents as Python objects (dicts/lists).

    Args:
        key: Cache key (typically the file path or a logical name).
        path: Path to the YAML file.

    Returns:
        Coroutine that yields a list of parsed YAML documents as Python objects.

    Raises:
        IOError: If the file cannot be read.
        ValueError: If the YAML is invalid.

    Example:
        >>> import asyncio
        >>> docs = await load_settings_async("config", "config.yaml")
        >>> print(docs[0]["key"])
        'value'

    """

def load_batch_sync(paths: list[str]) -> int:
    """Load multiple YAML files in batch (synchronous).

    Loads multiple YAML files and caches them. Each path becomes its own cache key.

    Args:
        paths: List of file paths to load.

    Returns:
        Number of files successfully loaded and cached.

    Raises:
        IOError: If any file cannot be read.
        ValueError: If any YAML is invalid.

    Example:
        >>> count = load_batch_sync(["config1.yaml", "config2.yaml"])
        >>> print(f"Loaded {count} files")
        Loaded 2 files

    """

async def load_batch_async(paths: list[str]) -> int:
    """Load multiple YAML files in batch (asynchronous).

    Loads multiple YAML files concurrently and caches them. Each path becomes
    its own cache key.

    Args:
        paths: List of file paths to load.

    Returns:
        Coroutine that yields the number of files successfully loaded and cached.

    Raises:
        IOError: If any file cannot be read.
        ValueError: If any YAML is invalid.

    Example:
        >>> count = await load_batch_async(["config1.yaml", "config2.yaml"])
        >>> print(f"Loaded {count} files")
        Loaded 2 files

    """

def get_cached(key: str) -> list[dict[str, Any]] | None:
    """Get cached settings by key.

    Retrieves cached YAML documents by key. Returns None if the key is not in the cache.

    Args:
        key: Cache key to look up.

    Returns:
        List of parsed YAML documents as Python objects, or None if not cached.

    Example:
        >>> load_settings_sync("config", "config.yaml")
        >>> docs = get_cached("config")
        >>> print(docs is not None)
        True

    """

def is_cached(key: str) -> bool:
    """Check if a key exists in the cache.

    Args:
        key: Cache key to check.

    Returns:
        True if the key exists, False otherwise.

    Example:
        >>> load_settings_sync("config", "config.yaml")
        >>> is_cached("config")
        True
        >>> is_cached("nonexistent")
        False

    """

def invalidate(key: str) -> bool:
    """Invalidate (remove) a cached entry.

    Removes a key from the cache. Returns True if the key existed and was removed.

    Args:
        key: Cache key to invalidate.

    Returns:
        True if the key was removed, False if it didn't exist.

    Example:
        >>> load_settings_sync("config", "config.yaml")
        >>> invalidate("config")
        True
        >>> is_cached("config")
        False

    """

def clear_cache() -> None:
    """Clear all cached settings.

    Removes all entries from the cache.

    Example:
        >>> load_settings_sync("config1", "config1.yaml")
        >>> load_settings_sync("config2", "config2.yaml")
        >>> clear_cache()
        >>> cache_size()
        0

    """

def cache_size() -> int:
    """Get the number of cached entries.

    Returns:
        The number of entries currently in the cache.

    Example:
        >>> load_settings_sync("config", "config.yaml")
        >>> cache_size()
        1

    """

def cache_keys() -> list[str]:
    """Get all cache keys.

    Returns:
        List of all keys currently in the cache.

    Example:
        >>> load_settings_sync("config1", "config1.yaml")
        >>> load_settings_sync("config2", "config2.yaml")
        >>> keys = cache_keys()
        >>> len(keys)
        2

    """

def cache_stats() -> SettingsCacheStats:
    """Get canonical cache statistics.

    Returns:
        Dictionary with cache statistics:
            - 'hits': Number of cache hits.
            - 'misses': Number of cache misses.
            - 'hit_rate': Hit ratio as a float from 0.0 to 1.0.
            - 'size': Current number of cached entries.
            - 'capacity': Maximum retained cache entries.

    Example:
        >>> stats = cache_stats()
        >>> print(stats["capacity"])
        64

    """

def reset_cache_stats() -> None:
    """Reset cache hit and miss counters.

    Example:
        >>> reset_cache_stats()
        >>> cache_stats()["hits"]
        0

    """
