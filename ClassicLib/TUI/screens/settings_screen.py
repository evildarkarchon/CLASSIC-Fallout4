"""Settings Screen for CLASSIC TUI.

Modal settings dialog for application configuration.
"""

from typing import ClassVar, TypedDict, override

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select


class _OriginalValues(TypedDict):
    """Type-safe container for original settings values."""

    mods_path: str
    scan_path: str
    game: str
    update_check: bool
    auto_switch: bool


class SettingsScreen(ModalScreen[bool]):
    """Modal settings dialog for application configuration.

    Allows configuration of:
        - Folder paths (Mods, Custom Scan)
        - Target game selection
        - Behavior settings (update check, auto-switch tabs)

    Returns True if settings were saved, False if cancelled.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-container {
        width: 70%;
        height: auto;
        max-height: 80%;
        background: #2d2d2d;
        border: solid #3c3c3c;
        padding: 2;
    }

    #settings-title {
        text-style: bold;
        color: #4a9eff;
        text-align: center;
        margin-bottom: 2;
    }

    .settings-section {
        margin-bottom: 2;
    }

    .section-header {
        text-style: bold;
        color: #4a9eff;
        margin-bottom: 1;
    }

    .setting-row {
        height: 3;
        margin-bottom: 1;
    }

    .setting-row Label {
        width: 25;
    }

    .setting-row Input {
        width: 1fr;
    }

    .setting-row Select {
        width: 1fr;
    }

    #buttons-row {
        height: 3;
        margin-top: 2;
        align: center middle;
    }

    #buttons-row Button {
        margin: 0 2;
    }
    """

    def __init__(self) -> None:
        """Initialize the settings screen."""
        super().__init__()
        self._original_values: _OriginalValues = {
            "mods_path": "",
            "scan_path": "",
            "game": "Fallout4",
            "update_check": True,
            "auto_switch": True,
        }

    @override
    def compose(self) -> ComposeResult:
        """Create the settings modal layout.

        Yields:
            Container with folder inputs, game selection, behavior checkboxes, and buttons.

        """
        with Vertical(id="settings-container"):
            yield Label("⚙️ Settings", id="settings-title")

            # Folder Configuration Section
            with Vertical(classes="settings-section"):
                yield Label("📁 FOLDER CONFIGURATION", classes="section-header")
                with Horizontal(classes="setting-row"):
                    yield Label("Staging Mods Folder:")
                    yield Input(id="mods-folder-input", placeholder="Path to mods folder...")
                with Horizontal(classes="setting-row"):
                    yield Label("Custom Scan Folder:")
                    yield Input(id="scan-folder-input", placeholder="Custom scan path...")

            # Game Configuration Section
            with Vertical(classes="settings-section"):
                yield Label("🎮 GAME CONFIGURATION", classes="section-header")
                with Horizontal(classes="setting-row"):
                    yield Label("Target Game:")
                    yield Select(
                        [
                            ("Fallout 4", "Fallout4"),
                            ("Skyrim Special Edition", "SkyrimSE"),
                            ("Skyrim VR", "SkyrimVR"),
                        ],
                        id="game-select",
                        value="Fallout4",
                    )

            # Behavior Section
            with Vertical(classes="settings-section"):
                yield Label("⚡ BEHAVIOR", classes="section-header")
                yield Checkbox("Check for updates on startup", id="update-check")
                yield Checkbox("Auto-switch to Results tab after scan", id="auto-switch")

            # Button Row
            with Horizontal(id="buttons-row"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        """Load current settings when modal is mounted."""
        self._load_current_settings()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event.

        """
        if event.button.id == "save-btn":
            self._save_settings()
            self.dismiss(True)
        elif event.button.id == "cancel-btn":
            self.action_cancel()

    def action_cancel(self) -> None:
        """Cancel and close without saving."""
        self.dismiss(False)

    def _load_current_settings(self) -> None:
        """Load current settings from YAML and populate inputs."""
        from ClassicLib.io.yaml import classic_settings

        # Load folder paths
        mods_path = classic_settings(str, "MODS Folder Path") or ""
        scan_path = classic_settings(str, "SCAN Custom Path") or ""
        game = classic_settings(str, "Game") or "Fallout4"
        update_check = classic_settings(bool, "Update Check")
        auto_switch = classic_settings(bool, "Auto Switch After Scan")

        # Store originals for potential rollback
        self._original_values = {
            "mods_path": mods_path,
            "scan_path": scan_path,
            "game": game,
            "update_check": update_check if update_check is not None else True,
            "auto_switch": auto_switch if auto_switch is not None else True,
        }

        # Populate inputs
        self.query_one("#mods-folder-input", Input).value = mods_path
        self.query_one("#scan-folder-input", Input).value = scan_path
        self.query_one("#game-select", Select).value = game
        self.query_one("#update-check", Checkbox).value = self._original_values["update_check"]
        self.query_one("#auto-switch", Checkbox).value = self._original_values["auto_switch"]

    def _save_settings(self) -> None:
        """Save current settings to YAML."""
        from ClassicLib.core.constants import YAML
        from ClassicLib.io.yaml import yaml_settings

        # Get current values
        mods_path = self.query_one("#mods-folder-input", Input).value
        scan_path = self.query_one("#scan-folder-input", Input).value
        game = self.query_one("#game-select", Select).value
        update_check = self.query_one("#update-check", Checkbox).value
        auto_switch = self.query_one("#auto-switch", Checkbox).value

        # Save to YAML
        if mods_path:
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", mods_path)
        if scan_path:
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", scan_path)
        if game:
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.Game", str(game))
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Update Check", update_check)
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Auto Switch After Scan", auto_switch)

        self.notify("Settings saved")
