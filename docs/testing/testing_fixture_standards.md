# Testing Fixture Standards

## Overview

This document defines the standardized fixture system for the CLASSIC test suite, ensuring proper test isolation and preventing singleton pollution in parallel test execution.

**Key Singletons Managed:**
- **MessageHandler** - Message output system singleton
- **GlobalRegistry** - Global state registry singleton
- **AsyncBridge** - Thread-local async execution bridge

## MessageHandler Fixtures

### Standard Fixtures

#### `message_handler` / `init_message_handler_fixture`

**Purpose**: Initialize MessageHandler for non-GUI tests with automatic cleanup.

**Features**:
- Thread-safe for parallel test execution
- Automatic cleanup after test completion
- Nested fixture support (can be used in other fixtures)
- Stack-based state management

**Usage**:
```python
def test_something(message_handler):
    """Test that needs MessageHandler."""
    from ClassicLib.MessageHandler import msg_info
    msg_info("Test message")
    # MessageHandler is automatically cleaned up
```

Or using the legacy name:
```python
def test_something(init_message_handler_fixture):
    """Test using the legacy fixture name."""
    # Works the same as message_handler
```

#### `gui_message_handler`

**Purpose**: Initialize MessageHandler in GUI mode with Qt parent widget.

**Features**:
- Requires Qt application context
- Mocks message signals to prevent blocking dialogs
- Thread-safe with same state management as non-GUI fixture

**Usage**:
```python
def test_gui_feature(gui_message_handler, qt_parent_widget):
    """Test GUI components with MessageHandler."""
    assert gui_message_handler.is_gui_mode
    # Dialog messages are mocked and won't block
```

### Automatic Cleanup

#### `ensure_message_handler_cleanup` (autouse)

This fixture runs automatically for ALL tests and ensures MessageHandler singleton is properly cleaned up, even if tests don't use fixtures correctly.

**You don't need to use this directly** - it's automatically applied to all tests.

## AsyncBridge Fixtures

### Standard Fixtures

#### `async_bridge`

**Purpose**: Provide a clean AsyncBridge instance for testing async operations.

**Features**:
- Thread-local instance management
- Event loop isolation between tests
- Automatic cleanup of loops and threads
- Stack-based state management for nested fixtures

**Usage**:
```python
def test_async_operations(async_bridge):
    """Test with AsyncBridge available."""
    async def my_async_func():
        await asyncio.sleep(0.1)
        return "result"

    result = async_bridge.run_async(my_async_func())
    assert result == "result"
```

#### `mock_async_bridge`

**Purpose**: Mock AsyncBridge for unit tests that don't need actual async execution.

**Features**:
- Returns mocked result immediately
- No actual event loop created
- Useful for testing sync wrappers

**Usage**:
```python
def test_sync_wrapper(mock_async_bridge):
    """Test with mocked AsyncBridge."""
    mock_async_bridge.run_async.return_value = "mocked_result"

    # Code under test that uses AsyncBridge internally
    result = my_sync_wrapper_function()
    assert result == "mocked_result"
```

### Automatic Cleanup

#### `ensure_async_bridge_cleanup` (autouse)

This fixture automatically runs for ALL tests and ensures AsyncBridge instances are properly cleaned up, including:
- Shutting down event loops
- Cleaning up thread-local instances
- Removing orphaned instances from dead threads

**You don't need to use this directly** - it's automatically applied to all tests.

## GlobalRegistry Fixtures

### Standard Fixtures

#### `global_registry`

**Purpose**: Provide a clean GlobalRegistry for testing.

**Features**:
- Clears registry before and after test
- Function-scoped for complete isolation
- Returns the GlobalRegistry class for use

**Usage**:
```python
def test_registry_operations(global_registry):
    """Test registry functionality."""
    global_registry.register("test_key", "test_value")
    assert global_registry.get("test_key") == "test_value"
    # Registry is automatically cleared after test
```

### Automatic Cleanup

#### `clean_global_registry` (autouse)

This fixture automatically clears GlobalRegistry before and after each test, ensuring complete isolation.

**You don't need to use this directly** - it's automatically applied to all tests.

## Migration Guide

### Old Pattern ❌
```python
@pytest.fixture
def init_message_handler_test():
    """Initialize message handler for testing."""
    import ClassicLib.MessageHandler
    from ClassicLib.MessageHandler import init_message_handler
    _handler = init_message_handler(parent=None, is_gui_mode=False)
    yield
    ClassicLib.MessageHandler._message_handler = None

def test_something(init_message_handler_test):
    # test code
```

### New Pattern ✅
```python
def test_something(message_handler):
    """Just use the standardized fixture."""
    # MessageHandler is initialized and cleaned up automatically
    # test code
```

### For Classes with Multiple Tests

**Old Pattern ❌**:
```python
@pytest.fixture(autouse=True)
def setup_handler():
    init_message_handler(parent=None, is_gui_mode=False)
    yield
    ClassicLib.MessageHandler._message_handler = None

class TestMyFeature:
    def test_one(self):
        # test code

    def test_two(self):
        # test code
```

**New Pattern ✅**:
```python
class TestMyFeature:
    def test_one(self, message_handler):
        # MessageHandler available and cleaned up
        # test code

    def test_two(self, message_handler):
        # MessageHandler available and cleaned up
        # test code
```

## Thread Safety

The fixture system is designed for thread-safe operation with `pytest-xdist`:

1. **Thread-local state tracking** - Each test worker maintains its own handler stack
2. **Lock-protected operations** - Critical sections use threading locks
3. **Automatic cleanup** - Autouse fixtures ensure cleanup even on test failures
4. **Stack-based management** - Supports nested fixture usage

## Best Practices

### DO ✅

1. **Use standardized fixtures** instead of manual initialization:
   ```python
   def test_feature(message_handler):
       # Correct - use the fixture
   ```

2. **Let fixtures handle cleanup** - don't manually reset singletons:
   ```python
   def test_feature(message_handler):
       # Do your testing
       # No need to clean up - fixture handles it
   ```

3. **Use appropriate fixture for context**:
   ```python
   def test_gui(gui_message_handler):  # GUI tests
   def test_core(message_handler):      # Non-GUI tests
   ```

### DON'T ❌

1. **Don't directly manipulate singleton state**:
   ```python
   # WRONG
   ClassicLib.MessageHandler._message_handler = None
   ```

2. **Don't create custom initialization fixtures**:
   ```python
   # WRONG - Use standardized fixtures instead
   @pytest.fixture
   def my_custom_handler():
       init_message_handler(...)
   ```

3. **Don't skip cleanup** thinking it's automatic:
   ```python
   # WRONG - Always use fixtures for proper cleanup
   def test_something():
       init_message_handler(...)  # No cleanup!
   ```

## Debugging Isolation Issues

If you encounter test pollution:

1. **Check fixture usage**:
   ```bash
   # Find tests not using standardized fixtures
   grep -r "_message_handler = None" tests/
   grep -r "init_message_handler(" tests/ | grep -v "fixture"
   ```

2. **Run tests in isolation**:
   ```bash
   # Test single file
   pytest tests/path/to/test.py -v

   # Test with different worker counts
   pytest tests/ -n 1  # Single worker
   pytest tests/ -n 4  # Parallel execution
   ```

3. **Use verbose output**:
   ```bash
   # See fixture setup/teardown
   pytest tests/ --setup-show
   ```

## Examples

### Basic Test
```python
def test_crash_log_processing(message_handler, tmp_path):
    """Test with MessageHandler available."""
    from ClassicLib.MessageHandler import msg_info

    # Create test file
    log_file = tmp_path / "test.log"
    log_file.write_text("ERROR: Test error")

    # MessageHandler is available for the code under test
    msg_info(f"Processing {log_file}")

    # Your test logic here
    assert log_file.exists()
```

### Async Test
```python
@pytest.mark.asyncio
async def test_async_operation(message_handler):
    """Async test with MessageHandler."""
    from ClassicLib.ScanGame.ScanGameCore import ScanGameCore

    core = ScanGameCore()  # Uses MessageHandler internally
    result = await core.check_log_errors(Path("logs"))
    assert result is not None
```

### GUI Test
```python
def test_settings_dialog(gui_message_handler, qt_parent_widget):
    """Test GUI with mocked message dialogs."""
    from ClassicLib.Interface.Settings import SettingsDialog

    dialog = SettingsDialog(qt_parent_widget)
    # Message dialogs are mocked and won't block
    dialog.save_settings()

    # Verify mocked signal was called
    assert gui_message_handler.message_signal.called
```

## Summary

The standardized fixture system provides comprehensive singleton management for:

### Managed Singletons
1. **MessageHandler** - Automatic initialization and cleanup for message handling
2. **GlobalRegistry** - Complete isolation of global state between tests
3. **AsyncBridge** - Thread-local event loop management and cleanup

### Key Benefits
1. **Automatic singleton cleanup** - No manual cleanup needed
2. **Thread-safe operation** - Safe for parallel testing with pytest-xdist
3. **Consistent patterns** - Same approach for all singletons
4. **Nested fixture support** - Fixtures can use other fixtures
5. **Minimal migration effort** - Just add fixture parameter to tests
6. **Event loop isolation** - AsyncBridge loops don't leak between tests
7. **Dead thread cleanup** - Orphaned instances automatically removed

### Parallel Testing Safety
All fixtures are designed for safe operation with `pytest-xdist`:
- Thread-local state tracking prevents cross-worker pollution
- Lock-protected critical sections ensure thread safety
- Automatic cleanup handles test failures gracefully
- Stack-based management supports complex fixture dependencies

By following these standards, the test suite maintains proper isolation, preventing test pollution and ensuring reliable parallel execution.
