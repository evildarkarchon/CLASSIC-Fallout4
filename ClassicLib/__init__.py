"""ClassicLib - Core library for CLASSIC crash log analyzer.

This module provides core functionality that works with or without PySide6.
GUI-specific components are available in ClassicLib.gui when PySide6 is installed.
"""

from ClassicLib.compat import HAS_PYSIDE6, HAS_TQDM, check_gui_requirements
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
from ClassicLib.Meta import SingletonMeta
from ClassicLib.Update import (
    UpdateCheckError,
    get_github_latest_stable_version_from_endpoint,
    get_latest_and_top_release_details,
    get_nexus_version,
    is_latest_version,
    try_parse_version,
)
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

__all__ = [
    # Constants
    "DB_PATHS",
    "F4SE_VERSIONS",
    "FO4_VERSIONS",
    # Compatibility
    "HAS_PYSIDE6",
    "HAS_TQDM",
    "NG_F4SE_VERSION",
    "NG_VERSION",
    "NULL_VERSION",
    "OG_F4SE_VERSION",
    "OG_VERSION",
    "SETTINGS_IGNORE_NONE",
    "VR_VERSION",
    "YAML",
    "GameID",
    # GlobalRegistry
    "Keys",
    # MessageHandler
    "Message",
    "MessageHandler",
    "MessageTarget",
    "MessageType",
    "ProgressContext",
    # Meta
    "SingletonMeta",
    # Update
    "UpdateCheckError",
    # YamlSettingsCache
    "YAMLLiteral",
    "YAMLMapping",
    "YAMLSequence",
    "YAMLValue",
    "YAMLValueOptional",
    "YamlSettingsCache",
    # Util
    "append_or_extend",
    "calculate_file_hash",
    "calculate_similarity",
    "check_gui_requirements",
    "classic_settings",
    "configure_logging",
    "crashgen_version_gen",
    "get",
    "get_game",
    "get_game_path_gui",
    "get_game_version",
    "get_github_latest_stable_version_from_endpoint",
    "get_latest_and_top_release_details",
    "get_local_dir",
    "get_manual_docs_gui",
    "get_message_handler",
    "get_nexus_version",
    "get_vr",
    "get_yaml_cache",
    "init_message_handler",
    "is_gui_mode",
    "is_latest_version",
    "is_registered",
    # Logger
    "logger",
    "msg_critical",
    "msg_debug",
    "msg_error",
    "msg_info",
    "msg_progress_context",
    "msg_success",
    "msg_warning",
    "normalize_list",
    "open_file_with_encoding",
    "pastebin_fetch",
    "pastebin_fetch_async",
    "register",
    "remove_readonly",
    "try_parse_version",
    # XseCheck
    "xse_check_hashes",
    "xse_check_integrity",
    "yaml_cache",
    "yaml_settings",
]
