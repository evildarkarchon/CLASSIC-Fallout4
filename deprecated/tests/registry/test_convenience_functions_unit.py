"""
Unit tests for convenience_functions - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ClassicLib.core.registry import GlobalRegistry

pytestmark = pytest.mark.unit


class TestConvenienceFunctions:
    """Tests for GlobalRegistry convenience functions."""

    def test_convenience_function_get_yaml_cache(self) -> None:
        """Test the get_yaml_cache convenience function."""
        result = GlobalRegistry.get_yaml_cache()
        assert result is None
        mock_cache = MagicMock()
        GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, mock_cache)
        result = GlobalRegistry.get_yaml_cache()
        assert result is mock_cache

    def test_convenience_function_get_manual_docs_gui(self) -> None:
        """Test the get_manual_docs_gui convenience function."""
        assert GlobalRegistry.get_manual_docs_gui() is None
        GlobalRegistry.register(GlobalRegistry.Keys.MANUAL_DOCS_GUI, True)
        assert GlobalRegistry.get_manual_docs_gui() is True
        GlobalRegistry.register(GlobalRegistry.Keys.MANUAL_DOCS_GUI, False)
        assert GlobalRegistry.get_manual_docs_gui() is False

    def test_convenience_function_get_game_path_gui(self) -> None:
        """Test the get_game_path_gui convenience function."""
        assert GlobalRegistry.get_game_path_gui() is None
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH_GUI, True)
        assert GlobalRegistry.get_game_path_gui() is True
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH_GUI, False)
        assert GlobalRegistry.get_game_path_gui() is False

    def test_convenience_function_is_gui_mode(self) -> None:
        """Test the is_gui_mode convenience function."""
        assert GlobalRegistry.is_gui_mode() is False
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, True)
        assert GlobalRegistry.is_gui_mode() is True
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)
        assert GlobalRegistry.is_gui_mode() is False
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, 1)
        assert GlobalRegistry.is_gui_mode() == 1
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, None)
        assert GlobalRegistry.is_gui_mode() is False

    def test_convenience_function_get_vr(self) -> None:
        """Test the get_vr convenience function."""
        assert GlobalRegistry.get_vr() == ""
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "VR")
        assert GlobalRegistry.get_vr() == "VR"
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")
        assert GlobalRegistry.get_vr() == ""
        GlobalRegistry.register(GlobalRegistry.Keys.VR, None)
        result = GlobalRegistry.get_vr()
        assert result == "" or result is None

    def test_convenience_function_get_game(self) -> None:
        """Test the get_game convenience function."""
        assert GlobalRegistry.get_game() == "Fallout4"
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Skyrim")
        assert GlobalRegistry.get_game() == "Skyrim"
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "SkyrimSE")
        assert GlobalRegistry.get_game() == "SkyrimSE"
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "")
        result = GlobalRegistry.get_game()
        assert result == "Fallout4" or result == ""
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, None)
        result = GlobalRegistry.get_game()
        assert result == "Fallout4" or result is None

    def test_convenience_function_get_local_dir_default(self) -> None:
        """Test get_local_dir returns current directory when not set."""
        result = GlobalRegistry.get_local_dir()
        assert isinstance(result, Path)
        assert result == Path(Path.cwd())

    def test_convenience_function_get_local_dir_registered(self, tmp_path: Path) -> None:
        """Test get_local_dir returns registered path."""
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, tmp_path)
        result = GlobalRegistry.get_local_dir()
        assert result == tmp_path
        str_path = str(tmp_path / "subdir")
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, str_path)
        result = GlobalRegistry.get_local_dir()
        assert result == str_path or result == Path(str_path)

    def test_convenience_function_get_local_dir_edge_cases(self) -> None:
        """Test get_local_dir edge cases."""
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, None)
        result = GlobalRegistry.get_local_dir()
        assert result is None or isinstance(result, Path)

    def test_open_file_with_encoding_function_not_registered(self) -> None:
        """Test open_file_with_encoding when function is not registered."""
        with pytest.raises(RuntimeError, match="open_file_with_encoding function not registered"):
            with GlobalRegistry.open_file_with_encoding(Path("dummy.txt")):
                pass

    def test_open_file_with_encoding_function_with_custom_params(self, tmp_path: Path) -> None:
        """Test open_file_with_encoding with custom parameters."""
        test_file = tmp_path / "test.txt"
        mock_func = MagicMock()
        mock_func.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_func.return_value.__exit__ = MagicMock(return_value=None)
        GlobalRegistry.register(GlobalRegistry.Keys.OPEN_FILE_FUNC, mock_func)
        with GlobalRegistry.open_file_with_encoding(test_file, encoding="latin-1", errors="strict"):
            pass
        mock_func.assert_called_once_with(test_file, "latin-1", "strict")
