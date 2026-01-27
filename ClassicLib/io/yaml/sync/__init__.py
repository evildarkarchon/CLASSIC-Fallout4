"""Synchronous YAML settings submodule.

This submodule provides synchronous wrappers for the async YAML settings
system, suitable for GUI contexts and legacy synchronous code.

Classes:
    YamlSettingsCache: Singleton sync wrapper for YAML settings.

Functions:
    yaml_settings: Synchronous settings read/write.
    classic_settings: Synchronous CLASSIC_Settings access.

Objects:
    yaml_cache: Proxy for lazy singleton access.

Usage:
    # Direct sync usage
    >>> from ClassicLib.YamlSettings.sync import yaml_settings, classic_settings
    >>> value = yaml_settings(str, YAML.Main, "key.path")
    >>> vr_mode = classic_settings(bool, "VR Mode")

    # Using the cache singleton
    >>> from ClassicLib.YamlSettings.sync import yaml_cache
    >>> cache = yaml_cache()
    >>> value = cache.async_yaml_settings(str, YAML.Main, "key.path")

Note:
    For async/CLI production code, use the async submodule instead:
    >>> from ClassicLib.YamlSettings.async_ import yaml_settings_async

"""

from ClassicLib.io.yaml.sync.cache import YamlSettingsCache
from ClassicLib.io.yaml.sync.convenience import (
    classic_settings,
    yaml_cache,
    yaml_settings,
)

__all__ = [
    # Cache class
    "YamlSettingsCache",
    # Convenience functions
    "classic_settings",
    "yaml_cache",
    "yaml_settings",
]
