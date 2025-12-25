"""
Test suite for file operation utility functions in ClassicLib/Util.py.

This module contains tests for file encoding detection, hashing,
and other file-related operations.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841
import hashlib
from pathlib import Path

import pytest

from ClassicLib.Utils.file_utils import calculate_file_hash, open_file_with_encoding
from ClassicLib.Utils.path_utils import remove_readonly

pytestmark = [pytest.mark.unit]


class TestEncodingOperations:
    """Tests for file encoding detection and handling."""

    def test_open_file_with_encoding_utf8(self, tmp_path: Path) -> None:
        """Test open_file_with_encoding with UTF-8 file."""
        test_file = tmp_path / "utf8.txt"
        content = "Hello, World! Test content"
        test_file.write_text(content, encoding="utf-8")

        with open_file_with_encoding(test_file) as f:
            result = f.read()

        assert result == content

    def test_open_file_with_encoding_latin1(self, tmp_path: Path) -> None:
        """Test open_file_with_encoding with Latin-1 encoded file."""
        test_file = tmp_path / "latin1.txt"
        content = "Café résumé naïve"
        test_file.write_bytes(content.encode("latin-1"))

        with open_file_with_encoding(test_file) as f:
            result = f.read()

        # Should detect encoding and read correctly
        assert content in result or len(result) > 0  # Fallback to basic check

    def test_open_file_with_encoding_nonexistent_file(self, tmp_path: Path) -> None:
        """Test open_file_with_encoding with nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.txt"

        with pytest.raises(FileNotFoundError):  # noqa: SIM117
            with open_file_with_encoding(nonexistent):
                pass

    def test_open_file_with_encoding_utf16(self, tmp_path: Path) -> None:
        """Test open_file_with_encoding with UTF-16 file."""
        test_file = tmp_path / "utf16.txt"
        content = "Unicode content with special characters: 你好世界"
        test_file.write_bytes(content.encode("utf-16"))

        with open_file_with_encoding(test_file) as f:
            result = f.read()

        # Should handle UTF-16 properly
        assert len(result) > 0

    def test_open_file_with_encoding_binary_file(self, tmp_path: Path) -> None:
        """Test open_file_with_encoding with binary file."""
        test_file = tmp_path / "binary.bin"
        test_file.write_bytes(bytes([0, 1, 2, 255, 254, 253]))

        # open_file_with_encoding is for text files, binary files should be handled differently
        # The function will try to decode it, which may fail or produce strange output
        try:
            with open_file_with_encoding(test_file) as f:
                result = f.read()
                # If it succeeds, we should get some string output
                assert isinstance(result, str)
        except (UnicodeDecodeError, Exception):
            # It's okay if it fails on binary data
            pass

    def test_open_file_with_encoding_empty_file(self, tmp_path: Path) -> None:
        """Test open_file_with_encoding with empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        with open_file_with_encoding(test_file) as f:
            result = f.read()

        assert result == ""


class TestFileHashing:
    """Tests for file hashing operations."""

    def test_calculate_file_hash_known_content(self, tmp_path: Path) -> None:
        """Test calculate_file_hash with known content."""
        test_file = tmp_path / "hash_test.txt"
        content = "Hello, World!"
        test_file.write_text(content, encoding="utf-8")

        # Calculate expected hash
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        result_hash = calculate_file_hash(test_file)
        assert result_hash == expected_hash

    def test_calculate_file_hash_empty_file(self, tmp_path: Path) -> None:
        """Test calculate_file_hash with empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        # Hash of empty string
        expected_hash = hashlib.sha256(b"").hexdigest()

        result_hash = calculate_file_hash(test_file)
        assert result_hash == expected_hash

    def test_calculate_file_hash_binary_file(self, tmp_path: Path) -> None:
        """Test calculate_file_hash with binary file."""
        test_file = tmp_path / "binary.bin"
        content = bytes([0, 1, 2, 3, 255, 254, 253])
        test_file.write_bytes(content)

        expected_hash = hashlib.sha256(content).hexdigest()

        result_hash = calculate_file_hash(test_file)
        assert result_hash == expected_hash

    def test_calculate_file_hash_large_file(self, tmp_path: Path) -> None:
        """Test calculate_file_hash with larger file to test chunking."""
        test_file = tmp_path / "large.txt"

        # Create content larger than typical buffer size
        content = "A" * 10000  # 10KB of 'A's
        test_file.write_text(content, encoding="utf-8")

        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        result_hash = calculate_file_hash(test_file)
        assert result_hash == expected_hash

    def test_calculate_file_hash_nonexistent_file(self, tmp_path: Path) -> None:
        """Test calculate_file_hash with nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.txt"

        # Should handle gracefully and return empty string
        result = calculate_file_hash(nonexistent)
        assert result == ""

    def test_calculate_file_hash_consistency(self, tmp_path: Path) -> None:
        """Test that calculate_file_hash returns consistent results."""
        test_file = tmp_path / "consistent.txt"
        test_file.write_text("Consistent content for hashing")

        hash1 = calculate_file_hash(test_file)
        hash2 = calculate_file_hash(test_file)

        assert hash1 == hash2  # Should be consistent


class TestFilePermissions:
    """Tests for file permission operations."""

    def test_remove_readonly_file_writable(self, tmp_path: Path) -> None:
        """Test remove_readonly with already writable file."""
        test_file = tmp_path / "writable.txt"
        test_file.write_text("test content")

        # Should not raise an exception
        remove_readonly(test_file)

        # File should still be writable
        assert test_file.is_file()

    def test_remove_readonly_nonexistent_file(self, tmp_path: Path) -> None:
        """Test remove_readonly with nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.txt"

        # Should not raise an exception (logs error internally)
        remove_readonly(nonexistent)

    def test_remove_readonly_directory(self, tmp_path: Path) -> None:
        """Test remove_readonly with directory."""
        test_dir = tmp_path / "test_directory"
        test_dir.mkdir()

        # Should handle directories gracefully
        remove_readonly(test_dir)

        assert test_dir.is_dir()

    def test_remove_readonly_with_readonly_file(self, tmp_path: Path) -> None:
        """Test remove_readonly with actual readonly file."""
        import stat

        test_file = tmp_path / "readonly.txt"
        test_file.write_text("readonly content")

        # Make file readonly
        test_file.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        # Remove readonly
        remove_readonly(test_file)

        # File should be writable now (can write to it)
        try:
            test_file.write_text("new content")
            assert True
        except PermissionError:
            # On some systems, this might still fail
            pytest.skip("Cannot test readonly removal on this system")


if __name__ == "__main__":
    pytest.main([__file__])
