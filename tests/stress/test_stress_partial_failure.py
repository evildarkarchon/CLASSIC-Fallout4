"""
Partial failure handling stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests validate that when some operations in a batch fail,
the system continues processing remaining operations successfully.
"""

import time

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

from classic_scanlog import LogParser

# Import components to test
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.FileIO import FileIOCore


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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
