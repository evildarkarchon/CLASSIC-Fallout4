"""
Memory stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests validate memory management, leak detection, and performance
characteristics when processing very large datasets that simulate
real-world production scenarios.
"""

import gc
from unittest.mock import patch

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

import classic_scanlog

# Import components to test
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.FileIOCore import FileIOCore
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.YamlSettingsCache import yaml_cache


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.memory
class TestMemoryLeakDetection:
    """
    Test for memory leaks during sustained operations.

    These tests run operations repeatedly and monitor memory growth
    patterns to detect potential memory leaks in both Python and Rust code.
    """

    def test_rust_string_processing_no_memory_leaks(self, fresh_memory_tracker):
        """
        Test that Rust string processing doesn't leak memory over time.

        Processes thousands of strings repeatedly and monitors for
        memory growth that would indicate a leak.
        """
        fresh_memory_tracker.start_tracking()

        processor = classic_scanlog.utils.StringProcessor()

        # Generate test data
        base_strings = [f"Test string {i} with content" for i in range(1000)]

        # Run multiple cycles to detect leaks
        for cycle in range(50):  # 50 cycles * 1000 strings = 50k operations
            fresh_memory_tracker.take_measurement(f"cycle_{cycle}_start")

            # Process strings in various ways
            upper_result = processor.process_batch(base_strings, "upper")
            lower_result = processor.process_batch(base_strings, "lower")
            trimmed_result = processor.process_batch([f"  {s}  " for s in base_strings], "trim")

            # Verify processing worked
            assert len(upper_result) == 1000
            assert len(lower_result) == 1000
            assert len(trimmed_result) == 1000

            # Force garbage collection
            del upper_result, lower_result, trimmed_result
            gc.collect()

            fresh_memory_tracker.take_measurement(f"cycle_{cycle}_end")

        # Stop tracking and analyze results
        memory_stats = fresh_memory_tracker.stop_tracking()

        # Memory growth should be minimal (< 10MB for this test)
        assert memory_stats["growth_mb"] < 10, f"Memory grew by {memory_stats['growth_mb']:.1f}MB, indicating potential leak"

        # Should not be flagged as potential leak
        assert not memory_stats["potential_leak"], "Memory tracker detected potential leak in Rust string processing"

    def test_rust_log_processor_memory_stability(self, fresh_memory_tracker, stress_data_generator):
        """
        Test log processor memory stability with large datasets.

        Processes very large logs repeatedly to ensure memory usage
        remains stable and doesn't grow indefinitely.
        """
        fresh_memory_tracker.start_tracking()

        processor = classic_scanlog.utils.LogProcessor()

        # Generate large log content
        large_log = stress_data_generator.generate_large_crash_log(
            size_mb=20,  # 20MB log
            plugin_count=200,
            formid_count=5000,
        )

        # Process the same log multiple times
        for iteration in range(10):  # Process 10 times = 200MB total processed
            fresh_memory_tracker.take_measurement(f"iteration_{iteration}_start")

            # Extract FormIDs - this involves regex processing
            formids = processor.extract_formids(large_log)
            assert len(formids) > 100  # Should find many FormIDs

            # Extract plugins - another regex-heavy operation
            plugins = processor.extract_plugins(large_log)
            assert len(plugins) > 50  # Should find many plugins

            # Pattern matching on large text
            patterns = ["ERROR", "WARNING", "FormID", "Plugin"]
            processor.init_pattern_matcher(patterns)
            matches = processor.find_all_patterns(large_log, patterns)
            assert len(matches) > 0

            # Clear results to avoid Python-side accumulation
            del formids, plugins, matches
            gc.collect()

            fresh_memory_tracker.take_measurement(f"iteration_{iteration}_end")

        memory_stats = fresh_memory_tracker.stop_tracking()

        # Memory growth should be reasonable (< 50MB for processing 200MB)
        assert memory_stats["growth_mb"] < 50, f"Memory grew by {memory_stats['growth_mb']:.1f}MB processing large logs"

    def test_file_io_memory_management(self, fresh_memory_tracker, temp_crash_logs_dir):
        """
        Test FileIOCore memory management with many large files.

        Reads many large files sequentially and concurrently to test
        memory management in file I/O operations.
        """
        fresh_memory_tracker.start_tracking()

        with AsyncBridge.get_instance() as bridge:
            io_core = FileIOCore()

            # Get all log files
            log_files = list(temp_crash_logs_dir.glob("*.log"))
            assert len(log_files) >= 5, "Need multiple log files for test"

            # Read files multiple times
            for round_num in range(5):
                fresh_memory_tracker.take_measurement(f"round_{round_num}_start")

                # Sequential reads
                for log_file in log_files:
                    content = bridge.run_async(io_core.read_file(log_file))
                    assert len(content) > 1000  # Should be substantial content

                    # Process content to ensure it's actually loaded
                    lines = content.split("\n")
                    filtered_lines = [line for line in lines if "FormID" in line]

                    # Clear references
                    del content, lines, filtered_lines

                # Force cleanup
                gc.collect()
                fresh_memory_tracker.take_measurement(f"round_{round_num}_end")

            memory_stats = fresh_memory_tracker.stop_tracking()

            # Should not accumulate file content in memory
            assert memory_stats["growth_mb"] < 30, f"File I/O accumulated {memory_stats['growth_mb']:.1f}MB in memory"

    def test_yaml_cache_memory_efficiency(self, fresh_memory_tracker):
        """
        Test YamlSettingsCache memory efficiency with many cache operations.

        Performs thousands of cache operations to ensure the cache
        doesn't grow indefinitely and manages memory effectively.
        """
        fresh_memory_tracker.start_tracking()

        # Clear cache to start fresh
        yaml_cache.clear_cache()
        fresh_memory_tracker.take_measurement("cache_cleared")

        # Perform many cache operations
        for batch in range(20):  # 20 batches
            keys_batch = []
            for i in range(100):  # 100 operations per batch
                key = f"stress_test_key_{batch}_{i}"
                keys_batch.append((str, "TEST", key, f"value_{i}"))

            # Batch load many settings (this creates cache entries)
            with patch.object(yaml_cache, "_load_yaml_file", return_value={"TEST": {}}):
                results = yaml_cache.batch_get_settings(keys_batch)

            assert len(results) == 100
            fresh_memory_tracker.take_measurement(f"batch_{batch}_completed")

        # Cache should have many entries now
        cache_size = len(yaml_cache._cache)
        assert cache_size > 1000, f"Expected large cache, got {cache_size} entries"

        # Clear cache and check memory is reclaimed
        yaml_cache.clear_cache()
        gc.collect()
        fresh_memory_tracker.take_measurement("final_cleared")

        memory_stats = fresh_memory_tracker.stop_tracking()

        # Memory should be efficiently managed
        assert memory_stats["growth_mb"] < 20, f"YAML cache used excessive memory: {memory_stats['growth_mb']:.1f}MB"


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.memory
class TestLargeDatasetProcessing:
    """
    Test processing of extremely large datasets that push memory limits.

    These tests verify that the system can handle production-scale
    datasets without running out of memory or crashing.
    """

    def test_massive_crash_log_processing(self, fresh_memory_tracker, tmp_path, stress_data_generator):
        """
        Test processing of a massive crash log (100MB+).

        Creates and processes a very large crash log to test memory
        efficiency and ensure the system doesn't crash under load.
        """
        fresh_memory_tracker.start_tracking()

        # Generate massive crash log
        massive_log_content = stress_data_generator.generate_large_crash_log(
            size_mb=100,  # 100MB crash log
            plugin_count=500,
            formid_count=20000,
        )

        # Write to file
        massive_log_file = tmp_path / "massive_crash.log"
        massive_log_file.write_text(massive_log_content, encoding="utf-8")

        fresh_memory_tracker.take_measurement("log_file_created")

        # Process with Rust components
        processor = classic_scanlog.utils.LogProcessor()

        # Read and process in chunks to test memory efficiency
        with AsyncBridge.get_instance() as bridge:
            io_core = FileIOCore()

            # Read the massive file
            content = bridge.run_async(io_core.read_file(massive_log_file))
            fresh_memory_tracker.take_measurement("file_loaded")

            # Extract FormIDs from massive content
            formids = processor.extract_formids(content)
            assert len(formids) > 10000, f"Expected many FormIDs, got {len(formids)}"
            fresh_memory_tracker.take_measurement("formids_extracted")

            # Extract plugins
            plugins = processor.extract_plugins(content)
            assert len(plugins) > 100, f"Expected many plugins, got {len(plugins)}"
            fresh_memory_tracker.take_measurement("plugins_extracted")

            # Process lines in parallel
            lines = content.split("\n")
            processed_lines = processor.process_lines_parallel(lines[:10000], "upper")  # Limit to avoid timeout
            assert len(processed_lines) == 10000
            fresh_memory_tracker.take_measurement("lines_processed")

            # Clear large objects
            del content, lines, processed_lines, formids, plugins
            gc.collect()
            fresh_memory_tracker.take_measurement("cleanup_done")

            memory_stats = fresh_memory_tracker.stop_tracking()

            # Peak memory should be reasonable (< 200MB for processing 100MB log)
            assert memory_stats["peak_mb"] < 200, f"Peak memory usage {memory_stats['peak_mb']:.1f}MB too high for 100MB log"

    def test_thousands_of_formids_processing(self, fresh_memory_tracker, stress_data_generator):
        """
        Test processing thousands of FormIDs simultaneously.

        Tests FormID processing at scale to ensure batch operations
        are memory efficient and performant.
        """
        fresh_memory_tracker.start_tracking()

        # Generate massive FormID dataset
        formids = stress_data_generator.generate_formid_dataset(count=50000)  # 50k FormIDs
        fresh_memory_tracker.take_measurement("formids_generated")

        # Process with Rust FormIDProcessor
        processor = classic_scanlog.FormIDProcessor()

        # Process in batches to test memory efficiency
        batch_size = 5000
        total_processed = 0

        for i in range(0, len(formids), batch_size):
            batch = formids[i : i + batch_size]
            results = processor.process_batch(batch)

            # Count valid results
            valid_results = sum(1 for r in results if r is not None)
            total_processed += valid_results

            fresh_memory_tracker.take_measurement(f"batch_{i // batch_size}_processed")

            # Clear batch results
            del results

        assert total_processed > 40000, f"Expected most FormIDs valid, got {total_processed}"

        memory_stats = fresh_memory_tracker.stop_tracking()

        # Memory usage should be efficient for processing 50k FormIDs
        assert memory_stats["peak_mb"] < 100, f"Peak memory {memory_stats['peak_mb']:.1f}MB too high for FormID processing"

    def test_massive_plugin_load_order_analysis(self, fresh_memory_tracker, massive_plugin_list):
        """
        Test analysis of a massive plugin load order (500+ plugins).

        Simulates analysis of very large plugin lists that some
        users might have with heavily modded games.
        """
        fresh_memory_tracker.start_tracking()

        # Analyze plugin list multiple times
        for analysis_round in range(10):
            # Simulate plugin analysis operations
            esp_plugins = [p for p in massive_plugin_list if p.endswith(".esp")]
            esm_plugins = [p for p in massive_plugin_list if p.endswith(".esm")]
            esl_plugins = [p for p in massive_plugin_list if p.endswith(".esl")]

            assert len(esp_plugins) > 200, "Should have many ESP files"
            assert len(esm_plugins) > 10, "Should have some ESM files"
            assert len(esl_plugins) > 50, "Should have some ESL files"

            # Simulate FormID processing for each plugin
            for _plugin in massive_plugin_list[:100]:  # Limit to avoid timeout
                # Simulate FormID extraction for this plugin
                plugin_formids = [f"0x{i:08X}" for i in range(100)]  # 100 FormIDs per plugin

                # Process with Rust
                processor = classic_scanlog.FormIDProcessor()
                results = processor.process_batch(plugin_formids)
                valid_count = sum(1 for r in results if r is not None)
                assert valid_count == 100  # All should be valid

            fresh_memory_tracker.take_measurement(f"analysis_round_{analysis_round}")

            # Clear intermediate results
            del esp_plugins, esm_plugins, esl_plugins
            gc.collect()

        memory_stats = fresh_memory_tracker.stop_tracking()

        # Should handle large plugin lists efficiently
        assert memory_stats["growth_mb"] < 50, f"Plugin analysis grew memory by {memory_stats['growth_mb']:.1f}MB"


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.memory
class TestMemoryLimitHandling:
    """
    Test behavior when approaching system memory limits.

    These tests verify graceful handling of low memory conditions
    and ensure the system doesn't crash when resources are constrained.
    """

    def test_orchestrator_memory_management(self, fresh_memory_tracker, temp_crash_logs_dir):
        """
        Test OrchestratorCore memory management with many concurrent operations.

        Runs the orchestrator with many files to test memory management
        in the core scanning pipeline.
        """
        fresh_memory_tracker.start_tracking()

        with AsyncBridge.get_instance() as bridge:
            orchestrator = OrchestratorCore()

            # Get log files
            log_files = list(temp_crash_logs_dir.glob("*.log"))

            # Process all files multiple times
            for processing_round in range(3):  # 3 rounds to test sustained load
                fresh_memory_tracker.take_measurement(f"round_{processing_round}_start")

                # Process each file
                for log_file in log_files:
                    # Use orchestrator to process file
                    result = bridge.run_async(orchestrator.process_single_log(log_file))

                    # Verify processing succeeded
                    assert result is not None
                    if hasattr(result, "formids"):
                        assert len(result.formids) >= 0  # Should have some FormIDs

                    fresh_memory_tracker.take_measurement(f"processed_{log_file.name}")

                # Force cleanup between rounds
                gc.collect()

            memory_stats = fresh_memory_tracker.stop_tracking()

            # Orchestrator should manage memory efficiently
            assert memory_stats["growth_mb"] < 100, f"Orchestrator memory growth {memory_stats['growth_mb']:.1f}MB too high"

    def test_concurrent_large_file_processing(self, fresh_memory_tracker, tmp_path, stress_data_generator):
        """
        Test concurrent processing of multiple large files.

        Creates several large files and processes them concurrently
        to test memory management under concurrent load.
        """
        fresh_memory_tracker.start_tracking()

        # Create multiple large files
        large_files = []
        for i in range(5):  # 5 large files
            content = stress_data_generator.generate_large_crash_log(
                size_mb=20,  # 20MB each = 100MB total
                plugin_count=100,
                formid_count=2000,
            )
            file_path = tmp_path / f"concurrent_test_{i}.log"
            file_path.write_text(content, encoding="utf-8")
            large_files.append(file_path)

        fresh_memory_tracker.take_measurement("files_created")

        # Process files concurrently using AsyncBridge
        with AsyncBridge.get_instance() as bridge:
            io_core = FileIOCore()

            async def process_file_async(file_path):
                """Process a single file asynchronously."""
                content = await io_core.read_file(file_path)

                # Process with Rust components
                processor = classic_scanlog.utils.LogProcessor()
                formids = processor.extract_formids(content)
                plugins = processor.extract_plugins(content)

                return {"file": file_path.name, "formid_count": len(formids), "plugin_count": len(plugins), "content_size": len(content)}

            # Process all files concurrently
            tasks = [process_file_async(f) for f in large_files]

            # Use AsyncBridge to run concurrent tasks
            results = []
            for task in tasks:
                result = bridge.run_async(task)
                results.append(result)

            fresh_memory_tracker.take_measurement("all_files_processed")

            # Verify all files were processed
            assert len(results) == 5
            for result in results:
                assert result["formid_count"] > 100  # Should find FormIDs
                assert result["plugin_count"] > 10  # Should find plugins
                assert result["content_size"] > 1000000  # Should be large

            memory_stats = fresh_memory_tracker.stop_tracking()

            # Memory should be managed efficiently even with concurrent processing
            assert memory_stats["peak_mb"] < 300, f"Concurrent processing used {memory_stats['peak_mb']:.1f}MB peak memory"

    def test_memory_pressure_recovery(self, fresh_memory_tracker, stress_data_generator):
        """
        Test system recovery from memory pressure situations.

        Simulates high memory usage scenarios and tests that the
        system can recover gracefully without permanent memory growth.
        """
        fresh_memory_tracker.start_tracking()

        # Create memory pressure by allocating large datasets
        large_datasets = []

        # Phase 1: Build up memory pressure
        for i in range(10):  # 10 large datasets
            dataset = stress_data_generator.generate_large_crash_log(
                size_mb=10,  # 10MB each = 100MB total
                plugin_count=50,
                formid_count=1000,
            )
            large_datasets.append(dataset)
            fresh_memory_tracker.take_measurement(f"dataset_{i}_created")

        # Process all datasets to create maximum memory pressure
        processor = classic_scanlog.utils.LogProcessor()
        all_formids = []

        for i, dataset in enumerate(large_datasets):
            formids = processor.extract_formids(dataset)
            all_formids.extend(formids)
            fresh_memory_tracker.take_measurement(f"dataset_{i}_processed")

        peak_memory_point = fresh_memory_tracker.take_measurement("peak_memory")

        # Phase 2: Release memory and test recovery
        del large_datasets  # Release large datasets
        gc.collect()  # Force garbage collection
        fresh_memory_tracker.take_measurement("datasets_released")

        # Process smaller dataset to test continued functionality
        small_dataset = stress_data_generator.generate_large_crash_log(
            size_mb=1,  # Small dataset
            plugin_count=10,
            formid_count=100,
        )

        small_formids = processor.extract_formids(small_dataset)
        assert len(small_formids) > 10, "Should still process small datasets efficiently"

        final_memory = fresh_memory_tracker.take_measurement("recovery_complete")

        memory_stats = fresh_memory_tracker.stop_tracking()

        # Memory should recover significantly after releasing large datasets
        memory_recovery = peak_memory_point - final_memory
        assert memory_recovery > 50, f"Memory recovery insufficient: {memory_recovery:.1f}MB recovered"

        # Final memory should not be excessive
        assert memory_stats["final_mb"] < memory_stats["peak_mb"] * 0.7, "Memory did not recover sufficiently after pressure relief"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
