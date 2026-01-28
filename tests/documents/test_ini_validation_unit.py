"""Tests for INI file validation and checking functionality."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.support.docs_path import DocumentsPathManager

pytestmark = [pytest.mark.unit]


class TestIniValidation:
    """Tests for INI file validation and checking."""

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_check_ini_existing_file_success(self, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test check_ini with existing, valid INI file."""
        # Setup mock YAML settings
        mock_yaml.return_value = str(tmp_path)

        # Create a valid INI file
        ini_file = tmp_path / "Fallout4.ini"
        ini_content = """[General]
sLanguage=ENGLISH

[Display]
iSize H=1080
iSize W=1920
"""
        ini_file.write_text(ini_content)

        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        result = manager.check_ini("Fallout4.ini")

        assert "✔️" in result
        assert "No obvious corruption detected" in result

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_check_ini_missing_file(self, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test check_ini with missing INI file."""
        mock_yaml.return_value = str(tmp_path)

        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        result = manager.check_ini("Fallout4.ini")

        assert "❌ CAUTION" in result
        assert "MISSING" in result

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_check_ini_custom_ini_creation(self, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test check_ini creates custom INI file when missing."""
        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        # Mock settings to return the test directory
        mock_yaml.side_effect = lambda type_hint, store, key, *args: {  # noqa: ARG005
            "Game_Info.Root_Folder_Docs": str(tmp_path),
            "Game_VR_Info.Root_Folder_Docs": str(tmp_path),
            "Default_CustomINI": "# Default custom INI content\n[Archive]\nbInvalidateOlderFiles=1\n",
        }.get(key)

        result = manager.check_ini("Fallout4Custom.ini")

        # Should create the file and return appropriate message
        assert "WARNING" in result or "Archive Invalidation" in result

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_check_ini_corrupted_file(self, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test check_ini handles corrupted INI files."""
        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        # Create a corrupted INI file
        ini_file = tmp_path / "Fallout4.ini"
        ini_file.write_text("This is not valid INI content [broken")

        # Mock settings
        mock_yaml.side_effect = lambda type_hint, store, key, *args: str(tmp_path) if "Root_Folder_Docs" in key else None  # noqa: ARG005

        result = manager.check_ini("Fallout4.ini")

        # Should detect corruption
        assert "CAUTION" in result
        assert "BROKEN" in result

    def test_check_ini_invalid_docs_name_type(self) -> None:
        """Test check_ini raises TypeError for invalid docs_name."""
        manager = DocumentsPathManager()
        manager.docs_name = None  # type: ignore[assignment] # Invalid type for testing

        with pytest.raises(TypeError):
            manager.check_ini("test.ini")

    @patch("ClassicLib.io.yaml.yaml_settings", return_value=None)
    def test_check_ini_invalid_folder_docs_type(self, mock_yaml: MagicMock) -> None:  # noqa: ARG002
        """Test check_ini raises TypeError for invalid folder_docs."""
        manager = DocumentsPathManager()
        manager.docs_name = "Fallout4"

        with pytest.raises(TypeError):
            manager.check_ini("test.ini")

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_generate_paths_success(self, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test generate_paths creates correct paths from settings."""
        manager = DocumentsPathManager()

        # Mock the required YAML settings
        mock_yaml.side_effect = lambda type_hint, store, key, *args: {  # noqa: ARG005
            "Game_Info.XSE_Acronym": "f4se",
            "Game_VR_Info.XSE_Acronym": "f4sevr",
            "Game_Info.Root_Folder_Docs": str(tmp_path),
            "Game_VR_Info.Root_Folder_Docs": None,  # Force fallback
        }.get(key)

        with patch.object(manager, "_update_game_setting") as mock_update:
            manager.generate_paths()

            # Verify paths are updated correctly
            mock_update.assert_called()

    @patch("ClassicLib.io.yaml.yaml_settings")
    def test_generate_paths_missing_settings(self, mock_yaml: MagicMock) -> None:
        """Test generate_paths raises TypeError for missing settings."""
        mock_yaml.return_value = None  # Simulate missing settings

        manager = DocumentsPathManager()

        with pytest.raises(TypeError):
            manager.generate_paths()
