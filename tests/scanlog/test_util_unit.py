"""Unit tests for ClassicLib.ScanLog.Util module.

This module tests the utility functions for managing SQLite database connections,
file operations, and directory path handling used in crash log scanning.

Test coverage includes:
- SyncDatabasePool singleton and connection management
- Directory and file operations (ensure_directory_exists, move_files, copy_files)
- Path setting utilities (get_path_from_setting, is_valid_custom_scan_path)
- Crash log file collection (crashlogs_get_files with Rust/Python fallback)
- Database entry lookup with caching (get_entry)
"""

import os
import platform
import sqlite3
import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# SyncDatabasePool Tests
# ============================================================================


@pytest.mark.unit
class TestSyncDatabasePool:
    """Tests for SyncDatabasePool singleton and connection management."""

    def test_get_instance_returns_singleton(self) -> None:
        """SyncDatabasePool should return the same instance on repeated calls."""
        from ClassicLib.ScanLog.Util import SyncDatabasePool

        # Reset singleton for testing
        SyncDatabasePool._instance = None

        instance1 = SyncDatabasePool.get_instance()
        instance2 = SyncDatabasePool.get_instance()

        assert instance1 is instance2
        assert isinstance(instance1, SyncDatabasePool)

    def test_get_instance_thread_safe(self) -> None:
        """SyncDatabasePool singleton should be thread-safe."""
        from ClassicLib.ScanLog.Util import SyncDatabasePool

        # Reset singleton for testing
        SyncDatabasePool._instance = None

        instances: list[SyncDatabasePool] = []

        def get_instance() -> None:
            instances.append(SyncDatabasePool.get_instance())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same
        assert len(set(id(i) for i in instances)) == 1

    def test_get_connection_creates_new_connection(self, tmp_path: Path) -> None:
        """get_connection should create a new connection for a new database path."""
        from ClassicLib.ScanLog.Util import SyncDatabasePool

        db_path = tmp_path / "test.db"
        # Create the database file
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.close()

        pool = SyncDatabasePool()
        connection = pool.get_connection(db_path)

        assert isinstance(connection, sqlite3.Connection)
        assert connection.row_factory == sqlite3.Row

        pool.close_all()

    def test_get_connection_reuses_existing_connection(self, tmp_path: Path) -> None:
        """get_connection should reuse an existing connection for the same path."""
        from ClassicLib.ScanLog.Util import SyncDatabasePool

        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.close()

        pool = SyncDatabasePool()
        conn1 = pool.get_connection(db_path)
        conn2 = pool.get_connection(db_path)

        assert conn1 is conn2

        pool.close_all()

    def test_get_connection_recreates_dead_connection(self, tmp_path: Path) -> None:
        """get_connection should create a new connection if the existing one is dead."""
        from ClassicLib.ScanLog.Util import SyncDatabasePool

        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.close()

        pool = SyncDatabasePool()
        conn1 = pool.get_connection(db_path)

        # Close the connection to simulate a dead connection
        conn1.close()

        # Force recreation by accessing the connection
        conn2 = pool.get_connection(db_path)

        # conn2 should be a new connection (conn1 was closed)
        assert conn2 is not conn1

        pool.close_all()

    def test_is_connection_alive_returns_true_for_alive(self, tmp_path: Path) -> None:
        """_is_connection_alive should return True for a healthy connection."""
        from ClassicLib.ScanLog.Util import SyncDatabasePool

        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)

        result = SyncDatabasePool._is_connection_alive(conn)

        assert result is True
        conn.close()

    def test_is_connection_alive_returns_false_for_closed(self, tmp_path: Path) -> None:
        """_is_connection_alive should return False for a closed connection."""
        from ClassicLib.ScanLog.Util import SyncDatabasePool

        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.close()

        result = SyncDatabasePool._is_connection_alive(conn)

        assert result is False

    def test_close_all_closes_all_connections(self, tmp_path: Path) -> None:
        """close_all should close all connections in the pool."""
        from ClassicLib.ScanLog.Util import SyncDatabasePool

        db1 = tmp_path / "test1.db"
        db2 = tmp_path / "test2.db"

        # Create database files
        for db in [db1, db2]:
            conn = sqlite3.connect(db)
            conn.close()

        pool = SyncDatabasePool()
        conn1 = pool.get_connection(db1)
        conn2 = pool.get_connection(db2)

        assert len(pool._connections) == 2

        pool.close_all()

        assert len(pool._connections) == 0


# ============================================================================
# Directory and File Operation Tests
# ============================================================================


@pytest.mark.unit
class TestEnsureDirectoryExists:
    """Tests for ensure_directory_exists function."""

    def test_creates_directory_if_not_exists(self, tmp_path: Path) -> None:
        """ensure_directory_exists should create directory if it doesn't exist."""
        from ClassicLib.ScanLog.Util import ensure_directory_exists

        new_dir = tmp_path / "new_directory"
        assert not new_dir.exists()

        ensure_directory_exists(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_creates_nested_directories(self, tmp_path: Path) -> None:
        """ensure_directory_exists should create nested directories."""
        from ClassicLib.ScanLog.Util import ensure_directory_exists

        nested_dir = tmp_path / "level1" / "level2" / "level3"
        assert not nested_dir.exists()

        ensure_directory_exists(nested_dir)

        assert nested_dir.exists()
        assert nested_dir.is_dir()

    def test_no_error_if_directory_exists(self, tmp_path: Path) -> None:
        """ensure_directory_exists should not raise if directory already exists."""
        from ClassicLib.ScanLog.Util import ensure_directory_exists

        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        assert existing_dir.exists()

        # Should not raise
        ensure_directory_exists(existing_dir)

        assert existing_dir.exists()


@pytest.mark.unit
class TestMoveFiles:
    """Tests for move_files function."""

    def test_moves_matching_files(self, tmp_path: Path) -> None:
        """move_files should move files matching the pattern."""
        from ClassicLib.ScanLog.Util import move_files

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create test files
        (source_dir / "crash-2024-01-01.log").write_text("log1")
        (source_dir / "crash-2024-01-02.log").write_text("log2")
        (source_dir / "other.txt").write_text("other")

        move_files(source_dir, target_dir, "crash-*.log")

        assert not (source_dir / "crash-2024-01-01.log").exists()
        assert not (source_dir / "crash-2024-01-02.log").exists()
        assert (source_dir / "other.txt").exists()  # Not moved
        assert (target_dir / "crash-2024-01-01.log").exists()
        assert (target_dir / "crash-2024-01-02.log").exists()

    def test_does_not_overwrite_existing_files(self, tmp_path: Path) -> None:
        """move_files should not overwrite existing files in target."""
        from ClassicLib.ScanLog.Util import move_files

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create source and existing target file
        (source_dir / "crash-test.log").write_text("source content")
        (target_dir / "crash-test.log").write_text("target content")

        move_files(source_dir, target_dir, "crash-*.log")

        # Source file should still exist (not moved because target exists)
        assert (source_dir / "crash-test.log").exists()
        # Target file should have original content
        assert (target_dir / "crash-test.log").read_text() == "target content"


@pytest.mark.unit
class TestCopyFiles:
    """Tests for copy_files function."""

    def test_copies_matching_files(self, tmp_path: Path) -> None:
        """copy_files should copy files matching the pattern."""
        from ClassicLib.ScanLog.Util import copy_files

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        (source_dir / "crash-2024-01-01.log").write_text("log1")
        (source_dir / "other.txt").write_text("other")

        copy_files(source_dir, target_dir, "crash-*.log")

        assert (source_dir / "crash-2024-01-01.log").exists()  # Still exists
        assert (target_dir / "crash-2024-01-01.log").exists()
        assert not (target_dir / "other.txt").exists()

    def test_does_not_overwrite_existing_files(self, tmp_path: Path) -> None:
        """copy_files should not overwrite existing files in target."""
        from ClassicLib.ScanLog.Util import copy_files

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        (source_dir / "crash-test.log").write_text("source content")
        (target_dir / "crash-test.log").write_text("target content")

        copy_files(source_dir, target_dir, "crash-*.log")

        assert (target_dir / "crash-test.log").read_text() == "target content"

    def test_handles_none_source_dir(self, tmp_path: Path) -> None:
        """copy_files should do nothing if source_dir is None."""
        from ClassicLib.ScanLog.Util import copy_files

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Should not raise
        copy_files(None, target_dir, "*.log")

    def test_handles_nonexistent_source_dir(self, tmp_path: Path) -> None:
        """copy_files should do nothing if source_dir doesn't exist."""
        from ClassicLib.ScanLog.Util import copy_files

        source_dir = tmp_path / "nonexistent"
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Should not raise
        copy_files(source_dir, target_dir, "*.log")


# ============================================================================
# Path Setting Utility Tests
# ============================================================================


@pytest.mark.unit
class TestGetPathFromSetting:
    """Tests for get_path_from_setting function."""

    def test_converts_string_to_path(self) -> None:
        """get_path_from_setting should convert string to Path."""
        from ClassicLib.ScanLog.Util import get_path_from_setting

        result = get_path_from_setting("/some/path")

        assert isinstance(result, Path)
        assert str(result) == "/some/path" or str(result) == "\\some\\path"

    def test_returns_none_for_none(self) -> None:
        """get_path_from_setting should return None for None input."""
        from ClassicLib.ScanLog.Util import get_path_from_setting

        result = get_path_from_setting(None)

        assert result is None

    def test_returns_none_for_non_string(self) -> None:
        """get_path_from_setting should return None for non-string input."""
        from ClassicLib.ScanLog.Util import get_path_from_setting

        result = get_path_from_setting(123)  # type: ignore

        assert result is None


@pytest.mark.unit
class TestIsValidCustomScanPath:
    """Tests for is_valid_custom_scan_path function."""

    def test_returns_false_for_none(self) -> None:
        """is_valid_custom_scan_path should return False for None."""
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        result = is_valid_custom_scan_path(None)

        assert result is False

    def test_returns_false_for_empty_string(self) -> None:
        """is_valid_custom_scan_path should return False for empty string."""
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        result = is_valid_custom_scan_path("")

        assert result is False

    def test_returns_false_for_whitespace_only(self) -> None:
        """is_valid_custom_scan_path should return False for whitespace-only string."""
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        result = is_valid_custom_scan_path("   ")

        assert result is False

    def test_returns_false_for_crash_logs_dir(self, tmp_path: Path) -> None:
        """is_valid_custom_scan_path should return False for Crash Logs directory."""
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        with (
            patch("ClassicLib.GlobalRegistry.get_local_dir", return_value=str(tmp_path)),
            patch("ClassicLib.ScanLog.Util.yaml_settings", return_value=None),
        ):
            crash_logs_dir = tmp_path / "Crash Logs"
            crash_logs_dir.mkdir()

            result = is_valid_custom_scan_path(crash_logs_dir)

            assert result is False

    def test_returns_false_for_pastebin_dir(self, tmp_path: Path) -> None:
        """is_valid_custom_scan_path should return False for Pastebin directory."""
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        with (
            patch("ClassicLib.GlobalRegistry.get_local_dir", return_value=str(tmp_path)),
            patch("ClassicLib.ScanLog.Util.yaml_settings", return_value=None),
        ):
            pastebin_dir = tmp_path / "Crash Logs" / "Pastebin"
            pastebin_dir.mkdir(parents=True)

            result = is_valid_custom_scan_path(pastebin_dir)

            assert result is False

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_returns_false_for_windows_system_dirs(self) -> None:
        """is_valid_custom_scan_path should return False for Windows system directories."""
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        with (
            patch("ClassicLib.GlobalRegistry.get_local_dir", return_value="C:\\Users\\Test"),
            patch("ClassicLib.ScanLog.Util.yaml_settings", return_value=None),
        ):
            system_root = os.environ.get("SystemRoot", r"C:\Windows")

            result = is_valid_custom_scan_path(system_root)

            assert result is False

    def test_returns_true_for_valid_path(self, tmp_path: Path) -> None:
        """is_valid_custom_scan_path should return True for a valid path."""
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        valid_path = tmp_path / "custom_scans"
        valid_path.mkdir()

        with (
            patch("ClassicLib.GlobalRegistry.get_local_dir", return_value=str(tmp_path / "app")),
            patch("ClassicLib.ScanLog.Util.yaml_settings", return_value=None),
        ):
            result = is_valid_custom_scan_path(valid_path)

            assert result is True


# ============================================================================
# Crash Log File Collection Tests
# ============================================================================


@pytest.mark.unit
class TestCrashlogsGetFiles:
    """Tests for crashlogs_get_files function and its implementations."""

    def test_python_fallback_creates_directories(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """_crashlogs_get_files_python should create required directories."""
        from ClassicLib.ScanLog.Util import _crashlogs_get_files_python

        monkeypatch.chdir(tmp_path)

        with (
            patch("ClassicLib.ScanLog.Util.classic_settings", return_value=None),
            patch("ClassicLib.ScanLog.Util.yaml_settings", return_value=None),
        ):
            _crashlogs_get_files_python()

            assert (tmp_path / "Crash Logs").exists()
            assert (tmp_path / "Crash Logs" / "Pastebin").exists()

    def test_python_fallback_finds_crash_logs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """_crashlogs_get_files_python should find crash log files."""
        from ClassicLib.ScanLog.Util import _crashlogs_get_files_python

        monkeypatch.chdir(tmp_path)

        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir(parents=True)
        (crash_logs_dir / "crash-2024-01-01.log").write_text("log1")
        (crash_logs_dir / "crash-2024-01-02.log").write_text("log2")
        (crash_logs_dir / "Pastebin").mkdir()

        with (
            patch("ClassicLib.ScanLog.Util.classic_settings", return_value=None),
            patch("ClassicLib.ScanLog.Util.yaml_settings", return_value=None),
        ):
            result = _crashlogs_get_files_python()

            assert len(result) == 2
            assert all(isinstance(p, Path) for p in result)

    def test_python_fallback_includes_custom_folder(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """_crashlogs_get_files_python should include files from custom folder."""
        from ClassicLib.ScanLog.Util import _crashlogs_get_files_python

        monkeypatch.chdir(tmp_path)

        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir(parents=True)
        (crash_logs_dir / "Pastebin").mkdir()

        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        (custom_dir / "crash-custom.log").write_text("custom log")

        with (
            patch("ClassicLib.ScanLog.Util.classic_settings", return_value=str(custom_dir)),
            patch("ClassicLib.ScanLog.Util.yaml_settings", return_value=None),
        ):
            result = _crashlogs_get_files_python()

            assert any("crash-custom.log" in str(p) for p in result)

    def test_crashlogs_get_files_falls_back_to_python(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """crashlogs_get_files should fall back to Python if Rust unavailable."""
        from ClassicLib.ScanLog.Util import crashlogs_get_files

        monkeypatch.chdir(tmp_path)

        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir(parents=True)
        (crash_logs_dir / "Pastebin").mkdir()
        (crash_logs_dir / "crash-test.log").write_text("test")

        with (
            patch("ClassicLib.ScanLog.Util._crashlogs_get_files_rust", side_effect=ImportError("No Rust")),
            patch("ClassicLib.ScanLog.Util.classic_settings", return_value=None),
            patch("ClassicLib.ScanLog.Util.yaml_settings", return_value=None),
        ):
            result = crashlogs_get_files()

            assert len(result) == 1
            assert "crash-test.log" in str(result[0])

    def test_crashlogs_get_files_uses_rust_when_available(self, tmp_path: Path) -> None:
        """crashlogs_get_files should use Rust implementation when available."""
        from ClassicLib.ScanLog.Util import crashlogs_get_files

        mock_paths = [str(tmp_path / "crash-1.log"), str(tmp_path / "crash-2.log")]

        with patch("ClassicLib.ScanLog.Util._crashlogs_get_files_rust", return_value=[Path(p) for p in mock_paths]):
            result = crashlogs_get_files()

            assert len(result) == 2
            assert all(isinstance(p, Path) for p in result)


# ============================================================================
# Database Entry Lookup Tests
# ============================================================================


@pytest.mark.unit
class TestGetEntry:
    """Tests for get_entry function."""

    def test_returns_cached_entry(self) -> None:
        """get_entry should return cached entry if available."""
        from ClassicLib.ScanLog import Util

        # Set up cache
        Util.query_cache[("test_formid", "test_plugin")] = "cached_entry"

        try:
            result = Util.get_entry("test_formid", "test_plugin")

            assert result == "cached_entry"
        finally:
            # Clean up
            Util.query_cache.clear()

    def test_queries_database_if_not_cached(self, tmp_path: Path) -> None:
        """get_entry should query database if entry not in cache."""
        from ClassicLib.ScanLog import Util

        # Clear cache
        Util.query_cache.clear()

        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE Fallout4 (formid TEXT, plugin TEXT, entry TEXT)")
        conn.execute("INSERT INTO Fallout4 VALUES ('12345', 'Test.esp', 'Test Entry')")
        conn.commit()
        conn.close()

        mock_pool = MagicMock()
        mock_conn = sqlite3.connect(db_path)
        mock_pool.get_connection.return_value = mock_conn

        with (
            patch("ClassicLib.ScanLog.Util.DB_PATHS", [db_path]),
            patch("ClassicLib.ScanLog.Util.SyncDatabasePool.get_instance", return_value=mock_pool),
            patch("ClassicLib.GlobalRegistry.get_game", return_value="Fallout4"),
        ):
            result = Util.get_entry("12345", "Test.esp")

            assert result == "Test Entry"
            # Should now be cached
            assert ("12345", "Test.esp") in Util.query_cache

        mock_conn.close()
        Util.query_cache.clear()

    def test_returns_none_if_not_found(self, tmp_path: Path) -> None:
        """get_entry should return None if entry not found in database."""
        from ClassicLib.ScanLog import Util

        Util.query_cache.clear()

        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE Fallout4 (formid TEXT, plugin TEXT, entry TEXT)")
        conn.commit()
        conn.close()

        mock_pool = MagicMock()
        mock_conn = sqlite3.connect(db_path)
        mock_pool.get_connection.return_value = mock_conn

        with (
            patch("ClassicLib.ScanLog.Util.DB_PATHS", [db_path]),
            patch("ClassicLib.ScanLog.Util.SyncDatabasePool.get_instance", return_value=mock_pool),
            patch("ClassicLib.GlobalRegistry.get_game", return_value="Fallout4"),
        ):
            result = Util.get_entry("nonexistent", "Unknown.esp")

            assert result is None

        mock_conn.close()
        Util.query_cache.clear()

    def test_handles_database_error(self, tmp_path: Path) -> None:
        """get_entry should handle database errors gracefully."""
        from ClassicLib.ScanLog import Util

        Util.query_cache.clear()

        db_path = tmp_path / "test.db"
        db_path.write_text("invalid database content")

        with (
            patch("ClassicLib.ScanLog.Util.DB_PATHS", [db_path]),
            patch("ClassicLib.GlobalRegistry.get_game", return_value="Fallout4"),
        ):
            result = Util.get_entry("12345", "Test.esp")

            # Should not raise, just return None
            assert result is None

        Util.query_cache.clear()


# ============================================================================
# Additional Edge Case Tests for Coverage
# ============================================================================


@pytest.mark.unit
class TestSyncDatabasePoolEdgeCases:
    """Additional edge case tests for SyncDatabasePool."""

    def test_get_connection_raises_on_sqlite_error(self, tmp_path: Path) -> None:
        """get_connection should raise sqlite3.Error when connection fails."""
        from ClassicLib.ScanLog.Util import SyncDatabasePool

        pool = SyncDatabasePool()
        # Use a path that cannot be connected to (directory instead of file)
        invalid_path = tmp_path / "invalid_dir"
        invalid_path.mkdir()

        # This should raise because we're trying to connect to a directory
        # SQLite will fail when trying to open a directory as a database
        with pytest.raises(sqlite3.Error):
            pool.get_connection(invalid_path)


@pytest.mark.unit
class TestIsValidCustomScanPathEdgeCases:
    """Additional edge case tests for is_valid_custom_scan_path."""

    def test_returns_false_for_path_with_oserror_on_resolve(self, tmp_path: Path) -> None:
        """is_valid_custom_scan_path should return False if path.resolve() raises OSError."""
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        # Create a mock path that raises OSError on resolve
        mock_path = MagicMock(spec=Path)
        mock_path.resolve.side_effect = OSError("Cannot resolve path")

        result = is_valid_custom_scan_path(mock_path)

        assert result is False

    def test_handles_value_error_in_restricted_path_comparison(self, tmp_path: Path) -> None:
        """is_valid_custom_scan_path should handle ValueError during restricted path comparison."""
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        # Create a path that can be resolved
        valid_path = tmp_path / "test_folder"
        valid_path.mkdir()

        # Mock restricted path that raises ValueError on resolve
        mock_restricted = MagicMock(spec=Path)
        mock_restricted.resolve.side_effect = ValueError("Different drives")

        with (
            patch("ClassicLib.GlobalRegistry.get_local_dir", return_value=str(tmp_path)),
            patch("ClassicLib.ScanLog.Util.yaml_settings", return_value=mock_restricted),
        ):
            # Should not raise, should return True since the restricted path comparison fails gracefully
            result = is_valid_custom_scan_path(valid_path)

            assert result is True  # Path is valid since restricted comparison failed gracefully


@pytest.mark.unit
class TestCrashlogsGetFilesEdgeCases:
    """Additional edge case tests for crashlogs_get_files."""

    def test_crashlogs_get_files_falls_back_on_general_exception(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """crashlogs_get_files should fall back to Python on any exception from Rust."""
        from ClassicLib.ScanLog.Util import crashlogs_get_files

        monkeypatch.chdir(tmp_path)

        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir(parents=True)
        (crash_logs_dir / "Pastebin").mkdir()
        (crash_logs_dir / "crash-fallback.log").write_text("fallback test")

        with (
            patch(
                "ClassicLib.ScanLog.Util._crashlogs_get_files_rust",
                side_effect=RuntimeError("Rust operation failed"),
            ),
            patch("ClassicLib.ScanLog.Util.classic_settings", return_value=None),
            patch("ClassicLib.ScanLog.Util.yaml_settings", return_value=None),
        ):
            result = crashlogs_get_files()

            # Should have fallen back to Python and found the file
            assert len(result) == 1
            assert "crash-fallback.log" in str(result[0])

    def test_rust_implementation_path_conversion(self, tmp_path: Path) -> None:
        """_crashlogs_get_files_rust should convert string paths to Path objects."""
        from ClassicLib.ScanLog.Util import _crashlogs_get_files_rust

        mock_collector = MagicMock()
        mock_collector.collect_all.return_value = [
            str(tmp_path / "crash-1.log"),
            str(tmp_path / "crash-2.log"),
        ]

        with (
            patch("ClassicLib.ScanLog.Util.classic_settings", return_value=None),
            patch("ClassicLib.ScanLog.Util.yaml_settings", return_value=None),
            patch("classic_file_io.PyLogCollector", return_value=mock_collector),
        ):
            result = _crashlogs_get_files_rust()

            assert len(result) == 2
            assert all(isinstance(p, Path) for p in result)
            mock_collector.collect_all.assert_called_once()


@pytest.mark.unit
class TestGetEntryEdgeCases:
    """Additional edge case tests for get_entry."""

    def test_skips_nonexistent_database_files(self, tmp_path: Path) -> None:
        """get_entry should skip database paths that don't exist."""
        from ClassicLib.ScanLog import Util

        Util.query_cache.clear()

        nonexistent_db = tmp_path / "nonexistent.db"

        with patch("ClassicLib.ScanLog.Util.DB_PATHS", [nonexistent_db]):
            result = Util.get_entry("12345", "Test.esp")

            # Should return None without raising (db file doesn't exist)
            assert result is None

        Util.query_cache.clear()
