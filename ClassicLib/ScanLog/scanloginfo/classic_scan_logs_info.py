"""A module for handling classic scan log information with dataclass modeling.

This module defines the `ClassicScanLogsInfo` class, which encapsulates various
properties and configurations related to classic scan logs, including game hints,
records, versioning details, and plugin/mod configurations. The information is
populated from cached YAML settings, and the class verifies the initialization of
necessary resources during its instantiation.
"""

from dataclasses import dataclass, field

from packaging.version import Version

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import NULL_VERSION, YAML


# noinspection PyUnresolvedReferences
@dataclass
class ClassicScanLogsInfo:
    """
    Represents the information and metadata regarding classic scan logs in a gaming system.

    This class is used for managing and organizing details about classic scan logs, including
    game hints, records, versions, crash generation details, warnings, and mod configuration.
    It also ensures that necessary external dependencies, such as YAML cache, are properly
    initialized before accessing the data.

    Attributes:
        classic_game_hints (list[str]): List of game hints related to classic logs.
        classic_records_list (list[str]): List of classic record data related to logs.
        classic_version (str): Version of the classic log system.
        classic_version_date (str): Release date of the classic version.
        crashgen_name (str): Name of the crash generation log.
        crashgen_latest_og (str): Latest version detail for the crash generation (original).
        crashgen_latest_vr (str): Latest version detail for the crash generation (VR).
        crashgen_ignore (set): Set of ignored crash generation logs.
        warn_noplugins (str): Warning message for missing plugins.
        warn_outdated (str): Warning message for outdated records or configurations.
        xse_acronym (str): Acronym used for XSE terminology in the classic logs.
        game_ignore_plugins (list[str]): List of plugins to ignore during game scanning.
        game_ignore_records (list[str]): List of records to ignore during game scanning.
        suspects_error_list (dict[str, str]): Mapping of error codes to respective descriptions.
        suspects_stack_list (dict[str, list[str]]): Mapping of suspect stack traces to descriptions.
        autoscan_text (str): Auto-scan text output for classic interface.
        ignore_list (list[str]): List of entries to ignore in classic logs processing.
        game_mods_conf (dict[str, str]): Configuration details for mods in the game.
        game_mods_core (dict[str, str]): Core mods configuration details.
        game_mods_core_folon (dict[str, str]): FOLON mods configuration details.
        game_mods_freq (dict[str, str]): Frequency mods configuration data.
        game_mods_opc2 (dict[str, str]): OPC2 mods configuration details.
        game_mods_solu (dict[str, str]): Solution mods configuration data.
        game_version (Version): The detected version of the game.
        game_version_new (Version): The new or updated detected version of the game.
        game_version_vr (Version): The detected version of the game in VR mode.
    """

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
    # Internal flag to skip __post_init__ for async factory
    _skip_post_init: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        """
        Initializes and validates YAML cache settings while performing batch operations
        to retrieve essential configuration values. This method is executed after the
        dataclass initialization (`__post_init__`). It ensures mandatory dependencies
        are registered in the `GlobalRegistry` and retrieves a comprehensive set of
        game-specific configurations from a YAML cache. The retrieved values are then
        processed and assigned as attributes.

        Note: This uses the sync version for backward compatibility. For async contexts,
        use the create_async() class method instead.

        Raises:
            TypeError: If `YAML Cache` is not initialized in `GlobalRegistry`.

        """
        # Skip if called from async factory
        if self._skip_post_init:
            return

        if not GlobalRegistry.is_registered(GlobalRegistry.Keys.YAML_CACHE):
            raise TypeError("YAML Cache is not initialized.")

        from ClassicLib.PerformanceMonitor import TimedBlock
        from ClassicLib.YamlSettingsCache import yaml_cache

        # Batch load all settings in a single operation
        with TimedBlock("ScanLogInfo Settings Load", log_level="debug"):
            requests = self._get_settings_requests()

            # Get all values in one batch operation (sync version)
            values = yaml_cache.batch_get_settings(requests)
            self._assign_values(values)

    @classmethod
    def _get_settings_requests(cls) -> list[tuple[type, YAML, str]]:
        """
        Build the list of settings requests.

        Returns:
            list: List of (type, YAML, key_path) tuples for batch loading
        """
        return [
            (list[str], YAML.Game, "Game_Hints"),
            (list[str], YAML.Main, "catch_log_records"),
            (str, YAML.Main, "CLASSIC_Info.version"),
            (str, YAML.Main, "CLASSIC_Info.version_date"),
            (str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.CRASHGEN_LogName"),
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

    def _assign_values(self, values: list) -> None:
        """
        Assign values from batch_get_settings result to attributes.

        Args:
            values: List of values from batch_get_settings
        """
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

    @classmethod
    async def create_async(cls) -> "ClassicScanLogsInfo":
        """
        Async factory method to create ClassicScanLogsInfo without blocking.

        This method should be used when creating ClassicScanLogsInfo in async contexts
        to avoid AsyncBridge overhead.

        Returns:
            ClassicScanLogsInfo: Initialized instance with all settings loaded

        Raises:
            TypeError: If `YAML Cache` is not initialized in `GlobalRegistry`.

        Example:
            async def main():
                info = await ClassicScanLogsInfo.create_async()
        """
        if not GlobalRegistry.is_registered(GlobalRegistry.Keys.YAML_CACHE):
            raise TypeError("YAML Cache is not initialized.")

        from ClassicLib.PerformanceMonitor import TimedBlock
        from ClassicLib.YamlSettingsCache import yaml_cache

        # Create instance without loading (skip __post_init__ logic)
        instance = cls.__new__(cls)
        # Initialize all fields with defaults manually (since we skipped __init__)
        instance._skip_post_init = True
        instance.classic_game_hints = []
        instance.classic_records_list = []
        instance.classic_version = ""
        instance.classic_version_date = ""
        instance.crashgen_name = ""
        instance.crashgen_latest_og = ""
        instance.crashgen_latest_vr = ""
        instance.crashgen_ignore = set()
        instance.warn_noplugins = ""
        instance.warn_outdated = ""
        instance.xse_acronym = ""
        instance.game_ignore_plugins = []
        instance.game_ignore_records = []
        instance.suspects_error_list = {}
        instance.suspects_stack_list = {}
        instance.autoscan_text = ""
        instance.ignore_list = []
        instance.game_mods_conf = {}
        instance.game_mods_core = {}
        instance.game_mods_core_folon = {}
        instance.game_mods_freq = {}
        instance.game_mods_opc2 = {}
        instance.game_mods_solu = {}
        instance.game_version = NULL_VERSION
        instance.game_version_new = NULL_VERSION
        instance.game_version_vr = NULL_VERSION

        # Batch load all settings in async context
        with TimedBlock("ScanLogInfo Settings Load (async)", log_level="debug"):
            requests = cls._get_settings_requests()

            # Get all values in one batch operation (async version)
            values = await yaml_cache.batch_get_settings_async(requests)
            instance._assign_values(values)

        return instance
