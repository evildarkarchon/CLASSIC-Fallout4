import sqlite3
import sys
from pathlib import Path

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
    def __init__(self) -> None:
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
        layout = QHBoxLayout()

        self.game_label = QLabel("Game:")
        self.game_combo = QComboBox()
        self.game_combo.addItems(["Fallout4", "Skyrim", "Starfield"])

        layout.addWidget(self.game_label)
        layout.addWidget(self.game_combo)
        layout.addStretch()

        self.main_layout.addLayout(layout)

    def create_mode_selection(self) -> None:
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
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.main_layout.addWidget(self.log_area)

    def create_process_button(self) -> None:
        self.process_btn = QPushButton("Process FormIDs")
        self.process_btn.clicked.connect(self.process_formids)
        self.main_layout.addWidget(self.process_btn)

    def select_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select FormID List", "", "Text Files (*.txt)")
        if file_path:
            self.file_path.setText(str(file_path))

    def select_database(self) -> None:
        db_path, _ = QFileDialog.getOpenFileName(self, "Select Database", "", "Database Files (*.db)")
        if db_path:
            self.db_path.setText(str(db_path))

    def log(self, message: str) -> None:
        self.log_area.append(message)
        QApplication.processEvents()  # Ensures UI updates during processing

    def switch_verbose_checkbox_enabled(self) -> None:
        self.verbose_checkbox.setEnabled(not self.dry_run_checkbox.isChecked())
        if self.dry_run_checkbox.isChecked():  # Doing it this way because I don't want to automatically check it when disabling dry run.
            self.verbose_checkbox.setChecked(False)

    def _parse_formid_line(self, line: str) -> tuple[str, str, str] | None:
        """Parse a FormID line and return plugin, formid, entry or None if invalid."""
        line = line.strip()
        if " | " not in line:
            return None

        parts = line.split(" | ", maxsplit=2)
        if len(parts) != 3:
            return None

        return parts[0], parts[1], parts[2]

    def _get_process_config(self) -> dict[str, Any]:
        """Get all configuration values for processing."""
        game = self.game_combo.currentText()
        return {
            "game": game,
            "file_path": Path(self.file_path.text()),
            "db_path": Path(self.db_path.text()) if self.db_path.text() != self.db_path.placeholderText()
                       else Path.cwd() / f"{game}.db",
            "update_mode": self.mode_checkbox.isChecked(),
            "verbose": self.verbose_checkbox.isChecked(),
            "dry_run": self.dry_run_checkbox.isChecked(),
        }

    def _validate_inputs(self, config: dict[str, Any]) -> bool:
        """Validate input file and database path."""
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
        """Ensure database table and index exist."""
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

            return True

        except sqlite3.DatabaseError as e:
            self.log(f"Error during database setup: {e!s}")
            return False

    def _perform_dry_run(self, file_path: Path, update_mode: bool) -> None:
        """Perform a dry run analysis of the FormID file."""
        plugins_to_process = set()
        entry_count = 0

        with file_path.open(encoding="utf-8", errors="ignore") as f:
            for line in f:
                parsed = self._parse_formid_line(line)
                if parsed:
                    plugin, _, _ = parsed
                    plugins_to_process.add(plugin)
                    entry_count += 1

        # Report dry run summary
        self.log("\nDry run summary:")
        self.log(f"Found {entry_count} valid entries to process")
        self.log(f"Found {len(plugins_to_process)} unique plugins:")

        for plugin in sorted(plugins_to_process):
            if update_mode:
                self.log(f"- Would delete existing entries for {plugin}")
            self.log(f"- Would add entries from {plugin}")

        self.log("\nNo changes were made to the database (dry run mode)")

    def _process_formid_entries(
        self, conn: sqlite3.Connection, file_path: Path,
        game: str, update_mode: bool, verbose: bool
    ) -> None:
        """Process FormID entries and update database."""
        cursor = conn.cursor()
        self.log(f"Processing FormIDs from {file_path} for {game}")

        plugins_deleted = set()
        plugins_announced = set()

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
                    plugins_deleted.add(plugin)

                # Log additions
                if update_mode and plugin not in plugins_announced and not verbose:
                    self.log(f"Adding {plugin}'s FormIDs to {game}")
                    plugins_announced.add(plugin)

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
                self._process_formid_entries(
                    conn, config["file_path"], config["game"],
                    config["update_mode"], config["verbose"]
                )

        except (OSError, sqlite3.DatabaseError) as e:
            self.log(f"Error during processing: {e!s}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FormIDManager()
    window.show()
    sys.exit(app.exec())
