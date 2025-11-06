"""
FormID analysis micro-benchmark for Rust vs Python performance comparison.

This benchmark tests the FormID extraction and analysis functionality which is
a high-impact performance component in CLASSIC. The target is 50x speedup for
Rust implementation.

Tests include:
- FormID pattern recognition and extraction from call stacks
- Batch FormID processing and validation
- Plugin matching and resolution
- Database lookup performance
- Memory efficiency during large-scale analysis
- Error handling for malformed FormIDs

Performance metrics tracked:
- FormIDs processed per second
- Pattern matching accuracy and speed
- Memory allocation during extraction
- Cache utilization for repeated patterns
- Database lookup response times
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add parent's parent directory to path to import ClassicLib
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ClassicLib.integration.factory import get_formid_analyzer
from ClassicLib.integration.status import RUST_AVAILABLE
from ClassicLib.rust.formid_rust import RustFormIDAnalyzer
from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

logger = logging.getLogger(__name__)


class FormIDBenchmarkResult:
    """Results from a FormID analysis benchmark run."""

    def __init__(self):
        self.execution_time: float = 0.0
        self.formids_processed: int = 0
        self.formids_extracted: int = 0
        self.unique_formids: int = 0
        self.pattern_matches: int = 0
        self.plugin_matches: int = 0
        self.database_lookups: int = 0
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.errors: int = 0
        self.memory_peak: int = 0

        # Analysis quality metrics
        self.extraction_accuracy: float = 100.0  # Percentage of correctly extracted FormIDs
        self.validation_errors: int = 0          # Invalid FormID formats detected
        self.duplicate_handling: int = 0         # Duplicate FormIDs filtered


class FormIDBenchmark:
    """
    Comprehensive benchmark for FormID analysis performance comparison.

    This benchmark provides detailed analysis of FormID extraction, validation,
    and plugin matching performance - a critical component for crash analysis.
    """

    component_name = "formid_analyzer"

    def __init__(self):
        """Initialize FormID benchmark with test configurations and patterns."""
        # Mock YAML data for benchmarking
        self.mock_yamldata = self._create_mock_yamldata()

        # Test scenarios for different FormID analysis challenges
        self.test_scenarios = {
            'standard_extraction': {
                'description': 'Standard FormID extraction from call stacks',
                'include_malformed': False,
                'include_edge_cases': False,
                'stress_volume': False,
                'test_plugins': True,
            },
            'malformed_handling': {
                'description': 'Error handling for malformed FormIDs',
                'include_malformed': True,
                'include_edge_cases': False,
                'stress_volume': False,
                'test_plugins': False,
            },
            'edge_case_patterns': {
                'description': 'Complex FormID patterns and edge cases',
                'include_malformed': False,
                'include_edge_cases': True,
                'stress_volume': False,
                'test_plugins': True,
            },
            'volume_stress': {
                'description': 'High-volume FormID processing stress test',
                'include_malformed': False,
                'include_edge_cases': False,
                'stress_volume': True,
                'test_plugins': True,
            },
        }

        # Common FormID patterns for realistic testing
        self.formid_patterns = [
            # Standard 8-digit hex FormIDs
            r'\b[0-9A-Fa-f]{8}\b',
            # FormIDs in brackets
            r'\[[0-9A-Fa-f]{8}\]',
            # FormIDs with plugin prefixes
            r'[0-9A-Fa-f]{2}[0-9A-Fa-f]{6}',
            # Script-referenced FormIDs
            r'FormID:\s*[0-9A-Fa-f]{8}',
        ]

        # Cache for analyzer instances
        self._rust_analyzer: RustFormIDAnalyzer | None = None
        self._python_analyzer: FormIDAnalyzer | None = None

    def _create_mock_yamldata(self) -> ClassicScanLogsInfo:
        """Create comprehensive mock YAML data for FormID analysis testing."""
        class MockYamlData:
            def __init__(self):
                # Mock plugin database for FormID resolution
                self.formid_database = {
                    # Common vanilla game FormIDs
                    '00000014': {'plugin': 'Fallout4.esm', 'name': 'Player'},
                    '0001F4F8': {'plugin': 'Fallout4.esm', 'name': 'CommonSword'},
                    '000133F4': {'plugin': 'Fallout4.esm', 'name': 'DefaultWeapon'},

                    # DLC FormIDs
                    '01000800': {'plugin': 'DLCRobot.esm', 'name': 'RobotWorkbench'},
                    '02001234': {'plugin': 'DLCCoast.esm', 'name': 'FarHarborQuest'},

                    # Mod FormIDs (typical patterns)
                    'FE000001': {'plugin': 'SomeModESP.esp', 'name': 'ModdedItem'},
                    'FF001ABC': {'plugin': 'AnotherMod.esp', 'name': 'CustomWeapon'},
                }

                # Mock problematic FormIDs that commonly cause crashes
                self.problematic_formids = {
                    '00000000': 'NULL FormID',
                    'FFFFFFFF': 'Invalid FormID',
                    '00000001': 'Reserved FormID',
                }

                # Game settings
                self.game_data = {
                    'show_formid_values': True,
                    'formid_db_exists': True,
                    'enable_formid_validation': True,
                }

            def get_formid_info(self, formid: str) -> dict[str, str] | None:
                """Mock FormID database lookup."""
                return self.formid_database.get(formid.upper())

            def is_problematic_formid(self, formid: str) -> bool:
                """Check if FormID is known to be problematic."""
                return formid.upper() in self.problematic_formids

            def get_setting(self, key: str, default=None):
                """Get configuration setting."""
                return self.game_data.get(key, default)

        return MockYamlData()

    def run_benchmark(
        self,
        implementation: str,
        dataset: dict[str, Any],
        warm_up: bool = False,
        scenario: str = 'standard_extraction'
    ) -> FormIDBenchmarkResult:
        """
        Execute FormID analysis benchmark for specified implementation.

        Args:
            implementation: "rust" or "python"
            dataset: Test data containing call stacks and FormID data
            warm_up: Whether this is a warm-up run (not measured)
            scenario: Test scenario to run

        Returns:
            FormIDBenchmarkResult with comprehensive performance metrics
        """
        if scenario not in self.test_scenarios:
            raise ValueError(f"Unknown scenario: {scenario}")

        scenario_config = self.test_scenarios[scenario]
        callstacks = dataset.get('callstacks', [])
        plugins = dataset.get('plugins', {})

        if not callstacks:
            logger.warning("No call stacks provided for FormID benchmark")
            return FormIDBenchmarkResult()

        if warm_up:
            logger.debug(f"Warm-up run for {implementation} FormID analyzer")
            # Quick single-stack warm-up
            self._run_single_extraction(implementation, callstacks[:1], scenario_config)
            return FormIDBenchmarkResult()

        logger.debug(f"Running {implementation} FormID analyzer benchmark - scenario: {scenario}")

        # Initialize result tracking
        result = FormIDBenchmarkResult()
        start_time = time.perf_counter()

        try:
            # Process FormID extraction and analysis
            extraction_results = self._run_batch_formid_analysis(
                implementation, callstacks, plugins, scenario_config
            )

            # Calculate comprehensive metrics
            end_time = time.perf_counter()
            result.execution_time = end_time - start_time

            # Aggregate results from all processed call stacks
            total_formids = 0
            total_extracted = 0
            unique_formids = set()
            total_plugin_matches = 0

            for extract_result in extraction_results:
                if 'formids' in extract_result:
                    formids = extract_result['formids']
                    total_formids += extract_result.get('lines_processed', 0)
                    total_extracted += len(formids)
                    unique_formids.update(formids)
                    total_plugin_matches += extract_result.get('plugin_matches', 0)

            result.formids_processed = total_formids
            result.formids_extracted = total_extracted
            result.unique_formids = len(unique_formids)
            result.plugin_matches = total_plugin_matches

            # Calculate derived metrics
            if result.execution_time > 0:
                result.pattern_matches = int(total_extracted / result.execution_time)

            logger.debug(f"{implementation} FormID analyzer: {total_extracted} FormIDs in {result.execution_time:.4f}s")

        except Exception as e:
            result.errors += 1
            logger.error(f"FormID benchmark failed for {implementation}: {e}")
            result.execution_time = float('inf')

        return result

    def _run_batch_formid_analysis(
        self,
        implementation: str,
        callstacks: list[list[str]],
        plugins: dict[str, str],
        scenario_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Run batch FormID analysis for performance measurement.

        Args:
            implementation: Analyzer implementation to use
            callstacks: List of call stack data (each is list of lines)
            plugins: Plugin information for matching
            scenario_config: Test scenario configuration

        Returns:
            List of analysis results for each call stack
        """
        results = []

        # Apply scenario preprocessing
        processed_callstacks = self._apply_scenario_preprocessing(callstacks, scenario_config)

        for i, callstack_lines in enumerate(processed_callstacks):
            try:
                if implementation == "rust" and RUST_AVAILABLE.get("formid_analyzer", False):
                    # Use Rust FormID analyzer
                    analysis_result = self._analyze_with_rust(
                        callstack_lines, plugins, scenario_config
                    )
                else:
                    # Use Python FormID analyzer
                    analysis_result = self._analyze_with_python(
                        callstack_lines, plugins, scenario_config
                    )

                results.append({
                    'callstack_index': i,
                    'lines_processed': len(callstack_lines),
                    'formids': analysis_result.get('formids', []),
                    'plugin_matches': analysis_result.get('plugin_matches', 0),
                    'validation_errors': analysis_result.get('validation_errors', 0),
                })

            except Exception as e:
                logger.debug(f"Failed to analyze call stack {i}: {e}")
                results.append({
                    'callstack_index': i,
                    'error': str(e),
                    'formids': [],
                    'plugin_matches': 0,
                })

        return results

    def _analyze_with_rust(
        self,
        callstack_lines: list[str],
        plugins: dict[str, str],
        scenario_config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze FormIDs using Rust implementation.

        This method leverages the high-performance Rust FormID extraction
        and analysis capabilities.

        Args:
            callstack_lines: Call stack lines to analyze
            plugins: Available plugins for matching
            scenario_config: Test scenario configuration

        Returns:
            Dictionary with analysis results
        """
        # Get or create Rust analyzer instance
        if self._rust_analyzer is None:
            self._rust_analyzer = get_formid_analyzer(
                self.mock_yamldata,
                show_formid_values=True,
                formid_db_exists=True
            )

        # Extract FormIDs using Rust batch processing
        extracted_formids = self._rust_analyzer.extract_formids(callstack_lines)

        result = {
            'formids': extracted_formids,
            'plugin_matches': 0,
            'validation_errors': 0,
        }

        # Perform plugin matching if requested and data available
        if scenario_config.get('test_plugins') and plugins:
            try:
                # Create mock report object for plugin matching
                mock_report = MockReportFragment()
                self._rust_analyzer.formid_match(extracted_formids, plugins, mock_report)
                result['plugin_matches'] = len(mock_report.matched_plugins)
            except Exception as e:
                logger.debug(f"Rust plugin matching failed: {e}")

        # Validate FormIDs if enabled
        if scenario_config.get('validate_formids', True):
            invalid_count = 0
            for formid in extracted_formids:
                if not self._is_valid_formid(formid):
                    invalid_count += 1
            result['validation_errors'] = invalid_count

        return result

    def _analyze_with_python(
        self,
        callstack_lines: list[str],
        plugins: dict[str, str],
        scenario_config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze FormIDs using Python implementation.

        This method uses the pure Python FormID analyzer for performance
        comparison against the Rust version.

        Args:
            callstack_lines: Call stack lines to analyze
            plugins: Available plugins for matching
            scenario_config: Test scenario configuration

        Returns:
            Dictionary with analysis results
        """
        # Get or create Python analyzer instance
        if self._python_analyzer is None:
            self._python_analyzer = FormIDAnalyzer(
                self.mock_yamldata,
                show_formid_values=True,
                formid_db_exists=True
            )

        # Extract FormIDs using Python implementation
        extracted_formids = self._python_analyzer.extract_formids(callstack_lines)

        result = {
            'formids': extracted_formids,
            'plugin_matches': 0,
            'validation_errors': 0,
        }

        # Perform plugin matching
        if scenario_config.get('test_plugins') and plugins:
            try:
                mock_report = MockReportFragment()
                self._python_analyzer.formid_match(extracted_formids, plugins, mock_report)
                result['plugin_matches'] = len(mock_report.matched_plugins)
            except Exception as e:
                logger.debug(f"Python plugin matching failed: {e}")

        # Validate FormIDs
        if scenario_config.get('validate_formids', True):
            invalid_count = 0
            for formid in extracted_formids:
                if not self._is_valid_formid(formid):
                    invalid_count += 1
            result['validation_errors'] = invalid_count

        return result

    def _apply_scenario_preprocessing(
        self,
        callstacks: list[list[str]],
        scenario_config: dict[str, Any]
    ) -> list[list[str]]:
        """
        Apply scenario-specific preprocessing to call stack data.

        Args:
            callstacks: Original call stack data
            scenario_config: Scenario configuration

        Returns:
            Preprocessed call stack data
        """
        processed = []

        for callstack in callstacks:
            modified_stack = list(callstack)  # Copy original

            # Add malformed FormIDs for error testing
            if scenario_config.get('include_malformed'):
                modified_stack = self._add_malformed_formids(modified_stack)

            # Add edge case FormID patterns
            if scenario_config.get('include_edge_cases'):
                modified_stack = self._add_edge_case_formids(modified_stack)

            # Increase volume for stress testing
            if scenario_config.get('stress_volume'):
                # Duplicate the call stack with variations to increase FormID density
                modified_stack = self._increase_formid_density(modified_stack)

            processed.append(modified_stack)

        return processed

    def _add_malformed_formids(self, callstack: list[str]) -> list[str]:
        """Add malformed FormID patterns for error handling testing."""
        malformed_patterns = [
            "FormID: INVALID_HEX",      # Non-hex characters
            "FormID: 12345",            # Too short
            "FormID: 1234567890AB",     # Too long
            "FormID: ",                 # Empty
            "[GGGGGGGG]",              # Invalid hex characters
            "FormID: NULL",             # NULL reference
        ]

        modified = list(callstack)

        # Insert malformed FormIDs at regular intervals
        for i, pattern in enumerate(malformed_patterns):
            if i * 10 < len(modified):
                insert_pos = min(i * 10, len(modified))
                modified.insert(insert_pos, f"    Stack frame: {pattern}")

        return modified

    def _add_edge_case_formids(self, callstack: list[str]) -> list[str]:
        """Add edge case FormID patterns for comprehensive testing."""
        edge_cases = [
            # Maximum values
            "FormID: FFFFFFFF",
            "FormID: FFFFFFFE",

            # Minimum values
            "FormID: 00000000",
            "FormID: 00000001",

            # Plugin boundary cases
            "FormID: FE000000",  # Light plugin start
            "FormID: FEFFFFFF",  # Light plugin end
            "FormID: FF000000",  # ESP plugin start

            # Common problematic patterns
            "[DEADBEEF]",        # Common placeholder
            "[CAFEBABE]",        # Another placeholder
            "FormID: BAADF00D",  # Bad food pattern

            # Mixed case variations
            "FormID: abcdef12",
            "FormID: AbCdEf12",
        ]

        modified = list(callstack)

        # Insert edge cases throughout the call stack
        for i, pattern in enumerate(edge_cases):
            if i * 5 < len(modified):
                insert_pos = min(i * 5, len(modified))
                modified.insert(insert_pos, f"    Stack frame: {pattern}")

        return modified

    def _increase_formid_density(self, callstack: list[str]) -> list[str]:
        """Increase FormID density for volume stress testing."""
        enhanced_stack = []

        for line in callstack:
            enhanced_stack.append(line)

            # Add multiple FormIDs per line for stress testing
            if "Stack frame" in line or "module" in line.lower():
                # Generate realistic FormID patterns
                stress_formids = [
                    f"    Referenced FormID: {self._generate_random_formid()}",
                    f"    Secondary FormID: {self._generate_random_formid()}",
                    f"    Cache FormID: [{self._generate_random_formid()}]",
                ]
                enhanced_stack.extend(stress_formids)

        return enhanced_stack

    def _generate_random_formid(self) -> str:
        """Generate a realistic random FormID for testing."""
        import random

        # Generate realistic FormID patterns
        patterns = [
            f"{random.randint(0, 255):02X}{random.randint(0, 16777215):06X}",  # Standard
            f"FE{random.randint(0, 16777215):06X}",                           # Light plugin
            f"FF{random.randint(0, 16777215):06X}",                           # ESP plugin
        ]

        return random.choice(patterns)

    def _is_valid_formid(self, formid: str) -> bool:
        """Validate FormID format."""
        if not formid or len(formid) != 8:
            return False

        # Check if it's valid hexadecimal
        try:
            int(formid, 16)
            return True
        except ValueError:
            return False

    def _run_single_extraction(
        self,
        implementation: str,
        callstacks: list[list[str]],
        scenario_config: dict[str, Any]
    ) -> None:
        """Run single FormID extraction for warm-up."""
        if not callstacks:
            return

        # Process first call stack only for warm-up
        if implementation == "rust" and RUST_AVAILABLE.get("formid_analyzer", False):
            self._analyze_with_rust(callstacks[0], {}, scenario_config)
        else:
            self._analyze_with_python(callstacks[0], {}, scenario_config)

    def run_all_scenarios(
        self,
        implementation: str,
        dataset: dict[str, Any]
    ) -> dict[str, FormIDBenchmarkResult]:
        """
        Run all test scenarios for comprehensive FormID analysis.

        Args:
            implementation: Analyzer implementation to test
            dataset: Test dataset with call stacks and plugins

        Returns:
            Dictionary mapping scenario names to benchmark results
        """
        results = {}

        for scenario_name, scenario_config in self.test_scenarios.items():
            logger.info(f"Running FormID scenario: {scenario_name} ({scenario_config['description']})")

            try:
                result = self.run_benchmark(implementation, dataset, scenario=scenario_name)
                results[scenario_name] = result

                logger.info(f"  {scenario_name}: {result.formids_extracted} FormIDs in {result.execution_time:.4f}s")

            except Exception as e:
                logger.error(f"FormID scenario {scenario_name} failed: {e}")
                results[scenario_name] = FormIDBenchmarkResult()
                results[scenario_name].errors = 1

        return results

    def get_formid_extraction_accuracy(
        self,
        dataset: dict[str, Any],
        reference_implementation: str = "python"
    ) -> dict[str, Any]:
        """
        Analyze FormID extraction accuracy between implementations.

        This method compares the FormID extraction results between different
        implementations to ensure accuracy is maintained while improving performance.

        Args:
            dataset: Test dataset
            reference_implementation: Implementation to use as reference

        Returns:
            Accuracy analysis results
        """
        accuracy_results = {
            'reference_implementation': reference_implementation,
            'comparison_results': {},
            'accuracy_metrics': {},
        }

        callstacks = dataset.get('callstacks', [])
        if not callstacks:
            return accuracy_results

        # Get reference results
        ref_results = []
        for callstack in callstacks[:10]:  # Test subset for accuracy
            if reference_implementation == "python":
                result = self._analyze_with_python(callstack, {}, self.test_scenarios['standard_extraction'])
            else:
                result = self._analyze_with_rust(callstack, {}, self.test_scenarios['standard_extraction'])
            ref_results.append(set(result.get('formids', [])))

        # Compare other implementations
        implementations_to_test = ['rust', 'python']
        if reference_implementation in implementations_to_test:
            implementations_to_test.remove(reference_implementation)

        for impl in implementations_to_test:
            if impl == 'rust' and not RUST_AVAILABLE.get("formid_analyzer", False):
                continue

            test_results = []
            for callstack in callstacks[:10]:
                if impl == "python":
                    result = self._analyze_with_python(callstack, {}, self.test_scenarios['standard_extraction'])
                else:
                    result = self._analyze_with_rust(callstack, {}, self.test_scenarios['standard_extraction'])
                test_results.append(set(result.get('formids', [])))

            # Calculate accuracy metrics
            total_matches = 0
            total_reference = 0
            total_test = 0

            for ref_set, test_set in zip(ref_results, test_results):
                intersection = ref_set & test_set
                total_matches += len(intersection)
                total_reference += len(ref_set)
                total_test += len(test_set)

            # Calculate precision, recall, and F1 score
            precision = total_matches / total_test if total_test > 0 else 0
            recall = total_matches / total_reference if total_reference > 0 else 0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            accuracy_results['accuracy_metrics'][impl] = {
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score,
                'total_matches': total_matches,
                'total_reference': total_reference,
                'total_test': total_test,
            }

        return accuracy_results


class MockReportFragment:
    """Mock report fragment for plugin matching testing."""

    def __init__(self):
        self.matched_plugins: set[str] = set()
        self.formid_matches: dict[str, str] = {}

    def add_plugin_match(self, plugin_name: str, formid: str):
        """Add a plugin match result."""
        self.matched_plugins.add(plugin_name)
        self.formid_matches[formid] = plugin_name


# Convenience function for standalone benchmarking
def benchmark_formid_analysis_performance(
    callstacks: list[list[str]],
    plugins: dict[str, str] | None = None,
    iterations: int = 5,
    include_scenarios: bool = True
) -> dict[str, Any]:
    """
    Standalone function for benchmarking FormID analysis performance.

    Args:
        callstacks: List of call stack data
        plugins: Plugin information for matching tests
        iterations: Number of benchmark iterations
        include_scenarios: Whether to run all test scenarios

    Returns:
        Comprehensive benchmark results
    """
    benchmark = FormIDBenchmark()
    dataset = {
        'callstacks': callstacks,
        'plugins': plugins or {}
    }

    results = {
        'metadata': {
            'component': 'formid_analyzer',
            'iterations': iterations,
            'callstack_count': len(callstacks),
            'total_lines': sum(len(stack) for stack in callstacks),
        },
        'implementations': {}
    }

    # Test available implementations
    implementations = ['python']
    if RUST_AVAILABLE.get("formid_analyzer", False):
        implementations.append('rust')

    for impl in implementations:
        impl_results = {'standard': [], 'scenarios': {}}

        # Run standard benchmarks
        for i in range(iterations):
            result = benchmark.run_benchmark(impl, dataset)
            impl_results['standard'].append({
                'execution_time': result.execution_time,
                'formids_extracted': result.formids_extracted,
                'unique_formids': result.unique_formids,
                'plugin_matches': result.plugin_matches,
                'errors': result.errors,
            })

        # Run scenario benchmarks if requested
        if include_scenarios:
            scenario_results = benchmark.run_all_scenarios(impl, dataset)
            impl_results['scenarios'] = {
                name: {
                    'execution_time': result.execution_time,
                    'formids_extracted': result.formids_extracted,
                    'unique_formids': result.unique_formids,
                    'errors': result.errors,
                }
                for name, result in scenario_results.items()
            }

        results['implementations'][impl] = impl_results

    return results
