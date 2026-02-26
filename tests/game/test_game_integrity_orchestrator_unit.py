"""Unit tests for ClassicLib.scanning.game.orchestrator module.

This module tests the async-first game integrity checking orchestration
functionality including concurrent checks, exception group handling,
and combined result generation.

Following TDD methodology - tests written to define expected behavior.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.scanning.game.models.fcx_issue import ConfigIssue
from ClassicLib.scanning.game.orchestrator import (
    GameIntegrityOrchestratorCore,
    generate_game_combined_result,
    generate_game_combined_result_async,
    generate_mods_combined_result,
    generate_mods_combined_result_async,
    get_game_integrity_orchestrator_core,
    write_combined_results,
    write_combined_results_async,
)

pytestmark = pytest.mark.unit


# ==============================================================================
# GameIntegrityOrchestratorCore Initialization Tests
# ==============================================================================


class TestGameIntegrityOrchestratorCoreInit:
    """Tests for the GameIntegrityOrchestratorCore initialization."""

    @patch("ClassicLib.scanning.game.orchestrator.get_file_io")
    def test_init_creates_file_io_instance(self, mock_get_file_io: MagicMock) -> None:
        """__init__ should create file_io instance using factory."""
        mock_file_io = MagicMock()
        mock_get_file_io.return_value = mock_file_io

        core = GameIntegrityOrchestratorCore()

        mock_get_file_io.assert_called_once()
        assert core.file_io == mock_file_io


# ==============================================================================
# generate_game_combined_result_async Tests
# ==============================================================================


class TestGenerateGameCombinedResultAsync:
    """Tests for the generate_game_combined_result_async method."""

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.get_file_io")
    @patch("ClassicLib.scanning.game.orchestrator.yaml_settings")
    async def test_returns_empty_when_game_path_missing(self, mock_yaml: MagicMock, mock_get_file_io: MagicMock) -> None:
        """generate_game_combined_result_async should return empty when game_path is None."""
        mock_yaml.return_value = None  # Neither docs nor game path configured

        core = GameIntegrityOrchestratorCore()
        result, issues = await core.generate_game_combined_result_async()

        assert result == ""
        assert issues == []

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.get_file_io")
    @patch("ClassicLib.scanning.game.orchestrator.yaml_settings")
    async def test_returns_empty_when_docs_path_missing(self, mock_yaml: MagicMock, mock_get_file_io: MagicMock, tmp_path: Path) -> None:
        """generate_game_combined_result_async should return empty when docs_path is None."""

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Root_Folder_Docs" in key_path:
                return None
            if "Root_Folder_Game" in key_path:
                return tmp_path
            return None

        mock_yaml.side_effect = yaml_side_effect

        core = GameIntegrityOrchestratorCore()
        result, issues = await core.generate_game_combined_result_async()

        assert result == ""
        assert issues == []

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.scan_mod_inis.detect_all_ini_issues_async")
    @patch("ClassicLib.scanning.game.config.ConfigFileCache")
    @patch("ClassicLib.scanning.game.core.ScanGameCore")
    @patch("ClassicLib.scanning.game.orchestrator.scan_mod_inis_async")
    @patch("ClassicLib.scanning.game.orchestrator.scan_wryecheck")
    @patch("ClassicLib.scanning.game.orchestrator.check_crashgen_settings")
    @patch("ClassicLib.scanning.game.orchestrator.check_xse_plugins")
    @patch("ClassicLib.scanning.game.orchestrator.get_file_io")
    @patch("ClassicLib.scanning.game.orchestrator.yaml_settings")
    async def test_runs_all_checks_concurrently(
        self,
        mock_yaml: MagicMock,
        mock_get_file_io: MagicMock,
        mock_xse: MagicMock,
        mock_crashgen: MagicMock,
        mock_wrye: MagicMock,
        mock_mod_inis: AsyncMock,
        mock_scan_game_core: MagicMock,
        mock_config_cache: MagicMock,
        mock_detect_issues: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """generate_game_combined_result_async should run all checks concurrently."""
        # Setup paths
        docs_path = tmp_path / "docs"
        game_path = tmp_path / "game"
        docs_path.mkdir()
        game_path.mkdir()

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Root_Folder_Docs" in key_path:
                return docs_path
            if "Root_Folder_Game" in key_path:
                return game_path
            return None

        mock_yaml.side_effect = yaml_side_effect

        # Setup mock returns
        mock_xse.return_value = "XSE Check Result\n"
        mock_crashgen.return_value = ("Crashgen Check Result\n", [])
        mock_wrye.return_value = "Wrye Check Result\n"
        mock_mod_inis.return_value = "Mod INIs Result\n"
        mock_detect_issues.return_value = []

        # Mock ScanGameCore.check_log_errors
        mock_core_instance = MagicMock()
        mock_core_instance.check_log_errors = AsyncMock(return_value="Log Errors\n")
        mock_scan_game_core.return_value = mock_core_instance

        core = GameIntegrityOrchestratorCore()
        result, issues = await core.generate_game_combined_result_async()

        # Verify all checks were called
        mock_xse.assert_called_once()
        mock_crashgen.assert_called_once()
        mock_wrye.assert_called_once()
        mock_mod_inis.assert_called_once()

        # Result should contain all check outputs
        assert "XSE Check Result" in result
        assert "Crashgen Check Result" in result
        assert "Wrye Check Result" in result
        assert "Mod INIs Result" in result

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.scan_mod_inis.detect_all_ini_issues_async")
    @patch("ClassicLib.scanning.game.config.ConfigFileCache")
    @patch("ClassicLib.scanning.game.core.ScanGameCore")
    @patch("ClassicLib.scanning.game.orchestrator.scan_mod_inis_async")
    @patch("ClassicLib.scanning.game.orchestrator.scan_wryecheck")
    @patch("ClassicLib.scanning.game.orchestrator.check_crashgen_settings")
    @patch("ClassicLib.scanning.game.orchestrator.check_xse_plugins")
    @patch("ClassicLib.scanning.game.orchestrator.get_file_io")
    @patch("ClassicLib.scanning.game.orchestrator.yaml_settings")
    async def test_returns_combined_config_issues(
        self,
        mock_yaml: MagicMock,
        mock_get_file_io: MagicMock,
        mock_xse: MagicMock,
        mock_crashgen: MagicMock,
        mock_wrye: MagicMock,
        mock_mod_inis: AsyncMock,
        mock_scan_game_core: MagicMock,
        mock_config_cache: MagicMock,
        mock_detect_issues: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """generate_game_combined_result_async should return combined config issues."""
        docs_path = tmp_path / "docs"
        game_path = tmp_path / "game"
        docs_path.mkdir()
        game_path.mkdir()

        def yaml_side_effect(type_arg, _store, key_path, *args):
            if "Root_Folder_Docs" in key_path:
                return docs_path
            if "Root_Folder_Game" in key_path:
                return game_path
            return None

        mock_yaml.side_effect = yaml_side_effect

        # Create issues from different sources
        crashgen_issue = ConfigIssue(
            file_path=tmp_path / "config.toml",
            section="Patches",
            setting="Achievements",
            current_value="true",
            recommended_value="false",
            description="Crashgen issue",
            severity="warning",
        )
        ini_issue = ConfigIssue(
            file_path=tmp_path / "fallout4.ini",
            section="General",
            setting="bLoadVehicles",
            current_value="0",
            recommended_value="1",
            description="INI issue",
            severity="error",
        )

        mock_xse.return_value = ""
        mock_crashgen.return_value = ("", [crashgen_issue])
        mock_wrye.return_value = ""
        mock_mod_inis.return_value = ""
        mock_detect_issues.return_value = [ini_issue]

        # Mock ScanGameCore.check_log_errors
        mock_core_instance = MagicMock()
        mock_core_instance.check_log_errors = AsyncMock(return_value="")
        mock_scan_game_core.return_value = mock_core_instance

        core = GameIntegrityOrchestratorCore()
        result, issues = await core.generate_game_combined_result_async()

        # Should have both issues combined
        assert len(issues) == 2
        assert crashgen_issue in issues
        assert ini_issue in issues

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.get_file_io")
    @patch("ClassicLib.scanning.game.orchestrator.yaml_settings")
    async def test_returns_tuple_type(self, mock_yaml: MagicMock, mock_get_file_io: MagicMock) -> None:
        """generate_game_combined_result_async should return tuple[str, list[ConfigIssue]]."""
        mock_yaml.return_value = None

        core = GameIntegrityOrchestratorCore()
        result = await core.generate_game_combined_result_async()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], list)


# ==============================================================================
# generate_mods_combined_result_async Tests
# ==============================================================================


class TestGenerateModsCombinedResultAsync:
    """Tests for the generate_mods_combined_result_async method."""

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.core.ScanGameCore")
    @patch("ClassicLib.scanning.game.orchestrator.yaml_settings")
    async def test_returns_warning_when_mod_path_missing(self, mock_yaml: MagicMock, mock_scan_game_core: MagicMock) -> None:
        """generate_mods_combined_result_async should return warning when mod path is None."""
        mock_core_instance = MagicMock()
        mock_core_instance.get_scan_settings.return_value = (None, None, None)  # No mod path
        mock_scan_game_core.return_value = mock_core_instance

        mock_yaml.return_value = "Mod path not configured warning"

        result = await GameIntegrityOrchestratorCore.generate_mods_combined_result_async()

        assert result == "Mod path not configured warning"

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.core.ScanGameCore")
    async def test_runs_both_scans_concurrently(self, mock_scan_game_core: MagicMock, tmp_path: Path) -> None:
        """generate_mods_combined_result_async should run unpacked and archived scans concurrently."""
        mock_core_instance = MagicMock()
        mock_core_instance.get_scan_settings.return_value = (None, None, tmp_path)
        mock_core_instance.scan_mods_unpacked = AsyncMock(return_value="Unpacked mods result\n")
        mock_core_instance.scan_mods_archived = AsyncMock(return_value="Archived mods result\n")
        mock_scan_game_core.return_value = mock_core_instance

        result = await GameIntegrityOrchestratorCore.generate_mods_combined_result_async()

        mock_core_instance.scan_mods_unpacked.assert_called_once()
        mock_core_instance.scan_mods_archived.assert_called_once()
        assert "Unpacked mods result" in result
        assert "Archived mods result" in result

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.core.ScanGameCore")
    async def test_handles_unpacked_scan_exception(self, mock_scan_game_core: MagicMock, tmp_path: Path) -> None:
        """generate_mods_combined_result_async should handle exceptions from unpacked scan."""
        mock_core_instance = MagicMock()
        mock_core_instance.get_scan_settings.return_value = (None, None, tmp_path)
        mock_core_instance.scan_mods_unpacked = AsyncMock(side_effect=RuntimeError("Unpacked scan failed"))
        mock_core_instance.scan_mods_archived = AsyncMock(return_value="Archived result")
        mock_scan_game_core.return_value = mock_core_instance

        result = await GameIntegrityOrchestratorCore.generate_mods_combined_result_async()

        # Should still include archived result despite unpacked failure
        assert "Archived result" in result

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.core.ScanGameCore")
    async def test_handles_archived_scan_exception(self, mock_scan_game_core: MagicMock, tmp_path: Path) -> None:
        """generate_mods_combined_result_async should handle exceptions from archived scan."""
        mock_core_instance = MagicMock()
        mock_core_instance.get_scan_settings.return_value = (None, None, tmp_path)
        mock_core_instance.scan_mods_unpacked = AsyncMock(return_value="Unpacked result")
        mock_core_instance.scan_mods_archived = AsyncMock(side_effect=RuntimeError("Archived scan failed"))
        mock_scan_game_core.return_value = mock_core_instance

        result = await GameIntegrityOrchestratorCore.generate_mods_combined_result_async()

        # Should still include unpacked result despite archived failure
        assert "Unpacked result" in result

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.core.ScanGameCore")
    async def test_returns_empty_when_both_scans_fail(self, mock_scan_game_core: MagicMock, tmp_path: Path) -> None:
        """generate_mods_combined_result_async should return empty when both scans fail."""
        mock_core_instance = MagicMock()
        mock_core_instance.get_scan_settings.return_value = (None, None, tmp_path)
        mock_core_instance.scan_mods_unpacked = AsyncMock(side_effect=RuntimeError("Unpacked failed"))
        mock_core_instance.scan_mods_archived = AsyncMock(side_effect=RuntimeError("Archived failed"))
        mock_scan_game_core.return_value = mock_core_instance

        result = await GameIntegrityOrchestratorCore.generate_mods_combined_result_async()

        assert result == ""


# ==============================================================================
# write_combined_results_async Tests
# ==============================================================================


class TestWriteCombinedResultsAsync:
    """Tests for the write_combined_results_async method."""

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.get_file_io")
    async def test_writes_combined_results_to_file(self, mock_get_file_io: MagicMock) -> None:
        """write_combined_results_async should write combined game and mods results."""
        mock_file_io = MagicMock()
        mock_file_io.write_file = AsyncMock()
        mock_get_file_io.return_value = mock_file_io

        core = GameIntegrityOrchestratorCore()

        with (
            patch.object(core, "generate_game_combined_result_async", new_callable=AsyncMock) as mock_game,
            patch.object(core, "generate_mods_combined_result_async", new_callable=AsyncMock) as mock_mods,
        ):
            mock_game.return_value = ("Game results\n", [])
            mock_mods.return_value = "Mods results\n"

            await core.write_combined_results_async()

        # Verify file was written with combined content
        mock_file_io.write_file.assert_called_once()
        call_args = mock_file_io.write_file.call_args
        assert call_args[0][0] == Path("CLASSIC GFS Report.md")
        assert "Game results" in call_args[0][1]
        assert "Mods results" in call_args[0][1]

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.get_file_io")
    async def test_runs_game_and_mods_concurrently(self, mock_get_file_io: MagicMock) -> None:
        """write_combined_results_async should run game and mods generation concurrently."""
        mock_file_io = MagicMock()
        mock_file_io.write_file = AsyncMock()
        mock_get_file_io.return_value = mock_file_io

        core = GameIntegrityOrchestratorCore()

        with (
            patch.object(core, "generate_game_combined_result_async", new_callable=AsyncMock) as mock_game,
            patch.object(core, "generate_mods_combined_result_async", new_callable=AsyncMock) as mock_mods,
        ):
            mock_game.return_value = ("", [])
            mock_mods.return_value = ""

            await core.write_combined_results_async()

        # Both should be called
        mock_game.assert_called_once()
        mock_mods.assert_called_once()


# ==============================================================================
# Singleton and Module-level Function Tests
# ==============================================================================


class TestSingletonAndModuleFunctions:
    """Tests for the singleton accessor and module-level functions."""

    @patch("ClassicLib.scanning.game.orchestrator._game_integrity_orchestrator_core", None)
    @patch("ClassicLib.scanning.game.orchestrator.get_file_io")
    def test_get_game_integrity_orchestrator_core_creates_singleton(self, mock_get_file_io: MagicMock) -> None:
        """get_game_integrity_orchestrator_core should create singleton instance."""
        core1 = get_game_integrity_orchestrator_core()
        core2 = get_game_integrity_orchestrator_core()

        assert core1 is core2
        assert isinstance(core1, GameIntegrityOrchestratorCore)

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.get_game_integrity_orchestrator_core")
    async def test_module_generate_game_combined_result_async(self, mock_get_core: MagicMock) -> None:
        """Module-level generate_game_combined_result_async should delegate to core."""
        mock_core = MagicMock()
        mock_core.generate_game_combined_result_async = AsyncMock(return_value=("Result", []))
        mock_get_core.return_value = mock_core

        result, issues = await generate_game_combined_result_async()

        mock_core.generate_game_combined_result_async.assert_called_once()
        assert result == "Result"
        assert issues == []

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.get_game_integrity_orchestrator_core")
    async def test_module_generate_mods_combined_result_async(self, mock_get_core: MagicMock) -> None:
        """Module-level generate_mods_combined_result_async should delegate to core."""
        mock_core = MagicMock()
        mock_core.generate_mods_combined_result_async = AsyncMock(return_value="Mods Result")
        mock_get_core.return_value = mock_core

        result = await generate_mods_combined_result_async()

        mock_core.generate_mods_combined_result_async.assert_called_once()
        assert result == "Mods Result"

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.get_game_integrity_orchestrator_core")
    async def test_module_write_combined_results_async(self, mock_get_core: MagicMock) -> None:
        """Module-level write_combined_results_async should delegate to core."""
        mock_core = MagicMock()
        mock_core.write_combined_results_async = AsyncMock()
        mock_get_core.return_value = mock_core

        await write_combined_results_async()

        mock_core.write_combined_results_async.assert_called_once()


# ==============================================================================
# Sync Adapter Tests
# ==============================================================================


class TestSyncAdapters:
    """Tests for the sync adapter functions."""

    @patch("ClassicLib.scanning.game.orchestrator.AsyncBridge")
    def test_generate_game_combined_result_uses_asyncbridge(self, mock_async_bridge_class: MagicMock) -> None:
        """generate_game_combined_result should use AsyncBridge for sync execution."""
        mock_bridge = MagicMock()

        def close_and_return(coro):
            """Close coroutine to prevent 'never awaited' warning and return value."""
            coro.close()
            return ("Result", [])

        mock_bridge.run_async.side_effect = close_and_return
        mock_async_bridge_class.get_instance.return_value = mock_bridge

        result, issues = generate_game_combined_result()

        mock_async_bridge_class.get_instance.assert_called_once()
        mock_bridge.run_async.assert_called_once()
        assert result == "Result"
        assert issues == []

    @patch("ClassicLib.scanning.game.orchestrator.AsyncBridge")
    def test_generate_mods_combined_result_uses_asyncbridge(self, mock_async_bridge_class: MagicMock) -> None:
        """generate_mods_combined_result should use AsyncBridge for sync execution."""
        mock_bridge = MagicMock()

        def close_and_return(coro):
            """Close coroutine to prevent 'never awaited' warning and return value."""
            coro.close()
            return "Mods Result"

        mock_bridge.run_async.side_effect = close_and_return
        mock_async_bridge_class.get_instance.return_value = mock_bridge

        result = generate_mods_combined_result()

        mock_async_bridge_class.get_instance.assert_called_once()
        mock_bridge.run_async.assert_called_once()
        assert result == "Mods Result"

    @patch("ClassicLib.scanning.game.orchestrator.AsyncBridge")
    def test_write_combined_results_uses_asyncbridge(self, mock_async_bridge_class: MagicMock) -> None:
        """write_combined_results should use AsyncBridge for sync execution."""
        mock_bridge = MagicMock()

        def close_and_return(coro):
            """Close coroutine to prevent 'never awaited' warning."""
            coro.close()
            return None

        mock_bridge.run_async.side_effect = close_and_return
        mock_async_bridge_class.get_instance.return_value = mock_bridge

        write_combined_results()

        mock_async_bridge_class.get_instance.assert_called_once()
        mock_bridge.run_async.assert_called_once()


# ==============================================================================
# Private Helper Method Tests
# ==============================================================================


class TestPrivateHelperMethods:
    """Tests for the private helper methods."""

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.check_xse_plugins")
    async def test_run_xse_plugins_check_async(self, mock_check_xse: MagicMock) -> None:
        """_run_xse_plugins_check_async should run check_xse_plugins in executor."""
        mock_check_xse.return_value = "XSE result"

        result = await GameIntegrityOrchestratorCore._run_xse_plugins_check_async()

        mock_check_xse.assert_called_once()
        assert result == "XSE result"

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.check_crashgen_settings")
    async def test_run_crashgen_check_async(self, mock_crashgen: MagicMock, tmp_path: Path) -> None:
        """_run_crashgen_check_async should run check_crashgen_settings in executor."""
        issue = ConfigIssue(
            file_path=tmp_path / "config.toml",
            section="Test",
            setting="Key",
            current_value="a",
            recommended_value="b",
            description="Test",
            severity="warning",
        )
        mock_crashgen.return_value = ("Crashgen result", [issue])

        message, issues = await GameIntegrityOrchestratorCore._run_crashgen_check_async()

        mock_crashgen.assert_called_once()
        assert message == "Crashgen result"
        assert issues == [issue]

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.scan_wryecheck")
    async def test_run_wryecheck_async(self, mock_wrye: MagicMock) -> None:
        """_run_wryecheck_async should run scan_wryecheck in executor."""
        mock_wrye.return_value = "Wrye result"

        result = await GameIntegrityOrchestratorCore._run_wryecheck_async()

        mock_wrye.assert_called_once()
        assert result == "Wrye result"

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.scan_mod_inis_async")
    async def test_run_mod_inis_scan_async(self, mock_mod_inis: AsyncMock) -> None:
        """_run_mod_inis_scan_async should call scan_mod_inis_async directly."""
        mock_mod_inis.return_value = "Mod INIs result"

        result = await GameIntegrityOrchestratorCore._run_mod_inis_scan_async()

        mock_mod_inis.assert_called_once()
        assert result == "Mod INIs result"

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.core.ScanGameCore")
    async def test_check_log_errors_async(self, mock_scan_game_core: MagicMock, tmp_path: Path) -> None:
        """_check_log_errors_async should delegate to ScanGameCore.check_log_errors."""
        mock_core_instance = MagicMock()
        mock_core_instance.check_log_errors = AsyncMock(return_value="Log errors")
        mock_scan_game_core.return_value = mock_core_instance

        result = await GameIntegrityOrchestratorCore._check_log_errors_async(tmp_path)

        mock_core_instance.check_log_errors.assert_called_once_with(tmp_path)
        assert result == "Log errors"


# ==============================================================================
# Error Handling Tests
# ==============================================================================


class TestErrorHandling:
    """Tests for error handling in the orchestrator."""

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.get_file_io")
    @patch("ClassicLib.scanning.game.orchestrator.yaml_settings")
    async def test_generate_game_returns_empty_on_os_error(self, mock_yaml: MagicMock, mock_get_file_io: MagicMock) -> None:
        """generate_game_combined_result_async should return empty on OSError."""
        mock_yaml.side_effect = OSError("File system error")

        core = GameIntegrityOrchestratorCore()
        result, issues = await core.generate_game_combined_result_async()

        assert result == ""
        assert issues == []

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.orchestrator.get_file_io")
    @patch("ClassicLib.scanning.game.orchestrator.yaml_settings")
    async def test_generate_game_returns_empty_on_runtime_error(self, mock_yaml: MagicMock, mock_get_file_io: MagicMock) -> None:
        """generate_game_combined_result_async should return empty on RuntimeError."""
        mock_yaml.side_effect = RuntimeError("Runtime error")

        core = GameIntegrityOrchestratorCore()
        result, issues = await core.generate_game_combined_result_async()

        assert result == ""
        assert issues == []

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.core.ScanGameCore")
    async def test_generate_mods_returns_empty_on_os_error(self, mock_scan_game_core: MagicMock) -> None:
        """generate_mods_combined_result_async should return empty on OSError."""
        mock_scan_game_core.side_effect = OSError("File system error")

        result = await GameIntegrityOrchestratorCore.generate_mods_combined_result_async()

        assert result == ""

    @pytest.mark.asyncio
    @patch("ClassicLib.scanning.game.core.ScanGameCore")
    async def test_generate_mods_returns_empty_on_runtime_error(self, mock_scan_game_core: MagicMock) -> None:
        """generate_mods_combined_result_async should return empty on RuntimeError."""
        mock_scan_game_core.side_effect = RuntimeError("Runtime error")

        result = await GameIntegrityOrchestratorCore.generate_mods_combined_result_async()

        assert result == ""
