"""
Tests for base async patterns and components.

This module contains tests for AsyncBase and AsyncProcessor classes
which provide the foundation for async operations in the pipeline.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import asyncio
from unittest.mock import AsyncMock

import pytest

from ClassicLib.AsyncCore import (
    AsyncBase,
    AsyncProcessor,
    batch_process,
    gather_with_concurrency,
)


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

    @pytest.mark.asyncio
    async def test_multiple_resource_cleanup(self):
        """Test cleanup of multiple resources"""
        resources = [AsyncMock() for _ in range(3)]
        for r in resources:
            r.close = AsyncMock()

        component = AsyncBase()
        for resource in resources:
            component.register_resource(resource)

        await component.cleanup()

        for resource in resources:
            resource.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_state(self):
        """Test initialization state tracking"""
        component = AsyncBase()
        assert not component._initialized

        await component.initialize()
        assert component._initialized

        await component.cleanup()
        assert not component._initialized


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

    @pytest.mark.asyncio
    async def test_process_with_errors(self):
        """Test batch processing with error handling"""

        class TestProcessor(AsyncProcessor):
            async def process_item(self, item):
                if item == 3:
                    raise ValueError("Test error")
                return item * 2

        processor = TestProcessor(max_concurrent=2)
        items = [1, 2, 3, 4, 5]

        results = await processor.process_batch(items, skip_errors=True)
        # Item 3 should be skipped due to error
        assert len(results) == 4
        assert 6 not in results  # 3 * 2 would be 6

    @pytest.mark.asyncio
    async def test_processor_initialization(self):
        """Test processor initialization and cleanup"""

        class TestProcessor(AsyncProcessor):
            def __init__(self):
                super().__init__(max_concurrent=3)
                self.init_called = False

            async def initialize(self):
                await super().initialize()
                self.init_called = True

            async def process_item(self, item):
                return item

        async with TestProcessor() as processor:
            assert processor.init_called
            assert processor._semaphore._value == 3

    @pytest.mark.asyncio
    async def test_concurrent_processing_limit(self):
        """Test that concurrency limit is respected"""
        concurrent_count = 0
        max_concurrent_seen = 0

        class TestProcessor(AsyncProcessor):
            async def process_item(self, item):
                nonlocal concurrent_count, max_concurrent_seen
                concurrent_count += 1
                max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
                await asyncio.sleep(0.01)
                concurrent_count -= 1
                return item

        processor = TestProcessor(max_concurrent=2)
        items = list(range(10))

        await processor.process_batch(items)
        assert max_concurrent_seen <= 2


class TestBatchProcessing:
    """Test batch processing utilities"""

    @pytest.mark.asyncio
    async def test_batch_process_function(self):
        """Test standalone batch_process function"""

        async def process_func(item):
            await asyncio.sleep(0.001)
            return item * 2

        items = [1, 2, 3, 4, 5]
        results = await batch_process(items, process_func, max_concurrent=2)
        assert results == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_gather_with_concurrency(self):
        """Test gather_with_concurrency function"""

        async def task_func(i):
            await asyncio.sleep(0.001)
            return i * 2

        tasks = [task_func(i) for i in range(5)]
        results = await gather_with_concurrency(tasks, max_concurrent=2)
        assert results == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_batch_process_with_empty_list(self):
        """Test batch processing with empty input"""

        async def process_func(item):
            return item

        results = await batch_process([], process_func)
        assert results == []

    @pytest.mark.asyncio
    async def test_gather_with_exceptions(self):
        """Test gather_with_concurrency with exceptions"""

        async def task_func(i):
            if i == 2:
                raise ValueError(f"Error at {i}")
            return i * 2

        tasks = [task_func(i) for i in range(5)]

        # With return_exceptions=True
        results = await gather_with_concurrency(
            tasks, max_concurrent=2, return_exceptions=True
        )

        # Check that we got results and exceptions
        assert len(results) == 5
        assert isinstance(results[2], ValueError)
        assert results[0] == 0
        assert results[1] == 2
