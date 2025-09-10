"""Log file error checking and processing functionality."""

import asyncio
from pathlib import Path

try:
    import aiofiles
except ImportError:
    aiofiles = None  # Handle gracefully if not installed

from ClassicLib import msg_error, msg_info
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.Util import normalize_list, open_file_with_encoding
from ClassicLib.YamlSettingsCache import yaml_settings

from .utils import ASYNC_ENCODING_AVAILABLE, read_lines_with_encoding_async


class LogProcessor:
    """Processes log files for error detection."""

    def __init__(self, log_read_semaphore: asyncio.Semaphore) -> None:
        """Initialize with semaphore for concurrency control."""
        self.log_read_semaphore = log_read_semaphore

    async def check_log_errors(self, folder_path: Path | str) -> str:
        """
        Async-first implementation for checking log file errors.

        Inspects log files within a specified folder for recorded errors, processing
        multiple log files concurrently for improved performance.

        Args:
            folder_path (Path | str): Path to the folder containing log files for error inspection.

        Returns:
            str: A detailed report of all detected errors in the relevant log files, if any.
        """

        def format_error_report(file_path: Path, errors: list[str]) -> list[str]:
            """Format the error report for a specific log file."""
            return [
                "[!] CAUTION : THE FOLLOWING LOG FILE REPORTS ONE OR MORE ERRORS!\n",
                "[ Errors do not necessarily mean that the mod is not working. ]\n",
                f"\nLOG PATH > {file_path}\n",
                *errors,
                f"\n* TOTAL NUMBER OF DETECTED LOG ERRORS * : {len(errors)}\n",
            ]

        # Convert string path to Path object if needed
        if isinstance(folder_path, str):
            folder_path = Path(folder_path)

        # Get YAML settings and convert to sets for faster lookups
        catch_errors_set: set[str] = set(normalize_list(yaml_settings(list[str], YAML.Main, "catch_log_errors") or []))
        ignore_files_set: set[str] = set(normalize_list(yaml_settings(list[str], YAML.Main, "exclude_log_files") or []))
        ignore_errors_set: set[str] = set(normalize_list(yaml_settings(list[str], YAML.Main, "exclude_log_errors") or []))

        # Find valid log files (excluding crash logs)
        valid_log_files: list[Path] = [
            file
            for file in folder_path.glob("*.log")
            if "crash-" not in file.name.lower() and not any(part in str(file).lower() for part in ignore_files_set)
        ]

        async def process_single_log(log_file_path: Path) -> list[str]:
            """Process a single log file and return formatted error report."""
            async with self.log_read_semaphore:
                try:
                    # Use async encoding detection if available
                    if ASYNC_ENCODING_AVAILABLE:
                        log_lines = await read_lines_with_encoding_async(log_file_path)
                    elif aiofiles:
                        # Fallback to aiofiles with utf-8 if async encoding not available
                        async with aiofiles.open(log_file_path, "r", encoding="utf-8", errors="ignore") as log_file:
                            log_lines = await log_file.readlines()
                    else:
                        # Fallback to sync read with async wrapper
                        loop = asyncio.get_event_loop()
                        with open_file_with_encoding(log_file_path) as log_file:
                            log_lines = await loop.run_in_executor(None, log_file.readlines)

                    # Filter for relevant errors
                    detected_errors = [
                        f"ERROR > {line}"
                        for line in log_lines
                        if any(error in line.lower() for error in catch_errors_set)
                        and all(ignore not in line.lower() for ignore in ignore_errors_set)
                    ]

                except OSError:
                    error_message = f"❌ ERROR : Unable to scan this log file :\n  {log_file_path}"
                    logger.warning(f"> ! > DETECT LOG ERRORS > UNABLE TO SCAN : {log_file_path}")
                    return [error_message]
                else:
                    if detected_errors:
                        return format_error_report(log_file_path, detected_errors)
                    return []

        # Process all log files concurrently
        if valid_log_files:
            msg_info(f"Processing {len(valid_log_files)} log files concurrently...")
        tasks = [process_single_log(log_file) for log_file in valid_log_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect all error reports
        error_report: list[str] = []
        for result in results:
            if isinstance(result, Exception):
                msg_error(f"Task failed with exception: {result}")
                continue
            if isinstance(result, list):
                error_report.extend(result)

        return "".join(error_report)
