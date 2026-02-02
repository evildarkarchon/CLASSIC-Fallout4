"""Unit tests for SetupCoordinator class.

This module provides comprehensive tests for the SetupCoordinator class which
handles application initialization, file generation, path detection, and
integrity checking workflows.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.setup import SetupCoordinator

# ============================================================================
# Initialization Tests
# ============================================================================


class TestSetupCoordinatorInit:
    """Tests for SetupCoordinator initialization."""

    @pytest.mark.unit
    def test_init_creates_file_generator(self) -> None:
        """SetupCoordinator.__init__ should create a FileGenerator instance."""
        coordinator = SetupCoordinator()

        assert coordinator.file_generator is not None
        assert hasattr(coordinator.file_generator, "generate_all_files")

    @pytest.mark.unit
    def test_init_creates_integrity_checker(self) -> None:
        """SetupCoordinator.__init__ should create a GameIntegrityChecker instance."""
        coordinator = SetupCoordinator()

        assert coordinator.integrity_checker is not None
        assert hasattr(coordinator.integrity_checker, "run_full_check")

    @pytest.mark.unit
    def test_init_creates_backup_manager(self) -> None:
        """SetupCoordinator.__init__ should create a BackupManager instance."""
        coordinator = SetupCoordinator()

        assert coordinator.backup_manager is not None
        assert hasattr(coordinator.backup_manager, "run_backup")

    @pytest.mark.unit
    def test_init_creates_docs_checker(self) -> None:
        """SetupCoordinator.__init__ should create a DocumentsChecker instance."""
        coordinator = SetupCoordinator()

        assert coordinator.docs_checker is not None
        assert hasattr(coordinator.docs_checker, "run_all_checks")

    @pytest.mark.unit
    def test_init_creates_path_validator(self) -> None:
        """SetupCoordinator.__init__ should create a PathValidator instance."""
        coordinator = SetupCoordinator()

        assert coordinator.path_validator is not None
        assert hasattr(coordinator.path_validator, "validate_all_settings_paths")


# ============================================================================
# _get_config_suffix Tests
# ============================================================================


class TestGetConfigSuffix:
    """Tests for the deprecated _get_config_suffix method."""

    @pytest.mark.unit
    def test_get_config_suffix_delegates_to_global_registry(self) -> None:
        """_get_config_suffix should delegate to GlobalRegistry.get_config_suffix()."""
        with patch.object(GlobalRegistry, "get_config_suffix", return_value="VR") as mock_get:
            result = SetupCoordinator._get_config_suffix()

            assert result == "VR"
            mock_get.assert_called_once()

    @pytest.mark.unit
    def test_get_config_suffix_returns_empty_for_non_vr(self) -> None:
        """_get_config_suffix should return empty string for non-VR mode."""
        with patch.object(GlobalRegistry, "get_config_suffix", return_value=""):
            result = SetupCoordinator._get_config_suffix()

            assert result == ""


# ============================================================================
# generate_combined_results Tests
# ============================================================================


class TestGenerateCombinedResults:
    """Tests for generate_combined_results method."""

    @pytest.mark.unit
    def test_generate_combined_results_runs_all_checks(self) -> None:
        """generate_combined_results should run all integrity checks."""
        coordinator = SetupCoordinator()

        with (
            patch.object(GlobalRegistry, "get_game", return_value="Fallout4"),
            patch.object(coordinator.integrity_checker, "run_full_check", return_value="[INTEGRITY]"),
            patch("ClassicLib.support.setup.xse_check_integrity", return_value="[XSE]"),
            patch("ClassicLib.support.setup.xse_check_hashes", return_value="[HASHES]"),
            patch.object(coordinator.docs_checker, "run_all_checks", return_value=["[DOCS1]", "[DOCS2]"]),
        ):
            result = coordinator.generate_combined_results()

            assert "[INTEGRITY]" in result
            assert "[XSE]" in result
            assert "[HASHES]" in result
            assert "[DOCS1]" in result
            assert "[DOCS2]" in result

    @pytest.mark.unit
    def test_generate_combined_results_returns_concatenated_string(self) -> None:
        """generate_combined_results should return all results joined together."""
        coordinator = SetupCoordinator()

        with (
            patch.object(GlobalRegistry, "get_game", return_value="Fallout4"),
            patch.object(coordinator.integrity_checker, "run_full_check", return_value="A"),
            patch("ClassicLib.support.setup.xse_check_integrity", return_value="B"),
            patch("ClassicLib.support.setup.xse_check_hashes", return_value="C"),
            patch.object(coordinator.docs_checker, "run_all_checks", return_value=["D", "E"]),
        ):
            result = coordinator.generate_combined_results()

            assert result == "ABCDE"

    @pytest.mark.unit
    def test_generate_combined_results_with_empty_checks(self) -> None:
        """generate_combined_results should handle empty check results."""
        coordinator = SetupCoordinator()

        with (
            patch.object(GlobalRegistry, "get_game", return_value="Fallout4"),
            patch.object(coordinator.integrity_checker, "run_full_check", return_value=""),
            patch("ClassicLib.support.setup.xse_check_integrity", return_value=""),
            patch("ClassicLib.support.setup.xse_check_hashes", return_value=""),
            patch.object(coordinator.docs_checker, "run_all_checks", return_value=[]),
        ):
            result = coordinator.generate_combined_results()

            assert result == ""


# ============================================================================
# run_initial_setup Tests
# ============================================================================


class TestRunInitialSetup:
    """Tests for run_initial_setup method."""

    @pytest.mark.unit
    def test_run_initial_setup_configures_logging(self) -> None:
        """run_initial_setup should configure logging."""
        coordinator = SetupCoordinator()

        # Create a mock for yaml_cache with the batch_get_settings_async method.
        # Patch on the setup module namespace since yaml_cache is imported at top level.
        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=("v8.0.0", "Fallout 4", None, False))

        with (
            patch("ClassicLib.support.setup.configure_logging") as mock_config_logging,
            patch.object(coordinator.file_generator, "generate_all_files"),
            patch.object(GlobalRegistry, "get_config_suffix", return_value=""),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch("ClassicLib.support.setup.msg_info"),
            patch("ClassicLib.support.setup.msg_success"),
            patch("ClassicLib.support.setup.docs_path_find"),
            patch("ClassicLib.support.setup.docs_generate_paths"),
            patch("ClassicLib.support.setup.game_path_find"),
            patch("ClassicLib.support.setup.game_generate_paths"),
            patch("ClassicLib.support.setup.logger"),
        ):
            coordinator.run_initial_setup()

            mock_config_logging.assert_called_once()

    @pytest.mark.unit
    def test_run_initial_setup_generates_files(self) -> None:
        """run_initial_setup should generate required configuration files."""
        coordinator = SetupCoordinator()

        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=("v8.0.0", "Fallout 4", None, False))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch.object(coordinator.file_generator, "generate_all_files") as mock_gen_files,
            patch.object(GlobalRegistry, "get_config_suffix", return_value=""),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch("ClassicLib.support.setup.msg_info"),
            patch("ClassicLib.support.setup.msg_success"),
            patch("ClassicLib.support.setup.docs_path_find"),
            patch("ClassicLib.support.setup.docs_generate_paths"),
            patch("ClassicLib.support.setup.game_path_find"),
            patch("ClassicLib.support.setup.game_generate_paths"),
            patch("ClassicLib.support.setup.logger"),
        ):
            coordinator.run_initial_setup()

            mock_gen_files.assert_called_once()

    @pytest.mark.unit
    def test_run_initial_setup_detects_paths_when_not_configured(self) -> None:
        """run_initial_setup should detect paths when game_path is not configured."""
        coordinator = SetupCoordinator()

        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=("v8.0.0", "Fallout 4", None, False))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch.object(coordinator.file_generator, "generate_all_files"),
            patch.object(GlobalRegistry, "get_config_suffix", return_value=""),
            patch.object(GlobalRegistry, "is_gui_mode", return_value=False),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch("ClassicLib.support.setup.msg_info"),
            patch("ClassicLib.support.setup.msg_success"),
            patch("ClassicLib.support.setup.docs_path_find") as mock_docs_find,
            patch("ClassicLib.support.setup.docs_generate_paths") as mock_docs_gen,
            patch("ClassicLib.support.setup.game_path_find") as mock_game_find,
            patch("ClassicLib.support.setup.game_generate_paths") as mock_game_gen,
            patch("ClassicLib.support.setup.logger"),
        ):
            # game_path is None - should trigger path detection
            coordinator.run_initial_setup()

            mock_docs_find.assert_called_once()
            mock_docs_gen.assert_called_once()
            mock_game_find.assert_called_once()
            mock_game_gen.assert_called_once()

    @pytest.mark.unit
    def test_run_initial_setup_runs_backup_when_paths_configured(self) -> None:
        """run_initial_setup should run backup when game_path is already configured."""
        coordinator = SetupCoordinator()

        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=("v8.0.0", "Fallout 4", "C:/Games/Fallout4", False))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch.object(coordinator.file_generator, "generate_all_files"),
            patch.object(GlobalRegistry, "get_config_suffix", return_value=""),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch("ClassicLib.support.setup.msg_info"),
            patch("ClassicLib.support.setup.msg_success"),
            patch.object(coordinator.backup_manager, "run_backup") as mock_backup,
            patch("ClassicLib.support.setup.logger"),
        ):
            # game_path is set - should run backup
            coordinator.run_initial_setup()

            mock_backup.assert_called_once()

    @pytest.mark.unit
    def test_run_initial_setup_raises_type_error_for_invalid_version(self) -> None:
        """run_initial_setup should raise TypeError when version is not a string."""
        coordinator = SetupCoordinator()

        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=(None, "Fallout 4", None, False))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch.object(coordinator.file_generator, "generate_all_files"),
            patch.object(GlobalRegistry, "get_config_suffix", return_value=""),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch("ClassicLib.support.setup.logger"),
        ):
            # classic_ver is not a string - TypeError raised before msg_info is called
            with pytest.raises(TypeError, match="Classic version and game name must be strings"):
                coordinator.run_initial_setup()

    @pytest.mark.unit
    def test_run_initial_setup_raises_type_error_for_invalid_game_name(self) -> None:
        """run_initial_setup should raise TypeError when game_name is not a string."""
        coordinator = SetupCoordinator()

        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=("v8.0.0", None, None, False))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch.object(coordinator.file_generator, "generate_all_files"),
            patch.object(GlobalRegistry, "get_config_suffix", return_value=""),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch("ClassicLib.support.setup.logger"),
        ):
            # game_name is not a string - TypeError raised before msg_info is called
            with pytest.raises(TypeError, match="Classic version and game name must be strings"):
                coordinator.run_initial_setup()

    @pytest.mark.unit
    def test_run_initial_setup_enables_debug_logging_when_setting_true(self) -> None:
        """run_initial_setup should enable debug logging when debug_messages is True."""
        coordinator = SetupCoordinator()

        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=("v8.0.0", "Fallout 4", "C:/Games", True))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch("ClassicLib.support.setup.enable_debug_logging") as mock_enable_debug,
            patch.object(coordinator.file_generator, "generate_all_files"),
            patch.object(GlobalRegistry, "get_config_suffix", return_value=""),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch("ClassicLib.support.setup.msg_info"),
            patch("ClassicLib.support.setup.msg_success"),
            patch.object(coordinator.backup_manager, "run_backup"),
            patch("ClassicLib.support.setup.logger"),
        ):
            # debug_messages is True
            coordinator.run_initial_setup()

            mock_enable_debug.assert_called_once()


# ============================================================================
# initialize_application Tests
# ============================================================================


class TestInitializeApplication:
    """Tests for initialize_application method."""

    @pytest.mark.unit
    def test_initialize_application_configures_logging(self, tmp_path: Path) -> None:
        """initialize_application should configure logging."""
        coordinator = SetupCoordinator()
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        settings_file.write_text("test: value")

        # Mock yaml_cache at the setup module namespace where it is imported.
        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=("auto", False, "Fallout4", False, False))

        with (
            patch("ClassicLib.support.setup.configure_logging") as mock_config_logging,
            patch("ClassicLib.support.setup.init_message_handler"),
            patch("ClassicLib.support.setup.ResourceLoader"),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch.object(coordinator.path_validator, "validate_all_settings_paths"),
            patch.object(SetupCoordinator, "_ensure_paths_configured"),
            patch.object(SetupCoordinator, "_log_rust_acceleration_status"),
            patch("ClassicLib.support.setup.Path", return_value=settings_file),
        ):
            coordinator.initialize_application(is_gui=False)

            mock_config_logging.assert_called_once()

    @pytest.mark.unit
    def test_initialize_application_initializes_message_handler(self, tmp_path: Path) -> None:
        """initialize_application should initialize the message handler."""
        coordinator = SetupCoordinator()
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        settings_file.write_text("test: value")

        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=("auto", False, "Fallout4", False, False))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch("ClassicLib.support.setup.init_message_handler") as mock_init_handler,
            patch("ClassicLib.support.setup.ResourceLoader"),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch.object(coordinator.path_validator, "validate_all_settings_paths"),
            patch.object(SetupCoordinator, "_ensure_paths_configured"),
            patch.object(SetupCoordinator, "_log_rust_acceleration_status"),
            patch("ClassicLib.support.setup.Path", return_value=settings_file),
        ):
            coordinator.initialize_application(is_gui=True, parent="mock_parent")

            mock_init_handler.assert_called_once_with(parent="mock_parent", is_gui_mode=True)

    @pytest.mark.unit
    def test_initialize_application_registers_gui_mode(self, tmp_path: Path) -> None:
        """initialize_application should register IS_GUI_MODE in GlobalRegistry."""
        coordinator = SetupCoordinator()
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        settings_file.write_text("test: value")

        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=("auto", False, "Fallout4", False, False))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch("ClassicLib.support.setup.init_message_handler"),
            patch("ClassicLib.support.setup.ResourceLoader"),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch.object(coordinator.path_validator, "validate_all_settings_paths"),
            patch.object(SetupCoordinator, "_ensure_paths_configured"),
            patch.object(SetupCoordinator, "_log_rust_acceleration_status"),
            patch("ClassicLib.support.setup.Path", return_value=settings_file),
        ):
            coordinator.initialize_application(is_gui=True)

            assert GlobalRegistry.is_registered(GlobalRegistry.Keys.IS_GUI_MODE)
            assert GlobalRegistry.get(GlobalRegistry.Keys.IS_GUI_MODE) is True

    @pytest.mark.unit
    def test_initialize_application_registers_game_version_vr(self, tmp_path: Path) -> None:
        """initialize_application should register VR game version from settings."""
        coordinator = SetupCoordinator()
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        settings_file.write_text("test: value")

        # batch_get_settings_async returns: (game_version, legacy_vr_mode, managed_game, is_prerelease, debug)
        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=("VR", False, "Fallout4", False, False))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch("ClassicLib.support.setup.init_message_handler"),
            patch("ClassicLib.support.setup.ResourceLoader"),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch.object(coordinator.path_validator, "validate_all_settings_paths"),
            patch.object(SetupCoordinator, "_ensure_paths_configured"),
            patch.object(SetupCoordinator, "_log_rust_acceleration_status"),
            patch("ClassicLib.support.setup.Path", return_value=settings_file),
        ):
            # Game Version = "VR"
            coordinator.initialize_application(is_gui=False)

            assert GlobalRegistry.get(GlobalRegistry.Keys.GAME_VERSION) == "VR"
            assert GlobalRegistry.get(GlobalRegistry.Keys.VR) == "VR"

    @pytest.mark.unit
    def test_initialize_application_migrates_legacy_vr_mode(self, tmp_path: Path) -> None:
        """initialize_application should migrate legacy VR Mode to Game Version."""
        coordinator = SetupCoordinator()
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        settings_file.write_text("test: value")

        # game_version is None (not set), legacy_vr_mode is True -> should migrate to VR
        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=(None, True, "Fallout4", False, False))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch("ClassicLib.support.setup.init_message_handler"),
            patch("ClassicLib.support.setup.ResourceLoader"),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch.object(coordinator.path_validator, "validate_all_settings_paths"),
            patch.object(SetupCoordinator, "_ensure_paths_configured"),
            patch.object(SetupCoordinator, "_log_rust_acceleration_status"),
            patch("ClassicLib.support.setup.Path", return_value=settings_file),
            patch("ClassicLib.support.setup.logger"),
        ):
            # game_version is None/auto, but legacy_vr_mode is True
            coordinator.initialize_application(is_gui=False)

            assert GlobalRegistry.get(GlobalRegistry.Keys.GAME_VERSION) == "VR"
            assert GlobalRegistry.get(GlobalRegistry.Keys.VR) == "VR"

    @pytest.mark.unit
    def test_initialize_application_defaults_game_version_to_auto(self, tmp_path: Path) -> None:
        """initialize_application should default game version to 'auto' when not set."""
        coordinator = SetupCoordinator()
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        settings_file.write_text("test: value")

        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=(None, False, "Fallout4", False, False))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch("ClassicLib.support.setup.init_message_handler"),
            patch("ClassicLib.support.setup.ResourceLoader"),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch.object(coordinator.path_validator, "validate_all_settings_paths"),
            patch.object(SetupCoordinator, "_ensure_paths_configured"),
            patch.object(SetupCoordinator, "_log_rust_acceleration_status"),
            patch("ClassicLib.support.setup.Path", return_value=settings_file),
        ):
            # game_version is None, legacy_vr_mode is False
            coordinator.initialize_application(is_gui=False)

            assert GlobalRegistry.get(GlobalRegistry.Keys.GAME_VERSION) == "auto"

    @pytest.mark.unit
    def test_initialize_application_validates_paths(self, tmp_path: Path) -> None:
        """initialize_application should validate all settings paths."""
        coordinator = SetupCoordinator()
        settings_file = tmp_path / "CLASSIC Settings.yaml"
        settings_file.write_text("test: value")

        mock_yaml_cache = MagicMock()
        mock_yaml_cache.batch_get_settings_async = AsyncMock(return_value=("auto", False, "Fallout4", False, False))

        with (
            patch("ClassicLib.support.setup.configure_logging"),
            patch("ClassicLib.support.setup.init_message_handler"),
            patch("ClassicLib.support.setup.ResourceLoader"),
            patch("ClassicLib.support.setup.yaml_cache", mock_yaml_cache),
            patch.object(coordinator.path_validator, "validate_all_settings_paths") as mock_validate,
            patch.object(SetupCoordinator, "_ensure_paths_configured"),
            patch.object(SetupCoordinator, "_log_rust_acceleration_status"),
            patch("ClassicLib.support.setup.Path", return_value=settings_file),
        ):
            coordinator.initialize_application(is_gui=False)

            mock_validate.assert_called_once()


# ============================================================================
# _ensure_paths_configured Tests
# ============================================================================


class TestEnsurePathsConfigured:
    """Tests for _ensure_paths_configured static method."""

    @pytest.mark.unit
    def test_ensure_paths_configured_detects_missing_game_path(self) -> None:
        """_ensure_paths_configured should detect game path when missing."""
        # Patch yaml_settings on the setup module namespace where it is imported
        mock_yaml_settings = MagicMock(return_value=None)

        with (
            patch.object(GlobalRegistry, "get_config_suffix", return_value=""),
            patch("ClassicLib.support.setup.yaml_settings", mock_yaml_settings),
            patch("ClassicLib.support.setup.docs_path_find") as mock_docs_find,
            patch("ClassicLib.support.setup.docs_generate_paths"),
            patch("ClassicLib.support.setup.game_path_find") as mock_game_find,
            patch("ClassicLib.support.setup.game_generate_paths"),
            patch("ClassicLib.support.setup.logger"),
        ):
            # Both paths are missing
            SetupCoordinator._ensure_paths_configured(is_gui=False)

            mock_docs_find.assert_called_once_with(False)
            mock_game_find.assert_called_once()

    @pytest.mark.unit
    def test_ensure_paths_configured_skips_detection_when_paths_exist(self) -> None:
        """_ensure_paths_configured should skip detection when paths are configured."""
        mock_yaml_settings = MagicMock(side_effect=["C:/Games/Fallout4", "C:/Documents/Fallout4"])

        with (
            patch.object(GlobalRegistry, "get_config_suffix", return_value=""),
            patch("ClassicLib.support.setup.yaml_settings", mock_yaml_settings),
            patch("ClassicLib.support.setup.docs_path_find") as mock_docs_find,
            patch("ClassicLib.support.setup.game_path_find") as mock_game_find,
            patch("ClassicLib.support.setup.logger"),
        ):
            # Both paths are configured
            SetupCoordinator._ensure_paths_configured(is_gui=True)

            mock_docs_find.assert_not_called()
            mock_game_find.assert_not_called()

    @pytest.mark.unit
    def test_ensure_paths_configured_uses_vr_suffix(self) -> None:
        """_ensure_paths_configured should use VR suffix for VR mode."""
        mock_yaml_settings = MagicMock(return_value=None)

        with (
            patch.object(GlobalRegistry, "get_config_suffix", return_value="VR"),
            patch("ClassicLib.support.setup.yaml_settings", mock_yaml_settings),
            patch("ClassicLib.support.setup.docs_path_find"),
            patch("ClassicLib.support.setup.docs_generate_paths"),
            patch("ClassicLib.support.setup.game_path_find"),
            patch("ClassicLib.support.setup.game_generate_paths"),
            patch("ClassicLib.support.setup.logger"),
        ):
            SetupCoordinator._ensure_paths_configured(is_gui=False)

            # Verify yaml_settings was called with VR suffix
            calls = mock_yaml_settings.call_args_list
            assert any("GameVR_Info.Root_Folder_Game" in str(call) for call in calls)
            assert any("GameVR_Info.Root_Folder_Docs" in str(call) for call in calls)


# ============================================================================
# Rust Acceleration Status Logging Tests
# ============================================================================


class TestLogRustAccelerationStatus:
    """Tests for _log_rust_acceleration_status method."""

    @pytest.mark.unit
    def test_log_rust_acceleration_status_active(self) -> None:
        """_log_rust_acceleration_status should log active components."""
        coordinator = SetupCoordinator()

        # Production code uses lazy import from factory.
        # Patch at the SOURCE module (factory), not the setup module.
        mock_yaml_settings_fn = MagicMock(return_value=True)

        # detect_component returns (True, module) for available components
        mock_detect = MagicMock(return_value=(True, MagicMock()))

        with (
            patch("ClassicLib.support.setup.yaml_settings", mock_yaml_settings_fn),
            patch.object(GlobalRegistry, "is_gui_mode", return_value=False),
            patch("ClassicLib.integration.factory._is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.detect_component", mock_detect),
            patch.object(SetupCoordinator, "_log_active_acceleration") as mock_log_active,
            patch("ClassicLib.support.setup.logger"),
        ):
            coordinator._log_rust_acceleration_status()

            mock_log_active.assert_called_once()

    @pytest.mark.unit
    def test_log_rust_acceleration_status_disabled(self) -> None:
        """_log_rust_acceleration_status should log when Rust is disabled."""
        coordinator = SetupCoordinator()

        mock_yaml_settings_fn = MagicMock(return_value=True)

        with (
            patch("ClassicLib.support.setup.yaml_settings", mock_yaml_settings_fn),
            patch.object(GlobalRegistry, "is_gui_mode", return_value=False),
            patch("ClassicLib.integration.factory._is_rust_disabled", return_value=True),
            patch.object(SetupCoordinator, "_log_disabled_status") as mock_log_disabled,
            patch("ClassicLib.support.setup.logger"),
        ):
            coordinator._log_rust_acceleration_status()

            mock_log_disabled.assert_called_once_with(True, False)

    @pytest.mark.unit
    def test_log_rust_acceleration_status_no_acceleration(self) -> None:
        """_log_rust_acceleration_status should log when no acceleration available."""
        coordinator = SetupCoordinator()

        mock_yaml_settings_fn = MagicMock(return_value=True)

        # detect_component returns (False, None) for all components
        mock_detect = MagicMock(return_value=(False, None))

        with (
            patch("ClassicLib.support.setup.yaml_settings", mock_yaml_settings_fn),
            patch.object(GlobalRegistry, "is_gui_mode", return_value=False),
            patch("ClassicLib.integration.factory._is_rust_disabled", return_value=False),
            patch("ClassicLib.integration.factory.detect_component", mock_detect),
            patch.object(SetupCoordinator, "_log_no_acceleration") as mock_log_none,
            patch("ClassicLib.support.setup.logger"),
        ):
            coordinator._log_rust_acceleration_status()

            mock_log_none.assert_called_once_with(True, False)

    @pytest.mark.unit
    def test_log_rust_acceleration_status_handles_import_error(self) -> None:
        """_log_rust_acceleration_status should handle ImportError gracefully."""
        coordinator = SetupCoordinator()

        mock_yaml_settings_fn = MagicMock(return_value=True)

        with (
            patch("ClassicLib.support.setup.yaml_settings", mock_yaml_settings_fn),
            patch.object(GlobalRegistry, "is_gui_mode", return_value=False),
            patch(
                "ClassicLib.integration.factory._is_rust_disabled",
                side_effect=ImportError("Module not found"),
            ),
            patch.object(SetupCoordinator, "_log_import_error") as mock_log_import,
        ):
            coordinator._log_rust_acceleration_status()

            mock_log_import.assert_called_once_with(True, False)

    @pytest.mark.unit
    def test_log_rust_acceleration_status_handles_generic_exception(self) -> None:
        """_log_rust_acceleration_status should handle unexpected exceptions."""
        coordinator = SetupCoordinator()

        mock_yaml_settings_fn = MagicMock(return_value=True)

        with (
            patch("ClassicLib.support.setup.yaml_settings", mock_yaml_settings_fn),
            patch.object(GlobalRegistry, "is_gui_mode", return_value=False),
            patch(
                "ClassicLib.integration.factory._is_rust_disabled",
                side_effect=RuntimeError("Unexpected error"),
            ),
            patch.object(SetupCoordinator, "_log_status_check_error") as mock_log_error,
        ):
            coordinator._log_rust_acceleration_status()

            mock_log_error.assert_called_once()


# ============================================================================
# Status Message Display Tests
# ============================================================================


class TestDisplayStatusMessage:
    """Tests for _display_status_message static method."""

    @pytest.mark.unit
    def test_display_status_message_info_cli(self) -> None:
        """_display_status_message should display info messages in CLI mode."""
        with (
            patch("builtins.print") as mock_print,
            patch("ClassicLib.support.setup.msg_info") as mock_msg_info,
        ):
            SetupCoordinator._display_status_message("Test message", "INFO", is_gui=False)

            mock_print.assert_called_once_with("Test message")
            mock_msg_info.assert_called_once_with("Test message")

    @pytest.mark.unit
    def test_display_status_message_warning_cli(self) -> None:
        """_display_status_message should display warning messages in CLI mode."""
        with (
            patch("builtins.print") as mock_print,
            patch("ClassicLib.msg_warning") as mock_msg_warning,
        ):
            SetupCoordinator._display_status_message("Warning message", "WARNING", is_gui=False)

            mock_print.assert_called_once_with("Warning message")
            mock_msg_warning.assert_called_once_with("Warning message")

    @pytest.mark.unit
    def test_display_status_message_error_cli(self) -> None:
        """_display_status_message should display error messages in CLI mode."""
        with (
            patch("builtins.print") as mock_print,
            patch("ClassicLib.msg_error") as mock_msg_error,
        ):
            SetupCoordinator._display_status_message("Error message", "ERROR", is_gui=False)

            mock_print.assert_called_once_with("Error message")
            mock_msg_error.assert_called_once_with("Error message")

    @pytest.mark.unit
    def test_display_status_message_gui_skips_print(self) -> None:
        """_display_status_message should skip print in GUI mode."""
        with (
            patch("builtins.print") as mock_print,
            patch("ClassicLib.support.setup.msg_info") as mock_msg_info,
        ):
            SetupCoordinator._display_status_message("Test message", "INFO", is_gui=True)

            mock_print.assert_not_called()
            mock_msg_info.assert_called_once_with("Test message")


# ============================================================================
# Rust Status Helper Methods Tests
# ============================================================================


class TestLogStatusHelpers:
    """Tests for individual log status helper methods."""

    @pytest.mark.unit
    def test_log_disabled_status(self) -> None:
        """_log_disabled_status should log disabled Rust message."""
        with (
            patch.object(SetupCoordinator, "_display_status_message") as mock_display,
            patch("ClassicLib.support.setup.logger") as mock_logger,
        ):
            SetupCoordinator._log_disabled_status(debug_enabled=True, is_gui=False)

            mock_display.assert_called_once()
            assert "disabled" in mock_display.call_args[0][0].lower()
            mock_logger.warning.assert_called_once()

    @pytest.mark.unit
    def test_log_disabled_status_skips_display_when_debug_disabled(self) -> None:
        """_log_disabled_status should skip display when debug is disabled."""
        with (
            patch.object(SetupCoordinator, "_display_status_message") as mock_display,
            patch("ClassicLib.support.setup.logger"),
        ):
            SetupCoordinator._log_disabled_status(debug_enabled=False, is_gui=False)

            mock_display.assert_not_called()

    @pytest.mark.unit
    def test_log_active_acceleration(self) -> None:
        """_log_active_acceleration should log active component status."""
        mock_status: dict[str, Any] = {
            "active_count": 5,
            "total_count": 8,
            "percentage": 62.5,
            "acceleration_level": "PARTIAL",
            "performance_gains": {"YAML": "15x faster"},
        }

        with (
            patch.object(SetupCoordinator, "_display_status_message") as mock_display,
            patch("ClassicLib.support.setup.logger") as mock_logger,
        ):
            SetupCoordinator._log_active_acceleration(mock_status, debug_enabled=True, is_gui=False)

            mock_display.assert_called_once()
            assert "5/8" in mock_display.call_args[0][0]
            mock_logger.info.assert_called()

    @pytest.mark.unit
    def test_log_no_acceleration(self) -> None:
        """_log_no_acceleration should log fallback message."""
        with (
            patch.object(SetupCoordinator, "_display_status_message") as mock_display,
            patch("ClassicLib.support.setup.logger") as mock_logger,
        ):
            SetupCoordinator._log_no_acceleration(debug_enabled=True, is_gui=False)

            mock_display.assert_called_once()
            assert "fallback" in mock_display.call_args[0][0].lower()
            mock_logger.warning.assert_called()

    @pytest.mark.unit
    def test_log_import_error(self) -> None:
        """_log_import_error should log import error message."""
        with (
            patch.object(SetupCoordinator, "_display_status_message") as mock_display,
            patch("ClassicLib.support.setup.logger") as mock_logger,
        ):
            SetupCoordinator._log_import_error(debug_enabled=True, is_gui=False)

            mock_display.assert_called_once()
            mock_logger.debug.assert_called_once()

    @pytest.mark.unit
    def test_log_status_check_error(self) -> None:
        """_log_status_check_error should log error checking status."""
        test_error = RuntimeError("Test error")

        with (
            patch("builtins.print") as mock_print,
            patch("ClassicLib.support.setup.logger") as mock_logger,
        ):
            SetupCoordinator._log_status_check_error(test_error, debug_enabled=True, is_gui=False)

            mock_logger.debug.assert_called_once()
            mock_print.assert_called_once()
            assert "Test error" in mock_print.call_args[0][0]

    @pytest.mark.unit
    def test_log_status_check_error_skips_print_in_gui(self) -> None:
        """_log_status_check_error should skip print in GUI mode."""
        test_error = RuntimeError("Test error")

        with (
            patch("builtins.print") as mock_print,
            patch("ClassicLib.support.setup.logger"),
        ):
            SetupCoordinator._log_status_check_error(test_error, debug_enabled=True, is_gui=True)

            mock_print.assert_not_called()
