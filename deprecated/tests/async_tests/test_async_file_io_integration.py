"""
Integration tests for async_file_io - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path

import pytest

from ClassicLib.scanning.logs.reporting.async_crash_log_pipeline import write_reports_batch

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

        # Only test write since load is deprecated/removed
        reports = [(large_file, [large_content], False)]
        await write_reports_batch(reports)
        report_file = large_file.with_name(f"{large_file.stem}-AUTOSCAN.md")
        assert report_file.exists()
        assert report_file.stat().st_size > 1000000
