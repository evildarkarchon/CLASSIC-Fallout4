"""Main options screen for CLASSIC TUI."""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, TextArea, Checkbox
from textual.reactive import reactive

from ClassicLib.YamlSettingsCache import classic_settings
from ..widgets.folder_selector import FolderSelector
from ..widgets.scan_buttons import ScanButton
from ..widgets.output_viewer import OutputViewer


class MainScreen(Screen):
    """Main options screen with folder selection and scan operations."""
    
    staging_folder = reactive("")
    custom_folder = reactive("")
    
    def compose(self) -> ComposeResult:
        """Compose the main screen layout."""
        with Container(id="main-container"):
            yield Label("MAIN OPTIONS", classes="title")
            
            with Vertical(classes="folder-section"):
                yield Label("STAGING MODS FOLDER")
                yield FolderSelector(
                    placeholder="Enter path to staging mods folder",
                    id="mods-folder",
                    classes="folder-input"
                )
                
                yield Label("CUSTOM SCAN FOLDER")
                yield FolderSelector(
                    placeholder="Enter path to custom scan folder",
                    id="scan-folder",
                    classes="folder-input"
                )
            
            with Horizontal(classes="scan-buttons"):
                yield ScanButton(
                    "Crash Logs Scan",
                    id="crash-scan",
                    variant="primary"
                )
                yield ScanButton(
                    "Game Files Scan",
                    id="game-scan",
                    variant="primary"
                )
                yield Button(
                    "Papyrus Monitor",
                    id="papyrus-monitor",
                    variant="default"
                )
            
            with Vertical(classes="settings-section"):
                yield Checkbox(
                    "Check for Updates",
                    id="update-check",
                    value=classic_settings(bool, "Update Check")
                )
            
            yield OutputViewer(id="output")
    
    def on_mount(self) -> None:
        """Initialize screen on mount."""
        self._load_folder_paths()
        self._setup_event_handlers()
    
    def _load_folder_paths(self) -> None:
        """Load saved folder paths from settings."""
        try:
            staging_path = classic_settings(str, "ModStagingFolder")
            if staging_path:
                mods_folder = self.query_one("#mods-folder", FolderSelector)
                mods_folder.value = staging_path
                self.staging_folder = staging_path
            
            custom_path = classic_settings(str, "CustomScanFolder")
            if custom_path:
                scan_folder = self.query_one("#scan-folder", FolderSelector)
                scan_folder.value = custom_path
                self.custom_folder = custom_path
        except Exception:
            pass
    
    def _setup_event_handlers(self) -> None:
        """Setup event handlers for widgets."""
        crash_scan = self.query_one("#crash-scan", ScanButton)
        crash_scan.on_click = self.perform_crash_scan
        
        game_scan = self.query_one("#game-scan", ScanButton)
        game_scan.on_click = self.perform_game_scan
        
        papyrus_btn = self.query_one("#papyrus-monitor", Button)
        papyrus_btn.on_click = self.toggle_papyrus_monitor
    
    async def perform_crash_scan(self) -> None:
        """Perform crash logs scan."""
        output = self.query_one("#output", OutputViewer)
        output.clear()
        output.append_output("Starting crash logs scan...\n")
        
        from ..handlers.scan_handler import TuiScanHandler
        handler = TuiScanHandler(output_callback=output.append_output)
        await handler.perform_crash_scan()
    
    async def perform_game_scan(self) -> None:
        """Perform game files scan."""
        output = self.query_one("#output", OutputViewer)
        output.clear()
        output.append_output("Starting game files scan...\n")
        
        from ..handlers.scan_handler import TuiScanHandler
        handler = TuiScanHandler(output_callback=output.append_output)
        await handler.perform_game_scan()
    
    async def toggle_papyrus_monitor(self) -> None:
        """Toggle Papyrus monitoring."""
        output = self.query_one("#output", OutputViewer)
        output.append_output("Papyrus monitoring not yet implemented in TUI mode.\n")
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes."""
        if event.checkbox.id == "update-check":
            classic_settings(bool, "Update Check", event.value)
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "mods-folder":
            self.staging_folder = event.value
            classic_settings(str, "ModStagingFolder", event.value)
        elif event.input.id == "scan-folder":
            self.custom_folder = event.value
            classic_settings(str, "CustomScanFolder", event.value)