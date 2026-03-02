"""Document folder and configuration checking module."""

from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import get_game, get_vr
from ClassicLib.support.docs_path import docs_check_ini


class DocumentsChecker:
    """Validate game documents folder and configuration files."""

    @staticmethod
    def check_folder_configuration() -> str:
        """Validate and checks the folder configuration for specific document paths.

        This method evaluates the configuration of document paths based on the settings
        from the YAML configuration. It performs checks to ensure the validity of the
        document name and warns if the path includes specific conditions (e.g., the
        presence of 'OneDrive'). Errors are raised when expected types are not met.

        Returns:
            str: A concatenated message list containing warnings or an empty string if
            no warnings are applicable.

        Raises:
            TypeError: If the document name or document warning is not a string.

        """
        from ClassicLib.io.yaml import yaml_settings
        from ClassicLib.support.versions import get_version_registry

        message_list: list[str] = []

        # Get docs_name from Version Registry (static metadata)
        registry = get_version_registry()
        is_vr = get_vr() == "VR"
        version_info = registry.get_by_id("FO4_VR" if is_vr else "FO4_OG")
        docs_name: str | None = version_info.docs_name if version_info else None

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
        """Validate if the provided INI filename refers to a valid INI file. This ensures that
        the given file adheres to the expected structure, syntax, and format of INI files.

        Args:
            ini_filename (str): The name of the INI file to validate.

        Returns:
            str: A string result indicating the outcome of the INI file validation.

        """
        logger.debug(f"Validating INI file: {ini_filename}")
        return docs_check_ini(ini_filename)

    def run_all_checks(self) -> list[str]:
        """Run all document-related checks.

        This method performs:
        1. Folder configuration check (OneDrive detection)
        2. Validation of all game INI files

        Returns:
            A list of message strings from all checks. Each string may
            contain warnings or validation results.

        """
        game_name: str = get_game()

        checks: list[str] = [
            self.check_folder_configuration(),
            self.validate_ini_file(f"{game_name}.ini"),
            self.validate_ini_file(f"{game_name}Custom.ini"),
            self.validate_ini_file(f"{game_name}Prefs.ini"),
        ]

        # Filter out empty strings
        return [check for check in checks if check]
