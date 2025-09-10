"""Path conversion utilities with caching."""

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=512)
def cached_path_conversion(path_str: str) -> Path:
    """
    Cached conversion of string paths to Path objects.

    The LRU cache stores up to 512 most recently used paths,
    significantly reducing overhead for frequently accessed files.

    Args:
        path_str: String representation of the path

    Returns:
        Path: Cached Path object
    """
    return Path(path_str)


def ensure_path(path: Path | str) -> Path:
    """
    Efficiently convert string to Path object with caching.

    This method provides a single point for path conversion with LRU caching
    for string paths, significantly reducing overhead for frequently accessed files.

    Args:
        path: Path object or string representation

    Returns:
        Path: Path object (cached if originally a string)
    """
    if isinstance(path, Path):
        return path
    return cached_path_conversion(str(path))
