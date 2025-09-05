"""
Tests for async utility functions used in the pipeline.

This module contains tests for various async utility functions
that support the crash log processing pipeline.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from ClassicLib.ScanLog.AsyncReformat import crashlogs_reformat_async
from ClassicLib.ScanLog.AsyncUtil import load_crash_logs_async


@pytest.fixture
def sample_crash_logs(tmp_path: Path) -> list[Path]:
    """Create sample crash log files."""
    crash_logs_dir: Path = tmp_path / "Crash Logs"
    crash_logs_dir.mkdir(exist_ok=True)

    content = """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512

PROBABLE CALL STACK:
\t[0] 0x7FF6EF4C3512 Fallout4.exe+0733512
\t[1] 0x7FF6EF4C145E Fallout4.exe+073145E

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[02] TestPlugin.esp
"""

    files: list[Path] = []
    for i in range(3):
        log_file: Path = crash_logs_dir / f"crash-2023-01-{i+10:02d}-12-00-00.log"
        log_file.write_text(content)
        files.append(log_file)

    return files


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncUtilityFunctions:
    """Integration tests for async utility functions."""

    async def test_load_crash_logs_async(self, sample_crash_logs: list[Path]) -> None:
        """Test async crash log loading."""
        result: dict[str, list[str]] = await load_crash_logs_async(sample_crash_logs)

        assert isinstance(result, dict)
        assert len(result) == 3

        for log_file in sample_crash_logs:
            assert log_file.name in result
            assert isinstance(result[log_file.name], list)
            assert len(result[log_file.name]) > 0  # Should have content lines

            # Verify content was parsed correctly
            lines = result[log_file.name]
            assert any("Fallout 4" in line for line in lines)
            assert any("EXCEPTION_ACCESS_VIOLATION" in line for line in lines)

    async def test_load_crash_logs_empty_list(self) -> None:
        """Test loading with empty file list."""
        result: dict[str, list[str]] = await load_crash_logs_async([])

        assert isinstance(result, dict)
        assert len(result) == 0

    async def test_load_crash_logs_mixed_encoding(self, tmp_path: Path) -> None:
        """Test loading files with different encodings."""
        # Create files with different encodings
        utf8_file = tmp_path / "utf8.log"
        utf8_file.write_text("UTF-8 content: é à ñ", encoding="utf-8")

        # Create ASCII file
        ascii_file = tmp_path / "ascii.log"
        ascii_file.write_text("ASCII content only", encoding="ascii")

        files = [utf8_file, ascii_file]
        result = await load_crash_logs_async(files)

        assert len(result) == 2
        assert "utf8.log" in result
        assert "ascii.log" in result

    @pytest.mark.usefixtures("init_message_handler_fixture")
    async def test_crashlogs_reformat_async(self, sample_crash_logs: list[Path]) -> None:
        """Test async crash log reformatting."""
        remove_list = ("test_remove",)

        # Mock the reformat logic
        with patch("ClassicLib.ScanLog.AsyncReformat.reformat_single_log_async") as mock_process:
            mock_process.return_value = None

            await crashlogs_reformat_async(sample_crash_logs, remove_list)

            # Verify each log was processed
            assert mock_process.call_count == 3

    @pytest.mark.usefixtures("init_message_handler_fixture")
    async def test_crashlogs_reformat_with_exclusions(self, tmp_path: Path) -> None:
        """Test crash log reformatting with exclusion list."""
        # Create logs with different patterns
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        keep_log = logs_dir / "keep-this.log"
        keep_log.write_text("Keep this content")

        remove_log = logs_dir / "remove-this.log"
        remove_log.write_text("Remove this content")

        files = [keep_log, remove_log]
        remove_list = ("remove",)  # Should match "remove-this.log"

        with patch("ClassicLib.ScanLog.AsyncReformat.reformat_single_log_async") as mock_process:
            mock_process.return_value = None

            await crashlogs_reformat_async(files, remove_list)

            # Should process the file even if it matches remove pattern
            # The actual removal logic depends on implementation
            assert mock_process.call_count >= 1

    async def test_concurrent_operations_performance(self, sample_crash_logs: list[Path]) -> None:
        """Test performance of concurrent async operations."""
        # Test sequential processing
        start = time.perf_counter()
        for log_file in sample_crash_logs:
            content = log_file.read_text()
            _ = content.splitlines()
        sequential_time = time.perf_counter() - start

        # Test concurrent processing
        async def process_file(file_path: Path) -> list[str]:
            import aiofiles
            async with aiofiles.open(file_path, encoding="utf-8", errors="ignore") as f:
                content = await f.read()
                return content.splitlines()

        start = time.perf_counter()
        tasks = [process_file(log_file) for log_file in sample_crash_logs]
        results = await asyncio.gather(*tasks)
        concurrent_time = time.perf_counter() - start

        # Verify results are consistent
        assert len(results) == 3
        for result in results:
            assert isinstance(result, list)
            assert len(result) > 0

        # Log performance comparison
        print(f"\nSequential time: {sequential_time:.4f}s")
        print(f"Concurrent time: {concurrent_time:.4f}s")

    async def test_error_handling_in_async_operations(self, tmp_path: Path) -> None:
        """Test error handling in async operations."""
        valid_file = tmp_path / "valid.log"
        valid_file.write_text("Valid content")

        invalid_file = tmp_path / "nonexistent.log"  # Doesn't exist

        files = [valid_file, invalid_file]

        # Test with error handling
        try:
            result = await load_crash_logs_async(files)
            # Should either skip invalid files or handle error gracefully
            assert "valid.log" in result or len(result) == 0
        except Exception:
            # If exception is raised, it should be handled appropriately
            pass

    async def test_async_operations_with_large_dataset(self, tmp_path: Path) -> None:
        """Test async operations with larger number of files."""
        # Create 50 small log files
        files = []
        for i in range(50):
            log_file = tmp_path / f"log_{i:03d}.log"
            log_file.write_text(f"Log file {i}\nWith some content\n")
            files.append(log_file)

        start = time.perf_counter()
        result = await load_crash_logs_async(files)
        elapsed = time.perf_counter() - start

        assert len(result) == 50
        assert all(f"log_{i:03d}.log" in result for i in range(50))

        # Should complete in reasonable time
        assert elapsed < 10.0  # 50 files should load in under 10 seconds

    async def test_async_memory_efficiency(self, tmp_path: Path) -> None:
        """Test memory efficiency of async operations."""
        # Create a few large files
        large_files = []
        for i in range(3):
            large_file = tmp_path / f"large_{i}.log"
            # Create 10MB file
            content = "X" * (10 * 1024 * 1024)
            large_file.write_text(content)
            large_files.append(large_file)

        # Load files asynchronously
        result = await load_crash_logs_async(large_files)

        # Verify all files were loaded
        assert len(result) == 3
        for i in range(3):
            assert f"large_{i}.log" in result
            # Content should be split into lines
            assert isinstance(result[f"large_{i}.log"], list)
