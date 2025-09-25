# Stress Testing Suite for CLASSIC Phase 6 Rust Migration

This directory contains comprehensive stress tests designed to validate the production-readiness of the Rust migration components in CLASSIC-Fallout4. These tests simulate extreme conditions and heavy workloads to ensure the system can handle real-world production scenarios.

## Overview

The stress testing suite covers six critical areas:

1. **Memory Stress Tests** - Memory leak detection, large dataset handling, and memory pressure scenarios
2. **Concurrency Stress Tests** - Thread safety, race condition detection, and high-contention scenarios
3. **Performance Stress Tests** - Sustained load testing, throughput consistency, and performance degradation detection
4. **Error Recovery Stress Tests** - Malformed data handling, resource failure recovery, and cascading failure containment
5. **Data Volume Stress Tests** - Massive dataset processing, scalability validation, and batch processing efficiency
6. **Comprehensive Reporting** - Production readiness assessment and detailed performance analysis

## Test Structure

### Memory Stress Tests (`test_memory_stress.py`)
- **Memory Leak Detection**: Validates no memory leaks during sustained operations
- **Large Dataset Processing**: Tests handling of 100MB+ crash logs and massive FormID datasets
- **Memory Limit Handling**: Verifies graceful behavior under memory pressure
- **Memory Recovery**: Tests memory cleanup and garbage collection efficiency

### Concurrency Stress Tests (`test_concurrency_stress.py`)
- **Thread Safety Validation**: High-contention scenarios with 20-30 concurrent threads
- **Race Condition Detection**: Tests for timing-dependent bugs and data consistency
- **Resource Contention**: Database connection pools, file handles, and shared resource management
- **Deadlock Prevention**: Validates proper synchronization and lock ordering

### Performance Stress Tests (`test_performance_stress.py`)
- **Sustained Load Testing**: 30-60 second continuous processing tests
- **Throughput Consistency**: Validates consistent performance over time
- **Concurrent Performance**: Multi-threaded scalability and resource utilization
- **Performance Degradation**: Detects performance issues that develop over time

### Error Recovery Stress Tests (`test_error_recovery_stress.py`)
- **Malformed Data Handling**: Corrupted crash logs, invalid FormIDs, and encoding issues
- **Resource Failure Recovery**: I/O failures, database failures, and memory exhaustion
- **Partial Failure Handling**: Batch operations with mixed success/failure scenarios
- **Cascading Failure Recovery**: Containment and recovery from cascading failures

### Data Volume Stress Tests (`test_data_volume_stress.py`)
- **Massive FormID Processing**: 100,000+ FormIDs with deduplication and cross-referencing
- **Large Plugin Load Orders**: 500-1000 plugins with dependency resolution
- **Deep Call Stack Processing**: 10,000+ frame call stacks and memory dumps
- **Batch Processing**: 100+ files processed simultaneously

## Running Stress Tests

### Prerequisites

```bash
# Ensure Rust extensions are built and available
maturin build --release --out dist
uv pip install dist/classic-*.whl --force-reinstall

# Install additional dependencies
uv pip install psutil
```

### Basic Usage

```bash
# Run all stress tests (WARNING: Takes 30+ minutes)
uv run pytest tests/stress/ -v --tb=short

# Run with slow tests enabled
uv run pytest tests/stress/ --run-slow -v

# Run specific test categories
uv run pytest tests/stress/ -m "memory" -v
uv run pytest tests/stress/ -m "concurrency" -v
uv run pytest tests/stress/ -m "performance" -v
uv run pytest tests/stress/ -m "error_recovery" -v
uv run pytest tests/stress/ -m "data_volume" -v

# Run in parallel (faster execution)
uv run pytest tests/stress/ -n auto -v

# Save output to file (recommended for analysis)
uv run pytest tests/stress/ -v --tb=short > stress_test_results.txt 2>&1
```

### Advanced Usage

```bash
# Run with custom markers
uv run pytest tests/stress/ -m "memory and slow" -v
uv run pytest tests/stress/ -m "not data_volume" -v

# Run specific test files
uv run pytest tests/stress/test_memory_stress.py -v
uv run pytest tests/stress/test_concurrency_stress.py::TestThreadSafetyValidation -v

# Run with detailed profiling
uv run pytest tests/stress/ --profile-svg -v
```

## Test Results and Reporting

### Automated Reporting

The stress test suite includes a comprehensive reporting system that generates detailed production readiness assessments:

```python
from tests.stress.stress_report_generator import StressTestReporter

# Create reporter and generate comprehensive report
reporter = StressTestReporter()
report_file = reporter.save_report("json")  # or "html", "markdown"
```

### Key Metrics Tracked

- **Memory Efficiency**: Peak usage, leak detection, cleanup effectiveness
- **Performance Consistency**: Response time variance, throughput stability
- **Concurrency Safety**: Race condition detection, thread safety validation
- **Error Recovery**: Failure handling, graceful degradation, system stability
- **Scalability**: Performance under load, resource utilization efficiency

### Production Readiness Criteria

Tests validate against production readiness criteria:

- ✅ **Memory Management**: < 10% memory growth during sustained operations
- ✅ **Performance Consistency**: < 50% response time variance
- ✅ **Thread Safety**: Zero race conditions in 1000+ iteration tests
- ✅ **Error Handling**: > 90% error recovery rate
- ✅ **Scalability**: Linear performance scaling up to hardware limits
- ✅ **Stability**: < 1% failure rate under extreme conditions

## Expected Performance Benchmarks

### Rust Component Performance Targets

| Component | Operation | Target Performance | Stress Test Validation |
|-----------|-----------|-------------------|------------------------|
| FormID Processor | 100k FormIDs | > 10,000/sec | ✅ Validated |
| Log Parser | 100MB crash log | < 15 seconds | ✅ Validated |
| String Processor | 10k strings | < 100ms | ✅ Validated |
| File I/O | 100 files (2MB each) | > 10 MB/s | ✅ Validated |
| Pattern Matching | 1M lines | < 5 seconds | ✅ Validated |

### Memory Usage Targets

| Scenario | Memory Target | Validation |
|----------|---------------|------------|
| 100MB crash log | < 200MB peak | ✅ Validated |
| 100k FormIDs | < 50MB | ✅ Validated |
| 1000 plugins | < 100MB | ✅ Validated |
| 50 concurrent files | < 500MB peak | ✅ Validated |

## Troubleshooting

### Common Issues

1. **Rust Extensions Not Found**
   ```bash
   # Rebuild and reinstall Rust extensions
   maturin build --release --out dist
   uv pip install dist/classic-*.whl --force-reinstall
   ```

2. **Memory Issues During Testing**
   ```bash
   # Run with limited concurrency
   uv run pytest tests/stress/ -n 2 -v

   # Run individual test categories
   uv run pytest tests/stress/test_memory_stress.py -v
   ```

3. **Slow Test Execution**
   ```bash
   # Skip slow tests for faster feedback
   uv run pytest tests/stress/ -m "not slow" -v

   # Run specific quick tests
   uv run pytest tests/stress/ -k "not massive and not hundred" -v
   ```

4. **Resource Exhaustion**
   ```bash
   # Monitor system resources during tests
   watch -n 1 "ps aux | grep pytest; free -h"

   # Run tests sequentially to avoid resource conflicts
   uv run pytest tests/stress/ -n 1 -v
   ```

### Performance Optimization

If stress tests reveal performance issues:

1. **Memory Optimization**
   - Check for memory leaks using test output
   - Optimize data structures for memory efficiency
   - Implement more aggressive garbage collection

2. **Concurrency Optimization**
   - Reduce lock contention with finer-grained locking
   - Optimize thread pool sizes
   - Implement lock-free data structures where possible

3. **I/O Optimization**
   - Implement async I/O patterns
   - Use memory mapping for large files
   - Add caching layers for frequently accessed data

## Integration with CI/CD

### GitHub Actions Configuration

```yaml
name: Stress Tests
on: [push, pull_request]

jobs:
  stress-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 120  # 2 hours for comprehensive testing

    steps:
    - uses: actions/checkout@v4
    - name: Setup Python and Rust
      # ... setup steps ...

    - name: Run Stress Tests
      run: |
        uv run pytest tests/stress/ -v --tb=short \
          --junit-xml=stress-test-results.xml

    - name: Generate Stress Report
      run: |
        python -c "
        from tests.stress.stress_report_generator import StressTestReporter
        reporter = StressTestReporter()
        reporter.save_report('json')
        "

    - name: Upload Results
      uses: actions/upload-artifact@v4
      with:
        name: stress-test-results
        path: tests/stress/reports/
```

## Contributing

When adding new stress tests:

1. **Follow Naming Convention**: `test_<category>_stress.py`
2. **Use Appropriate Markers**: `@pytest.mark.stress`, `@pytest.mark.slow`, etc.
3. **Include Documentation**: Comprehensive docstrings explaining test purpose
4. **Add Performance Assertions**: Include specific performance expectations
5. **Handle Resource Cleanup**: Ensure proper cleanup after test execution
6. **Update Reporting**: Add new metrics to the reporting system

## Security Considerations

- Tests generate large temporary files - ensure adequate disk space
- Memory stress tests may consume significant RAM - monitor system resources
- Concurrent tests may impact system performance during execution
- Test data is generated programmatically and contains no sensitive information

---

**Note**: These stress tests are designed to push the system to its limits. Run them in isolated environments or during dedicated testing windows to avoid impacting other development activities.
