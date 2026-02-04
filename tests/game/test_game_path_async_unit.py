"""Unit tests for async game path functionality.

This file contains unit tests for async methods in GamePath module:
- GamePathFinder.create_async()
- find_game_path_async()
- game_path_find_async()
- game_generate_paths_async()
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.core.constants import NULL_VERSION, YAML
from ClassicLib.core.registry import GlobalRegistry

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class TestGamePathFinderCreateAsync:
    """Tests for GamePathFinder.create_async() factory method."""

    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    async def test_create_async_returns_instance(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml_async: AsyncMock,
        message_handler,
    ) -> None:
        """Test create_async returns a properly initialized GamePathFinder."""

        # Create async mock that returns different values per call
        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Docs_File_XSE" in key:
                return "C:/Docs/Fallout4/F4SE/f4se.log"
            elif "XSE_Acronym" in key and "Game_Info" in key:
                return "F4SE"
            elif "Main_Root_Name" in key:
                return "Fallout 4"
            return "F4SE"

        mock_yaml_async.side_effect = yaml_side_effect

        from ClassicLib.support.game_path import GamePathFinder

        finder = await GamePathFinder.create_async()

        assert finder is not None
        assert finder.exe_name == "Fallout4.exe"
        assert finder.xse_file == "C:/Docs/Fallout4/F4SE/f4se.log"
        assert finder.xse_acronym == "F4SE"
        assert finder.xse_acronym_base == "F4SE"
        assert finder.game_name == "Fallout 4"

    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="VR")
    async def test_create_async_vr_mode(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml_async: AsyncMock,
        message_handler,
    ) -> None:
        """Test create_async handles VR mode correctly."""

        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Docs_File_XSE" in key:
                return "C:/Docs/Fallout4VR/F4SEVR/f4sevr.log"
            elif "VR_Info.XSE_Acronym" in key:
                return "F4SEVR"
            elif "Game_Info.XSE_Acronym" in key:
                return "F4SE"
            elif "Main_Root_Name" in key:
                return "Fallout 4 VR"
            return "F4SE"

        mock_yaml_async.side_effect = yaml_side_effect

        from ClassicLib.support.game_path import GamePathFinder

        finder = await GamePathFinder.create_async()

        assert finder.exe_name == "Fallout4VR.exe"
        assert finder.xse_acronym == "F4SEVR"

    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    async def test_create_async_invalid_types_raises_typeerror(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml_async: AsyncMock,
        message_handler,
    ) -> None:
        """Test create_async raises TypeError when YAML settings have invalid types."""

        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Docs_File_XSE" in key:
                return "C:/Docs/Fallout4/F4SE/f4se.log"
            elif "XSE_Acronym" in key:
                return 123  # Invalid type
            elif "Main_Root_Name" in key:
                return "Fallout 4"
            return "F4SE"

        mock_yaml_async.side_effect = yaml_side_effect

        from ClassicLib.support.game_path import GamePathFinder

        with pytest.raises(TypeError):
            await GamePathFinder.create_async()


class TestFindGamePathAsync:
    """Tests for GamePathFinder.find_game_path_async() method."""

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.PathValidator")
    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch("ClassicLib.support.resources.ResourceLoader.get_cached_game_path_async")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    async def test_find_game_path_async_uses_cached_path(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_get_cached: AsyncMock,
        mock_yaml_async: AsyncMock,
        mock_path_validator: MagicMock,
        mock_rust_finder_cls: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test find_game_path_async uses cached path when available."""
        game_path = tmp_path / "Fallout4"
        game_path.mkdir()
        exe_path = game_path / "Fallout4.exe"
        exe_path.write_text("# Fake exe")

        mock_get_cached.return_value = game_path

        # Mock Rust components
        mock_path_validator.is_valid_path.return_value = True
        mock_rust_finder = MagicMock()
        mock_rust_finder.validate_game_path.return_value = None
        mock_rust_finder_cls.return_value = mock_rust_finder

        # Create async side effect function
        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Docs_File_XSE" in key:
                return "C:/Docs/Fallout4/F4SE/f4se.log"
            elif "XSE_Acronym" in key:
                return "F4SE"
            elif "Main_Root_Name" in key:
                return "Fallout 4"
            elif "Root_Folder_Game" in key:
                return str(game_path)
            return None

        mock_yaml_async.side_effect = yaml_side_effect

        from ClassicLib.support.game_path import GamePathFinder

        finder = await GamePathFinder.create_async()
        await finder.find_game_path_async()

        assert GlobalRegistry.get(GlobalRegistry.Keys.GAME_PATH) == game_path

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.PathValidator")
    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch("ClassicLib.support.resources.ResourceLoader.get_cached_game_path_async")
    @patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    async def test_find_game_path_async_uses_rust_finder(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_save_cache: MagicMock,
        mock_get_cached: AsyncMock,
        mock_yaml_async: AsyncMock,
        mock_path_validator: MagicMock,
        mock_rust_finder_cls: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test find_game_path_async uses Rust finder when no cache."""
        game_path = tmp_path / "Fallout4"
        game_path.mkdir()
        (game_path / "Fallout4.exe").write_text("# Fake exe")

        mock_get_cached.return_value = None
        mock_path_validator.is_valid_path.return_value = True

        # Mock Rust finder to return game path
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.return_value = str(game_path)
        mock_rust_finder.validate_game_path.return_value = None
        mock_rust_finder_cls.return_value = mock_rust_finder

        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Docs_File_XSE" in key:
                return "C:/Docs/Fallout4/F4SE/f4se.log"
            elif "XSE_Acronym" in key:
                return "F4SE"
            elif "Main_Root_Name" in key:
                return "Fallout 4"
            return None

        mock_yaml_async.side_effect = yaml_side_effect

        from ClassicLib.support.game_path import GamePathFinder

        finder = await GamePathFinder.create_async()
        await finder.find_game_path_async()

        # Verify Rust finder was called
        mock_rust_finder.find_game_path.assert_called_once()
        assert GlobalRegistry.get(GlobalRegistry.Keys.GAME_PATH) == game_path

    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch("ClassicLib.support.game_path.PathValidator")
    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch("ClassicLib.support.resources.ResourceLoader.get_cached_game_path_async")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    @patch.object(GlobalRegistry, "is_gui_mode", return_value=True)
    async def test_find_game_path_async_skips_registry_on_linux(
        self,
        mock_is_gui: MagicMock,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_get_cached: AsyncMock,
        mock_yaml_async: AsyncMock,
        mock_path_validator: MagicMock,
        mock_rust_finder_cls: MagicMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test find_game_path_async falls back to GUI when Rust finder fails."""
        mock_get_cached.return_value = None
        game_path = tmp_path / "Fallout4"
        game_path.mkdir()

        # Mock Rust finder to fail (triggering GUI fallback)
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.side_effect = FileNotFoundError("Not found")
        mock_rust_finder_cls.return_value = mock_rust_finder

        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Docs_File_XSE" in key:
                return None  # Missing file
            elif "XSE_Acronym" in key:
                return "F4SE"
            elif "Main_Root_Name" in key:
                return "Fallout 4"
            return None

        mock_yaml_async.side_effect = yaml_side_effect

        from ClassicLib.support.game_path import GamePathFinder

        # Mock the GUI dialog to return a path
        with patch("ClassicLib.support.game_path.show_game_path_dialog_static", return_value=game_path):
            with patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache_async"):
                finder = await GamePathFinder.create_async()
                await finder.find_game_path_async()

        assert GlobalRegistry.get(GlobalRegistry.Keys.GAME_PATH) == game_path

    @patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache_async")
    @patch("platform.system", return_value="Linux")
    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch("ClassicLib.support.resources.ResourceLoader.get_cached_game_path_async")
    @patch("ClassicLib.support.game_path.RustGamePathFinder")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    @patch.object(GlobalRegistry, "is_gui_mode", return_value=False)
    async def test_find_game_path_async_console_fallback(
        self,
        mock_is_gui: MagicMock,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_rust_finder_cls: MagicMock,
        mock_get_cached: AsyncMock,
        mock_yaml_async: AsyncMock,
        mock_platform: MagicMock,
        mock_save_cache: AsyncMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test find_game_path_async falls back to Rust finder then user input."""
        game_path = tmp_path / "Fallout4"
        game_path.mkdir()
        (game_path / "Fallout4.exe").write_text("# Fake exe")

        mock_get_cached.return_value = None

        xse_file = tmp_path / "f4se.log"
        xse_file.write_text("plugin directory = C:\\Games\\Fallout4\\Data\\F4SE\\Plugins")

        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Docs_File_XSE" in key:
                return str(xse_file)
            elif "XSE_Acronym" in key:
                return "F4SE"
            elif "Main_Root_Name" in key:
                return "Fallout 4"
            return None

        mock_yaml_async.side_effect = yaml_side_effect

        # Mock RustGamePathFinder to return the game path via find_game_path
        mock_rust_finder = MagicMock()
        mock_rust_finder.find_game_path.return_value = str(game_path)
        mock_rust_finder_cls.return_value = mock_rust_finder

        from ClassicLib.support.game_path import GamePathFinder

        finder = await GamePathFinder.create_async()
        await finder.find_game_path_async()

        assert GlobalRegistry.get(GlobalRegistry.Keys.GAME_PATH) == game_path


class TestGamePathFindAsync:
    """Tests for game_path_find_async() top-level function."""

    @patch("ClassicLib.support.game_path.GamePathFinder.create_async")
    async def test_game_path_find_async_calls_finder(
        self,
        mock_create: AsyncMock,
        message_handler,
    ) -> None:
        """Test game_path_find_async creates finder and calls find_game_path_async."""
        mock_finder = AsyncMock()
        mock_create.return_value = mock_finder

        from ClassicLib.support.game_path import game_path_find_async

        await game_path_find_async()

        mock_create.assert_called_once()
        mock_finder.find_game_path_async.assert_called_once()


class TestGameGeneratePathsAsync:
    """Tests for game_generate_paths_async() function."""

    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch("ClassicLib.Utils.version_utils.read_game_exe_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    async def test_generate_paths_async_fallout4_og(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml_async: AsyncMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test game_generate_paths_async for Fallout 4 OG version."""
        game_path = str(tmp_path / "Fallout4")

        call_count = 0

        async def yaml_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            key = args[2] if len(args) > 2 else ""
            if "Root_Folder_Game" in key:
                return game_path
            elif "XSE_Acronym" in key:
                return "F4SE"
            elif "Game_File_EXE" in key:
                return f"{game_path}\\Fallout4.exe"
            return None

        mock_yaml_async.side_effect = yaml_side_effect

        from packaging.version import Version

        mock_get_version.return_value = Version("1.10.163.0")

        from ClassicLib.support.game_path import game_generate_paths_async

        await game_generate_paths_async()

        assert call_count >= 6

    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch("ClassicLib.Utils.version_utils.read_game_exe_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="VR")
    async def test_generate_paths_async_fallout4_vr(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml_async: AsyncMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test game_generate_paths_async for Fallout 4 VR."""
        game_path = str(tmp_path / "Fallout4VR")

        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Root_Folder_Game" in key:
                return game_path
            elif "VR_Info.XSE_Acronym" in key:
                return "F4SEVR"
            elif "Game_Info.XSE_Acronym" in key:
                return "F4SE"
            elif "Game_File_EXE" in key:
                return f"{game_path}\\Fallout4VR.exe"
            return None

        mock_yaml_async.side_effect = yaml_side_effect

        from packaging.version import Version

        mock_get_version.return_value = Version("1.2.72.0")

        from ClassicLib.support.game_path import game_generate_paths_async

        await game_generate_paths_async()

        assert mock_yaml_async.call_count >= 6

    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    async def test_generate_paths_async_missing_game_path(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml_async: AsyncMock,
        message_handler,
    ) -> None:
        """Test game_generate_paths_async raises TypeError with missing path."""

        async def yaml_side_effect(*args, **kwargs):
            return None

        mock_yaml_async.side_effect = yaml_side_effect

        from ClassicLib.support.game_path import game_generate_paths_async

        with pytest.raises(TypeError):
            await game_generate_paths_async()

    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    async def test_generate_paths_async_missing_xse_acronym(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml_async: AsyncMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test game_generate_paths_async raises TypeError with missing XSE acronym."""
        game_path = str(tmp_path / "Fallout4")

        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Root_Folder_Game" in key:
                return game_path
            elif "XSE_Acronym" in key:
                return None
            return None

        mock_yaml_async.side_effect = yaml_side_effect

        from ClassicLib.support.game_path import game_generate_paths_async

        with pytest.raises(TypeError):
            await game_generate_paths_async()

    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch("ClassicLib.Utils.version_utils.read_game_exe_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    async def test_generate_paths_async_null_version_uses_default(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml_async: AsyncMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test game_generate_paths_async uses default when version is NULL_VERSION."""
        game_path = str(tmp_path / "Fallout4")

        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Root_Folder_Game" in key:
                return game_path
            elif "XSE_Acronym" in key:
                return "F4SE"
            elif "Game_File_EXE" in key:
                return f"{game_path}\\Fallout4.exe"
            return None

        mock_yaml_async.side_effect = yaml_side_effect
        mock_get_version.return_value = NULL_VERSION

        from ClassicLib.support.game_path import game_generate_paths_async

        await game_generate_paths_async()

        # Should complete without error using default version
        assert mock_yaml_async.call_count >= 6

    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch("ClassicLib.Utils.version_utils.read_game_exe_version")
    @patch.object(GlobalRegistry, "get_game", return_value="Starfield")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    async def test_generate_paths_async_unsupported_game(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_get_version: MagicMock,
        mock_yaml_async: AsyncMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test game_generate_paths_async raises ValueError for unsupported game."""
        game_path = str(tmp_path / "Starfield")

        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Root_Folder_Game" in key:
                return game_path
            elif "XSE_Acronym" in key:
                return "SFSE"
            elif "Game_File_EXE" in key:
                return f"{game_path}\\Starfield.exe"
            return None

        mock_yaml_async.side_effect = yaml_side_effect

        from packaging.version import Version

        mock_get_version.return_value = Version("1.0.0")

        from ClassicLib.support.game_path import game_generate_paths_async

        with pytest.raises(ValueError, match="Unsupported game"):
            await game_generate_paths_async()


class TestSaveGamePathAsync:
    """Tests for _save_game_path_async method."""

    @patch("ClassicLib.support.resources.ResourceLoader.save_path_to_cache_async")
    @patch("ClassicLib.io.yaml.yaml_settings_async")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    async def test_save_game_path_async_saves_and_registers(
        self,
        mock_get_vr: MagicMock,
        mock_get_game: MagicMock,
        mock_yaml_async: AsyncMock,
        mock_save_cache: AsyncMock,
        tmp_path: Path,
        message_handler,
    ) -> None:
        """Test _save_game_path_async saves to cache and registers path."""
        game_path = tmp_path / "Fallout4"
        game_path.mkdir()

        async def yaml_side_effect(*args, **kwargs):
            key = args[2] if len(args) > 2 else ""
            if "Docs_File_XSE" in key:
                return "C:/Docs/Fallout4/F4SE/f4se.log"
            elif "XSE_Acronym" in key:
                return "F4SE"
            elif "Main_Root_Name" in key:
                return "Fallout 4"
            return None

        mock_yaml_async.side_effect = yaml_side_effect

        from ClassicLib.support.game_path import GamePathFinder

        finder = await GamePathFinder.create_async()
        await finder._save_game_path_async(game_path)

        mock_save_cache.assert_called_once_with(game_path, "GamePath")
        assert GlobalRegistry.get(GlobalRegistry.Keys.GAME_PATH) == game_path
