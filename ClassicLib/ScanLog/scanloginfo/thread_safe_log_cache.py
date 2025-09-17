"""
Thread-safe log cache for crash log processing.

This module provides a thread-safe caching mechanism for log files
using a dictionary protected by a lock.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ClassicLib import msg_error


class ThreadSafeLogCache:
    """
    Provides a thread-safe, in-memory log cache for managing log files.

    This class is designed to handle log file data in memory efficiently,
    supporting both asynchronous and parallel synchronous loading. The
    primary goal is to offer a thread-safe alternative to database-based
    log management systems like SQLite. The implementation uses a lock
    to ensure thread-safe operations, making it suitable for concurrent
    environments.

    Attributes:
        lock (RLock): A reentrant lock used to ensure thread safety during cache operations.
        cache (dict[str, bytes]): A dictionary storing the cached log data. The keys are
            log file names, and the values are their byte content.
    """
    def __init__(self, logfiles: list[Path]) -> None:
        """
        Initializes the log loader and populates a cache with the log_content of the provided log files.

        This class initializer attempts to load the log_content of log files either asynchronously
        through the FileIOCore module for better performance when available, or by falling
        back to parallel synchronous loading using ThreadPoolExecutor when async loading is
        not possible. Both approaches handle errors during file reads and optionally log them.

        Args:
            logfiles (list[Path]): A list of Path objects pointing to the log files to be loaded.
        """
        self.lock = threading.RLock()  # Reentrant lock allows nested acquisitions
        self.cache: dict[str, bytes] = {}

        # Populate the cache with log log_content
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
                        log_content = await io_core.read_bytes(file)
                        results[file.name] = log_content
                    except (OSError, ValueError, UnicodeDecodeError) as e:
                        msg_error(f"Error reading {file}: {e}")
                return results

            self.cache = run_async(load_all_logs())
            from ClassicLib.Logger import logger

            logger.debug(f"Loaded {len(self.cache)} crash logs using FileIOCore")
        except (ImportError, RuntimeError, OSError):
            # Fallback to parallel sync loading for better performance
            def load_file(file: Path) -> tuple[str, bytes | None]:
                """
                Loads the log_content of a file and handles potential errors during the process.

                This function attempts to read the bytes of the specified file and returns a
                tuple containing the file's name and its log_content. If an error occurs while
                reading the file, an error message is logged, and the log_content is returned as
                None.

                Args:
                    file (Path): The file to read.

                Returns:
                    tuple[str, bytes | None]: A tuple where the first item is the file's name
                    and the second item is the file's log_content as bytes, or None if reading the
                    file failed.
                """
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
        Reads the log contents for a specific log file from the cache and returns it as a list of strings.

        This method accesses the cache and retrieves the log information associated with the given logname.
        If the logname is not found in the cache, an empty list is returned. The log data is decoded from
        UTF-8 and split into individual lines.

        Args:
            logname (str): The name of the log file to read.

        Returns:
            list[str]: A list of strings representing the lines of the log file.
            Returns an empty list if the logname is not in the cache.
        """
        with self.lock:
            if logname not in self.cache:
                return []

            logdata = self.cache[logname]
            return logdata.decode("utf-8", errors="ignore").splitlines()

    def get_log_names(self) -> list[str]:
        """
        Retrieves the list of log names from the cache.

        This method accesses the cache in a thread-safe manner by using a lock,
        returning a list of all keys that represent log names.

        Returns:
            list[str]: A list of log name strings present in the cache.
        """
        with self.lock:
            return list(self.cache.keys())

    def add_log(self, path: Path) -> bool:
        """
        Adds a log entry to the cache from the specified file path.

        This method reads the contents of a file at the given path and adds it to
        an internal cache if it does not already exist. If the operation is
        successful, it returns True. If an error occurs while reading the file, it
        returns False.

        Args:
            path (Path): The file path from which log data is read and cached.

        Returns:
            bool: True if the log is added successfully; False otherwise.
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
        Clears the cache and releases any resources associated with the lock.

        This method is thread-safe. It acquires a lock to ensure no other threads
        are accessing or modifying the cache at the same moment. The cache is
        cleared entirely when this method is invoked.
        """
        with self.lock:
            self.cache.clear()

    @classmethod
    def from_cache(cls, cache_dict: dict[str, bytes]) -> "ThreadSafeLogCache":
        """
        Creates a ThreadSafeLogCache instance from an existing cache dictionary.

        Args:
            cache_dict (dict[str, bytes]): A dictionary containing log data where keys are
                string identifiers, and values are log contents as bytes.

        Returns:
            ThreadSafeLogCache: A new instance of ThreadSafeLogCache initialized with
                the provided cache dictionary.
        """
        # Create instance without loading files
        instance = cls.__new__(cls)
        instance.lock = threading.RLock()
        instance.cache = cache_dict.copy()

        from ClassicLib.Logger import logger

        logger.debug(f"Created ThreadSafeLogCache from existing cache with {len(cache_dict)} logs")

        return instance
