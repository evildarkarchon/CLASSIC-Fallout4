"""
Integration tests for the async crash log processing pipeline.

This module contains tests for the async components that provide concurrent
processing of crash logs with performance improvements.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanLog.AsyncPipeline import AsyncCrashLogPipeline, AsyncPerformanceMonitor
from ClassicLib.ScanLog.AsyncScanOrchestrator import AsyncScanOrchestrator
from ClassicLib.ScanLog.AsyncFormIDAnalyzer import AsyncFormIDAnalyzer
from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool, load_crash_logs_async
from ClassicLib.ScanLog.AsyncFileIO import (
    crashlogs_reformat_with_async,
    load_crash_logs_async_optimized,
    write_reports_batch,
)
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache


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
    crash_logs_dir = tmp_path / "Crash Logs"
    crash_logs_dir.mkdir(exist_ok=True)

    files = []
    for i in range(3):
        log_file = crash_logs_dir / f"crash-2023-01-0{i + 1}-00-00-00.log"
        log_file.write_text(sample_crash_log_content)
        files.append(log_file)

    return files


@pytest.fixture
def mock_yamldata() -> MagicMock:
    """Mock ClassicScanLogsInfo for testing."""
    yamldata = MagicMock(spec=ClassicScanLogsInfo)
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
    # Add any other common attributes that might be needed
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
        pipeline = AsyncCrashLogPipeline(
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

    async def test_async_pipeline_process_crash_logs(
        self, crash_log_files: list[Path], mock_yamldata: MagicMock, init_message_handler_fixture: Any
    ) -> None:
        """Test the full async pipeline processing."""
        pipeline = AsyncCrashLogPipeline(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        with (
            patch("ClassicLib.ScanLog.AsyncPipeline.crashlogs_reformat_async") as mock_reformat,
            patch("ClassicLib.ScanLog.AsyncPipeline.load_crash_logs_async") as mock_load,
            patch("ClassicLib.ScanLog.AsyncPipeline.write_reports_batch") as mock_write,
            patch("ClassicLib.ScanLog.AsyncScanOrchestrator.AsyncScanOrchestrator") as mock_orchestrator_class,
        ):
            # Setup mocks
            mock_reformat.return_value = None
            mock_load.return_value = {log_file.name: ["line1", "line2"] for log_file in crash_log_files}
            mock_write.return_value = None

            # Create mock orchestrator instance
            mock_orchestrator = AsyncMock()
            mock_orchestrator.process_crash_logs_batch_async.return_value = [
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
        async_stats = {
            "total_time": 5.0,
            "reformat_time": 1.0,
            "load_time": 1.5,
            "process_time": 2.0,
            "write_time": 0.5,
            "logs_per_second": 10.0,
        }
        sync_time = 15.0
        log_count = 50

        comparison = AsyncPerformanceMonitor.compare_performance(async_stats, sync_time, log_count)

        assert isinstance(comparison, dict)
        assert "speedup_factor" in comparison
        assert "improvement_percent" in comparison
        assert "async_total_time" in comparison
        assert "sync_total_time" in comparison
        assert comparison["speedup_factor"] == 3.0  # 15.0 / 5.0
        assert comparison["improvement_percent"] == (10.0 / 15.0) * 100  # percentage improvement


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncScanOrchestrator:
    """Integration tests for AsyncScanOrchestrator."""

    async def test_async_scan_orchestrator_context_manager(self, crash_log_files: list[Path], mock_yamldata: MagicMock) -> None:
        """Test AsyncScanOrchestrator as async context manager."""
        crashlogs = MagicMock(spec=ThreadSafeLogCache)

        with patch("ClassicLib.ScanLog.AsyncScanOrchestrator.AsyncDatabasePool") as mock_pool_class:
            mock_pool = AsyncMock()
            mock_pool.initialize = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool_class.return_value = mock_pool

            async with AsyncScanOrchestrator(
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

    async def test_async_scan_orchestrator_batch_processing(self, crash_log_files: list[Path], mock_yamldata: MagicMock) -> None:
        """Test batch processing of crash logs."""
        crashlogs = MagicMock(spec=ThreadSafeLogCache)

        with patch("ClassicLib.ScanLog.AsyncUtil.AsyncDatabasePool") as mock_pool_class:
            mock_pool = AsyncMock()
            mock_pool_class.return_value = mock_pool

            async with AsyncScanOrchestrator(
                yamldata=mock_yamldata,
                crashlogs=crashlogs,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            ) as orchestrator:
                # Mock the parent class method
                with patch.object(orchestrator, "process_crash_log", return_value=(Path("test.log"), ["report"], False, {})):
                    results = await orchestrator.process_crash_logs_batch_async(crash_log_files)

                    assert len(results) == 3
                    for result in results:
                        assert len(result) == 4  # (Path, list, bool, Counter)
                        assert isinstance(result[0], Path)
                        assert isinstance(result[1], list)
                        assert isinstance(result[2], bool)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncFormIDAnalyzer:
    """Integration tests for AsyncFormIDAnalyzer."""

    async def test_async_formid_analyzer_initialization(self, mock_yamldata: MagicMock) -> None:
        """Test AsyncFormIDAnalyzer initialization."""
        mock_pool = AsyncMock(spec=AsyncDatabasePool)

        analyzer = AsyncFormIDAnalyzer(
            yamldata=mock_yamldata,
            show_formid_values=True,
            formid_db_exists=True,
            db_pool=mock_pool,
        )

        assert analyzer.yamldata == mock_yamldata
        assert analyzer.show_formid_values is True
        assert analyzer.formid_db_exists is True
        assert analyzer.db_pool == mock_pool

    async def test_formid_extraction(self, mock_yamldata: MagicMock) -> None:
        """Test FormID extraction from call stack."""
        mock_pool = AsyncMock(spec=AsyncDatabasePool)
        analyzer = AsyncFormIDAnalyzer(mock_yamldata, True, True, mock_pool)

        callstack = [
            "Form ID: 0x12345678",
            "Form ID: 0x87654321",
            "Form ID: 0xFF000001",  # Should be skipped (FF prefix)
            "Regular line without FormID",
        ]

        formids = analyzer.extract_formids(callstack)

        assert len(formids) == 2
        assert "Form ID: 12345678" in formids
        assert "Form ID: 87654321" in formids
        assert "Form ID: FF000001" not in formids

    async def test_async_formid_matching(self, mock_yamldata: MagicMock) -> None:
        """Test async FormID matching with database lookups."""
        mock_pool = AsyncMock(spec=AsyncDatabasePool)
        mock_pool.get_entry.return_value = "Test Entry"

        analyzer = AsyncFormIDAnalyzer(mock_yamldata, True, True, mock_pool)

        formids_matches = ["Form ID: 12345678", "Form ID: 87654321"]
        crashlog_plugins = {"TestPlugin.esp": "12", "AnotherPlugin.esp": "87"}
        autoscan_report: list[str] = []

        await analyzer.formid_match_async(formids_matches, crashlog_plugins, autoscan_report)

        # Verify database queries were made
        assert mock_pool.get_entry.call_count == 2

        # Verify report was populated
        assert len(autoscan_report) == 2
        assert "TestPlugin.esp" in autoscan_report[0]
        assert "AnotherPlugin.esp" in autoscan_report[1]


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncFileIO:
    """Integration tests for async file I/O operations."""

    async def test_load_crash_logs_async_optimized(self, crash_log_files: list[Path]) -> None:
        """Test optimized async crash log loading."""
        result = await load_crash_logs_async_optimized(crash_log_files)

        assert isinstance(result, dict)
        assert len(result) == 3

        for log_file in crash_log_files:
            assert log_file.name in result
            assert isinstance(result[log_file.name], bytes)

    async def test_write_reports_batch(self, crash_log_files: list[Path]) -> None:
        """Test batch writing of reports."""
        reports = [(log_file, [f"Report for {log_file.name}\n"], False) for log_file in crash_log_files]

        await write_reports_batch(reports)

        # Verify reports were written
        for log_file in crash_log_files:
            report_file = log_file.with_name(f"{log_file.stem}-AUTOSCAN.md")
            assert report_file.exists()
            content = report_file.read_text()
            assert f"Report for {log_file.name}" in content

    def test_crashlogs_reformat_with_async(self, crash_log_files: list[Path]) -> None:
        """Test async reformatting with sync wrapper."""
        remove_list = ("test_remove",)

        with patch("asyncio.run") as mock_run:
            # This should run without errors
            crashlogs_reformat_with_async(crash_log_files, remove_list)

            # Verify asyncio.run was called
            mock_run.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncDatabasePool:
    """Integration tests for AsyncDatabasePool."""

    async def test_database_pool_context_manager(self) -> None:
        """Test AsyncDatabasePool as context manager."""
        with patch("ClassicLib.Constants.DB_PATHS", []):
            async with AsyncDatabasePool() as pool:
                assert pool is not None
                assert isinstance(pool.connections, dict)
                assert isinstance(pool.query_cache, dict)

    async def test_database_pool_initialization(self) -> None:
        """Test database pool initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test database file
            db_path = Path(temp_dir) / "test.db"
            db_path.write_text("dummy content")  # Not a real SQLite file, but exists

            # Mock aiosqlite.connect to avoid actual database operations
            async def mock_connect(path):
                mock_conn = AsyncMock()
                return mock_conn

            with (
                patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", [db_path]),
                patch("aiosqlite.connect", side_effect=mock_connect) as mock_connect_patch,
            ):
                pool = AsyncDatabasePool()
                await pool.initialize()

                # Verify connection was attempted
                mock_connect_patch.assert_called_once_with(db_path)
                assert db_path in pool.connections

                # Test cleanup
                await pool.close()
                # Note: We can't easily test close() call because it's on the mock connection


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncUtilityFunctions:
    """Integration tests for async utility functions."""

    async def test_load_crash_logs_async(self, crash_log_files: list[Path]) -> None:
        """Test async crash log loading."""
        result = await load_crash_logs_async(crash_log_files)

        assert isinstance(result, dict)
        assert len(result) == 3

        for log_file in crash_log_files:
            assert log_file.name in result
            assert isinstance(result[log_file.name], list)
            assert len(result[log_file.name]) > 0  # Should have content lines


@pytest.mark.integration
@pytest.mark.slow
class TestAsyncPerformanceComparison:
    """Performance comparison tests between sync and async operations."""

    def test_async_vs_sync_file_loading_performance(self, crash_log_files: list[Path]) -> None:
        """Compare async vs sync file loading performance."""
        # Test sync loading
        sync_start = time.perf_counter()
        sync_cache = {}
        for log_file in crash_log_files:
            sync_cache[log_file.name] = log_file.read_text().splitlines()
        sync_time = time.perf_counter() - sync_start

        # Test async loading
        async def async_test():
            async_start = time.perf_counter()
            async_cache = await load_crash_logs_async(crash_log_files)
            return time.perf_counter() - async_start, async_cache

        async_time, async_cache = asyncio.run(async_test())

        # Verify both methods produce same results
        assert len(sync_cache) == len(async_cache)
        for key in sync_cache:
            assert key in async_cache

        # Log performance comparison (async may not always be faster for small files)
        print(f"Sync time: {sync_time:.4f}s, Async time: {async_time:.4f}s")

        # Both should complete successfully
        assert sync_time > 0
        assert async_time > 0
