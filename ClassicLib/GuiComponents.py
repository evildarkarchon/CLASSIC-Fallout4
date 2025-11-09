"""
Defines a QObject-based class for handling manual documentation paths and game paths for configuration updates.

This module contains the `ManualDocsPath` class, which manages and validates user-provided
directory paths related to manual documentation and game data. Upon validation, the paths
are updated in a settings YAML file. Invalid paths trigger signals requesting new input.

Classes:
    ManualDocsPath: Handles validation and updating of manual documentation paths and game paths.
"""

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from ClassicLib import GlobalRegistry, msg_error, msg_info
from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import yaml_settings


class ManualDocsPath(QObject):
    """
    Handles the management and validation of directory paths related to manual documentation and game files.

    This class provides methods to validate user-provided paths and update configuration files if the paths
    are deemed valid. If invalid paths are provided, appropriate signals are emitted to re-prompt the user.

    Attributes:
        manual_docs_path_signal (Signal): Signal emitted to request a new manual documentation path when
            the provided path is invalid.
        game_path_signal (Signal): Signal emitted to request a new game directory path when the provided
            path is invalid.
    """

    manual_docs_path_signal: Signal = Signal()
    game_path_signal: Signal = Signal()

    def __init__(self) -> None:
        """
        Initializes an instance of a class.

        This constructor method is used to create and initialize an object of a class. It calls
        the parent class's constructor to ensure proper initialization, especially in cases where
        the class is inheriting from another base class.

        """
        super().__init__()

    def get_manual_docs_path_gui(self, path: str) -> None:
        """
        Ensures the provided path is valid for the manual documentation directory of a game.
        If valid, the path is added to the CLASSIC configuration file. Otherwise, the user is
        notified that the path is invalid and a signal to request a new path is emitted.

        Args:
            path (str): The directory path provided by the user to be validated and potentially
                added to the CLASSIC configuration file.

        """
        if Path(path).is_dir():
            msg_info(f"You entered: '{path}' | This path will be automatically added to CLASSIC Settings.yaml")
            manual_docs: Path = Path(path.strip())
            yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Docs", str(manual_docs))
        else:
            msg_error(f"'{path}' is not a valid or existing directory path. Please try again.")
            self.manual_docs_path_signal.emit()

    def get_game_path_gui(self, path: str) -> None:
        """
        Determines if the input path is a valid directory. If valid, updates a settings YAML file with
        the provided path and logs the changes. If invalid, informs the user and re-emits a signal to
        retry.

        Args:
            path (str): The input directory path to be validated and possibly stored.
        """
        if Path(path).is_dir():
            msg_info(f"You entered: '{path}' | This path will be automatically added to CLASSIC Settings.yaml")
            game_path: Path = Path(path.strip())
            yaml_settings(str, YAML.Game_Local, f"Game{GlobalRegistry.get_vr()}_Info.Root_Folder_Game", str(game_path))
        else:
            msg_error(f"'{path}' is not a valid or existing directory path. Please try again.")
            self.game_path_signal.emit()
