"""Documents folder and configuration checking module."""

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.DocsPath import docs_check_ini
from ClassicLib.Logger import logger


class DocumentsChecker:
    """Validates game documents folder and configuration files."""

    def check_folder_configuration(self) -> str:
        """
        Check for OneDrive and other problematic folder configurations.

        This method verifies the documentation path and checks for specific
        keywords like "onedrive" in the documentation path name. If problematic
        configurations are found, it returns appropriate warning messages.

        Returns:
            A warning message string if problematic configuration is found,
            otherwise an empty string.

        Raises:
            TypeError: If the docs_name or docs_warn obtained from YAML
                settings is not of type str.
        """
        from ClassicLib.YamlSettingsCache import yaml_settings

        message_list: list[str] = []
        docs_name: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.Main_Docs_Name")

        if not isinstance(docs_name, str):
            raise TypeError("Document name must be a string")

        if "onedrive" in docs_name.lower():
            docs_warn: str | None = yaml_settings(str, YAML.Main, "Warnings_GAME.warn_docs_path")
            if not isinstance(docs_warn, str):
                raise TypeError("Document warning must be a string")
            message_list.append(docs_warn)
            logger.warning(f"OneDrive detected in documents path: {docs_name}")

        return "".join(message_list)

    def validate_ini_file(self, ini_filename: str) -> str:
        """
        Validate a specific INI file configuration.

        This method delegates to the docs_check_ini function to validate
        the specified INI file.

        Args:
            ini_filename: Name of the INI file to validate (e.g., "Fallout4.ini")

        Returns:
            A message string containing validation results or warnings.
        """
        logger.debug(f"Validating INI file: {ini_filename}")
        return docs_check_ini(ini_filename)

    def run_all_checks(self) -> list[str]:
        """
        Run all document-related checks.

        This method performs:
        1. Folder configuration check (OneDrive detection)
        2. Validation of all game INI files

        Returns:
            A list of message strings from all checks. Each string may
            contain warnings or validation results.
        """
        game_name: str = GlobalRegistry.get_game()

        checks: list[str] = [
            self.check_folder_configuration(),
            self.validate_ini_file(f"{game_name}.ini"),
            self.validate_ini_file(f"{game_name}Custom.ini"),
            self.validate_ini_file(f"{game_name}Prefs.ini"),
        ]

        # Filter out empty strings
        return [check for check in checks if check]
