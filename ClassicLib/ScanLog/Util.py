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


def is_valid_custom_scan_path(path: Path | str | None) -> bool:
    """
    Check if the given path is valid as a custom scan directory.

    Prevents users from setting restricted directories as custom scan paths.
    This includes:
    - CLASSIC-specific directories (Crash Logs, Pastebin, XSE folder)
    - Windows system directories (System32, Program Files, ProgramData, etc.)

    These directories are restricted because they receive special treatment
    by Windows (antivirus scrutiny, elevated permissions) which can interfere
    with the operation of the program or the game.

    Args:
        path: The path to validate

    Returns:
        bool: True if the path is valid, False if it's a restricted directory
    """
    import os
    import platform

    # Handle None and empty strings
    if path is None:
        return False
    if isinstance(path, str):
        if not path.strip():
            return False
        path = Path(path)

    # Resolve to absolute path for comparison
    try:
        abs_path = path.resolve()
    except (OSError, RuntimeError):
        return False

    # Define CLASSIC-specific restricted paths
    cwd: Path = Path(GlobalRegistry.get_local_dir()).resolve()
    restricted_paths: list[Path | None] = [
        cwd / "Crash Logs",
        cwd / "Crash Logs" / "Pastebin",
        yaml_settings(Path, YAML.Game_Local, "Game_Info.Docs_Folder_XSE"),
    ]

    # Add Windows system directories if on Windows
    if platform.system() == "Windows":
        # Get environment variables for system paths
        system_root = os.environ.get("SystemRoot", r"C:\Windows")  # noqa: SIM112
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")  # noqa: SIM112
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")  # noqa: SIM112
        program_data = os.environ.get("ProgramData", r"C:\ProgramData")  # noqa: SIM112
        system_drive = os.environ.get("SystemDrive", "C:")  # noqa: SIM112

        # Add Windows restricted directories
        windows_restricted: list[Path | None] = [
            Path(system_root),  # C:\Windows (includes System32, SysWOW64, etc.)
            Path(program_files),  # C:\Program Files
            Path(program_files_x86) if program_files_x86 else None,  # C:\Program Files (x86)
            Path(program_data),  # C:\ProgramData
            Path(system_drive) / "Recovery",  # Recovery partition
            Path(system_drive) / "$Recycle.Bin",  # Recycle bin
        ]
        restricted_paths.extend(windows_restricted)

    # Check if the path matches any restricted path or is a subdirectory of one
    abs_path_str = str(abs_path).lower()
    for restricted in restricted_paths:
        if restricted is None:
            continue
        try:
            restricted_resolved = restricted.resolve()
            restricted_str = str(restricted_resolved).lower()

            # Check exact match or if abs_path is inside restricted directory
            if abs_path_str == restricted_str or abs_path_str.startswith(restricted_str + os.sep):
                logger.warning(f"Attempted to set restricted path as custom scan directory: {path}")
                return False
        except (ValueError, OSError):
            # Can happen if paths are on different drives on Windows or path doesn't exist
            pass

    return True


def _crashlogs_get_files_python() -> list[Path]:
    """
    Python implementation of crash log file collection.

    This is the fallback implementation when Rust acceleration is not available.

    Returns:
        list[Path]: A list of `Path` objects representing all discovered and processed crash log files.
    """
    logger.debug("- - - INITIATED CRASH LOG FILE LIST GENERATION (Python)")

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


def _crashlogs_get_files_rust() -> list[Path]:
    """
    Rust-accelerated implementation of crash log file collection (10x faster).

    Uses PyLogCollector from classic_file_io for high-performance async file operations.

    Returns:
        list[Path]: A list of `Path` objects representing all discovered and processed crash log files.
    """
    import classic_file_io

    logger.debug("- - - INITIATED CRASH LOG FILE LIST GENERATION (Rust)")

    # Get directories from settings
    custom_folder: Path | None = get_path_from_setting(classic_settings(str, "SCAN Custom Path"))
    xse_folder: Path | None = get_path_from_setting(yaml_settings(str, YAML.Game_Local, "Game_Info.Docs_Folder_XSE"))

    # Convert to strings for Rust (PyLogCollector expects strings)
    base_folder_str = str(Path.cwd())
    xse_folder_str = str(xse_folder) if xse_folder else None
    custom_folder_str = str(custom_folder) if custom_folder else None

    # Create LogCollector
    collector = classic_file_io.PyLogCollector(base_folder=base_folder_str, xse_folder=xse_folder_str, custom_folder=custom_folder_str)

    # Collect all crash logs (async operation handled by Rust runtime)
    log_paths: list[str] = collector.collect_all()

    # Convert strings back to Path objects
    return [Path(p) for p in log_paths]


def crashlogs_get_files() -> list[Path]:
    """
    Generates a list of crash log file paths from various defined directories, ensuring that necessary
    directories and files are aggregated and organized under a primary "Crash Logs" folder. This function
    handles file copying and renaming operations and supports the inclusion of custom and additional
    directories specified in settings.

    This function automatically uses Rust acceleration when available (10x faster), falling back to
    Python implementation for maximum compatibility.

    Returns:
        list[Path]: A list of `Path` objects representing all discovered and processed crash log files.
    """
    # Try Rust acceleration first
    try:
        return _crashlogs_get_files_rust()
    except ImportError:
        # Rust not available, use Python fallback
        logger.debug("Rust acceleration not available, using Python implementation")
        return _crashlogs_get_files_python()
    except Exception as e:  # noqa: BLE001 - Intentional: graceful fallback if Rust log collection fails
        # Rust failed for some reason, fall back to Python
        logger.warning(f"Rust log collection failed ({e}), falling back to Python implementation")
        return _crashlogs_get_files_python()


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
