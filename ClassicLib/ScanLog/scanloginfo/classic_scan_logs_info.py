"""
Configuration dataclass for scan log operations.

This module provides the ClassicScanLogsInfo dataclass that holds
all configuration data loaded from YAML settings for scan operations.
"""

from dataclasses import dataclass, field

from packaging.version import Version

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import NULL_VERSION, YAML


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
