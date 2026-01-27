"""Stress testing for concurrent operations.

This module tests concurrent log parsing, mixed operations, and sustained load
scenarios to validate system performance under parallel workloads.
"""

import asyncio
import random
import tempfile
import time
from pathlib import Path

import pytest

from tests.fixtures.stress_fixtures import StressTestMetrics, SyntheticWorkloadGenerator

# Mark all tests in this module
pytestmark = [pytest.mark.stress, pytest.mark.slow]


class TestConcurrentOperationsStress:
    """Stress test concurrent operations."""

    @pytest.fixture
    def metrics(self):
        return StressTestMetrics()

    @pytest.fixture
    def generator(self):
        return SyntheticWorkloadGenerator()

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_concurrent_log_parsing_stress(self, metrics, generator):
        """Stress test concurrent parsing of multiple logs."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()

        # Generate 20 typical crash logs
        logs = [generator.generate_typical_crash_log() for _ in range(20)]

        async def parse_log(log: str, index: int):
            """Parse a single log."""
            start = time.time()
            try:
                lines = log.splitlines()
                game_ver, crashgen_ver, error, segments = await asyncio.to_thread(
                    parser.find_segments, lines, "Buffout 4", "F4SE", "Fallout4.exe"
                )
                metrics.record_operation(time.time() - start)
                return segments
            except Exception as e:
                metrics.record_error(e)
                raise

        # Parse all logs concurrently
        tasks = [parse_log(log, i) for i, log in enumerate(logs)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Update metrics
        metrics.update_memory()
        metrics.update_threads()

        # Analyze results
        summary = metrics.get_summary()
        print("\nConcurrent Parsing Stress Test:")
        print(f"  Operations: {summary['operations']}")
        print(f"  Throughput: {summary['ops_per_second']:.2f} ops/sec")
        print(f"  Avg Response: {summary['avg_response_time'] * 1000:.1f}ms")
        print(f"  Peak Memory: {summary['peak_memory_mb']:.1f}MB")
        print(f"  Errors: {summary['errors']}")

        # Assertions
        assert summary["errors"] == 0, f"Errors during concurrent parsing: {metrics.errors_encountered}"
        assert summary["operations"] == 20
        assert summary["avg_response_time"] < 2.0, "Parsing too slow under load"
        assert summary["peak_memory_mb"] < 500, "Excessive memory usage"

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_mixed_operations_stress(self, metrics, generator, mock_yamldata_python_only):
        """Stress test with mixed operation types."""
        from ClassicLib.integration.factory import get_formid_analyzer, get_parser
        from ClassicLib.io.files import FileIOCore

        parser = get_parser()
        analyzer = get_formid_analyzer(mock_yamldata_python_only, True, False)
        io_core = FileIOCore()

        # Generate test data
        log = generator.generate_typical_crash_log()
        formids = [f"{random.randint(0, 255):02X}{random.randint(1, 0xFFFFFF):06X}" for _ in range(100)]

        async def mixed_operations():
            """Perform mixed operations."""
            operations = []

            # Parse log
            log_lines = log.splitlines()
            operations.append(asyncio.to_thread(parser.find_segments, log_lines, "Buffout 4", "F4SE", "Fallout4.exe"))

            # Analyze FormIDs - use extract_formids instead of analyze for batch
            operations.append(asyncio.to_thread(analyzer.extract_formids, formids[:10]))

            start = time.time()

            # Execute parse/analyze operations first
            results1 = await asyncio.gather(*operations, return_exceptions=True)

            # File operations - run inside temp directory context
            file_results = []
            with tempfile.TemporaryDirectory() as temp_dir:
                file_operations = []
                for i in range(5):
                    file_path = Path(temp_dir) / f"test_{i}.log"
                    # Write first, then read (in sequence per file)
                    file_operations.append(io_core.write_file(str(file_path), f"Content {i}"))
                # Execute writes
                write_results = await asyncio.gather(*file_operations, return_exceptions=True)
                file_results.extend(write_results)

                # Now execute reads
                read_operations = []
                for i in range(5):
                    file_path = Path(temp_dir) / f"test_{i}.log"
                    read_operations.append(io_core.read_file(str(file_path)))
                read_results = await asyncio.gather(*read_operations, return_exceptions=True)
                file_results.extend(read_results)

            duration = time.time() - start

            # Combine results
            all_results = list(results1) + file_results

            # Count successes and failures
            successes = sum(1 for r in all_results if not isinstance(r, Exception))
            failures = sum(1 for r in all_results if isinstance(r, Exception))

            return successes, failures, duration

        # Run multiple rounds
        total_successes = 0
        total_failures = 0

        for _round_num in range(5):
            successes, failures, duration = await mixed_operations()
            total_successes += successes
            total_failures += failures
            metrics.record_operation(duration)
            metrics.update_memory()
            metrics.update_threads()

        # Summary
        summary = metrics.get_summary()
        print("\nMixed Operations Stress Test:")
        print(f"  Total Operations: {total_successes + total_failures}")
        print(f"  Successes: {total_successes}")
        print(f"  Failures: {total_failures}")
        print(f"  Success Rate: {total_successes / (total_successes + total_failures) * 100:.1f}%")
        print(f"  Peak Memory: {summary['peak_memory_mb']:.1f}MB")

        # Assertions
        assert total_failures == 0 or total_failures < total_successes * 0.01  # <1% failure rate
        assert summary["peak_memory_mb"] < 500

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_sustained_load_stress(self, metrics, generator):
        """Test sustained load over extended period."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()
        stop_event = asyncio.Event()

        async def continuous_parsing():
            """Continuously parse logs until stopped."""
            while not stop_event.is_set():
                log = generator.generate_typical_crash_log()
                start = time.time()
                try:
                    lines = log.splitlines()
                    await asyncio.to_thread(parser.find_segments, lines, "Buffout 4", "F4SE", "Fallout4.exe")
                    metrics.record_operation(time.time() - start)
                except Exception as e:
                    metrics.record_error(e)
                await asyncio.sleep(0.01)  # Small delay between operations

        # Run for 10 seconds
        task = asyncio.create_task(continuous_parsing())
        await asyncio.sleep(10)
        stop_event.set()
        await task

        # Check metrics
        metrics.update_memory()
        summary = metrics.get_summary()

        print("\nSustained Load Stress Test (10 seconds):")
        print(f"  Operations: {summary['operations']}")
        print(f"  Throughput: {summary['ops_per_second']:.2f} ops/sec")
        print(f"  Error Rate: {summary['error_rate'] * 100:.2f}%")
        print(f"  Peak Memory: {summary['peak_memory_mb']:.1f}MB")

        # Assertions
        assert summary["ops_per_second"] > 5, "Throughput too low"
        assert summary["error_rate"] < 0.01, "Error rate too high"
        assert summary["peak_memory_mb"] < 500, "Memory usage too high"
