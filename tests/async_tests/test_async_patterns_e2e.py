"""
E2E tests for async_patterns - e2e logic testing.

This file contains e2e tests that test complete workflows from entry to output.
"""

# IMPORTANT: Async Test Pattern Documentation
# ============================================
# This test file follows correct AsyncBridge patterns:
# 1. For sync wrappers using AsyncBridge: Mock bridge.run_async(), not the async function
# 2. For pure async tests: Use @pytest.mark.asyncio and real async/await
# 3. Never use AsyncMock for methods called through AsyncBridge
# 4. See docs/async_test_patterns_guide.md for comprehensive patterns

import asyncio
from typing import Awaitable, Callable

import pytest

pytestmark = pytest.mark.e2e


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
            return [r for r in results if not isinstance(r, Exception)]

        items = [1, 2, 3, 4, 5]
        results = await process_with_errors(items)
        assert results == [2, 4, 8, 10]

    @pytest.mark.asyncio
    async def test_progress_tracking_pattern(self):
        """Test progress tracking in async processing"""

        class ProgressProcessor:
            def __init__(self):
                self.progress = 0
                self.total = 0
                self.progress_callback: Callable[[int, int], Awaitable[None]] | None = None

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
