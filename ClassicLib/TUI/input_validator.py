"""Input validation and sanitization for TUI components."""

import os
import re
from pathlib import Path
from typing import Any, ClassVar


class InputValidator:
    """Centralized input validation and sanitization."""

    # Maximum path length for Windows
    MAX_PATH_LENGTH = 260

    # Maximum input length for general text fields
    MAX_INPUT_LENGTH = 1024

    # Pre-compiled regex patterns for performance optimization
    YAML_INJECTION_PATTERN = re.compile(r"[\r\n\x00-\x08\x0b\x0c\x0e-\x1f]")
    WINDOWS_PATH_PATTERN = re.compile(r'[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*')
    UNIX_PATH_PATTERN = re.compile(r"/(?:[^/\0]+/)*[^/\0]*")

    # Allowed base directories for path operations - initialize as empty list
    ALLOWED_BASE_DIRS: ClassVar[list[Path]] = []

    @classmethod
    def _init_allowed_dirs(cls) -> None:
        """Initialize allowed directories list."""
        if not cls.ALLOWED_BASE_DIRS:  # Check if list is empty instead of None
            cls.ALLOWED_BASE_DIRS = [
                Path.home(),
                Path.cwd(),
                Path(os.environ.get("TEMP", "/tmp")),
                Path(os.environ.get("TMP", "/tmp")),
            ]
            # Add Documents folder if on Windows
            if os.name == "nt":
                docs = Path.home() / "Documents"
                if docs.exists():
                    cls.ALLOWED_BASE_DIRS.append(docs)
                # Add common game directories
                for drive in ["C:", "D:", "E:", "F:"]:
                    for game_dir in ["Program Files", "Program Files (x86)", "Games"]:
                        game_path = Path(f"{drive}/{game_dir}")
                        if game_path.exists():
                            cls.ALLOWED_BASE_DIRS.append(game_path)

    @classmethod
    def validate_path(cls, path_str: str, must_exist: bool = True, must_be_dir: bool = True) -> tuple[bool, str, Path | None]:
        """Validate and sanitize a file system path.

        Args:
            path_str: The path string to validate
            must_exist: Whether the path must exist
            must_be_dir: Whether the path must be a directory

        Returns:
            Tuple of (is_valid, error_message, resolved_path)
        """
        cls._init_allowed_dirs()

        # Check for empty path
        if not path_str or not path_str.strip():
            return True, "", None  # Empty path is valid (optional field)

        # Check path length
        if len(path_str) > cls.MAX_PATH_LENGTH:
            return False, f"Path exceeds maximum length ({cls.MAX_PATH_LENGTH} characters)", None

        try:
            # Resolve to absolute path and handle path traversal
            path_obj = Path(path_str).resolve()

            # Check if path contains suspicious patterns
            path_str_normalized = str(path_obj)
            if ".." in path_str or "~" in path_str:
                # These are resolved by resolve(), but flag them for logging
                pass  # Path traversal attempt, but safely resolved

            # Check if path is within allowed directories
            is_allowed = False
            # Defensive check to ensure ALLOWED_BASE_DIRS is not None
            allowed_dirs = cls.ALLOWED_BASE_DIRS or []
            for allowed_dir in allowed_dirs:
                try:
                    # Check if path is relative to allowed directory
                    path_obj.relative_to(allowed_dir)
                    is_allowed = True
                    break
                except ValueError:
                    continue

            if not is_allowed:
                # Special case: Allow reading from game installation directories
                game_indicators = ["steam", "epic", "gog", "bethesda", "fallout", "skyrim"]
                if any(indicator in path_str_normalized.lower() for indicator in game_indicators):
                    is_allowed = True

            if not is_allowed:
                return False, "Path is outside allowed directories", None

            # Check existence if required
            if must_exist:
                if not path_obj.exists():
                    return False, "Path does not exist", None

                if must_be_dir and not path_obj.is_dir():
                    return False, "Path is not a directory", None
                if not must_be_dir and not path_obj.is_file():
                    return False, "Path is not a file", None

        except (ValueError, OSError, RuntimeError) as e:
            return False, f"Invalid path format: {e!s}", None
        else:
            return True, "", path_obj

    @classmethod
    def sanitize_for_yaml(cls, value: str) -> str:
        """Sanitize a string for safe YAML storage.

        Args:
            value: The string to sanitize

        Returns:
            Sanitized string safe for YAML storage
        """
        # Remove any control characters that could break YAML
        sanitized = cls.YAML_INJECTION_PATTERN.sub("", value)

        # Escape special YAML characters
        yaml_special = [":", "#", "@", "|", ">", "-", "*", "&", "!", "%", "?", "[", "]", "{", "}"]
        for char in yaml_special:
            if sanitized.startswith(char):
                sanitized = f'"{sanitized}"'
                break

        # Limit length
        if len(sanitized) > cls.MAX_INPUT_LENGTH:
            sanitized = sanitized[: cls.MAX_INPUT_LENGTH]

        return sanitized

    @classmethod
    def validate_input_length(cls, value: str, max_length: int | None = None) -> tuple[bool, str]:
        """Validate input string length.

        Args:
            value: The string to validate
            max_length: Maximum allowed length (uses MAX_INPUT_LENGTH if None)

        Returns:
            Tuple of (is_valid, error_message)
        """
        max_len = max_length or cls.MAX_INPUT_LENGTH

        if len(value) > max_len:
            return False, f"Input exceeds maximum length ({max_len} characters)"

        return True, ""

    @classmethod
    def sanitize_output_message(cls, message: str) -> str:
        """Sanitize messages before displaying to avoid information disclosure.

        Args:
            message: The message to sanitize

        Returns:
            Sanitized message
        """
        # Hide full system paths in error messages using pre-compiled patterns
        message = cls.WINDOWS_PATH_PATTERN.sub("[PATH]", message)
        message = cls.UNIX_PATH_PATTERN.sub("[PATH]", message)

        # Hide usernames
        if Path.home().name:
            message = message.replace(Path.home().name, "[USER]")

        return message

    @classmethod
    def validate_scan_folder(cls, folder_path: str) -> tuple[bool, str, Path | None]:
        """Validate a folder path specifically for scanning operations.

        Args:
            folder_path: The folder path to validate

        Returns:
            Tuple of (is_valid, error_message, resolved_path)
        """
        # First do general path validation
        is_valid, error_msg, resolved_path = cls.validate_path(folder_path, must_exist=True, must_be_dir=True)

        if not is_valid:
            return is_valid, error_msg, resolved_path

        # Additional checks for scan folders
        if resolved_path:
            # Check if folder is readable
            if not os.access(resolved_path, os.R_OK):
                return False, "Folder is not readable", None

            # Check if folder is not a system directory
            system_dirs = [
                Path("C:\\Windows"),
                Path("C:\\Program Files"),
                Path("C:\\Program Files (x86)"),
                Path("/etc"),
                Path("/usr"),
                Path("/bin"),
                Path("/sbin"),
            ]

            for sys_dir in system_dirs:
                if sys_dir.exists():
                    try:
                        resolved_path.relative_to(sys_dir)
                        # It's a subdirectory of a system directory, allow if it's a game folder
                        if not any(game in str(resolved_path).lower() for game in ["fallout", "skyrim", "bethesda", "steam"]):
                            return False, "Cannot scan system directories", None
                    except ValueError:
                        pass  # Not a subdirectory, which is fine

        return True, "", resolved_path

    @classmethod
    def validate_settings_value(cls, key: str, value: Any) -> tuple[bool, Any]:
        """Validate a value before saving to settings.

        Args:
            key: The settings key
            value: The value to validate

        Returns:
            Tuple of (is_valid, sanitized_value)
        """
        # Handle different types of settings
        if "path" in key.lower() or "folder" in key.lower():
            # It's a path setting
            if isinstance(value, str):
                is_valid, _, resolved_path = cls.validate_path(value, must_exist=False)
                if is_valid and resolved_path:
                    return True, str(resolved_path)
                if is_valid and not value:  # Empty path is OK
                    return True, ""
                return False, None

        elif isinstance(value, str):
            # Regular string setting
            sanitized = cls.sanitize_for_yaml(value)
            return True, sanitized

        elif isinstance(value, int | float | bool):
            # Numeric or boolean values are generally safe
            return True, value

        elif isinstance(value, list | dict):
            # Complex types need more validation (not implemented here)
            return False, None

        return False, None
