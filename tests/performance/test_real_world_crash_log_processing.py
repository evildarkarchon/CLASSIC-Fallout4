"""
Real-world crash log processing performance tests.

This module contains performance tests for processing actual crash logs,
measuring pipeline performance with realistic data loads.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanLog.AsyncUtil import load_crash_logs_async
from ClassicLib.ScanLog.pipeline.async_crash_log_pipeline import AsyncCrashLogPipeline
from ClassicLib.ScanLog.pipeline.async_performance_monitor import AsyncPerformanceMonitor

pytestmark = pytest.mark.performance


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
@pytest.mark.asyncio
class TestRealWorldCrashLogProcessing:
    """Real-world crash log processing performance tests."""

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
        from collections import Counter

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
        # Note: load_crash_logs_async was removed from pipeline - it now uses direct file I/O
        with (
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.crashlogs_reformat_async", new_callable=AsyncMock) as mock_reformat,
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.write_reports_batch", new_callable=AsyncMock) as mock_write,
            patch("ClassicLib.ScanLog.pipeline.async_crash_log_pipeline.OrchestratorCore") as mock_orchestrator_class,
        ):
            # Return actual loaded data
            mock_reformat.return_value = None
            mock_write.return_value = None

            # Setup orchestrator with realistic processing
            mock_orchestrator: AsyncMock = AsyncMock()

            async def process_real_logs(batch: list[Path]) -> list[tuple[Path, list[str], bool, Counter]]:
                results = []
                for log_file in batch:
                    lines = async_cache.get(log_file.name, [])
                    report = [f"Async report for {log_file.name}\n"]
                    for i, line in enumerate(lines[:100]):
                        if "Form ID:" in line or "EXCEPTION_" in line or ".dll" in line.lower():
                            report.append(f"Line {i + 1}: {line.strip()}\n")
                    results.append((log_file, report, False, Counter()))
                return results

            mock_orchestrator.process_crash_logs_batch.side_effect = process_real_logs
            mock_orchestrator_class.return_value.__aenter__.return_value = mock_orchestrator
            mock_orchestrator_class.return_value.__aexit__.return_value = None

            # Run the pipeline (provide empty remove_list)
            results, stats = await pipeline.process_crash_logs_async(crash_log_files, ())

        full_test_time: float = time.perf_counter() - full_test_start
        async_stats = stats

        print(f"\nAsync total time:    {full_test_time:.4f}s")
        print(f"Async throughput:    {len(crash_log_files) / full_test_time:.2f} logs/sec")

        # Compare results
        print("\n--- PERFORMANCE COMPARISON ---")
        comparison = AsyncPerformanceMonitor.compare_performance(async_stats, sync_total_time, len(crash_log_files))

        print(f"Speedup factor:      {comparison['speedup_factor']:.2f}x")
        print(f"Improvement:         {comparison['improvement_percent']:.1f}%")
        print(f"Time saved:          {sync_total_time - full_test_time:.4f}s")

        # Assertions
        assert full_test_time > 0
        assert len(results) == len(crash_log_files)
        assert async_stats.get("total_time", 0) > 0

        # Save performance data
        self.save_performance_baseline(crash_log_files, total_size, sync_stats, async_stats, full_test_time, comparison)

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


if __name__ == "__main__":
    pytest.main([__file__])
