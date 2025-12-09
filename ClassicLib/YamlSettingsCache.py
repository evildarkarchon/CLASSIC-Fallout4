"""Backward compatibility module for YamlSettingsCache.

This module re-exports all YAML settings functionality from the new
ClassicLib.YamlSettings module structure for full backward compatibility.

MIGRATION NOTE:
    This module is preserved for backward compatibility. New code should
    import directly from ClassicLib.YamlSettings:

    # Sync
    from ClassicLib.YamlSettings import yaml_settings, classic_settings, yaml_cache

    # Async
    from ClassicLib.YamlSettings import yaml_settings_async, classic_settings_async

Usage Patterns (unchanged):
    # GUI context (Qt workers, GUI initialization)
    from ClassicLib.YamlSettingsCache import yaml_cache, yaml_settings
    result = yaml_cache.batch_get_settings(requests)
    value = yaml_settings(str, YAML.Main, "key")

    # CLI/TUI async context (production async code)
    from ClassicLib.YamlSettingsCache import yaml_cache, yaml_settings_async
    result = await yaml_cache.batch_get_settings_async(requests)
    value = await yaml_settings_async(str, YAML.Main, "key")

    # Testing/benchmarking (sync context, CLI mode)
    from ClassicLib.YamlSettingsCache import yaml_cache
    result = yaml_cache.batch_get_settings(requests)

Performance Notes:
    - CLI production code should use async methods directly for best performance
    - GUI contexts automatically use AsyncBridge (lazy initialized)
    - Sync methods in CLI mode use asyncio.run() fallback (valid for testing only)
"""

# Re-export everything from the new module structure for backward compatibility
from ClassicLib.YamlSettings import (
    # Async classes and functions
    AsyncYamlSettingsCore,
    # Types
    YAMLLiteral,
    YAMLMapping,
    YAMLSequence,
    # Sync classes and functions
    YamlSettingsCache,
    YAMLValue,
    YAMLValueOptional,
    classic_settings,
    classic_settings_async,
    get_async_yaml_core,
    yaml_cache,
    yaml_settings,
    yaml_settings_async,
)

# Re-export internal function for backward compatibility with tests
from ClassicLib.YamlSettings.sync.convenience import _get_yaml_cache  # noqa: PLC2701

__all__ = [
    # Types
    "YAMLLiteral",
    "YAMLMapping",
    "YAMLSequence",
    "YAMLValue",
    "YAMLValueOptional",
    # Main class
    "YamlSettingsCache",
    # Async class and getter
    "AsyncYamlSettingsCore",
    "get_async_yaml_core",
    # Convenience functions
    "classic_settings",
    "classic_settings_async",
    "yaml_cache",
    "yaml_settings",
    "yaml_settings_async",
    # Internal (for tests)
    "_get_yaml_cache",
]
