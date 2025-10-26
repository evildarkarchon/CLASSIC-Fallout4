# Async Test Patterns Guide for CLASSIC

## Overview

This guide provides comprehensive patterns for testing async code in the CLASSIC project. Following these patterns ensures tests run correctly without `RuntimeWarning: coroutine was never awaited` errors and maintain proper isolation for parallel execution with `pytest-xdist`.

## Table of Contents

1. [Core Principles](#core-principles)
2. [AsyncBridge Testing Patterns](#asyncbridge-testing-patterns)
3. [Pure Async Function Testing](#pure-async-function-testing)
4. [Common Anti-Patterns](#common-anti-patterns)
5. [Test File Organization](#test-file-organization)
6. [Migration Guide](#migration-guide)

## Core Principles

### 1. Understand the Architecture

CLASSIC uses an **async-first architecture** with sync adapters for backward compatibility:

- **Core implementations** are async (e.g., `OrchestratorCore`, `FileIOCore`)
- **AsyncBridge** manages async operations in sync contexts
- **Sync adapters** wrap async code using `AsyncBridge.run_async()`

### 2. Mock at the Right Level

- **For sync wrappers**: Mock `AsyncBridge.run_async()`, not the underlying async functions
- **For pure async tests**: Use real `async/await` with `@pytest.mark.asyncio`
- **Never use AsyncMock** for methods called through AsyncBridge

## AsyncBridge Testing Patterns

### Pattern 1: Testing Sync Wrappers

When testing synchronous functions that use AsyncBridge internally:

```python
def test_sync_wrapper_correct_pattern():
    """Test a sync function that uses AsyncBridge internally."""

    with patch("module.AsyncBridge") as mock_bridge_class:
        # Create mock bridge
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge

        # Mock what run_async returns (NOT a coroutine!)
        mock_bridge.run_async.return_value = "expected_result"

        # Test the sync wrapper
        result = sync_wrapper_function()

        assert result == "expected_result"
        mock_bridge.run_async.assert_called_once()
```

### Pattern 2: Testing Async Functions Directly

When testing async functions without sync wrappers:

```python
@pytest.mark.asyncio
async def test_pure_async_function():
    """Test an async function directly."""

    # For pure async testing, use real async/await
    result = await async_function(param1, param2)

    assert result == expected_value
```

### Pattern 3: Mocking Async Dependencies in Async Tests

When async functions have async dependencies:

```python
@pytest.mark.asyncio
async def test_async_with_mocked_dependencies():
    """Test async function with mocked async dependencies."""

    with patch("module.async_dependency") as mock_dep:
        # Create a coroutine that returns the mocked value
        async def mock_coro():
            return "mocked_result"

        mock_dep.return_value = mock_coro()

        # Test the async function
        result = await function_under_test()

        assert result == expected_value
```

### Pattern 4: Testing Hybrid Components

For components that support both sync and async usage:

```python
class TestHybridComponent:
    """Test component with both sync and async interfaces."""

    def test_sync_interface(self):
        """Test synchronous interface."""
        with patch("module.AsyncBridge") as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            mock_bridge.run_async.return_value = "sync_result"

            component = HybridComponent()
            result = component.sync_method()

            assert result == "sync_result"

    @pytest.mark.asyncio
    async def test_async_interface(self):
        """Test asynchronous interface."""
        component = HybridComponent()
        result = await component.async_method()

        assert result == expected_value
```

## Pure Async Function Testing

### Testing Async Context Managers

```python
@pytest.mark.asyncio
async def test_async_context_manager():
    """Test async context manager correctly."""

    # Mock the context manager protocol
    mock_cm = MagicMock()

    async def async_enter():
        return mock_cm

    async def async_exit(*args):
        return None

    mock_cm.__aenter__ = MagicMock(return_value=async_enter())
    mock_cm.__aexit__ = MagicMock(return_value=async_exit())

    async with mock_cm as cm:
        assert cm is mock_cm
```

### Testing Concurrent Operations

```python
@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test multiple async operations running concurrently."""

    async def operation1():
        await asyncio.sleep(0.01)
        return "result1"

    async def operation2():
        await asyncio.sleep(0.01)
        return "result2"

    # Run operations concurrently
    results = await asyncio.gather(operation1(), operation2())

    assert results == ["result1", "result2"]
```

## Common Anti-Patterns

### ❌ WRONG: Using AsyncMock for Bridge-Called Methods

```python
# This causes RuntimeWarning!
def test_bad_pattern():
    with patch("module.SomeClass") as mock_class:
        mock_instance = mock_class.return_value
        # WRONG: AsyncMock for method called through AsyncBridge
        mock_instance.async_method = AsyncMock(return_value="result")

        # When sync wrapper calls bridge.run_async(async_method())
        # the AsyncMock coroutine won't be properly awaited
        result = sync_wrapper()  # RuntimeWarning here!
```

### ❌ WRONG: Double-Calling AsyncMock

```python
# This creates an unawaited coroutine!
def test_another_bad_pattern():
    with patch.object(MyClass, "async_method") as mock_method:
        # WRONG: Double call creates unawaited coroutine
        mock_method.return_value = AsyncMock()()

        MyClass.sync_wrapper()  # RuntimeWarning here!
```

### ❌ WRONG: Mixing Async and Sync Without Bridge

```python
def test_mixing_without_bridge():
    # WRONG: Calling async function without await or bridge
    result = async_function()  # This returns a coroutine object!

    # result is a coroutine, not the actual value
    assert result == expected  # This will fail
```

## Test File Organization

### File Structure

```
tests/
├── async_tests/           # Pure async tests
│   ├── conftest.py       # Shared async fixtures
│   ├── test_*_unit.py    # Unit tests for async components
│   └── test_*_integration.py  # Integration tests
├── sync_tests/           # Tests for sync wrappers
│   └── test_*_wrappers.py  # AsyncBridge wrapper tests
└── fixtures/
    └── async_fixtures.py  # Reusable async test fixtures
```

### Test Markers

Always use appropriate markers:

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_unit():
    """Unit test for async function."""
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_integration():
    """Integration test for async components."""
    pass

@pytest.mark.unit
def test_sync_wrapper():
    """Unit test for sync wrapper using AsyncBridge."""
    pass
```

## Migration Guide

### Step 1: Identify Problematic Tests

Look for these warning signs:
- `RuntimeWarning: coroutine was never awaited`
- Tests using `AsyncMock` for bridge-called methods
- Tests importing from deprecated `AsyncCore` module

### Step 2: Categorize Tests

Determine if each test is:
1. Testing a pure async function → Use `@pytest.mark.asyncio`
2. Testing a sync wrapper → Mock `AsyncBridge.run_async()`
3. Testing both interfaces → Split into separate test methods

### Step 3: Apply Correct Pattern

#### For Sync Wrapper Tests:

Before:
```python
def test_old_pattern():
    with patch("module.async_func") as mock_func:
        mock_func.return_value = AsyncMock(return_value="result")
        result = sync_wrapper()  # RuntimeWarning!
```

After:
```python
def test_new_pattern():
    with patch("module.AsyncBridge") as mock_bridge_class:
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge
        mock_bridge.run_async.return_value = "result"

        result = sync_wrapper()  # No warning!
```

#### For Pure Async Tests:

Before:
```python
def test_old_async():
    # Incorrectly testing async as sync
    result = async_function()  # Returns coroutine!
```

After:
```python
@pytest.mark.asyncio
async def test_new_async():
    # Correctly using async/await
    result = await async_function()
```

### Step 4: Update Imports

Remove deprecated imports:
```python
# Remove these:
from ClassicLib.AsyncCore import SyncAdapter
from ClassicLib.AsyncCore import create_sync_adapter

# Use these instead:
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.AsyncBridge import run_async
```

### Step 5: Verify Tests

Run tests with verbose output to check for warnings:
```bash
# Run specific test file
uv run pytest tests/async_tests/test_file.py -xvs

# Run all async tests
uv run pytest tests/async_tests/ -xvs

# Run with parallel execution
uv run pytest tests/async_tests/ -n auto
```

## Best Practices

### 1. Document Mock Patterns

Always add comments explaining the mocking strategy:

```python
def test_with_clear_documentation():
    """Test sync wrapper with proper AsyncBridge mocking.

    This test mocks AsyncBridge.run_async() to return the expected value
    directly, avoiding the need to actually run async code. This is the
    correct pattern for testing sync wrappers that use AsyncBridge.
    """
    # Mock at the bridge level, not the async function level
    with patch("module.AsyncBridge") as mock_bridge_class:
        # ... test implementation
```

### 2. Use Fixtures for Common Patterns

Create reusable fixtures for common mock patterns:

```python
@pytest.fixture
def mock_async_bridge():
    """Provide a mocked AsyncBridge for sync wrapper tests."""
    with patch("ClassicLib.AsyncBridge.AsyncBridge") as mock_class:
        mock_bridge = MagicMock()
        mock_class.get_instance.return_value = mock_bridge
        yield mock_bridge
```

### 3. Test Both Success and Error Cases

Always test exception propagation:

```python
def test_error_propagation(mock_async_bridge):
    """Test that exceptions propagate through AsyncBridge."""
    mock_async_bridge.run_async.side_effect = ValueError("Async error")

    with pytest.raises(ValueError, match="Async error"):
        sync_wrapper()
```

### 4. Avoid Mixing Patterns in One Test

Keep sync and async testing separate:

```python
# Good: Separate test methods
class TestComponent:
    def test_sync_interface(self):
        """Test synchronous interface."""
        # Mock AsyncBridge

    @pytest.mark.asyncio
    async def test_async_interface(self):
        """Test asynchronous interface."""
        # Use real async/await

# Bad: Mixing in one test
def test_mixed_bad():
    # Don't mix sync and async testing in one method
```

## Troubleshooting

### RuntimeWarning: coroutine was never awaited

**Cause**: Using `AsyncMock` for methods called through `AsyncBridge`

**Solution**: Mock `AsyncBridge.run_async()` instead:
```python
# Replace AsyncMock with MagicMock
mock_bridge.run_async.return_value = expected_value
```

### Tests hang or timeout

**Cause**: Event loop conflicts or deadlocks

**Solution**: Use proper fixtures that clean up:
```python
@pytest.fixture
def async_bridge():
    """Provide clean AsyncBridge with proper cleanup."""
    from ClassicLib.AsyncBridge import AsyncBridge
    bridge = AsyncBridge.get_instance()
    yield bridge
    bridge.shutdown()
```

### Inconsistent test results

**Cause**: Test pollution from shared state

**Solution**: Use test isolation fixtures:
```python
@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean state for each test."""
    # Clear any global state before test
    yield
    # Clean up after test
```

## Related Documentation

- [AsyncBridge Implementation](../ClassicLib/AsyncBridge.py)
- [Testing AsyncBridge Guide](async_bridge.md)
- [Test Pollution Prevention Guide](test_pollution_guide.md)
- [CLAUDE.md Testing Section](../CLAUDE.md#testing-patterns)

## Summary

The key to successful async testing in CLASSIC is understanding the distinction between:

1. **Pure async code** - Test with `@pytest.mark.asyncio` and real `async/await`
2. **Sync wrappers using AsyncBridge** - Mock `AsyncBridge.run_async()`
3. **Hybrid components** - Test each interface appropriately

By following these patterns, tests will:
- Run without coroutine warnings
- Execute efficiently in parallel with `pytest-xdist`
- Maintain proper isolation between tests
- Clearly document the testing approach
