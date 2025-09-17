"""
Provides asynchronous utilities for handling log file reformatting, crash log
processing, file movement, and file copying operations.

This module includes asynchronous functions designed to efficiently handle
file operations such as reformatting logs, processing crash log files in
batches, and performing file move and copy operations concurrently. These
functions are optimized to limit blocking I/O using asyncio and thread pools to
ensure robust and efficient file system operations.
"""

import asyncio
from itertools import starmap
from pathlib import Path

import aiofiles

from ClassicLib.Logger import logger
from ClassicLib.YamlSettingsCache import classic_settings


async def reformat_single_log_async(file_path: Path, remove_list: tuple[str], simplify_logs: bool) -> None:
    """
    Reformats a single log file asynchronously with specified adjustments.

    This function reads the log file, applies formatting rules, removes unwanted
    lines, simplifies logs if specified, and rewrites the file with the modified
    content. The function is designed to handle specific sections like the
    PLUGINS section differently and adjust or retain line content based on the
    provided parameters.

    Args:
        file_path (Path): Path to the log file to be reformatted.
        remove_list (tuple[str]): Tuple of strings; lines containing any of these
            strings will be removed if `simplify_logs` is enabled.
        simplify_logs (bool): Whether to simplify logs by removing matching lines
            from the `remove_list`.

    Raises:
        OSError: If an error occurs while reading or writing the file.
    """
    try:
        # Read file asynchronously
        async with aiofiles.open(file_path, encoding="utf-8", errors="ignore") as f:
            original_lines = await f.readlines()

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

        # Write back asynchronously
        async with aiofiles.open(file_path, mode="w", encoding="utf-8", errors="ignore") as f:
            await f.writelines(final_processed_lines)

        logger.debug(f"Reformatted {file_path.name}")

    except OSError as e:
        logger.error(f"Error reformatting {file_path}: {e}")


async def crashlogs_reformat_async(crashlog_list: list[Path], remove_list: tuple[str]) -> None:
    """
    Reformats crash log files asynchronously by processing them in manageable batches
    to prevent overwhelming the file system. Each log file is reformatted with specific
    processing that involves removing specified log entries and optionally simplifying
    log content.

    Args:
        crashlog_list (list[Path]): A list containing file paths of crash log files
            to be reformatted.
        remove_list (tuple[str]): A tuple containing substrings or patterns that
            should be removed from the logs.
    """
    logger.debug("- - - INITIATED ASYNC CRASH LOG FILE REFORMAT")
    simplify_logs: bool = bool(classic_settings(bool, "Simplify Logs"))

    # Process in batches to avoid overwhelming the file system
    batch_size = 20

    for i in range(0, len(crashlog_list), batch_size):
        batch = crashlog_list[i : i + batch_size]

        # Create tasks for the batch
        tasks = [reformat_single_log_async(file_path, remove_list, simplify_logs) for file_path in batch]

        # Process batch concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        # Small delay between batches to avoid file system overload
        if i + batch_size < len(crashlog_list):
            await asyncio.sleep(0.1)

    logger.debug("- - - COMPLETED ASYNC CRASH LOG FILE REFORMAT")


async def batch_file_move_async(operations: list[tuple[Path, Path]]) -> None:
    """
    Moves multiple files asynchronously to their specified destinations. Each file
    move operation is executed concurrently using asyncio.

    Args:
        operations (list[tuple[Path, Path]]): A list of tuples, where each tuple
            contains the source (Path) and destination (Path) for a file to be
            moved.

    Raises:
        OSError: Raised if there is an issue with renaming (moving) a file, such as
            permission errors or non-existent paths. Errors for individual files
            are logged.
    """

    async def move_file(src: Path, dst: Path) -> None:
        """
        Moves a file from the source path to the destination path asynchronously. This
        operation renames the file in the file system and logs the action. In case of
        an error, logs the error message.

        Args:
            src (Path): The source file path to move.
            dst (Path): The destination file path where the file should be moved.

        Raises:
            OSError: If there is an issue with moving the file, such as
                permission errors or invalid paths.
        """
        try:
            await asyncio.to_thread(src.rename, dst)
            logger.debug(f"Moved {src.name} to {dst}")
        except OSError as e:
            logger.error(f"Error moving {src} to {dst}: {e}")

    # Execute all moves concurrently
    tasks = list(starmap(move_file, operations))
    await asyncio.gather(*tasks, return_exceptions=True)


async def batch_file_copy_async(operations: list[tuple[Path, Path]]) -> None:
    """
    Executes batch file copy operations concurrently using asynchronous tasks.

    This function uses asynchronous threading to perform file copy operations,
    executing multiple copy tasks concurrently. It leverages asyncio.gather to
    manage and execute tasks with error handling for each file copy operation.

    Args:
        operations (list[tuple[Path, Path]]): A list of tuples where each tuple
            contains the source path and destination path for the file copy
            operation.
    """
    import shutil

    async def copy_file(src: Path, dst: Path) -> None:
        """
        Asynchronously copies a file from the source path to the destination path.

        This function uses `shutil.copy2` to copy the file, preserving metadata. The
        copy operation is performed in a background thread to avoid blocking the
        event loop. Logs a debug message on successful copy and an error message if
        an exception occurs during the process.

        Args:
            src (Path): The source file path.
            dst (Path): The destination file path.

        Raises:
            OSError: If an OS-level error occurs during the copy.
            shutil.Error: If an error specific to the `shutil` library occurs.
        """
        try:
            await asyncio.to_thread(shutil.copy2, src, dst)
            logger.debug(f"Copied {src.name} to {dst}")
        except (OSError, shutil.Error) as e:
            logger.error(f"Error copying {src} to {dst}: {e}")

    # Execute all copies concurrently
    tasks = list(starmap(copy_file, operations))
    await asyncio.gather(*tasks, return_exceptions=True)
