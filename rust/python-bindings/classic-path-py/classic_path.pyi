"""Type stubs for classic_path module.

This module provides Python bindings for CLASSIC path management operations
implemented in Rust for optimal performance.
"""

__version__: str

class GamePathFinder:
    """Python wrapper for game path detection.

    Provides multi-strategy game path detection using registry queries,
    XSE log parsing, and cached paths.
    """

    def __init__(self, game_exe: str, xse_loader: str | None, game_name: str, is_vr: bool) -> None:
        """Create a new GamePathFinder.

        Args:
            game_exe: The game executable name (e.g., "Fallout4.exe")
            xse_loader: Optional XSE loader name (e.g., "f4se_loader.exe")
            game_name: Game name for registry queries (e.g., "Fallout4")
            is_vr: Whether this is a VR version

        """

    def find_game_path(self, cached_path: str | None, xse_log_path: str | None) -> str:
        """Find the game installation path using multiple strategies.

        Args:
            cached_path: Optional cached path from settings
            xse_log_path: Optional path to XSE log file

        Returns:
            The validated game installation path as a string.

        Raises:
            FileNotFoundError: If game not found by any method
            ValueError: If path validation fails

        """

    def validate_game_path(self, path: str) -> None:
        """Validate that a path is a valid game installation directory.

        Args:
            path: The path to validate

        Raises:
            ValueError: If validation fails
            FileNotFoundError: If path or required files don't exist

        """

    @property
    def game_exe(self) -> str:
        """Get the name of the game executable."""

    @property
    def xse_loader(self) -> str | None:
        """Get the name of the XSE loader executable."""

    @property
    def is_vr(self) -> bool:
        """Check if this is a VR version of the game."""

    @staticmethod
    def parse_xse_log(log_path: str) -> str:
        """Parse XSE log file to extract game installation path.

        Args:
            log_path: Path to the XSE log file

        Returns:
            The game installation path extracted from the log.

        Raises:
            FileNotFoundError: If log file doesn't exist
            ValueError: If log doesn't contain plugin directory line

        """

class PathValidator:
    """Python wrapper for path validation utilities."""

    @staticmethod
    def is_valid_path(path: str) -> bool:
        """Check if a path exists in the filesystem.

        Args:
            path: The path to check

        Returns:
            True if the path exists, False otherwise.

        """

    @staticmethod
    def is_restricted_path(path: str) -> bool:
        """Check if a path is restricted for custom scans.

        Args:
            path: The path to check

        Returns:
            True if the path is restricted, False if safe.

        """

    @staticmethod
    def validate_custom_scan_path(path: str) -> None:
        """Validate a custom scan path.

        Args:
            path: The path to validate

        Raises:
            ValueError: If the path is invalid or restricted
            FileNotFoundError: If the path does not exist

        """

    @staticmethod
    def validate_required_files(directory: str, required_files: list[str]) -> None:
        """Validate that required files exist in a directory.

        Args:
            directory: The directory to check
            required_files: List of file names that must exist

        Raises:
            FileNotFoundError: If directory or any file does not exist
            ValueError: If the path is not a directory

        """

    @staticmethod
    def validate_settings_path(path: str, setting_name: str, required_files: list[str] | None) -> None:
        """Validate a settings path with optional required files.

        Args:
            path: The path to validate
            setting_name: Name of the setting (for error messages)
            required_files: Optional list of required file names

        Raises:
            ValueError: If validation fails

        """

    @staticmethod
    def validate_settings_paths(game_path: str, docs_path: str, custom_scan_path: str | None, game_exe: str) -> None:
        """Validate all common settings paths.

        Args:
            game_path: Game installation path
            docs_path: Documents folder path
            custom_scan_path: Optional custom scan path
            game_exe: Game executable name

        Raises:
            ValueError: If any validation fails

        """

    @staticmethod
    def is_valid_executable_path(path: str) -> bool:
        """Check if a path points to a valid executable file.

        Args:
            path: The path to check

        Returns:
            True if the path is a valid executable, False otherwise.

        """

    @staticmethod
    def check_drive_exists(path: str) -> None:
        """Check if the drive exists (Windows only).

        Args:
            path: The path to check

        Raises:
            ValueError: If the drive does not exist (Windows only)

        """

    @staticmethod
    def check_read_permissions(path: str) -> None:
        """Check read permissions for a path.

        Args:
            path: The path to check

        Raises:
            PermissionError: If read access is denied
            OSError: If the path cannot be accessed

        """

    @staticmethod
    def check_write_permissions(path: str) -> None:
        """Check write permissions for a path.

        Args:
            path: The path to check

        Raises:
            PermissionError: If write access is denied
            OSError: If the path cannot be accessed

        """

    @staticmethod
    def validate_path_with_permissions(path: str, check_read: bool = True, check_write: bool = False) -> None:
        """Validate a path with comprehensive permission checks.

        Args:
            path: The path to validate
            check_read: Whether to check read permissions
            check_write: Whether to check write permissions

        Raises:
            FileNotFoundError: If path does not exist
            PermissionError: If permission checks fail
            ValueError: If drive check fails (Windows)
            OSError: If other access errors occur

        """

class DocsPathFinder:
    """Python wrapper for documents path detection."""

    def __init__(self, relative_path: str) -> None:
        """Create a new DocsPathFinder.

        Args:
            relative_path: Path relative to documents folder

        """

    def find_docs_path(self, cached_path: str | None) -> str:
        """Find the documents folder path using multiple strategies.

        Args:
            cached_path: Optional cached path from settings

        Returns:
            The validated documents folder path as a string.

        Raises:
            FileNotFoundError: If documents folder not found
            ValueError: If path validation fails

        """

    def validate_docs_path(self, path: str) -> None:
        """Validate that a documents path exists and is a directory.

        Args:
            path: The path to validate

        Raises:
            ValueError: If validation fails
            FileNotFoundError: If path doesn't exist

        """

    def validate_ini_files(self, docs_path: str, required_inis: list[str]) -> None:
        """Validate that required INI files exist in the documents path.

        Args:
            docs_path: The documents folder path
            required_inis: List of INI file names that must exist

        Raises:
            FileNotFoundError: If any required INI file is missing
            ValueError: If INI file cannot be parsed

        """

    @property
    def relative_path(self) -> str:
        """Get the relative path within documents folder."""

class BackupManager:
    """Python wrapper for backup management."""

    def __init__(self, backup_root: str) -> None:
        """Create a new BackupManager.

        Args:
            backup_root: Root directory where backups will be stored

        """

    def extract_version_from_xse_log(self, xse_log_path: str) -> XseVersion:
        """Extract version information from an XSE log file.

        Args:
            xse_log_path: Path to the XSE log file

        Returns:
            The extracted version information.

        Raises:
            FileNotFoundError: If log file doesn't exist
            ValueError: If version string not found or invalid

        """

    def create_backup(self, source_file: str, version: XseVersion) -> str:
        """Create a backup of a file with version metadata.

        Args:
            source_file: Path to the file to back up
            version: Version information for organizing the backup

        Returns:
            Path to the created backup file.

        Raises:
            FileNotFoundError: If source file doesn't exist
            IOError: If backup directory can't be created or file copy fails

        """

    @property
    def backup_root(self) -> str:
        """Get the backup root directory."""

    def list_versions(self) -> list[str]:
        """List all version directories in the backup root.

        Returns:
            List of version directory names.

        Raises:
            IOError: If backup directory can't be read

        """

    def get_version_path(self, version: XseVersion) -> str:
        """Get the path to a specific version's backup directory.

        Args:
            version: The version to get the path for

        Returns:
            Path to the version's backup directory.

        """

class XseVersion:
    """Python wrapper for XSE version information."""

    def __init__(self, version: str) -> None:
        """Create a new XseVersion from a version string.

        Args:
            version: The full version string (e.g., "1.10.163.0")

        """

    def full_version(self) -> str:
        """Get the full version string.

        Returns:
            The complete version string (e.g., "1.10.163.0").

        """

    def sanitized(self) -> str:
        """Get a sanitized version suitable for directory names.

        Returns:
            A sanitized version string (e.g., "1_10_163_0").

        """

    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...

class IniCheckResult:
    """Python wrapper for INI check result."""

    @property
    def ini_name(self) -> str:
        """Get the INI file name."""

    @property
    def exists(self) -> bool:
        """Check if the INI file exists."""

    @property
    def is_valid(self) -> bool:
        """Check if the INI file is valid."""

    @property
    def message(self) -> str:
        """Get the validation message."""

    @property
    def issue(self) -> str | None:
        """Get the issue type if any."""

    def has_issue(self) -> bool:
        """Check if this result indicates a problem.

        Returns:
            True if there's an issue, False otherwise.

        """

    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...

class DocumentsChecker:
    """Python wrapper for documents configuration checker."""

    def __init__(self, game_name: str) -> None:
        """Create a new DocumentsChecker.

        Args:
            game_name: Name of the game (e.g., "Fallout4")

        """

    def check_onedrive_in_path(self, docs_path: str) -> str | None:
        """Check if OneDrive is detected in the documents path.

        Args:
            docs_path: The documents folder path to check

        Returns:
            Warning message if OneDrive is detected, None otherwise.

        """

    def validate_ini_file(self, docs_path: str, ini_name: str) -> IniCheckResult:
        """Validate an INI file in the documents folder.

        Args:
            docs_path: The documents folder path
            ini_name: Name of the INI file

        Returns:
            An IniCheckResult containing the validation status.

        Raises:
            IOError: If file cannot be read

        """

    def run_all_checks(self, docs_path: str) -> list[str]:
        """Run all document checks for the game.

        Args:
            docs_path: The documents folder path

        Returns:
            A list of check result messages.

        Raises:
            IOError: If documents path cannot be accessed

        """

    @property
    def game_name(self) -> str:
        """Get the game name."""

def remove_readonly(file_path: str) -> None:
    """Remove the read-only attribute from a file or directory (Windows only).

    Args:
        file_path: Path to the file or directory

    Raises:
        PermissionError: If unable to modify permissions
        OSError: If other I/O errors occur

    """
