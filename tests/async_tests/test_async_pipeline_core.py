"""
Core tests for the async crash log processing pipeline.

This module contains tests for the main AsyncCrashLogPipeline class
and its initialization, processing, and monitoring functionality.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanLog.AsyncPipeline import AsyncCrashLogPipeline, AsyncPerformanceMonitor

if TYPE_CHECKING:
    from collections import Counter


@pytest.fixture
def sample_crash_log_content() -> str:
    """Sample crash log content for testing."""
    return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]

PROBABLE CALL STACK:
\t[0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> 703355+0x72
\t[1] 0x7FF6EF4C145E Fallout4.exe+073145E -> 825090+0x67E
\tForm ID: 0x12345678
\tForm ID: 0x87654321

MODULES:
\tproblematic_module.dll
\ttest_module.dll

F4SE PLUGINS:
\tf4se_plugin1.dll
\tcrash_plugin.dll

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[02] ProblemPlugin.esp
\t[03] AnotherMod.esp
"""


@pytest.fixture
def crash_log_files(tmp_path: Path, sample_crash_log_content: str) -> list[Path]:
    """Create multiple crash log files for testing."""
    crash_logs_dir: Path = tmp_path / "Crash Logs"
    crash_logs_dir.mkdir(exist_ok=True)

    files: list[Any] = []
    for i in range(3):
        log_file: Path = crash_logs_dir / f"crash-2023-01-0{i + 1}-00-00-00.log"
        log_file.write_text(sample_crash_log_content)
        files.append(log_file)

    return files


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


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncPipeline:
    """Integration tests for the async crash log processing pipeline."""

    async def test_async_pipeline_initialization(self, mock_yamldata: MagicMock) -> None:
        """Test that AsyncCrashLogPipeline initializes correctly."""
        pipeline: AsyncCrashLogPipeline = AsyncCrashLogPipeline(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        )

        assert pipeline.yamldata == mock_yamldata
        assert pipeline.fcx_mode is False
        assert pipeline.show_formid_values is True
        assert pipeline.formid_db_exists is False
        assert isinstance(pipeline.performance_stats, dict)

    @pytest.mark.usefixtures("init_message_handler_fixture")
    async def test_async_pipeline_process_crash_logs(self, crash_log_files: list[Path], mock_yamldata: MagicMock) -> None:
        """Test the full async pipeline processing."""
        pipeline: AsyncCrashLogPipeline = AsyncCrashLogPipeline(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        with (
            patch("ClassicLib.ScanLog.AsyncPipeline.crashlogs_reformat_async") as mock_reformat,
            patch("ClassicLib.ScanLog.AsyncPipeline.load_crash_logs_async") as mock_load,
            patch("ClassicLib.ScanLog.AsyncPipeline.write_reports_batch") as mock_write,
            patch("ClassicLib.ScanLog.OrchestratorCore.OrchestratorCore") as mock_orchestrator_class,
        ):
            # Setup mocks - use AsyncMock for async functions
            mock_reformat.return_value = AsyncMock()
            mock_load.return_value = {log_file.name: ["line1", "line2"] for log_file in crash_log_files}
            mock_write.return_value = AsyncMock()

            # Create mock orchestrator instance
            mock_orchestrator: AsyncMock = AsyncMock()
            mock_orchestrator.process_crash_logs_batch.return_value = [
                (log_file, [f"Report for {log_file.name}"], False, {}) for log_file in crash_log_files
            ]

            # Setup async context manager
            mock_orchestrator_class.return_value.__aenter__.return_value = mock_orchestrator
            mock_orchestrator_class.return_value.__aexit__.return_value = None

            # Run the pipeline
            results, stats = await pipeline.process_crash_logs_async(crashlog_list=crash_log_files, remove_list=("test_remove",))

            # Verify results
            assert len(results) == 3
            assert isinstance(stats, dict)
            assert "total_time" in stats
            assert "reformat_time" in stats
            assert "load_time" in stats
            assert "process_time" in stats
            assert "write_time" in stats
            assert "logs_per_second" in stats

            # Verify pipeline stages were called
            mock_reformat.assert_called_once_with(crash_log_files, ("test_remove",))
            mock_load.assert_called_once_with(crash_log_files)
            mock_write.assert_called_once()

    async def test_async_performance_monitor(self) -> None:
        """Test the AsyncPerformanceMonitor comparison functionality."""
        async_stats: dict[str, float] = {
            "total_time": 5.0,
            "reformat_time": 1.0,
            "load_time": 1.5,
            "process_time": 2.0,
            "write_time": 0.5,
            "logs_per_second": 10.0,
        }
        sync_time: float = 15.0
        log_count = 50

        comparison: dict[str, str | float] = AsyncPerformanceMonitor.compare_performance(async_stats, sync_time, log_count)

        assert isinstance(comparison, dict)
        assert "speedup_factor" in comparison
        assert "improvement_percent" in comparison
        assert "async_total_time" in comparison
        assert "sync_total_time" in comparison
        assert comparison["speedup_factor"] == 3.0  # 15.0 / 5.0
        assert comparison["improvement_percent"] == (10.0 / 15.0) * 100  # percentage improvement
