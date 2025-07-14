# Testing Guidelines for CLASSIC-Fallout4

## Running Tests

Due to VS Code test tool freezing issues, use the terminal for running tests:

### Basic Test Commands

```powershell
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_crash_log_processing.py -v

# Run tests matching a pattern
python -m pytest tests/ -k "async" -v

# Run tests with coverage
python -m pytest tests/ --cov=ClassicLib --cov-report=html

# Run specific test class
python -m pytest tests/test_async_pipeline.py::TestAsyncPipeline -v
```

### Performance Testing
```powershell
# Run performance baselines
python -m pytest tests/ -k "baseline" -v

# Run memory usage tests
python -m pytest tests/ -k "memory" -v
```

### Integration Testing
```powershell
# Run integration tests
python -m pytest tests/test_crash_log_processing.py::TestCrashLogProcessingIntegration -v
```

## Notes

- Always use `python -m pytest` instead of just `pytest` to ensure proper module resolution
- Use `-v` for verbose output to see individual test results
- The VS Code test tool has been freezing, so terminal testing is preferred
- Tests are configured in `pytest.ini` for proper async handling
