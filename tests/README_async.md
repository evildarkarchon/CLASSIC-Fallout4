# Async Pipeline Integration Tests

This document describes the async pipeline integration tests in `test_async_pipeline.py` and how to work with them.

## Overview

The async pipeline tests validate the concurrent crash log processing functionality introduced in CLASSIC-Fallout4. These tests ensure that async components work correctly and provide performance improvements over synchronous operations.

## Test Categories

### 1. AsyncCrashLogPipeline Tests
Tests the main async pipeline orchestration:
- Pipeline initialization with configuration
- Full end-to-end async processing workflow
- Performance monitoring and metrics collection

### 2. OrchestratorCore Tests
Tests the async scan orchestrator component:
- Async context manager lifecycle
- Batch processing of multiple crash logs
- Integration with database pool

### 3. FormIDAnalyzerCore Tests
Tests async FormID analysis functionality:
- FormID extraction from crash log segments
- Concurrent database lookups
- Report generation with async database queries

### 4. AsyncFileIO Tests
Tests async file I/O operations:
- Concurrent crash log loading
- Batch report writing
- Sync/async wrapper functions

### 5. AsyncDatabasePool Tests
Tests async database connection management:
- Connection pool initialization
- Context manager lifecycle
- Concurrent database queries

### 6. AsyncUtilityFunctions Tests
Tests core async utility functions:
- Async file reading operations
- Error handling in async context

### 7. Performance Comparison Tests
Tests performance characteristics:
- Async vs sync execution time comparisons
- Performance regression detection

## Running Async Tests

### Prerequisites
```bash
pip install pytest-asyncio
```

### Run All Async Tests
```bash
python -m pytest tests/test_async_pipeline.py -v
```

### Run Specific Test Categories
```bash
# Run only FormIDAnalyzerCore tests
python -m pytest tests/test_async_pipeline.py::TestFormIDAnalyzerCore -v

# Run only performance tests
python -m pytest tests/test_async_pipeline.py::TestAsyncPerformanceComparison -v
```

### Run with Performance Output
```bash
python -m pytest tests/test_async_pipeline.py -v -s --tb=short
```

## Test Fixtures

### `crash_log_files`
Creates temporary crash log files for testing:
```python
def test_example(self, crash_log_files: list[Path]) -> None:
    # crash_log_files contains 3 sample crash log files
    assert len(crash_log_files) == 3
```

### `mock_yamldata`
Provides a comprehensive mock of `ClassicScanLogsInfo`:
```python
def test_example(self, mock_yamldata: MagicMock) -> None:
    # mock_yamldata has all required attributes pre-configured
    assert mock_yamldata.game_ignore_plugins is not None
```

### `sample_crash_log_content`
Contains realistic crash log content for testing:
```python
def test_example(self, sample_crash_log_content: str) -> None:
    # Contains Fallout 4 crash log with FormIDs, plugins, etc.
    assert "Form ID:" in sample_crash_log_content
```

## Writing New Async Tests

### Basic Async Test Structure
```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestMyAsyncComponent:
    """Tests for MyAsyncComponent."""

    async def test_async_functionality(self, crash_log_files: list[Path]) -> None:
        """Test async functionality."""
        # Your async test code here
        result = await my_async_function(crash_log_files)
        assert result is not None
```

### Performance Test Pattern
```python
def test_performance_comparison(self, crash_log_files: list[Path]) -> None:
    """Compare async vs sync performance."""
    # Sync timing
    sync_start = time.perf_counter()
    sync_result = sync_function(crash_log_files)
    sync_time = time.perf_counter() - sync_start

    # Async timing
    async def async_test():
        async_start = time.perf_counter()
        async_result = await async_function(crash_log_files)
        return time.perf_counter() - async_start, async_result

    async_time, async_result = asyncio.run(async_test())

    # Verify both produce same results
    assert len(sync_result) == len(async_result)

    # Both should complete successfully
    assert sync_time > 0 and async_time > 0
```

### Mocking Async Dependencies
```python
async def test_with_async_mocks(self) -> None:
    """Test with async mocks."""
    with patch("module.async_function") as mock_async:
        # Create async mock
        mock_async.return_value = AsyncMock()

        # Test your code
        result = await my_function()

        # Verify async call was made
        mock_async.assert_called_once()
```

## Common Issues and Solutions

### Issue: `RuntimeError: asyncio.run() cannot be called from a running event loop`
**Solution**: Don't use `asyncio.run()` inside async test functions. Use `await` instead.

```python
# Wrong
async def test_wrong():
    result = asyncio.run(my_async_function())

# Correct
async def test_correct():
    result = await my_async_function()
```

### Issue: `AsyncMock can't be used in 'await' expression`
**Solution**: Create proper async mock functions:

```python
# Wrong
mock_connect.return_value = AsyncMock()

# Correct
async def mock_connect(path):
    return AsyncMock()

with patch("aiosqlite.connect", side_effect=mock_connect):
    # Your test code
```

### Issue: Mock object missing attributes
**Solution**: Add all required attributes to the mock fixture:

```python
@pytest.fixture
def mock_yamldata() -> MagicMock:
    yamldata = MagicMock(spec=ClassicScanLogsInfo)
    yamldata.required_attribute = "value"
    yamldata.another_attribute = ["list", "of", "values"]
    return yamldata
```

## Debugging Async Tests

### Enable Async Debug Mode
```python
import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())  # Windows
# or
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())  # Unix
```

### Use Async Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

async def test_with_logging():
    logger = logging.getLogger(__name__)
    logger.debug("Starting async test")
    result = await my_async_function()
    logger.debug(f"Got result: {result}")
```

### Check for Unawaited Coroutines
```bash
python -Xdev -m pytest tests/test_async_pipeline.py -v
```

## Performance Considerations

- Async tests may be slower than sync tests due to event loop overhead
- Use `@pytest.mark.slow` for tests that take >1 second
- Consider using `pytest-benchmark` for detailed performance testing
- Mock external I/O operations to focus on async logic testing

## Contributing

When adding new async components to CLASSIC:

1. **Add corresponding tests** in `test_async_pipeline.py`
2. **Use the established patterns** from existing tests
3. **Include performance comparisons** where applicable
4. **Mock external dependencies** to isolate async logic
5. **Update this README** with new test categories

## Future Enhancements

Planned improvements for the async test suite:

- [ ] Integration with actual crash log database
- [ ] Load testing with large numbers of crash logs
- [ ] Benchmark suite for performance regression testing
- [ ] CI/CD integration with performance thresholds
- [ ] Memory usage profiling for async operations
