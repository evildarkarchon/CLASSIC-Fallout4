# Testing ThreadSafeLogCache Guide

## Overview

ThreadSafeLogCache manages crash log data with thread-safe caching and concurrent access. It maintains persistent state through locks and caches that can cause test pollution, race conditions, and resource leaks in parallel test execution.

## The Problem

### Symptoms of ThreadSafeLogCache Test Pollution

1. **Cache Pollution**
   - Log data from previous tests appears in current test
   - Cached logs persist across test boundaries
   - Memory usage grows unbounded
   - Wrong log content returned due to stale cache

2. **Thread Lock Issues**
   - Deadlocks when tests run in parallel
   - Race conditions in cache access
   - Thread contention causing timeouts
   - Locks not released properly after test failures

3. **Resource Leaks**
   - File handles remain open after tests
   - Memory leaks from cached log data
   - Thread locks persist across tests
   - Log files locked by previous tests

4. **State Persistence**
   - Log names list persists across tests
   - Cache dictionary accumulates entries
   - Thread safety state corrupted
   - Inconsistent cache behavior

## Root Causes

### 1. Persistent Cache Dictionary

```python
# In ClassicLib/ScanLog/scanloginfo/thread_safe_log_cache.py
class ThreadSafeLogCache:
    def __init__(self, logfiles: list[Path]) -> None:
        self.lock = threading.RLock()  # Persists across instances
        self.cache: dict[str, bytes] = {}  # Never automatically cleared
```

### 2. Shared Thread Locks

ThreadSafeLogCache uses reentrant locks that can deadlock in parallel tests:
```python
def read_log(self, log_filename: str) -> list[str]:
    with self.lock:  # Lock shared across test boundaries
        # Cache access
```

### 3. Static Factory Method

The `from_cache` class method creates instances with pre-populated cache:
```python
@classmethod
def from_cache(cls, cache_dict: dict[str, bytes]) -> "ThreadSafeLogCache":
    instance = cls([])  # Empty logfiles
    instance.cache = cache_dict.copy()  # But populated cache
    return instance
```

### 4. File Handle Management

Cache initialization reads all files but may not close handles properly:
```python
def __init__(self, logfiles: list[Path]) -> None:
    # Reads all files into cache during initialization
    # File handles may leak if errors occur
```

## Testing Patterns

### ✅ CORRECT: Fresh Cache per Test

```python
import pytest
from pathlib import Path
from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache

@pytest.fixture
def fresh_log_cache(tmp_path):
    """Create fresh ThreadSafeLogCache for each test."""
    # Create test log files
    log_files = []
    for i in range(3):
        log_file = tmp_path / f"test_log_{i}.log"
        log_file.write_text(f"Log content {i}\nLine 2 of log {i}\n")
        log_files.append(log_file)

    # Create new cache instance
    cache = ThreadSafeLogCache(log_files)

    yield cache

    # Cleanup
    cache.close()  # Close any resources
    cache.cache.clear()  # Clear cache
    del cache


def test_with_fresh_cache(fresh_log_cache):
    """Test with isolated cache."""
    cache = fresh_log_cache

    log_names = cache.get_log_names()
    assert len(log_names) == 3

    content = cache.read_log("test_log_0.log")
    assert "Log content 0" in content[0]
```

### ✅ CORRECT: Mocking for Unit Tests

```python
from unittest.mock import MagicMock, patch
import pytest

@pytest.fixture
def mock_log_cache():
    """Mock ThreadSafeLogCache for unit tests."""
    mock_cache = MagicMock(spec=ThreadSafeLogCache)
    mock_cache.get_log_names.return_value = ["test1.log", "test2.log"]
    mock_cache.read_log.return_value = ["Mocked log content"]
    mock_cache.cache = {}  # Empty cache dict

    return mock_cache


def test_with_mock_cache(mock_log_cache):
    """Test function that uses log cache."""
    # Your code that uses ThreadSafeLogCache
    log_names = mock_log_cache.get_log_names()
    assert len(log_names) == 2

    content = mock_log_cache.read_log("test1.log")
    assert content == ["Mocked log content"]
```

### ✅ CORRECT: Testing Thread Safety

```python
import threading
import time
from concurrent.futures import ThreadPoolExecutor

def test_thread_safe_access(fresh_log_cache):
    """Test thread-safe cache access."""
    cache = fresh_log_cache
    results = []
    errors = []

    def read_logs_concurrently(thread_id):
        try:
            for i in range(10):
                log_names = cache.get_log_names()
                if log_names:
                    content = cache.read_log(log_names[0])
                    results.append((thread_id, len(content)))
                time.sleep(0.01)  # Yield to other threads
        except Exception as e:
            errors.append((thread_id, str(e)))

    # Test with multiple threads
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(read_logs_concurrently, i)
            for i in range(5)
        ]

        # Wait for completion
        for future in futures:
            future.result(timeout=10)

    # Verify no errors occurred
    assert len(errors) == 0, f"Thread safety errors: {errors}"
    assert len(results) == 50  # 5 threads × 10 iterations
```

### ✅ CORRECT: Testing from_cache Factory

```python
def test_from_cache_factory():
    """Test from_cache factory method isolation."""
    # Create test cache data
    cache_data = {
        "log1.log": b"Content 1\nLine 2\n",
        "log2.log": b"Content 2\nLine 2\n"
    }

    # Create cache from existing data
    cache = ThreadSafeLogCache.from_cache(cache_data)

    try:
        # Verify cache content
        log_names = cache.get_log_names()
        assert "log1.log" in log_names
        assert "log2.log" in log_names

        content = cache.read_log("log1.log")
        assert "Content 1" in content[0]

        # Modify original data - should not affect cache
        cache_data["log3.log"] = b"Content 3\n"
        updated_names = cache.get_log_names()
        assert "log3.log" not in updated_names

    finally:
        cache.close()
        cache.cache.clear()
```

### ❌ WRONG: Reusing Cache Across Tests

```python
# BAD - Cache created at module level
cache = ThreadSafeLogCache([Path("test.log")])

def test_one():
    content = cache.read_log("test.log")  # Pollutes cache
    # Modify cache state

def test_two():
    # Uses polluted cache from test_one!
    content = cache.read_log("test.log")
```

### ❌ WRONG: Not Cleaning Up Resources

```python
def test_without_cleanup():
    cache = ThreadSafeLogCache([Path("test.log")])
    # Test code
    # No cleanup - cache and locks persist!
```

### ❌ WRONG: Shared Test Data

```python
def test_shared_data():
    cache1 = ThreadSafeLogCache([Path("shared.log")])
    cache2 = ThreadSafeLogCache([Path("shared.log")])

    # Both caches read same file - can cause conflicts
    content1 = cache1.read_log("shared.log")
    content2 = cache2.read_log("shared.log")
    # File locking issues possible
```

## Parallel Testing Considerations

### Using pytest-xdist

```python
import pytest
import os
from pathlib import Path

@pytest.fixture
def isolated_log_cache(tmp_path):
    """Create worker-isolated cache for parallel testing."""
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')

    # Create worker-specific directory
    worker_dir = tmp_path / f"worker_{worker_id}"
    worker_dir.mkdir(exist_ok=True)

    # Create test files
    log_files = []
    for i in range(3):
        log_file = worker_dir / f"test_{worker_id}_{i}.log"
        log_file.write_text(f"Worker {worker_id} Log {i}\n")
        log_files.append(log_file)

    cache = ThreadSafeLogCache(log_files)

    yield cache

    # Cleanup
    cache.close()
    cache.cache.clear()


@pytest.mark.parametrize("log_index", [0, 1, 2])
def test_parallel_safe_cache(isolated_log_cache, log_index):
    """Test that works safely in parallel with parameters."""
    cache = isolated_log_cache
    log_names = cache.get_log_names()

    if log_index < len(log_names):
        content = cache.read_log(log_names[log_index])
        assert len(content) > 0
```

### Thread-Safe Test Fixtures

```python
import threading

@pytest.fixture
def thread_safe_cache_fixture():
    """Thread-safe cache fixture for concurrent tests."""
    local_storage = threading.local()

    def get_cache():
        if not hasattr(local_storage, 'cache'):
            # Create per-thread cache
            test_files = [Path(f"thread_{threading.current_thread().ident}.log")]
            local_storage.cache = ThreadSafeLogCache(test_files)
        return local_storage.cache

    yield get_cache

    # Cleanup all thread-local caches
    # (Complex cleanup would need thread tracking)
```

## Common Pitfalls and Solutions

### 1. Cache Size Growth

**Problem**: Cache grows unbounded
```python
def test_cache_growth():
    cache = ThreadSafeLogCache([])
    for i in range(1000):
        cache.cache[f"log_{i}.log"] = b"Large content" * 1000
    # Memory usage explodes!
```

**Solution**: Limit cache size or clear periodically
```python
def test_with_cache_limit():
    cache = ThreadSafeLogCache([])

    max_cache_size = 100
    for i in range(1000):
        if len(cache.cache) >= max_cache_size:
            cache.cache.clear()  # Clear when limit reached

        cache.cache[f"log_{i}.log"] = b"Content"
```

### 2. Deadlocks in Parallel Tests

**Problem**: RLock deadlocks
```python
def test_potential_deadlock():
    cache = ThreadSafeLogCache([Path("test.log")])

    def nested_access():
        with cache.lock:
            # Some operation
            cache.read_log("test.log")  # Acquires lock again

    # Multiple threads calling this can deadlock
```

**Solution**: Avoid nested locking or use timeouts
```python
def test_with_timeout():
    cache = ThreadSafeLogCache([Path("test.log")])

    def safe_access():
        if cache.lock.acquire(timeout=5.0):
            try:
                # Safe operation
                pass
            finally:
                cache.lock.release()
        else:
            pytest.fail("Lock timeout - possible deadlock")
```

### 3. File Handle Leaks

**Problem**: Files not closed properly
```python
def test_file_leak():
    for i in range(1000):
        cache = ThreadSafeLogCache([Path(f"test_{i}.log")])
        # Cache reads file but doesn't close handle
        # Eventually hits file handle limit
```

**Solution**: Explicit cleanup
```python
def test_with_cleanup():
    cache = ThreadSafeLogCache([Path("test.log")])
    try:
        # Your test code
        pass
    finally:
        cache.close()  # Ensure cleanup
        cache.cache.clear()
```

### 4. Cache Corruption

**Problem**: Concurrent modifications
```python
def test_cache_corruption():
    cache = ThreadSafeLogCache([])

    def modify_cache():
        cache.cache["test.log"] = b"Modified"

    # Multiple threads modifying - race condition
    threads = [threading.Thread(target=modify_cache) for _ in range(10)]
    for t in threads:
        t.start()
    # Cache state undefined!
```

**Solution**: Use proper synchronization
```python
def test_synchronized_access():
    cache = ThreadSafeLogCache([])

    def safe_modify_cache(content):
        with cache.lock:
            cache.cache["test.log"] = content.encode()

    # Properly synchronized access
    threads = [
        threading.Thread(target=safe_modify_cache, args=(f"Content {i}",))
        for i in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Cache state is well-defined
```

## Best Practices

1. **Create fresh instances per test**
   - Never reuse cache instances across tests
   - Use fixtures to create isolated caches

2. **Always clean up resources**
   - Call close() method explicitly
   - Clear cache dictionary after tests
   - Use try/finally blocks

3. **Mock for unit tests**
   - Unit tests should mock ThreadSafeLogCache
   - Only integration tests need real caches

4. **Use temporary files**
   - Create test-specific log files
   - Use tmp_path fixture for file isolation

5. **Test thread safety properly**
   - Use ThreadPoolExecutor for concurrent tests
   - Include timeout mechanisms
   - Test with realistic concurrency levels

## Complete Test Example

```python
import pytest
import threading
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch
from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache


class TestThreadSafeLogCacheIsolation:
    """Demonstrate proper ThreadSafeLogCache test isolation."""

    @pytest.fixture
    def test_log_files(self, tmp_path):
        """Create test log files."""
        log_files = []
        for i in range(3):
            log_file = tmp_path / f"test_log_{i}.log"
            content = f"=== Test Log {i} ===\n"
            content += f"Line 1 of log {i}\n"
            content += f"Line 2 of log {i}\n"
            log_file.write_text(content)
            log_files.append(log_file)
        return log_files

    @pytest.fixture
    def isolated_cache(self, test_log_files):
        """Create isolated cache for each test."""
        cache = ThreadSafeLogCache(test_log_files)
        yield cache
        # Cleanup
        cache.close()
        cache.cache.clear()

    def test_basic_cache_operations(self, isolated_cache):
        """Test basic cache operations."""
        cache = isolated_cache

        # Test log names
        log_names = cache.get_log_names()
        assert len(log_names) == 3
        assert "test_log_0.log" in log_names

        # Test reading log
        content = cache.read_log("test_log_0.log")
        assert "Test Log 0" in content[0]
        assert len(content) == 3  # 3 lines

    def test_from_cache_factory(self):
        """Test from_cache factory method."""
        cache_data = {
            "mock1.log": b"Mock content 1\nLine 2\n",
            "mock2.log": b"Mock content 2\nLine 2\n"
        }

        cache = ThreadSafeLogCache.from_cache(cache_data)
        try:
            log_names = cache.get_log_names()
            assert "mock1.log" in log_names
            assert "mock2.log" in log_names

            content = cache.read_log("mock1.log")
            assert "Mock content 1" in content[0]
        finally:
            cache.close()
            cache.cache.clear()

    def test_thread_safety(self, isolated_cache):
        """Test thread-safe operations."""
        cache = isolated_cache
        results = []
        errors = []

        def concurrent_reader(thread_id):
            try:
                for _ in range(10):
                    log_names = cache.get_log_names()
                    if log_names:
                        content = cache.read_log(log_names[0])
                        results.append((thread_id, len(content)))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Run concurrent readers
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(concurrent_reader, i)
                for i in range(3)
            ]
            for future in futures:
                future.result(timeout=10)

        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 30  # 3 threads × 10 iterations

    def test_with_mock_cache(self):
        """Test with mocked cache."""
        mock_cache = MagicMock(spec=ThreadSafeLogCache)
        mock_cache.get_log_names.return_value = ["test.log"]
        mock_cache.read_log.return_value = ["Mocked content"]

        # Test code using mock
        log_names = mock_cache.get_log_names()
        assert log_names == ["test.log"]

        content = mock_cache.read_log("test.log")
        assert content == ["Mocked content"]

    def test_cache_isolation(self, test_log_files):
        """Test that caches are properly isolated."""
        # Create two separate caches
        cache1 = ThreadSafeLogCache(test_log_files)
        cache2 = ThreadSafeLogCache(test_log_files)

        try:
            # Modify cache1
            cache1.cache["new_entry"] = b"Cache 1 data"

            # Verify cache2 is unaffected
            assert "new_entry" not in cache2.cache

            # Both should still read log files correctly
            content1 = cache1.read_log("test_log_0.log")
            content2 = cache2.read_log("test_log_0.log")
            assert content1 == content2

        finally:
            cache1.close()
            cache2.close()
            cache1.cache.clear()
            cache2.cache.clear()
```

## Debugging Tips

### 1. Check Cache State

```python
def debug_cache_state(cache: ThreadSafeLogCache):
    """Debug current cache state."""
    print(f"Cache size: {len(cache.cache)}")
    print(f"Log names: {cache.get_log_names()}")
    print(f"Lock acquired: {cache.lock._count if hasattr(cache.lock, '_count') else 'Unknown'}")

    # Check memory usage
    import sys
    cache_size = sys.getsizeof(cache.cache)
    print(f"Cache memory: {cache_size} bytes")
```

### 2. Detect Lock Issues

```python
import time

def detect_lock_issues(cache: ThreadSafeLogCache):
    """Detect potential lock issues."""
    # Try to acquire lock with timeout
    acquired = cache.lock.acquire(timeout=1.0)
    if acquired:
        try:
            print("Lock acquired successfully")
        finally:
            cache.lock.release()
    else:
        print("WARNING: Lock acquisition timed out!")


def test_lock_health(isolated_cache):
    """Test lock health."""
    cache = isolated_cache

    # Check that lock works
    with cache.lock:
        # Should work without timeout
        pass

    # Verify lock is released
    detect_lock_issues(cache)
```

### 3. Monitor Resource Usage

```python
import psutil
import os

def monitor_resources():
    """Monitor system resources during tests."""
    process = psutil.Process(os.getpid())

    print(f"Open files: {len(process.open_files())}")
    print(f"Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
    print(f"Threads: {process.num_threads()}")


@pytest.fixture(autouse=True)
def resource_monitor():
    """Monitor resources before and after tests."""
    print("Before test:")
    monitor_resources()

    yield

    print("After test:")
    monitor_resources()
```

## See Also

- [Testing AsyncBridge Guide](testing_async_bridge.md)
- [Testing Database Pools Guide](testing_database_pools.md)
- [Testing MessageHandler Guide](testing_message_handler.md)
- [Test Pollution Prevention Guide](test_pollution_guide.md)
