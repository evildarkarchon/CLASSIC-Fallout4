"""
A module for validating and maintaining file path configurations.

This module provides utilities for ensuring configurable paths, such as custom
scan directories or game root folders, are valid and accessible. It also includes
methods to clean up invalid or restricted path settings from application
configuration.

Methods in this module perform checks to ensure paths exist, are directories,
contain expected files if necessary, and are not restricted by predefined rules.
Users of this module can integrate these methods to maintain the validity and
consistency of configuration paths.

**Performance**: Basic path validation methods automatically use Rust acceleration
when available, providing 10-50x performance improvements.
"""

from pathlib import Path

from ClassicLib import GlobalRegistry, msg_warning
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger

# Import factory for Rust acceleration
from ClassicLib.integration.factory import get_path_operations

# Get Rust module if available, None otherwise
classic_path = get_path_operations()
_HAS_RUST_PATH = classic_path is not None


class PathValidator:
    """
    Provides static methods for validating and managing file system paths.

    This class provides utility methods to validate paths for existence, their appropriateness
    for specific purposes such as being part of restricted directories, and for cleaning
    invalid paths from configuration settings. Additionally, helper methods allow
    comprehensive path validations, including for specific required files.

    The class is particularly useful for applications managing custom configurations
    and paths related to file system operations or integrations with game files.
    """

    @staticmethod
    def is_valid_path(path: str | Path) -> bool:
        """
        Checks if the supplied path is valid and exists in the file system.

        This method determines the validity of a given path by verifying its type,
        checking if it is not empty or None, and confirming whether the path exists
        in the operating system's file system. If the path is invalid or does not exist,
        the method will return False.

        **Performance**: Uses Rust acceleration when available for 10-50x speedup.

        Args:
            path (str | Path): The file system path to check. May either be a string
                or a Path object.

        Returns:
            bool: True if the path is valid and exists in the file system, False otherwise.
        """
        # Handle None and empty strings
        if path is None or (isinstance(path, str) and not path.strip()):
            return False

        # Use Rust acceleration when available
        if _HAS_RUST_PATH and classic_path is not None:
            try:
                return classic_path.PathValidator.is_valid_path(str(path))  # pyright: ignore[reportOptionalMemberAccess]
            except (ValueError, OSError, RuntimeError):
                # Fall through to Python implementation on error
                pass

        # Pure Python implementation
        try:
            path_obj = Path(path) if isinstance(path, str) else path
            return path_obj.exists()
        except (OSError, ValueError):
            return False

    @staticmethod
    def is_restricted_path(path: str | Path) -> bool:
        """
        Checks whether the provided path is a restricted path.

        This method verifies if a given path is restricted or valid by utilizing an
        existing utility function. If any exception occurs during the validation
        process, it will consider the path as restricted.

        **Performance**: Uses Rust acceleration when available for 10-50x speedup.

        Args:
            path (str | Path): The path to be checked for restriction.

        Returns:
            bool: True if the path is restricted, False otherwise.
        """
        # Use Rust acceleration when available
        if _HAS_RUST_PATH and classic_path is not None:
            try:
                return classic_path.PathValidator.is_restricted_path(str(path))  # pyright: ignore[reportOptionalMemberAccess]
            except (ValueError, OSError, RuntimeError):
                # Fall through to Python implementation on error
                pass

        # Pure Python implementation
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        try:
            path_str = str(path)
            # Use the existing utility function to check if path is valid
            # (returns False for restricted paths)
            return not is_valid_custom_scan_path(path_str)
        except (ValueError, OSError, TypeError):
            # If there's any error checking, consider it restricted
            return True

    @staticmethod
    def validate_custom_scan_path() -> None:
        """
        Validates the custom scan path defined in the application settings.

        This method checks whether the custom scan path specified in the application
        settings is valid or not. A path is considered invalid if it does not exist,
        is not a directory, or is restricted based on implementation-specific rules.
        If an invalid or restricted path is found, the method removes the path from
        settings and logs a warning message.

        Raises:
            None: No exceptions are raised by this method. It handles all invalid
            path scenarios internally.
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
    def _validate_path_setting(
        path: str | Path | None,
        setting_name: str,
        yaml_type: YAML,
        setting_key: str,
        required_files: list[str] | None = None,
        path_description: str = "path",
    ) -> bool:
        """
        Validates the 'path' setting based on provided parameters.

        This static method ensures the specified 'path' meets certain validation
        criteria, such as existence, being a directory, and containing required files
        (if applicable). If 'path' is invalid, associated behaviors are handled,
        including logging, updating YAML settings, and warning messaging.

        Args:
            path (str | Path | None): The path to validate. Can be None, a string,
                or a Path instance.
            setting_name (str): The name of the setting to use in warning messages.
            yaml_type (YAML): YAML object type used for updating settings.
            setting_key (str): The key in YAML settings to be updated if the path
                is invalid.
            required_files (list[str] | None): A list of required filenames within
                the path. If provided, their presence is verified.
            path_description (str): A descriptor for the type of path being validated.
                Defaults to "path."

        Returns:
            bool: Returns True if the path is valid and meets all criteria. Otherwise,
                returns False.
        """
        from ClassicLib.YamlSettingsCache import yaml_settings

        # Handle None and empty strings
        if path is None or (isinstance(path, str) and not path.strip()):
            return False

        try:
            path_obj = Path(path) if isinstance(path, str) else path

            # Check if path exists and is a directory
            if not path_obj.exists():
                logger.debug(f"Invalid {path_description} - path does not exist: {path}")
                yaml_settings(str, yaml_type, setting_key, "")
                msg_warning(f"Removed invalid {setting_name}: {path}")
                return False

            if not path_obj.is_dir():
                logger.debug(f"Invalid {path_description} - not a directory: {path}")
                yaml_settings(str, yaml_type, setting_key, "")
                msg_warning(f"Removed invalid {setting_name} (not a directory): {path}")
                return False

            # Check for required files if specified
            if required_files:
                missing_files = [filename for filename in required_files if not (path_obj / filename).exists()]

                if missing_files:
                    logger.debug(f"Invalid {path_description} - missing required files: {', '.join(missing_files)}")
                    yaml_settings(str, yaml_type, setting_key, "")
                    msg_warning(f"Removed invalid {setting_name} (missing required files): {path}")
                    return False

        except (OSError, ValueError) as e:
            logger.debug(f"Error validating {path_description}: {e}")
            yaml_settings(str, yaml_type, setting_key, "")
            msg_warning(f"Removed invalid {setting_name}: {path}")
            return False
        else:
            return True

    @staticmethod
    def validate_game_root_path() -> None:
        """
        Validates the game root path settings and ensures the required files exist.

        This method retrieves the game root path from the settings, determines the
        expected executable file based on the game's name, and validates that the
        path is correctly configured in the settings. If the path exists, it also
        checks whether the required executable file is present.

        Raises:
            ValueError: If the specified path does not exist or is invalid.
            FileNotFoundError: If the required game executable is missing.

        """
        from ClassicLib.YamlSettingsCache import yaml_settings

        vr_suffix = GlobalRegistry.get_vr()
        game_name = GlobalRegistry.get_game()

        # Get the game root path from settings
        game_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{vr_suffix}_Info.Root_Folder_Game")

        if game_path:
            # Determine expected executable based on game
            game_exe = f"{game_name}.exe"

            PathValidator._validate_path_setting(
                path=game_path,
                setting_name="game root folder",
                yaml_type=YAML.Game_Local,
                setting_key=f"Game{vr_suffix}_Info.Root_Folder_Game",
                required_files=[game_exe],
                path_description="game root folder",
            )

    @staticmethod
    def validate_documents_path() -> None:
        """
        Validates the documents path specified in the YAML settings cache. Ensures the existence
        and proper directory structure of the documents folder for the application. This method
        checks the validity of the path configuration and ensures compliance without enforcing
        specific files within the directory.

        Raises:
            ValidationError: If the documents path is invalid or does not meet the specified
                requirements.
        """
        from ClassicLib.YamlSettingsCache import yaml_settings

        vr_suffix = GlobalRegistry.get_vr()

        # Get the documents path from settings
        docs_path: Path | None = yaml_settings(Path, YAML.Game_Local, f"Game{vr_suffix}_Info.Root_Folder_Docs")

        if docs_path:
            # Documents folder just needs to exist and be a directory
            # INI files may not exist yet if game hasn't been run
            PathValidator._validate_path_setting(
                path=docs_path,
                setting_name="documents folder",
                yaml_type=YAML.Game_Local,
                setting_key=f"Game{vr_suffix}_Info.Root_Folder_Docs",
                required_files=None,  # Don't require specific files
                path_description="documents folder",
            )

    @staticmethod
    def validate_mods_folder_path() -> None:
        """
        Validates the path of the mods folder based on application settings.

        Retrieves the path for the mods folder from configuration settings and checks
        its validity. If the path is specified, performs additional validation using
        internal utilities, including checks against provided settings and descriptions.
        The mods folder can be empty, so no required files are enforced during validation.
        """
        from ClassicLib.YamlSettingsCache import classic_settings

        # Get the mods folder path from settings
        mods_path: str | None = classic_settings(str, "MODS Folder Path")

        if mods_path:
            PathValidator._validate_path_setting(
                path=mods_path,
                setting_name="mods folder",
                yaml_type=YAML.Settings,
                setting_key="CLASSIC_Settings.MODS Folder Path",
                required_files=None,  # Mod folder might be empty
                path_description="mods staging folder",
            )

    @staticmethod
    def validate_ini_folder_path() -> None:
        """
        Validates the INI folder path retrieved from the application settings.

        This static method fetches the INI folder path from application settings and verifies
        if the given path adheres to expected criteria. The validation includes checking the
        existence and validity of the path. The folder may not yet contain INI files, so the
        validation skips checking for required files.

        Raises:
            ValueError: If the path is invalid or does not meet the expected criteria.
        """
        from ClassicLib.YamlSettingsCache import classic_settings

        # Get the INI folder path from settings
        ini_path: str | None = classic_settings(str, "INI Folder Path")

        if ini_path:
            PathValidator._validate_path_setting(
                path=ini_path,
                setting_name="INI folder",
                yaml_type=YAML.Settings,
                setting_key="CLASSIC_Settings.INI Folder Path",
                required_files=None,  # INI files might not exist yet
                path_description="INI folder",
            )

    @staticmethod
    def validate_all_settings_paths() -> None:
        """
        Validates all necessary settings paths to ensure proper application configuration.

        This static method performs a comprehensive validation of various critical paths
        required for the application to function correctly. These validations include paths
        for custom scans, game installation, documents, mod manager folders, and INI folders.
        If any path is invalid or misconfigured, this ensures those issues are identified at
        an early stage.
        """
        logger.debug("Validating all settings paths")

        # Validate custom scan path
        PathValidator.validate_custom_scan_path()

        # Validate game installation path
        PathValidator.validate_game_root_path()

        # Validate documents folder path
        PathValidator.validate_documents_path()

        # Validate mod manager paths
        PathValidator.validate_mods_folder_path()

        # Validate INI folder path
        PathValidator.validate_ini_folder_path()

        logger.debug("Path validation complete")
