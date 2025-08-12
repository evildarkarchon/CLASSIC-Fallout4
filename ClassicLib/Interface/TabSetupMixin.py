"""
Tab widgets and setup functionality for the CLASSIC interface.

This module contains mixin classes that handle the setup of different tabs
in the main window interface.
"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Literal

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from ClassicLib.Constants import YAML
from ClassicLib.Interface.UIHelpers import (
    BOTTOM_BUTTON_STYLE,
    CHECKBOX_STYLE,
    add_main_button,
    create_checkbox,
    create_separator,
    setup_folder_section,
)
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtWidgets import QButtonGroup, QLineEdit, QWidget


class TabSetupMixin:
    """
    Mixin class providing tab setup functionality for the MainWindow.

    This class contains methods for setting up the main tab, articles tab,
    and backups tab in the application interface.
    """

    # Type stubs for attributes that must be provided by the mixing class
    if TYPE_CHECKING:
        main_tab: QWidget
        articles_tab: QWidget
        backups_tab: QWidget
        mods_folder_edit: QLineEdit | None
        scan_folder_edit: QLineEdit | None
        scan_button_group: QButtonGroup
        crash_logs_button: QPushButton | None
        game_files_button: QPushButton | None
        papyrus_button: QPushButton | None

        # Required methods that must be implemented by the mixing class
        def select_folder_mods(self) -> None: ...
        def select_folder_scan(self) -> None: ...
        def select_folder_ini(self) -> None: ...
        def validate_scan_folder_text(self) -> None: ...
        @staticmethod
        def open_url(url: str) -> None: ...
        def show_about(self) -> None: ...
        def help_popup_main(self) -> None: ...
        def open_settings(self) -> None: ...
        def open_crash_logs_folder(self) -> None: ...
        def update_popup_explicit(self) -> None: ...
        def toggle_papyrus_worker(self) -> None: ...
        def update_papyrus_button_style(self, monitoring: bool) -> None: ...
        def crash_logs_scan(self) -> None: ...
        def game_files_scan(self) -> None: ...
        def open_backup_folder(self) -> None: ...
        def check_existing_backups(self) -> None: ...
        def create_checkbox(self, label_text: str, setting: str) -> QCheckBox: ...
        def add_main_button(self, layout: QLayout, text: str, callback: Callable[[], None], tooltip: str = "") -> QPushButton: ...
        def _create_button(self, text: str, tooltip: str, callback: Callable) -> QPushButton: ...
        def add_backup_section(self, layout: QBoxLayout, title: str, backup_type: Literal["XSE", "RESHADE", "VULKAN", "ENB"]) -> None: ...

    # noinspection PyUnresolvedReferences
    def setup_main_tab(self) -> None:
        """Sets up the main UI elements for the main tab.

        This method initializes and organizes various UI components on the main tab, including
        folder selection sections, buttons, checkboxes, articles, and output sections. The layout
        is configured with specific margins, spacing, and separator widgets to provide a structured
        and user-friendly interface.

        Attributes:
            mods_folder_edit (QWidget): The input widget for the staging mods folder selection.
            scan_folder_edit (QWidget): The input widget for the custom scan folder selection.
            output_text_box (QWidget or None): The widget for the output text box, if initialized.

        Returns:
            None
        """
        layout: QVBoxLayout = QVBoxLayout(self.main_tab)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        # Top section
        self.mods_folder_edit = setup_folder_section(
            layout,
            "STAGING MODS FOLDER",
            "Box_SelectedMods",
            self.select_folder_mods,
            tooltip="Select the folder where your mod manager (e.g., MO2) stages your mods.",
        )
        if self.mods_folder_edit:  # Check if it was created
            self.mods_folder_edit.setPlaceholderText("Optional: Select your mod staging folder (e.g., MO2/mods)")
            self.mods_folder_edit.setToolTip("Select the folder where your mod manager (e.g., MO2) stages your mods.")

        self.scan_folder_edit = setup_folder_section(
            layout,
            "CUSTOM SCAN FOLDER",
            "Box_SelectedScan",
            self.select_folder_scan,
            tooltip="Select a supplementary custom folder containing crash logs to scan. The game directory is always used for scanning.",
        )
        if self.scan_folder_edit:  # Check if it was created
            self.scan_folder_edit.setPlaceholderText("Optional: Select a supplementary custom folder with crash logs")
            self.scan_folder_edit.setToolTip(
                "Select a supplementary custom folder containing crash logs to scan. The game directory is always used for scanning."
            )
            # Connect signal to validate when user finishes editing the text
            self.scan_folder_edit.editingFinished.connect(self.validate_scan_folder_text)

        # self.setup_pastebin_elements(layout)  # Re-enabled Pastebin elements

        layout.addWidget(create_separator())
        self.setup_main_buttons(layout)
        # layout.addWidget(create_separator())
        self.setup_checkboxes(layout)
        layout.addWidget(create_separator())
        self.setup_bottom_buttons(layout)

    def setup_articles_tab(self) -> None:
        """Sets up the UI elements for the articles tab.
        Creates a layout for the articles tab with a title label and a grid of buttons.
        Each button is linked to a useful resource or website related to Fallout 4 modding
        and tools. The buttons are arranged in a 3-column grid layout and styled with
        a consistent dark theme.
        The resources include:
        - Buffout 4 installation guide
        - Fallout 4 setup tips
        - Important patches list
        - Links to relevant Nexus Mods pages
        - GitHub repository link
        - Various modding tools
        Each button, when clicked, will open the associated URL in the user's default web browser.
        Returns:
            None
        """
        layout: QVBoxLayout = QVBoxLayout(self.articles_tab)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        # Add a title label
        title_label: QLabel = QLabel("USEFUL RESOURCES & LINKS")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        layout.addWidget(title_label)

        # Create a grid layout for the buttons
        grid_layout: QGridLayout = QGridLayout()
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(10)

        # Define the article buttons data
        button_data: list[dict[str, str]] = [
            {"text": "BUFFOUT 4 INSTALLATION", "url": "https://www.nexusmods.com/fallout4/articles/3115"},
            {"text": "FALLOUT 4 SETUP TIPS", "url": "https://www.nexusmods.com/fallout4/articles/4141"},
            {"text": "IMPORTANT PATCHES LIST", "url": "https://www.nexusmods.com/fallout4/articles/3769"},
            {"text": "BUFFOUT 4 NEXUS", "url": "https://www.nexusmods.com/fallout4/mods/47359"},
            {"text": "CLASSIC NEXUS", "url": "https://www.nexusmods.com/fallout4/mods/56255"},
            {"text": "CLASSIC GITHUB", "url": "https://github.com/evildarkarchon/CLASSIC-Fallout4"},
            {"text": "DDS TEXTURE SCANNER", "url": "https://www.nexusmods.com/fallout4/mods/71588"},
            {"text": "BETHINI PIE", "url": "https://www.nexusmods.com/site/mods/631"},
            {"text": "WRYE BASH", "url": "https://www.nexusmods.com/fallout4/mods/20032"},
        ]

        # Define button style
        button_style = """
            QPushButton {
                color: white;
                background-color: rgba(60, 60, 60, 0.9);
                border: 1px solid #5c5c5c;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
                min-height: 40px;
            }
            QPushButton:hover { background-color: rgba(80, 80, 80, 0.9); }
            QPushButton:disabled { color: gray; background-color: rgba(45, 45, 45, 0.75); }
        """

        # Create buttons and connect to URLs
        for i, data in enumerate(button_data):
            button: QPushButton = QPushButton(data["text"])
            button.setStyleSheet(button_style)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setToolTip(f"Open {data['url']} in your browser.")

            # Fix: Use functools.partial instead of lambda to properly capture the URL
            button.clicked.connect(partial(self.open_url, data["url"]))

            row, col = divmod(i, 3)  # Arrange in 3 columns
            grid_layout.addWidget(button, row, col)

        layout.addLayout(grid_layout)
        layout.addStretch(1)  # Push content to the top

    def setup_backups_tab(self) -> None:
        """
        Configures the user interface layout and behavior for the "Backups" tab. This includes
        adding explanatory labels, dynamically created category buttons for managing backups,
        and additional functionality such as enabling/disabling restore buttons based on the
        existence of backups. The tab provides capabilities to backup, restore, and remove files
        related to specific categories such as XSE, RESHADE, VULKAN, and ENB.

        Returns:
            None
        """
        layout: QVBoxLayout = QVBoxLayout(self.backups_tab)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        layout.addWidget(QLabel("BACKUP > Backup files from the game folder into the CLASSIC Backup folder."))
        layout.addWidget(QLabel("RESTORE > Restore file backup from the CLASSIC Backup folder into the game folder."))
        layout.addWidget(QLabel("REMOVE > Remove files only from the game folder without removing existing backups."))

        categories: list[str] = ["XSE", "RESHADE", "VULKAN", "ENB"]
        for category in categories:
            self.add_backup_section(layout, category, category)  # type: ignore

        layout.addStretch(1)  # Push content to the top

        bottom_layout: QHBoxLayout = QHBoxLayout()
        open_backups_button: QPushButton = QPushButton("OPEN CLASSIC BACKUPS")
        open_backups_button.clicked.connect(self.open_backup_folder)
        bottom_layout.addWidget(open_backups_button)
        bottom_layout.addStretch(1)  # Keep button to the left
        layout.addLayout(bottom_layout)

        self.check_existing_backups()

    def setup_checkboxes(self, layout: QBoxLayout) -> None:
        """
        Initializes and configures the checkbox and drop-down sections within the given layout for
        user interface settings. This involves creating a group of checkboxes for various settings
        and a combo box for selecting the update source. Checkbox settings are arranged in a grid
        layout, and the combo box is included below the checkboxes with proper spacing and alignment.

        Args:
            layout (QBoxLayout): The parent layout to which the checkbox section, update source
                section, and separator will be added.
        """
        checkbox_section_layout: QVBoxLayout = QVBoxLayout()  # Main layout for this section

        title_label: QLabel = QLabel("CLASSIC SETTINGS")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        checkbox_section_layout.addWidget(title_label)

        grid_layout: QGridLayout = QGridLayout()
        grid_layout.setHorizontalSpacing(20)
        grid_layout.setVerticalSpacing(10)

        checkboxes: list[tuple[str, str, str]] = [
            ("FCX MODE", "FCX Mode", "Enable extended file integrity checks."),
            ("SIMPLIFY LOGS", "Simplify Logs", "Remove redundant lines from crash logs."),
            ("UPDATE CHECK", "Update Check", "Automatically check for CLASSIC updates."),
            ("VR MODE", "VR Mode", "Prioritize settings for VR version of the game."),
            ("SHOW FID VALUES", "Show FormID Values", "Look up FormID names (slower scans)."),
            ("MOVE INVALID LOGS", "Move Unsolved Logs", "Move incomplete/unscannable logs to a separate folder."),
            ("AUDIO NOTIFICATIONS", "Audio Notifications", "Play sounds for scan completion/errors."),
        ]

        for index, (label, setting, tooltip) in enumerate(checkboxes):
            checkbox: QCheckBox = self.create_checkbox(label, setting)
            checkbox.setToolTip(tooltip)
            row: int = index // 2  # Arrange in 2 columns
            col: int = index % 2
            grid_layout.addWidget(checkbox, row, col, Qt.AlignmentFlag.AlignLeft)

        checkbox_section_layout.addLayout(grid_layout)
        checkbox_section_layout.addSpacing(15)  # Space before update source

        # Update Source ComboBox
        update_source_hbox: QHBoxLayout = QHBoxLayout()
        update_source_label: QLabel = QLabel("Update Source:")
        update_source_combo: QComboBox = QComboBox()
        update_sources: tuple[str, str, str] = ("Nexus", "GitHub", "Both")
        update_source_combo.addItems(update_sources)

        # Set the combo box to the saved setting
        saved_source: str | None = classic_settings(str, "Update Source")
        if saved_source and saved_source in update_sources:
            update_source_combo.setCurrentText(saved_source)
        else:
            # Default to "Both" if no saved setting
            update_source_combo.setCurrentText("Both")
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.Update Source", "Both")

        # Connect the combo box change signal to save the setting
        update_source_combo.currentTextChanged.connect(
            lambda text: yaml_settings(str, YAML.Settings, "CLASSIC_Settings.Update Source", text)
        )

        update_source_hbox.addWidget(update_source_label)
        update_source_hbox.addWidget(update_source_combo)
        update_source_hbox.addStretch(1)  # Push to the left

        checkbox_section_layout.addLayout(update_source_hbox)

        # Add the entire checkbox section to the parent layout
        if isinstance(layout, QVBoxLayout | QHBoxLayout):
            layout.addLayout(checkbox_section_layout)

        # Separator is added after this section in setup_main_tab

    def setup_main_buttons(self, layout: QBoxLayout) -> None:
        """
        Sets up the main buttons and bottom row buttons within the provided layout.
        This method initializes the layout for two groups of buttons: main action buttons
        and bottom row buttons. It organizes them in horizontal layouts, with spacing configured
        as specified. Main buttons include "SCAN CRASH LOGS" and "SCAN GAME FILES," which are
        added to the scan button group. Bottom row buttons feature options such as "CHANGE INI PATH,"
        "OPEN CLASSIC SETTINGS," and "CHECK UPDATES."

        Args:
            layout: QBoxLayout instance where the main buttons and bottom row buttons
                are to be arranged and added.
        """
        main_buttons_layout: QHBoxLayout = QHBoxLayout()
        main_buttons_layout.setSpacing(10)
        self.crash_logs_button = self.add_main_button(
            main_buttons_layout, "SCAN CRASH LOGS", self.crash_logs_scan, "Scan all detected crash logs for issues."
        )
        if self.crash_logs_button:
            self.scan_button_group.addButton(self.crash_logs_button)

        self.game_files_button = self.add_main_button(
            main_buttons_layout,
            "SCAN GAME FILES",
            self.game_files_scan,
            "Scan game and mod files for potential problems (FCX Mode dependent).",
        )
        if self.game_files_button:
            self.scan_button_group.addButton(self.game_files_button)

        if isinstance(layout, QVBoxLayout | QHBoxLayout):  # Ensure layout supports addLayout
            layout.addLayout(main_buttons_layout)

    @staticmethod
    def setup_articles_section(layout: QBoxLayout) -> None:
        """
        Sets up an "Articles/Links" section in the specified layout with a descriptive
        title label, and populates it with buttons directing users to various helpful
        resources. Each button links to a specific external resource or webpage.

        This method creates a layout containing a title label aligned at the center,
        followed by a grid of buttons arranged in rows and columns. Each button is
        styled uniformly and can open a corresponding URL when clicked. After arranging
        the buttons, additional vertical spacing is added to visually separate the
        articles section from other content in the layout.

        Args:
            layout (QBoxLayout): The parent layout where the articles section will be
                added.
        """
        articles_section_layout: QVBoxLayout = QVBoxLayout()  # Main layout for this section
        articles_section_layout.setSpacing(10)

        title_label: QLabel = QLabel("USEFUL RESOURCES & LINKS")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        articles_section_layout.addWidget(title_label)

        grid_layout: QGridLayout = QGridLayout()
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(10)

        button_data: list[dict[str, str]] = [
            {"text": "BUFFOUT 4 INSTALLATION", "url": "https://www.nexusmods.com/fallout4/articles/3115"},
            {"text": "FALLOUT 4 SETUP TIPS", "url": "https://www.nexusmods.com/fallout4/articles/4141"},
            {"text": "IMPORTANT PATCHES LIST", "url": "https://www.nexusmods.com/fallout4/articles/3769"},
            {"text": "BUFFOUT 4 NEXUS", "url": "https://www.nexusmods.com/fallout4/mods/47359"},
            {"text": "CLASSIC NEXUS", "url": "https://www.nexusmods.com/fallout4/mods/56255"},
            {"text": "CLASSIC GITHUB", "url": "https://github.com/evildarkarchon/CLASSIC-Fallout4"},  # Updated URL
            {"text": "DDS TEXTURE SCANNER", "url": "https://www.nexusmods.com/fallout4/mods/71588"},
            {"text": "BETHINI PIE", "url": "https://www.nexusmods.com/site/mods/631"},
            {"text": "WRYE BASH", "url": "https://www.nexusmods.com/fallout4/mods/20032"},
        ]

        button_style = """
            QPushButton {
                color: white;
                background-color: rgba(60, 60, 60, 0.9);
                border: 1px solid #5c5c5c;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px; /* Adjusted for potentially longer text */
                font-weight: bold;
                min-height: 40px; /* Ensure buttons are not too small */
            }
            QPushButton:hover { background-color: rgba(80, 80, 80, 0.9); }
            QPushButton:disabled { color: gray; background-color: rgba(45, 45, 45, 0.75); }
        """

        for i, data in enumerate(button_data):
            button: QPushButton = QPushButton(data["text"])
            button.setStyleSheet(button_style)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # Allow horizontal expansion
            button.setToolTip(f"Open {data['url']} in your browser.")
            button.clicked.connect(lambda url=data["url"]: QDesktopServices.openUrl(QUrl(url)))
            row, col = divmod(i, 3)  # Arrange in 3 columns
            grid_layout.addWidget(button, row, col)

        articles_section_layout.addLayout(grid_layout)
        if isinstance(layout, QVBoxLayout | QHBoxLayout):
            layout.addLayout(articles_section_layout)

    def setup_bottom_buttons(self, layout: QBoxLayout) -> None:
        """
        Configures and adds a set of bottom buttons to a given layout. The buttons include
        "ABOUT", "HELP", "START PAPYRUS MONITORING", and "EXIT", each of which performs
        specific actions when clicked. Each button is styled, and some include tooltips
        and specific behavioral properties such as being checkable.
        Args:
            layout (QBoxLayout): The main layout to which the bottom button layout will
                be added.
        """
        # First row of utility buttons
        bottom_buttons_hbox: QHBoxLayout = QHBoxLayout()
        bottom_buttons_hbox.setSpacing(10)

        # Create first row of buttons
        buttons_config: list[tuple[str, str, Callable]] = [
            ("ABOUT", "Show application information.", self.show_about),
            ("HELP", "Show help information for main options.", self.help_popup_main),
            ("CHANGE INI PATH", "Manually set the path to your game's INI files folder.", self.select_folder_ini),
            ("OPEN SETTINGS", "Open CLASSIC Settings.yaml file.", self.open_settings),
            ("OPEN CRASH LOGS", "Open the Crash Logs directory in your file explorer.", self.open_crash_logs_folder),
            ("CHECK UPDATES", "Manually check for CLASSIC updates.", self.update_popup_explicit),
        ]

        utility_buttons: list[QPushButton] = []
        for text, tooltip, callback in buttons_config:
            button: QPushButton = self._create_button(text, tooltip, callback)
            bottom_buttons_hbox.addWidget(button)
            utility_buttons.append(button)

        # Second row with main action buttons
        main_actions_hbox: QHBoxLayout = QHBoxLayout()
        main_actions_hbox.setSpacing(10)  # Papyrus monitoring button (special handling for checkable button)
        self.papyrus_button = self._create_button(
            "START PAPYRUS MONITORING", "Toggle Papyrus log monitoring. Shows statistics in a dedicated dialog.", self.toggle_papyrus_worker
        )
        self.papyrus_button.setCheckable(True)
        self.update_papyrus_button_style(False)  # Initial style for "START"
        main_actions_hbox.addWidget(self.papyrus_button, 1)  # Allow to expand

        # Exit button
        exit_button: QPushButton = self._create_button("EXIT", "Close CLASSIC.", QApplication.quit)
        main_actions_hbox.addWidget(exit_button)

        # Add both layouts to the main layout
        if isinstance(layout, QVBoxLayout | QHBoxLayout):
            layout.addLayout(bottom_buttons_hbox)
            layout.addLayout(main_actions_hbox)

    def _create_button(self, text: str, tooltip: str, callback: Callable) -> QPushButton:
        """
        Creates and configures a button with common styling and properties.

        Args:
            text: The button text
            tooltip: The button tooltip
            callback: Function to call when button is clicked

        Returns:
            Configured QPushButton instance
        """
        button: QPushButton = QPushButton(text)
        button.setToolTip(tooltip)

        # Connect appropriate signal based on whether it's a toggle button or regular
        if isinstance(button, QPushButton) and button.isCheckable():
            button.toggled.connect(callback)
        else:
            button.clicked.connect(callback)

        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setStyleSheet(BOTTOM_BUTTON_STYLE)

        return button

    def create_checkbox(self, label_text: str, setting: str) -> QCheckBox:
        """Wrapper for create_checkbox from UIHelpers."""
        return create_checkbox(label_text, setting, CHECKBOX_STYLE)

    def add_main_button(self, layout: QLayout, text: str, callback: Callable[[], None], tooltip: str = "") -> QPushButton:
        """Wrapper for add_main_button from UIHelpers."""
        return add_main_button(layout, text, callback, tooltip)
