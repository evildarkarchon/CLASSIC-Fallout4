"""UI setup controller for CLASSIC interface.

This module provides the UISetupController class that orchestrates the setup
of all tabs and wires UI elements to their respective controllers.

Example:
    >>> from ClassicLib.Interface.controllers.ui_setup import UISetupController
    >>> ui_setup = UISetupController(context, scan=scan_ctrl, results=results_ctrl, ...)
    >>> ui_setup.setup_all_tabs()

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
from ClassicLib.Logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from ClassicLib.Interface.context import FeatureContext
    from ClassicLib.Interface.controllers.backup_manager import BackupManager
    from ClassicLib.Interface.controllers.folder_manager import FolderManager
    from ClassicLib.Interface.controllers.help_about import HelpAboutController
    from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager
    from ClassicLib.Interface.controllers.pastebin_controller import PastebinController
    from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController
    from ClassicLib.Interface.controllers.scan_controller import ScanController
    from ClassicLib.Interface.controllers.update_manager import UpdateManager


class UISetupController:
    """Controller for orchestrating UI tab setup.

    This controller handles setting up all tab layouts and wiring UI elements
    to their respective controllers. It serves as the central point for
    initializing the user interface.

    Attributes:
        _ctx: The FeatureContext providing access to shared dependencies.
        _scan: ScanController for scan operations.
        _results: ResultsViewerController for results display.
        _papyrus: PapyrusManager for Papyrus monitoring.
        _backup: BackupManager for backup operations.
        _folder: FolderManager for folder operations.
        _help_about: HelpAboutController for help/about dialogs.
        _update: UpdateManager for update checking.
        _pastebin: PastebinController for Pastebin fetching.

    Example:
        >>> ui_setup = UISetupController(
        ...     context=context,
        ...     scan=scan_ctrl,
        ...     results=results_ctrl,
        ...     papyrus=papyrus_ctrl,
        ...     backup=backup_ctrl,
        ...     folder=folder_ctrl,
        ...     help_about=help_ctrl,
        ...     update=update_ctrl,
        ...     pastebin=pastebin_ctrl,
        ... )
        >>> ui_setup.setup_all_tabs()

    """

    def __init__(
        self,
        context: FeatureContext,
        scan: ScanController,
        results: ResultsViewerController,
        papyrus: PapyrusManager,
        backup: BackupManager,
        folder: FolderManager,
        help_about: HelpAboutController,
        update: UpdateManager,
        pastebin: PastebinController,
    ) -> None:
        """Initialize the UISetupController.

        Args:
            context: FeatureContext providing access to main_window, signal_hub,
                and ui_widgets.
            scan: ScanController for crash logs and game files scanning.
            results: ResultsViewerController for report display.
            papyrus: PapyrusManager for Papyrus monitoring.
            backup: BackupManager for backup operations.
            folder: FolderManager for folder selection and operations.
            help_about: HelpAboutController for help and about dialogs.
            update: UpdateManager for update checking.
            pastebin: PastebinController for Pastebin fetching.

        """
        self._ctx = context
        self._scan = scan
        self._results = results
        self._papyrus = papyrus
        self._backup = backup
        self._folder = folder
        self._help_about = help_about
        self._update = update
        self._pastebin = pastebin

        # Connect to SignalHub for papyrus button style updates
        self._ctx.signal_hub.papyrus_button_style_update.connect(self._update_papyrus_button_style)

    def setup_all_tabs(self) -> None:
        """Set up all tabs in the main window.

        Calls setup methods for each tab in sequence and registers
        UI widget references with the context.
        """
        self.setup_main_tab()
        self.setup_articles_tab()
        self.setup_backups_tab()
        self._results.setup_results_tab()
        logger.debug("All tabs setup completed")

    def setup_main_tab(self) -> None:
        """Set up the main tab layout and its components.

        Configures the main tab with folder selection widgets, main scan
        buttons, and bottom utility buttons.
        """
        main_tab = self._ctx.ui_widgets.main_tab
        if main_tab is None:
            logger.warning("Main tab widget not found, skipping setup")
            return

        layout = QVBoxLayout(main_tab)
        layout.setContentsMargins(15, 5, 15, 10)
        layout.setSpacing(0)

        # Create a fixed header section for folder widgets
        header_widget = QWidget()
        header_widget.setMaximumHeight(100)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        # Set up folder sections
        mods_folder_edit = setup_folder_section(
            header_layout,
            "STAGING MODS FOLDER",
            "Box_SelectedMods",
            self._folder.select_folder_mods,
            tooltip="Select the folder where your mod manager (e.g., MO2) stages your mods.",
        )
        if mods_folder_edit:
            mods_folder_edit.setPlaceholderText("Optional: Select your mod staging folder (e.g., MO2/mods)")
            mods_folder_edit.setToolTip("Select the folder where your mod manager (e.g., MO2) stages your mods.")
            self._ctx.ui_widgets.mods_folder_edit = mods_folder_edit

        scan_folder_edit = setup_folder_section(
            header_layout,
            "CUSTOM SCAN FOLDER",
            "Box_SelectedScan",
            self._folder.select_folder_scan,
            tooltip="Select a supplementary custom folder containing crash logs to scan. The game directory is always used for scanning.",
        )
        if scan_folder_edit:
            scan_folder_edit.setPlaceholderText("Optional: Select a supplementary custom folder with crash logs")
            scan_folder_edit.setToolTip(
                "Select a supplementary custom folder containing crash logs to scan. The game directory is always used for scanning."
            )
            scan_folder_edit.editingFinished.connect(self._folder.validate_scan_folder_text)
            self._ctx.ui_widgets.scan_folder_edit = scan_folder_edit

        # Add the header widget to main layout
        layout.addWidget(header_widget)
        layout.addStretch()

        # Add spacing after folder sections before main buttons
        layout.addSpacing(5)
        self._setup_main_buttons(layout)
        layout.addStretch()
        layout.addSpacing(10)
        self._setup_bottom_buttons(layout)

    def setup_articles_tab(self) -> None:
        """Set up the Articles tab with resource links.

        Creates a grid of buttons linking to relevant resources and guides.
        """
        articles_tab = self._ctx.ui_widgets.articles_tab
        if articles_tab is None:
            logger.warning("Articles tab widget not found, skipping setup")
            return

        layout = QVBoxLayout(articles_tab)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        # Add a title label
        title_label = QLabel("USEFUL RESOURCES & LINKS")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        layout.addWidget(title_label)

        # Create a grid layout for the buttons
        grid_layout = QGridLayout()
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
            button = QPushButton(data["text"])
            button.setStyleSheet(button_style)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setToolTip(f"Open {data['url']} in your browser.")
            button.clicked.connect(partial(self._open_url, data["url"]))

            row, col = divmod(i, 3)
            grid_layout.addWidget(button, row, col)

        layout.addLayout(grid_layout)
        layout.addStretch(1)

    def setup_backups_tab(self) -> None:
        """Set up the Backups tab with backup management UI.

        Creates labels explaining backup operations and backup sections
        for each category.
        """
        backups_tab = self._ctx.ui_widgets.backups_tab
        if backups_tab is None:
            logger.warning("Backups tab widget not found, skipping setup")
            return

        layout = QVBoxLayout(backups_tab)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        layout.addWidget(QLabel("BACKUP > Backup files from the game folder into the CLASSIC Backup folder."))
        layout.addWidget(QLabel("RESTORE > Restore file backup from the CLASSIC Backup folder into the game folder."))
        layout.addWidget(QLabel("REMOVE > Remove files only from the game folder without removing existing backups."))

        categories: list[Literal["XSE", "RESHADE", "VULKAN", "ENB"]] = ["XSE", "RESHADE", "VULKAN", "ENB"]
        for category in categories:
            self._backup.add_backup_section(layout, category, category)

        layout.addStretch(1)

        bottom_layout = QHBoxLayout()
        open_backups_button = QPushButton("OPEN CLASSIC BACKUPS")
        open_backups_button.clicked.connect(self._backup.open_backup_folder)
        bottom_layout.addWidget(open_backups_button)
        bottom_layout.addStretch(1)
        layout.addLayout(bottom_layout)

        self._backup.check_existing_backups()

    def _setup_main_buttons(self, layout: QBoxLayout) -> None:
        """Set up main action buttons (scan buttons).

        Args:
            layout: The parent layout to add buttons to.

        """
        main_buttons_layout = QHBoxLayout()
        main_buttons_layout.setSpacing(10)

        crash_logs_button = add_main_button(
            main_buttons_layout,
            "SCAN CRASH LOGS",
            self._scan.crash_logs_scan,
            "Scan all detected crash logs for issues.",
        )
        if crash_logs_button:
            self._ctx.ui_widgets.crash_logs_button = crash_logs_button
            scan_button_group = self._ctx.ui_widgets.scan_button_group
            if scan_button_group is not None:
                scan_button_group.addButton(crash_logs_button)

        game_files_button = add_main_button(
            main_buttons_layout,
            "SCAN GAME FILES",
            self._scan.game_files_scan,
            "Scan game and mod files for potential problems (FCX Mode dependent).",
        )
        if game_files_button:
            self._ctx.ui_widgets.game_files_button = game_files_button
            scan_button_group = self._ctx.ui_widgets.scan_button_group
            if scan_button_group is not None:
                scan_button_group.addButton(game_files_button)

        if supports_add_layout(layout):
            layout.addLayout(main_buttons_layout)

    def _setup_bottom_buttons(self, layout: QBoxLayout) -> None:
        """Set up bottom utility buttons and action buttons.

        Args:
            layout: The parent layout to add buttons to.

        """
        # First row of utility buttons
        bottom_buttons_hbox = QHBoxLayout()
        bottom_buttons_hbox.setSpacing(10)
        bottom_buttons_hbox.setContentsMargins(0, 0, 0, 0)

        buttons_config: list[tuple[str, str, Callable[[], None]]] = [
            ("ABOUT", "Show application information.", self._help_about.show_about),
            ("HELP", "Show help information for main options.", self._help_about.help_popup_main),
            ("SETTINGS", "Open application settings dialog.", self._help_about.open_settings),
            ("OPEN CRASH LOGS", "Open the Crash Logs directory in your file explorer.", self._folder.open_crash_logs_folder),
            ("CHECK UPDATES", "Manually check for CLASSIC updates.", self._update.update_popup_explicit),
        ]

        for text, tooltip, callback in buttons_config:
            button = self._create_button(text, tooltip, callback)
            bottom_buttons_hbox.addWidget(button)

        # Second row with main action buttons
        main_actions_hbox = QHBoxLayout()
        main_actions_hbox.setSpacing(10)
        main_actions_hbox.setContentsMargins(0, 0, 0, 0)

        # Papyrus monitoring button
        papyrus_button = self._create_button(
            "START PAPYRUS MONITORING",
            "Toggle Papyrus log monitoring. Shows statistics in a dedicated dialog.",
            self._papyrus.toggle_monitoring,
        )
        papyrus_button.setCheckable(True)
        # Register button BEFORE applying style (style method looks up from context)
        self._ctx.ui_widgets.papyrus_button = papyrus_button
        self._update_papyrus_button_style(False)
        main_actions_hbox.addWidget(papyrus_button, 1)

        # Exit button
        exit_button = self._create_button("EXIT", "Close CLASSIC.", QApplication.quit)
        main_actions_hbox.addWidget(exit_button)

        # Add both layouts to the main layout
        if supports_add_layout(layout):
            layout.addLayout(bottom_buttons_hbox)
            layout.addSpacing(5)
            layout.addLayout(main_actions_hbox)

    def _update_papyrus_button_style(self, monitoring: bool) -> None:
        """Update the Papyrus button style based on monitoring state.

        Args:
            monitoring: True if monitoring is active, False otherwise.

        """
        papyrus_button = self._ctx.ui_widgets.papyrus_button
        if papyrus_button is None:
            return

        if monitoring:
            papyrus_button.setText("STOP PAPYRUS MONITORING")
            papyrus_button.setStyleSheet(
                """
                QPushButton {
                    color: black;
                    background: rgb(237, 45, 45);  /* Bright red background */
                    border-radius: 10px;
                    border: 1px solid black;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: rgb(255, 60, 60); }
                QPushButton:pressed { background-color: rgb(200, 35, 35); }
                """
            )
        else:
            papyrus_button.setText("START PAPYRUS MONITORING")
            papyrus_button.setStyleSheet(
                """
                QPushButton {
                    color: black;
                    background: rgb(45, 237, 138);  /* Bright green background */
                    border-radius: 10px;
                    border: 1px solid black;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: rgb(55, 255, 150); }
                QPushButton:pressed { background-color: rgb(35, 200, 115); }
                """
            )

    @staticmethod
    def _create_button(text: str, tooltip: str, callback: Callable[[], None]) -> QPushButton:
        """Create a styled button with the specified properties.

        Args:
            text: The button label text.
            tooltip: The button tooltip text.
            callback: The function to call when clicked.

        Returns:
            The configured QPushButton.

        """
        button = QPushButton(text)
        button.setToolTip(tooltip)
        button.clicked.connect(callback)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setStyleSheet(BOTTOM_BUTTON_STYLE)
        return button

    @staticmethod
    def _open_url(url: str) -> None:
        """Open a URL in the default browser.

        Args:
            url: The URL to open.

        """
        QDesktopServices.openUrl(QUrl(url))
