"""
Async crash log reformatting module.

This module provides async versions of crash log reformatting operations
for improved performance through concurrent file I/O.
"""

import asyncio
from pathlib import Path

import aiofiles

from ClassicLib.Logger import logger
from ClassicLib.YamlSettingsCache import classic_settings


async def reformat_single_log_async(file_path: Path, remove_list: tuple[str], simplify_logs: bool) -> None:
    """
    Reformats a single log file asynchronously based on the given parameters. It processes the log file by removing unwanted lines, maintaining consistency in formatting, especially within specific sections, and rewriting the content back to the file.

    Args:
        file_path (Path): The path to the log file to be reformatted.
        remove_list (tuple[str]): A tuple of strings to identify lines that should be removed, used when simplify_logs is enabled.
        simplify_logs (bool): Indicates whether to remove lines containing strings listed in remove_list, simplifying the log.

    Raises:
        Exception: If an error occurs during file processing (e.g., reading, writing, or reformatting).
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
    to avoid overwhelming the file system. Each crash log is reformatted by removing
    specified patterns and simplified if the respective setting is enabled.

    Parameters:
    crashlog_list (list[Path]): A list of file paths pointing to crash log files
        to be processed.
    remove_list (tuple[str]): A tuple of strings specifying patterns or substrings
        to be removed from the crash log files.

    Raises:
    None

    Returns:
    None
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
    Asynchronously performs batch file move operations.

    This function takes a list of file move operations, where each operation
    is represented as a tuple containing the source and destination paths. It
    executes all move operations concurrently, leveraging asynchronous execution
    to maximize efficiency. Individual move operations are performed using a thread
    pool to handle the blocking I/O operation of renaming files.

    Parameters:
    operations: list[tuple[Path, Path]]
        A list of tuples where each tuple contains the source file path as the
        first element and the destination file path as the second element.

    Returns:
    None
    """

    async def move_file(src: Path, dst: Path) -> None:
        """Move a single file using thread pool for blocking operation."""
        try:
            await asyncio.to_thread(src.rename, dst)
            logger.debug(f"Moved {src.name} to {dst}")
        except OSError as e:
            logger.error(f"Error moving {src} to {dst}: {e}")

    # Execute all moves concurrently
    tasks = [move_file(src, dst) for src, dst in operations]
    await asyncio.gather(*tasks, return_exceptions=True)


async def batch_file_copy_async(operations: list[tuple[Path, Path]]) -> None:
    """
    Perform batch asynchronous file copy operations.

    This function takes a list of file copy operations and performs them
    concurrently using asynchronous execution. Each individual file copy
    operation is processed through an asynchronous wrapper for non-blocking
    execution.

    Parameters:
        operations (list[tuple[Path, Path]]): A list of source and destination
                                              file paths as tuples. Each tuple
                                              contains a source file path
                                              (Path) and a destination file
                                              path (Path).

    Raises:
        Exceptions raised during file copy operations are logged but not
        propagated. This function ensures that all operations are attempted
        even if some of them fail.
    """
    import shutil

    async def copy_file(src: Path, dst: Path) -> None:
        """Copy a single file using thread pool for blocking operation."""
        try:
            await asyncio.to_thread(shutil.copy2, src, dst)
            logger.debug(f"Copied {src.name} to {dst}")
        except (OSError, shutil.Error) as e:
            logger.error(f"Error copying {src} to {dst}: {e}")

    # Execute all copies concurrently
    tasks = [copy_file(src, dst) for src, dst in operations]
    await asyncio.gather(*tasks, return_exceptions=True)
