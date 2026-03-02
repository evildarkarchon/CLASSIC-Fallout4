"""Unpacked mod scanner component for classic_scangame.

This module provides specialized scanning functionality for unpacked (loose) mod files,
handling directory traversal, file type detection, cleanup operations, and issue tracking.
"""

import asyncio
import os
from collections import defaultdict
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ClassicLib.core.registry import get_local_dir
from ClassicLib.messaging import MessageTarget, msg_error, msg_info
from ClassicLib.scanning.game.checks.dds_processor import DDSProcessor
from ClassicLib.scanning.game.checks.file_operations import FileOperations
from ClassicLib.scanning.game.config import TEST_MODE


class UnpackedModsScanner:
    """Handle unpacked (loose) mod file scanning.

    This class provides specialized functionality for scanning unpacked mod files
    in the file system. It performs directory traversal, file type detection,
    cleanup operations (moving readme files and FOMOD folders), and issue tracking
    for various mod problems including texture formats, sound formats, animation
    data, XSE scripts, and previs files.

    Attributes:
        walk_executor (ThreadPoolExecutor): Executor for async directory walking operations.
        file_operations (FileOperations): Component for file/folder movement operations.
        dds_processor (DDSProcessor): Component for DDS texture validation.

    """

    def __init__(self, walk_executor: ThreadPoolExecutor, file_operations: FileOperations, dds_processor: DDSProcessor) -> None:
        """Initialize the UnpackedModsScanner.

        Args:
            walk_executor: Thread pool executor for async directory operations.
            file_operations: Component for handling file operations.
            dds_processor: Component for DDS texture processing.

        """
        self.walk_executor = walk_executor
        self.file_operations = file_operations
        self.dds_processor = dds_processor

    async def scan_unpacked_mods_async(
        self,
        mod_path: Path,
        xse_acronym: str,
        xse_scriptfiles: dict[str, set[str]],
        dds_check_callback: Callable[[list[tuple[Path, Path]], dict[str, set[str]], dict[str, asyncio.Lock]], Awaitable[None]],
    ) -> dict[str, set[str]]:
        """Scan unpacked mod files and return detected issues.

        This method recursively scans the mod directory for various issues including:
        - Cleanup items (readme files, FOMOD folders)
        - Animation data presence
        - Texture format and dimension issues
        - Sound format issues
        - XSE script files
        - Previs/Precombine files

        Args:
            mod_path: The mod directory path to scan.
            xse_acronym: XSE acronym (e.g., "F4SE", "SKSE") for script detection.
            xse_scriptfiles: Dictionary of XSE script files to detect.
            dds_check_callback: Async callback function for batch DDS checking.

        Returns:
            Dictionary of detected issues by category.

        Raises:
            OSError: If there is an error accessing the mod files.
            FileNotFoundError: If the mod folder path does not exist.

        Example:
            >>> scanner = UnpackedModsScanner(executor, file_ops, dds_processor)
            >>> issues = await scanner.scan_unpacked_mods_async(
            ...     Path("/mods"), "F4SE", {"f4se.dll": "F4SE"}, check_dds_func
            ... )
            >>> len(issues["tex_frmt"])
            3

        """
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

        # Setup paths
        backup_path: Path = Path(get_local_dir()) / "CLASSIC Backup/Cleaned Files"
        if not TEST_MODE:
            backup_path.mkdir(parents=True, exist_ok=True)  # noqa: ASYNC240

        msg_info("✔️ MODS FOLDER PATH FOUND! PERFORMING ASYNC MOD FILES SCAN...", target=MessageTarget.CONSOLE)

        # Filter names for cleanup
        filter_names: tuple[str, ...] = ("readme", "changes", "changelog", "change log")

        # Locks for thread-safe updates to shared collections
        issue_locks: dict[str, asyncio.Lock] = {issue_type: asyncio.Lock() for issue_type in issue_lists}

        # Create context for file operations
        context: dict[str, Any] = {"mod_path": mod_path, "backup_path": backup_path, "issue_lists": issue_lists, "issue_locks": issue_locks}

        # Collect all directories to process
        try:
            all_dirs_data = await self.walk_directory_async(mod_path)
        except (OSError, FileNotFoundError) as e:
            msg_error(f"Error accessing mod files: {e}")
            raise

        # Process all directories concurrently
        msg_info(f"Processing {len(all_dirs_data)} directories...")

        # Create tasks for all directories
        tasks = [
            self.process_directory_async(root, dirs, files, context, xse_acronym, xse_scriptfiles, filter_names, dds_check_callback)
            for root, dirs, files in all_dirs_data
        ]

        # Process in batches to avoid overwhelming the system
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)

        return issue_lists

    async def walk_directory_async(self, path: Path) -> list[tuple[Path, list[str], list[str]]]:
        """Recursively walk through directory tree asynchronously.

        This method performs optimized directory traversal using pathlib's rglob,
        collecting all directories, subdirectories, and files in the tree. The
        traversal is performed asynchronously in a thread pool to avoid blocking.

        Args:
            path: The starting directory path for traversal.

        Returns:
            List of tuples containing (directory_path, subdirectory_names, file_names).

        Raises:
            OSError: If there is an error accessing the directory.

        Example:
            >>> scanner = UnpackedModsScanner(executor, file_ops, dds_processor)
            >>> dirs = await scanner.walk_directory_async(Path("/mods"))
            >>> len(dirs)
            125

        """

        def _walk() -> list[tuple[Path, list[str], list[str]]]:
            """Optimized directory traversal using pathlib's rglob.

            Returns:
                List of tuples with directory info.

            """
            # Use rglob to get all paths in one operation - much faster than os.walk
            try:
                all_paths = list(path.rglob("*"))
            except (OSError, PermissionError):
                # Fallback to empty if we can't access
                return []

            # Group paths by parent directory for efficient processing
            dir_structure: defaultdict[Path, dict[str, list[str]]] = defaultdict(lambda: {"dirs": [], "files": []})  # pyright: ignore[reportUnknownReturnType]

            for p in all_paths:
                parent: Path = p.parent
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
                    direct_children: list[Path] = list(path.iterdir())
                    root_dirs: list[str] = [p.name for p in direct_children if p.is_dir()]
                    root_files: list[str] = [p.name for p in direct_children if p.is_file()]
                    if root_files or root_dirs:
                        dir_structure[path] = {"dirs": root_dirs, "files": root_files}
                except (OSError, PermissionError):
                    pass  # Skip inaccessible directories

            # Convert to expected format, maintaining bottom-up order for compatibility
            return [
                (parent, data["dirs"], data["files"])  # pyright: ignore[reportUnknownVariableType]
                for parent, data in sorted(dir_structure.items(), key=lambda x: str(x[0]).count(os.sep), reverse=True)
            ]

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.walk_executor, _walk)

    async def process_directory_async(
        self,
        root: Path,
        dirs: list[str],
        files: list[str],
        context: dict[str, Any],
        _xse_acronym: str,
        xse_scriptfiles: dict[str, set[str]],
        filter_names: tuple[str, ...],
        dds_check_callback: Callable[[list[tuple[Path, Path]], dict[str, set[str]], dict[str, asyncio.Lock]], Awaitable[None]],
    ) -> None:
        """Process a single directory for issues and cleanup operations.

        This method processes all files and subdirectories in a given directory,
        performing cleanup operations (moving FOMOD folders and readme files),
        detecting issues (texture formats, sound formats, etc.), and tracking
        XSE scripts, animation data, and previs files.

        Args:
            root: The directory being processed.
            dirs: List of subdirectory names in the directory.
            files: List of file names in the directory.
            context: Context dict with mod_path, backup_path, issue_lists, issue_locks.
            _xse_acronym: XSE acronym for script detection (unused, reserved for future use).
            xse_scriptfiles: Dictionary of XSE script files.
            filter_names: Tuple of strings to match for cleanup files.
            dds_check_callback: Async callback for batch DDS checking.

        Raises:
            Any exceptions from async operations are captured via return_exceptions.

        Example:
            >>> await scanner.process_directory_async(
            ...     Path("/mods/textures"), ["subdir"], ["file.dds"],
            ...     context, "F4SE", xse_scriptfiles, filter_names, dds_check_callback
            ... )

        """
        mod_path = context["mod_path"]
        issue_lists = context["issue_lists"]
        issue_locks = context["issue_locks"]

        root_main: Path = root.relative_to(mod_path).parent
        has_anim_data = False
        has_previs_files = False
        has_xse_files = False

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
                dir_tasks.append(self.file_operations.move_fomod_async(context, root, dirname))

        # Execute directory operations concurrently
        if dir_tasks:
            await asyncio.gather(*dir_tasks, return_exceptions=True)  # pyright: ignore[reportUnknownArgumentType]

        # Process files concurrently
        file_tasks: list[Any] = []
        dds_files: list[tuple[Path, Path]] = []

        for filename in files:
            file_path = root / filename
            relative_path = file_path.relative_to(mod_path)
            file_ext = file_path.suffix.lower()

            # Process file and update flags
            has_xse_files, has_previs_files = await self.process_file_by_type_async(
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
                xse_scriptfiles,
                filter_names,
            )

        # Process DDS files in batch
        if dds_files:
            file_tasks.append(dds_check_callback(dds_files, issue_lists, issue_locks))

        # Execute all file operations concurrently
        if file_tasks:
            await asyncio.gather(*file_tasks, return_exceptions=True)

    async def process_file_by_type_async(
        self,
        filename: str,
        file_path: Path,
        relative_path: Path,
        file_ext: str,
        context: dict[str, Any],
        file_tasks: list[Any],
        dds_files: list[tuple[Path, Path]],
        has_xse_files: bool,
        has_previs_files: bool,
        root: Path,
        root_main: Path,
        xse_scriptfiles: dict[str, set[str]],
        filter_names: tuple[str, ...],
    ) -> tuple[bool, bool]:
        """Process a single file based on its type.

        This method examines a file and takes appropriate action based on its type:
        - Cleanup files (readme, changelog) are queued for moving
        - DDS files are collected for batch processing
        - TGA/PNG files are flagged as texture format issues
        - MP3/M4A files are flagged as sound format issues
        - XSE script files are detected
        - Previs files (.uvd, _oc.nif) are detected

        Args:
            filename: The file name.
            file_path: Full path to the file.
            relative_path: Path relative to mod directory.
            file_ext: File extension (lowercase with dot).
            context: Context dict with issue_lists and issue_locks.
            file_tasks: List to append file operation tasks to.
            dds_files: List to append DDS files to for batch processing.
            has_xse_files: Whether XSE files have been found in this directory.
            has_previs_files: Whether previs files have been found in this directory.
            root: Current directory being processed.
            root_main: Root directory relative to mod path.
            xse_scriptfiles: Dictionary of XSE script files to detect.
            filter_names: Tuple of strings to match for cleanup files.

        Returns:
            Updated (has_xse_files, has_previs_files) flags.

        Example:
            >>> has_xse, has_previs = await scanner.process_file_by_type_async(
            ...     "texture.dds", Path("/mod/texture.dds"), Path("texture.dds"),
            ...     ".dds", context, tasks, dds_list, False, False,
            ...     Path("/mod"), Path("."), xse_files, filter_names
            ... )
            >>> len(dds_list)
            1

        """
        issue_lists = context["issue_lists"]
        issue_locks = context["issue_locks"]
        filename_lower = filename.lower()

        # Cleanup operations
        if filename_lower.endswith(".txt") and any(name in filename_lower for name in filter_names):
            file_tasks.append(self.file_operations.move_file_async(context, file_path))
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
            and file_path.parent.name.lower() == "scripts"
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
