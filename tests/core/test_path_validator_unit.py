"""
Unit tests for path_validator - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.PathValidator import PathValidator

pytestmark = pytest.mark.unit

class TestPathValidator:
    """Tests for the PathValidator class."""

    def test_is_valid_path_existing_string(self, tmp_path: Path) -> None:
        """Test is_valid_path with existing path as string."""
        test_dir = tmp_path / 'test_directory'
        test_dir.mkdir()
        assert PathValidator.is_valid_path(str(test_dir)) is True

    def test_is_valid_path_existing_pathobj(self, tmp_path: Path) -> None:
        """Test is_valid_path with existing path as Path object."""
        test_file = tmp_path / 'test_file.txt'
        test_file.write_text('content')
        assert PathValidator.is_valid_path(test_file) is True

    def test_is_valid_path_nonexistent(self) -> None:
        """Test is_valid_path with non-existent path."""
        assert PathValidator.is_valid_path('/nonexistent/path/to/nowhere') is False

    def test_is_valid_path_invalid_string(self) -> None:
        """Test is_valid_path with invalid path string."""
        assert PathValidator.is_valid_path('') is False
        assert PathValidator.is_valid_path(':::invalid:::') is False

    def test_is_valid_path_none(self) -> None:
        """Test is_valid_path with None value."""
        assert PathValidator.is_valid_path(None) is False

    @patch('ClassicLib.ScanLog.Util.is_valid_custom_scan_path')
    def test_is_restricted_path_unrestricted(self, mock_is_valid: MagicMock) -> None:
        """Test is_restricted_path with unrestricted path."""
        mock_is_valid.return_value = True
        assert PathValidator.is_restricted_path('C:/Users/Test/Documents') is False
        mock_is_valid.assert_called_once_with('C:/Users/Test/Documents')

    @patch('ClassicLib.ScanLog.Util.is_valid_custom_scan_path')
    def test_is_restricted_path_restricted(self, mock_is_valid: MagicMock) -> None:
        """Test is_restricted_path with restricted path."""
        mock_is_valid.return_value = False
        assert PathValidator.is_restricted_path('C:/Windows/System32') is True

    @patch('ClassicLib.ScanLog.Util.is_valid_custom_scan_path', side_effect=Exception('Check failed'))
    def test_is_restricted_path_exception(self, mock_is_valid: MagicMock) -> None:
        """Test is_restricted_path when exception occurs."""
        assert PathValidator.is_restricted_path('C:/SomePath') is True

    @patch('ClassicLib.ScanLog.Util.is_valid_custom_scan_path')
    def test_is_restricted_path_with_pathobj(self, mock_is_valid: MagicMock) -> None:
        """Test is_restricted_path with Path object."""
        mock_is_valid.return_value = True
        test_path = Path('C:/Users/Test/Documents')
        assert PathValidator.is_restricted_path(test_path) is False
        mock_is_valid.assert_called_once_with(str(test_path))

    @patch.object(PathValidator, 'validate_custom_scan_path')
    @patch('ClassicLib.PathValidator.logger')
    def test_validate_all_settings_paths(self, mock_logger: MagicMock, mock_validate_custom: MagicMock) -> None:
        """Test validate_all_settings_paths calls all validation methods."""
        PathValidator.validate_all_settings_paths()
        mock_validate_custom.assert_called_once()
        mock_logger.debug.assert_any_call('Validating all settings paths')
        mock_logger.debug.assert_any_call('Path validation complete')

    @patch.object(PathValidator, 'validate_custom_scan_path', side_effect=Exception('Validation failed'))
    @patch('ClassicLib.PathValidator.logger')
    def test_validate_all_settings_paths_exception(self, mock_logger: MagicMock, mock_validate_custom: MagicMock) -> None:
        """Test that exceptions in validate_all_settings_paths are propagated."""
        with pytest.raises(Exception, match='Validation failed'):
            PathValidator.validate_all_settings_paths()

    def test_is_valid_path_special_chars(self, tmp_path: Path) -> None:
        """Test is_valid_path with special characters in path."""
        special_dir = tmp_path / 'Dir with Spaces & Chars'
        special_dir.mkdir()
        assert PathValidator.is_valid_path(special_dir) is True
        assert PathValidator.is_valid_path(str(special_dir)) is True

    @patch('ClassicLib.ScanLog.Util.is_valid_custom_scan_path')
    def test_is_restricted_path_empty_string(self, mock_is_valid: MagicMock) -> None:
        """Test is_restricted_path with empty string."""
        mock_is_valid.return_value = False
        assert PathValidator.is_restricted_path('') is True
