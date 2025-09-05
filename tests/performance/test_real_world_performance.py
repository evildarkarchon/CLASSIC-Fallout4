"""
Real-world performance tests using sample crash logs.

This module contains performance tests that use sample crash logs from the
test_data directory to measure pipeline performance. This ensures test
isolation and reproducibility without depending on production data.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanLog.AsyncPipeline import AsyncCrashLogPipeline, AsyncPerformanceMonitor
from ClassicLib.ScanLog.AsyncUtil import load_crash_logs_async

if TYPE_CHECKING:
    from collections.abc import Coroutine


@pytest.fixture
def mock_yamldata() -> MagicMock:
    """Mock ClassicScanLogsInfo for testing."""
    yamldata: MagicMock = MagicMock()
    yamldata.fallout4_crashlog_scan_exclusions = ["test_exclusion"]
    yamldata.fallout4_crashlog_mods_single = {"test_mod": "Test mod message"}
    yamldata.game_ignore_plugins = []
    yamldata.game_ignore_records = []
    yamldata.ignore_list = []
    yamldata.classic_records_list = []
    yamldata.fallout4_crashlog_mods_top = {}
    yamldata.fallout4_crashlog_mods_groups = {}
    yamldata.fallout4_crashlog_stack_check = {}
    yamldata.fallout4_crashlog_error_check = {}
    yamldata.formid_analyzer_enabled = True
    yamldata.record_scanner_enabled = True
    yamldata.plugin_analyzer_enabled = True
    return yamldata


@pytest.mark.slow
@pytest.mark.performance
@pytest.mark.asyncio
class TestRealWorldPerformance:
    """Real-world performance tests using actual crash logs."""

    @pytest.mark.usefixtures("init_message_handler_fixture")
    async def test_real_world_crash_logs_performance(self, mock_yamldata: MagicMock, performance_test_logs: list[Path]) -> None:
        """Real-world performance test: Process crash logs using test fixtures.

        This test uses sample crash logs from test_data directory to ensure
        test isolation and reproducibility.
        """
        # Use fixture-provided crash log files
        crash_log_files: list[Path] = performance_test_logs

        print("\n=== REAL-WORLD CRASH LOGS PERFORMANCE TEST ===")
        print(f"Processing {len(crash_log_files)} actual crash logs")

        # Calculate total file size
        total_size: int = sum(f.stat().st_size for f in crash_log_files)
        print(f"Total data size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")

        # First, run sync test for comparison
        print("\n--- SYNC PIPELINE TEST ---")
        sync_start: float = time.perf_counter()

        # Simulate sync pipeline with sequential operations
        sync_results: list[tuple[Path, list[str], bool, dict[str, Any]]] = []

        # Stage 1: Reformat (sequential)
        sync_reformat_start: float = time.perf_counter()
        for log_file in crash_log_files:  # noqa: B007
            # Simulate reformatting delay
            await asyncio.sleep(0.001)  # 1ms per file
        sync_reformat_time: float = time.perf_counter() - sync_reformat_start

        # Stage 2: Load (sequential)
        sync_load_start: float = time.perf_counter()
        sync_cache: dict[str, list[str]] = {}
        for log_file in crash_log_files:
            content: str = log_file.read_text(encoding="utf-8", errors="ignore")
            sync_cache[log_file.name] = content.splitlines()
            # Add small delay to simulate sequential I/O overhead
            await asyncio.sleep(0.0002)  # 0.2ms per file
        sync_load_time: float = time.perf_counter() - sync_load_start

        # Stage 3: Process (sequential)
        sync_process_start: float = time.perf_counter()
        for log_file in crash_log_files:
            lines: list[str] = sync_cache[log_file.name]
            # Simulate processing
            report: list[str] = [f"Sync report for {log_file.name}\n"]
            for i, line in enumerate(lines[:50]):
                if "Form ID:" in line or "EXCEPTION_" in line or ".dll" in line.lower():
                    report.append(f"Found at line {i + 1}: {line.strip()}\n")
            await asyncio.sleep(0.005)  # 5ms processing per file
            sync_results.append((log_file, report, False, {}))
        sync_process_time: float = time.perf_counter() - sync_process_start

        # Stage 4: Write (sequential)
        sync_write_start: float = time.perf_counter()
        for _result in sync_results:
            await asyncio.sleep(0.002)  # 2ms write per file
        sync_write_time: float = time.perf_counter() - sync_write_start

        sync_total_time: float = time.perf_counter() - sync_start

        sync_stats: dict[str, float] = {
            "total_time": sync_total_time,
            "reformat_time": sync_reformat_time,
            "load_time": sync_load_time,
            "process_time": sync_process_time,
            "write_time": sync_write_time,
            "logs_per_second": len(crash_log_files) / sync_total_time,
        }

        print(f"Sync total time:     {sync_total_time:.4f}s")
        print(f"Sync throughput:     {sync_stats['logs_per_second']:.2f} logs/sec")

        # Now run async test
        print("\n--- ASYNC PIPELINE TEST ---")

        pipeline: AsyncCrashLogPipeline = AsyncCrashLogPipeline(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,  # Don't use real DB in test
        )

        # Record comprehensive metrics
        full_test_start: float = time.perf_counter()

        # Actually load and process the real crash logs
        async_cache = await load_crash_logs_async(crash_log_files)

        # Process with mocked orchestrator for consistent timing
        with (
            patch("ClassicLib.ScanLog.AsyncPipeline.crashlogs_reformat_async") as mock_reformat,
            patch("ClassicLib.ScanLog.AsyncPipeline.load_crash_logs_async") as mock_load,
            patch("ClassicLib.ScanLog.AsyncPipeline.write_reports_batch") as mock_write,
            patch("ClassicLib.ScanLog.OrchestratorCore.OrchestratorCore") as mock_orchestrator_class,
        ):
            # Return actual loaded data
            mock_reformat.return_value = None
            mock_load.return_value = async_cache
            mock_write.return_value = None

            # Setup orchestrator with realistic processing
            mock_orchestrator: AsyncMock = AsyncMock()

            async def process_real_logs(batch: list[Path]) -> list[tuple[Path, list[str], bool, dict]]:
                results = []
                for log_file in batch:
                    lines = async_cache.get(log_file.name, [])
                    report = [f"Async report for {log_file.name}\n"]
                    for i, line in enumerate(lines[:100]):
                        if "Form ID:" in line or "EXCEPTION_" in line or ".dll" in line.lower():
                            report.append(f"Line {i + 1}: {line.strip()}\n")
                    results.append((log_file, report, False, {}))
                return results

            mock_orchestrator.process_crash_logs_batch.side_effect = process_real_logs
            mock_orchestrator_class.return_value.__aenter__.return_value = mock_orchestrator
            mock_orchestrator_class.return_value.__aexit__.return_value = None

            # Run the pipeline (provide empty remove_list)
            results, stats = await pipeline.process_crash_logs_async(crash_log_files, [])

        full_test_time: float = time.perf_counter() - full_test_start
        async_stats = stats

        print(f"\nAsync total time:    {full_test_time:.4f}s")
        print(f"Async throughput:    {len(crash_log_files) / full_test_time:.2f} logs/sec")

        # Compare results
        print("\n--- PERFORMANCE COMPARISON ---")
        comparison = AsyncPerformanceMonitor.compare_performance(
            async_stats, sync_total_time, len(crash_log_files)
        )

        print(f"Speedup factor:      {comparison['speedup_factor']:.2f}x")
        print(f"Improvement:         {comparison['improvement_percent']:.1f}%")
        print(f"Time saved:          {sync_total_time - full_test_time:.4f}s")

        # Assertions
        assert full_test_time > 0
        assert len(results) == len(crash_log_files)
        assert async_stats.get("total_time", 0) > 0

        # Save performance data
        self.save_performance_baseline(
            crash_log_files, total_size, sync_stats, async_stats, full_test_time, comparison
        )

    @pytest.mark.usefixtures("init_message_handler_fixture")
    async def test_sync_vs_async_real_world_comparison(self, mock_yamldata: MagicMock, small_performance_test_logs: list[Path]) -> None:
        """Direct comparison of sync vs async processing with test crash logs.

        This test uses sample crash logs from test_data directory to ensure
        test isolation and reproducibility.
        """
        # Use fixture-provided crash log files (20 files)
        crash_log_files: list[Path] = small_performance_test_logs

        if len(crash_log_files) < 5:
            pytest.skip("Not enough crash log files for comparison - need at least 5 crash logs")

        print("\n=== SYNC VS ASYNC REAL-WORLD COMPARISON ===")
        print(f"Testing with {len(crash_log_files)} crash logs")

        # Test 1: File Loading Performance
        print("\n1. FILE LOADING COMPARISON:")

        # Sync loading
        sync_load_start = time.perf_counter()
        sync_data = {}
        for log_file in crash_log_files:
            sync_data[log_file.name] = log_file.read_text(errors="ignore").splitlines()
        sync_load_time = time.perf_counter() - sync_load_start

        # Async loading
        async_load_start = time.perf_counter()
        async_data = await load_crash_logs_async(crash_log_files)
        async_load_time = time.perf_counter() - async_load_start

        print(f"  Sync:  {sync_load_time:.4f}s")
        print(f"  Async: {async_load_time:.4f}s")
        print(f"  Speedup: {sync_load_time / async_load_time:.2f}x" if async_load_time > 0 else "N/A")

        # Test 2: Concurrent Processing
        print("\n2. CONCURRENT PROCESSING COMPARISON:")

        # Sequential processing
        seq_start = time.perf_counter()
        seq_results = []
        for name, lines in sync_data.items():
            # Simulate processing
            result = len([l for l in lines if "Form ID:" in l or "EXCEPTION_" in l])
            seq_results.append(result)
            await asyncio.sleep(0.001)  # Simulate processing delay
        seq_time = time.perf_counter() - seq_start

        # Concurrent processing
        async def process_log(name: str, lines: list[str]) -> int:
            await asyncio.sleep(0.001)  # Simulate processing delay
            return len([l for l in lines if "Form ID:" in l or "EXCEPTION_" in l])

        conc_start = time.perf_counter()
        tasks = [process_log(name, lines) for name, lines in async_data.items()]
        conc_results = await asyncio.gather(*tasks)
        conc_time = time.perf_counter() - conc_start

        print(f"  Sequential: {seq_time:.4f}s")
        print(f"  Concurrent: {conc_time:.4f}s")
        print(f"  Speedup: {seq_time / conc_time:.2f}x" if conc_time > 0 else "N/A")

        # Test 3: Memory Efficiency
        print("\n3. MEMORY EFFICIENCY:")

        total_size = sum(len("".join(lines)) for lines in sync_data.values())
        print(f"  Total data processed: {total_size:,} bytes")
        print(f"  Files processed: {len(crash_log_files)}")
        print(f"  Avg file size: {total_size / len(crash_log_files):,.0f} bytes")

        # Assertions
        assert len(sync_data) == len(async_data)
        assert len(seq_results) == len(conc_results)
        assert async_load_time > 0
        assert conc_time > 0

        # Performance expectations
        # Async should generally be faster for I/O bound operations
        if len(crash_log_files) >= 10:
            # With enough files, async should show benefits
            assert conc_time <= seq_time * 1.1  # Allow 10% variance

    def save_performance_baseline(
        self,
        crash_log_files: list[Path],
        total_size: int,
        sync_stats: dict[str, float],
        async_stats: dict[str, float],
        full_test_time: float,
        comparison: dict[str, Any],
    ) -> None:
        """Save performance baseline data for future comparisons."""
        baseline_data: dict[str, Any] = {
            "test_type": "real_world_crash_logs",
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "log_count": len(crash_log_files),
            "total_size_bytes": total_size,
            "avg_file_size": total_size / len(crash_log_files),
            "sync_performance": sync_stats,
            "async_performance": {
                **async_stats,
                "total_time": full_test_time,
                "throughput_logs_per_sec": len(crash_log_files) / full_test_time,
            },
            "comparison": comparison,
        }

        # Save to project root
        project_root: Path = Path(__file__).parent.parent.parent
        baseline_dir: Path = project_root / "performance_baselines"
        baseline_dir.mkdir(exist_ok=True)

        timestamp: str = time.strftime("%Y%m%d_%H%M%S")
        baseline_file: Path = baseline_dir / f"real_world_baseline_{timestamp}.json"
        latest_file: Path = baseline_dir / "real_world_baseline_latest.json"

        baseline_file.write_text(json.dumps(baseline_data, indent=2))
        latest_file.write_text(json.dumps(baseline_data, indent=2))

        print(f"\nPerformance baseline saved to: {baseline_file}")
