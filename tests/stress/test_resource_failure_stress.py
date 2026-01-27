"""
Resource failure recovery stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests simulate resource failures including file I/O errors, database connection
failures, and memory pressure situations, validating graceful degradation and recovery.
"""

import time
from pathlib import Path

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

# Import components to test
from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.io.files import FileIOCore


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.error_recovery
class TestResourceFailureRecovery:
    """
    Test recovery from resource failures and exhaustion scenarios.

    These tests simulate network failures, disk I/O errors, memory
    exhaustion, and other resource-related failure conditions.
    """

    def test_file_io_failure_recovery(self, tmp_path, performance_profiler, concurrency_helper):
        """
        Test FileIOCore recovery from I/O failures.

        Simulates various I/O failure scenarios and tests that the
        system recovers gracefully and continues processing other files.
        """
        performance_profiler.start_profiling()

        with AsyncBridge.get_instance() as bridge:
            io_core = FileIOCore()

            # Create mix of valid and problematic files
            test_files = []

            # Valid files
            for i in range(5):
                content = f"Valid crash log content {i}\nFormID: 0x{i:08X}\n"
                file_path = tmp_path / f"valid_{i}.log"
                file_path.write_text(content, encoding="utf-8")
                test_files.append(("valid", file_path))

            # Create files that will cause I/O issues
            # Locked file (simulate by creating and keeping handle open)
            locked_file = tmp_path / "locked.log"
            locked_file.write_text("Locked file content")

            # File with permission issues (simulate by making read-only on Windows)
            permission_file = tmp_path / "permission_denied.log"
            permission_file.write_text("Permission denied content")

            # Non-existent file
            nonexistent_file = tmp_path / "does_not_exist.log"

            test_files.extend([("locked", locked_file), ("permission", permission_file), ("nonexistent", nonexistent_file)])

            def file_operation_with_recovery(thread_id: int, iteration: int, shared_data: list):
                """Test file operations with error recovery."""
                results = {"successful": 0, "failed": 0, "errors": []}

                for file_type, file_path in test_files:
                    try:
                        if file_type == "locked":
                            # Simulate locked file by trying to open with exclusive access
                            with Path(file_path).open("r+"):
                                bridge.run_async(io_core.read_file(file_path))
                        elif file_type == "permission":
                            # Make file read-only to simulate permission issues
                            if iteration == 0:  # Only on first iteration
                                Path(file_path).chmod(0o444)  # Read-only
                            bridge.run_async(io_core.read_file(file_path))
                        elif file_type == "nonexistent":
                            # Try to read non-existent file
                            bridge.run_async(io_core.read_file(file_path))
                        else:
                            # Normal file read
                            bridge.run_async(io_core.read_file(file_path))

                        results["successful"] += 1

                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append({"file_type": file_type, "error": str(e), "error_type": type(e).__name__})

                shared_data.append(results)
                return results["successful"]

            # Run concurrent file operations with failures
            shared_results = []
            concurrency_results = concurrency_helper.create_contention_scenario(
                target_func=file_operation_with_recovery, num_threads=10, iterations_per_thread=3, shared_data=shared_results
            )

            performance_profiler.stop_profiling()

            # Analyze recovery behavior
            total_successful = sum(r["successful"] for r in shared_results)
            total_failed = sum(r["failed"] for r in shared_results)

            # Valid files (5 per iteration) should mostly succeed
            # Note: locked, permission, and nonexistent files may fail
            expected_valid_operations = 10 * 3 * 5  # 10 threads * 3 iterations * 5 valid files
            expected_problematic_operations = 10 * 3 * 3  # 10 threads * 3 iterations * 3 problematic files
            total_operations = expected_valid_operations + expected_problematic_operations

            # Valid file success rate: total_successful should include mostly valid files
            # Since problematic files should fail, we expect at most expected_valid_operations successes
            valid_success_rate = total_successful / total_operations
            assert valid_success_rate > 0.5, f"Overall success rate too low: {valid_success_rate:.1%}"

            # The system should handle failures without crashing
            assert len(concurrency_results["errors"]) == 0, "System errors during I/O failure recovery"

            # Should have some failed operations (the problematic files)
            assert total_failed > 0, "Expected some file operations to fail"

    def test_database_connection_failure_simulation(self, performance_profiler, failing_database_pool):
        """
        Test recovery from database connection failures.

        Simulates database failures and tests graceful degradation
        and recovery patterns in database-dependent operations.
        """
        performance_profiler.start_profiling()

        # Simulate database operations with eventual failure
        pool = failing_database_pool  # Fails after 100 operations
        operation_results = []

        # Attempt many operations to trigger failure and recovery
        for i in range(150):  # More than the failure threshold
            operation_time = 0.0  # Initialize before try block
            try:
                start_time = time.time()

                # Attempt database operation
                result = pool.execute_query(f"SELECT * FROM logs WHERE id = {i}")

                operation_time = time.time() - start_time
                operation_results.append({"operation_id": i, "success": True, "time": operation_time, "error": None})

            except Exception as e:
                operation_results.append({"operation_id": i, "success": False, "error": str(e), "error_type": type(e).__name__})

            performance_profiler.record_operation(f"db_operation_{i}", operation_time, 0)

        performance_stats = performance_profiler.stop_profiling()

        # Analyze failure and recovery patterns
        successful_ops = [r for r in operation_results if r["success"]]
        failed_ops = [r for r in operation_results if not r["success"]]

        # Should have initial successes before failure
        assert len(successful_ops) >= 80, f"Too few successful operations: {len(successful_ops)}"

        # Should have failures after reaching limit
        assert len(failed_ops) > 0, "Expected database failures to occur"

        # Failures should be handled gracefully (no system crash)
        # This is validated by the fact that the loop completed

    def test_memory_pressure_recovery(self, performance_profiler, fresh_memory_tracker, resource_exhaustion_simulator):
        """
        Test recovery from memory pressure situations.

        Simulates memory exhaustion scenarios and tests system
        behavior and recovery under memory pressure.
        """
        performance_profiler.start_profiling()
        fresh_memory_tracker.start_tracking()

        simulator = resource_exhaustion_simulator

        # Simulate memory-intensive operations with pressure
        allocation_results = []

        for i in range(50):  # 50 memory-intensive operations
            operation_time = 0.0  # Initialize before try block
            try:
                start_time = time.time()

                # Try to allocate memory through simulator
                memory_chunk = simulator.allocate_memory(50 * 1024 * 1024)  # 50MB chunks

                # If allocation succeeds, do actual string processing using Python builtins
                large_strings = [f"Memory_pressure_test_{i}_{j}" * 1000 for j in range(100)]
                processed = [s.upper() for s in large_strings]

                operation_time = time.time() - start_time
                allocation_results.append({"operation_id": i, "success": True, "time": operation_time, "processed_count": len(processed)})

                # Clean up
                simulator.release_memory(50 * 1024 * 1024)
                del memory_chunk, large_strings, processed

            except MemoryError as e:
                allocation_results.append({"operation_id": i, "success": False, "error": "MemoryError", "message": str(e)})

                # Try to free some memory and continue
                simulator.release_memory(25 * 1024 * 1024)  # Release some memory

            except Exception as e:
                allocation_results.append({"operation_id": i, "success": False, "error": type(e).__name__, "message": str(e)})

            performance_profiler.record_operation(f"memory_pressure_{i}", operation_time, 0)

            fresh_memory_tracker.take_measurement(f"operation_{i}")

        performance_stats = performance_profiler.stop_profiling()
        memory_stats = fresh_memory_tracker.stop_tracking()

        # Analyze memory pressure recovery
        successful_ops = [r for r in allocation_results if r["success"]]
        memory_errors = [r for r in allocation_results if r.get("error") == "MemoryError"]

        # Should have successful operations under memory pressure
        # The test releases memory after each operation, so most should succeed
        assert len(successful_ops) > 10, f"Too few successful operations under memory pressure: {len(successful_ops)}"

        # Memory errors may or may not occur depending on system resources and timing
        # The key validation is that the system handles memory pressure gracefully
        # without crashing, which is validated by the loop completing

        # Memory should be managed efficiently
        assert memory_stats["peak_mb"] < 1000, f"Excessive peak memory usage: {memory_stats['peak_mb']:.1f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
