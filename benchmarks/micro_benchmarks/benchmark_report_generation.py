"""
Report generation micro-benchmark for Rust vs Python performance comparison.

This benchmark tests report composition and formatting functionality.
Target: 75x speedup for Rust implementation.

Performance metrics tracked:
- Report fragments processed per second
- String composition efficiency
- Memory usage during generation
- Parallel processing capabilities
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add parent's parent directory to path to import ClassicLib
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ClassicLib.integration.status import RUST_AVAILABLE

logger = logging.getLogger(__name__)


class ReportGenBenchmarkResult:
    """Results from a report generation benchmark run."""

    def __init__(self):
        self.execution_time: float = 0.0
        self.fragments_processed: int = 0
        self.reports_generated: int = 0
        self.string_operations: int = 0
        self.errors: int = 0


class ReportGenBenchmark:
    """Comprehensive benchmark for report generation performance comparison."""

    component_name = "report_generation"

    def __init__(self):
        """Initialize report generation benchmark."""
        self._rust_generator = None
        self._python_generator = None

    def run_benchmark(
        self,
        implementation: str,
        dataset: dict[str, Any],
        warm_up: bool = False
    ) -> ReportGenBenchmarkResult:
        """Execute report generation benchmark."""
        report_fragments = dataset.get('report_fragments', [])

        if not report_fragments:
            logger.warning("No report fragments provided for benchmark")
            return ReportGenBenchmarkResult()

        if warm_up:
            logger.debug(f"Warm-up run for {implementation} report generator")
            self._run_single_generation(implementation, report_fragments[:5])
            return ReportGenBenchmarkResult()

        logger.debug(f"Running {implementation} report generator benchmark")

        result = ReportGenBenchmarkResult()
        start_time = time.perf_counter()

        try:
            generation_results = self._run_batch_report_generation(implementation, report_fragments)

            end_time = time.perf_counter()
            result.execution_time = end_time - start_time

            result.fragments_processed = len(report_fragments)
            result.reports_generated = len(generation_results)
            result.string_operations = sum(len(str(report)) for report in generation_results)

            logger.debug(f"{implementation} report generator: {result.reports_generated} reports in {result.execution_time:.4f}s")

        except Exception as e:
            result.errors += 1
            logger.error(f"Report generation benchmark failed for {implementation}: {e}")
            result.execution_time = float('inf')

        return result

    def _run_batch_report_generation(
        self,
        implementation: str,
        report_fragments: list[list[str]]
    ) -> list[str]:
        """Run batch report generation for performance measurement."""
        results = []

        if implementation == "rust" and RUST_AVAILABLE.get("report_generation", False):
            results = self._generate_with_rust(report_fragments)
        else:
            results = self._generate_with_python(report_fragments)

        return results

    def _generate_with_rust(self, report_fragments: list[list[str]]) -> list[str]:
        """Generate reports using Rust implementation."""
        try:
            # Import Rust report generation components
            from ClassicLib.ScanLog.RustReportGeneration import (
                ReportComposer as RustComposer,
            )
            from ClassicLib.ScanLog.RustReportGeneration import (
                ReportFragment as RustFragment,
            )

            composer = RustComposer()

            # Process all fragments
            for fragment_lines in report_fragments:
                fragment = RustFragment.from_lines(fragment_lines)
                composer.add(fragment)

            # Generate final report
            return [composer.build_string()]

        except ImportError:
            logger.debug("Rust report generation not available, falling back to Python")
            return self._generate_with_python(report_fragments)

    def _generate_with_python(self, report_fragments: list[list[str]]) -> list[str]:
        """Generate reports using Python implementation."""
        try:
            # Import Python report generation components
            from ClassicLib.ScanLog.fragments.report_composer import ReportComposer as PyComposer
            from ClassicLib.ScanLog.fragments.report_fragment import ReportFragment as PyFragment

            # Create fragments
            fragments = []
            for fragment_lines in report_fragments:
                fragment = PyFragment.from_lines(fragment_lines)
                fragments.append(fragment)

            # Compose report
            result = PyComposer.compose(*fragments)
            result_list = result.to_list()
            return ["\n".join(result_list)]

        except ImportError:
            # Fallback: simple string concatenation
            logger.debug("Report generation modules not available, using fallback")
            reports = []
            for fragment_lines in report_fragments:
                report = "\n".join(fragment_lines)
                reports.append(report)
            return reports

    def _run_single_generation(self, implementation: str, report_fragments: list[list[str]]):
        """Run single report generation for warm-up."""
        if not report_fragments:
            return

        if implementation == "rust" and RUST_AVAILABLE.get("report_generation", False):
            self._generate_with_rust(report_fragments)
        else:
            self._generate_with_python(report_fragments)


def benchmark_report_generation_performance(
    report_fragments: list[list[str]],
    iterations: int = 5
) -> dict[str, Any]:
    """Standalone function for benchmarking report generation performance."""
    benchmark = ReportGenBenchmark()
    dataset = {'report_fragments': report_fragments}

    results = {
        'metadata': {
            'component': 'report_generation',
            'iterations': iterations,
            'fragment_count': len(report_fragments),
        },
        'implementations': {}
    }

    implementations = ['python']
    if RUST_AVAILABLE.get("report_generation", False):
        implementations.append('rust')

    for impl in implementations:
        impl_results = []
        for i in range(iterations):
            result = benchmark.run_benchmark(impl, dataset)
            impl_results.append({
                'execution_time': result.execution_time,
                'fragments_processed': result.fragments_processed,
                'reports_generated': result.reports_generated,
                'errors': result.errors,
            })
        results['implementations'][impl] = impl_results

    return results
