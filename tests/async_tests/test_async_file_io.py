"""
Tests for async file I/O operations in the crash log pipeline.

This module contains tests for optimized async file reading and writing operations
used throughout the async pipeline.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from pathlib import Path

import pytest

from ClassicLib.ScanLog.AsyncFileIO import (
    load_crash_logs_async_optimized,
    write_reports_batch,
)


@pytest.fixture
def sample_crash_logs(tmp_path: Path) -> list[Path]:
    """Create sample crash log files for testing."""
    crash_logs_dir: Path = tmp_path / "Crash Logs"
    crash_logs_dir.mkdir(exist_ok=True)

    content = """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512

PROBABLE CALL STACK:
\t[0] 0x7FF6EF4C3512 Fallout4.exe+0733512
\tForm ID: 0x12345678

PLUGINS:
\t[00] Fallout4.esm
\t[01] TestMod.esp
"""

    files: list[Path] = []
    for i in range(5):
        log_file: Path = crash_logs_dir / f"crash-log-{i:02d}.log"
        # Vary content slightly for each file
        file_content = content + f"\n\t[{i:02d}] TestPlugin{i}.esp"
        log_file.write_text(file_content)
        files.append(log_file)

    return files


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncFileIO:
    """Integration tests for async file I/O operations."""

    async def test_load_crash_logs_async_optimized(self, sample_crash_logs: list[Path]) -> None:
        """Test optimized async crash log loading."""
        result: dict[str, bytes] = await load_crash_logs_async_optimized(sample_crash_logs)

        assert isinstance(result, dict)
        assert len(result) == 5

        for log_file in sample_crash_logs:
            assert log_file.name in result
            assert isinstance(result[log_file.name], bytes)
            # Verify content was loaded correctly
            assert b"Fallout 4" in result[log_file.name]
            assert b"EXCEPTION_ACCESS_VIOLATION" in result[log_file.name]

    async def test_load_crash_logs_with_empty_list(self) -> None:
        """Test loading with empty file list."""
        result: dict[str, bytes] = await load_crash_logs_async_optimized([])

        assert isinstance(result, dict)
        assert len(result) == 0

    async def test_load_crash_logs_with_nonexistent_files(self, tmp_path: Path) -> None:
        """Test handling of non-existent files."""
        nonexistent_files = [
            tmp_path / "nonexistent1.log",
            tmp_path / "nonexistent2.log",
        ]

        # Should handle missing files gracefully
        result: dict[str, bytes] = await load_crash_logs_async_optimized(nonexistent_files)

        # Implementation may either skip missing files or raise exception
        # Adjust assertion based on actual implementation behavior
        assert isinstance(result, dict)

    async def test_write_reports_batch(self, sample_crash_logs: list[Path]) -> None:
        """Test batch writing of reports."""
        reports: list[tuple[Path, list[str], bool]] = [
            (log_file, [f"# Report for {log_file.name}\n\nTest report content\n"], False)
            for log_file in sample_crash_logs
        ]

        await write_reports_batch(reports)

        # Verify reports were written
        for log_file in sample_crash_logs:
            report_file: Path = log_file.with_name(f"{log_file.stem}-AUTOSCAN.md")
            assert report_file.exists()
            content: str = report_file.read_text()
            assert f"Report for {log_file.name}" in content
            assert "Test report content" in content

    async def test_write_reports_with_warning_flag(self, tmp_path: Path) -> None:
        """Test report writing with warning flag set."""
        log_file = tmp_path / "test.log"
        log_file.write_text("test content")

        reports = [
            (log_file, ["# Warning Report\n\nThis report has warnings\n"], True)  # Warning flag set
        ]

        await write_reports_batch(reports)

        # Check if warning affects file naming or content
        report_file: Path = log_file.with_name(f"{log_file.stem}-AUTOSCAN.md")
        assert report_file.exists()
        content: str = report_file.read_text()
        assert "Warning Report" in content

    async def test_write_reports_with_empty_content(self, tmp_path: Path) -> None:
        """Test writing reports with empty content."""
        log_file = tmp_path / "empty.log"
        log_file.write_text("test")

        reports = [(log_file, [], False)]  # Empty report content

        await write_reports_batch(reports)

        report_file: Path = log_file.with_name(f"{log_file.stem}-AUTOSCAN.md")
        # May or may not create file for empty reports - check implementation
        if report_file.exists():
            content: str = report_file.read_text()
            assert content == "" or len(content) == 0

    async def test_write_reports_overwrite_existing(self, tmp_path: Path) -> None:
        """Test that report writing overwrites existing report files."""
        log_file = tmp_path / "overwrite.log"
        log_file.write_text("test")

        report_file: Path = log_file.with_name(f"{log_file.stem}-AUTOSCAN.md")
        report_file.write_text("Old report content")

        reports = [(log_file, ["New report content\n"], False)]
        await write_reports_batch(reports)

        # Verify old content was overwritten
        content: str = report_file.read_text()
        assert "New report content" in content
        assert "Old report content" not in content

    async def test_concurrent_file_operations(self, sample_crash_logs: list[Path]) -> None:
        """Test that concurrent file operations work correctly."""
        import asyncio

        # Load files concurrently
        load_task = load_crash_logs_async_optimized(sample_crash_logs)

        # Prepare reports concurrently
        reports: list[tuple[Path, list[str], bool]] = [
            (log_file, [f"Concurrent report {i}\n"], False)
            for i, log_file in enumerate(sample_crash_logs)
        ]
        write_task = write_reports_batch(reports)

        # Execute both operations concurrently
        load_result, _ = await asyncio.gather(load_task, write_task)

        # Verify both operations completed successfully
        assert len(load_result) == 5
        for log_file in sample_crash_logs:
            report_file: Path = log_file.with_name(f"{log_file.stem}-AUTOSCAN.md")
            assert report_file.exists()

    async def test_large_file_handling(self, tmp_path: Path) -> None:
        """Test handling of large crash log files."""
        large_file = tmp_path / "large.log"

        # Create a large file (1MB)
        large_content = "Large file test line\n" * 50000
        large_file.write_text(large_content)

        result = await load_crash_logs_async_optimized([large_file])

        assert large_file.name in result
        assert len(result[large_file.name]) > 1000000  # Should be ~1MB

        # Test writing large report
        reports = [(large_file, [large_content], False)]
        await write_reports_batch(reports)

        report_file = large_file.with_name(f"{large_file.stem}-AUTOSCAN.md")
        assert report_file.exists()
        assert report_file.stat().st_size > 1000000
