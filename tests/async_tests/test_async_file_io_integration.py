"""
Integration tests for async_file_io - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path

import pytest

from ClassicLib.ScanLog.AsyncFileIO import load_crash_logs_async_optimized, write_reports_batch

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncFileIO:
    """Integration tests for async file I/O operations."""

    async def test_large_file_handling(self, tmp_path: Path) -> None:
        """Test handling of large crash log files."""
        large_file = tmp_path / "large.log"
        large_content = "Large file test line\n" * 50000
        large_file.write_text(large_content)
        result = await load_crash_logs_async_optimized([large_file])
        assert large_file.name in result
        assert len(result[large_file.name]) > 1000000
        reports = [(large_file, [large_content], False)]
        await write_reports_batch(reports)
        report_file = large_file.with_name(f"{large_file.stem}-AUTOSCAN.md")
        assert report_file.exists()
        assert report_file.stat().st_size > 1000000
