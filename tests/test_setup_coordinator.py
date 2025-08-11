"""Tests for SetupCoordinator module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.SetupCoordinator import SetupCoordinator


class TestSetupCoordinator:
    """Test suite for SetupCoordinator class."""

    @pytest.fixture
    def coordinator(self) -> SetupCoordinator:
        """Create a SetupCoordinator instance for testing."""
        return SetupCoordinator()

    @pytest.fixture(autouse=True)
    def cleanup(self) -> None:
        """Clean up after tests."""
        yield
        # Reset registry state
        GlobalRegistry._registry = {}

    def test_initialization(self, coordinator: SetupCoordinator) -> None:
        """Test SetupCoordinator initialization."""
        # Verify all components are initialized
        assert coordinator.file_generator is not None
        assert coordinator.integrity_checker is not None
        assert coordinator.backup_manager is not None
        assert coordinator.docs_checker is not None
        assert coordinator.path_validator is not None

    @patch("ClassicLib.SetupCoordinator.configure_logging")
    @patch("ClassicLib.FileGeneration.FileGenerator.generate_all_files")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch("ClassicLib.SetupCoordinator.msg_info")
    @patch("ClassicLib.SetupCoordinator.msg_success")
    @patch("ClassicLib.SetupCoordinator.docs_path_find")
    @patch("ClassicLib.SetupCoordinator.docs_generate_paths")
    @patch("ClassicLib.SetupCoordinator.game_path_find")
    @patch("ClassicLib.SetupCoordinator.game_generate_paths")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    @patch("ClassicLib.SetupCoordinator.logger")
    def test_run_initial_setup_no_game_path(
        self,
        mock_logger: MagicMock,
        mock_get_vr: MagicMock,
        mock_game_generate: MagicMock,
        mock_game_find: MagicMock,
        mock_docs_generate: MagicMock,
        mock_docs_find: MagicMock,
        mock_msg_success: MagicMock,
        mock_msg_info: MagicMock,
        mock_yaml: MagicMock,
        mock_file_gen: MagicMock,
        mock_configure_logging: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test initial setup when no game path is configured."""
        # Mock yaml_settings returns
        mock_yaml.side_effect = [
            "7.31.0",  # classic_ver
            "Fallout4",  # game_name
            None,  # game_path (not configured)
        ]

        # Run initial setup
        coordinator.run_initial_setup()

        # Verify setup sequence
        mock_configure_logging.assert_called_once()
        mock_file_gen.assert_called_once()

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
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch("ClassicLib.SetupCoordinator.msg_info")
    @patch("ClassicLib.SetupCoordinator.msg_success")
    @patch.object(GlobalRegistry, "get_vr", return_value="")
    def test_run_initial_setup_with_game_path(
        self,
        mock_get_vr: MagicMock,
        mock_msg_success: MagicMock,
        mock_msg_info: MagicMock,
        mock_yaml: MagicMock,
        mock_backup: MagicMock,
        mock_file_gen: MagicMock,
        mock_configure_logging: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test initial setup when game path is already configured."""
        # Mock yaml_settings returns
        mock_yaml.side_effect = [
            "7.31.0",  # classic_ver
            "Fallout4",  # game_name
            "C:/Games/Fallout4",  # game_path (configured)
        ]

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
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    def test_run_initial_setup_type_error_version(
        self, mock_yaml: MagicMock, mock_file_gen: MagicMock, mock_configure: MagicMock, coordinator: SetupCoordinator
    ) -> None:
        """Test that TypeError is raised when classic_ver is not a string."""
        mock_file_gen.return_value = None

        # Mock yaml_settings to return non-string for version
        mock_yaml.side_effect = [
            123,  # classic_ver (not a string)
            "Fallout4",  # game_name
        ]

        # Should raise TypeError
        with pytest.raises(TypeError):
            coordinator.run_initial_setup()

    @patch("ClassicLib.SetupCoordinator.configure_logging")
    @patch("ClassicLib.FileGeneration.FileGenerator.generate_all_files")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    def test_run_initial_setup_type_error_game_name(
        self, mock_yaml: MagicMock, mock_file_gen: MagicMock, mock_configure: MagicMock, coordinator: SetupCoordinator
    ) -> None:
        """Test that TypeError is raised when game_name is not a string."""
        mock_file_gen.return_value = None

        # Mock yaml_settings to return non-string for game name
        mock_yaml.side_effect = [
            "7.31.0",  # classic_ver
            None,  # game_name (not a string)
        ]

        # Should raise TypeError
        with pytest.raises(TypeError):
            coordinator.run_initial_setup()

    @patch("ClassicLib.GameIntegrity.GameIntegrityChecker.run_full_check")
    @patch("ClassicLib.SetupCoordinator.xse_check_integrity")
    @patch("ClassicLib.SetupCoordinator.xse_check_hashes")
    @patch("ClassicLib.DocumentsChecker.DocumentsChecker.run_all_checks")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_combined_results(
        self,
        mock_get_game: MagicMock,
        mock_docs_checks: MagicMock,
        mock_xse_hashes: MagicMock,
        mock_xse_integrity: MagicMock,
        mock_game_check: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test generate_combined_results combines all check results."""
        # Mock return values
        mock_game_check.return_value = "Game OK\n"
        mock_xse_integrity.return_value = "XSE OK\n"
        mock_xse_hashes.return_value = "Hashes OK\n"
        mock_docs_checks.return_value = ["Docs OK\n"]

        # Generate results
        result = coordinator.generate_combined_results()

        # Verify all checks were called
        mock_game_check.assert_called_once()
        mock_xse_integrity.assert_called_once()
        mock_xse_hashes.assert_called_once()
        mock_docs_checks.assert_called_once()

        # Verify result contains all outputs
        assert "Game OK" in result
        assert "XSE OK" in result
        assert "Hashes OK" in result
        assert "Docs OK" in result

    @patch("ClassicLib.GameIntegrity.GameIntegrityChecker.run_full_check")
    @patch("ClassicLib.SetupCoordinator.xse_check_integrity")
    @patch("ClassicLib.SetupCoordinator.xse_check_hashes")
    @patch("ClassicLib.DocumentsChecker.DocumentsChecker.run_all_checks")
    @patch.object(GlobalRegistry, "get_game", return_value="SkyrimSE")
    def test_generate_combined_results_different_game(
        self,
        mock_get_game: MagicMock,
        mock_docs_checks: MagicMock,
        mock_xse_hashes: MagicMock,
        mock_xse_integrity: MagicMock,
        mock_game_check: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test generate_combined_results with different game."""
        # Mock return values
        mock_game_check.return_value = "Skyrim OK\n"
        mock_xse_integrity.return_value = ""
        mock_xse_hashes.return_value = ""
        mock_docs_checks.return_value = []

        # Generate results
        result = coordinator.generate_combined_results()

        # Verify game name was used
        mock_get_game.assert_called_once()
        assert "Skyrim OK" in result

    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettingsCache.classic_settings")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_yaml_cache")
    def test_initialize_application_gui_mode(
        self,
        mock_get_cache: MagicMock,
        mock_yaml: MagicMock,
        mock_classic: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization in GUI mode."""
        # Mock YAML cache
        mock_cache = MagicMock()
        mock_cache.STATIC_YAML_STORES = ["store1", "store2"]
        mock_cache.get_path_for_store.return_value = Path("test.yaml")
        mock_cache.load_yaml.return_value = None
        mock_get_cache.return_value = mock_cache

        # Mock settings
        mock_classic.side_effect = [False, "Fallout 4"]  # VR Mode, Managed Game
        mock_yaml.return_value = False  # is_prerelease

        # Initialize application
        coordinator.initialize_application(is_gui=True)

        # Verify message handler was initialized for GUI
        mock_init_handler.assert_called_once_with(parent=None, is_gui_mode=True)

        # Verify registry was set up
        assert GlobalRegistry.get(GlobalRegistry.Keys.IS_GUI_MODE) is True

        # Verify paths were validated
        mock_validate_paths.assert_called_once()

    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettingsCache.classic_settings")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_yaml_cache")
    def test_initialize_application_gui_mode_with_parent(
        self,
        mock_get_cache: MagicMock,
        mock_yaml: MagicMock,
        mock_classic: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization in GUI mode with parent widget."""
        # Mock YAML cache
        mock_cache = MagicMock()
        mock_cache.STATIC_YAML_STORES = []
        mock_get_cache.return_value = mock_cache

        # Mock settings
        mock_classic.side_effect = [False, "Fallout 4"]
        mock_yaml.return_value = False

        # Create a mock parent widget
        mock_parent = MagicMock()

        # Initialize application with parent
        coordinator.initialize_application(is_gui=True, parent=mock_parent)

        # Verify message handler was initialized with parent
        mock_init_handler.assert_called_once_with(parent=mock_parent, is_gui_mode=True)

        # Verify registry was set up
        assert GlobalRegistry.get(GlobalRegistry.Keys.IS_GUI_MODE) is True

    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettingsCache.classic_settings")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_yaml_cache")
    def test_initialize_application_cli_mode(
        self,
        mock_get_cache: MagicMock,
        mock_yaml: MagicMock,
        mock_classic: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization in CLI mode."""
        # Mock YAML cache
        mock_cache = MagicMock()
        mock_cache.STATIC_YAML_STORES = []
        mock_get_cache.return_value = mock_cache

        # Mock settings
        mock_classic.side_effect = [True, "Skyrim SE"]  # VR Mode, Managed Game
        mock_yaml.return_value = True  # is_prerelease

        # Initialize application
        coordinator.initialize_application(is_gui=False)

        # Verify message handler was initialized for CLI
        mock_init_handler.assert_called_once_with(parent=None, is_gui_mode=False)

        # Verify registry was set up
        assert GlobalRegistry.get(GlobalRegistry.Keys.IS_GUI_MODE) is False
        assert GlobalRegistry.get(GlobalRegistry.Keys.VR) == "VR"
        assert GlobalRegistry.get(GlobalRegistry.Keys.GAME) == "SkyrimSE"

    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettingsCache.classic_settings")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_yaml_cache")
    def test_initialize_application_frozen_executable(
        self,
        mock_get_cache: MagicMock,
        mock_yaml: MagicMock,
        mock_classic: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization for frozen executable."""
        # Mock YAML cache
        mock_cache = MagicMock()
        mock_cache.STATIC_YAML_STORES = []
        mock_get_cache.return_value = mock_cache

        # Mock settings
        mock_classic.side_effect = [False, "Fallout 4"]
        mock_yaml.return_value = False

        # Mock frozen state
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "executable", "C:/Program Files/CLASSIC/CLASSIC.exe"):
                # Initialize application
                coordinator.initialize_application(is_gui=False)

                # Verify local dir was set from executable
                local_dir = GlobalRegistry.get(GlobalRegistry.Keys.LOCAL_DIR)
                assert local_dir == Path("C:/Program Files/CLASSIC")

    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettingsCache.classic_settings")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_yaml_cache")
    def test_initialize_application_source_mode(
        self,
        mock_get_cache: MagicMock,
        mock_yaml: MagicMock,
        mock_classic: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization in source mode (not frozen)."""
        # Mock YAML cache
        mock_cache = MagicMock()
        mock_cache.STATIC_YAML_STORES = []
        mock_get_cache.return_value = mock_cache

        # Mock settings
        mock_classic.side_effect = [False, "Fallout 4"]
        mock_yaml.return_value = False

        # Ensure not frozen
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")

        # Initialize application
        coordinator.initialize_application(is_gui=False)

        # Verify local dir was set from __file__
        local_dir = GlobalRegistry.get(GlobalRegistry.Keys.LOCAL_DIR)
        # Should be parent of SetupCoordinator.py location
        assert local_dir.name == "CLASSIC-Fallout4"

    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettingsCache.classic_settings")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_yaml_cache")
    def test_initialize_application_none_game_setting(
        self,
        mock_get_cache: MagicMock,
        mock_yaml: MagicMock,
        mock_classic: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization when managed game setting is None."""
        # Mock YAML cache
        mock_cache = MagicMock()
        mock_cache.STATIC_YAML_STORES = []
        mock_get_cache.return_value = mock_cache

        # Mock settings with None game
        mock_classic.side_effect = [False, None]  # VR Mode, Managed Game (None)
        mock_yaml.return_value = False

        # Initialize application
        coordinator.initialize_application(is_gui=False)

        # Verify empty string was used for game
        assert GlobalRegistry.get(GlobalRegistry.Keys.GAME) == ""

    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettingsCache.classic_settings")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    @patch.object(GlobalRegistry, "get_yaml_cache")
    def test_initialize_application_yaml_preload(
        self,
        mock_get_cache: MagicMock,
        mock_yaml: MagicMock,
        mock_classic: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test that YAML files are preloaded during initialization."""
        # Mock YAML cache with multiple stores
        mock_cache = MagicMock()
        mock_cache.STATIC_YAML_STORES = ["settings", "game", "main"]
        mock_cache.get_path_for_store.side_effect = [Path("settings.yaml"), Path("game.yaml"), Path("main.yaml")]
        mock_get_cache.return_value = mock_cache

        # Mock settings
        mock_classic.side_effect = [False, "Fallout 4"]
        mock_yaml.return_value = False

        # Initialize application
        coordinator.initialize_application(is_gui=False)

        # Verify all YAML stores were loaded
        assert mock_cache.load_yaml.call_count == 3
        mock_cache.load_yaml.assert_any_call(Path("settings.yaml"))
        mock_cache.load_yaml.assert_any_call(Path("game.yaml"))
        mock_cache.load_yaml.assert_any_call(Path("main.yaml"))

    @patch("ClassicLib.GameIntegrity.GameIntegrityChecker.run_full_check", side_effect=Exception("Check failed"))
    @patch("ClassicLib.SetupCoordinator.xse_check_integrity")
    @patch("ClassicLib.SetupCoordinator.xse_check_hashes")
    @patch("ClassicLib.DocumentsChecker.DocumentsChecker.run_all_checks")
    @patch.object(GlobalRegistry, "get_game", return_value="Fallout4")
    def test_generate_combined_results_exception(
        self,
        mock_get_game: MagicMock,
        mock_docs_checks: MagicMock,
        mock_xse_hashes: MagicMock,
        mock_xse_integrity: MagicMock,
        mock_game_check: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test that exceptions in generate_combined_results are propagated."""
        # Should raise the exception from game check
        with pytest.raises(Exception, match="Check failed"):
            coordinator.generate_combined_results()
