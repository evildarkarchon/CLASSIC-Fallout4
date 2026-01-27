"""Unit tests for ClassicLib.scanning.logs.AsyncReformat module.

This module tests the asynchronous utilities for log file reformatting,
batch file operations, and crash log processing.

Test coverage includes:
- reformat_single_log_async - single log file reformatting
- crashlogs_reformat_async - batch log reformatting
- batch_file_move_async - async file move operations
- batch_file_copy_async - async file copy operations
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# ============================================================================
# reformat_single_log_async Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestReformatSingleLogAsync:
    """Tests for reformat_single_log_async function."""

    async def test_reformats_plugin_section_brackets(self, tmp_path: Path) -> None:
        """reformat_single_log_async should replace spaces with 0s in plugin brackets."""
        from ClassicLib.scanning.logs.AsyncReformat import reformat_single_log_async

        log_file = tmp_path / "crash-test.log"
        log_content = """PLUGINS:
\t[ 0] Fallout4.esm
\t[ 1] DLCRobot.esm
\t[FE:  1] TestMod.esl
"""
        log_file.write_text(log_content, encoding="utf-8")

        await reformat_single_log_async(log_file, (), simplify_logs=False)

        result = log_file.read_text(encoding="utf-8")
        assert "[00]" in result
        assert "[01]" in result
        assert "[FE:001]" in result

    async def test_removes_lines_when_simplify_enabled(self, tmp_path: Path) -> None:
        """reformat_single_log_async should remove matching lines when simplify_logs is True."""
        from ClassicLib.scanning.logs.AsyncReformat import reformat_single_log_async

        log_file = tmp_path / "crash-test.log"
        log_content = """Header line
Remove this line
Keep this line
Remove another
Footer line
PLUGINS:
\t[00] Fallout4.esm
"""
        log_file.write_text(log_content, encoding="utf-8")

        remove_list = ("Remove this", "Remove another")

        await reformat_single_log_async(log_file, remove_list, simplify_logs=True)

        result = log_file.read_text(encoding="utf-8")
        assert "Remove this line" not in result
        assert "Remove another" not in result
        assert "Header line" in result
        assert "Keep this line" in result
        assert "Footer line" in result

    async def test_preserves_lines_when_simplify_disabled(self, tmp_path: Path) -> None:
        """reformat_single_log_async should preserve all lines when simplify_logs is False."""
        from ClassicLib.scanning.logs.AsyncReformat import reformat_single_log_async

        log_file = tmp_path / "crash-test.log"
        original_content = """Header line
Line to potentially remove
Footer line
PLUGINS:
\t[00] Fallout4.esm
"""
        log_file.write_text(original_content, encoding="utf-8")

        remove_list = ("Line to potentially remove",)

        await reformat_single_log_async(log_file, remove_list, simplify_logs=False)

        result = log_file.read_text(encoding="utf-8")
        assert "Line to potentially remove" in result

    async def test_handles_malformed_bracket_lines(self, tmp_path: Path) -> None:
        """reformat_single_log_async should handle malformed bracket lines gracefully."""
        from ClassicLib.scanning.logs.AsyncReformat import reformat_single_log_async

        log_file = tmp_path / "crash-test.log"
        # Line with '[' but no ']' - should be preserved
        log_content = """PLUGINS:
\t[00] Fallout4.esm
\t[Malformed line without closing bracket
\t[01] DLCRobot.esm
"""
        log_file.write_text(log_content, encoding="utf-8")

        await reformat_single_log_async(log_file, (), simplify_logs=False)

        result = log_file.read_text(encoding="utf-8")
        # Malformed line should be preserved
        assert "[Malformed line without closing bracket" in result
        assert "[00]" in result
        assert "[01]" in result

    async def test_handles_io_error(self, tmp_path: Path) -> None:
        """reformat_single_log_async should handle IO errors gracefully."""
        from ClassicLib.scanning.logs.AsyncReformat import reformat_single_log_async

        non_existent_file = tmp_path / "nonexistent.log"

        # Should not raise - just logs the error
        await reformat_single_log_async(non_existent_file, (), simplify_logs=False)

    async def test_preserves_non_plugin_lines(self, tmp_path: Path) -> None:
        """reformat_single_log_async should not modify lines outside PLUGINS section."""
        from ClassicLib.scanning.logs.AsyncReformat import reformat_single_log_async

        log_file = tmp_path / "crash-test.log"
        log_content = """SYSTEM SPECS:
\t[Some bracket content in system specs]
\tOS: Windows 11
PLUGINS:
\t[ 0] Fallout4.esm
"""
        log_file.write_text(log_content, encoding="utf-8")

        await reformat_single_log_async(log_file, (), simplify_logs=False)

        result = log_file.read_text(encoding="utf-8")
        # System specs bracket line should be unchanged (not in PLUGINS section)
        assert "[Some bracket content in system specs]" in result
        # Plugin line should be reformatted
        assert "[00]" in result


# ============================================================================
# crashlogs_reformat_async Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestCrashlogsReformatAsync:
    """Tests for crashlogs_reformat_async function."""

    async def test_processes_all_logs_in_list(self, tmp_path: Path) -> None:
        """crashlogs_reformat_async should process all logs in the list."""
        from ClassicLib.scanning.logs.AsyncReformat import crashlogs_reformat_async

        # Create multiple log files
        log_files = []
        for i in range(3):
            log_file = tmp_path / f"crash-{i}.log"
            log_file.write_text(f"PLUGINS:\n\t[ {i}] Plugin.esm\n", encoding="utf-8")
            log_files.append(log_file)

        with patch("ClassicLib.scanning.logs.AsyncReformat.classic_settings_async", return_value=False):
            await crashlogs_reformat_async(log_files, ())

        # All files should be reformatted
        for i, log_file in enumerate(log_files):
            content = log_file.read_text(encoding="utf-8")
            assert f"[0{i}]" in content

    async def test_respects_simplify_logs_setting(self, tmp_path: Path) -> None:
        """crashlogs_reformat_async should respect simplify_logs setting."""
        from ClassicLib.scanning.logs.AsyncReformat import crashlogs_reformat_async

        log_file = tmp_path / "crash-test.log"
        log_file.write_text("PLUGINS:\n\t[00] Plugin.esm\nRemove this\n", encoding="utf-8")

        with patch("ClassicLib.scanning.logs.AsyncReformat.classic_settings_async", return_value=True):
            await crashlogs_reformat_async([log_file], ("Remove this",))

        content = log_file.read_text(encoding="utf-8")
        assert "Remove this" not in content

    async def test_processes_in_batches(self, tmp_path: Path) -> None:
        """crashlogs_reformat_async should process logs in batches."""
        from ClassicLib.scanning.logs.AsyncReformat import crashlogs_reformat_async

        # Create more logs than batch size (20)
        log_files = []
        for i in range(25):
            log_file = tmp_path / f"crash-{i:02d}.log"
            log_file.write_text(f"PLUGINS:\n\t[{i:02d}] Plugin.esm\n", encoding="utf-8")
            log_files.append(log_file)

        with patch("ClassicLib.scanning.logs.AsyncReformat.classic_settings_async", return_value=False):
            await crashlogs_reformat_async(log_files, ())

        # All files should still be processed
        for log_file in log_files:
            assert log_file.exists()

    async def test_handles_empty_list(self) -> None:
        """crashlogs_reformat_async should handle empty list gracefully."""
        from ClassicLib.scanning.logs.AsyncReformat import crashlogs_reformat_async

        with patch("ClassicLib.scanning.logs.AsyncReformat.classic_settings_async", return_value=False):
            # Should not raise
            await crashlogs_reformat_async([], ())


# ============================================================================
# batch_file_move_async Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestBatchFileMoveAsync:
    """Tests for batch_file_move_async function."""

    async def test_moves_all_files(self, tmp_path: Path) -> None:
        """batch_file_move_async should move all files in operations list."""
        from ClassicLib.scanning.logs.AsyncReformat import batch_file_move_async

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create source files
        file1 = source_dir / "file1.log"
        file2 = source_dir / "file2.log"
        file1.write_text("content1")
        file2.write_text("content2")

        operations = [
            (file1, target_dir / "file1.log"),
            (file2, target_dir / "file2.log"),
        ]

        await batch_file_move_async(operations)

        assert not file1.exists()
        assert not file2.exists()
        assert (target_dir / "file1.log").exists()
        assert (target_dir / "file2.log").exists()

    async def test_handles_move_error(self, tmp_path: Path) -> None:
        """batch_file_move_async should handle move errors gracefully."""
        from ClassicLib.scanning.logs.AsyncReformat import batch_file_move_async

        source_file = tmp_path / "nonexistent.log"
        target_file = tmp_path / "target.log"

        operations = [(source_file, target_file)]

        # Should not raise - just logs the error
        await batch_file_move_async(operations)

    async def test_concurrent_moves(self, tmp_path: Path) -> None:
        """batch_file_move_async should move files concurrently."""
        from ClassicLib.scanning.logs.AsyncReformat import batch_file_move_async

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create multiple files
        operations = []
        for i in range(10):
            src = source_dir / f"file{i}.log"
            src.write_text(f"content{i}")
            operations.append((src, target_dir / f"file{i}.log"))

        await batch_file_move_async(operations)

        # All files should be moved
        for i in range(10):
            assert not (source_dir / f"file{i}.log").exists()
            assert (target_dir / f"file{i}.log").exists()

    async def test_handles_empty_operations(self) -> None:
        """batch_file_move_async should handle empty operations list."""
        from ClassicLib.scanning.logs.AsyncReformat import batch_file_move_async

        # Should not raise
        await batch_file_move_async([])


# ============================================================================
# batch_file_copy_async Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestBatchFileCopyAsync:
    """Tests for batch_file_copy_async function."""

    async def test_copies_all_files(self, tmp_path: Path) -> None:
        """batch_file_copy_async should copy all files in operations list."""
        from ClassicLib.scanning.logs.AsyncReformat import batch_file_copy_async

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create source files
        file1 = source_dir / "file1.log"
        file2 = source_dir / "file2.log"
        file1.write_text("content1")
        file2.write_text("content2")

        operations = [
            (file1, target_dir / "file1.log"),
            (file2, target_dir / "file2.log"),
        ]

        await batch_file_copy_async(operations)

        # Source files still exist
        assert file1.exists()
        assert file2.exists()
        # Target files created
        assert (target_dir / "file1.log").exists()
        assert (target_dir / "file2.log").exists()
        # Content preserved
        assert (target_dir / "file1.log").read_text() == "content1"
        assert (target_dir / "file2.log").read_text() == "content2"

    async def test_preserves_file_metadata(self, tmp_path: Path) -> None:
        """batch_file_copy_async should preserve file metadata (uses shutil.copy2)."""
        from ClassicLib.scanning.logs.AsyncReformat import batch_file_copy_async

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        source_file = source_dir / "file.log"
        source_file.write_text("content")

        # Get original mtime
        original_stat = source_file.stat()

        # Small delay to ensure different mtime if not preserved
        await asyncio.sleep(0.01)

        operations = [(source_file, target_dir / "file.log")]

        await batch_file_copy_async(operations)

        target_file = target_dir / "file.log"
        target_stat = target_file.stat()

        # Modification time should be similar (copy2 preserves it)
        # Allow small tolerance for filesystem precision
        assert abs(original_stat.st_mtime - target_stat.st_mtime) < 1.0

    async def test_handles_copy_error(self, tmp_path: Path) -> None:
        """batch_file_copy_async should handle copy errors gracefully."""
        from ClassicLib.scanning.logs.AsyncReformat import batch_file_copy_async

        source_file = tmp_path / "nonexistent.log"
        target_file = tmp_path / "target.log"

        operations = [(source_file, target_file)]

        # Should not raise - just logs the error
        await batch_file_copy_async(operations)

    async def test_concurrent_copies(self, tmp_path: Path) -> None:
        """batch_file_copy_async should copy files concurrently."""
        from ClassicLib.scanning.logs.AsyncReformat import batch_file_copy_async

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create multiple files
        operations = []
        for i in range(10):
            src = source_dir / f"file{i}.log"
            src.write_text(f"content{i}")
            operations.append((src, target_dir / f"file{i}.log"))

        await batch_file_copy_async(operations)

        # All files should be copied
        for i in range(10):
            assert (source_dir / f"file{i}.log").exists()  # Original still exists
            assert (target_dir / f"file{i}.log").exists()  # Copy created

    async def test_handles_empty_operations(self) -> None:
        """batch_file_copy_async should handle empty operations list."""
        from ClassicLib.scanning.logs.AsyncReformat import batch_file_copy_async

        # Should not raise
        await batch_file_copy_async([])

    async def test_handles_mixed_success_and_failure(self, tmp_path: Path) -> None:
        """batch_file_copy_async should continue with other copies if one fails."""
        from ClassicLib.scanning.logs.AsyncReformat import batch_file_copy_async

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # One valid file
        valid_file = source_dir / "valid.log"
        valid_file.write_text("valid content")

        # One nonexistent file
        invalid_file = source_dir / "invalid.log"

        operations = [
            (valid_file, target_dir / "valid.log"),
            (invalid_file, target_dir / "invalid.log"),
        ]

        await batch_file_copy_async(operations)

        # Valid file should be copied
        assert (target_dir / "valid.log").exists()
        # Invalid file copy should fail silently
        assert not (target_dir / "invalid.log").exists()
