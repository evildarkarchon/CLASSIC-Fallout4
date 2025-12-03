"""Tests for streaming file I/O operations."""
import asyncio
from pathlib import Path

import pytest

from ClassicLib.FileIO import FileIOCore, stream_lines_sync


class TestAsyncFileStreaming:
    """Test cases for async streaming I/O operations."""

    @pytest.mark.asyncio
    async def test_stream_lines(self, io_core: FileIOCore, temp_file: Path):
        """Test streaming text files asynchronously."""
        lines = []
        async for line in io_core.stream_lines(temp_file):
            lines.append(line)
        
        assert len(lines) == 3
        assert lines[0] == "Test content"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"

    @pytest.mark.asyncio
    async def test_stream_lines_sync_method(self, io_core: FileIOCore, temp_file: Path):
        """Test the synchronous streaming method on FileIOCore."""
        # This should work even if called from async context because it's a sync iterator
        lines = []
        # We run this in executor to simulate sync context safely if needed, 
        # but stream_lines_sync is designed to be safe.
        
        # Using executor just to be 100% safe in async test
        def run_sync_stream():
            return list(io_core.stream_lines_sync(temp_file))
            
        loop = asyncio.get_running_loop()
        lines = await loop.run_in_executor(None, run_sync_stream)
        
        assert len(lines) == 3
        assert lines[0] == "Test content"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"


class TestSyncFileStreaming:
    """Test cases for sync adapter streaming functions."""

    def test_stream_lines_sync_adapter(self, temp_file: Path):
        """Test global sync adapter for streaming lines."""
        lines = []
        for line in stream_lines_sync(temp_file):
            lines.append(line)
            
        assert len(lines) == 3
        assert lines[0] == "Test content"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"

    def test_stream_lines_sync_large_file(self, tmp_path: Path):
        """Test streaming a larger file to ensure iterator behavior."""
        large_file = tmp_path / "large_stream.txt"
        # Write 1000 lines
        with Path(large_file).open("w", encoding="utf-8") as f:
            for i in range(1000):
                f.write(f"Line {i}\n")
        
        count = 0
        for i, line in enumerate(stream_lines_sync(large_file)):
            assert line.strip() == f"Line {i}"
            count += 1
            
        assert count == 1000
