"""Settings dialog for the CLASSIC application.

Centralizes application settings within a tabbed, modal dialog,
allowing users to configure preferences and paths in a unified
interface. Supports settings related to general usage, scanning
features, paths, and updates.
"""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ClassicLib.Constants import YAML
from ClassicLib.Interface.Settings.path_manager import PathManager
from ClassicLib.Interface.Settings.tab_creators import TabCreator
from ClassicLib.Interface.StyleSheets import DARK_MODE
from ClassicLib.MessageHandler import msg_error, msg_success
from ClassicLib.YamlSettings import yaml_cache, yaml_settings


class SettingsDialog(QDialog):
    """A dialog for managing application settings.

    The SettingsDialog class represents a user interface for managing various
    application settings. It includes a tabbed layout for organizing settings
    categories and provides controls for adjusting specific settings stored in
    a YAML configuration file. The dialog is designed for both main application
    usage and testing purposes, with an option to make it non-modal.

    Attributes:
        SETTINGS_MAP (dict[str, str]): Mapping of widget identifiers to YAML
            configuration keys. Used for organizing and linking UI elements
            to the underlying settings.

    """

    # Mapping between widget keys and YAML setting names
    SETTINGS_MAP: ClassVar[dict[str, str]] = {
        "vr_mode": "VR Mode",
        "fcx_mode": "FCX Mode",
        "simplify_logs": "Simplify Logs",
        "show_fid_values": "Show FormID Values",
        "move_invalid_logs": "Move Unsolved Logs",  # Note: YAML uses "Unsolved" not "Invalid"
        "update_check": "Update Check",
        "update_source": "Update Source",
        "ini_folder_path": "INI Folder Path",
    }

    def __init__(
        self,
        parent: QWidget | None = None,
        yaml_store: YAML = YAML.Settings,
        modal: bool = True,
    ) -> None:
        """Initialize a dialog for CLASSIC settings, providing a user interface to configure settings using
        a set of tabs and widgets. The dialog supports dark mode styling and can operate in modal or
        non-modal mode. It integrates with a YAML store to save or load settings persistently.

        Args:
            parent (QWidget | None): The parent widget of the settings dialog, or None if it has no parent.
            yaml_store (YAML): An instance of a YAML store that holds settings data.
            modal (bool): A flag indicating whether the dialog is modal. True means modal behavior,
                blocking parent interface interaction, while False makes it non-modal.

        """
        super().__init__(parent)
        self.yaml_store = yaml_store

        # Set dialog properties
        self.setWindowTitle("CLASSIC Settings")
        self.setMinimumSize(600, 500)
        self.setWindowModality(Qt.WindowModality.ApplicationModal if modal else Qt.WindowModality.NonModal)

        # Apply dark mode styling
        self.setStyleSheet(DARK_MODE)

        # Store references to settings widgets for easy access
        self.settings_widgets: dict[str, QWidget] = {}

        # Initialize path manager
        self.path_manager = PathManager(self, yaml_store)

        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create tabs using TabCreator
        self._create_tabs()

        # Create button box
        # noinspection PyTypeChecker
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        # Load current settings
        self.load_settings()

    def _create_tabs(self) -> None:
        """Create and initializes tabs for a user interface, storing widget references for
        settings management and ensuring backward compatibility by maintaining legacy attribute
        names. Each tab corresponds to a specific category: General, Scanning, Paths, and Updates.

        Raises:
            None

        """
        # General tab
        general_widget, general_widgets = TabCreator.create_general_tab(self)
        self.settings_widgets.update(general_widgets)
        self.tab_widget.addTab(general_widget, "General")

        # Store widget references for backwards compatibility
        self.vr_checkbox = general_widgets.get("vr_mode")

        # Scanning tab
        scanning_widget, scanning_widgets = TabCreator.create_scanning_tab(self)
        self.settings_widgets.update(scanning_widgets)
        self.tab_widget.addTab(scanning_widget, "Scanning")

        # Store widget references for backwards compatibility
        self.fcx_checkbox = scanning_widgets.get("fcx_mode")
        self.simplify_checkbox = scanning_widgets.get("simplify_logs")
        self.show_fid_checkbox = scanning_widgets.get("show_fid_values")
        self.move_invalid_checkbox = scanning_widgets.get("move_invalid_logs")

        # Paths tab
        paths_widget, paths_widgets = TabCreator.create_paths_tab(self, self.path_manager)
        self.settings_widgets.update(paths_widgets)
        self.tab_widget.addTab(paths_widget, "Paths")

        # Store widget references for backwards compatibility
        self.ini_folder_input = paths_widgets.get("ini_folder_path")
        # Create proxy methods for backwards compatibility
        self.ini_reset_button = QPushButton()  # Dummy button for attribute access
        self.ini_browse_button = QPushButton()  # Dummy button for attribute access

        # Updates tab
        updates_widget, updates_widgets, check_now_button = TabCreator.create_updates_tab(self)
        self.settings_widgets.update(updates_widgets)
        self.tab_widget.addTab(updates_widget, "Updates")

        # Store widget references for backwards compatibility
        self.update_check_checkbox = updates_widgets.get("update_check")
        self.update_source_combo = updates_widgets.get("update_source")
        self.check_now_button = check_now_button

    # Backwards compatibility methods
    def _browse_ini_folder(self) -> None:
        """Trigger the browsing of an .ini folder through the path manager.

        This method utilizes the path manager to prompt a folder browsing dialog,
        allowing users to select an .ini folder.
        """
        self.path_manager.browse_ini_folder()

    def _reset_ini_folder(self) -> None:
        """Reset the INI folder to its default state.

        This method interacts with the path manager to reset the INI folder to its
        initial configuration or state.
        """
        self.path_manager.reset_ini_folder()

    def _autodetect_ini_folder(self) -> None:
        """Automatically detects the folder containing the INI configuration file and sets it
        appropriately in the path manager.

        Raises:
            None

        """
        self.path_manager.autodetect_ini_folder()

    def load_settings(self) -> None:
        """Load and applies settings from a configuration source into the application's GUI elements.

        This method retrieves settings from a YAML store using a batch request mechanism, processes
        the retrieved values, and then updates the corresponding GUI controls in the application.
        It handles both boolean and string settings, updating checkboxes, combo boxes, and text
        inputs accordingly. Default values or backup configurations are used when invalid or missing
        values are encountered during the loading process.

        Raises:
            TypeError: If the retrieved settings have incorrect types.
            ValueError: If the settings processing encounters unexpected values.
            KeyError: If a specified key is not found in the settings map.

        """
        from ClassicLib.Logger import logger

        try:
            # Get current settings - boolean settings
            bool_requests = [
                (bool, self.yaml_store, f"CLASSIC_Settings.{setting_name}")
                for key, setting_name in self.SETTINGS_MAP.items()
                if key not in {"update_source", "ini_folder_path"}
            ]
            # String settings
            str_requests = [
                (str, self.yaml_store, f"CLASSIC_Settings.{self.SETTINGS_MAP['update_source']}"),
                (str, self.yaml_store, f"CLASSIC_Settings.{self.SETTINGS_MAP['ini_folder_path']}"),
            ]
            # Combine all requests
            requests = bool_requests + str_requests

            # Batch load all settings
            values = yaml_cache.batch_get_settings(requests)
            value_iter = iter(values)

            # Update checkboxes
            for key in [
                "vr_mode",
                "fcx_mode",
                "simplify_logs",
                "show_fid_values",
                "move_invalid_logs",
                "update_check",
            ]:
                widget = self.settings_widgets.get(key)
                if isinstance(widget, QCheckBox):
                    widget.setChecked(next(value_iter) or False)

            # Update combo box
            update_source = next(value_iter) or "Nexus"
            if isinstance(self.update_source_combo, QComboBox):
                index = self.update_source_combo.findText(update_source)
                if index != -1:
                    self.update_source_combo.setCurrentIndex(index)
                else:
                    # Invalid value - use default
                    default_index = self.update_source_combo.findText("Both")
                    if default_index != -1:
                        self.update_source_combo.setCurrentIndex(default_index)

            # Update INI folder path
            ini_path = next(value_iter) or ""
            if isinstance(self.ini_folder_input, QLineEdit):
                if not ini_path:
                    # Try to get from Game_Local YAML if not set in settings
                    from ClassicLib import GlobalRegistry

                    try:
                        vr_suffix = GlobalRegistry.get_vr()
                        root_docs_key = f"Game{vr_suffix}_Info.Root_Folder_Docs"
                        ini_path = yaml_settings(str, YAML.Game_Local, root_docs_key) or ""
                    except (ImportError, TypeError, ValueError):
                        pass
                self.ini_folder_input.setText(ini_path)

            logger.info("Loaded settings into dialog")

        except (TypeError, ValueError, KeyError) as e:
            logger.error(f"Failed to load settings: {e}")
            msg_error(f"Failed to load some settings: {e!s}\n\nDefault values will be used.")

    def save_settings(self) -> None:
        """Save the user settings from the dialog widgets into the YAML storage.

        This method saves various user preferences and settings into a YAML
        store. It handles saving the states of checkboxes, combo box selections,
        and text inputs representing configurations. If an INI folder path is
        specified, it updates the related game-specific YAML configuration.
        Errors encountered during the process are logged, and appropriate user
        messages are displayed.

        Raises:
            TypeError: Raised if there are type compatibility issues during
                the saving process.
            ValueError: Raised if unexpected values are encountered during the
                saving process.
            OSError: Raised if there are file-related issues, such as lack of
                permissions or invalid paths.

        """
        from ClassicLib.Logger import logger

        try:
            # Save checkboxes
            for key in [
                "vr_mode",
                "fcx_mode",
                "simplify_logs",
                "show_fid_values",
                "move_invalid_logs",
                "update_check",
            ]:
                widget = self.settings_widgets.get(key)
                if isinstance(widget, QCheckBox):
                    setting_name = self.SETTINGS_MAP[key]
                    yaml_settings(bool, self.yaml_store, f"CLASSIC_Settings.{setting_name}", widget.isChecked())

            # Save combo box
            if isinstance(self.update_source_combo, QComboBox):
                yaml_settings(
                    str, self.yaml_store, f"CLASSIC_Settings.{self.SETTINGS_MAP['update_source']}", self.update_source_combo.currentText()
                )

            # Save INI folder path
            if isinstance(self.ini_folder_input, QLineEdit):
                ini_path = self.ini_folder_input.text().strip()
                yaml_settings(str, self.yaml_store, f"CLASSIC_Settings.{self.SETTINGS_MAP['ini_folder_path']}", ini_path)

                # Also update Game_Local YAML if path is set
                if ini_path:
                    from ClassicLib import GlobalRegistry

                    try:
                        vr_suffix = GlobalRegistry.get_vr()
                        root_docs_key = f"Game{vr_suffix}_Info.Root_Folder_Docs"
                        yaml_settings(str, YAML.Game_Local, root_docs_key, ini_path)
                    except (ImportError, TypeError, ValueError):
                        pass

            logger.info("Saved settings from dialog")
            msg_success("Settings saved successfully!")

        except (TypeError, ValueError, OSError) as e:
            logger.error(f"Failed to save settings: {e}")
            msg_error(f"Failed to save settings: {e!s}\n\nPlease check file permissions and try again.")

    def _recalculate_derivative_paths(self) -> None:
        """Recalculates derivative paths related to documents, game, and mods based on the current
        INI folder input.

        This method updates derived paths by validating and resolving paths using external utilities.
        It utilizes various modules to ensure the paths are recalculated, validated, and logged
        appropriately. The method silently handles known exceptions as it runs in the background
        without user interaction.

        Raises:
            ImportError: If there is an issue importing required modules.
            TypeError: If an operation encounters unexpected data types.
            ValueError: If there are issues with the path values.
            OSError: If there is an operating system-related error during the process.

        """
        from ClassicLib.DocsPath import docs_path_find
        from ClassicLib.GamePath import game_path_find
        from ClassicLib.Logger import logger
        from ClassicLib.PathValidator import PathValidator

        try:
            # Recalculate document paths if INI folder was changed
            if isinstance(self.ini_folder_input, QLineEdit):
                ini_path = self.ini_folder_input.text().strip()
                if ini_path:
                    logger.info(f"Recalculating paths based on INI folder: {ini_path}")
                    # This will update the derived paths
                    docs_path_find(is_gui_mode=True)

            # Recalculate game paths
            game_path_find()

            # Validate mods paths
            PathValidator.validate_mods_folder_path()

            logger.info("Successfully recalculated derivative paths")

        except (ImportError, TypeError, ValueError, OSError) as e:
            logger.error(f"Failed to recalculate paths: {e}")
            # Don't show error to user as this is a background operation

    def accept(self) -> None:
        """Execute the acceptance workflow by saving settings, recalculating derivative
        paths, and invoking the base class's accept method.

        Raises:
            Various exceptions depending on the implementation of `save_settings`,
            `_recalculate_derivative_paths`, or `super().accept()` if errors occur
            during execution.

        """
        self.save_settings()
        self._recalculate_derivative_paths()
        super().accept()

    def reject(self) -> None:
        """Close the dialog without saving any changes.

        This method overrides the parent's `reject` method to ensure that no changes
        are saved when the dialog is closed.

        Raises:
            None

        """
        # Just close without saving
        super().reject()
