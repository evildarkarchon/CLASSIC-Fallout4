# =========== CHECK GAME XSE SCRIPTS -> GET PATH AND HASHES ===========
"""Module for validating the integrity of the XSE installation and associated configurations.

This module contains functions for checking the integrity of the XSE installation,
verifying configuration settings, validating script file hashes, and identifying issues
in associated log files. It utilizes external settings loaded from YAML files and performs
comparisons to expected values.

The primary purposes of this module are:
- To ensure the user's XSE installation is configured properly.
- To verify the presence and validity of required dependencies, such as Address Library.
- To check for mismatches in hashes for script files.
"""

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import get_game, get_vr
from ClassicLib.io.files import read_bytes_sync, read_lines_sync
from ClassicLib.io.yaml import yaml_settings
from ClassicLib.messaging import msg_warning


class Tokens:
    """Represent a collection of token-related configurations or constants.

    This class defines and stores constants or configuration values related to token
    management, which can assist in managing states or properties associated with
    tokens within a given system.

    Attributes:
        XSE_HASHED_SCRIPTS_TYPE_ERROR_RAISED (bool): Indicates whether a type error
            was raised in the context of hashed scripts processing.

    """

    XSE_HASHED_SCRIPTS_TYPE_ERROR_RAISED: bool = False


# noinspection DuplicatedCode
def xse_check_integrity() -> str:
    """Perform an integrity check for the XSE installation by verifying associated configurations,
    address library, and log file for potential issues based on predefined error patterns.

    Returns a string compiled from all generated messages during the checking process, summarizing
    the integrity status of the XSE installation.

    Raises:
        TypeError: If error patterns from the settings configuration are not of type list.

    Returns:
        str: A summary of messages created during the XSE integrity check.

    """
    logger.debug("- - - INITIATED XSE INTEGRITY CHECK")
    messages: list[str] = []

    # Load configuration settings
    game_vr: str = get_vr()
    game_name: str = get_game()

    # Get error patterns to search for in logs
    error_patterns: list[str] | None = yaml_settings(list[str], YAML.Main, "catch_log_errors")
    if not isinstance(error_patterns, list):
        raise TypeError("Error patterns setting must be a list")

    # Get XSE-related settings
    xse_config: dict[Any, Any] = _load_xse_config(game_vr)

    # Check address library
    _check_address_library(xse_config["adlib_file"], game_name, messages)

    # Check XSE installation and log file
    _check_xse_installation(
        xse_config["log_file"], xse_config["acronym"], xse_config["full_name"], xse_config["latest_version"], error_patterns, messages
    )

    return "".join(messages)


# noinspection PyUnusedLocal
def _load_xse_config(game_vr: str) -> dict[str, str | Path | None]:
    """Load the configuration related to a game's XSE (eXtensible Script Engine) details and
    various associated components from a YAML settings file.

    This function retrieves and organizes information such as the acronym, full name,
    latest version, log file path, and address library file path for the specified game's XSE.

    Args:
        game_vr (str): The unique identifier for the game version for which the XSE configuration should be loaded.

    Returns:
        dict: A dictionary containing the following keys:
            - acronym (str | None): The acronym associated with the game's XSE.
            - full_name (str | None): The full name of the game's XSE.
            - latest_version (str | None): The latest version of the game's XSE.
            - log_file (str | None): The path to the XSE log file.
            - adlib_file (Path | None): A `Path` object representing the game's address library file, or None if not found.

    """
    xse_acronym: str | None = yaml_settings(str, YAML.Game, f"Game{game_vr}_Info.XSE_Acronym")
    xse_full_name: str | None = yaml_settings(str, YAML.Game, f"Game{game_vr}_Info.XSE_FullName")
    xse_latest_version: str | None = yaml_settings(str, YAML.Game, f"Game{game_vr}_Info.XSE_Ver_Latest")
    xse_log_file: str | None = yaml_settings(str, YAML.Game_Local, f"Game{game_vr}_Info.Docs_File_XSE")
    adlib_file_str: str | None = yaml_settings(str, YAML.Game_Local, f"Game{game_vr}_Info.Game_File_AddressLib")

    adlib_file: Path | None = Path(adlib_file_str) if adlib_file_str else None

    return {
        "acronym": xse_acronym,
        "full_name": xse_full_name,
        "latest_version": xse_latest_version,
        "log_file": xse_log_file,
        "adlib_file": adlib_file,
    }


def _check_address_library(adlib_file: Path | None, game_name: str, messages: list[str]) -> None:
    """Check the validity and existence of an Address Library file required for a game and updates the
    provided messages list with a status message accordingly.

    Args:
        adlib_file (Path | None): The path to the Address Library file, or None if not specified.
        game_name (str): The name of the game for which the Address Library is being validated.
        messages (list[str]): A list of messages to update with the validation results.

    Raises:
        TypeError: If the warning message for a missing Address Library is not a string.

    """
    if isinstance(adlib_file, str | Path):
        if Path(adlib_file).exists():
            messages.append("✔️ REQUIRED: *Address Library* for Script Extender is installed! \n-----\n")
        else:
            warn_adlib: str | None = yaml_settings(str, YAML.Game, "Warnings_MODS.Warn_ADLIB_Missing")
            if not isinstance(warn_adlib, str):
                raise TypeError("Address library warning message must be a string")
            messages.append(warn_adlib)
    else:
        messages.append(f"❌ Value for Address Library is invalid or missing from CLASSIC {game_name} Local.yaml!\n-----\n")


def _check_xse_installation(
    log_file: str | None, acronym: str, full_name: str, latest_version: str, error_patterns: list[str], messages: list[str]
) -> None:
    """Check the installation and error states of XSE (eXtendable System Environment)
    based on log files, and updates the messages list accordingly to indicate
    installation status, version status, or log errors.

    Args:
        log_file (str | None): The path to the log file. If None or invalid,
            an error message is appended to `messages`.
        acronym (str): The acronym representing the system being checked.
        full_name (str): The full name of the XSE system for proper reporting in
            messages.
        latest_version (str): The latest supported version of the XSE system to
            verify against the log contents.
        error_patterns (list[str]): A list of error patterns to search for in the
            log file. If matched, errors are appended to the `messages`.
        messages (list[str]): A mutable list to which status messages, error
            reports, or warnings will be appended.

    Raises:
        TypeError: If the outdated warning message specified in the YAML settings
            is not a string. This occurs when attempting to report warnings for
            an outdated version in the log.

    """
    if not isinstance(log_file, str | Path):
        from ClassicLib import GlobalRegistry

        game_name = GlobalRegistry.get_game()
        messages.append(f"❌ Value for {acronym.lower()}.log is invalid or missing from CLASSIC {game_name} Local.yaml!\n-----\n")
        return

    log_path: Path = Path(log_file)
    if not log_path.exists():
        messages.extend([
            f"❌ CAUTION : *{acronym.lower()}.log* FILE IS MISSING FROM YOUR DOCUMENTS FOLDER! \n",
            f"   You need to run the game at least once with {acronym.lower()}_loader.exe \n",
            "    After that, try running CLASSIC again! \n-----\n",
        ])
        return

    # XSE is installed
    messages.append(f"✔️ REQUIRED: *{full_name}* is installed! \n-----\n")

    # Check XSE version and log for errors
    log_contents: list[str] = read_lines_sync(log_path)

    # Check version
    if str(latest_version) in log_contents[0]:
        messages.append(f"✔️ You have the latest version of *{full_name}*! \n-----\n")
    else:
        warn_outdated: str | None = yaml_settings(str, YAML.Game, "Warnings_XSE.Warn_Outdated")
        if not isinstance(warn_outdated, str):
            raise TypeError("XSE outdated warning message must be a string")
        messages.append(warn_outdated)

    # Check for errors in log
    error_lines: list[str] = [line for line in log_contents if any(error.lower() in line.lower() for error in error_patterns)]

    if error_lines:
        messages.append(f"#❌ CAUTION : {acronym}.log REPORTS THE FOLLOWING ERRORS #\n")
        messages.extend([f"ERROR > {line.strip()} \n-----\n" for line in error_lines])


def xse_check_hashes() -> str:
    """Check the integrity of script files by comparing their hashes with the expected values.

    This function validates that script files in a specified folder match their expected
    hash values. It reads the configuration for expected hashes, calculates the actual
    hashes, and generates a result message indicating the status of the comparison.

    Returns:
        str: A result message indicating whether all hashes match or identifying any
        inconsistencies.

    """
    logger.debug("- - - INITIATED XSE FILE HASH CHECK")

    # Load configuration values
    expected_hashes = _get_expected_script_hashes()
    scripts_folder = _get_scripts_folder_path()

    # Check script files
    actual_hashes = _calculate_script_hashes(expected_hashes.keys(), scripts_folder)

    # Compare hashes and build messages
    return _generate_result_message(expected_hashes, actual_hashes)


def _get_expected_script_hashes() -> dict[str, str]:
    """Retrieve expected script hashes for the detected game version.

    Gets script hashes for the detected/configured game version from the
    VersionRegistry. The hashes must match the specific game version installed,
    not just any valid version.

    Returns:
        dict[str, str]: A dictionary containing the expected script hashes,
                        mapping script filenames to SHA-256 hashes for the
                        detected game version.

    Raises:
        ValueError: If the game version cannot be detected and no fallback
                    hashes are available.

    """
    from ClassicLib.VersionRegistry import get_detected_version_info, get_version_registry

    # Get the detected game version
    version_info = get_detected_version_info()
    registry = get_version_registry()

    if version_info is not None:
        # Use version-specific hashes
        hashes = registry.get_script_hashes_for_version(version_info)
        if hashes:
            return hashes

    # Fallback: If version detection fails, we can't validate properly.
    # Return empty dict which will skip validation rather than give false positives.
    logger.warning("Could not detect game version for XSE script validation")
    return {}


def _get_scripts_folder_path() -> str:
    """Retrieve the path for the game's scripts folder.

    This function fetches the folder path where the game's scripts are located
    by utilizing configuration settings and the global registry. The path is
    fetched based on the current game's virtual reality configuration. If the
    retrieved path is None, the function raises a ValueError indicating that the
    scripts folder path cannot be None.

    Raises:
        ValueError: If the game scripts folder path retrieved from the configuration
            is None.

    Returns:
        str: The path of the game's scripts folder.

    """
    game_folder_scripts: str | None = yaml_settings(str, YAML.Game_Local, f"Game{get_vr()}_Info.Game_Folder_Scripts")
    if game_folder_scripts is None:
        raise ValueError("Game scripts folder path cannot be None")
    return game_folder_scripts


def _calculate_script_hashes(script_filenames: Iterable[str], scripts_folder: str) -> dict[str, str | None]:
    """Calculate and returns the SHA-256 hash values for a list of script files. If a file cannot
    be read or does not exist, its hash value will be set to None. The method iterates through
    the provided script filenames, verifies their existence, and calculates their hashes.
    Exceptions that occur during file reading are logged and handled gracefully.

    Args:
        script_filenames (Iterable[str]): A list of script filenames for which the hashes are
            to be calculated.
        scripts_folder (str): The path to the folder containing the script files.

    Returns:
        dict[str, str | None]: A dictionary where the keys are the script filenames and the
            values are the SHA-256 hash values of the corresponding files or None if the file
            cannot be read or does not exist.

    """
    actual_hashes: dict[str, str | None] = {}

    for filename in script_filenames:
        script_path: Path = Path(rf"{scripts_folder}\{filename}")

        if script_path.is_file():
            try:
                file_contents = read_bytes_sync(script_path)
                # Algo should match the one used for Database YAML!
                # noinspection PyTypeChecker
                file_hash = hashlib.sha256(file_contents).hexdigest()
                actual_hashes[filename] = file_hash
            except (OSError, FileNotFoundError, PermissionError) as e:
                logger.debug(f"Error reading file {script_path}: {e}")
                msg_warning(f"Cannot read script file: {script_path.name}")
                actual_hashes[filename] = None
        else:
            actual_hashes[filename] = None

    return actual_hashes


def _generate_result_message(expected_hashes: dict[str, str], actual_hashes: dict[str, str | None]) -> str:
    """Generate a result message based on comparisons of expected script hashes and actual script hashes.

    This function examines each filename-hash pair from the expected data against the actual data provided.
    It identifies missing or mismatched script extender files, compiles related warning messages,
    and summarizes the findings into a single output string.

    Args:
        expected_hashes (dict[str, str]): A dictionary where keys are filenames and values are the expected
            hashes of script extender files for the detected game version.
        actual_hashes (dict[str, str | None]): A dictionary where keys are filenames and values are the actual
            hashes of script extender files, or `None` if the file is missing.

    Returns:
        str: A single formatted string summarizing the presence and validity of all script extender files.

    Raises:
        TypeError: If the warning messages obtained from the configuration are not strings.

    """
    message_list: list[str] = []
    has_missing_scripts = False
    has_mismatched_scripts = False

    # Compare hashes and collect messages
    for filename, expected_hash in expected_hashes.items():
        actual_hash = actual_hashes.get(filename)

        if actual_hash is None:
            message_list.append(f"❌ CAUTION : {filename} Script Extender file is missing from your game Scripts folder! \n-----\n")
            has_missing_scripts = True
        elif actual_hash != expected_hash:
            message_list.append(f"[!] CAUTION : {filename} Script Extender file is outdated or overriden by another mod! \n-----\n")
            has_mismatched_scripts = True

    # Add warning messages from configuration if needed
    if has_missing_scripts:
        warn_missing: str | None = yaml_settings(str, YAML.Game, "Warnings_XSE.Warn_Missing")
        if not isinstance(warn_missing, str):
            raise TypeError("Missing scripts warning message must be a string")
        message_list.append(warn_missing)

    if has_mismatched_scripts:
        warn_mismatch: str | None = yaml_settings(str, YAML.Game, "Warnings_XSE.Warn_Mismatch")
        if not isinstance(warn_mismatch, str):
            raise TypeError("Mismatched scripts warning message must be a string")
        message_list.append(warn_mismatch)

    # All checks passed
    if not has_missing_scripts and not has_mismatched_scripts:
        message_list.append("✔️ All Script Extender files have been found and accounted for! \n-----\n")

    return "".join(message_list)
