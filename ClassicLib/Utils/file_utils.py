"""File utilities for similarity comparison, hashing, and encoding detection., file hashing, and
file handling with automatic encoding detection. It includes functionalities to calculate
the similarity between text files, compute SHA256 file hashes, and open files with
encoding detection, ensuring robustness against various encoding issues.

Functions:
- calculate_similarity: Computes the similarity ratio between the content of two text files.
- calculate_file_hash: Generates a SHA256 hash string for a file.
- open_file_with_encoding: Context manager to open and read files with detected encoding.
"""

import contextlib
import hashlib
import os
from collections.abc import Iterator
from difflib import SequenceMatcher
from io import TextIOWrapper
from pathlib import Path

import chardet


def calculate_similarity(file1: Path, file2: Path) -> float:
    """Calculate the similarity percentage between two text files.

    Delegates to Rust LCS-based comparison for speed, with Python
    SequenceMatcher fallback.

    Args:
        file1: Path to the first file
        file2: Path to the second file

    Returns:
        Similarity ratio as a float between 0.0 and 1.0

    """
    try:
        from classic_file_io import calculate_similarity as rust_similarity

        return rust_similarity(str(file1), str(file2))
    except Exception:  # noqa: BLE001
        pass

    try:
        content1 = file1.read_text(encoding="utf-8", errors="ignore")
        content2 = file2.read_text(encoding="utf-8", errors="ignore")
        return SequenceMatcher(None, content1, content2).ratio()
    except (OSError, UnicodeDecodeError):
        return 0.0


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        Hex string of the SHA256 hash

    """
    sha256_hash = hashlib.sha256()
    try:
        with file_path.open("rb") as f:
            # Read in chunks for memory efficiency
            for byte_block in iter(lambda: f.read(4096), b""):
                # noinspection PyTypeChecker
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except OSError as e:
        from ClassicLib.core.logger import logger

        logger.error(f"Failed to calculate hash for {file_path}: {e}")
        return ""


@contextlib.contextmanager
def open_file_with_encoding(file_path: Path | str | os.PathLike[str]) -> Iterator[TextIOWrapper]:
    """Open a file with automatic encoding detection.

    This context manager attempts to detect the file's encoding using chardet,
    falling back to UTF-8 with error handling if detection fails.

    Args:
        file_path: Path to the file to open

    Yields:
        TextIOWrapper: Open file handle

    Raises:
        FileNotFoundError: If the file doesn't exist
        OSError: If the file cannot be opened

    """
    file_path = Path(file_path)

    # Try to detect encoding
    encoding = "utf-8"
    try:
        with file_path.open("rb") as raw_file:
            # Read first 10KB for encoding detection
            raw_data = raw_file.read(10240)
            if raw_data:
                result = chardet.detect(raw_data)
                if result and result.get("encoding"):
                    detected_encoding = result["encoding"]
                    # Use detected encoding if confidence is high enough
                    if result.get("confidence", 0) > 0.7:
                        encoding = detected_encoding
    except OSError:
        pass  # Can't read for detection, fall back to UTF-8

    # Open with detected or default encoding
    try:
        with file_path.open("r", encoding=encoding, errors="ignore") as file:
            yield file
    except UnicodeDecodeError:
        # If detected encoding fails, fall back to UTF-8
        with file_path.open("r", encoding="utf-8", errors="ignore") as file:
            yield file
