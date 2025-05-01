import contextlib
import datetime
import logging
import os
import platform
import stat
from collections.abc import Iterator
from io import TextIOWrapper
from logging import Logger
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

import aiohttp
import chardet
import requests
from packaging.version import Version

from CLASSIC_Main import logger
from ClassicLib import Constants


def get_game_version(game_exe_path: Path) -> Version:
    """
    Gets the version information of a specified game executable file.

    This function retrieves the version of a game executable file by using system-level
    API calls to fetch version information. It is specifically supported for systems running
    on Windows. If the path provided does not exist, is invalid, or is not a Windows
    executable file, a default null version is returned. Any unexpected errors during
    processing are gracefully handled and logged.

    Args:
        game_exe_path (Path): The file path to the target game executable.

    Returns:
        Version: The version of the game executable in the format "major.minor.patch.build".
        If detection fails, a null version is returned.
    """

    if platform.system() != "Windows":
        logger.warning("Game version detection is only supported on Windows")
        return Constants.NULL_VERSION
    import win32api

    # Check if path exists and is a file
    if not game_exe_path or not game_exe_path.is_file():
        logger.warning("Game executable not found or path is invalid")
        return Constants.NULL_VERSION

    try:
        # Get file version info using win32api
        version_info = win32api.GetFileVersionInfo(str(game_exe_path), "\\")  # type: ignore[attr-defined]

        # Extract version components
        major = version_info["FileVersionMS"] >> 16
        minor = version_info["FileVersionMS"] & 0xFFFF
        patch = version_info["FileVersionLS"] >> 16
        build = version_info["FileVersionLS"] & 0xFFFF

        version = Version(f"{major}.{minor}.{patch}.{build}")
        logger.debug(f"Game version detected: {version}")

    except FileNotFoundError:
        logger.error(f"Game executable not found at: {game_exe_path}")
        return Constants.NULL_VERSION
    except (AttributeError, UnboundLocalError):
        logger.error("win32api module not properly loaded")
        return Constants.NULL_VERSION
    except (OSError, ValueError) as e:
        logger.error(f"Error retrieving version info: {e}")
        return Constants.NULL_VERSION
    except Exception as e:  # noqa: BLE001
        logger.error(f"Unexpected error getting game version: {e}")
        return Constants.NULL_VERSION
    else:
        return version


def crashgen_version_gen(input_string: str) -> Version:
    """
    Generates a Version object from an input string.

    This function processes an input string to extract a version number. It looks
    for substrings prefixed with the letter 'v', strips the prefix, and constructs
    a Version instance if a valid version string is found. If no valid version is
    present, it returns a predefined null version.

    Args:
        input_string: A string that potentially includes a version prefixed by
            'v'.

    Returns:
        Version: A Version object representing the extracted version or a null
            Version instance if no valid version could be parsed.
    """
    input_string = input_string.strip()
    parts = input_string.split()
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
    Opens a file with its detected encoding as a context manager.

    This function detects the encoding of the specified file and opens the file using
    that encoding. It allows working with files having unknown or varied encodings
    to ensure the correct reading of the content. The function ensures that the file
    is properly closed after processing, even if exceptions are raised during the
    execution of the code block that uses the context manager.

    Args:
        file_path: The path to the file to be opened. It can be provided as a Path,
            string, or os.PathLike object.

    Yields:
        TextIOWrapper: An open text file object for reading the file's content using
        the detected encoding.

    """
    if not isinstance(file_path, Path):
        file_path = Path(file_path)
    raw_data = file_path.read_bytes()
    encoding = chardet.detect(raw_data)["encoding"]

    file_handle = cast("Iterator[TextIOWrapper]", file_path.open(encoding=encoding, errors="ignore"))
    try:
        yield cast("TextIOWrapper", file_handle)
    finally:
        cast("TextIOWrapper", file_handle).close()


# noinspection PyGlobalUndefined
def configure_logging(classic_logger: Logger) -> None:
    """
    Configures the logging system for the application.

    This function checks the existence and age of a log file named "CLASSIC Journal.log".
    If the log file is older than 7 days, it deletes the file and generates a new one.
    The function also ensures that logging is configured only once for the logger named
    "CLASSIC". The logs are stored in "CLASSIC Journal.log" using a specific format that
    includes timestamp, log level, and the log message.

    Args:
        classic_logger (Logger): 

    Raises:
        ValueError: If an error occurs while deleting the log file.
        OSError: If there is an operating system-related error during log file deletion.
    """

    journal_path = Path("CLASSIC Journal.log")
    if journal_path.exists():
        classic_logger.debug("- - - INITIATED LOGGING CHECK")
        log_time = datetime.datetime.fromtimestamp(journal_path.stat().st_mtime)
        current_time = datetime.datetime.now()
        log_age = current_time - log_time
        if log_age.days > 7:
            try:
                journal_path.unlink(missing_ok=True)
                print("CLASSIC Journal.log has been deleted and regenerated due to being older than 7 days.")
            except (ValueError, OSError) as err:
                print(f"An error occurred while deleting {journal_path.name}: {err}")

    # Make sure we only configure the handler once
    if "CLASSIC" not in logging.Logger.manager.loggerDict:
        classic_logger = logging.getLogger("CLASSIC")
        classic_logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            filename="CLASSIC Journal.log",
            mode="a",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        classic_logger.addHandler(handler)


def remove_readonly(file_path: Path) -> None:
    """
    Removes the read-only attribute or permission from the specified file path.
    On Windows, it clears the read-only file attribute. On other operating
    systems, it adds the write permission for the user if not already set.

    In case the file does not exist or an error occurs during the operation,
    appropriate error messages are logged.

    Args:
        file_path (Path): The path of the file from which the read-only
            attribute or permission is to be removed.
    """
    try:
        if platform.system() == "Windows":
            # Check if read-only attribute is set
            if file_path.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:
                file_path.chmod(stat.S_IWRITE)
                logger.debug(f"- - - '{file_path}' is no longer Read-Only.")
            else:
                logger.debug(f"- - - '{file_path}' is not set to Read-Only.")
        else:
            # Get current file permissions
            current_mode = file_path.stat().st_mode
            # Check if user write permission is not set (file is read-only)
            if not (current_mode & stat.S_IWUSR):
                # Add write permission for user
                file_path.chmod(current_mode | stat.S_IWUSR)
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
    if isinstance(value, list | tuple | set):
        destination.extend(value)
    else:
        destination.append(str(value))


def pastebin_fetch(url: str) -> None:
    """
    Fetches and saves raw content from a Pastebin URL to a local file.

    This function takes a Pastebin URL, converts it to its raw content version
    if necessary, downloads the content, and saves it to a specified directory.
    The output file is named based on the paste identifier extracted from the URL.

    Args:
        url: The Pastebin URL from which the content will be fetched.

    Raises:
        HTTPError: If the HTTP request to the provided URL fails.
    """
    if urlparse(url).netloc == "pastebin.com" and "/raw" not in url:
        url = url.replace("pastebin.com", "pastebin.com/raw")
    response = requests.get(url)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
    pastebin_path = Path("Crash Logs/Pastebin")
    if not pastebin_path.is_dir():
        pastebin_path.mkdir(parents=True, exist_ok=True)
    outfile = pastebin_path / f"crash-{urlparse(url).path.split("/")[-1]}.log"
    outfile.write_text(response.text, encoding="utf-8", errors="ignore")


async def pastebin_fetch_async(url: str) -> None:
    """
    Asynchronously fetches the raw content of a pastebin link and writes it to a log file.

    This function processes a given Pastebin URL, ensuring it fetches raw content if necessary,
    downloads the content asynchronously, and writes it to a local file. If the directory
    does not exist, it is created. The function operates asynchronously for network operations
    to improve efficiency in asynchronous workflows.

    Args:
        url (str): The Pastebin URL to fetch content from. The function automatically adjusts
            the URL to point to the raw content if it is not already.

    """

    if urlparse(url).netloc == "pastebin.com" and "/raw" not in url:
        url = url.replace("pastebin.com", "pastebin.com/raw")

    async with aiohttp.ClientSession() as session, session.get(url) as response:
        if response.status != 200:
            response.raise_for_status()
        content = await response.text()

    # File operations are still synchronous, but they're generally quick
    # For a fully async version, you could use aiofiles, but it's not always necessary
    pastebin_path = Path("Crash Logs/Pastebin")
    if not pastebin_path.is_dir():
        pastebin_path.mkdir(parents=True, exist_ok=True)

    outfile = pastebin_path / f"crash-{urlparse(url).path.split('/')[-1]}.log"

    # If you want fully async file operations, uncomment this and comment out the write_text line:
    # import aiofiles
    # async with aiofiles.open(outfile, 'w', encoding="utf-8", errors="ignore") as f:
    #     await f.write(content)

    # Otherwise, this is fine for most use cases:
    outfile.write_text(content, encoding="utf-8", errors="ignore")
