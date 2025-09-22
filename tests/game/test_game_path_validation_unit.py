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

    @patch('ClassicLib.GamePath.msg_error')
    @patch('ClassicLib.GamePath.msg_info')
    def test_game_path_find_missing_xse_file(self, mock_msg_info: MagicMock, mock_msg_error: MagicMock, tmp_path: Path, message_handler) -> None:
        """Test game path detection when XSE file is missing."""
        with patch('ClassicLib.GamePath.yaml_settings') as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {'Game_Info.XSE_Acronym': 'f4se', 'Game_VR_Info.XSE_Acronym': 'f4sevr', 'Game_Info.Main_Root_Name': 'Fallout 4', 'Game_VR_Info.Main_Root_Name': 'Fallout 4 VR', 'Game_Info.Docs_File_XSE': None, 'Game_VR_Info.Docs_File_XSE': None}.get(key)
            with patch('ClassicLib.ResourceLoader.ResourceLoader.get_cached_game_path', return_value=None):
                with patch('ClassicLib.GamePath._game_path_find_registry', return_value=None):
                    with patch.object(GlobalRegistry, 'is_gui_mode', return_value=False):
                        with patch('builtins.input', return_value='C:/Games/Fallout4'):
                            with patch('ClassicLib.Util.validate_path', return_value=(True, '')):
                                with patch('pathlib.Path.is_dir', return_value=True):
                                    with patch('pathlib.Path.is_file', return_value=True):
                                        with patch('ClassicLib.ResourceLoader.ResourceLoader.save_path_to_cache'):
                                            game_path_find()
                                            # Should report error about missing XSE file
                                            mock_msg_error.assert_called()

    @patch('ClassicLib.GamePath.msg_error')
    @patch('ClassicLib.GamePath.msg_info')
    def test_game_path_find_missing_xse_path_config(self, mock_msg_info: MagicMock, mock_msg_error: MagicMock, message_handler) -> None:
        """Test game path detection when XSE path config is missing."""
        with patch('ClassicLib.GamePath.yaml_settings') as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {'Game_Info.XSE_Acronym': 'f4se', 'Game_VR_Info.XSE_Acronym': 'f4sevr', 'Game_Info.Main_Root_Name': 'Fallout 4', 'Game_VR_Info.Main_Root_Name': 'Fallout 4 VR', 'Game_Info.Docs_File_XSE': None, 'Game_VR_Info.Docs_File_XSE': None}.get(key)
            with patch('ClassicLib.ResourceLoader.ResourceLoader.get_cached_game_path', return_value=None):
                with patch('ClassicLib.GamePath._game_path_find_registry', return_value=None):
                    with patch.object(GlobalRegistry, 'is_gui_mode', return_value=False):
                        with patch('builtins.input', return_value='C:/Games/Fallout4'):
                            with patch('ClassicLib.Util.validate_path', return_value=(True, '')):
                                with patch('pathlib.Path.is_dir', return_value=True):
                                    with patch('pathlib.Path.is_file', return_value=True):
                                        with patch('ClassicLib.ResourceLoader.ResourceLoader.save_path_to_cache'):
                                            game_path_find()
                                            # Should report error about missing XSE config
                                            mock_msg_error.assert_called()

class TestYAMLValidation:
    """Tests for YAML settings validation and error handling."""

    @patch('ClassicLib.GamePath.msg_error')
    @patch('ClassicLib.GamePath.msg_info')
    def test_game_path_find_invalid_yaml_types(self, mock_msg_info: MagicMock, mock_msg_error: MagicMock, message_handler) -> None:
        """Test game path detection with invalid YAML types."""
        with patch('ClassicLib.GamePath.yaml_settings') as mock_yaml:
            mock_yaml.side_effect = lambda type_hint, store, key, *args: {'Game_Info.XSE_Acronym': 123, 'Game_VR_Info.XSE_Acronym': 'f4sevr', 'Game_Info.Main_Root_Name': None, 'Game_VR_Info.Main_Root_Name': 'Fallout 4 VR'}.get(key)
            with pytest.raises(TypeError):
                game_path_find()
