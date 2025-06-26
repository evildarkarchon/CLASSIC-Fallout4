# CLASSIC-Fallout4 Testing Standards and Guidelines

## 🎯 Overview

This document establishes the testing standards, guidelines, and best practices for the CLASSIC-Fallout4 project. Following these standards ensures consistent, maintainable, and reliable tests across the codebase.

## 📋 Testing Philosophy

### Core Principles
1. **Test-Driven Development**: Write tests alongside or before implementation
2. **Comprehensive Coverage**: Aim for 90%+ line coverage with meaningful tests
3. **Maintainability**: Write clear, readable tests that serve as documentation
4. **Performance Awareness**: Tests should be fast by default, with slow tests marked appropriately
5. **Platform Independence**: Tests should work across Windows and Linux where applicable

### Test Categories
- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test component interactions and workflows
- **End-to-End Tests**: Test complete user workflows
- **Performance Tests**: Validate performance characteristics and prevent regressions
- **Error Handling Tests**: Verify proper error handling and edge cases

## 🏗️ Test Structure and Organization

### Directory Structure
```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── test_data/                  # Mock data and sample files
│   ├── sample_crash_logs/      # Sample crash log files
│   ├── mock_registry/          # Mock registry data
│   └── sample_yaml/            # Sample YAML configurations
├── test_*.py                   # Individual test modules
└── TESTING_STANDARDS.md       # This document
```

### File Naming Conventions
- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<functionality>_<scenario>`
- Test data files: Descriptive names with proper extensions

### Test Class Organization
```python
class TestClassName:
    """Test class for ClassName functionality."""
    
    def test_basic_functionality(self):
        """Test basic functionality works as expected."""
        pass
    
    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        pass
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        pass
```

## 🧪 Test Implementation Standards

### Test Method Structure
Each test should follow the **Arrange-Act-Assert** pattern:

```python
def test_example_functionality(self):
    """Test that example functionality works correctly."""
    # Arrange: Set up test data and conditions
    input_data = "test input"
    expected_result = "expected output"
    
    # Act: Execute the functionality being tested
    actual_result = function_under_test(input_data)
    
    # Assert: Verify the results
    assert actual_result == expected_result
```

### Assertions and Validation
- Use descriptive assertion messages: `assert result == expected, f"Expected {expected}, got {result}"`
- Test both positive and negative cases
- Validate types, values, and behavior
- Use `pytest.raises()` for exception testing

### Mock Usage Guidelines
- Mock external dependencies (network, file system, registry)
- Mock where functions are **used**, not where they're **defined**
- Use descriptive mock names and return values
- Verify mock calls when behavior verification is important

```python
@patch('module.where.function.is.used')
def test_with_mock(self, mock_function):
    """Test using proper mock placement."""
    mock_function.return_value = "expected value"
    # Test code here
    mock_function.assert_called_once()
```

## 🏷️ Test Markers and Categories

### Available Markers
- `@pytest.mark.unit`: Unit tests (fast, isolated)
- `@pytest.mark.integration`: Integration tests (moderate speed)
- `@pytest.mark.slow`: Tests that take >5 seconds
- `@pytest.mark.thread`: Thread safety and concurrency tests
- `@pytest.mark.asyncio`: Asynchronous tests
- `@pytest.mark.performance`: Performance and benchmark tests
- `@pytest.mark.ui`: User interface tests
- `@pytest.mark.network`: Tests requiring network connectivity
- `@pytest.mark.error_handling`: Error handling tests
- `@pytest.mark.cross_platform`: Cross-platform compatibility tests
- `@pytest.mark.e2e`: End-to-end integration tests
- `@pytest.mark.regression`: Regression tests for previously fixed bugs

### Marker Usage
```python
@pytest.mark.unit
def test_fast_unit_test():
    """Quick unit test that runs in isolation."""
    pass

@pytest.mark.slow
@pytest.mark.integration
def test_complex_integration():
    """Integration test that takes significant time."""
    pass
```

## 🔧 Fixtures and Test Data

### Fixture Guidelines
- Use descriptive fixture names
- Document fixture purposes and return values
- Prefer function-scoped fixtures unless session scope is needed
- Clean up resources in fixture teardown

### Using Shared Fixtures
The project provides several shared fixtures in `conftest.py`:

- `init_message_handler_fixture`: Initializes MessageHandler for tests
- `temp_game_installation`: Creates temporary game directory structure
- `mock_registry_entries`: Mocks Windows registry entries
- `sample_ini_files`: Creates sample INI files
- `mock_network_responses`: Mocks network requests
- `sample_crash_logs_dir`: Creates sample crash log files

### Test Data Management
- Store static test data in `tests/test_data/`
- Use fixtures for dynamic test data generation
- Keep test data minimal but representative
- Document complex test data structures

## 📊 Coverage Requirements

### Coverage Targets
- **Overall Project**: 90%+ line coverage
- **New Code**: 95%+ line coverage required
- **Critical Modules**: 95%+ line coverage required
- **UI Components**: 70%+ line coverage (GUI testing limitations accepted)

### Coverage Exclusions
The following are excluded from coverage requirements:
- Debug and logging statements
- Platform-specific code branches not testable in CI
- GUI event handlers that can't be easily tested
- Code marked with `# pragma: no cover`

### Running Coverage Reports
```bash
# Generate full coverage report
python -m pytest --cov=. --cov-report=html --cov-report=term

# Generate coverage for specific module
python -m pytest --cov=ClassicLib.Util tests/test_util.py --cov-report=term

# Check coverage threshold
python -m pytest --cov=. --cov-fail-under=85
```

## ⚡ Performance Testing Standards

### Performance Test Guidelines
- Mark performance tests with `@pytest.mark.performance`
- Include baseline measurements for regression detection
- Test with realistic data sizes
- Measure relevant metrics (time, memory, throughput)
- Set reasonable performance thresholds

### Performance Test Structure
```python
@pytest.mark.performance
def test_performance_baseline(self):
    """Test performance meets baseline requirements."""
    start_time = time.perf_counter()
    
    # Execute performance-critical code
    result = perform_operation()
    
    elapsed_time = time.perf_counter() - start_time
    
    # Verify correctness
    assert result is not None
    
    # Verify performance
    assert elapsed_time < 1.0, f"Operation took {elapsed_time:.3f}s, expected <1.0s"
```

## 🔍 Debugging and Troubleshooting

### Test Debugging
- Use `pytest -v` for verbose output
- Use `pytest -s` to see print statements
- Use `pytest --pdb` to drop into debugger on failures
- Use `pytest -k "test_name"` to run specific tests

### Common Issues and Solutions

#### Import Errors
- Ensure all required dependencies are installed
- Check `sys.path` modifications in test files
- Verify module structure and `__init__.py` files

#### Mock-Related Issues
- Ensure mocks target the correct import path
- Use `patch.object()` for class method mocking
- Reset mocks between tests if needed

#### Fixture Issues
- Check fixture scope and lifecycle
- Ensure proper cleanup in fixture teardown
- Verify fixture dependencies

## 🚀 Test Execution and CI/CD

### Local Test Execution
```bash
# Run all tests
python -m pytest

# Run specific test markers
python -m pytest -m "unit"
python -m pytest -m "not slow"

# Run with coverage
python -m pytest --cov=. --cov-report=html

# Run in parallel (if pytest-xdist installed)
python -m pytest -n auto
```

### Pre-commit Checklist
Before committing changes:
- [ ] All existing tests pass
- [ ] New functionality has corresponding tests
- [ ] Coverage requirements are met
- [ ] Tests follow naming conventions
- [ ] Appropriate markers are applied
- [ ] Test documentation is clear

### Test Quality Metrics
Monitor these metrics to ensure test suite health:
- **Pass Rate**: Should be 100%
- **Coverage**: 90%+ overall, 95%+ for new code
- **Execution Time**: <2 minutes for full suite
- **Flakiness**: <1% test failure rate due to intermittent issues

## 📚 Resources and References

### Tools and Libraries
- **pytest**: Primary testing framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Enhanced mocking capabilities
- **pytest-asyncio**: Async test support
- **unittest.mock**: Standard library mocking

### Documentation Links
- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

### Project-Specific Resources
- [Test Implementation Checklist](TEST_IMPLEMENTATION_CHECKLIST.md)
- [Test Suite Update Summary](TEST_SUITE_UPDATE_SUMMARY.md)
- [Test Data Documentation](test_data/README.md)

---

## 📝 Conclusion

Following these testing standards ensures that the CLASSIC-Fallout4 project maintains high code quality, reliability, and maintainability. Regular review and updates of these standards help the project adapt to new requirements and best practices.

For questions or suggestions regarding these standards, please refer to the project maintainers or open an issue for discussion. 