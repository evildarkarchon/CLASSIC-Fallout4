"""
Unit tests for async_patterns - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

# IMPORTANT: Async Test Pattern Documentation
# ============================================
# This test file follows correct AsyncBridge patterns:
# 1. For sync wrappers using AsyncBridge: Mock bridge.run_async(), not the async function
# 2. For pure async tests: Use @pytest.mark.asyncio and real async/await
# 3. Never use AsyncMock for methods called through AsyncBridge
# 4. See docs/async_test_patterns_guide.md for comprehensive patterns

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


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
    async def test_async_resource_pool_pattern(self):
        """Test async resource pool pattern"""

        class AsyncResourcePool:
            def __init__(self, factory, max_size=3):
                self.factory = factory
                self.max_size = max_size
                self.pool = []
                self.in_use = []
                self.lock = asyncio.Lock()

            async def acquire(self):
                async with self.lock:
                    if self.pool:
                        resource = self.pool.pop()
                    elif len(self.in_use) < self.max_size:
                        resource = await self.factory()
                    else:
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
                    if key in self.cache:
                        return self.cache[key]
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

        result1 = await cache.get_or_compute("key1", expensive_computation)
        assert result1 == "computed_value"
        assert compute_count == 1
        result2 = await cache.get_or_compute("key1", expensive_computation)
        assert result2 == "computed_value"
        assert compute_count == 1
        result3 = await cache.get_or_compute("key2", expensive_computation)
        assert result3 == "computed_value"
        assert compute_count == 2
