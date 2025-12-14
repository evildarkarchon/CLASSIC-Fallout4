"""
FormID processing stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests validate system performance and stability when processing
massive FormID datasets that represent extreme production scenarios, including
thousands of FormIDs, deduplication at scale, and cross-referencing operations.
"""

import time
from statistics import mean

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

from classic_scanlog import FormIDAnalyzer


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.data_volume
class TestMassiveFormIDProcessing:
    """
    Test processing of massive FormID datasets.

    These tests validate system performance when processing thousands
    to hundreds of thousands of FormIDs simultaneously, simulating
    heavily modded game installations.
    """

    def test_hundred_thousand_formids_processing(self, performance_profiler, fresh_memory_tracker, stress_data_generator):
        """
        Test processing 100,000+ FormIDs in various formats.

        Validates memory efficiency and processing speed when dealing
        with massive FormID datasets that might be encountered in
        heavily modded game installations.
        """
        performance_profiler.start_profiling()
        fresh_memory_tracker.start_tracking()

        analyzer = FormIDAnalyzer()

        # Generate massive FormID dataset
        massive_formid_count = 100000
        formids = stress_data_generator.generate_formid_dataset(count=massive_formid_count)

        fresh_memory_tracker.take_measurement("formids_generated")

        # Process in chunks to test scalability
        chunk_size = 10000
        processing_results = []
        total_valid_formids = 0

        start_time = time.time()

        for i in range(0, len(formids), chunk_size):
            chunk_start = time.time()
            chunk = formids[i : i + chunk_size]

            # Process chunk - validate each FormID
            results = []
            for formid in chunk:
                parsed = analyzer.parse_formid(formid)
                results.append(parsed)

            chunk_end = time.time()
            chunk_duration = chunk_end - chunk_start

            # Count valid results
            valid_count = sum(1 for r in results if r is not None)
            total_valid_formids += valid_count

            processing_results.append({
                "chunk_index": i // chunk_size,
                "chunk_size": len(chunk),
                "valid_formids": valid_count,
                "processing_time": chunk_duration,
                "formids_per_second": len(chunk) / chunk_duration,
            })

            performance_profiler.record_operation(f"formid_chunk_{i // chunk_size}", chunk_duration, 0)

            fresh_memory_tracker.take_measurement(f"chunk_{i // chunk_size}_processed")

        total_time = time.time() - start_time

        performance_profiler.stop_profiling()
        memory_stats = fresh_memory_tracker.stop_tracking()

        # Analyze massive FormID processing
        assert total_valid_formids > massive_formid_count * 0.8, f"Too few valid FormIDs: {total_valid_formids}/{massive_formid_count}"

        # Performance should remain consistent across chunks
        processing_times = [r["processing_time"] for r in processing_results]
        if len(processing_times) > 1:
            time_variance = max(processing_times) / min(processing_times)
            assert time_variance < 3.0, f"High processing time variance: {time_variance:.2f}x"

        # Overall throughput should be reasonable
        overall_throughput = massive_formid_count / total_time
        assert overall_throughput > 10000, f"FormID processing too slow: {overall_throughput:.0f} FormIDs/sec"

        # Memory should scale reasonably
        # Note: Python has significant per-object overhead, so we allow up to 5KB per FormID
        # which accounts for the FormID string, parsed result object, and Python's memory management
        memory_per_formid = memory_stats["peak_mb"] * 1024 * 1024 / massive_formid_count  # bytes per FormID
        assert memory_per_formid < 5000, f"Excessive memory per FormID: {memory_per_formid:.1f} bytes"

    def test_formid_deduplication_at_scale(self, performance_profiler, stress_data_generator):
        """
        Test FormID deduplication performance with massive duplicate datasets.

        Simulates scenarios where the same FormIDs appear many times
        across different plugins or crash log sections.
        """
        performance_profiler.start_profiling()

        analyzer = FormIDAnalyzer()

        # Generate dataset with many duplicates
        base_formids = stress_data_generator.generate_formid_dataset(count=5000)  # 5k unique

        # Create massive dataset with duplicates (simulate multiple plugin references)
        massive_formid_list = []
        for _ in range(20):  # 20 repetitions = 100k total FormIDs
            massive_formid_list.extend(base_formids)

        total_formids = len(massive_formid_list)
        assert total_formids == 100000, f"Expected 100k FormIDs, got {total_formids}"

        # Process the massive duplicate dataset
        start_time = time.time()

        # Process in batches to simulate real-world usage
        batch_size = 5000
        unique_formids_found = set()
        processing_times = []

        for i in range(0, len(massive_formid_list), batch_size):
            batch_start = time.time()
            batch = massive_formid_list[i : i + batch_size]

            # Process batch - validate each FormID
            for formid in batch:
                parsed = analyzer.parse_formid(formid)
                if parsed is not None:
                    unique_formids_found.add(formid)

            batch_time = time.time() - batch_start
            processing_times.append(batch_time)

            performance_profiler.record_operation(f"dedup_batch_{i // batch_size}", batch_time, 0)

        total_time = time.time() - start_time

        performance_profiler.stop_profiling()

        # Analyze deduplication performance
        # Should find approximately 5000 unique FormIDs (accounting for invalid ones)
        expected_unique = len(base_formids) * 0.8  # Account for some invalid FormIDs
        assert len(unique_formids_found) >= expected_unique, (
            f"Too few unique FormIDs found: {len(unique_formids_found)}/{expected_unique:.0f}"
        )

        # Processing time should remain consistent (no degradation due to duplicates)
        if len(processing_times) > 1:
            early_avg = mean(processing_times[: len(processing_times) // 3])
            late_avg = mean(processing_times[-len(processing_times) // 3 :])
            degradation_factor = late_avg / early_avg

            assert degradation_factor < 1.5, f"Performance degradation with duplicates: {degradation_factor:.2f}x"

        # Overall throughput should remain high
        throughput = total_formids / total_time
        assert throughput > 15000, f"Deduplication throughput too low: {throughput:.0f} FormIDs/sec"

    def test_formid_cross_referencing_massive_dataset(self, performance_profiler, stress_data_generator):
        """
        Test cross-referencing FormIDs across massive plugin datasets.

        Simulates scenarios where FormIDs need to be resolved across
        hundreds of plugins in heavily modded installations.
        """
        performance_profiler.start_profiling()

        analyzer = FormIDAnalyzer()

        # Generate massive plugin list and FormIDs
        plugin_list = stress_data_generator.generate_plugin_load_order(count=500)
        formid_dataset = stress_data_generator.generate_formid_dataset(count=20000)

        # Create cross-reference mapping (simulate FormID -> Plugin relationships)
        cross_reference_data = []
        for i, formid in enumerate(formid_dataset):
            plugin_index = i % len(plugin_list)
            cross_reference_data.append({"formid": formid, "plugin": plugin_list[plugin_index], "plugin_index": plugin_index})

        # Process cross-referencing operations
        cross_ref_results = []
        start_time = time.time()

        # Batch process cross-references
        batch_size = 2000
        for i in range(0, len(cross_reference_data), batch_size):
            batch_start = time.time()
            batch = cross_reference_data[i : i + batch_size]

            # Extract FormIDs and process
            batch_formids = [item["formid"] for item in batch]

            # Simulate cross-referencing logic - validate each FormID
            valid_cross_refs = 0
            for formid in batch_formids:
                if analyzer.parse_formid(formid) is not None:
                    valid_cross_refs += 1

            batch_time = time.time() - batch_start

            cross_ref_results.append({
                "batch_index": i // batch_size,
                "formids_processed": len(batch_formids),
                "valid_cross_refs": valid_cross_refs,
                "processing_time": batch_time,
            })

            performance_profiler.record_operation(f"cross_ref_batch_{i // batch_size}", batch_time, 0)

        total_time = time.time() - start_time

        performance_profiler.stop_profiling()

        # Analyze cross-referencing performance
        total_processed = sum(r["formids_processed"] for r in cross_ref_results)
        total_valid = sum(r["valid_cross_refs"] for r in cross_ref_results)

        assert total_processed == len(formid_dataset), f"Not all FormIDs processed: {total_processed}/{len(formid_dataset)}"

        # Should have high success rate for cross-referencing
        success_rate = total_valid / total_processed
        assert success_rate > 0.75, f"Cross-referencing success rate too low: {success_rate:.1%}"

        # Processing should be efficient even with large plugin list
        throughput = total_processed / total_time
        assert throughput > 8000, f"Cross-referencing throughput too low: {throughput:.0f} refs/sec"

        # Performance should remain consistent across batches
        # Allow for some system variability in stress tests (0.8 threshold)
        processing_times = [r["processing_time"] for r in cross_ref_results]
        if len(processing_times) > 1:
            time_std = (max(processing_times) - min(processing_times)) / mean(processing_times)
            assert time_std < 0.8, f"High cross-referencing time variance: {time_std:.2f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
