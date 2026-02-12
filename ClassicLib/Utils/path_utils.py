"""Path validation and manipulation utilities."""

import stat
import sys
from pathlib import Path

from classic_path import PathValidator


def validate_path(path: Path | str, check_write: bool = False, check_read: bool = True) -> tuple[bool, str]:
    """Validate that a path exists and is accessible with appropriate permissions.

    Delegates to Rust PathValidator via classic_path.

    Args:
        path: Path to validate
        check_write: Whether to check write permissions
        check_read: Whether to check read permissions

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty string.

    """
    try:
        PathValidator.validate_path_with_permissions(str(path), check_read, check_write)
    except Exception as e:  # noqa: BLE001
        return False, str(e)
    else:
        return True, ""


def remove_readonly(file_path: Path) -> None:
    """Remove the read-only attribute from a file or directory.

    Delegates to Rust PathValidator via classic_path.
    This operation is specific to Windows and is a no-op on other platforms.

    Args:
        file_path (Path): The path to the file or directory for which the read-only attribute needs
            to be removed.

    """
    if sys.platform != "win32":
        return

    try:
        PathValidator.remove_readonly_attribute(str(file_path))
    except Exception:  # noqa: BLE001
        # Fallback to Python for edge cases where Rust binding fails at runtime
        try:
            file_path.chmod(file_path.stat().st_mode | stat.S_IWRITE)
        except (OSError, PermissionError) as e:
            from ClassicLib.core.logger import logger

            logger.warning(f"Could not remove read-only attribute from {file_path}: {e}")
