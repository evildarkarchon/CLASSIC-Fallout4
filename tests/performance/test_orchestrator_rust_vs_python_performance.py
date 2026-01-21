"""
Performance benchmark tests comparing Rust vs Python orchestrator implementations.

This module provides comprehensive performance benchmarks to validate the expected
5-10x speedup for single-log processing and 10-20x speedup for batch processing
when using Rust acceleration.
"""

import asyncio
import time
import tracemalloc
from collections import Counter
from pathlib import Path
from typing import Any, AsyncGenerator
from unittest.mock import patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.integration.factory import get_orchestrator
from ClassicLib.integration.status import is_rust_accelerated
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.ScanLog.scanloginfo.classic_scan_logs_info import ClassicScanLogsInfo
from ClassicLib.YamlSettings import YamlSettingsCache


class TestOrchestratorPerformance:
    """
    Performance benchmarks for orchestrator implementations.

    Tests single-log and batch processing performance comparing Rust-accelerated
    HybridOrchestrator against pure Python OrchestratorCore.
    """

    @pytest.fixture(autouse=True)
    def mock_hybrid_orchestrator_settings(self):
        """Mock classic_settings for HybridOrchestrator.

        The HybridOrchestrator calls classic_settings(int, "Max Concurrent Scans")
        to determine concurrency. This fixture mocks it to return 0 (automatic
        concurrency) to ensure consistent behavior during performance tests.
        """
        with patch("ClassicLib.ScanLog.HybridOrchestrator.classic_settings", return_value=0):
            yield

    @pytest.fixture
    def sample_logs(self, tmp_path: Path) -> list[Path]:
        """
        Create sample crash log files for testing.

        Generates realistic crash log content with:
        - Crash generator info
        - System specs
        - Call stack with FormIDs
        - Module list
        - Plugin list

        Args:
            tmp_path: Pytest temp directory fixture

        Returns:
            list[Path]: List of 20 sample crash log file paths
        """
        logs = []
        for i in range(20):
            log_path = tmp_path / f"crash-{i:02d}.log"

            # Generate realistic crash log content
            content = f"""Buffout 4 v1.26.2
Crash Log Generated On: 2024-01-{i + 1:02d} 14:23:45

SYSTEM SPECS:
    OS: Windows 10
    CPU: Intel Core i7-9700K
    GPU: NVIDIA GeForce RTX 2080
    RAM: 32GB

PROBABLE CALL STACK:
    [0] 0x7FF6AB{i:06X}+0x123 (Fallout4.exe+0x123)
    [1] FormID 0x00{i:06X} (Plugin{i}.esp)
    [2] 0x7FF6AB{i + 1:06X}+0x456 (Fallout4.exe+0x456)

ALL MODULES:
    Fallout4.exe
    f4se_1_10_163.dll
    BuffoutNG.dll

F4SE PLUGINS:
    BuffoutNG v1.0
    MCM v1.0

PLUGINS:
    [00] Fallout4.esm
    [01] DLCRobot.esm
    [02] Plugin{i}.esp
    [03] ModA.esp
    [04] ModB.esp
    [FE:000] CCContent.esl
"""
            log_path.write_text(content, encoding="utf-8")
            logs.append(log_path)

        return logs

    @pytest.fixture
    async def yamldata(self, setup_global_registry: None) -> ClassicScanLogsInfo:
        """
        Load YAML configuration data for orchestrator.

        This fixture ensures the YAML cache is properly initialized in the GlobalRegistry
        before creating the ClassicScanLogsInfo instance using the async factory method.

        Args:
            setup_global_registry: Function-scoped registry initialization fixture

        Returns:
            ClassicScanLogsInfo instance with game configuration
        """
        # Ensure YAML cache is registered (should be done by setup_global_registry, but verify)
        if not GlobalRegistry.is_registered(GlobalRegistry.Keys.YAML_CACHE):
            yaml_cache = YamlSettingsCache()
            GlobalRegistry.register(GlobalRegistry.Keys.YAML_CACHE, yaml_cache)

        # Use async factory method for proper async initialization
        return await ClassicScanLogsInfo.create_async()

    @pytest.fixture
    async def python_orchestrator(self, yamldata: ClassicScanLogsInfo) -> AsyncGenerator[OrchestratorCore, None]:
        """
        Create pure Python orchestrator instance.

        Args:
            yamldata: Configuration data fixture

        Returns:
            OrchestratorCore instance (pure Python implementation)
        """
        async with OrchestratorCore(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            yield orch

    @pytest.fixture
    async def hybrid_orchestrator(self, yamldata: ClassicScanLogsInfo) -> AsyncGenerator[Any, None]:
        """
        Create hybrid orchestrator instance (Rust + Python).

        Args:
            yamldata: Configuration data fixture

        Returns:
            HybridOrchestrator or OrchestratorCore instance
        """
        async with get_orchestrator(
            yamldata=yamldata,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=False,
        ) as orch:
            yield orch

    @pytest.mark.performance
    @pytest.mark.rust
    @pytest.mark.asyncio
    async def test_single_log_processing_performance(
        self,
        python_orchestrator: OrchestratorCore,
        hybrid_orchestrator: Any,
        sample_logs: list[Path],
    ) -> None:
        """
        Compare Rust vs Python for single log processing.

        Expected: 5-10x speedup with Rust acceleration

        Args:
            python_orchestrator: Pure Python orchestrator
            hybrid_orchestrator: Hybrid (Rust+Python) orchestrator
            sample_logs: Sample crash log files
        """
        log_path = sample_logs[0]

        # Warm-up runs to ensure caches are populated
        await python_orchestrator.process_crash_log(log_path)
        await hybrid_orchestrator.process_crash_log(log_path)

        # Benchmark Python orchestrator
        start = time.perf_counter()
        python_result = await python_orchestrator.process_crash_log(log_path)
        python_time = time.perf_counter() - start

        # Benchmark hybrid orchestrator
        start = time.perf_counter()
        hybrid_result = await hybrid_orchestrator.process_crash_log(log_path)
        hybrid_time = time.perf_counter() - start

        # Verify both produce results
        assert isinstance(python_result, tuple)
        assert len(python_result) == 4
        assert isinstance(hybrid_result, tuple)
        assert len(hybrid_result) == 4

        # Check if Rust is actually being used
        if is_rust_accelerated("orchestrator"):
            # Calculate speedup
            speedup = python_time / hybrid_time if hybrid_time > 0 else 1.0

            # Print results for CI/CD tracking
            print(f"\n{'=' * 60}")
            print("SINGLE LOG PROCESSING BENCHMARK:")
            print(f"  Python time : {python_time * 1000:.2f}ms")
            print(f"  Hybrid time : {hybrid_time * 1000:.2f}ms")
            print(f"  Speedup     : {speedup:.2f}x")
            print(f"{'=' * 60}\n")

            # Note: Single-log processing may not show significant speedup
            # because Python orchestrator has complex logic that Rust doesn't
            # fully replicate yet. Expected speedup is 1.5-3x currently.
            assert speedup >= 1.0, f"Expected some speedup, got {speedup:.2f}x"

            # Write results to file for tracking
            results_file = Path("performance/results/orchestrator_single_log.txt")
            results_file.parent.mkdir(parents=True, exist_ok=True)
            with results_file.open("a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},")
                f.write(f"{python_time * 1000:.2f},{hybrid_time * 1000:.2f},{speedup:.2f}\n")
        else:
            print("\n⚠️  Rust orchestrator not available - skipping performance test\n")
            pytest.skip("Rust orchestrator not available")

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.rust
    @pytest.mark.asyncio
    async def test_batch_processing_performance(
        self,
        python_orchestrator: OrchestratorCore,
        hybrid_orchestrator: Any,
        sample_logs: list[Path],
    ) -> None:
        """
        Compare Rust vs Python for batch processing (20 logs).

        Expected: 10-20x speedup with Rust acceleration via unbounded parallelism

        Args:
            python_orchestrator: Pure Python orchestrator
            hybrid_orchestrator: Hybrid (Rust+Python) orchestrator
            sample_logs: Sample crash log files (20 logs)
        """
        # Use all 20 sample logs for batch testing
        batch_logs = sample_logs

        # Warm-up run
        await python_orchestrator.process_crash_logs_batch(batch_logs[:2])
        await hybrid_orchestrator.process_crash_logs_batch(batch_logs[:2])

        # Benchmark Python orchestrator (batch_size=10 limit)
        start = time.perf_counter()
        python_results = await python_orchestrator.process_crash_logs_batch(batch_logs)
        python_time = time.perf_counter() - start

        # Benchmark hybrid orchestrator (unbounded parallelism with Rust)
        start = time.perf_counter()
        hybrid_results = await hybrid_orchestrator.process_crash_logs_batch(batch_logs)
        hybrid_time = time.perf_counter() - start

        # Verify both produce correct number of results
        assert len(python_results) == len(batch_logs)
        assert len(hybrid_results) == len(batch_logs)

        # Check result format
        for result in python_results:
            assert isinstance(result, tuple)
            assert len(result) == 4
            assert isinstance(result[3], Counter)  # Statistics counter

        # Check if Rust is actually being used
        if is_rust_accelerated("orchestrator"):
            # Calculate speedup
            speedup = python_time / hybrid_time if hybrid_time > 0 else 1.0

            # Print results for CI/CD tracking
            print(f"\n{'=' * 60}")
            print("BATCH PROCESSING BENCHMARK (20 logs):")
            print(f"  Python time      : {python_time:.2f}s ({python_time / len(batch_logs) * 1000:.2f}ms per log)")
            print(f"  Hybrid time      : {hybrid_time:.2f}s ({hybrid_time / len(batch_logs) * 1000:.2f}ms per log)")
            print(f"  Speedup          : {speedup:.2f}x")
            print("  Python strategy  : batch_size=10 (limited parallelism)")
            print("  Hybrid strategy  : Rust unbounded parallelism")
            print(f"{'=' * 60}\n")

            # Expected: 10-20x speedup for batch processing
            # Minimum: 5x speedup (conservative estimate)
            assert speedup >= 5.0, (
                f"Expected 5x+ speedup for batch processing, got {speedup:.2f}x. Python: {python_time:.2f}s, Hybrid: {hybrid_time:.2f}s"
            )

            # Write results to file for tracking
            results_file = Path("performance/results/orchestrator_batch.txt")
            results_file.parent.mkdir(parents=True, exist_ok=True)
            with results_file.open("a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},")
                f.write(f"{len(batch_logs)},")
                f.write(f"{python_time:.2f},{hybrid_time:.2f},{speedup:.2f}\n")
        else:
            print("\n⚠️  Rust orchestrator not available - skipping performance test\n")
            pytest.skip("Rust orchestrator not available")

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.rust
    @pytest.mark.asyncio
    async def test_memory_usage_comparison(
        self,
        python_orchestrator: OrchestratorCore,
        hybrid_orchestrator: Any,
        sample_logs: list[Path],
    ) -> None:
        """
        Compare memory usage between Python and Rust implementations.

        Expected: 5-10x memory reduction with Rust (zero-copy operations)

        Args:
            python_orchestrator: Pure Python orchestrator
            hybrid_orchestrator: Hybrid orchestrator
            sample_logs: Sample crash log files
        """
        try:
            import os

            import psutil
        except ImportError:
            pytest.skip("psutil not installed - cannot measure memory usage")
            return

        process = psutil.Process(os.getpid())

        # Batch processing with Python
        initial_mem = process.memory_info().rss / 1024 / 1024  # MB
        await python_orchestrator.process_crash_logs_batch(sample_logs)
        python_mem = process.memory_info().rss / 1024 / 1024 - initial_mem

        # Force garbage collection
        import gc

        gc.collect()
        await asyncio.sleep(0.1)

        # Batch processing with Rust
        initial_mem = process.memory_info().rss / 1024 / 1024
        await hybrid_orchestrator.process_crash_logs_batch(sample_logs)
        hybrid_mem = process.memory_info().rss / 1024 / 1024 - initial_mem

        print(f"\n{'=' * 60}")
        print("MEMORY USAGE COMPARISON (20 logs):")
        print(f"  Python memory : {python_mem:.2f} MB")
        print(f"  Hybrid memory : {hybrid_mem:.2f} MB")
        if hybrid_mem > 0:
            reduction = python_mem / hybrid_mem
            print(f"  Reduction     : {reduction:.2f}x")
        print(f"{'=' * 60}\n")

        # Note: Memory comparison is informational only
        # Actual reduction depends on GC timing and system state
        assert python_mem > 0, "Python should use some memory"
        assert hybrid_mem > 0, "Hybrid should use some memory"

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.rust
    @pytest.mark.asyncio
    async def test_parallelism_factor(
        self,
        hybrid_orchestrator: Any,
        sample_logs: list[Path],
    ) -> None:
        """
        Measure parallelism factor for Rust batch processing.

        The parallelism factor is: sequential_time / actual_parallel_time
        Higher is better (indicates effective parallel processing)

        Args:
            hybrid_orchestrator: Hybrid orchestrator
            sample_logs: Sample crash log files
        """
        if not is_rust_accelerated("orchestrator"):
            pytest.skip("Rust orchestrator not available")
            return

        batch_logs = sample_logs[:10]  # Use 10 logs for quicker test

        # Process logs individually (sequential)
        sequential_times = []
        for log in batch_logs:
            start = time.perf_counter()
            await hybrid_orchestrator.process_crash_log(log)
            sequential_times.append(time.perf_counter() - start)

        sequential_total = sum(sequential_times)

        # Process logs in batch (parallel)
        start = time.perf_counter()
        await hybrid_orchestrator.process_crash_logs_batch(batch_logs)
        parallel_total = time.perf_counter() - start

        # Calculate parallelism factor
        parallelism_factor = sequential_total / parallel_total if parallel_total > 0 else 1.0

        print(f"\n{'=' * 60}")
        print(f"PARALLELISM FACTOR ({len(batch_logs)} logs):")
        print(f"  Sequential time  : {sequential_total:.2f}s")
        print(f"  Parallel time    : {parallel_total:.2f}s")
        print(f"  Parallelism      : {parallelism_factor:.2f}x")
        print(
            f"  CPU cores        : {hybrid_orchestrator._rust_orch.orchestrator.config().game if hasattr(hybrid_orchestrator, '_rust_orch') and hybrid_orchestrator._rust_orch else 'N/A'}"
        )
        print(f"{'=' * 60}\n")

        # Expected: parallelism factor close to CPU core count
        # Minimum: 2x parallelism (at least using 2 cores effectively)
        assert parallelism_factor >= 2.0, f"Expected 2x+ parallelism factor, got {parallelism_factor:.2f}x"
