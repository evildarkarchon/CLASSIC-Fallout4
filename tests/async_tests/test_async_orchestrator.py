"""
Tests for the OrchestratorCore component of the async pipeline.

This module contains tests for the OrchestratorCore class which coordinates
the processing of crash logs using various analyzers.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache

if TYPE_CHECKING:
    from collections import Counter


@pytest.fixture
def mock_yamldata() -> MagicMock:
    """Mock ClassicScanLogsInfo for testing."""
    yamldata: MagicMock = MagicMock()
    yamldata.fallout4_crashlog_scan_exclusions = ["test_exclusion"]
    yamldata.fallout4_crashlog_mods_single = {"test_mod": "Test mod message"}
    yamldata.game_ignore_plugins = ["plugin1.esp", "plugin2.esp"]
    yamldata.game_ignore_records = ["record1", "record2"]
    yamldata.ignore_list = ["ignore1.esp", "ignore2.esp"]
    yamldata.classic_records_list = ["record1", "record2"]
    yamldata.fallout4_crashlog_mods_top = {"top_mod": "Top mod message"}
    yamldata.fallout4_crashlog_mods_groups = {"group_mod": "Group mod message"}
    yamldata.fallout4_crashlog_stack_check = {"test_stack": "Test stack message"}
    yamldata.fallout4_crashlog_error_check = {"test_error": "Test error message"}
    yamldata.formid_analyzer_enabled = True
    yamldata.record_scanner_enabled = True
    yamldata.plugin_analyzer_enabled = True
    return yamldata


@pytest.fixture
def crash_log_files(tmp_path: Path) -> list[Path]:
    """Create multiple crash log files for testing."""
    crash_logs_dir: Path = tmp_path / "Crash Logs"
    crash_logs_dir.mkdir(exist_ok=True)

    sample_content = """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

PROBABLE CALL STACK:
\t[0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> 703355+0x72
\tForm ID: 0x12345678

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
"""

    files: list[Path] = []
    for i in range(3):
        log_file: Path = crash_logs_dir / f"crash-2023-01-0{i + 1}-00-00-00.log"
        log_file.write_text(sample_content)
        files.append(log_file)

    return files


@pytest.mark.integration
@pytest.mark.asyncio
class TestOrchestratorCore:
    """Integration tests for OrchestratorCore."""

    async def test_orchestrator_core_context_manager(self, mock_yamldata: MagicMock) -> None:
        """Test OrchestratorCore as async context manager."""
        crashlogs: MagicMock = MagicMock(spec=ThreadSafeLogCache)

        with patch("ClassicLib.ScanLog.OrchestratorCore.AsyncDatabasePool") as mock_pool_class:
            mock_pool: AsyncMock = AsyncMock()
            mock_pool.initialize = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool_class.return_value = mock_pool

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                crashlogs=crashlogs,
                fcx_mode=False,
                show_formid_values=True,
                formid_db_exists=True,
            ) as orchestrator:
                # Verify orchestrator is initialized
                assert orchestrator is not None
                assert orchestrator._db_pool == mock_pool

                # Verify database pool was initialized
                mock_pool.initialize.assert_called_once()

            # Verify cleanup was called
            mock_pool.close.assert_called_once()

    async def test_orchestrator_core_batch_processing(self, crash_log_files: list[Path], mock_yamldata: MagicMock) -> None:
        """Test batch processing of crash logs."""
        crashlogs: MagicMock = MagicMock(spec=ThreadSafeLogCache)

        with patch("ClassicLib.ScanLog.OrchestratorCore.AsyncDatabasePool") as mock_pool_class:
            mock_pool: AsyncMock = AsyncMock()
            mock_pool_class.return_value = mock_pool

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                crashlogs=crashlogs,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                # Mock the core method
                with patch.object(orchestrator, "process_crash_log", return_value=(Path("test.log"), ["report"], False, {})):
                    results: list[tuple[Path, list[str], bool, Counter[str]]] = await orchestrator.process_crash_logs_batch(crash_log_files)

                    assert len(results) == 3
                    for result in results:
                        assert len(result) == 4  # (Path, list, bool, Counter)
                        assert isinstance(result[0], Path)
                        assert isinstance(result[1], list)
                        assert isinstance(result[2], bool)

    async def test_orchestrator_initialization_without_db(self, mock_yamldata: MagicMock) -> None:
        """Test orchestrator initialization without FormID database."""
        crashlogs: MagicMock = MagicMock(spec=ThreadSafeLogCache)

        with patch("ClassicLib.ScanLog.OrchestratorCore.AsyncDatabasePool") as mock_pool_class:
            async with OrchestratorCore(
                yamldata=mock_yamldata,
                crashlogs=crashlogs,
                fcx_mode=True,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                # Verify orchestrator is initialized
                assert orchestrator is not None
                assert orchestrator.fcx_mode is True
                assert orchestrator.show_formid_values is False
                assert orchestrator.formid_db_exists is False

                # Database pool should not be initialized when formid_db_exists is False
                mock_pool_class.assert_not_called()

    async def test_orchestrator_with_multiple_analyzers(self, mock_yamldata: MagicMock) -> None:
        """Test orchestrator with multiple analyzer components enabled."""
        crashlogs: MagicMock = MagicMock(spec=ThreadSafeLogCache)

        # Ensure all analyzers are enabled in mock data
        mock_yamldata.formid_analyzer_enabled = True
        mock_yamldata.record_scanner_enabled = True
        mock_yamldata.plugin_analyzer_enabled = True

        with patch("ClassicLib.ScanLog.OrchestratorCore.AsyncDatabasePool") as mock_pool_class:
            mock_pool: AsyncMock = AsyncMock()
            mock_pool.initialize = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool_class.return_value = mock_pool

            async with OrchestratorCore(
                yamldata=mock_yamldata,
                crashlogs=crashlogs,
                fcx_mode=False,
                show_formid_values=True,
                formid_db_exists=True,
            ) as orchestrator:
                # Verify all analyzer flags are set correctly
                assert orchestrator._formid_analyzer is not None
                assert orchestrator._record_scanner is not None
                assert orchestrator._plugin_analyzer is not None
