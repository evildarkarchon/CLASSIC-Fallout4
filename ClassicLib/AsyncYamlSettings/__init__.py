"""Backward compatibility module for AsyncYamlSettings.

DEPRECATED: Use ClassicLib.YamlSettings.async_ instead.

This module re-exports all async YAML settings functionality from the new
ClassicLib.YamlSettings module structure for full backward compatibility.

Migration Guide:
    Old:
        from ClassicLib.AsyncYamlSettings import AsyncYamlSettingsCore

    New:
        from ClassicLib.YamlSettings.async_ import AsyncYamlSettingsCore
        # or
        from ClassicLib.YamlSettings import AsyncYamlSettingsCore

Example:
    >>> from ClassicLib.YamlSettings.async_ import get_async_yaml_core
    >>> core = await get_async_yaml_core()
    >>> value = await core.async_yaml_settings(str, YAML.Main, "key")
"""

import warnings

# Re-export everything from the new module structure for backward compatibility
from ClassicLib.YamlSettings import (
    # Core classes
    AsyncYamlSettingsCore,
    # Types
    T,
    YamlCache,
    YamlFileOperations,
    YAMLLiteral,
    YAMLMapping,
    YAMLSequence,
    YAMLValue,
    YAMLValueOptional,
    # Convenience functions
    classic_settings_async,
    # Validators
    coerce_setting_value,
    get_async_yaml_core,
    validate_setting_value,
    validate_settings_structure,
    yaml_settings_async,
)

warnings.warn(
    "ClassicLib.AsyncYamlSettings is deprecated. Use ClassicLib.YamlSettings.async_ instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    # Core classes
    "AsyncYamlSettingsCore",
    "YamlCache",
    "YamlFileOperations",
    # Convenience functions
    "classic_settings_async",
    "get_async_yaml_core",
    "yaml_settings_async",
    # Types
    "T",
    "YAMLLiteral",
    "YAMLMapping",
    "YAMLSequence",
    "YAMLValue",
    "YAMLValueOptional",
    # Validators
    "coerce_setting_value",
    "validate_setting_value",
    "validate_settings_structure",
]
