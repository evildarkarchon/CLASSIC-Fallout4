# =========== CHECK GAME XSE SCRIPTS -> GET PATH AND HASHES ===========
import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from ClassicLib import Constants, GlobalRegistry, msg_warning
from ClassicLib.FileIOCore import read_bytes_sync, read_lines_sync
from ClassicLib.Logger import logger
from ClassicLib.YamlSettingsCache import yaml_settings


class Tokens:
    XSE_HASHED_SCRIPTS_TYPE_ERROR_RAISED: bool = False


# noinspection DuplicatedCode
def xse_check_integrity() -> str:
    """
    Performs an integrity check for the XSE framework, ensuring the necessary configurations,
    libraries, and installation files are correctly set up and free of critical errors. This
    function analyzes configuration settings, validates the address library, and examines logs for
    patterns indicating issues. Results are compiled and returned as a single message string.

    Returns:
        str: A comprehensive message summarizing the results of the integrity check, including
        detected issues or confirmation of successful checks.
    """
    logger.debug("- - - INITIATED XSE INTEGRITY CHECK")
    messages: list[str] = []

    # Load configuration settings
    game_vr: str = GlobalRegistry.get_vr()
    game_name: str = GlobalRegistry.get_game()

    # Get error patterns to search for in logs
    error_patterns: list[str] | None = yaml_settings(list[str], Constants.YAML.Main, "catch_log_errors")
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
def _load_xse_config(game_vr: str) -> dict:
    """Load XSE configuration settings from YAML files"""
    xse_acronym: str | None = yaml_settings(str, Constants.YAML.Game, f"Game{game_vr}_Info.XSE_Acronym")
    xse_full_name: str | None = yaml_settings(str, Constants.YAML.Game, f"Game{game_vr}_Info.XSE_FullName")
    xse_latest_version: str | None = yaml_settings(str, Constants.YAML.Game, f"Game{game_vr}_Info.XSE_Ver_Latest")
    xse_log_file: str | None = yaml_settings(str, Constants.YAML.Game_Local, f"Game{game_vr}_Info.Docs_File_XSE")
    adlib_file_str: str | None = yaml_settings(str, Constants.YAML.Game_Local, f"Game{game_vr}_Info.Game_File_AddressLib")

    adlib_file: Path | None = Path(adlib_file_str) if adlib_file_str else None

    return {
        "acronym": xse_acronym,
        "full_name": xse_full_name,
        "latest_version": xse_latest_version,
        "log_file": xse_log_file,
        "adlib_file": adlib_file,
    }


def _check_address_library(adlib_file: Path | None, game_name: str, messages: list[str]) -> None:
    """Check if Address Library for Script Extender is installed"""
    if isinstance(adlib_file, str | Path):
        if Path(adlib_file).exists():
            messages.append("✔️ REQUIRED: *Address Library* for Script Extender is installed! \n-----\n")
        else:
            warn_adlib: str | None = yaml_settings(str, Constants.YAML.Game, "Warnings_MODS.Warn_ADLIB_Missing")
            if not isinstance(warn_adlib, str):
                raise TypeError("Address library warning message must be a string")
            messages.append(warn_adlib)
    else:
        messages.append(f"❌ Value for Address Library is invalid or missing from CLASSIC {game_name} Local.yaml!\n-----\n")


def _check_xse_installation(  # noqa: PLR0913
    log_file: str | None, acronym: str, full_name: str, latest_version: str, error_patterns: list[str], messages: list[str]
) -> None:
    """Check XSE installation status, version, and log for errors"""
    if not isinstance(log_file, str | Path):
        messages.append(f"❌ Value for {acronym.lower()}.log is invalid or missing from CLASSIC Local.yaml!\n-----\n")
        return

    log_path: Path = Path(cast("str", log_file))
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
        warn_outdated: str | None = yaml_settings(str, Constants.YAML.Game, "Warnings_XSE.Warn_Outdated")
        if not isinstance(warn_outdated, str):
            raise TypeError("XSE outdated warning message must be a string")
        messages.append(warn_outdated)

    # Check for errors in log
    error_lines: list[str] = [line for line in log_contents if any(error.lower() in line.lower() for error in error_patterns)]

    if error_lines:
        messages.append(f"#❌ CAUTION : {acronym}.log REPORTS THE FOLLOWING ERRORS #\n")
        messages.extend([f"ERROR > {line.strip()} \n-----\n" for line in error_lines])


def xse_check_hashes() -> str:
    """
    Checks the integrity of script files by comparing their hashes with the expected values.

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
    """Get expected script hashes from config."""
    xse_hashedscripts = yaml_settings(dict[str, str], Constants.YAML.Game, "Game_Info.XSE_HashedScripts")
    if not isinstance(xse_hashedscripts, dict):
        if not Tokens.XSE_HASHED_SCRIPTS_TYPE_ERROR_RAISED:
            Tokens.XSE_HASHED_SCRIPTS_TYPE_ERROR_RAISED = True
            raise TypeError("Expected script hashes configuration must be a dictionary")
        # If the error has been raised before, return an empty dict to avoid repeated errors
        # and allow the program to continue or handle it further up the call stack.
        return {}
    return xse_hashedscripts


def _get_scripts_folder_path() -> str:
    """Get scripts folder path from config."""
    game_folder_scripts: str | None = yaml_settings(
        str, Constants.YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Game_Folder_Scripts"
    )
    if game_folder_scripts is None:
        raise ValueError("Game scripts folder path cannot be None")
    return game_folder_scripts


def _calculate_script_hashes(script_filenames: Iterable[str], scripts_folder: str) -> dict[str, str | None]:
    """Calculate actual hashes for script files."""
    actual_hashes: dict[str, str | None] = {}

    for filename in script_filenames:
        script_path: Path = Path(rf"{scripts_folder}\{filename}")

        if script_path.is_file():
            try:
                file_contents = read_bytes_sync(script_path)
                # Algo should match the one used for Database YAML!
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
    """Generate result message based on hash comparison."""
    message_list: list[str] = []
    has_missing_scripts = False
    has_mismatched_scripts = False

    # Compare hashes and collect messages
    for filename, expected_hash in expected_hashes.items():
        actual_hash = actual_hashes.get(filename)

        if actual_hash is None:
            message_list.append(f"❌ CAUTION : {filename} Script Extender file is missing from your game Scripts folder! \n-----\n")
            has_missing_scripts = True
        elif expected_hash != actual_hash:
            message_list.append(f"[!] CAUTION : {filename} Script Extender file is outdated or overriden by another mod! \n-----\n")
            has_mismatched_scripts = True

    # Add warning messages from configuration if needed
    if has_missing_scripts:
        warn_missing: str | None = yaml_settings(str, Constants.YAML.Game, "Warnings_XSE.Warn_Missing")
        if not isinstance(warn_missing, str):
            raise TypeError("Missing scripts warning message must be a string")
        message_list.append(warn_missing)

    if has_mismatched_scripts:
        warn_mismatch: str | None = yaml_settings(str, Constants.YAML.Game, "Warnings_XSE.Warn_Mismatch")
        if not isinstance(warn_mismatch, str):
            raise TypeError("Mismatched scripts warning message must be a string")
        message_list.append(warn_mismatch)

    # All checks passed
    if not has_missing_scripts and not has_mismatched_scripts:
        message_list.append("✔️ All Script Extender files have been found and accounted for! \n-----\n")

    return "".join(message_list)
