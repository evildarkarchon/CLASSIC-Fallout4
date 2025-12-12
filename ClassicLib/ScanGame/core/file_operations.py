"""File operations for mod scanning (moving, cleanup, etc.)."""

import asyncio
import shutil
from pathlib import Path

from ClassicLib import msg_error
from ClassicLib.ScanGame.Config import TEST_MODE


class FileOperations:
    """Represent a class managing file operation tasks with controlled concurrency.

    This class is designed to handle file operations such as moving files or folders
    asynchronously while ensuring a controlled level of concurrency through the use
    of an asyncio semaphore. Intended for scenarios where concurrent file system
    interaction is required without overwhelming system resources.

    Attributes:
        file_ops_semaphore (asyncio.Semaphore): Semaphore to control the number of
            concurrent file operations.

    """

    def __init__(self, file_ops_semaphore: asyncio.Semaphore) -> None:
        """Initialize an instance of the class encapsulating a semaphore for file operations.

        This constructor sets up the semaphore that is used to regulate access to
        file operations, ensuring that a defined number of operations can proceed
        simultaneously to avoid resource contention.

        Args:
            file_ops_semaphore (asyncio.Semaphore): Semaphore object controlling
                the number of concurrent file operations.

        """
        self.file_ops_semaphore = file_ops_semaphore

    async def move_fomod_async(self, context: dict, root: Path, dirname: str) -> None:
        """Move a specified folder asynchronously to a backup location while handling potential
        errors and updating issue tracking.

        Performs the folder move operation inside an asyncio semaphore to ensure controlled
        parallel execution. If TEST_MODE is active, the operation is skipped. Updates are appended
        to a shared context issue list under 'cleanup' locks for thread safety.

        Args:
            context (dict): A dictionary containing mod_path, backup_path, issue_locks, and issue_lists
                to manage paths and track issues during execution.
            root (Path): The base directory path where the folder to be moved resides.
            dirname (str): The name of the directory that needs to be moved.

        """
        async with self.file_ops_semaphore:
            fomod_folder_path: Path = root / dirname
            relative_path: Path = fomod_folder_path.relative_to(context["mod_path"])
            new_folder_path: Path = context["backup_path"] / relative_path

            if not TEST_MODE:
                try:
                    # Use executor for blocking shutil.move
                    loop = asyncio.get_running_loop()
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
        """Asynchronously moves a file from the current location to a backup location specified
        in the context. Ensures that the backup directory structure is maintained. Handles
        possible exceptions during the file operation process and logs errors appropriately.

        Args:
            context (dict): A dictionary containing configuration details, including
                paths and synchronization mechanisms required for file operations.
                Keys include `mod_path`, `backup_path`, `issue_locks`, and `issue_lists`.
            file_path (Path): The path of the file to be moved.

        Raises:
            PermissionError: Raised if there is no permission to move the file.
            OSError: Raised for system-related errors during file operations.
            FileNotFoundError: Raised if the file to be moved is not found.
            FileExistsError: Raised if the destination file already exists.

        """
        async with self.file_ops_semaphore:
            relative_path: Path = file_path.relative_to(context["mod_path"])
            new_file_path: Path = context["backup_path"] / relative_path

            # Create parent directory if it doesn't exist
            new_file_path.parent.mkdir(parents=True, exist_ok=True)

            if not TEST_MODE:
                try:
                    # Use executor for blocking file operations
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, shutil.move, str(file_path), str(new_file_path))
                except PermissionError:
                    msg_error(f"Permission denied moving file: {file_path}")
                    return
                except (OSError, FileNotFoundError, FileExistsError) as e:
                    msg_error(f"Failed to move file {file_path}: {e}")
                    return

            async with context["issue_locks"]["cleanup"]:
                context["issue_lists"]["cleanup"].add(f"  - {relative_path}\n")
