"""YamlSettings - Unified YAML settings management.

This module provides both synchronous and asynchronous interfaces for YAML
settings management with caching, file operations, and optional Rust acceleration.

Submodules:
    async_: Async-first YAML settings (AsyncYamlSettingsCore, YamlCache, etc.)
    sync: Synchronous wrappers (YamlSettingsCache, yaml_settings, etc.)

Usage Patterns:
    # GUI context (Qt workers, GUI initialization) - use sync
    >>> from ClassicLib.YamlSettings import yaml_cache, yaml_settings
    >>> result = yaml_cache().batch_get_settings(requests)
    >>> value = yaml_settings(str, YAML.Main, "key")

    # CLI/TUI async context (production async code) - use async_
    >>> from ClassicLib.YamlSettings import yaml_settings_async, classic_settings_async
    >>> value = await yaml_settings_async(str, YAML.Main, "key")

    # Direct async access
    >>> from ClassicLib.YamlSettings.async_ import get_async_yaml_core
    >>> core = await get_async_yaml_core()
    >>> value = await core.async_yaml_settings(str, YAML.Main, "key")

Performance Notes:
    - CLI production code should use async methods directly for best performance
    - GUI contexts automatically use AsyncBridge (lazy initialized)
    - Rust acceleration available for static database files (Main, Game)

Example:
    # Sync access (GUI)
    >>> from ClassicLib.YamlSettings import yaml_settings, classic_settings
    >>> version = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
    >>> vr_mode = classic_settings(bool, "VR Mode")

    # Async access (CLI)
    >>> from ClassicLib.YamlSettings import yaml_settings_async, classic_settings_async
    >>> version = await yaml_settings_async(str, YAML.Main, "CLASSIC_Info.version")
    >>> vr_mode = await classic_settings_async(bool, "VR Mode", False)
"""

# ==========================================
# Types (shared between async and sync)
# ==========================================
# ==========================================
# Async submodule exports
# ==========================================
from ClassicLib.YamlSettings.async_ import (
    AsyncYamlSettingsCore,
    YamlCache,
    YamlFileOperations,
    classic_settings_async,
    get_async_yaml_core,
    yaml_settings_async,
)

# ==========================================
# Sync submodule exports
# ==========================================
from ClassicLib.YamlSettings.sync import (
    YamlSettingsCache,
    classic_settings,
    yaml_cache,
    yaml_settings,
)
from ClassicLib.YamlSettings.types import (
    T,
    YAMLLiteral,
    YAMLMapping,
    YAMLSequence,
    YAMLValue,
    YAMLValueOptional,
)

# ==========================================
# Validators (shared between async and sync)
# ==========================================
from ClassicLib.YamlSettings.validators import (
    coerce_setting_value,
    validate_setting_value,
    validate_settings_structure,
)

__all__ = [
    # ==========================================
    # Types
    # ==========================================
    "T",
    "YAMLLiteral",
    "YAMLMapping",
    "YAMLSequence",
    "YAMLValue",
    "YAMLValueOptional",
    # ==========================================
    # Validators
    # ==========================================
    "coerce_setting_value",
    "validate_setting_value",
    "validate_settings_structure",
    # ==========================================
    # Async classes and functions
    # ==========================================
    "AsyncYamlSettingsCore",
    "YamlCache",
    "YamlFileOperations",
    "classic_settings_async",
    "get_async_yaml_core",
    "yaml_settings_async",
    # ==========================================
    # Sync classes and functions
    # ==========================================
    "YamlSettingsCache",
    "classic_settings",
    "yaml_cache",
    "yaml_settings",
]
