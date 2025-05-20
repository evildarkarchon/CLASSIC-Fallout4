import os
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any, Literal

from CLASSIC_Main import initialize, main_generate_required
from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.ScanGame.CheckCrashgen import check_crashgen_settings
from ClassicLib.ScanGame.CheckXsePlugins import check_xse_plugins
from ClassicLib.ScanGame.Config import TEST_MODE
from ClassicLib.ScanGame.ScanModInis import scan_mod_inis
from ClassicLib.ScanGame.WryeCheck import scan_wryecheck
from ClassicLib.Util import open_file_with_encoding
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


# ================================================
# CHECK ERRORS IN LOG FILES FOR GIVEN FOLDER
# ================================================
def check_log_errors(folder_path: Path | str) -> str:
    """
    Inspects log files within a specified folder for recorded errors. Errors matching the provided
    catch criteria are highlighted, whereas those designated to be ignored in the settings or from
    specific files are omitted. The function aggregates error messages and provides a detailed
    report string containing relevant log error data.
    Args:
        folder_path (Path | str): Path to the folder containing log files for error inspection.
    Returns:
        str: A detailed report of all detected errors in the relevant log files, if any.
    """

    def get_setting_as_list(setting_type: type[list[str]], yaml_type: YAML, key: str) -> list[str]:
        """Retrieve a setting from YAML and ensure it's a list of strings."""
        setting: list[str] | None = yaml_settings(setting_type, yaml_type, key)
        return setting if isinstance(setting, list) else []

    def normalize_list(items: list[str]) -> list[str]:
        """Convert all strings in a list to lowercase."""
        return [item.lower() for item in items] if items else []

    def format_error_report(file_path: Path, errors: list[str]) -> list[str]:
        """Format the error report for a specific log file."""
        return [
            "[!] CAUTION : THE FOLLOWING LOG FILE REPORTS ONE OR MORE ERRORS!\n",
            "[ Errors do not necessarily mean that the mod is not working. ]\n",
            f"\nLOG PATH > {file_path}\n",
            *errors,
            f"\n* TOTAL NUMBER OF DETECTED LOG ERRORS * : {len(errors)}\n",
        ]

    # Convert string path to Path object if needed
    if isinstance(folder_path, str):
        folder_path = Path(folder_path)

    # Get YAML settings
    catch_errors: list[str] = normalize_list(get_setting_as_list(list[str], YAML.Main, "catch_log_errors"))
    ignore_files: list[str] = normalize_list(get_setting_as_list(list[str], YAML.Main, "exclude_log_files"))
    ignore_errors: list[str] = normalize_list(get_setting_as_list(list[str], YAML.Main, "exclude_log_errors"))

    error_report: list[str] = []

    # Find valid log files (excluding crash logs)
    valid_log_files: list[Path] = [file for file in folder_path.glob("*.log") if "crash-" not in file.name]

    for log_file_path in valid_log_files:
        # Skip files that should be ignored
        if any(part in str(log_file_path).lower() for part in ignore_files):
            continue

        try:
            with open_file_with_encoding(log_file_path) as log_file:
                log_lines = log_file.readlines()

                # Filter for relevant errors
                detected_errors = [
                    f"ERROR > {line}"
                    for line in log_lines
                    if any(error in line.lower() for error in catch_errors) and all(ignore not in line.lower() for ignore in ignore_errors)
                ]

                if detected_errors:
                    error_report.extend(format_error_report(log_file_path, detected_errors))

        except OSError:
            error_message = f"❌ ERROR : Unable to scan this log file :\n  {log_file_path}"
            error_report.append(error_message)
            logger.warning(f"> ! > DETECT LOG ERRORS > UNABLE TO SCAN : {log_file_path}")

    return "".join(error_report)


# ================================================
# CHECK ALL UNPACKED / LOOSE MOD FILES
# ================================================
# noinspection DuplicatedCode
def scan_mods_unpacked() -> str:
    """
    Scans loose mod files for issues and moves redundant files to backup location.
    Identifies problems with file formats, dimensions, and detects potentially problematic files.

    Returns:
        str: Detailed report of scan results.
    """
    # Initialize lists for reporting
    message_list: list[str] = [
        "=================== MOD FILES SCAN ====================\n",
        "========= RESULTS FROM UNPACKED / LOOSE FILES =========\n",
    ]

    # Initialize sets for collecting different issue types
    issue_lists: dict[str, set[str]] = {
        "cleanup": set(),
        "animdata": set(),
        "tex_dims": set(),
        "tex_frmt": set(),
        "snd_frmt": set(),
        "xse_file": set(),
        "previs": set(),
    }

    # Get settings
    xse_acronym_setting: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
    xse_scriptfiles_setting: dict[str, str] | None = yaml_settings(
        dict[str, str], YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_HashedScripts"
    )
    xse_acronym: str = xse_acronym_setting if isinstance(xse_acronym_setting, str) else "XSE"
    xse_scriptfiles: dict[str, str] = xse_scriptfiles_setting if isinstance(xse_scriptfiles_setting, dict) else {}

    # Setup paths
    backup_path: Path = Path("CLASSIC Backup/Cleaned Files")
    if not TEST_MODE:
        backup_path.mkdir(parents=True, exist_ok=True)

    mod_path: Path | None = classic_settings(Path, "MODS Folder Path")
    if not mod_path:
        return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_Path_Missing"))
    if not mod_path.is_dir():
        return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_Path_Invalid"))

    print("✔️ MODS FOLDER PATH FOUND! PERFORMING INITIAL MOD FILES CLEANUP...")

    # First pass: cleanup and detect animation data
    filter_names: tuple = ("readme", "changes", "changelog", "change log")
    for root, dirs, files in mod_path.walk(top_down=False):
        root_main: Path = root.relative_to(mod_path).parent
        has_anim_data = False

        # Process directories
        for dirname in dirs:
            dirname_lower: str = dirname.lower()
            if not has_anim_data and dirname_lower == "animationfiledata":
                has_anim_data = True
                issue_lists["animdata"].add(f"  - {root_main}\n")
            elif dirname_lower == "fomod":
                fomod_folder_path: Path = root / dirname
                relative_path: Path = fomod_folder_path.relative_to(mod_path)
                new_folder_path: Path = backup_path / relative_path
                if not TEST_MODE:
                    shutil.move(fomod_folder_path, new_folder_path)
                issue_lists["cleanup"].add(f"  - {relative_path}\n")

        # Process files for cleanup
        for filename in files:
            filename_lower: str = filename.lower()
            if filename_lower.endswith(".txt") and any(name in filename_lower for name in filter_names):
                file_path: Path = root / filename
                relative_path = file_path.relative_to(mod_path)
                new_file_path: Path = backup_path / relative_path
                if not TEST_MODE:
                    new_file_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(file_path, new_file_path)
                issue_lists["cleanup"].add(f"  - {relative_path}\n")

    print("✔️ CLEANUP COMPLETE! NOW ANALYZING ALL UNPACKED/LOOSE MOD FILES...")

    # Second pass: analyze files for issues
    for root, _, files in mod_path.walk(top_down=False):
        root_main = root.relative_to(mod_path).parent
        has_previs_files = has_xse_files = False

        for filename in files:
            filename_lower = filename.lower()
            file_path = root / filename
            relative_path = file_path.relative_to(mod_path)
            file_ext = file_path.suffix.lower()

            # Check DDS dimensions
            if file_ext == ".dds":
                with file_path.open("rb") as dds_file:
                    dds_data: bytes = dds_file.read(20)
                if dds_data[:4] == b"DDS ":
                    width: Any = struct.unpack("<I", dds_data[12:16])[0]
                    height: Any = struct.unpack("<I", dds_data[16:20])[0]
                    if width % 2 != 0 or height % 2 != 0:
                        issue_lists["tex_dims"].add(f"  - {relative_path} ({width}x{height})")

            # Check for invalid texture formats
            elif file_ext in {".tga", ".png"} and "BodySlide" not in file_path.parts:
                issue_lists["tex_frmt"].add(f"  - {file_ext[1:].upper()} : {relative_path}\n")

            # Check for invalid sound formats
            elif file_ext in {".mp3", ".m4a"}:
                issue_lists["snd_frmt"].add(f"  - {file_ext[1:].upper()} : {relative_path}\n")

            # Check for XSE files
            elif (
                not has_xse_files
                and any(filename_lower == key.lower() for key in xse_scriptfiles)
                and "workshop framework" not in str(root).lower()
                and f"Scripts\\{filename}" in str(file_path)
            ):
                has_xse_files = True
                issue_lists["xse_file"].add(f"  - {root_main}\n")

            # Check for previs files
            elif not has_previs_files and filename_lower.endswith((".uvd", "_oc.nif")):
                has_previs_files = True
                issue_lists["previs"].add(f"  - {root_main}\n")

    # Build the report
    issue_messages: dict[str, list[str]] = {
        "xse_file": [
            f"\n# ⚠️ FOLDERS CONTAIN COPIES OF *{xse_acronym}* SCRIPT FILES ⚠️\n",
            "▶️ Any mods with copies of original Script Extender files\n",
            "  may cause script related problems or crashes.\n\n",
        ],
        "previs": [
            "\n# ⚠️ FOLDERS CONTAIN LOOSE PRECOMBINE / PREVIS FILES ⚠️\n",
            "▶️ Any mods that contain custom precombine/previs files\n",
            "  should load after the PRP.esp plugin from Previs Repair Pack (PRP).\n",
            "  Otherwise, see if there is a PRP patch available for these mods.\n\n",
        ],
        "tex_dims": [
            "\n# ⚠️ DDS DIMENSIONS ARE NOT DIVISIBLE BY 2 ⚠️\n",
            "▶️ Any mods that have texture files with incorrect dimensions\n",
            "  are very likely to cause a *Texture (DDS) Crash*. For further details,\n",
            "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
        ],
        "tex_frmt": [
            "\n# ❓ TEXTURE FILES HAVE INCORRECT FORMAT, SHOULD BE DDS ❓\n",
            "▶️ Any files with an incorrect file format will not work.\n",
            "  Mod authors should convert these files to their proper game format.\n",
            "  If possible, notify the original mod authors about these problems.\n\n",
        ],
        "snd_frmt": [
            "\n# ❓ SOUND FILES HAVE INCORRECT FORMAT, SHOULD BE XWM OR WAV ❓\n",
            "▶️ Any files with an incorrect file format will not work.\n",
            "  Mod authors should convert these files to their proper game format.\n",
            "  If possible, notify the original mod authors about these problems.\n\n",
        ],
        "animdata": [
            "\n# ❓ FOLDERS CONTAIN CUSTOM ANIMATION FILE DATA ❓\n",
            "▶️ Any mods that have their own custom Animation File Data\n",
            "  may rarely cause an *Animation Corruption Crash*. For further details,\n",
            "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
        ],
        "cleanup": ["\n# 📄 DOCUMENTATION FILES MOVED TO 'CLASSIC Backup\\Cleaned Files' 📄\n"],
    }

    # Add found issues to message list
    for issue_type, items in issue_lists.items():
        if items:
            message_list.extend(issue_messages[issue_type])
            message_list.extend(sorted(items))

    return "".join(message_list)


def scan_mods_archived() -> str:
    """
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
    message_list: list[str] = ["\n========== RESULTS FROM ARCHIVED / BA2 FILES ==========\n"]

    # Initialize sets for collecting different issue types
    issue_lists: dict[str, set[str]] = {
        "ba2_frmt": set(),
        "animdata": set(),
        "tex_dims": set(),
        "tex_frmt": set(),
        "snd_frmt": set(),
        "xse_file": set(),
        "previs": set(),
    }

    # Get settings
    xse_acronym_setting: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
    xse_scriptfiles_setting: dict[str, str] | None = yaml_settings(
        dict[str, str], YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_HashedScripts"
    )
    xse_acronym: str = xse_acronym_setting if isinstance(xse_acronym_setting, str) else ""
    xse_scriptfiles: dict[str, str] = xse_scriptfiles_setting if isinstance(xse_scriptfiles_setting, dict) else {}

    # Setup paths
    bsarch_path: Path = Path.cwd() / "CLASSIC Data/BSArch.exe"
    mod_path: Path | None = classic_settings(Path, "MODS Folder Path")

    # Validate paths
    if not mod_path:
        return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_Path_Missing"))
    if not mod_path.exists():
        return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_Path_Invalid"))
    if not bsarch_path.exists():
        return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_BSArch_Missing"))

    print("✔️ ALL REQUIREMENTS SATISFIED! NOW ANALYZING ALL BA2 MOD ARCHIVES...")

    # Process BA2 files
    for root, _, files in mod_path.walk(top_down=False):
        for filename in files:
            filename_lower: str = filename.lower()
            if not filename_lower.endswith(".ba2") or filename_lower == "prp - main.ba2":
                continue

            file_path: Path = root / filename

            # Read BA2 header
            try:
                with file_path.open("rb") as f:
                    header: bytes = f.read(12)
            except OSError:
                print("Failed to read file:", filename)
                continue

            # Check BA2 format
            if header[:4] != b"BTDX" or header[8:] not in {b"DX10", b"GNRL"}:
                issue_lists["ba2_frmt"].add(f"  - {filename} : {header!s}\n")
                continue

            if header[8:] == b"DX10":
                # Process texture-format BA2
                command_dump: tuple = (bsarch_path, file_path, "-dump")
                archive_dump: subprocess.CompletedProcess[str] = subprocess.run(
                    command_dump, shell=True, capture_output=True, text=True, check=False
                )

                if archive_dump.returncode != 0:
                    print("BSArch command failed:", archive_dump.returncode, archive_dump.stderr)
                    continue

                output_split: list[str] = archive_dump.stdout.split("\n\n")
                if output_split[-1].startswith("Error:"):
                    print("BSArch command failed:", output_split[-1], archive_dump.stderr)
                    continue

                # Process texture information
                for file_block in output_split[4:]:
                    if not file_block:
                        continue

                    block_split: list[str] = file_block.split("\n", 3)

                    # Check texture format
                    if "Ext: dds" not in block_split[1]:
                        issue_lists["tex_frmt"].add(f"  - {block_split[0].rsplit('.', 1)[-1].upper()} : {filename} > {block_split[0]}\n")
                        continue

                    # Check texture dimensions
                    _, width, _, height, _ = block_split[2].split(maxsplit=4)
                    if (width.isdecimal() and int(width) % 2 != 0) or (height.isdecimal() and int(height) % 2 != 0):
                        issue_lists["tex_dims"].add(f"  - {width}x{height} : {filename} > {block_split[0]}")

            else:
                # Process general-format BA2
                command_list: tuple = (bsarch_path, file_path, "-list")
                archive_list: subprocess.CompletedProcess[str] = subprocess.run(
                    command_list, shell=True, capture_output=True, text=True, check=False
                )

                if archive_list.returncode != 0:
                    print("BSArch command failed:", archive_list.returncode, archive_list.stderr)
                    continue

                # Process file list
                output_split = archive_list.stdout.lower().split("\n")
                has_previs_files = has_anim_data = has_xse_files = False

                for file in output_split[15:]:
                    # Check sound formats
                    if file.endswith((".mp3", ".m4a")):
                        issue_lists["snd_frmt"].add(f"  - {file[-3:].upper()} : {filename} > {file}\n")

                    # Check animation data
                    elif not has_anim_data and "animationfiledata" in file:
                        has_anim_data = True
                        issue_lists["animdata"].add(f"  - {filename}\n")

                    # Check XSE files
                    elif (
                        not has_xse_files
                        and any(f"scripts\\{key.lower()}" in file for key in xse_scriptfiles)
                        and "workshop framework" not in str(root).lower()
                    ):
                        has_xse_files = True
                        issue_lists["xse_file"].add(f"  - {filename}\n")

                    # Check previs files
                    elif not has_previs_files and file.endswith((".uvd", "_oc.nif")):
                        has_previs_files = True
                        issue_lists["previs"].add(f"  - {filename}\n")

    # Build the report
    issue_messages: dict[str, list[str]] = {
        "xse_file": [
            f"\n# ⚠️ BA2 ARCHIVES CONTAIN COPIES OF *{xse_acronym}* SCRIPT FILES ⚠️\n",
            "▶️ Any mods with copies of original Script Extender files\n",
            "  may cause script related problems or crashes.\n\n",
        ],
        "previs": [
            "\n# ⚠️ BA2 ARCHIVES CONTAIN CUSTOM PRECOMBINE / PREVIS FILES ⚠️\n",
            "▶️ Any mods that contain custom precombine/previs files\n",
            "  should load after the PRP.esp plugin from Previs Repair Pack (PRP).\n",
            "  Otherwise, see if there is a PRP patch available for these mods.\n\n",
        ],
        "tex_dims": [
            "\n# ⚠️ DDS DIMENSIONS ARE NOT DIVISIBLE BY 2 ⚠️\n",
            "▶️ Any mods that have texture files with incorrect dimensions\n",
            "  are very likely to cause a *Texture (DDS) Crash*. For further details,\n",
            "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
        ],
        "tex_frmt": [
            "\n# ❓ TEXTURE FILES HAVE INCORRECT FORMAT, SHOULD BE DDS ❓\n",
            "▶️ Any files with an incorrect file format will not work.\n",
            "  Mod authors should convert these files to their proper game format.\n",
            "  If possible, notify the original mod authors about these problems.\n\n",
        ],
        "snd_frmt": [
            "\n# ❓ SOUND FILES HAVE INCORRECT FORMAT, SHOULD BE XWM OR WAV ❓\n",
            "▶️ Any files with an incorrect file format will not work.\n",
            "  Mod authors should convert these files to their proper game format.\n",
            "  If possible, notify the original mod authors about these problems.\n\n",
        ],
        "animdata": [
            "\n# ❓ BA2 ARCHIVES CONTAIN CUSTOM ANIMATION FILE DATA ❓\n",
            "▶️ Any mods that have their own custom Animation File Data\n",
            "  may rarely cause an *Animation Corruption Crash*. For further details,\n",
            "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
        ],
        "ba2_frmt": [
            "\n# ❓ BA2 ARCHIVES HAVE INCORRECT FORMAT, SHOULD BE BTDX-GNRL OR BTDX-DX10 ❓\n",
            "▶️ Any files with an incorrect file format will not work.\n",
            "  Mod authors should convert these files to their proper game format.\n",
            "  If possible, notify the original mod authors about these problems.\n\n",
        ],
    }

    # Add found issues to message list
    for issue_type, items in issue_lists.items():
        if items:
            message_list.extend(issue_messages[issue_type])
            message_list.extend(sorted(items))

    return "".join(message_list)


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
    SUCCESS_PREFIX = "✔️ SUCCESSFULLY"
    ERROR_PREFIX = "❌ ERROR :"
    ADMIN_SUGGESTION = "    TRY RUNNING CLASSIC.EXE IN ADMIN MODE TO RESOLVE THIS PROBLEM.\n"

    # Get paths and settings
    game_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")
    manage_list_setting: list[str] | None = yaml_settings(list[str], YAML.Game, classic_list)
    manage_list: list[str] = manage_list_setting if isinstance(manage_list_setting, list) else []

    # Validate game path
    if game_path is None or not game_path.is_dir():
        raise FileNotFoundError("Game folder not found or is not a valid directory")

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
        print(f"{ERROR_PREFIX} UNABLE TO {operation} {list_name} FILES DUE TO FILE PERMISSIONS!")
        print(ADMIN_SUGGESTION)

    def copy_file_or_directory(source: Path, destination: Path) -> None:
        """Copy a file or directory, handling existing destinations appropriately."""
        if source.is_file():
            shutil.copy2(source, destination)
        elif source.is_dir():
            if destination.is_dir():
                shutil.rmtree(destination)
            elif destination.is_file():
                destination.unlink(missing_ok=True)
            shutil.copytree(source, destination)

    # Perform the requested operation
    try:
        if mode == "BACKUP":
            print(f"CREATING A BACKUP OF {list_name} FILES, PLEASE WAIT...")
            for file in game_path.glob("*"):
                if matches_managed_file(file.name):
                    copy_file_or_directory(file, backup_path / file.name)
            print(f"{SUCCESS_PREFIX} CREATED A BACKUP OF {list_name} FILES\n")

        elif mode == "RESTORE":
            print(f"RESTORING {list_name} FILES FROM A BACKUP, PLEASE WAIT...")
            for file in game_path.glob("*"):
                if matches_managed_file(file.name):
                    source_file = backup_path / file.name
                    if source_file.exists():
                        copy_file_or_directory(source_file, file)
            print(f"{SUCCESS_PREFIX} RESTORED {list_name} FILES TO THE GAME FOLDER\n")

        elif mode == "REMOVE":
            print(f"REMOVING {list_name} FILES FROM YOUR GAME FOLDER, PLEASE WAIT...")
            for file in game_path.glob("*"):
                if matches_managed_file(file.name):
                    if file.is_file():
                        file.unlink(missing_ok=True)
                    elif file.is_dir():
                        shutil.rmtree(file)  # Using rmtree instead of os.removedirs for more reliable deletion
            print(f"{SUCCESS_PREFIX} REMOVED {list_name} FILES FROM THE GAME FOLDER\n")

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
    unpacked = scan_mods_unpacked()
    if unpacked.startswith("❌ MODS FOLDER PATH NOT PROVIDED"):
        return unpacked
    return unpacked + scan_mods_archived()


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
    initialize()
    main_generate_required()
    if TEST_MODE:
        write_combined_results()
    else:
        print(game_combined_result())
        print(mods_combined_result())
        game_files_manage("Backup ENB")
        os.system("pause")
