"""ClassicLib - Core library for CLASSIC crash log analyzer.

This module provides async-first core functionality for crash log analysis,
including file I/O, performance monitoring, and setup coordination.
GUI-specific components are available in ClassicLib.Interface when PySide6 is installed.
"""

# Core async infrastructure
from ClassicLib.AsyncBridge import AsyncBridge

# Compatibility utilities
from ClassicLib.compat import HAS_PYSIDE6, HAS_TQDM, check_gui_requirements

# Core constants
from ClassicLib.Constants import (
    DB_PATHS,
    F4SE_VERSIONS,
    FO4_VERSIONS,
    NG_F4SE_VERSION,
    NG_VERSION,
    NULL_VERSION,
    OG_F4SE_VERSION,
    OG_VERSION,
    SETTINGS_IGNORE_NONE,
    VR_VERSION,
    YAML,
    GameID,
)

# File I/O operations
from ClassicLib.FileIOCore import FileIOCore, read_file_sync, write_file_sync

# Global registry system
from ClassicLib.GlobalRegistry import (
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

# Logging system
from ClassicLib.Logger import logger

# Message handling system
from ClassicLib.MessageHandler import (
    Message,
    MessageHandler,
    MessageTarget,
    MessageType,
    ProgressContext,
    get_message_handler,
    init_message_handler,
    msg_critical,
    msg_debug,
    msg_error,
    msg_info,
    msg_progress_context,
    msg_success,
    msg_warning,
)

# Meta utilities
from ClassicLib.Meta import SingletonMeta

# Performance monitoring
from ClassicLib.PerformanceMonitor import TimedBlock, async_timed_operation, timed_operation

# Update management
from ClassicLib.Update import (
    UpdateCheckError,
    get_github_latest_stable_version_from_endpoint,
    get_latest_and_top_release_details,
    get_nexus_version,
    is_latest_version,
    try_parse_version,
)

# Utility functions
from ClassicLib.Util import (
    append_or_extend,
    calculate_file_hash,
    calculate_similarity,
    configure_logging,
    crashgen_version_gen,
    get_game_version,
    normalize_list,
    open_file_with_encoding,
    pastebin_fetch,
    pastebin_fetch_async,
    remove_readonly,
)

# XSE validation
from ClassicLib.XseCheck import xse_check_hashes, xse_check_integrity

# YAML settings management
from ClassicLib.YamlSettingsCache import (
    YAMLLiteral,
    YAMLMapping,
    YAMLSequence,
    YamlSettingsCache,
    YAMLValue,
    YAMLValueOptional,
    classic_settings,
    yaml_cache,
    yaml_settings,
)

# Import core setup and coordination modules
try:
    from ClassicLib.BackupManager import BackupManager
    from ClassicLib.DocumentsChecker import DocumentsChecker
    from ClassicLib.FileGeneration import FileGeneration
    from ClassicLib.GameIntegrity import GameIntegrity
    from ClassicLib.PathValidator import PathValidator
    from ClassicLib.SetupCoordinator import SetupCoordinator

    _HAS_CORE_MODULES = True
except ImportError:
    _HAS_CORE_MODULES = False

__all__ = [
    # Async infrastructure
    "AsyncBridge",
    # Constants
    "DB_PATHS",
    "F4SE_VERSIONS",
    "FO4_VERSIONS",
    "GameID",
    "NG_F4SE_VERSION",
    "NG_VERSION",
    "NULL_VERSION",
    "OG_F4SE_VERSION",
    "OG_VERSION",
    "SETTINGS_IGNORE_NONE",
    "VR_VERSION",
    "YAML",
    # Compatibility
    "HAS_PYSIDE6",
    "HAS_TQDM",
    "check_gui_requirements",
    # File I/O
    "FileIOCore",
    "read_file_sync",
    "write_file_sync",
    # Global registry functions
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
    # Logging
    "logger",
    # Message handling
    "Message",
    "MessageHandler",
    "MessageTarget",
    "MessageType",
    "ProgressContext",
    "get_message_handler",
    "init_message_handler",
    "msg_critical",
    "msg_debug",
    "msg_error",
    "msg_info",
    "msg_progress_context",
    "msg_success",
    "msg_warning",
    # Meta utilities
    "SingletonMeta",
    # Performance monitoring
    "TimedBlock",
    "async_timed_operation",
    "timed_operation",
    # Update functions
    "UpdateCheckError",
    "get_github_latest_stable_version_from_endpoint",
    "get_latest_and_top_release_details",
    "get_nexus_version",
    "is_latest_version",
    "try_parse_version",
    # Utility functions
    "append_or_extend",
    "calculate_file_hash",
    "calculate_similarity",
    "configure_logging",
    "crashgen_version_gen",
    "get_game_version",
    "normalize_list",
    "open_file_with_encoding",
    "pastebin_fetch",
    "pastebin_fetch_async",
    "remove_readonly",
    # XSE validation
    "xse_check_hashes",
    "xse_check_integrity",
    # YAML settings
    "YAMLLiteral",
    "YAMLMapping",
    "YAMLSequence",
    "YAMLValue",
    "YAMLValueOptional",
    "YamlSettingsCache",
    "classic_settings",
    "yaml_cache",
    "yaml_settings",
]

# Add core setup modules if available
if _HAS_CORE_MODULES:
    __all__.extend([
        "BackupManager",
        "DocumentsChecker",
        "FileGeneration",
        "GameIntegrity",
        "PathValidator",
        "SetupCoordinator",
    ])
