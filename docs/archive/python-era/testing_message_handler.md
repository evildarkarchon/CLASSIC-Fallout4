# Testing MessageHandler Guide

## Overview

MessageHandler is a singleton that manages all user communication across GUI, TUI, and CLI modes. It maintains global state through `_message_handler` that persists across tests, causing test pollution and failures in parallel execution.

## The Problem

### Symptoms of MessageHandler Test Pollution

1. **Cross-test Message Leakage**
   - Messages from one test appear in another test's output
   - GUI dialogs unexpectedly appear during CLI tests
   - Progress bars persist across test boundaries

2. **Mode Confusion**
   - Tests fail because MessageHandler is in wrong mode (GUI vs CLI)
   - Qt signals fire when no Qt application exists
   - CLI output appears when testing GUI components

3. **Thread Safety Issues**
   - Race conditions when parallel tests access the singleton
   - Deadlocks in Qt signal handling
   - Inconsistent state when tests run concurrently

4. **Resource Leaks**
   - Progress dialogs remain open after tests
   - Qt widgets not properly cleaned up
   - Logger handlers accumulate across tests

## Root Causes

### 1. Global Singleton Pattern

```python
# In ClassicLib/MessageHandler/handler.py
_message_handler: MessageHandler | None = None
_message_handler_lock = threading.Lock()

def init_message_handler(parent: QWidget | None = None, is_gui_mode: bool = False) -> MessageHandler:
    global _message_handler
    if _message_handler is None:
        with _message_handler_lock:
            if _message_handler is None:
                _message_handler = MessageHandler(parent, is_gui_mode)
    return _message_handler
```

### 2. Persistent Qt State

MessageHandler creates Qt signals that persist even after the handler is "cleared":
- `message_signal`
- `progress_signal`
- `progress_create_signal`
- `progress_close_signal`

### 3. Mode Persistence

Once initialized, the mode (`is_gui_mode`) cannot be changed without destroying and recreating the singleton.

## Testing Patterns

### ✅ CORRECT: Proper Isolation

```python
import pytest
from ClassicLib.MessageHandler import init_message_handler
import ClassicLib.MessageHandler

@pytest.fixture(autouse=True)
def clean_message_handler():
    """Ensure MessageHandler is clean for each test."""
    # Clear any existing handler
    ClassicLib.MessageHandler._message_handler = None
    yield
    # Clean up after test
    ClassicLib.MessageHandler._message_handler = None

def test_with_cli_mode(clean_message_handler):
    """Test with CLI message handler."""
    handler = init_message_handler(parent=None, is_gui_mode=False)
    # Your test code
    assert not handler.is_gui_mode

def test_with_gui_mode(clean_message_handler, qt_application):
    """Test with GUI message handler."""
    handler = init_message_handler(parent=None, is_gui_mode=True)
    # Your test code
    assert handler.is_gui_mode
```

### ✅ CORRECT: Mocking for Unit Tests

```python
from unittest.mock import patch, MagicMock

@patch('module.init_message_handler')
def test_with_mock_handler(mock_init):
    """Mock MessageHandler to avoid singleton issues."""
    mock_handler = MagicMock()
    mock_init.return_value = mock_handler

    # Configure mock for your test
    mock_handler.is_gui_mode = False
    mock_handler.info.return_value = None

    # Your test code
    result = function_that_uses_messages()

    # Verify interactions
    mock_handler.info.assert_called()
```

### ✅ CORRECT: Testing Message Output

```python
from unittest.mock import patch, MagicMock
from ClassicLib.MessageHandler import Message, MessageType

def test_message_output(clean_message_handler):
    """Test message output without pollution."""
    handler = init_message_handler(parent=None, is_gui_mode=False)

    # Capture messages instead of displaying them
    messages = []

    with patch.object(handler, '_handle_cli_message') as mock_cli:
        def capture_message(msg):
            messages.append(msg)
        mock_cli.side_effect = capture_message

        handler.info("Test message")

    assert len(messages) == 1
    assert messages[0].message == "Test message"
    assert messages[0].msg_type == MessageType.INFO
```

### ❌ WRONG: Shared Handler Across Tests

```python
# BAD - Creates handler at module level
handler = init_message_handler(parent=None, is_gui_mode=False)

def test_one():
    handler.info("Test 1")  # Pollutes global state

def test_two():
    handler.info("Test 2")  # May see messages from test_one
```

### ❌ WRONG: Not Cleaning Up

```python
def test_without_cleanup():
    """Test that doesn't clean up."""
    handler = init_message_handler(parent=None, is_gui_mode=True)
    # Test code
    # No cleanup - handler persists to next test!
```

## Parallel Testing Considerations

### Using pytest-xdist

When running tests in parallel with `pytest-xdist`, each worker process has its own MessageHandler singleton. However, tests within the same worker can still pollute each other.

```python
import pytest
import os

@pytest.fixture(autouse=True)
def isolate_message_handler():
    """Ensure complete isolation for parallel tests."""
    import ClassicLib.MessageHandler

    # Save original state
    original = ClassicLib.MessageHandler._message_handler

    # Clear for this test
    ClassicLib.MessageHandler._message_handler = None

    # Add worker ID to prevent cross-worker issues
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')

    yield worker_id

    # Restore (though usually None)
    ClassicLib.MessageHandler._message_handler = original
```

### Thread-Safe Test Patterns

```python
import threading
from ClassicLib.MessageHandler import init_message_handler

def test_concurrent_message_handling(clean_message_handler):
    """Test thread-safe message handling."""
    handler = init_message_handler(parent=None, is_gui_mode=False)
    results = []

    def send_messages(thread_id):
        for i in range(10):
            handler.info(f"Message {i} from thread {thread_id}")
        results.append(thread_id)

    threads = []
    for i in range(5):
        thread = threading.Thread(target=send_messages, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    assert len(results) == 5
```

## Common Pitfalls and Solutions

### 1. Qt Application Required for GUI Mode

**Problem**: GUI mode requires Qt application
```python
def test_gui_handler():
    handler = init_message_handler(parent=None, is_gui_mode=True)
    # RuntimeError: no Qt application found
```

**Solution**: Use qt_application fixture
```python
def test_gui_handler(qt_application, clean_message_handler):
    handler = init_message_handler(parent=None, is_gui_mode=True)
    # Works correctly
```

### 2. Progress Dialogs Not Closing

**Problem**: Progress dialogs persist
```python
def test_with_progress():
    with handler.progress_context("Task", 100) as progress:
        # Test code
    # Dialog may remain open
```

**Solution**: Ensure proper cleanup
```python
def test_with_progress(clean_message_handler):
    handler = init_message_handler(parent=None, is_gui_mode=False)

    try:
        with handler.progress_context("Task", 100) as progress:
            # Test code
            pass
    finally:
        if hasattr(handler, '_progress_dialog'):
            handler._progress_dialog = None
```

### 3. Logger Handler Accumulation

**Problem**: Logger handlers accumulate
```python
def test_logging():
    handler = init_message_handler()
    # Adds logger handler
    handler2 = init_message_handler()
    # May add duplicate handler
```

**Solution**: Check for existing handlers
```python
@pytest.fixture
def clean_logger():
    """Clean up logger handlers."""
    from ClassicLib.Logger import logger

    # Save original handlers
    original = logger.handlers.copy()

    yield

    # Restore original handlers
    logger.handlers = original
```

## Best Practices

1. **Always use fixtures for cleanup**
   - Use `autouse=True` for automatic cleanup
   - Clear handler before AND after each test

2. **Mock when possible**
   - Unit tests should mock MessageHandler
   - Only integration tests need real handler

3. **Specify mode explicitly**
   - Always specify `is_gui_mode` parameter
   - Don't rely on defaults

4. **Test in isolation**
   - Each test should create its own handler
   - Never share handlers between tests

5. **Handle Qt requirements**
   - Use `qt_application` fixture for GUI tests
   - Use CLI mode for non-GUI tests

## Example Test Suite

```python
import pytest
from unittest.mock import patch, MagicMock
from ClassicLib.MessageHandler import init_message_handler, MessageType
import ClassicLib.MessageHandler


class TestMessageHandlerIsolation:
    """Demonstrate proper MessageHandler test isolation."""

    @pytest.fixture(autouse=True)
    def clean_handler(self):
        """Ensure clean MessageHandler for each test."""
        ClassicLib.MessageHandler._message_handler = None
        yield
        ClassicLib.MessageHandler._message_handler = None

    def test_cli_mode_messages(self):
        """Test CLI mode message handling."""
        handler = init_message_handler(parent=None, is_gui_mode=False)

        # Capture output
        with patch('builtins.print') as mock_print:
            handler.info("Test message")
            mock_print.assert_called()

    def test_gui_mode_messages(self, qt_application):
        """Test GUI mode message handling."""
        handler = init_message_handler(parent=None, is_gui_mode=True)

        # Mock Qt message box
        with patch('PySide6.QtWidgets.QMessageBox.information') as mock_box:
            handler.info("Test message")
            mock_box.assert_called()

    def test_mode_isolation(self):
        """Test that modes don't affect each other."""
        # Test 1: CLI mode
        handler1 = init_message_handler(parent=None, is_gui_mode=False)
        assert not handler1.is_gui_mode

        # Clear and create new handler
        ClassicLib.MessageHandler._message_handler = None

        # Test 2: Different mode in same test
        handler2 = init_message_handler(parent=None, is_gui_mode=False)
        assert not handler2.is_gui_mode

    @patch('ClassicLib.MessageHandler.handler.MessageHandler')
    def test_with_mock(self, mock_handler_class):
        """Test with completely mocked handler."""
        mock_instance = MagicMock()
        mock_handler_class.return_value = mock_instance

        # Your code that uses MessageHandler
        mock_instance.info.assert_not_called()
```

## Debugging Tips

### 1. Check Handler State

```python
def debug_handler_state():
    """Debug current MessageHandler state."""
    import ClassicLib.MessageHandler

    handler = ClassicLib.MessageHandler._message_handler
    if handler:
        print(f"Handler exists: GUI={handler.is_gui_mode}")
        print(f"Parent widget: {handler.parent_widget}")
        print(f"Progress dialog: {getattr(handler, '_progress_dialog', None)}")
    else:
        print("No handler initialized")
```

### 2. Force Reset

```python
def force_reset_handler():
    """Force complete handler reset."""
    import ClassicLib.MessageHandler

    # Clear singleton
    ClassicLib.MessageHandler._message_handler = None

    # Clear any Qt widgets
    if HAS_QT:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.processEvents()
            app.closeAllWindows()
```

### 3. Detect Pollution

```python
@pytest.fixture(autouse=True)
def detect_handler_pollution():
    """Detect MessageHandler pollution between tests."""
    import ClassicLib.MessageHandler

    # Check if handler exists before test
    if ClassicLib.MessageHandler._message_handler is not None:
        pytest.fail("MessageHandler pollution detected!")

    yield

    # Cleanup for next test
    ClassicLib.MessageHandler._message_handler = None
```

## See Also

- [Testing AsyncBridge Guide](async_bridge.md)
- [Testing GlobalRegistry Guide](global_registry.md)
- [Testing YamlSettingsCache Guide](yaml_cache.md)
- [Test Pollution Prevention Guide](test_pollution_guide.md)
