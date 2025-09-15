"""
Unit tests for game_path_validation - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from ClassicLib import GlobalRegistry
from ClassicLib.GamePath import game_path_find

pytestmark = pytest.mark.unit

class TestXSELogParsing:
    """Tests for XSE log file parsing to find game path."""

    @pytest.mark.usefixtures('init_message_handler_fixture')
    @patch('ClassicLib.GamePath.msg_error')
    @patch('ClassicLib.GamePath.msg_info')
    def test_game_path_find_missing_xse_file(self, mock_msg_info: MagicMock, mock_msg_error: MagicMock, tmp_path: Path) -> None:
        """Test game path detection when XSE file is missing."""
        with patch('ClassicLib.GamePath.yaml_settings') as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {'Game_Info.XSE_Acronym': 'f4se', 'Game_VR_Info.XSE_Acronym': 'f4sevr', 'Game_Info.Main_Root_Name': 'Fallout 4', 'Game_VR_Info.Main_Root_Name': 'Fallout 4 VR', 'Game_Info.Docs_File_XSE': None, 'Game_VR_Info.Docs_File_XSE': None}.get(key)
            game_path_find()
            mock_msg_error.assert_called()

    @pytest.mark.usefixtures('init_message_handler_fixture')
    @patch('ClassicLib.GamePath.msg_error')
    @patch('ClassicLib.GamePath.msg_info')
    def test_game_path_find_missing_xse_path_config(self, mock_msg_info: MagicMock, mock_msg_error: MagicMock) -> None:
        """Test game path detection when XSE path config is missing."""
        with patch('ClassicLib.GamePath.yaml_settings') as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {'Game_Info.XSE_Acronym': 'f4se', 'Game_VR_Info.XSE_Acronym': 'f4sevr', 'Game_Info.Main_Root_Name': 'Fallout 4', 'Game_VR_Info.Main_Root_Name': 'Fallout 4 VR', 'Game_Info.Docs_File_XSE': None, 'Game_VR_Info.Docs_File_XSE': None}.get(key)
            game_path_find()
            mock_msg_error.assert_called()

class TestYAMLValidation:
    """Tests for YAML settings validation and error handling."""

    @pytest.mark.usefixtures('init_message_handler_fixture')
    @patch('ClassicLib.GamePath.msg_error')
    @patch('ClassicLib.GamePath.msg_info')
    def test_game_path_find_invalid_yaml_types(self, mock_msg_info: MagicMock, mock_msg_error: MagicMock) -> None:
        """Test game path detection with invalid YAML types."""
        with patch('ClassicLib.GamePath.yaml_settings') as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {'Game_Info.XSE_Acronym': 123, 'Game_VR_Info.XSE_Acronym': 'f4sevr', 'Game_Info.Main_Root_Name': None, 'Game_VR_Info.Main_Root_Name': 'Fallout 4 VR'}.get(key)
            with pytest.raises(TypeError):
                game_path_find()
