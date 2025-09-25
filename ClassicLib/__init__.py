"""
ClassicLib - Core library for CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker).

This module provides the main components for log analysis, file I/O, settings management,
and various utility functions for the CLASSIC application.
"""

# Core components
from ClassicLib.AsyncBridge import AsyncBridge
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
from ClassicLib.FileIOCore import FileIOCore, read_file_sync, write_file_sync
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
from ClassicLib.Logger import logger
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
from ClassicLib.PerformanceMonitor import TimedBlock, async_timed_operation, timed_operation

# NOTE: Update module is temporarily excluded due to external dependency issues
# from ClassicLib.Update import (
#     UpdateCheckError,
#     get_github_latest_stable_version_from_endpoint,
#     get_latest_and_top_release_details,
#     get_nexus_version,
#     is_latest_version,
#     try_parse_version,
# )

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
from ClassicLib.XseCheck import xse_check_hashes, xse_check_integrity
from ClassicLib.YamlSettingsCache import (
    YamlSettingsCache,
    classic_settings,
    yaml_cache,
    yaml_settings,
)

__all__ = [
    # AsyncBridge
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
    # FileIOCore
    "FileIOCore",
    "read_file_sync",
    "write_file_sync",
    # GlobalRegistry
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
    # Logger
    "logger",
    # MessageHandler
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
    # PerformanceMonitor
    "TimedBlock",
    "async_timed_operation",
    "timed_operation",
    # Util
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
    # XseCheck
    "xse_check_hashes",
    "xse_check_integrity",
    # YamlSettingsCache
    "YamlSettingsCache",
    "classic_settings",
    "yaml_cache",
    "yaml_settings",
]
