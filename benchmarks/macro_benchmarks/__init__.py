"""
Macro-benchmarks module for end-to-end system testing.

This module contains benchmarks that test complete workflows and pipelines
to measure overall system performance and identify bottlenecks in the
integration between components.

Macro-benchmark components:
- benchmark_end_to_end: Complete crash log processing pipeline
- benchmark_batch_processing: Batch processing performance with multiple files
- benchmark_pipeline_integration: Component integration and data flow testing
- benchmark_memory_intensive: Memory-intensive workload testing

Each macro-benchmark tests realistic usage scenarios and measures:
- Total processing time for complete workflows
- Memory usage patterns across the entire pipeline
- Component interaction overhead
- Scalability with different data sizes
- Error handling and recovery in complex scenarios
"""

__all__ = [
    'benchmark_end_to_end',
    'benchmark_batch_processing',
]
