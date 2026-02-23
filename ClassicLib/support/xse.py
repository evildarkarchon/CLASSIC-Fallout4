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

Phase 7 Additions:
- XSE Address Library validation using Rust XseChecker
- ENB detection using Rust EnbChecker
- FCX Mode gating (validation only runs when checking own installation)
- GlobalRegistry storage for validation results
- Both sync and async variants for dual-interface pattern
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ClassicLib.core.async_runtime import run_sync
from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import GlobalRegistry, get_game
from ClassicLib.integration.factory import get_file_io
from ClassicLib.io.yaml import yaml_settings
from ClassicLib.messaging import msg_warning

if TYPE_CHECKING:
    from collections.abc import Iterable

    from classic_scangame import EnbValidationResult, GameVersion


def _read_bytes(path: Path) -> bytes:
    """Read file bytes synchronously via runtime boundary helper.

    Args:
        path: Path to the file to read.

    Returns:
        The file contents as bytes.

    """
    io_core = get_file_io()
    return run_sync(io_core.read_bytes(path))


def _read_lines(path: Path) -> list[str]:
    """Read file lines synchronously via runtime boundary helper.

    Args:
        path: Path to the file to read.

    Returns:
        List of lines from the file.

    """
    io_core = get_file_io()
    return run_sync(io_core.read_lines(path))


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


def _is_fcx_mode_enabled() -> bool:
    """Check if FCX Mode is enabled (checking own installation).

    Per CONTEXT.md: Validation only runs when FCX Mode is enabled.
    FCX Mode indicates the user is checking their own game installation,
    not analyzing crash logs from others.

    Returns:
        bool: True if FCX Mode is enabled, False otherwise.

    """
    return yaml_settings(bool, YAML.Settings, "FCX_Mode", False)


def _get_rust_game_version() -> GameVersion:
    """Map the detected VersionInfo to the Rust GameVersion enum.

    Uses the Version Registry as the single source of truth. The VersionInfo
    short_name (OG, NG, AE, VR) is mapped to the corresponding GameVersion
    variant. Falls back to GameVersion.Original when detection fails.

    Returns:
        GameVersion: The corresponding Rust GameVersion enum value.

    """
    from classic_scangame import GameVersion
    from ClassicLib.support.versions import get_detected_version_info

    short_name_map: dict[str, GameVersion] = {
        "VR": GameVersion.Vr,
        "OG": GameVersion.Original,
        "NG": GameVersion.NextGen,
        "AE": GameVersion.AnniversaryEdition,
    }

    version_info = get_detected_version_info()
    if version_info is None:
        return GameVersion.Original

    return short_name_map.get(version_info.short_name, GameVersion.Original)


# noinspection DuplicatedCode
def xse_check_integrity() -> str:
    """Perform an integrity check for the XSE installation by verifying associated configurations,
    address library, and log file for potential issues based on predefined error patterns.

    If FCX Mode is enabled, this function also uses the Rust XseChecker to validate
    the Address Library installation and stores the result in GlobalRegistry.

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
    game_name: str = get_game()

    # Get error patterns to search for in logs
    error_patterns: list[str] | None = yaml_settings(list[str], YAML.Main, "catch_log_errors")
    if not isinstance(error_patterns, list):
        raise TypeError("Error patterns setting must be a list")

    # Get XSE-related settings
    xse_config: dict[Any, Any] = _load_xse_config()

    # Check address library using Rust XseChecker if FCX Mode is enabled
    if _is_fcx_mode_enabled():
        rust_message = _check_address_library_rust(xse_config.get("plugins_folder"))
        if rust_message:
            messages.append(rust_message)
    else:
        # Fall back to simple file existence check
        _check_address_library(xse_config["adlib_file"], game_name, messages)

    # Check XSE installation and log file
    _check_xse_installation(
        xse_config["log_file"], xse_config["acronym"], xse_config["full_name"], xse_config["latest_version"], error_patterns, messages
    )

    return "".join(messages)


async def xse_check_integrity_async() -> str:
    """Async version of XSE integrity check.

    Uses run_in_executor for Rust calls to prevent blocking event loop.
    Only runs validation when FCX Mode is enabled.

    Returns:
        str: Formatted validation message.

    """
    from ClassicLib.io.yaml.async_.core import yaml_settings_async

    logger.debug("- - - INITIATED XSE INTEGRITY CHECK (ASYNC)")
    messages: list[str] = []

    # Load configuration settings
    game_name: str = get_game()

    # Get error patterns to search for in logs
    error_patterns: list[str] | None = await yaml_settings_async(list[str], YAML.Main, "catch_log_errors")
    if not isinstance(error_patterns, list):
        raise TypeError("Error patterns setting must be a list")

    # Get XSE-related settings
    xse_config: dict[Any, Any] = await _load_xse_config_async()

    # Check address library using Rust XseChecker if FCX Mode is enabled
    fcx_mode = await yaml_settings_async(bool, YAML.Settings, "FCX_Mode", False)
    if fcx_mode:
        loop = asyncio.get_running_loop()
        rust_message = await loop.run_in_executor(None, _check_address_library_rust, xse_config.get("plugins_folder"))
        if rust_message:
            messages.append(rust_message)
    else:
        # Fall back to simple file existence check
        _check_address_library(xse_config["adlib_file"], game_name, messages)

    # Check XSE installation and log file (sync for now - file I/O)
    await _check_xse_installation_async(
        xse_config["log_file"], xse_config["acronym"], xse_config["full_name"], xse_config["latest_version"], error_patterns, messages
    )

    return "".join(messages)


def _check_address_library_rust(plugins_folder: str | None) -> str:
    """Check Address Library using Rust XseChecker.

    This function uses the Rust XseChecker to validate that the correct
    Address Library version is installed for the current game version.

    Args:
        plugins_folder: Path to the F4SE/SKSE plugins folder.

    Returns:
        str: Formatted validation message from Rust checker.

    """
    try:
        from classic_scangame import ValidationResult, XseChecker

        if not plugins_folder:
            GlobalRegistry.register(GlobalRegistry.Keys.XSE_VALID, False)
            return "XSE plugins path not configured.\n"

        # Determine game version for XseChecker
        is_vr = GlobalRegistry.is_vr_version()
        game_version = _get_rust_game_version()

        checker = XseChecker(Path(plugins_folder), is_vr, game_version)
        result = checker.check()
        message = checker.validate()

        # Store result in registry
        is_valid = result == ValidationResult.CorrectVersion
        GlobalRegistry.register(GlobalRegistry.Keys.XSE_VALID, is_valid)

        return message  # noqa: TRY300
    except (ImportError, RuntimeError, ValueError, OSError) as e:
        logger.error(f"Rust XSE validation error: {e}")
        GlobalRegistry.register(GlobalRegistry.Keys.XSE_VALID, False)
        return f"XSE validation error: {e}\n"


def _load_xse_config() -> dict[str, str | Path | None]:
    """Load the configuration related to the game's XSE (eXtensible Script Engine) details and
    various associated components from a YAML settings file.

    This function retrieves and organizes information such as the acronym, full name,
    latest version, log file path, and address library file path for the game's XSE.

    Returns:
        dict: A dictionary containing the following keys:
            - acronym (str | None): The acronym associated with the game's XSE.
            - full_name (str | None): The full name of the game's XSE.
            - latest_version (str | None): The latest version of the game's XSE.
            - log_file (str | None): The path to the XSE log file.
            - adlib_file (Path | None): A `Path` object representing the game's address library file, or None if not found.
            - plugins_folder (str | None): Path to the F4SE/SKSE plugins folder for Rust validation.

    """
    # Get XSE static metadata from Version Registry.
    # XSE acronym/full_name/version are identical across FO4_OG / FO4_NG / FO4_AE;
    # FO4_OG is used as the canonical non-VR source for these static fields.
    from ClassicLib.support.versions import get_version_registry

    registry = get_version_registry()
    is_vr = GlobalRegistry.is_vr_version()
    version_info = registry.get_by_id("FO4_VR" if is_vr else "FO4_OG")
    xse_config = version_info.xse if version_info else None

    xse_acronym: str | None = xse_config.acronym if xse_config else None
    xse_full_name: str | None = xse_config.full_name if xse_config else None
    xse_latest_version: str | None = xse_config.compatible_version if xse_config else None

    # Runtime paths still come from YAML cache
    xse_log_file: str | None = yaml_settings(str, YAML.Game_Local, "Game_Info.Docs_File_XSE")
    adlib_file_str: str | None = yaml_settings(str, YAML.Game_Local, "Game_Info.Game_File_AddressLib")
    plugins_folder: str | None = yaml_settings(str, YAML.Game_Local, "Game_Info.Game_Folder_Plugins")

    adlib_file: Path | None = Path(adlib_file_str) if adlib_file_str else None

    return {
        "acronym": xse_acronym,
        "full_name": xse_full_name,
        "latest_version": xse_latest_version,
        "log_file": xse_log_file,
        "adlib_file": adlib_file,
        "plugins_folder": plugins_folder,
    }


async def _load_xse_config_async() -> dict[str, str | Path | None]:
    """Async version of _load_xse_config.

    Returns:
        dict: XSE configuration dictionary.

    """
    from ClassicLib.io.yaml.async_.core import yaml_settings_async
    from ClassicLib.support.versions import get_version_registry

    # Get XSE static metadata from Version Registry.
    # XSE acronym/full_name/version are identical across FO4_OG / FO4_NG / FO4_AE;
    # FO4_OG is used as the canonical non-VR source for these static fields.
    registry = get_version_registry()
    is_vr = GlobalRegistry.is_vr_version()
    version_info = registry.get_by_id("FO4_VR" if is_vr else "FO4_OG")
    xse_config = version_info.xse if version_info else None

    xse_acronym: str | None = xse_config.acronym if xse_config else None
    xse_full_name: str | None = xse_config.full_name if xse_config else None
    xse_latest_version: str | None = xse_config.compatible_version if xse_config else None

    # Runtime paths still come from YAML cache
    xse_log_file: str | None = await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Docs_File_XSE")
    adlib_file_str: str | None = await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Game_File_AddressLib")
    plugins_folder: str | None = await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Game_Folder_Plugins")

    adlib_file: Path | None = Path(adlib_file_str) if adlib_file_str else None

    return {
        "acronym": xse_acronym,
        "full_name": xse_full_name,
        "latest_version": xse_latest_version,
        "log_file": xse_log_file,
        "adlib_file": adlib_file,
        "plugins_folder": plugins_folder,
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
    log_contents: list[str] = _read_lines(log_path)

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


async def _check_xse_installation_async(
    log_file: str | None, acronym: str, full_name: str, latest_version: str, error_patterns: list[str], messages: list[str]
) -> None:
    """Async version of _check_xse_installation.

    Args:
        log_file: Path to the log file.
        acronym: XSE acronym (e.g., "F4SE").
        full_name: XSE full name.
        latest_version: Latest version string.
        error_patterns: Error patterns to search for.
        messages: List to append messages to.

    """
    from ClassicLib.io.yaml.async_.core import yaml_settings_async

    if not isinstance(log_file, str | Path):
        game_name = GlobalRegistry.get_game()
        messages.append(f"❌ Value for {acronym.lower()}.log is invalid or missing from CLASSIC {game_name} Local.yaml!\n-----\n")
        return

    log_path: Path = Path(log_file)
    if not log_path.exists():  # noqa: ASYNC240
        messages.extend([
            f"❌ CAUTION : *{acronym.lower()}.log* FILE IS MISSING FROM YOUR DOCUMENTS FOLDER! \n",
            f"   You need to run the game at least once with {acronym.lower()}_loader.exe \n",
            "    After that, try running CLASSIC again! \n-----\n",
        ])
        return

    # XSE is installed
    messages.append(f"✔️ REQUIRED: *{full_name}* is installed! \n-----\n")

    # Check XSE version and log for errors (async file read)
    io_core = get_file_io()
    log_contents: list[str] = await io_core.read_lines(log_path)

    # Check version
    if str(latest_version) in log_contents[0]:
        messages.append(f"✔️ You have the latest version of *{full_name}*! \n-----\n")
    else:
        warn_outdated: str | None = await yaml_settings_async(str, YAML.Game, "Warnings_XSE.Warn_Outdated")
        if not isinstance(warn_outdated, str):
            raise TypeError("XSE outdated warning message must be a string")
        messages.append(warn_outdated)

    # Check for errors in log
    error_lines: list[str] = [line for line in log_contents if any(error.lower() in line.lower() for error in error_patterns)]

    if error_lines:
        messages.append(f"#❌ CAUTION : {acronym}.log REPORTS THE FOLLOWING ERRORS #\n")
        messages.extend([f"ERROR > {line.strip()} \n-----\n" for line in error_lines])


# ============ ENB VALIDATION FUNCTIONS ============


def enb_check_presence() -> str:
    """Check ENB installation using Rust EnbChecker.

    Only runs when FCX Mode is enabled. Stores result
    in GlobalRegistry.Keys.ENB_PRESENT.

    **Workflow integration:** This function is called during FCX Mode
    initialization, AFTER game path detection succeeds. Typical call site:
    - FCX Mode init in classic_interface.py or setup_fcx_mode()
    - After GlobalRegistry.Keys.GAME_PATH is populated

    Returns:
        str: Formatted message about ENB status.

    """
    if not _is_fcx_mode_enabled():
        logger.debug("FCX Mode disabled, skipping ENB validation")
        return ""

    game_path = GlobalRegistry.get(GlobalRegistry.Keys.GAME_PATH)
    if not game_path:
        game_path = yaml_settings(str, YAML.Game_Local, "Game_Info.Root_Folder_Game")

    if not game_path:
        GlobalRegistry.register(GlobalRegistry.Keys.ENB_PRESENT, False)
        return "Game path not configured.\n"

    try:
        from classic_scangame import EnbChecker

        checker = EnbChecker(str(game_path))
        result = checker.validate()

        is_present = result.is_present()
        GlobalRegistry.register(GlobalRegistry.Keys.ENB_PRESENT, is_present)

        return checker.format_message(result)
    except (ImportError, RuntimeError, ValueError, OSError) as e:
        logger.error(f"ENB check error: {e}")
        GlobalRegistry.register(GlobalRegistry.Keys.ENB_PRESENT, False)
        return f"ENB check error: {e}\n"


async def enb_check_presence_async() -> str:
    """Async version of ENB presence check using Rust EnbChecker.

    Uses run_in_executor for Rust calls to prevent blocking event loop.
    Only runs when FCX Mode is enabled.

    **Workflow integration:** Called during async FCX Mode initialization,
    AFTER game path detection. Typical call site:
    - Async FCX Mode setup
    - After find_game_path_async() completes

    Returns:
        str: Formatted message about ENB status.

    """
    from ClassicLib.io.yaml.async_.core import yaml_settings_async

    fcx_mode = await yaml_settings_async(bool, YAML.Settings, "FCX_Mode", False)
    if not fcx_mode:
        logger.debug("FCX Mode disabled, skipping ENB validation")
        return ""

    game_path = GlobalRegistry.get(GlobalRegistry.Keys.GAME_PATH)
    if not game_path:
        game_path = await yaml_settings_async(str, YAML.Game_Local, "Game_Info.Root_Folder_Game")

    if not game_path:
        GlobalRegistry.register(GlobalRegistry.Keys.ENB_PRESENT, False)
        return "Game path not configured.\n"

    loop = asyncio.get_running_loop()

    try:

        def _check_enb() -> tuple[EnbValidationResult, str]:
            from classic_scangame import EnbChecker

            checker = EnbChecker(str(game_path))
            result = checker.validate()
            return result, checker.format_message(result)

        result, message = await loop.run_in_executor(None, _check_enb)

        is_present = result.is_present()
        GlobalRegistry.register(GlobalRegistry.Keys.ENB_PRESENT, is_present)

        return message  # noqa: TRY300
    except (ImportError, RuntimeError, ValueError, OSError) as e:
        logger.error(f"ENB check error: {e}")
        GlobalRegistry.register(GlobalRegistry.Keys.ENB_PRESENT, False)
        return f"ENB check error: {e}\n"


# ============ XSE HASH CHECKING (UNCHANGED) ============


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
    from ClassicLib.support.versions import get_detected_version_info, get_version_registry

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
    game_folder_scripts: str | None = yaml_settings(str, YAML.Game_Local, "Game_Info.Game_Folder_Scripts")
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
                file_contents = _read_bytes(script_path)
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
