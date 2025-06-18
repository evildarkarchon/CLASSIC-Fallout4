import threading
from dataclasses import dataclass, field
from pathlib import Path

from packaging.version import Version

from ClassicLib import GlobalRegistry, msg_error
from ClassicLib.Constants import NULL_VERSION, YAML
from ClassicLib.YamlSettingsCache import yaml_settings


class ThreadSafeLogCache:
    def __init__(self, logfiles: list[Path]) -> None:
        """
        Initializes a thread-safe in-memory log cache using a dictionary protected by a lock.
        This provides a thread-safe alternative to SQLite for caching log files.

        Args:
            logfiles (list[Path]): A list of file paths representing the log files to be cached.
        """
        self.lock = threading.RLock()  # Reentrant lock allows nested acquisitions
        self.cache: dict[str, bytes] = {}

        # Populate the cache with log content
        # Try async loading first for better performance
        try:
            from ClassicLib.ScanLog.AsyncFileIO import integrate_async_file_loading

            self.cache = integrate_async_file_loading(logfiles)
            from ClassicLib.Logger import logger

            logger.debug(f"Loaded {len(self.cache)} crash logs using async I/O")
        except (ImportError, Exception):
            # Fallback to sync loading
            for file in logfiles:
                try:
                    self.cache[file.name] = file.read_bytes()
                except OSError as e:
                    msg_error(f"Error reading {file}: {e}")
            from ClassicLib.Logger import logger

            logger.debug(f"Loaded {len(self.cache)} crash logs using sync I/O")

    def read_log(self, logname: str) -> list[str]:
        """
        Reads log data for a specified log name from the cache.

        This method retrieves log data associated with the provided log name
        from a cached data source and returns it as a list of decoded string
        lines. If the log name does not exist in the cache, an empty list
        is returned.

        Parameters:
            logname (str): The name of the log to retrieve.

        Returns:
            list[str]: List of log lines as strings. Returns an empty list if
            the log name is not found in the cache.
        """
        with self.lock:
            if logname not in self.cache:
                return []

            logdata = self.cache[logname]
            return logdata.decode("utf-8", errors="ignore").splitlines()

    def get_log_names(self) -> list[str]:
        """
        Retrieves the names of all logs currently stored in the cache.

        This method provides a thread-safe way to access the keys representing
        log names in a cached storage structure, ensuring that data integrity is
        maintained during access.

        Returns:
            list[str]: A list containing the names of all logs in the cache.
        """
        with self.lock:
            return list(self.cache.keys())

    def add_log(self, path: Path) -> bool:
        """
        Adds a log file to the internal cache if it is not already present.

        Parameters:
        path (Path): The path to the log file to be added.

        Returns:
        bool: True if the log file was successfully added to the cache or is
        already present; False if an OSError occurred during reading.

        """
        with self.lock:
            try:
                if path.name not in self.cache:
                    self.cache[path.name] = path.read_bytes()
                return True  # noqa: TRY300
            except OSError:
                return False

    def close(self) -> None:
        """
        Clears the cache when no longer needed.
        """
        with self.lock:
            self.cache.clear()

    @classmethod
    def from_cache(cls, cache_dict: dict[str, bytes]) -> "ThreadSafeLogCache":
        """
        Creates a new instance of the ThreadSafeLogCache class using an existing cache
        dictionary. This method allows for generating an object without directly
        loading files, by copying the provided cache dictionary into the instance.
        Used primarily for scenarios where log files are already cached and need to
        be encapsulated in a thread-safe structure.

        Parameters:
            cache_dict (dict[str, bytes]): A dictionary representing cached log data,
            where keys are strings identifying logs, and values are byte content of
            the logs.

        Returns:
            ThreadSafeLogCache: A new instance of the ThreadSafeLogCache initialized
            with the contents of the provided cache.

        Raises:
            None
        """
        # Create instance without loading files
        instance = cls.__new__(cls)
        instance.lock = threading.RLock()
        instance.cache = cache_dict.copy()

        from ClassicLib.Logger import logger

        logger.debug(f"Created ThreadSafeLogCache from existing cache with {len(cache_dict)} logs")

        return instance


# noinspection PyUnresolvedReferences
@dataclass
class ClassicScanLogsInfo:
    classic_game_hints: list[str] = field(default_factory=list)
    classic_records_list: list[str] = field(default_factory=list)
    classic_version: str = ""
    classic_version_date: str = ""
    crashgen_name: str = ""
    crashgen_latest_og: str = ""
    crashgen_latest_vr: str = ""
    crashgen_ignore: set = field(default_factory=set)
    warn_noplugins: str = ""
    warn_outdated: str = ""
    xse_acronym: str = ""
    game_ignore_plugins: list[str] = field(default_factory=list)
    game_ignore_records: list[str] = field(default_factory=list)
    suspects_error_list: dict[str, str] = field(default_factory=dict)
    suspects_stack_list: dict[str, list[str]] = field(default_factory=dict)
    autoscan_text: str = ""
    ignore_list: list[str] = field(default_factory=list)
    game_mods_conf: dict[str, str] = field(default_factory=dict)
    game_mods_core: dict[str, str] = field(default_factory=dict)
    game_mods_core_folon: dict[str, str] = field(default_factory=dict)
    game_mods_freq: dict[str, str] = field(default_factory=dict)
    game_mods_opc2: dict[str, str] = field(default_factory=dict)
    game_mods_solu: dict[str, str] = field(default_factory=dict)
    game_version: Version = field(default=NULL_VERSION, init=False)
    game_version_new: Version = field(default=NULL_VERSION, init=False)
    game_version_vr: Version = field(default=NULL_VERSION, init=False)

    def __post_init__(self) -> None:
        if not GlobalRegistry.is_registered(GlobalRegistry.Keys.YAML_CACHE):
            raise TypeError("YAML Cache is not initialized.")
        self.classic_game_hints = yaml_settings(list[str], YAML.Game, "Game_Hints") or []
        self.classic_records_list = yaml_settings(list[str], YAML.Main, "catch_log_records") or []
        self.classic_version = yaml_settings(str, YAML.Main, "CLASSIC_Info.version") or ""
        self.classic_version_date = yaml_settings(str, YAML.Main, "CLASSIC_Info.version_date") or ""
        self.crashgen_name = yaml_settings(str, YAML.Game, "Game_Info.CRASHGEN_LogName") or ""
        self.crashgen_latest_og = yaml_settings(str, YAML.Game, "Game_Info.CRASHGEN_LatestVer") or ""
        self.crashgen_latest_vr = yaml_settings(str, YAML.Game, "GameVR_Info.CRASHGEN_LatestVer") or ""
        self.crashgen_ignore = set(yaml_settings(list[str], YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.CRASHGEN_Ignore") or [])
        self.warn_noplugins = yaml_settings(str, YAML.Game, "Warnings_CRASHGEN.Warn_NOPlugins") or ""
        self.warn_outdated = yaml_settings(str, YAML.Game, "Warnings_CRASHGEN.Warn_Outdated") or ""
        self.xse_acronym = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym") or ""
        self.game_ignore_plugins = yaml_settings(list[str], YAML.Game, "Crashlog_Plugins_Exclude") or []
        self.game_ignore_records = yaml_settings(list[str], YAML.Game, "Crashlog_Records_Exclude") or []
        self.suspects_error_list = yaml_settings(dict[str, str], YAML.Game, "Crashlog_Error_Check") or {}
        self.suspects_stack_list = yaml_settings(dict[str, list[str]], YAML.Game, "Crashlog_Stack_Check") or {}
        self.autoscan_text = yaml_settings(str, YAML.Main, f"CLASSIC_Interface.autoscan_text_{GlobalRegistry.get_game()}") or ""
        self.ignore_list = yaml_settings(list[str], YAML.Ignore, f"CLASSIC_Ignore_{GlobalRegistry.get_game()}") or []
        self.game_mods_conf = yaml_settings(dict[str, str], YAML.Game, "Mods_CONF") or {}
        self.game_mods_core = yaml_settings(dict[str, str], YAML.Game, "Mods_CORE") or {}
        self.game_mods_core_folon = yaml_settings(dict[str, str], YAML.Game, "Mods_CORE_FOLON") or {}
        self.game_mods_freq = yaml_settings(dict[str, str], YAML.Game, "Mods_FREQ") or {}
        self.game_mods_opc2 = yaml_settings(dict[str, str], YAML.Game, "Mods_OPC2") or {}
        self.game_mods_solu = yaml_settings(dict[str, str], YAML.Game, "Mods_SOLU") or {}
        self.game_version = Version(yaml_settings(str, YAML.Game, "Game_Info.GameVersion") or str(NULL_VERSION))
        self.game_version_new = Version(yaml_settings(str, YAML.Game, "Game_Info.GameVersionNEW") or str(NULL_VERSION))
        self.game_version_vr = Version(yaml_settings(str, YAML.Game, "GameVR_Info.GameVersion") or str(NULL_VERSION))
