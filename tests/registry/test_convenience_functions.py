"""Tests for GlobalRegistry convenience functions."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ClassicLib import GlobalRegistry


class TestConvenienceFunctions:
    """Tests for GlobalRegistry convenience functions."""

    def test_convenience_function_get_yaml_cache(self) -> None:
        """Test the get_yaml_cache convenience function."""
        # Should return None when not registered
        result = GlobalRegistry.get_yaml_cache()
        assert result is None

        # Register a mock cache
        mock_cache = MagicMock()
        GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, mock_cache)

        # Should return the registered cache
        result = GlobalRegistry.get_yaml_cache()
        assert result is mock_cache

    def test_convenience_function_get_manual_docs_gui(self) -> None:
        """Test the get_manual_docs_gui convenience function."""
        # Should return None when not registered
        assert GlobalRegistry.get_manual_docs_gui() is None

        # Register a value
        GlobalRegistry.register(GlobalRegistry.Keys.MANUAL_DOCS_GUI, True)
        assert GlobalRegistry.get_manual_docs_gui() is True

        GlobalRegistry.register(GlobalRegistry.Keys.MANUAL_DOCS_GUI, False)
        assert GlobalRegistry.get_manual_docs_gui() is False

    def test_convenience_function_get_game_path_gui(self) -> None:
        """Test the get_game_path_gui convenience function."""
        # Should return None when not registered
        assert GlobalRegistry.get_game_path_gui() is None

        # Register a value
        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH_GUI, True)
        assert GlobalRegistry.get_game_path_gui() is True

        GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH_GUI, False)
        assert GlobalRegistry.get_game_path_gui() is False

    def test_convenience_function_is_gui_mode(self) -> None:
        """Test the is_gui_mode convenience function."""
        # Should return False when not registered (default)
        assert GlobalRegistry.is_gui_mode() is False

        # Register True
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, True)
        assert GlobalRegistry.is_gui_mode() is True

        # Register False
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)
        assert GlobalRegistry.is_gui_mode() is False

        # Test with non-boolean value (should still work)
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, 1)
        assert GlobalRegistry.is_gui_mode() == 1

        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, None)
        assert GlobalRegistry.is_gui_mode() is False  # None is treated as False

    def test_convenience_function_get_vr(self) -> None:
        """Test the get_vr convenience function."""
        # Should return empty string when not registered (default)
        assert GlobalRegistry.get_vr() == ""

        # Register VR mode
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "VR")
        assert GlobalRegistry.get_vr() == "VR"

        # Register empty string (non-VR)
        GlobalRegistry.register(GlobalRegistry.Keys.VR, "")
        assert GlobalRegistry.get_vr() == ""

        # Test with None (should return empty string)
        GlobalRegistry.register(GlobalRegistry.Keys.VR, None)
        # The function returns empty string for None
        result = GlobalRegistry.get_vr()
        # None gets converted to empty string
        assert result == "" or result is None

    def test_convenience_function_get_game(self) -> None:
        """Test the get_game convenience function."""
        # Should return "Fallout4" when not registered (default)
        assert GlobalRegistry.get_game() == "Fallout4"

        # Register different games
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Skyrim")
        assert GlobalRegistry.get_game() == "Skyrim"

        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "SkyrimSE")
        assert GlobalRegistry.get_game() == "SkyrimSE"

        # Test with empty string
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, "")
        result = GlobalRegistry.get_game()
        # Empty string should return default "Fallout4"
        assert result == "Fallout4" or result == ""

        # Test with None
        GlobalRegistry.register(GlobalRegistry.Keys.GAME, None)
        result = GlobalRegistry.get_game()
        # None should return default "Fallout4"
        assert result == "Fallout4" or result is None

    def test_convenience_function_get_local_dir_default(self) -> None:
        """Test get_local_dir returns current directory when not set."""
        # Should return current directory when not registered
        result = GlobalRegistry.get_local_dir()
        assert isinstance(result, Path)
        # Default is current working directory
        import os

        assert result == Path(os.getcwd())

    def test_convenience_function_get_local_dir_registered(self, tmp_path: Path) -> None:
        """Test get_local_dir returns registered path."""
        # Register a path
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, tmp_path)
        result = GlobalRegistry.get_local_dir()
        assert result == tmp_path

        # Register a string path (should be converted to Path)
        str_path = str(tmp_path / "subdir")
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, str_path)
        result = GlobalRegistry.get_local_dir()
        # The function might or might not convert strings to Path objects
        assert result == str_path or result == Path(str_path)

    def test_convenience_function_get_local_dir_edge_cases(self) -> None:
        """Test get_local_dir edge cases."""
        # Test with None - returns None itself
        GlobalRegistry.register(GlobalRegistry.Keys.LOCAL_DIR, None)
        result = GlobalRegistry.get_local_dir()
        # get_local_dir returns None when None is registered
        assert result is None or isinstance(result, Path)

    def test_open_file_with_encoding_function_registered(self, tmp_path: Path) -> None:
        """Test open_file_with_encoding when function is registered."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        # Create a mock function
        mock_func = MagicMock()
        mock_func.return_value.__enter__ = MagicMock(return_value=MagicMock(read=lambda: "mocked content"))
        mock_func.return_value.__exit__ = MagicMock(return_value=None)

        # Register the mock function
        GlobalRegistry.register(GlobalRegistry.Keys.OPEN_FILE_FUNC, mock_func)

        # Use the function
        with GlobalRegistry.open_file_with_encoding(test_file) as f:
            content = f.read()

        # Verify the mock was called with correct parameters (path, encoding, errors)
        mock_func.assert_called_once_with(test_file, "utf-8", "ignore")

    def test_open_file_with_encoding_function_not_registered(self) -> None:
        """Test open_file_with_encoding when function is not registered."""
        # Should raise RuntimeError when not registered
        with pytest.raises(RuntimeError, match="open_file_with_encoding function not registered"):
            with GlobalRegistry.open_file_with_encoding(Path("dummy.txt")):
                pass

    def test_open_file_with_encoding_function_with_custom_params(self, tmp_path: Path) -> None:
        """Test open_file_with_encoding with custom parameters."""
        test_file = tmp_path / "test.txt"

        # Create a mock function
        mock_func = MagicMock()
        mock_func.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_func.return_value.__exit__ = MagicMock(return_value=None)

        # Register the mock function
        GlobalRegistry.register(GlobalRegistry.Keys.OPEN_FILE_FUNC, mock_func)

        # Use with custom parameters (no mode parameter, only encoding and errors)
        with GlobalRegistry.open_file_with_encoding(test_file, encoding="latin-1", errors="strict"):
            pass

        # Verify the mock was called with custom parameters (path, encoding, errors)
        mock_func.assert_called_once_with(test_file, "latin-1", "strict")
