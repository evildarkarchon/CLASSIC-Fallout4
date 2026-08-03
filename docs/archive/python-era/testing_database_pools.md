# Testing Database Pools Guide

## Overview

CLASSIC uses two database connection pools for FormID lookups:
- **AsyncDatabasePool** - For async operations in the scan pipeline
- **SyncDatabasePool** - Singleton for synchronous database access

Both maintain persistent connections and caches that cause test pollution, resource leaks, and failures in parallel test execution.

## The Problem

### Symptoms of Database Pool Test Pollution

1. **Connection Leaks**
   - SQLite database locks persist across tests
   - "Database is locked" errors in subsequent tests
   - File handles remain open after tests complete
   - Connection count grows with each test

2. **Cache Pollution**
   - FormID query results cached from previous tests
   - Incorrect data returned due to stale cache
   - Memory usage grows unbounded
   - Cache hits for queries that should miss

3. **Singleton State Persistence (SyncDatabasePool)**
   - Single global instance shared across all tests
   - Connection pool never resets between tests
   - Thread locks can deadlock in parallel execution

4. **Async Resource Leaks (AsyncDatabasePool)**
   - Connections not properly closed
   - Event loop warnings about unclosed resources
   - AsyncIO tasks left running after tests
   - Context manager cleanup failures

## Root Causes

### 1. SyncDatabasePool Singleton

```python
# In ClassicLib/ScanLog/Util.py
class SyncDatabasePool:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SyncDatabasePool":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
```

### 2. AsyncDatabasePool Connection Management

```python
# In ClassicLib/ScanLog/AsyncUtil.py
class AsyncDatabasePool:
    def __init__(self):
        self.connections: dict[Path, aiosqlite.Connection] = {}
        self.query_cache: dict[str, str] = {}
        self._lock = asyncio.Lock()
```

### 3. Persistent Query Caches

Both pools maintain query caches that persist across tests:
```python
# Never cleared automatically
self.query_cache[cache_key] = result
```

## Testing Patterns

### ✅ CORRECT: Async Pool Isolation

```python
import pytest
from unittest.mock import patch, AsyncMock
from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool

@pytest.mark.asyncio
async def test_with_isolated_async_pool():
    """Test with properly isolated AsyncDatabasePool."""
    # Create new pool for this test
    pool = AsyncDatabasePool()

    try:
        # Initialize with test databases
        with patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", []):
            await pool.initialize()

        # Your test code
        result = await pool.get_entry("test_key", "test_form_id")

    finally:
        # Always cleanup
        await pool.close()


@pytest.mark.asyncio
async def test_with_mocked_async_pool():
    """Test with fully mocked AsyncDatabasePool."""
    mock_pool = AsyncMock(spec=AsyncDatabasePool)
    mock_pool.get_entry.return_value = "Test Entry"
    mock_pool.get_entries_batch.return_value = {"id1": "Entry1"}

    # Use mock in your code
    with patch("ClassicLib.ScanLog.AsyncUtil.AsyncDatabasePool", return_value=mock_pool):
        # Your test code
        pass

    # Verify cleanup was called
    mock_pool.close.assert_called_once()
```

### ✅ CORRECT: Sync Pool Reset

```python
import pytest
from ClassicLib.ScanLog.Util import SyncDatabasePool

@pytest.fixture(autouse=True)
def reset_sync_database_pool():
    """Reset SyncDatabasePool singleton for each test."""
    # Clear singleton instance
    SyncDatabasePool._instance = None

    yield

    # Cleanup after test
    if SyncDatabasePool._instance:
        SyncDatabasePool._instance.close_all()
    SyncDatabasePool._instance = None


def test_with_sync_pool(reset_sync_database_pool):
    """Test using SyncDatabasePool with proper isolation."""
    pool = SyncDatabasePool.get_instance()

    # Your test code
    conn = pool.get_connection(Path("test.db"))

    # Connections will be cleaned up by fixture
```

### ✅ CORRECT: Testing with Temp Databases

```python
import tempfile
from pathlib import Path
import pytest

@pytest.fixture
def temp_database():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp:
        db_path = Path(temp.name)

    # Create test database schema
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS FormIDs (
            FormID TEXT PRIMARY KEY,
            Name TEXT
        )
    """)
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_with_temp_database(temp_database):
    """Test with temporary database."""
    with patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", [temp_database]):
        pool = AsyncDatabasePool()
        await pool.initialize()

        try:
            # Test code with real database
            result = await pool.get_entry("FormIDs", "12345678")
            assert result is None  # Empty database
        finally:
            await pool.close()
```

### ❌ WRONG: Shared Pool Instance

```python
# BAD - Pool created at module level
pool = AsyncDatabasePool()

@pytest.mark.asyncio
async def test_one():
    await pool.initialize()  # Pollutes module-level pool
    # Test code

@pytest.mark.asyncio
async def test_two():
    # Uses polluted pool from test_one!
    result = await pool.get_entry("key", "id")
```

### ❌ WRONG: No Cleanup

```python
@pytest.mark.asyncio
async def test_without_cleanup():
    pool = AsyncDatabasePool()
    await pool.initialize()

    # Test code

    # No cleanup - connections leak!
```

### ❌ WRONG: Not Resetting Singleton

```python
def test_sync_pool():
    pool = SyncDatabasePool.get_instance()
    # Modifies singleton state
    conn = pool.get_connection(Path("test.db"))

def test_another():
    # Gets same polluted singleton!
    pool = SyncDatabasePool.get_instance()
```

## Parallel Testing Considerations

### AsyncDatabasePool with pytest-xdist

```python
import pytest
import asyncio
import os

@pytest.fixture
async def isolated_async_pool():
    """Create isolated pool for parallel testing."""
    # Use worker-specific cache
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')

    pool = AsyncDatabasePool()
    # Override cache to prevent conflicts
    pool.query_cache = {}  # Fresh cache per test

    with patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", []):
        await pool.initialize()

    yield pool

    await pool.close()


@pytest.mark.asyncio
async def test_parallel_safe(isolated_async_pool):
    """Test that works safely in parallel."""
    pool = isolated_async_pool
    # Your test code
```

### SyncDatabasePool Thread Safety

```python
import threading
import pytest

@pytest.fixture
def thread_safe_sync_pool():
    """Ensure thread-safe SyncDatabasePool testing."""
    # Reset singleton
    SyncDatabasePool._instance = None

    # Create new instance with thread-local storage
    original_get_instance = SyncDatabasePool.get_instance

    local_pools = threading.local()

    def get_thread_local_instance():
        if not hasattr(local_pools, 'pool'):
            local_pools.pool = SyncDatabasePool()
        return local_pools.pool

    SyncDatabasePool.get_instance = get_thread_local_instance

    yield

    # Restore original
    SyncDatabasePool.get_instance = original_get_instance
    SyncDatabasePool._instance = None
```

## Common Pitfalls and Solutions

### 1. Unclosed Async Connections

**Problem**: Event loop warnings
```python
async def test_async_pool():
    pool = AsyncDatabasePool()
    await pool.initialize()
    # Test ends without closing
    # WARNING: Unclosed connection
```

**Solution**: Always use try/finally or context manager
```python
async def test_async_pool():
    pool = AsyncDatabasePool()
    await pool.initialize()
    try:
        # Your test code
        pass
    finally:
        await pool.close()

# Or use context manager
async def test_with_context_manager():
    async with AsyncDatabasePool() as pool:
        # Automatically cleaned up
        pass
```

### 2. Database Lock Errors

**Problem**: SQLite database locked
```python
def test_database_locked():
    pool1 = SyncDatabasePool.get_instance()
    conn1 = pool1.get_connection(Path("test.db"))
    # Holds lock

    pool2 = SyncDatabasePool.get_instance()  # Same instance!
    conn2 = pool2.get_connection(Path("test.db"))
    # Database is locked!
```

**Solution**: Reset singleton between tests
```python
@pytest.fixture(autouse=True)
def reset_pool():
    SyncDatabasePool._instance = None
    yield
    if SyncDatabasePool._instance:
        SyncDatabasePool._instance.close_all()
    SyncDatabasePool._instance = None
```

### 3. Cache Pollution

**Problem**: Stale cache data
```python
async def test_cache_pollution():
    pool = AsyncDatabasePool()
    # First query caches result
    result1 = await pool.get_entry("key", "id")

    # Modify database directly
    # ...

    # Still returns cached result!
    result2 = await pool.get_entry("key", "id")
```

**Solution**: Clear cache in tests
```python
async def test_without_cache():
    pool = AsyncDatabasePool()
    pool.query_cache.clear()  # Clear cache

    # Or disable caching for tests
    pool.query_cache = {}  # Fresh cache
```

### 4. Connection Pool Growth

**Problem**: Connections accumulate
```python
def test_connection_growth():
    pool = SyncDatabasePool.get_instance()
    for i in range(100):
        conn = pool.get_connection(Path(f"db_{i}.db"))
    # 100 connections remain open!
```

**Solution**: Limit connections or clean up
```python
def test_with_connection_limit():
    pool = SyncDatabasePool.get_instance()
    pool.max_connections = 5  # Limit

    # Or clean up periodically
    for i in range(100):
        if i % 10 == 0:
            pool.close_all()
        conn = pool.get_connection(Path("test.db"))
```

## Best Practices

1. **Always clean up resources**
   - Use try/finally blocks
   - Implement context managers
   - Call close() methods explicitly

2. **Reset singletons in fixtures**
   - Clear `_instance` before and after tests
   - Use autouse fixtures for automatic cleanup

3. **Mock when possible**
   - Unit tests should mock database pools
   - Only integration tests need real databases

4. **Use temporary databases**
   - Create fresh databases for each test
   - Use tempfile for database files

5. **Clear caches explicitly**
   - Reset query_cache between tests
   - Don't rely on cache in tests

## Complete Test Example

```python
import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool
from ClassicLib.ScanLog.Util import SyncDatabasePool


class TestDatabasePoolsIsolation:
    """Demonstrate proper database pool test isolation."""

    @pytest.fixture(autouse=True)
    def reset_pools(self):
        """Reset all database pools."""
        # Reset sync pool
        SyncDatabasePool._instance = None

        yield

        # Cleanup
        if SyncDatabasePool._instance:
            SyncDatabasePool._instance.close_all()
        SyncDatabasePool._instance = None

    @pytest.mark.asyncio
    async def test_async_pool_isolation(self):
        """Test AsyncDatabasePool in isolation."""
        pool = AsyncDatabasePool()

        with patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", []):
            await pool.initialize()

            try:
                # Test with empty pool
                result = await pool.get_entry("test", "123")
                assert result is None
            finally:
                await pool.close()

    def test_sync_pool_isolation(self):
        """Test SyncDatabasePool in isolation."""
        with tempfile.NamedTemporaryFile(suffix=".db") as temp:
            db_path = Path(temp.name)

            pool = SyncDatabasePool.get_instance()
            conn = pool.get_connection(db_path)

            # Verify connection works
            cursor = conn.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1

    @pytest.mark.asyncio
    async def test_async_pool_mock(self):
        """Test with mocked AsyncDatabasePool."""
        mock_pool = AsyncMock(spec=AsyncDatabasePool)
        mock_pool.get_entry.return_value = "Mocked Entry"

        with patch("ClassicLib.ScanLog.OrchestratorCore.AsyncDatabasePool", return_value=mock_pool):
            # Your test code using the mock
            result = await mock_pool.get_entry("test", "123")
            assert result == "Mocked Entry"

        mock_pool.close.assert_not_called()  # Verify mock behavior

    def test_sync_pool_mock(self):
        """Test with mocked SyncDatabasePool."""
        mock_instance = MagicMock(spec=SyncDatabasePool)
        mock_conn = MagicMock()
        mock_instance.get_connection.return_value = mock_conn

        with patch.object(SyncDatabasePool, 'get_instance', return_value=mock_instance):
            pool = SyncDatabasePool.get_instance()
            conn = pool.get_connection(Path("test.db"))

            assert conn == mock_conn
            mock_instance.get_connection.assert_called_once()
```

## Debugging Tips

### 1. Check Pool State

```python
def debug_pool_state():
    """Debug current pool states."""
    # Check sync pool
    if SyncDatabasePool._instance:
        pool = SyncDatabasePool._instance
        print(f"SyncPool connections: {len(pool._connections)}")
    else:
        print("No SyncDatabasePool instance")

    # Check async pool (if accessible)
    # Async pools are usually local to functions


async def debug_async_pool(pool: AsyncDatabasePool):
    """Debug AsyncDatabasePool state."""
    print(f"Connections: {len(pool.connections)}")
    print(f"Cache size: {len(pool.query_cache)}")
```

### 2. Force Cleanup

```python
def force_cleanup_pools():
    """Force cleanup of all pools."""
    # Sync pool
    if SyncDatabasePool._instance:
        SyncDatabasePool._instance.close_all()
    SyncDatabasePool._instance = None

    # Async pools must be closed in their context


async def force_async_cleanup(pool: AsyncDatabasePool):
    """Force cleanup of async pool."""
    await pool.close()
    pool.connections.clear()
    pool.query_cache.clear()
```

### 3. Detect Pool Pollution

```python
@pytest.fixture(autouse=True)
def detect_pool_pollution():
    """Detect database pool pollution."""
    # Check for existing sync pool
    if SyncDatabasePool._instance is not None:
        pytest.fail("SyncDatabasePool pollution detected!")

    yield

    # Check for leaks after test
    if SyncDatabasePool._instance and len(SyncDatabasePool._instance._connections) > 0:
        pytest.fail(f"Database connections leaked: {len(SyncDatabasePool._instance._connections)}")
```

## See Also

- [Testing AsyncBridge Guide](async_bridge.md)
- [Testing GlobalRegistry Guide](global_registry.md)
- [Testing MessageHandler Guide](message_handler.md)
- [Test Pollution Prevention Guide](test_pollution_guide.md)
