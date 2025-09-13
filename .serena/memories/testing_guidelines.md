# Testing Guidelines for CLASSIC-Fallout4

## Test-Driven Development (TDD) Methodology

### Red-Green-Refactor Cycle
1. **Red**: Write a failing test first
2. **Green**: Write minimal code to pass
3. **Refactor**: Improve code quality while keeping tests green

### Example TDD Flow
```python
# 1. RED - Write failing test
@pytest.mark.asyncio
async def test_new_feature():
    result = await new_feature()
    assert result == expected  # Fails

# 2. GREEN - Minimal implementation
async def new_feature():
    return expected  # Passes

# 3. REFACTOR - Improve implementation
async def new_feature():
    # Proper implementation with error handling
    try:
        return await process_data()
    except Exception as e:
        handle_error(e)
```

## Test Organization Rules

### File Structure Requirements
- **Maximum 300 lines per test file**
- **No tests in root tests/ directory**
- **Descriptive naming**: `test_<component>_<aspect>.py`
- **Appropriate subdirectory placement**

### Test Markers
```python
@pytest.mark.unit           # Fast, isolated tests
@pytest.mark.integration    # Component interaction tests
@pytest.mark.slow          # Tests taking >5 seconds
@pytest.mark.asyncio       # Async tests
@pytest.mark.performance   # Performance benchmarks
@pytest.mark.gui           # GUI-dependent tests
@pytest.mark.thread        # Thread safety tests
@pytest.mark.regression    # Regression tests
```

## Critical Test Isolation Rules

### Production Data is READ-ONLY
```python
# ❌ NEVER DO THIS
def test_bad():
    yaml_settings(str, YAML.Settings, "key", "test_value")
    # Modifies production settings!

# ✅ CORRECT APPROACH
def test_good(tmp_path):
    test_file = tmp_path / "test_settings.yaml"
    # Work with test file

# ✅ OR USE TEST ENUM
def test_with_enum():
    yaml_settings(str, YAML.TEST, "key", "test_value")
```

### Fixture Requirements
```python
@pytest.fixture
def init_message_handler_fixture():
    """Required for tests using MessageHandler."""
    handler = init_message_handler(parent=None, is_gui_mode=False)
    yield
    ClassicLib.MessageHandler._message_handler = None
```

## Testing Async Code

### Async Test Pattern
```python
@pytest.mark.asyncio
async def test_async_operation():
    # Setup
    core = AsyncComponentCore()

    # Execute
    result = await core.process_async()

    # Assert
    assert result.status == "success"
```

### Concurrent Testing
```python
@pytest.mark.asyncio
async def test_concurrent_operations(tmp_path):
    files = [tmp_path / f"test_{i}.log" for i in range(10)]

    # Test concurrent processing
    results = await asyncio.gather(*[
        process_file(f) for f in files
    ])

    assert all(r.success for r in results)
```

## Mock Patterns

### Mock Where Used, Not Defined
```python
# ❌ WRONG - Mocking at definition
@patch('ClassicLib.Util.some_function')

# ✅ CORRECT - Mocking where used
@patch('ClassicLib.Scanner.some_function')  # Scanner uses the function
```

### Mock External Dependencies
```python
@patch('requests.get')
def test_with_network_mock(mock_get):
    mock_get.return_value.json.return_value = {"data": "test"}
    result = fetch_data()
    assert result == {"data": "test"}
```

## Performance Testing

### Performance Test Structure
```python
@pytest.mark.performance
def test_performance_baseline():
    start = time.perf_counter()

    # Operation to benchmark
    result = perform_operation()

    elapsed = time.perf_counter() - start

    # Verify correctness
    assert result is not None

    # Verify performance
    assert elapsed < 1.0, f"Too slow: {elapsed:.3f}s"
```

## Test Execution Commands

### Quick Testing
```bash
# Fast unit tests only
poetry run python -m pytest -n 4 -m "unit and not slow"

# Specific component
poetry run python -m pytest tests/core/ -n 4
```

### Comprehensive Testing
```bash
# Full test suite
poetry run python -m pytest tests/ -n 4 -v

# With coverage
poetry run python -m pytest --cov=. --cov-report=html
```

### Parallel Execution
```bash
# Auto-detect cores
poetry run python -m pytest -n auto

# Specific worker count
poetry run python -m pytest -n 4
```

## Common Testing Patterns

### Arrange-Act-Assert
```python
def test_example():
    # Arrange - Setup
    input_data = prepare_test_data()
    expected = "expected result"

    # Act - Execute
    actual = function_under_test(input_data)

    # Assert - Verify
    assert actual == expected
```

### Exception Testing
```python
def test_error_handling():
    with pytest.raises(ValueError, match="Invalid input"):
        function_with_validation("")
```

### Parametrized Tests
```python
@pytest.mark.parametrize("input,expected", [
    ("valid", True),
    ("", False),
    (None, False),
])
def test_validation(input, expected):
    assert validate(input) == expected
```

## Test Quality Checklist

Before committing tests:
- [ ] Tests follow naming conventions
- [ ] Appropriate markers applied
- [ ] No production data modification
- [ ] External dependencies mocked
- [ ] File under 300 lines
- [ ] In correct subdirectory
- [ ] MessageHandler initialized if needed
- [ ] tmp_path used for test files
- [ ] Tests are isolated and repeatable
- [ ] Coverage requirements met (90%+)

## Debugging Tests

```bash
# Verbose output
poetry run python -m pytest -v

# Show print statements
poetry run python -m pytest -s

# Drop into debugger on failure
poetry run python -m pytest --pdb

# Run specific test
poetry run python -m pytest -k "test_name"
```

## Important Notes
- Always run tests in terminal (VS Code test tool freezes)
- Use parallel execution (-n 4 or -n auto)
- Write tests BEFORE implementation (TDD)
- Keep tests simple and focused
- Mock external dependencies
- Never modify production configuration
