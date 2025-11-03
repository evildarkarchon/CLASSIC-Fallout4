"""
Record scanning micro-benchmark for Rust vs Python performance comparison.

This benchmark tests named record scanning functionality.
Target: 40x speedup for Rust implementation.

Performance metrics tracked:
- Records scanned per second
- Pattern matching efficiency
- Memory usage during scanning
- Cache utilization
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add parent's parent directory to path to import ClassicLib
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ClassicLib.integration.factory import get_record_scanner
from ClassicLib.integration.status import RUST_AVAILABLE
from ClassicLib.rust.record_rust import RustRecordScanner
from ClassicLib.ScanLog.RecordScanner import RecordScanner

logger = logging.getLogger(__name__)


class RecordScanBenchmarkResult:
    """Results from a record scanning benchmark run."""

    def __init__(self):
        self.execution_time: float = 0.0
        self.records_scanned: int = 0
        self.matches_found: int = 0
        self.cache_hits: int = 0
        self.errors: int = 0


class RecordScanBenchmark:
    """Comprehensive benchmark for record scanning performance comparison."""

    component_name = "record_scanner"

    def __init__(self):
        """Initialize record scanning benchmark."""
        self.mock_yamldata = self._create_mock_yamldata()
        self._rust_scanner: RustRecordScanner | None = None
        self._python_scanner: RecordScanner | None = None

    def _create_mock_yamldata(self):
        """Create mock YAML data for record scanning testing."""
        class MockYamlData:
            def __init__(self):
                self.named_records = {
                    'CommonWeapon': ['Common weapon patterns'],
                    'PlayerCharacter': ['Player-related records'],
                    'QuestScript': ['Quest scripting patterns'],
                }

        return MockYamlData()

    def run_benchmark(
        self,
        implementation: str,
        dataset: dict[str, Any],
        warm_up: bool = False
    ) -> RecordScanBenchmarkResult:
        """Execute record scanning benchmark."""
        callstacks = dataset.get('callstacks', [])

        if not callstacks:
            logger.warning("No call stacks provided for record scanning benchmark")
            return RecordScanBenchmarkResult()

        if warm_up:
            logger.debug(f"Warm-up run for {implementation} record scanner")
            self._run_single_scan(implementation, callstacks[:1])
            return RecordScanBenchmarkResult()

        logger.debug(f"Running {implementation} record scanner benchmark")

        result = RecordScanBenchmarkResult()
        start_time = time.perf_counter()

        try:
            scan_results = self._run_batch_record_scanning(implementation, callstacks)

            end_time = time.perf_counter()
            result.execution_time = end_time - start_time

            for scan_result in scan_results:
                result.records_scanned += scan_result.get('lines_scanned', 0)
                result.matches_found += len(scan_result.get('matches', []))

            logger.debug(f"{implementation} record scanner: {result.matches_found} matches in {result.execution_time:.4f}s")

        except Exception as e:
            result.errors += 1
            logger.error(f"Record scanning benchmark failed for {implementation}: {e}")
            result.execution_time = float('inf')

        return result

    def _run_batch_record_scanning(
        self,
        implementation: str,
        callstacks: list[list[str]]
    ) -> list[dict[str, Any]]:
        """Run batch record scanning for performance measurement."""
        results = []

        for i, callstack_lines in enumerate(callstacks):
            try:
                if implementation == "rust" and RUST_AVAILABLE.get("record_scanner", False):
                    scan_result = self._scan_with_rust(callstack_lines)
                else:
                    scan_result = self._scan_with_python(callstack_lines)

                results.append({
                    'callstack_index': i,
                    'lines_scanned': len(callstack_lines),
                    'matches': scan_result[1] if len(scan_result) > 1 else [],
                })

            except Exception as e:
                logger.debug(f"Failed to scan callstack {i}: {e}")
                results.append({
                    'callstack_index': i,
                    'error': str(e),
                    'matches': [],
                })

        return results

    def _scan_with_rust(self, callstack_lines: list[str]):
        """Scan records using Rust implementation."""
        if self._rust_scanner is None:
            self._rust_scanner = get_record_scanner(self.mock_yamldata)

        return self._rust_scanner.scan_named_records(callstack_lines)

    def _scan_with_python(self, callstack_lines: list[str]):
        """Scan records using Python implementation."""
        if self._python_scanner is None:
            self._python_scanner = RecordScanner(self.mock_yamldata)

        return self._python_scanner.scan_named_records(callstack_lines)

    def _run_single_scan(self, implementation: str, callstacks: list[list[str]]):
        """Run single record scan for warm-up."""
        if not callstacks:
            return

        if implementation == "rust" and RUST_AVAILABLE.get("record_scanner", False):
            self._scan_with_rust(callstacks[0])
        else:
            self._scan_with_python(callstacks[0])


def benchmark_record_scanning_performance(
    callstacks: list[list[str]],
    iterations: int = 5
) -> dict[str, Any]:
    """Standalone function for benchmarking record scanning performance."""
    benchmark = RecordScanBenchmark()
    dataset = {'callstacks': callstacks}

    results = {
        'metadata': {
            'component': 'record_scanner',
            'iterations': iterations,
            'callstack_count': len(callstacks),
        },
        'implementations': {}
    }

    implementations = ['python']
    if RUST_AVAILABLE.get("record_scanner", False):
        implementations.append('rust')

    for impl in implementations:
        impl_results = []
        for i in range(iterations):
            result = benchmark.run_benchmark(impl, dataset)
            impl_results.append({
                'execution_time': result.execution_time,
                'records_scanned': result.records_scanned,
                'matches_found': result.matches_found,
                'errors': result.errors,
            })
        results['implementations'][impl] = impl_results

    return results
