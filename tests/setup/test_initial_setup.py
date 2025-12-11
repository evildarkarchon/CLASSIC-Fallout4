"""Tests for SetupCoordinator initial setup sequence."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913

from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.SetupCoordinator import SetupCoordinator


class TestInitialSetup:
    """Test suite for initial setup functionality."""

    @pytest.fixture
    def coordinator(self) -> SetupCoordinator:
        """Create a SetupCoordinator instance for testing."""
        return SetupCoordinator()

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up after tests."""
        yield
        # Reset registry state
        GlobalRegistry._registry = {}

    @patch("ClassicLib.SetupCoordinator.configure_logging")
    @patch("ClassicLib.FileGeneration.FileGenerator.generate_all_files")
    @patch("ClassicLib.BackupManager.BackupManager.run_backup")
    @patch("ClassicLib.YamlSettings.yaml_cache")
    @patch("ClassicLib.SetupCoordinator.msg_info")
    @patch("ClassicLib.SetupCoordinator.msg_success")
    @patch("ClassicLib.SetupCoordinator.docs_path_find")
    @patch("ClassicLib.SetupCoordinator.docs_generate_paths")
    @patch("ClassicLib.SetupCoordinator.game_path_find")
    @patch("ClassicLib.SetupCoordinator.game_generate_paths")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    @patch.object(GlobalRegistry, "is_gui_mode", return_value=False)
    @patch("ClassicLib.SetupCoordinator.logger")
    def test_run_initial_setup_no_game_path(
        self,
        mock_logger: MagicMock,
        mock_is_gui: MagicMock,
        mock_get_vr: MagicMock,
        mock_game_generate: MagicMock,
        mock_game_find: MagicMock,
        mock_docs_generate: MagicMock,
        mock_docs_find: MagicMock,
        mock_msg_success: MagicMock,
        mock_msg_info: MagicMock,
        mock_yaml_cache: MagicMock,
        mock_run_backup: MagicMock,
        mock_file_gen: MagicMock,
        mock_configure_logging: MagicMock,
    ) -> None:
        """Test initial setup when no game path is configured."""
        coordinator = SetupCoordinator()

        # Configure mock to return an awaitable coroutine
        async def async_return(*args, **kwargs):
            return [
                "7.31.0",  # classic_ver
                "Fallout4",  # game_name
                None,  # game_path (not configured)
            ]

        mock_yaml_cache.batch_get_settings_async.side_effect = async_return

        # Run initial setup
        coordinator.run_initial_setup()

        # Verify setup sequence
        mock_configure_logging.assert_called_once()
        mock_file_gen.assert_called_once()

        # Verify batch_get_settings_async was called
        mock_yaml_cache.batch_get_settings_async.assert_called_once()

        # Verify path generation was called (no existing path)
        mock_docs_find.assert_called_once()
        mock_docs_generate.assert_called_once()
        mock_game_find.assert_called_once()
        mock_game_generate.assert_called_once()

        # Verify messages were displayed
        assert mock_msg_info.call_count >= 3
        mock_msg_success.assert_called_once()

        # Verify logging
        mock_logger.debug.assert_called_with("> > > STARTED 7.31.0")

    @patch("ClassicLib.SetupCoordinator.configure_logging")
    @patch("ClassicLib.FileGeneration.FileGenerator.generate_all_files")
    @patch("ClassicLib.BackupManager.BackupManager.run_backup")
    @patch("ClassicLib.YamlSettings.yaml_cache")
    @patch("ClassicLib.SetupCoordinator.msg_info")
    @patch("ClassicLib.SetupCoordinator.msg_success")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_run_initial_setup_with_game_path(
        self,
        mock_get_vr: MagicMock,
        mock_msg_success: MagicMock,
        mock_msg_info: MagicMock,
        mock_yaml_cache: MagicMock,
        mock_backup: MagicMock,
        mock_file_gen: MagicMock,
        mock_configure_logging: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test initial setup when game path is already configured."""

        # Mock batch_get_settings_async to return values with game path configured
        async def async_return(*args, **kwargs):
            return [
                "7.31.0",  # classic_ver
                "Fallout4",  # game_name
                "C:/Games/Fallout4",  # game_path (configured)
            ]

        mock_yaml_cache.batch_get_settings_async.side_effect = async_return

        # Run initial setup
        coordinator.run_initial_setup()

        # Verify backup was called (path exists)
        mock_backup.assert_called_once()
        mock_file_gen.assert_called_once()

        # Path generation should NOT be called
        with patch("ClassicLib.SetupCoordinator.docs_path_find") as mock_docs_find:
            with patch("ClassicLib.SetupCoordinator.game_path_find") as mock_game_find:
                mock_docs_find.assert_not_called()
                mock_game_find.assert_not_called()

    @patch("ClassicLib.SetupCoordinator.configure_logging")
    @patch("ClassicLib.FileGeneration.FileGenerator.generate_all_files")
    @patch("ClassicLib.YamlSettings.yaml_cache")
    @patch("ClassicLib.SetupCoordinator.msg_info")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_run_initial_setup_type_error_version(
        self,
        mock_get_vr: MagicMock,
        mock_msg_info: MagicMock,
        mock_yaml_cache: MagicMock,
        mock_file_gen: MagicMock,
        mock_configure: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test that TypeError is raised when classic_ver is not a string."""
        mock_file_gen.return_value = None

        # Mock batch_get_settings_async to return non-string for version
        async def async_return(*args, **kwargs):
            return [
                123,  # classic_ver (not a string)
                "Fallout4",  # game_name
                None,  # game_path
            ]

        mock_yaml_cache.batch_get_settings_async.side_effect = async_return

        # Should raise TypeError
        with pytest.raises(TypeError):
            coordinator.run_initial_setup()

    @patch("ClassicLib.SetupCoordinator.configure_logging")
    @patch("ClassicLib.FileGeneration.FileGenerator.generate_all_files")
    @patch("ClassicLib.YamlSettings.yaml_cache")
    @patch("ClassicLib.SetupCoordinator.msg_info")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_run_initial_setup_type_error_game_name(
        self,
        mock_get_vr: MagicMock,
        mock_msg_info: MagicMock,
        mock_yaml_cache: MagicMock,
        mock_file_gen: MagicMock,
        mock_configure: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test that TypeError is raised when game_name is not a string."""
        mock_file_gen.return_value = None

        # Mock batch_get_settings_async to return non-string for game name
        async def async_return(*args, **kwargs):
            return [
                "7.31.0",  # classic_ver
                None,  # game_name (not a string)
                None,  # game_path
            ]

        mock_yaml_cache.batch_get_settings_async.side_effect = async_return

        # Should raise TypeError
        with pytest.raises(TypeError):
            coordinator.run_initial_setup()
