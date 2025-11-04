"""Type stubs for classic_version.

Python bindings for classic-version-core, providing comprehensive version handling
utilities including parsing, comparison, extraction, and validation.

Architecture:
    - classic-version-core: Business logic (version parsing, comparison, extraction)
    - classic-version-py: Python bindings (this module - PyO3 adapters)

Features:
    - Flexible version string parsing (supports multiple formats)
    - Semantic version comparison
    - Version extraction from filenames and logs
    - Known version validation for Fallout 4 and F4SE
    - Version formatting with customizable prefixes

Usage:
    import classic_version

    # Parse version strings
    version = classic_version.parse_version("1.10.163.0")
    assert version == (1, 10, 163)

    # Compare versions
    result = classic_version.compare_versions((1, 10, 163), (1, 10, 984))
    assert result == -1  # 1.10.163 < 1.10.984

    # Extract from filenames
    version = classic_version.extract_version_from_filename("MyMod-v1.2.3.esp")
    assert version == (1, 2, 3)

    # Validate known versions
    assert classic_version.is_known_fallout4_version((1, 10, 163))

    # Format versions
    formatted = classic_version.format_version((1, 10, 163))
    assert formatted == "v1.10.163"
"""

from __future__ import annotations

from typing import List, Optional, Tuple

__version__: str

# Type alias for version tuples
Version = Tuple[int, int, int]


def parse_version(version_str: str) -> Version:
    """Parse a version string into a semantic version.

    Accepts various formats:
    - "1.10.163.0" -> (1, 10, 163)
    - "1.10.163" -> (1, 10, 163)
    - "1.10" -> (1, 10, 0)
    - "v1.10.163" -> (1, 10, 163)

    Args:
        version_str: The version string to parse.

    Returns:
        A tuple of (major, minor, patch) representing the semantic version.

    Raises:
        ValueError: If the version string cannot be parsed.

    Example:
        >>> import classic_version
        >>> version = classic_version.parse_version("1.10.163.0")
        >>> assert version == (1, 10, 163)
        >>> version = classic_version.parse_version("v1.2.3")
        >>> assert version == (1, 2, 3)
    """


def try_parse_version(version_str: str) -> Optional[Version]:
    """Try to parse a version string, returning None if parsing fails.

    This is a non-throwing version of `parse_version()` that returns None
    instead of raising an exception when parsing fails.

    Args:
        version_str: The version string to parse.

    Returns:
        A tuple of (major, minor, patch) if successful, None otherwise.

    Example:
        >>> import classic_version
        >>> version = classic_version.try_parse_version("1.10.163.0")
        >>> assert version == (1, 10, 163)
        >>> version = classic_version.try_parse_version("invalid")
        >>> assert version is None
    """


def compare_versions(v1: Version, v2: Version) -> int:
    """Compare two semantic versions.

    Args:
        v1: First version tuple (major, minor, patch).
        v2: Second version tuple (major, minor, patch).

    Returns:
        * -1 if v1 < v2
        * 0 if v1 == v2
        * 1 if v1 > v2

    Example:
        >>> import classic_version
        >>> result = classic_version.compare_versions((1, 10, 163), (1, 10, 984))
        >>> assert result == -1  # 1.10.163 < 1.10.984
        >>> result = classic_version.compare_versions((1, 10, 163), (1, 10, 163))
        >>> assert result == 0
        >>> result = classic_version.compare_versions((1, 10, 984), (1, 10, 163))
        >>> assert result == 1
    """


def is_known_fallout4_version(version: Version) -> bool:
    """Check if a version is a known Fallout 4 version.

    Args:
        version: Version tuple (major, minor, patch).

    Returns:
        True if the version is in the known Fallout 4 versions list.

    Example:
        >>> import classic_version
        >>> assert classic_version.is_known_fallout4_version((1, 10, 163))
        >>> assert classic_version.is_known_fallout4_version((1, 10, 984))
        >>> assert not classic_version.is_known_fallout4_version((9, 9, 9))
    """


def is_known_f4se_version(version: Version) -> bool:
    """Check if a version is a known F4SE version.

    Args:
        version: Version tuple (major, minor, patch).

    Returns:
        True if the version is in the known F4SE versions list.

    Example:
        >>> import classic_version
        >>> assert classic_version.is_known_f4se_version((0, 6, 23))
        >>> assert classic_version.is_known_f4se_version((0, 7, 2))
        >>> assert not classic_version.is_known_f4se_version((9, 9, 9))
    """


def extract_version_from_filename(filename: str) -> Optional[Version]:
    """Extract a version from a filename.

    Looks for version patterns like:
    - "MyMod-v1.2.3.esp"
    - "SomeMod_1.2.3.ba2"
    - "Plugin-1.2.esp"

    Args:
        filename: The filename to extract version from.

    Returns:
        A tuple of (major, minor, patch) if a version is found, None otherwise.

    Example:
        >>> import classic_version
        >>> version = classic_version.extract_version_from_filename("MyMod-v1.2.3.esp")
        >>> assert version == (1, 2, 3)
        >>> version = classic_version.extract_version_from_filename("SomeMod_1.2.esp")
        >>> assert version == (1, 2, 0)
        >>> version = classic_version.extract_version_from_filename("NoVersion.esp")
        >>> assert version is None
    """


def extract_version_from_log(log_content: str) -> Optional[Version]:
    """Extract a version from log content.

    Searches for version patterns in log file content, typically looking
    for patterns like "Version: 1.10.163.0" or similar.

    Args:
        log_content: The log file content to search.

    Returns:
        A tuple of (major, minor, patch) if a version is found, None otherwise.

    Example:
        >>> import classic_version
        >>> log = "Game Version: 1.10.163.0\\nOther info..."
        >>> version = classic_version.extract_version_from_log(log)
        >>> assert version == (1, 10, 163)
    """


def extract_all_versions(content: str) -> List[Version]:
    """Extract all versions from a text content.

    Finds all version patterns in the given text and returns them as a list.

    Args:
        content: The text content to search for versions.

    Returns:
        A list of version tuples (major, minor, patch).

    Example:
        >>> import classic_version
        >>> content = "Version 1.2.3 and version 4.5.6 found"
        >>> versions = classic_version.extract_all_versions(content)
        >>> assert versions == [(1, 2, 3), (4, 5, 6)]
    """


def format_version(version: Version, prefix: Optional[str] = None) -> str:
    """Format a version with optional prefix.

    Args:
        version: Version tuple (major, minor, patch).
        prefix: Optional prefix string (default: "v"). Use empty string "" for no prefix.

    Returns:
        Formatted version string like "v1.10.163".

    Example:
        >>> import classic_version
        >>> formatted = classic_version.format_version((1, 10, 163))
        >>> assert formatted == "v1.10.163"
        >>> formatted = classic_version.format_version((1, 10, 163), prefix="Version ")
        >>> assert formatted == "Version 1.10.163"
        >>> formatted = classic_version.format_version((1, 10, 163), prefix="")
        >>> assert formatted == "1.10.163"
    """
