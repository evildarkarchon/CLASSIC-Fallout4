import shutil
import sqlite3
from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import DB_PATHS, YAML
from ClassicLib.Logger import logger
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

# Constants for file patterns
CRASH_LOG_PATTERN = "crash-*.log"
CRASH_AUTOSCAN_PATTERN = "crash-*-AUTOSCAN.md"


def ensure_directory_exists(directory: Path) -> None:
    """
    Ensures that a specified directory exists by creating it, including any necessary
    parent directories.

    If the directory already exists, the function does nothing.

    Parameters:
        directory (Path): The path of the directory to ensure exists.

    Returns:
        None
    """
    directory.mkdir(parents=True, exist_ok=True)


def move_files(source_dir: Path, target_dir: Path, pattern: str) -> None:
    """
    Moves files matching a given pattern from the source directory to the
    target directory.

    This function iterates through all files in the source directory that
    match the specified pattern, and moves each file to the target directory
    if a file with the same name does not already exist in the target
    directory.

    Arguments:
        source_dir (Path): The directory containing the files to be moved.
        target_dir (Path): The directory to which the files will be moved.
        pattern (str): A glob pattern to filter the files to be moved.

    Returns:
        None
    """
    for file in source_dir.glob(pattern):
        destination_file: Path = target_dir / file.name
        if not destination_file.is_file():
            file.rename(destination_file)


def copy_files(source_dir: Path | None, target_dir: Path, pattern: str) -> None:
    """
    Copies files from the source directory to the target directory based on a given pattern.

    This function iterates through all files in the specified source
    directory that match the given pattern and copies them to the target
    directory. Files that already exist in the target directory are not
    overwritten.

    Args:
        source_dir (Path | None): The path to the source directory. If None or
                                  the directory does not exist, the function
                                  does nothing.
        target_dir (Path): The path to the target directory where files will
                           be copied.
        pattern (str): A glob-style pattern used to match files in the source
                       directory.

    Returns:
        None
    """
    if source_dir and source_dir.is_dir():
        for file in source_dir.glob(pattern):
            destination_file: Path = target_dir / file.name
            if not destination_file.is_file():
                shutil.copy2(file, destination_file)


def get_path_from_setting(setting_value: str | None) -> Path | None:
    """
    Converts a setting value to a Path object if it is a valid string.

    This function takes a provided setting value and checks if it is a string.
    If the value is a string, it converts it to a Path object. If the value is
    not a string or is None, the function returns None. This utility can be
    used to ensure a safe conversion of various input configuration values
    to Path objects.

    Args:
        setting_value: The input value to convert to a Path. Can be a string
            or None.

    Returns:
        A Path object if the input value is a string, otherwise None.
    """
    return Path(setting_value) if isinstance(setting_value, str) else None


def is_valid_custom_scan_path(path: Path | str) -> bool:
    """
    Check if the given path is valid as a custom scan directory.
    Prevents users from setting hard-coded directories as custom scan paths.

    Args:
        path: The path to validate

    Returns:
        bool: True if the path is valid, False if it's a restricted directory
    """
    if isinstance(path, str):
        path = Path(path)

    # Resolve to absolute path for comparison
    try:
        abs_path = path.resolve()
    except (OSError, RuntimeError):
        return False

    # Define restricted paths (hard-coded directories)
    cwd: Path = Path(GlobalRegistry.get_local_dir()).resolve()
    restricted_paths = [
        cwd / "Crash Logs",
        cwd / "Crash Logs" / "Pastebin",
        yaml_settings(Path, YAML.Game_Local, "Game_Info.Docs_Folder_XSE"),
    ]

    # Check if the path matches any restricted path
    for restricted in restricted_paths:
        if restricted is None:
            continue
        try:
            if abs_path == restricted or abs_path in restricted.parents:
                logger.warning(f"Attempted to set restricted path as custom scan directory: {path}")
                return False
        except ValueError:
            # Can happen if paths are on different drives on Windows
            pass

    return True


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

    # Define directory structure
    base_folder: Path = Path.cwd()
    crash_logs_dir: Path = base_folder / "Crash Logs"
    pastebin_dir: Path = crash_logs_dir / "Pastebin"

    # Get additional directories from settings
    custom_folder: Path | None = get_path_from_setting(classic_settings(str, "SCAN Custom Path"))
    xse_folder: Path | None = get_path_from_setting(yaml_settings(str, YAML.Game_Local, "Game_Info.Docs_Folder_XSE"))

    # Ensure required directories exist
    ensure_directory_exists(crash_logs_dir)
    ensure_directory_exists(pastebin_dir)

    # Process files from base directory
    move_files(base_folder, crash_logs_dir, CRASH_LOG_PATTERN)
    move_files(base_folder, crash_logs_dir, CRASH_AUTOSCAN_PATTERN)

    # Copy files from XSE folder if available
    copy_files(xse_folder, crash_logs_dir, CRASH_LOG_PATTERN)

    # Collect crash log files
    crash_files: list[Path] = list(crash_logs_dir.rglob(CRASH_LOG_PATTERN))
    if custom_folder and custom_folder.is_dir():
        crash_files.extend(custom_folder.glob(CRASH_LOG_PATTERN))

    return crash_files


query_cache: dict[tuple[str, str], str] = {}


def get_entry(formid: str, plugin: str) -> str | None:
    """
    Fetches an entry from the cache or database based on the given form ID and plugin.

    This function checks if an entry corresponding to the given `formid` and
    `plugin` exists in the query cache. If the entry is not found in the cache,
    it iterates through a list of database paths (`DB_PATHS`) to locate the entry
    in the database file. If found in the database, the entry is added to the
    query cache for faster access on subsequent calls.

    Args:
        formid: The unique identifier for the form entry to be retrieved.
        plugin: The name of the plugin associated with the form entry.

    Returns:
        str | None: The retrieved entry if found, or None if no such entry exists.
    """
    if (entry := query_cache.get((formid, plugin))) is not None:
        return entry

    for db_path in DB_PATHS:
        if db_path.is_file():
            with sqlite3.connect(db_path) as conn:
                c: sqlite3.Cursor = conn.cursor()
                c.execute(
                    f"SELECT entry FROM {GlobalRegistry.get_game()} WHERE formid=? AND plugin=? COLLATE nocase",
                    (formid, plugin),
                )
                entry = c.fetchone()
                if entry:
                    query_cache[formid, plugin] = entry[0]
                    return entry[0]

    return None


def crashlogs_reformat(crashlog_list: list[Path], remove_list: tuple[str]) -> None:
    """
    Processes and reformats a list of crash log files based on specified settings and criteria. This function performs
    operations such as removing certain lines from logs if simplification is enabled and modifying plugin load order lines
    to ensure consistency across different log versions.

    Args:
        crashlog_list (list[Path]): A list of file paths pointing to crash log files to be reformatted.
        remove_list (tuple[str]): A tuple of strings representing the substrings that should trigger line removal from
            crash logs when log simplification is enabled.

    """
    logger.debug("- - - INITIATED CRASH LOG FILE REFORMAT")
    simplify_logs: bool | None = classic_settings(bool, "Simplify Logs")

    for file in crashlog_list:
        with file.open(encoding="utf-8", errors="ignore") as crash_log:
            original_lines: list[str] = crash_log.readlines()

        processed_lines_reversed: list[str] = []
        in_plugins_section = True  # State for tracking if currently in the PLUGINS section

        # Iterate over lines from bottom to top to correctly handle PLUGINS section logic
        for line in reversed(original_lines):
            if in_plugins_section and line.startswith("PLUGINS:"):
                in_plugins_section = False  # Exited the PLUGINS section (from bottom)

            # Condition for removing lines if Simplify Logs is enabled
            if simplify_logs and any(string in line for string in remove_list):
                # Skip this line by not adding it to processed_lines_reversed
                continue

            # Condition for reformatting lines within the PLUGINS section
            if in_plugins_section and "[" in line:
                # Replace all spaces inside the load order [brackets] with 0s.
                # This maintains consistency between different versions of Buffout 4.
                # Example log lines:
                # [ 1] DLCRobot.esm
                # [FE:  0] RedRocketsGlareII.esl
                try:
                    indent, rest = line.split("[", 1)
                    fid, name = rest.split("]", 1)
                    modified_line: str = f"{indent}[{fid.replace(' ', '0')}]{name}"
                    processed_lines_reversed.append(modified_line)
                except ValueError:
                    # If line format is unexpected (e.g., no ']' after '['), keep original line
                    processed_lines_reversed.append(line)
            else:
                # Line is not removed or modified, keep as is
                processed_lines_reversed.append(line)

        # The processed_lines_reversed list is in reverse order, so reverse it back
        final_processed_lines: list[str] = list(reversed(processed_lines_reversed))

        with file.open("w", encoding="utf-8", errors="ignore") as crash_log:
            crash_log.writelines(final_processed_lines)
