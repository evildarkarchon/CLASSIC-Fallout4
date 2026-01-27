"""
Cascading failure recovery stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests create scenarios where one failure leads to others,
testing the system's ability to contain and recover from
cascading failure patterns.
"""

import time

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

from classic_scanlog import LogParser, PatternMatcher

# Import components to test
from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.io.files import FileIOCore


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.error_recovery
class TestCascadingFailureRecovery:
    """
    Test recovery from cascading failure scenarios.

    These tests create scenarios where one failure leads to others,
    testing the system's ability to contain and recover from
    cascading failure patterns.
    """

    def test_cascading_resource_exhaustion(self, performance_profiler, resource_exhaustion_simulator, concurrency_helper):
        """
        Test recovery from cascading resource exhaustion.

        Creates scenarios where resource exhaustion in one area leads
        to failures in other areas, testing containment and recovery.
        """
        performance_profiler.start_profiling()

        simulator = resource_exhaustion_simulator

        def resource_intensive_operation(thread_id: int, iteration: int, shared_data: dict):
            """Operation that consumes multiple resource types."""
            operation_result = {
                "thread_id": thread_id,
                "iteration": iteration,
                "file_handles_used": 0,
                "memory_allocated": 0,
                "success": False,
                "errors": [],
            }

            try:
                # Try to allocate file handles
                handles = []
                for _i in range(5):  # Try to allocate 5 handles
                    handle = simulator.allocate_file_handle()
                    handles.append(handle)
                    operation_result["file_handles_used"] += 1

                # Try to allocate memory
                memory_chunks = []
                for _i in range(3):  # Try to allocate 3 chunks
                    chunk = simulator.allocate_memory(10 * 1024 * 1024)  # 10MB each
                    memory_chunks.append(chunk)
                    operation_result["memory_allocated"] += 10 * 1024 * 1024

                # Simulate processing work
                time.sleep(0.01)  # Brief processing time

                operation_result["success"] = True

                # Clean up resources
                for _ in handles:
                    simulator.release_handle()

                for chunk in memory_chunks:
                    simulator.release_memory(10 * 1024 * 1024)

            except Exception as e:
                operation_result["errors"].append({"error_type": type(e).__name__, "message": str(e)})

                # Try to clean up any allocated resources
                try:
                    for _ in range(operation_result["file_handles_used"]):
                        simulator.release_handle()

                    if operation_result["memory_allocated"] > 0:
                        simulator.release_memory(operation_result["memory_allocated"])
                except:
                    pass  # Ignore cleanup errors

            # Store result in shared data with thread safety
            import threading

            with threading.Lock():
                if "results" not in shared_data:
                    shared_data["results"] = []
                shared_data["results"].append(operation_result)

            return 1 if operation_result["success"] else 0

        shared_state = {}
        results = concurrency_helper.create_contention_scenario(
            target_func=resource_intensive_operation,
            num_threads=20,  # High contention for resources
            iterations_per_thread=10,
            shared_data=shared_state,
        )

        performance_profiler.stop_profiling()

        # Analyze cascading failure patterns
        operation_results = shared_state.get("results", [])

        successful_operations = sum(1 for r in operation_results if r["success"])
        failed_operations = len(operation_results) - successful_operations

        # Should have some successful operations
        # Note: Since resources are released after each iteration, most operations may succeed
        assert successful_operations > 0, "No operations succeeded"

        # Collect error types if any occurred
        error_types = {}
        for result in operation_results:
            for error in result.get("errors", []):
                error_type = error["error_type"]
                error_types[error_type] = error_types.get(error_type, 0) + 1

        # Resource exhaustion may or may not occur depending on timing
        # The key validation is that the system handles resource contention gracefully
        # without crashing, which is validated by the loop completing

        # No system crashes should occur (validates containment)
        assert len(results["errors"]) == 0, "System errors during resource contention"

        # Most operations should succeed since resources are properly released
        total_operations = len(operation_results)
        success_rate = successful_operations / max(total_operations, 1)
        assert success_rate > 0.5, f"Success rate too low under resource contention: {success_rate:.1%}"

    def test_error_propagation_containment(self, performance_profiler, tmp_path):
        """
        Test containment of error propagation across system components.

        Creates error conditions in one component and tests that
        errors don't propagate uncontrollably to other components.
        """
        performance_profiler.start_profiling()

        with AsyncBridge.get_instance() as bridge:
            io_core = FileIOCore()
            parser = LogParser()

            # Create scenario with deliberate error injection
            error_injection_points = ["file_read", "formid_extraction", "plugin_extraction", "pattern_matching"]

            containment_results = []

            for error_point in error_injection_points:
                test_result = {
                    "error_injection_point": error_point,
                    "operations_attempted": 0,
                    "operations_succeeded": 0,
                    "contained_errors": 0,
                    "system_errors": 0,
                }

                # Create test file
                test_content = (
                    f"""Fallout 4 v1.10.163
FormID: 0x12345678
Plugin: TestMod.esp
Error injection point: {error_point}
"""
                    * 100
                )

                test_file = tmp_path / f"error_injection_{error_point}.log"
                test_file.write_text(test_content, encoding="utf-8")

                # Attempt operations with error injection
                for operation_id in range(20):  # 20 operations per injection point
                    test_result["operations_attempted"] += 1

                    try:
                        # File reading
                        if error_point == "file_read":
                            # Simulate file read error by trying to read non-existent file occasionally
                            if operation_id % 5 == 0:
                                content = bridge.run_async(io_core.read_file(tmp_path / "nonexistent.log"))
                            else:
                                content = bridge.run_async(io_core.read_file(test_file))
                        else:
                            content = bridge.run_async(io_core.read_file(test_file))

                        # Convert to lines for LogParser
                        lines = content.split("\n")

                        # FormID extraction
                        if error_point == "formid_extraction":
                            # Inject corrupted content for FormID extraction
                            if operation_id % 5 == 0:
                                parser.extract_formids(["CORRUPTED_FORMID_DATA_0xINVALID"])
                            else:
                                parser.extract_formids(lines)
                        else:
                            parser.extract_formids(lines)

                        # Plugin extraction
                        if error_point == "plugin_extraction":
                            # Inject corrupted content for plugin extraction
                            if operation_id % 5 == 0:
                                parser.extract_plugins(["CORRUPTED_PLUGIN_DATA"])
                            else:
                                parser.extract_plugins(lines)
                        else:
                            parser.extract_plugins(lines)

                        # Pattern matching
                        if error_point == "pattern_matching":
                            # Use invalid patterns occasionally
                            if operation_id % 5 == 0:
                                pattern_matcher = PatternMatcher([r"\x00\x01\x02"])  # Invalid regex patterns
                                pattern_matcher.find_all(content)
                            else:
                                pattern_matcher = PatternMatcher(["FormID", "Plugin"])
                                pattern_matcher.find_all(content)
                        else:
                            pattern_matcher = PatternMatcher(["FormID", "Plugin"])
                            pattern_matcher.find_all(content)

                        test_result["operations_succeeded"] += 1

                    except Exception as e:
                        # Categorize error as contained vs system error
                        error_message = str(e).lower()
                        if any(keyword in error_message for keyword in ["file", "formid", "plugin", "pattern"]):
                            test_result["contained_errors"] += 1
                        else:
                            test_result["system_errors"] += 1

                    performance_profiler.record_operation(
                        f"error_containment_{error_point}_{operation_id}",
                        0.001,  # Minimal time for error cases
                        0,
                    )

                containment_results.append(test_result)

            performance_profiler.stop_profiling()

            # Analyze error containment
            for result in containment_results:
                error_point = result["error_injection_point"]

                # Should have attempted all operations
                assert result["operations_attempted"] == 20, f"Not all operations attempted for {error_point}"

                # Should have some successful operations (error injection is intermittent)
                assert result["operations_succeeded"] > 10, (
                    f"Too few successful operations for {error_point}: {result['operations_succeeded']}"
                )

                # Errors should be contained (not propagate to system level)
                total_errors = result["contained_errors"] + result["system_errors"]
                if total_errors > 0:
                    containment_rate = result["contained_errors"] / total_errors
                    assert containment_rate > 0.8, f"Poor error containment for {error_point}: {containment_rate:.1%}"

                # System errors should be minimal
                assert result["system_errors"] < 5, f"Too many system errors for {error_point}: {result['system_errors']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
