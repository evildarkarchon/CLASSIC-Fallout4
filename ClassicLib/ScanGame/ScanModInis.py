"""
This module analyzes and modifies game-related INI configuration files to ensure optimal game
performance, user experience, and adherence to desirable settings. It performs tasks such as
checking for specific console command settings that might affect startup time, evaluating VSync
settings across configuration files, applying required fixes, and logging messages for user
notification.

The module includes functionalities to:
- Identify problematic settings in INI files and notify users.
- Apply specific fixes to ensure compatibility and performance.
- Detect duplicate configuration files and notify users.
"""
from typing import TYPE_CHECKING, Any

from ClassicLib import GlobalRegistry
from ClassicLib.ScanGame.Config import ConfigFileCache

if TYPE_CHECKING:
    from pathlib import Path

# Constants for config settings
CONSOLE_COMMAND_SETTING = "sStartingConsoleCommand"
CONSOLE_COMMAND_SECTION = "General"
CONSOLE_COMMAND_NOTICE = (
    "In rare cases, this setting can slow down the initial game startup time for some players.\n"
    "You can test your initial startup time difference by removing this setting from the INI file.\n-----\n"
)

# List of files and their VSync settings to check
VSYNC_SETTINGS: list[tuple[str, str, str]] = [
    ("dxvk.conf", f"{GlobalRegistry.get_game()}.exe", "dxgi.syncInterval"),
    ("enblocal.ini", "ENGINE", "ForceVSync"),
    ("longloadingtimesfix.ini", "Limiter", "EnableVSync"),
    ("reshade.ini", "APP", "ForceVsync"),
    ("fallout4_test.ini", "CreationKit", "VSyncRender"),
    # highfpsphysicsfix.ini is handled separately since it has additional settings
]


async def scan_mod_inis_async() -> str:
    """
    Asynchronously check INI files for mods and perform necessary fixes or notify about potential issues.

    This async function analyzes INI configuration files associated with a game, looking for specific settings or
    conditions that can potentially impact game performance, startup time, or user settings. If specific
    conditions or discrepancies are found, it performs updates to the INI files, logs the changes, and collects
    notices for the user. The function also identifies duplicate INI files and verifies the presence of VSync
    settings across several configuration files. Uses async I/O operations to avoid blocking the event loop.

    Returns:
        str: A concatenated string of messages highlighting changes, issues, or notices for the user regarding
        the analyzed INI files.
    """
    message_list: list[str] = []
    config_files: ConfigFileCache = ConfigFileCache()

    # TODO: Maybe return a message that no ini files were found? (See also: TODO in ConfigFileCache)
    # if not config_files:
    #     pass

    # Check for console command settings that might slow down startup
    await check_starting_console_command_async(config_files, message_list)

    # Check for VSync settings in various files
    vsync_list: list[str] = await check_vsync_settings_async(config_files)

    # Note: FCX mode previously auto-fixed INI files here, but now operates in read-only mode.
    # Configuration issues are detected and reported by FCXModeHandler instead.

    # Report VSync settings if found
    if vsync_list:
        message_list.extend([
            "* NOTICE : VSYNC IS CURRENTLY ENABLED IN THE FOLLOWING FILES *\n",
            *vsync_list,
        ])

    # Report duplicate files if found
    check_duplicate_files(config_files, message_list)

    return "".join(message_list)


def scan_mod_inis() -> str:
    """
    Synchronous wrapper for scan_mod_inis_async for backward compatibility.

    This wrapper uses AsyncBridge to run the async function in a sync context,
    maintaining compatibility with existing code that expects a synchronous interface.

    Returns:
        str: A concatenated string of messages highlighting changes, issues, or notices for the user regarding
        the analyzed INI files.
    """
    from ClassicLib.AsyncBridge import AsyncBridge

    bridge = AsyncBridge.get_instance()
    return bridge.run_async(scan_mod_inis_async())


def check_starting_console_command(config_files: ConfigFileCache, message_list: list[str]) -> None:
    """Sync wrapper for backward compatibility."""
    from ClassicLib.AsyncBridge import AsyncBridge

    bridge = AsyncBridge.get_instance()
    return bridge.run_async(check_starting_console_command_async(config_files, message_list))


async def check_starting_console_command_async(config_files: ConfigFileCache, message_list: list[str]) -> None:
    """
    Checks for the presence of a specific console command setting in configuration files
    matching the current game's name, and updates the message list with relevant notices.

    Args:
        config_files: A cache of configuration files containing file paths and their
            corresponding sections and settings.
        message_list: A list of messages to be updated with notices if configuration files
            contain the specific console command setting.
    """
    game_lower: str = GlobalRegistry.get_game().lower()

    for file_lower, file_path in config_files.items():
        if file_lower.startswith(game_lower) and config_files.has(file_lower, CONSOLE_COMMAND_SECTION, CONSOLE_COMMAND_SETTING):
            message_list.extend([
                f"[!] NOTICE: {file_path} contains the *{CONSOLE_COMMAND_SETTING}* setting.\n",
                CONSOLE_COMMAND_NOTICE,
            ])


def check_vsync_settings(config_files: ConfigFileCache) -> list[str]:
    """Sync wrapper for backward compatibility."""
    from ClassicLib.AsyncBridge import AsyncBridge

    bridge = AsyncBridge.get_instance()
    return bridge.run_async(check_vsync_settings_async(config_files))


async def check_vsync_settings_async(config_files: ConfigFileCache) -> list[str]:
    """
    Checks the VSync settings in the given configuration files.

    This function iterates through a predefined list of VSYNC_SETTINGS to determine
    if VSync is enabled for specific files and settings. Additionally, it performs a specific
    check for the "highfpsphysicsfix.ini" configuration file to validate its VSync settings.

    Args:
        config_files (ConfigFileCache): A cache object containing the configuration
            files and their respective settings.

    Returns:
        list[str]: A list containing formatted strings that indicate which configuration
        files have VSync settings enabled.
    """
    vsync_list: list[str] = []

    # Check standard VSync settings
    for file_name, section, setting in VSYNC_SETTINGS:
        if await config_files.get_async(bool, file_name, section, setting):
            vsync_list.append(f"{config_files[file_name]} | SETTING: {setting}\n")

    # Check highfpsphysicsfix.ini separately
    if "highfpsphysicsfix.ini" in config_files and await config_files.get_async(bool, "highfpsphysicsfix.ini", "Main", "EnableVSync"):
        vsync_list.append(f"{config_files['highfpsphysicsfix.ini']} | SETTING: EnableVSync\n")

    return vsync_list


async def detect_ini_issue_async(
    config_files: ConfigFileCache,
    file_name_lower: str,
    section: str,
    setting: str,
    value_type: type,
    recommended_value: Any,
    condition_check: Any,
    description: str,
    severity: str = "warning",
) -> Any | None:
    """
    Detect a configuration issue in an INI file without modifying it.

    This function checks if a configuration setting meets a specific condition
    and, if so, creates a ConfigIssue report with the current value,
    recommended value, and description.

    Args:
        config_files: The configuration file cache used to check INI configurations.
        file_name_lower: The lowercase name of the configuration file to check.
        section: The section in the INI file where the setting resides.
        setting: The specific setting within the section to check.
        value_type: The expected type of the configuration value (str, bool, int, float).
        recommended_value: The value that should be set to resolve the issue.
        condition_check: A callable that takes the current value and returns True if
            there's an issue, False otherwise.
        description: Human-readable description of the issue.
        severity: Issue severity level ("error", "warning", "info"). Defaults to "warning".

    Returns:
        ConfigIssue object if an issue is detected, None otherwise.

    Example:
        ```no_run
        issue = await detect_ini_issue_async(
        config_files, "epo.ini", "Particles", "iMaxDesired", int, 5000,
        lambda val: int(val) > 5000,
        "High particle count can cause crashes"
        )```
    """
    # Check if file exists in cache
    if file_name_lower not in config_files:
        return None

    # Use ConfigFileCache.detect_issue() to detect the issue
    return await config_files.detect_issue(
        value_type,
        file_name_lower,
        section,
        setting,
        recommended_value,
        description,
        condition_check,
        severity,
    )


async def detect_all_ini_issues_async(config_files: ConfigFileCache) -> list[Any]:
    """
    Detect all configuration issues in INI files without modifying them.

    This function checks for all known INI configuration issues and returns
    a list of ConfigIssue objects describing each detected issue.

    Args:
        config_files: The configuration file cache used to check INI configurations.

    Returns:
        list[ConfigIssue]: List of detected configuration issues. Empty list if
            no issues found.

    Notes:
        Issues detected:
        - ESPExplorer hotkey commented out
        - EPO particle count too high (> 5000)
        - F4EE head parts locked (bUnlockHeadParts == 0)
        - F4EE face tints locked (bUnlockTints == 0)
        - High FPS Physics Fix loading screen FPS too low (< 600)
    """
    issues: list[Any] = []

    # ESPExplorer hotkey check
    if "espexplorer.ini" in config_files:
        issue = await detect_ini_issue_async(
            config_files,
            "espexplorer.ini",
            "General",
            "HotKey",
            str,
            "0x79",
            lambda val: "; F10" in str(val),
            "Hotkey is commented out and won't work. Change to hex code 0x79 for F10.",
        )
        if issue is not None:
            issues.append(issue)

    # EPO particle count check
    if "epo.ini" in config_files:
        issue = await detect_ini_issue_async(
            config_files,
            "epo.ini",
            "Particles",
            "iMaxDesired",
            int,
            5000,
            lambda val: int(val) > 5000,
            "High particle count can cause performance issues and crashes.",
        )
        if issue is not None:
            issues.append(issue)

    # F4EE settings checks
    if "f4ee.ini" in config_files:
        # Head parts unlock check
        issue = await detect_ini_issue_async(
            config_files,
            "f4ee.ini",
            "CharGen",
            "bUnlockHeadParts",
            int,
            1,
            lambda val: int(val) == 0,
            "Head parts are locked. Set to 1 to unlock all head parts.",
        )
        if issue is not None:
            issues.append(issue)

        # Face tints unlock check
        issue = await detect_ini_issue_async(
            config_files,
            "f4ee.ini",
            "CharGen",
            "bUnlockTints",
            int,
            1,
            lambda val: int(val) == 0,
            "Face tints are locked. Set to 1 to unlock all face tints.",
        )
        if issue is not None:
            issues.append(issue)

    # High FPS Physics Fix loading screen FPS check
    if "highfpsphysicsfix.ini" in config_files:
        issue = await detect_ini_issue_async(
            config_files,
            "highfpsphysicsfix.ini",
            "Limiter",
            "LoadingScreenFPS",
            float,
            600.0,
            lambda val: float(val) < 600.0,
            "Loading screen FPS is too low. Increase to 600.0 to prevent physics issues.",
        )
        if issue is not None:
            issues.append(issue)

    return issues


def check_duplicate_files(config_files: ConfigFileCache, message_list: list[str]) -> None:
    """
    Check for duplicate files in the configuration files and update the provided message list with
    information about the duplicates. It sorts duplicate files by their name for consistent output
    and appends formatted messages detailing the duplicates.

    Arguments:
        config_files (ConfigFileCache): Cache object containing file configuration details and
            a mapping of duplicate files.
        message_list (list[str]): A list to which formatted messages about duplicate files are appended.

    Raises:
        None
    Returns:
        None
    """
    if config_files.duplicate_files:
        all_duplicates: list[Path] = []

        # Collect paths from duplicate_files dictionary
        for paths in config_files.duplicate_files.values():
            all_duplicates.extend(paths)

        # Also add original files that have duplicates
        all_duplicates.extend([fp for f, fp in config_files.items() if f in config_files.duplicate_files])

        # Sort by filename for consistent output
        sorted_duplicates = sorted(all_duplicates, key=lambda p: p.name)

        message_list.extend([
            "* NOTICE : DUPLICATES FOUND OF THE FOLLOWING FILES *\n",
            *[f"{p!s}\n" for p in sorted_duplicates],
        ])
