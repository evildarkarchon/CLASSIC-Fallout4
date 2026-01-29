"""Main Options Tab for CLASSIC TUI.

This tab provides folder configuration, scan controls, Pastebin fetch,
and Papyrus monitoring.
"""

from typing import override

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label

from ClassicLib.TUI.widgets.folder_input import FolderInput
from ClassicLib.TUI.widgets.papyrus_monitor import PapyrusMonitor


class MainTab(Vertical):
    """Main Options tab content with scan controls and folder configuration.

    Provides:
        - Folder inputs for staging mods and custom scan paths
        - Scan buttons for crash logs and game files
        - Papyrus monitoring toggle and stats display
        - Pastebin fetch functionality
        - Quick action buttons (Help, Settings, Logs, Update, About)
    """

    DEFAULT_CSS = """
    MainTab {
        padding: 1 2;
    }

    .section-header {
        text-style: bold;
        color: #4a9eff;
        margin-bottom: 1;
    }

    .scan-buttons {
        height: 3;
        margin: 1 0;
    }

    .scan-buttons Button {
        margin-right: 2;
    }

    .pastebin-section {
        margin-top: 1;
    }

    .pastebin-input {
        height: 3;
    }

    .pastebin-input Input {
        width: 1fr;
    }

    .pastebin-input Button {
        min-width: 10;
        margin-left: 1;
    }

    .action-row {
        height: 3;
        margin-top: 2;
    }

    .action-row Button {
        margin-right: 1;
    }
    """

    def __init__(self) -> None:
        """Initialize the MainTab."""
        super().__init__()
        self._papyrus_active = False

    @override
    def compose(self) -> ComposeResult:
        """Create the main tab layout.

        Yields:
            Folder inputs, scan buttons, Papyrus monitor, Pastebin input, and action buttons.

        """
        # Folder Configuration Section
        yield Label("STAGING MODS FOLDER", classes="section-header")
        yield FolderInput(
            placeholder="Enter path to staging mods folder...",
            setting_key="MODS Folder Path",
            widget_id="mods-folder",
        )

        yield Label("CUSTOM SCAN FOLDER", classes="section-header")
        yield FolderInput(
            placeholder="Enter custom scan folder path...",
            setting_key="SCAN Custom Path",
            widget_id="scan-folder",
        )

        # Scan Buttons Section
        with Horizontal(classes="scan-buttons"):
            yield Button("CRASH LOGS SCAN", id="btn-crash-scan", variant="primary")
            yield Button("GAME FILES SCAN", id="btn-game-scan", variant="primary")
            yield Button("● PAPYRUS MONITOR \\[OFF]", id="btn-papyrus-toggle")

        # Papyrus Monitor Widget
        yield PapyrusMonitor(id="papyrus-monitor")

        # Pastebin Section
        yield Label("PASTEBIN LOG FETCH", classes="section-header")
        with Horizontal(classes="pastebin-input"):
            yield Input(placeholder="Enter Pastebin URL or ID...", id="pastebin-input")
            yield Button("Fetch", id="btn-pastebin-fetch")

        # Bottom Action Row
        with Horizontal(classes="action-row"):
            yield Button("? Help", id="btn-help")
            yield Button("⚙ Settings", id="btn-settings")
            yield Button("📁 Logs Folder", id="btn-logs-folder")
            yield Button("🔄 Check Update", id="btn-update")
            yield Button("(i) About", id="btn-about")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event.

        """
        button_id = event.button.id
        if button_id == "btn-crash-scan":
            self.start_crash_scan()
        elif button_id == "btn-game-scan":
            self.start_game_scan()
        elif button_id == "btn-papyrus-toggle":
            self.toggle_papyrus()
        elif button_id == "btn-pastebin-fetch":
            self._fetch_pastebin()
        elif button_id == "btn-help":
            self.app.action_show_help()
        elif button_id == "btn-settings":
            self.app.action_show_settings()
        elif button_id == "btn-logs-folder":
            self._open_logs_folder()
        elif button_id == "btn-update":
            self._check_update()
        elif button_id == "btn-about":
            self._show_about()

    def start_crash_scan(self) -> None:
        """Start a crash logs scan with progress indicator."""
        from ClassicLib.TUI.widgets.scan_progress import ScanProgressModal

        self.app.push_screen(
            ScanProgressModal(scan_type="crash_logs"),
            callback=self._on_scan_complete,
        )

    def start_game_scan(self) -> None:
        """Start a game files scan with progress indicator."""
        from ClassicLib.TUI.widgets.scan_progress import ScanProgressModal

        self.app.push_screen(
            ScanProgressModal(scan_type="game_files"),
            callback=self._on_scan_complete,
        )

    def toggle_papyrus(self) -> None:
        """Toggle Papyrus monitoring on/off."""
        self._papyrus_active = not self._papyrus_active
        button = self.query_one("#btn-papyrus-toggle", Button)
        monitor = self.query_one("#papyrus-monitor", PapyrusMonitor)

        if self._papyrus_active:
            button.label = "● PAPYRUS MONITOR \\[ON]"
            button.add_class("-success")
            monitor.start_monitoring()
        else:
            button.label = "● PAPYRUS MONITOR \\[OFF]"
            button.remove_class("-success")
            monitor.stop_monitoring()

    def _on_scan_complete(self, result: bool) -> None:
        """Handle scan completion.

        Args:
            result: True if scan completed successfully, False otherwise.

        """
        if result:
            # Check if auto-switch is enabled and switch to Results tab
            from ClassicLib.io.yaml import classic_settings

            auto_switch = classic_settings(bool, "Auto Switch After Scan")
            if auto_switch:
                self.app.switch_to_results_tab()

    def _fetch_pastebin(self) -> None:
        """Fetch content from Pastebin URL/ID."""
        pastebin_input = self.query_one("#pastebin-input", Input)
        url_or_id = pastebin_input.value.strip()
        if url_or_id:
            self.notify(f"Fetching Pastebin: {url_or_id}...")
            self._run_pastebin_fetch(url_or_id)

    @work(thread=True)
    async def _run_pastebin_fetch(self, url_or_id: str) -> None:
        """Run pastebin fetch in background worker."""
        from ClassicLib.TUI.services import PastebinService

        service = PastebinService()
        result = await service.fetch(url_or_id)
        if result:
            self.app.call_from_thread(self.notify, f"Downloaded: {result.name}")
        else:
            self.app.call_from_thread(self.notify, "Failed to fetch pastebin content", severity="error")

    @staticmethod
    def _open_logs_folder() -> None:
        """Open the Crash Logs folder in file explorer."""
        from ClassicLib.TUI.test_mode import is_test_mode

        if is_test_mode():
            return  # Don't open folders in test mode

        import subprocess
        import sys

        from ClassicLib.core.registry import GlobalRegistry

        logs_dir = GlobalRegistry.get_local_dir() / "Crash Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(logs_dir)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(logs_dir)])
        else:
            subprocess.Popen(["xdg-open", str(logs_dir)])

    def _check_update(self) -> None:
        """Check for application updates."""
        self.notify("Checking for updates...")
        self._run_update_check()

    @work(thread=True)
    async def _run_update_check(self) -> None:
        """Run update check in background worker."""
        from ClassicLib.TUI.services import UpdateService

        service = UpdateService()
        is_latest, error = await service.check_for_updates(explicit=True)

        if error:
            self.app.call_from_thread(self.notify, error, severity="warning")
        elif is_latest:
            self.app.call_from_thread(self.notify, "You are running the latest version!")
        else:
            self.app.call_from_thread(self.notify, "A new version is available!", severity="information")

    def _show_about(self) -> None:
        """Show the About dialog."""
        self.notify("CLASSIC v8.0.0\nCrash Log Auto Scanner & Setup Integrity Checker")
