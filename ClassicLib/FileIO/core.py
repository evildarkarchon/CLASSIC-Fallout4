"""
Async-first unified file I/O operations for CLASSIC.

This module provides the primary async implementations for all file I/O operations,
consolidating functionality from various modules into a single async-first design.
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
    """Async-first core implementation for all file I/O operations."""

    def __init__(self, encoding: str = "utf-8", errors: str = "ignore") -> None:
        """
        Initialize FileIOCore with default encoding settings.

        Args:
            encoding: Default encoding for file operations
            errors: Error handling strategy for encoding errors
        """
        self.default_encoding = encoding
        self.default_errors = errors

    @staticmethod
    def _ensure_path(path: Path | str) -> Path:
        """
        Efficiently convert string to Path object with caching.

        Args:
            path: Path object or string representation

        Returns:
            Path: Path object (cached if originally a string)
        """
        return ensure_path(path)

    # ==========================================
    # Core Read Operations
    # ==========================================

    async def read_file(self, path: Path | str) -> str:
        """
        Read entire file contents with automatic encoding detection.

        Args:
            path: Path to the file to read

        Returns:
            str: Complete file contents

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read
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
        Read file lines with automatic encoding detection.

        Args:
            path: Path to the file to read

        Returns:
            list[str]: List of lines from the file

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read
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
        Read file as bytes.

        Args:
            path: Path to the file to read

        Returns:
            bytes: Raw file contents

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file cannot be read
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
        Write string content to file.

        Args:
            path: Path to the file to write
            content: String content to write

        Raises:
            PermissionError: If file cannot be written
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
        Write lines to file.

        Args:
            path: Path to the file to write
            lines: List of lines to write (newlines will be added)

        Raises:
            PermissionError: If file cannot be written
        """
        content = "\n".join(lines)
        if not content.endswith("\n"):
            content += "\n"
        await self.write_file(path, content)

    async def write_bytes(self, path: Path | str, content: bytes) -> None:
        """
        Write bytes to file.

        Args:
            path: Path to the file to write
            content: Bytes content to write

        Raises:
            PermissionError: If file cannot be written
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
        Append string content to file.

        Args:
            path: Path to the file to append to
            content: String content to append

        Raises:
            PermissionError: If file cannot be written
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
        Read crash log file with appropriate encoding detection.

        Args:
            path: Path to crash log file

        Returns:
            list[str]: Lines from the crash log
        """
        lines = await self.read_lines(path)
        # Strip any trailing empty lines for consistency
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    async def write_crash_report(self, path: Path | str, report_lines: list[str]) -> None:
        """
        Write crash report to file.

        Args:
            path: Path to write report to
            report_lines: Lines of the report
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
        Read multiple files concurrently.

        Args:
            paths: List of file paths to read

        Returns:
            dict: Mapping of file names to contents
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
        Write multiple files concurrently.

        Args:
            files: Dictionary mapping paths to contents
        """

        async def write_single(path: Path | str, content: str) -> None:
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
        Check if file exists (async-compatible).

        Args:
            path: Path to check

        Returns:
            bool: True if file exists
        """
        path = FileIOCore._ensure_path(path)

        # Path.exists() is a fast filesystem metadata check that doesn't block
        # No need for executor overhead - saves ~10-15ms per call
        return path.exists()

    def get_file_size(self, path: Path | str) -> int:  # No longer async because Path.stat() is non-blocking and fast
        """
        Get file size in bytes.

        Args:
            path: Path to check

        Returns:
            int: File size in bytes, or -1 if file doesn't exist
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
