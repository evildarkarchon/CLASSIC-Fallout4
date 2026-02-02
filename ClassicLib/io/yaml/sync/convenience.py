"""Synchronous convenience functions for YAML settings access.

This module provides easy-to-use synchronous functions for accessing YAML
settings. It includes the yaml_cache proxy for singleton access and
convenience functions for common settings operations.

Functions:
    yaml_settings: Read or write a YAML setting synchronously.
    classic_settings: Read a CLASSIC_Settings value synchronously.

Objects:
    yaml_cache: Proxy object for lazy singleton access.

Example:
    >>> from ClassicLib.YamlSettings.sync.convenience import yaml_settings, classic_settings
    >>> # Read a setting
    >>> value = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
    >>> # Read a CLASSIC_Settings value
    >>> vr_mode = classic_settings(bool, "VR Mode")

"""

import asyncio
from pathlib import Path
from typing import Any, TypeVar

from ClassicLib.core.constants import YAML
from ClassicLib.core.registry import Keys, is_registered, register
from ClassicLib.io.yaml.sync.cache import YamlSettingsCache

T = TypeVar("T")

# ==========================================
# Lazy singleton management
# ==========================================


def _get_yaml_cache() -> YamlSettingsCache:
    """Get or initialize the singleton YAML settings cache.

    Always delegates to YamlSettingsCache.get_instance() to ensure
    proper singleton behavior, especially in test scenarios where
    _instance may be reset. Also registers with GlobalRegistry on first call.

    Returns:
        The singleton YamlSettingsCache instance.

    """
    cache = YamlSettingsCache.get_instance()
    # Register with GlobalRegistry if not already registered
    if not is_registered(Keys.YAML_CACHE):
        register(Keys.YAML_CACHE, cache)
    return cache


class _YamlCacheProxy:
    """Proxy class for lazy YamlSettingsCache singleton access.

    Acts as a proxy that defers initialization of the cache until first
    attribute access. This allows the module to be imported without
    immediately creating the cache.

    IMPORTANT: The proxy always delegates to YamlSettingsCache.get_instance()
    to properly support test scenarios where _instance is reset.

    Example:
        >>> yaml_cache = _YamlCacheProxy()
        >>> # First attribute access creates the real cache
        >>> yaml_cache.batch_get_settings([...])
        >>> # Or call it to get the singleton directly
        >>> cache = yaml_cache()

    """

    def __init__(self) -> None:
        """Initialize the proxy.

        Note: Does NOT register with GlobalRegistry here to avoid
        complications with test cleanup. Registration happens in
        _get_yaml_cache().
        """

    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to the real cache.

        Args:
            name: Name of the attribute being accessed.

        Returns:
            The value of the requested attribute from the real cache.

        """
        return getattr(_get_yaml_cache(), name)

    def __call__(self) -> YamlSettingsCache:
        """Return the singleton cache instance.

        Returns:
            The singleton YamlSettingsCache instance.

        """
        return _get_yaml_cache()


# Module-level proxy for yaml_cache
yaml_cache = _YamlCacheProxy()


# ==========================================
# Convenience functions
# ==========================================


def _raise_async_context_error(yaml_store: YAML, key_path: str) -> None:
    """Raise an error when sync function is called from async context.

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
    """Read or write a YAML setting synchronously.

    Provides synchronous access to YAML configuration data. If called from
    an async context, raises a RuntimeError directing to use the async version.

    Args:
        _type: The expected type of the setting value.
        yaml_store: The YAML store to access.
        key_path: The dot-delimited path to the setting (e.g., "section.key").
        new_value: Optional new value to set. Defaults to None for read operations.

    Returns:
        The setting value (properly typed), or None if not found.

    Raises:
        RuntimeError: If called from within an async context.

    Example:
        >>> value = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
        >>> # Write a setting
        >>> yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.VR Mode", True)

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
    """Read a setting from the CLASSIC_Settings section.

    Convenience function for accessing settings in the CLASSIC Settings YAML file.
    If the settings file doesn't exist, creates it with defaults from CLASSIC Main.yaml.

    Args:
        _type: The expected type of the setting to be returned.
        setting: The name of the setting within CLASSIC_Settings (without prefix).

    Returns:
        The requested setting cast to the provided type, or None if not found.

    Raises:
        ValueError: If default settings from CLASSIC Main.yaml are not valid.

    Example:
        >>> vr_mode = classic_settings(bool, "VR Mode")
        >>> # Equivalent to: yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.VR Mode")

    """
    # Check if settings file exists, create if needed
    settings_path = Path("CLASSIC Settings.yaml")
    if not settings_path.exists():
        # Get default settings from Main YAML
        default_settings = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_settings")
        if not isinstance(default_settings, str):
            raise ValueError("Invalid Default Settings in 'CLASSIC Main.yaml'")

        # Use FileIOCore for consistency
        from ClassicLib.core.async_bridge import AsyncBridge
        from ClassicLib.integration.factory import get_file_io

        io_core = get_file_io()
        AsyncBridge.get_instance().run_async(io_core.write_file(settings_path, default_settings))

    return yaml_settings(_type, YAML.Settings, f"CLASSIC_Settings.{setting}")


__all__ = [
    "classic_settings",
    "yaml_cache",
    "yaml_settings",
]
