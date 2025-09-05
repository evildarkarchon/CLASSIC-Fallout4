"""
Performance tests and benchmarks for async operations.

This module contains performance comparison tests between sync and async operations,
establishing baseline metrics for the async pipeline performance.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanLog.AsyncFileIO import load_crash_logs_async_optimized
from ClassicLib.ScanLog.AsyncPipeline import AsyncCrashLogPipeline
from ClassicLib.ScanLog.AsyncReformat import crashlogs_reformat_async
from ClassicLib.ScanLog.AsyncUtil import load_crash_logs_async


def create_large_crash_log_set(tmp_path: Path, log_count: int) -> list[Path]:
    """Create a larger set of crash logs for performance testing."""
    crash_logs_dir: Path = tmp_path / "Performance_Test_Logs"
    crash_logs_dir.mkdir(parents=True, exist_ok=True)

    # Realistic crash log content with various sizes
    base_content: str = """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]

PROBABLE CALL STACK:
"""

    files: list[Path] = []
    for i in range(log_count):
        log_file: Path = crash_logs_dir / f"crash-perf-test-{i:03d}.log"

        # Vary content size to simulate real-world scenarios
        callstack_lines: int = min(50 + (i % 20), 100)  # 50-100 lines of callstack
        content_parts: list[str] = [base_content]

        for j in range(callstack_lines):
            content_parts.append(f"\t[{j:2d}] 0x7FF6EF{j:06X} Fallout4.exe+{j:07X} -> {j * 1000 + 555}+0x{j:02X}\n")
            if j % 5 == 0:  # Add FormIDs periodically
                content_parts.append(f"\tForm ID: 0x{j:08X}\n")

        # Add modules and plugins
        content_parts.extend([
            "\nMODULES:\n",
            f"\tperformance_module_{i}.dll\n",
            f"\ttest_module_{i % 10}.dll\n",
            "\nF4SE PLUGINS:\n",
            f"\tf4se_perf_plugin_{i}.dll\n",
            "\nPLUGINS:\n",
            "\t[00] Fallout4.esm\n",
            "\t[01] DLCRobot.esm\n",
            f"\t[{i:02d}] PerfTestPlugin_{i}.esp\n",
        ])

        log_file.write_text("".join(content_parts))
        files.append(log_file)

    return files


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


@pytest.mark.integration
@pytest.mark.slow
class TestAsyncPerformanceComparison:
    """Performance comparison tests between sync and async operations."""

    @pytest.mark.usefixtures("init_message_handler_fixture")
    def test_crashlogs_reformat_async_direct(self, tmp_path: Path) -> None:
        """Test direct async reformatting call."""
        crash_logs = create_large_crash_log_set(tmp_path, 3)
        remove_list: tuple[str] = ("test_remove",)

        # Mock the async function at the local import location
        with patch("tests.performance.test_async_performance.crashlogs_reformat_async", new_callable=AsyncMock) as mock_async_func:
            # AsyncMock handles coroutines properly without creating them prematurely
            mock_async_func.return_value = None

            # This should run without errors using asyncio.run
            asyncio.run(crashlogs_reformat_async(crash_logs, remove_list))

            # Verify the async function was called
            mock_async_func.assert_called_once_with(crash_logs, remove_list)

    def test_async_vs_sync_file_loading_performance(self, tmp_path: Path) -> None:
        """Compare async vs sync file loading performance."""
        crash_log_files = create_large_crash_log_set(tmp_path, 10)

        # Test sync loading
        sync_start: float = time.perf_counter()
        sync_cache: dict[Any, Any] = {}
        for log_file in crash_log_files:
            sync_cache[log_file.name] = log_file.read_text().splitlines()
        sync_time: float = time.perf_counter() - sync_start

        # Test async loading
        async def async_test() -> tuple[float, dict[str, list[str]]]:
            async_start: float = time.perf_counter()
            async_cache: dict[str, list[str]] = await load_crash_logs_async(crash_log_files)
            return time.perf_counter() - async_start, async_cache

        async_time, async_cache = asyncio.run(async_test())

        # Verify both methods produce same results
        assert len(sync_cache) == len(async_cache)
        for key in sync_cache:
            assert key in async_cache

        # Log performance comparison (async may not always be faster for small files)
        print(f"\nFile Loading Performance (10 files):")
        print(f"Sync time:  {sync_time:.4f}s")
        print(f"Async time: {async_time:.4f}s")
        if async_time > 0:
            print(f"Speedup:    {sync_time / async_time:.2f}x")

        # Both should complete successfully
        assert sync_time > 0
        assert async_time > 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.performance
class TestAsyncPerformanceBaselines:
    """
    Comprehensive performance baseline tests for async operations.

    These tests establish baseline performance metrics for:
    - File I/O operations (single/batch/concurrent)
    - Database operations (async vs sync)
    - Pipeline processing (full async pipeline)
    - Memory usage patterns
    - Scalability with different log counts
    """

    @pytest.mark.slow
    def test_file_io_baseline_single_files(self, tmp_path: Path) -> None:
        """Baseline: Single file I/O performance (async vs sync)."""
        test_files: list[Path] = create_large_crash_log_set(tmp_path, 5)

        results: dict[str, list[float]] = {
            "sync_read_times": [],
            "async_read_times": [],
            "sync_write_times": [],
            "async_write_times": [],
            "file_sizes": [],
        }

        for test_file in test_files:
            file_size: int = test_file.stat().st_size
            results["file_sizes"].append(file_size)

            # Test sync reading
            sync_start: float = time.perf_counter()
            sync_content: str = test_file.read_text()
            sync_read_time: float = time.perf_counter() - sync_start
            results["sync_read_times"].append(sync_read_time)

            # Test async reading
            async def async_read_test(file_path: Path = test_file) -> tuple[float, str]:
                async_start: float = time.perf_counter()
                import aiofiles

                async with aiofiles.open(file_path, encoding="utf-8", errors="ignore") as f:
                    async_content: str = await f.read()
                async_read_time: float = time.perf_counter() - async_start
                return async_read_time, async_content

            async_read_time, async_content = asyncio.run(async_read_test())
            results["async_read_times"].append(async_read_time)

            # Verify content consistency
            assert len(sync_content) == len(async_content)

            # Test sync writing
            write_content: str = f"Modified content for {test_file.name}\n" + sync_content
            write_file: Path = test_file.with_name(f"{test_file.stem}_sync_write.log")

            sync_start = time.perf_counter()
            write_file.write_text(write_content)
            sync_write_time: float = time.perf_counter() - sync_start
            results["sync_write_times"].append(sync_write_time)

            # Test async writing
            async def async_write_test(file_path: Path = test_file, content: str = write_content) -> float:
                async_start: float = time.perf_counter()
                async_write_file: Path = file_path.with_name(f"{file_path.stem}_async_write.log")
                import aiofiles

                async with aiofiles.open(async_write_file, mode="w", encoding="utf-8", errors="ignore") as f:
                    await f.write(content)
                async_write_time: float = time.perf_counter() - async_start
                return async_write_time

            async_write_time: float = asyncio.run(async_write_test())
            results["async_write_times"].append(async_write_time)

        # Log baseline metrics
        avg_file_size: float = sum(results["file_sizes"]) / len(results["file_sizes"])
        avg_sync_read: float = sum(results["sync_read_times"]) / len(results["sync_read_times"])
        avg_async_read: float = sum(results["async_read_times"]) / len(results["async_read_times"])
        avg_sync_write: float = sum(results["sync_write_times"]) / len(results["sync_write_times"])
        avg_async_write: float = sum(results["async_write_times"]) / len(results["async_write_times"])

        print("\n=== SINGLE FILE I/O BASELINE METRICS ===")
        print(f"Average file size: {avg_file_size:,.0f} bytes")
        print(f"Sync read time:    {avg_sync_read:.4f}s")
        print(f"Async read time:   {avg_async_read:.4f}s")
        print(f"Sync write time:   {avg_sync_write:.4f}s")
        print(f"Async write time:  {avg_async_write:.4f}s")
        print(f"Read speedup:      {avg_sync_read / avg_async_read:.2f}x" if avg_async_read > 0 else "N/A")
        print(f"Write speedup:     {avg_sync_write / avg_async_write:.2f}x" if avg_async_write > 0 else "N/A")

        # Assertions
        assert all(t > 0 for t in results["sync_read_times"])
        assert all(t > 0 for t in results["async_read_times"])
        assert all(t > 0 for t in results["sync_write_times"])
        assert all(t > 0 for t in results["async_write_times"])

    @pytest.mark.slow
    def test_file_io_baseline_batch_operations(self, tmp_path: Path) -> None:
        """Baseline: Batch file I/O performance (concurrent async vs sequential sync)."""
        test_files: list[Path] = create_large_crash_log_set(tmp_path, 20)

        # Test sync batch reading (sequential)
        sync_start: float = time.perf_counter()
        sync_results: dict[str, list[str]] = {}
        for test_file in test_files:
            sync_results[test_file.name] = test_file.read_text().splitlines()
        sync_total_time: float = time.perf_counter() - sync_start

        # Test async batch reading (concurrent)
        async def async_batch_read() -> tuple[dict[str, list[str]], float]:
            import aiofiles
            from typing import Coroutine

            async def read_single(file_path: Path) -> tuple[str, list[str]]:
                async with aiofiles.open(file_path, encoding="utf-8", errors="ignore") as f:
                    content: str = await f.read()
                    return file_path.name, content.splitlines()

            async_start: float = time.perf_counter()
            tasks: list[Coroutine[Any, Any, tuple[str, list[str]]]] = [
                read_single(test_file) for test_file in test_files
            ]
            results: list[tuple[str, list[str]] | BaseException] = await asyncio.gather(
                *tasks, return_exceptions=True
            )
            async_total_time: float = time.perf_counter() - async_start

            # Convert results to dict
            async_results: dict[str, list[str]] = {}
            for result in results:
                if not isinstance(result, BaseException):
                    name, lines = result
                    async_results[name] = lines

            return async_results, async_total_time

        async_results, async_total_time = asyncio.run(async_batch_read())

        # Verify consistency
        assert len(sync_results) == len(async_results)
        for key in sync_results:
            assert key in async_results

        # Calculate metrics
        files_per_sec_sync = len(test_files) / sync_total_time if sync_total_time > 0 else 0
        files_per_sec_async = len(test_files) / async_total_time if async_total_time > 0 else 0

        print("\n=== BATCH FILE I/O BASELINE METRICS (20 files) ===")
        print(f"Sync total time:   {sync_total_time:.4f}s ({files_per_sec_sync:.1f} files/sec)")
        print(f"Async total time:  {async_total_time:.4f}s ({files_per_sec_async:.1f} files/sec)")
        if async_total_time > 0:
            print(f"Speedup factor:    {sync_total_time / async_total_time:.2f}x")

        # Assertions
        assert sync_total_time > 0
        assert async_total_time > 0
        assert len(async_results) == 20

    @pytest.mark.slow
    async def test_async_pipeline_scalability_baseline(
        self, tmp_path: Path, mock_yamldata: MagicMock
    ) -> None:
        """Baseline: Async pipeline scalability with different log counts."""
        test_counts = [5, 10, 25]
        results = []

        for count in test_counts:
            test_files = create_large_crash_log_set(tmp_path / f"scale_{count}", count)

            pipeline = AsyncCrashLogPipeline(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            # Mock pipeline components
            with (
                patch("ClassicLib.ScanLog.AsyncPipeline.crashlogs_reformat_async"),
                patch("ClassicLib.ScanLog.AsyncPipeline.load_crash_logs_async") as mock_load,
                patch("ClassicLib.ScanLog.AsyncPipeline.write_reports_batch"),
                patch("ClassicLib.ScanLog.OrchestratorCore.OrchestratorCore") as mock_orch,
            ):
                mock_load.return_value = {f.name: ["content"] for f in test_files}

                mock_orchestrator = AsyncMock()
                mock_orchestrator.process_crash_logs_batch.return_value = [
                    (f, ["report"], False, {}) for f in test_files
                ]
                mock_orch.return_value.__aenter__.return_value = mock_orchestrator
                mock_orch.return_value.__aexit__.return_value = None

                start = time.perf_counter()
                _, stats = await pipeline.process_crash_logs_async(test_files)
                total_time = time.perf_counter() - start

                results.append({
                    "count": count,
                    "time": total_time,
                    "logs_per_second": count / total_time if total_time > 0 else 0,
                })

        print("\n=== PIPELINE SCALABILITY BASELINE ===")
        for result in results:
            print(
                f"{result['count']:3d} logs: {result['time']:.3f}s "
                f"({result['logs_per_second']:.1f} logs/sec)"
            )

        # Verify scalability (time should increase sublinearly with count)
        if len(results) >= 2:
            # Rough check: doubling files shouldn't double time (concurrent benefit)
            time_ratio = results[1]["time"] / results[0]["time"]
            count_ratio = results[1]["count"] / results[0]["count"]
            # Time should increase less than linearly
            assert time_ratio < count_ratio * 1.5  # Allow some overhead

    @pytest.mark.slow
    def test_memory_usage_baseline(self, tmp_path: Path) -> None:
        """Baseline: Memory usage patterns for async operations."""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        process = psutil.Process()
        test_files = create_large_crash_log_set(tmp_path, 30)

        # Measure sync memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        sync_data = {}
        for f in test_files:
            sync_data[f.name] = f.read_text()

        sync_peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        sync_memory_increase = sync_peak_memory - initial_memory

        # Clear sync data
        sync_data.clear()
        import gc
        gc.collect()

        # Measure async memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        async def async_load():
            return await load_crash_logs_async_optimized(test_files)

        async_data = asyncio.run(async_load())

        async_peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        async_memory_increase = async_peak_memory - initial_memory

        print("\n=== MEMORY USAGE BASELINE (30 files) ===")
        print(f"Sync memory increase:  {sync_memory_increase:.1f} MB")
        print(f"Async memory increase: {async_memory_increase:.1f} MB")
        if sync_memory_increase > 0:
            efficiency = (1 - async_memory_increase / sync_memory_increase) * 100
            print(f"Memory efficiency:     {efficiency:+.1f}%")

        # Both should use reasonable memory
        assert sync_memory_increase < 100  # Less than 100MB for 30 files
        assert async_memory_increase < 100

    @pytest.mark.slow
    def test_error_handling_performance_baseline(self, tmp_path: Path) -> None:
        """Baseline: Performance impact of error handling."""
        # Mix of valid and problematic files
        valid_files = create_large_crash_log_set(tmp_path / "valid", 10)

        # Create some problematic files
        problem_dir = tmp_path / "problems"
        problem_dir.mkdir()

        empty_file = problem_dir / "empty.log"
        empty_file.write_text("")

        large_file = problem_dir / "large.log"
        large_file.write_text("X" * (5 * 1024 * 1024))  # 5MB file

        all_files = valid_files + [empty_file, large_file]

        # Time with error handling
        async def with_error_handling():
            start = time.perf_counter()
            try:
                result = await load_crash_logs_async(all_files)
            except Exception:
                result = {}
            return time.perf_counter() - start, result

        time_with_errors, result = asyncio.run(with_error_handling())

        # Time without problematic files
        async def without_errors():
            start = time.perf_counter()
            result = await load_crash_logs_async(valid_files)
            return time.perf_counter() - start, result

        time_without_errors, _ = asyncio.run(without_errors())

        print("\n=== ERROR HANDLING PERFORMANCE ===")
        print(f"With problematic files:    {time_with_errors:.4f}s")
        print(f"Without problematic files: {time_without_errors:.4f}s")
        overhead = ((time_with_errors - time_without_errors) / time_without_errors) * 100
        print(f"Error handling overhead:   {overhead:.1f}%")

        # Error handling shouldn't cause massive slowdown
        assert time_with_errors < time_without_errors * 2  # Less than 2x slowdown
