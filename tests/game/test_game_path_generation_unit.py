"""
Unit tests for game_path_generation - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import Constants, GlobalRegistry
from ClassicLib.GamePath import game_generate_paths

pytestmark = pytest.mark.unit

class TestGamePathGeneration:
    """Tests for game path generation functionality."""

    @patch('ClassicLib.GamePath.yaml_settings')
    @patch('ClassicLib.GamePath.get_game_version')
    @patch.object(GlobalRegistry, 'get_game', return_value='Fallout4')
    @patch.object(GlobalRegistry, 'get_vr', return_value='')
    def test_generate_paths_fallout4_og_version(self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_get_version: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test game_generate_paths for Fallout 4 OG version."""
        game_path = str(tmp_path / 'Fallout4')
        mock_yaml.side_effect = [game_path, 'F4SE', 'F4SE', None, None, None, None, None, f'{game_path}\\Fallout4.exe', None]
        mock_get_version.return_value = Constants.OG_VERSION
        game_generate_paths()
        assert mock_yaml.call_count >= 6
        mock_get_version.assert_called_once()

    @patch('ClassicLib.GamePath.yaml_settings')
    @patch('ClassicLib.GamePath.get_game_version')
    @patch.object(GlobalRegistry, 'get_game', return_value='Fallout4')
    @patch.object(GlobalRegistry, 'get_vr', return_value='')
    def test_generate_paths_fallout4_ng_version(self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_get_version: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test game_generate_paths for Fallout 4 NG version."""
        game_path = str(tmp_path / 'Fallout4')
        mock_yaml.side_effect = [game_path, 'F4SE', 'F4SE', None, None, None, None, None, f'{game_path}\\Fallout4.exe', None]
        mock_get_version.return_value = Constants.NG_VERSION
        game_generate_paths()
        assert mock_yaml.call_count >= 6
        mock_get_version.assert_called_once()

    @patch('ClassicLib.GamePath.yaml_settings')
    @patch.object(GlobalRegistry, 'get_game', return_value='Fallout4')
    @patch.object(GlobalRegistry, 'get_vr', return_value='')
    def test_generate_paths_missing_game_path(self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock) -> None:
        """Test game_generate_paths with missing game path."""
        mock_yaml.return_value = None
        with pytest.raises(TypeError):
            game_generate_paths()

    @patch('ClassicLib.GamePath.yaml_settings')
    @patch.object(GlobalRegistry, 'get_game', return_value='Fallout4')
    @patch.object(GlobalRegistry, 'get_vr', return_value='')
    def test_generate_paths_missing_xse_acronym(self, mock_get_vr: MagicMock, mock_get_game: MagicMock, mock_yaml: MagicMock, tmp_path: Path) -> None:
        """Test game_generate_paths with missing XSE acronym."""
        game_path = str(tmp_path / 'Fallout4')
        mock_yaml.side_effect = [game_path, 'F4SE', None]
        with pytest.raises(TypeError):
            game_generate_paths()
