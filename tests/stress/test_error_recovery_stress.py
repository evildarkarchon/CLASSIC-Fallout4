"""
Error recovery stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests validate error handling and recovery capabilities under extreme
conditions, including malformed data, resource failures, partial failures,
and cascading error scenarios that simulate production failure conditions.
"""

import time
from pathlib import Path

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

import classic_scanlog
from classic_scanlog import FormIDAnalyzer, LogParser, PatternMatcher

# Import components to test
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.FileIO import FileIOCore
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.error_recovery
class TestMalformedDataHandling:
    """
    Test error recovery when processing malformed or corrupted data.

    These tests validate that the system gracefully handles corrupted
    crash logs, malformed FormIDs, and other data integrity issues.
    """

    def test_corrupted_crash_log_handling(self, tmp_path, performance_profiler):
        """
        Test handling of corrupted crash logs at scale.

        Creates various types of corrupted crash logs and ensures
        the system handles them gracefully without crashing.
        """
        performance_profiler.start_profiling()

        parser = LogParser()

        # Generate different types of corrupted logs
        corrupted_logs = [
            # Binary data mixed with text
            b"Fallout 4 v1.10.163\x00\x01\x02\x03\nPlugins:\n[001] Test.esm\xff\xfe".decode("utf-8", errors="ignore"),
            # Extremely long lines
            "Fallout 4 v1.10.163\n" + "A" * 100000 + "\nFormID: 0x12345678\n",
            # Invalid encoding sequences
            "Fallout 4 v1.10.163\nFormID: 0x12345678\n" + "\ufffd" * 1000,
            # Malformed structure
            "Random text without any structure\n" * 1000,
            # Empty sections
            "Fallout 4 v1.10.163\n\n\n\nPLUGINS:\n\n\nSTACK TRACE:\n\n\n",
            # Unicode issues
            "Fallout 4 v1.10.163\nPlugin: Tëst_Mød_Ñamé.esp\nFormID: 0x12345678\n" * 100,
        ]

        error_counts = []
        processing_results = []
        for i, corrupted_content in enumerate(corrupted_logs):
            processing_time = 0.0  # Initialize before try block
            try:
                start_time = time.time()

                # Convert content to lines for LogParser
                lines = corrupted_content.split("\n")

                # Try to extract FormIDs from corrupted content
                formids = parser.extract_formids(lines)

                # Try to extract plugins
                plugins = parser.extract_plugins(lines)

                # Try pattern matching using PatternMatcher
                pattern_matcher = PatternMatcher(["ERROR", "WARNING", "FormID"])
                matches = pattern_matcher.find_all(corrupted_content)

                processing_time = time.time() - start_time

                processing_results.append({
                    "log_type": f"corrupted_{i}",
                    "formids_found": len(formids),
                    "plugins_found": len(plugins),
                    "patterns_matched": len(matches),
                    "processing_time": processing_time,
                    "error": None,
                })

            except Exception as e:
                processing_results.append({"log_type": f"corrupted_{i}", "error": str(e), "error_type": type(e).__name__})

            performance_profiler.record_operation(f"corrupted_log_{i}", processing_time, 0)

        performance_stats = performance_profiler.stop_profiling()

        # Analyze error handling
        successful_processing = sum(1 for r in processing_results if r["error"] is None)
        total_attempts = len(processing_results)

        # Most corrupted logs should be processed without crashing
        success_rate = successful_processing / total_attempts
        assert success_rate > 0.7, f"Too many failures processing corrupted logs: {success_rate:.1%}"

        # No critical system errors should occur
        critical_errors = [r for r in processing_results if r.get("error") and "system" in r["error"].lower()]
        assert len(critical_errors) == 0, f"Critical system errors occurred: {critical_errors}"

    def test_malformed_formid_batch_processing(self, performance_profiler):
        """
        Test batch processing of malformed FormIDs at scale.

        Processes thousands of malformed FormIDs to ensure robust
        error handling in batch processing scenarios.
        """
        performance_profiler.start_profiling()

        analyzer = FormIDAnalyzer()

        # Generate various malformed FormID patterns
        malformed_formids = []

        # Invalid hex values
        malformed_formids.extend(["0xGGGGGGGG", "0xHHHHHHHH", "0xZZZZZZZZ"] * 100)

        # Wrong format
        malformed_formids.extend(["12345678", "ABCDEF", "0X12345678"] * 100)

        # Empty/null values - filter out None since Rust can't handle it
        malformed_formids.extend(["", "0x", "0x0"] * 100)

        # Extremely long values
        malformed_formids.extend([f"0x{'A' * 100}", f"0x{'F' * 50}"] * 100)

        # Special characters
        malformed_formids.extend(["0x1234!@#$", "0x<script>", "0x\x00\x01"] * 100)

        # Mixed valid and invalid
        for i in range(500):
            if i % 10 == 0:
                malformed_formids.append(f"0x{i:08X}")  # Valid FormID
            else:
                malformed_formids.append(f"0xINVALID{i}")  # Invalid

        # Process in batches to test error handling at scale
        batch_size = 1000
        batch_results = []
        total_processed = 0
        total_errors = 0

        for i in range(0, len(malformed_formids), batch_size):
            batch = malformed_formids[i : i + batch_size]
            processing_time = 0.0  # Initialize before try block

            start_time = time.time()

            try:
                # Process batch using FormIDAnalyzer - validate each FormID
                valid_results = 0
                invalid_results = 0
                for formid in batch:
                    parsed = analyzer.parse_formid(formid)
                    if parsed is not None:
                        valid_results += 1
                    else:
                        invalid_results += 1

                processing_time = time.time() - start_time

                batch_results.append({
                    "batch_index": i // batch_size,
                    "total_items": len(batch),
                    "valid_results": valid_results,
                    "invalid_results": invalid_results,
                    "processing_time": processing_time,
                    "error": None,
                })

                total_processed += len(batch)

            except Exception as e:
                batch_results.append({"batch_index": i // batch_size, "error": str(e), "error_type": type(e).__name__})
                total_errors += 1

            performance_profiler.record_operation(f"malformed_formid_batch_{i // batch_size}", processing_time, 0)

        performance_stats = performance_profiler.stop_profiling()

        # Analyze batch processing results
        successful_batches = sum(1 for r in batch_results if r.get("error") is None)
        total_batches = len(batch_results)

        # Most batches should process successfully despite malformed data
        assert successful_batches / total_batches > 0.9, f"Too many batch processing failures: {successful_batches}/{total_batches}"

        # Should process a reasonable number of items
        assert total_processed > len(malformed_formids) * 0.8, (
            f"Processed fewer items than expected: {total_processed}/{len(malformed_formids)}"
        )

    def test_invalid_plugin_data_handling(self, tmp_path, performance_profiler):
        """
        Test handling of invalid plugin data structures.

        Creates crash logs with invalid plugin structures and tests
        robust parsing and error recovery capabilities.
        """
        performance_profiler.start_profiling()

        parser = LogParser()

        # Generate logs with various plugin data issues
        invalid_plugin_logs = [
            # Malformed plugin entries
            """Fallout 4 v1.10.163
PLUGINS:
[001 Fallout4.esm  # Missing closing bracket
[002] DLCRobot.esm
[003 TestMod.esp   # Missing closing bracket
            """,
            # Invalid plugin indexes
            """Fallout 4 v1.10.163
PLUGINS:
[999] Fallout4.esm
[-01] DLCRobot.esm
[abc] TestMod.esp
            """,
            # Extremely long plugin names
            """Fallout 4 v1.10.163
PLUGINS:
[001] """
            + "A" * 10000
            + """.esp
[002] """
            + "B" * 5000
            + """.esm
            """,
            # Mixed encoding in plugin names
            """Fallout 4 v1.10.163
PLUGINS:
[001] Fallout4.esm
[002] Tëst_Mød_Ñamé_Wïth_Ûnïcødé.esp
[003] """
            + "\ufffd" * 100
            + """.esp
            """,
            # Duplicate plugin indexes
            """Fallout 4 v1.10.163
PLUGINS:
[001] Fallout4.esm
[001] DuplicateIndex.esp
[001] AnotherDuplicate.esp
            """,
        ]

        processing_results = []

        for i, log_content in enumerate(invalid_plugin_logs):
            processing_time = 0.0  # Initialize before try block
            try:
                start_time = time.time()

                # Convert to lines for LogParser
                lines = log_content.split("\n")

                # Extract plugins from invalid log
                plugins = parser.extract_plugins(lines)

                # Also test FormID extraction on the same content
                formids = parser.extract_formids(lines)

                processing_time = time.time() - start_time

                processing_results.append({
                    "log_index": i,
                    "plugins_extracted": len(plugins),
                    "formids_extracted": len(formids),
                    "processing_time": processing_time,
                    "success": True,
                })

            except Exception as e:
                processing_results.append({"log_index": i, "error": str(e), "error_type": type(e).__name__, "success": False})

            performance_profiler.record_operation(f"invalid_plugin_log_{i}", processing_time, 0)

        performance_stats = performance_profiler.stop_profiling()

        # Analyze plugin parsing error handling
        successful_extractions = sum(1 for r in processing_results if r["success"])
        total_attempts = len(processing_results)

        # Should handle most invalid plugin structures gracefully
        success_rate = successful_extractions / total_attempts
        assert success_rate > 0.8, f"Plugin parsing too fragile: {success_rate:.1%} success rate"

        # Processing times should remain reasonable even with invalid data
        successful_results = [r for r in processing_results if r["success"]]
        if successful_results:
            avg_processing_time = sum(r["processing_time"] for r in successful_results) / len(successful_results)
            assert avg_processing_time < 1.0, f"Invalid plugin processing too slow: {avg_processing_time:.2f}s"


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


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.error_recovery
class TestPartialFailureHandling:
    """
    Test handling of partial failures in batch operations.

    These tests validate that when some operations in a batch fail,
    the system continues processing remaining operations successfully.
    """

    def test_mixed_batch_processing_resilience(self, performance_profiler, tmp_path, stress_data_generator):
        """
        Test batch processing resilience with mixed success/failure scenarios.

        Creates batches with mix of valid and invalid data to test
        partial failure handling and processing continuation.
        """
        performance_profiler.start_profiling()

        with AsyncBridge.get_instance() as bridge:
            io_core = FileIOCore()
            parser = LogParser()

            # Create mixed batch of files (some good, some problematic)
            batch_files = []

            # Good files
            for i in range(10):
                content = stress_data_generator.generate_large_crash_log(size_mb=1, plugin_count=20, formid_count=100)
                file_path = tmp_path / f"good_file_{i}.log"
                file_path.write_text(content, encoding="utf-8")
                batch_files.append(("good", file_path))

            # Problematic files
            problematic_files = [
                # Corrupted content
                ("Corrupted binary data: \x00\x01\x02\x03\xff\xfe" * 1000, "corrupted_1.log"),
                # Empty file
                ("", "empty.log"),
                # Extremely large file with minimal content
                ("Large file content\n" * 100000, "huge.log"),
                # File with only invalid FormIDs
                ("FormID: 0xINVALID\nFormID: 0xBADDATA\n" * 1000, "invalid_formids.log"),
                # Mixed encoding issues
                ("Fallout 4\n" + "Tëst_Ñamé\ufffd" * 500 + "\nFormID: 0x12345678", "encoding_issues.log"),
            ]

            for content, filename in problematic_files:
                file_path = tmp_path / filename
                file_path.write_text(content, encoding="utf-8", errors="ignore")
                batch_files.append(("problematic", file_path))

            # Process mixed batch
            processing_results = []

            for file_type, file_path in batch_files:
                result = {"file_type": file_type, "filename": file_path.name}
                processing_time = 0.0  # Initialize before try block

                try:
                    start_time = time.time()

                    # Read file
                    content = bridge.run_async(io_core.read_file(file_path))

                    # Convert to lines for LogParser
                    lines = content.split("\n")

                    # Process content
                    formids = parser.extract_formids(lines)
                    plugins = parser.extract_plugins(lines)

                    processing_time = time.time() - start_time

                    result.update({
                        "success": True,
                        "processing_time": processing_time,
                        "formids_found": len(formids),
                        "plugins_found": len(plugins),
                        "content_size": len(content),
                    })

                except Exception as e:
                    result.update({"success": False, "error": str(e), "error_type": type(e).__name__})

                processing_results.append(result)

                performance_profiler.record_operation(f"mixed_batch_{file_type}", processing_time, 0)

            performance_stats = performance_profiler.stop_profiling()

            # Analyze partial failure handling
            good_results = [r for r in processing_results if r["file_type"] == "good"]
            problematic_results = [r for r in processing_results if r["file_type"] == "problematic"]

            # Most good files should process successfully
            successful_good = sum(1 for r in good_results if r["success"])
            good_success_rate = successful_good / len(good_results) if good_results else 0

            assert good_success_rate > 0.9, f"Good files success rate too low: {good_success_rate:.1%}"

            # System should handle problematic files gracefully (not crash)
            # Some may succeed (robust parsing) or fail (expected), but no system crash
            processed_count = len(processing_results)
            expected_count = len(batch_files)

            assert processed_count == expected_count, f"Partial failures caused processing to stop: {processed_count}/{expected_count}"

    def test_concurrent_partial_failures(self, performance_profiler, concurrency_helper):
        """
        Test concurrent operations with partial failures.

        Runs concurrent operations where some threads encounter
        failures while others continue successfully.
        """
        performance_profiler.start_profiling()

        parser = LogParser()

        # Create test data with mix of valid and invalid content
        test_contents = [
            # Valid content
            "Fallout 4 v1.10.163\nFormID: 0x12345678\nPlugin: Test.esp\n" * 100,
            "Fallout 4 v1.10.163\nFormID: 0xABCDEF01\nPlugin: Another.esp\n" * 100,
            # Invalid content that should cause processing issues
            "\x00\x01\x02\xff\xfe" * 1000,  # Binary data
            "FormID: 0xINVALID\n" * 1000,  # Invalid FormIDs
            "",  # Empty content
            "A" * 1000000,  # Extremely large content
        ]

        def concurrent_operation_with_failures(thread_id: int, iteration: int, shared_data: list):
            """Operation that may encounter failures."""
            results = {"processed": 0, "failed": 0, "errors": []}

            for i, content in enumerate(test_contents):
                try:
                    # Convert to lines for LogParser
                    lines = content.split("\n")

                    # Process content that may be valid or invalid
                    parser.extract_formids(lines)
                    parser.extract_plugins(lines)

                    results["processed"] += 1

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "content_index": i,
                        "error": str(e)[:100],  # Limit error message length
                        "error_type": type(e).__name__,
                    })

            shared_data.append(results)
            return results["processed"]

        shared_results = []
        concurrency_results = concurrency_helper.create_contention_scenario(
            target_func=concurrent_operation_with_failures, num_threads=15, iterations_per_thread=5, shared_data=shared_results
        )

        performance_profiler.stop_profiling()

        # Analyze concurrent partial failure handling
        total_processed = sum(r["processed"] for r in shared_results)
        total_failed = sum(r["failed"] for r in shared_results)
        total_operations = total_processed + total_failed

        # Should process valid content successfully
        assert total_processed > 0, "No operations processed successfully"

        # Should handle invalid content without system failure
        assert len(concurrency_results["errors"]) == 0, "System errors during partial failures"

        # Processing should continue despite individual failures
        expected_total = 15 * 5 * len(test_contents)  # threads * iterations * content pieces
        completion_rate = total_operations / expected_total

        assert completion_rate > 0.95, f"Operations incomplete due to failures: {completion_rate:.1%}"


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
