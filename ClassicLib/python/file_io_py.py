"""
Pure Python implementation of file I/O operations.

This module provides the fallback Python implementation for file I/O operations
when the Rust acceleration is not available. It maintains full compatibility
with the FileIOCore API while using standard Python libraries.
"""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiofiles

try:
    import aiofiles

    AIOFILES_AVAILABLE = True
except ImportError:
    aiofiles = None  # type: ignore[assignment]
    AIOFILES_AVAILABLE = False

import logging
from itertools import starmap

logger = logging.getLogger(__name__)


class PythonFileIO:
    """
    Pure Python implementation of file I/O operations.

    This class provides async-first file operations using standard Python
    libraries and aiofiles when available. It serves as the fallback
    implementation when Rust acceleration is not available.
    """

    def __init__(self, encoding: str = "utf-8", errors: str = "ignore") -> None:
        """
        Initialize PythonFileIO with default encoding settings.

        Args:
            encoding: Default encoding for file operations
            errors: Error handling strategy for encoding errors
        """
        self.default_encoding = encoding
        self.default_errors = errors

    @staticmethod
    def _ensure_path(path: Path | str) -> Path:
        """
        Ensures that the given input is converted to a `Path` object. This utility method checks the
        type of the provided input and converts it to a `Path` object if it is not already one. It is
        useful for handling inputs that can either be file paths in string format or `Path` objects.

        Args:
            path (Path | str): The input path, which can either be a string representing the file
                path or a `Path` object.

        Returns:
            Path: The input path converted to a `Path` object.
        """
        if isinstance(path, str):
            return Path(path)
        return path

    async def read_file(self, path: Path | str) -> str:
        """
        Reads the contents of a file asynchronously and returns it as a string.

        This method ensures the given path is valid and attempts to read the file,
        with proper encoding detection if available. If async file handling is not
        available, it falls back to reading the file synchronously in an executor.

        Args:
            path (Path | str): The file path to read. Can be either a Path object
                or a string representing the file path.

        Returns:
            str: The content of the file.

        Raises:
            ValueError: If the given path is invalid.
            ImportError: If the async encoding detection library cannot be imported.
        """
        path = self._ensure_path(path)

        # Try to use async encoding detection if available
        try:
            from ClassicLib.AsyncUtil import read_file_with_encoding_async

            return await read_file_with_encoding_async(path)
        except ImportError:
            pass

        if AIOFILES_AVAILABLE:
            assert aiofiles is not None
            async with aiofiles.open(path, encoding=self.default_encoding, errors=self.default_errors) as f:
                return await f.read()
        else:
            # Fallback to sync read in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, path.read_text, self.default_encoding, self.default_errors)

    async def read_lines(self, path: Path | str) -> list[str]:
        """
        Reads the lines of a file and returns them as a list of strings.

        This asynchronous method reads the content of a file at the specified path and
        splits its content into individual lines.

        Args:
            path (Path | str): The path to the file to be read. It can be provided as
                a `Path` object or a string.

        Returns:
            list[str]: A list of strings, where each string represents a line from
                the file.
        """
        content = await self.read_file(path)
        return content.splitlines()

    async def read_bytes(self, path: Path | str) -> bytes:
        """
        Reads and returns the content of a file as bytes asynchronously.

        This method works with both `Path` and string representations of paths.
        If `aiofiles` is available, it utilizes asynchronous file I/O for better
        performance. If `aiofiles` is not available, it falls back to running the
        operation in the default event loop executor.

        Args:
            path (Path | str): The path to the file to be read. Can be a Path object
                or a string representing the file path.

        Returns:
            bytes: The content of the file in bytes format.

        Raises:
            AssertionError: If `aiofiles` is not available but is attempted to be
                used.
        """
        path = self._ensure_path(path)

        if AIOFILES_AVAILABLE:
            assert aiofiles is not None
            async with aiofiles.open(path, mode="rb") as f:
                return await f.read()
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, path.read_bytes)

    async def write_file(self, path: Path | str, content: str) -> None:
        """
        Writes the given content to the specified file asynchronously. Ensures that
        the parent directories for the file path exist before writing. Uses aiofiles
        if available for asynchronous I/O, otherwise falls back to running the
        file writing operation in an executor.

        Args:
            path: The file path where the content should be written. It can be either
                a Path object or a string.
            content: The content to write into the file.
        """
        path = self._ensure_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if AIOFILES_AVAILABLE:
            assert aiofiles is not None
            async with aiofiles.open(path, mode="w", encoding=self.default_encoding, errors=self.default_errors) as f:
                await f.write(content)
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, path.write_text, content, self.default_encoding, self.default_errors)

    async def write_lines(self, path: Path | str, lines: list[str]) -> None:
        """
        Writes a list of strings to a file asynchronously.

        This method takes a list of strings and writes them to the specified file
        path. Each string in the list is joined by a newline character. If the
        content does not already end with a newline, one is appended before the
        file is written. The method is asynchronous and supports both "Path" or
        string types for the file path.

        Args:
            path: Path or string specifying the file location to write the content.
            lines: List of strings, where each string represents a line of content
                to write into the file.

        """
        content = "\n".join(lines)
        if not content.endswith("\n"):
            content += "\n"
        await self.write_file(path, content)

    async def write_bytes(self, path: Path | str, content: bytes) -> None:
        """
        Writes a byte content to the specified file path asynchronously. Ensures that parent directories
        exist before writing. If `aiofiles` is available, it uses asynchronous file operations to write
        the bytes. Otherwise, it falls back to using a thread executor for writing.

        Args:
            path (Path | str): The path to the file where the bytes will be written. Can be provided
                as a string or Path object.
            content (bytes): The byte content to be written to the file.

        Raises:
            AssertionError: If attempting to use `aiofiles` but it is not properly imported or available.
        """
        path = self._ensure_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if AIOFILES_AVAILABLE:
            assert aiofiles is not None
            async with aiofiles.open(path, mode="wb") as f:
                await f.write(content)
        else:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, path.write_bytes, content)

    async def append_file(self, path: Path | str, content: str) -> None:
        """
        Appends content to a file asynchronously. If the file does not exist, it creates
        the file and writes the content to it. If the directory structure for the given
        file path does not exist, it is created automatically. The operation is
        performed asynchronously using aiofiles if available, otherwise it falls back
        to a synchronous operation executed in a thread via an event loop executor.

        Args:
            path (Path | str): Path to the file where the content should be appended. This
                can be provided as either a `Path` object or a string.
            content (str): The content to append to the file.

        """
        path = self._ensure_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if AIOFILES_AVAILABLE:
            assert aiofiles is not None
            async with aiofiles.open(path, mode="a", encoding=self.default_encoding, errors=self.default_errors) as f:
                await f.write(content)
        else:
            loop = asyncio.get_event_loop()

            def append_sync() -> None:
                with path.open("a", encoding=self.default_encoding, errors=self.default_errors) as f:
                    f.write(content)

            await loop.run_in_executor(None, append_sync)

    async def read_crash_log(self, path: Path | str) -> list[str]:
        """
        Reads and processes a crash log file provided by its path. This method retrieves the
        content of the file asynchronously by reading all lines, ensures any trailing empty
        lines are removed, and returns the processed content as a list of strings.

        Args:
            path (Path | str): The file path to the crash log, which can be a string or a
                Path object.

        Returns:
            list[str]: A list of strings where each string represents a line of the processed
                crash log.

        Raises:
            Any exception related to file I/O or async operations encountered during reading
            the file can be propagated.
        """
        lines = await self.read_lines(path)
        # Strip any trailing empty lines for consistency
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    async def write_crash_report(self, path: Path | str, report_lines: list[str]) -> None:
        """
        Writes a crash report to a specified file.

        This method asynchronously creates a markdown file at the specified path and
        writes the provided report lines into it. The provided lines are assumed to
        already include appropriate newlines. After successfully writing the file,
        a log message is generated to indicate the location of the written report.

        Args:
            path (Path | str): The path where the crash report will be saved. It can be
                either a Path object or a string representing the path.
            report_lines (list[str]): A list of strings representing the lines of the
                crash report. Each line should already include the necessary newline
                character.
        """
        path = self._ensure_path(path)
        report_path = path.with_suffix(".md")
        content = "".join(report_lines)  # Assume lines already have newlines
        await self.write_file(report_path, content)
        logger.info(f"Report written to: {report_path}")

    async def read_multiple_files(self, paths: list[Path | str]) -> dict[str, str]:
        """
        Reads multiple files asynchronously and returns their contents in a dictionary.

        This function reads the contents of multiple files specified by their paths
        and returns a dictionary where the keys are the file names (as strings) and
        the values are the file contents (as strings). It uses asynchronous operations
        to simultaneously read files, improving performance for I/O-bound tasks.

        Args:
            paths (list[Path | str]): A list of file paths to be read. Each path can
                be either a `Path` object or a string representing the file's path.

        Returns:
            dict[str, str]: A dictionary containing file names as keys and their
            respective contents as values. If there is an error reading a file,
            its value in the dictionary will be an empty string.

        Raises:
            Exception: If an error occurs while reading a specific file, it is logged,
            and its content will be set to an empty string, but no exception is
            propagated to the caller.
        """

        async def read_single(path: Path | str) -> tuple[str, str]:
            """
            Reads the content of a single file asynchronously.

            This method attempts to read the content of the file at the specified
            path. If an error occurs during the file reading process, it logs the
            error and returns the name of the file along with an empty string as
            its content.

            Args:
                path: The path to the file. Can be a `Path` object or a string
                    representing the file path.

            Returns:
                tuple[str, str]: A tuple where the first element is the name of
                the file, and the second element is the content of the file. If
                an error occurs, the first element is the name of the file, and
                the second element is an empty string.
            """
            path = self._ensure_path(path)
            try:
                content = await self.read_file(path)
            except Exception as e:
                logger.error(f"Error reading {path}: {e}")
                return path.name, ""
            else:
                return path.name, content

        tasks = [read_single(path) for path in paths]
        results = await asyncio.gather(*tasks)
        return dict(results)

    async def write_multiple_files(self, files: dict[Path | str, str]) -> None:
        """
        Writes multiple files asynchronously by delegating to a helper function that performs individual file writes.

        This function takes in a dictionary where keys represent file paths and values represent the corresponding content to be written to the files. It efficiently writes all files concurrently, utilizing asynchronous tasks.

        Args:
            files (dict[Path | str, str]): A dictionary mapping file paths (as Path or string) to their respective content (as string) to be written.

        Raises:
            Exception: Logged if any error occurs during the writing process.
        """

        async def write_single(path: Path | str, content: str) -> None:
            """
            Writes content to a specified file asynchronously. If there is an error during the write
            operation, it is logged.

            Args:
                path (Path | str): The path of the file to write to.
                content (str): The content to be written to the file.
            """
            try:
                await self.write_file(path, content)
            except Exception as e:
                logger.error(f"Error writing {path}: {e}")

        tasks = list(starmap(write_single, files.items()))
        await asyncio.gather(*tasks)

    def file_exists(self, path: Path | str) -> bool:
        """
        Checks if the given file path exists.

        This method verifies the existence of a file or a directory at the specified
        path. It handles both string-based file paths and `Path` objects.

        Args:
            path: The file or directory path to check. It can be provided either as a
                string or a `Path` object.

        Returns:
            bool: True if the path exists; otherwise, False.
        """
        path = self._ensure_path(path)
        return path.exists()

    def get_file_size(self, path: Path | str) -> int:
        """
        Returns the size of a given file in bytes. If the file does not exist or an
        error occurs while accessing it, the method returns -1.

        Args:
            path: The path to the file, which can be specified as a Path object or
                a string.

        Returns:
            int: The size of the file in bytes, or -1 if the file does not exist or
                an error occurs.
        """
        path = self._ensure_path(path)
        try:
            return path.stat().st_size
        except (OSError, FileNotFoundError):
            return -1


# Alias for compatibility
FileIOCore = PythonFileIO
