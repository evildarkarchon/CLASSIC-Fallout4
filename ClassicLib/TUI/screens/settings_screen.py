"""Settings screen for CLASSIC TUI."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static

from ClassicLib.YamlSettingsCache import classic_settings


class SettingsScreen(ModalScreen):
    """Modal settings screen for configuration options."""

    CSS = """
    SettingsScreen {
        align: center middle;
    }
    
    #settings-container {
        width: 70;
        height: 35;
        border: thick $primary;
        padding: 1;
        background: $surface;
    }
    
    .settings-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $primary;
        text-style: bold underline;
    }
    
    .settings-content {
        height: 100%;
        margin: 1 0;
    }
    
    .setting-group {
        margin: 1 0;
        padding: 1;
        border: solid $border;
    }
    
    .setting-group-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .setting-item {
        margin: 1 0;
    }
    
    .setting-label {
        width: 30;
        color: $text-muted;
    }
    
    .setting-input {
        width: 100%;
    }
    
    .settings-buttons {
        dock: bottom;
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    
    .settings-buttons Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def __init__(self) -> None:
        """Initialize settings screen."""
        super().__init__()
        self.original_settings = {}
        self._load_current_settings()

    def _load_current_settings(self) -> None:
        """Load current settings values."""
        try:
            self.original_settings = {
                "ModStagingFolder": classic_settings(str, "ModStagingFolder") or "",
                "CustomScanFolder": classic_settings(str, "CustomScanFolder") or "",
                "UpdateCheck": classic_settings(bool, "Update Check"),
                "AutoScroll": classic_settings(bool, "AutoScroll", True),
                "ShowTimestamps": classic_settings(bool, "ShowTimestamps", True),
                "MaxOutputLines": classic_settings(int, "MaxOutputLines", 10000),
                "Game": classic_settings(str, "Game", "Fallout4"),
            }
        except Exception:
            self.original_settings = {
                "ModStagingFolder": "",
                "CustomScanFolder": "",
                "UpdateCheck": True,
                "AutoScroll": True,
                "ShowTimestamps": True,
                "MaxOutputLines": 10000,
                "Game": "Fallout4",
            }

    def compose(self) -> ComposeResult:
        """Compose settings screen layout."""
        with Container(id="settings-container"):
            yield Static("⚙️ Settings", classes="settings-title")

            with VerticalScroll(classes="settings-content"):
                # Folder Settings
                with Container(classes="setting-group"):
                    yield Static("📁 Folder Configuration", classes="setting-group-title")

                    with Vertical(classes="setting-item"):
                        yield Label("Staging Mods Folder:", classes="setting-label")
                        yield Input(
                            value=self.original_settings.get("ModStagingFolder", ""),
                            placeholder="Path to staging mods folder",
                            id="staging-folder",
                            classes="setting-input",
                        )

                    with Vertical(classes="setting-item"):
                        yield Label("Custom Scan Folder:", classes="setting-label")
                        yield Input(
                            value=self.original_settings.get("CustomScanFolder", ""),
                            placeholder="Path to custom scan folder",
                            id="custom-folder",
                            classes="setting-input",
                        )

                # Display Settings
                with Container(classes="setting-group"):
                    yield Static("🖥️ Display Settings", classes="setting-group-title")

                    yield Checkbox(
                        "Auto-scroll output", value=self.original_settings.get("AutoScroll", True), id="auto-scroll", classes="setting-item"
                    )

                    yield Checkbox(
                        "Show timestamps in output",
                        value=self.original_settings.get("ShowTimestamps", True),
                        id="show-timestamps",
                        classes="setting-item",
                    )

                    with Vertical(classes="setting-item"):
                        yield Label("Max output lines:", classes="setting-label")
                        yield Input(
                            value=str(self.original_settings.get("MaxOutputLines", 10000)),
                            placeholder="Maximum lines in output viewer",
                            id="max-lines",
                            classes="setting-input",
                        )

                # General Settings
                with Container(classes="setting-group"):
                    yield Static("⚡ General Settings", classes="setting-group-title")

                    yield Checkbox(
                        "Check for updates on startup",
                        value=self.original_settings.get("UpdateCheck", True),
                        id="update-check",
                        classes="setting-item",
                    )

                    with Vertical(classes="setting-item"):
                        yield Label("Game:", classes="setting-label")
                        yield Select(
                            [(line, line) for line in ["Fallout4", "Skyrim", "SkyrimSE"]],
                            value=self.original_settings.get("Game", "Fallout4"),
                            id="game-select",
                            classes="setting-input",
                        )

            with Horizontal(classes="settings-buttons"):
                yield Button("Save", variant="primary", id="save-settings")
                yield Button("Reset", variant="warning", id="reset-settings")
                yield Button("Cancel", variant="default", id="cancel-settings")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-settings":
            self._save_settings()
            self.dismiss(True)
        elif event.button.id == "reset-settings":
            self._reset_settings()
        elif event.button.id == "cancel-settings":
            self.dismiss(False)

    def _save_settings(self) -> None:
        """Save all settings."""
        try:
            # Save folder paths
            staging_input = self.query_one("#staging-folder", Input)
            if staging_input.value:
                classic_settings(str, "ModStagingFolder", staging_input.value)

            custom_input = self.query_one("#custom-folder", Input)
            if custom_input.value:
                classic_settings(str, "CustomScanFolder", custom_input.value)

            # Save display settings
            auto_scroll = self.query_one("#auto-scroll", Checkbox)
            classic_settings(bool, "AutoScroll", auto_scroll.value)

            show_timestamps = self.query_one("#show-timestamps", Checkbox)
            classic_settings(bool, "ShowTimestamps", show_timestamps.value)

            max_lines_input = self.query_one("#max-lines", Input)
            try:
                max_lines = int(max_lines_input.value)
                classic_settings(int, "MaxOutputLines", max_lines)
            except ValueError:
                pass

            # Save general settings
            update_check = self.query_one("#update-check", Checkbox)
            classic_settings(bool, "Update Check", update_check.value)

            game_select = self.query_one("#game-select", Select)
            if game_select.value:
                classic_settings(str, "Game", game_select.value)

            # Show success message
            self.app.notify("Settings saved successfully", severity="information")
        except Exception as e:
            self.app.notify(f"Failed to save settings: {e!s}", severity="error")

    def _reset_settings(self) -> None:
        """Reset settings to original values."""
        # Reset inputs
        staging_input = self.query_one("#staging-folder", Input)
        staging_input.value = self.original_settings.get("ModStagingFolder", "")

        custom_input = self.query_one("#custom-folder", Input)
        custom_input.value = self.original_settings.get("CustomScanFolder", "")

        auto_scroll = self.query_one("#auto-scroll", Checkbox)
        auto_scroll.value = self.original_settings.get("AutoScroll", True)

        show_timestamps = self.query_one("#show-timestamps", Checkbox)
        show_timestamps.value = self.original_settings.get("ShowTimestamps", True)

        max_lines_input = self.query_one("#max-lines", Input)
        max_lines_input.value = str(self.original_settings.get("MaxOutputLines", 10000))

        update_check = self.query_one("#update-check", Checkbox)
        update_check.value = self.original_settings.get("UpdateCheck", True)

        game_select = self.query_one("#game-select", Select)
        game_select.value = self.original_settings.get("Game", "Fallout4")

        self.app.notify("Settings reset to original values", severity="information")

    def on_key(self, event) -> None:
        """Handle keyboard events."""
        if event.key == "escape":
            self.dismiss(False)
