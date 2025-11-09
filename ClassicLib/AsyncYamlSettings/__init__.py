"""AsyncYamlSettings module - Async-first YAML settings management.

This module provides high-performance YAML settings access with:
- Automatic file change detection and reloading
- TTL-based caching
- Concurrent access with proper locking
- Batch operations for efficiency
"""

# Import all public APIs for backwards compatibility
from ClassicLib.AsyncYamlSettings.cache import YamlCache
from ClassicLib.AsyncYamlSettings.core import (
    AsyncYamlSettingsCore,
    classic_settings_async,
    get_async_yaml_core,
    yaml_settings_async,
)
from ClassicLib.AsyncYamlSettings.file_operations import YamlFileOperations
from ClassicLib.AsyncYamlSettings.types import T, YAMLLiteral, YAMLMapping, YAMLSequence, YAMLValue, YAMLValueOptional
from ClassicLib.AsyncYamlSettings.validators import coerce_setting_value, validate_setting_value, validate_settings_structure

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
