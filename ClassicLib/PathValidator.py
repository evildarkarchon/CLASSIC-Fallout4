"""Path validation module for settings and configuration paths."""

from pathlib import Path

from ClassicLib import msg_warning
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger


class PathValidator:
    """Validates and maintains path settings."""

    @staticmethod
    def is_valid_path(path: str | Path) -> bool:
        """
        Check if a path exists and is accessible.

        Args:
            path: Path to validate (string or Path object)

        Returns:
            True if the path exists and is accessible, False otherwise.
        """
        # Handle None and empty strings
        if path is None or (isinstance(path, str) and not path.strip()):
            return False

        try:
            path_obj = Path(path) if isinstance(path, str) else path
            return path_obj.exists()
        except (OSError, ValueError):
            return False

    @staticmethod
    def is_restricted_path(path: str | Path) -> bool:
        """
        Check if path is in a restricted directory.

        Restricted directories are hard-coded paths that should not be
        used for custom scanning or other user-configurable paths.

        Args:
            path: Path to check (string or Path object)

        Returns:
            True if the path is restricted, False otherwise.
        """
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        try:
            path_str = str(path)
            # Use the existing utility function to check if path is valid
            # (returns False for restricted paths)
            return not is_valid_custom_scan_path(path_str)
        except Exception:
            # If there's any error checking, consider it restricted
            return True

    @staticmethod
    def validate_custom_scan_path() -> None:
        """
        Validate and clean custom scan path setting.

        This method checks the custom scan path stored in settings and
        removes it if:
        - The path doesn't exist on the filesystem
        - The path is empty or None
        - The path is in a restricted directory

        The custom scan path is used for scanning crash logs from
        user-specified directories.
        """
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path
        from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

        # Get the custom scan path from settings
        custom_scan_path: str | None = classic_settings(str, "SCAN Custom Path")

        if custom_scan_path:
            # Check if the path exists
            path_obj = Path(custom_scan_path)

            if not path_obj.exists() or not path_obj.is_dir():
                logger.debug(f"Invalid custom scan path found in settings: {custom_scan_path}")
                # Clear the invalid path from settings
                yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")
                msg_warning(f"Removed invalid custom scan path: {custom_scan_path}")

            elif not is_valid_custom_scan_path(custom_scan_path):
                logger.debug(f"Restricted custom scan path found in settings: {custom_scan_path}")
                # Clear the restricted path from settings
                yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")
                msg_warning(f"Removed restricted custom scan path: {custom_scan_path}")

    @staticmethod
    def validate_all_settings_paths() -> None:
        """
        Validate all paths stored in settings.

        This method performs validation on all path-related settings,
        removing any that are invalid, non-existent, or restricted.

        Currently validates:
        - Custom scan path for crash log directories

        Future implementations may include:
        - Game installation paths
        - Mod directory paths
        - Backup directory paths
        """
        logger.debug("Validating all settings paths")

        # Validate custom scan path
        PathValidator.validate_custom_scan_path()

        # TODO: Add validation for other path settings as needed
        # For example:
        # - Game root folder paths
        # - Documents folder paths
        # - Mod organizer paths

        logger.debug("Path validation complete")
