"""
Tab creation methods for CLASSIC settings dialog.

This module contains factory methods for creating the various settings tabs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from ClassicLib.Interface.Settings.path_manager import PathManager


class TabCreator:
    """Factory class for creating settings dialog tabs."""

    @staticmethod
    def create_general_tab(parent: QWidget) -> tuple[QWidget, dict[str, QWidget]]:
        """
        Create the General settings tab.

        Returns:
            Tuple of (tab widget, settings widgets dict)
        """
        general_widget = QWidget()
        layout = QVBoxLayout(general_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        settings_widgets = {}

        # Create general settings group
        general_group = QGroupBox("General Settings")
        general_layout = QVBoxLayout(general_group)
        general_layout.setSpacing(10)

        # Audio Notifications checkbox
        audio_checkbox = QCheckBox("Audio Notifications")
        audio_checkbox.setToolTip("Play sound effects when scans complete or errors occur")
        general_layout.addWidget(audio_checkbox)
        settings_widgets["audio_notifications"] = audio_checkbox

        # VR Mode checkbox
        vr_checkbox = QCheckBox("VR Mode")
        vr_checkbox.setToolTip("Prioritize settings and checks for VR version of the game")
        general_layout.addWidget(vr_checkbox)
        settings_widgets["vr_mode"] = vr_checkbox

        layout.addWidget(general_group)
        layout.addStretch()

        return general_widget, settings_widgets

    @staticmethod
    def create_scanning_tab(parent: QWidget) -> tuple[QWidget, dict[str, QWidget]]:
        """
        Create the Scanning settings tab.

        Returns:
            Tuple of (tab widget, settings widgets dict)
        """
        scanning_widget = QWidget()
        layout = QVBoxLayout(scanning_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        settings_widgets = {}

        # Create scanning settings group
        scanning_group = QGroupBox("Scanning Options")
        scanning_layout = QVBoxLayout(scanning_group)
        scanning_layout.setSpacing(10)

        # FCX Mode checkbox
        fcx_checkbox = QCheckBox("FCX Mode")
        fcx_checkbox.setToolTip("Enable extended file integrity checks for more thorough scanning")
        scanning_layout.addWidget(fcx_checkbox)
        settings_widgets["fcx_mode"] = fcx_checkbox

        # Simplify Logs checkbox
        simplify_checkbox = QCheckBox("Simplify Logs")
        simplify_checkbox.setToolTip("Remove redundant and repetitive lines from crash logs for easier reading")
        scanning_layout.addWidget(simplify_checkbox)
        settings_widgets["simplify_logs"] = simplify_checkbox

        # Show FID Values checkbox
        show_fid_checkbox = QCheckBox("Show FID Values")
        show_fid_checkbox.setToolTip("Look up FormID names during scan (slower but more informative)")
        scanning_layout.addWidget(show_fid_checkbox)
        settings_widgets["show_fid_values"] = show_fid_checkbox

        # Move Invalid Logs checkbox
        move_invalid_checkbox = QCheckBox("Move Invalid Logs")
        move_invalid_checkbox.setToolTip("Automatically move incomplete or unscannable logs to a separate folder")
        scanning_layout.addWidget(move_invalid_checkbox)
        settings_widgets["move_invalid_logs"] = move_invalid_checkbox

        layout.addWidget(scanning_group)
        layout.addStretch()

        return scanning_widget, settings_widgets

    @staticmethod
    def create_paths_tab(parent: QWidget, path_manager: PathManager) -> tuple[QWidget, dict[str, QWidget]]:
        """
        Create the Paths settings tab.

        Args:
            parent: Parent widget
            path_manager: PathManager instance for handling path operations

        Returns:
            Tuple of (tab widget, settings widgets dict)
        """
        paths_widget = QWidget()
        layout = QVBoxLayout(paths_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        settings_widgets = {}

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

        ini_folder_input = QLineEdit()
        ini_folder_input.setPlaceholderText("Enter INI folder path or click Browse...")
        ini_folder_input.setToolTip(
            "Specify the folder containing your game's INI configuration files\nLeave empty to use automatic detection"
        )
        ini_path_layout.addWidget(ini_folder_input)
        settings_widgets["ini_folder_path"] = ini_folder_input

        # Set the input widget reference in path manager
        path_manager.set_ini_folder_input(ini_folder_input)

        # Reset button for INI folder
        ini_reset_button = QPushButton("Reset")
        ini_reset_button.setToolTip("Reset to auto-detected INI folder location")
        ini_reset_button.setMaximumWidth(80)
        ini_reset_button.clicked.connect(path_manager.reset_ini_folder)
        ini_path_layout.addWidget(ini_reset_button)

        # Browse button for INI folder
        ini_browse_button = QPushButton("Browse...")
        ini_browse_button.setToolTip("Browse for INI folder location")
        ini_browse_button.setMaximumWidth(100)
        ini_browse_button.clicked.connect(path_manager.browse_ini_folder)
        ini_path_layout.addWidget(ini_browse_button)

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

        return paths_widget, settings_widgets

    @staticmethod
    def create_updates_tab(parent: QWidget) -> tuple[QWidget, dict[str, QWidget]]:
        """
        Create the Updates settings tab.

        Returns:
            Tuple of (tab widget, settings widgets dict, check_now_button)
        """
        updates_widget = QWidget()
        layout = QVBoxLayout(updates_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        settings_widgets = {}

        # Create update settings group
        updates_group = QGroupBox("Update Settings")
        updates_layout = QVBoxLayout(updates_group)
        updates_layout.setSpacing(15)

        # Update Check checkbox
        update_check_checkbox = QCheckBox("Check for Updates")
        update_check_checkbox.setToolTip("Automatically check for CLASSIC updates on startup")
        updates_layout.addWidget(update_check_checkbox)
        settings_widgets["update_check"] = update_check_checkbox

        # Update Source selection
        source_layout = QHBoxLayout()
        source_layout.setSpacing(10)

        source_label = QLabel("Update Source:")
        source_label.setToolTip("Choose where to check for updates")
        source_layout.addWidget(source_label)

        update_source_combo = QComboBox()
        update_source_combo.addItems(["Nexus", "GitHub", "Both"])
        update_source_combo.setToolTip(
            "Select which source to check for updates:\n"
            "• Nexus - Check Nexus Mods for updates\n"
            "• GitHub - Check GitHub releases for updates\n"
            "• Both - Check both sources"
        )
        source_layout.addWidget(update_source_combo)
        source_layout.addStretch()

        updates_layout.addLayout(source_layout)
        settings_widgets["update_source"] = update_source_combo

        # Check Now button
        check_now_button = QPushButton("Check for Updates Now")
        check_now_button.setToolTip("Immediately check for available updates")
        check_now_button.setMaximumWidth(200)
        updates_layout.addWidget(check_now_button)

        layout.addWidget(updates_group)
        layout.addStretch()

        # Return the button separately so it can be connected in the main dialog
        return updates_widget, settings_widgets, check_now_button
