from functools import reduce
from pathlib import Path
from typing import Any, ClassVar

import ruamel.yaml

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import SETTINGS_IGNORE_NONE, YAML, YAMLMapping, YAMLValue, gamevars
from ClassicLib.Logger import logger
from ClassicLib.Util import open_file_with_encoding


class SingletonMeta(type):
    _instances: ClassVar[dict[type, Any]] = {}

    def __call__(cls, *args, **kwargs):  # noqa: ANN002, ANN003, ANN204
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


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
        Retrieves the file path for the given YAML store. If the path is already cached,
        it returns the cached path. Otherwise, it determines the path based on the
        YAML store type, caches it, and then returns the path. The function uses
        different predefined paths based on the type of YAML store passed.

        Args:
            yaml_store: An enum value of type YAML indicating the type of YAML store,
                such as Main, Settings, Ignore, Game, Game_Local, or TEST.

        Returns:
            Path: The file path corresponding to the specified YAML store.

        Raises:
            NotImplementedError: If the provided yaml_store is not recognized or
                implemented.
        """
        if yaml_store in self.path_cache:
            return self.path_cache[yaml_store]

        data_path = Path("CLASSIC Data/")
        match yaml_store:
            case YAML.Main:
                yaml_path = data_path / "databases/CLASSIC Main.yaml"
            case YAML.Settings:
                yaml_path = Path("CLASSIC Settings.yaml")
            case YAML.Ignore:
                yaml_path = Path("CLASSIC Ignore.yaml")
            case YAML.Game:
                yaml_path = data_path / f"databases/CLASSIC {gamevars['game']}.yaml"
            case YAML.Game_Local:
                yaml_path = data_path / f"CLASSIC {gamevars['game']} Local.yaml"
            case YAML.TEST:
                yaml_path = Path("tests/test_settings.yaml")
            case _:
                raise NotImplementedError

        self.path_cache[yaml_store] = yaml_path
        return yaml_path

    def load_yaml(self, yaml_path: Path) -> YAMLMapping:
        """
        Loads a YAML file with caching to optimize reloading. Supports static and dynamic files,
        with separate handling based on file type. Static files are loaded once and cached, while
        dynamic files are reloaded if their modification timestamp changes.

        Args:
            yaml_path (Path): The path to the YAML file to be loaded.

        Returns:
            YAMLMapping: The loaded YAML content. If the file does not exist, an empty dictionary
            is returned.
        """
        if not yaml_path.exists():
            return {}

        # Determine if this is a static file
        is_static = any(yaml_path == self.get_path_for_store(store) for store in self.STATIC_YAML_STORES)

        def cache_file(yaml_path_obj: Path) -> None:
            with open_file_with_encoding(yaml_path_obj) as yaml_file:
                yaml = ruamel.yaml.YAML()
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
            if (yaml_path not in self.file_mod_times or
                    self.file_mod_times[yaml_path] != last_mod_time):
                # Update the file modification time
                self.file_mod_times[yaml_path] = last_mod_time

                logger.debug(f"Loading dynamic YAML file: {yaml_path}")
                # Reload the YAML file
                cache_file(yaml_path)

        return self.cache.get(yaml_path, {})

    def get_setting[T](self, _type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
        """
        Fetches or modifies a setting within a YAML file. This function is responsible for retrieving or modifying
        nested settings in YAML files, depending on the provided arguments. It handles caching for static YAML
        stores, ensuring efficient access and updates. Static stores are also protected against unintended
        modifications with appropriate warnings.

        Args:
            _type: The expected type of the setting to be retrieved or updated.
            yaml_store: An identifier for the specific YAML store to access.
            key_path: The dot-separated path key to locate the setting within the YAML structure.
            new_value: The new value to be assigned to the setting. If None, no modification is performed,
                and the function operates in a read-only mode.

        Returns:
            The value retrieved from the YAML structure or the newly updated value. Returns None if
            the key path is invalid or leads to a None value and is not listed in the settings ignore list.
        """
        # If this is a read operation for a static store, check cache first
        cache_key = (yaml_store, key_path, _type)
        if new_value is None and yaml_store in self.STATIC_YAML_STORES and cache_key in self.settings_cache:
            return self.settings_cache[cache_key]

        yaml_path = self.get_path_for_store(yaml_store)

        # Load YAML with caching logic
        data = self.load_yaml(yaml_path)
        keys = key_path.split(".")

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
            # If this is a static file and we're trying to modify it, warn about this
            if yaml_store in self.STATIC_YAML_STORES:
                logger.warning(f"Attempting to modify static YAML store {yaml_store} at {key_path}")

            setting_container[keys[-1]] = new_value  # type: ignore[assignment]

            # Write changes back to the YAML file
            with yaml_path.open("w", encoding="utf-8") as yaml_file:
                yaml = ruamel.yaml.YAML()
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
            print(f"❌ ERROR (yaml_settings) : Trying to grab a None value for : '{key_path}'")

        # Cache the result for static stores
        if yaml_store in self.STATIC_YAML_STORES:
            self.settings_cache[cache_key] = setting_value

        return setting_value  # type: ignore[return-value]


yaml_cache = YamlSettingsCache()
GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, yaml_cache)


def yaml_settings[T](_type: type[T], yaml_store: YAML, key_path: str, new_value: T | None = None) -> T | None:
    """
    Updates or retrieves a setting value from a given YAML store. The method
    handles type-specific processing for the retrieved or updated value, such
    as converting to a `Path` object when appropriate.

    Args:
        _type: The type of setting to retrieve or update. Supports generic
            type hinting.
        yaml_store: The YAML store object representing the settings data.
        key_path: The key path in the YAML store where the setting resides.
        new_value: The new value to be set in the YAML store at the given key
            path. This value must match the specified `_type`. Defaults to None.

    Returns:
        T | None: If `new_value` is provided, returns the updated setting value
        from the YAML store of the specified `_type`. If no `new_value` is
        provided, it retrieves and returns the current setting value in the
        YAML store of the given `_type`. Returns None if the setting does not
        exist or a type mismatch occurs.

    Raises:
        TypeError: If the YAML cache is not initialized.
    """
    if yaml_cache is None:
        raise TypeError("CMain not initialized")
    setting = yaml_cache.get_setting(_type, yaml_store, key_path, new_value)
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
    settings_path = Path("CLASSIC Settings.yaml")
    if not settings_path.exists():
        default_settings = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_settings")
        if not isinstance(default_settings, str):
            raise ValueError("Invalid Default Settings in 'CLASSIC Main.yaml'")

        settings_path.write_text(default_settings, encoding="utf-8")

    return yaml_settings(_type, YAML.Settings, f"CLASSIC_Settings.{setting}")
