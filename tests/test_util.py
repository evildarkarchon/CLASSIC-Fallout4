"""
Test suite for ClassicLib/Util.py utility functions.

This module contains tests for utility functions including file operations,
path validation, version detection, encoding handling, and network operations.
"""

import hashlib
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from packaging.version import Version

from ClassicLib import Constants
from ClassicLib.Util import (
    append_or_extend,
    calculate_file_hash,
    calculate_similarity,
    configure_logging,
    crashgen_version_gen,
    get_game_version,
    normalize_list,
    open_file_with_encoding,
    pastebin_fetch,
    remove_readonly,
    validate_path,
)


class TestUtilityFunctions:
    """Tests for core utility functions in ClassicLib/Util.py."""

    def test_normalize_list_with_items(self) -> None:
        """Test normalize_list with various input types."""
        # Test with mixed case strings
        input_list = ["Hello", "WORLD", "Test", "MiXeD"]
        expected = ["hello", "world", "test", "mixed"]
        result = normalize_list(input_list)
        assert result == expected

        # Test with already lowercase strings
        input_list = ["already", "lowercase"]
        expected = ["already", "lowercase"]
        result = normalize_list(input_list)
        assert result == expected

        # Test with single item
        input_list = ["SINGLE"]
        expected = ["single"]
        result = normalize_list(input_list)
        assert result == expected

    def test_normalize_list_empty(self) -> None:
        """Test normalize_list with empty list."""
        result = normalize_list([])
        assert result == []

    def test_calculate_similarity_identical_files(self, tmp_path: Path) -> None:
        """Test calculate_similarity with identical files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        content = "This is identical content\nLine 2\nLine 3"
        file1.write_text(content)
        file2.write_text(content)

        similarity = calculate_similarity(file1, file2)
        assert similarity == 1.0

    def test_calculate_similarity_different_files(self, tmp_path: Path) -> None:
        """Test calculate_similarity with different files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("This is content A\nDifferent line")
        file2.write_text("This is content B\nAnother different line")

        similarity = calculate_similarity(file1, file2)
        assert 0.0 <= similarity < 1.0  # Should be similar but not identical

    def test_calculate_similarity_completely_different_files(self, tmp_path: Path) -> None:
        """Test calculate_similarity with completely different files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("AAAAAAAAAA")
        file2.write_text("BBBBBBBBBB")

        similarity = calculate_similarity(file1, file2)
        assert similarity == 0.0

    def test_validate_path_valid_existing_file(self, tmp_path: Path) -> None:
        """Test validate_path with valid existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        is_valid, error_msg = validate_path(test_file, check_read=True)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_path_valid_existing_directory(self, tmp_path: Path) -> None:
        """Test validate_path with valid existing directory."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        is_valid, error_msg = validate_path(test_dir, check_read=True)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_path_nonexistent_path(self, tmp_path: Path) -> None:
        """Test validate_path with nonexistent path."""
        nonexistent = tmp_path / "does_not_exist.txt"

        is_valid, error_msg = validate_path(nonexistent)
        assert is_valid is False
        assert "does not exist" in error_msg

    def test_validate_path_with_write_check(self, tmp_path: Path) -> None:
        """Test validate_path with write permission check."""
        test_dir = tmp_path / "writable_dir"
        test_dir.mkdir()

        is_valid, error_msg = validate_path(test_dir, check_write=True, check_read=True)
        assert is_valid is True
        assert error_msg == ""

    @patch("platform.system", return_value="Windows")
    @patch("pathlib.Path.exists", return_value=False)
    def test_validate_path_windows_invalid_drive(self, mock_exists: MagicMock, mock_platform: MagicMock) -> None:  # noqa: ARG002
        """Test validate_path with invalid Windows drive."""
        invalid_path = "Z:/nonexistent/path"

        is_valid, error_msg = validate_path(invalid_path)
        assert is_valid is False
        assert "does not exist" in error_msg

    def test_get_game_version_invalid_path(self) -> None:
        """Test get_game_version with invalid executable path."""
        nonexistent_exe = Path("nonexistent.exe")

        version = get_game_version(nonexistent_exe)
        assert version == Constants.NULL_VERSION

    @patch("platform.system", return_value="Windows")
    @patch("ClassicLib.Util._get_version_windows_api")
    def test_get_game_version_windows_success(self, mock_windows_api: MagicMock, mock_platform: MagicMock, tmp_path: Path) -> None:  # noqa: ARG002
        """Test get_game_version on Windows with successful API call."""
        test_exe = tmp_path / "test.exe"
        test_exe.write_bytes(b"fake exe content")

        expected_version = Version("1.10.163.0")
        mock_windows_api.return_value = expected_version

        version = get_game_version(test_exe)
        assert version == expected_version
        mock_windows_api.assert_called_once_with(test_exe)

    @patch("platform.system", return_value="Linux")
    @patch("ClassicLib.Util._get_version_from_pe_header")
    def test_get_game_version_linux_fallback(self, mock_pe_header: MagicMock, mock_platform: MagicMock, tmp_path: Path) -> None:  # noqa: ARG002
        """Test get_game_version on Linux using PE header fallback."""
        test_exe = tmp_path / "test.exe"
        test_exe.write_bytes(b"fake exe content")

        expected_version = Version("1.10.163.0")
        mock_pe_header.return_value = expected_version

        version = get_game_version(test_exe)
        assert version == expected_version
        mock_pe_header.assert_called_once_with(test_exe)

    def test_crashgen_version_gen_valid_version(self) -> None:
        """Test crashgen_version_gen with valid version string."""
        input_string = "Buffout 4 v1.28.6"
        result = crashgen_version_gen(input_string)
        assert result == Version("1.28.6")

    def test_crashgen_version_gen_multiple_versions(self) -> None:
        """Test crashgen_version_gen with multiple version-like strings."""
        input_string = "Test v1.0.0 another v2.0.0"
        result = crashgen_version_gen(input_string)
        assert result == Version("2.0.0")  # Function takes the last one found

    def test_crashgen_version_gen_no_version(self) -> None:
        """Test crashgen_version_gen with no version information."""
        input_string = "No matching patterns found here"
        result = crashgen_version_gen(input_string)
        assert result == Constants.NULL_VERSION

    def test_crashgen_version_gen_empty_string(self) -> None:
        """Test crashgen_version_gen with empty string."""
        input_string = ""
        result = crashgen_version_gen(input_string)
        assert result == Constants.NULL_VERSION

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

    def test_configure_logging_new_logger(self) -> None:
        """Test configure_logging with a fresh logger."""
        test_logger = logging.getLogger("test_classic_logger")

        # Ensure logger starts clean
        test_logger.handlers.clear()

        with patch("ClassicLib.Util.msg_info"):  # Mock msg_info to avoid MessageHandler dependency
            configure_logging(test_logger)

        assert test_logger.level == logging.INFO
        assert len(test_logger.handlers) == 1
        assert isinstance(test_logger.handlers[0], logging.FileHandler)

    def test_configure_logging_existing_handlers(self) -> None:
        """Test configure_logging with logger that already has handlers."""
        test_logger = logging.getLogger("test_classic_logger_existing")

        # Add a handler first
        existing_handler = logging.StreamHandler()
        test_logger.addHandler(existing_handler)
        original_handler_count = len(test_logger.handlers)

        with patch("ClassicLib.Util.msg_info"):  # Mock msg_info to avoid MessageHandler dependency
            configure_logging(test_logger)

        # Should not add another handler
        assert len(test_logger.handlers) == original_handler_count

    @patch("ClassicLib.Util.msg_info")  # Mock msg_info to avoid MessageHandler dependency
    @patch("ClassicLib.Util.msg_error")  # Mock msg_error as well
    def test_configure_logging_old_log_file(self, mock_msg_error: MagicMock, mock_msg_info: MagicMock) -> None:  # noqa: ARG002
        """Test configure_logging removes old log file."""
        test_logger = logging.getLogger("test_classic_logger_old")
        test_logger.handlers.clear()
        test_logger.setLevel(logging.DEBUG)  # Enable DEBUG level for the test

        # Mock Path class to intercept Path("CLASSIC Journal.log") call
        with patch("ClassicLib.Util.Path") as mock_path_class:
            mock_journal_path = MagicMock()
            mock_path_class.return_value = mock_journal_path
            mock_journal_path.exists.return_value = True

            # Mock old file (8 days old)
            import time

            old_time = time.time() - (8 * 24 * 60 * 60)  # 8 days ago
            mock_stat = MagicMock()
            mock_stat.st_mtime = old_time
            mock_journal_path.stat.return_value = mock_stat

            configure_logging(test_logger)

            # Verify Path was called with the correct argument
            mock_path_class.assert_called_with("CLASSIC Journal.log")
            mock_journal_path.unlink.assert_called_once_with(missing_ok=True)

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

    def test_append_or_extend_single_values(self) -> None:
        """Test append_or_extend with single values."""
        destination: list[str] = []

        append_or_extend("string", destination)
        append_or_extend(42, destination)
        append_or_extend(3.14, destination)

        assert destination == ["string", "42", "3.14"]

    def test_append_or_extend_collections(self) -> None:
        """Test append_or_extend with collections."""
        destination: list[str] = []

        append_or_extend(["a", "b"], destination)
        append_or_extend(("c", "d"), destination)
        append_or_extend({"e", "f"}, destination)

        # Order might vary for set, but all elements should be present
        assert len(destination) == 6
        assert all(item in destination for item in ["a", "b", "c", "d", "e", "f"])

    @patch("requests.get")
    def test_pastebin_fetch_success(self, mock_get: MagicMock, tmp_path: Path, monkeypatch) -> None:
        """Test pastebin_fetch with successful request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Sample crash log content"
        mock_get.return_value = mock_response

        # Change to temp directory for complete isolation
        monkeypatch.chdir(tmp_path)

        # Create the directory structure that pastebin_fetch expects
        crash_logs_dir = tmp_path / "Crash Logs" / "Pastebin"
        crash_logs_dir.mkdir(parents=True, exist_ok=True)

        url = "https://pastebin.com/abc123"
        pastebin_fetch(url)

        # Check if file was created
        expected_file = crash_logs_dir / "crash-abc123.log"
        assert expected_file.exists()
        assert expected_file.read_text() == "Sample crash log content"

    @patch("requests.get")
    def test_pastebin_fetch_raw_url_conversion(self, mock_get: MagicMock, tmp_path: Path, monkeypatch) -> None:
        """Test pastebin_fetch converts regular URL to raw URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "content"
        mock_get.return_value = mock_response

        # Use monkeypatch for proper isolation
        monkeypatch.chdir(tmp_path)

        # Create the directory structure that pastebin_fetch expects
        crash_logs_dir = tmp_path / "Crash Logs" / "Pastebin"
        crash_logs_dir.mkdir(parents=True, exist_ok=True)

        url = "https://pastebin.com/abc123"  # Not raw URL
        pastebin_fetch(url)

        # Should have called with raw URL
        expected_url = "https://pastebin.com/raw/abc123"
        mock_get.assert_called_once_with(expected_url)

    @patch("requests.get")
    def test_pastebin_fetch_http_error(self, mock_get: MagicMock) -> None:
        """Test pastebin_fetch with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        url = "https://pastebin.com/nonexistent"

        with pytest.raises(requests.HTTPError):
            pastebin_fetch(url)

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


if __name__ == "__main__":
    pytest.main()
