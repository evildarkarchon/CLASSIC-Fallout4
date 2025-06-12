"""ClassicLib - Core library for CLASSIC crash log analyzer."""

from ClassicLib.Constants import NG_VERSION, NULL_VERSION, OG_VERSION, YAML, GameID
from ClassicLib.GlobalRegistry import Keys, get, get_game, get_vr, register
from ClassicLib.MessageHandler import (
    MessageTarget,
    MessageType,
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
from ClassicLib.Util import calculate_file_hash, open_file_with_encoding
from ClassicLib.YamlSettingsCache import YamlSettingsCache, classic_settings, yaml_settings

__all__ = [
    "NG_VERSION",
    "NULL_VERSION",
    "OG_VERSION",
    "YAML",
    "GameID",
    "Keys",
    "MessageTarget",
    "MessageType",
    "YamlSettingsCache",
    "calculate_file_hash",
    "classic_settings",
    "get",
    "get_game",
    "get_message_handler",
    "get_vr",
    "init_message_handler",
    "msg_critical",
    "msg_debug",
    "msg_error",
    "msg_info",
    "msg_progress_context",
    "msg_success",
    "msg_warning",
    "open_file_with_encoding",
    "register",
    "yaml_settings",
]