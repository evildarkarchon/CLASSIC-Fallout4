import contextlib
import platform
from pathlib import Path
from typing import cast

from iniparse import configparser

from ClassicLib import GlobalRegistry, msg_error, msg_info
from ClassicLib.Constants import YAML
from ClassicLib.Logger import logger
from ClassicLib.Util import remove_readonly
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class DocumentsPathManager:
    """Manages game document paths across different platforms."""

    def __init__(self, is_gui_mode: bool = False) -> None:
        """Initialize the document path manager.

        Args:
            gui_mode: Whether the program is running in GUI mode
        """
        self.is_gui_mode = is_gui_mode
        self.manual_docs_gui = GlobalRegistry.get_manual_docs_gui() if is_gui_mode else None
        self.docs_name = self._get_docs_name()

    @staticmethod
    def _get_docs_name() -> str:
        """Get the document folder name from settings."""
        docs_name: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.Main_Docs_Name")
        if not isinstance(docs_name, str):
            docs_name = GlobalRegistry.get_game()
        return docs_name

    @staticmethod
    def _get_game_setting_path(setting_name: str) -> str:
        """Get a path from game settings.

        Args:
            setting_name: The setting name suffix to retrieve

        Returns:
            The path as a string

        Raises:
            TypeError: If the setting value is not a string
        """
        path: str | None = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.{setting_name}")
        if not isinstance(path, str):
            raise TypeError(f"Expected string value for {setting_name}")
        return path

    @staticmethod
    def _update_game_setting(setting_name: str, value: str) -> None:
        """Update a game setting value.

        Args:
            setting_name: The setting name suffix to update
            value: The value to set
        """
        yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.{setting_name}", value)

    def find_docs_path(self) -> None:
        """Find and configure the game documents folder path."""
        logger.debug("- - - INITIATED DOCS PATH CHECK")

        from ClassicLib.Util import validate_path

        # First check if INI Folder Path is set in CLASSIC Settings.yaml
        ini_folder_path: str | None = classic_settings(str, "INI Folder Path")
        if isinstance(ini_folder_path, str) and ini_folder_path.strip():
            # Validate the configured INI folder path
            is_valid, error_msg = validate_path(ini_folder_path, check_write=True, check_read=True)
            if is_valid and Path(ini_folder_path).is_dir():
                logger.debug(f"Using INI Folder Path from settings: {ini_folder_path}")
                self._update_game_setting("Root_Folder_Docs", ini_folder_path)
                return
            logger.warning(f"Configured INI Folder Path is not accessible: {error_msg}")
            # Continue to auto-detection

        # Check if path already exists and is accessible
        docs_path: str | None = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Docs")
        if isinstance(docs_path, str):
            is_valid, error_msg = validate_path(docs_path, check_write=True, check_read=True)
            if is_valid and Path(docs_path).is_dir():
                return  # Path is valid, no need to re-detect
            logger.warning(f"Existing docs path is not accessible: {error_msg}")
            # Continue to auto-detection

        if True:  # Always attempt to find/update path if we get here
            # Find path based on platform
            if platform.system() == "Windows":
                self._find_windows_docs_path()
            else:
                self._find_linux_docs_path()

            # Check if path was found successfully
            docs_path = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Docs")
            if not isinstance(docs_path, str) or not Path(docs_path).is_dir():
                self._get_manual_docs_path()

    def _find_windows_docs_path(self) -> None:
        """Find the Windows documents path using the registry."""
        # Initialize with default value first
        import winreg

        documents_path: Path = Path.home() / "Documents"

        try:
            # Open the registry key to get the user's documents path
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:  # type: ignore[reportAttributeAccessIssue]
                documents_path = Path(winreg.QueryValueEx(key, "Personal")[0])  # type: ignore[reportAttributeAccessIssue]
        except (OSError, UnboundLocalError):
            # Fallback to a default path if registry key is not found
            pass  # We already initialized documents_path with the default value

        # Construct the full path to the game's documents folder
        win_docs: str = str(documents_path / "My Games" / cast("str", self.docs_name))

        # Update the YAML settings with the documents path
        self._update_game_setting("Root_Folder_Docs", win_docs)

    def _find_linux_docs_path(self) -> None:
        """Find the Linux documents path using Steam library configuration."""
        # Retrieve the Steam ID from YAML settings
        game_sid: int | None = yaml_settings(int, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.Main_SteamID")
        if not isinstance(game_sid, int):
            raise TypeError("Invalid Steam ID")

        # Path to the Steam library folders configuration file
        libraryfolders_path: Path = Path.home() / ".local/share/Steam/steamapps/common/libraryfolders.vdf"
        if not libraryfolders_path.is_file():
            return

        library_path: Path = Path()
        with libraryfolders_path.open(encoding="utf-8", errors="ignore") as steam_library_raw:
            steam_library: list[str] = steam_library_raw.readlines()

        for library_line in steam_library:
            if "path" in library_line:
                library_path = Path(library_line.split('"')[3])
            if str(game_sid) in library_line:
                library_path = library_path / "steamapps"
                linux_docs: Path = (
                    library_path
                    / "compatdata"
                    / str(game_sid)
                    / "pfx/drive_c/users/steamuser/My Documents/My Games"
                    / cast("str", self.docs_name)
                )
                self._update_game_setting("Root_Folder_Docs", str(linux_docs))

    def _get_manual_docs_path(self) -> None:
        """Get manual documents path input from the user."""
        if self.is_gui_mode and self.manual_docs_gui is not None:
            self.manual_docs_gui.manual_docs_path_signal.emit()
            return

        msg_info(f"> > > PLEASE ENTER THE FULL DIRECTORY PATH WHERE YOUR {self.docs_name}.ini IS LOCATED < < <")
        while True:
            input_str: str = input(f"(EXAMPLE: C:/Users/Zen/Documents/My Games/{self.docs_name} | Press ENTER to confirm.)\n> ").strip()
            input_path: Path = Path(input_str)
            if input_str and input_path.is_dir():
                msg_info(f"You entered: '{input_str}' | This path will be automatically added to CLASSIC Settings.yaml")
                self._update_game_setting("Root_Folder_Docs", str(input_path))
                break
            msg_error(f"'{input_str}' is not a valid or existing directory path. Please try again.")

    def generate_paths(self) -> None:
        """
        Generates and updates the documentation paths necessary for the game.

        This method uses the current game version and YAML configuration to determine
        the appropriate paths required for generating and updating documentation-related
        files. The paths are then updated in the current game settings registry. If
        any required settings are missing or invalid, a TypeError will be raised.

        Raises:
            TypeError: If required settings are missing or not valid.

        """
        logger.debug("- - - INITIATED DOCS PATH GENERATION")

        # Get required settings
        xse_acronym: str | None = yaml_settings(str, YAML.Game, f"Game{GlobalRegistry.get_vr()}_Info.XSE_Acronym")
        xse_acronym_base: str | None = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
        docs_path_str: str | None = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Docs")

        if not (isinstance(xse_acronym, str) and isinstance(xse_acronym_base, str) and isinstance(docs_path_str, str)):
            raise TypeError("Missing or invalid settings")

        docs_path: Path = Path(docs_path_str)

        # Update path settings
        self._update_game_setting("Docs_Folder_XSE", str(docs_path.joinpath(xse_acronym_base)))
        self._update_game_setting("Docs_File_PapyrusLog", str(docs_path.joinpath("Logs/Script/Papyrus.0.log")))
        self._update_game_setting("Docs_File_WryeBashPC", str(docs_path.joinpath("ModChecker.html")))
        self._update_game_setting("Docs_File_XSE", str(docs_path.joinpath(xse_acronym_base, f"{xse_acronym.lower()}.log")))

    def check_ini(self, ini_name: str) -> str:
        """
        Check the existence and validity of an INI file.

        This method verifies whether an INI file with the given name (`ini_name`)
        exists in the specified documentation folder. If the file exists, further
        checks are carried out on its content. If the file is missing, the absence is
        handled accordingly. The function returns a message detailing the results of
        the checks.

        Args:
            ini_name: The name of the INI file to check.

        Raises:
            TypeError: Raised if the `docs_name` attribute is not a string.
            TypeError: Raised if the `folder_docs` is not a string or is None.

        Returns:
            A string containing the results of the INI file checks.
        """
        message_list: list[str] = []
        logger.info(f"- - - INITIATED {ini_name} CHECK")

        folder_docs: str | None = yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Docs")

        if not isinstance(self.docs_name, str):
            raise TypeError("Invalid docs_name")
        if not isinstance(folder_docs, str) or folder_docs is None:
            raise TypeError("Invalid folder_docs type")

        docs_path: Path = Path(folder_docs)
        ini_file_list: list[Path] = list(docs_path.glob("*.ini"))
        ini_path: Path = docs_path.joinpath(ini_name)

        if any(ini_name.lower() in file.name.lower() for file in ini_file_list):
            message_list.extend(self._check_existing_ini(ini_path, ini_name))
        else:
            message_list.extend(self._handle_missing_ini(ini_path, ini_name))

        return "".join(message_list)

    def _check_existing_ini(self, ini_path: Path, ini_name: str) -> list[str]:
        """Check an existing INI file.

        Args:
            ini_path: Path to the INI file
            ini_name: Name of the INI file

        Returns:
            List of messages about the file status
        """
        message_list: list[str] = []
        try:
            remove_readonly(ini_path)
            ini_config: configparser.ConfigParser = configparser.ConfigParser()
            ini_config.optionxform = str  # type: ignore[method-assign, assignment]
            ini_config.read(ini_path)

            message_list.append(f"✔️ No obvious corruption detected in {ini_name}, file seems OK! \n-----\n")

            if ini_name.lower() == f"{self.docs_name.lower()}custom.ini":
                message_list.extend(self._configure_custom_ini(ini_config, ini_path))

        except PermissionError:
            message_list.extend([
                f"[!] CAUTION : YOUR {ini_name} FILE IS SET TO READ ONLY. \n",
                "     PLEASE REMOVE THE READ ONLY PROPERTY FROM THIS FILE, \n",
                "     SO CLASSIC CAN MAKE THE REQUIRED CHANGES TO IT. \n-----\n",
            ])
        except (configparser.MissingSectionHeaderError, configparser.ParsingError, ValueError, OSError):
            message_list.extend([
                f"[!] CAUTION : YOUR {ini_name} FILE IS VERY LIKELY BROKEN, PLEASE CREATE A NEW ONE \n",
                f"    Delete this file from your Documents/My Games/{self.docs_name} folder, then press \n",
                f"    *Scan Game Files* in CLASSIC to generate a new {ini_name} file. \n-----\n",
            ])
        except configparser.DuplicateOptionError as e:
            message_list.extend([f"[!] ERROR : Your {ini_name} file has duplicate options! \n", f"    {e} \n-----\n"])

        return message_list

    @staticmethod
    def _configure_custom_ini(ini_config: configparser.ConfigParser, ini_path: Path) -> list[str]:
        """Configure custom INI settings.

        Args:
            ini_config: ConfigParser with the INI content
            ini_path: Path to the INI file

        Returns:
            List of messages about the configuration changes
        """
        message_list: list[str] = []
        if "Archive" not in ini_config.sections():
            message_list.extend([
                "❌ WARNING : Archive Invalidation / Loose Files setting is not enabled. \n",
                "  CLASSIC will now enable this setting automatically in the game INI files. \n-----\n",
            ])
            with contextlib.suppress(configparser.DuplicateSectionError):
                ini_config.add_section("Archive")
        else:
            message_list.append("✔️ Archive Invalidation / Loose Files setting is already enabled! \n-----\n")

        ini_config.set("Archive", "bInvalidateOlderFiles", "1")
        ini_config.set("Archive", "sResourceDataDirsFinal", "")

        with ini_path.open("w+", encoding="utf-8", errors="ignore") as ini_file:
            ini_config.write(ini_file, space_around_delimiters=False)

        return message_list

    def _handle_missing_ini(self, ini_path: Path, ini_name: str) -> list[str]:
        """Handle a missing INI file.

        Args:
            ini_path: Path where the INI file should be
            ini_name: Name of the INI file

        Returns:
            List of messages about the missing file
        """
        message_list: list[str] = []

        if ini_name.lower() == f"{self.docs_name.lower()}.ini":
            message_list.extend([
                f"❌ CAUTION : {ini_name} FILE IS MISSING FROM YOUR DOCUMENTS FOLDER! \n",
                f"   You need to run the game at least once with {self.docs_name}Launcher.exe \n",
                "    This will create files and INI settings required for the game to run. \n-----\n",
            ])
        elif ini_name.lower() == f"{self.docs_name.lower()}custom.ini":
            with ini_path.open("a", encoding="utf-8", errors="ignore") as ini_file:
                message_list.extend([
                    "❌ WARNING : Archive Invalidation / Loose Files setting is not enabled. \n",
                    "  CLASSIC will now enable this setting automatically in the game INI files. \n-----\n",
                ])
                customini_config: str | None = yaml_settings(str, YAML.Game, "Default_CustomINI")
                if not isinstance(customini_config, str):
                    raise TypeError("Invalid customINI config")
                ini_file.write(customini_config)

        return message_list


# Public API functions that use the DocumentsPathManager class
def docs_path_find(is_gui_mode: bool = False) -> None:
    """
    Locates the documents path using a manager instance.

    This function initializes a `DocumentsPathManager` object, passing the
    specified mode (GUI or non-GUI) and invokes its `find_docs_path` method
    to determine the location of the documents path.

    Args:
        is_gui_mode (bool): If True, enables GUI mode; otherwise, operates in
            command-line mode.

    Returns:
        None
    """
    manager: DocumentsPathManager = DocumentsPathManager(is_gui_mode)
    manager.find_docs_path()


def docs_generate_paths() -> None:
    """
    Executes the process to generate document paths using the DocumentsPathManager.

    The function initializes a DocumentsPathManager instance and invokes its
    generate_paths method to perform the document paths generation.

    """
    manager: DocumentsPathManager = DocumentsPathManager()
    manager.generate_paths()


def docs_check_ini(ini_name: str) -> str:
    """
    Checks the validity of the provided ini file by utilizing the DocumentsPathManager
    to determine its existence or setup requirements.

    Args:
        ini_name (str): The name of the ini file to be checked.

    Returns:
        str: A status message indicating the result of the check.
    """
    manager: DocumentsPathManager = DocumentsPathManager()
    return manager.check_ini(ini_name)
