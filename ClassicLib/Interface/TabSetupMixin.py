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
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ClassicLib.Interface.UIHelpers import (
    BOTTOM_BUTTON_STYLE,
    add_main_button,
    setup_folder_section,
    supports_add_layout,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtWidgets import QButtonGroup, QLineEdit


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
        results_tab: QWidget
        mods_folder_edit: QLineEdit | None
        scan_folder_edit: QLineEdit | None
        scan_button_group: QButtonGroup
        crash_logs_button: QPushButton | None
        game_files_button: QPushButton | None
        papyrus_button: QPushButton | None

        # Required methods that must be implemented by the mixing class
        def select_folder_mods(self) -> None: ...  # noqa: D102
        def select_folder_scan(self) -> None: ...  # noqa: D102
        def validate_scan_folder_text(self) -> None: ...  # noqa: D102
        @staticmethod
        def open_url(url: str) -> None: ...  # noqa: D102
        def show_about(self) -> None: ...  # noqa: D102
        def help_popup_main(self) -> None: ...  # noqa: D102
        def open_settings(self) -> None: ...  # noqa: D102
        def open_crash_logs_folder(self) -> None: ...  # noqa: D102
        def update_popup_explicit(self) -> None: ...  # noqa: D102
        def toggle_papyrus_worker(self) -> None: ...  # noqa: D102
        def update_papyrus_button_style(self, monitoring: bool) -> None: ...  # noqa: D102
        def crash_logs_scan(self) -> None: ...  # noqa: D102
        def game_files_scan(self) -> None: ...  # noqa: D102
        def open_backup_folder(self) -> None: ...  # noqa: D102
        def check_existing_backups(self) -> None: ...  # noqa: D102
        def add_main_button(self, layout: QLayout, text: str, callback: Callable[[], None], tooltip: str = "") -> QPushButton: ...  # noqa: D102
        def _create_button(self, text: str, tooltip: str, callback: Callable) -> QPushButton: ...
        def add_backup_section(self, layout: QBoxLayout, title: str, backup_type: Literal["XSE", "RESHADE", "VULKAN", "ENB"]) -> None: ...  # noqa: D102

    # noinspection PyUnresolvedReferences
    def setup_main_tab(self) -> None:
        """
        Configures the main tab layout for the application's graphical user interface.

        This method sets up the layout, header section for folder input widgets, and buttons within
        the main tab. It ensures the content is compact, aligned, and user-friendly by customizing
        spacing and margins. The function manages folder selection fields, validates user input,
        and organizes related user interface elements systematically.
        """
        layout: QVBoxLayout = QVBoxLayout(self.main_tab)
        layout.setContentsMargins(15, 5, 15, 10)  # Minimal top margin to sit close to tab bar
        layout.setSpacing(0)  # No default spacing - we'll add it manually where needed

        # Create a fixed header section for folder widgets
        header_widget = QWidget()
        header_widget.setMaximumHeight(100)  # Limit height to keep it compact
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        # Top section - folder selections grouped tightly together
        self.mods_folder_edit = setup_folder_section(
            header_layout,
            "STAGING MODS FOLDER",
            "Box_SelectedMods",
            self.select_folder_mods,
            tooltip="Select the folder where your mod manager (e.g., MO2) stages your mods.",
        )
        if self.mods_folder_edit:  # Check if it was created
            self.mods_folder_edit.setPlaceholderText("Optional: Select your mod staging folder (e.g., MO2/mods)")
            self.mods_folder_edit.setToolTip("Select the folder where your mod manager (e.g., MO2) stages your mods.")

        # No spacing between folder widgets - they'll be right on top of each other
        self.scan_folder_edit = setup_folder_section(
            header_layout,
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

        # Add the header widget to main layout
        # self.setup_pastebin_elements(header_layout)  # Re-enabled Pastebin elements
        layout.addWidget(header_widget)
        layout.addStretch()

        # Add spacing after folder sections before main buttons
        layout.addSpacing(5)
        self.setup_main_buttons(layout)
        layout.addStretch()
        layout.addSpacing(10)
        self.setup_bottom_buttons(layout)

        # Add stretch at the end to push everything up and keep folder widgets at top

    def update_papyrus_button_style(self, monitoring: bool) -> None:
        """
        Updates the style and text of the Papyrus button based on the monitoring state.

        This method adjusts the visual appearance and label of the Papyrus button
        to reflect whether monitoring is active or inactive. The button is styled
        in red for the "STOP" state and green for the "START" state.

        Args:
            monitoring (bool): A boolean indicating whether monitoring is active. If
                True, the button is styled as "STOP PAPYRUS MONITORING". If False,
                the button is styled as "START PAPYRUS MONITORING".
        """
        if not hasattr(self, "papyrus_button") or self.papyrus_button is None:
            return

        if monitoring:
            # Red style for "STOP" state
            self.papyrus_button.setText("STOP PAPYRUS MONITORING")
            self.papyrus_button.setStyleSheet(
                """
                QPushButton {
                    color: black;
                    background: rgb(237, 45, 45);  /* Red background */
                    border-radius: 10px;
                    border: 1px solid black;
                    font-weight: bold;
                    font-size: 14px;
                }
                """
            )
        else:
            # Green style for "START" state
            self.papyrus_button.setText("START PAPYRUS MONITORING")
            self.papyrus_button.setStyleSheet(
                """
                QPushButton {
                    color: black;
                    background: rgb(45, 237, 138);  /* Green background */
                    border-radius: 10px;
                    border: 1px solid black;
                    font-weight: bold;
                    font-size: 14px;
                }
                """
            )

    def setup_articles_tab(self) -> None:
        """
        Sets up the articles tab in the application's user interface by creating and styling a layout,
        adding a title label, dynamically generating clickable buttons (each linked to a URL), and
        organizing the buttons within a grid layout. The articles tab provides users with quick access
        to useful links and resources.

        Raises:
            Any exceptions that may occur during the creation or setup of UI components.
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
        Sets up the backups tab of the GUI by arranging layout, adding widget controls, and configuring interactions.

        This function initializes the backup tab by creating a vertical layout, adding informational labels, and dynamically
        creating sections for backup-related actions. It also includes a button to open the CLASSIC Backups folder
        and ensures existing backups are checked.
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
        self.crash_logs_button = add_main_button(
            main_buttons_layout, "SCAN CRASH LOGS", self.crash_logs_scan, "Scan all detected crash logs for issues."
        )
        if self.crash_logs_button:
            self.scan_button_group.addButton(self.crash_logs_button)

        self.game_files_button = add_main_button(
            main_buttons_layout,
            "SCAN GAME FILES",
            self.game_files_scan,
            "Scan game and mod files for potential problems (FCX Mode dependent).",
        )
        if self.game_files_button:
            self.scan_button_group.addButton(self.game_files_button)

        if supports_add_layout(layout):  # Ensure layout supports addLayout
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
        if supports_add_layout(layout):
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
        bottom_buttons_hbox.setContentsMargins(0, 0, 0, 0)  # Remove extra margins

        # Create first row of buttons
        buttons_config: list[tuple[str, str, Callable]] = [
            ("ABOUT", "Show application information.", self.show_about),
            ("HELP", "Show help information for main options.", self.help_popup_main),
            ("SETTINGS", "Open application settings dialog.", self.open_settings),
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
        main_actions_hbox.setSpacing(10)
        main_actions_hbox.setContentsMargins(0, 0, 0, 0)  # Remove extra margins

        # Papyrus monitoring button (special handling for checkable button)
        self.papyrus_button = self._create_button(
            "START PAPYRUS MONITORING", "Toggle Papyrus log monitoring. Shows statistics in a dedicated dialog.", self.toggle_papyrus_worker
        )
        self.papyrus_button.setCheckable(True)
        self.update_papyrus_button_style(False)  # Initial style for "START"
        main_actions_hbox.addWidget(self.papyrus_button, 1)  # Allow to expand

        # Exit button
        exit_button: QPushButton = self._create_button("EXIT", "Close CLASSIC.", QApplication.quit)
        main_actions_hbox.addWidget(exit_button)

        # Add both layouts to the main layout with minimal spacing
        if supports_add_layout(layout):
            layout.addLayout(bottom_buttons_hbox)
            layout.addSpacing(5)  # Small spacing between button rows
            layout.addLayout(main_actions_hbox)

    def _create_button(self, text: str, tooltip: str, callback: Callable) -> QPushButton:
        """
        Creates a QPushButton with the specified text, tooltip, and callback functionality.

        This function initializes a QPushButton, sets its tooltip, connects the provided
        callback to the appropriate signal based on the button type (toggle button or
        regular), and applies style and size policies.

        Args:
            text (str): The label text to display on the button.
            tooltip (str): The text to be shown as a tooltip when hovering over the button.
            callback (Callable): The function that will be connected to the button's signal.

        Returns:
            QPushButton: The configured button instance.
        """
        button: QPushButton = QPushButton(text)
        button.setToolTip(tooltip)

        # Connect appropriate signal based on whether it's a toggle button or regular
        # Use hasattr to avoid isinstance issues with mocked objects in tests
        if hasattr(button, 'isCheckable') and button.isCheckable():
            button.toggled.connect(callback)
        else:
            button.clicked.connect(callback)

        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setStyleSheet(BOTTOM_BUTTON_STYLE)

        return button
