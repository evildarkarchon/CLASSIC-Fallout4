"""Backup Service for CLASSIC TUI.

Manages backup operations via existing backend functions.
"""

from pathlib import Path

from ClassicLib.scanning.game.game_files_manager import manage_game_files_async

# Mapping of user-friendly names to internal backup list names
BACKUP_TYPE_MAP: dict[str, str] = {
    "XSE": "Backup XSE",
    "RESHADE": "Backup ReShade",
    "VULKAN": "Backup Vulkan",
    "ENB": "Backup ENB",
}


class BackupInfo:
    """Information about a backup status."""

    def __init__(self, backup_type: str, exists: bool, file_count: int, path: Path | None) -> None:
        """Initialize BackupInfo.

        Args:
            backup_type: The type of backup (XSE, RESHADE, VULKAN, ENB).
            exists: Whether the backup exists.
            file_count: Number of files in the backup.
            path: Path to the backup directory.

        """
        self.backup_type = backup_type
        self.exists = exists
        self.file_count = file_count
        self.path = path


class BackupService:
    """Service for backup/restore operations.

    Wraps existing backup functionality from ClassicLib.scanning.game
    for use with the TUI.
    """

    @staticmethod
    async def backup(backup_type: str) -> bool:
        """Create a backup for the specified type.

        Args:
            backup_type: One of "XSE", "RESHADE", "VULKAN", "ENB".

        Returns:
            True if backup succeeded, False otherwise.

        """
        list_name = BACKUP_TYPE_MAP.get(backup_type.upper())
        if not list_name:
            return False

        try:
            await manage_game_files_async(list_name, "BACKUP")
        except (OSError, PermissionError, FileNotFoundError):
            return False
        else:
            return True

    @staticmethod
    async def restore(backup_type: str) -> bool:
        """Restore from a backup for the specified type.

        Args:
            backup_type: One of "XSE", "RESHADE", "VULKAN", "ENB".

        Returns:
            True if restore succeeded, False otherwise.

        """
        list_name = BACKUP_TYPE_MAP.get(backup_type.upper())
        if not list_name:
            return False

        try:
            await manage_game_files_async(list_name, "RESTORE")
        except (OSError, PermissionError, FileNotFoundError):
            return False
        else:
            return True

    @staticmethod
    async def remove(backup_type: str) -> bool:
        """Remove a backup for the specified type.

        Args:
            backup_type: One of "XSE", "RESHADE", "VULKAN", "ENB".

        Returns:
            True if removal succeeded, False otherwise.

        """
        list_name = BACKUP_TYPE_MAP.get(backup_type.upper())
        if not list_name:
            return False

        try:
            await manage_game_files_async(list_name, "REMOVE")
        except (OSError, PermissionError, FileNotFoundError):
            return False
        else:
            return True

    @staticmethod
    def check_status(backup_type: str) -> BackupInfo:
        """Check the status of a backup synchronously.

        Args:
            backup_type: One of "XSE", "RESHADE", "VULKAN", "ENB".

        Returns:
            BackupInfo with backup status details.

        """
        from ClassicLib.core.registry import GlobalRegistry

        list_name = BACKUP_TYPE_MAP.get(backup_type.upper())
        if not list_name:
            return BackupInfo(backup_type, exists=False, file_count=0, path=None)

        local_dir = Path(GlobalRegistry.get_local_dir())
        backup_dir = local_dir / "CLASSIC Backup" / "Game Files" / list_name

        if backup_dir.exists():
            files = list(backup_dir.iterdir())
            return BackupInfo(
                backup_type=backup_type,
                exists=len(files) > 0,
                file_count=len(files),
                path=backup_dir,
            )

        return BackupInfo(backup_type, exists=False, file_count=0, path=None)
