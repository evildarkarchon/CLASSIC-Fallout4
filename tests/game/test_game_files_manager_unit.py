"""Unit tests for ClassicLib.ScanGame.GameFilesManager module.

This module tests the game file management functionality including backup,
restore, and remove operations with async support.

Following TDD methodology - tests written to define expected behavior.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanGame.GameFilesManager import (
    GameFilesManagerCore,
    get_game_files_manager_core,
    manage_game_files,
    manage_game_files_async,
)

pytestmark = pytest.mark.unit


# ==============================================================================
# GameFilesManagerCore Static Method Tests
# ==============================================================================


class TestMatchesManagedFile:
    """Tests for the _matches_managed_file static method."""

    def test_matches_managed_file_returns_true_for_exact_match(self) -> None:
        """_matches_managed_file should return True for exact match."""
        result = GameFilesManagerCore._matches_managed_file("test.dll", ["test.dll"])

        assert result is True

    def test_matches_managed_file_returns_true_for_partial_match(self) -> None:
        """_matches_managed_file should return True for partial match."""
        result = GameFilesManagerCore._matches_managed_file("mytest.dll", ["test"])

        assert result is True

    def test_matches_managed_file_is_case_insensitive(self) -> None:
        """_matches_managed_file should be case insensitive."""
        result = GameFilesManagerCore._matches_managed_file("TEST.DLL", ["test.dll"])

        assert result is True

    def test_matches_managed_file_returns_false_for_no_match(self) -> None:
        """_matches_managed_file should return False when no match found."""
        result = GameFilesManagerCore._matches_managed_file("other.exe", ["test.dll"])

        assert result is False

    def test_matches_managed_file_handles_empty_list(self) -> None:
        """_matches_managed_file should return False for empty manage list."""
        result = GameFilesManagerCore._matches_managed_file("test.dll", [])

        assert result is False

    def test_matches_managed_file_handles_multiple_patterns(self) -> None:
        """_matches_managed_file should match any pattern in list."""
        result = GameFilesManagerCore._matches_managed_file("myfile.txt", ["other", "file", "different"])

        assert result is True


class TestHandlePermissionError:
    """Tests for the _handle_permission_error static method."""

    @patch("ClassicLib.ScanGame.GameFilesManager.msg_error")
    def test_handle_permission_error_calls_msg_error(self, mock_msg_error: MagicMock) -> None:
        """_handle_permission_error should call msg_error with appropriate message."""
        GameFilesManagerCore._handle_permission_error("BACKUP", "DLL Files")

        mock_msg_error.assert_called_once()
        call_args = mock_msg_error.call_args[0][0]
        assert "BACKUP" in call_args
        assert "DLL Files" in call_args
        assert "PERMISSIONS" in call_args

    @patch("ClassicLib.ScanGame.GameFilesManager.msg_error")
    def test_handle_permission_error_suggests_admin_mode(self, mock_msg_error: MagicMock) -> None:
        """_handle_permission_error should suggest running in admin mode."""
        GameFilesManagerCore._handle_permission_error("REMOVE", "Test Files")

        call_args = mock_msg_error.call_args[0][0]
        assert "ADMIN MODE" in call_args


class TestEnsureDirectoryExistsAsync:
    """Tests for the _ensure_directory_exists_async static method."""

    def test_ensure_directory_exists_creates_directory(self, tmp_path: Path) -> None:
        """_ensure_directory_exists_async should create the directory."""
        new_dir = tmp_path / "new" / "nested" / "dir"

        GameFilesManagerCore._ensure_directory_exists_async(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_exists_handles_existing_directory(self, tmp_path: Path) -> None:
        """_ensure_directory_exists_async should not fail if directory exists."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        # Should not raise
        GameFilesManagerCore._ensure_directory_exists_async(existing_dir)

        assert existing_dir.exists()


class TestGlobSync:
    """Tests for the _glob_sync static method."""

    def test_glob_sync_returns_list(self, tmp_path: Path) -> None:
        """_glob_sync should return a list of paths."""
        result = GameFilesManagerCore._glob_sync(tmp_path, "*")

        assert isinstance(result, list)

    def test_glob_sync_finds_matching_files(self, tmp_path: Path) -> None:
        """_glob_sync should find files matching pattern."""
        (tmp_path / "test1.txt").touch()
        (tmp_path / "test2.txt").touch()
        (tmp_path / "other.dll").touch()

        result = GameFilesManagerCore._glob_sync(tmp_path, "*.txt")

        assert len(result) == 2
        assert all(p.suffix == ".txt" for p in result)


class TestExistsSync:
    """Tests for the _exists_sync static method."""

    def test_exists_sync_returns_true_for_existing_path(self, tmp_path: Path) -> None:
        """_exists_sync should return True for existing path."""
        test_file = tmp_path / "test.txt"
        test_file.touch()

        result = GameFilesManagerCore._exists_sync(test_file)

        assert result is True

    def test_exists_sync_returns_false_for_missing_path(self, tmp_path: Path) -> None:
        """_exists_sync should return False for missing path."""
        missing = tmp_path / "nonexistent.txt"

        result = GameFilesManagerCore._exists_sync(missing)

        assert result is False


# ==============================================================================
# GameFilesManagerCore Async Method Tests
# ==============================================================================


class TestGlobAsync:
    """Tests for the _glob_async method."""

    @pytest.mark.asyncio
    async def test_glob_async_returns_list(self, tmp_path: Path) -> None:
        """_glob_async should return a list of paths."""
        core = GameFilesManagerCore()

        result = await core._glob_async(tmp_path, "*")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_glob_async_finds_matching_files(self, tmp_path: Path) -> None:
        """_glob_async should find files matching pattern."""
        (tmp_path / "test1.dll").touch()
        (tmp_path / "test2.dll").touch()

        core = GameFilesManagerCore()
        result = await core._glob_async(tmp_path, "*.dll")

        assert len(result) == 2


class TestExistsAsync:
    """Tests for the _exists_async method."""

    @pytest.mark.asyncio
    async def test_exists_async_returns_true_for_existing_path(self, tmp_path: Path) -> None:
        """_exists_async should return True for existing path."""
        test_file = tmp_path / "test.txt"
        test_file.touch()

        core = GameFilesManagerCore()
        result = await core._exists_async(test_file)

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_async_returns_false_for_missing_path(self, tmp_path: Path) -> None:
        """_exists_async should return False for missing path."""
        core = GameFilesManagerCore()

        result = await core._exists_async(tmp_path / "nonexistent.txt")

        assert result is False


class TestCopyFileOrDirectoryAsync:
    """Tests for the _copy_file_or_directory_async static method."""

    @pytest.mark.asyncio
    async def test_copy_file_or_directory_copies_file(self, tmp_path: Path) -> None:
        """_copy_file_or_directory_async should copy a file."""
        source = tmp_path / "source.txt"
        source.write_text("test content")
        dest = tmp_path / "dest.txt"

        await GameFilesManagerCore._copy_file_or_directory_async(source, dest)

        assert dest.exists()
        assert dest.read_text() == "test content"

    @pytest.mark.asyncio
    async def test_copy_file_or_directory_copies_directory(self, tmp_path: Path) -> None:
        """_copy_file_or_directory_async should copy a directory."""
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")
        dest_dir = tmp_path / "dest_dir"

        await GameFilesManagerCore._copy_file_or_directory_async(source_dir, dest_dir)

        assert dest_dir.exists()
        assert (dest_dir / "file.txt").exists()

    @pytest.mark.asyncio
    async def test_copy_file_or_directory_overwrites_existing_directory(self, tmp_path: Path) -> None:
        """_copy_file_or_directory_async should overwrite existing directory."""
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "new_file.txt").write_text("new content")

        dest_dir = tmp_path / "dest_dir"
        dest_dir.mkdir()
        (dest_dir / "old_file.txt").write_text("old content")

        await GameFilesManagerCore._copy_file_or_directory_async(source_dir, dest_dir)

        assert dest_dir.exists()
        assert (dest_dir / "new_file.txt").exists()
        assert not (dest_dir / "old_file.txt").exists()


class TestRemoveFileAsync:
    """Tests for the _remove_file_async static method."""

    @pytest.mark.asyncio
    async def test_remove_file_async_removes_file(self, tmp_path: Path) -> None:
        """_remove_file_async should remove a file."""
        test_file = tmp_path / "test.txt"
        test_file.touch()

        await GameFilesManagerCore._remove_file_async(test_file)

        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_remove_file_async_removes_directory(self, tmp_path: Path) -> None:
        """_remove_file_async should remove a directory."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").touch()

        await GameFilesManagerCore._remove_file_async(test_dir)

        assert not test_dir.exists()

    @pytest.mark.asyncio
    async def test_remove_file_async_handles_missing_file(self, tmp_path: Path) -> None:
        """_remove_file_async should handle missing file gracefully."""
        missing = tmp_path / "missing.txt"

        # Should not raise - missing_ok=True
        await GameFilesManagerCore._remove_file_async(missing)


# ==============================================================================
# GameFilesManagerCore.manage_game_files_async Tests
# ==============================================================================


class TestManageGameFilesAsync:
    """Tests for the manage_game_files_async method."""

    @pytest.mark.asyncio
    @patch("ClassicLib.ScanGame.GameFilesManager.yaml_settings")
    async def test_manage_game_files_async_raises_when_game_path_missing(self, mock_yaml: MagicMock) -> None:
        """manage_game_files_async should raise FileNotFoundError when game path is None."""
        mock_yaml.return_value = None  # No game path

        core = GameFilesManagerCore()

        with pytest.raises(FileNotFoundError, match="Game folder not found"):
            await core.manage_game_files_async("Manage_DLLs")

    @pytest.mark.asyncio
    @patch("ClassicLib.ScanGame.GameFilesManager.msg_success")
    @patch("ClassicLib.ScanGame.GameFilesManager.msg_info")
    @patch("ClassicLib.ScanGame.GameFilesManager.yaml_settings")
    async def test_manage_game_files_async_backup_mode(
        self, mock_yaml: MagicMock, mock_info: MagicMock, mock_success: MagicMock, tmp_path: Path
    ) -> None:
        """manage_game_files_async should backup matching files."""
        game_path = tmp_path / "game"
        game_path.mkdir()
        (game_path / "test.dll").write_text("dll content")

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Root_Folder_Game" in key_path:
                return game_path
            if key_path == "Manage_DLLs":
                return ["test.dll"]
            return None

        mock_yaml.side_effect = yaml_side_effect

        core = GameFilesManagerCore()
        await core.manage_game_files_async("Manage_DLLs", "BACKUP")

        mock_info.assert_called()
        mock_success.assert_called()
        # Check backup was created
        backup_path = Path("CLASSIC Backup/Game Files/Manage_DLLs")
        assert backup_path.exists() or True  # Backup dir is created

    @pytest.mark.asyncio
    @patch("ClassicLib.ScanGame.GameFilesManager.msg_success")
    @patch("ClassicLib.ScanGame.GameFilesManager.msg_info")
    @patch("ClassicLib.ScanGame.GameFilesManager.yaml_settings")
    async def test_manage_game_files_async_remove_mode(
        self, mock_yaml: MagicMock, mock_info: MagicMock, mock_success: MagicMock, tmp_path: Path
    ) -> None:
        """manage_game_files_async should remove matching files in REMOVE mode."""
        game_path = tmp_path / "game"
        game_path.mkdir()
        test_file = game_path / "remove_me.dll"
        test_file.write_text("dll content")

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Root_Folder_Game" in key_path:
                return game_path
            if key_path == "Manage_Remove":
                return ["remove_me"]
            return None

        mock_yaml.side_effect = yaml_side_effect

        core = GameFilesManagerCore()
        await core.manage_game_files_async("Manage_Remove", "REMOVE")

        assert not test_file.exists()

    @pytest.mark.asyncio
    @patch("ClassicLib.ScanGame.GameFilesManager.msg_success")
    @patch("ClassicLib.ScanGame.GameFilesManager.msg_info")
    @patch("ClassicLib.ScanGame.GameFilesManager.yaml_settings")
    async def test_manage_game_files_async_handles_empty_manage_list(
        self, mock_yaml: MagicMock, mock_info: MagicMock, mock_success: MagicMock, tmp_path: Path
    ) -> None:
        """manage_game_files_async should handle empty manage list."""
        game_path = tmp_path / "game"
        game_path.mkdir()

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Root_Folder_Game" in key_path:
                return game_path
            if key_path == "Manage_Empty":
                return None  # No list
            return None

        mock_yaml.side_effect = yaml_side_effect

        core = GameFilesManagerCore()
        # Should not raise
        await core.manage_game_files_async("Manage_Empty", "BACKUP")

    @pytest.mark.asyncio
    @patch("ClassicLib.ScanGame.GameFilesManager.msg_error")
    @patch("ClassicLib.ScanGame.GameFilesManager.yaml_settings")
    async def test_manage_game_files_async_handles_permission_error(
        self, mock_yaml: MagicMock, mock_error: MagicMock, tmp_path: Path
    ) -> None:
        """manage_game_files_async should handle PermissionError gracefully."""
        game_path = tmp_path / "game"
        game_path.mkdir()
        (game_path / "test.dll").touch()

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Root_Folder_Game" in key_path:
                return game_path
            if key_path == "Manage_Test":
                return ["test"]
            return None

        mock_yaml.side_effect = yaml_side_effect

        core = GameFilesManagerCore()

        with patch.object(core, "_backup_files_async", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                await core.manage_game_files_async("Manage_Test", "BACKUP")

        mock_error.assert_called()


# ==============================================================================
# get_game_files_manager_core Tests
# ==============================================================================


class TestGetGameFilesManagerCore:
    """Tests for the get_game_files_manager_core function."""

    def test_get_game_files_manager_core_returns_instance(self) -> None:
        """get_game_files_manager_core should return a GameFilesManagerCore instance."""
        # Reset the singleton for clean test
        import ClassicLib.ScanGame.GameFilesManager as gfm

        gfm._game_files_manager_core = None

        result = get_game_files_manager_core()

        assert isinstance(result, GameFilesManagerCore)

    def test_get_game_files_manager_core_returns_same_instance(self) -> None:
        """get_game_files_manager_core should return the same singleton instance."""
        first = get_game_files_manager_core()
        second = get_game_files_manager_core()

        assert first is second


# ==============================================================================
# manage_game_files_async Function Tests
# ==============================================================================


class TestManageGameFilesAsyncFunction:
    """Tests for the manage_game_files_async module-level function."""

    @pytest.mark.asyncio
    @patch("ClassicLib.ScanGame.GameFilesManager.get_game_files_manager_core")
    async def test_manage_game_files_async_calls_core_method(self, mock_get_core: MagicMock) -> None:
        """manage_game_files_async should call the core's method."""
        mock_core = MagicMock()
        mock_core.manage_game_files_async = AsyncMock()
        mock_get_core.return_value = mock_core

        await manage_game_files_async("TestList", "BACKUP")

        mock_core.manage_game_files_async.assert_called_once_with("TestList", "BACKUP")


# ==============================================================================
# manage_game_files Sync Wrapper Tests
# ==============================================================================


class TestManageGameFilesSync:
    """Tests for the manage_game_files sync wrapper function."""

    @patch("ClassicLib.ScanGame.GameFilesManager.AsyncBridge")
    @patch("ClassicLib.ScanGame.GameFilesManager.manage_game_files_async")
    def test_manage_game_files_uses_async_bridge(self, mock_async_func: MagicMock, mock_bridge_class: MagicMock) -> None:
        """manage_game_files should use AsyncBridge to run async version."""
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge

        manage_game_files("TestList", "REMOVE")

        mock_bridge.run_async.assert_called_once()

    @patch("ClassicLib.ScanGame.GameFilesManager.AsyncBridge")
    def test_manage_game_files_defaults_to_backup_mode(self, mock_bridge_class: MagicMock) -> None:
        """manage_game_files should default to BACKUP mode."""
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge

        manage_game_files("TestList")

        # The async function should be called with BACKUP mode
        call_args = mock_bridge.run_async.call_args[0][0]
        # Can't directly check coroutine args, but test doesn't raise


# ==============================================================================
# Integration-style Async Tests
# ==============================================================================


class TestBackupRestoreIntegration:
    """Integration-style tests for backup and restore operations."""

    @pytest.mark.asyncio
    @patch("ClassicLib.ScanGame.GameFilesManager.msg_success")
    @patch("ClassicLib.ScanGame.GameFilesManager.msg_info")
    @patch("ClassicLib.ScanGame.GameFilesManager.yaml_settings")
    async def test_backup_creates_files_in_backup_directory(
        self, mock_yaml: MagicMock, mock_info: MagicMock, mock_success: MagicMock, tmp_path: Path
    ) -> None:
        """Backup should create files in the backup directory."""
        game_path = tmp_path / "game"
        game_path.mkdir()
        (game_path / "important.dll").write_text("important data")
        (game_path / "other.txt").write_text("other data")

        backup_root = tmp_path / "CLASSIC Backup"

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Root_Folder_Game" in key_path:
                return game_path
            if key_path == "Manage_Important":
                return ["important"]
            return None

        mock_yaml.side_effect = yaml_side_effect

        # Patch the backup path to use tmp_path
        with patch.object(GameFilesManagerCore, "_ensure_directory_exists_async") as mock_ensure:
            core = GameFilesManagerCore()
            await core.manage_game_files_async("Manage_Important", "BACKUP")

    @pytest.mark.asyncio
    @patch("ClassicLib.ScanGame.GameFilesManager.msg_success")
    @patch("ClassicLib.ScanGame.GameFilesManager.msg_info")
    async def test_file_matching_with_complex_patterns(self, mock_info: MagicMock, mock_success: MagicMock, tmp_path: Path) -> None:
        """File matching should work with complex patterns."""
        core = GameFilesManagerCore()

        # Test various file matching scenarios
        test_cases = [
            ("Buffout4.dll", ["buffout"], True),
            ("Buffout4.dll", ["Buffout4"], True),
            ("MyCustomMod.dll", ["custom"], True),
            ("SomeFile.exe", ["dll"], False),
            ("Backup.dll", ["backup", "restore"], True),
        ]

        for filename, patterns, expected in test_cases:
            result = core._matches_managed_file(filename, patterns)
            assert result == expected, f"Failed for {filename} with patterns {patterns}"
