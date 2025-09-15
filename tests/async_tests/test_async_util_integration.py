"""
Integration tests for async_util - integration logic testing.

This file contains integration tests that test interactions between components.
"""

import asyncio
import tempfile
from pathlib import Path
import pytest
from ClassicLib.AsyncUtil import detect_encoding_async, get_encoding_detection_available, open_file_with_encoding_async, read_file_with_encoding_async, read_lines_with_encoding_async

pytestmark = pytest.mark.integration

class TestAsyncEncodingDetection:
    """Test cases for async encoding detection utilities."""

    @pytest.mark.asyncio
    async def test_detect_encoding_utf8(self) -> None:
        """Test detection of UTF-8 encoded files."""
        import aiofiles
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as f:
            test_path = Path(f.name)
            f.write(b'\xef\xbb\xbf')
            f.write('Hello, 世界! 🌍'.encode())
        try:
            encoding = await detect_encoding_async(test_path)
            assert encoding.lower() in ['utf-8', 'utf-8-sig']
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_detect_encoding_latin1(self) -> None:
        """Test detection of Latin-1 encoded files."""
        import aiofiles
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as f:
            test_path = Path(f.name)
            f.write('Héllö Wörld! àèìòù'.encode('latin-1'))
        try:
            encoding = await detect_encoding_async(test_path)
            assert encoding.lower() in ['iso-8859-1', 'windows-1252', 'latin-1', 'utf-8']
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_detect_encoding_with_small_sample(self) -> None:
        """Test encoding detection with custom sample size."""
        import aiofiles
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as f:
            test_path = Path(f.name)
            content = ('A' * 1000 + '世界' + 'B' * 1000).encode('utf-8')
            f.write(content)
        try:
            encoding = await detect_encoding_async(test_path, sample_size=500)
            assert encoding.lower() in ['utf-8', 'ascii']
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_open_file_with_encoding_async(self) -> None:
        """Test opening file with automatic encoding detection."""
        import aiofiles
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
            test_path = Path(f.name)
            f.write('Hello\n世界\n🌍')
        try:
            async with open_file_with_encoding_async(test_path) as f:
                contents = await f.read()
                assert 'Hello' in contents
                assert '世界' in contents
                assert '🌍' in contents
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_read_file_with_encoding_async(self) -> None:
        """Test reading entire file with automatic encoding detection."""
        import aiofiles
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-16', delete=False, suffix='.txt') as f:
            test_path = Path(f.name)
            f.write('UTF-16 encoded content: 世界')
        try:
            contents = await read_file_with_encoding_async(test_path)
            assert 'UTF-16' in contents
            assert '世界' in contents
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_read_lines_with_encoding_async(self) -> None:
        """Test reading file lines with automatic encoding detection."""
        import aiofiles
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
            test_path = Path(f.name)
            f.write('Line 1\nLine 2 with 世界\nLine 3')
        try:
            lines = await read_lines_with_encoding_async(test_path)
            assert len(lines) == 3
            assert 'Line 1' in lines[0]
            assert '世界' in lines[1]
            assert 'Line 3' in lines[2]
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_nonexistent_file(self) -> None:
        """Test handling of nonexistent files."""
        nonexistent_path = Path('/tmp/nonexistent_file_12345.txt')
        with pytest.raises(FileNotFoundError):
            await detect_encoding_async(nonexistent_path)
        with pytest.raises(FileNotFoundError):
            await read_file_with_encoding_async(nonexistent_path)

    @pytest.mark.asyncio
    async def test_concurrent_encoding_detection(self) -> None:
        """Test concurrent encoding detection on multiple files."""
        test_files = []
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            utf8_file = tmpdir_path / 'utf8.txt'
            utf8_file.write_text('UTF-8: 世界', encoding='utf-8')
            test_files.append(utf8_file)
            ascii_file = tmpdir_path / 'ascii.txt'
            ascii_file.write_text('Pure ASCII content')
            test_files.append(ascii_file)
            latin1_file = tmpdir_path / 'latin1.txt'
            latin1_file.write_bytes('Café Münchën'.encode('latin-1'))
            test_files.append(latin1_file)
            tasks = [detect_encoding_async(f) for f in test_files]
            encodings = await asyncio.gather(*tasks)
            assert len(encodings) == 3
            for encoding in encodings:
                assert encoding is not None
                assert len(encoding) > 0
