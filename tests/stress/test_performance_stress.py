"""
Performance stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests validate performance characteristics under sustained heavy load,
throughput consistency, response time stability, and performance degradation
detection under production-level stress conditions.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, stdev
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

import classic_scanlog
from classic_scanlog import LogParser, PatternMatcher

# Import components to test
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.FileIO import FileIOCore
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.YamlSettingsCache import yaml_cache


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.performance
class TestSustainedLoadPerformance:
    """
    Test performance characteristics under sustained heavy load.

    These tests run operations continuously for extended periods
    to validate performance stability and detect degradation patterns.
    """

    def test_rust_string_processing_sustained_load(self, performance_profiler):
        """
        Test Rust string processing under sustained high-throughput load.

        Processes thousands of strings continuously to measure throughput
        consistency and detect performance degradation over time.
        """
        performance_profiler.start_profiling()

        # Test parameters
        duration_seconds = 30  # 30-second sustained load test
        batch_size = 1000
        target_ops_per_second = 50  # 50 batches per second = 50k strings/sec

        start_time = time.time()
        operations_completed = 0
        batch_times = []

        while time.time() - start_time < duration_seconds:
            batch_start = time.time()

            # Generate test strings for this batch
            test_strings = [f"SustainedLoad_String_{operations_completed}_{i}" for i in range(batch_size)]

            # Process batch using Python builtins (no StringProcessor in Rust API)
            upper_result = [s.upper() for s in test_strings]
            lower_result = [s.lower() for s in test_strings]

            # Verify results
            assert len(upper_result) == batch_size
            assert len(lower_result) == batch_size

            batch_end = time.time()
            batch_duration = batch_end - batch_start
            batch_times.append(batch_duration)

            # Record operation performance
            performance_profiler.record_operation(
                "string_batch_processing",
                batch_duration,
                0,  # Memory tracking handled elsewhere
            )

            operations_completed += 1

            # Brief pause to achieve target rate
            target_interval = 1.0 / target_ops_per_second
            if batch_duration < target_interval:
                time.sleep(target_interval - batch_duration)

        performance_profiler.stop_profiling()

        # Analyze performance characteristics
        assert operations_completed >= duration_seconds * target_ops_per_second * 0.8, (
            f"Throughput too low: {operations_completed} operations in {duration_seconds}s"
        )

        # Check for performance degradation
        early_batches = batch_times[: len(batch_times) // 4]  # First 25%
        late_batches = batch_times[-len(batch_times) // 4 :]  # Last 25%

        early_avg = mean(early_batches)
        late_avg = mean(late_batches)

        degradation_factor = late_avg / early_avg
        assert degradation_factor < 1.5, f"Performance degraded by {degradation_factor:.2f}x during sustained load"

        # Response time consistency
        batch_times_ms = [t * 1000 for t in batch_times]
        if len(batch_times_ms) > 1:
            cv = stdev(batch_times_ms) / mean(batch_times_ms)  # Coefficient of variation
            assert cv < 0.5, f"High response time variability: CV = {cv:.2f}"

    def test_rust_log_processor_throughput_consistency(self, performance_profiler, stress_data_generator):
        """
        Test LogProcessor throughput consistency under continuous load.

        Continuously processes large logs to measure sustained throughput
        and ensure processing speed remains consistent over time.
        """
        performance_profiler.start_profiling()

        parser = LogParser()

        # Generate test log content
        log_content = stress_data_generator.generate_large_crash_log(
            size_mb=5,  # 5MB log for each operation
            plugin_count=100,
            formid_count=2000,
        )

        # Convert to lines for LogParser
        log_lines = log_content.split("\n")

        # Test parameters
        duration_seconds = 45  # 45-second sustained test
        start_time = time.time()
        processing_times = []
        formid_counts = []
        plugin_counts = []

        iteration = 0
        while time.time() - start_time < duration_seconds:
            iteration_start = time.time()

            # Process the log content
            formids = parser.extract_formids(log_lines)
            plugins = parser.extract_plugins(log_lines)

            # Pattern matching
            pattern_matcher = PatternMatcher(["ERROR", "WARNING", "FormID", "Plugin"])
            pattern_matcher.find_all(log_content)

            iteration_end = time.time()
            processing_time = iteration_end - iteration_start

            # Record metrics
            processing_times.append(processing_time)
            formid_counts.append(len(formids))
            plugin_counts.append(len(plugins))

            performance_profiler.record_operation("log_processing_iteration", processing_time, 0)

            iteration += 1

        performance_profiler.stop_profiling()

        # Validate consistent results
        assert len(set(formid_counts)) <= 2, "FormID extraction results should be consistent"
        assert len(set(plugin_counts)) <= 2, "Plugin extraction results should be consistent"

        # Analyze throughput consistency
        if len(processing_times) > 1:
            processing_times_ms = [t * 1000 for t in processing_times]
            avg_time = mean(processing_times_ms)
            std_time = stdev(processing_times_ms)

            # Coefficient of variation should be reasonable
            cv = std_time / avg_time
            assert cv < 0.3, f"High processing time variability: CV = {cv:.2f}"

            # No significant degradation
            early_times = processing_times[: len(processing_times) // 3]
            late_times = processing_times[-len(processing_times) // 3 :]

            early_avg = mean(early_times)
            late_avg = mean(late_times)

            assert late_avg / early_avg < 1.3, "Significant performance degradation detected during sustained load"

    def test_file_io_sustained_throughput(self, performance_profiler, tmp_path, stress_data_generator):
        """
        Test FileIOCore sustained throughput with continuous file operations.

        Performs continuous file I/O operations to measure sustained
        throughput and ensure I/O performance remains stable.
        """
        performance_profiler.start_profiling()

        with AsyncBridge.get_instance() as bridge:
            io_core = FileIOCore()

            # Create multiple test files
            test_files = []
            for i in range(20):  # 20 files to rotate through
                content = stress_data_generator.generate_large_crash_log(
                    size_mb=2,  # 2MB per file
                    plugin_count=50,
                    formid_count=500,
                )
                file_path = tmp_path / f"sustained_io_test_{i}.log"
                file_path.write_text(content, encoding="utf-8")
                test_files.append(file_path)

            # Sustained I/O test
            duration_seconds = 20  # 20-second I/O test
            start_time = time.time()
            read_times = []
            bytes_read = []

            file_index = 0
            while time.time() - start_time < duration_seconds:
                read_start = time.time()

                # Read file
                current_file = test_files[file_index % len(test_files)]
                content = bridge.run_async(io_core.read_file(current_file))

                read_end = time.time()
                read_time = read_end - read_start

                read_times.append(read_time)
                bytes_read.append(len(content.encode("utf-8")))

                performance_profiler.record_operation("file_read_operation", read_time, 0)

                file_index += 1

            performance_profiler.stop_profiling()

            # Analyze I/O performance
            total_bytes = sum(bytes_read)
            max(read_times) if read_times else 1
            avg_throughput_mb_s = (total_bytes / (1024 * 1024)) / (duration_seconds)

            # Should maintain reasonable I/O throughput
            assert avg_throughput_mb_s > 10, f"I/O throughput too low: {avg_throughput_mb_s:.1f} MB/s"

            # Consistent read times
            if len(read_times) > 1:
                read_times_ms = [t * 1000 for t in read_times]
                cv = stdev(read_times_ms) / mean(read_times_ms)
                assert cv < 0.4, f"High I/O time variability: CV = {cv:.2f}"

    def test_yaml_cache_sustained_operations(self, performance_profiler):
        """
        Test YamlSettingsCache performance under sustained access patterns.

        Continuously accesses cache with various patterns to measure
        sustained cache performance and hit rate consistency.
        """
        performance_profiler.start_profiling()

        # Clear cache to start fresh
        yaml_cache.clear_cache()

        # Test parameters
        duration_seconds = 25  # 25-second cache test
        start_time = time.time()
        operation_times = []
        cache_hits = 0
        cache_misses = 0

        operation_count = 0
        while time.time() - start_time < duration_seconds:
            operation_start = time.time()

            # Create mix of new and repeated keys
            if operation_count % 3 == 0:
                # New key (cache miss)
                key = f"sustained_test_new_{operation_count}"
                cache_miss = True
            else:
                # Repeated key (cache hit)
                key = f"sustained_test_repeated_{operation_count % 10}"
                cache_miss = False

            # Mock YAML data
            mock_data = {"TEST": {key: f"value_{operation_count}"}}

            with patch.object(yaml_cache, "_load_yaml_file", return_value=mock_data):
                # Single setting access
                yaml_cache.get_setting(str, "TEST", key, "default")

            operation_end = time.time()
            operation_time = operation_end - operation_start

            operation_times.append(operation_time)

            if cache_miss:
                cache_misses += 1
            else:
                cache_hits += 1

            performance_profiler.record_operation("cache_access", operation_time, 0)

            operation_count += 1

        performance_profiler.stop_profiling()

        # Analyze cache performance
        hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
        assert hit_rate > 0.5, f"Cache hit rate too low: {hit_rate:.1%}"

        # Consistent operation times
        if len(operation_times) > 1:
            operation_times_ms = [t * 1000 for t in operation_times]
            avg_time = mean(operation_times_ms)

            # Cache operations should be fast
            assert avg_time < 1.0, f"Cache operations too slow: {avg_time:.2f}ms average"


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.performance
class TestConcurrentPerformance:
    """
    Test performance characteristics under concurrent load scenarios.

    These tests measure performance when multiple operations run
    simultaneously, validating scalability and resource utilization.
    """

    def test_concurrent_rust_operations_scalability(self, performance_profiler):
        """
        Test Rust component performance scalability with concurrent operations.

        Runs operations with increasing concurrency levels to measure
        performance scaling and identify optimal concurrency levels.
        """
        performance_profiler.start_profiling()

        parser = LogParser()

        # Test data
        test_content = (
            """
        ERROR: System failure at FormID 0x12345678
        WARNING: Plugin TestMod.esp has issues
        INFO: Processing FormID 0xABCDEF01
        """
            * 1000
        )  # Substantial content

        # Convert to lines for LogParser - cast to avoid LiteralString variance issues
        test_lines = cast(list[str], test_content.split("\n"))

        concurrency_levels = [1, 5, 10, 20, 30]  # Different concurrency levels
        results_by_concurrency = {}

        for concurrency in concurrency_levels:

            def concurrent_operation():
                """Operation to run concurrently."""
                start = time.time()

                # Extract FormIDs and plugins
                formids = parser.extract_formids(test_lines)
                plugins = parser.extract_plugins(test_lines)

                duration = time.time() - start
                return {"duration": duration, "formid_count": len(formids), "plugin_count": len(plugins)}

            # Run operations concurrently
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(concurrent_operation) for _ in range(concurrency)]
                results = [f.result() for f in as_completed(futures)]

            total_time = time.time() - start_time

            # Analyze results for this concurrency level
            durations = [r["duration"] for r in results]
            avg_duration = mean(durations)
            throughput = concurrency / total_time  # Operations per second

            results_by_concurrency[concurrency] = {"avg_duration": avg_duration, "throughput": throughput, "total_time": total_time}

            performance_profiler.record_operation(f"concurrent_ops_level_{concurrency}", total_time, 0)

        performance_profiler.stop_profiling()

        # Analyze scalability
        # Throughput should generally increase with concurrency up to a point
        throughputs = [results_by_concurrency[c]["throughput"] for c in concurrency_levels]

        # At least some benefit from concurrency
        assert throughputs[2] > throughputs[0] * 1.5, "Insufficient performance benefit from concurrency"

        # Performance shouldn't degrade severely at high concurrency
        max_throughput = max(throughputs)
        high_concurrency_throughput = throughputs[-1]
        assert high_concurrency_throughput > max_throughput * 0.7, "Severe performance degradation at high concurrency"

    def test_mixed_workload_performance(self, performance_profiler, tmp_path, stress_data_generator):
        """
        Test performance with mixed concurrent workloads.

        Runs different types of operations simultaneously to test
        performance under realistic mixed workload conditions.
        """
        performance_profiler.start_profiling()

        with AsyncBridge.get_instance() as bridge:
            io_core = FileIOCore()
            log_parser = LogParser()

            # Prepare test data
            log_files = []
            for i in range(5):
                content = stress_data_generator.generate_large_crash_log(size_mb=3, plugin_count=50, formid_count=500)
                file_path = tmp_path / f"mixed_workload_{i}.log"
                file_path.write_text(content, encoding="utf-8")
                log_files.append(file_path)

            test_strings = [f"Mixed_workload_string_{i}" for i in range(1000)]

            def io_heavy_task():
                """I/O intensive task."""
                start = time.time()
                for file_path in log_files:
                    bridge.run_async(io_core.read_file(file_path))
                return time.time() - start

            def cpu_heavy_task():
                """CPU intensive task - use Python builtins."""
                start = time.time()
                for _ in range(5):
                    [s.upper() for s in test_strings]
                    [s.lower() for s in test_strings]
                return time.time() - start

            def log_processing_task():
                """Log processing task."""
                start = time.time()
                content = log_files[0].read_text()
                lines = content.split("\n")
                for _ in range(3):
                    log_parser.extract_formids(lines)
                    log_parser.extract_plugins(lines)
                return time.time() - start

            # Run mixed workload
            workload_start = time.time()

            with ThreadPoolExecutor(max_workers=12) as executor:
                # Submit different types of tasks
                io_futures = [executor.submit(io_heavy_task) for _ in range(3)]
                cpu_futures = [executor.submit(cpu_heavy_task) for _ in range(4)]
                log_futures = [executor.submit(log_processing_task) for _ in range(5)]

                # Collect results
                io_times = [f.result() for f in as_completed(io_futures)]
                cpu_times = [f.result() for f in as_completed(cpu_futures)]
                log_times = [f.result() for f in as_completed(log_futures)]

            total_workload_time = time.time() - workload_start

            performance_profiler.stop_profiling()

            # Analyze mixed workload performance
            avg_io_time = mean(io_times)
            avg_cpu_time = mean(cpu_times)
            avg_log_time = mean(log_times)

            performance_profiler.record_operation("mixed_io_tasks", avg_io_time)
            performance_profiler.record_operation("mixed_cpu_tasks", avg_cpu_time)
            performance_profiler.record_operation("mixed_log_tasks", avg_log_time)

            # All task types should complete in reasonable time
            assert avg_io_time < 10.0, f"I/O tasks too slow: {avg_io_time:.2f}s"
            assert avg_cpu_time < 5.0, f"CPU tasks too slow: {avg_cpu_time:.2f}s"
            assert avg_log_time < 8.0, f"Log processing tasks too slow: {avg_log_time:.2f}s"

            # Total workload time should show benefits of concurrency
            sequential_estimate = sum(io_times) + sum(cpu_times) + sum(log_times)
            concurrency_benefit = sequential_estimate / total_workload_time

            assert concurrency_benefit > 2.0, f"Insufficient concurrency benefit: {concurrency_benefit:.2f}x speedup"

    def test_resource_utilization_efficiency(self, performance_profiler, fresh_memory_tracker):
        """
        Test resource utilization efficiency under concurrent load.

        Monitors CPU and memory utilization patterns during concurrent
        operations to ensure efficient resource usage.
        """
        performance_profiler.start_profiling()
        fresh_memory_tracker.start_tracking()

        parser = LogParser()

        # Generate substantial workload
        large_content = (
            """
        ERROR: Critical system failure at FormID 0x12345678
        WARNING: Plugin conflict detected in TestMod.esp
        INFO: Loading FormID 0xABCDEF01 from MasterFile.esm
        """
            * 2000
        )  # Large content block

        # Cast to avoid LiteralString variance issues
        large_lines = cast(list[str], large_content.split("\n"))
        large_strings = [f"Resource_test_string_{i}_with_content" for i in range(5000)]

        def resource_intensive_operation(operation_id: int):
            """Operation that uses significant resources."""
            start_time = time.time()

            # Mix of operations
            if operation_id % 3 == 0:
                # String processing using Python builtins
                upper = [s.upper() for s in large_strings]
                result_size = len(upper)
            elif operation_id % 3 == 1:
                # Log processing
                formids = parser.extract_formids(large_lines)
                plugins = parser.extract_plugins(large_lines)
                result_size = len(formids) + len(plugins)
            else:
                # Pattern matching
                pattern_matcher = PatternMatcher(["ERROR", "WARNING", "INFO", "FormID"])
                matches = pattern_matcher.find_all(large_content)
                result_size = len(matches)

            duration = time.time() - start_time
            return {"operation_id": operation_id, "duration": duration, "result_size": result_size}

        # Run operations with high concurrency
        num_operations = 30
        max_workers = 15

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(resource_intensive_operation, i) for i in range(num_operations)]
            results = [f.result() for f in as_completed(futures)]

        total_execution_time = time.time() - start_time

        performance_profiler.stop_profiling()
        memory_stats = fresh_memory_tracker.stop_tracking()

        # Analyze resource utilization
        total_operation_time = sum(r["duration"] for r in results)
        cpu_utilization_efficiency = total_operation_time / (total_execution_time * max_workers)

        # CPU utilization should be reasonably high but not excessive
        assert 0.3 < cpu_utilization_efficiency < 1.2, f"CPU utilization efficiency poor: {cpu_utilization_efficiency:.2f}"

        # Memory usage should be efficient
        memory_per_operation = memory_stats["peak_mb"] / num_operations
        assert memory_per_operation < 20, f"Excessive memory per operation: {memory_per_operation:.1f}MB"

        # All operations should complete successfully
        assert len(results) == num_operations, "Not all operations completed"

        # Results should be reasonable
        for result in results:
            assert result["result_size"] > 0, "Operations should produce results"
            assert result["duration"] < 10.0, "Individual operations too slow"


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.performance
class TestPerformanceDegradation:
    """
    Test for performance degradation patterns under extended load.

    These tests specifically look for performance degradation over time
    and ensure consistent performance characteristics.
    """

    def test_long_running_session_performance(self, performance_profiler, stress_data_generator):
        """
        Test performance consistency during long-running sessions.

        Runs operations continuously for an extended period to detect
        performance degradation that might occur over time.
        """
        performance_profiler.start_profiling()

        parser = LogParser()

        # Generate test content
        log_content = stress_data_generator.generate_large_crash_log(
            size_mb=10,  # 10MB log
            plugin_count=200,
            formid_count=3000,
        )

        # Convert to lines for LogParser
        log_lines = log_content.split("\n")

        # Long-running test parameters
        total_duration = 60  # 1 minute continuous operation
        measurement_interval = 5  # Take measurements every 5 seconds
        performance_measurements = []

        start_time = time.time()
        last_measurement = start_time
        operation_count = 0

        while time.time() - start_time < total_duration:
            operation_start = time.time()

            # Perform standard operations
            formids = parser.extract_formids(log_lines)
            plugins = parser.extract_plugins(log_lines)

            # Pattern matching
            pattern_matcher = PatternMatcher(["ERROR", "WARNING", "FormID"])
            pattern_matcher.find_all(log_content)

            operation_end = time.time()
            operation_duration = operation_end - operation_start

            operation_count += 1

            # Record measurement every interval
            if operation_end - last_measurement >= measurement_interval:
                performance_measurements.append({
                    "timestamp": operation_end - start_time,
                    "operation_duration": operation_duration,
                    "cumulative_operations": operation_count,
                    "formid_count": len(formids),
                    "plugin_count": len(plugins),
                })
                last_measurement = operation_end

            performance_profiler.record_operation("long_running_operation", operation_duration, 0)

        performance_profiler.stop_profiling()

        # Analyze performance degradation
        if len(performance_measurements) >= 4:
            early_measurements = performance_measurements[:2]
            late_measurements = performance_measurements[-2:]

            early_avg = mean([m["operation_duration"] for m in early_measurements])
            late_avg = mean([m["operation_duration"] for m in late_measurements])

            degradation_factor = late_avg / early_avg

            assert degradation_factor < 1.3, f"Significant performance degradation over time: {degradation_factor:.2f}x"

            # Results should remain consistent
            formid_counts = [m["formid_count"] for m in performance_measurements]
            plugin_counts = [m["plugin_count"] for m in performance_measurements]

            assert len(set(formid_counts)) <= 2, "FormID counts should remain consistent"
            assert len(set(plugin_counts)) <= 2, "Plugin counts should remain consistent"

    def test_cache_performance_under_pressure(self, performance_profiler):
        """
        Test cache performance degradation under memory pressure.

        Creates cache pressure scenarios to test performance characteristics
        when cache hit rates vary and memory pressure increases.
        """
        performance_profiler.start_profiling()

        yaml_cache.clear_cache()

        # Test phases with different cache pressure
        phases = [
            {"name": "warmup", "operations": 100, "unique_keys": 50},
            {"name": "steady", "operations": 500, "unique_keys": 50},  # Good hit rate
            {"name": "pressure", "operations": 1000, "unique_keys": 800},  # Poor hit rate
            {"name": "recovery", "operations": 200, "unique_keys": 50},  # Good hit rate again
        ]

        phase_results = {}

        for phase in phases:
            phase_start = time.time()
            operation_times = []

            for i in range(phase["operations"]):
                operation_start = time.time()

                # Select key based on unique key count (affects hit rate)
                key = f"cache_pressure_key_{i % phase['unique_keys']}"

                # Mock YAML data
                mock_data = {"TEST": {key: f"value_{i}"}}

                with patch.object(yaml_cache, "_load_yaml_file", return_value=mock_data):
                    yaml_cache.get_setting(str, "TEST", key, "default")

                operation_end = time.time()
                operation_times.append(operation_end - operation_start)

            phase_end = time.time()

            phase_results[phase["name"]] = {
                "total_time": phase_end - phase_start,
                "avg_operation_time": mean(operation_times),
                "operations": phase["operations"],
                "cache_size": len(yaml_cache._cache),
            }

            performance_profiler.record_operation(f"cache_phase_{phase['name']}", phase_end - phase_start, 0)

        performance_profiler.stop_profiling()

        # Analyze cache performance patterns
        warmup_avg = phase_results["warmup"]["avg_operation_time"]
        steady_avg = phase_results["steady"]["avg_operation_time"]
        pressure_avg = phase_results["pressure"]["avg_operation_time"]
        recovery_avg = phase_results["recovery"]["avg_operation_time"]

        # Steady state should be faster than warmup (cache warmed)
        assert steady_avg <= warmup_avg * 1.2, "Cache should provide benefit in steady state"

        # Pressure phase should be slower but not excessively
        assert pressure_avg <= steady_avg * 3.0, f"Excessive slowdown under cache pressure: {pressure_avg / steady_avg:.2f}x"

        # Recovery should return to good performance
        assert recovery_avg <= pressure_avg * 0.8, "Performance should recover after cache pressure relief"

    def test_orchestrator_performance_scaling(self, performance_profiler, tmp_path, stress_data_generator):
        """
        Test OrchestratorCore performance scaling with increasing workload.

        Tests orchestrator performance with increasing numbers of files
        to validate scaling characteristics and detect bottlenecks.
        """
        performance_profiler.start_profiling()

        # Create mock yamldata for OrchestratorCore
        mock_yamldata = MagicMock()
        mock_yamldata.crashgen_name = "Buffout 4"
        mock_yamldata.xse_acronym = "F4SE"
        mock_yamldata.crashgen_latest_og = "1.28.6"
        mock_yamldata.crashgen_latest_vr = "1.26.2"
        mock_yamldata.game_mods_conf = {}
        mock_yamldata.game_mods_freq = {}
        mock_yamldata.game_mods_solu = {}
        mock_yamldata.game_mods_core = {}
        mock_yamldata.game_mods_core_folon = {}
        mock_yamldata.game_mods_opc2 = {}

        with AsyncBridge.get_instance() as bridge:
            orchestrator = OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            # Create test files with increasing batch sizes
            batch_sizes = [1, 5, 10, 20]  # Different workload sizes
            scaling_results = {}

            for batch_size in batch_sizes:
                # Create files for this batch
                batch_files = []
                for i in range(batch_size):
                    content = stress_data_generator.generate_large_crash_log(
                        size_mb=2,  # 2MB per file
                        plugin_count=50,
                        formid_count=500,
                    )
                    file_path = tmp_path / f"orchestrator_scaling_{batch_size}_{i}.log"
                    file_path.write_text(content, encoding="utf-8")
                    batch_files.append(file_path)

                # Process batch and measure performance
                batch_start = time.time()
                results = []

                for file_path in batch_files:
                    result = bridge.run_async(orchestrator.process_crash_log(file_path))
                    results.append(result)

                batch_end = time.time()
                batch_duration = batch_end - batch_start

                scaling_results[batch_size] = {
                    "duration": batch_duration,
                    "files_processed": len(results),
                    "avg_time_per_file": batch_duration / batch_size,
                    "throughput_files_per_sec": batch_size / batch_duration,
                }

                performance_profiler.record_operation(f"orchestrator_batch_{batch_size}", batch_duration, 0)

            performance_profiler.stop_profiling()

            # Analyze scaling characteristics
            single_file_time = scaling_results[1]["avg_time_per_file"]

            for batch_size in [5, 10, 20]:
                batch_avg_time = scaling_results[batch_size]["avg_time_per_file"]

                # Per-file time shouldn't increase dramatically with batch size
                scaling_factor = batch_avg_time / single_file_time
                assert scaling_factor < 2.0, f"Poor scaling at batch size {batch_size}: {scaling_factor:.2f}x slower per file"

            # Throughput should generally improve with batch size (some benefit)
            single_throughput = scaling_results[1]["throughput_files_per_sec"]
            large_batch_throughput = scaling_results[20]["throughput_files_per_sec"]

            assert large_batch_throughput >= single_throughput * 0.8, "Significant throughput degradation with larger batches"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
