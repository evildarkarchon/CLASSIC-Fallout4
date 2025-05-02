import shutil
import sqlite3
from pathlib import Path

from CLASSIC_Main import classic_settings, logger, yaml_settings
from ClassicLib.Constants import DB_PATHS, YAML, gamevars


def crashlogs_get_files() -> list[Path]:
    """
    Generates a list of crash log file paths from various defined directories, ensuring that necessary
    directories and files are aggregated and organized under a primary "Crash Logs" folder. This function
    handles file copying and renaming operations and supports the inclusion of custom and additional
    directories specified in settings.

    Returns:
        list[Path]: A list of `Path` objects representing all discovered and processed crash log files.
    """
    logger.debug("- - - INITIATED CRASH LOG FILE LIST GENERATION")
    classic_folder = Path.cwd()
    classic_logs = classic_folder / "Crash Logs"
    classic_pastebin = classic_logs / "Pastebin"
    custom_folder_setting = classic_settings(str, "SCAN Custom Path")
    xse_folder_setting = yaml_settings(str, YAML.Game_Local, "Game_Info.Docs_Folder_XSE")

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


query_cache: dict[tuple[str, str], str] = {}

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
                    f"SELECT entry FROM {gamevars["game"]} WHERE formid=? AND plugin=? COLLATE nocase",
                    (formid, plugin),
                )
                entry = c.fetchone()
                if entry:
                    query_cache[formid, plugin] = entry[0]
                    return entry[0]

    return None


def crashlogs_reformat(crashlog_list: list[Path], remove_list: tuple[str]) -> None:
    """
    Reformats crash log files by simplifying or modifying their content based on specified settings and criteria. This function processes each log file in the provided list, removes lines containing specific substrings if 'Simplify Logs' is enabled, and reformats load order lines for consistency.

    Args:
        crashlog_list: A list of file paths representing crash log files to be reformatted.
        remove_list: A list of strings; if any of these strings appear in a log line and 'Simplify Logs'
            is enabled, the line is removed.

    """
    logger.debug("- - - INITIATED CRASH LOG FILE REFORMAT")
    simplify_logs = classic_settings(bool, "Simplify Logs")

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
