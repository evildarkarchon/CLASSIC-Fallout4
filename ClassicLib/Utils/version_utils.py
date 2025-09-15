"""Version detection and parsing utilities."""

import platform
import re
import struct
from importlib import util
from pathlib import Path
from typing import Any

from packaging.version import Version

from ClassicLib import Constants
from ClassicLib.Logger import logger

# Pre-compiled regex patterns for version detection performance optimization
VERSION_PATTERNS = [
    re.compile(rb"FileVersion[\x00\s]*(\d+\.\d+\.\d+\.\d+)"),
    re.compile(rb"ProductVersion[\x00\s]*(\d+\.\d+\.\d+\.\d+)"),
    re.compile(rb"(\d+\.\d+\.\d+\.\d+)[\x00\s]*FileVersion"),
    re.compile(rb"(\d+\.\d+\.\d+\.\d+)[\x00\s]*ProductVersion"),
]


def is_valid_executable_path(path: Path | None) -> bool:
    """Check if a path points to a valid executable file."""
    return path is not None and path.exists() and path.is_file() and path.suffix.lower() in (".exe", ".app", "")


def extract_windows_version_info(win32api_module: Any, exe_path: Path) -> tuple[int, int]:
    """
    Extract version info using Windows API.

    Args:
        win32api_module: The win32api module instance
        exe_path: Path to the executable

    Returns:
        Tuple of (FileVersionMS, FileVersionLS)
    """
    info = win32api_module.GetFileVersionInfo(str(exe_path), "\\")
    return info["FileVersionMS"], info["FileVersionLS"]


def create_version_from_info(ms: int, ls: int) -> Version:
    """
    Create Version object from Windows version info components.

    Args:
        ms: FileVersionMS value
        ls: FileVersionLS value

    Returns:
        Version object
    """
    return Version(f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}")


def get_version_windows_api(game_exe_path: Path) -> Version:
    """
    Get version using Windows API (pywin32).

    Args:
        game_exe_path: Path to the executable

    Returns:
        Version object or NULL_VERSION if failed
    """
    try:
        # Try to import win32api
        win32api_spec = util.find_spec("win32api")
        if win32api_spec is None:
            logger.debug("win32api not available")
            return Constants.NULL_VERSION

        import win32api

        ms, ls = extract_windows_version_info(win32api, game_exe_path)
        return create_version_from_info(ms, ls)

    except ImportError:
        logger.debug("win32api not available")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Windows API version detection failed: {e}")

    return Constants.NULL_VERSION


def get_version_from_pe_header(exe_path: Path) -> Version:
    """
    Extract version from PE header with multiple fallback strategies.

    Args:
        exe_path: Path to the executable

    Returns:
        Version object or NULL_VERSION if all methods fail
    """
    # Try pefile first if available
    version = get_version_with_pefile(exe_path)
    if version != Constants.NULL_VERSION:
        return version

    # Fallback to manual PE parsing
    return get_version_fallback(exe_path)


def get_version_with_pefile(exe_path: Path) -> Version:
    """
    Get version using pefile library.

    Args:
        exe_path: Path to the executable

    Returns:
        Version object or NULL_VERSION if failed
    """
    try:
        pefile_spec = util.find_spec("pefile")
        if pefile_spec is None:
            logger.debug("pefile not available")
            return Constants.NULL_VERSION

        import pefile

        pe = pefile.PE(str(exe_path))

        # Try to get version from VS_VERSIONINFO
        if hasattr(pe, "VS_VERSIONINFO") and pe.VS_VERSIONINFO:
            for file_info in pe.VS_VERSIONINFO:
                if hasattr(file_info, "StringFileInfo") and file_info.StringFileInfo:
                    for string_table in file_info.StringFileInfo:
                        if hasattr(string_table, "entries") and string_table.entries:
                            file_version = string_table.entries.get(b"FileVersion")
                            if file_version:
                                # Convert bytes to string and clean up
                                version_str = file_version.decode("utf-8", errors="ignore").strip()
                                # Remove any null characters
                                version_str = version_str.replace("\x00", "")
                                try:
                                    return Version(version_str)
                                except Exception:  # noqa: BLE001
                                    logger.debug(f"Could not parse version string: {version_str}")

        pe.close()

    except ImportError:
        logger.debug("pefile not available")
    except Exception as e:  # noqa: BLE001
        logger.debug(f"pefile version detection failed: {e}")

    return Constants.NULL_VERSION


def get_version_fallback(exe_path: Path) -> Version:
    """
    Fallback method to extract version using regex patterns.

    This method reads the PE file directly and searches for version
    strings using pre-compiled regex patterns.

    Args:
        exe_path: Path to the executable

    Returns:
        Version object or NULL_VERSION if failed
    """
    try:
        # Read the file in chunks to avoid memory issues with large files
        with exe_path.open("rb") as f:
            # Read first 1MB (versions are usually in the first part)
            content = f.read(1024 * 1024)

            # Try each pattern
            for pattern in VERSION_PATTERNS:
                match = pattern.search(content)
                if match:
                    version_str = match.group(1).decode("utf-8", errors="ignore")
                    try:
                        return Version(version_str)
                    except Exception:  # noqa: BLE001
                        continue

    except (OSError, IOError) as e:
        logger.warning(f"Failed to read executable for version detection: {e}")

    return Constants.NULL_VERSION


def get_game_version(game_exe_path: Path) -> Version:
    """
    Retrieves the version information of a game executable.

    This function attempts to detect the version of a given game executable
    file located at `game_exe_path`. It supports both Windows API-based
    extraction and a cross-platform PE header parsing fallback.

    Args:
        game_exe_path (Path): Path to the game executable file.

    Returns:
        Version: Parsed version of the game executable, or a null version
        placeholder if any error occurs during version detection.
    """
    # Early return for invalid path
    if not is_valid_executable_path(game_exe_path):
        logger.warning("Game executable not found or path is invalid")
        return Constants.NULL_VERSION

    # Try Windows API first if on Windows
    if platform.system() == "Windows":
        version = get_version_windows_api(game_exe_path)
        if version != Constants.NULL_VERSION:
            return version
        logger.debug("Windows API failed, trying PE header parsing")

    # Fallback to cross-platform PE header parsing
    return get_version_from_pe_header(game_exe_path)


def crashgen_version_gen(input_string: str) -> Version:
    """
    Generate a Version object from CrashGen version string.

    Parses version information from various CrashGen output formats.
    Supports both 3-part (e.g., "1.28.6") and 4-part (e.g., "1.10.163.0") versions.

    Args:
        input_string: String containing version information

    Returns:
        Version object or NULL_VERSION if parsing fails
    """
    # Pattern for 4-part version format (e.g., "1.10.163.0")
    version_pattern_4 = re.compile(r"(\d+)\.(\d+)\.(\d+)\.(\d+)")

    # Pattern for 3-part version format (e.g., "v1.28.6" or "1.28.6")
    version_pattern_3 = re.compile(r"v?(\d+)\.(\d+)\.(\d+)(?!\.\d)")

    # Try 4-part pattern first
    match = version_pattern_4.search(input_string)
    if match:
        try:
            major, minor, patch, build = match.groups()
            version_string = f"{major}.{minor}.{patch}.{build}"
            return Version(version_string)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Failed to parse 4-part version from CrashGen string: {e}")

    # Try 3-part pattern
    match = version_pattern_3.search(input_string)
    if match:
        try:
            major, minor, patch = match.groups()
            version_string = f"{major}.{minor}.{patch}"
            return Version(version_string)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Failed to parse 3-part version from CrashGen string: {e}")

    # If no match found or parsing failed
    logger.debug(f"Could not extract version from: {input_string[:100]}")  # Log first 100 chars
    return Constants.NULL_VERSION
