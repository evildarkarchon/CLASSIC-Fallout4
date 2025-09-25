# Rust Integration Tests

This directory contains comprehensive end-to-end integration tests for Phase 6 Rust migration validation. These tests validate that all Rust components work together correctly with real crash log data and provide the expected performance improvements.

## Test Structure

### Core Test Files

- **`test_e2e_pipeline.py`** - End-to-end pipeline tests using real crash log data
- **`test_component_integration.py`** - Component interaction and data flow tests
- **`test_real_data_validation.py`** - Validation tests using actual crash logs
- **`test_performance_integration.py`** - Performance benchmarking and validation

### Test Fixtures (`fixtures/`)

- **`crash_log_factory.py`** - Factory for generating realistic crash log test data
- **`mock_data_factory.py`** - Factory for creating mock objects and test doubles
- **`performance_fixtures.py`** - Performance testing utilities and benchmarking tools
- **`validation_utilities.py`** - Validation and comparison utilities

## Test Categories

### 1. End-to-End Pipeline Tests (`test_e2e_pipeline.py`)

**Purpose**: Validate the complete crash log processing pipeline with all Rust components.

**Key Test Areas**:
- Complete pipeline processing with real crash logs
- Output consistency between Rust and Python implementations
- FormID extraction integration across the pipeline
- Plugin analysis integration in the complete pipeline
- Record scanning integration in the complete pipeline
- Error handling and fallback mechanisms
- Concurrent processing of multiple crash logs
- Performance improvements in real-world scenarios

**Markers**: `@pytest.mark.rust`, `@pytest.mark.integration`, `@pytest.mark.e2e`

### 2. Component Integration Tests (`test_component_integration.py`)

**Purpose**: Test how all Rust components work together and validate data flow between components.

**Key Test Areas**:
- Data flow from LogParser → FormIDAnalyzer
- Data flow from LogParser → PluginAnalyzer
- Data flow from LogParser → RecordScanner
- Integrated component chain processing
- Error isolation and recovery mechanisms
- Thread safety and concurrent access patterns
- Memory management across component boundaries

**Markers**: `@pytest.mark.rust`, `@pytest.mark.integration`, `@pytest.mark.component`

### 3. Real Data Validation Tests (`test_real_data_validation.py`)

**Purpose**: Validate Rust components using actual crash logs and test accuracy with real-world data.

**Key Test Areas**:
- FormID extraction accuracy with real crash data
- Plugin analysis with authentic load orders
- Record scanning with real crash log patterns
- Cross-validation between Rust and Python implementations
- Edge cases and malformed data handling
- Performance characteristics with varying log sizes
- Known pattern recognition and accuracy

**Markers**: `@pytest.mark.rust`, `@pytest.mark.integration`, `@pytest.mark.real_data`

### 4. Performance Integration Tests (`test_performance_integration.py`)

**Purpose**: Comprehensive performance testing and benchmarking of Rust components.

**Key Test Areas**:
- Performance scaling across different data sizes
- Memory usage optimization and leak detection
- Concurrent processing performance
- Performance regression detection
- Throughput and latency measurements
- Integrated pipeline performance
- Memory efficiency validation

**Markers**: `@pytest.mark.rust`, `@pytest.mark.integration`, `@pytest.mark.performance`

## Running the Tests

### Prerequisites

1. **Rust Components**: Ensure Rust components are built and available:
   ```bash
   maturin build --release --out dist
   uv pip install dist/classic-*.whl --force-reinstall
   ```

2. **Test Dependencies**: Install test dependencies:
   ```bash
   uv sync --all-extras
   ```

### Basic Test Execution

```bash
# Run all Rust integration tests
uv run pytest tests/rust_integration/ -v

# Run specific test categories
uv run pytest tests/rust_integration/ -m "e2e" -v
uv run pytest tests/rust_integration/ -m "component" -v
uv run pytest tests/rust_integration/ -m "real_data" -v
uv run pytest tests/rust_integration/ -m "performance" -v

# Run tests in parallel
uv run pytest tests/rust_integration/ -n auto -v
```

### Performance Testing

```bash
# Run only performance tests
uv run pytest tests/rust_integration/ -m "performance" -v -s

# Run performance tests with detailed output
uv run pytest tests/rust_integration/test_performance_integration.py -v -s --tb=short
```

### Real Data Testing

```bash
# Run real data validation tests
uv run pytest tests/rust_integration/ -m "real_data" -v -s

# Run with specific crash log samples
uv run pytest tests/rust_integration/test_real_data_validation.py::TestRealCrashLogValidation::test_formid_extraction_accuracy -v -s
```

## Test Configuration

### Environment Variables

- `CLASSIC_RUST_COMPONENTS_REQUIRED` - Fail tests if Rust components not available
- `CLASSIC_TEST_CRASH_LOGS_PATH` - Path to crash logs for real data testing
- `CLASSIC_TEST_PERFORMANCE_BASELINE` - Path to performance baseline data

### Pytest Markers

The tests use the following pytest markers:

- `rust` - Tests that require Rust components
- `integration` - Integration tests (as opposed to unit tests)
- `e2e` - End-to-end pipeline tests
- `component` - Component interaction tests
- `real_data` - Tests using real crash log data
- `performance` - Performance and benchmarking tests
- `slow` - Tests that take longer to execute

### Skipping Tests

Tests automatically skip when:
- Rust components are not available (`pytest.importorskip("classic_core")`)
- Specific Rust components are not accelerated (`is_rust_accelerated()` checks)
- Real crash log data is not available (falls back to synthetic data)

## Test Data

### Real Crash Logs

Tests look for real crash logs in:
1. `CLASSIC Backup/Unsolved Logs/` (project backup directory)
2. Path specified by `CLASSIC_TEST_CRASH_LOGS_PATH` environment variable
3. Falls back to synthetic data if real logs unavailable

### Synthetic Data

The `CrashLogFactory` generates realistic crash logs for testing:
- Multiple crash log types (Buffout4, Crash Logger, etc.)
- Scalable data sizes for performance testing
- Realistic FormIDs, plugin structures, and load orders
- Corrupted data for error handling tests

## Performance Targets

The tests validate against these performance targets:

### Parser Performance
- Small logs (< 1000 lines): < 10ms
- Medium logs (< 5000 lines): < 50ms
- Large logs (< 20000 lines): < 150ms
- Extra large logs: < 500ms

### FormID Analyzer Performance
- > 1000 FormIDs/second extraction rate
- < 50ms for typical crash logs

### Plugin Analyzer Performance
- > 5000 plugins/second parsing rate
- < 50ms for typical load orders

### Integrated Pipeline Performance
- Small logs: < 50ms total
- Medium logs: < 150ms total
- Large logs: < 500ms total
- Extra large logs: < 2s total

## Memory Usage Targets

- Memory growth: < 50MB for repeated processing
- Peak memory: < 100MB above baseline
- No memory leaks in concurrent processing

## Validation Criteria

### Data Accuracy
- FormID extraction: > 90% validity ratio
- Plugin parsing: > 95% validity ratio
- Record scanning: > 70% validity ratio

### Cross-Implementation Consistency
- > 90% similarity between Rust and Python results
- Structural consistency in output format
- Equivalent error handling behavior

### Performance Requirements
- At least 50% of operations meet performance targets
- No performance regressions > 20%
- Reasonable scaling characteristics (sub-quadratic)

## Troubleshooting

### Common Issues

1. **"Rust extensions not available"**
   ```bash
   # Rebuild and reinstall Rust components
   maturin build --release --out dist
   uv pip install dist/classic-*.whl --force-reinstall
   ```

2. **"No crash logs available for testing"**
   - Ensure `CLASSIC Backup/Unsolved Logs/` contains `.log` files
   - Set `CLASSIC_TEST_CRASH_LOGS_PATH` to crash log directory
   - Tests will use synthetic data if no real logs found

3. **Performance tests failing**
   - Check system load during testing
   - Run tests with `--tb=short` for cleaner output
   - Some performance targets may need adjustment for different hardware

4. **Memory tracking errors**
   - Install `psutil` for memory monitoring: `uv add psutil`
   - Tests fall back to mock memory tracking if `psutil` unavailable

### Debugging

```bash
# Run with verbose output and no capture
uv run pytest tests/rust_integration/ -v -s --tb=long

# Run single test with debugging
uv run pytest tests/rust_integration/test_e2e_pipeline.py::TestE2EPipeline::test_complete_pipeline_with_rust -v -s

# Check Rust component status
python -c "from ClassicLib.RustIntegration import print_rust_status; print_rust_status()"
```

## Contributing

When adding new integration tests:

1. **Follow naming conventions**: `test_<component>_<type>.py`
2. **Use appropriate markers**: Add `@pytest.mark.rust` and specific markers
3. **Include comprehensive docstrings**: Explain what is being tested and why
4. **Add performance targets**: Include expected performance characteristics
5. **Handle component availability**: Skip gracefully when Rust components unavailable
6. **Validate results thoroughly**: Use validation utilities for consistency checks

## Integration with CI/CD

These tests are designed to run in CI/CD pipelines:

- Automatic skipping when Rust components unavailable
- Synthetic data fallback when real crash logs unavailable
- Performance baseline comparison for regression detection
- Comprehensive reporting for validation results
- Parallel execution support for faster CI runs

The tests provide comprehensive validation that the Rust migration maintains functionality while providing significant performance improvements.
