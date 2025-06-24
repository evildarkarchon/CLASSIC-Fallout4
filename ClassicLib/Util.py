import contextlib
import datetime
import hashlib
import logging
import os
import platform
import re
import stat
import sys
from collections.abc import Iterator
from difflib import SequenceMatcher
from importlib import util
from io import TextIOWrapper
from logging import Logger
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import aiohttp
import chardet
import requests
from packaging.version import Version

from ClassicLib import Constants, GlobalRegistry, msg_error, msg_info
from ClassicLib.Logger import logger


def normalize_list(items: list[str]) -> list[str]:
    """
    Normalizes a list of strings by converting each string to lowercase. If the input
    list is empty, returns an empty list.

    Args:
        items: A list of strings to be normalized.

    Returns:
        A list of strings converted to lowercase.
    """
    return [item.lower() for item in items] if items else []


def calculate_similarity(file1: Path, file2: Path) -> float:
    """
    Calculates the similarity ratio between the content of two text files using the
    SequenceMatcher utility. This method reads the content of both files and determines
    how closely they resemble each other by computing a numerical similarity ratio.

    Args:
        file1 (Path): The path to the first file for comparison.
        file2 (Path): The path to the second file for comparison.

    Returns:
        float: A ratio between 0 and 1 indicating the similarity between the two file
        contents, where 1 implies an exact match and 0 indicates no similarity.
    """
    with file1.open("r") as f1, file2.open("r") as f2:
        return SequenceMatcher(None, f1.read(), f2.read()).ratio()


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
    if not _is_valid_executable_path(game_exe_path):
        logger.warning("Game executable not found or path is invalid")
        return Constants.NULL_VERSION

    # Try Windows API first if on Windows
    if platform.system() == "Windows":
        version = _get_version_windows_api(game_exe_path)
        if version != Constants.NULL_VERSION:
            return version
        logger.debug("Windows API failed, trying PE header parsing")

    # Fallback to cross-platform PE header parsing
    return _get_version_from_pe_header(game_exe_path)


def _is_valid_executable_path(path: Path | None) -> bool:
    """Checks if the provided path exists and is a file."""
    return bool(path and path.is_file())


def validate_path(path: Path | str, check_write: bool = False, check_read: bool = True) -> tuple[bool, str]:
    """
    Validate that a path exists and is accessible with appropriate permissions.

    Args:
        path: Path to validate
        check_write: Whether to check write permissions
        check_read: Whether to check read permissions

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty string.
    """
    try:
        path_obj = Path(path) if not isinstance(path, Path) else path

        # Check if the drive exists (Windows)
        if sys.platform == "win32" or platform.system() == "Windows":
            drive = path_obj.drive
            if drive and not Path(drive + "/").exists():
                return False, f"Drive {drive} does not exist"

        # Check if path exists
        if not path_obj.exists():
            return False, f"Path does not exist: {path_obj}"

        # Check read permissions
        if check_read:
            try:
                # For directories, check if we can list contents
                if path_obj.is_dir():
                    list(path_obj.iterdir())
                # For files, check if we can open for reading
                else:
                    with path_obj.open("rb"):
                        pass
            except PermissionError:
                return False, f"No read permission for: {path_obj}"
            except OSError as e:
                return False, f"Cannot access {path_obj}: {e}"

        # Check write permissions
        if check_write:
            try:
                # For directories, check if we can create a temp file
                if path_obj.is_dir():
                    test_file = path_obj / ".classic_test_write"
                    test_file.touch()
                    test_file.unlink()
                # For files, check if parent directory is writable
                else:
                    parent = path_obj.parent
                    test_file = parent / ".classic_test_write"
                    test_file.touch()
                    test_file.unlink()
            except PermissionError:
                return False, f"No write permission for: {path_obj}"
            except OSError as e:
                return False, f"Cannot write to {path_obj}: {e}"

    except Exception as e:  # noqa: BLE001
        return False, f"Error validating path: {e}"
    else:
        return True, ""


def _extract_windows_version_info(win32api_module: Any, exe_path: Path) -> dict[str, int]:
    """Extracts version information from a Windows executable using win32api."""
    return cast("dict[str, int]", win32api_module.GetFileVersionInfo(str(exe_path), "\\"))


def _create_version_from_info(version_info: dict[str, int]) -> Version:
    """Creates a Version object from Windows version info dictionary."""
    major: int = version_info["FileVersionMS"] >> 16
    minor: int = version_info["FileVersionMS"] & 0xFFFF
    patch: int = version_info["FileVersionLS"] >> 16
    build: int = version_info["FileVersionLS"] & 0xFFFF
    return Version(f"{major}.{minor}.{patch}.{build}")


def _get_version_windows_api(game_exe_path: Path) -> Version:
    """Attempts to get version using Windows API."""
    try:
        # Conditional import of Windows-specific module
        import win32api  # type: ignore[reportMissingModuleSource]

        version_info: dict[str, int] = _extract_windows_version_info(win32api, game_exe_path)
        version: Version = _create_version_from_info(version_info)
    except (FileNotFoundError, OSError):
        logger.error(f"Game executable not found or inaccessible at: {game_exe_path}")
        return Constants.NULL_VERSION
    except (AttributeError, UnboundLocalError, ImportError):
        logger.error("Windows API module not properly loaded")
        return Constants.NULL_VERSION
    except ValueError as e:
        logger.error(f"Error parsing version info: {e}")
        return Constants.NULL_VERSION
    except Exception as e:  # noqa: BLE001
        logger.error(f"Unexpected error getting game version: {e}")
        return Constants.NULL_VERSION
    else:
        logger.debug(f"Game version detected: {version}")
        return version


def _get_version_from_pe_header(exe_path: Path) -> Version:
    """
    Cross-platform PE header parser to extract version information.

    This function attempts to use pefile if available, otherwise falls back
    to a simple string search for version patterns in the binary.
    """
    # Try pefile first if available
    if util.find_spec("pefile"):
        return _get_version_with_pefile(exe_path)
    logger.warning("pefile module not found, using fallback method for version detection")
    return _get_version_fallback(exe_path)


def _get_version_with_pefile(exe_path: Path) -> Version:
    """Extract version using pefile library."""
    try:
        import pefile  # pyrefly: ignore

        pe = pefile.PE(str(exe_path))

        # Try to get version from VS_FIXEDFILEINFO
        if hasattr(pe, "VS_FIXEDFILEINFO") and pe.VS_FIXEDFILEINFO:
            file_version = pe.VS_FIXEDFILEINFO[0]
            major = (file_version.FileVersionMS >> 16) & 0xFFFF
            minor = file_version.FileVersionMS & 0xFFFF
            patch = (file_version.FileVersionLS >> 16) & 0xFFFF
            build = file_version.FileVersionLS & 0xFFFF

            version = Version(f"{major}.{minor}.{patch}.{build}")
            logger.debug(f"Game version detected from PE header: {version}")
            return version

        # Try to get version from FileInfo
        if hasattr(pe, "FileInfo") and pe.FileInfo:
            for file_info in pe.FileInfo:
                for info in file_info:
                    if hasattr(info, "StringTable"):
                        for st in info.StringTable:
                            for entry in st.entries.items():
                                if entry[0] == b"FileVersion":
                                    version_str = entry[1].decode("utf-8", errors="ignore")
                                    # Clean up version string
                                    version_str = version_str.replace(",", ".").strip()
                                    try:
                                        version = Version(version_str)
                                    except ValueError:
                                        # Invalid version string format
                                        continue
                                    else:
                                        logger.debug(f"Game version detected from StringTable: {version}")
                                        return version

        logger.error("Version information not found in PE file")

    except Exception as e:  # noqa: BLE001
        logger.error(f"Error parsing PE file with pefile: {e}")
        return Constants.NULL_VERSION
    else:
        return Constants.NULL_VERSION


def _get_version_fallback(exe_path: Path) -> Version:
    """
    Fallback method to extract version by searching for version patterns in the binary.
    This is less reliable but works without additional dependencies.
    """
    try:
        # Common version patterns to search for
        version_patterns = [
            rb"FileVersion[\x00\s]*(\d+\.\d+\.\d+\.\d+)",
            rb"ProductVersion[\x00\s]*(\d+\.\d+\.\d+\.\d+)",
            rb"(\d+\.\d+\.\d+\.\d+)[\x00\s]*FileVersion",
            rb"(\d+\.\d+\.\d+\.\d+)[\x00\s]*ProductVersion",
        ]

        # Read file in chunks to avoid loading entire file into memory
        chunk_size = 1024 * 1024  # 1MB chunks
        overlap = 256  # Overlap to catch versions split between chunks

        with exe_path.open("rb") as f:
            previous_chunk = b""

            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break

                # Combine with overlap from previous chunk
                search_data = previous_chunk[-overlap:] + chunk if previous_chunk else chunk

                # Search for version patterns
                for pattern in version_patterns:
                    matches = re.findall(pattern, search_data)
                    for match in matches:
                        try:
                            version_str = match.decode("utf-8", errors="ignore")
                            version = Version(version_str)
                            if version != Constants.NULL_VERSION:
                                logger.debug(f"Game version detected using pattern search: {version}")
                                return version
                        except ValueError:
                            # Invalid version string format
                            continue

                previous_chunk = chunk

    except Exception as e:  # noqa: BLE001
        logger.error(f"Error in fallback version detection: {e}")
        return Constants.NULL_VERSION
    else:
        logger.warning("No version information found using fallback method")
        return Constants.NULL_VERSION


def crashgen_version_gen(input_string: str) -> Version:
    """
    Parses an input string to extract the version information and returns a Version
    object if successful. If no valid version information is found in the input,
    it returns a predefined constant representing a null version.

    Args:
        input_string: A string potentially containing version information prefixed
            with the character 'v'. The string may contain multiple components
            separated by whitespace.

    Returns:
        Version: A Version object initialized with the extracted version string
            if found, otherwise a constant representing a null version.

    """
    input_string = input_string.strip()
    parts: list[str] = input_string.split()
    version_str = ""
    for part in parts:
        if part.startswith("v") and len(part) > 1:
            version_str = part[1:]  # Remove the 'v'
    if version_str:
        return Version(version_str)
    return Constants.NULL_VERSION


@contextlib.contextmanager
def open_file_with_encoding(file_path: Path | str | os.PathLike) -> Iterator[TextIOWrapper]:
    """
    Context manager for opening a file with an automatically detected encoding. This utility uses
    `chardet` to determine the encoding of the file, allowing reading and processing files with
    varied encodings in an error-tolerant manner. The detected encoding is also set to ignore
    encoding-related errors, ensuring that invalid characters in files do not raise exceptions
    during processing.

    Args:
        file_path (Path | str | os.PathLike): The path to the file that is to be opened. It can be
            provided either as a `Path` object, a string path, or any object implementing the
            `os.PathLike` interface.

    Yields:
        TextIOWrapper: A file object opened with the detected encoding, for reading the contents of
            the file.

    Raises:
        FileNotFoundError: If the file does not exist or is not accessible.
        PermissionError: If the file cannot be read due to permissions.
    """
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    # Validate path before attempting to read
    is_valid, error_msg = validate_path(file_path, check_write=False, check_read=True)
    if not is_valid:
        if "does not exist" in error_msg:
            raise FileNotFoundError(error_msg)
        elif "permission" in error_msg.lower():
            raise PermissionError(error_msg)
        else:
            raise OSError(error_msg)

    raw_data: bytes = file_path.read_bytes()
    encoding: str | None = chardet.detect(raw_data)["encoding"]

    file_handle: Iterator[TextIOWrapper] = cast("Iterator[TextIOWrapper]", file_path.open(encoding=encoding, errors="ignore"))
    try:
        yield cast("TextIOWrapper", file_handle)  # pyrefly: ignore
    finally:
        cast("TextIOWrapper", file_handle).close()


GlobalRegistry.register(GlobalRegistry.Keys.OPEN_FILE_FUNC, open_file_with_encoding)


# noinspection PyGlobalUndefined
def configure_logging(classic_logger: Logger) -> None:
    """
    Configures the logging system for the provided logger, ensuring that a
    file-based log with specific formatting is maintained. It checks the
    existence of the "CLASSIC Journal.log" file and removes it if it is older
    than seven days, regenerating a new logging file as needed. Additionally,
    it ensures that the logging handler is only initialized once for the logger
    named "CLASSIC".

    Args:
        classic_logger: A Logger instance to configure the logging settings
            for. This will be modified to include appropriate level, handler,
            and formatter settings.
    """

    journal_path: Path = Path("CLASSIC Journal.log")
    if journal_path.exists():
        classic_logger.debug("- - - INITIATED LOGGING CHECK")
        log_time: datetime.datetime = datetime.datetime.fromtimestamp(journal_path.stat().st_mtime)
        current_time: datetime.datetime = datetime.datetime.now()
        log_age: datetime.timedelta = current_time - log_time
        if log_age.days > 7:
            try:
                journal_path.unlink(missing_ok=True)
                msg_info("CLASSIC Journal.log has been deleted and regenerated due to being older than 7 days.")
            except (ValueError, OSError) as err:
                msg_error(f"An error occurred while deleting {journal_path.name}: {err}")

    # Make sure we only configure the handler once
    if not classic_logger.handlers:
        classic_logger.setLevel(logging.INFO)
        handler: logging.FileHandler = logging.FileHandler(
            filename="CLASSIC Journal.log",
            mode="a",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        classic_logger.addHandler(handler)


def remove_readonly(file_path: Path) -> None:
    """Removes the read-only attribute from a file or directory.

    This function modifies the file attributes to ensure the specified file or
    directory is writable. It checks the file system type and applies the
    necessary operations based on the OS. If the file or directory is already
    writable, it logs the corresponding outcome.

    Args:
        file_path (Path): The path of the file or directory for which the read-only
            attribute should be removed.
    """
    try:
        if platform.system() == "Windows":
            is_readonly: int = file_path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY  # type: ignore[reportAttributeAccessIssue]
            if is_readonly:
                file_path.chmod(stat.S_IWRITE)
        else:
            current_mode: int = file_path.stat().st_mode
            is_readonly = not (current_mode & stat.S_IWUSR)
            if is_readonly:
                file_path.chmod(current_mode | stat.S_IWUSR)

        # Log the outcome based on whether the file was read-only
        if is_readonly:
            logger.debug(f"- - - '{file_path}' is no longer Read-Only.")
        else:
            logger.debug(f"- - - '{file_path}' is not set to Read-Only.")

    except FileNotFoundError:
        logger.error(f"> > > ERROR (remove_readonly) : '{file_path}' not found.")
    except (ValueError, OSError) as err:
        logger.error(f"> > > ERROR (remove_readonly) : {err}")


def append_or_extend(value: str | int | float | list | tuple | set, destination: list[str]) -> None:
    """
    Appends a single value or extends a list with multiple values into the destination list.

    If the input `value` is a string, integer, or float, it is appended to the `destination`
    list after converting it to a string. If the `value` is a collection type such as a list,
    tuple, or set, its elements are extended into the `destination` list.

    Args:
        value: A single value to append or a collection (list, tuple, or set) whose elements
            will be extended into the destination list.
        destination: The list to which the value or collection of values will be appended
            or extended.

    Returns:
        None
    """
    if isinstance(value, list | tuple | set):  # pyrefly: ignore
        destination.extend(value)
    else:
        destination.append(str(value))


def pastebin_fetch(url: str) -> None:
    """
    Fetches the contents of a Pastebin raw URL and saves them as a crash log file.

    The function checks if the given URL belongs to a Pastebin page and converts it
    to a raw content URL if necessary. It then retrieves the content from the URL,
    ensures the required directory structure exists, and saves the content to a
    file. File paths and directories are created if they do not exist.

    Args:
        url: The URL to a Pastebin page or raw content.

    Raises:
        HTTPError: If the HTTP request to fetch the Pastebin content fails with a
            non-200 status code.
    """
    if urlparse(url).netloc == "pastebin.com" and "/raw" not in url:
        url = url.replace("pastebin.com", "pastebin.com/raw")
    response = requests.get(url)
    if response.status_code != 200:
        response.raise_for_status()
    pastebin_path: Path = Path("Crash Logs/Pastebin")
    if not pastebin_path.is_dir():
        pastebin_path.mkdir(parents=True, exist_ok=True)
    outfile: Path = pastebin_path / f"crash-{urlparse(url).path.split('/')[-1]}.log"
    outfile.write_text(response.text, encoding="utf-8", errors="ignore")


async def pastebin_fetch_async(url: str) -> None:
    """
    Fetches and saves the contents of a Pastebin raw URL asynchronously to a local file.

    This function takes a Pastebin URL, modifies it to ensure it points to the raw content
    (if not already), retrieves the content asynchronously, and saves it to a file
    within a local "Crash Logs/Pastebin" directory. The filename is derived from the
    last segment of the URL path. If the specified directory does not exist,
    it is created.

    Args:
        url (str): The Pastebin URL to fetch and save. If the input URL is not a raw
            URL (i.e., it doesn't include '/raw'), it will be modified accordingly.
    """

    if urlparse(url).netloc == "pastebin.com" and "/raw" not in url:
        url = url.replace("pastebin.com", "pastebin.com/raw")

    async with aiohttp.ClientSession() as session, session.get(url) as response:
        if response.status != 200:
            response.raise_for_status()
        content: str = await response.text()

    # File operations are still synchronous, but they're generally quick
    # For a fully async version, you could use aiofiles, but it's not always necessary
    pastebin_path: Path = Path("Crash Logs/Pastebin")
    if not pastebin_path.is_dir():
        pastebin_path.mkdir(parents=True, exist_ok=True)

    outfile: Path = pastebin_path / f"crash-{urlparse(url).path.split('/')[-1]}.log"

    # If you want fully async file operations, uncomment this and comment out the write_text line:
    # import aiofiles
    # async with aiofiles.open(outfile, 'w', encoding="utf-8", errors="ignore") as f:
    #     await f.write(content)

    # Otherwise, this is fine for most use cases:
    outfile.write_text(content, encoding="utf-8", errors="ignore")


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculates the SHA-256 hash of a file. This function reads the content of the file
    in blocks to efficiently compute the hash for large files without loading the entire
    file into memory.

    Args:
        file_path (Path): The path to the file whose SHA-256 hash needs to be calculated.

    Returns:
        str: The computed SHA-256 hash of the file in hexadecimal format.
    """
    hash_sha256 = hashlib.sha256()
    with file_path.open("rb") as file:
        for block in iter(lambda: file.read(4096), b""):
            hash_sha256.update(block)
    return hash_sha256.hexdigest()
