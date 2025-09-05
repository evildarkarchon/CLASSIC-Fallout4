"""
GameFilesManager module - Async-first game file backup/restore/remove operations.

This module provides async-first implementations for managing game files through
backup, restore, and remove operations. It follows the project's architectural
pattern with core async functions and sync adapters for backwards compatibility.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Literal

from ClassicLib import GlobalRegistry, msg_error, msg_info, msg_success
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.Constants import YAML
from ClassicLib.FileIOCore import FileIOCore
from ClassicLib.Logger import logger
from ClassicLib.YamlSettingsCache import yaml_settings


class GameFilesManagerCore:
    """Async-first core implementation for game file management operations."""

    def __init__(self) -> None:
        """Initialize the game files manager core."""
        self.file_io = FileIOCore()

    async def manage_game_files_async(self, classic_list: str, mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
        """
        Async implementation of game files management operations.

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
        """
        # Constants
        BACKUP_DIR = "CLASSIC Backup/Game Files"

        def _validate_game_path(path: Path | None) -> None:
            """Validate that the game path exists."""
            if path is None:
                raise FileNotFoundError("Game folder not found")

        try:
            # Get paths and settings
            game_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game")
            manage_list_setting: list[str] | None = yaml_settings(list[str], YAML.Game, classic_list)
            manage_list: list[str] = manage_list_setting if isinstance(manage_list_setting, list) else []

            # Validate game path
            _validate_game_path(game_path)

            # Set up backup path
            backup_path: Path = Path(f"{BACKUP_DIR}/{classic_list}")
            await self._ensure_directory_exists_async(backup_path)

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
        except Exception as e:
            logger.error(f"Unexpected error in manage_game_files_async: {e}")
            raise

    async def _ensure_directory_exists_async(self, path: Path) -> None:
        """Ensure directory exists asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: path.mkdir(parents=True, exist_ok=True))

    async def _backup_files_async(self, game_path: Path, backup_path: Path, manage_list: list[str], list_name: str) -> None:
        """Backup files asynchronously."""
        msg_info(f"CREATING A BACKUP OF {list_name} FILES, PLEASE WAIT...")

        # Get all matching files
        matching_files = [file for file in game_path.glob("*") if self._matches_managed_file(file.name, manage_list)]

        # Process files concurrently with semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(8)  # Limit concurrent file operations
        tasks = [self._copy_file_with_semaphore(semaphore, file, backup_path / file.name) for file in matching_files]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        msg_success(f"SUCCESSFULLY CREATED A BACKUP OF {list_name} FILES\n")

    async def _restore_files_async(self, game_path: Path, backup_path: Path, manage_list: list[str], list_name: str) -> None:
        """Restore files asynchronously."""
        msg_info(f"RESTORING {list_name} FILES FROM A BACKUP, PLEASE WAIT...")

        # Get all matching files that have backups
        restore_tasks = []
        semaphore = asyncio.Semaphore(8)  # Limit concurrent file operations

        for file in game_path.glob("*"):
            if self._matches_managed_file(file.name, manage_list):
                source_file = backup_path / file.name
                if source_file.exists():
                    restore_tasks.append(self._copy_file_with_semaphore(semaphore, source_file, file))

        if restore_tasks:
            await asyncio.gather(*restore_tasks, return_exceptions=True)

        msg_success(f"SUCCESSFULLY RESTORED {list_name} FILES TO THE GAME FOLDER\n")

    async def _remove_files_async(self, game_path: Path, manage_list: list[str], list_name: str) -> None:
        """Remove files asynchronously."""
        msg_info(f"REMOVING {list_name} FILES FROM YOUR GAME FOLDER, PLEASE WAIT...")

        # Get all matching files
        matching_files = [file for file in game_path.glob("*") if self._matches_managed_file(file.name, manage_list)]

        # Process files concurrently with semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(8)  # Limit concurrent file operations
        tasks = [self._remove_file_with_semaphore(semaphore, file) for file in matching_files]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        msg_success(f"SUCCESSFULLY REMOVED {list_name} FILES FROM THE GAME FOLDER\n")

    async def _copy_file_with_semaphore(self, semaphore: asyncio.Semaphore, source: Path, destination: Path) -> None:
        """Copy a file or directory with semaphore control."""
        async with semaphore:
            await self._copy_file_or_directory_async(source, destination)

    async def _remove_file_with_semaphore(self, semaphore: asyncio.Semaphore, file: Path) -> None:
        """Remove a file or directory with semaphore control."""
        async with semaphore:
            await self._remove_file_async(file)

    async def _copy_file_or_directory_async(self, source: Path, destination: Path) -> None:
        """Copy a file or directory asynchronously, handling existing destinations."""

        def copy_operation() -> None:
            """Synchronous copy operation to run in thread executor."""
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

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, copy_operation)

    async def _remove_file_async(self, file: Path) -> None:
        """Remove a file or directory asynchronously."""

        def remove_operation() -> None:
            """Synchronous remove operation to run in thread executor."""
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

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, remove_operation)

    def _matches_managed_file(self, file_name: str, manage_list: list[str]) -> bool:
        """Check if the file name matches any item in the manage list."""
        return any(item.lower() in file_name.lower() for item in manage_list)

    def _handle_permission_error(self, operation: str, list_name: str) -> None:
        """Print consistent error message for permission errors."""
        ERROR_PREFIX = "ERROR :"
        ADMIN_SUGGESTION = "    TRY RUNNING CLASSIC.EXE IN ADMIN MODE TO RESOLVE THIS PROBLEM.\n"
        msg_error(f"{ERROR_PREFIX} UNABLE TO {operation} {list_name} FILES DUE TO FILE PERMISSIONS!\n{ADMIN_SUGGESTION}")


# Global singleton instance
_game_files_manager_core: GameFilesManagerCore | None = None


def get_game_files_manager_core() -> GameFilesManagerCore:
    """Get singleton GameFilesManagerCore instance."""
    global _game_files_manager_core  # noqa: PLW0603
    if _game_files_manager_core is None:
        _game_files_manager_core = GameFilesManagerCore()
    return _game_files_manager_core


# Async-first interface
async def manage_game_files_async(classic_list: str, mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
    """
    Async interface for game files management operations.

    Args:
        classic_list: The name of the list specifying which files need to be managed.
        mode: The operation mode ("BACKUP", "RESTORE", or "REMOVE").

    Raises:
        FileNotFoundError: If the specified game folder is not found.
        PermissionError: If there are file permission issues.
    """
    core = get_game_files_manager_core()
    await core.manage_game_files_async(classic_list, mode)


# Sync adapter for backwards compatibility
def manage_game_files(classic_list: str, mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
    """
    Sync adapter for game files management operations.

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
            Defaults to "BACKUP".

    Raises:
        FileNotFoundError: If the specified game folder is not found or is not a
            valid directory.
        PermissionError: If there are file permission issues preventing the operation
            from completing.
    """
    bridge = AsyncBridge.get_instance()
    bridge.run_async(manage_game_files_async(classic_list, mode))
