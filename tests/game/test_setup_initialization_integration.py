"""Tests for SetupCoordinator initialization and application setup."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.SetupCoordinator import SetupCoordinator

pytestmark = [pytest.mark.unit]


class TestSetupInitialization:
    """Test suite for SetupCoordinator initialization."""

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

    def test_initialization(self, coordinator: SetupCoordinator) -> None:
        """Test SetupCoordinator initialization."""
        # Verify all components are initialized
        assert coordinator.file_generator is not None
        assert coordinator.integrity_checker is not None
        assert coordinator.backup_manager is not None
        assert coordinator.docs_checker is not None
        assert coordinator.path_validator is not None

    @patch.object(SetupCoordinator, "_log_rust_acceleration_status")
    @patch.object(SetupCoordinator, "_ensure_paths_configured")
    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.batch_get_settings_async", new_callable=AsyncMock)
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.prefetch_all_settings")
    def test_initialize_application_gui_mode(
        self,
        mock_prefetch: MagicMock,
        mock_batch_get: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        mock_ensure_paths: MagicMock,
        mock_log_rust: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization in GUI mode."""
        # Mock batch_get_settings to return values for GUI mode
        # Order: Game Version, VR Mode (legacy), Managed Game, is_prerelease, Debug Messages
        mock_batch_get.return_value = [
            "auto",  # Game Version (new setting)
            False,  # VR Mode (legacy, deprecated)
            "Fallout 4",  # Managed Game
            False,  # is_prerelease False
            False,  # Debug Messages
        ]

        # Initialize application
        coordinator.initialize_application(is_gui=True)

        # Verify message handler was initialized for GUI
        mock_init_handler.assert_called_once_with(parent=None, is_gui_mode=True)

        # Verify registry was set up
        assert GlobalRegistry.get(GlobalRegistry.Keys.IS_GUI_MODE) is True

        # Verify paths were validated
        mock_validate_paths.assert_called_once()

    @patch.object(SetupCoordinator, "_log_rust_acceleration_status")
    @patch.object(SetupCoordinator, "_ensure_paths_configured")
    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.batch_get_settings_async", new_callable=AsyncMock)
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.prefetch_all_settings")
    def test_initialize_application_gui_mode_with_parent(
        self,
        mock_prefetch: MagicMock,
        mock_batch_get: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        mock_ensure_paths: MagicMock,
        mock_log_rust: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization in GUI mode with parent widget."""
        # Mock batch_get_settings to return values
        # Order: Game Version, VR Mode (legacy), Managed Game, is_prerelease, Debug Messages
        mock_batch_get.return_value = [
            "auto",  # Game Version (new setting)
            False,  # VR Mode (legacy, deprecated)
            "Fallout 4",  # Managed Game
            False,  # is_prerelease False
            False,  # Debug Messages
        ]

        # Create a mock parent widget
        mock_parent = MagicMock()

        # Initialize application with parent
        coordinator.initialize_application(is_gui=True, parent=mock_parent)

        # Verify message handler was initialized with parent
        mock_init_handler.assert_called_once_with(parent=mock_parent, is_gui_mode=True)

        # Verify registry was set up
        assert GlobalRegistry.get(GlobalRegistry.Keys.IS_GUI_MODE) is True

    @patch.object(SetupCoordinator, "_log_rust_acceleration_status")
    @patch.object(SetupCoordinator, "_ensure_paths_configured")
    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.batch_get_settings_async", new_callable=AsyncMock)
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.prefetch_all_settings")
    def test_initialize_application_cli_mode(
        self,
        mock_prefetch: MagicMock,
        mock_batch_get: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        mock_ensure_paths: MagicMock,
        mock_log_rust: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization in CLI mode."""
        # Mock batch_get_settings to return values for CLI mode
        # Order: Game Version, VR Mode (legacy), Managed Game, is_prerelease, Debug Messages
        mock_batch_get.return_value = [
            "VR",  # Game Version (new setting - VR mode)
            True,  # VR Mode (legacy, deprecated - used for migration)
            "Skyrim SE",  # Managed Game
            True,  # is_prerelease
            False,  # Debug Messages
        ]

        # Initialize application
        coordinator.initialize_application(is_gui=False)

        # Verify message handler was initialized for CLI
        mock_init_handler.assert_called_once_with(parent=None, is_gui_mode=False)

        # Verify registry was set up
        assert GlobalRegistry.get(GlobalRegistry.Keys.IS_GUI_MODE) is False
        # Note: GlobalRegistry stores VR as "VR" when True, empty string when False
        assert GlobalRegistry.get(GlobalRegistry.Keys.VR) == "VR"
        # Note: Game name has spaces removed
        game = GlobalRegistry.get(GlobalRegistry.Keys.GAME)
        assert game == "SkyrimSE"  # Spaces are removed

    @patch.object(SetupCoordinator, "_log_rust_acceleration_status")
    @patch.object(SetupCoordinator, "_ensure_paths_configured")
    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.batch_get_settings_async", new_callable=AsyncMock)
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.prefetch_all_settings")
    def test_initialize_application_frozen_executable(
        self,
        mock_prefetch: MagicMock,
        mock_batch_get: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        mock_ensure_paths: MagicMock,
        mock_log_rust: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization for frozen executable."""
        # Mock batch_get_settings to return values
        # Order: Game Version, VR Mode (legacy), Managed Game, is_prerelease, Debug Messages
        mock_batch_get.return_value = [
            "auto",  # Game Version (new setting)
            False,  # VR Mode (legacy, deprecated)
            "Fallout 4",  # Managed Game
            False,  # is_prerelease False
            False,  # Debug Messages
        ]

        # Mock frozen state
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "executable", "C:/Program Files/CLASSIC/CLASSIC.exe"):
                # Initialize application
                coordinator.initialize_application(is_gui=False)

                # Verify local dir was set from executable
                local_dir = GlobalRegistry.get(GlobalRegistry.Keys.LOCAL_DIR)
                assert local_dir == Path("C:/Program Files/CLASSIC")

    @patch.object(SetupCoordinator, "_log_rust_acceleration_status")
    @patch.object(SetupCoordinator, "_ensure_paths_configured")
    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.batch_get_settings_async", new_callable=AsyncMock)
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.prefetch_all_settings")
    def test_initialize_application_source_mode(
        self,
        mock_prefetch: MagicMock,
        mock_batch_get: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        mock_ensure_paths: MagicMock,
        mock_log_rust: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization in source mode (not frozen)."""
        # Mock batch_get_settings to return values
        # Order: Game Version, VR Mode (legacy), Managed Game, is_prerelease, Debug Messages
        mock_batch_get.return_value = [
            "auto",  # Game Version (new setting)
            False,  # VR Mode (legacy, deprecated)
            "Fallout 4",  # Managed Game
            False,  # is_prerelease False
            False,  # Debug Messages
        ]

        # Ensure not frozen
        if hasattr(sys, "frozen"):
            delattr(sys, "frozen")

        # Initialize application
        coordinator.initialize_application(is_gui=False)

        # Verify local dir was set from __file__
        local_dir = GlobalRegistry.get(GlobalRegistry.Keys.LOCAL_DIR)
        # Should be parent of SetupCoordinator.py location
        assert local_dir.name == "ClassicLib" or local_dir.name == "CLASSIC-Fallout4"

    @patch.object(SetupCoordinator, "_log_rust_acceleration_status")
    @patch.object(SetupCoordinator, "_ensure_paths_configured")
    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.batch_get_settings_async", new_callable=AsyncMock)
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.prefetch_all_settings")
    def test_initialize_application_none_game_setting(
        self,
        mock_prefetch: MagicMock,
        mock_batch_get: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        mock_ensure_paths: MagicMock,
        mock_log_rust: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test application initialization when managed game setting is None."""
        # Mock batch_get_settings with None game
        # Order: Game Version, VR Mode (legacy), Managed Game, is_prerelease, Debug Messages
        mock_batch_get.return_value = [
            "auto",  # Game Version (new setting)
            False,  # VR Mode (legacy, deprecated)
            None,  # Managed Game (None)
            False,  # is_prerelease False
            False,  # Debug Messages
        ]

        # Initialize application
        coordinator.initialize_application(is_gui=False)

        # Verify empty string or default was used for game
        game = GlobalRegistry.get(GlobalRegistry.Keys.GAME)
        # When None is passed, it might be stored as empty string or kept as previous value
        assert game in ["", "Fallout4", None]  # Accept possible values

    @patch.object(SetupCoordinator, "_log_rust_acceleration_status")
    @patch.object(SetupCoordinator, "_ensure_paths_configured")
    @patch("ClassicLib.PathValidator.PathValidator.validate_all_settings_paths")
    @patch("ClassicLib.SetupCoordinator.init_message_handler")
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.batch_get_settings_async", new_callable=AsyncMock)
    @patch("ClassicLib.YamlSettings.YamlSettingsCache.prefetch_all_settings")
    def test_initialize_application_yaml_preload(
        self,
        mock_prefetch: MagicMock,
        mock_batch_get: MagicMock,
        mock_init_handler: MagicMock,
        mock_validate_paths: MagicMock,
        mock_ensure_paths: MagicMock,
        mock_log_rust: MagicMock,
        coordinator: SetupCoordinator,
    ) -> None:
        """Test that YAML files are NOT preloaded during initialization (performance optimization)."""
        # Mock batch_get_settings to return values
        # Order: Game Version, VR Mode (legacy), Managed Game, is_prerelease, Debug Messages
        mock_batch_get.return_value = [
            "auto",  # Game Version (new setting)
            False,  # VR Mode (legacy, deprecated)
            "Fallout 4",  # Managed Game
            False,  # not prerelease
            False,  # Debug Messages
        ]

        # Initialize application
        coordinator.initialize_application(is_gui=False)

        # Verify prefetch_all_settings was NOT called (lazy loading preferred)
        mock_prefetch.assert_not_called()

        # Verify batch_get_settings was called with correct requests
        mock_batch_get.assert_called_once()

        # Verify the requests passed to batch_get_settings
        call_args = mock_batch_get.call_args[0][0]
        assert len(call_args) == 5  # Five settings requested
        assert any("Game Version" in str(req) for req in call_args)
        assert any("VR Mode" in str(req) for req in call_args)
        assert any("Managed Game" in str(req) for req in call_args)
        assert any("is_prerelease" in str(req) for req in call_args)
        assert any("Debug Messages" in str(req) for req in call_args)
