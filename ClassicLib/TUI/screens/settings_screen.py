"""Settings screen for CLASSIC TUI."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static

from ClassicLib import YAML
from ClassicLib.YamlSettingsCache import yaml_cache, yaml_settings


class SettingsScreen(ModalScreen):
    """
    Manages the settings screen for the application, providing UI components for users to
    configure various settings and persist those settings.

    The settings screen includes folder configuration, display options, and general settings
    that are divided into separate groups. Users can interact with text inputs, checkboxes,
    and dropdown menus to adjust application settings. Changes can be saved, reset, or
    discarded using buttons provided on the screen.

    Attributes:
        original_settings (dict): Stores the currently loaded settings and their default values.
    """

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
        """
        Initializes an instance of the class.

        This constructor sets up the initial state for the object and loads the
        current settings into the `original_settings` attribute.
        """
        super().__init__()
        self.original_settings = {}
        self._load_current_settings()

    def _load_current_settings(self) -> None:
        """
        Loads the current application settings from a YAML settings configuration file,
        while applying default values for missing or invalid entries.

        Handles reading and initializing various settings, setting default values for
        missing keys, and ensures the internal settings dictionary is populated with
        appropriate defaults or user-defined configurations.

        Raises:
            FileNotFoundError: If the settings file does not exist.
            KeyError: If a required key is missing or invalid in the YAML configuration.
            ValueError: If a setting's value is not the expected data type or malformed.
            TypeError: If a setting retrieval fails due to unexpected data type.
        """
        try:
            # Batch load all settings at once
            requests = [
                (str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path"),
                (str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path"),
                (bool, YAML.Settings, "CLASSIC_Settings.Update Check"),
                (bool, YAML.Settings, "AutoScroll"),
                (bool, YAML.Settings, "ShowTimestamps"),
                (int, YAML.Settings, "MaxOutputLines"),
                (str, YAML.Settings, "Game"),
            ]

            values = yaml_cache.batch_get_settings(requests)

            # Create settings dictionary with defaults
            self.original_settings = {
                "CLASSIC_Settings.MODS Folder Path": values[0] or "",
                "CLASSIC_Settings.SCAN Custom Path": values[1] or "",
                "UpdateCheck": values[2] if values[2] is not None else True,
                "AutoScroll": values[3] if values[3] is not None else True,
                "ShowTimestamps": values[4] if values[4] is not None else True,
                "MaxOutputLines": values[5] if values[5] is not None else 10000,
                "Game": values[6] if values[6] is not None else "Fallout4",
            }

            # Set defaults for None values
            if values[3] is None:
                yaml_settings(bool, YAML.Settings, "AutoScroll", True)
            if values[4] is None:
                yaml_settings(bool, YAML.Settings, "ShowTimestamps", True)
            if values[5] is None:
                yaml_settings(int, YAML.Settings, "MaxOutputLines", 10000)
            if values[6] is None:
                yaml_settings(str, YAML.Settings, "Game", "Fallout4")

        except (FileNotFoundError, KeyError, ValueError, TypeError):
            self.original_settings = {
                "CLASSIC_Settings.MODS Folder Path": "",
                "CLASSIC_Settings.SCAN Custom Path": "",
                "UpdateCheck": True,
                "AutoScroll": True,
                "ShowTimestamps": True,
                "MaxOutputLines": 10000,
                "Game": "Fallout4",
            }

    def compose(self) -> ComposeResult:
        """
        Compose and organize the user interface components for the settings menu.

        This method constructs the layout for a settings interface, structured into
        multiple setting groups, each containing configurable options. The user
        interface components include text labels, input fields, checkboxes, and
        buttons to provide a graphical interface for modifying application settings.

        The settings groups within this method are logically organized into:
        1. Folder Configuration
        2. Display Settings
        3. General Settings

        Additionally, it includes action buttons to save, reset, or cancel the
        modifications in the settings.

        Yields:
            ComposeResult: A textual representation or data structure describing the
            UI components and their hierarchy for rendering the settings menu.
        """
        with Container(id="settings-container"):
            yield Static("⚙️ Settings", classes="settings-title")

            with VerticalScroll(classes="settings-content"):
                # Folder Settings
                with Container(classes="setting-group"):
                    yield Static("📁 Folder Configuration", classes="setting-group-title")

                    with Vertical(classes="setting-item"):
                        yield Label("Staging Mods Folder:", classes="setting-label")
                        yield Input(
                            value=self.original_settings.get("CLASSIC_Settings.MODS Folder Path", ""),
                            placeholder="Path to staging mods folder",
                            id="staging-folder",
                            classes="setting-input",
                        )

                    with Vertical(classes="setting-item"):
                        yield Label("Custom Scan Folder:", classes="setting-label")
                        yield Input(
                            value=self.original_settings.get("CLASSIC_Settings.SCAN Custom Path", ""),
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
        """
        Handles button press events for settings-related actions.

        This method determines the button pressed based on its `id` and executes
        the associated functionality such as saving settings, resetting settings,
        or dismissing the dialog.

        Args:
            event: Button.Pressed
                The button press event containing the button's identifier.

        """
        if event.button.id == "save-settings":
            self._save_settings()
            self.dismiss(True)
        elif event.button.id == "reset-settings":
            self._reset_settings()
        elif event.button.id == "cancel-settings":
            self.dismiss(False)

    def _save_settings(self) -> None:
        """
        Saves application settings to a YAML configuration file and updates the user interface
        with the results.

        This method retrieves user-inputted values from various UI components (e.g., inputs,
        checkboxes, and dropdowns) using their corresponding identifiers. The values are then
        used to update specific fields in the application's YAML settings. If the operation
        succeeds, a success message is displayed to the user. In case of a failure during
        the saving process, an error notification with the reason is displayed.

        Raises:
            LookupError: Raised if query_one fails to find the specified UI component.
            ValueError: Raised if the max_lines input cannot be converted to an integer.
            AttributeError: Raised if accessed attributes do not exist.
            TypeError: Raised if a mismatch occurs during type conversion.
            OSError: Raised in case of failure during file-related operations.
        """
        try:
            # Save folder paths
            staging_input = self.query_one("#staging-folder", Input)
            if staging_input.value:
                yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", staging_input.value)

            custom_input = self.query_one("#custom-folder", Input)
            if custom_input.value:
                yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", custom_input.value)

            # Save display settings
            auto_scroll = self.query_one("#auto-scroll", Checkbox)
            yaml_settings(bool, YAML.Settings, "AutoScroll", auto_scroll.value)

            show_timestamps = self.query_one("#show-timestamps", Checkbox)
            yaml_settings(bool, YAML.Settings, "ShowTimestamps", show_timestamps.value)

            max_lines_input = self.query_one("#max-lines", Input)
            try:
                max_lines = int(max_lines_input.value)
                yaml_settings(int, YAML.Settings, "MaxOutputLines", max_lines)
            except ValueError:
                pass

            # Save general settings
            update_check = self.query_one("#update-check", Checkbox)
            yaml_settings(bool, YAML.Settings, "Update Check", update_check.value)

            game_select = self.query_one("#game-select", Select)
            if game_select.value:
                yaml_settings(str, YAML.Settings, "Game", game_select.value)

            # Show success message
            self.app.notify("Settings saved successfully", severity="information")
        except (LookupError, ValueError, AttributeError, TypeError, OSError) as e:
            self.app.notify(f"Failed to save settings: {e!s}", severity="error")

    def _reset_settings(self) -> None:
        """
        Resets application settings to their original values.

        This method resets various input fields, checkboxes, and select elements in the
        application's interface to their initial state, as defined by the original
        settings. The method also provides a notification indicating that the settings
        have been successfully reset.

        Raises:
            None
        """
        # Reset inputs
        staging_input = self.query_one("#staging-folder", Input)
        staging_input.value = self.original_settings.get("CLASSIC_Settings.MODS Folder Path", "")

        custom_input = self.query_one("#custom-folder", Input)
        custom_input.value = self.original_settings.get("CLASSIC_Settings.SCAN Custom Path", "")

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

    def on_key(self, event: Key) -> None:
        """
        Handles a key press event, checking for the "escape" key to perform an action.

        Args:
            event (Key): The key event object containing details of the key press.
        """
        if event.key == "escape":
            self.dismiss(False)
