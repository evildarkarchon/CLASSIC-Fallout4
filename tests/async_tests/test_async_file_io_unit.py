"""
Unit tests for async_file_io - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

# IMPORTANT: Async Test Pattern Documentation
# ============================================
# This test file follows correct AsyncBridge patterns:
# 1. For sync wrappers using AsyncBridge: Mock bridge.run_async(), not the async function
# 2. For pure async tests: Use @pytest.mark.asyncio and real async/await
# 3. Never use AsyncMock for methods called through AsyncBridge
# 4. See docs/async_test_patterns_guide.md for comprehensive patterns


from pathlib import Path
import pytest
from ClassicLib.ScanLog.AsyncFileIO import load_crash_logs_async_optimized, write_reports_batch

pytestmark = pytest.mark.unit

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
            assert b'Fallout 4' in result[log_file.name]
            assert b'EXCEPTION_ACCESS_VIOLATION' in result[log_file.name]

    @pytest.mark.asyncio
    async def test_load_crash_logs_with_empty_list(self) -> None:
        """Test loading with empty file list."""
        result: dict[str, bytes] = await load_crash_logs_async_optimized([])
        assert isinstance(result, dict)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_load_crash_logs_with_nonexistent_files(self, tmp_path: Path) -> None:
        """Test handling of non-existent files."""
        nonexistent_files = [tmp_path / 'nonexistent1.log', tmp_path / 'nonexistent2.log']
        result: dict[str, bytes] = await load_crash_logs_async_optimized(nonexistent_files)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_write_reports_batch(self, sample_crash_logs: list[Path]) -> None:
        """Test batch writing of reports."""
        reports: list[tuple[Path, list[str], bool]] = [(log_file, [f'# Report for {log_file.name}\n\nTest report content\n'], False) for log_file in sample_crash_logs]
        await write_reports_batch(reports)
        for log_file in sample_crash_logs:
            report_file: Path = log_file.with_name(f'{log_file.stem}-AUTOSCAN.md')
            assert report_file.exists()
            content: str = report_file.read_text()
            assert f'Report for {log_file.name}' in content
            assert 'Test report content' in content

    @pytest.mark.asyncio
    async def test_write_reports_with_warning_flag(self, tmp_path: Path) -> None:
        """Test report writing with warning flag set."""
        log_file = tmp_path / 'test.log'
        log_file.write_text('test content')
        reports = [(log_file, ['# Warning Report\n\nThis report has warnings\n'], True)]
        await write_reports_batch(reports)
        report_file: Path = log_file.with_name(f'{log_file.stem}-AUTOSCAN.md')
        assert report_file.exists()
        content: str = report_file.read_text()
        assert 'Warning Report' in content

    @pytest.mark.asyncio
    async def test_write_reports_with_empty_content(self, tmp_path: Path) -> None:
        """Test writing reports with empty content."""
        log_file = tmp_path / 'empty.log'
        log_file.write_text('test')
        reports = [(log_file, [], False)]
        await write_reports_batch(reports)
        report_file: Path = log_file.with_name(f'{log_file.stem}-AUTOSCAN.md')
        if report_file.exists():
            content: str = report_file.read_text()
            assert content == '' or len(content) == 0

    @pytest.mark.asyncio
    async def test_write_reports_overwrite_existing(self, tmp_path: Path) -> None:
        """Test that report writing overwrites existing report files."""
        log_file = tmp_path / 'overwrite.log'
        log_file.write_text('test')
        report_file: Path = log_file.with_name(f'{log_file.stem}-AUTOSCAN.md')
        report_file.write_text('Old report content')
        reports = [(log_file, ['New report content\n'], False)]
        await write_reports_batch(reports)
        content: str = report_file.read_text()
        assert 'New report content' in content
        assert 'Old report content' not in content

    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, sample_crash_logs: list[Path]) -> None:
        """Test that concurrent file operations work correctly."""
        import asyncio
        load_task = load_crash_logs_async_optimized(sample_crash_logs)
        reports: list[tuple[Path, list[str], bool]] = [(log_file, [f'Concurrent report {i}\n'], False) for i, log_file in enumerate(sample_crash_logs)]
        write_task = write_reports_batch(reports)
        load_result, _ = await asyncio.gather(load_task, write_task)
        assert len(load_result) == 5
        for log_file in sample_crash_logs:
            report_file: Path = log_file.with_name(f'{log_file.stem}-AUTOSCAN.md')
            assert report_file.exists()
