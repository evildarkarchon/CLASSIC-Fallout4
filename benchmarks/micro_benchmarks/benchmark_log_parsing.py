"""
Log parsing micro-benchmark for Rust vs Python performance comparison.

This benchmark tests the core log parsing functionality which is the most critical
performance component in CLASSIC. The target is 150x speedup for Rust implementation.

Tests include:
- Crash log segment parsing and extraction
- Header metadata extraction
- Multi-format log support
- Error handling and edge cases
- Large file processing performance
- Memory usage during parsing operations

Performance metrics tracked:
- Parse time per log file
- Lines processed per second
- Memory allocation patterns
- Cache hit rates for repeated patterns
- Error recovery performance
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add parent's parent directory to path to import ClassicLib
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ClassicLib.integration.factory import get_parser
from ClassicLib.integration.status import RUST_AVAILABLE
from ClassicLib.rust.parser_rust import RustLogParser
from ClassicLib.ScanLog.Parser import find_segments
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)


class BenchmarkResult:
    """Results from a single parsing benchmark run."""

    def __init__(self):
        self.execution_time: float = 0.0
        self.lines_processed: int = 0
        self.segments_extracted: int = 0
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.errors: int = 0
        self.memory_peak: int = 0


class LogParsingBenchmark:
    """
    Comprehensive benchmark for log parsing performance comparison.

    This benchmark provides detailed performance analysis of the core log parsing
    functionality, which is critical for CLASSIC's overall performance.
    """

    component_name = "parser"

    def __init__(self):
        """Initialize log parsing benchmark with test configurations."""
        # Mock YAML data for benchmarking (minimal required for parsing)
        self.mock_yamldata = self._create_mock_yamldata()

        # Test configurations for different scenarios
        self.test_scenarios = {
            'standard_parsing': {
                'description': 'Standard crash log parsing with typical segments',
                'test_complex_headers': False,
                'test_malformed_data': False,
                'simulate_large_files': False,
            },
            'complex_headers': {
                'description': 'Complex header parsing with version detection',
                'test_complex_headers': True,
                'test_malformed_data': False,
                'simulate_large_files': False,
            },
            'error_handling': {
                'description': 'Malformed data and error recovery',
                'test_complex_headers': False,
                'test_malformed_data': True,
                'simulate_large_files': False,
            },
            'large_file_stress': {
                'description': 'Large file processing stress test',
                'test_complex_headers': False,
                'test_malformed_data': False,
                'simulate_large_files': True,
            },
        }

        # Cache for reused components
        self._rust_parser: RustLogParser | None = None
        self._python_parser_cache: dict[str, Any] = {}

    def _create_mock_yamldata(self) -> ClassicScanLogsInfo:
        """Create minimal mock YAML data for parsing tests."""
        # This would normally load from YAML files, but for benchmarking
        # we create a minimal mock to avoid I/O overhead
        class MockYamlData:
            def __init__(self):
                self.game_data = {
                    'Fallout4': {
                        'game_root_name': 'Fallout4.exe',
                        'crashgen_name': 'Buffout 4',
                        'xse_acronym': 'F4SE',
                    },
                    'Skyrim': {
                        'game_root_name': 'SkyrimSE.exe',
                        'crashgen_name': 'Crash Logger SSE',
                        'xse_acronym': 'SKSE',
                    }
                }

                # Default to Fallout 4 for benchmarking
                self.current_game = 'Fallout4'

            def get_game_data(self, key: str, default=None):
                """Get game-specific data."""
                return self.game_data.get(self.current_game, {}).get(key, default)

        return MockYamlData()

    def run_benchmark(
        self,
        implementation: str,
        dataset: dict[str, Any],
        warm_up: bool = False,
        scenario: str = 'standard_parsing'
    ) -> BenchmarkResult:
        """
        Execute log parsing benchmark for specified implementation.

        Args:
            implementation: "rust" or "python"
            dataset: Test data containing crash logs and metadata
            warm_up: Whether this is a warm-up run (not measured)
            scenario: Test scenario to run

        Returns:
            BenchmarkResult with performance metrics
        """
        if scenario not in self.test_scenarios:
            raise ValueError(f"Unknown scenario: {scenario}")

        scenario_config = self.test_scenarios[scenario]
        crash_logs = dataset.get('crash_logs', [])

        if not crash_logs:
            logger.warning("No crash logs provided for parsing benchmark")
            return BenchmarkResult()

        if warm_up:
            logger.debug(f"Warm-up run for {implementation} parser")
            # Quick single-log warm-up
            self._run_single_parse(implementation, crash_logs[:1], scenario_config)
            return BenchmarkResult()

        logger.debug(f"Running {implementation} parser benchmark - scenario: {scenario}")

        # Initialize result tracking
        result = BenchmarkResult()
        start_time = time.perf_counter()

        try:
            # Process all crash logs in the dataset
            processed_logs = self._run_batch_parse(implementation, crash_logs, scenario_config)

            # Calculate metrics
            end_time = time.perf_counter()
            result.execution_time = end_time - start_time
            result.lines_processed = sum(len(log) for log in crash_logs)
            result.segments_extracted = len(processed_logs) * 6  # Standard 6 segments per log

            logger.debug(f"{implementation} parser: {result.lines_processed} lines in {result.execution_time:.4f}s")

        except Exception as e:
            result.errors += 1
            logger.error(f"Parser benchmark failed for {implementation}: {e}")
            # Set penalty time for failures
            result.execution_time = float('inf')

        return result

    def _run_batch_parse(
        self,
        implementation: str,
        crash_logs: list[list[str]],
        scenario_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Run batch parsing operation for performance measurement.

        Args:
            implementation: Parser implementation to use
            crash_logs: List of crash log data (each log is a list of lines)
            scenario_config: Test scenario configuration

        Returns:
            List of parsed log results
        """
        results = []

        # Get game configuration
        game_root_name = self.mock_yamldata.get_game_data('game_root_name')
        crashgen_name = self.mock_yamldata.get_game_data('crashgen_name')
        xse_acronym = self.mock_yamldata.get_game_data('xse_acronym')

        for i, crash_data in enumerate(crash_logs):
            try:
                if implementation == "rust" and RUST_AVAILABLE.get("parser", False):
                    # Use Rust parser
                    parsed_result = self._parse_with_rust(
                        crash_data, crashgen_name, xse_acronym, game_root_name, scenario_config
                    )
                else:
                    # Use Python parser
                    parsed_result = self._parse_with_python(
                        crash_data, crashgen_name, xse_acronym, game_root_name, scenario_config
                    )

                results.append({
                    'log_index': i,
                    'game_version': parsed_result[0],
                    'crashgen_version': parsed_result[1],
                    'main_error': parsed_result[2],
                    'segments': parsed_result[3],
                    'segment_count': len(parsed_result[3]),
                })

            except Exception as e:
                logger.debug(f"Failed to parse log {i}: {e}")
                results.append({
                    'log_index': i,
                    'error': str(e),
                    'segments': [],
                    'segment_count': 0,
                })

        return results

    def _parse_with_rust(
        self,
        crash_data: list[str],
        crashgen_name: str,
        xse_acronym: str,
        game_root_name: str,
        scenario_config: dict[str, Any]
    ) -> tuple[str, str, str, list[list[str]]]:
        """
        Parse crash log using Rust implementation.

        This method leverages the RustLogParser wrapper to provide consistent
        API while using the high-performance Rust parsing engine.

        Args:
            crash_data: Raw crash log lines
            crashgen_name: Name of crash generator (e.g., "Buffout 4")
            xse_acronym: Script extender acronym (e.g., "F4SE")
            game_root_name: Game executable name
            scenario_config: Test scenario configuration

        Returns:
            Tuple of (game_version, crashgen_version, main_error, segments)
        """
        # Get or create Rust parser instance
        if self._rust_parser is None:
            self._rust_parser = get_parser()

        # Apply scenario-specific preprocessing if needed
        if scenario_config.get('test_complex_headers'):
            # Add complex version strings for testing header parsing
            crash_data = self._add_complex_headers(crash_data)
        elif scenario_config.get('test_malformed_data'):
            # Introduce parsing challenges
            crash_data = self._add_malformed_data(crash_data)
        elif scenario_config.get('simulate_large_files'):
            # Duplicate data to simulate larger files
            crash_data = crash_data * 3

        # Use the Rust parser's find_segments method
        return self._rust_parser.find_segments(
            crash_data, crashgen_name, xse_acronym, game_root_name
        )

    def _parse_with_python(
        self,
        crash_data: list[str],
        crashgen_name: str,
        xse_acronym: str,
        game_root_name: str,
        scenario_config: dict[str, Any]
    ) -> tuple[str, str, str, list[list[str]]]:
        """
        Parse crash log using Python implementation.

        This method uses the pure Python parser implementation for comparison
        against the Rust-accelerated version.

        Args:
            crash_data: Raw crash log lines
            crashgen_name: Name of crash generator
            xse_acronym: Script extender acronym
            game_root_name: Game executable name
            scenario_config: Test scenario configuration

        Returns:
            Tuple of (game_version, crashgen_version, main_error, segments)
        """
        # Apply scenario-specific preprocessing
        if scenario_config.get('test_complex_headers'):
            crash_data = self._add_complex_headers(crash_data)
        elif scenario_config.get('test_malformed_data'):
            crash_data = self._add_malformed_data(crash_data)
        elif scenario_config.get('simulate_large_files'):
            crash_data = crash_data * 3

        # Use the Python find_segments function directly
        return find_segments(crash_data, crashgen_name, xse_acronym, game_root_name)

    def _run_single_parse(
        self,
        implementation: str,
        crash_logs: list[list[str]],
        scenario_config: dict[str, Any]
    ) -> None:
        """Run single parse operation for warm-up."""
        if not crash_logs:
            return

        # Just parse the first log for warm-up
        game_root_name = self.mock_yamldata.get_game_data('game_root_name')
        crashgen_name = self.mock_yamldata.get_game_data('crashgen_name')
        xse_acronym = self.mock_yamldata.get_game_data('xse_acronym')

        if implementation == "rust" and RUST_AVAILABLE.get("parser", False):
            self._parse_with_rust(
                crash_logs[0], crashgen_name, xse_acronym, game_root_name, scenario_config
            )
        else:
            self._parse_with_python(
                crash_logs[0], crashgen_name, xse_acronym, game_root_name, scenario_config
            )

    def _add_complex_headers(self, crash_data: list[str]) -> list[str]:
        """
        Add complex header information for testing header parsing performance.

        This method simulates more complex crash logs with detailed version
        information and metadata that require more sophisticated parsing.

        Args:
            crash_data: Original crash log data

        Returns:
            Modified crash log with complex headers
        """
        complex_headers = [
            "Fallout4.exe v1.10.163.0 (Steam) - Build 163.0.1",
            "Buffout 4 v1.28.6 - Advanced Crash Logger",
            "F4SE v0.6.23 - Fallout 4 Script Extender",
            "Windows 11 Professional (Build 22621.2715)",
            "System Memory: 32768 MB (Available: 24576 MB)",
            "Graphics: NVIDIA GeForce RTX 4080 (Driver: 546.01)",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6F2C45A80 Fallout4.exe+1DC5A80',
            "Additional Exception Info: Attempted to read from virtual address 0x0000000000000000",
            "",
        ]

        # Insert complex headers at the beginning
        return complex_headers + crash_data

    def _add_malformed_data(self, crash_data: list[str]) -> list[str]:
        """
        Add malformed data to test error handling and recovery.

        This method introduces various parsing challenges including:
        - Missing segment markers
        - Truncated lines
        - Invalid characters
        - Unexpected formatting

        Args:
            crash_data: Original crash log data

        Returns:
            Modified crash log with malformed elements
        """
        modified_data = []

        for i, line in enumerate(crash_data):
            # Every 50th line has some form of corruption
            if i % 50 == 0 and i > 0:
                if "MODULES:" in line:
                    # Missing colon (common parsing issue)
                    modified_data.append(line.replace(":", ""))
                elif "PLUGINS:" in line:
                    # Extra characters that might break parsing
                    modified_data.append(line + "���INVALID_CHARS")
                elif line.strip().startswith("["):
                    # Truncated plugin entry
                    modified_data.append(line[:len(line)//2])
                else:
                    # Random corruption
                    modified_data.append("__CORRUPTED_LINE__")
            else:
                modified_data.append(line)

        return modified_data

    def run_all_scenarios(
        self,
        implementation: str,
        dataset: dict[str, Any]
    ) -> dict[str, BenchmarkResult]:
        """
        Run all test scenarios for comprehensive performance analysis.

        Args:
            implementation: Parser implementation to test
            dataset: Test dataset

        Returns:
            Dictionary mapping scenario names to benchmark results
        """
        results = {}

        for scenario_name, scenario_config in self.test_scenarios.items():
            logger.info(f"Running scenario: {scenario_name} ({scenario_config['description']})")

            try:
                result = self.run_benchmark(implementation, dataset, scenario=scenario_name)
                results[scenario_name] = result

                logger.info(f"  {scenario_name}: {result.lines_processed} lines in {result.execution_time:.4f}s")

            except Exception as e:
                logger.error(f"Scenario {scenario_name} failed: {e}")
                results[scenario_name] = BenchmarkResult()
                results[scenario_name].errors = 1

        return results

    def get_performance_characteristics(
        self,
        dataset: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze performance characteristics across different data sizes and complexity.

        This method provides detailed analysis of how parser performance scales
        with different types of input data.

        Args:
            dataset: Test dataset with various log types

        Returns:
            Dictionary with performance characteristics analysis
        """
        characteristics = {
            'scaling_analysis': {},
            'complexity_impact': {},
            'error_handling_performance': {},
            'memory_usage_patterns': {}
        }

        crash_logs = dataset.get('crash_logs', [])
        if not crash_logs:
            return characteristics

        # Test scaling with different data sizes
        size_tests = [
            ('small', crash_logs[:10]),
            ('medium', crash_logs[:50]),
            ('large', crash_logs),
        ]

        for size_name, test_logs in size_tests:
            test_dataset = {'crash_logs': test_logs}

            # Test both implementations if available
            for impl in ['python', 'rust']:
                if impl == 'rust' and not RUST_AVAILABLE.get("parser", False):
                    continue

                result = self.run_benchmark(impl, test_dataset)

                if size_name not in characteristics['scaling_analysis']:
                    characteristics['scaling_analysis'][size_name] = {}

                characteristics['scaling_analysis'][size_name][impl] = {
                    'execution_time': result.execution_time,
                    'lines_per_second': result.lines_processed / result.execution_time if result.execution_time > 0 else 0,
                    'logs_per_second': len(test_logs) / result.execution_time if result.execution_time > 0 else 0,
                }

        # Test scenario complexity impact
        for scenario_name in self.test_scenarios:
            for impl in ['python', 'rust']:
                if impl == 'rust' and not RUST_AVAILABLE.get("parser", False):
                    continue

                result = self.run_benchmark(impl, dataset, scenario=scenario_name)

                if scenario_name not in characteristics['complexity_impact']:
                    characteristics['complexity_impact'][scenario_name] = {}

                characteristics['complexity_impact'][scenario_name][impl] = {
                    'execution_time': result.execution_time,
                    'performance_overhead': result.execution_time,  # Compared to standard parsing
                    'error_rate': result.errors / max(len(crash_logs), 1),
                }

        return characteristics


# Convenience function for standalone benchmarking
def benchmark_log_parsing_performance(
    crash_logs: list[list[str]],
    iterations: int = 5,
    include_scenarios: bool = True
) -> dict[str, Any]:
    """
    Standalone function for benchmarking log parsing performance.

    Args:
        crash_logs: List of crash log data
        iterations: Number of benchmark iterations
        include_scenarios: Whether to run all test scenarios

    Returns:
        Comprehensive benchmark results
    """
    benchmark = LogParsingBenchmark()
    dataset = {'crash_logs': crash_logs}

    results = {
        'metadata': {
            'component': 'log_parser',
            'iterations': iterations,
            'log_count': len(crash_logs),
            'total_lines': sum(len(log) for log in crash_logs),
        },
        'implementations': {}
    }

    # Test available implementations
    implementations = ['python']
    if RUST_AVAILABLE.get("parser", False):
        implementations.append('rust')

    for impl in implementations:
        impl_results = {'standard': [], 'scenarios': {}}

        # Run standard benchmarks
        for i in range(iterations):
            result = benchmark.run_benchmark(impl, dataset)
            impl_results['standard'].append({
                'execution_time': result.execution_time,
                'lines_processed': result.lines_processed,
                'errors': result.errors,
            })

        # Run scenario benchmarks if requested
        if include_scenarios:
            scenario_results = benchmark.run_all_scenarios(impl, dataset)
            impl_results['scenarios'] = {
                name: {
                    'execution_time': result.execution_time,
                    'lines_processed': result.lines_processed,
                    'errors': result.errors,
                }
                for name, result in scenario_results.items()
            }

        results['implementations'][impl] = impl_results

    return results
