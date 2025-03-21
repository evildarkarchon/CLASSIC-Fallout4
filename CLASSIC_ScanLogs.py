import os
import random
import shutil
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import aiohttp
import regex as re
import requests
from packaging.version import Version

import CLASSIC_Main as CMain
import CLASSIC_ScanGame as CGame

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
    Append or extend the specified list with the given value.

    Args:
        value (str | int | float | list | tuple | set): The value to append or extend.
        destination (list[str]): The list to update.
    """
    if isinstance(value, list | tuple | set):
        destination.extend(value)
    else:
        destination.append(str(value))


def pastebin_fetch(url: str) -> None:
    """
    Fetches the content from a given Pastebin URL and saves it to a local file.

    If the URL does not point to the raw Pastebin content, it modifies the URL to point to the raw content.
    The fetched content is saved in the "Crash Logs/Pastebin" directory with a filename derived from the Pastebin ID.

    Args:
        url (str): The URL of the Pastebin content to fetch.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request to fetch the content fails.
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
    Asynchronously fetches the content from a given Pastebin URL and saves it to a local file.

    If the URL does not point to the raw Pastebin content, it modifies the URL to point to the raw content.
    The fetched content is saved in the "Crash Logs/Pastebin" directory with a filename derived from the Pastebin ID.

    Args:
        url (str): The URL of the Pastebin content to fetch.

    Raises:
        aiohttp.ClientError: If the HTTP request to fetch the content fails.
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
    Retrieve an entry from the database based on the given form ID and plugin.
    This function first checks a cache for the entry. If the entry is not found
    in the cache, it searches through a list of database paths. If a database
    file is found, it queries the database for the entry. If the entry is found,
    it is added to the cache and returned. If the entry is not found in any
    database, the function returns None.
    Args:
        formid (str): The form ID to search for.
        plugin (str): The plugin name to search for.
    Returns:
        str | None: The entry if found, otherwise None.
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
    Get paths of all available crash logs.
    This function scans the current working directory and specified custom directories
    for crash log files, moves or copies them to a designated "Crash Logs" folder, and
    returns a list of paths to these crash log files.
    Returns:
        list[Path]: A list of Path objects representing the paths to the crash log files.
    """
    CMain.logger.debug("- - - INITIATED CRASH LOG FILE LIST GENERATION")
    CLASSIC_folder = Path.cwd()
    CLASSIC_logs = CLASSIC_folder / "Crash Logs"
    CLASSIC_pastebin = CLASSIC_logs / "Pastebin"
    CUSTOM_folder_setting = CMain.classic_settings(str, "SCAN Custom Path")
    XSE_folder_setting = CMain.yaml_settings(str, CMain.YAML.Game_Local, "Game_Info.Docs_Folder_XSE")

    CUSTOM_folder = Path(CUSTOM_folder_setting) if isinstance(CUSTOM_folder_setting, str) else None
    XSE_folder = Path(XSE_folder_setting) if isinstance(XSE_folder_setting, str) else None

    if not CLASSIC_logs.is_dir():
        CLASSIC_logs.mkdir(parents=True, exist_ok=True)
    if not CLASSIC_pastebin.is_dir():
        CLASSIC_pastebin.mkdir(parents=True, exist_ok=True)
    for file in CLASSIC_folder.glob("crash-*.log"):
        destination_file = CLASSIC_logs / file.name
        if not destination_file.is_file():
            file.rename(destination_file)
    for file in CLASSIC_folder.glob("crash-*-AUTOSCAN.md"):
        destination_file = CLASSIC_logs / file.name
        if not destination_file.is_file():
            file.rename(destination_file)
    if XSE_folder and XSE_folder.is_dir():
        for crash_file in XSE_folder.glob("crash-*.log"):
            destination_file = CLASSIC_logs / crash_file.name
            if not destination_file.is_file():
                shutil.copy2(crash_file, destination_file)

    crash_files = list(CLASSIC_logs.rglob("crash-*.log"))
    if CUSTOM_folder and CUSTOM_folder.is_dir():
        crash_files.extend(CUSTOM_folder.glob("crash-*.log"))

    return crash_files


def crashlogs_reformat(crashlog_list: list[Path], remove_list: list[str]) -> None:
    """
    Reformat plugin lists in crash logs to ensure consistency between old and new CRASHGEN formats.
    Args:
        crashlog_list (list[Path]): A list of file paths to the crash logs that need reformatting.
        remove_list (list[str]): A list of strings that, if found in a line, will cause that line to be removed from the crash log.
    Returns:
        None
    The function performs the following operations:
        - Logs the initiation of the crash log file reformatting process.
        - Reads each crash log file line by line.
        - If "Simplify Logs" setting is enabled, removes lines containing any string from the remove_list.
        - Replaces spaces inside load order brackets with zeros to maintain consistency between different versions of Buffout 4.
        - Writes the modified crash log data back to the file.
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
    Detects mods from a YAML dictionary within a crash log plugins dictionary and updates the autoscan report.
    Args:
        yaml_dict (dict[str, str]): A dictionary where keys are mod names and values are warnings associated with the mods.
        crashlog_plugins (dict[str, str]): A dictionary where keys are plugin names and values are plugin identifiers.
        autoscan_report (list[str]): A list to be updated with found mods and their warnings.
    Returns:
        bool: True if any mod is found in the crash log plugins, False otherwise.
    Raises:
        ValueError: If a mod is found in the crash log plugins but has no associated warning in the YAML dictionary.
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
    Detects if any pair of mods (split by " | ") from the YAML dictionary are present in the crashlog plugins.
    Args:
        yaml_dict (dict[str, str]): A dictionary where keys are mod names and values are warning messages (using " | " to indicate key and value).
        crashlog_plugins (dict[str, str]): A dictionary of plugins from the crashlog where keys are plugin names.
        autoscan_report (list[str]): A list to append warning messages if a pair of mods is detected.
    Returns:
        bool: True if any pair of mods is detected in the crashlog plugins, False otherwise.
    Raises:
        ValueError: If a detected pair of mods does not have an associated warning message in the YAML dictionary.
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
    Detects important Core and GPU-specific mods from the provided YAML dictionary and updates the autoscan report.

    Args:
        yaml_dict (dict[str, str]): A dictionary containing mod names and their corresponding warnings.
        crashlog_plugins (dict[str, str]): A dictionary containing plugin names found in the crash log.
        autoscan_report (list[str]): A list to append the scan results.
        gpu_rival (Literal["nvidia", "amd"] | None): The GPU brand to check for specific warnings, can be "nvidia", "amd", or None.

    Returns:
        None: This function does not return any value. It updates the autoscan_report list in place.
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
            # noinspection PyTypeChecker
            if gpu_rival and gpu_rival in mod_warn.lower():
                autoscan_report.extend((
                    f"❓ {mod_split[1]} is installed, BUT IT SEEMS YOU DON'T HAVE AN {gpu_rival.upper()} GPU?\n",
                    "IF THIS IS CORRECT, COMPLETELY UNINSTALL THIS MOD TO AVOID ANY PROBLEMS! \n\n",
                ))
            else:
                autoscan_report.append(f"✔️ {mod_split[1]} is installed!\n\n")
        elif (gpu_rival and mod_warn) and gpu_rival not in mod_warn.lower():
            autoscan_report.extend((f"❌ {mod_split[1]} is not installed!\n", mod_warn, "\n"))


def crashgen_version_gen(input_string: str) -> Version:
    """
    Extracts and returns a version number from the given input string.

    The function looks for a part of the input string that starts with 'v'
    followed by version numbers (e.g., 'v1.2.3'). If such a part is found,
    it removes the 'v' and returns the remaining string as a Version object.
    If no version string is found, it returns a default Version object with
    the version "0.0.0".

    Args:
        input_string (str): The input string containing the version information.

    Returns:
        Version: A Version object representing the extracted version number.
    """
    input_string = input_string.strip()
    parts = input_string.split()
    version_str = ""
    for part in parts:
        if part.startswith("v") and len(part) > 1:
            version_str = part[1:]  # Remove the 'v'
    if version_str:
        return Version(version_str)
    return CMain.NULL_VERSION


class SQLiteReader:
    # noinspection SpellCheckingInspection
    def __init__(self, logfiles: list[Path]) -> None:
        """
        Initializes the CLASSIC_ScanLogs object.

        Args:
            logfiles (list[Path]): A list of Path objects representing the log files to be processed.

        Initializes an in-memory SQLite database and creates a table named 'crashlogs' with columns for
        log name and log data. Also creates an index on the 'logname' column for faster lookups. Inserts
        the provided log files into the 'crashlogs' table.

        Raises:
            sqlite3.Error: If an error occurs while interacting with the SQLite database.
        """
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE crashlogs (logname TEXT UNIQUE, logdata BLOB)")
        self.db.execute("CREATE INDEX idx_logname ON crashlogs (logname)")
        self.db.executemany("INSERT INTO crashlogs VALUES (?, ?)",
                            ((file.name, file.read_bytes()) for file in logfiles))

    def read_log(self, logname: str) -> list[str]:
        """
        Reads the log data from the database for the given log name.

        Args:
            logname (str): The name of the log to read.

        Returns:
            list[str]: A list of strings, each representing a line of the log data.
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
    """
    A class to represent and manage the scanning logs information for the CLASSIC Fallout 4 game.
    Attributes:
        classic_game_hints (list[str]): Hints related to the classic game.
        classic_records_list (list[str]): List of classic records.
        classic_version (str): Version of the classic game.
        classic_version_date (str): Date of the classic game version.
        crashgen_name (str): Name of the crash generator.
        crashgen_latest_og (str): Latest version of the original crash generator.
        crashgen_latest_vr (str): Latest version of the VR crash generator.
        crashgen_ignore (set): Set of items to ignore for the crash generator.
        warn_noplugins (str): Warning message for no plugins.
        warn_outdated (str): Warning message for outdated plugins.
        xse_acronym (str): Acronym for XSE.
        game_ignore_plugins (list[str]): List of plugins to ignore.
        game_ignore_records (list[str]): List of records to ignore.
        suspects_error_list (dict[str, str]): Dictionary of suspect errors.
        suspects_stack_list (dict[str, list[str]]): Dictionary of suspect stacks.
        autoscan_text (str): Text for auto scan.
        ignore_list (list[str]): List of items to ignore.
        game_mods_conf (dict[str, str]): Configuration of game mods.
        game_mods_core (dict[str, str]): Core game mods.
        game_mods_core_folon (dict[str, str]): Core FOLON game mods.
        game_mods_freq (dict[str, str]): Frequently used game mods.
        game_mods_opc2 (dict[str, str]): OPC2 game mods.
        game_mods_solu (dict[str, str]): SOLU game mods.
        game_version (Version): Version of the game.
        game_version_new (Version): New version of the game.
        game_version_vr (Version): VR version of the game.
    Methods:
        __post_init__(): Initializes the class attributes with settings from CMain.
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
    game_version: Version = field(default=CMain.NULL_VERSION, init=False)
    game_version_new: Version = field(default=CMain.NULL_VERSION, init=False)
    game_version_vr: Version = field(default=CMain.NULL_VERSION, init=False)

    def __post_init__(self) -> None:
        """
        Post-initialization method for setting up various game-related configurations and settings.

        Raises:
            TypeError: If CMain.yaml_cache is None, indicating that CMain is not initialized.

        Attributes:
            classic_game_hints (list[str]): List of game hints.
            classic_records_list (list[str]): List of log records to catch.
            classic_version (str): Version of the CLASSIC.
            classic_version_date (str): Date of the CLASSIC version.
            crashgen_name (str): Name of the CRASHGEN log.
            crashgen_latest_og (str): Latest version of CRASHGEN for the original game.
            crashgen_latest_vr (str): Latest version of CRASHGEN for the VR game.
            crashgen_ignore (set[str]): Set of CRASHGEN ignore settings.
            warn_noplugins (str): Warning message for no plugins.
            warn_outdated (str): Warning message for outdated plugins.
            xse_acronym (str): Acronym for XSE.
            game_ignore_plugins (list[str]): List of plugins to ignore in crash logs.
            game_ignore_records (list[str]): List of records to ignore in crash logs.
            suspects_error_list (dict[str, str]): Dictionary of error checks for crash logs.
            suspects_stack_list (dict[str, list[str]]): Dictionary of stack checks for crash logs.
            autoscan_text (str): Text for the autoscan interface.
            ignore_list (list[str]): List of items to ignore.
            game_mods_conf (dict[str, str]): Configuration for game mods.
            game_mods_core (dict[str, str]): Core game mods.
            game_mods_core_folon (dict[str, str]): Core FOLON game mods.
            game_mods_freq (dict[str, str]): Frequently used game mods.
            game_mods_opc2 (dict[str, str]): OPC2 game mods.
            game_mods_solu (dict[str, str]): SOLU game mods.
            game_version (Version): Version of the game.
            game_version_new (Version): New version of the game.
            game_version_vr (Version): Version of the VR game.
        """
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
        """
        Initializes the CLASSIC_ScanLogs class.

        This method performs the following tasks:
        - Compiles a regular expression pattern for plugin search.
        - Retrieves a list of crash log files.
        - Prints a message indicating the start of crash log reformatting.
        - Loads a list of log records to exclude from YAML settings.
        - Reformats the crash logs based on the retrieved list and exclusion list.
        - Loads various settings and data from YAML and other sources.
        - Prints a message indicating the start of crash log scanning.
        - Records the start time of the scan.

        Attributes:
            pluginsearch (re.Pattern): Compiled regex pattern for plugin search.
            crashlog_list (list): List of crash log files.
            remove_list (list): List of log records to exclude.
            yamldata (ClassicScanLogsInfo): Instance containing scan log information.
            xse_acronym (str): Lowercase acronym for XSE.
            fcx_mode (bool): Flag indicating if FCX Mode is enabled.
            show_formid_values (bool): Flag indicating if FormID values should be shown.
            formid_db_exists (bool): Flag indicating if the FormID database exists.
            move_unsolved_logs (bool): Flag indicating if unsolved logs should be moved.
            lower_records (list): List of classic records in lowercase.
            lower_ignore (list): List of game ignore records in lowercase.
            lower_plugins_ignore (set): Set of game ignore plugins in lowercase.
            ignore_plugins_list (set): Set of plugins to ignore in lowercase.
            scan_start_time (float): Start time of the scan.
            main_files_check (str): Results of the main files check.
            game_files_check (str): Results of the game files check.
            scan_failed_list (list): List of failed scans.
            user_folder (Path): Path to the user's home folder.
            stats_crashlog_scanned (int): Number of scanned crash logs.
            stats_crashlog_incomplete (int): Number of incomplete crash logs.
            stats_crashlog_failed (int): Number of failed crash logs.
        """
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
        Checks the FCX mode status and performs corresponding actions.

        If FCX mode is enabled, it updates `main_files_check` and `game_files_check`
        with the results from `CMain.main_combined_result()` and `CGame.game_combined_result()`
        respectively. If FCX mode is disabled, it sets `main_files_check` to a message
        indicating that FCX mode is disabled and skips the game files check, leaving
        `game_files_check` empty.

        Returns:
            None
        """
        if self.fcx_mode:
            self.main_files_check = CMain.main_combined_result()
            self.game_files_check = CGame.game_combined_result()
        else:
            self.main_files_check = "❌ FCX Mode is disabled, skipping game files check... \n-----\n"
            self.game_files_check = ""

    def find_segments(self, crash_data: list[str], crashgen_name: str) -> tuple[str, str, str, list[list[str]]]:
        """
        Divide the log up into segments.
        Args:
            crash_data (list[str]): The list of strings representing the crash log data.
            crashgen_name (str): The name of the crash generator to look for in the log.
        Returns:
            tuple[str, str, str, list[list[str]]]: A tuple containing:
                - crashlog_gameversion (str): The game version found in the log or "UNKNOWN" if not found.
                - crashlog_crashgen (str): The crash generator name found in the log or "UNKNOWN" if not found.
                - crashlog_mainerror (str): The main error message found in the log or "UNKNOWN" if not found.
                - segment_results (list[list[str]]): A list of lists, where each inner list represents a segment of the log.
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
        Scan the loadorder.txt file for plugins.

        This method reads the loadorder.txt file and extracts the plugin names,
        storing them in a dictionary with a marker indicating they were found in
        the load order. It also sets a trigger to indicate that plugins were loaded.

        Returns:
            tuple[dict[str, str], bool]: A tuple containing a dictionary of plugin
            names with their markers and a boolean indicating if plugins were loaded.
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
        Scan the crash log for plugins and determine if certain conditions are met.

        Args:
            segment_plugins (list[str]): A list of plugin strings to scan.
            game_version (Version): The version of the game being analyzed.
            version_current (Version): The current version of the game being analyzed.

        Returns:
            tuple[dict[str, str], bool, bool]:
                - A dictionary mapping plugin names to their file IDs or special identifiers.
                - A boolean indicating if the plugin limit trigger is activated.
                - A boolean indicating if the limit check is disabled.
        """
        crashlog_plugins: dict[str, str] = {}
        trigger_plugin_limit = trigger_limit_check_disabled = False
        for elem in segment_plugins:
            if "[FF]" in elem:
                if game_version in (self.yamldata.game_version, self.yamldata.game_version_vr):
                    trigger_plugin_limit = True
                elif game_version >= self.yamldata.game_version_new and version_current < Version("1.37.0"):
                    trigger_limit_check_disabled = True
            pluginmatch = self.pluginsearch.match(elem, concurrent=True)
            if pluginmatch is not None:
                plugin_fid = pluginmatch.group(1)
                plugin_name = pluginmatch.group(3)
                if plugin_fid is not None and all(plugin_name not in item for item in crashlog_plugins):
                    crashlog_plugins[plugin_name] = plugin_fid.replace(":", "")
                elif plugin_name and "dll" in plugin_name.lower():
                    crashlog_plugins[plugin_name] = "DLL"
                else:
                    crashlog_plugins[plugin_name] = "???"
        return crashlog_plugins, trigger_plugin_limit, trigger_limit_check_disabled

    def suspect_scan_mainerror(self, autoscan_report: list[str], crashlog_mainerror: str, max_warn_length: int) -> bool:
        """
        Scans the crash log main error for known suspect errors and updates the autoscan report.

        Args:
            autoscan_report (list[str]): The list to append the scan results to.
            crashlog_mainerror (str): The main error message from the crash log.
            max_warn_length (int): The maximum length for the warning message.

        Returns:
            bool: True if a suspect error is found, False otherwise.
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
        Scans the provided crash log and call stack segment for known suspect errors and updates the autoscan report.
        Args:
            crashlog_mainerror (str): The main error message from the crash log.
            segment_callstack_intact (str): The intact segment of the call stack to be scanned.
            autoscan_report (list[str]): The list to append the scan results to.
            max_warn_length (int): The maximum length for the warning message.
        Returns:
            bool: True if any suspect error is found, False otherwise.
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
        Scans the Buffout achievements setting and updates the autoscan report accordingly.

        This method checks if the "Achievements" setting in the crashgen dictionary is enabled
        and if either "achievements.dll" or "unlimitedsurvivalmode.dll" is present in the xsemodules set.
        If both conditions are met, it appends a caution message to the autoscan report suggesting
        to disable the Achievements setting to prevent conflicts. Otherwise, it appends a message
        indicating that the Achievements parameter is correctly configured.

        Args:
            autoscan_report (list[str]): The list to which the scan results will be appended.
            xsemodules (set[str]): A set of module names to check for the presence of specific DLLs.
            crashgen (dict[str, bool | int | str]): A dictionary containing the crash generation settings.

        Returns:
            None
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
        Scans and validates the memory management settings for the Buffout 4 crash generator configuration.
        This function checks the compatibility of the memory management settings with the installed mods (X-Cell and Baka ScrapHeap)
        and appends appropriate messages to the autoscan report.
        
        Parameters:
        autoscan_report (list[str]): The list to which the scan results will be appended.
        crashgen (dict[str, bool | int | str]): The crash generator configuration settings.
        Has_XCell (bool): Indicates if the X-Cell mod is installed.
        Has_BakaScrapHeap (bool): Indicates if the Baka ScrapHeap mod is installed.
        
        Returns:
        None
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
        Scans the ArchiveLimit setting and updates the autoscan report accordingly.

        This method checks if the "ArchiveLimit" setting in the crashgen dictionary is enabled.
        If the setting is enabled, it appends a caution message to the autoscan report suggesting
        to disable the ArchiveLimit setting to reduce instability.
        Otherwise, it appends a message indicating that the ArchiveLimit parameter is correctly configured.

        Args:
            autoscan_report (list[str]): The list to which the scan results will be appended.
            crashgen (dict[str, bool | int | str]): A dictionary containing the crash generation settings.

        Returns:
            None
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
        Scans the Buffout settings for LooksMenu and updates the autoscan report accordingly.

        This method checks if the "F4EE" setting in the crashgen dictionary is enabled
        and if "f4ee.dll" is present in the xsemodules set. If the setting is not enabled
        but the DLL is present, it appends a caution message to the autoscan report suggesting
        to enable the F4EE setting to prevent bugs and crashes from LooksMenu. Otherwise, it
        appends a message indicating that the F4EE parameter is correctly configured.

        Args:
            crashgen (dict[str, bool | int | str]): A dictionary containing the crash generation settings.
            autoscan_report (list[str]): The list to which the scan results will be appended.
            xsemodules (set[str]): A set of module names to check for the presence of specific DLLs.

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
        Matches FormIDs with plugins and updates the autoscan report.

        Args:
            formids_matches (list[str]): A list of FormID matches found in the crash log.
            crashlog_plugins (dict[str, str]): A dictionary mapping plugin names to their file IDs.
            autoscan_report (list[str]): A list to append the scan results to.

        Returns:
            None
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
        Matches plugins found in the call stack segment with the crash log plugins and updates the autoscan report.

        Args:
            segment_callstack_lower (list[str]): A list of strings representing the call stack segment in lowercase.
            crashlog_plugins_lower (set[str]): A set of plugin names in lowercase.
            autoscan_report (list[str]): A list to append the scan results to.

        Returns:
            None
        """
        plugins_matches: list[str] = [
            plugin
            for line in segment_callstack_lower
            for plugin in crashlog_plugins_lower
            if plugin in line and "modified by:" not in line and all(
                ignore not in plugin for ignore in self.lower_plugins_ignore)
        ]
        if plugins_matches:
            plugins_found = dict(Counter(plugins_matches))
            if plugins_found:
                append_or_extend([f"- {key} | {value}\n" for key, value in plugins_found.items()], autoscan_report)
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
        Scans the system segment of the crash log to determine the GPU brand.

        Args:
            segment_system (list[str]): The list of strings representing the system segment of the crash log.

        Returns:
            tuple[str, str | None]: A tuple containing:
                - The GPU brand found in the log ("AMD", "Nvidia", or "Unknown").
                - The rival GPU brand ("nvidia" or "amd") if a known GPU brand is found, otherwise None.
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
        Scans the call stack segment for named records and updates the autoscan report.

        Args:
            segment_callstack (list[str]): The list of strings representing the call stack segment.
            records_matches (list[str]): The list of record matches found in the call stack.
            autoscan_report (list[str]): The list to append the scan results to.

        Returns:
            None
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


# ================================================
# CRASH LOG SCAN START
# ================================================
def crashlogs_scan() -> None:
    """
    Scans crash logs for a Fallout 4 game, generates detailed autoscan reports, and identifies potential issues.
    This function performs the following steps:
    1. Initializes the ClassicScanLogs scanner and retrieves YAML data.
    2. Iterates through each crash log file in the scanner's crashlog list.
    3. Reads the crash log data and generates an autoscan report header.
    4. Extracts and processes various segments from the crash log.
    5. Checks for important DLLs and updates the crash generation dictionary.
    6. Updates scanner statistics based on the completeness of the crash log.
    7. Appends main error and crash generation version information to the report.
    8. Checks for loaded plugins and updates the crash log plugins dictionary.
    9. Scans for GPU type and loads plugins from loadorder.txt if available.
    10. Checks for ignored plugins and appends relevant information to the report.
    11. Identifies potential crash suspects and appends relevant information to the report.
    12. Checks for necessary files and settings, and appends relevant information to the report.
    13. Scans for mods that can cause frequent crashes and appends relevant information to the report.
    14. Scans for mods that conflict with other mods and appends relevant information to the report.
    15. Scans for mods with solutions and community patches and appends relevant information to the report.
    16. Checks for mods patched through the OPC installer (specific to Fallout 4).
    17. Checks for important patches and fixes, and appends relevant information to the report.
    18. Scans the log for specific possible suspects and appends relevant information to the report.
    19. Lists possible plugin and form ID suspects, and appends relevant information to the report.
    20. Writes the autoscan report to a file and handles failed scans by moving logs to a backup folder.
    21. Checks for failed or invalid crash logs and prints a notice if any are found.
    22. Closes the scanner database and prints the scan completion message and statistics.
    Note:
        - The function assumes the presence of various methods and attributes in the ClassicScanLogs class.
        - The function also assumes the presence of certain global variables and constants (e.g., CMain, yamldata).
        - The function generates autoscan reports in Markdown format and saves them to files.
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
        segment_xsemodules_lower = {x.lower() for x in segment_xsemodules}
        xsemodules = (
            {x.split(" v", 1)[0].strip() if "dll v" in x else x.strip() for x in segment_xsemodules_lower}
            if segment_xsemodules_lower
            else set()
        )
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
        crashlog_GPU, crashlog_GPU_rival = scanner.scan_log_gpu(segment_system)

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
                if any(signal == plugin for plugin in crashlog_plugins_lower):
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

        Has_XCell = ("x-cell-fo4.dll" in xsemodules or "x-cell-og.dll" in xsemodules or "x-cell-ng2.dll" in xsemodules)
        Has_BakaScrapHeap = "bakascrapheap.dll" in xsemodules

        if scanner.fcx_mode:
            append_or_extend((
                "* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION * \n",
                "[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ] \n\n",
            ), autoscan_report)

        else:
            append_or_extend((
                "* NOTICE: FCX MODE IS DISABLED. YOU CAN ENABLE IT TO DETECT PROBLEMS IN YOUR MOD & GAME FILES * \n",
                "[ FCX Mode can be enabled in the exe or CLASSIC Settings.yaml located in your CLASSIC folder. ] \n\n",
            ), autoscan_report)
            if Has_XCell:
                yamldata.crashgen_ignore.update(
                    ("MemoryManager", "HavokMemorySystem", "ScaleformAllocator", "SmallBlockAllocator"))
            elif Has_BakaScrapHeap:
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
                scanner.scan_buffout_memorymanagement_settings(autoscan_report, crashgen, Has_XCell, Has_BakaScrapHeap)
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
                                      crashlog_GPU_rival)
            else:
                detect_mods_important(yamldata.game_mods_core, crashlog_plugins, autoscan_report, crashlog_GPU_rival)
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
    from pathlib import Path

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
