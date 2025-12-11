"""Documents folder and configuration checking module."""

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.DocsPath import docs_check_ini
from ClassicLib.Logger import logger


class DocumentsChecker:
    """Validates game documents folder and configuration files."""

    @staticmethod
    def check_folder_configuration() -> str:
        """
        Validates and checks the folder configuration for specific document paths.

        This method evaluates the configuration of document paths based on the settings
        from the YAML configuration. It performs checks to ensure the validity of the
        document name and warns if the path includes specific conditions (e.g., the
        presence of 'OneDrive'). Errors are raised when expected types are not met.

        Raises:
            TypeError: If the document name or document warning is not a string.

        Returns:
            str: A concatenated message list containing warnings or an empty string if
            no warnings are applicable.
        """
        from ClassicLib.YamlSettings import yaml_settings

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

    @staticmethod
    def validate_ini_file(ini_filename: str) -> str:
        """
        Validates if the provided INI filename refers to a valid INI file. This ensures that
        the given file adheres to the expected structure, syntax, and format of INI files.

        Args:
            ini_filename (str): The name of the INI file to validate.

        Returns:
            str: A string result indicating the outcome of the INI file validation.
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
