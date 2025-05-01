import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from packaging.version import Version

from ClassicLib.Constants import NULL_VERSION, YAML, gamevars
from ClassicLib.YamlSettingsCache import yaml_cache, yaml_settings


class SQLiteReader:
    # noinspection SpellCheckingInspection
    def __init__(self, logfiles: list[Path]) -> None:
        """
        Initializes an in-memory SQLite database and populates it with crash log data
        from provided log files. The logs are stored in a table with each entry
        containing the log file name and its binary data. Additionally, a unique index
        on the log file name is created for efficient retrieval.

        Args:
            logfiles (list[Path]): A list of file paths representing the log files to
                be read and stored in the SQLite database.
        """
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE crashlogs (logname TEXT UNIQUE, logdata BLOB)")
        self.db.execute("CREATE INDEX idx_logname ON crashlogs (logname)")
        self.db.executemany("INSERT INTO crashlogs VALUES (?, ?)",
                            ((file.name, file.read_bytes()) for file in logfiles))

    def read_log(self, logname: str) -> list[str]:
        """
        Reads log data from the database for the given logname, processes it to decode
        and split the log content into individual lines.

        The method connects to the database, retrieves data associated with the
        specified logname from the 'crashlogs' table, decodes the stored byte data
        ignoring any errors, and splits it into lines to return a list of strings for
        further use.

        Args:
            logname: The name of the log whose data is to be retrieved.
                     It is used as a key to query the 'crashlogs' table.

        Returns:
            list[str]: A list of individual log lines as strings, extracted and processed
                       from the database entry corresponding to the provided logname.
        """
        with self.db as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT logdata FROM crashlogs WHERE logname = ?", (logname,))
            return cursor.fetchone()[0].decode("utf-8", errors="ignore").splitlines()

    def close(self) -> None:
        self.db.close()


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
        if yaml_cache is None:
            raise TypeError("CMain is not initialized.")
        self.classic_game_hints = yaml_settings(list[str], YAML.Game, "Game_Hints") or []
        self.classic_records_list = yaml_settings(list[str], YAML.Main, "catch_log_records") or []
        self.classic_version = yaml_settings(str, YAML.Main, "CLASSIC_Info.version") or ""
        self.classic_version_date = yaml_settings(str, YAML.Main, "CLASSIC_Info.version_date") or ""
        self.crashgen_name = yaml_settings(str, YAML.Game, "Game_Info.CRASHGEN_LogName") or ""
        self.crashgen_latest_og = yaml_settings(str, YAML.Game, "Game_Info.CRASHGEN_LatestVer") or ""
        self.crashgen_latest_vr = yaml_settings(str, YAML.Game, "GameVR_Info.CRASHGEN_LatestVer") or ""
        self.crashgen_ignore = set(
            yaml_settings(list[str], YAML.Game, f"Game{gamevars['vr']}_Info.CRASHGEN_Ignore") or [])
        self.warn_noplugins = yaml_settings(str, YAML.Game, "Warnings_CRASHGEN.Warn_NOPlugins") or ""
        self.warn_outdated = yaml_settings(str, YAML.Game, "Warnings_CRASHGEN.Warn_Outdated") or ""
        self.xse_acronym = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym") or ""
        self.game_ignore_plugins = yaml_settings(list[str], YAML.Game, "Crashlog_Plugins_Exclude") or []
        self.game_ignore_records = yaml_settings(list[str], YAML.Game, "Crashlog_Records_Exclude") or []
        self.suspects_error_list = yaml_settings(dict[str, str], YAML.Game, "Crashlog_Error_Check") or {}
        self.suspects_stack_list = yaml_settings(dict[str, list[str]], YAML.Game,
                                                 "Crashlog_Stack_Check") or {}
        self.autoscan_text = yaml_settings(str, YAML.Main,
                                           f"CLASSIC_Interface.autoscan_text_{gamevars['game']}") or ""
        self.ignore_list = yaml_settings(list[str], YAML.Ignore,
                                         f"CLASSIC_Ignore_{gamevars['game']}") or []
        self.game_mods_conf = yaml_settings(dict[str, str], YAML.Game, "Mods_CONF") or {}
        self.game_mods_core = yaml_settings(dict[str, str], YAML.Game, "Mods_CORE") or {}
        self.game_mods_core_folon = yaml_settings(dict[str, str], YAML.Game, "Mods_CORE_FOLON") or {}
        self.game_mods_freq = yaml_settings(dict[str, str], YAML.Game, "Mods_FREQ") or {}
        self.game_mods_opc2 = yaml_settings(dict[str, str], YAML.Game, "Mods_OPC2") or {}
        self.game_mods_solu = yaml_settings(dict[str, str], YAML.Game, "Mods_SOLU") or {}
        self.game_version = Version(yaml_settings(str, YAML.Game, "Game_Info.GameVersion") or "0.0.0")
        self.game_version_new = Version(
            yaml_settings(str, YAML.Game, "Game_Info.GameVersionNEW") or "0.0.0")
        self.game_version_vr = Version(yaml_settings(str, YAML.Game, "GameVR_Info.GameVersion") or "0.0.0")
