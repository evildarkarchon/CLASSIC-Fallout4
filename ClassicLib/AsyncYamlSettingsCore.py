"""AsyncYamlSettingsCore - Backwards compatibility wrapper.

This file maintains backwards compatibility by re-exporting the refactored
AsyncYamlSettings module components.
"""

# Re-export everything from the refactored module for backwards compatibility
from ClassicLib.AsyncYamlSettings import (
    AsyncYamlSettingsCore,
    T,
    YAMLLiteral,
    YAMLMapping,
    YAMLSequence,
    YAMLValue,
    YAMLValueOptional,
    YamlCache,
    YamlFileOperations,
    classic_settings_async,
    coerce_setting_value,
    get_async_yaml_core,
    validate_setting_value,
    validate_settings_structure,
    yaml_settings_async,
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
