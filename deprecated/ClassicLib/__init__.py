"""ClassicLib public API exports.

This module exposes a broad convenience API for application code and tests.
All exports are resolved lazily to avoid importing Rust bindings during package
initialization. This keeps startup validation in entrypoints authoritative:
`validate_rust_modules("startup_all")` now runs before optional bindings are
loaded via the aggregate package API.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORT_MAP: dict[str, tuple[str, str | None]] = {
    # AsyncBridge
    "AsyncBridge": ("ClassicLib.core.async_bridge", "AsyncBridge"),
    # Constants
    "DB_PATHS": ("ClassicLib.core.constants", "DB_PATHS"),
    "GameID": ("ClassicLib.core.constants", "GameID"),
    "NULL_VERSION": ("ClassicLib.core.constants", "NULL_VERSION"),
    "SETTINGS_IGNORE_NONE": ("ClassicLib.core.constants", "SETTINGS_IGNORE_NONE"),
    "YAML": ("ClassicLib.core.constants", "YAML"),
    "get_all_db_paths": ("ClassicLib.core.constants", "get_all_db_paths"),
    "get_main_db_path": ("ClassicLib.core.constants", "get_main_db_path"),
    "get_user_db_paths": ("ClassicLib.core.constants", "get_user_db_paths"),
    # VersionRegistry
    "VersionRegistry": ("ClassicLib.support.versions", "VersionRegistry"),
    "get_version_registry": ("ClassicLib.support.versions", "get_version_registry"),
    # FileIOCore
    "FileIOCore": ("ClassicLib.io.files", "FileIOCore"),
    # GlobalRegistry helpers
    "Keys": ("ClassicLib.core.registry", "Keys"),
    "get": ("ClassicLib.core.registry", "get"),
    "get_game": ("ClassicLib.core.registry", "get_game"),
    "get_game_path_gui": ("ClassicLib.core.registry", "get_game_path_gui"),
    "get_local_dir": ("ClassicLib.core.registry", "get_local_dir"),
    "get_manual_docs_gui": ("ClassicLib.core.registry", "get_manual_docs_gui"),
    "get_vr": ("ClassicLib.core.registry", "get_vr"),
    "get_yaml_cache": ("ClassicLib.core.registry", "get_yaml_cache"),
    "is_gui_mode": ("ClassicLib.core.registry", "is_gui_mode"),
    "is_registered": ("ClassicLib.core.registry", "is_registered"),
    "register": ("ClassicLib.core.registry", "register"),
    # Logger
    "logger": ("ClassicLib.core.logger", "logger"),
    # Message handling
    "Message": ("ClassicLib.messaging", "Message"),
    "MessageHandler": ("ClassicLib.messaging", "MessageHandler"),
    "MessageTarget": ("ClassicLib.messaging", "MessageTarget"),
    "MessageType": ("ClassicLib.messaging", "MessageType"),
    "ProgressContext": ("ClassicLib.messaging", "ProgressContext"),
    "get_message_handler": ("ClassicLib.messaging", "get_message_handler"),
    "init_message_handler": ("ClassicLib.messaging", "init_message_handler"),
    "msg_critical": ("ClassicLib.messaging", "msg_critical"),
    "msg_debug": ("ClassicLib.messaging", "msg_debug"),
    "msg_error": ("ClassicLib.messaging", "msg_error"),
    "msg_info": ("ClassicLib.messaging", "msg_info"),
    "msg_progress_context": ("ClassicLib.messaging", "msg_progress_context"),
    "msg_success": ("ClassicLib.messaging", "msg_success"),
    "msg_warning": ("ClassicLib.messaging", "msg_warning"),
    # Performance monitor
    "TimedBlock": ("ClassicLib.core.performance", "TimedBlock"),
    "async_timed_operation": ("ClassicLib.core.performance", "async_timed_operation"),
    "timed_operation": ("ClassicLib.core.performance", "timed_operation"),
    # Utilities
    "append_or_extend": ("ClassicLib.Utils.string_utils", "append_or_extend"),
    "calculate_file_hash": ("ClassicLib.Utils.file_utils", "calculate_file_hash"),
    "calculate_similarity": ("ClassicLib.Utils.file_utils", "calculate_similarity"),
    "configure_logging": ("ClassicLib.Utils.logging_utils", "configure_logging"),
    "enable_debug_logging": ("ClassicLib.Utils.logging_utils", "enable_debug_logging"),
    "crashgen_version_gen": ("ClassicLib.Utils.version_utils", "crashgen_version_gen"),
    "read_game_exe_version": ("ClassicLib.Utils.version_utils", "read_game_exe_version"),
    "normalize_list": ("ClassicLib.Utils.string_utils", "normalize_list"),
    "open_file_with_encoding": ("ClassicLib.Utils.file_utils", "open_file_with_encoding"),
    "pastebin_fetch": ("ClassicLib.Utils.web_utils", "pastebin_fetch"),
    "pastebin_fetch_async": ("ClassicLib.Utils.web_utils", "async_pastebin_fetch"),
    "remove_readonly": ("ClassicLib.Utils.path_utils", "remove_readonly"),
    # XSE
    "xse_check_hashes": ("ClassicLib.support.xse", "xse_check_hashes"),
    "xse_check_integrity": ("ClassicLib.support.xse", "xse_check_integrity"),
    # YAML
    "YamlSettingsCache": ("ClassicLib.io.yaml", "YamlSettingsCache"),
    "classic_settings": ("ClassicLib.io.yaml", "classic_settings"),
    "yaml_cache": ("ClassicLib.io.yaml", "yaml_cache"),
    "yaml_settings": ("ClassicLib.io.yaml", "yaml_settings"),
    # Rust bindings
    "classic_registry": ("classic_registry", None),
    "classic_perf": ("classic_perf", None),
    "classic_pybridge": ("classic_pybridge", None),
    "rust_settings": ("classic_settings", None),
    "classic_message": ("classic_message", None),
}

__all__ = list(_EXPORT_MAP)


def __getattr__(name: str) -> Any:
    """Resolve public exports lazily on first attribute access."""
    if name not in _EXPORT_MAP:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORT_MAP[name]
    module = import_module(module_name)
    value = module if attr_name is None else getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy exports in introspection results."""
    return sorted(set(globals()) | set(__all__))
