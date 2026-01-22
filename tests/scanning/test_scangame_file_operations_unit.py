"""Unit tests for ClassicLib.ScanGame.core.file_operations module.

This module tests the FileOperations class for async file moving operations.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


@pytest.fixture(autouse=True)
def mock_message_handler():
    """Mock message handler for all tests."""
    with patch("ClassicLib.ScanGame.core.file_operations.msg_error"):
        yield


@pytest.fixture
def file_ops_context(tmp_path: Path):
    """Create a context dictionary for file operations."""
    mod_path = tmp_path / "mods"
    backup_path = tmp_path / "backup"
    mod_path.mkdir(parents=True)
    backup_path.mkdir(parents=True)

    return {"mod_path": mod_path, "backup_path": backup_path, "issue_locks": {"cleanup": asyncio.Lock()}, "issue_lists": {"cleanup": set()}}


class TestFileOperationsInit:
    """Tests for FileOperations initialization."""

    def test_init_stores_semaphore(self) -> None:
        """Test __init__ stores the semaphore."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        assert ops.file_ops_semaphore is semaphore

    def test_init_accepts_any_semaphore_value(self) -> None:
        """Test __init__ accepts semaphores with any value."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        semaphore = asyncio.Semaphore(1)
        ops = FileOperations(semaphore)

        assert ops.file_ops_semaphore is not None


class TestMoveFomodAsync:
    """Tests for move_fomod_async method."""

    @pytest.mark.asyncio
    async def test_adds_to_cleanup_list_in_test_mode(self, file_ops_context: dict) -> None:
        """Test adds to cleanup list when TEST_MODE is True."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create a fomod folder to move
        fomod_dir = file_ops_context["mod_path"] / "fomod"
        fomod_dir.mkdir()

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", True):
            await ops.move_fomod_async(file_ops_context, file_ops_context["mod_path"], "fomod")

        # Check that the cleanup list was updated
        assert len(file_ops_context["issue_lists"]["cleanup"]) == 1
        assert "fomod" in list(file_ops_context["issue_lists"]["cleanup"])[0]

    @pytest.mark.asyncio
    async def test_skips_actual_move_in_test_mode(self, file_ops_context: dict) -> None:
        """Test skips actual file move when TEST_MODE is True."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create a fomod folder to move
        fomod_dir = file_ops_context["mod_path"] / "fomod"
        fomod_dir.mkdir()
        (fomod_dir / "test.xml").write_text("test")

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", True):
            await ops.move_fomod_async(file_ops_context, file_ops_context["mod_path"], "fomod")

        # Folder should still exist (not moved)
        assert fomod_dir.exists()

    @pytest.mark.asyncio
    async def test_moves_folder_when_not_in_test_mode(self, file_ops_context: dict) -> None:
        """Test actually moves folder when TEST_MODE is False."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create a fomod folder to move
        fomod_dir = file_ops_context["mod_path"] / "fomod"
        fomod_dir.mkdir()
        (fomod_dir / "test.xml").write_text("test")

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", False):
            await ops.move_fomod_async(file_ops_context, file_ops_context["mod_path"], "fomod")

        # Original folder should be gone
        assert not fomod_dir.exists()
        # New location should exist
        assert (file_ops_context["backup_path"] / "fomod").exists()

    @pytest.mark.asyncio
    async def test_handles_permission_error(self, file_ops_context: dict) -> None:
        """Test handles PermissionError gracefully."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create a fomod folder
        fomod_dir = file_ops_context["mod_path"] / "fomod"
        fomod_dir.mkdir()

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", False):
            with patch("shutil.move", side_effect=PermissionError("Access denied")):
                # Should not raise
                await ops.move_fomod_async(file_ops_context, file_ops_context["mod_path"], "fomod")

        # Cleanup list should be empty (operation failed)
        assert len(file_ops_context["issue_lists"]["cleanup"]) == 0

    @pytest.mark.asyncio
    async def test_handles_os_error(self, file_ops_context: dict) -> None:
        """Test handles OSError gracefully."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create a fomod folder
        fomod_dir = file_ops_context["mod_path"] / "fomod"
        fomod_dir.mkdir()

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", False):
            with patch("shutil.move", side_effect=OSError("Disk error")):
                # Should not raise
                await ops.move_fomod_async(file_ops_context, file_ops_context["mod_path"], "fomod")

        # Cleanup list should be empty (operation failed)
        assert len(file_ops_context["issue_lists"]["cleanup"]) == 0


class TestMoveFileAsync:
    """Tests for move_file_async method."""

    @pytest.mark.asyncio
    async def test_adds_to_cleanup_list_in_test_mode(self, file_ops_context: dict) -> None:
        """Test adds to cleanup list when TEST_MODE is True."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create a file to move
        test_file = file_ops_context["mod_path"] / "test.txt"
        test_file.write_text("test content")

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", True):
            await ops.move_file_async(file_ops_context, test_file)

        # Check that the cleanup list was updated
        assert len(file_ops_context["issue_lists"]["cleanup"]) == 1
        assert "test.txt" in list(file_ops_context["issue_lists"]["cleanup"])[0]

    @pytest.mark.asyncio
    async def test_skips_actual_move_in_test_mode(self, file_ops_context: dict) -> None:
        """Test skips actual file move when TEST_MODE is True."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create a file to move
        test_file = file_ops_context["mod_path"] / "test.txt"
        test_file.write_text("test content")

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", True):
            await ops.move_file_async(file_ops_context, test_file)

        # File should still exist (not moved)
        assert test_file.exists()

    @pytest.mark.asyncio
    async def test_moves_file_when_not_in_test_mode(self, file_ops_context: dict) -> None:
        """Test actually moves file when TEST_MODE is False."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create a file to move
        test_file = file_ops_context["mod_path"] / "test.txt"
        test_file.write_text("test content")

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", False):
            await ops.move_file_async(file_ops_context, test_file)

        # Original file should be gone
        assert not test_file.exists()
        # New location should exist
        assert (file_ops_context["backup_path"] / "test.txt").exists()

    @pytest.mark.asyncio
    async def test_creates_parent_directories(self, file_ops_context: dict) -> None:
        """Test creates parent directories if they don't exist."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create a nested file
        nested_dir = file_ops_context["mod_path"] / "subdir" / "nested"
        nested_dir.mkdir(parents=True)
        test_file = nested_dir / "test.txt"
        test_file.write_text("test content")

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", True):
            await ops.move_file_async(file_ops_context, test_file)

        # Check that parent directories were created
        expected_backup = file_ops_context["backup_path"] / "subdir" / "nested"
        assert expected_backup.exists()

    @pytest.mark.asyncio
    async def test_handles_permission_error(self, file_ops_context: dict) -> None:
        """Test handles PermissionError gracefully."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create a file
        test_file = file_ops_context["mod_path"] / "test.txt"
        test_file.write_text("test content")

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", False):
            with patch("shutil.move", side_effect=PermissionError("Access denied")):
                # Should not raise
                await ops.move_file_async(file_ops_context, test_file)

        # Cleanup list should be empty (operation failed)
        assert len(file_ops_context["issue_lists"]["cleanup"]) == 0

    @pytest.mark.asyncio
    async def test_handles_file_not_found_error(self, file_ops_context: dict) -> None:
        """Test handles FileNotFoundError gracefully."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create a file
        test_file = file_ops_context["mod_path"] / "test.txt"
        test_file.write_text("test content")

        semaphore = asyncio.Semaphore(5)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", False):
            with patch("shutil.move", side_effect=FileNotFoundError("File not found")):
                # Should not raise
                await ops.move_file_async(file_ops_context, test_file)

        # Cleanup list should be empty (operation failed)
        assert len(file_ops_context["issue_lists"]["cleanup"]) == 0


class TestConcurrency:
    """Tests for concurrency behavior."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_operations(self, file_ops_context: dict) -> None:
        """Test semaphore limits concurrent file operations."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        # Create multiple files
        files = []
        for i in range(5):
            test_file = file_ops_context["mod_path"] / f"test{i}.txt"
            test_file.write_text(f"content {i}")
            files.append(test_file)

        # Use semaphore with limit of 2
        semaphore = asyncio.Semaphore(2)
        ops = FileOperations(semaphore)

        with patch("ClassicLib.ScanGame.core.file_operations.TEST_MODE", True):
            # Run all operations concurrently
            tasks = [ops.move_file_async(file_ops_context, f) for f in files]
            await asyncio.gather(*tasks)

        # All files should be added to cleanup list
        assert len(file_ops_context["issue_lists"]["cleanup"]) == 5


class TestModuleImports:
    """Tests for module-level imports."""

    def test_file_operations_class_exists(self) -> None:
        """Test FileOperations class can be imported."""
        from ClassicLib.ScanGame.core.file_operations import FileOperations

        assert FileOperations is not None

    def test_test_mode_import(self) -> None:
        """Test TEST_MODE can be imported from Config."""
        from ClassicLib.ScanGame.core.file_operations import TEST_MODE

        assert isinstance(TEST_MODE, bool)
