"""
Integration tests for thread_safe_log_cache - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path

import pytest

from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache

pytestmark = pytest.mark.integration

@pytest.mark.thread
class TestThreadSafeLogCacheEdgeCases:
    """Test edge cases for ThreadSafeLogCache."""

    def test_log_with_invalid_chars(self, tmp_path: Path) -> None:
        """Test handling of logs with invalid UTF-8 characters."""
        log_file: Path = tmp_path / 'invalid_utf8.log'
        with log_file.open('wb') as f:
            f.write(b'Valid text\n')
            f.write(b'\xff\xfe\xfd\n')
            f.write(b'More valid text\n')
        log_cache: ThreadSafeLogCache = ThreadSafeLogCache([log_file])
        result: list[str] = log_cache.read_log('invalid_utf8.log')
        assert len(result) == 3
        assert result[0] == 'Valid text'
        assert result[2] == 'More valid text'
