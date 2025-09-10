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
    def __init__(self, logfiles: list[Path]) -> None:
        """
        Initializes a thread-safe in-memory log cache using a dictionary protected by a lock.
        This provides a thread-safe alternative to SQLite for caching log files.

        Args:
            logfiles (list[Path]): A list of file paths representing the log files to be cached.
        """
        self.lock = threading.RLock()  # Reentrant lock allows nested acquisitions
        self.cache: dict[str, bytes] = {}

        # Populate the cache with log content
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
                        content = await io_core.read_bytes(file)
                        results[file.name] = content
                    except (OSError, ValueError, UnicodeDecodeError) as e:
                        msg_error(f"Error reading {file}: {e}")
                return results

            self.cache = run_async(load_all_logs())
            from ClassicLib.Logger import logger

            logger.debug(f"Loaded {len(self.cache)} crash logs using FileIOCore")
        except (ImportError, RuntimeError, OSError):
            # Fallback to parallel sync loading for better performance
            def load_file(file: Path) -> tuple[str, bytes | None]:
                """Load a single file and return its name and content."""
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
        Reads log data for a specified log name from the cache.

        This method retrieves log data associated with the provided log name
        from a cached data source and returns it as a list of decoded string
        lines. If the log name does not exist in the cache, an empty list
        is returned.

        Parameters:
            logname (str): The name of the log to retrieve.

        Returns:
            list[str]: List of log lines as strings. Returns an empty list if
            the log name is not found in the cache.
        """
        with self.lock:
            if logname not in self.cache:
                return []

            logdata = self.cache[logname]
            return logdata.decode("utf-8", errors="ignore").splitlines()

    def get_log_names(self) -> list[str]:
        """
        Retrieves the names of all logs currently stored in the cache.

        This method provides a thread-safe way to access the keys representing
        log names in a cached storage structure, ensuring that data integrity is
        maintained during access.

        Returns:
            list[str]: A list containing the names of all logs in the cache.
        """
        with self.lock:
            return list(self.cache.keys())

    def add_log(self, path: Path) -> bool:
        """
        Adds a log file to the internal cache if it is not already present.

        Parameters:
        path (Path): The path to the log file to be added.

        Returns:
        bool: True if the log file was successfully added to the cache or is
        already present; False if an OSError occurred during reading.

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
        Clears the cache when no longer needed.
        """
        with self.lock:
            self.cache.clear()

    @classmethod
    def from_cache(cls, cache_dict: dict[str, bytes]) -> "ThreadSafeLogCache":
        """
        Creates a new instance of the ThreadSafeLogCache class using an existing cache
        dictionary. This method allows for generating an object without directly
        loading files, by copying the provided cache dictionary into the instance.
        Used primarily for scenarios where log files are already cached and need to
        be encapsulated in a thread-safe structure.

        Parameters:
            cache_dict (dict[str, bytes]): A dictionary representing cached log data,
            where keys are strings identifying logs, and values are byte content of
            the logs.

        Returns:
            ThreadSafeLogCache: A new instance of the ThreadSafeLogCache initialized
            with the contents of the provided cache.

        Raises:
            None
        """
        # Create instance without loading files
        instance = cls.__new__(cls)
        instance.lock = threading.RLock()
        instance.cache = cache_dict.copy()

        from ClassicLib.Logger import logger

        logger.debug(f"Created ThreadSafeLogCache from existing cache with {len(cache_dict)} logs")

        return instance
