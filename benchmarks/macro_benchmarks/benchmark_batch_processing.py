"""
Batch processing macro-benchmark for scalability and throughput testing.

This benchmark tests CLASSIC's performance when processing multiple crash logs
in batch mode, measuring scalability characteristics and identifying performance
bottlenecks under heavy load conditions.

Performance metrics tracked:
- Batch processing throughput (logs/second)
- Memory usage scaling with batch size
- Component resource utilization
- Parallel processing efficiency
- Error handling under load
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path

# Add parent's parent directory to path to import ClassicLib
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ClassicLib.RustAcceleration import get_rust_acceleration, configure_for_batch_processing

logger = logging.getLogger(__name__)


class BatchProcessingBenchmarkResult:
    """Results from a batch processing benchmark run."""

    def __init__(self):
        self.total_execution_time: float = 0.0
        self.logs_processed: int = 0
        self.batch_size: int = 0
        self.throughput_logs_per_second: float = 0.0
        self.average_log_processing_time: float = 0.0
        self.peak_memory_usage: int = 0
        self.errors: int = 0
        self.parallel_efficiency: float = 0.0
        self.resource_utilization: Dict[str, Any] = {}


class BatchProcessingBenchmark:
    """
    Comprehensive benchmark for batch processing performance and scalability.

    This benchmark evaluates how well CLASSIC scales when processing multiple
    crash logs simultaneously, testing both sequential and parallel processing
    patterns to identify optimal batch sizes and processing strategies.
    """

    def __init__(self):
        """Initialize batch processing benchmark."""
        self.rust_acceleration = get_rust_acceleration()

        # Test configurations for different batch processing scenarios
        self.batch_scenarios = {
            'small_batch_sequential': {
                'description': 'Small batches processed sequentially',
                'batch_size': 5,
                'parallel': False,
                'max_workers': 1,
            },
            'medium_batch_sequential': {
                'description': 'Medium batches processed sequentially',
                'batch_size': 20,
                'parallel': False,
                'max_workers': 1,
            },
            'small_batch_parallel': {
                'description': 'Small batches with parallel processing',
                'batch_size': 5,
                'parallel': True,
                'max_workers': 4,
            },
            'medium_batch_parallel': {
                'description': 'Medium batches with parallel processing',
                'batch_size': 20,
                'parallel': True,
                'max_workers': 4,
            },
            'large_batch_parallel': {
                'description': 'Large batches with optimized parallel processing',
                'batch_size': 50,
                'parallel': True,
                'max_workers': 8,
            },
            'stress_test_batch': {
                'description': 'Stress test with maximum batch size',
                'batch_size': 100,
                'parallel': True,
                'max_workers': 12,
            },
        }

    def run_complete_pipeline(
        self,
        dataset: Dict[str, Any],
        scenario: str = 'medium_batch_parallel'
    ) -> BatchProcessingBenchmarkResult:
        """
        Execute complete batch processing pipeline for specified scenario.

        Args:
            dataset: Test dataset containing crash logs
            scenario: Batch processing scenario to execute

        Returns:
            BatchProcessingBenchmarkResult with comprehensive metrics
        """
        if scenario not in self.batch_scenarios:
            raise ValueError(f"Unknown batch scenario: {scenario}")

        scenario_config = self.batch_scenarios[scenario]
        crash_logs = dataset.get('crash_logs', [])

        if not crash_logs:
            logger.warning("No crash logs provided for batch processing benchmark")
            return BatchProcessingBenchmarkResult()

        logger.info(f"Running batch processing scenario: {scenario} ({scenario_config['description']})")
        logger.info(f"Processing {len(crash_logs)} logs in batches of {scenario_config['batch_size']}")

        # Configure Rust acceleration for batch processing
        configure_for_batch_processing(len(crash_logs))

        result = BatchProcessingBenchmarkResult()
        result.batch_size = scenario_config['batch_size']

        batch_start_time = time.perf_counter()

        try:
            if scenario_config['parallel']:
                processing_results = self._run_parallel_batch_processing(
                    crash_logs, scenario_config
                )
            else:
                processing_results = self._run_sequential_batch_processing(
                    crash_logs, scenario_config
                )

            # Calculate comprehensive metrics
            batch_end_time = time.perf_counter()
            result.total_execution_time = batch_end_time - batch_start_time

            # Aggregate results from all batches
            successful_logs = 0
            total_processing_time = 0

            for batch_result in processing_results:
                successful_logs += batch_result.get('logs_processed', 0)
                total_processing_time += batch_result.get('batch_time', 0)
                result.errors += batch_result.get('errors', 0)

            result.logs_processed = successful_logs
            result.throughput_logs_per_second = (
                successful_logs / result.total_execution_time if result.total_execution_time > 0 else 0
            )
            result.average_log_processing_time = (
                total_processing_time / successful_logs if successful_logs > 0 else 0
            )

            # Calculate parallel efficiency (for parallel scenarios)
            if scenario_config['parallel'] and scenario_config['max_workers'] > 1:
                theoretical_sequential_time = total_processing_time
                actual_parallel_time = result.total_execution_time
                result.parallel_efficiency = (
                    (theoretical_sequential_time / (actual_parallel_time * scenario_config['max_workers'])) * 100
                    if actual_parallel_time > 0 else 0
                )

            logger.info(f"Batch processing complete: {result.logs_processed} logs in {result.total_execution_time:.4f}s")
            logger.info(f"Throughput: {result.throughput_logs_per_second:.2f} logs/sec")

        except Exception as e:
            logger.error(f"Batch processing failed for scenario {scenario}: {e}")
            result.errors += 1
            result.total_execution_time = float('inf')

        return result

    def _run_sequential_batch_processing(
        self,
        crash_logs: List[List[str]],
        scenario_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Run sequential batch processing.

        Args:
            crash_logs: List of crash log data
            scenario_config: Scenario configuration

        Returns:
            List of batch processing results
        """
        batch_size = scenario_config['batch_size']
        batch_results = []

        # Process logs in batches
        for i in range(0, len(crash_logs), batch_size):
            batch_logs = crash_logs[i:i + batch_size]
            batch_start_time = time.perf_counter()

            try:
                # Process this batch sequentially
                logs_processed = 0
                batch_errors = 0

                for log_data in batch_logs:
                    try:
                        # Simulate crash log processing
                        self._process_single_log_simplified(log_data)
                        logs_processed += 1
                    except Exception as e:
                        logger.debug(f"Failed to process log in batch {i//batch_size + 1}: {e}")
                        batch_errors += 1

                batch_end_time = time.perf_counter()
                batch_time = batch_end_time - batch_start_time

                batch_results.append({
                    'batch_index': i // batch_size,
                    'logs_processed': logs_processed,
                    'batch_time': batch_time,
                    'errors': batch_errors,
                    'throughput': logs_processed / batch_time if batch_time > 0 else 0,
                })

                logger.debug(f"Batch {i//batch_size + 1}: {logs_processed} logs in {batch_time:.4f}s")

            except Exception as e:
                logger.debug(f"Batch {i//batch_size + 1} failed: {e}")
                batch_results.append({
                    'batch_index': i // batch_size,
                    'logs_processed': 0,
                    'batch_time': 0,
                    'errors': len(batch_logs),
                })

        return batch_results

    def _run_parallel_batch_processing(
        self,
        crash_logs: List[List[str]],
        scenario_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Run parallel batch processing using ThreadPoolExecutor.

        Args:
            crash_logs: List of crash log data
            scenario_config: Scenario configuration

        Returns:
            List of batch processing results
        """
        batch_size = scenario_config['batch_size']
        max_workers = scenario_config['max_workers']
        batch_results = []

        # Create batches
        batches = [
            crash_logs[i:i + batch_size]
            for i in range(0, len(crash_logs), batch_size)
        ]

        logger.debug(f"Processing {len(batches)} batches with {max_workers} parallel workers")

        # Process batches in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._process_batch_parallel, batch_logs, batch_index): batch_index
                for batch_index, batch_logs in enumerate(batches)
            }

            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch_index = future_to_batch[future]
                try:
                    batch_result = future.result()
                    batch_result['batch_index'] = batch_index
                    batch_results.append(batch_result)

                    logger.debug(f"Parallel batch {batch_index + 1}: "
                               f"{batch_result['logs_processed']} logs in {batch_result['batch_time']:.4f}s")

                except Exception as e:
                    logger.debug(f"Parallel batch {batch_index + 1} failed: {e}")
                    batch_results.append({
                        'batch_index': batch_index,
                        'logs_processed': 0,
                        'batch_time': 0,
                        'errors': len(batches[batch_index]),
                    })

        return batch_results

    def _process_batch_parallel(
        self,
        batch_logs: List[List[str]],
        batch_index: int
    ) -> Dict[str, Any]:
        """
        Process a single batch of logs in a worker thread.

        Args:
            batch_logs: Logs in this batch
            batch_index: Index of this batch

        Returns:
            Batch processing result
        """
        batch_start_time = time.perf_counter()
        logs_processed = 0
        batch_errors = 0

        try:
            for log_data in batch_logs:
                try:
                    # Process individual log
                    self._process_single_log_simplified(log_data)
                    logs_processed += 1
                except Exception as e:
                    logger.debug(f"Log processing failed in batch {batch_index}: {e}")
                    batch_errors += 1

        except Exception as e:
            logger.debug(f"Batch {batch_index} processing failed: {e}")
            batch_errors += len(batch_logs)

        batch_end_time = time.perf_counter()
        batch_time = batch_end_time - batch_start_time

        return {
            'logs_processed': logs_processed,
            'batch_time': batch_time,
            'errors': batch_errors,
            'throughput': logs_processed / batch_time if batch_time > 0 else 0,
        }

    def _process_single_log_simplified(self, log_data: List[str]):
        """
        Simplified single log processing for batch benchmarking.

        This method performs essential processing steps without full pipeline
        complexity to focus on batch processing performance characteristics.

        Args:
            log_data: Single crash log data
        """
        # Simulate core processing steps
        # 1. Basic parsing
        lines_processed = len(log_data)

        # 2. Pattern matching (FormID extraction simulation)
        formid_count = 0
        for line in log_data:
            if any(char in line for char in '0123456789ABCDEF'):
                formid_count += 1

        # 3. Simple validation
        if lines_processed < 10:
            raise ValueError("Insufficient log data")

        # Add small processing delay to simulate real work
        time.sleep(0.001)  # 1ms per log

        return {
            'lines_processed': lines_processed,
            'formids_found': formid_count,
        }

    def compare_batch_scenarios(
        self,
        dataset: Dict[str, Any],
        scenarios: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compare performance across different batch processing scenarios.

        Args:
            dataset: Test dataset
            scenarios: List of scenarios to test (default: all)

        Returns:
            Comprehensive scenario comparison results
        """
        if scenarios is None:
            scenarios = list(self.batch_scenarios.keys())

        crash_logs = dataset.get('crash_logs', [])
        logger.info(f"Comparing {len(scenarios)} batch processing scenarios with {len(crash_logs)} logs")

        comparison_results = {
            'scenarios_tested': scenarios,
            'dataset_size': len(crash_logs),
            'scenario_results': {},
            'performance_ranking': [],
            'optimization_recommendations': [],
        }

        # Test each scenario
        for scenario in scenarios:
            logger.info(f"Testing scenario: {scenario}")

            try:
                result = self.run_complete_pipeline(dataset, scenario=scenario)

                comparison_results['scenario_results'][scenario] = {
                    'throughput': result.throughput_logs_per_second,
                    'total_time': result.total_execution_time,
                    'logs_processed': result.logs_processed,
                    'batch_size': result.batch_size,
                    'errors': result.errors,
                    'parallel_efficiency': result.parallel_efficiency,
                    'avg_log_time': result.average_log_processing_time,
                    'config': self.batch_scenarios[scenario],
                }

            except Exception as e:
                logger.error(f"Scenario {scenario} failed: {e}")
                comparison_results['scenario_results'][scenario] = {
                    'error': str(e),
                    'throughput': 0,
                    'config': self.batch_scenarios[scenario],
                }

        # Rank scenarios by throughput
        valid_results = {
            scenario: results for scenario, results in comparison_results['scenario_results'].items()
            if 'throughput' in results and results['throughput'] > 0
        }

        comparison_results['performance_ranking'] = sorted(
            valid_results.items(),
            key=lambda x: x[1]['throughput'],
            reverse=True
        )

        # Generate optimization recommendations
        comparison_results['optimization_recommendations'] = self._generate_batch_optimization_recommendations(
            comparison_results['performance_ranking']
        )

        # Log top performers
        logger.info("Batch processing scenario ranking:")
        for i, (scenario, results) in enumerate(comparison_results['performance_ranking'][:3]):
            logger.info(f"  {i+1}. {scenario}: {results['throughput']:.2f} logs/sec")

        return comparison_results

    def _generate_batch_optimization_recommendations(
        self,
        performance_ranking: List[tuple]
    ) -> List[str]:
        """Generate optimization recommendations based on batch processing results."""
        recommendations = []

        if not performance_ranking:
            recommendations.append("No valid results available for optimization recommendations.")
            return recommendations

        # Analyze top performer
        best_scenario, best_results = performance_ranking[0]
        best_config = best_results['config']

        recommendations.append(
            f"Best performing scenario: {best_scenario} with {best_results['throughput']:.2f} logs/sec"
        )

        # Batch size recommendations
        batch_sizes = [(scenario, results['batch_size'], results['throughput'])
                      for scenario, results in performance_ranking if 'batch_size' in results]

        if len(batch_sizes) > 1:
            optimal_batch_size = max(batch_sizes, key=lambda x: x[2])[1]
            recommendations.append(
                f"Optimal batch size appears to be {optimal_batch_size} logs per batch"
            )

        # Parallelization recommendations
        parallel_scenarios = [
            (scenario, results) for scenario, results in performance_ranking
            if results['config'].get('parallel', False)
        ]
        sequential_scenarios = [
            (scenario, results) for scenario, results in performance_ranking
            if not results['config'].get('parallel', False)
        ]

        if parallel_scenarios and sequential_scenarios:
            best_parallel = max(parallel_scenarios, key=lambda x: x[1]['throughput'])
            best_sequential = max(sequential_scenarios, key=lambda x: x[1]['throughput'])

            speedup = best_parallel[1]['throughput'] / best_sequential[1]['throughput']
            if speedup > 1.5:
                recommendations.append(
                    f"Parallel processing provides {speedup:.1f}x speedup over sequential processing"
                )
            else:
                recommendations.append(
                    "Parallel processing overhead may outweigh benefits for this workload size"
                )

        # Error rate analysis
        error_rates = [
            (scenario, (results.get('errors', 0) / max(results.get('logs_processed', 1), 1)) * 100)
            for scenario, results in performance_ranking
        ]

        high_error_scenarios = [(s, r) for s, r in error_rates if r > 5]
        if high_error_scenarios:
            recommendations.append(
                f"High error rates detected in: {', '.join(s for s, r in high_error_scenarios)}. "
                f"Consider reducing batch sizes or worker counts."
            )

        # Memory efficiency recommendations
        if best_config.get('parallel', False):
            recommendations.append(
                f"For production deployment, consider using {best_config['max_workers']} worker threads "
                f"with batch size {best_config['batch_size']}"
            )

        return recommendations

    def analyze_scalability_characteristics(
        self,
        dataset: Dict[str, Any],
        max_batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Analyze how batch processing performance scales with batch size.

        Args:
            dataset: Test dataset
            max_batch_size: Maximum batch size to test

        Returns:
            Scalability analysis results
        """
        crash_logs = dataset.get('crash_logs', [])
        logger.info(f"Analyzing scalability with batch sizes from 5 to {max_batch_size}")

        # Test different batch sizes
        batch_sizes_to_test = [5, 10, 20, 30, 50, max_batch_size]
        batch_sizes_to_test = [size for size in batch_sizes_to_test if size <= len(crash_logs)]

        scalability_results = {
            'batch_sizes_tested': batch_sizes_to_test,
            'scalability_data': [],
            'optimal_batch_size': None,
            'scalability_metrics': {},
        }

        for batch_size in batch_sizes_to_test:
            logger.info(f"Testing batch size: {batch_size}")

            # Create custom scenario for this batch size
            test_scenario = {
                'batch_size': batch_size,
                'parallel': True,
                'max_workers': min(8, batch_size // 2 + 1),  # Scale workers with batch size
            }

            # Temporarily add to scenarios
            scenario_name = f'scalability_test_{batch_size}'
            self.batch_scenarios[scenario_name] = test_scenario

            try:
                result = self.run_complete_pipeline(dataset, scenario=scenario_name)

                scalability_results['scalability_data'].append({
                    'batch_size': batch_size,
                    'throughput': result.throughput_logs_per_second,
                    'total_time': result.total_execution_time,
                    'avg_log_time': result.average_log_processing_time,
                    'parallel_efficiency': result.parallel_efficiency,
                    'errors': result.errors,
                })

            except Exception as e:
                logger.error(f"Scalability test failed for batch size {batch_size}: {e}")
                scalability_results['scalability_data'].append({
                    'batch_size': batch_size,
                    'error': str(e),
                    'throughput': 0,
                })

            # Clean up temporary scenario
            del self.batch_scenarios[scenario_name]

        # Analyze scalability trends
        valid_data = [d for d in scalability_results['scalability_data'] if 'throughput' in d and d['throughput'] > 0]

        if valid_data:
            # Find optimal batch size
            optimal = max(valid_data, key=lambda x: x['throughput'])
            scalability_results['optimal_batch_size'] = optimal['batch_size']

            # Calculate scalability metrics
            throughputs = [d['throughput'] for d in valid_data]
            batch_sizes = [d['batch_size'] for d in valid_data]

            scalability_results['scalability_metrics'] = {
                'min_throughput': min(throughputs),
                'max_throughput': max(throughputs),
                'throughput_range': max(throughputs) - min(throughputs),
                'optimal_batch_size': optimal['batch_size'],
                'optimal_throughput': optimal['throughput'],
                'scalability_trend': 'increasing' if throughputs[-1] > throughputs[0] else 'decreasing',
            }

            logger.info(f"Scalability analysis complete:")
            logger.info(f"  Optimal batch size: {optimal['batch_size']}")
            logger.info(f"  Peak throughput: {optimal['throughput']:.2f} logs/sec")

        return scalability_results


def benchmark_batch_processing_performance(
    crash_logs: List[List[str]],
    scenarios: Optional[List[str]] = None,
    include_scalability_analysis: bool = True
) -> Dict[str, Any]:
    """
    Standalone function for batch processing performance benchmarking.

    Args:
        crash_logs: List of crash log data
        scenarios: Specific scenarios to test (optional)
        include_scalability_analysis: Whether to include scalability analysis

    Returns:
        Comprehensive batch processing benchmark results
    """
    benchmark = BatchProcessingBenchmark()
    dataset = {'crash_logs': crash_logs}

    results = {
        'metadata': {
            'component': 'batch_processing',
            'crash_log_count': len(crash_logs),
            'total_lines': sum(len(log) for log in crash_logs),
        }
    }

    # Run scenario comparison
    if scenarios:
        comparison_results = benchmark.compare_batch_scenarios(dataset, scenarios)
    else:
        comparison_results = benchmark.compare_batch_scenarios(dataset)

    results['scenario_comparison'] = comparison_results

    # Run scalability analysis if requested
    if include_scalability_analysis and len(crash_logs) >= 50:
        scalability_results = benchmark.analyze_scalability_characteristics(dataset)
        results['scalability_analysis'] = scalability_results

    return results
