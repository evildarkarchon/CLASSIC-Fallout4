"""
Plugin analysis micro-benchmark for Rust vs Python performance comparison.

This benchmark tests plugin load order parsing and analysis functionality.
Target: 30x speedup for Rust implementation.

Performance metrics tracked:
- Plugins parsed per second
- Load order validation speed
- Plugin limit detection performance
- Memory usage during plugin processing
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

# Add parent's parent directory to path to import ClassicLib
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ClassicLib.integration.status import RUST_AVAILABLE
from ClassicLib.integration.factory import get_plugin_analyzer
from ClassicLib.rust.plugin_rust import RustPluginAnalyzer
from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer

logger = logging.getLogger(__name__)


class PluginBenchmarkResult:
    """Results from a plugin analysis benchmark run."""

    def __init__(self):
        self.execution_time: float = 0.0
        self.plugins_processed: int = 0
        self.load_order_validations: int = 0
        self.plugin_matches: int = 0
        self.limit_checks: int = 0
        self.errors: int = 0


class PluginBenchmark:
    """Comprehensive benchmark for plugin analysis performance comparison."""

    component_name = "plugin_analyzer"

    def __init__(self):
        """Initialize plugin analysis benchmark."""
        self.mock_yamldata = self._create_mock_yamldata()
        self._rust_analyzer: Optional[RustPluginAnalyzer] = None
        self._python_analyzer: Optional[PluginAnalyzer] = None

    def _create_mock_yamldata(self):
        """Create mock YAML data for plugin analysis testing."""
        class MockYamlData:
            def __init__(self):
                self.problematic_plugins = {
                    'problematic_mod.esp': 'Known to cause crashes',
                    'unstable_plugin.esm': 'Memory issues',
                }

                self.plugin_limits = {
                    'fallout4': {'limit': 255, 'light_limit': 4096}
                }

        return MockYamlData()

    def run_benchmark(
        self,
        implementation: str,
        dataset: Dict[str, Any],
        warm_up: bool = False
    ) -> PluginBenchmarkResult:
        """
        Execute plugin analysis benchmark for specified implementation.

        Args:
            implementation: "rust" or "python"
            dataset: Test data containing plugin segments
            warm_up: Whether this is a warm-up run

        Returns:
            PluginBenchmarkResult with performance metrics
        """
        plugin_segments = dataset.get('plugin_segments', [])

        if not plugin_segments:
            logger.warning("No plugin segments provided for benchmark")
            return PluginBenchmarkResult()

        if warm_up:
            logger.debug(f"Warm-up run for {implementation} plugin analyzer")
            self._run_single_analysis(implementation, plugin_segments[:1])
            return PluginBenchmarkResult()

        logger.debug(f"Running {implementation} plugin analyzer benchmark")

        result = PluginBenchmarkResult()
        start_time = time.perf_counter()

        try:
            # Process all plugin segments
            analysis_results = self._run_batch_plugin_analysis(implementation, plugin_segments)

            end_time = time.perf_counter()
            result.execution_time = end_time - start_time

            # Aggregate metrics
            for analysis in analysis_results:
                if 'plugins' in analysis:
                    result.plugins_processed += len(analysis['plugins'])
                if 'load_order_valid' in analysis:
                    result.load_order_validations += 1
                result.plugin_matches += analysis.get('plugin_matches', 0)

            logger.debug(f"{implementation} plugin analyzer: {result.plugins_processed} plugins in {result.execution_time:.4f}s")

        except Exception as e:
            result.errors += 1
            logger.error(f"Plugin benchmark failed for {implementation}: {e}")
            result.execution_time = float('inf')

        return result

    def _run_batch_plugin_analysis(
        self,
        implementation: str,
        plugin_segments: List[List[str]]
    ) -> List[Dict[str, Any]]:
        """Run batch plugin analysis for performance measurement."""
        results = []

        for i, segment_lines in enumerate(plugin_segments):
            try:
                if implementation == "rust" and RUST_AVAILABLE.get("plugin_analyzer", False):
                    analysis_result = self._analyze_with_rust(segment_lines)
                else:
                    analysis_result = self._analyze_with_python(segment_lines)

                results.append({
                    'segment_index': i,
                    'plugins': analysis_result.get('plugins', {}),
                    'load_order_valid': analysis_result.get('load_order_valid', False),
                    'plugin_matches': analysis_result.get('plugin_matches', 0),
                })

            except Exception as e:
                logger.debug(f"Failed to analyze plugin segment {i}: {e}")
                results.append({
                    'segment_index': i,
                    'error': str(e),
                    'plugins': {},
                })

        return results

    def _analyze_with_rust(self, segment_lines: List[str]) -> Dict[str, Any]:
        """Analyze plugins using Rust implementation."""
        if self._rust_analyzer is None:
            self._rust_analyzer = get_plugin_analyzer(self.mock_yamldata)

        # Parse load order using Rust
        plugins, limit_triggered, limit_disabled = self._rust_analyzer.loadorder_scan_log(segment_lines)

        # Mock plugin matching for performance testing
        plugin_matches = 0
        for plugin_name in plugins.values():
            if plugin_name.lower() in [p.lower() for p in self.mock_yamldata.problematic_plugins]:
                plugin_matches += 1

        return {
            'plugins': plugins,
            'load_order_valid': not limit_triggered,
            'plugin_matches': plugin_matches,
            'limit_triggered': limit_triggered,
        }

    def _analyze_with_python(self, segment_lines: List[str]) -> Dict[str, Any]:
        """Analyze plugins using Python implementation."""
        if self._python_analyzer is None:
            self._python_analyzer = PluginAnalyzer(self.mock_yamldata)

        # Parse load order using Python
        plugins, limit_triggered, limit_disabled = self._python_analyzer.loadorder_scan_log(segment_lines)

        # Mock plugin matching
        plugin_matches = 0
        for plugin_name in plugins.values():
            if plugin_name.lower() in [p.lower() for p in self.mock_yamldata.problematic_plugins]:
                plugin_matches += 1

        return {
            'plugins': plugins,
            'load_order_valid': not limit_triggered,
            'plugin_matches': plugin_matches,
            'limit_triggered': limit_triggered,
        }

    def _run_single_analysis(self, implementation: str, plugin_segments: List[List[str]]):
        """Run single plugin analysis for warm-up."""
        if not plugin_segments:
            return

        if implementation == "rust" and RUST_AVAILABLE.get("plugin_analyzer", False):
            self._analyze_with_rust(plugin_segments[0])
        else:
            self._analyze_with_python(plugin_segments[0])


def benchmark_plugin_analysis_performance(
    plugin_segments: List[List[str]],
    iterations: int = 5
) -> Dict[str, Any]:
    """Standalone function for benchmarking plugin analysis performance."""
    benchmark = PluginBenchmark()
    dataset = {'plugin_segments': plugin_segments}

    results = {
        'metadata': {
            'component': 'plugin_analyzer',
            'iterations': iterations,
            'segment_count': len(plugin_segments),
        },
        'implementations': {}
    }

    implementations = ['python']
    if RUST_AVAILABLE.get("plugin_analyzer", False):
        implementations.append('rust')

    for impl in implementations:
        impl_results = []
        for i in range(iterations):
            result = benchmark.run_benchmark(impl, dataset)
            impl_results.append({
                'execution_time': result.execution_time,
                'plugins_processed': result.plugins_processed,
                'errors': result.errors,
            })
        results['implementations'][impl] = impl_results

    return results
