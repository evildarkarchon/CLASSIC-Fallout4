"""
Tests for async patterns without AsyncCore.

This module demonstrates how to implement async patterns directly
without relying on deprecated AsyncCore base classes.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest


class TestAsyncContextPattern:
    """Test async context manager patterns"""

    @pytest.mark.asyncio
    async def test_custom_async_context_manager(self):
        """Test custom async context manager implementation"""

        class AsyncComponent:
            def __init__(self):
                self.initialized = False
                self.cleaned_up = False
                self.resources = []

            async def __aenter__(self):
                await self.initialize()
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await self.cleanup()

            async def initialize(self):
                self.initialized = True

            async def cleanup(self):
                for resource in self.resources:
                    if hasattr(resource, "close"):
                        if asyncio.iscoroutinefunction(resource.close):
                            await resource.close()
                        else:
                            resource.close()
                self.cleaned_up = True
                self.initialized = False

            def add_resource(self, resource):
                self.resources.append(resource)

        async with AsyncComponent() as component:
            assert component.initialized
            mock_resource = AsyncMock()
            mock_resource.close = AsyncMock()
            component.add_resource(mock_resource)

        assert component.cleaned_up
        assert not component.initialized
        mock_resource.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_with_exception(self):
        """Test async context manager handles exceptions properly"""

        cleanup_called = False

        @asynccontextmanager
        async def managed_resource():
            resource = {"active": True}
            try:
                yield resource
            finally:
                nonlocal cleanup_called
                cleanup_called = True
                resource["active"] = False

        try:
            async with managed_resource() as resource:
                assert resource["active"]
                raise ValueError("Test error")
        except ValueError:
            pass

        assert cleanup_called


class TestAsyncProcessingPattern:
    """Test async processing patterns"""

    @pytest.mark.asyncio
    async def test_concurrent_processing_with_semaphore(self):
        """Test concurrent processing with semaphore for rate limiting"""

        class AsyncProcessor:
            def __init__(self, max_concurrent=3):
                self.semaphore = asyncio.Semaphore(max_concurrent)
                self.processed_count = 0

            async def process_item(self, item):
                async with self.semaphore:
                    await asyncio.sleep(0.01)
                    self.processed_count += 1
                    return item * 2

            async def process_batch(self, items):
                tasks = [self.process_item(item) for item in items]
                return await asyncio.gather(*tasks)

        processor = AsyncProcessor(max_concurrent=2)
        items = [1, 2, 3, 4, 5]
        results = await processor.process_batch(items)

        assert results == [2, 4, 6, 8, 10]
        assert processor.processed_count == 5

    @pytest.mark.asyncio
    async def test_processing_with_error_handling(self):
        """Test processing with proper error handling"""

        async def process_with_errors(items):
            async def process_item(item):
                if item == 3:
                    raise ValueError(f"Error processing {item}")
                return item * 2

            tasks = [process_item(item) for item in items]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions
            return [r for r in results if not isinstance(r, Exception)]

        items = [1, 2, 3, 4, 5]
        results = await process_with_errors(items)
        assert results == [2, 4, 8, 10]  # 3 is skipped

    @pytest.mark.asyncio
    async def test_progress_tracking_pattern(self):
        """Test progress tracking in async processing"""

        class ProgressProcessor:
            def __init__(self):
                self.progress = 0
                self.total = 0
                self.progress_callback = None

            async def process_item(self, item):
                await asyncio.sleep(0.01)
                result = item * 2
                self.progress += 1
                if self.progress_callback:
                    await self.progress_callback(self.progress, self.total)
                return result

            async def process_all(self, items):
                self.progress = 0
                self.total = len(items)
                tasks = [self.process_item(item) for item in items]
                return await asyncio.gather(*tasks)

        processor = ProgressProcessor()
        progress_updates = []

        async def track_progress(current, total):
            progress_updates.append((current, total))

        processor.progress_callback = track_progress
        results = await processor.process_all([1, 2, 3])

        assert results == [2, 4, 6]
        assert len(progress_updates) > 0
        assert progress_updates[-1] == (3, 3)


class TestAsyncUtilityPatterns:
    """Test async utility patterns"""

    @pytest.mark.asyncio
    async def test_gather_with_concurrency_limit(self):
        """Test gathering tasks with concurrency limit"""

        async def gather_with_limit(tasks, limit):
            semaphore = asyncio.Semaphore(limit)

            async def bounded_task(task):
                async with semaphore:
                    return await task

            return await asyncio.gather(*[bounded_task(t) for t in tasks])

        async def work_task(n):
            await asyncio.sleep(0.01)
            return n * 2

        tasks = [work_task(i) for i in range(5)]
        results = await gather_with_limit(tasks, limit=2)
        assert results == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_batch_processing_pattern(self):
        """Test batch processing pattern"""

        async def process_in_batches(items, processor, batch_size=2):
            results = []
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                batch_tasks = [processor(item) for item in batch]
                batch_results = await asyncio.gather(*batch_tasks)
                results.extend(batch_results)
            return results

        async def process_item(item):
            await asyncio.sleep(0.01)
            return item * 2

        items = [1, 2, 3, 4, 5]
        results = await process_in_batches(items, process_item, batch_size=2)
        assert results == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_async_resource_pool_pattern(self):
        """Test async resource pool pattern"""

        class AsyncResourcePool:
            def __init__(self, factory, max_size=3):
                self.factory = factory
                self.max_size = max_size
                self.pool = []
                self.in_use = []  # Use list instead of set for unhashable types
                self.lock = asyncio.Lock()

            async def acquire(self):
                async with self.lock:
                    if self.pool:
                        resource = self.pool.pop()
                    elif len(self.in_use) < self.max_size:
                        resource = await self.factory()
                    else:
                        # Wait for a resource to be released
                        while not self.pool:
                            await asyncio.sleep(0.01)
                        resource = self.pool.pop()
                    self.in_use.append(resource)
                    return resource

            async def release(self, resource):
                async with self.lock:
                    if resource in self.in_use:
                        self.in_use.remove(resource)
                    self.pool.append(resource)

            @asynccontextmanager
            async def get_resource(self):
                resource = await self.acquire()
                try:
                    yield resource
                finally:
                    await self.release(resource)

        resource_counter = 0

        async def create_resource():
            nonlocal resource_counter
            resource_counter += 1
            return {"id": resource_counter}

        pool = AsyncResourcePool(create_resource, max_size=2)

        async with pool.get_resource() as resource1:
            assert resource1 is not None
            async with pool.get_resource() as resource2:
                assert resource2 is not None
                assert resource1 != resource2

    @pytest.mark.asyncio
    async def test_async_cache_pattern(self):
        """Test async caching pattern"""

        class AsyncCache:
            def __init__(self):
                self.cache = {}
                self.locks = {}

            async def get_or_compute(self, key, compute_func):
                if key in self.cache:
                    return self.cache[key]

                if key not in self.locks:
                    self.locks[key] = asyncio.Lock()

                async with self.locks[key]:
                    # Double-check after acquiring lock
                    if key in self.cache:
                        return self.cache[key]

                    # Compute value
                    if asyncio.iscoroutinefunction(compute_func):
                        value = await compute_func()
                    else:
                        value = compute_func()

                    self.cache[key] = value
                    return value

        cache = AsyncCache()
        compute_count = 0

        async def expensive_computation():
            nonlocal compute_count
            compute_count += 1
            await asyncio.sleep(0.01)
            return "computed_value"

        # First call computes
        result1 = await cache.get_or_compute("key1", expensive_computation)
        assert result1 == "computed_value"
        assert compute_count == 1

        # Second call uses cache
        result2 = await cache.get_or_compute("key1", expensive_computation)
        assert result2 == "computed_value"
        assert compute_count == 1  # Not incremented

        # Different key computes again
        result3 = await cache.get_or_compute("key2", expensive_computation)
        assert result3 == "computed_value"
        assert compute_count == 2
