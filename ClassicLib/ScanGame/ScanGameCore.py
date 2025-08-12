"""
Async-first core implementation for CLASSIC_ScanGame.py operations.

This module provides the primary async implementations that are used by both
sync adapters (for backwards compatibility) and async callers directly.
All I/O-intensive operations are implemented asynchronously for optimal performance.
"""

import asyncio
import shutil
import struct
import subprocess
from pathlib import Path
from typing import cast

try:
    import aiofiles
except ImportError:
    aiofiles = None  # Handle gracefully if not installed

from ClassicLib import GlobalRegistry, MessageTarget, msg_error, msg_info, msg_warning
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.ScanGame.Config import TEST_MODE
from ClassicLib.Util import normalize_list, open_file_with_encoding
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

# Import async utilities if available
try:
    from ClassicLib.AsyncUtil import open_file_with_encoding_async, read_lines_with_encoding_async

    ASYNC_ENCODING_AVAILABLE = True
except ImportError:
    ASYNC_ENCODING_AVAILABLE = False

# Semaphore limits for resource control
MAX_CONCURRENT_SUBPROCESSES = 4  # Limit BSArch.exe processes
MAX_CONCURRENT_FILE_OPS = 10  # Limit concurrent file operations
MAX_CONCURRENT_LOG_READS = 20  # Limit concurrent log file reads
MAX_CONCURRENT_DDS_READS = 50  # Limit concurrent DDS header reads


class ScanGameCore:
    """Async-first core implementation for game scanning operations."""

    def __init__(self):
        """Initialize the core scanner."""
        self.process_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SUBPROCESSES)
        self.file_ops_semaphore = asyncio.Semaphore(MAX_CONCURRENT_FILE_OPS)
        self.log_read_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LOG_READS)
        self.dds_read_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DDS_READS)

    def get_scan_settings(self) -> tuple[str, dict[str, str], Path | None]:
        """
        Gets common settings used by mod scanning functions.

        Returns:
            tuple: (xse_acronym, xse_scriptfiles, mod_path)
        """
        # Get XSE settings
        xse_acronym_setting: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
        xse_scriptfiles_setting: dict[str, str] | None = yaml_settings(
            dict[str, str], YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_HashedScripts"
        )
        xse_acronym: str = xse_acronym_setting if isinstance(xse_acronym_setting, str) else "XSE"
        xse_scriptfiles: dict[str, str] = xse_scriptfiles_setting if isinstance(xse_scriptfiles_setting, dict) else {}

        # Get mods path
        mod_path: Path | None = classic_settings(Path, "MODS Folder Path")

        return xse_acronym, xse_scriptfiles, mod_path

    def get_issue_messages(self, xse_acronym: str, mode: str) -> dict[str, list[str]]:
        """
        Returns standardized issue messages for mod scan reports.

        Args:
            xse_acronym: Script extender acronym from settings
            mode: Either "unpacked" or "archived"

        Returns:
            dict: Dictionary of issue types and their message templates
        """
        base_messages = {
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
        }

        # Add mode-specific messages
        if mode == "unpacked":
            base_messages.update({
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
                "animdata": [
                    "\n# ❓ FOLDERS CONTAIN CUSTOM ANIMATION FILE DATA ❓\n",
                    "▶️ Any mods that have their own custom Animation File Data\n",
                    "  may rarely cause an *Animation Corruption Crash*. For further details,\n",
                    "  read the *How To Read Crash Logs.pdf* included with the CLASSIC exe.\n\n",
                ],
                "cleanup": ["\n# 📄 DOCUMENTATION FILES MOVED TO 'CLASSIC Backup\\Cleaned Files' 📄\n"],
            })
        else:  # archived
            base_messages.update({
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
            })

        return base_messages

    async def check_log_errors(self, folder_path: Path | str) -> str:
        """
        Async-first implementation for checking log file errors.

        Inspects log files within a specified folder for recorded errors, processing
        multiple log files concurrently for improved performance.

        Args:
            folder_path (Path | str): Path to the folder containing log files for error inspection.

        Returns:
            str: A detailed report of all detected errors in the relevant log files, if any.
        """

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
        catch_errors: list[str] = normalize_list(yaml_settings(list[str], YAML.Main, "catch_log_errors") or [])
        ignore_files: list[str] = normalize_list(yaml_settings(list[str], YAML.Main, "exclude_log_files") or [])
        ignore_errors: list[str] = normalize_list(yaml_settings(list[str], YAML.Main, "exclude_log_errors") or [])

        # Find valid log files (excluding crash logs)
        valid_log_files: list[Path] = [
            file
            for file in folder_path.glob("*.log")
            if "crash-" not in file.name.lower() and not any(part in str(file).lower() for part in ignore_files)
        ]

        async def process_single_log(log_file_path: Path) -> list[str]:
            """Process a single log file and return formatted error report."""
            async with self.log_read_semaphore:
                try:
                    # Use async encoding detection if available
                    if ASYNC_ENCODING_AVAILABLE:
                        log_lines = await read_lines_with_encoding_async(log_file_path)
                    elif aiofiles:
                        # Fallback to aiofiles with utf-8 if async encoding not available
                        async with aiofiles.open(log_file_path, "r", encoding="utf-8", errors="ignore") as log_file:
                            log_lines = await log_file.readlines()
                    else:
                        # Fallback to sync read with async wrapper
                        loop = asyncio.get_event_loop()
                        with open_file_with_encoding(log_file_path) as log_file:
                            log_lines = await loop.run_in_executor(None, log_file.readlines)

                    # Filter for relevant errors
                    detected_errors = [
                        f"ERROR > {line}"
                        for line in log_lines
                        if any(error in line.lower() for error in catch_errors)
                        and all(ignore not in line.lower() for ignore in ignore_errors)
                    ]

                except OSError:
                    error_message = f"❌ ERROR : Unable to scan this log file :\n  {log_file_path}"
                    logger.warning(f"> ! > DETECT LOG ERRORS > UNABLE TO SCAN : {log_file_path}")
                    return [error_message]
                else:
                    if detected_errors:
                        return format_error_report(log_file_path, detected_errors)
                    return []

        # Process all log files concurrently
        if valid_log_files:
            msg_info(f"Processing {len(valid_log_files)} log files concurrently...")
        tasks = [process_single_log(log_file) for log_file in valid_log_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect all error reports
        error_report: list[str] = []
        for result in results:
            if isinstance(result, Exception):
                msg_error(f"Task failed with exception: {result}")
                continue
            if isinstance(result, list):
                error_report.extend(result)

        return "".join(error_report)

    async def scan_mods_unpacked(self) -> str:
        """
        Async-first implementation for scanning unpacked/loose mod files.

        Combines cleanup and analysis passes into a single traversal with
        concurrent file operations for significant performance improvements.

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
        xse_acronym, xse_scriptfiles, mod_path = self.get_scan_settings()

        # Setup paths
        backup_path: Path = Path(GlobalRegistry.get_local_dir()) / "CLASSIC Backup/Cleaned Files"
        if not TEST_MODE:
            backup_path.mkdir(parents=True, exist_ok=True)

        if not mod_path:
            return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_Path_Missing"))

        msg_info("✔️ MODS FOLDER PATH FOUND! PERFORMING ASYNC MOD FILES SCAN...", target=MessageTarget.CLI_ONLY)

        # Filter names for cleanup
        filter_names: tuple = ("readme", "changes", "changelog", "change log")

        # Locks for thread-safe updates to shared collections
        issue_locks = {issue_type: asyncio.Lock() for issue_type in issue_lists}

        async def process_directory(root: Path, dirs: list[str], files: list[str]) -> None:
            """Process a single directory with concurrent file operations."""
            root_main: Path = root.relative_to(mod_path).parent
            has_anim_data = False
            has_previs_files = False
            has_xse_files = False

            # Create context for file operations
            context = {"mod_path": mod_path, "backup_path": backup_path, "issue_lists": issue_lists, "issue_locks": issue_locks}

            # Process directories for cleanup and animation data
            dir_tasks = []
            for dirname in dirs:
                dirname_lower: str = dirname.lower()
                if not has_anim_data and dirname_lower == "animationfiledata":
                    has_anim_data = True
                    async with issue_locks["animdata"]:
                        issue_lists["animdata"].add(f"  - {root_main}\n")
                elif dirname_lower == "fomod":
                    # Create async task for moving fomod folder
                    dir_tasks.append(self._move_fomod_async(context, root, dirname))

            # Execute directory operations concurrently
            if dir_tasks:
                await asyncio.gather(*dir_tasks, return_exceptions=True)

            # Process files concurrently
            file_tasks = []
            dds_files = []

            for filename in files:
                filename_lower = filename.lower()
                file_path = root / filename
                relative_path = file_path.relative_to(mod_path)
                file_ext = file_path.suffix.lower()

                # Cleanup operations
                if filename_lower.endswith(".txt") and any(name in filename_lower for name in filter_names):
                    file_tasks.append(self._move_file_async(context, file_path))

                # Analysis operations
                elif file_ext == ".dds":
                    dds_files.append((file_path, relative_path))

                elif file_ext in {".tga", ".png"} and "BodySlide" not in file_path.parts:
                    async with issue_locks["tex_frmt"]:
                        issue_lists["tex_frmt"].add(f"  - {file_ext[1:].upper()} : {relative_path}\n")

                elif file_ext in {".mp3", ".m4a"}:
                    async with issue_locks["snd_frmt"]:
                        issue_lists["snd_frmt"].add(f"  - {file_ext[1:].upper()} : {relative_path}\n")

                elif (
                    not has_xse_files
                    and any(filename_lower == key.lower() for key in xse_scriptfiles)
                    and "workshop framework" not in str(root).lower()
                    and f"Scripts\\{filename}" in str(file_path)
                ):
                    has_xse_files = True
                    async with issue_locks["xse_file"]:
                        issue_lists["xse_file"].add(f"  - {root_main}\n")

                elif not has_previs_files and filename_lower.endswith((".uvd", "_oc.nif")):
                    has_previs_files = True
                    async with issue_locks["previs"]:
                        issue_lists["previs"].add(f"  - {root_main}\n")

            # Process DDS files in batch
            if dds_files:
                file_tasks.append(self._check_dds_batch_async(dds_files, issue_lists, issue_locks))

            # Execute all file operations concurrently
            if file_tasks:
                await asyncio.gather(*file_tasks, return_exceptions=True)

        # Collect all directories to process
        try:
            # Collect all directory data first (synchronous for os.walk compatibility)
            all_dirs_data = []
            for root, dirs, files in mod_path.walk(top_down=False):
                all_dirs_data.append((Path(root), list(dirs), list(files)))
        except (OSError, FileNotFoundError) as e:
            msg_error(f"Error accessing mod files: {e}")
            return "Error: Could not access mod files"

        # Process all directories concurrently
        msg_info(f"Processing {len(all_dirs_data)} directories with async pipeline...")

        # Create tasks for all directories
        tasks = [process_directory(root, dirs, files) for root, dirs, files in all_dirs_data]

        # Process in batches to avoid overwhelming the system
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)

        # Build the report
        issue_messages = self.get_issue_messages(xse_acronym, "unpacked")

        # Add found issues to message list
        for issue_type, items in issue_lists.items():
            if items and issue_type in issue_messages:
                message_list.extend(issue_messages[issue_type])
                message_list.extend(sorted(items))

        return "".join(message_list)

    async def scan_mods_archived(self) -> str:
        """
        Async-first implementation for scanning archived BA2 mod files.

        Analyzes archived BA2 mod files to identify potential issues, processing
        multiple archives concurrently for significant performance improvements.

        Returns:
            str: A report detailing the findings, including errors and warnings
            regarding issues found in the BA2 files.
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
        xse_acronym, xse_scriptfiles, mod_path = self.get_scan_settings()

        # Setup paths
        bsarch_path: Path = cast("Path", GlobalRegistry.get_local_dir()) / "CLASSIC Data/BSArch.exe"

        # Validate paths
        if not mod_path:
            return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_Path_Missing"))
        if not mod_path.exists():
            return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_Path_Invalid"))
        if not bsarch_path.exists():
            return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_BSArch_Missing"))

        msg_info("✔️ ALL REQUIREMENTS SATISFIED! NOW ANALYZING ALL BA2 MOD ARCHIVES (ASYNC)...")

        # Collect all BA2 files first
        ba2_files: list[tuple[Path, str]] = []
        try:
            for root, _, files in mod_path.walk(top_down=False):
                for filename in files:
                    filename_lower: str = filename.lower()
                    if filename_lower.endswith(".ba2") and filename_lower != "prp - main.ba2":
                        ba2_files.append((root / filename, filename))
        except OSError as e:
            msg_error(f"Error scanning for BA2 files: {e}")
            return "Error: Could not scan for BA2 files"

        # Process BA2 files concurrently
        async def process_single_ba2(file_path: Path, filename: str) -> dict[str, set[str]]:
            """Process a single BA2 file and return its issues."""
            local_issues: dict[str, set[str]] = {
                "ba2_frmt": set(),
                "animdata": set(),
                "tex_dims": set(),
                "tex_frmt": set(),
                "snd_frmt": set(),
                "xse_file": set(),
                "previs": set(),
            }

            # Read BA2 header
            try:
                if aiofiles:
                    async with aiofiles.open(file_path, "rb") as f:
                        header: bytes = await f.read(12)
                else:
                    # Fallback to sync read if aiofiles not available
                    with file_path.open("rb") as f:
                        header: bytes = f.read(12)
            except OSError:
                msg_warning(f"Failed to read file: {filename}")
                return local_issues

            # Check BA2 format
            if header[:4] != b"BTDX" or header[8:] not in {b"DX10", b"GNRL"}:
                local_issues["ba2_frmt"].add(f"  - {filename} : {header!s}\n")
                return local_issues

            async with self.process_semaphore:  # Limit concurrent subprocesses
                if header[8:] == b"DX10":
                    # Process texture-format BA2
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            str(bsarch_path),
                            str(file_path),
                            "-dump",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            text=True,
                        )

                        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

                        if proc.returncode != 0:
                            msg_error(f"BSArch command failed for {filename}:\n{stderr}")
                            return local_issues

                        output_split: list[str] = stdout.split("\n\n")
                        if output_split[-1].startswith("Error:"):
                            msg_error(f"BSArch error for {filename}:\n{output_split[-1]}\n\n{stderr}")
                            return local_issues

                        # Process texture information
                        for file_block in output_split[4:]:
                            if not file_block:
                                continue

                            block_split: list[str] = file_block.split("\n", 3)

                            # Check texture format
                            if "Ext: dds" not in block_split[1]:
                                local_issues["tex_frmt"].add(
                                    f"  - {block_split[0].rsplit('.', 1)[-1].upper()} : {filename} > {block_split[0]}\n"
                                )
                                continue

                            # Check texture dimensions
                            _, width, _, height, _ = block_split[2].split(maxsplit=4)
                            if (width.isdecimal() and int(width) % 2 != 0) or (height.isdecimal() and int(height) % 2 != 0):
                                local_issues["tex_dims"].add(f"  - {width}x{height} : {filename} > {block_split[0]}")

                    except TimeoutError:
                        msg_error(f"BSArch command timed out processing {filename}")
                    except (OSError, ValueError, subprocess.SubprocessError) as e:
                        msg_error(f"Error processing {filename}: {e}")

                else:
                    # Process general-format BA2
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            str(bsarch_path),
                            str(file_path),
                            "-list",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            text=True,
                        )

                        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

                        if proc.returncode != 0:
                            msg_error(f"BSArch command failed for {filename}:\n{stderr}")
                            return local_issues

                        # Process file list
                        output_split = stdout.lower().split("\n")
                        has_previs_files = has_anim_data = has_xse_files = False

                        for file in output_split[15:]:
                            # Check sound formats
                            if file.endswith((".mp3", ".m4a")):
                                local_issues["snd_frmt"].add(f"  - {file[-3:].upper()} : {filename} > {file}\n")

                            # Check animation data
                            elif not has_anim_data and "animationfiledata" in file:
                                has_anim_data = True
                                local_issues["animdata"].add(f"  - {filename}\n")

                            # Check XSE files
                            elif (
                                not has_xse_files
                                and any(f"scripts\\{key.lower()}" in file for key in xse_scriptfiles)
                                and "workshop framework" not in str(file_path.parent).lower()
                            ):
                                has_xse_files = True
                                local_issues["xse_file"].add(f"  - {filename}\n")

                            # Check previs files
                            elif not has_previs_files and file.endswith((".uvd", "_oc.nif")):
                                has_previs_files = True
                                local_issues["previs"].add(f"  - {filename}\n")

                    except TimeoutError:
                        msg_error(f"BSArch command timed out processing {filename}")
                    except (OSError, ValueError, subprocess.SubprocessError) as e:
                        msg_error(f"Error processing {filename}: {e}")

            return local_issues

        # Create tasks for all BA2 files
        tasks = [process_single_ba2(file_path, filename) for file_path, filename in ba2_files]

        # Process all files concurrently and collect results
        msg_info(f"Processing {len(ba2_files)} BA2 files concurrently...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results from all tasks
        for result in results:
            if isinstance(result, Exception):
                msg_error(f"Task failed with exception: {result}")
                continue
            if isinstance(result, dict):
                for issue_type, items in result.items():
                    issue_lists[issue_type].update(items)

        # Build the report using shared function
        issue_messages = self.get_issue_messages(xse_acronym, "archived")

        # Add found issues to message list
        for issue_type, items in issue_lists.items():
            if items and issue_type in issue_messages:
                message_list.extend(issue_messages[issue_type])
                message_list.extend(sorted(items))

        return "".join(message_list)

    # Helper methods for internal operations
    async def _move_fomod_async(self, context: dict, root: Path, dirname: str) -> None:
        """Async move FOMOD folder to backup."""
        async with self.file_ops_semaphore:
            fomod_folder_path: Path = root / dirname
            relative_path: Path = fomod_folder_path.relative_to(context["mod_path"])
            new_folder_path: Path = context["backup_path"] / relative_path

            if not TEST_MODE:
                try:
                    # Use executor for blocking shutil.move
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, shutil.move, str(fomod_folder_path), str(new_folder_path))
                except PermissionError:
                    msg_error(f"Permission denied moving folder: {fomod_folder_path}")
                    return
                except (OSError, FileNotFoundError, FileExistsError) as e:
                    msg_error(f"Failed to move folder {fomod_folder_path}: {e}")
                    return

            async with context["issue_locks"]["cleanup"]:
                context["issue_lists"]["cleanup"].add(f"  - {relative_path}\n")

    async def _move_file_async(self, context: dict, file_path: Path) -> None:
        """Async move file to backup."""
        async with self.file_ops_semaphore:
            relative_path = file_path.relative_to(context["mod_path"])
            new_file_path: Path = context["backup_path"] / relative_path

            if not TEST_MODE:
                try:
                    # Ensure parent directory exists
                    new_file_path.parent.mkdir(parents=True, exist_ok=True)
                    # Use executor for blocking shutil.move
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, shutil.move, str(file_path), str(new_file_path))
                except PermissionError:
                    msg_error(f"Permission denied moving file: {file_path}")
                    return
                except (OSError, FileNotFoundError, FileExistsError) as e:
                    msg_error(f"Failed to move file {file_path}: {e}")
                    return

            async with context["issue_locks"]["cleanup"]:
                context["issue_lists"]["cleanup"].add(f"  - {relative_path}\n")

    async def _check_dds_batch_async(self, dds_files: list[tuple[Path, Path]], issue_lists: dict, issue_locks: dict) -> None:
        """Check DDS dimensions for a batch of files."""

        async def check_single_dds(file_path: Path, relative_path: Path) -> None:
            async with self.dds_read_semaphore:
                try:
                    if aiofiles:
                        async with aiofiles.open(file_path, "rb") as dds_file:
                            dds_data: bytes = await dds_file.read(20)
                    else:
                        # Fallback to sync read in executor
                        loop = asyncio.get_event_loop()
                        with file_path.open("rb") as dds_file:
                            dds_data: bytes = await loop.run_in_executor(None, dds_file.read, 20)

                    if dds_data[:4] == b"DDS ":
                        width = struct.unpack("<I", dds_data[12:16])[0]
                        height = struct.unpack("<I", dds_data[16:20])[0]
                        if width % 2 != 0 or height % 2 != 0:
                            async with issue_locks["tex_dims"]:
                                issue_lists["tex_dims"].add(f"  - {relative_path} ({width}x{height})")
                except OSError as e:
                    msg_warning(f"Failed to read DDS file {file_path}: {e}")

        # Process all DDS files concurrently
        tasks = [check_single_dds(file_path, relative_path) for file_path, relative_path in dds_files]
        await asyncio.gather(*tasks, return_exceptions=True)
