"""Path validation module for settings and configuration paths."""

from pathlib import Path

from ClassicLib import GlobalRegistry, msg_warning
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
    def _validate_path_setting(
        path: str | Path | None,
        setting_name: str,
        yaml_type: YAML,
        setting_key: str,
        required_files: list[str] | None = None,
        path_description: str = "path",
    ) -> bool:
        """
        Helper method to validate a path setting and clear it if invalid.

        Args:
            path: The path to validate
            setting_name: Human-readable name for logging
            yaml_type: YAML settings type (e.g., YAML.Settings, YAML.Game_Local)
            setting_key: Full settings key to update if invalid
            required_files: Optional list of filenames that must exist in the path
            path_description: Description of the path type for error messages

        Returns:
            True if the path is valid, False otherwise.
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
                missing_files = []
                for filename in required_files:
                    if not (path_obj / filename).exists():
                        missing_files.append(filename)

                if missing_files:
                    logger.debug(f"Invalid {path_description} - missing required files: {', '.join(missing_files)}")
                    yaml_settings(str, yaml_type, setting_key, "")
                    msg_warning(f"Removed invalid {setting_name} (missing required files): {path}")
                    return False

            return True

        except (OSError, ValueError) as e:
            logger.debug(f"Error validating {path_description}: {e}")
            yaml_settings(str, yaml_type, setting_key, "")
            msg_warning(f"Removed invalid {setting_name}: {path}")
            return False

    @staticmethod
    def validate_game_root_path() -> None:
        """
        Validate the game root folder path.

        This checks that the game installation directory exists and contains
        the expected game executable file.
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
        Validate the documents folder path.

        This checks that the My Games documents folder exists and is accessible.
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
        Validate the mods folder path.

        This checks that the mod manager staging directory exists and is accessible.
        Used for mod managers like MO2 (Mod Organizer 2) and Vortex.
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
        Validate the INI folder path.

        This checks that the custom INI folder exists and is accessible.
        Used primarily for MO2 profile-specific INI files.
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
        Validate all paths stored in settings.

        This method performs validation on all path-related settings,
        removing any that are invalid, non-existent, or restricted.

        Validates:
        - Custom scan path for crash log directories
        - Game root folder path
        - Documents folder path
        - Mods folder path (MO2/Vortex)
        - INI folder path (MO2 profiles)
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
