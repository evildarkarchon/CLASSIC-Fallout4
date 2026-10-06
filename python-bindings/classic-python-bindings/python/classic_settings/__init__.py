"""Python module for YAML settings cache.

This module provides Rust-accelerated YAML settings caching with both
synchronous and asynchronous APIs. It integrates with the ONE RUNTIME RULE
to ensure all async operations use the shared global Tokio runtime.

# Synchronous API

- `load_settings_sync(key, path)`: Load and cache a YAML file
- `load_batch_sync(paths)`: Load multiple files

# Asynchronous API

- `load_settings_async(key, path)`: Load and cache a YAML file (async)
- `load_batch_async(paths)`: Load multiple files (async)

# Cache Management

- `get_cached(key)`: Get cached settings
- `is_cached(key)`: Check if key exists
- `invalidate(key)`: Remove a key
- `clear_cache()`: Clear all entries
- `cache_size()`: Get number of entries
- `cache_keys()`: Get all keys
- `cache_stats()`: Get cache performance statistics
- `reset_cache_stats()`: Reset hit/miss counters

Example:
    >>> import classic_settings
    >>> # Sync API
    >>> docs = classic_settings.load_settings_sync("game_config", "config.yaml")
    >>> print(docs[0]["game"])
    Fallout4
    >>>
    >>> # Async API
    >>> import asyncio
    >>> async def load_async():
    ...     docs = await classic_settings.load_settings_async("game_config", "config.yaml")
    ...     print(docs[0]["game"])
    >>> asyncio.run(load_async())
    Fallout4
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_settings import (
    RustYamlError,
    RustYamlIOError,
    RustYamlParseError,
    YamlFile,
    YamlOperations,
    __version__,
    cache_keys,
    cache_size,
    cache_stats,
    clear_cache,
    clear_global_yaml_cache,
    coerce_setting_value,
    get_cached,
    invalidate,
    is_cached,
    load_batch_async,
    load_batch_sync,
    load_settings_async,
    load_settings_sync,
    merge_keys,
    reset_cache_stats,
    reset_yaml_cache_stats,
    validate_setting_value,
    yaml_cache_stats,
)

__all__ = [
    "RustYamlError",
    "RustYamlIOError",
    "RustYamlParseError",
    "YamlFile",
    "YamlOperations",
    "__version__",
    "cache_keys",
    "cache_size",
    "cache_stats",
    "clear_cache",
    "clear_global_yaml_cache",
    "coerce_setting_value",
    "get_cached",
    "invalidate",
    "is_cached",
    "load_batch_async",
    "load_batch_sync",
    "load_settings_async",
    "load_settings_sync",
    "merge_keys",
    "reset_cache_stats",
    "reset_yaml_cache_stats",
    "validate_setting_value",
    "yaml_cache_stats",
]
