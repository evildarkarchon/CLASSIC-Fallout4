"""
Manages path-related settings and operations effectively, allowing the user to interact
with path settings such as INI folder paths. Provides functionalities including setting,
browsing, resetting, and auto-detecting path values for customization and ease of use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QLineEdit

from ClassicLib.Constants import YAML
from ClassicLib.MessageHandler import msg_error, msg_success, msg_warning
from ClassicLib.YamlSettingsCache import yaml_settings

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class PathManager:
    """
    Manage the operations related to the path configuration for INI folder settings.

    This class provides methods for managing the INI folder settings using a graphical
    user interface (GUI). It enables browsing for a specific folder, resetting the INI
    folder to its auto-detected value, and triggering auto-detection of the folder path.
    The operations involve interactions with the YAML settings and executing folder
    detection logic to update the relevant user interface components.

    Attributes:
        parent (QWidget): The parent widget for displaying file dialogs and messages.
        yaml_store (YAML): The YAML store instance utilized for managing settings.
        ini_folder_input (QLineEdit | None): Reference to the input widget for displaying
            and modifying the INI folder path.
    """

    def __init__(self, parent: QWidget, yaml_store: YAML = YAML.Settings) -> None:
        """
        Initializes a new instance of the class.

        Args:
            parent (QWidget): The parent widget associated with the instance.
            yaml_store (YAML): The YAML configuration or settings object.
        """
        self.parent = parent
        self.yaml_store = yaml_store
        self.ini_folder_input: QLineEdit | None = None

    def set_ini_folder_input(self, input_widget: QLineEdit) -> None:
        """
        Sets the folder input widget for the application.

        This method assigns an input widget to the attribute responsible for managing
        the folder path input. It should be used to dynamically set the widget for
        user interaction with folder path inputs.

        Args:
            input_widget (QLineEdit): The input widget to set as the folder input
                handler.
        """
        self.ini_folder_input = input_widget

    def browse_ini_folder(self) -> None:
        """
        Opens a folder dialog to allow the user to select an INI folder for a game. The selected
        folder path is then set to the corresponding input field. If no input or folder is
        selected, the function exits without changes.

        Raises:
            TypeError: Raised if an invalid type is provided when retrieving the game information.
            ValueError: Raised if an invalid value is encountered during game information retrieval.
            AttributeError: Raised if an attribute is missing during game information retrieval.
        """
        from ClassicLib import GlobalRegistry

        if not self.ini_folder_input:
            return

        try:
            game = GlobalRegistry.get_game()
        except (TypeError, ValueError, AttributeError):
            game = "Game"

        folder = QFileDialog.getExistingDirectory(
            self.parent,
            f"Select INI Folder for {game}",
            self.ini_folder_input.text() or "",
            QFileDialog.Option.ShowDirsOnly,
        )

        if folder:
            self.ini_folder_input.setText(folder)

    def reset_ini_folder(self) -> None:
        """
        Resets the INI folder path in the configuration and triggers a fresh autodetection process.

        This method performs the following operations:
        1. Clears the INI folder path setting in the CLASSIC_Settings.yaml file and logs this
           action for tracking purposes.
        2. Clears the Root_Folder_Docs key in the Game_Local YAML file to ensure a fresh
           detection of the folder paths specific to the game configuration.
        3. Invokes the autodetection mechanism to reinitialize the configuration for the
           INI folder path based on the current environment.

        Relevant exceptions caught include ImportError, TypeError, ValueError, and OSError,
        and appropriate error messages are logged and displayed to the user.

        Raises:
            ImportError: If required modules or components are not found.
            TypeError: If the provided data type is not as expected.
            ValueError: If the operation encounters invalid data or values.
            OSError: On operating system-related failures.

        """
        from ClassicLib import GlobalRegistry
        from ClassicLib.Logger import logger

        try:
            # Clear the INI Folder Path setting in CLASSIC Settings.yaml
            yaml_settings(str, self.yaml_store, "CLASSIC_Settings.INI Folder Path", "")
            logger.info("Cleared INI Folder Path setting for autodetection")

            # Clear the Root_Folder_Docs in Game_Local YAML to trigger fresh detection
            vr_suffix = GlobalRegistry.get_vr()
            root_docs_key = f"Game{vr_suffix}_Info.Root_Folder_Docs"
            yaml_settings(str, YAML.Game_Local, root_docs_key, "")
            logger.info("Cleared Root_Folder_Docs for fresh autodetection")

            # Run the autodetection
            self.autodetect_ini_folder()

        except (ImportError, TypeError, ValueError, OSError) as e:
            logger.error(f"Failed to reset INI folder path: {e}")
            # Show error to user
            msg_error(f"Failed to reset INI folder path: {e!s}\n\nPlease try again or set the path manually.")

    def autodetect_ini_folder(self) -> None:
        """
        Autodetects the INI folder path and updates the user interface.

        This method attempts to automatically detect the INI folder path used by the application or
        game. If a new path is successfully detected, the method updates the relevant UI element
        and notifies the user. In case the detection fails or encounters an error, it clears the
        input UI element, logs the incident, and informs the user with an appropriate message.

        Raises:
            ImportError: If there is an error importing necessary modules or libraries.
            TypeError: If there is a type-related error during the operation.
            ValueError: If a value-related error occurs, such as invalid YAML content.
            OSError: If a system-related error occurs, like file-related issues.
        """
        from ClassicLib import GlobalRegistry
        from ClassicLib.DocsPath import docs_path_find
        from ClassicLib.Logger import logger

        if not self.ini_folder_input:
            return

        try:
            # Run the autodetection logic (same as first run)
            docs_path_find(is_gui_mode=True)
            logger.info("Ran INI folder autodetection")

            # Retrieve the newly detected path from Game_Local YAML
            vr_suffix = GlobalRegistry.get_vr()
            root_docs_key = f"Game{vr_suffix}_Info.Root_Folder_Docs"
            detected_path = yaml_settings(str, YAML.Game_Local, root_docs_key)

            # Update the UI with the detected path
            if detected_path:
                self.ini_folder_input.setText(detected_path)
                logger.info(f"Updated INI folder path to: {detected_path}")
                # Show success message to user
                msg_success(f"INI folder path reset successfully!\n\nDetected path: {detected_path}")
            else:
                # If autodetection failed, clear the input field
                self.ini_folder_input.clear()
                logger.warning("Autodetection did not find a valid INI folder path")
                # Show warning to user
                msg_warning(
                    "Could not auto-detect INI folder path.\n\n"
                    "Please use the Browse button to manually select your game's INI folder.\n"
                    "This is typically located in Documents/My Games/[Game Name]"
                )

        except (ImportError, TypeError, ValueError, OSError) as e:
            logger.error(f"Failed to autodetect INI folder path: {e}")
            # Show error to user
            msg_error(f"Failed to auto-detect INI folder path: {e!s}\n\nPlease set the path manually using the Browse button.")
