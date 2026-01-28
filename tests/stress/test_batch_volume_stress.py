"""
Batch processing stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests validate system performance when processing hundreds
of crash logs simultaneously in batch operations.
"""

import asyncio
import time
from statistics import mean
from unittest.mock import MagicMock

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

from classic_scanlog import LogParser

# Import components to test
from ClassicLib.scanning.logs.orchestrator_core import OrchestratorCore


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.data_volume
class TestBatchProcessingAtScale:
    """
    Test batch processing capabilities at massive scale.

    These tests validate system performance when processing hundreds
    of crash logs simultaneously in batch operations.
    """

    @pytest.mark.asyncio
    async def test_hundred_crash_log_batch_processing(self, performance_profiler, fresh_memory_tracker, tmp_path, stress_data_generator):
        """
        Test batch processing of 100+ crash logs simultaneously.

        Simulates batch processing scenarios that might occur in
        automated analysis systems processing many crash logs.
        """
        performance_profiler.start_profiling()
        fresh_memory_tracker.start_tracking()

        # Create 100 crash log files
        batch_size = 100
        crash_log_files = []

        for i in range(batch_size):
            content = stress_data_generator.generate_large_crash_log(
                size_mb=2,  # 2MB per log
                plugin_count=50,
                formid_count=500,
            )

            file_path = tmp_path / f"batch_crash_{i:03d}.log"
            file_path.write_text(content, encoding="utf-8")
            crash_log_files.append(file_path)

        fresh_memory_tracker.take_measurement("batch_files_created")

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

        async with OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        ) as orchestrator:
            # Process batch sequentially (simulating single-threaded batch processing)
            sequential_start = time.time()
            sequential_results = []

            for i, log_file in enumerate(crash_log_files):
                file_start = time.time()

                # Process single log through orchestrator
                result = await orchestrator.process_crash_log(log_file)

                file_time = time.time() - file_start

                sequential_results.append({
                    "file_index": i,
                    "filename": log_file.name,
                    "processing_time": file_time,
                    "success": result is not None,
                })

                performance_profiler.record_operation(f"batch_sequential_{i}", file_time)

                # Memory checkpoint every 20 files
                if i % 20 == 0:
                    fresh_memory_tracker.take_measurement(f"sequential_{i}")

            sequential_total_time = time.time() - sequential_start

            fresh_memory_tracker.take_measurement("sequential_batch_complete")

            # Process batch with concurrency using asyncio.gather
            concurrent_start = time.time()

            async def process_single_file(file_path):
                """Process a single file and return timing information."""
                start = time.time()
                try:
                    result = await orchestrator.process_crash_log(file_path)
                    return {
                        "filename": file_path.name,
                        "processing_time": time.time() - start,
                        "success": result is not None,
                        "error": None,
                    }
                except Exception as e:
                    return {"filename": file_path.name, "processing_time": time.time() - start, "success": False, "error": str(e)}

            # Use asyncio.gather for concurrent processing
            concurrent_results = await asyncio.gather(*[process_single_file(f) for f in crash_log_files])

            concurrent_total_time = time.time() - concurrent_start

            fresh_memory_tracker.take_measurement("concurrent_batch_complete")

            performance_profiler.record_operation("batch_sequential_total", sequential_total_time)
            performance_profiler.record_operation("batch_concurrent_total", concurrent_total_time)

        performance_profiler.stop_profiling()
        memory_stats = fresh_memory_tracker.stop_tracking()

        # Analyze batch processing performance
        sequential_successes = sum(1 for r in sequential_results if r["success"])
        concurrent_successes = sum(1 for r in concurrent_results if r["success"])

        assert sequential_successes >= batch_size * 0.9, f"Sequential batch success rate too low: {sequential_successes}/{batch_size}"

        assert concurrent_successes >= batch_size * 0.9, f"Concurrent batch success rate too low: {concurrent_successes}/{batch_size}"

        # Concurrent processing should be faster (at least 1.3x speedup with async I/O)
        # Note: Using 1.3x threshold to account for timing variance in CI environments
        speedup = sequential_total_time / concurrent_total_time if concurrent_total_time > 0 else 1.0
        assert speedup > 1.3, f"Insufficient concurrent speedup: {speedup:.2f}x"

        # Individual file processing times should be reasonable
        sequential_times = [r["processing_time"] for r in sequential_results if r["success"]]
        concurrent_times = [r["processing_time"] for r in concurrent_results if r["success"]]

        if sequential_times:
            seq_avg = mean(sequential_times)
            assert seq_avg < 5.0, f"Sequential processing too slow: {seq_avg:.2f}s per file"

        if concurrent_times:
            conc_avg = mean(concurrent_times)
            assert conc_avg < 8.0, f"Concurrent processing too slow: {conc_avg:.2f}s per file"

        # Memory should be managed efficiently
        total_log_size_mb = batch_size * 2  # 2MB per log
        peak_memory_mb = memory_stats["peak_mb"]
        memory_efficiency = peak_memory_mb / total_log_size_mb

        assert memory_efficiency < 3.0, f"Memory efficiency poor: {memory_efficiency:.2f}x total log size"

    def test_streaming_batch_processing(self, performance_profiler, tmp_path, stress_data_generator):
        """
        Test streaming batch processing to handle memory constraints.

        Simulates processing of many large files using streaming
        techniques to maintain constant memory usage.
        """
        performance_profiler.start_profiling()

        parser = LogParser()

        # Create many medium-sized files for streaming processing
        file_count = 200
        log_files = []

        for i in range(file_count):
            content = stress_data_generator.generate_large_crash_log(
                size_mb=1,  # 1MB per log for streaming test
                plugin_count=30,
                formid_count=300,
            )

            file_path = tmp_path / f"stream_log_{i:03d}.log"
            file_path.write_text(content, encoding="utf-8")
            log_files.append(file_path)

        # Process files in streaming fashion (small batches)
        stream_batch_size = 5  # Process 5 files at a time
        streaming_results = []

        total_formids = 0
        total_plugins = 0
        processing_times = []

        start_time = time.time()

        for i in range(0, len(log_files), stream_batch_size):
            batch_start = time.time()
            batch_files = log_files[i : i + stream_batch_size]

            batch_formids = 0
            batch_plugins = 0

            for file_path in batch_files:
                # Read and process file
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                # Extract data
                formids = parser.extract_formids(lines)
                plugins = parser.extract_plugins(lines)

                batch_formids += len(formids)
                batch_plugins += len(plugins)

                # Clear content to simulate streaming
                del content, lines, formids, plugins

            batch_time = time.time() - batch_start
            processing_times.append(batch_time)

            total_formids += batch_formids
            total_plugins += batch_plugins

            streaming_results.append({
                "batch_index": i // stream_batch_size,
                "files_processed": len(batch_files),
                "formids_found": batch_formids,
                "plugins_found": batch_plugins,
                "processing_time": batch_time,
            })

            performance_profiler.record_operation(f"streaming_batch_{i // stream_batch_size}", batch_time)

        total_time = time.time() - start_time

        performance_profiler.record_operation("streaming_total", total_time)

        performance_profiler.stop_profiling()

        # Analyze streaming batch processing
        # Note: generate_large_crash_log creates formid_count // 10 FormIDs per file
        # With formid_count=300, that's 30 FormIDs per file, so 200 * 30 = 6000 total
        expected_formids_per_file = 300 // 10  # 30 FormIDs per file from generator
        assert total_formids > file_count * expected_formids_per_file * 0.8, f"Too few FormIDs from streaming processing: {total_formids}"

        assert total_plugins > file_count * 20, f"Too few plugins from streaming processing: {total_plugins}"

        # Processing times should remain consistent (no memory accumulation)
        if len(processing_times) > 10:
            early_batches = processing_times[: len(processing_times) // 3]
            late_batches = processing_times[-len(processing_times) // 3 :]

            early_avg = mean(early_batches)
            late_avg = mean(late_batches)
            degradation = late_avg / early_avg

            assert degradation < 1.5, f"Performance degradation in streaming: {degradation:.2f}x"

        # Overall throughput should be reasonable
        throughput = file_count / total_time
        assert throughput > 10, f"Streaming throughput too low: {throughput:.1f} files/sec"

        # Memory usage should remain stable (validated by consistent timing)
        # This is indirectly tested by the degradation check above


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
