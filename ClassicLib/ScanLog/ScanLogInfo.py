import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from packaging.version import Version

from ClassicLib import GlobalRegistry, msg_error
from ClassicLib.Constants import NULL_VERSION, YAML


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
            # Use FileIOCore for async loading
            from ClassicLib.AsyncBridge import run_async
            from ClassicLib.FileIOCore import FileIOCore

            async def load_all_logs() -> dict[str, bytes]:
                io_core = FileIOCore()
                results = {}
                for file in logfiles:
                    try:
                        content = await io_core.read_bytes(file)
                        results[file.name] = content
                    except (OSError, ValueError, UnicodeDecodeError) as e:
                        msg_error(f"Error reading {file}: {e}")
                return results

            self.cache = run_async(load_all_logs())
            from ClassicLib.Logger import logger

            logger.debug(f"Loaded {len(self.cache)} crash logs using FileIOCore")
        except (ImportError, RuntimeError, OSError):
            # Fallback to parallel sync loading for better performance
            def load_file(file: Path) -> tuple[str, bytes | None]:
                """Load a single file and return its name and content."""
                try:
                    return file.name, file.read_bytes()
                except OSError as e:
                    msg_error(f"Error reading {file}: {e}")
                    return file.name, None

            # Use ThreadPoolExecutor for parallel file loading
            with ThreadPoolExecutor(max_workers=min(8, len(logfiles))) as executor:
                futures = {executor.submit(load_file, file): file for file in logfiles}
                for future in as_completed(futures):
                    name, content = future.result()
                    if content is not None:
                        self.cache[name] = content

            from ClassicLib.Logger import logger

            logger.debug(f"Loaded {len(self.cache)} crash logs using parallel sync I/O")

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

        from ClassicLib.PerformanceMonitor import TimedBlock
        from ClassicLib.YamlSettingsCache import yaml_cache

        # Batch load all settings in a single operation
        with TimedBlock("ScanLogInfo Settings Load", log_level="debug"):
            requests = [
                (list[str], YAML.Game, "Game_Hints"),
                (list[str], YAML.Main, "catch_log_records"),
                (str, YAML.Main, "CLASSIC_Info.version"),
                (str, YAML.Main, "CLASSIC_Info.version_date"),
                (str, YAML.Game, "Game_Info.CRASHGEN_LogName"),
                (str, YAML.Game, "Game_Info.CRASHGEN_LatestVer"),
                (str, YAML.Game, "GameVR_Info.CRASHGEN_LatestVer"),
                (list[str], YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.CRASHGEN_Ignore"),
                (str, YAML.Game, "Warnings_CRASHGEN.Warn_NOPlugins"),
                (str, YAML.Game, "Warnings_CRASHGEN.Warn_Outdated"),
                (str, YAML.Game, "Game_Info.XSE_Acronym"),
                (list[str], YAML.Game, "Crashlog_Plugins_Exclude"),
                (list[str], YAML.Game, "Crashlog_Records_Exclude"),
                (dict[str, str], YAML.Game, "Crashlog_Error_Check"),
                (dict[str, list[str]], YAML.Game, "Crashlog_Stack_Check"),
                (str, YAML.Main, f"CLASSIC_Interface.autoscan_text_{GlobalRegistry.get_game()}"),
                (list[str], YAML.Ignore, f"CLASSIC_Ignore_{GlobalRegistry.get_game()}"),
                (dict[str, str], YAML.Game, "Mods_CONF"),
                (dict[str, str], YAML.Game, "Mods_CORE"),
                (dict[str, str], YAML.Game, "Mods_CORE_FOLON"),
                (dict[str, str], YAML.Game, "Mods_FREQ"),
                (dict[str, str], YAML.Game, "Mods_OPC2"),
                (dict[str, str], YAML.Game, "Mods_SOLU"),
                (str, YAML.Game, "Game_Info.GameVersion"),
                (str, YAML.Game, "Game_Info.GameVersionNEW"),
                (str, YAML.Game, "GameVR_Info.GameVersion"),
            ]

            # Get all values in one batch operation
            values = yaml_cache.batch_get_settings(requests)

        # Unpack and assign values with defaults
        self.classic_game_hints = values[0] or []
        self.classic_records_list = values[1] or []
        self.classic_version = values[2] or ""
        self.classic_version_date = values[3] or ""
        self.crashgen_name = values[4] or ""
        self.crashgen_latest_og = values[5] or ""
        self.crashgen_latest_vr = values[6] or ""
        self.crashgen_ignore = set(values[7] or [])
        self.warn_noplugins = values[8] or ""
        self.warn_outdated = values[9] or ""
        self.xse_acronym = values[10] or ""
        self.game_ignore_plugins = values[11] or []
        self.game_ignore_records = values[12] or []
        self.suspects_error_list = values[13] or {}
        self.suspects_stack_list = values[14] or {}
        self.autoscan_text = values[15] or ""
        self.ignore_list = values[16] or []
        self.game_mods_conf = values[17] or {}
        self.game_mods_core = values[18] or {}
        self.game_mods_core_folon = values[19] or {}
        self.game_mods_freq = values[20] or {}
        self.game_mods_opc2 = values[21] or {}
        self.game_mods_solu = values[22] or {}
        self.game_version = Version(values[23] or str(NULL_VERSION))
        self.game_version_new = Version(values[24] or str(NULL_VERSION))
        self.game_version_vr = Version(values[25] or str(NULL_VERSION))
