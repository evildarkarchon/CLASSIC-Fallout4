#!/usr/bin/env python3
"""
Example usage of the CLASSIC Phase 6 Comprehensive Benchmark Suite.

This script demonstrates how to use the benchmarking suite to validate
Rust performance improvements against the target specifications.

Performance targets for Phase 6:
- Log parsing: 150x speedup
- FormID analysis: 50x speedup
- Plugin analysis: 30x speedup
- Record scanning: 40x speedup
- Report generation: 75x speedup
- Database operations: 25x speedup
- File I/O operations: 10-20x speedup
- End-to-end processing: 10x overall speedup
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now we can import the benchmark suite
from benchmarks.benchmark_suite_comprehensive import (
    BenchmarkType,
    ComprehensiveBenchmarkSuite,
    TestDataSize,
)


def run_quick_validation():
    """Run a quick validation benchmark to check system functionality."""
    print("=" * 80)
    print("🚀 CLASSIC Phase 6 - Quick Validation Benchmark")
    print("=" * 80)

    # Initialize benchmark suite
    suite = ComprehensiveBenchmarkSuite(
        output_dir=Path("benchmarks/reports"),
        baseline_dir=Path("performance_baselines")
    )

    # Run quick benchmark with small dataset
    results = suite.run_comprehensive_benchmark(
        benchmark_types=[BenchmarkType.MICRO],
        test_sizes=[TestDataSize.TINY],
        iterations=3,
        include_memory_profiling=False,
        parallel_execution=False
    )

    # Display results summary
    summary = results.get('summary', {})
    overall = summary.get('overall_assessment', {})

    print("\n📊 Quick Validation Results:")
    print(f"   Status: {overall.get('status', 'Unknown')}")
    print(f"   Targets Achieved: {overall.get('targets_achieved', 0)}/{overall.get('total_comparisons', 0)}")
    print(f"   Average Speedup: {overall.get('average_speedup', 0):.2f}x")

    return results


def run_full_benchmark():
    """Run comprehensive benchmark with all test types and sizes."""
    print("=" * 80)
    print("🚀 CLASSIC Phase 6 - Full Comprehensive Benchmark")
    print("=" * 80)

    # Initialize benchmark suite
    suite = ComprehensiveBenchmarkSuite()

    # Run comprehensive benchmark
    results = suite.run_comprehensive_benchmark(
        benchmark_types=[BenchmarkType.MICRO, BenchmarkType.MACRO],
        test_sizes=[TestDataSize.SMALL, TestDataSize.MEDIUM, TestDataSize.LARGE],
        iterations=5,
        include_memory_profiling=True,
        parallel_execution=True
    )

    # Display comprehensive results
    summary = results.get('summary', {})
    overall = summary.get('overall_assessment', {})

    print("\n📊 Comprehensive Benchmark Results:")
    print(f"   Status: {overall.get('status', 'Unknown')}")
    print(f"   Message: {overall.get('message', 'No message available')}")
    print(f"   Targets Achieved: {overall.get('targets_achieved', 0)}/{overall.get('total_comparisons', 0)} "
          f"({overall.get('target_achievement_rate', 0):.1f}%)")
    print(f"   Average Speedup: {overall.get('average_speedup', 0):.2f}x")

    # Show component performance summary
    component_summary = summary.get('component_summary', {})
    print("\n🔧 Component Performance:")
    for component, perf_data in component_summary.items():
        print(f"   {component}:")
        print(f"     Speedup: {perf_data.get('avg_speedup', 0):.1f}x")
        print(f"     Target Achievement: {perf_data.get('target_achievement_rate', 0):.1f}%")

    # Show optimization priorities
    optimization_priorities = summary.get('optimization_priorities', [])
    if optimization_priorities:
        print("\n⚡ Top Optimization Priorities:")
        for priority in optimization_priorities[:3]:
            print(f"   {priority.get('priority', 'UNKNOWN')}: {priority.get('component', 'Unknown')} "
                  f"({priority.get('target_achievement', 0):.1f}% of target)")

    # Show Rust acceleration status
    rust_status = summary.get('rust_acceleration_status', {})
    print("\n🦀 Rust Acceleration Status:")
    print(f"   Components Active: {rust_status.get('components_active', 0)}/{rust_status.get('components_total', 0)} "
          f"({rust_status.get('acceleration_percentage', 0):.1f}%)")

    missing_components = rust_status.get('missing_components', [])
    if missing_components:
        print(f"   Missing: {', '.join(missing_components)}")
    else:
        print("   All components available!")

    return results


def run_regression_test():
    """Run regression testing against stored baselines."""
    print("=" * 80)
    print("📈 CLASSIC Phase 6 - Regression Testing")
    print("=" * 80)

    # Initialize benchmark suite
    suite = ComprehensiveBenchmarkSuite()

    # Check if we have recent results to compare
    latest_results_file = Path("benchmarks/reports/latest_results.json")

    if not latest_results_file.exists():
        print("⚠️  No recent benchmark results found.")
        print("   Running benchmark first to establish baseline...")

        # Run benchmark to create baseline
        results = suite.run_comprehensive_benchmark(
            benchmark_types=[BenchmarkType.MICRO],
            test_sizes=[TestDataSize.MEDIUM],
            iterations=3,
            include_memory_profiling=False
        )
    else:
        print("✅ Found recent benchmark results, loading for regression analysis...")
        import json
        with Path(latest_results_file).open() as f:
            results = json.load(f)

    # Run regression analysis
    regression_results = suite.compare_with_baseline(results)

    print("\n📊 Regression Analysis Results:")
    print(f"   Status: {regression_results.get('overall_status', 'Unknown')}")
    print(f"   Baseline Date: {regression_results.get('baseline_date', 'Unknown')}")
    print(f"   Current Date: {regression_results.get('current_date', 'Unknown')}")

    regressions = regression_results.get('regressions_detected', [])
    improvements = regression_results.get('improvements_detected', [])

    if regressions:
        print(f"\n❌ Performance Regressions Detected ({len(regressions)}):")
        for reg in regressions[:5]:  # Show top 5
            print(f"   {reg.get('component', 'Unknown')} ({reg.get('test_size', 'Unknown')}): "
                  f"{reg.get('performance_change', 0):+.1f}%")

    if improvements:
        print(f"\n✅ Performance Improvements Detected ({len(improvements)}):")
        for imp in improvements[:5]:  # Show top 5
            print(f"   {imp.get('component', 'Unknown')} ({imp.get('test_size', 'Unknown')}): "
                  f"{imp.get('performance_change', 0):+.1f}%")

    if not regressions and not improvements:
        print("\n✅ No significant performance changes detected.")

    return regression_results


def main():
    """Main entry point with command-line argument handling."""
    import argparse

    parser = argparse.ArgumentParser(
        description="CLASSIC Phase 6 Benchmark Suite Example Usage"
    )
    parser.add_argument("--mode", choices=['quick', 'full', 'regression'], default='quick',
                       help="Benchmark mode to run (default: quick)")
    parser.add_argument("--output-dir", type=Path,
                       help="Output directory for results")

    args = parser.parse_args()

    # Check if we're in the right directory
    if not Path("ClassicLib").exists():
        print("❌ Error: Please run this script from the CLASSIC project root directory")
        print("   Current directory should contain ClassicLib/ folder")
        sys.exit(1)

    try:
        if args.mode == 'quick':
            results = run_quick_validation()
        elif args.mode == 'full':
            results = run_full_benchmark()
        elif args.mode == 'regression':
            results = run_regression_test()

        print("\n✅ Benchmark completed successfully!")
        print("   Results saved in: benchmarks/reports/")
        print("   Check the generated markdown and CSV reports for detailed analysis.")

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("   Make sure all required dependencies are installed:")
        print("   - ClassicLib modules must be available")
        print("   - Rust components should be built (optional but recommended)")
        print("   Run: maturin develop --release (if using Rust acceleration)")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        print("   Check the log files in benchmarks/reports/ for detailed error information")
        sys.exit(1)


if __name__ == "__main__":
    main()
