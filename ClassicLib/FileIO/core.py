"""
A module for asynchronous and synchronous file I/O operations with encoding handling.

This module provides the `FileIOCore` class, which enables convenient reading and
writing of files using async-first implementations. It supports automatic encoding
detection when dependencies are available, and offers fallback to synchronous
operations when asyncio-based tools are unavailable.
"""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # For type checking, always import the functions/modules
    import aiofiles

    from ClassicLib.AsyncUtil import (
        read_file_with_encoding_async,
    )

try:
    import aiofiles

    AIOFILES_AVAILABLE = True
except ImportError:
    aiofiles = None  # type: ignore[assignment]
    AIOFILES_AVAILABLE = False

from itertools import starmap

from ClassicLib.FileIO.path_utils import ensure_path
from ClassicLib.Logger import logger

# Import async utilities if available
try:
    from ClassicLib.AsyncUtil import (
        read_file_with_encoding_async,
    )

    ASYNC_ENCODING_AVAILABLE = True
except ImportError:
    ASYNC_ENCODING_AVAILABLE = False


class FileIOCore:
    """
    Handles asynchronous file input/output operations with options for reading,
    writing, and appending textual or binary data. Includes functionality for
    working with crash logs and encoding detection.

    This class provides a unified interface to handle file operations both
    asynchronously and with automatic encoding detection when available. It
    supports reading and writing operations for strings, lines, and bytes,
    and ensures compatibility with directories. Reliable crash log-specific
    methods are also included to manage such files effectively.

    Attributes:
        default_encoding (str): Default text encoding used for file reading and writing.
        default_errors (str): Error handling strategy for encoding-related errors.
    """

    def __init__(self, encoding: str = "utf-8", errors: str = "ignore") -> None:
        """
        Initializes the object with specified encoding and error handling.

        Args:
            encoding (str): The encoding to be used as the default. Defaults to "utf-8".
            errors (str): The error handling strategy for encoding/decoding errors.
                Defaults to "ignore".
        """
        self.default_encoding = encoding
        self.default_errors = errors

    @staticmethod
    def _ensure_path(path: Path | str) -> Path:
        """
        Ensures that the given path is of type `Path`. If the path is provided as a string,
        it will convert it to `Path` object and return it. This is mainly useful for
        standardizing input paths.

        Args:
            path: The path to be ensured, either as a `Path` object or a string.

        Returns:
            Path: A Path object corresponding to the given input.

        """
        return ensure_path(path)

    # ==========================================
    # Core Read Operations
    # ==========================================

    async def read_file(self, path: Path | str) -> str:
        """
        Reads the content of a file asynchronously using the most suitable method available.

        This function reads the content of a file specified by the `path` parameter. It attempts
        to use an asynchronous file reading approach if the required libraries or encoding detection
        tools are available. Otherwise, it falls back to reading the file synchronously in an
        asynchronous context.

        Args:
            path (Path | str): The path to the file to be read. It can either be a string or a pathlib.Path object.

        Returns:
            str: The content of the file as a string.
        """
        path = FileIOCore._ensure_path(path)

        # Use encoding detection if available
        if ASYNC_ENCODING_AVAILABLE:
            return await read_file_with_encoding_async(path)
        if AIOFILES_AVAILABLE:
            assert aiofiles is not None  # for type checker
            async with aiofiles.open(path, encoding=self.default_encoding, errors=self.default_errors) as f:
                return await f.read()
        else:
            # Fallback to sync read in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, path.read_text, self.default_encoding, self.default_errors)

    async def read_lines(self, path: Path | str) -> list[str]:
        """
        Reads the contents of a file line by line asynchronously.

        This method reads the file at the specified path and splits its contents into
        individual lines. Encoding detection, if available, is utilized to correctly
        read files. It falls back to synchronous reading where required.

        Args:
            path (Path | str): The path to the file to be read.

        Returns:
            list[str]: A list of strings where each string is a line from the file.
        """
        path = FileIOCore._ensure_path(path)

        # Use encoding detection if available
        if ASYNC_ENCODING_AVAILABLE:
            content = await read_file_with_encoding_async(path)
            return content.splitlines()
        if AIOFILES_AVAILABLE:
            assert aiofiles is not None  # for type checker
            async with aiofiles.open(path, encoding=self.default_encoding, errors=self.default_errors) as f:
                content = await f.read()
                return content.splitlines()
        else:
            # Fallback to sync read in executor
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, path.read_text, self.default_encoding, self.default_errors)
            return content.splitlines()

    async def read_bytes(self, path: Path | str) -> bytes:
        """
        Reads the contents of the file located at the specified path as bytes. This
        method uses asynchronous file handling if available, otherwise it falls
        back to synchronous file reading executed in an asynchronous executor.

        Args:
            path (Path | str): The path to the file to be read. Can be provided
                as a string or a Path object.

        Returns:
            bytes: The content of the file read as bytes.
        """
        path = FileIOCore._ensure_path(path)

        if AIOFILES_AVAILABLE:
            assert aiofiles is not None  # for type checker
            async with aiofiles.open(path, mode="rb") as f:
                return await f.read()
        else:
            # Fallback to sync read in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, path.read_bytes)

    # ==========================================
    # Core Write Operations
    # ==========================================

    async def write_file(self, path: Path | str, content: str) -> None:
        """
        Writes the provided content to the specified file path asynchronously.

        This method ensures the parent directory exists before attempting to write
        to the file. If the `aiofiles` module is available, it writes to the file
        asynchronously using aiofiles. Otherwise, it falls back to synchronous
        file writing executed in an executor.

        Args:
            path (Path | str): The path to the file where content will be written.
            content (str): The content to write to the file.
        """
        path = FileIOCore._ensure_path(path)

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        if AIOFILES_AVAILABLE:
            assert aiofiles is not None  # for type checker
            async with aiofiles.open(path, mode="w", encoding=self.default_encoding, errors=self.default_errors) as f:
                await f.write(content)
        else:
            # Fallback to sync write in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, path.write_text, content, self.default_encoding, self.default_errors)

    async def write_lines(self, path: Path | str, lines: list[str]) -> None:
        """
        Writes a list of lines to a file at the specified path.

        The lines are joined together into a single string using a newline character
        as a separator. If the resulting content does not end with a newline character,
        one will be appended. The content is then written to the file specified by the
        path.

        Args:
            path: Path or string indicating the file to write to.
            lines: List of strings representing the lines to write to the file.

        """
        content = "\n".join(lines)
        if not content.endswith("\n"):
            content += "\n"
        await self.write_file(path, content)

    async def write_bytes(self, path: Path | str, content: bytes) -> None:
        """
        Writes the given byte content to a specified file path, ensuring the parent
        directory exists. Supports both asynchronous and synchronous file operations
        depending on the availability of aiofiles module.

        Args:
            path (Path | str): The file path where the content should be written.
            content (bytes): The byte content to be written to the file.

        """
        path = FileIOCore._ensure_path(path)

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        if AIOFILES_AVAILABLE:
            assert aiofiles is not None  # for type checker
            async with aiofiles.open(path, mode="wb") as f:
                await f.write(content)
        else:
            # Fallback to sync write in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, path.write_bytes, content)

    async def append_file(self, path: Path | str, content: str) -> None:
        """
        Asynchronously appends content to a file at the specified path. If the file does not exist, it creates
        it along with its parent directories. Uses asynchronous file I/O if available, otherwise falls back
        to synchronous file writing executed in an executor.

        Args:
            path: The file path where the content should be appended. Can be a Path object or a string.
            content: The string content to append to the file.
        """
        path = FileIOCore._ensure_path(path)

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        if AIOFILES_AVAILABLE:
            assert aiofiles is not None  # for type checker
            async with aiofiles.open(path, mode="a", encoding=self.default_encoding, errors=self.default_errors) as f:
                await f.write(content)
        else:
            # Fallback to sync append in executor
            loop = asyncio.get_event_loop()

            def append_sync() -> None:
                with path.open("a", encoding=self.default_encoding, errors=self.default_errors) as f:
                    f.write(content)

            await loop.run_in_executor(None, append_sync)

    # ==========================================
    # Crash Log Specific Operations
    # ==========================================

    async def read_crash_log(self, path: Path | str) -> list[str]:
        """
        Reads the crash log from a specified file path asynchronously and returns a
        list of non-empty lines. Trailing empty lines are removed for consistency.

        Args:
            path (Path | str): The path to the crash log file to read.

        Returns:
            list[str]: A list of strings, each representing a line from the crash log
            file, excluding any trailing empty lines.
        """
        lines = await self.read_lines(path)
        # Strip any trailing empty lines for consistency
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    async def write_crash_report(self, path: Path | str, report_lines: list[str]) -> None:
        """
        Writes a crash report to a markdown file at the specified location.

        This method takes a file path and a list of report lines to write a crash report
        to a markdown file. The file path will be ensured and adjusted if needed, and
        the provided list of report lines will be concatenated into the file content.

        Args:
            path (Path | str): The desired file path for the crash report. The file
                extension will be automatically set to `.md`.
            report_lines (list[str]): A list of strings containing the lines to be
                written in the crash report. Each string in the list is expected to
                already include a newline character if necessary.
        """
        # Generate report file path
        path = FileIOCore._ensure_path(path)

        report_path = path.with_suffix(".md")
        content = "".join(report_lines)  # Assume lines already have newlines

        await self.write_file(report_path, content)
        logger.info(f"Report written to: {report_path}")

    # ==========================================
    # Batch Operations
    # ==========================================

    async def read_multiple_files(self, paths: list[Path | str]) -> dict[str, str]:
        """
        Reads the content of multiple files concurrently and returns their data.

        This method accepts a list of file paths, reads the content of each file
        asynchronously, and returns a dictionary where the keys are the file names
        and the values are their respective contents. If an error occurs while reading
        a file, its content will be an empty string.

        Args:
            paths (list[Path | str]): A list of file paths to read. Each path can be
                provided as an instance of `Path` or a string.

        Returns:
            dict[str, str]: A dictionary mapping file names to their respective content.
        """

        async def read_single(path: Path | str) -> tuple[str, str]:
            path = FileIOCore._ensure_path(path)
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
        Writes multiple files asynchronously.

        This method allows writing multiple files concurrently by mapping file paths
        to their corresponding content. Each file write operation is executed as an
        asynchronous task, and any errors encountered during the write are logged.

        Args:
            files (dict[Path | str, str]): A dictionary where the keys are file paths
                (as Path or str) and the values are the file content to be written.

        Returns:
            None
        """

        async def write_single(path: Path | str, content: str) -> None:
            """
            Writes the specified content to a file asynchronously.

            This function attempts to write the given content to the file specified
            by the path. If any errors occur during the process, an error is logged
            with details about the error and the file path.

            Args:
                path: Path or string representing the target file location.
                content: String data to be written to the specified file.

            """
            try:
                await self.write_file(path, content)
            except Exception as e:
                logger.error(f"Error writing {path}: {e}")

        tasks = list(starmap(write_single, files.items()))
        await asyncio.gather(*tasks)

    # ==========================================
    # Utility Operations
    # ==========================================

    def file_exists(self, path: Path | str) -> bool:  # No longer async because Path.exists() is non-blocking and fast
        """
        Checks if the given file or directory exists at the specified path.

        This method determines whether the specified file system path points to an
        existing file or directory. It utilizes a fast metadata check to determine
        existence without I/O overhead, ensuring minimal latency.

        Args:
            path (Path | str): The file system path to check, which can be provided
                as a Path object or a string.

        Returns:
            bool: True if the specified file or directory exists, False otherwise.
        """
        path = FileIOCore._ensure_path(path)

        # Path.exists() is a fast filesystem metadata check that doesn't block
        # No need for executor overhead - saves ~10-15ms per call
        return path.exists()

    def get_file_size(self, path: Path | str) -> int:  # No longer async because Path.stat() is non-blocking and fast
        """
        Gets the size of the file located at the specified path.

        This method retrieves the size of a file in bytes using a fast filesystem
        metadata operation. It ensures the provided path is in the correct format
        and handles errors in case the file does not exist or is inaccessible.

        Args:
            path (Path | str): The path to the file whose size is to be retrieved. It
                must be either a pathlib.Path object or a string representing the path.

        Returns:
            int: The size of the file in bytes. Returns -1 if the file does not exist
                or an error occurs while accessing its metadata.
        """
        path = FileIOCore._ensure_path(path)

        try:
            # Path.stat() is a fast filesystem metadata operation
            # No need for executor overhead - saves ~10-15ms per call
            stat = path.stat()
        except (OSError, FileNotFoundError):
            return -1
        else:
            return stat.st_size
