from typing import TYPE_CHECKING, Any

from ClassicLib import GlobalRegistry
from ClassicLib.Logger import logger
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


def scan_mod_inis() -> str:
    """
    Check INI files for mods and perform necessary fixes or notify about potential issues.

    This function analyzes INI configuration files associated with a game, looking for specific settings or
    conditions that can potentially impact game performance, startup time, or user settings. If specific
    conditions or discrepancies are found, it performs updates to the INI files, logs the changes, and collects
    notices for the user. The function also identifies duplicate INI files and verifies the presence of VSync
    settings across several configuration files.

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
    check_starting_console_command(config_files, message_list)

    # Check for VSync settings in various files
    vsync_list: list[str] = check_vsync_settings(config_files)

    # Apply fixes to various INI files
    apply_all_ini_fixes(config_files, message_list)

    # Report VSync settings if found
    if vsync_list:
        message_list.extend([
            "* NOTICE : VSYNC IS CURRENTLY ENABLED IN THE FOLLOWING FILES *\n",
            *vsync_list,
        ])

    # Report duplicate files if found
    check_duplicate_files(config_files, message_list)

    return "".join(message_list)


def check_starting_console_command(config_files: ConfigFileCache, message_list: list[str]) -> None:
    """Check for console command settings that might slow down game startup."""
    game_lower: str = GlobalRegistry.get_game().lower()

    for file_lower, file_path in config_files.items():
        if file_lower.startswith(game_lower) and config_files.has(file_lower, CONSOLE_COMMAND_SECTION, CONSOLE_COMMAND_SETTING):
            message_list.extend([
                f"[!] NOTICE: {file_path} contains the *{CONSOLE_COMMAND_SETTING}* setting.\n",
                CONSOLE_COMMAND_NOTICE,
            ])


def check_vsync_settings(config_files: ConfigFileCache) -> list[str]:
    """Check for VSync settings in various configuration files."""
    vsync_list: list[str] = []

    # Check standard VSync settings
    for file_name, section, setting in VSYNC_SETTINGS:
        if config_files.get(bool, file_name, section, setting):
            vsync_list.append(f"{config_files[file_name]} | SETTING: {setting}\n")

    # Check highfpsphysicsfix.ini separately
    if "highfpsphysicsfix.ini" in config_files and config_files.get(bool, "highfpsphysicsfix.ini", "Main", "EnableVSync"):
        vsync_list.append(f"{config_files['highfpsphysicsfix.ini']} | SETTING: EnableVSync\n")

    return vsync_list


def apply_ini_fix(  # noqa: PLR0913
    config_files: ConfigFileCache,
    file_name: str,
    section: str,
    setting: str,
    value: Any,
    fix_description: str,
    message_list: list[str],
) -> None:
    """Apply a fix to an INI file and log the change."""
    config_files.set(type(value), file_name, section, setting, value)
    logger.info(f"> > > PERFORMED {fix_description} FIX FOR {config_files[file_name]}")
    message_list.append(f"> Performed {fix_description.title()} Fix For : {config_files[file_name]}\n")


def apply_all_ini_fixes(config_files: ConfigFileCache, message_list: list[str]) -> None:
    """Apply all necessary fixes to INI files."""
    # Fix ESPExplorer hotkey
    if "; F10" in config_files.get_strict(str, "espexplorer.ini", "General", "HotKey"):
        apply_ini_fix(config_files, "espexplorer.ini", "General", "HotKey", "0x79", "INI HOTKEY", message_list)

    # Fix EPO particle count
    if config_files.get_strict(int, "epo.ini", "Particles", "iMaxDesired") > 5000:
        apply_ini_fix(config_files, "epo.ini", "Particles", "iMaxDesired", 5000, "INI PARTICLE COUNT", message_list)

    # Fix F4EE settings if present
    if "f4ee.ini" in config_files:
        # Fix head parts unlock setting
        if config_files.get(int, "f4ee.ini", "CharGen", "bUnlockHeadParts") == 0:
            apply_ini_fix(config_files, "f4ee.ini", "CharGen", "bUnlockHeadParts", 1, "INI HEAD PARTS UNLOCK", message_list)

        # Fix face tints unlock setting
        if config_files.get(int, "f4ee.ini", "CharGen", "bUnlockTints") == 0:
            apply_ini_fix(config_files, "f4ee.ini", "CharGen", "bUnlockTints", 1, "INI FACE TINTS UNLOCK", message_list)

    # Fix highfpsphysicsfix.ini loading screen FPS if present
    if (
        "highfpsphysicsfix.ini" in config_files
        and config_files.get_strict(float, "highfpsphysicsfix.ini", "Limiter", "LoadingScreenFPS") < 600.0
    ):
        apply_ini_fix(config_files, "highfpsphysicsfix.ini", "Limiter", "LoadingScreenFPS", 600.0, "INI LOADING SCREEN FPS", message_list)


def check_duplicate_files(config_files: ConfigFileCache, message_list: list[str]) -> None:
    """Check for and report duplicate INI files."""
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
