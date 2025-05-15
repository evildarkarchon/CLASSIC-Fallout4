from pathlib import Path

from PySide6.QtCore import QObject, Signal
from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import yaml_settings


class ManualDocsPath(QObject):
    manual_docs_path_signal = Signal()

    def __init__(self) -> None:
        super().__init__()

    def get_manual_docs_path_gui(self, path: str) -> None:
        """
        Validates the provided path to ensure it is a directory and updates settings accordingly. Emits a
        signal if the path is invalid.

        Args:
            path: The directory path input by the user. This is validated to ensure it is an existing
                directory.
        """
        if Path(path).is_dir():
            print(f"You entered: '{path}' | This path will be automatically added to CLASSIC Settings.yaml")
            manual_docs = Path(path.strip())
            yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Docs",
                          str(manual_docs))
        else:
            print(f"'{path}' is not a valid or existing directory path. Please try again.")
            self.manual_docs_path_signal.emit()


class GamePathEntry(QObject):
    game_path_signal = Signal()

    def __init__(self) -> None:
        super().__init__()

    def get_game_path_gui(self, path: str) -> None:
        """
        Processes the provided directory path to configure the game settings via GUI.

        Args:
            path: The directory path entered by the user
        """
        if Path(path).is_dir():
            print(f"You entered: '{path}' | This path will be automatically added to CLASSIC Settings.yaml")
            game_path = Path(path.strip())
            yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game",
                          str(game_path))
        else:
            print(f"'{path}' is not a valid or existing directory path. Please try again.")
            self.game_path_signal.emit()
