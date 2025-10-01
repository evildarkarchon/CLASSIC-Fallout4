"""
Async file I/O integration for CLASSIC.

This module provides drop-in replacements for synchronous file operations
using async I/O for improved performance.
"""

import asyncio
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.Logger import logger
from ClassicLib.ScanLog.AsyncReformat import crashlogs_reformat_async

try:
    from ClassicLib.ScanLog.AsyncUtil import write_file_async
except ImportError:
    # Fallback to basic aiofiles for write operations
    import aiofiles

    async def write_file_async(file_path: Path, content: str) -> None:
        """
        Writes the provided content to a file asynchronously.

        This function opens the specified file asynchronously in write mode,
        writes the provided content to it, and ensures the operation is done
        without blocking the main thread.

        Args:
            file_path (Path): The path to the file where the content should be written.
            content (str): The content to write into the specified file.
        """
        async with aiofiles.open(file_path, mode="w", encoding="utf-8", errors="ignore") as f:
            await f.write(content)


async def load_crash_logs_async_optimized(crashlog_list: list[Path]) -> dict[str, bytes]:
    """
    Asynchronously loads crash logs from provided file paths and converts them to a dictionary of
    file names to their contents in bytes format. Attempts to use optimized external libraries for
    loading when available, with a fallback to basic asynchronous file reading.

    Args:
        crashlog_list (list[Path]): A list of file paths to crash logs that need to be loaded.

    Returns:
        dict[str, bytes]: A dictionary mapping file names to their corresponding contents
        encoded as UTF-8 bytes.
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
    A decorator function for timing asynchronous operations and logging their duration.

    This decorator records the time taken by an asynchronous function to execute and logs the
    duration using the specified operation name. It is useful for monitoring the performance of
    async routines.

    Args:
        operation_name: str. A string specifying the name of the operation being timed.

    Returns:
        Callable. A decorator function that wraps the target asynchronous function, logs
        its execution time, and returns the result.
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
    Asynchronously reformats crash logs and removes specified entries.

    This function is a timed operation that utilizes the `time_async_operation`
    decorator. It takes a list of crash log file paths and a list of entries to
    remove, then processes the logs accordingly. The reformatting and removal are
    handled by the `crashlogs_reformat_async` helper function.

    Args:
        crashlog_list (list[Path]): A list of Path objects representing the
            locations of the crash log files to be processed.
        remove_list (tuple[str]): A tuple of string entries specifying which parts
            of the crash logs should be removed during reformatting.

    """
    await crashlogs_reformat_async(crashlog_list, remove_list)


@time_async_operation("Crash log loading")
async def timed_load_async(crashlog_list: list[Path]) -> dict[str, bytes]:
    """
    Asynchronously loads crash logs from the given list of file paths, timed with
    a decorator for performance measurement.

    This function utilizes an optimized crash log loading mechanism to read and
    process crash logs asynchronously, returning a dictionary where keys are
    file names and values are their corresponding file contents in bytes.

    Args:
        crashlog_list (list[Path]): A list of file paths pointing to crash log
            files to be loaded asynchronously.

    Returns:
        dict[str, bytes]: A dictionary mapping file names (str) to file contents
            (bytes) of the crash logs.

    Raises:
        Any exceptions raised during the file loading process are propagated by
        this function.
    """
    return await load_crash_logs_async_optimized(crashlog_list)


async def write_report_async(crashlog_file: Path, autoscan_report: list[str]) -> None:
    """
    Writes a report asynchronously by combining provided log contents into a formatted
    output file and storing it on disk. The method generates the filename based on
    the input crash log file and specifies the file content using the autoscan
    report details.

    Args:
        crashlog_file (Path): Path to the crash log file which is used to derive the
            report's filename.
        autoscan_report (list[str]): List of strings containing the autoscan report
            content that will be written to the output.
    """
    autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
    autoscan_output: str = "".join(autoscan_report)
    await write_file_async(autoscan_path, autoscan_output)
    logger.debug(f"Wrote async report for {crashlog_file.name}")


async def write_reports_batch(reports: list[tuple[Path, list[str], bool]]) -> None:
    """
    Writes a batch of reports asynchronously to the filesystem.

    This function receives a list of reports, where each report is a tuple
    containing the path to the crashlog file, the autoscan report content,
    and a boolean. It processes these reports asynchronously using
    FileIOCore for efficient I/O operations. The processed reports are
    written to new files named based on the original crashlog filenames.

    Args:
        reports (list[tuple[Path, list[str], bool]]): A list of tuples, where
            each tuple contains:
            - crashlog_file (Path): The path to the original crashlog file.
            - autoscan_report (list[str]): The content of the report as a list
              of strings.
            - a boolean value that is ignored in the processing.
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


def run_performance_test(crashlog_list: list[Path], remove_list: tuple[str]) -> None:
    """
    Runs a performance test comparing synchronous and asynchronous reformatting
    of crash log files. The method measures the time taken for both methods and
    reports the performance comparison including speedup and improvement.

    Args:
        crashlog_list (list[Path]): A list of paths to crash log files intended
            for performance testing. A maximum of 10 files will be used to limit
            test duration.
        remove_list (tuple[str]): Tuple containing keys or elements to identify
            and remove specific entries from the crash logs during reformatting.

    """
    import shutil
    import tempfile
    import time

    # Create temporary copies for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_files = []

        # Copy a subset of files for testing (max 10 to avoid long test times)
        test_count: int = min(len(crashlog_list), 10)
        for i, original_file in enumerate(crashlog_list[:test_count]):
            if original_file.exists():
                test_file = temp_path / f"test_{i}_{original_file.name}"
                shutil.copy2(original_file, test_file)
                test_files.append(test_file)

        if not test_files:
            logger.warning("No crash log files found for performance testing")
            return

        logger.info(f"Performance test with {len(test_files)} files")

        # Test sync version (using original logic)
        sync_start: float = time.perf_counter()
        from ClassicLib.ScanLog.Util import crashlogs_reformat

        crashlogs_reformat(test_files, remove_list)
        sync_time: float = time.perf_counter() - sync_start

        # Test async version
        async_start: float = time.perf_counter()
        bridge = AsyncBridge.get_instance()
        bridge.run_async(timed_reformat_async(test_files, remove_list))
        async_time: float = time.perf_counter() - async_start

        # Results
        logger.info(f"Sync reformatting: {sync_time:.3f} seconds")
        logger.info(f"Async reformatting: {async_time:.3f} seconds")

        if async_time > 0:
            speedup: float = sync_time / async_time
            improvement: float = ((sync_time - async_time) / sync_time) * 100
            logger.info(f"Speedup: {speedup:.2f}x ({improvement:.1f}% faster)")
        else:
            logger.info("Async operation was too fast to measure accurately")
