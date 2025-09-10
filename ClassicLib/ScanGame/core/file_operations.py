"""File operations for mod scanning (moving, cleanup, etc.)."""

import asyncio
import shutil
from pathlib import Path

from ClassicLib import msg_error
from ClassicLib.ScanGame.Config import TEST_MODE


class FileOperations:
    """Handles file operations during mod scanning."""

    def __init__(self, file_ops_semaphore: asyncio.Semaphore) -> None:
        """Initialize with semaphore for concurrency control."""
        self.file_ops_semaphore = file_ops_semaphore

    async def move_fomod_async(self, context: dict, root: Path, dirname: str) -> None:
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

    async def move_file_async(self, context: dict, file_path: Path) -> None:
        """Async move file to backup location."""
        async with self.file_ops_semaphore:
            relative_path: Path = file_path.relative_to(context["mod_path"])
            new_file_path: Path = context["backup_path"] / relative_path

            # Create parent directory if it doesn't exist
            new_file_path.parent.mkdir(parents=True, exist_ok=True)

            if not TEST_MODE:
                try:
                    # Use executor for blocking file operations
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
