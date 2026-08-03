# Testing Guide: GlobalRegistry and Singleton Patterns

## Overview

GlobalRegistry is a singleton pattern used throughout CLASSIC for managing global instances like ScanGameCore, MessageHandler, and other shared components. When testing code that uses GlobalRegistry, especially in parallel tests (pytest-xdist), proper isolation is critical to prevent test pollution and race conditions.

## The Problem with Singletons in Tests

### Test Pollution
```python
# ❌ BAD: One test affects another
def test_one():
    from ClassicLib import GlobalRegistry
    GlobalRegistry.register("key", "value1")
    assert GlobalRegistry.get("key") == "value1"

def test_two():
    from ClassicLib import GlobalRegistry
    # This might fail if test_one ran first!
    assert GlobalRegistry.get("key") is None  # FAILS!
```

### Race Conditions in Parallel Tests
```python
# ❌ BAD: Tests running in parallel can interfere
def test_parallel_one():
    GlobalRegistry.register("shared_key", "value_from_test_1")
    # Another test might overwrite this!

def test_parallel_two():
    GlobalRegistry.register("shared_key", "value_from_test_2")
    # Race condition with test_parallel_one!
```

## Correct Testing Patterns

### ✅ Pattern 1: Clear Registry in Fixtures (Recommended)

```python
import pytest
from ClassicLib import GlobalRegistry

@pytest.fixture(autouse=True)
def clean_global_registry():
    """Clear GlobalRegistry before and after each test.
    
    Uses the public clear() API which is designed for testing
    and includes safety checks to prevent accidental use in production.
    """
    # Clear before test using the public API
    GlobalRegistry.clear()

    yield

    # Clear after test using the public API
    GlobalRegistry.clear()
```

**Note**: The `GlobalRegistry.clear()` function will only work when running under
pytest (it detects the `PYTEST_CURRENT_TEST` environment variable). This prevents
accidental clearing in production code.

### ✅ Pattern 2: Mock the Registry Entirely

```python
from unittest.mock import patch, MagicMock

def test_with_mocked_registry():
    """Mock GlobalRegistry to avoid side effects."""
    with patch("ClassicLib.GlobalRegistry") as mock_registry:
        mock_registry.get.return_value = "mocked_value"
        mock_registry.register.return_value = None

        # Your test code here
        from my_module import function_using_registry
        result = function_using_registry()

        mock_registry.get.assert_called_once_with("expected_key")
```

### ✅ Pattern 3: Scoped Registry for Tests

```python
@pytest.fixture
def scoped_registry():
    """Create a scoped registry that doesn't affect global state.
    
    Uses direct _registry access for copy/restore semantics where
    needed, and the public clear() API where appropriate.
    """
    from ClassicLib import GlobalRegistry

    # Save original registry (requires direct access for copy semantics)
    original_registry = GlobalRegistry._registry.copy()

    # Clear for this test using the public API
    GlobalRegistry.clear()

    yield GlobalRegistry

    # Restore original (requires direct access for update semantics)
    GlobalRegistry._registry.clear()
    GlobalRegistry._registry.update(original_registry)
```

### ✅ Pattern 4: Test-Specific Keys with Cleanup

```python
import uuid

def test_with_unique_keys():
    """Use unique keys to avoid conflicts."""
    test_key = f"test_key_{uuid.uuid4()}"

    GlobalRegistry.register(test_key, "test_value")
    assert GlobalRegistry.get(test_key) == "test_value"

    # Clean up using the public unregister() API
    GlobalRegistry.unregister(test_key)
```

### ✅ Pattern 5: Using the Unregister Function

```python
def test_with_targeted_cleanup():
    """Use unregister() for specific key removal in production-safe code."""
    test_key = "my_component"
    
    try:
        GlobalRegistry.register(test_key, create_my_component())
        # test code
    finally:
        # unregister() returns True if key was found and removed
        removed = GlobalRegistry.unregister(test_key)
        assert removed  # Verify cleanup happened
```

## Testing Singleton Classes

### Testing ScanGameCore

```python
@pytest.fixture
def clean_scan_game_core():
    """Ensure ScanGameCore singleton is reset."""
    from ClassicLib import GlobalRegistry
    from ClassicLib.ScanGame.ScanGameCore import SCAN_GAME_CORE_KEY

    # Remove existing instance
    if SCAN_GAME_CORE_KEY in GlobalRegistry._registry:
        del GlobalRegistry._registry[SCAN_GAME_CORE_KEY]

    yield

    # Clean up after test
    if SCAN_GAME_CORE_KEY in GlobalRegistry._registry:
        del GlobalRegistry._registry[SCAN_GAME_CORE_KEY]

def test_scan_game_core(clean_scan_game_core):
    """Test with fresh ScanGameCore instance."""
    from ClassicLib.ScanGame.ScanGameCore import ScanGameCore

    core = ScanGameCore()
    # Test your core functionality
```

### Testing MessageHandler

```python
@pytest.fixture
def init_message_handler():
    """Initialize MessageHandler for tests."""
    from ClassicLib.MessageHandler import init_message_handler
    import ClassicLib.MessageHandler

    # Initialize fresh handler
    handler = init_message_handler(parent=None, is_gui_mode=False)

    yield handler

    # Clean up
    ClassicLib.MessageHandler._message_handler = None
```

## Parallel Testing Considerations

### Using pytest-xdist Safely

```python
# conftest.py
import pytest
from _pytest.fixtures import FixtureRequest

@pytest.fixture(scope="function", autouse=True)
def isolate_global_state(request: FixtureRequest):
    """Isolate global state for each test worker."""
    from ClassicLib import GlobalRegistry

    # Each worker gets its own registry state
    worker_id = getattr(request.config, 'workerinput', {}).get('workerid', 'master')

    # Save state
    original_registry = GlobalRegistry._registry.copy()

    yield

    # Restore state
    GlobalRegistry._registry = original_registry
```

### Worker-Specific Instances

```python
def get_worker_specific_key(base_key: str) -> str:
    """Get a worker-specific key for parallel tests."""
    import os
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')
    return f"{base_key}_{worker_id}"

def test_with_worker_isolation():
    """Test that works in parallel execution."""
    key = get_worker_specific_key("my_key")
    GlobalRegistry.register(key, "value")

    # No conflicts with other workers
    assert GlobalRegistry.get(key) == "value"
```

## Real-World Examples from CLASSIC

### Example 1: Testing with Fresh ScanGameCore

```python
@pytest.fixture
def fresh_scan_core():
    """Provide fresh ScanGameCore instance."""
    from ClassicLib import GlobalRegistry
    from ClassicLib.ScanGame.ScanGameCore import SCAN_GAME_CORE_KEY

    # Clear any existing instance
    GlobalRegistry._registry.pop(SCAN_GAME_CORE_KEY, None)

    # Create new instance
    from ClassicLib.ScanGame.ScanGameCore import ScanGameCore
    core = ScanGameCore()

    yield core

    # Clean up
    GlobalRegistry._registry.pop(SCAN_GAME_CORE_KEY, None)

@pytest.mark.asyncio
async def test_scan_operation(fresh_scan_core):
    """Test scan operation with isolated core."""
    result = await fresh_scan_core.check_log_errors(test_path)
    assert "error" in result.lower()
```

### Example 2: Testing Game Selection

```python
def test_game_selection():
    """Test game selection with registry isolation."""
    from ClassicLib import GlobalRegistry

    # Use unique key for this test
    test_game_key = f"test_game_{id(test_game_selection)}"

    try:
        GlobalRegistry.register(test_game_key, "Fallout4")
        assert GlobalRegistry.get(test_game_key) == "Fallout4"

        # Change game
        GlobalRegistry.register(test_game_key, "SkyrimSE")
        assert GlobalRegistry.get(test_game_key) == "SkyrimSE"
    finally:
        # Always clean up
        GlobalRegistry._registry.pop(test_game_key, None)
```

## Common Pitfalls and Solutions

### Pitfall 1: Forgetting to Clean Up

```python
# ❌ BAD: No cleanup
def test_bad():
    GlobalRegistry.register("key", "value")
    # This pollutes other tests!

# ✅ GOOD: Always clean up using unregister()
def test_good():
    try:
        GlobalRegistry.register("key", "value")
        # test code
    finally:
        GlobalRegistry.unregister("key")  # Safe, returns False if key doesn't exist
```

### Pitfall 2: Assuming Empty Registry

```python
# ❌ BAD: Assumes registry is empty
def test_bad():
    assert len(GlobalRegistry._registry) == 0  # Might fail!

# ✅ GOOD: Clear first or use fixture
def test_good(clean_global_registry):
    assert len(GlobalRegistry._registry) == 0  # Now safe
```

### Pitfall 3: Module-Level Registry Access

```python
# ❌ BAD: Module-level access
from ClassicLib import GlobalRegistry
MY_VALUE = GlobalRegistry.get("some_key")  # Executes at import!

def test_something():
    # MY_VALUE is already set!
    pass

# ✅ GOOD: Access within functions
def test_something():
    from ClassicLib import GlobalRegistry
    my_value = GlobalRegistry.get("some_key")
    # Now properly isolated
```

## API Reference

### `GlobalRegistry.clear()`

Clears all entries from the registry. **Test-only function** that raises
`RuntimeError` if called outside of pytest context.

```python
# Only works when running under pytest
GlobalRegistry.clear()  # Clears all registry entries
```

### `GlobalRegistry.unregister(key: str) -> bool`

Removes a specific key from the registry. **Production-safe** function that
can be used for targeted cleanup.

```python
# Safe for both production and test code
removed = GlobalRegistry.unregister("my_key")  # Returns True if key existed
```

## Best Practices Summary

1. **Use `clear()` in fixtures**: Clean registry before and after tests using the public API
2. **Use `unregister()` for targeted cleanup**: Prefer `unregister()` over direct `_registry` access
3. **Use unique keys**: When possible, use unique keys (UUIDs, test names) to avoid conflicts
4. **Mock when appropriate**: Mock the entire registry for unit tests that don't need real instances
5. **Isolate workers**: In parallel tests, ensure each worker has isolated state
6. **Test in functions**: Avoid module-level registry access in test files
7. **Document dependencies**: If a test requires specific registry state, document it clearly

## Quick Reference

| Scenario           | Solution             | Example                                    |
| ------------------ | -------------------- | ------------------------------------------ |
| Unit test          | Mock GlobalRegistry  | `patch("ClassicLib.GlobalRegistry")`       |
| Integration test   | Clear and restore    | `GlobalRegistry.clear()` in fixture        |
| Single key cleanup | Use unregister()     | `GlobalRegistry.unregister(key)`           |
| Parallel tests     | Worker-specific keys | `f"{key}_{worker_id}"`                     |
| Singleton testing  | Reset instance       | `GlobalRegistry.unregister(SINGLETON_KEY)` |
| Test isolation     | Scoped fixture       | Save/restore registry state                |

## Related Documentation

- [Testing AsyncBridge](./testing_async_bridge.md)
- [Testing YamlSettingsCache](./testing_yaml_cache.md)
- [CLAUDE.md Testing Section](../CLAUDE.md#testing-patterns)
