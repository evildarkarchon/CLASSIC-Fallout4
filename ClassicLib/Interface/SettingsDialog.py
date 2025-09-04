"""
Settings dialog for CLASSIC application configuration.

This module provides a centralized settings dialog that replaces the scattered
settings previously embedded in the main window's grid layout.
"""

from __future__ import annotations

from typing import ClassVar

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ClassicLib.Constants import YAML
from ClassicLib.Interface.StyleSheets import DARK_MODE
from ClassicLib.MessageHandler import msg_error, msg_success, msg_warning
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class SettingsDialog(QDialog):
    """
    Dedicated settings dialog for CLASSIC application configuration.

    Centralizes all application settings in a single modal dialog with
    tabbed organization for better UX and maintainability.
    """

    # Mapping between widget keys and YAML setting names
    SETTINGS_MAP: ClassVar[dict[str, str]] = {
        "audio_notifications": "Audio Notifications",
        "vr_mode": "VR Mode",
        "fcx_mode": "FCX Mode",
        "simplify_logs": "Simplify Logs",
        "show_fid_values": "Show FormID Values",
        "move_invalid_logs": "Move Unsolved Logs",  # Note: YAML uses "Unsolved" not "Invalid"
        "update_check": "Update Check",
        "update_source": "Update Source",
        "ini_folder_path": "INI Folder Path",
    }

    def __init__(self, parent: QWidget | None = None, yaml_store: YAML = YAML.Settings) -> None:
        """
        Initialize the settings dialog.

        Args:
            parent: Parent widget for the dialog
            yaml_store: YAML store to use for settings (defaults to YAML.Settings)
        """
        super().__init__(parent)
        self.yaml_store = yaml_store

        # Set dialog properties
        self.setWindowTitle("CLASSIC Settings")
        self.setMinimumSize(600, 500)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Apply dark mode styling
        self.setStyleSheet(DARK_MODE)

        # Store references to settings widgets for easy access
        self.settings_widgets: dict[str, QWidget] = {}

        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create tabs
        self._create_general_tab()
        self._create_scanning_tab()
        self._create_paths_tab()
        self._create_updates_tab()

        # Create button box
        # noinspection PyTypeChecker
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        # Load current settings
        self.load_settings()

    def _create_general_tab(self) -> None:
        """Create the General settings tab."""
        general_widget = QWidget()
        layout = QVBoxLayout(general_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create general settings group
        general_group = QGroupBox("General Settings")
        general_layout = QVBoxLayout(general_group)
        general_layout.setSpacing(10)

        # Audio Notifications checkbox
        self.audio_checkbox = QCheckBox("Audio Notifications")
        self.audio_checkbox.setToolTip("Play sound effects when scans complete or errors occur")
        general_layout.addWidget(self.audio_checkbox)
        self.settings_widgets["audio_notifications"] = self.audio_checkbox

        # VR Mode checkbox
        self.vr_checkbox = QCheckBox("VR Mode")
        self.vr_checkbox.setToolTip("Prioritize settings and checks for VR version of the game")
        general_layout.addWidget(self.vr_checkbox)
        self.settings_widgets["vr_mode"] = self.vr_checkbox

        layout.addWidget(general_group)
        layout.addStretch()

        # Add tab to widget
        self.tab_widget.addTab(general_widget, "General")

    def _create_scanning_tab(self) -> None:
        """Create the Scanning settings tab."""
        scanning_widget = QWidget()
        layout = QVBoxLayout(scanning_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create scanning settings group
        scanning_group = QGroupBox("Scanning Options")
        scanning_layout = QVBoxLayout(scanning_group)
        scanning_layout.setSpacing(10)

        # FCX Mode checkbox
        self.fcx_checkbox = QCheckBox("FCX Mode")
        self.fcx_checkbox.setToolTip("Enable extended file integrity checks for more thorough scanning")
        scanning_layout.addWidget(self.fcx_checkbox)
        self.settings_widgets["fcx_mode"] = self.fcx_checkbox

        # Simplify Logs checkbox
        self.simplify_checkbox = QCheckBox("Simplify Logs")
        self.simplify_checkbox.setToolTip("Remove redundant and repetitive lines from crash logs for easier reading")
        scanning_layout.addWidget(self.simplify_checkbox)
        self.settings_widgets["simplify_logs"] = self.simplify_checkbox

        # Show FID Values checkbox
        self.show_fid_checkbox = QCheckBox("Show FID Values")
        self.show_fid_checkbox.setToolTip("Look up FormID names during scan (slower but more informative)")
        scanning_layout.addWidget(self.show_fid_checkbox)
        self.settings_widgets["show_fid_values"] = self.show_fid_checkbox

        # Move Invalid Logs checkbox
        self.move_invalid_checkbox = QCheckBox("Move Invalid Logs")
        self.move_invalid_checkbox.setToolTip("Automatically move incomplete or unscannable logs to a separate folder")
        scanning_layout.addWidget(self.move_invalid_checkbox)
        self.settings_widgets["move_invalid_logs"] = self.move_invalid_checkbox

        layout.addWidget(scanning_group)
        layout.addStretch()

        # Add tab to widget
        self.tab_widget.addTab(scanning_widget, "Scanning")

    def _create_paths_tab(self) -> None:
        """Create the Paths settings tab."""
        paths_widget = QWidget()
        layout = QVBoxLayout(paths_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create paths settings group
        paths_group = QGroupBox("Path Settings")
        paths_layout = QVBoxLayout(paths_group)
        paths_layout.setSpacing(15)

        # INI Folder Path setting
        ini_path_label = QLabel("INI Folder Path:")
        ini_path_label.setToolTip("Path to your game's INI files directory\nUsually located in Documents/My Games/[Game Name]")
        paths_layout.addWidget(ini_path_label)

        # Create horizontal layout for input and browse button
        ini_path_layout = QHBoxLayout()
        ini_path_layout.setSpacing(10)

        self.ini_folder_input = QLineEdit()
        self.ini_folder_input.setPlaceholderText("Enter INI folder path or click Browse...")
        self.ini_folder_input.setToolTip(
            "Specify the folder containing your game's INI configuration files\nLeave empty to use automatic detection"
        )
        ini_path_layout.addWidget(self.ini_folder_input)
        self.settings_widgets["ini_folder_path"] = self.ini_folder_input

        # Reset button for INI folder
        self.ini_reset_button = QPushButton("Reset")
        self.ini_reset_button.setToolTip("Reset to auto-detected INI folder location")
        self.ini_reset_button.setMaximumWidth(80)
        self.ini_reset_button.clicked.connect(self._reset_ini_folder)
        ini_path_layout.addWidget(self.ini_reset_button)

        # Browse button for INI folder
        self.ini_browse_button = QPushButton("Browse...")
        self.ini_browse_button.setToolTip("Browse for INI folder location")
        self.ini_browse_button.setMaximumWidth(100)
        self.ini_browse_button.clicked.connect(self._browse_ini_folder)
        ini_path_layout.addWidget(self.ini_browse_button)

        paths_layout.addLayout(ini_path_layout)

        # Help text
        help_label = QLabel(
            "If CLASSIC has trouble detecting your game files, specify the INI folder manually.\n"
            "This is typically found in your Documents folder under 'My Games'."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("QLabel { color: #888888; font-size: 11px; }")
        paths_layout.addWidget(help_label)

        layout.addWidget(paths_group)
        layout.addStretch()

        # Add tab to widget
        self.tab_widget.addTab(paths_widget, "Paths")

    def _browse_ini_folder(self) -> None:
        """Open a folder browser dialog for selecting the INI folder."""
        from ClassicLib import GlobalRegistry

        try:
            game = GlobalRegistry.get_game()
        except (TypeError, ValueError, AttributeError):
            game = "Game"

        folder = QFileDialog.getExistingDirectory(
            self, f"Select INI Folder for {game}", self.ini_folder_input.text() or "", QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self.ini_folder_input.setText(folder)

    def _reset_ini_folder(self) -> None:
        """Reset the INI folder path to auto-detected value."""
        from ClassicLib import GlobalRegistry
        from ClassicLib.Logger import logger

        try:
            # Clear the INI Folder Path setting in CLASSIC Settings.yaml
            yaml_settings(str, self.yaml_store, f"CLASSIC_Settings.{self.SETTINGS_MAP['ini_folder_path']}", "")
            logger.info("Cleared INI Folder Path setting for autodetection")

            # Clear the Root_Folder_Docs in Game_Local YAML to trigger fresh detection
            vr_suffix = GlobalRegistry.get_vr()
            root_docs_key = f"Game{vr_suffix}_Info.Root_Folder_Docs"
            yaml_settings(str, YAML.Game_Local, root_docs_key, "")
            logger.info("Cleared Root_Folder_Docs for fresh autodetection")

            # Run the autodetection
            self._autodetect_ini_folder()

        except (ImportError, TypeError, ValueError, OSError) as e:
            logger.error(f"Failed to reset INI folder path: {e}")
            # Show error to user
            msg_error(f"Failed to reset INI folder path: {e!s}\n\nPlease try again or set the path manually.")

    def _autodetect_ini_folder(self) -> None:
        """Trigger autodetection of the INI folder path and update the UI."""
        from ClassicLib import GlobalRegistry
        from ClassicLib.DocsPath import docs_path_find
        from ClassicLib.Logger import logger

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

    def _create_updates_tab(self) -> None:
        """Create the Updates settings tab."""
        updates_widget = QWidget()
        layout = QVBoxLayout(updates_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Create update settings group
        updates_group = QGroupBox("Update Settings")
        updates_layout = QVBoxLayout(updates_group)
        updates_layout.setSpacing(15)

        # Update Check checkbox
        self.update_check_checkbox = QCheckBox("Check for Updates")
        self.update_check_checkbox.setToolTip("Automatically check for CLASSIC updates on startup")
        updates_layout.addWidget(self.update_check_checkbox)
        self.settings_widgets["update_check"] = self.update_check_checkbox

        # Update Source selection
        source_layout = QHBoxLayout()
        source_layout.setSpacing(10)

        source_label = QLabel("Update Source:")
        source_label.setToolTip("Choose where to check for updates")
        source_layout.addWidget(source_label)

        self.update_source_combo = QComboBox()
        self.update_source_combo.addItems(["Nexus", "GitHub", "Both"])
        self.update_source_combo.setToolTip(
            "Select which source to check for updates:\n"
            "• Nexus - Check Nexus Mods for updates\n"
            "• GitHub - Check GitHub releases for updates\n"
            "• Both - Check both sources"
        )
        source_layout.addWidget(self.update_source_combo)
        source_layout.addStretch()

        updates_layout.addLayout(source_layout)
        self.settings_widgets["update_source"] = self.update_source_combo

        # Check Now button
        self.check_now_button = QPushButton("Check for Updates Now")
        self.check_now_button.setToolTip("Immediately check for available updates")
        self.check_now_button.setMaximumWidth(200)
        updates_layout.addWidget(self.check_now_button)

        layout.addWidget(updates_group)
        layout.addStretch()

        # Add tab to widget
        self.tab_widget.addTab(updates_widget, "Updates")

    def load_settings(self) -> None:
        """
        Load current settings from YAML configuration.

        Reads settings from CLASSIC Settings.yaml and updates the UI widgets
        to reflect the current configuration values.
        """
        from ClassicLib.YamlSettingsCache import yaml_cache, yaml_settings

        # Prepare batch requests for all settings
        requests = []
        widget_info = []  # Store widget info to match with results

        for widget_key, yaml_key in self.SETTINGS_MAP.items():
            widget = self.settings_widgets.get(widget_key)
            if not widget:
                continue

            widget_info.append((widget_key, widget))

            # Determine the type and create request
            if isinstance(widget, QCheckBox):
                if self.yaml_store == YAML.Settings:
                    requests.append((bool, YAML.Settings, f"CLASSIC_Settings.{yaml_key}"))
                else:
                    requests.append((bool, self.yaml_store, f"CLASSIC_Settings.{yaml_key}"))
            elif isinstance(widget, QComboBox | QLineEdit):
                if self.yaml_store == YAML.Settings:
                    requests.append((str, YAML.Settings, f"CLASSIC_Settings.{yaml_key}"))
                else:
                    requests.append((str, self.yaml_store, f"CLASSIC_Settings.{yaml_key}"))

        # Batch load all settings at once
        if requests:
            values = yaml_cache.batch_get_settings(requests)

            # Apply loaded values to widgets
            for (widget_key, widget), value, _request in zip(widget_info, values, requests, strict=False):
                yaml_key = self.SETTINGS_MAP[widget_key]

                if isinstance(widget, QCheckBox):
                    if value is None:
                        # Set default value if not found
                        value = False
                        yaml_settings(bool, self.yaml_store, f"CLASSIC_Settings.{yaml_key}", False)
                    widget.setChecked(value)

                elif isinstance(widget, QComboBox):
                    if value is None:
                        # Set default value if not found
                        value = "Both"
                        yaml_settings(str, self.yaml_store, f"CLASSIC_Settings.{yaml_key}", "Both")
                    # Find and set the matching item in the combo box
                    index = widget.findText(value)
                    if index >= 0:
                        widget.setCurrentIndex(index)

                elif isinstance(widget, QLineEdit):
                    if value is None:
                        value = ""
                    widget.setText(value)

    def save_settings(self) -> None:
        """
        Save current settings to YAML configuration.

        Writes the current UI widget values back to CLASSIC Settings.yaml
        for persistence across application sessions.
        """
        ini_path_changed = False
        old_ini_path = None
        new_ini_path = None

        for widget_key, yaml_key in self.SETTINGS_MAP.items():
            widget = self.settings_widgets.get(widget_key)
            if not widget:
                continue

            # Save the widget value to YAML
            if isinstance(widget, QCheckBox):
                # Save checkbox state
                value = widget.isChecked()
                yaml_settings(bool, self.yaml_store, f"CLASSIC_Settings.{yaml_key}", value)

            elif isinstance(widget, QComboBox):
                # Save combo box selection
                value = widget.currentText()
                yaml_settings(str, self.yaml_store, f"CLASSIC_Settings.{yaml_key}", value)

            elif isinstance(widget, QLineEdit):
                # Save text input value
                value = widget.text()

                # Check if this is the INI Folder Path and if it changed
                if widget_key == "ini_folder_path":
                    # Get the old value to compare
                    if self.yaml_store == YAML.Settings:
                        old_ini_path = classic_settings(str, yaml_key)
                    else:
                        old_ini_path = yaml_settings(str, self.yaml_store, f"CLASSIC_Settings.{yaml_key}")

                    new_ini_path = value.strip()
                    ini_path_changed = (old_ini_path or "") != new_ini_path

                yaml_settings(str, self.yaml_store, f"CLASSIC_Settings.{yaml_key}", value)

        # If INI Folder Path changed, recalculate derivative paths
        if ini_path_changed:
            self._recalculate_derivative_paths(new_ini_path)

    def _recalculate_derivative_paths(self, new_ini_path: str) -> None:
        """
        Recalculate derivative paths when INI Folder Path changes.

        Updates Root_Folder_Docs in Game_Local YAML and regenerates all
        Docs_Folder_* and Docs_File_* paths that depend on it.

        Args:
            new_ini_path: The new INI folder path
        """
        try:
            from ClassicLib import GlobalRegistry
            from ClassicLib.DocsPath import docs_generate_paths
            from ClassicLib.Logger import logger

            # Check if we have a valid game context
            try:
                game = GlobalRegistry.get_game()
                if not game:
                    logger.warning("Cannot recalculate derivative paths: No game configured")
                    return
            except (TypeError, ValueError, AttributeError):
                logger.warning("Cannot recalculate derivative paths: Unable to get game context")
                return

            # Update Root_Folder_Docs in Game_Local YAML
            vr_suffix = GlobalRegistry.get_vr()  # Returns "_VR" or empty string
            root_docs_key = f"Game{vr_suffix}_Info.Root_Folder_Docs"

            if new_ini_path:
                # Set the new path
                yaml_settings(str, YAML.Game_Local, root_docs_key, new_ini_path)
                logger.info(f"Updated Root_Folder_Docs to: {new_ini_path}")
            else:
                # Clear the path to trigger auto-detection
                yaml_settings(str, YAML.Game_Local, root_docs_key, "")
                logger.info("Cleared Root_Folder_Docs - will use auto-detection")

            # Regenerate all derivative paths
            docs_generate_paths()
            logger.info("Recalculated all derivative document paths")

        except (ImportError, TypeError, ValueError, OSError) as e:
            # Log the error but don't crash the settings dialog
            try:
                from ClassicLib.Logger import logger

                logger.error(f"Failed to recalculate derivative paths: {e}")
            except ImportError:
                # If logger import fails, just continue silently
                pass

    def accept(self) -> None:
        """Handle dialog acceptance (OK button)."""
        self.save_settings()
        super().accept()

    def reject(self) -> None:
        """Handle dialog rejection (Cancel button)."""
        super().reject()
