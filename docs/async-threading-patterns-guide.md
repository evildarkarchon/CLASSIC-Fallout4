# Advanced Async & Threading Patterns Guide

## Overview

The CLASSIC codebase implements production-grade asynchronous and threading patterns that represent best practices in Python concurrent programming. This guide documents these advanced patterns to help maintainers and contributors understand and extend the codebase effectively.

## Table of Contents

1. [Async-First Architecture](#async-first-architecture)
2. [Dynamic Concurrency Management](#dynamic-concurrency-management)
3. [Memory-Mapped File I/O](#memory-mapped-file-io)
4. [Thread-Safe Singleton Pattern](#thread-safe-singleton-pattern)
5. [Sync Adapter Pattern](#sync-adapter-pattern)
6. [Batching and Streaming](#batching-and-streaming)
7. [Resource Lifecycle Management](#resource-lifecycle-management)
8. [Error Handling in Async Contexts](#error-handling-in-async-contexts)
9. [Performance Monitoring Integration](#performance-monitoring-integration)
10. [Best Practices](#best-practices)

## <a name="async-first-architecture"></a>Async-First Architecture

### Philosophy

The CLASSIC codebase follows an **async-first design pattern** where:
- Core implementations are async by default
- Sync adapters provide backwards compatibility
- No feature flags needed - async is always used internally
- All I/O operations are non-blocking

### Implementation Example

```python
# Core async implementation (ScanGameCore.py)
class ScanGameCore:
    def __init__(self):
        self._semaphore = None
        self._max_concurrent = self._get_max_concurrent()
    
    async def scan_files(self, paths: list[Path]) -> list[ScanResult]:
        """Core async implementation."""
        async with self._get_semaphore():
            tasks = [self._scan_single_file(path) for path in paths]
            return await asyncio.gather(*tasks, return_exceptions=True)

# Sync adapter for backwards compatibility
class ClassicScanGame:
    def __init__(self):
        self.core = ScanGameCore()
    
    def scan_files(self, paths: list[Path]) -> list[ScanResult]:
        """Sync wrapper using asyncio.run()."""
        return asyncio.run(self.core.scan_files(paths))
```

## <a name="dynamic-concurrency-management"></a>Dynamic Concurrency Management

### Semaphore-Based Concurrency Control

The codebase implements dynamic semaphore limits that adapt to system capabilities:

```python
class ScanGameCore:
    def _get_max_concurrent(self) -> int:
        """Calculate optimal concurrency based on system resources."""
        cpu_count = os.cpu_count() or 4
        
        # Adjust based on available memory
        import psutil
        available_memory_gb = psutil.virtual_memory().available / (1024**3)
        
        if available_memory_gb < 2:
            return min(cpu_count, 4)  # Limited concurrency on low memory
        elif available_memory_gb < 4:
            return min(cpu_count * 2, 8)
        else:
            return min(cpu_count * 4, 16)  # High concurrency on ample memory
    
    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore with dynamic limits."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
        return self._semaphore
    
    async def process_batch(self, items: list[Any]) -> list[Result]:
        """Process items with controlled concurrency."""
        async with self._get_semaphore():
            # Ensures only N operations run concurrently
            tasks = [self._process_item(item) for item in items]
            return await asyncio.gather(*tasks)
```

### Benefits
- Prevents resource exhaustion
- Adapts to system capabilities
- Maintains responsiveness under load
- Avoids overwhelming I/O subsystems

## <a name="memory-mapped-file-io"></a>Memory-Mapped File I/O

### Large File Optimization

For files larger than 10MB, the codebase uses memory-mapped I/O for efficient processing:

```python
import mmap
from pathlib import Path

class FileIOCore:
    MMAP_THRESHOLD = 10 * 1024 * 1024  # 10MB
    
    async def read_large_file(self, path: Path) -> str:
        """Read large files using memory mapping."""
        file_size = path.stat().st_size
        
        if file_size > self.MMAP_THRESHOLD:
            return await self._read_with_mmap(path)
        else:
            return await self._read_standard(path)
    
    async def _read_with_mmap(self, path: Path) -> str:
        """Memory-mapped reading for large files."""
        def _mmap_read():
            with open(path, 'r+b') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped:
                    # Process in chunks to avoid loading entire file
                    chunk_size = 1024 * 1024  # 1MB chunks
                    chunks = []
                    
                    for i in range(0, len(mmapped), chunk_size):
                        chunk = mmapped[i:i + chunk_size]
                        chunks.append(chunk.decode('utf-8', errors='ignore'))
                    
                    return ''.join(chunks)
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _mmap_read)
```

### Benefits
- Reduces memory footprint for large files
- Enables efficient random access
- OS handles caching and paging
- Faster than traditional file reading for large files

## <a name="thread-safe-singleton-pattern"></a>Thread-Safe Singleton Pattern

### AsyncBridge Implementation

The AsyncBridge provides thread-safe async execution in sync contexts:

```python
import threading
import asyncio
from typing import Optional, Any

class AsyncBridge:
    """Thread-safe singleton for managing async operations in sync contexts."""
    
    _instance: Optional['AsyncBridge'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'AsyncBridge':
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the async bridge."""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
    
    @classmethod
    def get_instance(cls) -> 'AsyncBridge':
        """Get or create the singleton instance."""
        return cls()
    
    def run_async(self, coro) -> Any:
        """Run async coroutine in sync context without creating new loop."""
        # Check if we're already in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in async context, create task
            future = asyncio.ensure_future(coro)
            return asyncio.run_until_complete(future)
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            return asyncio.run(coro)
```

### Benefits
- Prevents multiple event loop creation
- Thread-safe singleton access
- Handles nested async calls gracefully
- Efficient resource utilization

## <a name="sync-adapter-pattern"></a>Sync Adapter Pattern

### Providing Backwards Compatibility

The codebase provides sync wrappers for all async operations:

```python
# FileIOCore.py
class FileIOCore:
    """Core async implementation."""
    
    async def read_file(self, path: Path, encoding: str = 'utf-8') -> str:
        """Async file reading."""
        async with aiofiles.open(path, 'r', encoding=encoding) as f:
            return await f.read()
    
    async def write_file(self, path: Path, content: str) -> None:
        """Async file writing."""
        async with aiofiles.open(path, 'w', encoding='utf-8') as f:
            await f.write(content)

# Sync adapters for backwards compatibility
def read_file_sync(path: Path, encoding: str = 'utf-8') -> str:
    """Sync wrapper for async read_file."""
    core = FileIOCore()
    return asyncio.run(core.read_file(path, encoding))

def write_file_sync(path: Path, content: str) -> None:
    """Sync wrapper for async write_file."""
    core = FileIOCore()
    asyncio.run(core.write_file(path, content))
```

### Usage Guidelines
- Always implement async version first
- Provide sync wrapper using `asyncio.run()`
- Document both versions clearly
- Prefer async in new code

## <a name="batching-and-streaming"></a>Batching and Streaming

### Batch Processing Pattern

Efficient processing of multiple items:

```python
class YamlSettingsCache:
    async def batch_load_settings(
        self, 
        requests: list[tuple[type, Enum, str]]
    ) -> list[Any]:
        """Load multiple settings in a single operation."""
        # Group by file to minimize I/O
        grouped = defaultdict(list)
        for type_, source, key in requests:
            grouped[source].append((type_, key))
        
        results = []
        async with asyncio.TaskGroup() as tg:  # Python 3.11+
            for source, items in grouped.items():
                task = tg.create_task(self._load_source(source, items))
                results.append(task)
        
        # Flatten results in original order
        return [await task for task in results]
```

### Streaming Large Data

Process large datasets without loading everything into memory:

```python
class LogProcessor:
    async def process_logs_streaming(self, log_dir: Path):
        """Stream process logs without loading all into memory."""
        async for log_file in self._scan_directory_async(log_dir):
            async with aiofiles.open(log_file, 'r') as f:
                line_buffer = []
                async for line in f:
                    line_buffer.append(line)
                    
                    # Process in chunks
                    if len(line_buffer) >= 1000:
                        await self._process_chunk(line_buffer)
                        line_buffer = []
                
                # Process remaining lines
                if line_buffer:
                    await self._process_chunk(line_buffer)
```

## <a name="resource-lifecycle-management"></a>Resource Lifecycle Management

### Context Managers for Resource Safety

```python
class DatabasePool:
    def __init__(self, db_path: Path, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool: Optional[aiosqlite.Pool] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._pool = await aiosqlite.create_pool(
            self.db_path,
            maxsize=self.max_connections
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def execute(self, query: str, params: tuple = ()) -> list:
        """Execute query using connection from pool."""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()
```

### Cleanup Patterns

```python
class ResourceManager:
    def __init__(self):
        self._resources = []
        self._cleanup_tasks = []
    
    async def cleanup(self):
        """Cleanup all resources gracefully."""
        # Cancel pending tasks
        for task in self._cleanup_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for cancellation with timeout
        if self._cleanup_tasks:
            await asyncio.wait(
                self._cleanup_tasks,
                timeout=5.0,
                return_when=asyncio.ALL_COMPLETED
            )
        
        # Close resources
        for resource in self._resources:
            if hasattr(resource, 'close'):
                await resource.close()
```

## <a name="error-handling-in-async-contexts"></a>Error Handling in Async Contexts

### Comprehensive Exception Management

```python
class AsyncErrorHandler:
    @staticmethod
    async def safe_gather(*tasks, return_exceptions=True):
        """Gather with proper error handling."""
        results = await asyncio.gather(*tasks, return_exceptions=return_exceptions)
        
        errors = []
        valid_results = []
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(result)
                # Log the error with context
                logger.error(f"Task failed: {result}", exc_info=result)
            else:
                valid_results.append(result)
        
        if errors and not return_exceptions:
            # Raise aggregated exception
            raise ExceptionGroup("Multiple tasks failed", errors)
        
        return valid_results, errors
    
    @staticmethod
    def retry_async(max_attempts=3, delay=1.0, backoff=2.0):
        """Decorator for async retry logic."""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                attempt = 0
                current_delay = delay
                
                while attempt < max_attempts:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        attempt += 1
                        if attempt >= max_attempts:
                            raise
                        
                        logger.warning(
                            f"Attempt {attempt} failed: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            return wrapper
        return decorator
```

## <a name="performance-monitoring-integration"></a>Performance Monitoring Integration

### Async-Aware Performance Tracking

```python
from contextlib import asynccontextmanager
import time

class AsyncPerformanceMonitor:
    @staticmethod
    @asynccontextmanager
    async def timed_operation(operation_name: str):
        """Async context manager for timing operations."""
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start_time
            logger.info(f"{operation_name} took {elapsed:.3f}s")
            
            # Store metrics for analysis
            await MetricsCollector.record(operation_name, elapsed)
    
    @staticmethod
    def async_timed(func):
        """Decorator for timing async functions."""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            async with AsyncPerformanceMonitor.timed_operation(func.__name__):
                return await func(*args, **kwargs)
        return wrapper
```

### Usage Example

```python
class ScanGameCore:
    @AsyncPerformanceMonitor.async_timed
    async def scan_directory(self, path: Path) -> ScanResults:
        """Scan directory with automatic performance tracking."""
        async with AsyncPerformanceMonitor.timed_operation("file_enumeration"):
            files = await self._enumerate_files(path)
        
        async with AsyncPerformanceMonitor.timed_operation("file_processing"):
            results = await self._process_files(files)
        
        return results
```

## <a name="best-practices"></a>Best Practices

### <a name="always-use-async-io"></a>1. Always Use Async I/O

```python
# ❌ Bad: Blocking I/O in async function
async def bad_example():
    with open('file.txt') as f:  # Blocks the event loop!
        return f.read()

# ✅ Good: Non-blocking async I/O
async def good_example():
    async with aiofiles.open('file.txt') as f:
        return await f.read()
```

### <a name="avoid-creating-event-loops"></a>2. Avoid Creating Event Loops

```python
# ❌ Bad: Creating new event loop
def bad_sync_wrapper(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ✅ Good: Use asyncio.run() or AsyncBridge
def good_sync_wrapper(coro):
    return asyncio.run(coro)  # Or AsyncBridge.get_instance().run_async(coro)
```

### <a name="proper-task-cancellation"></a>3. Proper Task Cancellation

```python
class TaskManager:
    async def run_with_timeout(self, coro, timeout: float):
        """Run coroutine with timeout and proper cleanup."""
        task = asyncio.create_task(coro)
        
        try:
            return await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            # Ensure task is cancelled
            task.cancel()
            
            # Wait for cancellation to complete
            try:
                await task
            except asyncio.CancelledError:
                pass  # Expected
            
            raise TimeoutError(f"Operation exceeded {timeout}s timeout")
```

### <a name="use-taskgroup"></a>4. Use TaskGroup for Multiple Operations (Python 3.11+)

```python
# ✅ Modern approach with automatic error handling
async def process_multiple():
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(operation1())
        task2 = tg.create_task(operation2())
        task3 = tg.create_task(operation3())
    
    # All tasks completed successfully if we reach here
    return task1.result(), task2.result(), task3.result()
```

### <a name="thread-safety-mixed"></a>5. Thread Safety in Mixed Environments

```python
class ThreadSafeAsyncExecutor:
    def __init__(self):
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def execute(self, coro):
        """Execute async code from any thread."""
        with self._lock:
            # Check if we need to create event loop
            if self._loop is None or not self._loop.is_running():
                return asyncio.run(coro)
            else:
                # Schedule in existing loop
                future = asyncio.run_coroutine_threadsafe(coro, self._loop)
                return future.result()
```

### <a name="resource-pooling"></a>6. Resource Pooling

```python
class ConnectionPool:
    def __init__(self, factory, max_size=10):
        self._factory = factory
        self._pool = asyncio.Queue(maxsize=max_size)
        self._semaphore = asyncio.Semaphore(max_size)
    
    async def acquire(self):
        """Acquire connection from pool."""
        await self._semaphore.acquire()
        
        try:
            return self._pool.get_nowait()
        except asyncio.QueueEmpty:
            return await self._factory()
    
    async def release(self, conn):
        """Return connection to pool."""
        try:
            self._pool.put_nowait(conn)
        finally:
            self._semaphore.release()
```

## <a name="common-pitfalls"></a>Common Pitfalls and Solutions

### <a name="pitfall-blocking"></a>Pitfall 1: Blocking the Event Loop

**Problem:** Using blocking operations in async functions
**Solution:** Always use async alternatives or run in executor

```python
# ❌ Bad
async def calculate_hash(data):
    return hashlib.sha256(data).hexdigest()  # CPU-intensive, blocks loop

# ✅ Good
async def calculate_hash(data):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        lambda: hashlib.sha256(data).hexdigest()
    )
```

### <a name="pitfall-concurrent-errors"></a>Pitfall 2: Not Handling Concurrent Errors

**Problem:** Ignoring exceptions in gathered tasks
**Solution:** Always handle exceptions explicitly

```python
# ✅ Proper error handling
results = await asyncio.gather(*tasks, return_exceptions=True)
for i, result in enumerate(results):
    if isinstance(result, Exception):
        logger.error(f"Task {i} failed: {result}")
        # Handle specific error
    else:
        # Process successful result
        pass
```

### <a name="pitfall-resource-leaks"></a>Pitfall 3: Resource Leaks

**Problem:** Not cleaning up async resources
**Solution:** Always use context managers or try/finally

```python
# ✅ Guaranteed cleanup
async def process_with_cleanup():
    resource = None
    try:
        resource = await acquire_resource()
        return await process(resource)
    finally:
        if resource:
            await resource.cleanup()
```

## <a name="testing-async-code"></a>Testing Async Code

### <a name="basic-async-test"></a>Basic Async Test Pattern

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_operation():
    """Test async functionality."""
    core = ScanGameCore()
    result = await core.scan_files([Path("test.txt")])
    assert result is not None

# Alternative with pytest-asyncio
@pytest.fixture
async def async_client():
    """Async fixture."""
    client = AsyncClient()
    await client.connect()
    yield client
    await client.disconnect()
```

### <a name="testing-concurrency"></a>Testing Concurrency

```python
@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test that operations run concurrently."""
    import time
    
    async def slow_operation(n):
        await asyncio.sleep(1)
        return n
    
    start = time.time()
    
    # Should complete in ~1 second, not 5
    results = await asyncio.gather(
        *[slow_operation(i) for i in range(5)]
    )
    
    elapsed = time.time() - start
    assert elapsed < 2  # Confirms concurrent execution
    assert results == [0, 1, 2, 3, 4]
```

## <a name="conclusion"></a>Conclusion

The CLASSIC codebase demonstrates exceptional async and threading patterns that ensure:
- High performance through proper concurrency
- Resource efficiency with dynamic limits
- Robustness through comprehensive error handling
- Maintainability with clear architectural patterns

These patterns represent production-grade concurrent programming and should be followed when extending the codebase. The async-first architecture with sync adapters provides the best of both worlds: modern async performance with backwards compatibility.

For questions or clarifications about these patterns, refer to the specific implementation files mentioned throughout this guide or consult the inline documentation in the codebase.