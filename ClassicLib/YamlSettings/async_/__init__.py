"""Async YAML settings submodule.

This submodule provides asynchronous YAML settings management with caching,
file operations, and Rust acceleration support.

Classes:
    AsyncYamlSettingsCore: Main class for async YAML settings operations.
    YamlCache: Cache manager with TTL and modification detection.
    YamlFileOperations: File I/O with optional Rust acceleration.

Functions:
    get_async_yaml_core: Get the singleton AsyncYamlSettingsCore instance.
    yaml_settings_async: Convenience function for async settings access.
    classic_settings_async: Convenience function for CLASSIC_Settings access.

Usage:
    # Direct async usage
    >>> from ClassicLib.YamlSettings.async_ import yaml_settings_async
    >>> value = await yaml_settings_async(str, YAML.Main, "key.path")

    # Using the core class
    >>> from ClassicLib.YamlSettings.async_ import get_async_yaml_core
    >>> core = await get_async_yaml_core()
    >>> value = await core.async_yaml_settings(str, YAML.Main, "key.path")
"""

from ClassicLib.YamlSettings.async_.cache import YamlCache
from ClassicLib.YamlSettings.async_.core import (
    AsyncYamlSettingsCore,
    classic_settings_async,
    get_async_yaml_core,
    yaml_settings_async,
)
from ClassicLib.YamlSettings.async_.file_operations import YamlFileOperations

__all__ = [
    # Core class
    "AsyncYamlSettingsCore",
    # Helper classes
    "YamlCache",
    "YamlFileOperations",
    # Convenience functions
    "classic_settings_async",
    "get_async_yaml_core",
    "yaml_settings_async",
]
