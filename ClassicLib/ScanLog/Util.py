"""
Utility module for managing SQLite database connections, file operations, and handling directory paths.

This module provides a thread-safe SQLite connection pool, utilities for managing files and directories,
and functions to validate and handle paths used for application configuration, especially related to crash
logs and custom scan directories.
"""
import contextlib
import shutil
import sqlite3
import threading
from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import DB_PATHS, YAML
from ClassicLib.Logger import logger
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

# Constants for file patterns
CRASH_LOG_PATTERN = "crash-*.log"
CRASH_AUTOSCAN_PATTERN = "crash-*-AUTOSCAN.md"


class SyncDatabasePool:
    """
    Manages SQLite database connections safely in a multithreaded environment.

    This class ensures that SQLite connections are handled securely by using a
    lock mechanism to manage access when performing operations from multiple
    threads. Connections are stored and managed internally.

    Attributes:
        _connections (dict[Path, sqlite3.Connection]): A mapping of database file
            paths to their corresponding SQLite connection objects.
        _connection_lock (threading.Lock): A lock to ensure thread-safe access to
            the connections dictionary.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        """
        Manages SQLite database connections safely in a multithreaded environment.

        This class ensures that SQLite connections are
        handled securely by using a lock mechanism to
        manage access when performing operations from
        multiple threads. Connections are stored and
        managed internally.

        """
        self._connections: dict[Path, sqlite3.Connection] = {}
        self._connection_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SyncDatabasePool":
        """
        Retrieves the singleton instance of the `SyncDatabasePool` class.

        This method ensures that there is only one instance of the `SyncDatabasePool`
        class by employing the singleton design pattern. It uses a thread-safe
        double-checked locking mechanism to initialize the instance.

        Returns:
            SyncDatabasePool: The singleton instance of the class.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_connection(self, db_path: Path) -> sqlite3.Connection:
        """
        Creates or retrieves a sqlite3 connection for the specified database file. Ensures that a single
        connection is reused for the same database path, and manages the connections in a thread-safe manner.
        If the connection is not alive or does not exist, a new connection is created.

        Args:
            db_path (Path): Path to the SQLite database file.

        Returns:
            sqlite3.Connection: A SQLite database connection object.

        Raises:
            sqlite3.Error: If there is an issue connecting to the SQLite database file.
        """
        with self._connection_lock:
            if db_path not in self._connections or not self._is_connection_alive(self._connections[db_path]):
                try:
                    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
                    conn.row_factory = sqlite3.Row
                    self._connections[db_path] = conn
                    logger.debug(f"Created new connection for {db_path}")
                except sqlite3.Error as e:
                    logger.error(f"Failed to connect to {db_path}: {e}")
                    raise

            return self._connections[db_path]

    @staticmethod
    def _is_connection_alive(conn: sqlite3.Connection) -> bool:
        """
        Checks if a given SQLite connection is active and alive by executing a test query.

        Args:
            conn (sqlite3.Connection): The SQLite connection object to check.

        Returns:
            bool: True if the connection is alive, False otherwise.
        """
        try:
            conn.execute("SELECT 1")
        except sqlite3.Error:
            return False
        else:
            return True

    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self._connection_lock:
            for conn in self._connections.values():
                with contextlib.suppress(sqlite3.Error):
                    conn.close()
            self._connections.clear()


def ensure_directory_exists(directory: Path) -> None:
    """
    Ensures that the specified directory exists by creating it if it does not already exist.

    If necessary, this function will also create any intermediate directories in the path.

    Args:
        directory: A Path object representing the directory to ensure exists.
    """
    directory.mkdir(parents=True, exist_ok=True)


def move_files(source_dir: Path, target_dir: Path, pattern: str) -> None:
    """
    Moves files matching a given pattern from the source directory to the target directory.

    This function searches for files in the specified source directory matching
    the given pattern, and moves them to the target directory. If a file with
    the same name already exists in the target directory, it will not be
    overwritten.

    Args:
        source_dir (Path): Path to the source directory where files are located.
        target_dir (Path): Path to the target directory where files will be moved.
        pattern (str): Pattern to match files in the source directory.
    """
    for file in source_dir.glob(pattern):
        destination_file: Path = target_dir / file.name
        if not destination_file.is_file():
            file.rename(destination_file)


def copy_files(source_dir: Path | None, target_dir: Path, pattern: str) -> None:
    """
    Copies files from a source directory to a target directory based on a specified pattern.

    This function iterates through all files in the given source directory that match the
    provided pattern. It then copies these files to the target directory if they do not
    already exist in the target directory.

    Args:
        source_dir: The directory from which files will be copied. If None or not a directory,
            the function performs no operation.
        target_dir: The directory to which files will be copied.
        pattern: The pattern to match files in the source directory.
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
    else:
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

    # Use connection pool for better performance
    pool = SyncDatabasePool.get_instance()

    for db_path in DB_PATHS:
        if db_path.is_file():
            try:
                conn = pool.get_connection(db_path)
                c: sqlite3.Cursor = conn.cursor()
                c.execute(
                    f"SELECT entry FROM {GlobalRegistry.get_game()} WHERE formid=? AND plugin=? COLLATE nocase",
                    (formid, plugin),
                )
                entry = c.fetchone()
                if entry:
                    query_cache[formid, plugin] = entry[0]
                    return entry[0]
            except sqlite3.Error as e:
                logger.error(f"Database query error in {db_path}: {e}")

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

    # Track how many files were actually modified
    files_modified = 0

    for file in crashlog_list:
        with file.open(encoding="utf-8", errors="ignore") as crash_log:
            original_lines: list[str] = crash_log.readlines()

        processed_lines_reversed: list[str] = []
        in_plugins_section = True  # State for tracking if currently in the PLUGINS section
        file_was_modified = False  # Track if this file needs to be written

        # Iterate over lines from bottom to top to correctly handle PLUGINS section logic
        for line in reversed(original_lines):
            if in_plugins_section and line.startswith("PLUGINS:"):
                in_plugins_section = False  # Exited the PLUGINS section (from bottom)

            # Condition for removing lines if Simplify Logs is enabled
            if simplify_logs and any(string in line for string in remove_list):
                # Skip this line by not adding it to processed_lines_reversed
                file_was_modified = True  # Mark that we removed a line
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
                    # Check if modification is actually needed
                    if " " in fid:
                        modified_line: str = f"{indent}[{fid.replace(' ', '0')}]{name}"
                        processed_lines_reversed.append(modified_line)
                        file_was_modified = True  # Mark that we modified a line
                    else:
                        # No spaces to replace, keep original
                        processed_lines_reversed.append(line)
                except ValueError:
                    # If line format is unexpected (e.g., no ']' after '['), keep original line
                    processed_lines_reversed.append(line)
            else:
                # Line is not removed or modified, keep as is
                processed_lines_reversed.append(line)

        # Only write the file if it was actually modified
        if file_was_modified:
            # The processed_lines_reversed list is in reverse order, so reverse it back
            final_processed_lines: list[str] = list(reversed(processed_lines_reversed))

            with file.open("w", encoding="utf-8", errors="ignore") as crash_log:
                crash_log.writelines(final_processed_lines)
            files_modified += 1

    if files_modified > 0:
        logger.debug(f"- - - REFORMATTED {files_modified} OF {len(crashlog_list)} FILES")
    else:
        logger.debug("- - - NO FILES REQUIRED REFORMATTING")
        logger.debug("- - - NO FILES REQUIRED REFORMATTING")
