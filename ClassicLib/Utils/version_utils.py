"""Version detection and parsing utilities."""

import re
from functools import lru_cache
from pathlib import Path

from classic_version import extract_pe_version
from packaging.version import Version

from ClassicLib.core.constants import NULL_VERSION
from ClassicLib.core.logger import logger

# Pre-compiled patterns for crashgen version parsing (5-10ms performance gain)
CRASHGEN_VERSION_PATTERN_4 = re.compile(r"(\d+)\.(\d+)\.(\d+)\.(\d+)")
CRASHGEN_VERSION_PATTERN_3 = re.compile(r"v?(\d+)\.(\d+)\.(\d+)(?!\.\d)")


def is_valid_executable_path(path: Path | None) -> bool:
    """Check if the provided path is valid as an executable file.

    The function evaluates whether the given path corresponds to a valid
    executable file. This includes checking for the existence of the path,
    ensuring it is a file, and verifying that its extension matches known
    executable file types.

    Args:
        path (Path | None): The file path to validate.

    Returns:
        bool: True if the path is valid as an executable, otherwise False.

    """
    return path is not None and path.exists() and path.is_file() and path.suffix.lower() in {".exe", ".app", ""}


def read_game_exe_version(game_exe_path: Path) -> Version:
    """Retrieve the version information of a game executable.

    Uses Rust PE parser (pelite) via classic_version for extraction.

    Args:
        game_exe_path (Path): Path to the game executable file.

    Returns:
        Version: Parsed version of the game executable, or a null version
        placeholder if any error occurs during version detection.

    """
    if not is_valid_executable_path(game_exe_path):
        logger.warning("Game executable not found or path is invalid")
        return NULL_VERSION

    try:
        major, minor, patch, build = extract_pe_version(str(game_exe_path))
        logger.debug("PE version extracted via Rust (pelite)")
        return Version(f"{major}.{minor}.{patch}.{build}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"PE version extraction failed: {e}")
        return NULL_VERSION


@lru_cache(maxsize=128)
def crashgen_version_gen(input_string: str) -> Version:
    """Generate a Version object from CrashGen version string.

    Parses version information from various CrashGen output formats.
    Supports both 3-part (e.g., "1.28.6") and 4-part (e.g., "1.10.163.0") versions.
    Results are cached to avoid re-parsing the same version strings repeatedly.

    Args:
        input_string: String containing version information

    Returns:
        Version object or NULL_VERSION if parsing fails

    """
    # Use pre-compiled module-level patterns for better performance
    # Try 4-part pattern first
    match = CRASHGEN_VERSION_PATTERN_4.search(input_string)
    if match:
        try:
            major, minor, patch, build = match.groups()
            version_string = f"{major}.{minor}.{patch}.{build}"
            return Version(version_string)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Failed to parse 4-part version from CrashGen string: {e}")

    # Try 3-part pattern
    match = CRASHGEN_VERSION_PATTERN_3.search(input_string)
    if match:
        try:
            major, minor, patch = match.groups()
            version_string = f"{major}.{minor}.{patch}"
            return Version(version_string)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Failed to parse 3-part version from CrashGen string: {e}")

    # If no match found or parsing failed
    logger.debug(f"Could not extract version from: {input_string[:100]}")  # Log first 100 chars
    return NULL_VERSION
