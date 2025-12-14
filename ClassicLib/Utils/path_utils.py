"""Path validation and manipulation utilities."""

import platform
import stat
import sys
from pathlib import Path


def _is_valid_executable_path(path: Path | None) -> bool:
    """Check if the provided path points to a valid executable file.

    This function validates whether the given path exists, is a file, and has a
    recognized executable file extension (".exe", ".app", or no extension).

    Args:
        path: The path to validate as a potential executable.

    Returns:
        True if the path is a valid executable, otherwise False.

    """
    return path is not None and path.exists() and path.is_file() and path.suffix.lower() in {".exe", ".app", ""}


def _check_drive_exists(path_obj: Path) -> tuple[bool, str]:
    """Check if the drive exists (Windows only).

    Args:
        path_obj: The path object to check.

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty string.

    """
    if sys.platform == "win32" or platform.system() == "Windows":
        drive = path_obj.drive
        if drive and not Path(drive + "/").exists():
            return False, f"Drive {drive} does not exist"
    return True, ""


def _check_read_permissions(path_obj: Path) -> tuple[bool, str]:
    """Check read permissions for a path.

    Args:
        path_obj: The path object to check.

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty string.

    """
    try:
        # For directories, check if we can list contents
        if path_obj.is_dir():
            list(path_obj.iterdir())
        # For files, check if we can open for reading
        else:
            with path_obj.open("rb"):
                pass  # Just checking file is readable
    except PermissionError:
        return False, f"No read permission for: {path_obj}"
    except OSError as e:
        return False, f"Cannot access {path_obj}: {e}"
    return True, ""


def _check_write_permissions(path_obj: Path) -> tuple[bool, str]:
    """Check write permissions for a path.

    Args:
        path_obj: The path object to check.

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty string.

    """
    try:
        # For directories, check if we can create a temp file
        if path_obj.is_dir():
            test_file = path_obj / ".classic_test_write"
            test_file.touch()
            test_file.unlink()
        # For files, check if parent directory is writable
        else:
            parent = path_obj.parent
            test_file = parent / ".classic_test_write"
            test_file.touch()
            test_file.unlink()
    except PermissionError:
        return False, f"No write permission for: {path_obj}"
    except OSError as e:
        return False, f"Cannot write to {path_obj}: {e}"
    return True, ""


def validate_path(path: Path | str, check_write: bool = False, check_read: bool = True) -> tuple[bool, str]:
    """Validate that a path exists and is accessible with appropriate permissions.

    Args:
        path: Path to validate
        check_write: Whether to check write permissions
        check_read: Whether to check read permissions

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty string.

    """
    try:
        # Reject empty or whitespace-only paths
        path_str = str(path).strip() if path else ""
        if not path_str:
            return False, "Path is empty"

        path_obj = Path(path) if not isinstance(path, Path) else path

        # Check if the drive exists (Windows)
        is_valid, error_msg = _check_drive_exists(path_obj)
        if not is_valid:
            return False, error_msg

        # Check if path exists
        if not path_obj.exists():
            return False, f"Path does not exist: {path_obj}"

        # Check read permissions
        if check_read:
            is_valid, error_msg = _check_read_permissions(path_obj)
            if not is_valid:
                return False, error_msg

        # Check write permissions
        if check_write:
            is_valid, error_msg = _check_write_permissions(path_obj)
            if not is_valid:
                return False, error_msg

    except Exception as e:  # noqa: BLE001
        return False, f"Error validating path: {e}"
    else:
        return True, ""


def remove_readonly(file_path: Path) -> None:
    """Remove the read-only attribute from a file or directory at the given path. This operation is
    specific to the Windows platform and will not perform any actions on other platforms. If any
    error occurs, such as an `OSError` or `PermissionError`, a warning will be logged instead of
    raising an exception.

    Args:
        file_path (Path): The path to the file or directory for which the read-only attribute needs
            to be removed.

    Raises:
        OSError: If the file operation encounters a general operating system error.
        PermissionError: If there is a permissions issue preventing the operation.

    """
    if sys.platform == "win32":
        try:
            # Remove the read-only attribute
            file_path.chmod(file_path.stat().st_mode | stat.S_IWRITE)
        except (OSError, PermissionError) as e:
            # Log error but don't raise - this is a best-effort operation
            from ClassicLib.Logger import logger

            logger.warning(f"Could not remove read-only attribute from {file_path}: {e}")
