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
from ClassicLib.ScanGame.core.utils import ASYNC_ENCODING_AVAILABLE, read_lines_with_encoding_async
from ClassicLib.Utils.file_utils import open_file_with_encoding
from ClassicLib.Utils.string_utils import normalize_list
from ClassicLib.YamlSettings import yaml_settings_async  # pyright: ignore[reportAttributeAccessIssue]


class LogProcessor:
    """Class for processing log files and detecting errors.

    Handles concurrent reading and analysis of log files located in a specified folder.
    The class ensures efficient processing with the use of concurrency controls like semaphores.
    It filters logs based on customizable inclusion and exclusion rules and generates detailed
    error reports for identified issues.

    Attributes:
        log_read_semaphore (asyncio.Semaphore): Semaphore used to control concurrency when
            processing log files asynchronously.

    """

    def __init__(self, log_read_semaphore: asyncio.Semaphore) -> None:
        """Initialize an instance of the class with the provided log semaphore.

        The constructor takes an asyncio semaphore object to control the
        simultaneous execution of log-reading operations.

        Args:
            log_read_semaphore (asyncio.Semaphore): Semaphore that regulates access
                to log-reading operations based on its permits.

        """
        self.log_read_semaphore = log_read_semaphore

    async def check_log_errors(self, folder_path: Path | str) -> str:
        """Check for errors in log files within the specified folder path and returns a detailed
        error report. This function scans log files for specific error patterns as defined in
        the YAML configuration and allows for the exclusion of certain files and error types.

        Args:
            folder_path (Path | str): The folder path to scan for log files. Can be provided
                as a `Path` object or a string.

        Returns:
            str: A detailed error report containing information about detected errors in the
                log files.

        """

        def format_error_report(file_path: Path, errors: list[str], total_count: int) -> list[str]:
            """Format an error report for a given file path and list of error messages.

            This function generates a formatted error report that includes a warning message,
            the file path of the log, the list of error messages, and a summary of the total
            number of detected errors. If errors were truncated, shows a notice.

            Args:
                file_path (Path): The path to the log file associated with the errors.
                errors (list[str]): A list of error messages (limited to last 50).
                total_count (int): Total number of errors found before truncation.

            Returns:
                list[str]: A list of strings containing the formatted error report.

            """
            report = [
                "[!] CAUTION : THE FOLLOWING LOG FILE REPORTS ONE OR MORE ERRORS!\n",
                "[ Errors do not necessarily mean that the mod is not working. ]\n",
                f"\nLOG PATH > {file_path}\n",
            ]

            # Show truncation notice if errors were limited
            if total_count > len(errors):
                report.append(f"[ Showing last {len(errors)} of {total_count} total errors ]\n\n")
            else:
                report.append("\n")

            report.extend(errors)
            report.append(f"\n* TOTAL NUMBER OF DETECTED LOG ERRORS * : {total_count}\n")

            return report

        # Convert string path to Path object if needed
        if isinstance(folder_path, str):
            folder_path = Path(folder_path)

        # Get YAML settings and convert to sets for faster lookups
        catch_errors_set: set[str] = set(normalize_list(await yaml_settings_async(list[str], YAML.Main, "catch_log_errors") or []))
        ignore_files_set: set[str] = set(normalize_list(await yaml_settings_async(list[str], YAML.Main, "exclude_log_files") or []))
        ignore_errors_set: set[str] = set(normalize_list(await yaml_settings_async(list[str], YAML.Main, "exclude_log_errors") or []))

        # Find valid log files (excluding crash logs)
        valid_log_files: list[Path] = [
            file
            for file in folder_path.glob("*.log")
            if "crash-" not in file.name.lower() and not any(part in str(file).lower() for part in ignore_files_set)
        ]

        async def process_single_log(log_file_path: Path) -> list[str]:
            """Process a single log file to detect and filter specific error messages.

            This asynchronous function reads a log file, identifies error lines based on
            specified criteria, and formats those errors for further processing. Different
            methods of reading the file are employed depending on the availability of
            async libraries.

            Args:
                log_file_path (Path): Path to the log file to be processed.

            Returns:
                list[str]: A list containing formatted error messages detected from
                    the log file. If no errors are detected, an empty list is returned.
                    If the file cannot be read, a list with a single error message is
                    returned.

            """
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
                        loop = asyncio.get_running_loop()
                        with open_file_with_encoding(log_file_path) as log_file:
                            log_lines = await loop.run_in_executor(None, log_file.readlines)

                    # Filter for relevant errors
                    detected_errors = [
                        f"ERROR > {line}"
                        for line in log_lines
                        if any(error in line.lower() for error in catch_errors_set)
                        and all(ignore not in line.lower() for ignore in ignore_errors_set)
                    ]

                    # Keep track of total count before truncation
                    total_errors = len(detected_errors)

                    # Limit to last 50 errors (tail -50)
                    if total_errors > 50:
                        detected_errors = detected_errors[-50:]

                except OSError:
                    error_message = f"❌ ERROR : Unable to scan this log file :\n  {log_file_path}"
                    logger.warning(f"> ! > DETECT LOG ERRORS > UNABLE TO SCAN : {log_file_path}")
                    return [error_message]
                else:
                    if detected_errors:
                        return format_error_report(log_file_path, detected_errors, total_errors)
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
