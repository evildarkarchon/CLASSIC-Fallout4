#!/usr/bin/env python3
"""Extract p95/p99 percentiles from Criterion raw.csv files.

Criterion natively reports mean/median/MAD but not tail percentiles.
This script post-processes raw.csv to calculate p50/p95/p99.

Usage:
    python extract_percentiles.py [--output FILE] [--criterion-dir DIR]

Output format (JSON):
{
    "benchmark_name": {
        "min": 1234.5,
        "p50": 1300.0,
        "p95": 1450.0,
        "p99": 1500.0,
        "max": 1600.0,
        "mean": 1310.5,
        "stddev": 45.2,
        "unit": "ns",
        "samples": 100
    }
}

The raw.csv format from Criterion contains:
- group: benchmark group name
- function: function being benchmarked
- value: parameter value (if parameterized)
- throughput_num/throughput_type: throughput info (if applicable)
- sample_measured_value: total time for all iterations in the sample (ns)
- unit: always "ns"
- iteration_count: number of iterations in this sample

Per-iteration time = sample_measured_value / iteration_count
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import mean, stdev
from typing import Any


def calculate_percentiles(values: list[float]) -> dict[str, float]:
    """Calculate statistical percentiles from a list of values.

    Args:
        values: List of numeric values to analyze.

    Returns:
        Dictionary containing min, p50, p95, p99, max, mean, stddev.

    Raises:
        ValueError: If values list is empty.

    """
    if not values:
        raise ValueError("Cannot calculate percentiles from empty list")

    sorted_values = sorted(values)
    n = len(sorted_values)

    def percentile(p: float) -> float:
        """Calculate the p-th percentile using linear interpolation."""
        if n == 1:
            return sorted_values[0]
        # Use linear interpolation between closest ranks
        rank = (p / 100) * (n - 1)
        lower_idx = int(rank)
        upper_idx = min(lower_idx + 1, n - 1)
        weight = rank - lower_idx
        return sorted_values[lower_idx] * (1 - weight) + sorted_values[upper_idx] * weight

    result = {
        "min": sorted_values[0],
        "p50": percentile(50),
        "p95": percentile(95),
        "p99": percentile(99),
        "max": sorted_values[-1],
        "mean": mean(sorted_values),
        "samples": n,
    }

    # Standard deviation requires at least 2 samples
    if n >= 2:
        result["stddev"] = stdev(sorted_values)
    else:
        result["stddev"] = 0.0

    return result


def process_raw_csv(csv_path: Path) -> dict[str, Any] | None:
    """Process a Criterion raw.csv file and extract per-iteration times.

    Args:
        csv_path: Path to the raw.csv file.

    Returns:
        Dictionary with percentile statistics, or None if file is invalid.

    """
    try:
        with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return None

        # Calculate per-iteration times from each sample
        per_iteration_times: list[float] = []
        unit = "ns"  # Criterion always uses nanoseconds

        for row in rows:
            try:
                sample_measured_value = float(row["sample_measured_value"])
                iteration_count = int(row["iteration_count"])

                if iteration_count > 0:
                    per_iteration_time = sample_measured_value / iteration_count
                    per_iteration_times.append(per_iteration_time)

                if "unit" in row:
                    unit = row["unit"]
            except (KeyError, ValueError, TypeError):
                # Skip malformed rows
                continue

        if not per_iteration_times:
            return None

        stats = calculate_percentiles(per_iteration_times)
        stats["unit"] = unit

        return stats  # noqa: TRY300

    except (OSError, csv.Error) as e:
        print(f"Warning: Failed to process {csv_path}: {e}", file=sys.stderr)
        return None


def extract_benchmark_name(csv_path: Path) -> str:
    """Extract benchmark name from the CSV file path.

    The path structure is typically:
    target/criterion/<group>/<function>/<value>/new/raw.csv
    or
    target/criterion/<benchmark_name>/new/raw.csv

    Args:
        csv_path: Path to the raw.csv file.

    Returns:
        Extracted benchmark name.

    """
    parts = csv_path.parts
    # Find the index of "criterion" and "new" to extract the benchmark path
    try:
        criterion_idx = parts.index("criterion")
        new_idx = parts.index("new")
        benchmark_parts = parts[criterion_idx + 1 : new_idx]
        return "/".join(benchmark_parts)
    except ValueError:
        # Fallback: use parent directories
        return csv_path.parent.parent.name


def format_time(ns: float) -> str:
    """Format nanoseconds into human-readable time string.

    Args:
        ns: Time in nanoseconds.

    Returns:
        Formatted time string with appropriate unit.

    """
    if ns < 1_000:
        return f"{ns:.2f} ns"
    if ns < 1_000_000:
        return f"{ns / 1_000:.2f} us"
    if ns < 1_000_000_000:
        return f"{ns / 1_000_000:.2f} ms"
    return f"{ns / 1_000_000_000:.2f} s"


def print_summary(results: dict[str, dict[str, Any]]) -> None:
    """Print human-readable summary of percentile results.

    Args:
        results: Dictionary mapping benchmark names to their statistics.

    """
    if not results:
        print("No benchmark data found.")
        return

    print("\n" + "=" * 70)
    print("Benchmark Percentile Summary")
    print("=" * 70)

    for name, stats in sorted(results.items()):
        print(f"\n{name}:")
        print(f"  Samples:  {stats['samples']}")
        print(f"  Min:      {format_time(stats['min'])}")
        print(f"  P50:      {format_time(stats['p50'])}")
        print(f"  P95:      {format_time(stats['p95'])}")
        print(f"  P99:      {format_time(stats['p99'])}")
        print(f"  Max:      {format_time(stats['max'])}")
        print(f"  Mean:     {format_time(stats['mean'])}")
        print(f"  Stddev:   {format_time(stats['stddev'])}")

    print("\n" + "=" * 70)


def main() -> int:
    """Run percentile extraction.

    Returns:
        Exit code: 0 for success, 1 for error.

    """
    parser = argparse.ArgumentParser(
        description="Extract p95/p99 percentiles from Criterion raw.csv files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python extract_percentiles.py
    python extract_percentiles.py --output results.json
    python extract_percentiles.py --criterion-dir target/criterion
        """,
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file (default: <criterion-dir>/percentiles.json)",
    )
    parser.add_argument(
        "--criterion-dir",
        type=Path,
        default=Path("rust/target/criterion"),
        help="Path to Criterion results directory (default: rust/target/criterion)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress human-readable output, only write JSON",
    )

    args = parser.parse_args()

    criterion_dir = args.criterion_dir.resolve()

    if not criterion_dir.exists():
        print(f"Error: Criterion directory not found: {criterion_dir}", file=sys.stderr)
        print("Run benchmarks first: cargo bench", file=sys.stderr)
        return 1

    # Find all raw.csv files in the new/ subdirectories
    raw_csv_files = list(criterion_dir.glob("**/new/raw.csv"))

    if not raw_csv_files:
        print(f"No raw.csv files found in {criterion_dir}", file=sys.stderr)
        print("Run benchmarks first: cargo bench", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Found {len(raw_csv_files)} benchmark(s) to process...")

    # Process each CSV file
    results: dict[str, dict[str, Any]] = {}

    for csv_path in raw_csv_files:
        benchmark_name = extract_benchmark_name(csv_path)
        stats = process_raw_csv(csv_path)

        if stats:
            results[benchmark_name] = stats
            if not args.quiet:
                print(f"  Processed: {benchmark_name}")
        elif not args.quiet:
            print(f"  Skipped (empty/invalid): {benchmark_name}")

    if not results:
        print("No valid benchmark data found.", file=sys.stderr)
        return 1

    # Determine output path
    output_path = args.output or criterion_dir / "percentiles.json"

    # Write JSON output
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    if not args.quiet:
        print_summary(results)
        print(f"\nResults written to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
