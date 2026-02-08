"""Unit tests for the FormID database list widget in Settings dialog.

Tests the QListWidget and Add/Remove buttons added to the Paths tab of the
Settings dialog, including load/save operations for the database list and
duplicate-prevention logic in the add handler.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip entire module if PySide6 is not available
PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QListWidget, QPushButton

from ClassicLib.core.constants import YAML
from ClassicLib.Interface.Settings.dialog import SettingsDialog


@pytest.mark.unit
@pytest.mark.gui
class TestDatabaseListWidget:
    """Tests for the database list widget in the Paths tab."""

    def test_paths_tab_contains_database_list(self, gui_settings_dialog: SettingsDialog) -> None:
        """The Paths tab should include a QListWidget keyed as 'database_list'."""
        widget = gui_settings_dialog.settings_widgets.get("database_list")
        assert widget is not None, "database_list widget not found in settings_widgets"
        assert isinstance(widget, QListWidget), (
            f"Expected QListWidget, got {type(widget).__name__}"
        )

    def test_paths_tab_has_add_button(self, gui_settings_dialog: SettingsDialog) -> None:
        """The Paths tab should have an Add button keyed as 'db_add_button'."""
        widget = gui_settings_dialog.settings_widgets.get("db_add_button")
        assert widget is not None, "db_add_button widget not found in settings_widgets"
        assert isinstance(widget, QPushButton), (
            f"Expected QPushButton, got {type(widget).__name__}"
        )

    def test_paths_tab_has_remove_button(self, gui_settings_dialog: SettingsDialog) -> None:
        """The Paths tab should have a Remove button keyed as 'db_remove_button'."""
        widget = gui_settings_dialog.settings_widgets.get("db_remove_button")
        assert widget is not None, "db_remove_button widget not found in settings_widgets"
        assert isinstance(widget, QPushButton), (
            f"Expected QPushButton, got {type(widget).__name__}"
        )

    def test_remove_button_starts_disabled(self, gui_settings_dialog: SettingsDialog) -> None:
        """The Remove button should start disabled (no selection)."""
        remove_btn = gui_settings_dialog.settings_widgets.get("db_remove_button")
        assert isinstance(remove_btn, QPushButton)
        assert not remove_btn.isEnabled(), "Remove button should start disabled"

    def test_add_button_max_width(self, gui_settings_dialog: SettingsDialog) -> None:
        """The Add button should have a maximum width of 100."""
        add_btn = gui_settings_dialog.settings_widgets.get("db_add_button")
        assert isinstance(add_btn, QPushButton)
        assert add_btn.maximumWidth() == 100

    def test_remove_button_max_width(self, gui_settings_dialog: SettingsDialog) -> None:
        """The Remove button should have a maximum width of 100."""
        remove_btn = gui_settings_dialog.settings_widgets.get("db_remove_button")
        assert isinstance(remove_btn, QPushButton)
        assert remove_btn.maximumWidth() == 100


@pytest.mark.unit
@pytest.mark.gui
class TestDatabaseListLoadSave:
    """Tests for loading and saving the database list in the dialog."""

    def test_load_populates_list(self, gui_settings_dialog: SettingsDialog, gui_settings_mock_cache: MagicMock) -> None:
        """load_database_list should populate the QListWidget from YAML settings."""
        db_list = gui_settings_dialog.settings_widgets.get("database_list")
        assert isinstance(db_list, QListWidget)

        # Pre-populate mock cache with database paths for the game
        with patch("ClassicLib.core.registry.get_game", return_value="Fallout4"):
            gui_settings_mock_cache.store[
                (gui_settings_dialog.yaml_store, "CLASSIC_Settings.FormID Databases.Fallout4")
            ] = [
                "C:/databases/formids.db",
                "C:/databases/extra.sqlite",
            ]
            gui_settings_dialog.load_database_list()

        assert db_list.count() == 2
        assert db_list.item(0).text() == "C:/databases/formids.db"
        assert db_list.item(1).text() == "C:/databases/extra.sqlite"

    def test_load_clears_existing_items(self, gui_settings_dialog: SettingsDialog, gui_settings_mock_cache: MagicMock) -> None:
        """load_database_list should clear existing items before populating."""
        db_list = gui_settings_dialog.settings_widgets.get("database_list")
        assert isinstance(db_list, QListWidget)

        # Add some items manually
        db_list.addItem("old_item.db")
        assert db_list.count() == 1

        # Now load with empty list
        with patch("ClassicLib.core.registry.get_game", return_value="Fallout4"):
            gui_settings_dialog.load_database_list()

        assert db_list.count() == 0

    def test_load_handles_none(self, gui_settings_dialog: SettingsDialog, gui_settings_mock_cache: MagicMock) -> None:
        """load_database_list should handle None (missing key) gracefully."""
        db_list = gui_settings_dialog.settings_widgets.get("database_list")
        assert isinstance(db_list, QListWidget)

        with patch("ClassicLib.core.registry.get_game", return_value="Fallout4"):
            # No entry in mock cache => returns None
            gui_settings_dialog.load_database_list()

        assert db_list.count() == 0

    def test_save_writes_list_to_yaml(self, gui_settings_dialog: SettingsDialog, gui_settings_mock_cache: MagicMock) -> None:
        """save_database_list should write the QListWidget contents to YAML settings."""
        db_list = gui_settings_dialog.settings_widgets.get("database_list")
        assert isinstance(db_list, QListWidget)

        # Add items to the list widget
        db_list.addItem("C:/databases/formids.db")
        db_list.addItem("C:/databases/extra.sqlite")

        with patch("ClassicLib.core.registry.get_game", return_value="Fallout4"):
            gui_settings_dialog.save_database_list()

        # Verify the mock cache was written to
        key = (gui_settings_dialog.yaml_store, "CLASSIC_Settings.FormID Databases.Fallout4")
        assert key in gui_settings_mock_cache.store
        saved_value = gui_settings_mock_cache.store[key]
        assert saved_value == ["C:/databases/formids.db", "C:/databases/extra.sqlite"]

    def test_save_writes_empty_list(self, gui_settings_dialog: SettingsDialog, gui_settings_mock_cache: MagicMock) -> None:
        """save_database_list should save an empty list when no items are present."""
        db_list = gui_settings_dialog.settings_widgets.get("database_list")
        assert isinstance(db_list, QListWidget)
        assert db_list.count() == 0

        with patch("ClassicLib.core.registry.get_game", return_value="Fallout4"):
            gui_settings_dialog.save_database_list()

        key = (gui_settings_dialog.yaml_store, "CLASSIC_Settings.FormID Databases.Fallout4")
        assert key in gui_settings_mock_cache.store
        assert gui_settings_mock_cache.store[key] == []


@pytest.mark.unit
@pytest.mark.gui
class TestDatabaseListAddRemove:
    """Tests for add/remove behavior of the database list."""

    def test_add_databases_populates_list(self, gui_settings_dialog: SettingsDialog) -> None:
        """_add_databases should add selected files to the QListWidget."""
        db_list = gui_settings_dialog.settings_widgets.get("database_list")
        assert isinstance(db_list, QListWidget)

        mock_files = [
            "C:/databases/formids.db",
            "C:/databases/extra.sqlite",
        ]
        with patch(
            "ClassicLib.Interface.Settings.dialog.QFileDialog.getOpenFileNames",
            return_value=(mock_files, ""),
        ):
            gui_settings_dialog._add_databases()

        assert db_list.count() == 2
        assert db_list.item(0).text() == "C:/databases/formids.db"
        assert db_list.item(1).text() == "C:/databases/extra.sqlite"

    def test_add_databases_skips_duplicates(self, gui_settings_dialog: SettingsDialog) -> None:
        """Adding a database that is already in the list should be skipped."""
        db_list = gui_settings_dialog.settings_widgets.get("database_list")
        assert isinstance(db_list, QListWidget)

        # Pre-populate with one item
        db_list.addItem("C:/databases/formids.db")
        assert db_list.count() == 1

        # Try to add the same item plus a new one
        mock_files = [
            "C:/databases/formids.db",
            "C:/databases/extra.sqlite",
        ]
        with patch(
            "ClassicLib.Interface.Settings.dialog.QFileDialog.getOpenFileNames",
            return_value=(mock_files, ""),
        ):
            gui_settings_dialog._add_databases()

        assert db_list.count() == 2, "Duplicate should not be added"
        texts = [db_list.item(i).text() for i in range(db_list.count())]
        assert texts == ["C:/databases/formids.db", "C:/databases/extra.sqlite"]

    def test_add_databases_cancel(self, gui_settings_dialog: SettingsDialog) -> None:
        """Cancelling the file dialog should not modify the list."""
        db_list = gui_settings_dialog.settings_widgets.get("database_list")
        assert isinstance(db_list, QListWidget)

        with patch(
            "ClassicLib.Interface.Settings.dialog.QFileDialog.getOpenFileNames",
            return_value=([], ""),
        ):
            gui_settings_dialog._add_databases()

        assert db_list.count() == 0

    def test_remove_database_removes_selected(self, gui_settings_dialog: SettingsDialog) -> None:
        """_remove_database should remove the selected items from the list."""
        db_list = gui_settings_dialog.settings_widgets.get("database_list")
        assert isinstance(db_list, QListWidget)

        db_list.addItem("C:/databases/formids.db")
        db_list.addItem("C:/databases/extra.sqlite")
        assert db_list.count() == 2

        # Select the first item
        db_list.setCurrentRow(0)
        gui_settings_dialog._remove_database()

        assert db_list.count() == 1
        assert db_list.item(0).text() == "C:/databases/extra.sqlite"

    def test_selection_enables_remove_button(self, gui_settings_dialog: SettingsDialog) -> None:
        """Selecting an item in the list should enable the Remove button."""
        db_list = gui_settings_dialog.settings_widgets.get("database_list")
        remove_btn = gui_settings_dialog.settings_widgets.get("db_remove_button")
        assert isinstance(db_list, QListWidget)
        assert isinstance(remove_btn, QPushButton)

        # Initially disabled
        assert not remove_btn.isEnabled()

        # Add an item and select it
        db_list.addItem("C:/databases/formids.db")
        db_list.setCurrentRow(0)

        # The signal should have fired and enabled the button
        assert remove_btn.isEnabled()

    def test_clearing_selection_disables_remove_button(self, gui_settings_dialog: SettingsDialog) -> None:
        """Clearing the selection should disable the Remove button."""
        db_list = gui_settings_dialog.settings_widgets.get("database_list")
        remove_btn = gui_settings_dialog.settings_widgets.get("db_remove_button")
        assert isinstance(db_list, QListWidget)
        assert isinstance(remove_btn, QPushButton)

        # Add and select an item
        db_list.addItem("C:/databases/formids.db")
        db_list.setCurrentRow(0)
        assert remove_btn.isEnabled()

        # Clear selection
        db_list.clearSelection()

        assert not remove_btn.isEnabled()
