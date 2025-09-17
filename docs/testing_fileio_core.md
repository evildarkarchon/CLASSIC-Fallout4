# Testing FileIOCore and AsyncBridge Coupling Guide

## Overview

FileIOCore provides unified async-first file I/O operations, while sync adapters use AsyncBridge to run async operations in sync contexts. This creates indirect singleton coupling that can cause test pollution when AsyncBridge state persists across tests, affecting all file operations.

## The Problem

### Symptoms of FileIOCore/AsyncBridge Test Pollution

1. **Event Loop Pollution**
   - FileIOCore operations use different event loops across tests
   - "RuntimeError: Cannot attach a running loop" warnings
   - Async operations from previous tests still running
   - Event loop state corruption affecting file operations

2. **AsyncBridge State Persistence**
   - AsyncBridge singleton retains state across tests
   - Cached async functions persist between tests
   - Error handling state corrupted from previous tests
   - Performance metrics accumulated across tests

3. **File Operation Interference**
   - File operations succeed with stale AsyncBridge state
   - Encoding settings persist from previous tests
   - Error handling behavior inconsistent
   - File paths resolved incorrectly due to bridge state

4. **Resource Leaks**
   - File handles remain open from failed operations
   - Async tasks not properly cleaned up
   - Bridge resources not released between tests
   - Memory leaks from accumulated file operations

## Root Causes

### 1. Indirect Singleton Coupling

```python
# In ClassicLib/FileIO/sync_adapters.py
def read_file_sync(path: Path | str) -> str:
    bridge = AsyncBridge.get_instance()  # Singleton dependency
    return bridge.run_async(FileIOCore().read_file(path))

def write_file_sync(path: Path | str, content: str) -> None:
    bridge = AsyncBridge.get_instance()  # Same singleton
    bridge.run_async(FileIOCore().write_file(path, content))
```

### 2. New FileIOCore Instances

While FileIOCore creates new instances, it depends on the AsyncBridge singleton:
```python
class FileIOCore:
    def __init__(self, encoding: str = "utf-8", errors: str = "ignore"):
        # New instance, but uses singleton bridge through adapters
```

### 3. Sync Wrapper Pattern

All sync adapters follow the same pattern:
```python
def operation_sync(*args):
    bridge = AsyncBridge.get_instance()  # Pollution source
    return bridge.run_async(FileIOCore().async_operation(*args))
```

### 4. Error State Accumulation

AsyncBridge accumulates error state that affects FileIOCore operations:
- Failed operations leave bridge in error state
- Retry logic affected by previous failures
- Error callbacks persist across tests

## Testing Patterns

### ✅ CORRECT: Mock AsyncBridge for FileIOCore Tests

```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from ClassicLib.FileIOCore import read_file_sync, write_file_sync

@pytest.fixture
def mock_async_bridge():
    """Mock AsyncBridge to isolate FileIOCore tests."""
    with patch("ClassicLib.FileIOCore.AsyncBridge") as mock_bridge_class:
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge

        # Configure mock for file operations
        mock_bridge.run_async.return_value = "test content"

        yield mock_bridge


def test_read_file_with_mock_bridge(mock_async_bridge):
    """Test read_file_sync with mocked AsyncBridge."""
    result = read_file_sync(Path("test.txt"))

    assert result == "test content"
    mock_async_bridge.run_async.assert_called_once()


def test_write_file_with_mock_bridge(mock_async_bridge):
    """Test write_file_sync with mocked AsyncBridge."""
    mock_async_bridge.run_async.return_value = None  # write returns None

    write_file_sync(Path("test.txt"), "content")

    mock_async_bridge.run_async.assert_called_once()
```

### ✅ CORRECT: Reset AsyncBridge for Integration Tests

```python
import pytest
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.FileIOCore import read_file_sync, write_file_sync

@pytest.fixture
def reset_async_bridge():
    """Reset AsyncBridge state for integration tests."""
    # Clear any existing instance
    AsyncBridge._instance = None

    yield

    # Cleanup after test
    if AsyncBridge._instance:
        bridge = AsyncBridge._instance
        # Close any open resources
        if hasattr(bridge, '_loop') and bridge._loop:
            if not bridge._loop.is_closed():
                bridge._loop.close()
    AsyncBridge._instance = None


def test_file_operations_integration(tmp_path, reset_async_bridge):
    """Test FileIOCore with clean AsyncBridge."""
    test_file = tmp_path / "test.txt"
    test_content = "Test file content\nLine 2"

    # Write file
    write_file_sync(test_file, test_content)
    assert test_file.exists()

    # Read file
    content = read_file_sync(test_file)
    assert content == test_content
```

### ✅ CORRECT: Direct FileIOCore Testing

```python
import pytest
import asyncio
from ClassicLib.FileIO.core import FileIOCore

@pytest.mark.asyncio
async def test_direct_fileio_core(tmp_path):
    """Test FileIOCore directly without sync adapters."""
    core = FileIOCore()
    test_file = tmp_path / "direct_test.txt"
    test_content = "Direct async test"

    # Write file directly
    await core.write_file(test_file, test_content)
    assert test_file.exists()

    # Read file directly
    content = await core.read_file(test_file)
    assert content == test_content


@pytest.mark.asyncio
async def test_fileio_core_error_handling(tmp_path):
    """Test FileIOCore error handling without bridge pollution."""
    core = FileIOCore()
    nonexistent = tmp_path / "nonexistent.txt"

    # Test error handling
    with pytest.raises(FileNotFoundError):
        await core.read_file(nonexistent)
```

### ✅ CORRECT: Mocking for Unit Tests

```python
from unittest.mock import patch, AsyncMock, MagicMock

@patch('ClassicLib.FileIOCore.FileIOCore')
def test_sync_adapter_mocking(mock_fileio_class):
    """Test sync adapters with mocked FileIOCore."""
    # Setup mocks
    mock_instance = AsyncMock()
    mock_fileio_class.return_value = mock_instance
    mock_instance.read_file.return_value = "mocked content"

    with patch("ClassicLib.FileIOCore.AsyncBridge") as mock_bridge_class:
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge
        mock_bridge.run_async.return_value = "mocked content"

        # Test the sync adapter
        result = read_file_sync("test.txt")

        assert result == "mocked content"
        mock_bridge.run_async.assert_called_once()
```

### ❌ WRONG: Shared AsyncBridge Across Tests

```python
# BAD - AsyncBridge singleton shared across tests
def test_one():
    content = read_file_sync("test1.txt")  # Affects bridge state

def test_two():
    content = read_file_sync("test2.txt")  # Uses polluted bridge
```

### ❌ WRONG: No Bridge Cleanup

```python
def test_without_cleanup():
    """Test that doesn't clean up AsyncBridge."""
    # Uses AsyncBridge singleton
    content = read_file_sync("test.txt")
    # Bridge state persists to next test!
```

### ❌ WRONG: Mixing Async and Sync

```python
@pytest.mark.asyncio
async def test_mixed_operations():
    """Mixing async and sync operations."""
    # Direct async
    core = FileIOCore()
    await core.write_file("test.txt", "content")

    # Sync adapter - may conflict with async context
    content = read_file_sync("test.txt")  # Uses different bridge context
```

## Parallel Testing Considerations

### Worker Isolation with pytest-xdist

```python
import pytest
import os
from ClassicLib.AsyncBridge import AsyncBridge

@pytest.fixture
def worker_isolated_bridge():
    """Ensure AsyncBridge isolation for parallel workers."""
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')

    # Clear any existing instance
    AsyncBridge._instance = None

    # Create worker-specific state if needed
    yield worker_id

    # Cleanup
    if AsyncBridge._instance:
        # Close loop if it exists
        bridge = AsyncBridge._instance
        if hasattr(bridge, '_loop') and bridge._loop and not bridge._loop.is_closed():
            bridge._loop.close()
    AsyncBridge._instance = None


def test_file_operations_parallel_safe(tmp_path, worker_isolated_bridge):
    """Test that works safely in parallel workers."""
    worker_id = worker_isolated_bridge

    # Create worker-specific files
    test_file = tmp_path / f"worker_{worker_id}.txt"
    content = f"Worker {worker_id} content"

    write_file_sync(test_file, content)
    result = read_file_sync(test_file)

    assert result == content
```

### Concurrent File Operations

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.asyncio
async def test_concurrent_file_operations(tmp_path, reset_async_bridge):
    """Test concurrent file operations."""
    async def write_and_read(file_id):
        """Async operation for one file."""
        core = FileIOCore()
        file_path = tmp_path / f"concurrent_{file_id}.txt"
        content = f"File {file_id} content"

        await core.write_file(file_path, content)
        result = await core.read_file(file_path)
        return file_id, result

    # Run multiple operations concurrently
    tasks = [write_and_read(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    # Verify all operations succeeded
    assert len(results) == 10
    for file_id, content in results:
        assert content == f"File {file_id} content"


def test_sync_concurrent_operations(tmp_path, reset_async_bridge):
    """Test concurrent sync operations."""
    def sync_write_and_read(file_id):
        """Sync operation for one file."""
        file_path = tmp_path / f"sync_concurrent_{file_id}.txt"
        content = f"Sync File {file_id} content"

        write_file_sync(file_path, content)
        return read_file_sync(file_path)

    # Run with thread pool
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(sync_write_and_read, i)
            for i in range(10)
        ]

        results = [future.result() for future in futures]

    # Verify all operations succeeded
    assert len(results) == 10
    for i, content in enumerate(results):
        assert content == f"Sync File {i} content"
```

## Common Pitfalls and Solutions

### 1. Event Loop Conflicts

**Problem**: Multiple event loops
```python
@pytest.mark.asyncio
async def test_loop_conflict():
    # Async context
    core = FileIOCore()
    await core.write_file("test.txt", "content")

    # Sync adapter creates new loop
    content = read_file_sync("test.txt")  # May conflict
```

**Solution**: Use consistent approach
```python
@pytest.mark.asyncio
async def test_consistent_async():
    """Use only async operations in async tests."""
    core = FileIOCore()
    await core.write_file("test.txt", "content")
    content = await core.read_file("test.txt")
    assert content == "content"


def test_consistent_sync(reset_async_bridge):
    """Use only sync operations in sync tests."""
    write_file_sync("test.txt", "content")
    content = read_file_sync("test.txt")
    assert content == "content"
```

### 2. Bridge State Accumulation

**Problem**: Error state persists
```python
def test_error_accumulation():
    try:
        read_file_sync("nonexistent.txt")  # Sets error state
    except FileNotFoundError:
        pass

    # Bridge may be in error state for next operation
    content = read_file_sync("real_file.txt")
```

**Solution**: Reset bridge between tests
```python
@pytest.fixture(autouse=True)
def reset_bridge_state():
    """Reset AsyncBridge state between tests."""
    AsyncBridge._instance = None
    yield
    AsyncBridge._instance = None
```

### 3. Resource Leaks in Failed Operations

**Problem**: Failed operations leak resources
```python
def test_resource_leak():
    for i in range(1000):
        try:
            content = read_file_sync(f"nonexistent_{i}.txt")
        except FileNotFoundError:
            pass  # Bridge may accumulate resources
```

**Solution**: Proper error handling and cleanup
```python
def test_with_proper_cleanup(reset_async_bridge):
    """Test with proper resource cleanup."""
    failed_operations = 0

    for i in range(100):
        try:
            content = read_file_sync(f"nonexistent_{i}.txt")
        except FileNotFoundError:
            failed_operations += 1

    assert failed_operations == 100

    # Bridge automatically cleaned by fixture
```

### 4. Encoding State Persistence

**Problem**: Encoding settings persist
```python
def test_encoding_pollution():
    # First test uses specific encoding
    core1 = FileIOCore(encoding="latin-1")
    # Operations may affect global state

    # Second test expects default encoding
    content = read_file_sync("utf8_file.txt")  # May use wrong encoding
```

**Solution**: Explicit encoding per test
```python
def test_explicit_encoding(tmp_path):
    """Test with explicit encoding handling."""
    test_file = tmp_path / "encoding_test.txt"

    # Write with specific encoding
    with patch("ClassicLib.FileIOCore.AsyncBridge") as mock_bridge_class:
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge

        # Test operation
        core = FileIOCore(encoding="utf-8", errors="strict")
        # Use core directly to avoid bridge pollution
```

## Best Practices

1. **Mock AsyncBridge for unit tests**
   - Always mock AsyncBridge.get_instance()
   - Configure mock for expected behavior
   - Verify bridge interactions

2. **Reset bridge for integration tests**
   - Clear AsyncBridge._instance between tests
   - Use fixtures for automatic cleanup
   - Close event loops properly

3. **Use consistent async patterns**
   - Don't mix async and sync operations in tests
   - Choose either direct FileIOCore or sync adapters

4. **Test file operations in isolation**
   - Use tmp_path for test files
   - Create fresh FileIOCore instances
   - Don't share files between tests

5. **Handle errors properly**
   - Test error conditions explicitly
   - Clean up after failed operations
   - Don't let errors accumulate

## Complete Test Example

```python
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from ClassicLib.FileIOCore import read_file_sync, write_file_sync
from ClassicLib.FileIO.core import FileIOCore
from ClassicLib.AsyncBridge import AsyncBridge


class TestFileIOCoreIsolation:
    """Demonstrate proper FileIOCore/AsyncBridge test isolation."""

    @pytest.fixture
    def mock_bridge(self):
        """Mock AsyncBridge for unit tests."""
        with patch("ClassicLib.FileIOCore.AsyncBridge") as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge_class.get_instance.return_value = mock_bridge
            yield mock_bridge

    @pytest.fixture
    def reset_bridge(self):
        """Reset AsyncBridge for integration tests."""
        AsyncBridge._instance = None
        yield
        if AsyncBridge._instance:
            bridge = AsyncBridge._instance
            if hasattr(bridge, '_loop') and bridge._loop and not bridge._loop.is_closed():
                bridge._loop.close()
        AsyncBridge._instance = None

    def test_sync_operations_with_mock(self, tmp_path, mock_bridge):
        """Test sync operations with mocked bridge."""
        test_file = tmp_path / "mock_test.txt"
        test_content = "Mock test content"

        # Configure mock
        mock_bridge.run_async.return_value = test_content

        # Test read operation
        result = read_file_sync(test_file)
        assert result == test_content

        # Configure mock for write (returns None)
        mock_bridge.run_async.return_value = None

        # Test write operation
        write_file_sync(test_file, test_content)

        # Verify bridge was called
        assert mock_bridge.run_async.call_count == 2

    @pytest.mark.asyncio
    async def test_direct_async_operations(self, tmp_path):
        """Test FileIOCore directly without bridge."""
        core = FileIOCore()
        test_file = tmp_path / "async_test.txt"
        test_content = "Direct async content"

        # Test write
        await core.write_file(test_file, test_content)
        assert test_file.exists()

        # Test read
        result = await core.read_file(test_file)
        assert result == test_content

        # Test lines
        lines = await core.read_lines(test_file)
        assert lines == [test_content]

    def test_integration_with_real_bridge(self, tmp_path, reset_bridge):
        """Test with real AsyncBridge integration."""
        test_file = tmp_path / "integration_test.txt"
        test_content = "Integration test content\nLine 2"

        # Write file
        write_file_sync(test_file, test_content)
        assert test_file.exists()

        # Read file
        result = read_file_sync(test_file)
        assert result == test_content

        # Test lines
        from ClassicLib.FileIOCore import read_lines_sync
        lines = read_lines_sync(test_file)
        assert len(lines) == 2
        assert lines[0] == "Integration test content"

    def test_error_handling_isolation(self, tmp_path, mock_bridge):
        """Test error handling without bridge pollution."""
        nonexistent = tmp_path / "nonexistent.txt"

        # Configure mock to raise exception
        mock_bridge.run_async.side_effect = FileNotFoundError("File not found")

        # Test error handling
        with pytest.raises(FileNotFoundError):
            read_file_sync(nonexistent)

        # Reset mock for next operation
        mock_bridge.run_async.side_effect = None
        mock_bridge.run_async.return_value = "success"

        # Should work normally
        result = read_file_sync("any_file.txt")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, tmp_path, reset_bridge):
        """Test concurrent operations work correctly."""
        async def write_read_file(file_id):
            core = FileIOCore()
            file_path = tmp_path / f"concurrent_{file_id}.txt"
            content = f"Concurrent content {file_id}"

            await core.write_file(file_path, content)
            result = await core.read_file(file_path)
            return result

        # Run multiple operations
        tasks = [write_read_file(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result == f"Concurrent content {i}"

    def test_encoding_isolation(self, tmp_path, mock_bridge):
        """Test encoding doesn't pollute between tests."""
        # First operation with specific encoding
        core1 = FileIOCore(encoding="utf-8", errors="strict")

        # Mock the bridge call
        mock_bridge.run_async.return_value = "encoded content"

        # Second operation should be independent
        result = read_file_sync("test.txt")
        assert result == "encoded content"

        # Bridge isolation ensures no encoding pollution
        mock_bridge.run_async.assert_called()
```

## Debugging Tips

### 1. Check AsyncBridge State

```python
def debug_bridge_state():
    """Debug current AsyncBridge state."""
    from ClassicLib.AsyncBridge import AsyncBridge

    if AsyncBridge._instance:
        bridge = AsyncBridge._instance
        print(f"Bridge exists: {bridge}")
        print(f"Loop: {getattr(bridge, '_loop', 'None')}")
        print(f"Loop running: {getattr(bridge._loop, 'is_running', lambda: False)()}")
    else:
        print("No AsyncBridge instance")


@pytest.fixture(autouse=True)
def debug_bridge():
    """Debug bridge state before and after tests."""
    print("Before test:")
    debug_bridge_state()

    yield

    print("After test:")
    debug_bridge_state()
```

### 2. Monitor File Operations

```python
from unittest.mock import patch

@pytest.fixture
def monitor_file_operations():
    """Monitor FileIOCore operations."""
    operations = []

    original_read = FileIOCore.read_file
    original_write = FileIOCore.write_file

    async def monitored_read(self, path):
        operations.append(('read', str(path)))
        return await original_read(self, path)

    async def monitored_write(self, path, content):
        operations.append(('write', str(path)))
        return await original_write(self, path, content)

    with patch.object(FileIOCore, 'read_file', monitored_read), \
         patch.object(FileIOCore, 'write_file', monitored_write):
        yield operations
```

### 3. Detect Resource Leaks

```python
import gc
import asyncio

@pytest.fixture(autouse=True)
def detect_async_leaks():
    """Detect async resource leaks."""
    # Get initial task count
    initial_tasks = len(asyncio.all_tasks()) if hasattr(asyncio, 'all_tasks') else 0

    yield

    # Check for task leaks
    gc.collect()  # Force garbage collection
    final_tasks = len(asyncio.all_tasks()) if hasattr(asyncio, 'all_tasks') else 0

    if final_tasks > initial_tasks:
        print(f"WARNING: Possible task leak. Initial: {initial_tasks}, Final: {final_tasks}")
```

## See Also

- [Testing AsyncBridge Guide](testing_async_bridge.md)
- [Testing MessageHandler Guide](testing_message_handler.md)
- [Testing Database Pools Guide](testing_database_pools.md)
- [Test Pollution Prevention Guide](test_pollution_guide.md)
