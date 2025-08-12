"""Backup management module for automatic game file backups."""

import shutil
from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.Util import normalize_list, open_file_with_encoding


class BackupManager:
    """Manages automatic backup of game files."""

    def __init__(self) -> None:
        """Initialize the BackupManager."""
        self._backup_config: dict[str, str | list[str] | None] = {}

    def load_backup_configuration(self) -> None:
        """
        Load backup settings from YAML configuration.

        Loads settings including:
        - List of files to backup
        - Game path
        - XSE log file path
        - Latest XSE version

        Raises:
            TypeError: If any of the settings have invalid types.
        """
        from ClassicLib.YamlSettingsCache import yaml_settings

        game_vr: str = GlobalRegistry.get_vr()

        backup_list: list[str] | None = yaml_settings(list[str], YAML.Main, "CLASSIC_AutoBackup")
        game_path: str | None = yaml_settings(str, YAML.Game_Local, f"Game{game_vr}_Info.Root_Folder_Game")
        xse_log_file: str | None = yaml_settings(str, YAML.Game_Local, f"Game{game_vr}_Info.Docs_File_XSE")
        xse_ver_latest: str | None = yaml_settings(str, YAML.Game, f"Game{game_vr}_Info.XSE_Ver_Latest")

        # Validate types
        if not isinstance(backup_list, list):
            raise TypeError("Backup list must be a list of strings")
        if not isinstance(xse_log_file, str):
            raise TypeError("XSE log file path must be a string")
        if not isinstance(xse_ver_latest, str):
            raise TypeError("Latest XSE version must be a string")

        self._backup_config = {
            "backup_list": backup_list,
            "game_path": game_path,
            "xse_log_file": xse_log_file,
            "xse_ver_latest": xse_ver_latest,
        }

        logger.debug("Loaded backup configuration")

    def extract_xse_version(self, log_file: str) -> str | None:
        """
        Extract XSE version from log file.

        Args:
            log_file: Path to the XSE log file

        Returns:
            The extracted XSE version or None if no log data is available
        """
        xse_data_lower: list[str] = []
        try:
            with open_file_with_encoding(log_file) as xse_log:
                xse_data: list[str] = xse_log.readlines()
                xse_data_lower = normalize_list(xse_data)
        except FileNotFoundError:
            logger.debug(f"XSE log file not found: {log_file}")

        if not xse_data_lower:
            return None

        # Use default version from config if available
        version: str = self._backup_config.get("xse_ver_latest", "unknown")  # type: ignore

        try:
            line_with_version: str = next(line for line in xse_data_lower if "version = " in line)
            split_line: list[str] = line_with_version.split(" ")

            for index, item in enumerate(split_line):
                if "version" in item:
                    version = split_line[index + 2]
                    break
        except (StopIteration, IndexError):
            # If we can't extract version from log, use the default
            logger.debug(f"Could not extract version from log, using default: {version}")

        return version

    def create_backup_directory(self, version: str) -> Path:
        """
        Create versioned backup directory.

        Args:
            version: Version string to use in directory name

        Returns:
            Path object for the created backup directory
        """
        backup_path = Path(f"CLASSIC Backup/Game Files/{version}")
        backup_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created backup directory: {backup_path}")
        return backup_path

    def backup_files(self, source_dir: str, backup_list: list[str], version: str) -> None:
        """
        Backup specified files to versioned directory.

        Args:
            source_dir: Source directory containing files to backup
            backup_list: List of file patterns to backup
            version: Version string for backup directory
        """
        # Create backup directory
        backup_path = self.create_backup_directory(version)

        # Validate source directory
        from ClassicLib.Util import validate_path

        is_valid, error_msg = validate_path(source_dir, check_write=False, check_read=True)
        if not is_valid:
            logger.warning(f"Cannot backup files - {error_msg}")
            return

        # Get lists of game files and existing backup files
        game_files: list[Path] = list(Path(source_dir).glob("*.*"))
        backup_files: list[str] = [file.name for file in backup_path.glob("*.*")]

        # Back up files that don't already exist in backup
        backed_up_count = 0
        for file in game_files:
            if file.name not in backup_files and any(file.name in item for item in backup_list):
                destination_file: Path = backup_path / file.name
                shutil.copy2(file, destination_file)
                backed_up_count += 1
                logger.debug(f"Backed up: {file.name}")

        if backed_up_count > 0:
            logger.info(f"Backed up {backed_up_count} files to {backup_path}")

    def run_backup(self) -> None:
        """
        Execute complete backup process.

        This method:
        1. Loads backup configuration if not already loaded
        2. Extracts XSE version from log file
        3. Creates versioned backup directory
        4. Copies specified files from game directory to backup

        Files are only backed up if:
        - They match patterns in the backup list
        - They don't already exist in the backup directory
        """
        # Ensure configuration is loaded
        if not self._backup_config:
            self.load_backup_configuration()

        # Get XSE version from log file
        xse_log_file = self._backup_config.get("xse_log_file")
        if not xse_log_file or not isinstance(xse_log_file, str):
            logger.warning("No XSE log file configured, skipping backup")
            return

        xse_version = self.extract_xse_version(xse_log_file)
        if not xse_version:
            logger.debug("No XSE version found, skipping backup")
            return

        # Perform backup
        game_path = self._backup_config.get("game_path")
        backup_list = self._backup_config.get("backup_list")

        if game_path and isinstance(game_path, str) and backup_list and isinstance(backup_list, list):
            self.backup_files(game_path, backup_list, xse_version)
        else:
            logger.warning("Missing game path or backup list configuration")
