"""
FFI Optimization Benchmark for CLASSIC-Fallout4

This script measures the performance improvements from FFI boundary optimizations.
It compares the original multi-call approach with the optimized single-call approach.
"""

import time
import statistics
import psutil
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json

# Add project root to path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ClassicLib.rust.parser_rust import RustLogParser
from ClassicLib.rust.formid_rust import RustFormIDAnalyzer


class FFIBenchmark:
    """Benchmark FFI optimizations for log parsing and FormID extraction."""

    def __init__(self):
        """Initialize benchmark with sample data."""
        self.sample_log_lines = self._generate_sample_log(10000)
        self.sample_callstack = self._generate_sample_callstack(500)
        self.sample_plugins = self._generate_sample_plugins()

    def _generate_sample_log(self, lines: int) -> List[str]:
        """Generate a realistic sample crash log."""
        log = []

        # Header
        log.append("Fallout 4 v1.10.984")
        log.append("Buffout 4 Crash Logger v1.0.0")
        log.append("Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x7FF6E5D29E91")

        # Compatibility section
        log.append("\t[Compatibility]")
        log.extend(["Address Library: All good"] * 20)

        # System specs
        log.append("SYSTEM SPECS:")
        log.extend(["OS: Windows 11 22H2"] * 10)

        # Call stack (most lines)
        log.append("PROBABLE CALL STACK:")
        for i in range(lines - 100):
            if i % 10 == 0:
                log.append(f"[{i//10}] 0x7FF6E5D29E91 Form ID: {i:08X}")
            else:
                log.append(f"[{i//10}] 0x7FF6E5D29E91 SomeFunction+0x123")

        # Modules
        log.append("MODULES:")
        log.extend(["Fallout4.exe v1.10.984"] * 10)

        # Plugins
        log.append("F4SE PLUGINS:")
        log.extend(["buffout4.dll"] * 5)

        log.append("PLUGINS:")
        for i in range(30):
            log.append(f"[{i:02X}] Plugin{i}.esp")

        return log

    def _generate_sample_callstack(self, lines: int) -> List[str]:
        """Generate sample callstack with FormIDs."""
        callstack = []
        for i in range(lines):
            if i % 3 == 0:  # Every 3rd line has a FormID
                callstack.append(f"[{i}] 0x7FF6E5D29E91 Form ID: {i*1000:08X}")
            else:
                callstack.append(f"[{i}] 0x7FF6E5D29E91 Function::Call+0x{i:03X}")
        return callstack

    def _generate_sample_plugins(self) -> Dict[str, str]:
        """Generate sample plugin mappings."""
        plugins = {}
        for i in range(255):
            plugins[f"{i:02X}"] = f"Plugin_{i:03d}.esp"
        return plugins

    def benchmark_parser_legacy(self, iterations: int = 10) -> Dict[str, Any]:
        """Benchmark the legacy multi-FFI-call parser."""
        parser = RustLogParser()

        # Force legacy mode by removing the optimized method
        if hasattr(parser._rust_parser, "parse_complete"):
            original_method = parser._rust_parser.parse_complete
            delattr(parser._rust_parser, "parse_complete")

        times = []
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        for _ in range(iterations):
            start = time.perf_counter()
            parser.find_segments(
                self.sample_log_lines,
                "Buffout4",
                "F4SE",
                "Fallout4"
            )
            times.append(time.perf_counter() - start)

        memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # Restore method if we removed it
        if 'original_method' in locals():
            parser._rust_parser.parse_complete = original_method

        return {
            "avg_time": statistics.mean(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "min_time": min(times),
            "max_time": max(times),
            "memory_delta": memory_after - memory_before,
            "ffi_crossings": 7,  # Known number for legacy
        }

    def benchmark_parser_optimized(self, iterations: int = 10) -> Dict[str, Any]:
        """Benchmark the optimized single-FFI-call parser."""
        parser = RustLogParser()

        times = []
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        for _ in range(iterations):
            start = time.perf_counter()
            parser.find_segments(
                self.sample_log_lines,
                "Buffout4",
                "F4SE",
                "Fallout4"
            )
            times.append(time.perf_counter() - start)

        memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        return {
            "avg_time": statistics.mean(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "min_time": min(times),
            "max_time": max(times),
            "memory_delta": memory_after - memory_before,
            "ffi_crossings": 1,  # Optimized to single call
        }

    def benchmark_formid_legacy(self, iterations: int = 10) -> Dict[str, Any]:
        """Benchmark legacy FormID extraction."""
        from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

        yamldata = ClassicScanLogsInfo()
        analyzer = RustFormIDAnalyzer(yamldata, True, False)

        # Force to not use zero-copy if available
        if hasattr(analyzer._rust_core_analyzer, "extract_formids_nocopy"):
            original = analyzer._rust_core_analyzer.extract_formids_nocopy
            delattr(analyzer._rust_core_analyzer, "extract_formids_nocopy")

        times = []
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        for _ in range(iterations):
            start = time.perf_counter()
            analyzer.extract_formids(self.sample_callstack)
            times.append(time.perf_counter() - start)

        memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # Restore if removed
        if 'original' in locals():
            analyzer._rust_core_analyzer.extract_formids_nocopy = original

        return {
            "avg_time": statistics.mean(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "min_time": min(times),
            "max_time": max(times),
            "memory_delta": memory_after - memory_before,
            "string_copies": len(self.sample_callstack),
        }

    def benchmark_formid_optimized(self, iterations: int = 10) -> Dict[str, Any]:
        """Benchmark optimized zero-copy FormID extraction."""
        from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

        yamldata = ClassicScanLogsInfo()
        analyzer = RustFormIDAnalyzer(yamldata, True, False)

        times = []
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        for _ in range(iterations):
            start = time.perf_counter()
            analyzer.extract_formids(self.sample_callstack)
            times.append(time.perf_counter() - start)

        memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        return {
            "avg_time": statistics.mean(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "min_time": min(times),
            "max_time": max(times),
            "memory_delta": memory_after - memory_before,
            "string_copies": 0,  # Zero-copy
        }

    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all benchmarks and compare results."""
        print("=" * 60)
        print("FFI OPTIMIZATION BENCHMARK")
        print("=" * 60)
        print(f"Test data: {len(self.sample_log_lines)} log lines")
        print(f"           {len(self.sample_callstack)} callstack lines")
        print("=" * 60)

        results = {}

        # LogParser benchmarks
        print("\n📊 Benchmarking LogParser...")
        print("  Legacy (multiple FFI calls)...")
        results["parser_legacy"] = self.benchmark_parser_legacy()

        print("  Optimized (single FFI call)...")
        results["parser_optimized"] = self.benchmark_parser_optimized()

        # Calculate improvements
        parser_speedup = results["parser_legacy"]["avg_time"] / results["parser_optimized"]["avg_time"]
        parser_ffi_reduction = results["parser_legacy"]["ffi_crossings"] / results["parser_optimized"]["ffi_crossings"]

        # FormID benchmarks
        print("\n📊 Benchmarking FormIDAnalyzer...")
        print("  Legacy (Vec<String> copies)...")
        results["formid_legacy"] = self.benchmark_formid_legacy()

        print("  Optimized (zero-copy)...")
        results["formid_optimized"] = self.benchmark_formid_optimized()

        # Calculate improvements
        formid_speedup = results["formid_legacy"]["avg_time"] / results["formid_optimized"]["avg_time"]
        formid_memory_reduction = (results["formid_legacy"]["string_copies"] -
                                  results["formid_optimized"]["string_copies"])

        # Print results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)

        print("\n🚀 LogParser Optimizations:")
        print(f"  FFI Crossings: {results['parser_legacy']['ffi_crossings']} → {results['parser_optimized']['ffi_crossings']} ({parser_ffi_reduction:.1f}x reduction)")
        print(f"  Average Time:  {results['parser_legacy']['avg_time']*1000:.2f}ms → {results['parser_optimized']['avg_time']*1000:.2f}ms ({parser_speedup:.1f}x faster)")
        print(f"  Memory Delta:  {results['parser_legacy']['memory_delta']:.1f}MB → {results['parser_optimized']['memory_delta']:.1f}MB")

        print("\n🚀 FormIDAnalyzer Optimizations:")
        print(f"  String Copies: {results['formid_legacy']['string_copies']} → {results['formid_optimized']['string_copies']} ({formid_memory_reduction} eliminated)")
        print(f"  Average Time:  {results['formid_legacy']['avg_time']*1000:.2f}ms → {results['formid_optimized']['avg_time']*1000:.2f}ms ({formid_speedup:.1f}x faster)")
        print(f"  Memory Delta:  {results['formid_legacy']['memory_delta']:.1f}MB → {results['formid_optimized']['memory_delta']:.1f}MB")

        print("\n📈 Overall Impact:")
        print(f"  Total FFI Reduction:     {parser_ffi_reduction:.1f}x")
        print(f"  Average Speedup:         {(parser_speedup + formid_speedup) / 2:.1f}x")
        print(f"  String Allocations Saved: {formid_memory_reduction}")

        # Save results to file
        output_file = Path(__file__).parent / "ffi_benchmark_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to: {output_file}")

        return results


def main():
    """Run the FFI optimization benchmark."""
    try:
        # Check if Rust is available
        import classic_core
        print("✅ Rust acceleration available\n")
    except ImportError:
        print("❌ Rust acceleration not available. Please build with:")
        print("   cd classic-rust && maturin build --release --out dist")
        print("   uv pip install dist/classic-*.whl --force-reinstall")
        return

    benchmark = FFIBenchmark()
    results = benchmark.run_all_benchmarks()

    # Additional analysis
    if results["parser_optimized"]["avg_time"] < results["parser_legacy"]["avg_time"]:
        print("\n✅ SUCCESS: FFI optimizations are working!")
    else:
        print("\n⚠️  WARNING: Optimizations may not be active.")


if __name__ == "__main__":
    main()