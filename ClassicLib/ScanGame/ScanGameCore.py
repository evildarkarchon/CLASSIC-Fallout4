"""
Async-first core implementation for CLASSIC_ScanGame.py operations.

This module provides the primary async implementations that are used by both
sync adapters (for backwards compatibility) and async callers directly.
All I/O-intensive operations are implemented asynchronously for optimal performance.
"""

import asyncio
import mmap
import os
import shutil
import struct
import subprocess
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from pathlib import Path
from typing import cast

try:
    import aiofiles
except ImportError:
    aiofiles = None  # Handle gracefully if not installed

from itertools import starmap

from ClassicLib import GlobalRegistry, MessageTarget, msg_error, msg_info, msg_warning
from ClassicLib.Constants import YAML
from ClassicLib.GlobalRegistry import get, register
from ClassicLib.ScanGame.Config import TEST_MODE

# Import refactored components
from ClassicLib.ScanGame.core import (
    SCAN_GAME_CORE_KEY,
    DDSProcessor,
    FileOperations,
    LogProcessor,
    ScanValidators,
    get_optimal_limits,
)
from ClassicLib.YamlSettingsCache import yaml_settings


class ScanGameCore:
    """
    Implements the core functionalities for scanning mods in an optimized and
    concurrent manner. The class applies singleton design principles, ensuring
    only one instance exists and centralizes management of scan and validation
    operations for efficiency.

    The primary use of this class is to provide an interface for assessing mods'
    files, validating their structure and content, and offering error reporting
    or issue lists derived from the scans.

    Attributes:
        process_semaphore (asyncio.Semaphore): Semaphore to limit subprocess execution.
        file_ops_semaphore (asyncio.Semaphore): Semaphore to limit concurrent file operations.
        log_read_semaphore (asyncio.Semaphore): Semaphore to limit the examination of log reads.
        dds_read_semaphore (asyncio.Semaphore): Semaphore to regulate DDS file reads.
        header_executor (ThreadPoolExecutor): Thread pool for managing CPU-intensive tasks (e.g., file headers).
        walk_executor (ThreadPoolExecutor): Thread pool for handling async directory operations.
        validators (ScanValidators): Collection of validators used during scanning processes.
        log_processor (LogProcessor): Processor to analyze error logs.
        dds_processor (DDSProcessor): Component for handling DDS image scans.
        file_operations (FileOperations): Facilitates safe file operations under semaphore limits.
    """

    def __new__(cls) -> "ScanGameCore":
        """
        Creates a new instance of the ScanGameCore class or retrieves an existing one
        from a shared store. Implements a Singleton pattern to ensure only one
        instance of the class exists.

        Args:
            cls: The class to instantiate.

        Returns:
            ScanGameCore: The instance of the ScanGameCore class.
        """
        instance = get(SCAN_GAME_CORE_KEY)
        if instance is None:
            instance = super().__new__(cls)
            register(SCAN_GAME_CORE_KEY, instance)
        return instance

    def __init__(self) -> None:
        """
        Initializes the class and configures internal semaphores, thread pools, and
        other components required for processing operations.

        This method ensures initialization is only performed once and sets up
        semaphores for managing different asynchronous tasks. It dynamically fetches
        optimal limits for subprocesses, file operations, log reads, and DDS reads.
        Thread pool executors are created to handle CPU-bound and asynchronous
        directory walking operations. The method also initializes various components
        required for validation, log handling, DDS handling, and file operations.
        """
        # Only initialize once
        if not hasattr(self, "_initialized"):
            # Get optimal limits dynamically
            limits = get_optimal_limits()
            self.process_semaphore = asyncio.Semaphore(limits["subprocesses"])
            self.file_ops_semaphore = asyncio.Semaphore(limits["file_ops"])
            self.log_read_semaphore = asyncio.Semaphore(limits["log_reads"])
            self.dds_read_semaphore = asyncio.Semaphore(limits["dds_reads"])

            # Thread pool for CPU-bound operations
            self.header_executor = ThreadPoolExecutor(max_workers=min(10, limits["file_ops"] // 2))

            # For async directory walking
            self.walk_executor = ThreadPoolExecutor(max_workers=4)

            # Initialize extracted components
            self.validators = ScanValidators()
            self.log_processor = LogProcessor(self.log_read_semaphore)
            self.dds_processor = DDSProcessor(self.dds_read_semaphore)
            self.file_operations = FileOperations(self.file_ops_semaphore)

            self._initialized = True

    def get_scan_settings(self) -> tuple[str, dict[str, str], Path | None]:
        """
        Retrieves settings required for a scanning process.

        This method returns a tuple containing three items: a string, a dictionary where
        both keys and values are strings, and an optional Path object. These settings
        are essential for configuring and executing a scan.

        Returns:
            tuple[str, dict[str, str], Path | None]: A tuple containing the scan settings,
            where the first element is a string, the second is a dictionary with string
            keys and values, and the third is an optional Path object.
        """
        return self.validators.get_scan_settings()

    def get_issue_messages(self, xse_acronym: str, mode: str) -> dict[str, list[str]]:
        """
        Retrieves issue messages for the given acronym and mode.

        This method fetches issue messages using the specified acronym and mode as input
        parameters. It is commonly used to validate or retrieve diagnostic messages
        associated with certain operations or processes.

        Args:
            xse_acronym (str): The acronym representing the entity or category for which
                issue messages are retrieved.
            mode (str): The operational mode or context in which issue messages are
                being queried.

        Returns:
            dict[str, list[str]]: A dictionary where the keys represent categories or
            issue types, and the values are lists of issue messages corresponding to
            those keys.
        """
        return self.validators.get_issue_messages(xse_acronym, mode)

    async def check_log_errors(self, folder_path: Path | str) -> str:
        """
        Checks for errors in log files within the specified folder.

        This method processes the log files found in the given folder, identifies error entries,
        and returns a summary of the errors. It relies on an internal log processor to perform
        the analysis.

        Args:
            folder_path (Path | str): The path to the folder containing the log files to be
                analyzed.

        Returns:
            str: A summary of errors found within the processed log files.
        """
        return await self.log_processor.check_log_errors(folder_path)

    async def scan_mods_unpacked(self) -> str:
        """
        Scans and processes unpacked mod files for cleanup and issue detection. The method performs
        a comprehensive analysis of directories and files within a specified mod folder, identifying
        and reporting various issues, such as file format inconsistencies, directory misplacements,
        and other indicators for mod improvements.

        This is an asynchronous operation that utilizes concurrent processing for efficiency and
        supports large-scale file management. The function organizes detected issues into categories,
        applies cleanup operations on specific files and directories, and generates a detailed
        report summarizing all findings.

        Returns:
            str: A report summarizing findings from the unpacked mod files scan.

        Raises:
            OSError: If there is an error accessing the mod files.
            FileNotFoundError: If the specified mod folder path does not exist.
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

        async def process_file_by_type(
            filename: str,
            file_path: Path,
            relative_path: Path,
            file_ext: str,
            context: dict,
            file_tasks: list,
            dds_files: list,
            has_xse_files: bool,
            has_previs_files: bool,
            root: Path,
            root_main: Path,
        ) -> tuple[bool, bool]:
            """
            Process a single file based on its type and add appropriate tasks or issue tracking.

            Returns:
                tuple[bool, bool]: Updated has_xse_files and has_previs_files flags
            """
            filename_lower = filename.lower()

            # Cleanup operations
            if filename_lower.endswith(".txt") and any(name in filename_lower for name in filter_names):
                file_tasks.append(self._move_file_async(context, file_path))
                return has_xse_files, has_previs_files

            # Analysis operations
            if file_ext == ".dds":
                dds_files.append((file_path, relative_path))
                return has_xse_files, has_previs_files

            if file_ext in {".tga", ".png"} and "BodySlide" not in file_path.parts:
                async with issue_locks["tex_frmt"]:
                    issue_lists["tex_frmt"].add(f"  - {file_ext[1:].upper()} : {relative_path}\n")
                return has_xse_files, has_previs_files

            if file_ext in {".mp3", ".m4a"}:
                async with issue_locks["snd_frmt"]:
                    issue_lists["snd_frmt"].add(f"  - {file_ext[1:].upper()} : {relative_path}\n")
                return has_xse_files, has_previs_files

            if (
                not has_xse_files
                and any(filename_lower == key.lower() for key in xse_scriptfiles)
                and "workshop framework" not in str(root).lower()
                and f"Scripts\\{filename}" in str(file_path)
            ):
                has_xse_files = True
                async with issue_locks["xse_file"]:
                    issue_lists["xse_file"].add(f"  - {root_main}\n")
                return has_xse_files, has_previs_files

            if not has_previs_files and filename_lower.endswith((".uvd", "_oc.nif")):
                has_previs_files = True
                async with issue_locks["previs"]:
                    issue_lists["previs"].add(f"  - {root_main}\n")

            return has_xse_files, has_previs_files

        async def process_directory(root: Path, dirs: list[str], files: list[str]) -> None:
            """
            Processes a directory with both files and subdirectories, performing cleanup and analysis operations
            while leveraging asynchronous tasks for concurrency. It supports operations like moving directories,
            analyzing file formats for specific issues, and processing DDS files in batches.

            Args:
                root (Path): The root directory currently being processed.
                dirs (list[str]): List of subdirectory names within the root directory.
                files (list[str]): List of filenames within the root directory.

            Raises:
                Any exceptions encountered during asynchronous operations are captured and handled
                via `return_exceptions` in asyncio gathering.
            """
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
                file_path = root / filename
                relative_path = file_path.relative_to(mod_path)
                file_ext = file_path.suffix.lower()

                # Process file and update flags
                has_xse_files, has_previs_files = await process_file_by_type(
                    filename,
                    file_path,
                    relative_path,
                    file_ext,
                    context,
                    file_tasks,
                    dds_files,
                    has_xse_files,
                    has_previs_files,
                    root,
                    root_main,
                )

            # Process DDS files in batch
            if dds_files:
                file_tasks.append(self._check_dds_batch_async(dds_files, issue_lists, issue_locks))

            # Execute all file operations concurrently
            if file_tasks:
                await asyncio.gather(*file_tasks, return_exceptions=True)

        # Async directory walking
        # noinspection PyUnresolvedReferences,PyTypeChecker
        async def async_walk(path: Path) -> list[tuple[Path, list[str], list[str]]]:
            """
            Recursively walks through the directory tree starting from the given path using
            an asynchronous approach. Returns all directory paths, subdirectory names, and
            file names within the directory tree.

            This function leverages `os.walk` to iterate over directories and performs the
            operation asynchronously to avoid blocking on long-running file system tasks.

            Args:
                path (Path): The starting directory path for traversing the directory tree.

            Returns:
                list[tuple[Path, list[str], list[str]]]: A list of tuples where each tuple
                contains:
                    - A `Path` object representing the current directory
                    - A list of subdirectory names within the current directory
                    - A list of file names within the current directory
            """

            def _walk() -> list[tuple[Path, list[str], list[str]]]:
                """
                Optimized directory traversal using pathlib's rglob for better performance.

                This function walks through a directory tree more efficiently than os.walk,
                collecting the path to each directory, its subdirectories, and its files.

                Returns:
                    list[tuple[Path, list[str], list[str]]]: A list of tuples, where each tuple
                    contains a Path object for the directory, a list of its subdirectory names,
                    and a list of its file names.
                """
                from collections import defaultdict

                # Use rglob to get all paths in one operation - much faster than os.walk
                try:
                    all_paths = list(path.rglob("*"))
                except (OSError, PermissionError):
                    # Fallback to empty if we can't access
                    return []

                # Group paths by parent directory for efficient processing
                dir_structure = defaultdict(lambda: {"dirs": [], "files": []})

                for p in all_paths:
                    parent = p.parent
                    try:
                        if p.is_dir():
                            dir_structure[parent]["dirs"].append(p.name)
                        elif p.is_file():
                            dir_structure[parent]["files"].append(p.name)
                    except (OSError, PermissionError):
                        # Skip inaccessible paths
                        continue

                # Add the root directory if it has files or subdirs
                if path.is_dir():
                    try:
                        direct_children = list(path.iterdir())
                        root_dirs = [p.name for p in direct_children if p.is_dir()]
                        root_files = [p.name for p in direct_children if p.is_file()]
                        if root_files or root_dirs:
                            dir_structure[path] = {"dirs": root_dirs, "files": root_files}
                    except (OSError, PermissionError):
                        pass

                # Convert to expected format, maintaining bottom-up order for compatibility
                return [
                    (parent, data["dirs"], data["files"])
                    for parent, data in sorted(dir_structure.items(), key=lambda x: str(x[0]).count(os.sep), reverse=True)
                ]

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.walk_executor, _walk)

        # Collect all directories to process
        try:
            all_dirs_data = await async_walk(mod_path)
        except (OSError, FileNotFoundError) as e:
            msg_error(f"Error accessing mod files: {e}")
            return "Error: Could not access mod files"

        # Process all directories concurrently
        msg_info(f"Processing {len(all_dirs_data)} directories with async pipeline...")

        # Create tasks for all directories
        tasks = list(starmap(process_directory, all_dirs_data))

        # Process in batches to avoid overwhelming the system
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)

        # Build the report using StringIO for efficiency
        output = StringIO()
        issue_messages = self.get_issue_messages(xse_acronym, "unpacked")

        # Write initial messages
        for msg in message_list:
            output.write(msg)

        # Add found issues
        for issue_type, items in issue_lists.items():
            if items and issue_type in issue_messages:
                for msg in issue_messages[issue_type]:
                    output.write(msg)
                for item in sorted(items):
                    output.write(item)

        return output.getvalue()

    async def scan_mods_archived(self) -> str:
        """
        Asynchronously scans for archived .ba2 mod files and processes them to detect potential issues
        like texture format problems, invalid dimensions, incorrect sound formats, and other file
        anomalies. Utilizes asynchronous I/O and controlled subprocess execution to ensure optimized
        performance.

        Returns:
            str: A string summary outlining any detected issues, or an appropriate status message if
            no issues are found or requirements are not satisfied.

        Raises:
            OSError: If there is an error accessing the filesystem.
            TimeoutError: If a subprocess execution exceeds the specified timeout duration.

        Notes:
            - The method checks .ba2 archive format validity and extracts file-level metadata to
              analyze textures, sound formats, animation data, XSE files, Previs files, etc.
            - Processes files in controlled asynchronous batches, leveraging system resources effectively.
            - Relies on external tools like BSArch.exe for parsing archive files and retrieving necessary
              metadata.
        """
        # Initialize the scan setup
        scan_setup = await self._initialize_archived_scan()
        if isinstance(scan_setup, str):  # Error message returned
            return scan_setup

        issue_lists, xse_acronym, xse_scriptfiles, mod_path, bsarch_path = scan_setup

        msg_info("✔️ ALL REQUIREMENTS SATISFIED! NOW ANALYZING ALL BA2 MOD ARCHIVES (ASYNC)...")

        # Find and process BA2 files
        ba2_files = await self._find_ba2_files(mod_path)
        if not ba2_files:
            return self._build_report(issue_lists, xse_acronym)

        # Process all BA2 files concurrently
        results = await self._process_ba2_files_concurrently(ba2_files, bsarch_path, xse_scriptfiles)

        # Merge results into issue lists
        ScanGameCore._merge_scan_results(results, issue_lists)

        return self._build_report(issue_lists, xse_acronym)

    async def _initialize_archived_scan(self) -> tuple[dict[str, set[str]], str, dict[str, str], Path, Path] | str:
        """
        Initialize the archived scan with validation and setup.

        Returns:
            Either a tuple of initialized components or an error message string.
        """
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

        # Validate requirements
        validation_error = self._validate_archived_scan_requirements(mod_path, bsarch_path)
        if validation_error:
            return validation_error

        # At this point, mod_path is guaranteed to be not None due to validation
        assert mod_path is not None, "mod_path should not be None after validation"
        return issue_lists, xse_acronym, xse_scriptfiles, mod_path, bsarch_path

    @staticmethod
    def _validate_archived_scan_requirements(mod_path: Path | None, bsarch_path: Path) -> str | None:
        """
        Validate all requirements for archived scan.

        Returns:
            Error message if validation fails, None if all requirements are satisfied.
        """
        if not mod_path:
            return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_Path_Missing"))
        if not mod_path.exists():
            return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_Path_Invalid"))
        if not bsarch_path.exists():
            return str(yaml_settings(str, YAML.Main, "Mods_Warn.Mods_BSArch_Missing"))
        return None

    async def _find_ba2_files(self, mod_path: Path) -> list[tuple[Path, str]]:
        """
        Find all BA2 files in the mod directory.

        Args:
            mod_path: The mod directory path to search.

        Returns:
            List of tuples containing BA2 file path and filename.
        """

        # Async directory walking for BA2 files
        # noinspection PyUnresolvedReferences,PyTypeChecker
        async def find_ba2_files(path: Path) -> list[tuple[Path, str]]:
            """
            Searches for .ba2 files in the specified directory and its subdirectories.

            This asynchronous function scans the given directory for files with the
            ".ba2" extension, excluding files named "prp - main.ba2". It returns a
            list of tuples, where each tuple contains the full path to the .ba2
            file and its filename.

            Args:
                path (Path): The directory path to search for .ba2 files.

            Returns:
                list[tuple[Path, str]]: A list of tuples containing the full path
                and filename of the .ba2 files found.
            """

            def _find() -> list[tuple[Path, str]]:
                """
                Optimized BA2 file finding using pathlib.rglob().

                Returns:
                    list[tuple[Path, str]]: List of BA2 file paths and filenames.
                """
                result = []
                try:
                    # Use rglob to find all .ba2 files directly - much faster
                    for ba2_path in path.rglob("*.ba2"):
                        filename = ba2_path.name
                        filename_lower = filename.lower()
                        if filename_lower != "prp - main.ba2":
                            result.append((ba2_path, filename))

                    # Also check for uppercase extension on case-sensitive systems
                    for ba2_path in path.rglob("*.BA2"):
                        filename = ba2_path.name
                        filename_lower = filename.lower()
                        if filename_lower != "prp - main.ba2" and (ba2_path, filename) not in result:
                            result.append((ba2_path, filename))

                except (OSError, PermissionError):
                    # Return empty list if we can't access the directory
                    pass

                return result

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.walk_executor, _find)

        # Collect all BA2 files
        try:
            return await find_ba2_files(mod_path)
        except OSError as e:
            msg_error(f"Error scanning for BA2 files: {e}")
            return []

    async def _process_ba2_files_concurrently(
        self, ba2_files: list[tuple[Path, str]], bsarch_path: Path, xse_scriptfiles: dict[str, str]
    ) -> list:
        """
        Process all BA2 files concurrently using the process_single_ba2 function.

        Args:
            ba2_files: List of BA2 file tuples (path, filename).
            bsarch_path: Path to BSArch executable.
            xse_scriptfiles: Dictionary of XSE script files.

        Returns:
            List of processing results.
        """

        # Process BA2 files concurrently with improved batching
        async def process_single_ba2(file_path: Path, filename: str) -> dict[str, set[str]]:
            """
            Processes a single BA2 file to identify and collect potential issues including format
            discrepancies, texture properties, sound formats, and specific file types.

            The function first determines the format of the BA2 file and accordingly processes
            either texture-format or general-format files. It uses BSArch for extracting file data
            and validates various aspects such as texture dimensions, sound formats, and the
            presence of specific file groups like animation data or previs files.

            Args:
                file_path (Path): The path to the BA2 file to be processed.
                filename (str): The name of the BA2 file.

            Returns:
                dict[str, set[str]]: A dictionary categorizing identified issues with the BA2 file.
            """
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
            header = await ScanGameCore._read_ba2_header(file_path, filename)
            if header is None:
                return local_issues

            # Validate BA2 format
            if not self._validate_ba2_header(header, filename, local_issues):
                return local_issues

            async with self.process_semaphore:  # Limit concurrent subprocesses
                if header[8:] == b"DX10":
                    # Process texture-format BA2
                    texture_issues = await self._process_texture_ba2(file_path, filename, bsarch_path)
                    local_issues.update(texture_issues)
                else:
                    # Process general-format BA2
                    general_issues = await self._process_general_ba2(file_path, filename, bsarch_path, xse_scriptfiles)
                    local_issues.update(general_issues)

            return local_issues

        # Process BA2 files with improved concurrency control
        msg_info(f"Processing {len(ba2_files)} BA2 files with dynamic batching...")

        # Create all tasks upfront - let the semaphore handle concurrency naturally
        # The semaphore in process_single_ba2 already limits concurrent subprocesses,
        # so we don't need artificial batching or delays
        all_tasks = list(starmap(process_single_ba2, ba2_files))

        # Process all tasks with natural backpressure from the semaphore
        # This is more efficient than artificial batching with delays
        return await asyncio.gather(*all_tasks, return_exceptions=True)

    @staticmethod
    def _merge_scan_results(results: list, issue_lists: dict[str, set[str]]) -> None:
        """
        Merge the scan results from multiple BA2 files into the main issue lists.

        Args:
            results: List of scan results from BA2 processing.
            issue_lists: Main issue lists to merge results into.
        """
        for result in results:
            if isinstance(result, Exception):
                msg_error(f"Task failed with exception: {result}")
                continue
            if isinstance(result, dict):
                for issue_type, items in result.items():
                    issue_lists[issue_type].update(items)

    def _build_report(self, issue_lists: dict[str, set[str]], xse_acronym: str) -> str:
        """
        Build the final scan report from collected issues.

        Args:
            issue_lists: Dictionary of issue sets by type.
            xse_acronym: XSE acronym for getting issue messages.

        Returns:
            The formatted scan report as a string.
        """
        message_list: list[str] = ["\n========== RESULTS FROM ARCHIVED / BA2 FILES ==========\n"]

        # Build the report using StringIO for efficiency
        output = StringIO()

        # Write initial messages
        for msg in message_list:
            output.write(msg)

        issue_messages = self.get_issue_messages(xse_acronym, "archived")

        # Add found issues
        for issue_type, items in issue_lists.items():
            if items and issue_type in issue_messages:
                for msg in issue_messages[issue_type]:
                    output.write(msg)
                for item in sorted(items):
                    output.write(item)

        return output.getvalue()

    # Helper methods for internal operations
    async def _move_fomod_async(self, context: dict, root: Path, dirname: str) -> None:
        """
        Asynchronously moves a specified folder to a backup location within the context of a file
        operation semaphore to ensure concurrent operations are managed correctly. This function utilizes
        an executor for potentially blocking `shutil.move` operations and handles exceptions that may
        arise during the move process.

        Args:
            context (dict): A dictionary containing context-specific information such as paths and locks.
            root (Path): The root path where the folder to be moved is located.
            dirname (str): The name of the directory to move.

        Raises:
            PermissionError: If permission is denied when attempting to move the folder.
            OSError: If a general operating system-related failure occurs during the move operation.
            FileNotFoundError: If the folder to be moved does not exist.
            FileExistsError: If the destination already contains the target folder.
        """
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
        """
        Asynchronously moves a file to a backup location specified in the context.

        This function is designed to operate within an asyncio-based application. It
        ensures that a file is moved from its current location to a specified backup
        path while respecting a semaphore to limit concurrency. In the event of
        errors like permission issues or file operations, it logs those errors
        rather than propagating exceptions. It also updates the cleanup issue list
        in the provided context.

        Args:
            context (dict): A dictionary containing paths and other operational data
                needed for the file-moving process. Must include the keys:
                - "mod_path" (Path): Base path for deriving relative file paths.
                - "backup_path" (Path): Target directory to move the file into.
                - "issue_locks" (dict): Contains asyncio locks for concurrent updates.
                - "issue_lists" (dict): Contains issue lists for tracking cleanup
                  operations.
            file_path (Path): The path of the file to be moved.
        """
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

    @staticmethod
    def _read_dds_header_mmap(file_path: Path) -> tuple[int, int] | None:
        """Reads a DDS file header using memory mapping.

        This method checks if the file is a valid DDS file and extracts its width
        and height from the header if the file is of sufficient size. It utilizes
        memory mapping for efficient header reading.

        Args:
            file_path (Path): The path to the DDS file to be read.

        Returns:
            tuple[int, int] | None: A tuple containing the width and height of the
            DDS file if valid, or None if the file is invalid or an error occurs.
        """
        try:
            with file_path.open("rb") as f:
                # Check if file is at least 20 bytes
                f.seek(0, 2)  # Seek to end
                file_size = f.tell()
                if file_size < 20:
                    return None
                f.seek(0)  # Seek back to start

                # Use mmap for efficient header reading
                with mmap.mmap(f.fileno(), length=20, access=mmap.ACCESS_READ) as mm:
                    if mm[:4] == b"DDS ":
                        width = struct.unpack("<I", mm[12:16])[0]
                        height = struct.unpack("<I", mm[16:20])[0]
                        return width, height
        except (OSError, ValueError):
            return None
        return None

    async def _check_dds_batch_async(self, dds_files: list[tuple[Path, Path]], issue_lists: dict, issue_locks: dict) -> None:
        """
        Checks a batch of DDS files asynchronously to validate their dimensions and adds issues
        to provided lists if any discrepancies are found.

        Optimized version that processes DDS headers in chunks for better performance,
        reducing async overhead and improving memory efficiency.

        Args:
            dds_files (list[tuple[Path, Path]]): A list of tuples where each tuple contains the
                full file path and the relative path of a DDS file.
            issue_lists (dict): A dictionary of issue lists where any detected issues will be
                appended based on the type of issue.
            issue_locks (dict): A dictionary of asynchronous locks to ensure thread-safe additions
                to the issue lists.

        """
        loop = asyncio.get_event_loop()

        # Process in chunks to balance memory usage and performance
        chunk_size = 100  # Process 100 DDS files at a time for better efficiency

        for chunk_start in range(0, len(dds_files), chunk_size):
            chunk = dds_files[chunk_start : chunk_start + chunk_size]

            # Create batch processing function for better efficiency
            def process_chunk(chunk_data: list[tuple[Path, Path]]) -> list[tuple[Path, int, int]]:
                """
                Process a chunk of DDS files in one executor call.

                Args:
                    chunk_data: List of tuples containing DDS file path and relative path.

                Returns:
                    list[tuple[Path, int, int]]: List of tuples with relative path, width, and height
                    for files with invalid dimensions.
                """
                results = []
                for file_path, relative_path in chunk_data:
                    header = self._read_dds_header_mmap(file_path)
                    if header:
                        width, height = header
                        if width % 2 != 0 or height % 2 != 0:
                            results.append((relative_path, width, height))
                return results

            # Process entire chunk in one executor call with semaphore
            async with self.dds_read_semaphore:
                chunk_results = await loop.run_in_executor(self.header_executor, process_chunk, chunk)

            # Update issue lists for the chunk
            if chunk_results:
                async with issue_locks["tex_dims"]:
                    for relative_path, width, height in chunk_results:
                        issue_lists["tex_dims"].add(f"  - {relative_path} ({width}x{height})\n")

    @staticmethod
    async def _read_ba2_header(file_path: Path, filename: str) -> bytes | None:
        """
        Reads the BA2 file header.

        Args:
            file_path (Path): The path to the BA2 file.
            filename (str): The name of the BA2 file for error reporting.

        Returns:
            bytes | None: The 12-byte header if successful, None if failed.
        """
        try:
            if aiofiles:
                async with aiofiles.open(file_path, "rb") as f:
                    return await f.read(12)
            else:
                # Fallback to sync read if aiofiles not available
                with file_path.open("rb") as f:
                    return f.read(12)
        except OSError:
            msg_warning(f"Failed to read file: {filename}")
            return None

    @staticmethod
    def _validate_ba2_header(header: bytes, filename: str, local_issues: dict[str, set[str]]) -> bool:
        """
        Validates BA2 file header format.

        Args:
            header (bytes): The BA2 file header.
            filename (str): The name of the BA2 file.
            local_issues (dict): Dictionary to store format issues.

        Returns:
            bool: True if header is valid, False otherwise.
        """
        if header[:4] != b"BTDX" or header[8:] not in {b"DX10", b"GNRL"}:
            local_issues["ba2_frmt"].add(f"  - {filename} : {header!s}\n")
            return False
        return True

    async def _process_texture_ba2(self, file_path: Path, filename: str, bsarch_path: Path) -> dict[str, set[str]]:
        """
        Processes a texture-format BA2 file (DX10).

        Args:
            file_path (Path): The path to the BA2 file.
            filename (str): The name of the BA2 file.
            bsarch_path (Path): Path to BSArch executable.

        Returns:
            dict[str, set[str]]: Dictionary of detected issues.
        """
        local_issues: dict[str, set[str]] = {"tex_dims": set(), "tex_frmt": set()}

        try:
            proc = await asyncio.create_subprocess_exec(
                str(bsarch_path),
                str(file_path),
                "-dump",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024,  # 1MB buffer limit to prevent memory issues
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=30)
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

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

                self._process_texture_block(file_block, filename, local_issues)

        except TimeoutError:
            msg_error(f"BSArch command timed out processing {filename}")
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            msg_error(f"Error processing {filename}: {e}")

        return local_issues

    @staticmethod
    def _process_texture_block(file_block: str, filename: str, local_issues: dict[str, set[str]]) -> None:
        """
        Processes a single texture block from BSArch output.

        Args:
            file_block (str): The texture block data.
            filename (str): The name of the BA2 file.
            local_issues (dict): Dictionary to store detected issues.
        """
        block_split: list[str] = file_block.split("\n", 3)

        # Check texture format
        if "Ext: dds" not in block_split[1]:
            local_issues["tex_frmt"].add(f"  - {block_split[0].rsplit('.', 1)[-1].upper()} : {filename} > {block_split[0]}\n")
            return

        # Check texture dimensions
        try:
            _, width, _, height, _ = block_split[2].split(maxsplit=4)
            if (width.isdecimal() and int(width) % 2 != 0) or (height.isdecimal() and int(height) % 2 != 0):
                local_issues["tex_dims"].add(f"  - {width}x{height} : {filename} > {block_split[0]}")
        except (ValueError, IndexError):
            # Skip if we can't parse dimensions
            pass

    async def _process_general_ba2(
        self, file_path: Path, filename: str, bsarch_path: Path, xse_scriptfiles: dict[str, str]
    ) -> dict[str, set[str]]:
        """
        Processes a general-format BA2 file (GNRL).

        Args:
            file_path (Path): The path to the BA2 file.
            filename (str): The name of the BA2 file.
            bsarch_path (Path): Path to BSArch executable.
            xse_scriptfiles (dict): Dictionary of XSE script files.

        Returns:
            dict[str, set[str]]: Dictionary of detected issues.
        """
        local_issues: dict[str, set[str]] = {
            "animdata": set(),
            "snd_frmt": set(),
            "xse_file": set(),
            "previs": set(),
        }

        try:
            proc = await asyncio.create_subprocess_exec(
                str(bsarch_path),
                str(file_path),
                "-list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024,  # 1MB buffer limit to prevent memory issues
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=30)
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            if proc.returncode != 0:
                msg_error(f"BSArch command failed for {filename}:\n{stderr}")
                return local_issues

            # Process file list
            output_split = stdout.lower().split("\n")
            self._analyze_general_files(output_split[15:], filename, file_path, xse_scriptfiles, local_issues)

        except TimeoutError:
            msg_error(f"BSArch command timed out processing {filename}")
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            msg_error(f"Error processing {filename}: {e}")

        return local_issues

    @staticmethod
    def _analyze_general_files(
        files: list[str], filename: str, file_path: Path, xse_scriptfiles: dict[str, str], local_issues: dict[str, set[str]]
    ) -> None:
        """
        Analyzes files in a general-format BA2 for various issues.

        Args:
            files (list[str]): List of files in the BA2.
            filename (str): The name of the BA2 file.
            file_path (Path): The path to the BA2 file.
            xse_scriptfiles (dict): Dictionary of XSE script files.
            local_issues (dict): Dictionary to store detected issues.
        """
        has_previs_files = has_anim_data = has_xse_files = False

        for file in files:
            # Check sound formats
            if file.endswith((".mp3", ".m4a")):
                local_issues["snd_frmt"].add(f"  - {file[-3:].upper()} : {filename} > {file}\n")
                continue

            # Check animation data
            if not has_anim_data and "animationfiledata" in file:
                has_anim_data = True
                local_issues["animdata"].add(f"  - {filename}\n")
                continue

            # Check XSE files
            if (
                not has_xse_files
                and any(f"scripts\\{key.lower()}" in file for key in xse_scriptfiles)
                and "workshop framework" not in str(file_path.parent).lower()
            ):
                has_xse_files = True
                local_issues["xse_file"].add(f"  - {filename}\n")
                continue

            # Check previs files
            if not has_previs_files and file.endswith((".uvd", "_oc.nif")):
                has_previs_files = True
                local_issues["previs"].add(f"  - {filename}\n")
