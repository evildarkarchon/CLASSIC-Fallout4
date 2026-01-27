"""
Call stack processing stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests validate system performance when processing very deep
call stacks and extensive trace information from complex crashes.
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
@pytest.mark.data_volume
class TestMassiveCallStackProcessing:
    """
    Test processing of massive call stacks and trace data.

    These tests validate system performance when processing very deep
    call stacks and extensive trace information from complex crashes.
    """

    def test_deep_call_stack_processing(self, performance_profiler, fresh_memory_tracker, tmp_path, stress_data_generator):
        """
        Test processing of extremely deep call stacks (10,000+ frames).

        Simulates complex crashes with very deep call stacks that
        might occur in heavily scripted or recursion-heavy scenarios.
        """
        performance_profiler.start_profiling()
        fresh_memory_tracker.start_tracking()

        parser = LogParser()

        # Generate extremely deep call stack
        stack_depth = 10000
        formid_dataset = stress_data_generator.generate_formid_dataset(count=stack_depth)
        plugin_list = stress_data_generator.generate_plugin_load_order(count=200)

        # Create massive call stack log
        log_lines = ["Fallout 4 v1.10.163", "Buffout 4 v1.28.6", "", 'Unhandled exception "EXCEPTION_ACCESS_VIOLATION"', ""]

        # Add PLUGINS section in standard format so extract_plugins can find them
        log_lines.append("PLUGINS:")
        for idx, plugin in enumerate(plugin_list[:200]):
            log_lines.append(f"[{idx:02X}] {plugin}")
        log_lines.append("")

        log_lines.append("STACK TRACE:")

        # Generate deep call stack
        for i in range(stack_depth):
            plugin = plugin_list[i % len(plugin_list)]
            formid = formid_dataset[i]
            memory_addr = f"0x{(0x140000000 + i * 0x1000):012X}"

            log_lines.extend([
                f"\t{i:05d} Fallout4.exe+{0x500000 + i * 16:07X}",
                f"\t      FormID: {formid} ({plugin})",
                f"\t      Memory: {memory_addr}",
                f"\t      Function: deep_function_level_{i % 100}()",
            ])

            # Add some recursion patterns
            if i > 0 and i % 500 == 0:
                log_lines.append(f"\t      [RECURSION DETECTED - Level {i // 500}]")

        massive_stack_log = "\n".join(log_lines)

        # Write to file for realistic I/O testing
        log_file = tmp_path / "deep_stack.log"
        log_file.write_text(massive_stack_log, encoding="utf-8")

        fresh_memory_tracker.take_measurement("deep_stack_created")

        # Process the massive call stack
        start_time = time.time()

        # Read the file
        with AsyncBridge.get_instance() as bridge:
            io_core = FileIOCore()
            content = bridge.run_async(io_core.read_file(log_file))

        read_time = time.time() - start_time
        fresh_memory_tracker.take_measurement("file_read")

        # Convert to lines for LogParser
        content_lines = content.split("\n")

        # Extract FormIDs from deep stack
        formid_start = time.time()
        extracted_formids = parser.extract_formids(content_lines)
        formid_time = time.time() - formid_start

        fresh_memory_tracker.take_measurement("formids_extracted")

        # Extract plugins
        plugin_start = time.time()
        extracted_plugins = parser.extract_plugins(content_lines)
        plugin_time = time.time() - plugin_start

        fresh_memory_tracker.take_measurement("plugins_extracted")

        # Pattern matching for stack analysis
        pattern_start = time.time()
        pattern_matcher = PatternMatcher(["STACK TRACE", "FormID", "Function", "RECURSION"])
        stack_matches = pattern_matcher.find_all(content)
        pattern_time = time.time() - pattern_start

        fresh_memory_tracker.take_measurement("patterns_processed")

        _ = time.time() - start_time

        performance_profiler.record_operation("deep_stack_file_read", read_time)
        performance_profiler.record_operation("deep_stack_formid_extraction", formid_time)
        performance_profiler.record_operation("deep_stack_plugin_extraction", plugin_time)
        performance_profiler.record_operation("deep_stack_pattern_matching", pattern_time)

        performance_profiler.stop_profiling()
        memory_stats = fresh_memory_tracker.stop_tracking()

        # Analyze deep call stack processing
        assert len(extracted_formids) >= stack_depth * 0.8, (
            f"Too few FormIDs extracted from deep stack: {len(extracted_formids)}/{stack_depth}"
        )

        assert len(extracted_plugins) >= 150, f"Too few plugins extracted from deep stack: {len(extracted_plugins)}"

        # Performance should be reasonable even with deep stacks
        assert formid_time < 20.0, f"FormID extraction from deep stack too slow: {formid_time:.2f}s"
        assert plugin_time < 15.0, f"Plugin extraction from deep stack too slow: {plugin_time:.2f}s"

        # Memory usage should be efficient
        # Note: Peak memory includes Python runtime and test infrastructure overhead
        memory_per_frame = memory_stats["peak_mb"] * 1024 / stack_depth  # KB per stack frame
        assert memory_per_frame < 50.0, f"Excessive memory per stack frame: {memory_per_frame:.2f}KB"

        # Should detect recursion patterns - count by filtering matches containing RECURSION
        recursion_matches = sum(1 for pos, text in stack_matches if "RECURSION" in text)
        expected_recursion = stack_depth // 500  # One recursion marker every 500 frames
        assert recursion_matches >= expected_recursion * 0.8, (
            f"Too few recursion patterns detected: {recursion_matches}/{expected_recursion}"
        )

    def test_massive_memory_dump_analysis(self, performance_profiler, fresh_memory_tracker, stress_data_generator):
        """
        Test analysis of massive memory dump information.

        Simulates processing of extensive memory dump data with
        thousands of memory regions and allocations.
        """
        performance_profiler.start_profiling()
        fresh_memory_tracker.start_tracking()

        parser = LogParser()

        # Generate massive memory dump data
        memory_region_count = 5000
        formid_dataset = stress_data_generator.generate_formid_dataset(count=memory_region_count)

        # Create massive memory dump log
        log_sections = ["Fallout 4 v1.10.163", "Memory Dump Analysis", "", "MEMORY REGIONS:"]

        for i in range(memory_region_count):
            base_addr = 0x7FF000000000 + (i * 0x10000)  # 64KB regions
            size = 0x10000 + (i % 8192)  # Variable sizes
            protection = ["PAGE_READWRITE", "PAGE_READONLY", "PAGE_EXECUTE_READ"][i % 3]
            state = ["COMMITTED", "RESERVED", "FREE"][i % 3]

            log_sections.extend([
                f"Region {i:05d}:",
                f"\tBase Address: 0x{base_addr:012X}",
                f"\tSize: {size:,} bytes",
                f"\tProtection: {protection}",
                f"\tState: {state}",
                f"\tFormID: {formid_dataset[i]}",  # Use FormID: format that parser can recognize
                "",
            ])

            # Add some heap allocation information
            if i % 100 == 0:
                log_sections.extend([
                    "\tHEAP ALLOCATIONS:",
                    f"\t  Active Allocations: {(i // 100 + 1) * 50}",
                    f"\t  Total Allocated: {(i // 100 + 1) * 1024 * 1024:,} bytes",
                    f"\t  Fragmentation: {(i % 10) * 10}%",
                    "",
                ])

        massive_memory_dump = "\n".join(log_sections)

        fresh_memory_tracker.take_measurement("memory_dump_created")

        # Process the massive memory dump
        start_time = time.time()

        # Extract FormIDs from memory dump
        formid_start = time.time()
        extracted_formids = parser.extract_formids(log_sections)
        formid_time = time.time() - formid_start

        fresh_memory_tracker.take_measurement("formids_extracted")

        # Pattern matching for memory analysis
        pattern_start = time.time()
        pattern_matcher = PatternMatcher(["MEMORY REGIONS", "Base Address", "FormID:", "HEAP ALLOCATIONS"])
        memory_matches = pattern_matcher.find_all(massive_memory_dump)
        pattern_time = time.time() - pattern_start

        fresh_memory_tracker.take_measurement("patterns_matched")

        # Process lines for memory statistics - use Python string operations
        lines_start = time.time()
        lines = massive_memory_dump.split("\n")
        processed_lines = [line.strip() for line in lines[:10000]]  # Process subset
        lines_time = time.time() - lines_start

        fresh_memory_tracker.take_measurement("lines_processed")

        _ = time.time() - start_time

        performance_profiler.record_operation("memory_dump_formid_extraction", formid_time)
        performance_profiler.record_operation("memory_dump_pattern_matching", pattern_time)
        performance_profiler.record_operation("memory_dump_line_processing", lines_time)

        performance_profiler.stop_profiling()
        memory_stats = fresh_memory_tracker.stop_tracking()

        # Analyze memory dump processing
        assert len(extracted_formids) >= memory_region_count * 0.8, (
            f"Too few FormIDs extracted from memory dump: {len(extracted_formids)}/{memory_region_count}"
        )

        # Should find memory-related patterns
        total_memory_matches = len(memory_matches)
        assert total_memory_matches >= memory_region_count, f"Too few memory patterns found: {total_memory_matches}"

        # Performance should be reasonable for massive memory dump
        assert formid_time < 15.0, f"Memory dump FormID extraction too slow: {formid_time:.2f}s"
        assert pattern_time < 10.0, f"Memory dump pattern matching too slow: {pattern_time:.2f}s"

        # Memory efficiency should be maintained
        # Note: peak_mb includes entire Python process memory (runtime, test infrastructure, etc.)
        # so the ratio is not a meaningful measure of processing efficiency
        processing_memory_mb = memory_stats["peak_mb"]
        memory_dump_size_mb = len(massive_memory_dump.encode("utf-8")) / (1024 * 1024)
        memory_ratio = processing_memory_mb / max(memory_dump_size_mb, 0.001)  # Avoid division by zero

        # Use a generous threshold since peak_mb includes Python runtime overhead
        assert memory_ratio < 1000.0, f"Excessive memory usage ratio: {memory_ratio:.2f}x"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
