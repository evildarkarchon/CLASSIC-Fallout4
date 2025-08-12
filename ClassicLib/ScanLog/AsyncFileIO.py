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
        async with aiofiles.open(file_path, mode="w", encoding="utf-8", errors="ignore") as f:
            await f.write(content)


def crashlogs_reformat_with_async(crashlog_list: list[Path], remove_list: tuple[str]) -> None:
    """
    DEPRECATED: Use crashlogs_reformat_async directly or through FileIOCore.

    Drop-in replacement for crashlogs_reformat that uses async I/O.

    This function can be used as a direct replacement for the synchronous
    crashlogs_reformat function to get the performance benefits of async I/O.

    Args:
        crashlog_list: List of crash log file paths to reformat
        remove_list: Tuple of strings to remove from logs if simplification is enabled
    """
    import warnings

    warnings.warn("crashlogs_reformat_with_async is deprecated. Use crashlogs_reformat_async directly.", DeprecationWarning, stacklevel=2)
    logger.debug("- - - INITIATED ASYNC CRASH LOG FILE REFORMAT")

    # Run the async function using asyncio.run
    asyncio.run(crashlogs_reformat_async(crashlog_list, remove_list))

    logger.debug("- - - COMPLETED ASYNC CRASH LOG FILE REFORMAT")


async def load_crash_logs_async_optimized(crashlog_list: list[Path]) -> dict[str, bytes]:
    """
    Optimized async loading of crash logs with batching and progress tracking.

    This function loads crash logs concurrently in batches to avoid overwhelming
    the file system while providing maximum performance improvement.

    Args:
        crashlog_list: List of crash log file paths

    Returns:
        Dictionary mapping log names to their content as bytes
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

    # Convert to bytes format to match ThreadSafeLogCache expectations
    # Strip any trailing newlines from lines before joining to avoid double newlines
    bytes_cache: dict[str, bytes] = {
        name: "\n".join(line.rstrip("\n\r") for line in lines).encode("utf-8") for name, lines in cache_dict.items()
    }

    logger.debug(f"Completed async load of {len(bytes_cache)} crash logs")
    return bytes_cache


def integrate_async_file_loading(crashlog_list: list[Path]) -> dict[str, bytes]:
    """
    DEPRECATED: Use FileIOCore.read_multiple_files() instead.

    Drop-in replacement for synchronous crash log loading.

    This can replace the file loading in ThreadSafeLogCache.__init__
    to use async I/O for better performance.

    Args:
        crashlog_list: List of crash log file paths

    Returns:
        Dictionary suitable for ThreadSafeLogCache.cache
    """
    import warnings

    warnings.warn(
        "integrate_async_file_loading is deprecated. Use FileIOCore.read_multiple_files() instead.", DeprecationWarning, stacklevel=2
    )
    return asyncio.run(load_crash_logs_async_optimized(crashlog_list))


def time_async_operation(operation_name: str) -> Callable:
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
    """Timed version of async reformatting for performance monitoring."""
    await crashlogs_reformat_async(crashlog_list, remove_list)


@time_async_operation("Crash log loading")
async def timed_load_async(crashlog_list: list[Path]) -> dict[str, bytes]:
    """Timed version of async loading for performance monitoring."""
    return await load_crash_logs_async_optimized(crashlog_list)


async def write_report_async(crashlog_file: Path, autoscan_report: list[str]) -> None:
    """
    Asynchronously write a crash log report to file.

    Args:
        crashlog_file: Path to the crash log file
        autoscan_report: Generated report lines
    """
    autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
    autoscan_output: str = "".join(autoscan_report)
    await write_file_async(autoscan_path, autoscan_output)
    logger.debug(f"Wrote async report for {crashlog_file.name}")


def write_report_with_async(crashlog_file: Path, autoscan_report: list[str]) -> None:
    """
    DEPRECATED: Use write_report_async directly or FileIOCore.write_crash_report().

    Drop-in replacement for synchronous report writing using async I/O.

    Args:
        crashlog_file: Path to the crash log file
        autoscan_report: Generated report lines
    """
    import warnings

    warnings.warn("write_report_with_async is deprecated. Use write_report_async directly or FileIOCore.", DeprecationWarning, stacklevel=2)
    asyncio.run(write_report_async(crashlog_file, autoscan_report))


async def write_reports_batch(reports: list[tuple[Path, list[str], bool]]) -> None:
    """
    Write multiple reports concurrently for maximum performance.

    NOTE: Consider using FileIOCore.write_multiple_files() for new code.

    Args:
        reports: List of (crashlog_file, autoscan_report, trigger_scan_failed) tuples
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
    Run a performance comparison between sync and async file operations.

    This function can be used to measure the actual performance improvement
    on your specific crash log files.

    Args:
        crashlog_list: List of crash log file paths
        remove_list: Tuple of strings for reformatting
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
        asyncio.run(timed_reformat_async(test_files, remove_list))
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
