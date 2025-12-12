"""GameFilesManager module - Async-first game file backup/restore/remove operations.

This module provides async-first implementations for managing game files through
backup, restore, and remove operations. It follows the project's architectural
pattern with core async functions and sync adapters for backwards compatibility.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Literal, cast

from ClassicLib import GlobalRegistry, msg_error, msg_info, msg_success
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.Constants import YAML
from ClassicLib.FileIO import FileIOCore
from ClassicLib.Logger import logger
from ClassicLib.YamlSettings import yaml_settings


class GameFilesManagerCore:
    """Core functionality for managing game files.

    This class provides asynchronous methods to handle operations such as backing up,
    restoring, and removing game files. It leverages a file I/O core utility to
    interact with the filesystem and maintain the integrity of game data during these
    operations.

    Attributes:
        file_io (FileIOCore): The file I/O core utility used to manage file operations.

    """

    def __init__(self) -> None:
        """Initialize an instance of the class.

        This constructor sets up an instance of the class with the default
        settings and initializes necessary components for managing file input
        and output operations.
        """
        self.file_io = FileIOCore()

    async def manage_game_files_async(self, classic_list: str, mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
        """Async implementation of game files management operations.

        Manages game files by performing backup, restore, or removal operations.
        The function interacts with the game's directory and modifies files based
        on the specified mode.

        Args:
            classic_list: The name of the list specifying which files need to be managed.
                This parameter is used to identify target files or directories in the
                game's folder.
            mode: The operation mode to be performed on the files. Available options are:
                - "BACKUP": Creates a backup of the specified files.
                - "RESTORE": Restores the files from a backup to the game folder.
                - "REMOVE": Deletes the specified files from the game folder.

        Raises:
            FileNotFoundError: If the specified game folder is not found or is not a
                valid directory.
            PermissionError: If there are file permission issues preventing the
                operation from completing.
            OSError: If a system-related error occurs during file operations.
            IsADirectoryError: If a directory is encountered where a file is expected.

        """
        # Constants
        # noinspection PyPep8Naming
        BACKUP_DIR = "CLASSIC Backup/Game Files"

        def _validate_game_path(path: Path | None) -> None:
            """Validate the provided game folder path.

            This function ensures that the given `path` is not `None`. If the `path`
            is `None`, it raises a `FileNotFoundError` indicating that the game
            folder was not found.

            Args:
                path (Path | None): The path to the game folder being validated. If
                    `None`, it triggers an error.

            Raises:
                FileNotFoundError: If the `path` is `None`, indicating the game
                    folder could not be located.

            """
            if path is None:
                raise FileNotFoundError("Game folder not found")

        try:
            # Get paths and settings
            game_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")
            manage_list_setting: list[str] | None = yaml_settings(list[str], YAML.Game, classic_list)
            manage_list: list[str] = manage_list_setting if isinstance(manage_list_setting, list) else []

            # Validate game path
            _validate_game_path(game_path)
            # Type narrowing: game_path is validated by _validate_game_path (raises if None)
            game_path = cast("Path", game_path)

            # Set up backup path
            backup_path: Path = Path(f"{BACKUP_DIR}/{classic_list}")
            self._ensure_directory_exists_async(backup_path)

            # Extract list name for display purposes
            list_name: str = classic_list.split(maxsplit=1)[-1]

            # Perform the requested operation
            if mode == "BACKUP":
                await self._backup_files_async(game_path, backup_path, manage_list, list_name)
            elif mode == "RESTORE":
                await self._restore_files_async(game_path, backup_path, manage_list, list_name)
            elif mode == "REMOVE":
                await self._remove_files_async(game_path, manage_list, list_name)

        except PermissionError:
            self._handle_permission_error(mode, classic_list.split(maxsplit=1)[-1])
            raise
        except (OSError, FileNotFoundError, IsADirectoryError) as e:
            logger.error(f"File operation error in manage_game_files_async: {e}")
            raise
        # Let other exceptions (KeyError, AttributeError, etc.) propagate naturally without logging

    # noinspection PyUnresolvedReferences,PyTypeChecker
    @staticmethod
    def _ensure_directory_exists_async(path: Path) -> None:  # no longer async because mkdir is very fast
        """Ensure that the specified directory exists asynchronously. If the directory does not
        exist, it will be created along with any necessary parent directories.

        Args:
            path (Path): The path of the directory to check or create.

        """
        # Path.mkdir() is a fast filesystem operation - creating directories is near-instantaneous
        # on modern filesystems (typically < 1ms). The overhead of using run_in_executor
        # (thread pool scheduling, context switching) is 5-10ms, which is significantly
        # MORE than the actual operation time. Running directly saves ~5-10ms per call.
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _glob_sync(path: Path, pattern: str) -> list[Path]:
        """Perform synchronously a glob operation.

        Args:
            path: The Path object to perform the glob operation on.
            pattern: The glob pattern to match (e.g., "*", "*.txt").

        Returns:
            A list of Path objects matching the pattern.

        """
        return list(path.glob(pattern))

    async def _glob_async(self, path: Path, pattern: str) -> list[Path]:
        """Asynchronously performs a glob operation on the given path.

        This method executes the blocking Path.glob() operation in a thread pool
        to avoid blocking the async event loop.

        Args:
            path: The Path object to perform the glob operation on.
            pattern: The glob pattern to match (e.g., "*", "*.txt").

        Returns:
            A list of Path objects matching the pattern.

        """
        # Run blocking glob operation in thread pool to avoid blocking event loop
        return await asyncio.to_thread(self._glob_sync, path, pattern)

    @staticmethod
    def _exists_sync(path: Path) -> bool:
        """Check synchronously if a path exists.

        Args:
            path: The Path object to check for existence.

        Returns:
            True if the path exists, False otherwise.

        """
        return path.exists()

    async def _exists_async(self, path: Path) -> bool:
        """Asynchronously checks if a path exists.

        This method executes the blocking Path.exists() operation in a thread pool
        to avoid blocking the async event loop.

        Args:
            path: The Path object to check for existence.

        Returns:
            True if the path exists, False otherwise.

        """
        # Run blocking exists check in thread pool to avoid blocking event loop
        return await asyncio.to_thread(self._exists_sync, path)

    async def _backup_files_async(self, game_path: Path, backup_path: Path, manage_list: list[str], list_name: str) -> None:
        """Create a backup of specified game files asynchronously.

        This function identifies all files in the provided game directory that match
        a predefined list of managed file patterns. It then makes use of asynchronous
        file copying operations, with a concurrency limit enforced by a semaphore,
        to back up these files to the specified backup location.

        Args:
            game_path (Path): Path to the game directory containing files to be backed up.
            backup_path (Path): Path to the destination directory where the backups will be stored.
            manage_list (list[str]): List of file patterns or names specifying which files should be backed up.
            list_name (str): Friendly name used to describe the collection of files being backed up.

        """
        msg_info(f"CREATING A BACKUP OF {list_name} FILES, PLEASE WAIT...")

        # Get all matching files asynchronously
        all_files = await self._glob_async(game_path, "*")
        matching_files = [file for file in all_files if self._matches_managed_file(file.name, manage_list)]

        # Process files concurrently with semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(8)  # Limit concurrent file operations
        tasks = [self._copy_file_with_semaphore(semaphore, file, backup_path / file.name) for file in matching_files]

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Check for exceptions in results
            failed_operations = [r for r in results if isinstance(r, Exception)]
            if failed_operations:
                logger.error(f"Some backup operations failed for {list_name}:")
                for exc in failed_operations:
                    logger.error(f"  - {type(exc).__name__}: {exc}")
                # Continue execution - partial backup is better than no backup

        msg_success(f"SUCCESSFULLY CREATED A BACKUP OF {list_name} FILES\n")

    async def _restore_files_async(self, game_path: Path, backup_path: Path, manage_list: list[str], list_name: str) -> None:
        """Restore files from a backup directory to the game directory asynchronously. This method identifies
        files in the game directory that match a specific list of managed files and restores their backups
        from the provided backup path, if available. Restoration operations are limited to a specified
        number of concurrent tasks.

        Args:
            game_path: A Path object representing the directory containing game files.
            backup_path: A Path object representing the directory containing backup files.
            manage_list: A list of strings representing the names or patterns of files to be managed
                during the restoration process.
            list_name: A string specifying the name or identifier of the list of files being restored.

        """
        msg_info(f"RESTORING {list_name} FILES FROM A BACKUP, PLEASE WAIT...")

        # Get all matching files that have backups asynchronously
        restore_tasks = []
        semaphore = asyncio.Semaphore(8)  # Limit concurrent file operations

        all_files = await self._glob_async(game_path, "*")
        for file in all_files:
            if self._matches_managed_file(file.name, manage_list):
                source_file = backup_path / file.name
                if await self._exists_async(source_file):
                    restore_tasks.append(self._copy_file_with_semaphore(semaphore, source_file, file))

        if restore_tasks:
            results = await asyncio.gather(*restore_tasks, return_exceptions=True)
            # Check for exceptions in results
            failed_operations = [r for r in results if isinstance(r, Exception)]
            if failed_operations:
                logger.error(f"Some restore operations failed for {list_name}:")
                for exc in failed_operations:
                    logger.error(f"  - {type(exc).__name__}: {exc}")
                # Continue execution - partial restore is better than no restore

        msg_success(f"SUCCESSFULLY RESTORED {list_name} FILES TO THE GAME FOLDER\n")

    async def _remove_files_async(self, game_path: Path, manage_list: list[str], list_name: str) -> None:
        """Asynchronously removes files from a game directory based on a specified list of managed file patterns.

        This method identifies files in the specified game path that match the patterns provided in
        the manage_list and removes them. File operations are performed concurrently with a semaphore
        to restrict the number of simultaneous file operations.

        Args:
            game_path (Path): Path to the game directory where files will be removed.
            manage_list (list[str]): List of file name patterns to match and remove from the game directory.
            list_name (str): Name or category of the managed files being removed.

        """
        msg_info(f"REMOVING {list_name} FILES FROM YOUR GAME FOLDER, PLEASE WAIT...")

        # Get all matching files asynchronously
        all_files = await self._glob_async(game_path, "*")
        matching_files = [file for file in all_files if self._matches_managed_file(file.name, manage_list)]

        # Process files concurrently with semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(8)  # Limit concurrent file operations
        tasks = [self._remove_file_with_semaphore(semaphore, file) for file in matching_files]

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Check for exceptions in results
            failed_operations = [r for r in results if isinstance(r, Exception)]
            if failed_operations:
                logger.error(f"Some remove operations failed for {list_name}:")
                for exc in failed_operations:
                    logger.error(f"  - {type(exc).__name__}: {exc}")
                # Continue execution - partial removal is tracked

        msg_success(f"SUCCESSFULLY REMOVED {list_name} FILES FROM THE GAME FOLDER\n")

    async def _copy_file_with_semaphore(self, semaphore: asyncio.Semaphore, source: Path, destination: Path) -> None:
        """Copy a file while ensuring the operation adheres to a limit on concurrent tasks,
        enforced by a semaphore.

        This coroutine ensures that the copying operation does not exceed the
        maximum number of concurrent operations specified by the semaphore.

        Args:
            semaphore (asyncio.Semaphore): Semaphore used to limit the number of concurrent tasks.
            source (Path): The source file path to copy from.
            destination (Path): The destination file path to copy to.

        """
        async with semaphore:
            await self._copy_file_or_directory_async(source, destination)

    async def _remove_file_with_semaphore(self, semaphore: asyncio.Semaphore, file: Path) -> None:
        """Remove a file asynchronously, ensuring that the operation respects the limitation
        imposed by the provided semaphore. This function enables concurrency control to
        prevent exceeding specified limits in operations such as file deletions.

        Args:
            semaphore: An asyncio.Semaphore instance used to control the number of concurrent
                asynchronous file operations.
            file: A Path object representing the file to be removed.

        """
        async with semaphore:
            await self._remove_file_async(file)

    # noinspection PyUnresolvedReferences,PyTypeChecker
    @staticmethod
    async def _copy_file_or_directory_async(source: Path, destination: Path) -> None:
        """Asynchronously copies a file or directory from the source to the destination
        using a synchronous copy operation executed in a thread pool.

        The method attempts to replicate the source file or directory structure at
        the destination. For files, it uses a standard file copy. For directories,
        it handles edge cases like overwriting existing files or directories at the
        destination. Errors during the copying process are logged and re-raised.

        Args:
            source (Path): The path of the file or directory to be copied.
            destination (Path): The target path for the copied file or directory.

        Raises:
            PermissionError: If permission is denied while copying.
            OSError: If a system-related error occurs.
            FileNotFoundError: If the source does not exist.
            FileExistsError: If a naming conflict occurs during copying.
            Exception: For any other unexpected error during copying.

        """

        def copy_operation() -> None:
            """Copy a file or directory from a source to a destination with error handling.

            The function checks whether the source is a file or a directory. Based on this
            check, it uses appropriate methods to copy the source to the destination. If the
            destination already exists, it handles this case by either removing the existing
            destination directory or unlinking the file. During the operation, any relevant
            exceptions are caught and logged.

            Raises:
                PermissionError: If permission is denied while accessing the source or
                    destination.
                OSError: Raised for system-related errors during the copy operation.
                FileNotFoundError: If the source or destination paths are invalid.
                FileExistsError: If the destination file or directory unexpectedly exists when
                    it shouldn't.
                Exception: For any other unexpected errors encountered during the copy
                    operation.

            """
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

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, copy_operation)

    # noinspection PyUnresolvedReferences,PyTypeChecker
    @staticmethod
    async def _remove_file_async(file: Path) -> None:
        """Asynchronously removes a file or directory. This method ensures that the file or directory is
        deleted using an asynchronous approach via a thread executor to avoid blocking the event loop.

        Args:
            file (Path): The file or directory path that needs to be removed.

        Raises:
            PermissionError: If permission is denied while attempting to remove the file or directory.
            Exception: If an unexpected error occurs during the removal process.

        """

        def remove_operation() -> None:
            """Remove a file or directory specified by the `file` variable.

            This function attempts to remove the specified file or directory.
            If the file or directory does not exist, or it is inaccessible due to
            specific file permissions, appropriate error handling is applied.

            Raises:
                PermissionError: If the operation lacks necessary permissions to
                    delete the file or directory.
                Exception: For any unexpected errors that occur during the removal
                    process. The original error message is included in the raised
                    exception.

            """
            try:
                if file.is_file():
                    file.unlink(missing_ok=True)
                elif file.is_dir():
                    shutil.rmtree(file)
            except PermissionError:
                msg_error(f"Permission denied removing {file}")
                raise
            except Exception as e:
                msg_error(f"Unexpected error removing {file}: {e}")
                raise

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, remove_operation)

    @staticmethod
    def _matches_managed_file(file_name: str, manage_list: list[str]) -> bool:
        """Determine if a file name matches any of the criteria in the managed list.

        This static method checks whether the given file name contains any of the
        strings specified in the managed list, ignoring case.

        Args:
            file_name (str): The name of the file to be checked.
            manage_list (list[str]): A list of strings representing the criteria
                to check against the file name.

        Returns:
            bool: True if the file name matches any entry in the managed list,
            otherwise False.

        """
        return any(item.lower() in file_name.lower() for item in manage_list)

    @staticmethod
    def _handle_permission_error(operation: str, list_name: str) -> None:
        """Handle permission-related errors encountered during file operations.

        This utility function logs an error message when the program is unable
        to perform the specified operation on the specified file due to file
        permissions. It advises the user to run the program in admin mode to
        resolve the issue.

        Args:
            operation (str): The attempted operation (e.g., 'read', 'write', 'delete').
            list_name (str): The name of the file or list the operation is targeting.

        """
        ERROR_PREFIX = "ERROR :"
        ADMIN_SUGGESTION = "    TRY RUNNING CLASSIC.EXE IN ADMIN MODE TO RESOLVE THIS PROBLEM.\n"
        msg_error(f"{ERROR_PREFIX} UNABLE TO {operation} {list_name} FILES DUE TO FILE PERMISSIONS!\n{ADMIN_SUGGESTION}")


# Global singleton instance
_game_files_manager_core: GameFilesManagerCore | None = None


def get_game_files_manager_core() -> GameFilesManagerCore:
    """Retrieve or initializes the global instance of the `GameFilesManagerCore` class.

    This function ensures that a single instance of the `GameFilesManagerCore`
    is created and reused across the application. It initializes the global
    instance if it has not been created already.

    Returns:
        GameFilesManagerCore: The global instance of the `GameFilesManagerCore` class.

    """
    global _game_files_manager_core  # noqa: PLW0603
    if _game_files_manager_core is None:
        _game_files_manager_core = GameFilesManagerCore()
    return _game_files_manager_core


# Async-first interface
async def manage_game_files_async(classic_list: str, mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
    """Async interface for game files management operations.

    Args:
        classic_list: The name of the list specifying which files need to be managed.
        mode: The operation mode ("BACKUP", "RESTORE", or "REMOVE").

    Raises:
        FileNotFoundError: If the specified game folder is not found.
        PermissionError: If there are file permission issues.

    """
    core = get_game_files_manager_core()
    await core.manage_game_files_async(classic_list, mode)


# Sync adapter for backwards compatibility and GUI usage
def manage_game_files(classic_list: str, mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
    """Sync adapter for game files management operations.

    Manages game files by performing backup, restore, or removal operations.
    The function interacts with the game's directory and modifies files based
    on the specified mode.

    IMPORTANT - Usage:
    ✅ GUI workers and Qt threads
    ✅ Testing and benchmarking
    ❌ Production CLI code (use manage_game_files_async() instead)

    For CLI production code, use the async version:
        await manage_game_files_async(classic_list, mode)

    Args:
        classic_list: The name of the list specifying which files need to be managed.
            This parameter is used to identify target files or directories in the
            game's folder.
        mode: The operation mode to be performed on the files. Available options are:
            - "BACKUP": Creates a backup of the specified files.
            - "RESTORE": Restores the files from a backup to the game folder.
            - "REMOVE": Deletes the specified files from the game folder.
            Defaults to "BACKUP".

    Raises:
        FileNotFoundError: If the specified game folder is not found or is not a
            valid directory.
        PermissionError: If there are file permission issues preventing the operation
            from completing.

    """
    bridge = AsyncBridge.get_instance()
    bridge.run_async(manage_game_files_async(classic_list, mode))
