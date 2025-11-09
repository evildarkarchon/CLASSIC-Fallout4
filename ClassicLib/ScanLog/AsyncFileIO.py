"""
Async file I/O integration for CLASSIC.

This module provides drop-in replacements for synchronous file operations
using async I/O for improved performance.
"""

import asyncio
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from ClassicLib.Logger import logger
from ClassicLib.ScanLog.AsyncReformat import crashlogs_reformat_async

try:
    from ClassicLib.ScanLog.AsyncUtil import write_file_async
except ImportError:
    # Fallback to basic aiofiles for write operations
    import aiofiles

    async def write_file_async(file_path: Path, content: str) -> None:
        """
        Writes content to a file asynchronously. The operation overwrites any existing
        content in the specified file. The file is created if it does not exist.

        Args:
            file_path: A `Path` object representing the file to write to.
            content: A string containing the content to be written to the file.

        Raises:
            OSError: If an error occurs while interacting with the file.
            TypeError: If the specified `file_path` is not a `Path` object or `content`
                is not a string.
        """
        async with aiofiles.open(file_path, mode="w", encoding="utf-8", errors="ignore") as f:
            await f.write(content)


async def load_crash_logs_async_optimized(crashlog_list: list[Path]) -> dict[str, bytes]:
    """
    Asynchronously loads and processes crash logs from the provided list of file paths.

    This function attempts to use an optimized asynchronous loading process by leveraging
    the `load_crash_logs_async` from `ClassicLib.ScanLog.AsyncUtil` if available. In the
    absence of the external utility, it falls back to a custom implementation using
    `aiofiles` for asynchronous file handling. All crash logs are processed into a
    consistent bytes format for compatibility across operations.

    Args:
        crashlog_list (list[Path]): A list of file paths pointing to crash log files.

    Returns:
        dict[str, bytes]: A dictionary containing crash log file names as keys and their
            contents as values in bytes format.
    """
    logger.debug(f"Starting async load of {len(crashlog_list)} crash logs")

    try:
        # noinspection PyUnresolvedReferences
        from ClassicLib.ScanLog.AsyncUtil import load_crash_logs_async

        # Load all logs concurrently and convert to bytes format for compatibility
        cache_dict = await load_crash_logs_async(crashlog_list)
    except ImportError:
        # Fallback implementation using basic aiofiles
        import aiofiles

        # noinspection PyUnusedImports
        async def load_single_log(file_path: Path) -> tuple[str, list[str]]:
            """
            Loads the content of a single log file asynchronously. Reads the file line by line
            into a list, with fallback to UTF-8 encoding if async encoding detection utility
            is not available. If an error occurs during reading, an empty list is returned
            for the content.

            Args:
                file_path (Path): Path to the log file to be read.

            Returns:
                tuple[str, list[str]]: A tuple where the first element is the name of the file,
                and the second element is a list of strings representing the lines of the file.

            Raises:
                Exception: This function handles unexpected errors during file reading internally,
                logs the error, and returns an empty list for the file content instead of propagating
                the exception.
            """
            try:
                # Try to use async encoding detection if available
                try:
                    from ClassicLib.AsyncUtil import read_file_with_encoding_async

                    content = await read_file_with_encoding_async(file_path)
                    return file_path.name, content.splitlines()
                except ImportError:
                    # Fallback to UTF-8
                    async with aiofiles.open(file_path, encoding="utf-8", errors="ignore") as f:
                        content = await f.read()
                        return file_path.name, content.splitlines()
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error reading {file_path}: {e}")
                return file_path.name, []

        tasks: list[Coroutine[Any, Any, tuple[str, list[str]]]] = [load_single_log(log_path) for log_path in crashlog_list]
        results: list[tuple[str, list[str]] | BaseException] = await asyncio.gather(*tasks, return_exceptions=True)

        cache_dict: dict = {}
        for result in results:
            if isinstance(result, tuple):
                name, lines = result
                cache_dict[name] = lines

    # Convert to bytes format for consistency with async operations
    # Strip any trailing newlines from lines before joining to avoid double newlines
    bytes_cache: dict[str, bytes] = {
        name: "\n".join(line.rstrip("\n\r") for line in lines).encode("utf-8") for name, lines in cache_dict.items()
    }

    logger.debug(f"Completed async load of {len(bytes_cache)} crash logs")
    return bytes_cache


def time_async_operation(operation_name: str) -> Callable:
    """
    Decorator to measure the execution time of an asynchronous operation and log the result.

    This decorator wraps an asynchronous function to calculate the time it takes for the
    function to complete execution. It logs the elapsed time with the provided operation
    name. It can be useful for monitoring performance or debugging purposes.

    Args:
        operation_name (str): The name of the operation being measured. This will be
            included in the log message.

    Returns:
        Callable: A decorator that, when applied to an asynchronous function, returns
            the enhanced version of that function wrapped with timing functionality.

    """

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        async def wrapper(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            import time

            start: float = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed: float = time.perf_counter() - start
            logger.info(f"{operation_name} completed in {elapsed:.3f} seconds")
            return result

        return wrapper

    return decorator


@time_async_operation("Crash log reformatting")
async def timed_reformat_async(crashlog_list: list[Path], remove_list: tuple[str]) -> None:
    """
    Reformats a list of crash logs asynchronously and removes specific log entries based
    on the provided list.

    This function wraps the asynchronous reformatting operation with a decorator to measure
    the execution time for the process. It processes the provided crash logs and filters out
    entries specified in the `remove_list`.

    Args:
        crashlog_list (list[Path]): A list of Path objects representing the crash log files
            that need to be reformatted.
        remove_list (tuple[str]): A tuple of strings specifying identifiers or patterns of
            log entries to be removed during the reformatting process.

    """
    await crashlogs_reformat_async(crashlog_list, remove_list)


@time_async_operation("Crash log loading")
async def timed_load_async(crashlog_list: list[Path]) -> dict[str, bytes]:
    """
    Asynchronously loads crash logs and returns a dictionary with the processed logs.

    This function measures the time taken to execute the asynchronous loading operation
    using a decorator. It processes a list of file paths that represent crash logs and
    returns them in the form of a dictionary, where the keys are the file paths (as strings)
    and the values are the corresponding file contents as bytes.

    Args:
        crashlog_list (list[Path]): A list of file paths pointing to crash logs.

    Returns:
        dict[str, bytes]: A dictionary where the keys are the string representations
        of file paths and the values are the crash log contents as bytes.
    """
    return await load_crash_logs_async_optimized(crashlog_list)


async def write_report_async(crashlog_file: Path, autoscan_report: list[str]) -> None:
    """
    Writes an asynchronous report by processing crash log data and generating a corresponding
    autoscan report. The output is saved into a markdown file with a specific naming convention.

    Args:
        crashlog_file (Path): The file path of the crash log that serves as the source for the
            report.
        autoscan_report (list[str]): A list of strings containing the lines of the autoscan
            report to be written.
    """
    autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
    autoscan_output: str = "".join(autoscan_report)
    await write_file_async(autoscan_path, autoscan_output)
    logger.debug(f"Wrote async report for {crashlog_file.name}")


async def write_reports_batch(reports: list[tuple[Path, list[str], bool]]) -> None:
    """
    Writes a batch of autoscan reports to files asynchronously.

    This function takes a batch of reports, writes them to respective .md files
    using efficient asynchronous file I/O, and ensures all tasks are completed. Each
    report is written to a file with a name derived from the corresponding crashlog
    file's name, appended with the suffix "-AUTOSCAN".

    Args:
        reports (list[tuple[Path, list[str], bool]]): A batch of reports to write,
            where each tuple consists of:
                - crashlog_file (Path): The path to the crashlog file.
                - autoscan_report (list[str]): The content of the autoscan report.
                - A boolean flag (bool) (unused).
    """
    # Use FileIOCore for better performance
    from ClassicLib.FileIOCore import FileIOCore

    io_core = FileIOCore()

    tasks: list[Coroutine[Any, Any, None]] = []
    for crashlog_file, autoscan_report, _ in reports:
        report_path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
        content = "".join(autoscan_report)
        tasks.append(io_core.write_file(report_path, content))

    await asyncio.gather(*tasks, return_exceptions=True)
    logger.debug(f"Wrote {len(reports)} reports using FileIOCore batch I/O")
