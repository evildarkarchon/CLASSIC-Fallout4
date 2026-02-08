"""Unit tests for FormID database path functions in constants.py.

Tests cover:
- get_main_db_path(): Returns the Main FormID database path for the current game
- get_user_db_paths(): Reads user-configured database paths from YAML settings
- get_all_db_paths(): Combines Main + user databases
- _DBPaths backward-compat wrapper delegates to get_all_db_paths()
- _DEFAULT_FORMID_DATABASES dict provides fallback defaults
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# Patch targets: these are the source modules where the names are defined,
# since get_main_db_path / get_user_db_paths use local imports.
_REGISTRY = "ClassicLib.core.registry.GlobalRegistry"
_RESOURCE_LOADER = "ClassicLib.support.resources.ResourceLoader"
_YAML_SETTINGS = "ClassicLib.io.yaml.convenience.yaml_settings"
_LOGGER = "ClassicLib.core.logger.logger"


@pytest.mark.unit
class TestGetMainDbPath:
    """Tests for get_main_db_path()."""

    def test_returns_path_for_fallout4(self) -> None:
        """Main db path uses game name from GlobalRegistry."""
        from ClassicLib.core.constants import get_main_db_path

        fake_data_dir = Path("/fake/CLASSIC Data")
        with (
            patch(_REGISTRY) as mock_registry,
            patch(_RESOURCE_LOADER) as mock_loader,
        ):
            mock_registry.get_game.return_value = "Fallout4"
            mock_loader.get_data_directory.return_value = fake_data_dir

            result = get_main_db_path()

        assert result == fake_data_dir / "databases" / "Fallout4 FormIDs Main.db"
        assert isinstance(result, Path)

    def test_returns_path_for_skyrim(self) -> None:
        """Main db path adapts to Skyrim game."""
        from ClassicLib.core.constants import get_main_db_path

        fake_data_dir = Path("/fake/CLASSIC Data")
        with (
            patch(_REGISTRY) as mock_registry,
            patch(_RESOURCE_LOADER) as mock_loader,
        ):
            mock_registry.get_game.return_value = "Skyrim"
            mock_loader.get_data_directory.return_value = fake_data_dir

            result = get_main_db_path()

        assert result == fake_data_dir / "databases" / "Skyrim FormIDs Main.db"


@pytest.mark.unit
class TestDefaultFormidDatabases:
    """Tests for the _DEFAULT_FORMID_DATABASES constant."""

    def test_fallout4_has_folon_default(self) -> None:
        """Fallout4 defaults include FOLON FormIDs.db."""
        from ClassicLib.core.constants import _DEFAULT_FORMID_DATABASES

        assert "Fallout4" in _DEFAULT_FORMID_DATABASES
        assert _DEFAULT_FORMID_DATABASES["Fallout4"] == ["databases/FOLON FormIDs.db"]

    def test_skyrim_has_empty_default(self) -> None:
        """Skyrim defaults to no extra databases."""
        from ClassicLib.core.constants import _DEFAULT_FORMID_DATABASES

        assert "Skyrim" in _DEFAULT_FORMID_DATABASES
        assert _DEFAULT_FORMID_DATABASES["Skyrim"] == []


@pytest.mark.unit
class TestGetUserDbPaths:
    """Tests for get_user_db_paths()."""

    def test_returns_resolved_paths_from_yaml(self, tmp_path: Path) -> None:
        """User db paths are resolved relative to data directory."""
        from ClassicLib.core.constants import get_user_db_paths

        # Create a fake db file so it passes the exists check
        db_file = tmp_path / "databases" / "FOLON FormIDs.db"
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.touch()

        with (
            patch(_REGISTRY) as mock_registry,
            patch(_RESOURCE_LOADER) as mock_loader,
            patch(_YAML_SETTINGS) as mock_yaml,
        ):
            mock_registry.get_game.return_value = "Fallout4"
            mock_loader.get_data_directory.return_value = tmp_path
            mock_yaml.return_value = ["databases/FOLON FormIDs.db"]

            result = get_user_db_paths()

        assert result == [db_file]

    def test_absolute_paths_used_as_is(self, tmp_path: Path) -> None:
        """Absolute paths in YAML settings are not resolved against data dir."""
        from ClassicLib.core.constants import get_user_db_paths

        db_file = tmp_path / "my_custom.db"
        db_file.touch()

        with (
            patch(_REGISTRY) as mock_registry,
            patch(_RESOURCE_LOADER) as mock_loader,
            patch(_YAML_SETTINGS) as mock_yaml,
        ):
            mock_registry.get_game.return_value = "Fallout4"
            mock_loader.get_data_directory.return_value = tmp_path
            mock_yaml.return_value = [str(db_file)]

            result = get_user_db_paths()

        assert result == [db_file]

    def test_missing_files_filtered_with_warning(self, tmp_path: Path) -> None:
        """Missing database files are excluded and a warning is logged."""
        from ClassicLib.core.constants import get_user_db_paths

        with (
            patch(_REGISTRY) as mock_registry,
            patch(_RESOURCE_LOADER) as mock_loader,
            patch(_YAML_SETTINGS) as mock_yaml,
            patch(_LOGGER) as mock_logger,
        ):
            mock_registry.get_game.return_value = "Fallout4"
            mock_loader.get_data_directory.return_value = tmp_path
            mock_yaml.return_value = ["databases/nonexistent.db"]

            result = get_user_db_paths()

        assert result == []
        mock_logger.warning.assert_called_once()

    def test_uses_defaults_when_yaml_returns_none(self, tmp_path: Path) -> None:
        """When YAML key is missing, _DEFAULT_FORMID_DATABASES provides fallback."""
        from ClassicLib.core.constants import get_user_db_paths

        # Create the default FOLON db so it passes the exists check
        db_file = tmp_path / "databases" / "FOLON FormIDs.db"
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.touch()

        with (
            patch(_REGISTRY) as mock_registry,
            patch(_RESOURCE_LOADER) as mock_loader,
            patch(_YAML_SETTINGS) as mock_yaml,
        ):
            mock_registry.get_game.return_value = "Fallout4"
            mock_loader.get_data_directory.return_value = tmp_path
            mock_yaml.return_value = None  # YAML key missing

            result = get_user_db_paths()

        assert result == [db_file]

    def test_defaults_for_unknown_game_is_empty(self, tmp_path: Path) -> None:
        """Unknown games with no YAML config get empty user db list."""
        from ClassicLib.core.constants import get_user_db_paths

        with (
            patch(_REGISTRY) as mock_registry,
            patch(_RESOURCE_LOADER) as mock_loader,
            patch(_YAML_SETTINGS) as mock_yaml,
        ):
            mock_registry.get_game.return_value = "UnknownGame"
            mock_loader.get_data_directory.return_value = tmp_path
            mock_yaml.return_value = None

            result = get_user_db_paths()

        assert result == []

    def test_reads_correct_yaml_key_path(self, tmp_path: Path) -> None:
        """yaml_settings is called with the correct key path for the game."""
        from ClassicLib.core.constants import YAML, get_user_db_paths

        with (
            patch(_REGISTRY) as mock_registry,
            patch(_RESOURCE_LOADER) as mock_loader,
            patch(_YAML_SETTINGS) as mock_yaml,
        ):
            mock_registry.get_game.return_value = "Fallout4"
            mock_loader.get_data_directory.return_value = tmp_path
            mock_yaml.return_value = []

            get_user_db_paths()

        mock_yaml.assert_called_once_with(list, YAML.Settings, "CLASSIC_Settings.FormID Databases.Fallout4")

    def test_empty_yaml_list_returns_empty(self, tmp_path: Path) -> None:
        """An empty list from YAML returns empty user paths."""
        from ClassicLib.core.constants import get_user_db_paths

        with (
            patch(_REGISTRY) as mock_registry,
            patch(_RESOURCE_LOADER) as mock_loader,
            patch(_YAML_SETTINGS) as mock_yaml,
        ):
            mock_registry.get_game.return_value = "Fallout4"
            mock_loader.get_data_directory.return_value = tmp_path
            mock_yaml.return_value = []

            result = get_user_db_paths()

        assert result == []

    def test_mixed_existing_and_missing_files(self, tmp_path: Path) -> None:
        """Only existing files are returned; missing ones are filtered."""
        from ClassicLib.core.constants import get_user_db_paths

        existing = tmp_path / "databases" / "good.db"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.touch()

        with (
            patch(_REGISTRY) as mock_registry,
            patch(_RESOURCE_LOADER) as mock_loader,
            patch(_YAML_SETTINGS) as mock_yaml,
            patch(_LOGGER),
        ):
            mock_registry.get_game.return_value = "Fallout4"
            mock_loader.get_data_directory.return_value = tmp_path
            mock_yaml.return_value = [
                "databases/good.db",
                "databases/missing.db",
            ]

            result = get_user_db_paths()

        assert result == [existing]


@pytest.mark.unit
class TestGetAllDbPaths:
    """Tests for get_all_db_paths()."""

    def test_combines_main_and_user_paths(self, tmp_path: Path) -> None:
        """get_all_db_paths() returns Main path followed by user paths."""
        from ClassicLib.core.constants import get_all_db_paths

        main_db = tmp_path / "databases" / "Fallout4 FormIDs Main.db"
        user_db = tmp_path / "databases" / "FOLON FormIDs.db"

        with (
            patch(
                "ClassicLib.core.constants.get_main_db_path",
                return_value=main_db,
            ),
            patch(
                "ClassicLib.core.constants.get_user_db_paths",
                return_value=[user_db],
            ),
        ):
            result = get_all_db_paths()

        assert result == [main_db, user_db]

    def test_main_only_when_no_user_paths(self, tmp_path: Path) -> None:
        """When no user databases, list contains only the Main path."""
        from ClassicLib.core.constants import get_all_db_paths

        main_db = tmp_path / "databases" / "Fallout4 FormIDs Main.db"

        with (
            patch(
                "ClassicLib.core.constants.get_main_db_path",
                return_value=main_db,
            ),
            patch(
                "ClassicLib.core.constants.get_user_db_paths",
                return_value=[],
            ),
        ):
            result = get_all_db_paths()

        assert result == [main_db]


@pytest.mark.unit
class TestDBPathsBackwardCompat:
    """Tests for the _DBPaths backward-compatibility wrapper."""

    def test_iter_delegates_to_get_all_db_paths(self, tmp_path: Path) -> None:
        """Iterating DB_PATHS yields results from get_all_db_paths()."""
        from ClassicLib.core.constants import DB_PATHS

        main_db = tmp_path / "main.db"
        user_db = tmp_path / "user.db"

        with patch(
            "ClassicLib.core.constants.get_all_db_paths",
            return_value=[main_db, user_db],
        ):
            result = list(DB_PATHS)

        assert result == [main_db, user_db]

    def test_getitem_delegates_to_get_all_db_paths(self, tmp_path: Path) -> None:
        """Indexing DB_PATHS delegates to get_all_db_paths()."""
        from ClassicLib.core.constants import DB_PATHS

        main_db = tmp_path / "main.db"
        user_db = tmp_path / "user.db"

        with patch(
            "ClassicLib.core.constants.get_all_db_paths",
            return_value=[main_db, user_db],
        ):
            assert DB_PATHS[0] == main_db
            assert DB_PATHS[1] == user_db

    def test_len_delegates_to_get_all_db_paths(self, tmp_path: Path) -> None:
        """len(DB_PATHS) returns count from get_all_db_paths()."""
        from ClassicLib.core.constants import DB_PATHS

        with patch(
            "ClassicLib.core.constants.get_all_db_paths",
            return_value=[tmp_path / "a.db", tmp_path / "b.db", tmp_path / "c.db"],
        ):
            assert len(DB_PATHS) == 3
