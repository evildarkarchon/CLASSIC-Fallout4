# CLASSIC Phase 6 Comprehensive Benchmarking Suite

This benchmarking suite provides exhaustive performance testing for the Phase 6 Rust migration validation. It measures all Rust components against their Python implementations to validate performance improvements and identify optimization opportunities.

## 🎯 Performance Targets

The benchmarking suite validates the following Phase 6 performance targets:

| Component | Target Speedup | Current Implementation |
|-----------|----------------|----------------------|
| Log Parsing | **150x** | Rust + Python fallback |
| FormID Analysis | **50x** | Rust + Python fallback |
| Plugin Analysis | **30x** | Rust + Python fallback |
| Record Scanning | **40x** | Rust + Python fallback |
| Report Generation | **75x** | Rust + Python fallback |
| Database Operations | **25x** | Rust + Python fallback |
| File I/O Operations | **10-20x** | Rust + Python fallback |
| **End-to-End Processing** | **10x overall** | Complete pipeline |

## 📁 Directory Structure

```
benchmarks/
├── benchmark_suite_comprehensive.py  # Main orchestrator
├── example_benchmark_usage.py       # Usage examples
├── README.md                        # This file
├── micro_benchmarks/               # Individual component tests
│   ├── __init__.py
│   ├── benchmark_log_parsing.py    # Parser performance (150x target)
│   ├── benchmark_formid_analysis.py # FormID analysis (50x target)
│   ├── benchmark_plugin_analysis.py # Plugin analysis (30x target)
│   ├── benchmark_record_scanning.py # Record scanning (40x target)
│   ├── benchmark_report_generation.py # Report generation (75x target)
│   ├── benchmark_database_ops.py   # Database operations (25x target)
│   └── benchmark_file_io.py        # File I/O (10-20x target)
├── macro_benchmarks/               # End-to-end system tests
│   ├── __init__.py
│   ├── benchmark_end_to_end.py     # Complete pipeline (10x target)
│   └── benchmark_batch_processing.py # Batch processing scalability
├── test_data/                      # Realistic test data generation
│   ├── __init__.py
│   └── realistic_data_generator.py # Authentic test scenarios
└── reports/                        # Generated benchmark reports
    ├── benchmark_results_*.json    # Raw results
    ├── benchmark_summary_*.json    # Summary data
    ├── benchmark_report_*.md       # Detailed markdown reports
    ├── benchmark_summary_*.csv     # CSV for spreadsheet analysis
    └── latest_results.json         # Symlink to most recent results
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.12+** with required dependencies installed
2. **CLASSIC project** set up and working
3. **Rust components** (optional but recommended):
   ```bash
   maturin develop --release
   # or
   maturin build --release --out dist
   uv pip install dist/classic-*.whl --force-reinstall
   ```

### Basic Usage

```bash
# Quick validation (3 minutes)
python benchmarks/example_benchmark_usage.py --mode quick

# Comprehensive benchmark (15-30 minutes)
python benchmarks/example_benchmark_usage.py --mode full

# Regression testing
python benchmarks/example_benchmark_usage.py --mode regression
```

### Advanced Usage

```bash
# Direct suite usage with custom parameters
python benchmarks/benchmark_suite_comprehensive.py \
    --benchmark-types micro macro \
    --test-sizes small medium large \
    --iterations 5 \
    --parallel
```

## 🔬 Benchmark Types

### Micro-Benchmarks

Test individual components in isolation to measure specific performance characteristics:

- **Log Parsing**: Crash log segment extraction and parsing
- **FormID Analysis**: FormID extraction and validation from call stacks
- **Plugin Analysis**: Load order parsing and plugin metadata processing
- **Record Scanning**: Named record pattern matching and identification
- **Report Generation**: Report composition and string formatting
- **Database Operations**: FormID database lookups and connection pooling
- **File I/O**: File reading, encoding detection, and batch processing

### Macro-Benchmarks

Test complete workflows and system integration:

- **End-to-End Pipeline**: Complete crash log processing workflow
- **Batch Processing**: Multiple file processing with parallelization
- **Memory Intensive**: Large dataset processing and memory profiling
- **Scalability Testing**: Performance scaling with different data sizes

### Test Data Sizes

| Size | Files | Lines/File | Plugins | Use Case |
|------|-------|------------|---------|----------|
| Tiny | 10 | 100 | 50 | Quick validation |
| Small | 50 | 500 | 100 | Standard testing |
| Medium | 100 | 1000 | 200 | Realistic workloads |
| Large | 500 | 2000 | 500 | Stress testing |
| Huge | 1000 | 5000 | 1000 | Maximum stress |

## 📊 Output and Reports

The benchmarking suite generates comprehensive reports in multiple formats:

### JSON Reports
- `benchmark_results_*.json`: Complete raw data with all metrics
- `benchmark_summary_*.json`: Executive summary and key metrics
- `latest_results.json`: Symlink to most recent results

### Markdown Reports
- `benchmark_report_*.md`: Detailed analysis with recommendations
- Performance comparisons and statistical analysis
- Optimization priorities and actionable insights
- Component-by-component breakdown

### CSV Reports
- `benchmark_summary_*.csv`: Spreadsheet-compatible data
- Easy import into Excel, Google Sheets, or data analysis tools

### Report Contents

Each report includes:

1. **Executive Summary**
   - Overall performance status
   - Target achievement rates
   - System recommendations

2. **Component Analysis**
   - Individual component performance
   - Speedup factors and confidence intervals
   - Memory usage and efficiency metrics

3. **Optimization Priorities**
   - High-impact optimization opportunities
   - Component-specific recommendations
   - Resource allocation guidance

4. **Regression Analysis**
   - Performance changes over time
   - Baseline comparisons
   - Trend identification

5. **System Information**
   - Rust component availability
   - Test configuration details
   - Environment specifications

## 🎛️ Configuration Options

### Benchmark Parameters

```python
suite.run_comprehensive_benchmark(
    benchmark_types=[BenchmarkType.MICRO, BenchmarkType.MACRO],
    test_sizes=[TestDataSize.SMALL, TestDataSize.MEDIUM],
    iterations=5,                     # Number of test runs per benchmark
    include_memory_profiling=True,    # Enable memory usage tracking
    parallel_execution=True           # Use parallel processing where possible
)
```

### Test Data Configuration

```python
generator = RealisticDataGenerator(seed=42)  # Reproducible data
dataset = generator.generate_comprehensive_dataset(
    num_crash_logs=100,
    lines_per_log=1000,
    num_plugins=200,
    include_formids=True,
    include_edge_cases=True,
    corruption_probability=0.02,      # 2% data corruption for robustness
    vary_formats=True,                # Multiple log formats
    game_type='fallout4'             # Game-specific templates
)
```

### Output Configuration

```python
suite = ComprehensiveBenchmarkSuite(
    output_dir=Path("custom_reports"),           # Custom report location
    baseline_dir=Path("performance_baselines")  # Regression test baselines
)
```

## 📈 Performance Analysis Features

### Statistical Analysis
- **Confidence intervals** for performance measurements
- **Statistical significance testing** between implementations
- **Outlier detection** and handling
- **Performance variance** analysis

### Memory Profiling
- **Peak memory usage** tracking
- **Memory allocation patterns**
- **Leak detection** across test iterations
- **Garbage collection impact** analysis

### Regression Testing
- **Baseline storage** and comparison
- **Performance trend tracking**
- **Automated regression detection**
- **Historical performance data**

### Optimization Recommendations
- **Component-specific guidance**
- **Priority-based optimization lists**
- **Resource allocation advice**
- **Architecture improvement suggestions**

## 🛠️ Integration with Development Workflow

### Pre-Release Validation

```bash
# Validate performance before release
python benchmarks/example_benchmark_usage.py --mode full
# Check that all targets are achieved and no regressions exist
```

### Continuous Integration

```bash
# Quick validation in CI pipeline
python benchmarks/example_benchmark_usage.py --mode quick
# Fail build if critical regressions detected
```

### Performance Monitoring

```bash
# Regular performance monitoring
python benchmarks/example_benchmark_usage.py --mode regression
# Track performance trends over time
```

## 📝 Interpreting Results

### Success Criteria

- **Target Achievement**: ≥80% of performance targets met
- **Error Rate**: ≤1% errors during benchmark execution
- **Statistical Significance**: Performance differences confirmed with 95% confidence
- **Memory Efficiency**: Rust implementations should not use >20% more memory than Python

### Warning Signs

- **High Variance**: Standard deviation >20% of mean execution time
- **Memory Leaks**: Increasing memory usage across iterations
- **Component Failures**: >5% error rate in any component
- **Regression Detection**: >10% performance decrease from baseline

### Optimization Priority

1. **High Priority**: <50% of target achieved, affects critical path
2. **Medium Priority**: 50-80% of target achieved, moderate impact
3. **Low Priority**: >80% of target achieved, minor optimizations

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure CLASSIC project is set up correctly
   python -c "import ClassicLib; print('✅ ClassicLib available')"

   # Check Rust component availability
   python -c "from ClassicLib.RustIntegration import print_rust_status; print_rust_status()"
   ```

2. **Rust Components Not Found**
   ```bash
   # Build Rust components
   maturin develop --release

   # Or install wheel
   maturin build --release --out dist
   uv pip install dist/classic-*.whl --force-reinstall
   ```

3. **Memory Issues**
   ```bash
   # Reduce test data size
   --test-sizes tiny small

   # Disable memory profiling
   --no-memory
   ```

4. **Long Execution Times**
   ```bash
   # Reduce iterations
   --iterations 3

   # Use smaller test sizes
   --test-sizes small medium
   ```

### Performance Debugging

If benchmarks show unexpected results:

1. **Check Component Availability**: Verify all Rust components are loaded
2. **Review System Resources**: Ensure adequate CPU and memory
3. **Examine Test Data**: Validate test data generation and quality
4. **Enable Detailed Logging**: Use verbose mode for debugging
5. **Compare Baselines**: Check against known good performance baselines

## 🤝 Contributing

### Adding New Benchmarks

1. Create benchmark class in appropriate directory
2. Implement standard interface methods
3. Add comprehensive test scenarios
4. Include performance target validation
5. Update main orchestrator integration

### Benchmark Interface

```python
class NewBenchmark:
    component_name = "new_component"

    def run_benchmark(self, implementation: str, dataset: Dict[str, Any],
                     warm_up: bool = False) -> BenchmarkResult:
        """Execute benchmark with specified implementation."""
        pass
```

### Test Data Generation

Add new realistic test scenarios to `realistic_data_generator.py`:

```python
def generate_new_scenario_data(self, **kwargs) -> Dict[str, Any]:
    """Generate data for new benchmark scenarios."""
    pass
```

## 📄 License

This benchmarking suite is part of the CLASSIC project and follows the same license terms.

## 📞 Support

For issues with the benchmarking suite:

1. Check this README for common solutions
2. Review the generated log files in `benchmarks/reports/`
3. Examine the detailed error messages and stack traces
4. Verify system requirements and dependencies
5. Test with reduced complexity (fewer iterations, smaller data sizes)

---

**Note**: This benchmarking suite is designed to validate the Phase 6 Rust migration performance improvements. Results should be interpreted in the context of the overall CLASSIC performance optimization goals and user experience improvements.
