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
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ClassicLib.Constants import YAML
from ClassicLib.Interface.StyleSheets import DARK_MODE
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
        for widget_key, yaml_key in self.SETTINGS_MAP.items():
            widget = self.settings_widgets.get(widget_key)
            if not widget:
                continue

            # Read the setting value from YAML
            if isinstance(widget, QCheckBox):
                # Handle checkbox settings
                if self.yaml_store == YAML.Settings:
                    value = classic_settings(bool, yaml_key)
                else:
                    value = yaml_settings(bool, self.yaml_store, f"CLASSIC_Settings.{yaml_key}")
                if value is None:
                    # Set default value if not found
                    value = False
                    yaml_settings(bool, self.yaml_store, f"CLASSIC_Settings.{yaml_key}", False)
                widget.setChecked(value)

            elif isinstance(widget, QComboBox):
                # Handle combo box settings
                if self.yaml_store == YAML.Settings:
                    value = classic_settings(str, yaml_key)
                else:
                    value = yaml_settings(str, self.yaml_store, f"CLASSIC_Settings.{yaml_key}")
                if value is None:
                    # Set default value if not found
                    value = "Both"
                    yaml_settings(str, self.yaml_store, f"CLASSIC_Settings.{yaml_key}", "Both")
                # Find and set the matching item in the combo box
                index = widget.findText(value)
                if index >= 0:
                    widget.setCurrentIndex(index)

    def save_settings(self) -> None:
        """
        Save current settings to YAML configuration.

        Writes the current UI widget values back to CLASSIC Settings.yaml
        for persistence across application sessions.
        """
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

    def accept(self) -> None:
        """Handle dialog acceptance (OK button)."""
        self.save_settings()
        super().accept()

    def reject(self) -> None:
        """Handle dialog rejection (Cancel button)."""
        super().reject()
