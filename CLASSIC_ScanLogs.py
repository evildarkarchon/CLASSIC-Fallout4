import os
import random
import shutil
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlparse

import aiohttp
import regex as re
import requests
from packaging.version import Version

import CLASSIC_Main as CMain
import CLASSIC_ScanGame as CGame
from ClassicLib.Util import crashgen_version_gen

query_cache: dict[tuple[str, str], str] = {}
# Define paths for both Main and Local databases
DB_PATHS = (
    Path(f"CLASSIC Data/databases/{CMain.gamevars["game"]} FormIDs Main.db"),
    Path(f"CLASSIC Data/databases/{CMain.gamevars["game"]} FormIDs Local.db"),
)


# ================================================
# ASSORTED FUNCTIONS
# ================================================
# Nice little convenience function to abstract adding a value to a list.
def append_or_extend(value: str | int | float | list | tuple | set, destination: list[str]) -> None:
    """
    Appends a single value or extends a list with multiple values into the destination list.

    If the input `value` is a string, integer, or float, it is appended to the `destination`
    list after converting it to a string. If the `value` is a collection type such as a list,
    tuple, or set, its elements are extended into the `destination` list.

    Args:
        value: A single value to append or a collection (list, tuple, or set) whose elements
            will be extended into the destination list.
        destination: The list to which the value or collection of values will be appended
            or extended.

    Returns:
        None
    """
    if isinstance(value, list | tuple | set):
        destination.extend(value)
    else:
        destination.append(str(value))


def pastebin_fetch(url: str) -> None:
    """
    Fetches and saves raw content from a Pastebin URL to a local file.

    This function takes a Pastebin URL, converts it to its raw content version
    if necessary, downloads the content, and saves it to a specified directory.
    The output file is named based on the paste identifier extracted from the URL.

    Args:
        url: The Pastebin URL from which the content will be fetched.

    Raises:
        HTTPError: If the HTTP request to the provided URL fails.
    """
    if urlparse(url).netloc == "pastebin.com" and "/raw" not in url:
        url = url.replace("pastebin.com", "pastebin.com/raw")
    response = requests.get(url)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
    pastebin_path = Path("Crash Logs/Pastebin")
    if not pastebin_path.is_dir():
        pastebin_path.mkdir(parents=True, exist_ok=True)
    outfile = pastebin_path / f"crash-{urlparse(url).path.split("/")[-1]}.log"
    outfile.write_text(response.text, encoding="utf-8", errors="ignore")


async def pastebin_fetch_async(url: str) -> None:
    """
    Asynchronously fetches the raw content of a pastebin link and writes it to a log file.

    This function processes a given Pastebin URL, ensuring it fetches raw content if necessary,
    downloads the content asynchronously, and writes it to a local file. If the directory
    does not exist, it is created. The function operates asynchronously for network operations
    to improve efficiency in asynchronous workflows.

    Args:
        url (str): The Pastebin URL to fetch content from. The function automatically adjusts
            the URL to point to the raw content if it is not already.

    """

    if urlparse(url).netloc == "pastebin.com" and "/raw" not in url:
        url = url.replace("pastebin.com", "pastebin.com/raw")

    async with aiohttp.ClientSession() as session, session.get(url) as response:
        if response.status != 200:
            response.raise_for_status()
        content = await response.text()

    # File operations are still synchronous, but they're generally quick
    # For a fully async version, you could use aiofiles, but it's not always necessary
    pastebin_path = Path("Crash Logs/Pastebin")
    if not pastebin_path.is_dir():
        pastebin_path.mkdir(parents=True, exist_ok=True)

    outfile = pastebin_path / f"crash-{urlparse(url).path.split('/')[-1]}.log"

    # If you want fully async file operations, uncomment this and comment out the write_text line:
    # import aiofiles
    # async with aiofiles.open(outfile, 'w', encoding="utf-8", errors="ignore") as f:
    #     await f.write(content)

    # Otherwise, this is fine for most use cases:
    outfile.write_text(content, encoding="utf-8", errors="ignore")


def get_entry(formid: str, plugin: str) -> str | None:
    """
    Retrieves the entry associated with the provided `formid` and `plugin` from the cache or
    the database. If the pair is found in the query cache, it is returned directly. Otherwise,
    searches through the defined database paths, and if an entry is found, it is stored in the
    cache before returning it.

    Args:
        formid: The unique identifier associated with the entry to be retrieved.
        plugin: The name of the plugin associated with the specified `formid`.

    Returns:
        str | None: The entry as a string if found; otherwise, returns None.
    """
    if (entry := query_cache.get((formid, plugin))) is not None:
        return entry

    for db_path in DB_PATHS:
        if db_path.is_file():
            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute(
                    f"SELECT entry FROM {CMain.gamevars["game"]} WHERE formid=? AND plugin=? COLLATE nocase",
                    (formid, plugin),
                )
                entry = c.fetchone()
                if entry:
                    query_cache[formid, plugin] = entry[0]
                    return entry[0]

    return None


# ================================================
# INITIAL REFORMAT FOR CRASH LOG FILES
# ================================================
def crashlogs_get_files() -> list[Path]:
    """
    Generates a list of crash log file paths from various defined directories, ensuring that necessary
    directories and files are aggregated and organized under a primary "Crash Logs" folder. This function
    handles file copying and renaming operations and supports the inclusion of custom and additional
    directories specified in settings.

    Returns:
        list[Path]: A list of `Path` objects representing all discovered and processed crash log files.
    """
    CMain.logger.debug("- - - INITIATED CRASH LOG FILE LIST GENERATION")
    classic_folder = Path.cwd()
    classic_logs = classic_folder / "Crash Logs"
    classic_pastebin = classic_logs / "Pastebin"
    custom_folder_setting = CMain.classic_settings(str, "SCAN Custom Path")
    xse_folder_setting = CMain.yaml_settings(str, CMain.YAML.Game_Local, "Game_Info.Docs_Folder_XSE")

    custom_folder = Path(custom_folder_setting) if isinstance(custom_folder_setting, str) else None
    xse_folder = Path(xse_folder_setting) if isinstance(xse_folder_setting, str) else None

    if not classic_logs.is_dir():
        classic_logs.mkdir(parents=True, exist_ok=True)
    if not classic_pastebin.is_dir():
        classic_pastebin.mkdir(parents=True, exist_ok=True)
    for file in classic_folder.glob("crash-*.log"):
        destination_file = classic_logs / file.name
        if not destination_file.is_file():
            file.rename(destination_file)
    for file in classic_folder.glob("crash-*-AUTOSCAN.md"):
        destination_file = classic_logs / file.name
        if not destination_file.is_file():
            file.rename(destination_file)
    if xse_folder and xse_folder.is_dir():
        for crash_file in xse_folder.glob("crash-*.log"):
            destination_file = classic_logs / crash_file.name
            if not destination_file.is_file():
                shutil.copy2(crash_file, destination_file)

    crash_files = list(classic_logs.rglob("crash-*.log"))
    if custom_folder and custom_folder.is_dir():
        crash_files.extend(custom_folder.glob("crash-*.log"))

    return crash_files


def crashlogs_reformat(crashlog_list: list[Path], remove_list: list[str]) -> None:
    """
    Reformats crash log files by simplifying or modifying their content based on specified settings and criteria. This function processes each log file in the provided list, removes lines containing specific substrings if 'Simplify Logs' is enabled, and reformats load order lines for consistency.

    Args:
        crashlog_list: A list of file paths representing crash log files to be reformatted.
        remove_list: A list of strings; if any of these strings appear in a log line and 'Simplify Logs'
            is enabled, the line is removed.

    """
    CMain.logger.debug("- - - INITIATED CRASH LOG FILE REFORMAT")
    simplify_logs = CMain.classic_settings(bool, "Simplify Logs")

    for file in crashlog_list:
        with file.open(encoding="utf-8", errors="ignore") as crash_log:
            crash_data = crash_log.readlines()

        last_index = len(crash_data) - 1
        in_plugins = True
        for index, line in enumerate(reversed(crash_data)):
            if in_plugins and line.startswith("PLUGINS:"):
                in_plugins = False
            reversed_index = last_index - index
            if simplify_logs and any(string in line for string in remove_list):
                # Remove *useless* lines from crash log if Simplify Logs is enabled.
                crash_data.pop(reversed_index)
            elif in_plugins and "[" in line:
                # Replace all spaces inside the load order [brackets] with 0s.
                # This maintains consistency between different versions of Buffout 4.
                # Example log lines:
                # [ 1] DLCRobot.esm
                # [FE:  0] RedRocketsGlareII.esl
                indent, rest = line.split("[", 1)
                fid, name = rest.split("]", 1)
                crash_data[reversed_index] = f"{indent}[{fid.replace(" ", "0")}]{name}"

        with file.open("w", encoding="utf-8", errors="ignore") as crash_log:
            crash_log.writelines(crash_data)


def detect_mods_single(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> bool:
    """
    Detects modifications (mods) based on provided YAML dictionary, crashlog plugins, and updates the
    autoscan report accordingly.

    This function checks if any mod names from the YAML dictionary exist in the crashlog plugins. If a match is found, it
    will append the respective plugin's identifier and a warning message to the autoscan report. If a mod in the YAML
    dictionary has no associated warning but is found in the crashlog plugins, a ValueError is raised.

    Args:
        yaml_dict (dict[str, str]): A mapping of mod names (as keys) to their respective warnings (as values).
        crashlog_plugins (dict[str, str]): A mapping of plugin names (as keys) to their corresponding identifiers
            (as values).
        autoscan_report (list[str]): A collection of strings that the function updates to log findings based on the match
            results.

    Returns:
        bool: True if at least one mod was detected in the crashlog plugins; otherwise, False.

    Raises:
        ValueError: If a mod from the YAML dictionary has no warning defined and is found in the crashlog plugins.
    """
    trigger_mod_found = False
    yaml_dict_lower = {key.lower(): value for key, value in yaml_dict.items()}
    crashlog_plugins_lower = {key.lower(): value for key, value in crashlog_plugins.items()}

    for mod_name_lower, mod_warn in yaml_dict_lower.items():
        for plugin_name_lower, plugin_fid in crashlog_plugins_lower.items():
            if mod_name_lower in plugin_name_lower:
                if mod_warn:
                    autoscan_report.extend((f"[!] FOUND : [{plugin_fid}] ", mod_warn))
                else:
                    raise ValueError(f"ERROR: {mod_name_lower} has no warning in the database!")
                trigger_mod_found = True
                break
    return trigger_mod_found


def detect_mods_double(yaml_dict: dict[str, str], crashlog_plugins: dict[str, str], autoscan_report: list[str]) -> bool:
    """
    Detects conflicts or combinations of specific plugins based on given mappings and produces warnings
    or errors if necessary.

    This function checks for combinations of mods (plugins) defined in the `yaml_dict` by iterating
    over the plugins extracted from a crash log. If a predefined combination is found, it either raises
    an error or appends a caution message to the report. Matches are case-insensitive.

    Args:
        yaml_dict (dict[str, str]): A dictionary where the key is a combination of two mod names joined
            by ' | ', and the value is either a warning message or an empty string.
        crashlog_plugins (dict[str, str]): A dictionary containing plugin names identified in a crash log.
        autoscan_report (list[str]): A list to collect warnings or other scan-related messages.

    Returns:
        bool: True if any combination of mods was found; otherwise, False.

    Raises:
        ValueError: If a detected mod combination from the database has no warning associated with it.
    """
    trigger_mod_found = False
    yaml_dict_lower = {key.lower(): value for key, value in yaml_dict.items()}
    crashlog_plugins_lower = {key.lower(): value for key, value in crashlog_plugins.items()}

    for mod_name_lower, mod_warn in yaml_dict_lower.items():
        mod_split = mod_name_lower.split(" | ", 1)
        mod1_found = mod2_found = False
        for plugin_name_lower in crashlog_plugins_lower:
            if not mod1_found and mod_split[0] in plugin_name_lower:
                mod1_found = True
                continue
            if not mod2_found and mod_split[1] in plugin_name_lower:
                mod2_found = True
                continue
        if mod1_found and mod2_found:
            if mod_warn:
                autoscan_report.extend(("[!] CAUTION : ", mod_warn))
            else:
                raise ValueError(f"ERROR: {mod_name_lower} has no warning in the database!")
            trigger_mod_found = True
    return trigger_mod_found


def detect_mods_important(yaml_dict: dict[str, str],
                          crashlog_plugins: dict[str, str],
                          autoscan_report: list[str],
                          gpu_rival: Literal["nvidia", "amd"] | None) -> None:
    """
    Detects and evaluates important mods based on provided information, updating a report accordingly.

    This function processes a dictionary of mods and their warnings, compares them
    against available plugins, and generates a report indicating whether a mod is
    installed and compatible with the specified GPU (if provided). It appends the
    status and any relevant warnings to the auto-scan report.

    Args:
        yaml_dict (dict[str, str]): A dictionary where keys represent mod names
            and values contain any warnings or messages associated with those mods.
        crashlog_plugins (dict[str, str]): A dictionary of plugins present in the
            crash log, used to check for installed mods.
        autoscan_report (list[str]): A list that serves as a report, updated with
            the status of mods (installed, not installed, or incompatible).
        gpu_rival (Literal["nvidia", "amd"] | None): An optional indicator of a GPU
            type to be compared against mod warnings. If provided, it is used to
            adjust the compatibility checks and generate warnings.
    """
    for mod_name in yaml_dict:
        mod_warn = yaml_dict.get(mod_name, "")
        mod_split = mod_name.split(" | ", 1)
        mod_found = False
        for plugin_name in crashlog_plugins:
            if mod_split[0].lower() in plugin_name.lower():
                mod_found = True
                continue
        if mod_found:
            if gpu_rival and cast("str", gpu_rival) in mod_warn.lower():
                autoscan_report.extend((
                    f"❓ {mod_split[1]} is installed, BUT IT SEEMS YOU DON'T HAVE AN {gpu_rival.upper()} GPU?\n",
                    "IF THIS IS CORRECT, COMPLETELY UNINSTALL THIS MOD TO AVOID ANY PROBLEMS! \n\n",
                ))
            else:
                autoscan_report.append(f"✔️ {mod_split[1]} is installed!\n\n")
        elif (gpu_rival and mod_warn) and gpu_rival not in mod_warn.lower():
            autoscan_report.extend((f"❌ {mod_split[1]} is not installed!\n", mod_warn, "\n"))


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
    game_version: Version = field(default=CMain.NULL_VERSION, init=False)
    game_version_new: Version = field(default=CMain.NULL_VERSION, init=False)
    game_version_vr: Version = field(default=CMain.NULL_VERSION, init=False)

    def __post_init__(self) -> None:
        if CMain.yaml_cache is None:
            raise TypeError("CMain is not initialized.")
        self.classic_game_hints = CMain.yaml_settings(list[str], CMain.YAML.Game, "Game_Hints") or []
        self.classic_records_list = CMain.yaml_settings(list[str], CMain.YAML.Main, "catch_log_records") or []
        self.classic_version = CMain.yaml_settings(str, CMain.YAML.Main, "CLASSIC_Info.version") or ""
        self.classic_version_date = CMain.yaml_settings(str, CMain.YAML.Main, "CLASSIC_Info.version_date") or ""
        self.crashgen_name = CMain.yaml_settings(str, CMain.YAML.Game, "Game_Info.CRASHGEN_LogName") or ""
        self.crashgen_latest_og = CMain.yaml_settings(str, CMain.YAML.Game, "Game_Info.CRASHGEN_LatestVer") or ""
        self.crashgen_latest_vr = CMain.yaml_settings(str, CMain.YAML.Game, "GameVR_Info.CRASHGEN_LatestVer") or ""
        self.crashgen_ignore = set(
            CMain.yaml_settings(list[str], CMain.YAML.Game, f"Game{CMain.gamevars['vr']}_Info.CRASHGEN_Ignore") or [])
        self.warn_noplugins = CMain.yaml_settings(str, CMain.YAML.Game, "Warnings_CRASHGEN.Warn_NOPlugins") or ""
        self.warn_outdated = CMain.yaml_settings(str, CMain.YAML.Game, "Warnings_CRASHGEN.Warn_Outdated") or ""
        self.xse_acronym = CMain.yaml_settings(str, CMain.YAML.Game, "Game_Info.XSE_Acronym") or ""
        self.game_ignore_plugins = CMain.yaml_settings(list[str], CMain.YAML.Game, "Crashlog_Plugins_Exclude") or []
        self.game_ignore_records = CMain.yaml_settings(list[str], CMain.YAML.Game, "Crashlog_Records_Exclude") or []
        self.suspects_error_list = CMain.yaml_settings(dict[str, str], CMain.YAML.Game, "Crashlog_Error_Check") or {}
        self.suspects_stack_list = CMain.yaml_settings(dict[str, list[str]], CMain.YAML.Game,
                                                       "Crashlog_Stack_Check") or {}
        self.autoscan_text = CMain.yaml_settings(str, CMain.YAML.Main,
                                                 f"CLASSIC_Interface.autoscan_text_{CMain.gamevars['game']}") or ""
        self.ignore_list = CMain.yaml_settings(list[str], CMain.YAML.Ignore,
                                               f"CLASSIC_Ignore_{CMain.gamevars['game']}") or []
        self.game_mods_conf = CMain.yaml_settings(dict[str, str], CMain.YAML.Game, "Mods_CONF") or {}
        self.game_mods_core = CMain.yaml_settings(dict[str, str], CMain.YAML.Game, "Mods_CORE") or {}
        self.game_mods_core_folon = CMain.yaml_settings(dict[str, str], CMain.YAML.Game, "Mods_CORE_FOLON") or {}
        self.game_mods_freq = CMain.yaml_settings(dict[str, str], CMain.YAML.Game, "Mods_FREQ") or {}
        self.game_mods_opc2 = CMain.yaml_settings(dict[str, str], CMain.YAML.Game, "Mods_OPC2") or {}
        self.game_mods_solu = CMain.yaml_settings(dict[str, str], CMain.YAML.Game, "Mods_SOLU") or {}
        self.game_version = Version(CMain.yaml_settings(str, CMain.YAML.Game, "Game_Info.GameVersion") or "0.0.0")
        self.game_version_new = Version(
            CMain.yaml_settings(str, CMain.YAML.Game, "Game_Info.GameVersionNEW") or "0.0.0")
        self.game_version_vr = Version(CMain.yaml_settings(str, CMain.YAML.Game, "GameVR_Info.GameVersion") or "0.0.0")


# noinspection PyUnresolvedReferences,PyPep8Naming
class ClassicScanLogs:
    def __init__(self) -> None:
        self.pluginsearch = re.compile(r"\s*\[(FE:([0-9A-F]{3})|[0-9A-F]{2})\]\s*(.+?(?:\.es[pml])+)",
                                       flags=re.IGNORECASE)
        self.crashlog_list = crashlogs_get_files()
        print("REFORMATTING CRASH LOGS, PLEASE WAIT...\n")
        self.remove_list = CMain.yaml_settings(list[str], CMain.YAML.Main, "exclude_log_records") or []
        crashlogs_reformat(self.crashlog_list, self.remove_list)
        self.yamldata = ClassicScanLogsInfo()
        self.xse_acronym = self.yamldata.xse_acronym.lower()
        self.fcx_mode = CMain.classic_settings(bool, "FCX Mode")
        self.show_formid_values = CMain.classic_settings(bool, "Show FormID Values")
        self.formid_db_exists = any(db.is_file() for db in DB_PATHS)
        self.move_unsolved_logs = CMain.classic_settings(bool, "Move Unsolved Logs")
        self.lower_records = [record.lower() for record in self.yamldata.classic_records_list]
        self.lower_ignore = [record.lower() for record in self.yamldata.game_ignore_records]
        self.lower_plugins_ignore = {ignore.lower() for ignore in self.yamldata.game_ignore_plugins}
        self.ignore_plugins_list = {item.lower() for item in
                                    self.yamldata.ignore_list} if self.yamldata.ignore_list else set()
        print("SCANNING CRASH LOGS, PLEASE WAIT...\n")
        self.scan_start_time = time.perf_counter()
        self.crashlogs = SQLiteReader(self.crashlog_list)
        self.main_files_check = ""
        self.game_files_check = ""
        self.scan_failed_list: list[str] = []
        self.user_folder = Path.home()
        self.stats_crashlog_scanned = 0
        self.stats_crashlog_incomplete = 0
        self.stats_crashlog_failed = 0
        CMain.logger.info(f"- - - INITIATED CRASH LOG FILE SCAN >>> CURRENTLY SCANNING {len(self.crashlog_list)} FILES")

    def close_database(self) -> None:
        """Close the SQLite database."""
        self.crashlogs.close()

    def fcx_mode_check(self) -> None:
        """
        Checks the FCX mode status and performs corresponding file integrity checks.

        If FCX mode is enabled, this method performs integrity checks for the main
        files and game files by invoking the respective methods. If FCX mode is
        disabled, it sets the results to indicate that checks are skipped.

        Attributes:
            main_files_check (str): The result of the main files check. If FCX mode is
                disabled, it contains a message indicating the check was skipped.
            game_files_check (str): The result of the game files check. If FCX mode is
                disabled, it is set to an empty string.
        """
        if self.fcx_mode:
            self.main_files_check = CMain.main_combined_result()
            self.game_files_check = CGame.game_combined_result()
        else:
            self.main_files_check = "❌ FCX Mode is disabled, skipping game files check... \n-----\n"
            self.game_files_check = ""

    def find_segments(self, crash_data: list[str], crashgen_name: str) -> tuple[str, str, str, list[list[str]]]:
        """
        Finds and extracts structured segments from the crash report data based on predefined boundary markers. This function
        parses sections such as crash generation details, system specifications, probable call stack, module details, XSE plugins,
        and general plugins. The extracted segments are returned alongside metadata such as the game version, crash generator name,
        and the main error message from the crash log.

        Args:
            crash_data (list[str]): The raw crash report data represented as a list of strings.
            crashgen_name (str): The designated crash generator name to identify the associated crash details.

        Returns:
            tuple[str, str, str, list[list[str]]]: A tuple containing:
                - The identified game version from the crash log or "UNKNOWN" if not found.
                - The identified crash generator version or "UNKNOWN" if not found.
                - The primary error message extracted from the crash log or "UNKNOWN" if not found.
                - A list of lists, where each nested list contains stripped lines belonging to a specific segment of the crash log.
        """
        xse = self.yamldata.xse_acronym.upper()
        segment_boundaries = (
            ("	[Compatibility]", "SYSTEM SPECS:"),  # segment_crashgen
            ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),  # segment_system
            ("PROBABLE CALL STACK:", "MODULES:"),  # segment_callstack
            ("MODULES:", f"{xse} PLUGINS:"),  # segment_allmodules
            (f"{xse} PLUGINS:", "PLUGINS:"),  # segment_xsemodules
            ("PLUGINS:", "EOF"),  # segment_plugins
        )
        segment_index = 0
        collect = False
        segments: list[list[str]] = []
        next_boundary = segment_boundaries[0][0]
        index_start = 0
        total = len(crash_data)
        current_index = 0
        crashlog_gameversion = None
        crashlog_crashgen = None
        crashlog_mainerror = None
        game_root_name = CMain.yaml_settings(str, CMain.YAML.Game, f"Game_{CMain.gamevars["vr"]}Info.Main_Root_Name")
        while current_index < total:
            line = crash_data[current_index]
            if crashlog_gameversion is None and game_root_name and line.startswith(game_root_name):
                crashlog_gameversion = line.strip()
            if crashlog_crashgen is None:
                if line.startswith(crashgen_name):
                    crashlog_crashgen = line.strip()
            elif crashlog_mainerror is None and line.startswith("Unhandled exception"):
                crashlog_mainerror = line.replace("|", "\n", 1)

            elif line.startswith(next_boundary):
                if collect:
                    index_end = current_index - 1 if current_index > 0 else current_index
                    segments.append(crash_data[index_start:index_end])
                    segment_index += 1
                    if segment_index == len(segment_boundaries):
                        break
                else:
                    index_start = current_index + 1 if total > current_index else current_index
                collect = not collect
                next_boundary = segment_boundaries[segment_index][collect]
                if collect:
                    if next_boundary == "EOF":
                        segments.append(crash_data[index_start:])
                        break
                else:
                    # Don't increase current_index in case the current
                    # line is also the next start boundary
                    continue
            current_index += 1
            if collect and current_index == total:
                segments.append(crash_data[index_start:])

        segment_results = [[line.strip() for line in segment] for segment in segments] if segments else segments
        missing_segments = len(segment_boundaries) - len(segment_results)
        if missing_segments > 0:
            segment_results.extend([[]] * missing_segments)
        # Set default values incase actual index is not found.
        return crashlog_gameversion or "UNKNOWN", crashlog_crashgen or "UNKNOWN", crashlog_mainerror or "UNKNOWN", segment_results

    @staticmethod
    def loadorder_scan_loadorder_txt(autoscan_report: list[str]) -> tuple[dict[str, str], bool]:
        """
        Parses the 'loadorder.txt' file and updates the autoscan report. It processes the file to
        determine plugins in a specific load order and marks whether any plugins were loaded as a
        result.

        The 'loadorder.txt' information ensures the application prioritizes plugins detected from
        this file over those detected from crash logs. If the file is removed, the application
        will revert to its default behavior of detecting plugins from crash logs.

        Args:
            autoscan_report (list[str]): The current autoscan report to append messages indicating
                the presence and usage of the 'loadorder.txt' file.

        Returns:
            tuple[dict[str, str], bool]:
                - A dictionary of plugins (keys) with their load origin "LO" (value) based on
                  'loadorder.txt'.
                - A boolean indicating whether any plugins were successfully loaded from
                  'loadorder.txt'.
        """
        append_or_extend((
            "* ✔️ LOADORDER.TXT FILE FOUND IN THE MAIN CLASSIC FOLDER! *\n",
            "CLASSIC will now ignore plugins in all crash logs and only detect plugins in this file.\n",
            "[ To disable this functionality, simply remove loadorder.txt from your CLASSIC folder. ]\n\n",
        ), autoscan_report)
        trigger_plugins_loaded = False
        loadorder_path = Path("loadorder.txt")
        crashlog_plugins: dict[str, str] = {}
        with loadorder_path.open(encoding="utf-8", errors="ignore") as loadorder_file:
            loadorder_data = loadorder_file.readlines()
        for elem in loadorder_data[1:]:
            if all(elem not in item for item in crashlog_plugins):
                crashlog_plugins[elem] = "LO"
                if not trigger_plugins_loaded:
                    trigger_plugins_loaded = True
        return crashlog_plugins, trigger_plugins_loaded

    def loadorder_scan_log(self, segment_plugins: list[str], game_version: Version, version_current: Version) -> tuple[
        dict[str, str], bool, bool]:
        """
        Scans load order logs to extract plugin information, which helps determine plugin-related issues
        in a specific game version and its compatibility. It identifies potential plugin limit triggers,
        disabled limit checks, and classifies plugins based on their unique identifiers or names.

        Args:
            segment_plugins (list[str]): A list of plugin entries from the scanned load order log.
            game_version (Version): The current game version being analyzed.
            version_current (Version): The version of the game currently in use.

        Returns:
            tuple[dict[str, str], bool, bool]: A tuple containing three elements:
                - A dictionary mapping plugin names to their unique identifiers or statuses.
                - A boolean indicating whether the plugin limit trigger has been activated.
                - A boolean indicating whether the plugin limit check has been disabled under specific conditions.
        """
        if not segment_plugins:
            return {}, False, False

        is_og = game_version in (self.yamldata.game_version, self.yamldata.game_version_vr)
        is_ng = game_version >= self.yamldata.game_version_new and version_current < Version("1.37.0")
        crashlog_plugins: dict[str, str] = {}
        trigger_plugin_limit = trigger_limit_check_disabled = False
        for elem in segment_plugins:
            if "[FF]" in elem:
                if is_og:
                    trigger_plugin_limit = True
                elif is_ng:
                    trigger_limit_check_disabled = True
            pluginmatch = self.pluginsearch.match(elem, concurrent=True)
            if pluginmatch is not None:
                plugin_fid = pluginmatch.group(1)
                plugin_name = pluginmatch.group(3)
                is_unique = plugin_name and plugin_name not in crashlog_plugins
                if plugin_fid is not None and is_unique:
                    crashlog_plugins[plugin_name] = plugin_fid.replace(":", "")
                elif plugin_name and "dll" in plugin_name.lower():
                    crashlog_plugins[plugin_name] = "DLL"
                else:
                    crashlog_plugins[plugin_name] = "???"
        return crashlog_plugins, trigger_plugin_limit, trigger_limit_check_disabled

    def suspect_scan_mainerror(self, autoscan_report: list[str], crashlog_mainerror: str, max_warn_length: int) -> bool:
        """
        Scans for main errors in the autoscan report based on a list of suspect errors and
        signals. Matches errors in the crash log main error with predefined suspect signals
        and adds detailed error information to the autoscan report if a match is found. A
        flag indicating whether any suspect was found is returned.

        Args:
            autoscan_report (list[str]): A list containing lines of the autoscan report
                where detected errors will be appended.
            crashlog_mainerror (str): A string containing the main error log which is
                checked for suspect signals.
            max_warn_length (int): The maximum allowed length of the warning label in
                the autoscan report.

        Returns:
            bool: True if any suspect error was found in the crash log main error;
                False otherwise.
        """
        trigger_suspect_found = False
        for error, signal in self.yamldata.suspects_error_list.items():
            error_severity, error_name = error.split(" | ", 1)
            if signal in crashlog_mainerror:
                error_name = error_name.ljust(max_warn_length, ".")
                append_or_extend(
                    f"# Checking for {error_name} SUSPECT FOUND! > Severity : {error_severity} # \n-----\n",
                    autoscan_report)
                if not trigger_suspect_found:
                    trigger_suspect_found = True
        return trigger_suspect_found

    def suspect_scan_stack(self, crashlog_mainerror: str, segment_callstack_intact: str, autoscan_report: list[str],
                           max_warn_length: int) -> bool:
        """
        Scans a crash log's main error and call stack for patterns defined in the suspects
        stack list to identify potential issues and appends relevant findings to the autoscan
        report if any suspects are found.

        The function evaluates signals specified in the suspects stack list, which are categorized
        by modifiers such as "ME-REQ", "ME-OPT", "NOT", or numerical counts. The analysis determines
        whether required or optional patterns are matched, or specific conditions exist in the
        call stack segment. Based on these conditions, the report is updated with findings.

        Args:
            crashlog_mainerror (str): The main error string from the crash log to be analyzed
                against the suspects stack list.
            segment_callstack_intact (str): Complete call stack segment as a string to identify
                patterns or conditions specified in the suspects stack list.
            autoscan_report (list[str]): A list to store detailed findings and results of the
                scan for suspects for further review.
            max_warn_length (int): Maximum length used to format suspect issue names or warnings
                when appending them to the report.

        Returns:
            bool: True if at least one suspect is found based on the analysis; otherwise, False.
        """
        trigger_suspect_found = False
        for error in self.yamldata.suspects_stack_list:
            error_severity, error_name = error.split(" | ", 1)
            error_req_found = error_opt_found = stack_found = False
            signal_list = self.yamldata.suspects_stack_list.get(error, [])
            has_required_item = False
            for signal in signal_list:
                if "|" in signal:
                    signal_modifier, signal_string = signal.split("|", 1)
                    match signal_modifier:
                        case "ME-REQ":
                            has_required_item = True
                            if signal_string in crashlog_mainerror:
                                error_req_found = True
                        case "ME-OPT":
                            if signal_string in crashlog_mainerror:
                                error_opt_found = True
                        case "NOT" if signal_string in segment_callstack_intact:
                            break
                        case _ if signal_modifier.isdecimal():
                            if segment_callstack_intact.count(signal_string) >= int(signal_modifier):
                                stack_found = True
                elif signal in segment_callstack_intact:
                    stack_found = True

            # print(f"TEST: {error_req_found} | {error_opt_found} | {stack_found}")
            if has_required_item:
                if error_req_found:
                    error_name = error_name.ljust(max_warn_length, ".")
                    append_or_extend(
                        f"# Checking for {error_name} SUSPECT FOUND! > Severity : {error_severity} # \n-----\n",
                        autoscan_report)
                    trigger_suspect_found = True
            elif error_opt_found or stack_found:
                error_name = error_name.ljust(max_warn_length, ".")
                append_or_extend(
                    f"# Checking for {error_name} SUSPECT FOUND! > Severity : {error_severity} # \n-----\n",
                    autoscan_report)
                trigger_suspect_found = True
        return trigger_suspect_found

    def scan_buffout_achievements_setting(self, autoscan_report: list[str], xsemodules: set[str],
                                          crashgen: dict[str, bool | int | str]) -> None:
        """
        Validates the configuration of the Achievements parameter in the crash generator settings file
        (crashgen) against installed modules in XSE (xsemodules) and updates the autoscan report with
        findings, including necessary fixes if a conflict is detected.

        Args:
            autoscan_report: The report list where messages about the configuration status are
                appended or extended.
            xsemodules: A set of strings representing the names of installed XSE modules.
            crashgen: A dictionary containing configuration values for the crash generator, where
                the key is a configuration parameter, and the value is its corresponding setting.

        """
        crashgen_achievements = crashgen.get("Achievements")
        if crashgen_achievements and ("achievements.dll" in xsemodules or "unlimitedsurvivalmode.dll" in xsemodules):
            append_or_extend((
                "# ❌ CAUTION : The Achievements Mod and/or Unlimited Survival Mode is installed, but Achievements is set to TRUE # \n",
                f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change Achievements to FALSE, this prevents conflicts with {self.yamldata.crashgen_name}.\n-----\n",
            ), autoscan_report)
        else:
            append_or_extend(
                f"✔️ Achievements parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n-----\n",
                autoscan_report
            )

    def scan_buffout_memorymanagement_settings(self, autoscan_report: list[str], crashgen: dict[str, bool | int | str],
                                               Has_XCell: bool, Has_BakaScrapHeap: bool) -> None:
        """
        Validates and scans the memory management settings in the configuration file for conflicts with
        X-Cell and the Baka ScrapHeap Mod. Generates a report based on the findings, providing guidance on
        necessary fixes if parameters are incorrectly configured.

        Args:
            autoscan_report (list[str]): A list to store findings and recommendations based on the memory
                management settings validation.
            crashgen (dict[str, bool | int | str]): A dictionary containing current CrashGen configuration
                settings, including memory management parameters and other related properties.
            Has_XCell (bool): A flag indicating whether the X-Cell mod is installed.
            Has_BakaScrapHeap (bool): A flag indicating whether the Baka ScrapHeap mod is installed.
        """
        # Check main MemoryManager setting first
        mem_manager = crashgen.get("MemoryManager")
        if mem_manager:
            if Has_XCell:
                append_or_extend((
                    "# ❌ CAUTION : X-Cell is installed, but MemoryManager parameter is set to TRUE # \n",
                    f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change MemoryManager to FALSE, this prevents conflicts with X-Cell.\n-----\n"
                ), autoscan_report)
            elif Has_BakaScrapHeap:
                append_or_extend((
                    f"# ❌ CAUTION : The Baka ScrapHeap Mod is installed, but is redundant with {self.yamldata.crashgen_name} # \n",
                    f" FIX: Uninstall the Baka ScrapHeap Mod, this prevents conflicts with {self.yamldata.crashgen_name}.\n-----\n"
                ), autoscan_report)
            else:
                append_or_extend(
                    f"✔️ Memory Manager parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n-----\n",
                    autoscan_report
                )
        elif Has_XCell:
            if Has_BakaScrapHeap:
                append_or_extend((
                    "# ❌ CAUTION : The Baka ScrapHeap Mod is installed, but is redundant with X-Cell # \n",
                    " FIX: Uninstall the Baka ScrapHeap Mod, this prevents conflicts with X-Cell.\n-----\n"
                ), autoscan_report)
            else:
                append_or_extend(
                    f"✔️ Memory Manager parameter is correctly configured for use with X-Cell in your {self.yamldata.crashgen_name} settings! \n-----\n",
                    autoscan_report
                )
        elif Has_BakaScrapHeap:
            append_or_extend((
                f"# ❌ CAUTION : The Baka ScrapHeap Mod is installed, but is redundant with {self.yamldata.crashgen_name} # \n",
                f" FIX: Uninstall the Baka ScrapHeap Mod and open {self.yamldata.crashgen_name}'s TOML file and change MemoryManager to TRUE, this improves performance.\n-----\n"
            ), autoscan_report)

        # Check other memory settings (only relevant when X-Cell is installed)
        if Has_XCell:
            memory_settings = {
                "HavokMemorySystem": "Havok Memory System",
                "BSTextureStreamerLocalHeap": "BSTextureStreamerLocalHeap",
                "ScaleformAllocator": "Scaleform Allocator",
                "SmallBlockAllocator": "Small Block Allocator"
            }

            for setting_key, setting_name in memory_settings.items():
                if crashgen.get(setting_key):
                    append_or_extend((
                        f"# ❌ CAUTION : X-Cell is installed, but {setting_key} parameter is set to TRUE # \n",
                        f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change {setting_key} to FALSE, this prevents conflicts with X-Cell.\n-----\n"
                    ), autoscan_report)
                else:
                    append_or_extend(
                        f"✔️ {setting_name} parameter is correctly configured for use with X-Cell in your {self.yamldata.crashgen_name} settings! \n-----\n",
                        autoscan_report
                    )

    def scan_archivelimit_setting(self, autoscan_report: list[str], crashgen: dict[str, bool | int | str]) -> None:
        """
        Scans the 'ArchiveLimit' setting in the crashgen configuration and appends either
        a warning or confirmation message to the autoscan_report.

        This method evaluates the 'ArchiveLimit' parameter of the crashgen configuration;
        if the parameter is enabled (True), it adds a cautionary message to the report,
        notifying the user of its potential instability and providing guidance for
        disabling it. Conversely, if the parameter is disabled (False or not set), it
        adds a confirmation message to the report, indicating that the setting is
        correctly configured.

        Args:
            autoscan_report (list[str]): A list where logging or reporting messages are
                appended to indicate issues or validation details during the scan.
            crashgen (dict[str, bool | int | str]): A dictionary representing the
                crashgen configuration, which is evaluated to determine the value of
                the 'ArchiveLimit' parameter.
        """
        crashgen_archivelimit = crashgen.get("ArchiveLimit")
        if crashgen_archivelimit:
            append_or_extend(
                (
                    "# ❌ CAUTION : ArchiveLimit is set to TRUE, this setting is known to cause instability. # \n",
                    f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change ArchiveLimit to FALSE.\n-----\n",
                ),
                autoscan_report,
            )
        else:
            append_or_extend(
                f"✔️ ArchiveLimit parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n-----\n",
                autoscan_report,
            )

    def scan_buffout_looksmenu_setting(self, crashgen: dict[str, bool | int | str], autoscan_report: list[str],
                                       xsemodules: set[str]) -> None:
        """
        Scans the Buffout 4 settings for the correct configuration of the Looks Menu (F4EE)
        parameter under the `[Compatibility]` section and appends the corresponding
        messages to the autoscan report.

        This function checks if the F4EE parameter in the crashgen configuration is
        set appropriately based on the presence of `f4ee.dll` in the installed modules. If the
        parameter is incorrectly configured, it provides specific instructions for fixing the
        configuration in the TOML file. Otherwise, it confirms that the parameter is correct.

        Args:
            crashgen (dict[str, bool | int | str]): The settings dictionary containing
                configuration parameters, including the F4EE parameter under the `[Compatibility]`.
            autoscan_report (list[str]): The list used to store diagnostic messages
                regarding the scan results.
            xsemodules (set[str]): The set of installed module filenames in the current
                environment used to determine compatibility requirements.

        Returns:
            None
        """
        crashgen_f4ee = crashgen.get("F4EE")
        if crashgen_f4ee is not None:
            if not crashgen_f4ee and "f4ee.dll" in xsemodules:
                append_or_extend((
                    "# ❌ CAUTION : Looks Menu is installed, but F4EE parameter under [Compatibility] is set to FALSE # \n",
                    f" FIX: Open {self.yamldata.crashgen_name}'s TOML file and change F4EE to TRUE, this prevents bugs and crashes from Looks Menu.\n-----\n",
                ),
                    autoscan_report)
            else:
                append_or_extend(
                    f"✔️ F4EE (Looks Menu) parameter is correctly configured in your {self.yamldata.crashgen_name} settings! \n-----\n",
                    autoscan_report
                )

    def formid_match(self, formids_matches: list[str], crashlog_plugins: dict[str, str],
                     autoscan_report: list[str]) -> None:
        """
        Processes and analyzes Form IDs from the provided data sources, matching them
        against crash log plugins and generating a report based on the findings. This
        method identifies potentially relevant Form IDs present in the crash log and
        provides insights using a database, if available.

        Args:
            formids_matches (list[str]): A list of Form ID strings identified
                from the crash log.
            crashlog_plugins (dict[str, str]): A dictionary mapping plugin names
                to their associated plugin IDs.
            autoscan_report (list[str]): A list to which the method appends
                formatted analysis results.
        """
        if formids_matches:
            formids_found = dict(Counter(sorted(formids_matches)))
            for formid_full, count in formids_found.items():
                formid_split = formid_full.split(": ", 1)
                if len(formid_split) < 2:
                    continue
                for plugin, plugin_id in crashlog_plugins.items():
                    if plugin_id != formid_split[1][:2]:
                        continue

                    if self.show_formid_values and self.formid_db_exists:
                        report = get_entry(formid_split[1][2:], plugin)
                        if report:
                            append_or_extend(f"- {formid_full} | [{plugin}] | {report} | {count}\n", autoscan_report)
                            continue

                    append_or_extend(f"- {formid_full} | [{plugin}] | {count}\n", autoscan_report)
                    break
            append_or_extend((
                "\n[Last number counts how many times each Form ID shows up in the crash log.]\n",
                f"These Form IDs were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n",
                "You can try searching any listed Form IDs in xEdit and see if they lead to relevant records.\n\n",
            ), autoscan_report)
        else:
            append_or_extend("* COULDN'T FIND ANY FORM ID SUSPECTS *\n\n", autoscan_report)

    def plugin_match(self, segment_callstack_lower: list[str], crashlog_plugins_lower: set[str],
                     autoscan_report: list[str]) -> None:
        """
        Matches plugins in the given segment callstack against the crashlog plugins and appends the result
        to the autoscan report. The method identifies plugins in the crash log that correspond to the given
        plugin list, filtering based on relevance and ignoring specific plugins as configured in the class.

        Args:
            segment_callstack_lower (list[str]): Lowercase representation of the segment callstack,
                containing lines to be analyzed for potential plugin matches.
            crashlog_plugins_lower (set[str]): Set of lowercase plugin names extracted from the crash log,
                used as a reference for matching against the callstack lines.
            autoscan_report (list[str]): List where the method will append strings documenting plugin matches
                or the absence of matches. This is modified in-place.
        """
        # Pre-filter call stack lines that won't match
        relevant_lines = [line for line in segment_callstack_lower if "modified by:" not in line]

        # Use Counter directly instead of list + Counter conversion
        plugins_matches: Counter[str] = Counter()

        # Optimize the matching algorithm
        for line in relevant_lines:
            for plugin in crashlog_plugins_lower:
                # Skip plugins that are in the ignore list
                if plugin in self.lower_plugins_ignore:
                    continue

                if plugin in line:
                    plugins_matches[plugin] += 1

        if plugins_matches:
            append_or_extend("The following PLUGINS were found in the CRASH STACK:\n", autoscan_report)
            # Sort by count (descending) then by name for consistent output
            for plugin, count in sorted(plugins_matches.items(), key=lambda x: (-x[1], x[0])):
                append_or_extend(f"- {plugin} | {count}\n", autoscan_report)
            append_or_extend((
                "\n[Last number counts how many times each Plugin Suspect shows up in the crash log.]\n",
                f"These Plugins were caught by {self.yamldata.crashgen_name} and some of them might be responsible for this crash.\n",
                "You can try disabling these plugins and check if the game still crashes, though this method can be unreliable.\n\n",
            ), autoscan_report)
        else:
            append_or_extend("* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n", autoscan_report)

    @staticmethod
    def scan_log_gpu(segment_system: list[str]) -> tuple[str, Literal["nvidia", "amd"] | None]:
        """
        Scans the log to determine the GPU information and its rival.

        This method analyzes a list of system log segments to identify the primary
        graphics processing unit (GPU) being used. It also determines the rival GPU
        manufacturer based on the GPU identified. If the GPU information cannot be
        determined, the method returns "Unknown" and the rival GPU is set to None.

        Args:
            segment_system (list[str]): A list of log segments containing system
                information. Each log segment is expected to contain details about
                hardware components including GPUs.

        Returns:
            tuple[str, Literal["nvidia", "amd"] | None]: A tuple containing the GPU
                name and the rival GPU manufacturer. The first element is a string
                that represents the GPU name ("AMD", "Nvidia", or "Unknown"). The
                second element is a Literal that specifies the rival GPU
                manufacturer ("nvidia", "amd"), or None if no rival is identified.
        """
        GPU: str
        gpu_rival: Literal["nvidia", "amd"] | None
        if any("GPU #1" in elem and "AMD" in elem for elem in segment_system):
            GPU = "AMD"
            gpu_rival = "nvidia"
        elif any("GPU #1" in elem and "Nvidia" in elem for elem in segment_system):
            GPU = "Nvidia"
            gpu_rival = "amd"
        else:
            GPU = "Unknown"
            gpu_rival = None
        return GPU, gpu_rival

    def scan_named_records(self, segment_callstack: list[str], records_matches: list[str],
                           autoscan_report: list[str]) -> None:
        """
        Scans a given call stack segment to identify and record named records, and appends
        relevant information about the findings to the autoscan report.

        This method processes the `segment_callstack` to identify specific patterns for "named
        records" while respecting the specified ignore list. If any matches are found, it
        counts occurrences, formats findings, and appends suitable annotations or information
        to the autoscan report, summarizing potential crash-related data for further analysis.

        Args:
            segment_callstack (list[str]): List of strings representing the call stack segment
                to be analyzed for named records.
            records_matches (list[str]): List to store the matched named records identified during
                the scan.
            autoscan_report (list[str]): List to which the analysis summary or findings about
                named records will be appended.

        """
        for line in segment_callstack:
            lower_line = line.lower()

            if any(item in lower_line for item in self.lower_records) and all(
                    record not in lower_line for record in self.lower_ignore
            ):
                if "[RSP+" in line:
                    records_matches.append(line[30:].strip())
                else:
                    records_matches.append(line.strip())
        if records_matches:
            records_found = dict(Counter(sorted(records_matches)))
            for record, count in records_found.items():
                append_or_extend(f"- {record} | {count}\n", autoscan_report)

            append_or_extend((
                "\n[Last number counts how many times each Named Record shows up in the crash log.]\n",
                f"These records were caught by {self.yamldata.crashgen_name} and some of them might be related to this crash.\n",
                "Named records should give extra info on involved game objects, record types or mod files.\n\n",
            ), autoscan_report)
        else:
            append_or_extend("* COULDN'T FIND ANY NAMED RECORDS *\n\n", autoscan_report)

    @staticmethod
    def extract_module_names(module_texts):
        if not module_texts:
            return set()

        # Pattern matches module name potentially followed by version
        pattern = re.compile(r"(.*?\.dll)\s*v?.*", re.IGNORECASE)

        result = set()
        for text in module_texts:
            text = text.strip()
            match = pattern.match(text)
            if match:
                result.add(match.group(1))
            else:
                result.add(text)

        return result


# ================================================
# CRASH LOG SCAN START
# ================================================
def crashlogs_scan() -> None:
    """
    Scans crash log files to generate reports, identify issues, and provide insights into the cause of crashes. This
    function utilizes crash log data, plugin configurations, and system segments to correlate crash events with probable
    causes and generate detailed reports that include warnings, errors, and potential solutions.

    The function performs a sequence of actions:
    1) Collects and processes crash log segments, such as system information, stack traces, and plugin lists.
    2) Analyzes crash-generation details, checks for specific errors, and identifies potential crash suspects.
    3) Evaluates system and game configurations, scans for missing files or conflicting plugins, and suggests fixes.
    4) Produces an autoscan report summarizing the findings, which can assist in troubleshooting and resolving crash issues.

    Raises:
        RuntimeError: If a critical error occurs during crash log scanning or data processing.
    """
    scanner = ClassicScanLogs()
    yamldata = scanner.yamldata

    for crashlog_file in scanner.crashlog_list:
        autoscan_report: list[str] = []
        trigger_plugin_limit = trigger_limit_check_disabled = trigger_plugins_loaded = trigger_scan_failed = False
        crash_data = scanner.crashlogs.read_log(crashlog_file.name)

        append_or_extend((
            f"{crashlog_file.name} -> AUTOSCAN REPORT GENERATED BY {yamldata.classic_version} \n",
            "# FOR BEST VIEWING EXPERIENCE OPEN THIS FILE IN NOTEPAD++ OR SIMILAR # \n",
            "# PLEASE READ EVERYTHING CAREFULLY AND BEWARE OF FALSE POSITIVES # \n",
            "====================================================\n",
        ), autoscan_report)

        # ================================================
        # 1) GENERATE REQUIRED SEGMENTS FROM THE CRASH LOG
        # ================================================
        (
            crashlog_gameversion,
            crashlog_crashgen,
            crashlog_mainerror,
            (
                segment_crashgen,
                segment_system,
                segment_callstack,
                segment_allmodules,
                segment_xsemodules,
                segment_plugins,
            ),
        ) = scanner.find_segments(crash_data, yamldata.crashgen_name)
        segment_callstack_intact = "".join(segment_callstack)

        game_version = crashgen_version_gen(crashlog_gameversion)

        # SOME IMPORTANT DLLs HAVE A VERSION, REMOVE IT

        xsemodules = ClassicScanLogs.extract_module_names(segment_xsemodules)

        crashgen: dict[str, bool | int | str] = {}
        if segment_crashgen:
            for elem in segment_crashgen:
                if ":" in elem:
                    key, value = elem.split(":", 1)
                    crashgen[key] = True if value == " true" else False if value == " false" else int(
                        value) if value.isdecimal() else value.strip()

        if not segment_plugins:
            scanner.stats_crashlog_incomplete += 1
        if len(crash_data) < 20:
            scanner.stats_crashlog_scanned -= 1
            scanner.stats_crashlog_failed += 1
            trigger_scan_failed = True

        # ================== MAIN ERROR ==================
        # =============== CRASHGEN VERSION ===============
        version_current = crashgen_version_gen(crashlog_crashgen)
        version_latest = crashgen_version_gen(yamldata.crashgen_latest_og)
        version_latest_vr = crashgen_version_gen(yamldata.crashgen_latest_vr)
        append_or_extend((
            f"\nMain Error: {crashlog_mainerror}\n",
            f"Detected {yamldata.crashgen_name} Version: {crashlog_crashgen} \n",
            (
                f"* You have the latest version of {yamldata.crashgen_name}! *\n\n"
                if version_current >= version_latest or version_current >= version_latest_vr
                else f"{yamldata.warn_outdated} \n"
            ),
        ), autoscan_report)

        # ======= REQUIRED LISTS, DICTS AND CHECKS =======

        crashlog_plugins: dict[str, str] = {}

        esm_name = f"{CMain.gamevars["game"]}.esm"
        if any(esm_name in elem for elem in segment_plugins):
            trigger_plugins_loaded = True
        else:
            scanner.stats_crashlog_incomplete += 1

        # ================================================
        # 2) CHECK EACH SEGMENT AND CREATE REQUIRED VALUES
        # ================================================

        # CHECK GPU TYPE FOR CRASH LOG
        crashlog_gpu, crashlog_gpu_rival = scanner.scan_log_gpu(segment_system)

        # IF LOADORDER FILE EXISTS, USE ITS PLUGINS
        loadorder_path = Path("loadorder.txt")
        if loadorder_path.exists():
            loadorder_plugins, trigger_plugins_loaded = scanner.loadorder_scan_loadorder_txt(autoscan_report)
            crashlog_plugins = crashlog_plugins | loadorder_plugins

        else:  # OTHERWISE, USE PLUGINS FROM CRASH LOG
            log_plugins, trigger_plugin_limit, trigger_limit_check_disabled = scanner.loadorder_scan_log(
                segment_plugins, game_version, version_current)
            crashlog_plugins = crashlog_plugins | log_plugins

        crashlog_plugins.update(
            {elem: "DLL" for elem in xsemodules if all(elem not in item for item in crashlog_plugins)})

        for elem in segment_allmodules:
            # SOME IMPORTANT DLLs ONLY APPEAR UNDER ALL MODULES
            if "vulkan" in elem.lower():
                elem_parts = elem.strip().split(" ", 1)
                crashlog_plugins.update({elem_parts[0]: "DLL"})

        crashlog_plugins_lower = {plugin.lower() for plugin in crashlog_plugins}

        # CHECK IF THERE ARE ANY PLUGINS IN THE IGNORE YAML
        if scanner.ignore_plugins_list:
            for signal in scanner.ignore_plugins_list:
                if signal in crashlog_plugins_lower:
                    del crashlog_plugins[signal]

        append_or_extend((
            "====================================================\n",
            "CHECKING IF LOG MATCHES ANY KNOWN CRASH SUSPECTS...\n",
            "====================================================\n",
        ), autoscan_report)

        crashlog_mainerror_lower = crashlog_mainerror.lower()
        if ".dll" in crashlog_mainerror_lower and "tbbmalloc" not in crashlog_mainerror_lower:
            append_or_extend((
                "* NOTICE : MAIN ERROR REPORTS THAT A DLL FILE WAS INVOLVED IN THIS CRASH! * \n",
                "If that dll file belongs to a mod, that mod is a prime suspect for the crash. \n-----\n",
            ), autoscan_report)
        max_warn_length = 30
        trigger_suspect_found = any(
            (scanner.suspect_scan_mainerror(autoscan_report, crashlog_mainerror, max_warn_length),
             scanner.suspect_scan_stack(crashlog_mainerror, segment_callstack_intact, autoscan_report,
                                        max_warn_length)))

        if trigger_suspect_found:
            append_or_extend((
                "* FOR DETAILED DESCRIPTIONS AND POSSIBLE SOLUTIONS TO ANY ABOVE DETECTED CRASH SUSPECTS *\n",
                "* SEE: https://docs.google.com/document/d/17FzeIMJ256xE85XdjoPvv_Zi3C5uHeSTQh6wOZugs4c *\n\n",
            ), autoscan_report)
        else:
            append_or_extend((
                "# FOUND NO CRASH ERRORS / SUSPECTS THAT MATCH THE CURRENT DATABASE #\n",
                "Check below for mods that can cause frequent crashes and other problems.\n\n",
            ), autoscan_report)

        append_or_extend((
            "====================================================\n",
            "CHECKING IF NECESSARY FILES/SETTINGS ARE CORRECT...\n",
            "====================================================\n",
        ), autoscan_report)

        has_x_cell: bool = (
                    "x-cell-fo4.dll" in xsemodules or "x-cell-og.dll" in xsemodules or "x-cell-ng2.dll" in xsemodules)
        has_baka_scrapheap: bool = "bakascrapheap.dll" in xsemodules

        if scanner.fcx_mode:
            append_or_extend((
                "* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION * \n",
                "[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ] \n\n",
            ), autoscan_report)
            scanner.fcx_mode_check()
            append_or_extend(scanner.main_files_check, autoscan_report)
            append_or_extend(scanner.game_files_check, autoscan_report)

        else:
            append_or_extend((
                "* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES * \n",
                "[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ] \n\n",
            ), autoscan_report)
            if has_x_cell:
                yamldata.crashgen_ignore.update(
                    ("MemoryManager", "HavokMemorySystem", "ScaleformAllocator", "SmallBlockAllocator"))
            elif has_baka_scrapheap:
                # To prevent two messages mentioning this parameter.
                yamldata.crashgen_ignore.add("MemoryManager")

            if crashgen:
                for setting_name, setting_value in crashgen.items():
                    if setting_value is False and setting_name not in yamldata.crashgen_ignore:
                        append_or_extend(
                            f"* NOTICE : {setting_name} is disabled in your {yamldata.crashgen_name} settings, is this intentional? * \n-----\n",
                            autoscan_report
                        )
                scanner.scan_buffout_achievements_setting(autoscan_report, xsemodules, crashgen)
                scanner.scan_buffout_memorymanagement_settings(autoscan_report, crashgen, has_x_cell,
                                                               has_baka_scrapheap)
                if crashgen_version_gen(scanner.yamldata.crashgen_latest_og) <= crashgen_version_gen(
                        crashlog_crashgen) >= Version("1.27.0"):
                    scanner.scan_archivelimit_setting(autoscan_report, crashgen)
                scanner.scan_buffout_looksmenu_setting(crashgen, autoscan_report, xsemodules)

        append_or_extend(scanner.main_files_check, autoscan_report)
        if scanner.game_files_check:
            append_or_extend(scanner.game_files_check, autoscan_report)

        append_or_extend((
            "====================================================\n",
            "CHECKING FOR MODS THAT CAN CAUSE FREQUENT CRASHES...\n",
            "====================================================\n",
        ), autoscan_report)

        if trigger_plugins_loaded:
            if detect_mods_single(yamldata.game_mods_freq, crashlog_plugins, autoscan_report):
                append_or_extend((
                    "# [!] CAUTION : ANY ABOVE DETECTED MODS HAVE A MUCH HIGHER CHANCE TO CRASH YOUR GAME! #\n",
                    "* YOU CAN DISABLE ANY / ALL OF THEM TEMPORARILY TO CONFIRM THEY CAUSED THIS CRASH. * \n\n",
                ), autoscan_report)
            else:
                append_or_extend((
                    "# FOUND NO PROBLEMATIC MODS THAT MATCH THE CURRENT DATABASE FOR THIS CRASH LOG #\n",
                    "THAT DOESN'T MEAN THERE AREN'T ANY! YOU SHOULD RUN PLUGIN CHECKER IN WRYE BASH \n",
                    "Plugin Checker Instructions: https://www.nexusmods.com/fallout4/articles/4141 \n\n",
                ), autoscan_report)
        else:
            append_or_extend(yamldata.warn_noplugins, autoscan_report)

        append_or_extend((
            "====================================================\n",
            "CHECKING FOR MODS THAT CONFLICT WITH OTHER MODS...\n",
            "====================================================\n",
        ), autoscan_report)

        if trigger_plugins_loaded:
            if detect_mods_double(yamldata.game_mods_conf, crashlog_plugins, autoscan_report):
                append_or_extend((
                    "# [!] CAUTION : FOUND MODS THAT ARE INCOMPATIBLE OR CONFLICT WITH YOUR OTHER MODS # \n",
                    "* YOU SHOULD CHOOSE WHICH MOD TO KEEP AND DISABLE OR COMPLETELY REMOVE THE OTHER MOD * \n\n",
                ), autoscan_report)
            else:
                append_or_extend("# FOUND NO MODS THAT ARE INCOMPATIBLE OR CONFLICT WITH YOUR OTHER MODS # \n\n",
                                 autoscan_report)
        else:
            append_or_extend(yamldata.warn_noplugins, autoscan_report)

        append_or_extend((
            "====================================================\n",
            "CHECKING FOR MODS WITH SOLUTIONS & COMMUNITY PATCHES\n",
            "====================================================\n",
        ), autoscan_report)

        if trigger_plugins_loaded:
            if detect_mods_single(yamldata.game_mods_solu, crashlog_plugins, autoscan_report):
                append_or_extend((
                    "# [!] CAUTION : FOUND PROBLEMATIC MODS WITH SOLUTIONS AND COMMUNITY PATCHES # \n",
                    "[Due to limitations, CLASSIC will show warnings for some mods even if fixes or patches are already installed.] \n",
                    "[To hide these warnings, you can add their plugin names to the CLASSIC Ignore.yaml file. ONE PLUGIN PER LINE.] \n\n",
                ), autoscan_report)
            else:
                append_or_extend("# FOUND NO PROBLEMATIC MODS WITH AVAILABLE SOLUTIONS AND COMMUNITY PATCHES # \n\n",
                                 autoscan_report)
        else:
            append_or_extend(yamldata.warn_noplugins, autoscan_report)

        if CMain.gamevars["game"] == "Fallout4":
            append_or_extend((
                "====================================================\n",
                "CHECKING FOR MODS PATCHED THROUGH OPC INSTALLER...\n",
                "====================================================\n",
            ), autoscan_report)

            if trigger_plugins_loaded:
                if detect_mods_single(yamldata.game_mods_opc2, crashlog_plugins, autoscan_report):
                    append_or_extend((
                        "\n* FOR PATCH REPOSITORY THAT PREVENTS CRASHES AND FIXES PROBLEMS IN THESE AND OTHER MODS,* \n",
                        "* VISIT OPTIMIZATION PATCHES COLLECTION: https://www.nexusmods.com/fallout4/mods/54872 * \n\n",
                    ), autoscan_report)
                else:
                    append_or_extend(
                        "# FOUND NO PROBLEMATIC MODS THAT ARE ALREADY PATCHED THROUGH THE OPC INSTALLER # \n\n",
                        autoscan_report)
            else:
                append_or_extend(yamldata.warn_noplugins, autoscan_report)

        append_or_extend((
            "====================================================\n",
            "CHECKING IF IMPORTANT PATCHES & FIXES ARE INSTALLED\n",
            "====================================================\n",
        ), autoscan_report)

        if trigger_plugins_loaded:
            if any("londonworldspace" in plugin.lower() for plugin in crashlog_plugins):
                detect_mods_important(yamldata.game_mods_core_folon, crashlog_plugins, autoscan_report,
                                      crashlog_gpu_rival)
            else:
                detect_mods_important(yamldata.game_mods_core, crashlog_plugins, autoscan_report, crashlog_gpu_rival)
        else:
            append_or_extend(yamldata.warn_noplugins, autoscan_report)

        append_or_extend((
            "====================================================\n",
            "SCANNING THE LOG FOR SPECIFIC (POSSIBLE) SUSPECTS...\n",
            "====================================================\n",
        ), autoscan_report)

        if trigger_plugin_limit and not trigger_limit_check_disabled:
            warn_plugin_limit = CMain.yaml_settings(str, CMain.YAML.Main, "Mods_Warn.Mods_Plugin_Limit") or ""
            append_or_extend(warn_plugin_limit, autoscan_report)

        if trigger_limit_check_disabled:
            append_or_extend(
                ("❌ WARNING : Crash logs for the current game version do not report plugin indexes correctly! \n",
                 "The plugin limit check will be disabled for this scan. \n\n"), autoscan_report)

        # ================================================

        append_or_extend("# LIST OF (POSSIBLE) PLUGIN SUSPECTS #\n", autoscan_report)
        segment_callstack_lower = [line.lower() for line in segment_callstack]

        scanner.plugin_match(segment_callstack_lower, crashlog_plugins_lower, autoscan_report)

        # ================================================
        append_or_extend("# LIST OF (POSSIBLE) FORM ID SUSPECTS #\n", autoscan_report)
        formids_matches = [line.replace("0x", "").strip() for line in segment_callstack if
                           "0xFF" not in line and "id:" in line.lower()]
        scanner.formid_match(formids_matches, crashlog_plugins, autoscan_report)

        # ================================================

        append_or_extend("# LIST OF DETECTED (NAMED) RECORDS #\n", autoscan_report)
        records_matches: list[str] = []
        scanner.scan_named_records(segment_callstack, records_matches, autoscan_report)

        # ============== AUTOSCAN REPORT END ==============
        if CMain.gamevars["game"] == "Fallout4":
            append_or_extend(yamldata.autoscan_text, autoscan_report)
        append_or_extend(f"{yamldata.classic_version} | {yamldata.classic_version_date} | END OF AUTOSCAN \n",
                         autoscan_report)

        # CHECK IF SCAN FAILED
        scanner.stats_crashlog_scanned += 1
        if trigger_scan_failed:
            append_or_extend(crashlog_file.name, scanner.scan_failed_list)

        # HIDE PERSONAL USERNAME
        user_name = scanner.user_folder.name
        user_path_1 = f"{scanner.user_folder.parent}\\{user_name}"
        user_path_2 = f"{scanner.user_folder.parent}/{user_name}"
        for line in autoscan_report:
            if user_name in line:
                line.replace(user_path_1, "******").replace(user_path_2, "******")

        # WRITE AUTOSCAN REPORT TO FILE
        autoscan_path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
        with autoscan_path.open("w", encoding="utf-8", errors="ignore") as autoscan_file:
            CMain.logger.debug(f"- - -> RUNNING CRASH LOG FILE SCAN >>> SCANNED {crashlog_file.name}")
            autoscan_output = "".join(autoscan_report)
            autoscan_file.write(autoscan_output)

        if trigger_scan_failed and scanner.move_unsolved_logs:
            backup_path = Path("CLASSIC Backup/Unsolved Logs")
            backup_path.mkdir(parents=True, exist_ok=True)
            autoscan_filepath = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
            crash_move = backup_path / crashlog_file.name
            scan_move = backup_path / autoscan_file.name

            if crashlog_file.exists():
                shutil.copy2(crashlog_file, crash_move)
            if autoscan_filepath.exists():
                shutil.copy2(autoscan_filepath, scan_move)

    # CHECK FOR FAILED OR INVALID CRASH LOGS
    scan_invalid_list = list(Path.cwd().glob("crash-*.txt"))
    if scanner.scan_failed_list or scan_invalid_list:
        print("❌ NOTICE : CLASSIC WAS UNABLE TO PROPERLY SCAN THE FOLLOWING LOG(S):")
        print("\n".join(scanner.scan_failed_list))
        if scan_invalid_list:
            for file in scan_invalid_list:
                print(f"{file}\n")
        print("===============================================================================")
        print("Most common reason for this are logs being incomplete or in the wrong format.")
        print("Make sure that your crash log files have the .log file format, NOT .txt! \n")

    # ================================================
    # CRASH LOG SCAN COMPLETE / TERMINAL OUTPUT
    # ================================================
    scanner.close_database()
    CMain.logger.info("- - - COMPLETED CRASH LOG FILE SCAN >>> ALL AVAILABLE LOGS SCANNED")
    print("SCAN COMPLETE! (IT MIGHT TAKE SEVERAL SECONDS FOR SCAN RESULTS TO APPEAR)")
    print("SCAN RESULTS ARE AVAILABLE IN FILES NAMED crash-date-and-time-AUTOSCAN.md \n")
    print(f"{random.choice(yamldata.classic_game_hints)}\n-----")
    print(f"Scanned all available logs in {str(time.perf_counter() - 0.5 - scanner.scan_start_time)[:5]} seconds.")
    print(f"Number of Scanned Logs (No Autoscan Errors): {scanner.stats_crashlog_scanned}")
    print(f"Number of Incomplete Logs (No Plugins List): {scanner.stats_crashlog_incomplete}")
    print(f"Number of Failed Logs (Autoscan Can't Scan): {scanner.stats_crashlog_failed}\n-----")
    if CMain.gamevars["game"] == "Fallout4":
        print(yamldata.autoscan_text)
    if scanner.stats_crashlog_scanned == 0 and scanner.stats_crashlog_incomplete == 0:
        print("\n❌ CLASSIC found no crash logs to scan or the scan failed.")
        print("    There are no statistics to show (at this time).\n")


if __name__ == "__main__":
    CMain.initialize()

    # noinspection PyUnresolvedReferences
    from tap import Tap


    class Args(Tap):
        """Command-line arguments for CLASSIC's Command Line Interface"""

        fcx_mode: bool = False
        """Enable FCX mode"""

        show_fid_values: bool = False
        """Show FormID values"""

        stat_logging: bool = False
        """Enable statistical logging"""

        move_unsolved: bool = False
        """Move unsolved logs"""

        ini_path: Path | None = None
        """Path to the INI file"""

        scan_path: Path | None = None
        """Path to the scan directory"""

        mods_folder_path: Path | None = None
        """Path to the mods folder"""

        simplify_logs: bool = False
        """Simplify the logs"""


    args = Args().parse_args()

    if isinstance(args.fcx_mode, bool) and args.fcx_mode != CMain.classic_settings(bool, "FCX Mode"):
        CMain.yaml_settings(bool, CMain.YAML.Settings, "CLASSIC_Settings.FCX Mode", args.fcx_mode)

    if isinstance(args.show_fid_values, bool) and args.show_fid_values != CMain.classic_settings(bool,
                                                                                                 "Show FormID Values"):
        CMain.yaml_settings(bool, CMain.YAML.Settings, "Show FormID Values", args.show_fid_values)

    if isinstance(args.move_unsolved, bool) and args.move_unsolved != CMain.classic_settings(bool,
                                                                                             "Move Unsolved Logs"):
        CMain.yaml_settings(bool, CMain.YAML.Settings, "CLASSIC_Settings.Move Unsolved", args.move_unsolved)

    if isinstance(args.ini_path, Path) and args.ini_path.resolve().is_dir() and str(
            args.ini_path) != CMain.classic_settings(str, "INI Folder Path"):
        CMain.yaml_settings(str, CMain.YAML.Settings, "CLASSIC_Settings.INI Folder Path", str(args.ini_path.resolve()))

    if isinstance(args.scan_path, Path) and args.scan_path.resolve().is_dir() and str(
            args.scan_path) != CMain.classic_settings(str, "SCAN Custom Path"):
        CMain.yaml_settings(str, CMain.YAML.Settings, "CLASSIC_Settings.SCAN Custom Path",
                            str(args.scan_path.resolve()))

    if (
            isinstance(args.mods_folder_path, Path)
            and args.mods_folder_path.resolve().is_dir()
            and str(args.mods_folder_path) != CMain.classic_settings(str, "MODS Folder Path")
    ):
        CMain.yaml_settings(str, CMain.YAML.Settings, "CLASSIC_Settings.MODS Folder Path",
                            str(args.mods_folder_path.resolve()))

    if isinstance(args.simplify_logs, bool) and args.simplify_logs != CMain.classic_settings(bool, "Simplify Logs"):
        CMain.yaml_settings(bool, CMain.YAML.Settings, "CLASSIC_Settings.Simplify Logs", args.simplify_logs)

    crashlogs_scan()
    os.system("pause")
