"""
Test suite for ClassicLib/DocumentsChecker.py documents folder checking functionality.

This module contains tests for the DocumentsChecker class which validates
game documents folder and configuration files.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]

from ClassicLib.core.constants import YAML
from ClassicLib.support.documents import DocumentsChecker


class TestDocumentsChecker:
    """Tests for the DocumentsChecker class."""

    @pytest.fixture
    def checker(self) -> DocumentsChecker:
        """Create a DocumentsChecker instance for testing."""
        return DocumentsChecker()

    @patch("ClassicLib.support.versions.get_version_registry")
    @patch("ClassicLib.support.documents.get_vr", return_value="")
    def test_check_folder_configuration_no_onedrive(
        self, mock_get_vr: MagicMock, mock_get_registry: MagicMock, checker: DocumentsChecker
    ) -> None:
        """Test folder configuration check when OneDrive is NOT present."""
        # Mock Version Registry to return docs_name without OneDrive
        mock_version_info = MagicMock()
        mock_version_info.docs_name = "C:/Users/TestUser/Documents/My Games/Fallout4"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Check folder configuration
        result = checker.check_folder_configuration()

        # Should return empty string (no warning)
        assert result == ""

        # Verify OG version was requested from registry
        mock_registry.get_by_id.assert_called_once_with("FO4_OG")

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.versions.get_version_registry")
    @patch("ClassicLib.support.documents.get_vr", return_value="")
    @patch("ClassicLib.support.documents.logger")
    def test_check_folder_configuration_with_onedrive(
        self,
        mock_logger: MagicMock,
        mock_get_vr: MagicMock,
        mock_get_registry: MagicMock,
        mock_yaml_settings: MagicMock,
        checker: DocumentsChecker,
    ) -> None:
        """Test folder configuration check when OneDrive IS present."""
        # Mock Version Registry to return docs_name with OneDrive
        mock_version_info = MagicMock()
        mock_version_info.docs_name = "C:/Users/TestUser/OneDrive/Documents/My Games/Fallout4"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Mock yaml_settings for the warning message lookup
        mock_yaml_settings.return_value = "WARNING: OneDrive detected! This may cause issues."

        # Check folder configuration
        result = checker.check_folder_configuration()

        # Should return warning message
        assert result == "WARNING: OneDrive detected! This may cause issues."

        # Verify logging
        mock_logger.warning.assert_called_with(
            "OneDrive detected in documents path: C:/Users/TestUser/OneDrive/Documents/My Games/Fallout4"
        )

    @patch("ClassicLib.support.versions.get_version_registry")
    @patch("ClassicLib.support.documents.get_vr", return_value="VR")
    def test_check_folder_configuration_vr_mode(
        self, mock_get_vr: MagicMock, mock_get_registry: MagicMock, checker: DocumentsChecker
    ) -> None:
        """Test folder configuration check in VR mode uses Version Registry."""
        # Mock Version Registry to return VR docs name
        mock_version_info = MagicMock()
        mock_version_info.docs_name = "C:/Users/TestUser/Documents/My Games/Fallout4VR"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Check folder configuration
        checker.check_folder_configuration()

        # Verify VR version was requested from the registry
        mock_registry.get_by_id.assert_called_once_with("FO4_VR")

    @patch("ClassicLib.support.versions.get_version_registry")
    @patch("ClassicLib.support.documents.get_vr", return_value="")
    def test_check_folder_configuration_docs_name_type_error(
        self, mock_get_vr: MagicMock, mock_get_registry: MagicMock, checker: DocumentsChecker
    ) -> None:
        """Test TypeError when docs_name is not a string."""
        # Mock Version Registry to return None docs_name
        mock_version_info = MagicMock()
        mock_version_info.docs_name = None
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Should raise TypeError
        with pytest.raises(TypeError, match="Document name must be a string"):
            checker.check_folder_configuration()

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.versions.get_version_registry")
    @patch("ClassicLib.support.documents.get_vr", return_value="")
    def test_check_folder_configuration_docs_warn_type_error(
        self, mock_get_vr: MagicMock, mock_get_registry: MagicMock, mock_yaml_settings: MagicMock, checker: DocumentsChecker
    ) -> None:
        """Test TypeError when docs_warn is not a string."""
        # Mock Version Registry to return docs_name with OneDrive
        mock_version_info = MagicMock()
        mock_version_info.docs_name = "C:/Users/TestUser/OneDrive/Documents"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Mock yaml_settings to return non-string warning
        mock_yaml_settings.return_value = 123  # Invalid type for docs_warn

        # Should raise TypeError
        with pytest.raises(TypeError, match="Document warning must be a string"):
            checker.check_folder_configuration()

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.versions.get_version_registry")
    @patch("ClassicLib.support.documents.get_vr", return_value="")
    def test_check_folder_configuration_case_insensitive(
        self, mock_get_vr: MagicMock, mock_get_registry: MagicMock, mock_yaml_settings: MagicMock, checker: DocumentsChecker
    ) -> None:
        """Test that OneDrive detection is case-insensitive."""
        # Mock Version Registry to return docs_name with mixed case OneDrive
        mock_version_info = MagicMock()
        mock_version_info.docs_name = "C:/Users/TestUser/OnEDriVe/Documents/My Games"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Mock yaml_settings for warning
        mock_yaml_settings.return_value = "OneDrive warning"

        # Check folder configuration
        result = checker.check_folder_configuration()

        # Should detect OneDrive regardless of case
        assert result == "OneDrive warning"

    @patch("ClassicLib.support.documents.docs_check_ini")
    @patch("ClassicLib.support.documents.logger")
    def test_validate_ini_file(self, mock_logger: MagicMock, mock_docs_check: MagicMock, checker: DocumentsChecker) -> None:
        """Test validating a specific INI file."""
        # Mock docs_check_ini return
        mock_docs_check.return_value = "INI validation result"

        # Validate INI file
        result = checker.validate_ini_file("Fallout4.ini")

        # Verify result
        assert result == "INI validation result"

        # Verify docs_check_ini was called
        mock_docs_check.assert_called_once_with("Fallout4.ini")

        # Verify logging
        mock_logger.debug.assert_called_with("Validating INI file: Fallout4.ini")

    @patch.object(DocumentsChecker, "check_folder_configuration")
    @patch.object(DocumentsChecker, "validate_ini_file")
    @patch("ClassicLib.support.documents.get_game", return_value="Fallout4")
    def test_run_all_checks_with_results(
        self, mock_get_game: MagicMock, mock_validate_ini: MagicMock, mock_check_folder: MagicMock, checker: DocumentsChecker
    ) -> None:
        """Test running all checks with various results."""
        # Setup mock returns
        mock_check_folder.return_value = "OneDrive warning"
        mock_validate_ini.side_effect = [
            "Fallout4.ini: OK",
            "",  # Empty result for Custom.ini
            "Fallout4Prefs.ini: Missing settings",
        ]

        # Run all checks
        results = checker.run_all_checks()

        # Verify all checks were called
        mock_check_folder.assert_called_once()
        assert mock_validate_ini.call_count == 3
        mock_validate_ini.assert_any_call("Fallout4.ini")
        mock_validate_ini.assert_any_call("Fallout4Custom.ini")
        mock_validate_ini.assert_any_call("Fallout4Prefs.ini")

        # Verify results (empty strings filtered out)
        assert len(results) == 3
        assert "OneDrive warning" in results
        assert "Fallout4.ini: OK" in results
        assert "Fallout4Prefs.ini: Missing settings" in results

    @patch.object(DocumentsChecker, "check_folder_configuration")
    @patch.object(DocumentsChecker, "validate_ini_file")
    @patch("ClassicLib.support.documents.get_game", return_value="SkyrimSE")
    def test_run_all_checks_different_game(
        self, mock_get_game: MagicMock, mock_validate_ini: MagicMock, mock_check_folder: MagicMock, checker: DocumentsChecker
    ) -> None:
        """Test running all checks for a different game."""
        # Setup mock returns
        mock_check_folder.return_value = ""
        mock_validate_ini.return_value = "OK"

        # Run all checks
        checker.run_all_checks()

        # Verify correct INI files were checked for Skyrim
        assert mock_validate_ini.call_count == 3
        mock_validate_ini.assert_any_call("SkyrimSE.ini")
        mock_validate_ini.assert_any_call("SkyrimSECustom.ini")
        mock_validate_ini.assert_any_call("SkyrimSEPrefs.ini")

    @patch.object(DocumentsChecker, "check_folder_configuration")
    @patch.object(DocumentsChecker, "validate_ini_file")
    @patch("ClassicLib.support.documents.get_game", return_value="Fallout4")
    def test_run_all_checks_all_empty(
        self, mock_get_game: MagicMock, mock_validate_ini: MagicMock, mock_check_folder: MagicMock, checker: DocumentsChecker
    ) -> None:
        """Test running all checks when all return empty strings."""
        # Setup all mocks to return empty strings
        mock_check_folder.return_value = ""
        mock_validate_ini.return_value = ""

        # Run all checks
        results = checker.run_all_checks()

        # Should return empty list (all empty strings filtered out)
        assert results == []

    @patch.object(DocumentsChecker, "check_folder_configuration")
    @patch.object(DocumentsChecker, "validate_ini_file")
    @patch("ClassicLib.support.documents.get_game", return_value="Fallout4")
    def test_run_all_checks_mixed_results(
        self, mock_get_game: MagicMock, mock_validate_ini: MagicMock, mock_check_folder: MagicMock, checker: DocumentsChecker
    ) -> None:
        """Test running all checks with mix of valid and empty results."""
        # Setup mixed returns
        mock_check_folder.return_value = ""
        mock_validate_ini.side_effect = ["INI1 OK", "", "INI3 Warning"]

        # Run all checks
        results = checker.run_all_checks()

        # Should only include non-empty results
        assert len(results) == 2
        assert "INI1 OK" in results
        assert "INI3 Warning" in results

    @patch("ClassicLib.support.documents.docs_check_ini", side_effect=Exception("INI check failed"))
    def test_validate_ini_file_exception(self, mock_docs_check: MagicMock, checker: DocumentsChecker) -> None:
        """Test that exceptions from docs_check_ini are propagated."""
        # Should raise the exception
        with pytest.raises(Exception, match="INI check failed"):
            checker.validate_ini_file("Fallout4.ini")

    @patch.object(DocumentsChecker, "check_folder_configuration", side_effect=Exception("Folder check failed"))
    @patch("ClassicLib.support.documents.get_game", return_value="Fallout4")
    def test_run_all_checks_exception(self, mock_get_game: MagicMock, mock_check_folder: MagicMock, checker: DocumentsChecker) -> None:
        """Test that exceptions in run_all_checks are propagated."""
        # Should raise the exception
        with pytest.raises(Exception, match="Folder check failed"):
            checker.run_all_checks()

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.versions.get_version_registry")
    @patch("ClassicLib.support.documents.get_vr", return_value="")
    def test_check_folder_configuration_onedrive_in_middle(
        self, mock_get_vr: MagicMock, mock_get_registry: MagicMock, mock_yaml_settings: MagicMock, checker: DocumentsChecker
    ) -> None:
        """Test OneDrive detection when it's in the middle of the path."""
        # Mock Version Registry to return docs_name with OneDrive in middle
        mock_version_info = MagicMock()
        mock_version_info.docs_name = "C:/Users/OneDrive User/Documents/My Games"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Mock yaml_settings for warning
        mock_yaml_settings.return_value = "OneDrive warning"

        # Check folder configuration
        result = checker.check_folder_configuration()

        # Should detect OneDrive
        assert result == "OneDrive warning"

    @patch("ClassicLib.io.yaml.yaml_settings")
    @patch("ClassicLib.support.versions.get_version_registry")
    @patch("ClassicLib.support.documents.get_vr", return_value="")
    def test_check_folder_configuration_multiple_onedrive(
        self, mock_get_vr: MagicMock, mock_get_registry: MagicMock, mock_yaml_settings: MagicMock, checker: DocumentsChecker
    ) -> None:
        """Test OneDrive detection with multiple occurrences."""
        # Mock Version Registry to return docs_name with multiple OneDrive
        mock_version_info = MagicMock()
        mock_version_info.docs_name = "C:/OneDrive/Users/TestUser/OneDrive/Documents"
        mock_registry = MagicMock()
        mock_registry.get_by_id.return_value = mock_version_info
        mock_get_registry.return_value = mock_registry

        # Mock yaml_settings for warning
        mock_yaml_settings.return_value = "Multiple OneDrive warning"

        # Check folder configuration
        result = checker.check_folder_configuration()

        # Should detect OneDrive
        assert result == "Multiple OneDrive warning"
