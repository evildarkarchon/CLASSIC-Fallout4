"""File generation module for CLASSIC configuration files."""

from pathlib import Path

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger


class FileGenerator:
    """Manages generation of CLASSIC configuration files."""

    @staticmethod
    def generate_ignore_file() -> None:
        """
        Generate CLASSIC Ignore.yaml if it doesn't exist.

        Creates the ignore file with default content from YAML settings.
        The file content is written in UTF-8 encoding.

        Raises:
            TypeError: If the default content retrieved for the ignore file
                is not of type str.
        """
        from ClassicLib.YamlSettingsCache import yaml_settings

        ignore_path = Path("CLASSIC Ignore.yaml")
        if not ignore_path.exists():
            default_ignorefile = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_ignorefile")
            if not isinstance(default_ignorefile, str):
                raise TypeError("Default ignore file content must be a string")
            ignore_path.write_text(default_ignorefile, encoding="utf-8")
            logger.debug(f"Generated CLASSIC Ignore.yaml at {ignore_path}")

    @staticmethod
    def generate_local_yaml() -> None:
        """
        Generate CLASSIC Data/CLASSIC <GAME> Local.yaml if it doesn't exist.

        Creates the local YAML file with default content from YAML settings,
        where <GAME> is dynamically determined from GlobalRegistry.
        The file content is written in UTF-8 encoding.

        Raises:
            TypeError: If the default content retrieved for the local YAML file
                is not of type str.
        """
        from ClassicLib.YamlSettingsCache import yaml_settings

        local_path = Path(f"CLASSIC Data/CLASSIC {GlobalRegistry.get_game()} Local.yaml")
        if not local_path.exists():
            default_yaml = yaml_settings(str, YAML.Main, "CLASSIC_Info.default_localyaml")
            if not isinstance(default_yaml, str):
                raise TypeError("Default local YAML content must be a string")
            # Create parent directory if it doesn't exist
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(default_yaml, encoding="utf-8")
            logger.debug(f"Generated local YAML at {local_path}")

    @staticmethod
    def generate_all_files() -> None:
        """
        Generate all required CLASSIC configuration files.

        This method generates:
        - CLASSIC Ignore.yaml: Contains ignore patterns for file scanning
        - CLASSIC Data/CLASSIC <GAME> Local.yaml: Contains game-specific local settings

        The method ensures all necessary configuration files exist before
        the application starts processing.
        """
        FileGenerator.generate_ignore_file()
        FileGenerator.generate_local_yaml()
