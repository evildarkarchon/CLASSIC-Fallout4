# Testing Guide: AsyncBridge and Async Code Mocking

## Overview

AsyncBridge is a singleton pattern that manages async operations in synchronous contexts throughout the CLASSIC codebase. When testing code that uses AsyncBridge, it's crucial to mock it correctly to avoid `RuntimeWarning: coroutine was never awaited` errors.

## Common Testing Pitfalls

### ❌ INCORRECT: Using AsyncMock for wrapped async methods

```python
# This will cause RuntimeWarning!
from unittest.mock import AsyncMock, patch

def test_bad_example():
    with patch("module.SomeClass") as mock_class:
        mock_instance = mock_class.return_value
        # WRONG: AsyncMock for a method called through AsyncBridge
        mock_instance.async_method = AsyncMock(return_value="result")

        # When the sync wrapper calls bridge.run_async(async_method())
        # the AsyncMock coroutine won't be properly awaited
        result = sync_wrapper_function()
```

### ❌ INCORRECT: Creating and calling AsyncMock

```python
# This will cause RuntimeWarning!
from unittest.mock import AsyncMock

def test_another_bad_example():
    with patch.object(MyClass, "async_method") as mock_method:
        # WRONG: Trying to call AsyncMock as a regular function
        mock_method.return_value = AsyncMock()()  # Double call creates unawaited coroutine

        MyClass.sync_wrapper()
```

## Correct Testing Patterns

### ✅ CORRECT: Mock AsyncBridge.run_async directly

```python
from unittest.mock import MagicMock, patch

def test_sync_wrapper_with_async_bridge():
    """Test a sync function that uses AsyncBridge to call async code."""

    # Mock the AsyncBridge singleton
    with patch("module.AsyncBridge") as mock_bridge_class:
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge

        # Mock what run_async returns (NOT the async function itself)
        mock_bridge.run_async.return_value = "expected_result"

        # Test the sync wrapper
        result = sync_wrapper_function()

        assert result == "expected_result"
        mock_bridge.run_async.assert_called_once()
```

### ✅ CORRECT: Testing multiple async operations

```python
def test_multiple_async_operations():
    """Test sync wrappers that call multiple async methods."""

    with patch("CLASSIC_ScanGame.get_scan_game_core") as mock_get_core, \
         patch("CLASSIC_ScanGame.AsyncBridge") as mock_bridge_class:

        # Setup bridge mock
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge

        # Setup core mock (use regular MagicMock, NOT AsyncMock)
        mock_core = mock_get_core.return_value

        # Mock the return value of bridge.run_async
        mock_bridge.run_async.return_value = "scan_result"

        # Call the sync adapter
        import CLASSIC_ScanGame
        result = CLASSIC_ScanGame.scan_mods_archived()

        assert result == "scan_result"
```

### ✅ CORRECT: Testing async functions directly (without bridge)

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_pure_async_function():
    """When testing async functions directly, use AsyncMock normally."""

    with patch("module.async_dependency") as mock_dep:
        # This is fine for pure async testing
        mock_dep.some_method = AsyncMock(return_value="async_result")

        # Call the async function directly
        result = await my_async_function()

        assert result == "expected"
```

## Real-World Examples from CLASSIC

### Example 1: Testing FileGenerator with AsyncBridge

```python
@patch("ClassicLib.AsyncBridge.AsyncBridge.get_instance")
@patch.object(FileGenerator, "generate_all_files_async")
def test_generate_all_files(self, mock_generate_async, mock_bridge_get_instance):
    """Test that generate_all_files calls the async implementation."""
    from unittest.mock import AsyncMock

    # Create async mock but don't call it
    async_mock = AsyncMock()
    mock_generate_async.return_value = async_mock

    # Mock the bridge to handle the async call
    mock_bridge = MagicMock()
    mock_bridge_get_instance.return_value = mock_bridge
    mock_bridge.run_async.return_value = None  # Simulate successful completion

    FileGenerator.generate_all_files()

    # Verify the async method was called
    mock_generate_async.assert_called_once()
    mock_bridge.run_async.assert_called_once()
```

### Example 2: Testing ScanGame wrappers

```python
def test_scan_mods_archived_wrapper():
    """Test synchronous wrapper for scan_mods_archived."""

    with patch("CLASSIC_ScanGame.get_scan_game_core") as mock_get_core, \
         patch("CLASSIC_ScanGame.AsyncBridge") as mock_bridge_class:

        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge

        # Create a regular mock for the core (NOT AsyncMock)
        mock_core = mock_get_core.return_value

        # Mock what run_async returns
        mock_bridge.run_async.return_value = "Test result"

        import CLASSIC_ScanGame
        result = CLASSIC_ScanGame.scan_mods_archived()

        assert result == "Test result"
```

## Quick Reference: When to Use What

| Scenario | Mock Type | Example |
|----------|-----------|---------|
| Sync wrapper using AsyncBridge | MagicMock + mock bridge.run_async | `mock_bridge.run_async.return_value = "result"` |
| Direct async function test | AsyncMock | `@pytest.mark.asyncio` + `await function()` |
| Async method called via bridge | MagicMock (NOT AsyncMock) | `mock_core.async_method = MagicMock()` |
| Testing async context managers | Use real async operations or simplify | Don't mock `aiofiles.open`, use real temp files |

## Debugging Tips

1. **See RuntimeWarning about unawaited coroutine?**
   - Check if you're using AsyncMock where code goes through AsyncBridge
   - Look for `AsyncMock()()` double-call pattern
   - Verify you're mocking the bridge's run_async method

2. **Test passes but with warnings?**
   - The test might be working "by accident"
   - AsyncMock might be returning another AsyncMock instead of a value
   - Fix the mocking pattern even if test passes

3. **Complex async context managers?**
   - Consider using real operations with temp files
   - Or simplify the test to focus on the logic, not the I/O

## Key Principles

1. **AsyncBridge converts async → sync**: Mock the bridge's return value, not the async function
2. **Use MagicMock for bridge-wrapped methods**: The bridge handles the async part
3. **Use AsyncMock only for direct async testing**: When you're actually awaiting in the test
4. **Mock at the right level**: Mock AsyncBridge.run_async, not the underlying async methods
5. **Simplify when possible**: Sometimes it's better to test with real async operations than complex mocks

## Related Documentation

- [AsyncBridge Implementation](../ClassicLib/AsyncBridge.py)
- [Test Examples](../tests/scanning/test_scan_game_wrappers.py)
- [CLAUDE.md Testing Section](../CLAUDE.md#testing-patterns)
