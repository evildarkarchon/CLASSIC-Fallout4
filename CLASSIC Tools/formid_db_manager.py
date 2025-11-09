"""FormID Database Manager GUI application.

This module provides a PySide6-based GUI tool for managing FormID databases
used by CLASSIC for crash log analysis. It allows users to:

- Import FormID lists from text files into SQLite databases
- Select target game (Fallout 4, Skyrim, Starfield)
- Update existing database entries or add new ones
- Preview changes with dry-run mode
- View processing logs in real-time

The FormID format is: plugin | formid | entry (pipe-separated values).

Classes:
    FormIDManager: Main window class providing the GUI and database operations.

Example:
    Run as standalone application:

    $ python formid_db_manager.py
"""

import sqlite3
import sys
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class FormIDManager(QMainWindow):
    """Main window for managing FormID databases used in CLASSIC crash log analysis.

    This GUI application provides an interface for importing FormID lists from
    text files into SQLite databases. It supports multiple games (Fallout 4,
    Skyrim, Starfield) and offers features like update mode (replacing existing
    entries), dry-run preview, and verbose logging.

    The FormID format expected in input files is:
        plugin | formid | entry

    Attributes:
        main_layout (QVBoxLayout): Main vertical layout container.
        file_label (QLabel): Label for file selection input.
        file_path (QLineEdit): Input field displaying selected FormID list file.
        db_label (QLabel): Label for database selection input.
        db_path (QLineEdit): Input field displaying selected database file.
        game_label (QLabel): Label for game selection.
        game_combo (QComboBox): Dropdown for selecting target game.
        mode_checkbox (QCheckBox): Toggle for update mode (replace vs append).
        verbose_checkbox (QCheckBox): Toggle for detailed logging output.
        dry_run_checkbox (QCheckBox): Toggle for preview mode without changes.
        log_area (QTextEdit): Read-only text area for displaying processing logs.
        process_btn (QPushButton): Button to initiate FormID processing.

    Example:
        >>> app = QApplication(sys.argv)
        >>> window = FormIDManager()
        >>> window.show()
        >>> sys.exit(app.exec())
    """

    def __init__(self) -> None:
        """Initialize the FormID Database Manager window.

        Sets up the main window with all UI components including file selection,
        database selection, game selection, processing mode options, log display,
        and the process button. Configures minimum window dimensions.
        """
        super().__init__()
        self.setWindowTitle("FormID Database Manager")

        # Create main widget and its main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)

        # Create UI elements
        self.create_file_selection()
        self.create_database_selection()
        self.create_game_selection()
        self.create_mode_selection()
        self.create_log_area()
        self.create_process_button()

        # Set window properties
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

    def create_file_selection(self) -> None:
        """Create the file selection row with label, input field, and browse button.

        Sets up a horizontal layout containing a label, text field for displaying
        the selected FormID list file path, and a button to open a file dialog.
        The text field shows "No file selected" as placeholder text.
        """
        layout = QHBoxLayout()

        self.file_label = QLabel("FormID List File:")
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("No file selected")
        select_file_btn = QPushButton("Select File")
        select_file_btn.clicked.connect(self.select_file)

        layout.addWidget(self.file_label)
        layout.addWidget(self.file_path, 1)
        layout.addWidget(select_file_btn)

        self.main_layout.addLayout(layout)

    def create_database_selection(self) -> None:
        """Create the database selection row with label, input field, and browse button.

        Sets up a horizontal layout containing a label, text field for displaying
        the selected database file path, and a button to open a file dialog.
        The text field shows "No database selected" as placeholder text.
        """
        layout = QHBoxLayout()

        self.db_label = QLabel("Database File:")
        self.db_path = QLineEdit()
        self.db_path.setPlaceholderText("No database selected")
        select_db_btn = QPushButton("Select Database")
        select_db_btn.clicked.connect(self.select_database)

        layout.addWidget(self.db_label)
        layout.addWidget(self.db_path, 1)
        layout.addWidget(select_db_btn)

        self.main_layout.addLayout(layout)

    def create_game_selection(self) -> None:
        """Create the game selection row with label and dropdown.

        Sets up a horizontal layout containing a label and combo box populated
        with supported games (Fallout4, Skyrim, Starfield). Adds stretch spacing
        to left-align the controls.
        """
        layout = QHBoxLayout()

        self.game_label = QLabel("Game:")
        self.game_combo = QComboBox()
        self.game_combo.addItems(["Fallout4", "Skyrim", "Starfield"])

        layout.addWidget(self.game_label)
        layout.addWidget(self.game_combo)
        layout.addStretch()

        self.main_layout.addLayout(layout)

    def create_mode_selection(self) -> None:
        """Create the processing mode options row with three checkboxes.

        Sets up a horizontal layout containing checkboxes for:
        - Update Mode: Replace existing entries vs append
        - Verbose Output: Detailed per-entry logging
        - Dry Run: Preview changes without modifying database

        The dry run checkbox automatically disables verbose output when checked.
        """
        layout = QHBoxLayout()

        self.mode_checkbox = QCheckBox("Update Mode (replaces existing entries)")
        self.verbose_checkbox = QCheckBox("Verbose Output")
        self.dry_run_checkbox = QCheckBox("Dry Run (preview changes)")
        self.dry_run_checkbox.stateChanged.connect(self.switch_verbose_checkbox_enabled)

        layout.addWidget(self.mode_checkbox)
        layout.addWidget(self.verbose_checkbox)
        layout.addWidget(self.dry_run_checkbox)
        layout.addStretch()

        self.main_layout.addLayout(layout)

    def create_log_area(self) -> None:
        """Create the read-only text area for displaying processing logs.

        Adds a QTextEdit widget configured as read-only to show status messages,
        progress updates, and error information during FormID processing.
        """
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.main_layout.addWidget(self.log_area)

    def create_process_button(self) -> None:
        """Create the main process button that triggers FormID import.

        Adds a QPushButton labeled "Process FormIDs" and connects it to the
        process_formids method that handles the actual database operations.
        """
        self.process_btn = QPushButton("Process FormIDs")
        self.process_btn.clicked.connect(self.process_formids)
        self.main_layout.addWidget(self.process_btn)

    def select_file(self) -> None:
        """Open file dialog to select a FormID list text file.

        Displays a file open dialog filtered to .txt files. If a file is selected,
        updates the file_path text field with the selected file's path.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Select FormID List", "", "Text Files (*.txt)")
        if file_path:
            self.file_path.setText(str(file_path))

    def select_database(self) -> None:
        """Open file dialog to select a SQLite database file.

        Displays a file open dialog filtered to .db files. If a file is selected,
        updates the db_path text field with the selected database file's path.
        """
        db_path, _ = QFileDialog.getOpenFileName(self, "Select Database", "", "Database Files (*.db)")
        if db_path:
            self.db_path.setText(str(db_path))

    def log(self, message: str) -> None:
        """Append a message to the log area and update the UI.

        Args:
            message: Text message to display in the log area.

        Note:
            Calls QApplication.processEvents() to ensure the UI updates
            immediately during long-running operations.
        """
        self.log_area.append(message)
        QApplication.processEvents()  # Ensures UI updates during processing

    def switch_verbose_checkbox_enabled(self) -> None:
        """Enable or disable verbose output checkbox based on dry run state.

        When dry run mode is enabled, disables and unchecks the verbose checkbox
        since dry runs don't perform actual operations. When dry run is disabled,
        re-enables the verbose checkbox without automatically checking it.
        """
        self.verbose_checkbox.setEnabled(not self.dry_run_checkbox.isChecked())
        if self.dry_run_checkbox.isChecked():  # Doing it this way because I don't want to automatically check it when disabling dry run.
            self.verbose_checkbox.setChecked(False)

    @staticmethod
    def _parse_formid_line(line: str) -> tuple[str, str, str] | None:
        """Parse a FormID line and return plugin, formid, entry or None if invalid.

        Args:
            line: A line from the FormID list file in "plugin | formid | entry" format.

        Returns:
            A tuple of (plugin, formid, entry) if the line is valid, or None if the
            line is malformed or doesn't match the expected format.
        """
        line = line.strip()
        if " | " not in line:
            return None

        parts = line.split(" | ", maxsplit=2)
        if len(parts) != 3:
            return None

        return parts[0], parts[1], parts[2]

    def _get_process_config(self) -> dict[str, Any]:  # pyright: ignore[reportUnknownParameterType]
        """Get all configuration values for processing.

        Returns:
            A dictionary containing processing configuration with keys:
                - game (str): Selected game name (Fallout4, Skyrim, or Starfield)
                - file_path (Path): Path to the FormID list file
                - db_path (Path): Path to the target database file
                - update_mode (bool): Whether to replace existing entries
                - verbose (bool): Whether to log detailed per-entry information
                - dry_run (bool): Whether to preview changes without modifying database
        """
        game = self.game_combo.currentText()
        return {
            "game": game,
            "file_path": Path(self.file_path.text()),
            "db_path": Path(self.db_path.text()) if self.db_path.text() != self.db_path.placeholderText() else Path.cwd() / f"{game}.db",
            "update_mode": self.mode_checkbox.isChecked(),
            "verbose": self.verbose_checkbox.isChecked(),
            "dry_run": self.dry_run_checkbox.isChecked(),
        }

    def _validate_inputs(self, config: dict[str, Any]) -> bool:
        """Validate input file and database path.

        Args:
            config: Configuration dictionary containing 'file_path' and 'db_path' keys.

        Returns:
            True if validation passes (file exists and database path is valid),
            False otherwise.
        """
        file_path = config["file_path"]
        db_path = config["db_path"]

        if not file_path.exists() or self.file_path.text() == self.file_path.placeholderText():
            self.log("Error: FormID list file not found")
            return False

        if not db_path.parent.exists():
            self.log("Error: Database file not found, creating in current directory.")
            db_path.touch()

        return True

    def _ensure_database_structure(self, conn: sqlite3.Connection, game: str, dry_run: bool) -> bool:
        """Ensure database table and index exist.

        Args:
            conn: Active SQLite database connection.
            game: Name of the game (used as table name).
            dry_run: If True, only logs what would be done without making changes.

        Returns:
            True if database structure was successfully verified/created,
            False if a DatabaseError occurred during setup.
        """
        try:
            cursor = conn.cursor()

            # Check table existence
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{game}'")
            table_exists = cursor.fetchone() is not None

            # Check index existence
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{game}_index'")
            index_exists = cursor.fetchone() is not None

            # Create table if needed
            if not table_exists:
                msg = "Would create" if dry_run else "Creating"
                self.log(f"{msg} table {game}...")
                if not dry_run:
                    conn.execute(
                        f"""CREATE TABLE IF NOT EXISTS {game}
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plugin TEXT, formid TEXT, entry TEXT)"""
                    )

            # Create index if needed
            if not index_exists:
                msg = "Would create" if dry_run else "Creating"
                self.log(f"{msg} index {game}_index...")
                if not dry_run:
                    conn.execute(f"CREATE INDEX IF NOT EXISTS {game}_index ON {game} (formid, plugin COLLATE nocase);")

            if not dry_run and conn.in_transaction:
                conn.commit()

        except sqlite3.DatabaseError as e:
            self.log(f"Error during database setup: {e!s}")
            return False
        else:
            return True

    def _perform_dry_run(self, file_path: Path, update_mode: bool) -> None:
        """Perform a dry run analysis of the FormID file."""
        plugins_to_process = set()  # pyright: ignore[reportUnknownVariableType]
        entry_count = 0

        with file_path.open(encoding="utf-8", errors="ignore") as f:
            for line in f:
                parsed = self._parse_formid_line(line)
                if parsed:
                    plugin, _, _ = parsed
                    plugins_to_process.add(plugin)  # pyright: ignore[reportUnknownMemberType]
                    entry_count += 1

        # Report dry run summary
        self.log("\nDry run summary:")
        self.log(f"Found {entry_count} valid entries to process")
        self.log(f"Found {len(plugins_to_process)} unique plugins:")  # pyright: ignore[reportUnknownArgumentType]

        for plugin in sorted(plugins_to_process):  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
            if update_mode:
                self.log(f"- Would delete existing entries for {plugin}")
            self.log(f"- Would add entries from {plugin}")

        self.log("\nNo changes were made to the database (dry run mode)")

    def _process_formid_entries(self, conn: sqlite3.Connection, file_path: Path, game: str, update_mode: bool, verbose: bool) -> None:
        """Process FormID entries and update database."""
        cursor = conn.cursor()
        self.log(f"Processing FormIDs from {file_path} for {game}")

        plugins_deleted = set()  # pyright: ignore[reportUnknownVariableType]
        plugins_announced = set()  # pyright: ignore[reportUnknownVariableType]

        with file_path.open(encoding="utf-8", errors="ignore") as f:
            for line in f:
                parsed = self._parse_formid_line(line)
                if not parsed:
                    continue

                plugin, formid, entry = parsed

                # Handle update mode deletions
                if update_mode and plugin not in plugins_deleted:
                    self.log(f"Deleting {plugin}'s FormIDs from {game}")
                    cursor.execute(f"DELETE FROM {game} WHERE plugin = ?", (plugin,))
                    plugins_deleted.add(plugin)  # pyright: ignore[reportUnknownMemberType]

                # Log additions
                if update_mode and plugin not in plugins_announced and not verbose:
                    self.log(f"Adding {plugin}'s FormIDs to {game}")
                    plugins_announced.add(plugin)  # pyright: ignore[reportUnknownMemberType]

                if verbose:
                    self.log(f"Adding {line.strip()} to {game}")

                # Insert new entry
                cursor.execute(
                    f"INSERT INTO {game} (plugin, formid, entry) VALUES (?, ?, ?)",
                    (plugin, formid, entry),
                )

        if conn.in_transaction:
            conn.commit()

        self.log("Optimizing database...")
        cursor.execute("vacuum")
        self.log("Processing completed successfully!")

    def process_formids(self) -> None:
        """Process FormIDs from file and update database."""
        # Get configuration
        config = self._get_process_config()

        if config["dry_run"]:
            self.log("DRY RUN MODE - No changes will be made to the database")

        # Validate inputs
        if not self._validate_inputs(config):
            return

        try:
            # Setup database structure
            with sqlite3.connect(config["db_path"]) as conn:
                if not self._ensure_database_structure(conn, config["game"], config["dry_run"]):
                    return

            # Perform dry run if requested
            if config["dry_run"]:
                self._perform_dry_run(config["file_path"], config["update_mode"])
                return

            # Process actual FormID entries
            with sqlite3.connect(config["db_path"]) as conn:
                self._process_formid_entries(conn, config["file_path"], config["game"], config["update_mode"], config["verbose"])

        except (OSError, sqlite3.DatabaseError) as e:
            self.log(f"Error during processing: {e!s}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FormIDManager()
    window.show()
    sys.exit(app.exec())
