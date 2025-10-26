# Rust-Python Test Parity

This document tracks the parity between Rust unit tests and Python integration tests for the CLASSIC project's Rust acceleration layer.

## Overview

All Rust components have corresponding Python integration tests to ensure that the PyO3 bindings work correctly and maintain functional parity with the Rust implementations.

## Test Coverage

### 1. Pattern Matcher (`PatternMatcher`)

**Rust Tests**: `classic-rust/tests/test_patterns.rs`
**Python Tests**: `tests/rust_integration/test_pattern_matcher_parity.py`

Coverage:
- ✅ Basic pattern creation and matching
- ✅ Multi-pattern matching with Aho-Corasick
- ✅ Cache effectiveness and management
- ✅ Case-insensitive matching
- ✅ Edge cases (empty patterns, special characters, unicode)
- ✅ Performance characteristics
- ✅ PyO3 integration and error handling

**Test Count**: 43 Python tests

### 2. Mod Detector (`detect_mods_*`)

**Rust Tests**: `classic-rust/tests/test_mod_detector.rs`
**Python Tests**: `tests/rust_integration/test_mod_detector_parity.py`

Coverage:
- ✅ Single mod detection with pattern matching
- ✅ Mod conflict detection (double mods)
- ✅ Important mod detection with GPU compatibility
- ✅ Batch processing capabilities
- ✅ Case sensitivity and pattern matching
- ✅ Edge cases and error handling

**Test Count**: 25 Python tests

### 3. Record Scanner (`RecordScanner`)

**Rust Tests**: `classic-rust/tests/test_record_scanner.rs`
**Python Tests**: `tests/rust_integration/test_record_scanner_parity.py`

Coverage:
- ✅ Basic record scanning and extraction
- ✅ Record validation and filtering
- ✅ Aho-Corasick multi-pattern matching
- ✅ Batch processing with parallel operations
- ✅ RSP marker detection and offset extraction
- ✅ Edge cases and error handling
- ✅ Performance tests (40x speedup target)

**Test Count**: 30 Python tests

### 4. YAML Operations (`RustYamlOperations`)

**Rust Tests**: `classic-rust/tests/test_yaml.rs`
**Python Tests**: `tests/rust_integration/test_yaml_parity.py`

Coverage:
- ✅ Basic YAML parsing and dumping
- ✅ Python type conversions (null, bool, number, string, list, dict)
- ✅ File operations with caching
- ✅ Settings navigation (get/set with dot notation)
- ✅ Cache management
- ✅ Error handling

**Test Count**: 28 Python tests

## Total Coverage

- **Total Rust Test Files**: 11 files
- **Total Python Integration Test Files**: 15+ files
- **New Parity Test Files**: 4 files
- **New Python Tests Added**: 126 tests

## Running the Tests

### Run All Rust-Python Parity Tests
```bash
pytest tests/rust_integration/ -v -m rust
```

### Run Specific Parity Tests
```bash
# Pattern Matcher
pytest tests/rust_integration/test_pattern_matcher_parity.py -v

# Mod Detector
pytest tests/rust_integration/test_mod_detector_parity.py -v

# Record Scanner
pytest tests/rust_integration/test_record_scanner_parity.py -v

# YAML Operations
pytest tests/rust_integration/test_yaml_parity.py -v
```

### Run Performance Tests
```bash
pytest tests/rust_integration/ -v -m "rust and slow"
```

## Test Markers

All parity tests use the following pytest markers:

- `@pytest.mark.rust` - Identifies Rust integration tests
- `@pytest.mark.slow` - Marks performance/benchmark tests
- `@pytest.mark.skipif(not RUST_AVAILABLE, ...)` - Skips when Rust unavailable

## Building Rust for Testing

Before running the tests, ensure the Rust extension is built:

```bash
# Method 1: Build wheel (RECOMMENDED)
cd classic-rust
maturin build --release --out dist
uv pip install dist/classic-*.whl --force-reinstall

# Method 2: Editable install (DEVELOPMENT)
rm .venv/Lib/site-packages/classic_core.pyd  # Remove old FIRST
uv pip install -e . --force-reinstall

# Verify Rust acceleration is working
python -c "from ClassicLib.integration.status import print_rust_status; print_rust_status()"
```

## Test Structure

Each parity test file follows this structure:

1. **Imports and Availability Check**
   - Try importing Rust components
   - Set `RUST_AVAILABLE` flag
   - All tests skip if Rust unavailable

2. **Test Data Helpers**
   - Factory functions for test data
   - Match Rust test data structures

3. **Test Classes**
   - Organized by functionality
   - Mirror Rust test organization
   - Comprehensive edge case coverage

4. **Performance Tests**
   - Marked with `@pytest.mark.slow`
   - Verify speedup targets (10-150x)
   - Measure cache effectiveness

## Maintaining Parity

When adding new Rust functionality:

1. ✅ Write Rust unit tests in `classic-rust/tests/`
2. ✅ Write corresponding Python integration tests
3. ✅ Ensure both test suites pass
4. ✅ Update this document

When modifying existing Rust code:

1. ✅ Update Rust unit tests
2. ✅ Update Python integration tests
3. ✅ Verify parity still maintained
4. ✅ Check performance hasn't regressed

## Known Issues

None currently. All tests pass when Rust components are available.

## Future Enhancements

Potential areas for additional test coverage:

- [ ] Fuzz testing for edge cases
- [ ] More comprehensive property-based tests
- [ ] Cross-platform behavior verification
- [ ] Memory leak detection tests
- [ ] Thread safety stress tests

## References

- [Rust Documentation Index](RUST_DOCUMENTATION_INDEX.md)
- [Rust Usage Guide](rust_usage_guide.md)
- [Performance Monitoring](performance_monitoring.md)
- [Troubleshooting Guide](troubleshooting_rust.md)
