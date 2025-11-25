"""AsyncYamlSettingsCore - Backwards compatibility wrapper.

DEPRECATED: Use ClassicLib.AsyncYamlSettings instead.
"""

import warnings

# Re-export everything from the refactored module for backwards compatibility
from ClassicLib.AsyncYamlSettings import (
    AsyncYamlSettingsCore,
    T,
    YamlCache,
    YamlFileOperations,
    YAMLLiteral,
    YAMLMapping,
    YAMLSequence,
    YAMLValue,
    YAMLValueOptional,
    classic_settings_async,
    coerce_setting_value,
    get_async_yaml_core,
    validate_setting_value,
    validate_settings_structure,
    yaml_settings_async,
)

warnings.warn(
    "ClassicLib.AsyncYamlSettingsCore is deprecated. Use ClassicLib.AsyncYamlSettings instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    # Core classes
    "AsyncYamlSettingsCore",
    "YamlCache",
    "YamlFileOperations",
    # Convenience functions
    "get_async_yaml_core",
    "yaml_settings_async",
    "classic_settings_async",
    # Types
    "T",
    "YAMLLiteral",
    "YAMLMapping",
    "YAMLSequence",
    "YAMLValue",
    "YAMLValueOptional",
    # Validators
    "validate_settings_structure",
    "validate_setting_value",
    "coerce_setting_value",
]
