"""Async-first core implementation for CLASSIC_ScanGame.py operations.

This module provides the primary async implementations that are used by both
sync adapters (for backwards compatibility) and async callers directly.
All I/O-intensive operations are implemented asynchronously for optimal performance.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast

from ClassicLib import GlobalRegistry, msg_info
from ClassicLib.Constants import YAML
from ClassicLib.GlobalRegistry import get, register

# Import refactored components
from ClassicLib.ScanGame.core import (
    SCAN_GAME_CORE_KEY,
    BA2ArchiveScanner,
    DDSProcessor,
    FileOperations,
    LogProcessor,
    ScanReportBuilder,
    ScanValidators,
    UnpackedModsScanner,
    get_optimal_limits,
)
from ClassicLib.YamlSettings import yaml_settings_async


class ScanGameCore:
    """Implement the core functionalities for scanning mods in an optimized and
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
        """Create a new instance of the ScanGameCore class or retrieves an existing one
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
        """Initialize the class and configures internal semaphores, thread pools, and
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
            self.ba2_scanner = BA2ArchiveScanner(self.process_semaphore, self.walk_executor)
            self.unpacked_scanner = UnpackedModsScanner(self.walk_executor, self.file_operations, self.dds_processor)
            self.report_builder = ScanReportBuilder(self.validators)

            self._initialized = True

    async def cleanup_async(self) -> None:
        """Clean up thread pool executors to prevent resource leaks.

        This method should be called when the ScanGameCore instance is no longer needed
        to ensure proper cleanup of thread pools. It gracefully shuts down both
        header_executor and walk_executor.

        Note:
            This is an async method to allow cleanup to happen without blocking the event loop.
            The actual shutdown operations are run in the executor to avoid blocking.

        """
        loop = asyncio.get_running_loop()

        # Shutdown executors in parallel
        await asyncio.gather(
            loop.run_in_executor(None, self.header_executor.shutdown, True),
            loop.run_in_executor(None, self.walk_executor.shutdown, True),
            return_exceptions=False,
        )

    async def get_scan_settings(self) -> tuple[str, dict[str, str], Path | None]:
        """Retrieve settings required for a scanning process asynchronously.

        Returns:
            Tuple of (game_type, ini_settings, game_path) for the scan configuration.

        """
        return await self.validators.get_scan_settings()

    def get_issue_messages(self, xse_acronym: str, mode: str) -> dict[str, list[str]]:
        """Retrieve issue messages for the given acronym and mode.

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
        """Check for errors in log files within the specified folder.

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
        """Scan and processes unpacked mod files for cleanup and issue detection. The method performs
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
        # Get settings
        xse_acronym, xse_scriptfiles, mod_path = await self.get_scan_settings()

        if not mod_path:
            return str(await yaml_settings_async(str, YAML.Main, "Mods_Warn.Mods_Path_Missing"))

        # Delegate scanning to unpacked_scanner
        try:
            issue_lists = await self.unpacked_scanner.scan_unpacked_mods_async(
                mod_path, xse_acronym, xse_scriptfiles, self._check_dds_batch_async
            )
        except (OSError, FileNotFoundError):
            return "Error: Could not access mod files"

        # Build and return report
        return self.report_builder.build_unpacked_report(issue_lists, xse_acronym)

    async def scan_mods_archived(self) -> str:
        """Asynchronously scans for archived .ba2 mod files and processes them to detect potential issues
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
              analyze textures, sound formats, XSE files, etc.
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
        ba2_files = await self.ba2_scanner.find_ba2_files_async(mod_path)
        if not ba2_files:
            return self.report_builder.build_archived_report(issue_lists, xse_acronym)

        # Process all BA2 files concurrently
        results = await self.ba2_scanner.process_ba2_files_async(ba2_files, bsarch_path, xse_scriptfiles)

        # Merge results into issue lists
        BA2ArchiveScanner.merge_scan_results(results, issue_lists)

        return self.report_builder.build_archived_report(issue_lists, xse_acronym)

    async def _initialize_archived_scan(self) -> tuple[dict[str, set[str]], str, dict[str, str], Path, Path] | str:
        """Initialize the archived scan with validation and setup.

        Returns:
            Either a tuple of initialized components or an error message string.

        """
        # Initialize sets for collecting different issue types
        issue_lists: dict[str, set[str]] = {
            "ba2_frmt": set(),
            "tex_dims": set(),
            "tex_frmt": set(),
            "snd_frmt": set(),
            "xse_file": set(),
        }

        # Get settings
        xse_acronym, xse_scriptfiles, mod_path = await self.get_scan_settings()

        # Setup paths
        bsarch_path: Path = cast("Path", GlobalRegistry.get_local_dir()) / "CLASSIC Data/BSArch.exe"

        # Validate requirements
        validation_error = await self._validate_archived_scan_requirements(mod_path, bsarch_path)
        if validation_error:
            return validation_error

        # Type narrowing: mod_path is validated (validation returns error if None)
        mod_path = cast("Path", mod_path)
        return issue_lists, xse_acronym, xse_scriptfiles, mod_path, bsarch_path

    @staticmethod
    async def _validate_archived_scan_requirements(mod_path: Path | None, bsarch_path: Path) -> str | None:
        """Validate all requirements for archived scan.

        Returns:
            Error message if validation fails, None if all requirements are satisfied.

        """
        if not mod_path:
            return str(await yaml_settings_async(str, YAML.Main, "Mods_Warn.Mods_Path_Missing"))
        if not mod_path.exists():  # noqa: ASYNC240
            return str(await yaml_settings_async(str, YAML.Main, "Mods_Warn.Mods_Path_Invalid"))
        if not bsarch_path.exists():  # noqa: ASYNC240
            return str(await yaml_settings_async(str, YAML.Main, "Mods_Warn.Mods_BSArch_Missing"))
        return None

    # Helper methods for internal operations
    async def _check_dds_batch_async(self, dds_files: list[tuple[Path, Path]], issue_lists: dict, issue_locks: dict) -> None:
        """Check a batch of DDS files asynchronously to validate their dimensions and adds issues
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
        loop = asyncio.get_running_loop()

        # Capture reference to dds_processor for use in closure
        read_header = self.dds_processor.read_dds_header_mmap

        # Process in chunks to balance memory usage and performance
        chunk_size = 100  # Process 100 DDS files at a time for better efficiency

        for chunk_start in range(0, len(dds_files), chunk_size):
            chunk = dds_files[chunk_start : chunk_start + chunk_size]

            # Create batch processing function for better efficiency
            def process_chunk(chunk_data: list[tuple[Path, Path]]) -> list[tuple[Path, int, int]]:
                """Process a chunk of DDS files in one executor call.

                Args:
                    chunk_data: List of tuples containing DDS file path and relative path.

                Returns:
                    list[tuple[Path, int, int]]: List of tuples with relative path, width, and height
                    for files with invalid dimensions.

                """
                results = []
                for file_path, relative_path in chunk_data:
                    header = read_header(file_path)
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
