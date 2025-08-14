import asyncio
import shutil
from pathlib import Path
from typing import Literal

from ClassicLib import GlobalRegistry, msg_error, msg_info, msg_success
from ClassicLib.Constants import YAML
from ClassicLib.ScanGame.CheckCrashgen import check_crashgen_settings
from ClassicLib.ScanGame.CheckXsePlugins import check_xse_plugins
from ClassicLib.ScanGame.Config import TEST_MODE
from ClassicLib.ScanGame.ScanGameCore import ScanGameCore
from ClassicLib.ScanGame.ScanModInis import scan_mod_inis
from ClassicLib.ScanGame.WryeCheck import scan_wryecheck
from ClassicLib.SetupCoordinator import SetupCoordinator
from ClassicLib.YamlSettingsCache import yaml_settings


# ================================================
# CHECK ERRORS IN LOG FILES FOR GIVEN FOLDER
# ================================================
def get_scan_game_core() -> ScanGameCore:
    """Get singleton ScanGameCore instance from GlobalRegistry."""
    # ScanGameCore's __new__ method handles singleton via GlobalRegistry
    return ScanGameCore()


def check_log_errors(folder_path: Path | str) -> str:
    """
    Sync adapter for async check_log_errors.

    Inspects log files within a specified folder for recorded errors. Errors matching the provided
    catch criteria are highlighted, whereas those designated to be ignored in the settings or from
    specific files are omitted. The function aggregates error messages and provides a detailed
    report string containing relevant log error data.

    Args:
        folder_path (Path | str): Path to the folder containing log files for error inspection.

    Returns:
        str: A detailed report of all detected errors in the relevant log files, if any.
    """
    core = get_scan_game_core()
    return asyncio.run(core.check_log_errors(folder_path))


# ================================================
# SHARED SCAN FUNCTIONS
# ================================================
def get_scan_settings() -> tuple[str, dict[str, str], Path | None]:
    """
    Gets common settings used by mod scanning functions.

    Returns:
        tuple: (xse_acronym, xse_scriptfiles, mod_path)
    """
    # Delegate to singleton core for consistency
    core = get_scan_game_core()
    return core.get_scan_settings()


def get_issue_messages(xse_acronym: str, mode: str) -> dict[str, list[str]]:
    """
    Returns standardized issue messages for mod scan reports.

    Args:
        xse_acronym: Script extender acronym from settings
        mode: Either "unpacked" or "archived"

    Returns:
        dict: Dictionary of issue types and their message templates
    """
    # Delegate to singleton core for consistency
    core = get_scan_game_core()
    return core.get_issue_messages(xse_acronym, mode)


# ================================================
# CHECK ALL UNPACKED / LOOSE MOD FILES
# ================================================
# noinspection DuplicatedCode
def scan_mods_unpacked() -> str:
    """
    Sync adapter for async scan_mods_unpacked.

    Scans loose mod files for issues and moves redundant files to backup location.
    Identifies problems with file formats, dimensions, and detects potentially problematic files.

    Returns:
        str: Detailed report of scan results.
    """
    core = get_scan_game_core()
    return asyncio.run(core.scan_mods_unpacked())


def scan_mods_archived() -> str:
    """
    Sync adapter for async scan_mods_archived.

    Analyzes archived BA2 mod files to identify potential issues, such as incorrect
    formats, invalid dimensions, or unexpected content, and generates a detailed
    report about the detected anomalies. Ensures compliance with specific
    modding requirements and alerts users to potential crashes or compatibility
    issues.

    Returns:
        str: A report detailing the findings, including errors and warnings
        regarding issues found in the BA2 files. The report contains recommendations
        for rectifying the problems or guidance for further action.

    Raises:
        OSError: If the function fails to open or read a BA2 file during analysis.
        subprocess.SubprocessError: If there is an error while running `BSArch`
        commands for file dumping or listing.
    """
    core = get_scan_game_core()
    return asyncio.run(core.scan_mods_archived())


# ================================================
# BACKUP / RESTORE / REMOVE
# ================================================
# noinspection PyPep8Naming
def game_files_manage(classic_list: str, mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
    """
    Manages game files by performing backup, restore, or removal operations. The function interacts
    with the game's directory and modifies files based on the specified mode.

    Args:
        classic_list: str
            The name of the list specifying which files need to be managed. This parameter
            is used to identify target files or directories in the game's folder.
        mode: Literal["BACKUP", "RESTORE", "REMOVE"], optional
            The operation mode to be performed on the files. Available options are:
            - "BACKUP": Creates a backup of the specified files.
            - "RESTORE": Restores the files from a backup to the game folder.
            - "REMOVE": Deletes the specified files from the game folder. Defaults to "BACKUP".

    Raises:
        FileNotFoundError: If the specified game folder is not found or is not a valid
            directory.
        PermissionError: If there are file permission issues preventing the operation
            from completing.
    """
    # Constants
    BACKUP_DIR = "CLASSIC Backup/Game Files"
    SUCCESS_PREFIX = "SUCCESSFULLY"
    ERROR_PREFIX = "ERROR :"
    ADMIN_SUGGESTION = "    TRY RUNNING CLASSIC.EXE IN ADMIN MODE TO RESOLVE THIS PROBLEM.\n"

    # Get paths and settings
    game_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")
    manage_list_setting: list[str] | None = yaml_settings(list[str], YAML.Game, classic_list)
    manage_list: list[str] = manage_list_setting if isinstance(manage_list_setting, list) else []

    # Validate game path
    if game_path is None:
        raise FileNotFoundError("Game folder not found")

    # Set up backup path
    backup_path: Path = Path(f"{BACKUP_DIR}/{classic_list}")
    backup_path.mkdir(parents=True, exist_ok=True)

    # Extract list name for display purposes
    list_name: str = classic_list.split(maxsplit=1)[-1]

    def matches_managed_file(file_name: str) -> bool:
        """Check if the file name matches any item in the manage list."""
        return any(item.lower() in file_name.lower() for item in manage_list)

    def handle_permission_error(operation: str) -> None:
        """Print consistent error message for permission errors."""
        msg_error(f"{ERROR_PREFIX} UNABLE TO {operation} {list_name} FILES DUE TO FILE PERMISSIONS!\n{ADMIN_SUGGESTION}")

    def copy_file_or_directory(source: Path, destination: Path) -> None:
        """Copy a file or directory, handling existing destinations appropriately."""
        try:
            if source.is_file():
                shutil.copy2(source, destination)
            elif source.is_dir():
                if destination.is_dir():
                    shutil.rmtree(destination)
                elif destination.is_file():
                    destination.unlink(missing_ok=True)
                shutil.copytree(source, destination)
        except PermissionError:
            msg_error(f"Permission denied copying {source} to {destination}")
            raise
        except (OSError, FileNotFoundError, FileExistsError) as e:
            msg_error(f"Failed to copy {source} to {destination}: {e}")
            raise
        except Exception as e:
            msg_error(f"Unexpected error copying {source} to {destination}: {e}")
            raise

    # Perform the requested operation
    try:
        if mode == "BACKUP":
            msg_info(f"CREATING A BACKUP OF {list_name} FILES, PLEASE WAIT...")
            for file in game_path.glob("*"):
                if matches_managed_file(file.name):
                    copy_file_or_directory(file, backup_path / file.name)
            msg_success(f"{SUCCESS_PREFIX} CREATED A BACKUP OF {list_name} FILES\n")

        elif mode == "RESTORE":
            msg_info(f"RESTORING {list_name} FILES FROM A BACKUP, PLEASE WAIT...")
            for file in game_path.glob("*"):
                if matches_managed_file(file.name):
                    source_file = backup_path / file.name
                    if source_file.exists():
                        copy_file_or_directory(source_file, file)
            msg_success(f"{SUCCESS_PREFIX} RESTORED {list_name} FILES TO THE GAME FOLDER\n")

        elif mode == "REMOVE":
            msg_info(f"REMOVING {list_name} FILES FROM YOUR GAME FOLDER, PLEASE WAIT...")
            for file in game_path.glob("*"):
                if matches_managed_file(file.name):
                    if file.is_file():
                        file.unlink(missing_ok=True)
                    elif file.is_dir():
                        shutil.rmtree(file)  # Using rmtree instead of os.removedirs for more reliable deletion
            msg_success(f"{SUCCESS_PREFIX} REMOVED {list_name} FILES FROM THE GAME FOLDER\n")

    except PermissionError:
        handle_permission_error(mode)


# ================================================
# COMBINED RESULTS
# ================================================
def game_combined_result() -> str:
    """
    Generates a combined result summarizing game-related checks and scans.

    This function performs a series of validations and scans on the game files
    and documentation directories. It consolidates plugin checks, crash generation
    settings, log errors, and additional configuration validations into a single
    text result. The returned result can be used for diagnostics or reporting
    purposes.

    Returns:
        str: A string summarizing the results of all performed checks and scans.
        If the necessary paths or directories are not available, an empty string
        is returned.
    """
    docs_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Docs")
    game_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")

    if not (game_path and docs_path):
        return ""
    return "".join((
        check_xse_plugins(),
        check_crashgen_settings(),
        check_log_errors(docs_path),
        check_log_errors(game_path),
        scan_wryecheck(),
        scan_mod_inis(),
    ))


def mods_combined_result() -> str:  # KEEP THESE SEPARATE SO THEY ARE NOT INCLUDED IN AUTOSCAN REPORTS
    """
    Combines the results of scanning unpacked and archived mods.

    This function first scans for unpacked mods and checks their status. If the unpacked mods
    path is not provided, it quickly returns a relevant message. Otherwise, it appends the
    results of scanning the archived mods to the result of the unpacked mods scan and provides
    a combined status report.

    Returns:
        str: The combined results of the unpacked and archived mods scans, or a message
        indicating that the mods folder path is not provided.
    """
    # Get mod path to verify it exists before running scans
    _, _, mod_path = get_scan_settings()

    if not mod_path:
        return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_Path_Missing"))

    # Run both scans and combine results
    unpacked = scan_mods_unpacked()
    archived = scan_mods_archived()
    return unpacked + archived


def main() -> None:
    """Main entry point for game scanning."""

    # Initialize application using SetupCoordinator
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=False)
    coordinator.run_initial_setup()

    if TEST_MODE:
        write_combined_results()
    else:
        msg_info(game_combined_result())
        msg_info(mods_combined_result())
        game_files_manage("Backup ENB")


def write_combined_results() -> None:
    """
    Writes combined results of game and mods into a markdown report file.

    This function aggregates results from two separate processes: the game result
    and the mods result. It then writes their combined output into a markdown
    file named "CLASSIC GFS Report.md". The report file is encoded in UTF-8 and
    any errors during encoding are ignored.
    """
    game_result: str = game_combined_result()
    mods_result: str = mods_combined_result()
    gfs_report: Path = Path("CLASSIC GFS Report.md")
    with gfs_report.open("w", encoding="utf-8", errors="ignore") as scan_report:
        scan_report.write(game_result + mods_result)


if __name__ == "__main__":
    main()
    input("Press Enter to continue...")
