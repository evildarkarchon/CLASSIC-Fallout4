"""
Micro-benchmarks module for individual Rust component testing.

This module contains benchmarks that test individual components in isolation
to measure their specific performance characteristics and identify optimization
opportunities at the component level.

Each micro-benchmark follows a standardized interface:
- component_name: String identifier for the component
- run_benchmark(implementation, dataset, warm_up=False): Execute benchmark
- Supports both "rust" and "python" implementations
- Returns performance metrics and results

Micro-benchmark components:
- benchmark_log_parsing: LogParser component (target: 150x speedup)
- benchmark_formid_analysis: FormIDAnalyzer component (target: 50x speedup)
- benchmark_plugin_analysis: PluginAnalyzer component (target: 30x speedup)
- benchmark_record_scanning: RecordScanner component (target: 40x speedup)
- benchmark_report_generation: ReportGeneration component (target: 75x speedup)
- benchmark_database_ops: Database operations (target: 25x speedup)
- benchmark_file_io: File I/O operations (target: 10-20x speedup)
"""

__all__ = [
    'benchmark_log_parsing',
    'benchmark_formid_analysis',
    'benchmark_plugin_analysis',
    'benchmark_record_scanning',
    'benchmark_report_generation',
    'benchmark_database_ops',
    'benchmark_file_io',
]
