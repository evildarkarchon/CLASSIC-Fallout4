"""
Malformed data handling stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests validate error handling when processing malformed or corrupted data,
including corrupted crash logs, malformed FormIDs, and invalid plugin structures.
"""

import time

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

from classic_scanlog import FormIDAnalyzer, LogParser, PatternMatcher


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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
