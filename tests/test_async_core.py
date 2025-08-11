"""Tests for AsyncCore infrastructure"""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from ClassicLib.AsyncCore import (
    AsyncBase,
    AsyncErrorHandler,
    AsyncExecutionError,
    AsyncProcessor,
    AsyncResourceManager,
    AsyncSemaphorePool,
    ErrorSeverity,
    SyncAdapter,
    batch_process,
    create_sync_adapter,
    gather_with_concurrency,
)
from ClassicLib.AsyncCore.base import AsyncCacheBase, AsyncFileProcessor
from ClassicLib.AsyncCore.error_handler import AsyncCircuitBreaker, retry_async
from ClassicLib.AsyncCore.resource_manager import AsyncConnectionPool
from ClassicLib.AsyncCore.sync_adapter import HybridMethod, create_sync_wrapper
from ClassicLib.AsyncCore.utils import AsyncLazyLoader, AsyncTimer, async_filter, async_map


class TestAsyncBase:
    """Test AsyncBase class"""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager functionality"""

        class TestComponent(AsyncBase):
            def __init__(self):
                super().__init__()
                self.initialized_called = False
                self.cleanup_called = False

            async def initialize(self):
                await super().initialize()
                self.initialized_called = True

            async def cleanup(self):
                self.cleanup_called = True
                await super().cleanup()

        async with TestComponent() as component:
            assert component.initialized_called
            assert component._initialized

        assert component.cleanup_called
        assert not component._initialized

    @pytest.mark.asyncio
    async def test_resource_registration(self):
        """Test resource registration and cleanup"""
        mock_resource = AsyncMock()
        mock_resource.close = AsyncMock()

        component = AsyncBase()
        component.register_resource(mock_resource)

        await component.cleanup()
        mock_resource.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_task_registration(self):
        """Test cleanup task registration"""
        cleanup_called = False

        async def cleanup_task():
            nonlocal cleanup_called
            cleanup_called = True

        component = AsyncBase()
        component.register_cleanup(cleanup_task)

        await component.cleanup()
        assert cleanup_called


class TestAsyncProcessor:
    """Test AsyncProcessor class"""

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test batch processing with concurrency control"""

        class TestProcessor(AsyncProcessor):
            async def process_item(self, item):
                await asyncio.sleep(0.01)
                return item * 2

        processor = TestProcessor(max_concurrent=2)
        items = [1, 2, 3, 4, 5]

        results = await processor.process_batch(items)
        assert results == [2, 4, 6, 8, 10]
        assert processor.progress == (5, 5)

    @pytest.mark.asyncio
    async def test_progress_callback(self):
        """Test progress callback functionality"""
        progress_updates = []

        class TestProcessor(AsyncProcessor):
            async def process_item(self, item):
                return item

        processor = TestProcessor()
        processor.set_progress_callback(lambda p, t: progress_updates.append((p, t)))

        await processor.process_batch([1, 2, 3])
        assert len(progress_updates) == 3
        assert progress_updates[-1] == (3, 3)

    @pytest.mark.asyncio
    async def test_cancellation(self):
        """Test processing cancellation"""

        class TestProcessor(AsyncProcessor):
            async def process_item(self, item):
                # Check cancellation before processing
                if self._cancelled:
                    return None
                await asyncio.sleep(0.1)
                return item

        processor = TestProcessor(max_concurrent=2)  # Limit concurrency
        items = list(range(10))

        # Start processing and cancel quickly
        task = asyncio.create_task(processor.process_batch(items))
        await asyncio.sleep(0.05)  # Let some items start
        processor.cancel()

        results = await task
        # Should have processed some but not all items
        # With cancellation, some results will be None or missing
        assert len([r for r in results if r is not None]) < len(items)


class TestAsyncErrorHandler:
    """Test AsyncErrorHandler class"""

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test basic error handling"""
        handler = AsyncErrorHandler()
        error_callback_called = False

        def callback(error):
            nonlocal error_callback_called
            error_callback_called = True
            assert isinstance(error, AsyncExecutionError)

        handler.register_callback(callback)

        test_error = ValueError("Test error")
        await handler.handle_error(test_error, context={"test": True})

        assert error_callback_called
        assert len(handler.get_error_history()) == 1

    @pytest.mark.asyncio
    async def test_safe_execute(self):
        """Test safe execution with error handling"""
        handler = AsyncErrorHandler()

        async def failing_coro():
            raise ValueError("Expected error")

        result = await handler.safe_execute(failing_coro, default="default_value")
        assert result == "default_value"
        assert len(handler.get_error_history()) == 1

    @pytest.mark.asyncio
    async def test_safe_execute_reraise(self):
        """Test safe execution with reraise option"""
        handler = AsyncErrorHandler()

        async def failing_coro():
            raise ValueError("Expected error")

        with pytest.raises(ValueError):
            await handler.safe_execute(failing_coro, reraise=True)

    @pytest.mark.asyncio
    async def test_safe_task(self):
        """Test safe task creation"""
        handler = AsyncErrorHandler()

        async def test_coro():
            return "success"

        task = handler.safe_task(test_coro, name="test_task")
        assert task.get_name() == "test_task"
        result = await task
        assert result == "success"

    @pytest.mark.asyncio
    async def test_error_severity_filtering(self):
        """Test error history filtering by severity"""
        handler = AsyncErrorHandler()

        await handler.handle_error(ValueError("Error 1"), severity=ErrorSeverity.ERROR)
        await handler.handle_error(ValueError("Warning 1"), severity=ErrorSeverity.WARNING)
        await handler.handle_error(ValueError("Error 2"), severity=ErrorSeverity.ERROR)

        errors = handler.get_error_history(severity=ErrorSeverity.ERROR)
        assert len(errors) == 2

        warnings = handler.get_error_history(severity=ErrorSeverity.WARNING)
        assert len(warnings) == 1


class TestAsyncRetry:
    """Test retry functionality"""

    @pytest.mark.asyncio
    async def test_retry_success(self):
        """Test successful retry after failures"""
        attempt_count = 0

        async def flaky_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await retry_async(flaky_func, max_attempts=5)
        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry attempts exhausted"""

        async def always_fails():
            raise ValueError("Permanent error")

        with pytest.raises(AsyncExecutionError) as exc_info:
            await retry_async(always_fails, max_attempts=3, delay=0.01)

        assert "All 3 retry attempts failed" in str(exc_info.value)


class TestAsyncCircuitBreaker:
    """Test circuit breaker pattern"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after failures"""
        breaker = AsyncCircuitBreaker(failure_threshold=2, timeout=0.1)

        async def failing_func():
            raise ValueError("Error")

        # First two failures
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        assert breaker.is_open

        # Circuit is open, should reject immediately
        with pytest.raises(AsyncExecutionError) as exc_info:
            await breaker.call(failing_func)
        assert "Circuit breaker is open" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open(self):
        """Test circuit breaker half-open state"""
        breaker = AsyncCircuitBreaker(failure_threshold=2, timeout=0.05)

        async def failing_func():
            raise ValueError("Error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(0.06)

        # Should enter half-open state and try again
        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        # Should be open again after failure in half-open
        assert breaker.is_open


class TestAsyncResourceManager:
    """Test AsyncResourceManager class"""

    @pytest.mark.asyncio
    async def test_resource_acquisition(self):
        """Test resource acquisition and caching"""
        manager = AsyncResourceManager()

        created_count = 0

        async def create_resource():
            nonlocal created_count
            created_count += 1
            return f"resource_{created_count}"

        # First acquisition creates resource
        resource1 = await manager.acquire_resource("test", create_resource)
        assert resource1 == "resource_1"
        assert created_count == 1

        # Second acquisition returns cached resource
        resource2 = await manager.acquire_resource("test", create_resource)
        assert resource2 == "resource_1"
        assert created_count == 1

    @pytest.mark.asyncio
    async def test_resource_cleanup(self):
        """Test resource cleanup"""
        manager = AsyncResourceManager()
        cleanup_called = False

        async def cleanup(resource):
            nonlocal cleanup_called
            cleanup_called = True

        resource = await manager.acquire_resource("test", lambda: "resource", cleanup)
        await manager.release_resource("test")

        assert cleanup_called
        assert manager.get_resource("test") is None

    @pytest.mark.asyncio
    async def test_resource_limit(self):
        """Test resource limit enforcement"""
        manager = AsyncResourceManager(max_resources=2)

        await manager.acquire_resource("res1", lambda: "r1")
        await manager.acquire_resource("res2", lambda: "r2")

        with pytest.raises(RuntimeError) as exc_info:
            await manager.acquire_resource("res3", lambda: "r3")
        assert "Resource limit" in str(exc_info.value)


class TestAsyncSemaphorePool:
    """Test AsyncSemaphorePool class"""

    @pytest.mark.asyncio
    async def test_semaphore_acquisition(self):
        """Test semaphore acquisition and concurrency control"""
        pool = AsyncSemaphorePool(default_limit=2)

        concurrent_count = 0
        max_concurrent = 0

        async def controlled_task():
            nonlocal concurrent_count, max_concurrent
            async with pool.acquire("test"):
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
                await asyncio.sleep(0.01)
                concurrent_count -= 1

        tasks = [controlled_task() for _ in range(5)]
        await asyncio.gather(*tasks)

        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_multiple_semaphores(self):
        """Test multiple independent semaphores"""
        pool = AsyncSemaphorePool()

        async with pool.acquire("type1", limit=1):
            # Should be able to acquire different type
            async with pool.acquire("type2", limit=1):
                pass


class TestSyncAdapter:
    """Test sync adapter functionality"""

    def test_create_sync_adapter(self):
        """Test creating sync adapter for async class"""

        class AsyncClass:
            async def process(self, data):
                await asyncio.sleep(0.01)
                return data * 2

        sync_instance = create_sync_adapter(AsyncClass)
        result = sync_instance.process(5)
        assert result == 10

    def test_sync_adapter_base_class(self):
        """Test SyncAdapter base class"""

        class AsyncComponent:
            async def async_method(self):
                return "async_result"

            def sync_method(self):
                return "sync_result"

        adapter = SyncAdapter(AsyncComponent())

        # Async method should be wrapped
        assert adapter.async_method() == "async_result"

        # Sync method should be delegated
        assert adapter.sync_method() == "sync_result"

    def test_hybrid_method(self):
        """Test HybridMethod decorator"""

        class TestClass:
            @HybridMethod
            async def process(self, value):
                await asyncio.sleep(0.01)
                return value * 2

        obj = TestClass()

        # Sync usage
        result = obj.process.sync(5)
        assert result == 10

        # Async usage would be: await obj.process(5)

    def test_create_sync_wrapper(self):
        """Test creating sync wrapper for async function"""

        async def async_func(x):
            await asyncio.sleep(0.01)
            return x * 2

        sync_func = create_sync_wrapper(async_func)
        result = sync_func(5)
        assert result == 10


class TestAsyncUtilities:
    """Test async utility functions"""

    @pytest.mark.asyncio
    async def test_gather_with_concurrency(self):
        """Test gathering with concurrency limit"""
        call_times = []

        async def task(n):
            start = time.time()
            call_times.append(start)
            await asyncio.sleep(0.01)
            return n

        results = await gather_with_concurrency(2, *[task(i) for i in range(5)])
        assert results == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_batch_process(self):
        """Test batch processing"""

        async def process(item):
            await asyncio.sleep(0.01)
            return item * 2

        items = list(range(10))
        results = await batch_process(items, process, batch_size=3, max_concurrent=2)
        assert results == [i * 2 for i in items]

    @pytest.mark.asyncio
    async def test_async_timer(self):
        """Test async timer context manager"""
        async with AsyncTimer() as timer:
            await asyncio.sleep(0.01)

        assert 0.01 <= timer.elapsed <= 0.02

    @pytest.mark.asyncio
    async def test_async_lazy_loader(self):
        """Test lazy loading"""
        load_count = 0

        async def load_data():
            nonlocal load_count
            load_count += 1
            await asyncio.sleep(0.01)
            return "loaded_data"

        loader = AsyncLazyLoader(load_data)

        # First call loads data
        data1 = await loader.get()
        assert data1 == "loaded_data"
        assert load_count == 1

        # Second call returns cached data
        data2 = await loader.get()
        assert data2 == "loaded_data"
        assert load_count == 1

    @pytest.mark.asyncio
    async def test_async_map(self):
        """Test async map function"""

        async def double(x):
            await asyncio.sleep(0.01)
            return x * 2

        results = await async_map(double, [1, 2, 3], max_concurrent=2)
        assert results == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_async_filter(self):
        """Test async filter function"""

        async def is_even(x):
            await asyncio.sleep(0.01)
            return x % 2 == 0

        results = await async_filter(is_even, [1, 2, 3, 4, 5], max_concurrent=2)
        assert results == [2, 4]


class TestAsyncConnectionPool:
    """Test AsyncConnectionPool class"""

    @pytest.mark.asyncio
    async def test_connection_pool(self):
        """Test basic connection pool functionality"""
        created_count = 0

        async def create_connection():
            nonlocal created_count
            created_count += 1
            return f"conn_{created_count}"

        pool = AsyncConnectionPool(factory=create_connection, min_size=1, max_size=3)

        await pool.initialize()
        assert pool.size == 1
        assert created_count == 1

        # Acquire and release connections
        async with pool.acquire() as conn1:
            assert conn1 == "conn_1"

            async with pool.acquire() as conn2:
                assert conn2 == "conn_2"
                assert pool.size == 2

        # Connections should be returned to pool
        assert pool.available == 2

    @pytest.mark.asyncio
    async def test_pool_max_size(self):
        """Test pool max size enforcement"""
        pool = AsyncConnectionPool(factory=lambda: "conn", max_size=2)

        await pool.initialize()

        # Acquire max connections
        conn1_ctx = pool.acquire()
        conn1 = await conn1_ctx.__aenter__()

        conn2_ctx = pool.acquire()
        conn2 = await conn2_ctx.__aenter__()

        # Third should wait
        acquire_task = asyncio.create_task(pool._acquire())
        await asyncio.sleep(0.01)
        assert not acquire_task.done()

        # Release one connection
        await conn1_ctx.__aexit__(None, None, None)

        # Now third should complete
        await asyncio.sleep(0.01)
        assert acquire_task.done()

        # Cleanup
        await conn2_ctx.__aexit__(None, None, None)
        await pool.close()


class TestAsyncFileProcessor:
    """Test AsyncFileProcessor class"""

    @pytest.mark.asyncio
    async def test_file_processing(self, tmp_path):
        """Test file processing functionality"""
        # Create test files
        test_files = []
        for i in range(3):
            file_path = tmp_path / f"test_{i}.txt"
            file_path.write_text(f"content_{i}")
            test_files.append(file_path)

        class TestFileProcessor(AsyncFileProcessor):
            async def process_file_content(self, content, path):
                return f"processed: {content}"

        processor = TestFileProcessor(max_concurrent=2)
        results = await processor.process_batch(test_files)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result == f"processed: content_{i}"


class TestAsyncCacheBase:
    """Test AsyncCacheBase class"""

    @pytest.mark.asyncio
    async def test_cache_operations(self):
        """Test basic cache operations"""
        cache = AsyncCacheBase()

        # Set and get
        await cache.set("key1", "value1")
        value = await cache.get("key1")
        assert value == "value1"

        # Non-existent key
        value = await cache.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_ttl(self):
        """Test cache TTL functionality"""
        cache = AsyncCacheBase(ttl=0.05)

        await cache.set("key1", "value1")

        # Should exist immediately
        value = await cache.get("key1")
        assert value == "value1"

        # Should expire after TTL
        await asyncio.sleep(0.06)
        value = await cache.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_get_or_compute(self):
        """Test get_or_compute functionality"""
        compute_count = 0

        async def compute():
            nonlocal compute_count
            compute_count += 1
            await asyncio.sleep(0.01)
            return "computed_value"

        cache = AsyncCacheBase()

        # First call computes
        value1 = await cache.get_or_compute("key1", compute)
        assert value1 == "computed_value"
        assert compute_count == 1

        # Second call uses cache
        value2 = await cache.get_or_compute("key1", compute)
        assert value2 == "computed_value"
        assert compute_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_get_or_compute(self):
        """Test concurrent get_or_compute calls"""
        compute_count = 0

        async def compute():
            nonlocal compute_count
            compute_count += 1
            await asyncio.sleep(0.05)
            return "computed_value"

        cache = AsyncCacheBase()

        # Multiple concurrent calls should only compute once
        tasks = [cache.get_or_compute("key1", compute) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        assert all(r == "computed_value" for r in results)
        assert compute_count == 1
