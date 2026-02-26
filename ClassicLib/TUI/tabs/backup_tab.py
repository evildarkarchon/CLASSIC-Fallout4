"""File Backup Tab for CLASSIC TUI.

This tab provides a compact table-based backup management interface
for XSE, ReShade, Vulkan, and ENB files.
"""

from pathlib import Path
from typing import ClassVar, Literal, override

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.widgets import Button, DataTable, Label, Static


class BackupTab(Vertical):
    """File Backup tab with DataTable for backup operations.

    Provides backup, restore, and removal operations for:
        - XSE (F4SE/SKSE)
        - ReShade
        - Vulkan
        - ENB

    Keyboard shortcuts:
        - B: Backup selected type
        - R: Restore selected type
        - D: Delete selected backup
        - O: Open backup folder
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("b", "backup_selected", "Backup"),
        Binding("r", "restore_selected", "Restore"),
        Binding("d", "delete_selected", "Delete"),
        Binding("o", "open_folder", "Open Folder"),
    ]

    BACKUP_TYPES: ClassVar[list[tuple[str, str]]] = [
        ("XSE", "XSE (F4SE/SKSE)"),
        ("RESHADE", "ReShade"),
        ("VULKAN", "Vulkan"),
        ("ENB", "ENB"),
    ]

    DEFAULT_CSS = """
    BackupTab {
        padding: 1 2;
    }

    #backup-description {
        margin-bottom: 1;
    }

    #backup-table {
        height: 12;
        margin-bottom: 1;
    }

    #backup-legend {
        color: #808080;
        margin-bottom: 1;
    }

    #btn-open-backup {
        margin-top: 1;
    }
    """

    @override
    def compose(self) -> ComposeResult:
        """Create the backup tab layout.

        Yields:
            Description, backup table, legend, and open folder button.

        """
        yield Label(
            "Manage backups for game files. Backups are stored in:",
            id="backup-description",
        )
        yield Static("CLASSIC Backup/Game Files/", classes="section-header")

        yield DataTable(id="backup-table", cursor_type="row")

        yield Static(
            "Legend: ✓ Backup exists  ○ No backup  │  Keys: [B]ackup [R]estore [D]elete [O]pen",
            id="backup-legend",
        )

        yield Button("OPEN BACKUP FOLDER", id="btn-open-backup")

    def on_mount(self) -> None:
        """Initialize the backup table when mounted."""
        table = self.query_one("#backup-table", DataTable)
        table.add_columns("Type", "Status", "Files", "Actions")
        self.refresh_backup_status()

    def refresh_backup_status(self) -> None:
        """Check backup directories and update table rows."""
        from ClassicLib.TUI.test_mode import get_test_local_dir, is_test_mode

        if is_test_mode():
            backup_base = get_test_local_dir() / "CLASSIC Backup" / "Game Files"
        else:
            from ClassicLib.core.registry import GlobalRegistry

            backup_base = Path(GlobalRegistry.get_local_dir()) / "CLASSIC Backup" / "Game Files"

        table = self.query_one("#backup-table", DataTable)
        table.clear()

        for type_key, type_name in self.BACKUP_TYPES:
            backup_path = backup_base / f"Backup {type_key}"
            exists = backup_path.is_dir() and any(backup_path.iterdir()) if backup_path.exists() else False
            file_count = len(list(backup_path.iterdir())) if exists else 0

            status = "✓ Exists" if exists else "○ None"
            files = str(file_count) if exists else "-"
            actions = "[B]kp [R]st [D]el" if exists else "[B]kp"

            table.add_row(type_name, status, files, actions, key=type_key)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event.

        """
        if event.button.id == "btn-open-backup":
            self._open_backup_folder()

    def action_backup_selected(self) -> None:
        """Create backup for selected type."""
        selected_type = self._get_selected_type()
        if selected_type:
            self._perform_backup_operation(selected_type, "BACKUP")

    def action_restore_selected(self) -> None:
        """Restore backup for selected type."""
        selected_type = self._get_selected_type()
        if selected_type:
            self._perform_backup_operation(selected_type, "RESTORE")

    def action_delete_selected(self) -> None:
        """Delete backup for selected type."""
        selected_type = self._get_selected_type()
        if selected_type:
            self._perform_backup_operation(selected_type, "REMOVE")

    def action_open_folder(self) -> None:
        """Open the backup folder."""
        self._open_backup_folder()

    def _get_selected_type(self) -> str | None:
        """Get the currently selected backup type from the table.

        Returns:
            The backup type key (XSE, RESHADE, etc.) or None if no selection.

        """
        table = self.query_one("#backup-table", DataTable)
        row = table.cursor_row
        if 0 <= row < len(self.BACKUP_TYPES):
            return self.BACKUP_TYPES[row][0]
        return None

    def _perform_backup_operation(
        self,
        backup_type: str,
        operation: Literal["BACKUP", "RESTORE", "REMOVE"],
    ) -> None:
        """Perform a backup operation.

        Args:
            backup_type: The backup type (XSE, RESHADE, VULKAN, ENB).
            operation: The operation to perform.

        """
        from ClassicLib.scanning.game import manage_game_files

        try:
            selected_list = f"Backup {backup_type}"
            manage_game_files(selected_list, operation)
        except (OSError, PermissionError, FileNotFoundError) as e:
            self.notify(f"Error: {e}", severity="error")
        else:
            self.notify(f"{operation.title()} completed for {backup_type}")
            self.refresh_backup_status()

    @staticmethod
    def _open_backup_folder() -> None:
        """Open the CLASSIC Backup folder in file explorer."""
        from ClassicLib.TUI.test_mode import is_test_mode

        if is_test_mode():
            return  # Don't open folders in test mode

        import subprocess
        import sys

        from ClassicLib.core.registry import GlobalRegistry

        backup_dir = Path(GlobalRegistry.get_local_dir()) / "CLASSIC Backup"
        backup_dir.mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(backup_dir)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(backup_dir)])
        else:
            subprocess.Popen(["xdg-open", str(backup_dir)])
