# CLASSIC-Fallout4 Test Suite

This directory contains a comprehensive test suite for the CLASSIC-Fallout4 crash log scanner.

## Test Coverage

The tests are organized into several modules, each focusing on specific aspects of the codebase:

1. `test_scan_logs.py` - Tests for the core functionality in CLASSIC_ScanLogs.py
   - ClassicScanLogs class initialization and configuration
   - Segment extraction from crash logs
   - Plugin detection and loadorder scanning
   - Suspect scanning in crash logs

2. `test_detect_mods.py` - Tests for the DetectMods module
   - String case conversion helpers
   - Warning validation
   - Single mod detection
   - Mod conflict detection
   - Important mod detection with GPU compatibility checks

3. `test_thread_safe_log_cache.py` - Thread safety tests for ThreadSafeLogCache
   - Concurrent log reads
   - Reentrant lock behavior
   - Edge cases like nonexistent logs and invalid UTF-8 characters

4. `test_yaml_integration.py` - Tests for YAML settings integration
   - Loading YAML settings
   - Settings integration with ClassicScanLogs
   - Local settings overrides
   - Settings updates

5. `test_crash_log_processing.py` - Integration tests for end-to-end crash log processing
   - Process individual crash logs
   - End-to-end scanning with multiple logs

6. `test_formid_matching.py` - Tests for FormID matching functionality
   - Basic FormID matching
   - FormID matching with plugin prefixes
   - Multiple FormID lookups

## Running Tests

To run the full test suite:

```bash
pytest
```

To run a specific test module:

```bash
pytest tests/test_scan_logs.py
```

To run tests with a specific marker:

```bash
pytest -m unit
pytest -m integration
pytest -m thread
```

## Test Categories

Tests are categorized using pytest markers:

- `unit`: Unit tests that focus on testing individual functions or classes
- `integration`: Tests that focus on the integration of multiple components
- `thread`: Tests that focus on thread safety and concurrency
- `slow`: Tests that take a long time to run

## Configuration

The testing environment is configured through:

- `conftest.py`: Contains shared fixtures and setup code
- `pytest.ini`: Contains pytest configuration settings

## Sample Data

Tests use either:
- Mock data created within the tests
- Sample crash logs in fixtures
- Temporary files created during test execution

## Adding New Tests

When adding new tests:

1. Choose the appropriate module or create a new one if needed
2. Use the appropriate marker for the test type
3. Use fixtures from conftest.py where applicable
4. Add docstrings to explain the purpose of the test

## Testing Best Practices

- Mock external dependencies for unit tests
- Use fixtures for shared setup code
- Use appropriate assertions to verify expected behavior
- Clean up any temporary files or resources created during tests
