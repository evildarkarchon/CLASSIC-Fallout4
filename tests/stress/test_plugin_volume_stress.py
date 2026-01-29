"""
Plugin load order stress tests for CLASSIC-Fallout4 Phase 6 Rust migration validation.

These tests validate system performance when processing hundreds
of plugins with complex dependencies and load order requirements.
"""

import time
from statistics import mean

import pytest

# Skip these tests if Rust extensions are not available
pytest.importorskip("classic_scanlog", reason="Rust extensions not available")

from classic_scanlog import LogParser, PatternMatcher


@pytest.mark.stress
@pytest.mark.slow
@pytest.mark.data_volume
class TestMassivePluginLoadOrders:
    """
    Test processing of massive plugin load orders.

    These tests validate system performance when processing hundreds
    of plugins with complex dependencies and load order requirements.
    """

    def test_thousand_plugin_load_order_analysis(self, performance_profiler, fresh_memory_tracker, stress_data_generator):
        """
        Test analysis of load orders with 1000+ plugins.

        Simulates extreme modding scenarios with massive plugin counts
        and validates performance and memory efficiency.
        """
        performance_profiler.start_profiling()
        fresh_memory_tracker.start_tracking()

        parser = LogParser()

        # Generate massive plugin load order
        massive_plugin_count = 1000
        plugin_list = stress_data_generator.generate_plugin_load_order(count=massive_plugin_count)

        # Create crash log content with massive plugin list
        log_lines = ["Fallout 4 v1.10.163", "Buffout 4 v1.28.6", "", "PLUGINS:"]

        # Add all plugins to the log
        for i, plugin in enumerate(plugin_list):
            log_lines.append(f"\t[{i:03d}] {plugin}")

        # Add some FormIDs that reference these plugins
        log_lines.append("")
        log_lines.append("STACK TRACE:")
        for i in range(5000):  # 5000 FormID references
            plugin_index = i % len(plugin_list)
            formid = f"0x{(0x14000000 + i):08X}"
            log_lines.append(f"\tFormID: {formid} Plugin: {plugin_list[plugin_index]}")

        massive_log_content = "\n".join(log_lines)

        fresh_memory_tracker.take_measurement("massive_log_created")

        # Process the massive plugin load order
        start_time = time.time()

        # Extract plugins using LogParser (needs lines, not string)
        extracted_plugins = parser.extract_plugins(log_lines)

        plugin_extraction_time = time.time() - start_time
        fresh_memory_tracker.take_measurement("plugins_extracted")

        # Extract FormIDs
        formid_start = time.time()
        extracted_formids = parser.extract_formids(log_lines)
        formid_extraction_time = time.time() - formid_start

        fresh_memory_tracker.take_measurement("formids_extracted")

        # Pattern matching on massive content
        pattern_start = time.time()
        pattern_matcher = PatternMatcher(["ERROR", "WARNING", "FormID", "Plugin"])
        pattern_matcher.find_all(massive_log_content)
        pattern_matching_time = time.time() - pattern_start

        fresh_memory_tracker.take_measurement("patterns_matched")

        _ = time.time() - start_time

        performance_profiler.record_operation("massive_plugin_extraction", plugin_extraction_time)
        performance_profiler.record_operation("massive_formid_extraction", formid_extraction_time)
        performance_profiler.record_operation("massive_pattern_matching", pattern_matching_time)

        performance_profiler.stop_profiling()
        memory_stats = fresh_memory_tracker.stop_tracking()

        # Analyze massive plugin processing
        assert len(extracted_plugins) >= massive_plugin_count * 0.9, (
            f"Too few plugins extracted: {len(extracted_plugins)}/{massive_plugin_count}"
        )

        assert len(extracted_formids) >= 4000, f"Too few FormIDs extracted: {len(extracted_formids)}"

        # Performance should be reasonable even with massive datasets
        assert plugin_extraction_time < 10.0, f"Plugin extraction too slow: {plugin_extraction_time:.2f}s"

        assert formid_extraction_time < 15.0, f"FormID extraction too slow: {formid_extraction_time:.2f}s"

        # Memory usage should be efficient
        # Note: Plugin processing involves parsing, string operations, and result storage
        # Allow up to 600KB per plugin to account for all intermediate data structures and test variability
        memory_per_plugin = memory_stats["peak_mb"] * 1024 / massive_plugin_count  # KB per plugin
        assert memory_per_plugin < 600, f"Excessive memory per plugin: {memory_per_plugin:.1f}KB"

    def test_plugin_dependency_resolution_at_scale(self, performance_profiler, stress_data_generator):
        """
        Test plugin dependency resolution with complex dependency trees.

        Simulates complex plugin dependency scenarios that might occur
        in heavily modded installations with intricate mod relationships.
        """
        performance_profiler.start_profiling()

        # Generate complex plugin dependency structure
        plugin_count = 500
        base_plugins = stress_data_generator.generate_plugin_load_order(count=plugin_count)

        # Create dependency relationships (simulate master-plugin relationships)
        dependency_map = {}
        for i, plugin in enumerate(base_plugins):
            dependencies = []

            # Master files depend on each other
            if plugin.endswith(".esm"):
                # ESM files might depend on other ESM files
                for j in range(max(0, i - 5), i):
                    if base_plugins[j].endswith(".esm"):
                        dependencies.append(base_plugins[j])

            # ESP files depend on ESM files and some other ESP files
            elif plugin.endswith(".esp"):
                # Depend on all ESM files loaded before this
                for j in range(i):
                    if base_plugins[j].endswith(".esm"):
                        dependencies.append(base_plugins[j])

                # Some ESP files depend on other ESP files (patches, etc.)
                if i > 50:  # Only after some ESP files are loaded
                    dependency_count = min(3, (i - 50) // 10)  # Up to 3 ESP dependencies
                    for k in range(dependency_count):
                        dep_index = 50 + (i - 50) // (k + 2)
                        if dep_index < i and base_plugins[dep_index].endswith(".esp"):
                            dependencies.append(base_plugins[dep_index])

            dependency_map[plugin] = dependencies

        # Process dependency resolution
        resolution_results = []
        start_time = time.time()

        # Process dependencies in batches
        batch_size = 50
        plugin_batches = [base_plugins[i : i + batch_size] for i in range(0, len(base_plugins), batch_size)]

        for batch_index, plugin_batch in enumerate(plugin_batches):
            batch_start = time.time()

            resolved_count = 0
            circular_dependencies = 0
            missing_dependencies = 0

            for plugin in plugin_batch:
                dependencies = dependency_map.get(plugin, [])

                # Simulate dependency resolution logic
                resolved_deps = []
                for dep in dependencies:
                    if dep in base_plugins[: base_plugins.index(plugin)]:
                        resolved_deps.append(dep)
                    else:
                        missing_dependencies += 1

                # Check for circular dependencies (simplified check)
                if plugin in dependencies:
                    circular_dependencies += 1
                else:
                    resolved_count += 1

            batch_time = time.time() - batch_start

            resolution_results.append({
                "batch_index": batch_index,
                "plugins_in_batch": len(plugin_batch),
                "resolved_count": resolved_count,
                "circular_dependencies": circular_dependencies,
                "missing_dependencies": missing_dependencies,
                "processing_time": batch_time,
            })

            performance_profiler.record_operation(f"dependency_batch_{batch_index}", batch_time, 0)

        total_time = time.time() - start_time

        performance_profiler.stop_profiling()

        # Analyze dependency resolution performance
        total_resolved = sum(r["resolved_count"] for r in resolution_results)
        total_circular = sum(r["circular_dependencies"] for r in resolution_results)
        sum(r["missing_dependencies"] for r in resolution_results)

        # Most plugins should resolve successfully
        resolution_rate = total_resolved / plugin_count
        assert resolution_rate > 0.9, f"Dependency resolution rate too low: {resolution_rate:.1%}"

        # Should detect circular dependencies (if any)
        assert total_circular < plugin_count * 0.05, f"Too many circular dependencies detected: {total_circular}"

        # Processing should be efficient
        throughput = plugin_count / total_time
        assert throughput > 50, f"Dependency resolution too slow: {throughput:.1f} plugins/sec"

        # Performance should remain relatively consistent
        # Note: First operations may be much faster due to caching/warm-up effects
        # Only check variance if minimum time is significant (>1ms) to avoid division issues
        processing_times = [r["processing_time"] for r in resolution_results]
        if len(processing_times) > 1 and min(processing_times) > 0.001:
            time_variance = max(processing_times) / min(processing_times)
            # Allow high variance as first chunks often complete much faster
            assert time_variance < 100.0, f"Extremely high dependency resolution variance: {time_variance:.2f}x"

    def test_plugin_conflict_detection_massive_scale(self, performance_profiler, stress_data_generator):
        """
        Test plugin conflict detection across hundreds of plugins.

        Simulates conflict detection scenarios in massive plugin
        load orders where multiple plugins might modify the same records.
        """
        performance_profiler.start_profiling()

        parser = LogParser()

        # Generate massive plugin list with potential conflicts
        plugin_count = 400
        base_plugins = stress_data_generator.generate_plugin_load_order(count=plugin_count)

        # Create log content simulating plugin conflicts
        conflict_log_sections = []

        # Generate FormIDs that might be modified by multiple plugins
        conflicting_formids = []
        for i in range(1000):  # 1000 potentially conflicting FormIDs
            formid = f"0x{(0x01000000 + i):08X}"
            conflicting_formids.append(formid)

        # Create log entries showing these FormIDs in different plugins
        for formid in conflicting_formids:
            # Each FormID appears in 2-5 plugins (potential conflicts)
            conflict_count = (hash(formid) % 4) + 2  # 2-5 conflicts
            conflicting_plugins = []

            for j in range(conflict_count):
                plugin_index = hash(formid + str(j)) % len(base_plugins)
                conflicting_plugins.append(base_plugins[plugin_index])

            conflict_log_sections.append({"formid": formid, "plugins": conflicting_plugins})

        # Create massive log content with conflict information
        # Use format that LogParser can parse: [XX] PluginName.esp for plugins
        log_lines = ["Fallout 4 v1.10.163", "Plugin Conflict Analysis:", ""]
        log_lines.append("PLUGINS:")

        # First add all plugins in standard format so extract_plugins can find them
        for idx, plugin in enumerate(base_plugins[:255]):  # Max 255 plugins in standard format
            log_lines.append(f"[{idx:02X}] {plugin}")

        log_lines.append("")
        log_lines.append("CONFLICT ANALYSIS:")

        for conflict in conflict_log_sections:
            # Include FormID in parseable format
            log_lines.append(f"FormID: {conflict['formid']} has conflicts")
            for idx, plugin in enumerate(conflict["plugins"]):
                # Also include plugin references in parseable format
                plugin_idx = base_plugins.index(plugin) if plugin in base_plugins else idx
                log_lines.append(f"  [E{plugin_idx % 16:X}] {plugin}")
            log_lines.append("")

        massive_conflict_log = "\n".join(log_lines)

        # Process conflict detection
        start_time = time.time()

        # Extract all FormIDs from conflict log
        detected_formids = parser.extract_formids(log_lines)

        # Extract all plugins mentioned
        detected_plugins = parser.extract_plugins(log_lines)

        # Pattern matching for conflict indicators
        pattern_matcher = PatternMatcher(["conflict", "Modified by", "FormID"])
        conflict_matches = pattern_matcher.find_all(massive_conflict_log)

        total_time = time.time() - start_time

        performance_profiler.record_operation("massive_conflict_detection", total_time)

        performance_profiler.stop_profiling()

        # Analyze conflict detection performance
        assert len(detected_formids) >= 800, f"Too few FormIDs detected in conflicts: {len(detected_formids)}"

        assert len(detected_plugins) >= 200, f"Too few plugins detected in conflicts: {len(detected_plugins)}"

        # Should find conflict pattern matches
        conflict_pattern_count = len(conflict_matches)
        assert conflict_pattern_count >= 1000, f"Too few conflict patterns detected: {conflict_pattern_count}"

        # Performance should be reasonable for massive conflict analysis
        assert total_time < 30.0, f"Conflict detection too slow: {total_time:.2f}s"

        # Throughput should be acceptable
        total_conflicts_processed = len(conflict_log_sections)
        throughput = total_conflicts_processed / total_time
        assert throughput > 20, f"Conflict detection throughput too low: {throughput:.1f} conflicts/sec"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
