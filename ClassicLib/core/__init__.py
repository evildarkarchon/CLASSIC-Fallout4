"""Core infrastructure components for CLASSIC.

This module provides the fundamental infrastructure used throughout CLASSIC:
- AsyncBridge: Singleton for async/sync bridging in GUI contexts
- GlobalRegistry: Central registry for application-wide state
- Constants: Global constants and configuration values
- Logger: Logging configuration and utilities
- PerformanceMonitor: Performance monitoring utilities
- rust_loader: Rust module loading utilities
"""

from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.core.constants import (
    DB_PATHS,
    NULL_VERSION,
    SETTINGS_IGNORE_NONE,
    YAML,
    GameID,
)
from ClassicLib.core.logger import logger
from ClassicLib.core.performance import TimedBlock, async_timed_operation, timed_operation
from ClassicLib.core.registry import (
    GlobalRegistry,
    Keys,
    get,
    get_game,
    get_game_path_gui,
    get_local_dir,
    get_manual_docs_gui,
    get_vr,
    get_yaml_cache,
    is_gui_mode,
    is_registered,
    register,
)
from ClassicLib.support.versions import (
    VersionRegistry,
    get_version_registry,
)

__all__ = [
    # AsyncBridge
    "AsyncBridge",
    # Constants
    "DB_PATHS",
    "GameID",
    "NULL_VERSION",
    "SETTINGS_IGNORE_NONE",
    "YAML",
    # VersionRegistry (replaces deprecated version constants)
    "VersionRegistry",
    "get_version_registry",
    # Logger
    "logger",
    # PerformanceMonitor
    "TimedBlock",
    "async_timed_operation",
    "timed_operation",
    # GlobalRegistry
    "GlobalRegistry",
    "Keys",
    "get",
    "get_game",
    "get_game_path_gui",
    "get_local_dir",
    "get_manual_docs_gui",
    "get_vr",
    "get_yaml_cache",
    "is_gui_mode",
    "is_registered",
    "register",
]
