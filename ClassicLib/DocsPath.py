import winreg
from pathlib import Path
from typing import cast

from CLASSIC_Main import yaml_settings, manual_docs_gui, logger
from ClassicLib.Constants import YAML, gamevars


# noinspection PyUnresolvedReferences
def docs_path_find() -> None:
    """
    Provides utility functions to locate and configure the path to a game's documents folder across different platforms.

    The module includes functionality to:
    - Locate the Documents folder on Windows using the system registry.
    - Locate the equivalent folder for Linux when run through Steam.
    - Allow manual user input for specifying the path when automated detection fails.

    Raises:
        OSError: If there is an error accessing the Windows registry.
        UnboundLocalError: If the required registry key is not found.
        TypeError: If the retrieved Steam ID is not an integer or if a required GUI component is uninitialized.
        FileNotFoundError: If a manual input path is provided but does not exist.

    Attributes:
        logger (Logger): Logger instance for debug-level messages.
        winreg (module): Windows registry access used for retrieving the user's documents path.
        Path (Path): Used for handling file and directory paths.
        yaml_settings (function): Utility function for reading and writing configuration from YAML files.
        YAML (enum): Enumerator for YAML configuration sections.
        gamevars (dict): Dictionary storing configuration values related to the current game context.
        gui_mode (bool): Indicator if the program is running in GUI mode.
        manual_docs_gui (object): GUI object for managing manual path inputs or directory selection.

    Defines:
        docs_path_find: Function to initialize the process of finding and validating the game's documents folder path.

    Sub-functions:
        get_windows_docs_path: Retrieves the Documents folder path for Windows systems.
        get_linux_docs_path: Retrieves the equivalent documents path for Linux systems when using Steam.
        get_manual_docs_path: Prompts the user for manual input to specify the documents folder path.
    """
    logger.debug("- - - INITIATED DOCS PATH CHECK")

    # Retrieve the document name from YAML settings
    docs_name = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.Main_Docs_Name")
    if not isinstance(docs_name, str):
        docs_name = gamevars["game"]

    def get_windows_docs_path() -> None:
        """
        Find and update the path of the user's My Documents folder on Windows and save
        it in the game's specific YAML configuration. This function uses the Windows
        Registry to retrieve the target path and falls back to defaults in case of
        errors.

        Raises:
            OSError: If there is an issue accessing the Windows Registry.
            UnboundLocalError: If the registry access results in unbound variable usage.
        """
        try:
            # Open the registry key to get the user's documents path
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders") as key:  # pyright: ignore[reportPossiblyUnboundVariable]
                documents_path = Path(
                    winreg.QueryValueEx(key, "Personal")[0])  # pyright: ignore[reportPossiblyUnboundVariable]
        except (OSError, UnboundLocalError):
            # Fallback to a default path if registry key is not found
            documents_path = Path.home() / "Documents"

        # Construct the full path to the game's documents folder
        win_docs = str(documents_path / "My Games" / cast("str", docs_name))

        # Update the YAML settings with the documents path
        yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs", win_docs)

    def get_linux_docs_path() -> None:
        """
        Retrieves and sets the path to the Linux-compatible game documents directory using the Steam
        library configuration file. This function reads the Steam library folders configuration, looks
        for the appropriate folder associated with the game's Steam ID, and constructs the path to the
        game's "My Documents" folder. It then sets this information into the YAML settings.

        Raises:
            TypeError: If the retrieved Steam ID is not of the expected integer type.
        """
        # Retrieve the Steam ID from YAML settings
        game_sid = yaml_settings(int, YAML.Game, f"Game{gamevars["vr"]}_Info.Main_SteamID")
        if not isinstance(game_sid, int):
            raise TypeError

        # Path to the Steam library folders configuration file
        libraryfolders_path = Path.home() / ".local/share/Steam/steamapps/common/libraryfolders.vdf"

        if libraryfolders_path.is_file():
            library_path = Path()
            with libraryfolders_path.open(encoding="utf-8", errors="ignore") as steam_library_raw:
                steam_library = steam_library_raw.readlines()

            for library_line in steam_library:
                if "path" in library_line:
                    library_path = Path(library_line.split('"')[3])
                if str(game_sid) in library_line:
                    library_path = library_path / "steamapps"
                    linux_docs = library_path / "compatdata" / str(
                        game_sid) / "pfx/drive_c/users/steamuser/My Documents/My Games" / cast("str", docs_name)
                    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs", str(linux_docs))

    def get_manual_docs_path() -> None:
        """
        Locates the path for manual documentation files and updates the application's YAML settings with the
        path provided by the user. Allows repeated attempts until a valid directory path is entered.

        Functions:
            get_manual_docs_path: Prompts the user for a directory path, validates the input, and updates the
                settings file with the path if valid. Displays guidance messages for user input validation.

        Raises:
            None
        """
        print(f"> > > PLEASE ENTER THE FULL DIRECTORY PATH WHERE YOUR {docs_name}.ini IS LOCATED < < <")
        while True:
            input_str = input(
                f"(EXAMPLE: C:/Users/Zen/Documents/My Games/{docs_name} | Press ENTER to confirm.)\n> ").strip()
            input_path = Path(input_str)
            if input_str and input_path.is_dir():
                print(f"You entered: '{input_str}' | This path will be automatically added to CLASSIC Settings.yaml")
                yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs", str(input_path))
                break

            print(f"'{input_str}' is not a valid or existing directory path. Please try again.")

    # =========== CHECK IF GAME DOCUMENTS FOLDER PATH WAS GENERATED AND FOUND ===========
    docs_path = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs")
    if not isinstance(docs_path, str):
        docs_path = None

    if docs_path is None:
        if platform.system() == "Windows":
            get_windows_docs_path()
        else:
            get_linux_docs_path()

    docs_path = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs")
    if not isinstance(docs_path, str):
        docs_path = None

    if docs_path and not Path(docs_path).is_dir():
        if gui_mode:
            if manual_docs_gui is None:
                raise TypeError("CMain not initialized")
            manual_docs_gui.manual_docs_path_signal.emit()
        else:
            get_manual_docs_path()


def get_manual_docs_path_gui(path: str) -> None:
    """
    Handles the selection of a manual documentation path through the
    graphical user interface (GUI). This function validates the given
    path, searches for a specific configuration file in the directory,
    and updates settings if the required file is found. If the validation
    fails or the required file is not found, an error message is
    displayed and the user is prompted to try again.

    Args:
        path: A string representing the directory path entered by the
            user through the GUI. The function expects this path to be
            validated as an existing directory containing the necessary
            game-specific configuration file (e.g., `{game}.ini`).
    """
    if manual_docs_gui is None:
        raise TypeError("CMain not initialized")

    path = path.strip()
    if Path(path).is_dir():
        file_found: bool = False
        for file in Path(path).rglob("*.ini"):
            if f"{gamevars["game"]}.ini" in file.name:
                print(f"You entered: '{path}' | This path will be automatically added to CLASSIC Settings.yaml")
                manual_docs = Path(path)
                yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs", str(manual_docs))
                file_found = True
                break
        if not file_found:
            print(f"❌ ERROR : NO {gamevars["game"]}.ini FILE FOUND IN '{path}'! Please try again.")
            manual_docs_gui.manual_docs_path_signal.emit()
    else:
        print(f"'{path}' is not a valid or existing directory path. Please try again.")
        manual_docs_gui.manual_docs_path_signal.emit()


def docs_generate_paths() -> None:
    """
    Generates and configures paths for documentation files based on various game-specific
    yaml settings. Integrates configuration with specific folders and file paths required
    for documentation purposes. Validates the types of fetched data and applies the
    appropriate yaml updates for local game documentation settings.

    Raises:
        TypeError: Raised if any of the key yaml retrieved settings are not of
            expected types as str.
    """
    logger.debug("- - - INITIATED DOCS PATH GENERATION")
    xse_acronym = yaml_settings(str, YAML.Game, f"Game{gamevars["vr"]}_Info.XSE_Acronym")
    xse_acronym_base = yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")
    docs_path_str = yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Root_Folder_Docs")
    if not (isinstance(xse_acronym, str) and isinstance(xse_acronym_base, str) and isinstance(docs_path_str, str)):
        raise TypeError
    docs_path = Path(docs_path_str)

    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_Folder_XSE",
                  str(docs_path.joinpath(xse_acronym_base)))
    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_File_PapyrusLog",
                  str(docs_path.joinpath("Logs/Script/Papyrus.0.log")))
    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_File_WryeBashPC",
                  str(docs_path.joinpath("ModChecker.html")))
    yaml_settings(str, YAML.Game_Local, f"Game{gamevars["vr"]}_Info.Docs_File_XSE",
                  str(docs_path.joinpath(xse_acronym_base, f"{xse_acronym.lower()}.log")))