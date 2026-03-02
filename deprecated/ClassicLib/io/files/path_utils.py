"""Provide utility functions for path conversion and caching.

This module contains functions that handle the conversion of string
representations of paths to `Path` objects. It includes an efficient
caching mechanism to optimize repeated operations on frequently used
paths.
"""

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=512)
def cached_path_conversion(path_str: str) -> Path:
    """Convert a string representation of a file system path to a `Path` object and caches the result
    to improve performance for repeated path conversions. The caching mechanism allows up to 512 unique
    path conversions to be stored.

    Args:
        path_str: A string representing the file system path to be converted.

    Returns:
        A `Path` object corresponding to the provided `path_str`.

    """
    return Path(path_str)


def ensure_path(path: Path | str) -> Path:
    """Ensure that the given input is converted to a Path object. If the input
    is already a Path object, it is returned as-is. Otherwise, the input is
    converted to a Path object through an appropriate conversion process.

    Args:
        path (Path | str): A filesystem path provided as either a Path object
        or a string.

    Returns:
        Path: The ensured Path object.

    """
    if isinstance(path, Path):
        return path
    return cached_path_conversion(str(path))
