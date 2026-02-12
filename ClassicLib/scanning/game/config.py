"""Configuration file cache - thin wrapper over Rust RustConfigFileCache (G-03).

Delegates INI/CONF file scanning, encoding detection, duplicate detection,
and typed value retrieval to the Rust implementation. The Python class
maintains API compatibility with callers expecting ConfigFileCache.
"""

from collections.abc import ItemsView
from pathlib import Path
from typing import Any

from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import get_vr
from ClassicLib.io.yaml import yaml_settings
from ClassicLib.scanning.game.models.fcx_issue import ConfigIssueSeverity

TEST_MODE = False


class ConfigFileCache:
    """Cache and manage configuration files, delegating to Rust implementation.

    Scans the game root directory for INI/CONF files, detects duplicates
    via content hashing and similarity, and provides typed getters.

    Example:
        >>> cache = ConfigFileCache()
        >>> if "enblocal.ini" in cache:
        ...     val = cache.get(bool, "enblocal.ini", "ENGINE", "ForceVSync")
        ...     print(f"VSync: {val}")

    """

    def __init__(self) -> None:
        from classic_scangame import RustConfigFileCache

        game_root = yaml_settings(Path, YAML.Game_Local, f"Game{get_vr()}_Info.Root_Folder_Game")
        if game_root is None:
            raise FileNotFoundError

        self._inner = RustConfigFileCache(game_root, ["F4EE"])
        self.duplicate_files: dict[str, list[Path]] = {
            k: [Path(p) for p in v] for k, v in self._inner.get_duplicates().items()
        }

    def __contains__(self, file_name_lower: str) -> bool:
        return self._inner.contains(file_name_lower)

    def __getitem__(self, file_name_lower: str) -> Path:
        path = self._inner.get_path(file_name_lower)
        if path is None:
            raise KeyError(file_name_lower)
        return Path(path)

    def get[T](self, value_type: type[T], file_name_lower: str, section: str, setting: str) -> T | None:
        """Retrieve a typed configuration value.

        Args:
            value_type: Expected type (str, bool, int, or float).
            file_name_lower: Lowercase config filename.
            section: INI section name.
            setting: Setting key within section.

        Returns:
            Typed value or None if not found.

        """
        if value_type is str:
            return self._inner.get_str(file_name_lower, section, setting)  # type: ignore[return-value]
        if value_type is bool:
            return self._inner.get_bool(file_name_lower, section, setting)  # type: ignore[return-value]
        if value_type is int:
            return self._inner.get_int(file_name_lower, section, setting)  # type: ignore[return-value]
        if value_type is float:
            return self._inner.get_float(file_name_lower, section, setting)  # type: ignore[return-value]
        raise NotImplementedError(f"Unsupported type: {value_type}")

    async def get_async[T](self, value_type: type[T], file_name_lower: str, section: str, setting: str) -> T | None:
        """Async version of get(). Rust loading is synchronous and fast."""
        return self.get(value_type, file_name_lower, section, setting)

    async def detect_issue[T](
        self,
        value_type: type[T],
        file_name_lower: str,
        section: str,
        setting: str,
        recommended_value: T,
        description: str,
        condition_check: Any,
        severity: ConfigIssueSeverity = "warning",
    ) -> Any | None:
        """Detect a configuration issue without modifying the file.

        Args:
            value_type: Expected type of the configuration value.
            file_name_lower: Lowercase config filename.
            section: INI section name.
            setting: Setting key.
            recommended_value: Value that should be set.
            description: Human-readable issue description.
            condition_check: Callable(value) -> True if issue exists.
            severity: Issue severity ("error", "warning", "info").

        Returns:
            ConfigIssue if issue detected, None otherwise.

        """
        from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue

        current_value = self.get(value_type, file_name_lower, section, setting)
        if current_value is None:
            return None
        if not condition_check(current_value):
            return None

        path = self._inner.get_path(file_name_lower)
        return ConfigIssue(
            file_path=Path(path) if path else Path(file_name_lower),
            section=section,
            setting=setting,
            current_value=str(current_value),
            recommended_value=str(recommended_value),
            description=description,
            severity=severity,
        )

    def get_strict[T](self, value_type: type[T], file: str, section: str, setting: str) -> T:
        """Fetch a value with strict type-based fallback for missing values."""
        value = self.get(value_type, file, section, setting)
        if value is not None:
            return value
        if value_type is str:
            return ""  # type: ignore[return-value]
        if value_type is bool:
            return False  # type: ignore[return-value]
        if value_type is int:
            return 0  # type: ignore[return-value]
        if value_type is float:
            return 0.0  # type: ignore[return-value]
        raise NotImplementedError

    def has(self, file_name_lower: str, section: str, setting: str) -> bool:
        """Check if a setting exists in a config file."""
        return self._inner.has_setting(file_name_lower, section, setting)

    def items(self) -> ItemsView[str, Path]:
        """Return config file name -> path pairs."""
        return self._inner.config_files().items()  # type: ignore[return-value]


def mod_toml_config(toml_path: Path, section: str, key: str, new_value: Any = None) -> Any | None:
    """Read a value from a TOML configuration file.

    Args:
        toml_path: Path to the TOML file.
        section: Section in the TOML file.
        key: Key within the section.
        new_value: Deprecated - write support removed. Ignored if provided.

    Returns:
        The current value of the key, or None if section/key doesn't exist.

    """
    if new_value is not None:
        logger.warning("mod_toml_config write support has been removed. new_value ignored.")

    import tomlkit

    file_bytes = toml_path.read_bytes()

    import chardet

    file_encoding: str = chardet.detect(file_bytes)["encoding"] or "utf-8"
    file_text = file_bytes.decode(file_encoding)
    data = tomlkit.parse(file_text)

    if section not in data:
        return None
    section_item = data[section]
    if not hasattr(section_item, "__getitem__") or not hasattr(section_item, "__contains__"):
        return None
    if key not in section_item:
        return None
    return section_item[key]
