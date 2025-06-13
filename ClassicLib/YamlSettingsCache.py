from functools import reduce
from pathlib import Path
from typing import Any, ClassVar

import ruamel.yaml

from ClassicLib import GlobalRegistry, MessageTarget, msg_error
from ClassicLib.Constants import SETTINGS_IGNORE_NONE, YAML
from ClassicLib.Logger import logger
from ClassicLib.Meta import SingletonMeta
from ClassicLib.Util import open_file_with_encoding

type YAMLLiteral = str | int | bool
type YAMLSequence = list[str]
type YAMLMapping = dict[str, "YAMLValue"]
type YAMLValue = YAMLMapping | YAMLSequence | YAMLLiteral
type YAMLValueOptional = YAMLValue | None


class YamlSettingsCache(metaclass=SingletonMeta):
    """
    A utility class for managing and caching YAML settings.

    This class provides mechanisms for working with YAML configurations, including
    retrieving paths, loading YAML files with caching, and accessing or modifying
    settings in a structured YAML format. It employs a singleton pattern to ensure
    a single instance across the application. Static YAML files (those that don't
    change during program execution) are handled differently from dynamic YAML
    files, with separate caching mechanisms for improved performance.

    Attributes:
        STATIC_YAML_STORES (set[YAML]): A set of YAML stores considered static,
            meaning their contents won't be expected to change during program
            execution. Examples include Main, Game YAML files.
    """

    # Static YAML stores that won't change during program execution
    STATIC_YAML_STORES: ClassVar[set[YAML]] = {YAML.Main, YAML.Game}

    def __init__(self) -> None:
        """Initialize the instance attributes."""
        self.cache: dict[Path, YAMLMapping] = {}
        self.file_mod_times: dict[Path, float] = {}
        self.path_cache: dict[YAML, Path] = {}
        self.settings_cache: dict[tuple[YAML, str, type], Any] = {}

    def get_path_for_store(self, yaml_store: YAML) -> Path:
        """
        Determines and returns the file path for a given YAML configuration type. The file path is derived based on the
        specific YAML store requested. A cache is utilized to avoid recalculating paths for previously accessed stores.

        Args:
            yaml_store (YAML): The identifier for the configuration type. Specifies which YAML file's path is being requested.

        Returns:
            Path: The resolved file path corresponding to the provided YAML store.

        Raises:
            NotImplementedError: If the provided yaml_store does not match any of the predefined YAML types.
            FileNotFoundError: If no valid file path could be resolved for the provided yaml_store.
        """
        if yaml_store in self.path_cache:
            return self.path_cache[yaml_store]
        yaml_path: Path = Path.cwd()
        data_path: Path = Path("CLASSIC Data/")
        match yaml_store:
            case YAML.Main:
                yaml_path = data_path / "databases/CLASSIC Main.yaml"
            case YAML.Settings:
                yaml_path = Path("CLASSIC Settings.yaml")
            case YAML.Ignore:
                yaml_path = Path("CLASSIC Ignore.yaml")
            case YAML.Game:
                yaml_path = data_path / f"databases/CLASSIC {GlobalRegistry.get_game()}.yaml"
            case YAML.Game_Local:
                yaml_path = data_path / f"CLASSIC {GlobalRegistry.get_game()} Local.yaml"
            case YAML.TEST:
                yaml_path = Path("tests/test_settings.yaml")
            case other if other not in (YAML.Main, YAML.Settings, YAML.Ignore, YAML.Game, YAML.Game_Local, YAML.TEST):
                raise NotImplementedError

        if yaml_path != Path.cwd():
            self.path_cache[yaml_store] = yaml_path
        else:
            raise FileNotFoundError(f"No YAML file found for {yaml_store}")
        return yaml_path

    def load_yaml(self, yaml_path: Path) -> YAMLMapping:
        """
        Loads the content of a YAML file into a cache and retrieves it. Supports static and dynamic YAML files,
        with handling for file modification times to reload dynamic files when they change.

        Args:
            yaml_path (Path): The path to the YAML file to be loaded.

        Returns:
            YAMLMapping: The content of the YAML file, either from the cache or loaded dynamically. Returns
                an empty dictionary if the file does not exist.
        """
        if not yaml_path.exists():
            return {}

        # Determine if this is a static file
        is_static = any(yaml_path == self.get_path_for_store(store) for store in self.STATIC_YAML_STORES)

        def cache_file(yaml_path_obj: Path) -> None:
            with open_file_with_encoding(yaml_path_obj) as yaml_file:
                yaml: ruamel.yaml.YAML = ruamel.yaml.YAML()
                yaml.indent(offset=2)
                yaml.width = 300
                self.cache[yaml_path_obj] = yaml.load(yaml_file)

        if is_static:
            # For static files, just load once
            if yaml_path not in self.cache:
                logger.debug(f"Loading static YAML file: {yaml_path}")
                cache_file(yaml_path)
        else:
            # For dynamic files, check modification time
            last_mod_time = yaml_path.stat().st_mtime
            if yaml_path not in self.file_mod_times or self.file_mod_times[yaml_path] != last_mod_time:
                # Update the file modification time
                self.file_mod_times[yaml_path] = last_mod_time

                logger.debug(f"Loading dynamic YAML file: {yaml_path}")
                # Reload the YAML file
                cache_file(yaml_path)

        return self.cache.get(yaml_path, {})

    def get_setting[T](self, _type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
        """
        Retrieves or updates a setting from a nested YAML data structure. This method allows you to perform both
        read and write operations on YAML files while incorporating caching mechanisms for improved performance
        when accessing static YAML stores. If a new value is provided, the corresponding YAML file is updated
        and the cache is refreshed to reflect the changes.

        Args:
            _type: The expected type of the setting value.
            yaml_store: The YAML store from which the setting is retrieved or updated.
            key_path: The dot-delimited path specifying the location of the setting within the YAML structure.
            new_value: The new value to update the setting with. If None, the method operates as a read.

        Returns:
            The existing or updated setting value if successful, otherwise None.

        Raises:
            ValueError: If a static YAML store is being modified.
        """
        # If this is a read operation for a static store, check cache first
        cache_key: tuple[YAML, str, type[T]] = (yaml_store, key_path, _type)
        if new_value is None and yaml_store in self.STATIC_YAML_STORES and cache_key in self.settings_cache:
            return self.settings_cache[cache_key]

        yaml_path: Path = self.get_path_for_store(yaml_store)

        # Load YAML with caching logic
        data: dict = self.load_yaml(yaml_path)
        keys: list[str] = key_path.split(".")

        def setdefault(dictionary: dict[str, YAMLValue], key: str) -> dict[str, YAMLValue]:
            """
            A utility class for managing and working with YAML settings. This class provides
            methods to retrieve and modify settings within a nested YAML data structure.
            """
            if key not in dictionary:
                dictionary[key] = {}
            next_value = dictionary[key]
            if not isinstance(next_value, dict):
                raise TypeError
            return next_value

        try:
            setting_container = reduce(setdefault, keys[:-1], data)
        except TypeError:
            # Handle the case where a non-dictionary value is encountered
            logger.error(f"Invalid path structure for {key_path} in {yaml_store}")
            return None

        # If new_value is provided, update the value
        if new_value is not None:
            # If this is a static file and we're trying to modify it, raise a ValueError
            if yaml_store in self.STATIC_YAML_STORES:
                logger.error(f"Attempting to modify static YAML store {yaml_store} at {key_path}")
                raise ValueError(f"Attempted to modify static YAML store {yaml_store} at {key_path}")

            setting_container[keys[-1]] = new_value  # type: ignore[assignment]

            # Write changes back to the YAML file
            with yaml_path.open("w", encoding="utf-8") as yaml_file:
                yaml: ruamel.yaml.YAML = ruamel.yaml.YAML()
                yaml.indent(offset=2)
                yaml.width = 300
                yaml.dump(data, yaml_file)

            # Update the cache
            self.cache[yaml_path] = data

            # Clear any cached results for this path
            if cache_key in self.settings_cache:
                del self.settings_cache[cache_key]

            return new_value

        # Traverse YAML structure to get value
        setting_value = setting_container.get(keys[-1])
        if setting_value is None and keys[-1] not in SETTINGS_IGNORE_NONE:
            msg_error(f"ERROR (yaml_settings) : Trying to grab a None value for : '{key_path}'", target=MessageTarget.CLI_ONLY)

        # Cache the result for static stores
        if yaml_store in self.STATIC_YAML_STORES:
            self.settings_cache[cache_key] = setting_value

        return setting_value  # type: ignore[return-value]


yaml_cache: YamlSettingsCache = YamlSettingsCache()
GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, yaml_cache)


def yaml_settings[T](_type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
    """
    Manages YAML settings by retrieving or updating a specific setting in the YAML store.

    This function operates on YAML configuration data. It retrieves or updates a setting
    based on the provided key path. The function ensures that types are consistent with
    the required input or output. If `new_value` is provided, it updates the setting in
    the YAML store, otherwise it fetches the current value. If `_type` is `Path`, it
    attempts to convert the setting to a `Path` object before returning it.

    Args:
        _type: The expected type of the setting value. It defines the type of the value
            to be retrieved or updated in the YAML store.
        yaml_store: The YAML object where the settings are stored and managed.
        key_path: The key path in the YAML store that points to the specific setting.
        new_value: The new value for the setting that is to be updated in the YAML
            store. If not provided, the function simply retrieves the current value.
            Defaults to None.

    Returns:
        The value of the setting retrieved from the YAML store if `new_value` is not
        provided. If `_type` is `Path`, it returns the value as a `Path` object;
        otherwise, it returns it with the specified type `_type`. Returns None if the
        setting is not found.
    """
    setting: T | None = yaml_cache.get_setting(_type, yaml_store, key_path, new_value)
    if _type is Path:
        return Path(setting) if setting and isinstance(setting, str) else None  # type: ignore[return-value]
    return setting


def classic_settings[T](_type: type[T], setting: str) -> T | None:
    """
    Fetches a specific setting from a CLASSIC settings file or creates the settings file
    if it does not exist.

    This function ensures that a settings file named "CLASSIC Settings.yaml" exists in the
    current directory. If the file does not exist, it creates the file based on default
    settings specified in another YAML configuration. The function then retrieves and
    returns the requested setting based on the provided type and setting key.

    Args:
        _type: The expected type of the setting value. This helps ensure the retrieved
            setting is appropriately cast to the desired type.
        setting: The key of the setting to retrieve from the "CLASSIC Settings.yaml"
            file.

    Returns:
        The value of the requested setting, cast to the specified type `_type`. If the
        setting is not found, or if an error occurs, it returns `None`.
    """
    settings_path: Path = Path("CLASSIC Settings.yaml")
    if not settings_path.exists():
        default_settings: str | None = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_settings")
        if not isinstance(default_settings, str):
            raise ValueError("Invalid Default Settings in 'CLASSIC Main.yaml'")

        settings_path.write_text(default_settings, encoding="utf-8")

    return yaml_settings(_type, YAML.Settings, f"CLASSIC_Settings.{setting}")
