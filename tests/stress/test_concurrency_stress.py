"""
Concurrency stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests validate thread safety, race condition handling, and concurrent
operation stability under high-contention scenarios that simulate
production-level concurrent usage patterns.
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from threading import Barrier, Lock, Event
from unittest.mock import Mock, patch

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_core", reason="Rust extensions not available")

import classic_core
from .stress_test_fixtures import (
    ConcurrencyTestHelper,
    MemoryTracker,
    PerformanceProfiler
)

# Import components to test
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.FileIOCore import FileIOCore
from ClassicLib.GlobalRegistry import GlobalRegistry
from ClassicLib.MessageHandler.MessageHandler import MessageHandler
from ClassicLib.YamlSettingsCache import yaml_cache


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.concurrency
class TestThreadSafetyValidation:
    """
    Test thread safety of core components under high concurrency.

    These tests create high-contention scenarios with many threads
    accessing shared resources simultaneously to detect race conditions
    and ensure thread safety guarantees are maintained.
    """

    def test_rust_string_processor_thread_safety(self, concurrency_helper):
        """
        Test Rust StringProcessor thread safety under concurrent access.

        Multiple threads simultaneously use the same StringProcessor
        instance to ensure thread-safe operations and consistent results.
        """
        from classic_core.utils import StringProcessor
        processor = StringProcessor()

        def concurrent_string_operation(thread_id: int, iteration: int, shared_data: list):
            """Worker function for concurrent string processing."""
            test_strings = [f"Thread_{thread_id}_String_{iteration}_{i}" for i in range(10)]

            # Intern strings (tests internal cache thread safety)
            interned = [processor.intern(s) for s in test_strings]

            # Batch process strings
            upper_result = processor.process_batch(test_strings, "upper")
            lower_result = processor.process_batch(test_strings, "lower")

            # Store results in shared data for validation
            shared_data.append({
                'thread_id': thread_id,
                'iteration': iteration,
                'upper_count': len(upper_result),
                'lower_count': len(lower_result),
                'interned_count': len(interned)
            })

            return len(upper_result)  # Return processed count

        # Run concurrent operations
        shared_results = []
        results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_string_operation,
            num_threads=30,
            iterations_per_thread=50,
            shared_data=shared_results
        )

        # Validate no errors occurred
        assert len(results["errors"]) == 0, f"Thread safety errors: {results['errors']}"

        # Validate all operations completed successfully
        expected_operations = 30 * 50  # 30 threads * 50 iterations
        assert results["total_operations"] == expected_operations

        # Validate shared results consistency
        assert len(shared_results) == expected_operations
        for result in shared_results:
            assert result["upper_count"] == 10  # Should process all 10 strings
            assert result["lower_count"] == 10
            assert result["interned_count"] == 10

    def test_rust_log_processor_concurrent_pattern_matching(self, concurrency_helper, tmp_path):
        """
        Test LogProcessor pattern matching thread safety.

        Multiple threads perform pattern matching operations on the same
        processor to ensure internal state management is thread-safe.
        """
        from classic_core.utils import LogProcessor
        processor = LogProcessor()
        patterns = ["ERROR", "WARNING", "INFO", "FormID", "Plugin"]

        # Initialize pattern matcher once
        processor.init_pattern_matcher(patterns)

        # Create test log content
        test_log = """
        ERROR: System failure at 0x12345678
        WARNING: Low memory condition
        INFO: Processing started
        FormID: 0xABCDEF01 found in plugin
        Plugin: TestMod.esp loaded successfully
        ERROR: Another error occurred
        """ * 20  # Multiply to create substantial content

        def concurrent_pattern_matching(thread_id: int, iteration: int, shared_data: dict):
            """Worker function for concurrent pattern matching."""
            # Find all patterns in the log
            matches = processor.find_all_patterns(test_log, patterns)

            # Extract FormIDs
            formids = processor.extract_formids(test_log)

            # Extract plugins
            plugins = processor.extract_plugins(test_log)

            # Track results
            with threading.Lock():
                if 'match_counts' not in shared_data:
                    shared_data['match_counts'] = []
                if 'formid_counts' not in shared_data:
                    shared_data['formid_counts'] = []
                if 'plugin_counts' not in shared_data:
                    shared_data['plugin_counts'] = []

                shared_data['match_counts'].append(len(matches))
                shared_data['formid_counts'].append(len(formids))
                shared_data['plugin_counts'].append(len(plugins))

            return len(matches)

        shared_state = {}
        results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_pattern_matching,
            num_threads=25,
            iterations_per_thread=40,
            shared_data=shared_state
        )

        # Validate no threading errors
        assert len(results["errors"]) == 0, f"Pattern matching thread safety errors: {results['errors']}"

        # All operations should return consistent results
        match_counts = shared_state.get('match_counts', [])
        formid_counts = shared_state.get('formid_counts', [])
        plugin_counts = shared_state.get('plugin_counts', [])

        # All counts should be consistent across threads
        assert len(set(match_counts)) <= 2, "Pattern match counts should be consistent across threads"
        assert len(set(formid_counts)) <= 2, "FormID counts should be consistent across threads"
        assert len(set(plugin_counts)) <= 2, "Plugin counts should be consistent across threads"

    def test_async_bridge_concurrent_access(self, concurrency_helper):
        """
        Test AsyncBridge thread safety with concurrent async operations.

        Multiple threads simultaneously use AsyncBridge to run async
        operations, testing the thread-local event loop management.
        """
        bridge = AsyncBridge.get_instance()

        async def async_operation(duration: float, data: str):
            """Simple async operation for testing."""
            await asyncio.sleep(duration)
            return f"Processed: {data}"

        def concurrent_bridge_operation(thread_id: int, iteration: int, shared_data: list):
            """Worker function using AsyncBridge concurrently."""
            # Each thread runs its own async operation
            data = f"Thread_{thread_id}_Iter_{iteration}"
            result = bridge.run_async(async_operation(0.01, data))  # 10ms operation

            shared_data.append({
                'thread_id': thread_id,
                'iteration': iteration,
                'result': result,
                'success': result.startswith("Processed:")
            })

            return 1 if result.startswith("Processed:") else 0

        shared_results = []
        results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_bridge_operation,
            num_threads=20,
            iterations_per_thread=25,
            shared_data=shared_results
        )

        # Validate no async bridge errors
        assert len(results["errors"]) == 0, f"AsyncBridge thread safety errors: {results['errors']}"

        # All operations should succeed
        success_count = sum(1 for r in shared_results if r['success'])
        expected_count = 20 * 25  # 20 threads * 25 iterations
        assert success_count == expected_count, f"Expected {expected_count} successes, got {success_count}"

    def test_yaml_cache_concurrent_access(self, concurrency_helper):
        """
        Test YamlSettingsCache thread safety with concurrent cache operations.

        Multiple threads simultaneously access the YAML cache to ensure
        cache consistency and thread safety under high contention.
        """
        # Clear cache to start fresh
        yaml_cache.clear_cache()

        def concurrent_cache_operation(thread_id: int, iteration: int, shared_data: dict):
            """Worker function for concurrent cache access."""
            # Create unique keys for each thread/iteration
            keys = [
                (str, "TEST", f"thread_{thread_id}_key_{iteration}_{i}", f"value_{i}")
                for i in range(5)
            ]

            # Mock the YAML file loading to return consistent data
            mock_data = {"TEST": {f"thread_{thread_id}_key_{iteration}_{i}": f"value_{i}" for i in range(5)}}

            with patch.object(yaml_cache, '_load_yaml_file', return_value=mock_data):
                # Batch get settings (this will create cache entries)
                results = yaml_cache.batch_get_settings(keys)

            # Track successful operations
            with threading.Lock():
                if 'successful_operations' not in shared_data:
                    shared_data['successful_operations'] = 0
                if 'cache_sizes' not in shared_data:
                    shared_data['cache_sizes'] = []

                if len(results) == 5:
                    shared_data['successful_operations'] += 1

                # Record cache size
                shared_data['cache_sizes'].append(len(yaml_cache._cache))

            return len(results)

        shared_state = {}
        results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_cache_operation,
            num_threads=15,
            iterations_per_thread=30,
            shared_data=shared_state
        )

        # Validate no cache-related errors
        assert len(results["errors"]) == 0, f"YAML cache thread safety errors: {results['errors']}"

        # Most operations should succeed
        successful_ops = shared_state.get('successful_operations', 0)
        expected_ops = 15 * 30
        assert successful_ops >= expected_ops * 0.9, \
            f"Too many cache operation failures: {successful_ops}/{expected_ops}"


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.concurrency
class TestRaceConditionDetection:
    """
    Test for race conditions in shared resources and state management.

    These tests specifically look for race conditions by running operations
    in patterns designed to expose timing-dependent bugs.
    """

    def test_global_registry_race_conditions(self, concurrency_helper):
        """
        Test GlobalRegistry for race conditions during concurrent access.

        Multiple threads simultaneously register and access components
        to detect race conditions in the singleton registry pattern.
        """
        # Clear registry to start fresh
        GlobalRegistry.clear()

        def register_and_access_operation(shared_state: dict):
            """Operation that registers and accesses registry entries."""
            component_name = f"TestComponent_{threading.current_thread().ident}"

            # Register a mock component
            component = Mock()
            component.name = component_name
            GlobalRegistry.register(component_name, component)

            # Access the component
            retrieved = GlobalRegistry.get(component_name)

            # Modify shared state
            shared_state['counter'] = shared_state.get('counter', 0) + 1
            shared_state['data'].append(component_name)

        operations = [register_and_access_operation] * 10  # 10 concurrent operations

        race_results = concurrency_helper.detect_race_conditions(
            operations=operations,
            num_iterations=200  # 200 iterations to catch intermittent issues
        )

        # Should have minimal race conditions (< 5% rate)
        assert race_results["race_condition_rate"] < 0.05, \
            f"High race condition rate: {race_results['race_condition_rate']:.2%}"

        # Clean up
        GlobalRegistry.clear()

    def test_message_handler_concurrent_logging(self, concurrency_helper):
        """
        Test MessageHandler thread safety during concurrent logging.

        Multiple threads log messages simultaneously to ensure
        message ordering and consistency under concurrent access.
        """
        # Create fresh message handler
        handler = MessageHandler()
        message_queue = Queue()

        def concurrent_logging_operation(thread_id: int, iteration: int, shared_data: list):
            """Worker function for concurrent message logging."""
            messages = [
                f"INFO: Thread {thread_id} iteration {iteration} message {i}"
                for i in range(5)
            ]

            for message in messages:
                handler.msg_info(message)
                shared_data.append(message)

            return len(messages)

        shared_messages = []
        results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_logging_operation,
            num_threads=20,
            iterations_per_thread=10,
            shared_data=shared_messages
        )

        # Validate no message handler errors
        assert len(results["errors"]) == 0, f"MessageHandler thread safety errors: {results['errors']}"

        # All messages should be recorded
        expected_message_count = 20 * 10 * 5  # 20 threads * 10 iterations * 5 messages
        assert len(shared_messages) == expected_message_count

    def test_file_io_concurrent_access_patterns(self, concurrency_helper, tmp_path):
        """
        Test FileIOCore race conditions during concurrent file operations.

        Multiple threads perform file I/O operations simultaneously
        to ensure no race conditions in file handle management.
        """
        bridge = AsyncBridge.get_instance()
        io_core = FileIOCore()

        # Create test files
        test_files = []
        for i in range(10):
            file_path = tmp_path / f"concurrent_test_{i}.txt"
            file_path.write_text(f"Test content for file {i}")
            test_files.append(file_path)

        def concurrent_file_operation(thread_id: int, iteration: int, shared_data: list):
            """Worker function for concurrent file I/O."""
            # Each thread reads from a different file
            file_index = (thread_id + iteration) % len(test_files)
            file_path = test_files[file_index]

            try:
                # Read file content
                content = bridge.run_async(io_core.read_file(file_path))

                # Validate content
                expected = f"Test content for file {file_index}"
                success = content.strip() == expected

                shared_data.append({
                    'thread_id': thread_id,
                    'file_index': file_index,
                    'success': success,
                    'content_length': len(content)
                })

                return 1 if success else 0

            except Exception as e:
                shared_data.append({
                    'thread_id': thread_id,
                    'file_index': file_index,
                    'success': False,
                    'error': str(e)
                })
                return 0

        shared_results = []
        results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_file_operation,
            num_threads=25,
            iterations_per_thread=20,
            shared_data=shared_results
        )

        # Validate minimal file I/O errors
        assert len(results["errors"]) < results["total_operations"] * 0.05, \
            "Too many file I/O errors during concurrent access"

        # Most file operations should succeed
        success_count = sum(1 for r in shared_results if r.get('success', False))
        expected_count = 25 * 20
        assert success_count >= expected_count * 0.95, \
            f"File I/O success rate too low: {success_count}/{expected_count}"


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.concurrency
class TestHighContentionScenarios:
    """
    Test system behavior under extremely high contention scenarios.

    These tests create maximum contention on shared resources to
    validate behavior under the most stressful concurrent conditions.
    """

    def test_database_pool_exhaustion_simulation(self, concurrency_helper, failing_database_pool):
        """
        Test database connection pool behavior under exhaustion conditions.

        Simulates database connection pool exhaustion with many concurrent
        requests to ensure graceful handling of resource limits.
        """
        pool = failing_database_pool  # Fails after 100 operations
        operation_lock = Lock()
        successful_operations = []
        failed_operations = []

        def database_operation(thread_id: int, iteration: int, shared_data: None):
            """Worker function that uses database pool."""
            try:
                result = pool.execute_query(f"SELECT * FROM test WHERE thread={thread_id}")
                with operation_lock:
                    successful_operations.append((thread_id, iteration))
                return 1
            except Exception as e:
                with operation_lock:
                    failed_operations.append((thread_id, iteration, str(e)))
                return 0

        results = concurrency_helper.create_contention_scenario(
            target_func=database_operation,
            num_threads=50,  # More threads than pool capacity
            iterations_per_thread=5,
            shared_data=None
        )

        # Should have some successful operations (before exhaustion)
        assert len(successful_operations) > 50, "Should have some successful database operations"

        # Should have failed operations due to exhaustion
        assert len(failed_operations) > 0, "Should have failed operations due to pool exhaustion"

        # Combined operations should equal total attempts
        total_operations = len(successful_operations) + len(failed_operations)
        assert total_operations == 50 * 5, f"Operation count mismatch: {total_operations}"

    def test_thread_pool_saturation(self, concurrency_helper):
        """
        Test behavior when thread pool becomes saturated.

        Creates more concurrent operations than available threads
        to test queuing and resource management behavior.
        """
        max_workers = 10  # Limited thread pool
        barrier = Barrier(max_workers + 5)  # More operations than workers
        operation_times = []
        time_lock = Lock()

        def saturating_operation(thread_id: int, iteration: int, shared_data: None):
            """Operation that waits for barrier, saturating thread pool."""
            start_time = time.time()

            try:
                # Wait for barrier - this will block until all threads reach this point
                barrier.wait(timeout=30)  # 30 second timeout
                operation_time = time.time() - start_time

                with time_lock:
                    operation_times.append(operation_time)

                return operation_time
            except Exception as e:
                return -1  # Indicate failure

        # Use ThreadPoolExecutor to simulate thread pool saturation
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            # Submit more tasks than available workers
            for i in range(max_workers + 5):
                future = executor.submit(saturating_operation, i, 0, None)
                futures.append(future)

            # Wait for completion
            results = []
            for future in as_completed(futures, timeout=60):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(-1)

        total_time = time.time() - start_time

        # All operations should eventually complete
        successful_operations = [r for r in results if r >= 0]
        assert len(successful_operations) >= max_workers, \
            f"Expected at least {max_workers} successful operations, got {len(successful_operations)}"

        # Total time should be reasonable (not stuck indefinitely)
        assert total_time < 120, f"Thread pool saturation took too long: {total_time:.1f}s"

    def test_rust_component_under_extreme_load(self, concurrency_helper, stress_data_generator):
        """
        Test Rust components under extreme concurrent load.

        Creates maximum concurrent load on Rust components to test
        stability and performance under extreme stress conditions.
        """
        from classic_core.utils import LogProcessor
        processor = LogProcessor()

        # Generate challenging test data
        large_log_content = stress_data_generator.generate_large_crash_log(
            size_mb=5,  # 5MB per operation
            plugin_count=100,
            formid_count=1000
        )

        results_lock = Lock()
        processing_results = {
            'formid_counts': [],
            'plugin_counts': [],
            'processing_times': [],
            'errors': []
        }

        def extreme_load_operation(thread_id: int, iteration: int, shared_data: None):
            """Worker function for extreme load testing."""
            start_time = time.time()

            try:
                # Perform multiple operations per thread
                formids = processor.extract_formids(large_log_content)
                plugins = processor.extract_plugins(large_log_content)

                # Pattern matching
                patterns = ["ERROR", "WARNING", "FormID"]
                matches = processor.find_all_patterns(large_log_content, patterns)

                processing_time = time.time() - start_time

                with results_lock:
                    processing_results['formid_counts'].append(len(formids))
                    processing_results['plugin_counts'].append(len(plugins))
                    processing_results['processing_times'].append(processing_time)

                return processing_time

            except Exception as e:
                with results_lock:
                    processing_results['errors'].append(str(e))
                return -1

        results = concurrency_helper.create_contention_scenario(
            target_func=extreme_load_operation,
            num_threads=40,  # High thread count
            iterations_per_thread=10,  # Multiple operations per thread
            shared_data=None
        )

        # Most operations should succeed even under extreme load
        total_expected = 40 * 10
        error_count = len(processing_results['errors'])
        success_rate = (total_expected - error_count) / total_expected

        assert success_rate > 0.9, f"Success rate too low under extreme load: {success_rate:.1%}"

        # Results should be consistent across threads
        formid_counts = processing_results['formid_counts']
        if formid_counts:
            # All successful operations should find similar numbers of FormIDs
            avg_formids = sum(formid_counts) / len(formid_counts)
            assert avg_formids > 100, f"Expected significant FormIDs, got avg {avg_formids}"

        # Performance should remain reasonable even under load
        processing_times = processing_results['processing_times']
        if processing_times:
            avg_time = sum(processing_times) / len(processing_times)
            assert avg_time < 5.0, f"Average processing time too high: {avg_time:.2f}s"

    def test_memory_allocation_contention(self, concurrency_helper, fresh_memory_tracker):
        """
        Test memory allocation patterns under high concurrency.

        Multiple threads allocate and deallocate memory simultaneously
        to test memory management under concurrent pressure.
        """
        fresh_memory_tracker.start_tracking()

        allocation_lock = Lock()
        allocation_stats = {
            'successful_allocations': 0,
            'failed_allocations': 0,
            'peak_allocations': 0
        }

        def concurrent_memory_operation(thread_id: int, iteration: int, shared_data: None):
            """Worker function for concurrent memory allocation."""
            try:
                # Allocate memory for large string processing
                large_strings = [f"Thread_{thread_id}_String_{iteration}_{i}" * 1000
                               for i in range(100)]  # ~100KB per thread

                # Process with Rust components (internal memory allocation)
                from classic_core.utils import StringProcessor
                processor = StringProcessor()
                processed = processor.process_batch(large_strings, "upper")

                # Track allocation success
                with allocation_lock:
                    allocation_stats['successful_allocations'] += 1

                # Clean up
                del large_strings, processed

                return 1

            except MemoryError:
                with allocation_lock:
                    allocation_stats['failed_allocations'] += 1
                return 0

        # Take memory measurement before stress
        fresh_memory_tracker.take_measurement("before_stress")

        results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_memory_operation,
            num_threads=30,
            iterations_per_thread=20,
            shared_data=None
        )

        # Take measurement after stress
        fresh_memory_tracker.take_measurement("after_stress")

        memory_stats = fresh_memory_tracker.stop_tracking()

        # Most allocations should succeed
        successful = allocation_stats['successful_allocations']
        total_expected = 30 * 20
        success_rate = successful / total_expected

        assert success_rate > 0.95, f"Memory allocation success rate too low: {success_rate:.1%}"

        # Memory growth should be reasonable
        assert memory_stats["growth_mb"] < 200, \
            f"Excessive memory growth during concurrent allocation: {memory_stats['growth_mb']:.1f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
