"""
End-to-end macro-benchmark for complete crash log processing pipeline.

This benchmark tests the entire CLASSIC workflow from crash log parsing
through final report generation, measuring overall system performance
and identifying integration bottlenecks.

Target: 10x overall speedup with Rust acceleration.

Pipeline stages tested:
1. Log parsing and segment extraction
2. FormID analysis and extraction
3. Plugin analysis and load order parsing
4. Record scanning and pattern matching
5. Database lookups and caching
6. Report generation and formatting
7. File I/O operations throughout

Performance metrics tracked:
- End-to-end processing time per crash log
- Total throughput (logs processed per second)
- Memory usage across entire pipeline
- Component interaction overhead
- Error rates and recovery performance
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add parent's parent directory to path to import ClassicLib
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ClassicLib.integration.factory import (
    get_formid_analyzer,
    get_parser,
    get_plugin_analyzer,
    get_record_scanner,
)
from ClassicLib.integration.status import RUST_AVAILABLE
from ClassicLib.RustAcceleration import get_rust_acceleration

logger = logging.getLogger(__name__)


class EndToEndBenchmarkResult:
    """Results from an end-to-end benchmark run."""

    def __init__(self):
        self.total_execution_time: float = 0.0
        self.logs_processed: int = 0
        self.pipeline_stages: dict[str, float] = {}
        self.throughput_logs_per_second: float = 0.0
        self.memory_peak: int = 0
        self.errors: int = 0
        self.component_performance: dict[str, dict[str, Any]] = {}


class EndToEndBenchmark:
    """
    Comprehensive end-to-end benchmark for complete crash log processing.

    This benchmark simulates realistic usage of CLASSIC by processing
    crash logs through the complete analysis pipeline, measuring both
    individual component performance and overall system integration.
    """

    def __init__(self):
        """Initialize end-to-end benchmark."""
        self.rust_acceleration = get_rust_acceleration()

        # Mock YAML data for testing
        self.mock_yamldata = self._create_mock_yamldata()

        # Initialize components for reuse across tests
        self._components_cache = {}

    def _create_mock_yamldata(self):
        """Create comprehensive mock YAML data for end-to-end testing."""
        class MockYamlData:
            def __init__(self):
                # Game configuration
                self.game_data = {
                    'game_root_name': 'Fallout4.exe',
                    'crashgen_name': 'Buffout 4',
                    'xse_acronym': 'F4SE',
                }

                # FormID database for lookups
                self.formid_database = {
                    '00000014': {'plugin': 'Fallout4.esm', 'name': 'Player'},
                    '0001F4F8': {'plugin': 'Fallout4.esm', 'name': 'CommonWeapon'},
                    'FE000001': {'plugin': 'ModPlugin.esp', 'name': 'ModdedItem'},
                }

                # Problematic plugins for matching
                self.problematic_plugins = {
                    'problematic_mod.esp': 'Known crash source',
                    'unstable_plugin.esm': 'Memory corruption issues',
                }

                # Named records for scanning
                self.named_records = {
                    'CommonWeapon': ['weapon_patterns'],
                    'PlayerCharacter': ['player_patterns'],
                }

            def get_game_data(self, key: str, default=None):
                return self.game_data.get(key, default)

        return MockYamlData()

    def run_complete_pipeline(
        self,
        dataset: dict[str, Any],
        use_rust_acceleration: bool = True
    ) -> EndToEndBenchmarkResult:
        """
        Execute complete crash log processing pipeline.

        Args:
            dataset: Test dataset containing crash logs and metadata
            use_rust_acceleration: Whether to use Rust acceleration when available

        Returns:
            EndToEndBenchmarkResult with comprehensive performance metrics
        """
        crash_logs = dataset.get('crash_logs', [])
        plugins_data = dataset.get('plugins', {})

        if not crash_logs:
            logger.warning("No crash logs provided for end-to-end benchmark")
            return EndToEndBenchmarkResult()

        logger.debug(f"Running end-to-end pipeline on {len(crash_logs)} crash logs")

        result = EndToEndBenchmarkResult()
        pipeline_start_time = time.perf_counter()

        # Configure acceleration based on parameter
        if use_rust_acceleration:
            self.rust_acceleration.update_workload_characteristics(
                file_count=len(crash_logs),
                is_batch=len(crash_logs) > 1
            )

        try:
            # Process each crash log through the complete pipeline
            for i, crash_log_data in enumerate(crash_logs):
                try:
                    log_result = self._process_single_crash_log(
                        crash_log_data, plugins_data, use_rust_acceleration
                    )

                    # Aggregate stage timings
                    for stage, timing in log_result.get('stage_timings', {}).items():
                        if stage not in result.pipeline_stages:
                            result.pipeline_stages[stage] = 0
                        result.pipeline_stages[stage] += timing

                    result.logs_processed += 1

                except Exception as e:
                    logger.debug(f"Failed to process crash log {i}: {e}")
                    result.errors += 1

            # Calculate final metrics
            pipeline_end_time = time.perf_counter()
            result.total_execution_time = pipeline_end_time - pipeline_start_time

            if result.total_execution_time > 0:
                result.throughput_logs_per_second = result.logs_processed / result.total_execution_time

            logger.debug(f"End-to-end pipeline: {result.logs_processed} logs in {result.total_execution_time:.4f}s "
                        f"({result.throughput_logs_per_second:.2f} logs/sec)")

        except Exception as e:
            logger.error(f"End-to-end pipeline failed: {e}")
            result.errors += 1
            result.total_execution_time = float('inf')

        return result

    def _process_single_crash_log(
        self,
        crash_log_data: list[str],
        plugins_data: dict[str, str],
        use_rust: bool
    ) -> dict[str, Any]:
        """
        Process a single crash log through the complete pipeline.

        This method orchestrates all pipeline stages in the correct order,
        measuring timing for each stage and handling data flow between components.

        Args:
            crash_log_data: Raw crash log lines
            plugins_data: Plugin information
            use_rust: Whether to prefer Rust implementations

        Returns:
            Dictionary with processing results and stage timings
        """
        stage_timings = {}
        results = {}

        # Stage 1: Log Parsing
        stage_start = time.perf_counter()
        try:
            parser = self._get_component('parser', use_rust)
            if hasattr(parser, 'find_segments'):
                # Use RustLogParser interface
                game_version, crashgen_version, main_error, segments = parser.find_segments(
                    crash_log_data,
                    self.mock_yamldata.get_game_data('crashgen_name'),
                    self.mock_yamldata.get_game_data('xse_acronym'),
                    self.mock_yamldata.get_game_data('game_root_name')
                )
            else:
                # Use direct function interface
                from ClassicLib.ScanLog.Parser import find_segments
                game_version, crashgen_version, main_error, segments = find_segments(
                    crash_log_data,
                    self.mock_yamldata.get_game_data('crashgen_name'),
                    self.mock_yamldata.get_game_data('xse_acronym'),
                    self.mock_yamldata.get_game_data('game_root_name')
                )

            results['parsing'] = {
                'game_version': game_version,
                'crashgen_version': crashgen_version,
                'main_error': main_error,
                'segments': segments,
            }

        except Exception as e:
            logger.debug(f"Parsing stage failed: {e}")
            results['parsing'] = {'error': str(e)}
            segments = [[] for _ in range(6)]  # Empty segments for fallback

        stage_timings['parsing'] = time.perf_counter() - stage_start

        # Extract segments for downstream processing
        segment_callstack = segments[2] if len(segments) > 2 else []
        segment_plugins = segments[5] if len(segments) > 5 else []

        # Stage 2: FormID Analysis
        stage_start = time.perf_counter()
        try:
            formid_analyzer = self._get_component('formid_analyzer', use_rust,
                                                yamldata=self.mock_yamldata,
                                                show_formid_values=True,
                                                formid_db_exists=True)

            extracted_formids = formid_analyzer.extract_formids(segment_callstack)
            results['formid_analysis'] = {
                'formids_extracted': len(extracted_formids),
                'formids': extracted_formids[:10],  # Sample for results
            }

        except Exception as e:
            logger.debug(f"FormID analysis stage failed: {e}")
            results['formid_analysis'] = {'error': str(e)}
            extracted_formids = []

        stage_timings['formid_analysis'] = time.perf_counter() - stage_start

        # Stage 3: Plugin Analysis
        stage_start = time.perf_counter()
        try:
            plugin_analyzer = self._get_component('plugin_analyzer', use_rust,
                                                yamldata=self.mock_yamldata)

            plugins, limit_triggered, limit_disabled = plugin_analyzer.loadorder_scan_log(segment_plugins)
            results['plugin_analysis'] = {
                'plugins_parsed': len(plugins),
                'limit_triggered': limit_triggered,
                'sample_plugins': list(plugins.items())[:5],  # Sample for results
            }

        except Exception as e:
            logger.debug(f"Plugin analysis stage failed: {e}")
            results['plugin_analysis'] = {'error': str(e)}
            plugins = {}

        stage_timings['plugin_analysis'] = time.perf_counter() - stage_start

        # Stage 4: Record Scanning
        stage_start = time.perf_counter()
        try:
            record_scanner = self._get_component('record_scanner', use_rust,
                                               yamldata=self.mock_yamldata)

            record_fragment, matches = record_scanner.scan_named_records(segment_callstack)
            results['record_scanning'] = {
                'matches_found': len(matches),
                'matches': matches[:5],  # Sample for results
            }

        except Exception as e:
            logger.debug(f"Record scanning stage failed: {e}")
            results['record_scanning'] = {'error': str(e)}

        stage_timings['record_scanning'] = time.perf_counter() - stage_start

        # Stage 5: Database Operations (simulated)
        stage_start = time.perf_counter()
        try:
            # Simulate database lookups for FormIDs
            database_results = []
            for formid in extracted_formids[:20]:  # Limit for performance
                lookup_result = self.mock_yamldata.formid_database.get(formid)
                if lookup_result:
                    database_results.append(lookup_result)

            results['database_ops'] = {
                'lookups_performed': len(extracted_formids[:20]),
                'successful_lookups': len(database_results),
            }

        except Exception as e:
            logger.debug(f"Database operations stage failed: {e}")
            results['database_ops'] = {'error': str(e)}

        stage_timings['database_ops'] = time.perf_counter() - stage_start

        # Stage 6: Report Generation
        stage_start = time.perf_counter()
        try:
            # Simulate report generation
            report_fragments = [
                f"Game Version: {results.get('parsing', {}).get('game_version', 'Unknown')}",
                f"FormIDs Found: {len(extracted_formids)}",
                f"Plugins Loaded: {len(plugins)}",
                f"Records Matched: {results.get('record_scanning', {}).get('matches_found', 0)}",
            ]

            # Simple report composition for benchmarking
            final_report = "\n".join(report_fragments)
            results['report_generation'] = {
                'report_size': len(final_report),
                'fragments_composed': len(report_fragments),
            }

        except Exception as e:
            logger.debug(f"Report generation stage failed: {e}")
            results['report_generation'] = {'error': str(e)}

        stage_timings['report_generation'] = time.perf_counter() - stage_start

        return {
            'stage_timings': stage_timings,
            'results': results,
            'total_stages': len(stage_timings),
        }

    def _get_component(self, component_type: str, use_rust: bool, **kwargs):
        """
        Get component instance with caching and implementation preference.

        Args:
            component_type: Type of component to get
            use_rust: Whether to prefer Rust implementation
            **kwargs: Additional arguments for component initialization

        Returns:
            Component instance
        """
        cache_key = f"{component_type}_{use_rust}_{hash(frozenset(kwargs.items()) if kwargs else 0)}"

        if cache_key in self._components_cache:
            return self._components_cache[cache_key]

        component = None

        try:
            if component_type == 'parser':
                component = get_parser() if (use_rust and RUST_AVAILABLE.get('parser', False)) else None
                if not component:
                    # Fallback to direct function usage
                    component = 'python_function'  # Marker for function usage

            elif component_type == 'formid_analyzer':
                if use_rust and RUST_AVAILABLE.get('formid_analyzer', False):
                    component = get_formid_analyzer(**kwargs)
                else:
                    from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
                    component = FormIDAnalyzer(**kwargs)

            elif component_type == 'plugin_analyzer':
                if use_rust and RUST_AVAILABLE.get('plugin_analyzer', False):
                    component = get_plugin_analyzer(**kwargs)
                else:
                    from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer
                    component = PluginAnalyzer(**kwargs)

            elif component_type == 'record_scanner':
                if use_rust and RUST_AVAILABLE.get('record_scanner', False):
                    component = get_record_scanner(**kwargs)
                else:
                    from ClassicLib.ScanLog.RecordScanner import RecordScanner
                    component = RecordScanner(**kwargs)

        except Exception as e:
            logger.debug(f"Failed to create {component_type} component: {e}")

        if component:
            self._components_cache[cache_key] = component

        return component

    def compare_rust_vs_python_pipeline(
        self,
        dataset: dict[str, Any],
        iterations: int = 3
    ) -> dict[str, Any]:
        """
        Compare end-to-end pipeline performance between Rust and Python implementations.

        Args:
            dataset: Test dataset
            iterations: Number of iterations to run for each implementation

        Returns:
            Comprehensive comparison results
        """
        comparison_results = {
            'iterations': iterations,
            'rust_results': [],
            'python_results': [],
            'comparison_metrics': {},
        }

        crash_logs = dataset.get('crash_logs', [])
        logger.info(f"Comparing pipeline performance over {iterations} iterations with {len(crash_logs)} logs")

        # Test Rust-accelerated pipeline
        logger.info("Testing Rust-accelerated pipeline...")
        for i in range(iterations):
            rust_result = self.run_complete_pipeline(dataset, use_rust_acceleration=True)
            comparison_results['rust_results'].append({
                'iteration': i + 1,
                'total_time': rust_result.total_execution_time,
                'throughput': rust_result.throughput_logs_per_second,
                'logs_processed': rust_result.logs_processed,
                'errors': rust_result.errors,
                'stage_timings': rust_result.pipeline_stages,
            })

        # Test Python-only pipeline
        logger.info("Testing Python-only pipeline...")
        for i in range(iterations):
            python_result = self.run_complete_pipeline(dataset, use_rust_acceleration=False)
            comparison_results['python_results'].append({
                'iteration': i + 1,
                'total_time': python_result.total_execution_time,
                'throughput': python_result.throughput_logs_per_second,
                'logs_processed': python_result.logs_processed,
                'errors': python_result.errors,
                'stage_timings': python_result.pipeline_stages,
            })

        # Calculate comparison metrics
        rust_times = [r['total_time'] for r in comparison_results['rust_results'] if r['total_time'] != float('inf')]
        python_times = [r['total_time'] for r in comparison_results['python_results'] if r['total_time'] != float('inf')]

        if rust_times and python_times:
            avg_rust_time = sum(rust_times) / len(rust_times)
            avg_python_time = sum(python_times) / len(python_times)

            comparison_results['comparison_metrics'] = {
                'avg_rust_time': avg_rust_time,
                'avg_python_time': avg_python_time,
                'speedup_factor': avg_python_time / avg_rust_time if avg_rust_time > 0 else float('inf'),
                'rust_throughput': sum(r['throughput'] for r in comparison_results['rust_results']) / len(comparison_results['rust_results']),
                'python_throughput': sum(r['throughput'] for r in comparison_results['python_results']) / len(comparison_results['python_results']),
            }

            logger.info("Pipeline comparison complete:")
            logger.info(f"  Rust average: {avg_rust_time:.4f}s")
            logger.info(f"  Python average: {avg_python_time:.4f}s")
            logger.info(f"  Speedup: {comparison_results['comparison_metrics']['speedup_factor']:.2f}x")

        return comparison_results

    def analyze_pipeline_bottlenecks(
        self,
        dataset: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze pipeline stages to identify performance bottlenecks.

        Args:
            dataset: Test dataset

        Returns:
            Bottleneck analysis results
        """
        logger.info("Analyzing pipeline bottlenecks...")

        # Run pipeline with detailed timing
        result = self.run_complete_pipeline(dataset, use_rust_acceleration=True)

        if not result.pipeline_stages:
            return {'error': 'No stage timing data available'}

        # Analyze stage performance
        total_time = sum(result.pipeline_stages.values())
        stage_percentages = {
            stage: (timing / total_time * 100) if total_time > 0 else 0
            for stage, timing in result.pipeline_stages.items()
        }

        # Sort stages by time consumption
        bottleneck_ranking = sorted(
            stage_percentages.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Identify major bottlenecks (>20% of total time)
        major_bottlenecks = [(stage, pct) for stage, pct in bottleneck_ranking if pct > 20]
        minor_bottlenecks = [(stage, pct) for stage, pct in bottleneck_ranking if 5 <= pct <= 20]

        analysis_results = {
            'total_pipeline_time': total_time,
            'stage_timings': result.pipeline_stages,
            'stage_percentages': stage_percentages,
            'bottleneck_ranking': bottleneck_ranking,
            'major_bottlenecks': major_bottlenecks,
            'minor_bottlenecks': minor_bottlenecks,
            'recommendations': self._generate_bottleneck_recommendations(major_bottlenecks, minor_bottlenecks),
        }

        logger.info("Bottleneck analysis complete:")
        for stage, percentage in bottleneck_ranking[:3]:
            logger.info(f"  {stage}: {percentage:.1f}% of total time")

        return analysis_results

    def _generate_bottleneck_recommendations(
        self,
        major_bottlenecks: list[tuple],
        minor_bottlenecks: list[tuple]
    ) -> list[str]:
        """Generate optimization recommendations based on bottleneck analysis."""
        recommendations = []

        # Recommendations for major bottlenecks
        for stage, percentage in major_bottlenecks:
            if stage == 'parsing':
                recommendations.append(
                    f"Parsing consumes {percentage:.1f}% of time. Consider optimizing regex patterns "
                    f"or implementing parallel segment parsing."
                )
            elif stage == 'formid_analysis':
                recommendations.append(
                    f"FormID analysis consumes {percentage:.1f}% of time. Consider implementing "
                    f"bulk extraction algorithms or better caching strategies."
                )
            elif stage == 'plugin_analysis':
                recommendations.append(
                    f"Plugin analysis consumes {percentage:.1f}% of time. Consider optimizing "
                    f"load order parsing or implementing plugin metadata caching."
                )
            elif stage == 'record_scanning':
                recommendations.append(
                    f"Record scanning consumes {percentage:.1f}% of time. Consider using "
                    f"more efficient pattern matching algorithms or precompiled patterns."
                )
            elif stage == 'database_ops':
                recommendations.append(
                    f"Database operations consume {percentage:.1f}% of time. Consider implementing "
                    f"connection pooling, batch queries, or improved caching."
                )
            elif stage == 'report_generation':
                recommendations.append(
                    f"Report generation consumes {percentage:.1f}% of time. Consider using "
                    f"string builders, template engines, or parallel composition."
                )

        # General recommendations for minor bottlenecks
        if minor_bottlenecks:
            stage_names = [stage for stage, _ in minor_bottlenecks]
            recommendations.append(
                f"Minor optimization opportunities in: {', '.join(stage_names)}. "
                f"Consider profiling these stages for micro-optimizations."
            )

        if not major_bottlenecks:
            recommendations.append(
                "Pipeline is well-balanced with no major bottlenecks. Focus on overall "
                "architectural improvements or parallel processing capabilities."
            )

        return recommendations


def benchmark_end_to_end_performance(
    crash_logs: list[list[str]],
    plugins: dict[str, str] | None = None,
    iterations: int = 3,
    compare_implementations: bool = True
) -> dict[str, Any]:
    """
    Standalone function for end-to-end performance benchmarking.

    Args:
        crash_logs: List of crash log data
        plugins: Plugin information (optional)
        iterations: Number of iterations per test
        compare_implementations: Whether to compare Rust vs Python

    Returns:
        Comprehensive end-to-end benchmark results
    """
    benchmark = EndToEndBenchmark()
    dataset = {
        'crash_logs': crash_logs,
        'plugins': plugins or {}
    }

    results = {
        'metadata': {
            'component': 'end_to_end_pipeline',
            'iterations': iterations,
            'crash_log_count': len(crash_logs),
            'total_lines': sum(len(log) for log in crash_logs),
        },
        'pipeline_results': {},
    }

    if compare_implementations:
        # Run comprehensive comparison
        comparison_results = benchmark.compare_rust_vs_python_pipeline(dataset, iterations)
        results['comparison'] = comparison_results

        # Extract summary metrics
        if 'comparison_metrics' in comparison_results:
            metrics = comparison_results['comparison_metrics']
            results['pipeline_results']['summary'] = {
                'rust_avg_time': metrics.get('avg_rust_time', 0),
                'python_avg_time': metrics.get('avg_python_time', 0),
                'speedup_factor': metrics.get('speedup_factor', 0),
                'rust_throughput': metrics.get('rust_throughput', 0),
                'python_throughput': metrics.get('python_throughput', 0),
            }
    else:
        # Run single implementation test
        pipeline_results = []
        for i in range(iterations):
            result = benchmark.run_complete_pipeline(dataset, use_rust_acceleration=True)
            pipeline_results.append({
                'iteration': i + 1,
                'total_time': result.total_execution_time,
                'throughput': result.throughput_logs_per_second,
                'stage_timings': result.pipeline_stages,
            })

        results['pipeline_results']['iterations'] = pipeline_results

    # Perform bottleneck analysis
    bottleneck_analysis = benchmark.analyze_pipeline_bottlenecks(dataset)
    results['bottleneck_analysis'] = bottleneck_analysis

    return results
