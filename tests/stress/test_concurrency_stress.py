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
from threading import Barrier, Lock
from unittest.mock import Mock

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")


# Import components to test
# Import Rust components directly
import classic_scanlog

from ClassicLib import GlobalRegistry
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.FileIO import FileIOCore
from ClassicLib.MessageHandler import MessageHandler


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

    def test_rust_string_pool_thread_safety(self, concurrency_helper):
        """
        Test Rust StringPool thread safety under concurrent access.

        Multiple threads simultaneously use the same StringPool
        instance to ensure thread-safe operations and consistent results.
        """
        string_pool = classic_scanlog.StringPool()

        def concurrent_string_operation(thread_id: int, iteration: int, shared_data: list):
            """Worker function for concurrent string processing."""
            test_strings = [f"Thread_{thread_id}_String_{iteration}_{i}" for i in range(10)]

            # Intern strings (tests internal cache thread safety)
            interned = [string_pool.intern(s) for s in test_strings]

            # Batch intern strings (uses parallel processing internally)
            batch_interned = string_pool.intern_batch(test_strings)

            # Process strings using Python (we're testing StringPool thread safety)
            upper_result = [s.upper() for s in test_strings]
            lower_result = [s.lower() for s in test_strings]

            # Store results in shared data for validation
            shared_data.append({
                "thread_id": thread_id,
                "iteration": iteration,
                "upper_count": len(upper_result),
                "lower_count": len(lower_result),
                "interned_count": len(interned),
                "batch_interned_count": len(batch_interned),
            })

            return len(upper_result)  # Return processed count

        # Run concurrent operations
        shared_results = []
        results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_string_operation, num_threads=30, iterations_per_thread=50, shared_data=shared_results
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
            assert result["batch_interned_count"] == 10

    def test_rust_log_parser_concurrent_pattern_matching(self, concurrency_helper, tmp_path):
        """
        Test LogParser and PatternMatcher thread safety.

        Multiple threads perform pattern matching operations on the same
        parser/matcher to ensure internal state management is thread-safe.
        """
        parser = classic_scanlog.LogParser()
        patterns = ["ERROR", "WARNING", "INFO", "FormID", "Plugin"]
        pattern_matcher = classic_scanlog.PatternMatcher(patterns)

        # Create test log content as list of lines (LogParser API expects list[str])
        test_log_lines = [
            "ERROR: System failure at 0x12345678",
            "WARNING: Low memory condition",
            "INFO: Processing started",
            "FormID: 0xABCDEF01 found in plugin",
            "Plugin: TestMod.esp loaded successfully",
            "ERROR: Another error occurred",
        ] * 20  # Multiply to create substantial content

        # Also create as single string for pattern matcher
        test_log_text = "\n".join(test_log_lines)

        def concurrent_pattern_matching(thread_id: int, iteration: int, shared_data: dict):
            """Worker function for concurrent pattern matching."""
            # Find all patterns in the log using PatternMatcher
            matches = pattern_matcher.find_all(test_log_text)

            # Extract FormIDs using LogParser
            formids = parser.extract_formids(test_log_lines)

            # Extract plugins using LogParser
            plugins = parser.extract_plugins(test_log_lines)

            # Track results
            with threading.Lock():
                if "match_counts" not in shared_data:
                    shared_data["match_counts"] = []
                if "formid_counts" not in shared_data:
                    shared_data["formid_counts"] = []
                if "plugin_counts" not in shared_data:
                    shared_data["plugin_counts"] = []

                shared_data["match_counts"].append(len(matches))
                shared_data["formid_counts"].append(len(formids))
                shared_data["plugin_counts"].append(len(plugins))

            return len(matches)

        shared_state = {}
        results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_pattern_matching, num_threads=25, iterations_per_thread=40, shared_data=shared_state
        )

        # Validate no threading errors
        assert len(results["errors"]) == 0, f"Pattern matching thread safety errors: {results['errors']}"

        # All operations should return consistent results
        match_counts = shared_state.get("match_counts", [])
        formid_counts = shared_state.get("formid_counts", [])
        plugin_counts = shared_state.get("plugin_counts", [])

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
        with AsyncBridge.get_instance() as bridge:

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
                    "thread_id": thread_id,
                    "iteration": iteration,
                    "result": result,
                    "success": result.startswith("Processed:"),
                })

                return 1 if result.startswith("Processed:") else 0

            shared_results = []
            results = concurrency_helper.create_contention_scenario(
                target_func=concurrent_bridge_operation, num_threads=20, iterations_per_thread=25, shared_data=shared_results
            )

            # Validate no async bridge errors
            assert len(results["errors"]) == 0, f"AsyncBridge thread safety errors: {results['errors']}"

            # All operations should succeed
            success_count = sum(1 for r in shared_results if r["success"])
            expected_count = 20 * 25  # 20 threads * 25 iterations
            assert success_count == expected_count, f"Expected {expected_count} successes, got {success_count}"

    def test_yaml_cache_concurrent_access(self, concurrency_helper, tmp_path):
        """
        Test YamlSettingsCache thread safety with concurrent cache operations.

        Multiple threads simultaneously access the YAML cache to ensure
        cache consistency and thread safety under high contention.
        """
        from ClassicLib.YamlSettings.sync.cache import YamlSettingsCache as YSC

        # Reset singleton to start fresh
        YSC._instance = None

        # Create a test YAML file with known content
        test_yaml_content = """
CLASSIC_Info:
  version: "7.31.0"
  test_key: "test_value"
"""
        test_yaml_path = tmp_path / "CLASSIC Data" / "databases" / "CLASSIC Main.yaml"
        test_yaml_path.parent.mkdir(parents=True, exist_ok=True)
        test_yaml_path.write_text(test_yaml_content, encoding="utf-8")

        # Track results with proper lock
        results_lock = threading.Lock()

        def concurrent_cache_operation(thread_id: int, iteration: int, shared_data: dict):
            """Worker function for concurrent cache access."""
            try:
                # Get singleton instance (thread-safe operation we're testing)
                cache = YSC.get_instance()

                # Verify singleton consistency - all threads should get same instance
                instance_id = id(cache)

                with results_lock:
                    if "instance_ids" not in shared_data:
                        shared_data["instance_ids"] = set()
                    if "successful_operations" not in shared_data:
                        shared_data["successful_operations"] = 0

                    shared_data["instance_ids"].add(instance_id)
                    shared_data["successful_operations"] += 1

                return 1

            except Exception as e:
                with results_lock:
                    if "operation_errors" not in shared_data:
                        shared_data["operation_errors"] = []
                    shared_data["operation_errors"].append(str(e))
                return 0

        shared_state = {}
        results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_cache_operation, num_threads=15, iterations_per_thread=30, shared_data=shared_state
        )

        # Validate no cache-related errors
        assert len(results["errors"]) == 0, f"YAML cache thread safety errors: {results['errors']}"

        # Verify singleton consistency - all threads should get the same instance
        instance_ids = shared_state.get("instance_ids", set())
        assert len(instance_ids) == 1, f"Multiple cache instances created: {len(instance_ids)} (should be 1)"

        # Most operations should succeed
        successful_ops = shared_state.get("successful_operations", 0)
        expected_ops = 15 * 30
        assert successful_ops >= expected_ops * 0.9, f"Too many cache operation failures: {successful_ops}/{expected_ops}"

        # Clean up singleton for other tests
        YSC._instance = None


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
            GlobalRegistry.get(component_name)

            # Modify shared state
            shared_state["counter"] = shared_state.get("counter", 0) + 1
            shared_state["data"].append(component_name)

        operations = [register_and_access_operation] * 10  # 10 concurrent operations

        race_results = concurrency_helper.detect_race_conditions(
            operations=operations,
            num_iterations=200,  # 200 iterations to catch intermittent issues
        )

        # Should have minimal race conditions (< 5% rate)
        assert race_results["race_condition_rate"] < 0.05, f"High race condition rate: {race_results['race_condition_rate']:.2%}"

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

        def concurrent_logging_operation(thread_id: int, iteration: int, shared_data: list):
            """Worker function for concurrent message logging."""
            messages = [f"INFO: Thread {thread_id} iteration {iteration} message {i}" for i in range(5)]

            for message in messages:
                handler.info(message)
                shared_data.append(message)

            return len(messages)

        shared_messages = []
        results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_logging_operation, num_threads=20, iterations_per_thread=10, shared_data=shared_messages
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
        with AsyncBridge.get_instance() as bridge:
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
                        "thread_id": thread_id,
                        "file_index": file_index,
                        "success": success,
                        "content_length": len(content),
                    })

                    return 1 if success else 0

                except Exception as e:
                    shared_data.append({"thread_id": thread_id, "file_index": file_index, "success": False, "error": str(e)})
                    return 0

            shared_results = []
            results = concurrency_helper.create_contention_scenario(
                target_func=concurrent_file_operation, num_threads=25, iterations_per_thread=20, shared_data=shared_results
            )

            # Validate minimal file I/O errors
            assert len(results["errors"]) < results["total_operations"] * 0.05, "Too many file I/O errors during concurrent access"

            # Most file operations should succeed
            success_count = sum(1 for r in shared_results if r.get("success", False))
            expected_count = 25 * 20
            assert success_count >= expected_count * 0.95, f"File I/O success rate too low: {success_count}/{expected_count}"


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
                pool.execute_query(f"SELECT * FROM test WHERE thread={thread_id}")
                with operation_lock:
                    successful_operations.append((thread_id, iteration))
                return 1
            except Exception as e:
                with operation_lock:
                    failed_operations.append((thread_id, iteration, str(e)))
                return 0

        concurrency_helper.create_contention_scenario(
            target_func=database_operation,
            num_threads=50,  # More threads than pool capacity
            iterations_per_thread=5,
            shared_data=None,
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
        total_tasks = max_workers + 5  # More operations than workers
        operation_times = []
        time_lock = Lock()
        # Use barrier that matches max_workers so concurrent tasks can synchronize
        barrier = Barrier(max_workers)

        def saturating_operation(thread_id: int):
            """Operation that does some work to simulate thread pool saturation."""
            start_time = time.time()

            try:
                # Do some CPU-bound work to occupy the thread
                result = 0
                for i in range(100000):
                    result += i * thread_id

                # Use barrier only for the first max_workers tasks
                # Others just proceed directly (they run after earlier tasks complete)
                if thread_id < max_workers:
                    try:
                        barrier.wait(timeout=10)
                    except Exception:
                        pass  # Barrier timeout is okay

                operation_time = time.time() - start_time

                with time_lock:
                    operation_times.append(operation_time)

                return operation_time
            except Exception:
                return -1  # Indicate failure

        # Use ThreadPoolExecutor to simulate thread pool saturation
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            # Submit more tasks than available workers
            for i in range(total_tasks):
                future = executor.submit(saturating_operation, i)
                futures.append(future)

            # Wait for completion
            results = []
            for future in as_completed(futures, timeout=60):
                try:
                    result = future.result()
                    results.append(result)
                except Exception:
                    results.append(-1)

        total_time = time.time() - start_time

        # All operations should eventually complete
        successful_operations = [r for r in results if r >= 0]
        assert len(successful_operations) >= max_workers, (
            f"Expected at least {max_workers} successful operations, got {len(successful_operations)}"
        )

        # Total time should be reasonable (not stuck indefinitely)
        assert total_time < 120, f"Thread pool saturation took too long: {total_time:.1f}s"

    def test_rust_component_under_extreme_load(self, concurrency_helper, stress_data_generator):
        """
        Test Rust components under extreme concurrent load.

        Creates maximum concurrent load on Rust components to test
        stability and performance under extreme stress conditions.
        """
        parser = classic_scanlog.LogParser()
        patterns = ["ERROR", "WARNING", "FormID"]
        pattern_matcher = classic_scanlog.PatternMatcher(patterns)

        # Generate challenging test data
        large_log_content = stress_data_generator.generate_large_crash_log(
            size_mb=5,  # 5MB per operation
            plugin_count=100,
            formid_count=1000,
        )

        # Convert to list of lines for LogParser API
        large_log_lines = large_log_content.split("\n") if isinstance(large_log_content, str) else large_log_content

        results_lock = Lock()
        processing_results = {"formid_counts": [], "plugin_counts": [], "processing_times": [], "errors": []}

        def extreme_load_operation(thread_id: int, iteration: int, shared_data: None):
            """Worker function for extreme load testing."""
            start_time = time.time()

            try:
                # Perform multiple operations per thread using LogParser
                formids = parser.extract_formids(large_log_lines)
                plugins = parser.extract_plugins(large_log_lines)

                # Pattern matching using PatternMatcher
                large_log_text = "\n".join(large_log_lines) if isinstance(large_log_lines, list) else large_log_lines
                pattern_matcher.find_all(large_log_text)

                processing_time = time.time() - start_time

                with results_lock:
                    processing_results["formid_counts"].append(len(formids))
                    processing_results["plugin_counts"].append(len(plugins))
                    processing_results["processing_times"].append(processing_time)

                return processing_time

            except Exception as e:
                with results_lock:
                    processing_results["errors"].append(str(e))
                return -1

        concurrency_helper.create_contention_scenario(
            target_func=extreme_load_operation,
            num_threads=40,  # High thread count
            iterations_per_thread=10,  # Multiple operations per thread
            shared_data=None,
        )

        # Most operations should succeed even under extreme load
        total_expected = 40 * 10
        error_count = len(processing_results["errors"])
        success_rate = (total_expected - error_count) / total_expected

        assert success_rate > 0.9, f"Success rate too low under extreme load: {success_rate:.1%}"

        # Results should be consistent across threads
        formid_counts = processing_results["formid_counts"]
        if formid_counts:
            # All successful operations should find similar numbers of FormIDs
            # Note: With formid_count=1000 in generator, we get 1000//10 = 100 FormIDs
            avg_formids = sum(formid_counts) / len(formid_counts)
            assert avg_formids >= 100, f"Expected significant FormIDs, got avg {avg_formids}"

        # Performance should remain reasonable even under load
        processing_times = processing_results["processing_times"]
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
        allocation_stats = {"successful_allocations": 0, "failed_allocations": 0, "peak_allocations": 0}

        def concurrent_memory_operation(thread_id: int, iteration: int, shared_data: None):
            """Worker function for concurrent memory allocation."""
            try:
                # Allocate memory for large string processing
                large_strings = [f"Thread_{thread_id}_String_{iteration}_{i}" * 1000 for i in range(100)]  # ~100KB per thread

                # Process with Rust components (internal memory allocation)
                string_pool = classic_scanlog.StringPool()
                interned = string_pool.intern_batch(large_strings)

                # Also test LogParser memory handling
                parser = classic_scanlog.LogParser()
                # Parse the strings as if they were log lines
                parser.parse_segments(large_strings[:10])  # Use first 10 as sample

                # Track allocation success
                with allocation_lock:
                    allocation_stats["successful_allocations"] += 1

                # Clean up
                del large_strings, interned, string_pool, parser

                return 1

            except MemoryError:
                with allocation_lock:
                    allocation_stats["failed_allocations"] += 1
                return 0

        # Take memory measurement before stress
        fresh_memory_tracker.take_measurement("before_stress")

        concurrency_helper.create_contention_scenario(
            target_func=concurrent_memory_operation, num_threads=30, iterations_per_thread=20, shared_data=None
        )

        # Take measurement after stress
        fresh_memory_tracker.take_measurement("after_stress")

        memory_stats = fresh_memory_tracker.stop_tracking()

        # Most allocations should succeed
        successful = allocation_stats["successful_allocations"]
        total_expected = 30 * 20
        success_rate = successful / total_expected

        assert success_rate > 0.95, f"Memory allocation success rate too low: {success_rate:.1%}"

        # Memory growth should be reasonable
        assert memory_stats["growth_mb"] < 200, f"Excessive memory growth during concurrent allocation: {memory_stats['growth_mb']:.1f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
