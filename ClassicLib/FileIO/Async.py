"""
Async File I/O Utilities for CLASSIC.

This module provides async-first implementations of common file operations,
focusing on encoding detection and non-blocking reads.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

try:
    import aiofiles
    import chardet

    AIOFILES_AVAILABLE = True
except ImportError:
    aiofiles = None  # type: ignore
    chardet = None  # type: ignore
    AIOFILES_AVAILABLE = False

from ClassicLib.Utils.file_utils import open_file_with_encoding
from ClassicLib.Utils.path_utils import validate_path


async def detect_encoding_async(file_path: Path | str | os.PathLike, sample_size: int = 65536) -> str:
    """
    Asynchronously detects the encoding of a given file by reading a sample of its
    content and using the chardet library for encoding detection.

    Args:
        file_path (Path | str | os.PathLike): The path to the file whose encoding
            needs to be detected.
        sample_size (int): The number of bytes to read from the file for encoding
            detection. Defaults to 65536.

    Returns:
        str: The detected encoding of the provided file. Defaults to 'utf-8' if
            detection fails or confidence is low.
    """
    if not AIOFILES_AVAILABLE or aiofiles is None or chardet is None:
        raise ImportError("aiofiles and chardet are required for async encoding detection")

    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    # Validate path before attempting to read
    is_valid, error_msg = validate_path(file_path, check_write=False, check_read=True)
    if not is_valid:
        if "does not exist" in error_msg:
            raise FileNotFoundError(error_msg)
        if "permission" in error_msg.lower():
            raise PermissionError(error_msg)
        raise OSError(error_msg)

    # Read sample data asynchronously
    async with aiofiles.open(file_path, "rb") as f:
        # Read up to sample_size bytes for encoding detection
        sample_data = await f.read(sample_size)

    # Detect encoding (this is CPU-bound, so run in executor)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, chardet.detect, sample_data)

    encoding = result.get("encoding")
    confidence = result.get("confidence", 0)

    # Fallback to utf-8 if detection fails or confidence is too low
    if not encoding or confidence < 0.7:
        encoding = "utf-8"

    return encoding


@asynccontextmanager
async def open_file_with_encoding_async(file_path: Path | str | os.PathLike, mode: str = "r", sample_size: int = 65536) -> AsyncIterator:
    """
    Async context manager for opening a file with automatically detected encoding.

    Args:
        file_path: Path to the file to open
        mode: File open mode (default 'r' for reading)
        sample_size: Number of bytes to sample for encoding detection

    Yields:
        An async file handle opened with the detected encoding
    """
    if not AIOFILES_AVAILABLE or aiofiles is None:
        raise ImportError("aiofiles is required for async file operations")

    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    # Detect encoding first
    encoding = await detect_encoding_async(file_path, sample_size)

    # Open file with detected encoding
    async with aiofiles.open(file_path, mode=mode, encoding=encoding, errors="ignore") as f:  # type: ignore[misc]
        yield f


async def read_file_with_encoding_async(file_path: Path | str | os.PathLike, sample_size: int = 65536) -> str:
    """
    Convenience function to read entire file contents with automatic encoding detection.
    """
    async with open_file_with_encoding_async(file_path, sample_size=sample_size) as f:
        return await f.read()


async def read_lines_with_encoding_async(file_path: Path | str | os.PathLike, sample_size: int = 65536) -> list[str]:
    """
    Convenience function to read file lines with automatic encoding detection.
    """
    async with open_file_with_encoding_async(file_path, sample_size=sample_size) as f:
        return await f.readlines()


# Fallback implementations for when aiofiles is not available
def get_encoding_detection_available() -> bool:
    """Determines if encoding detection is available based on the availability of aiofiles."""
    return AIOFILES_AVAILABLE


async def fallback_to_sync_encoding_detection(file_path: Path | str | os.PathLike) -> str:
    """
    Determines the encoding of a given file path using a synchronous method executed
    in an asynchronous context.
    """
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    # Run in executor to avoid blocking
    loop = asyncio.get_event_loop()

    def get_encoding() -> str:
        with open_file_with_encoding(file_path) as f:
            # The encoding is already detected by open_file_with_encoding
            # We need to extract it from the file object
            return f.encoding or "utf-8"

    return await loop.run_in_executor(None, get_encoding)
