"""Base classes and patterns for async-first architecture"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncBase(ABC):
    """Base class for all async components in CLASSIC

    Provides common patterns for initialization, cleanup, and resource management.
    """

    def __init__(self):
        self._initialized = False
        self._resources = []
        self._cleanup_tasks = []

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup"""
        await self.cleanup()

    async def initialize(self):
        """Initialize async resources

        Override this method to set up any async resources needed by the component.
        """
        if self._initialized:
            return
        self._initialized = True
        logger.debug(f"Initialized {self.__class__.__name__}")

    async def cleanup(self):
        """Clean up async resources

        Override this method to clean up any resources.
        Base implementation handles registered cleanup tasks.
        """
        if self._cleanup_tasks:
            await asyncio.gather(*self._cleanup_tasks, return_exceptions=True)
            self._cleanup_tasks.clear()

        for resource in self._resources:
            if hasattr(resource, "close"):
                try:
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()
                except Exception as e:
                    logger.error(f"Error closing resource: {e}")

        self._resources.clear()
        self._initialized = False
        logger.debug(f"Cleaned up {self.__class__.__name__}")

    def register_resource(self, resource: Any):
        """Register a resource for automatic cleanup"""
        self._resources.append(resource)

    def register_cleanup(self, coro: Callable):
        """Register a cleanup coroutine to run during cleanup"""
        self._cleanup_tasks.append(coro())


class AsyncProcessor(AsyncBase, Generic[T]):
    """Base class for async data processors

    Provides patterns for processing data with progress tracking and cancellation.
    """

    def __init__(self, max_concurrent: int = 10):
        super().__init__()
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._progress = 0
        self._total = 0
        self._cancelled = False
        self._progress_callback: Callable[[int, int], None] | None = None

    @abstractmethod
    async def process_item(self, item: T) -> Any:
        """Process a single item

        Must be implemented by subclasses.
        """

    async def process_batch(self, items: list[T]) -> list[Any]:
        """Process a batch of items with concurrency control"""
        self._progress = 0
        self._total = len(items)
        self._cancelled = False

        tasks = []
        for item in items:
            if self._cancelled:
                break
            task = asyncio.create_task(self._process_with_semaphore(item))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return successful results
        return [r for r in results if not isinstance(r, Exception)]

    async def _process_with_semaphore(self, item: T) -> Any:
        """Process item with semaphore for concurrency control"""
        async with self._semaphore:
            if self._cancelled:
                return None

            try:
                result = await self.process_item(item)
                self._update_progress()
                return result
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                raise

    def _update_progress(self):
        """Update progress and call callback if set"""
        self._progress += 1
        if self._progress_callback:
            self._progress_callback(self._progress, self._total)

    def set_progress_callback(self, callback: Callable[[int, int], None]):
        """Set a callback for progress updates"""
        self._progress_callback = callback

    def cancel(self):
        """Cancel ongoing processing"""
        self._cancelled = True

    @property
    def progress(self) -> tuple[int, int]:
        """Get current progress as (completed, total)"""
        return (self._progress, self._total)


class AsyncFileProcessor(AsyncProcessor[Path]):
    """Base class for async file processing

    Specialized processor for file operations with built-in I/O patterns.
    """

    def __init__(self, max_concurrent: int = 5):
        # Limit concurrent file operations to avoid too many open files
        super().__init__(max_concurrent=max_concurrent)

    @abstractmethod
    async def process_file_content(self, content: str, path: Path) -> Any:
        """Process the content of a file

        Must be implemented by subclasses.
        """

    async def process_item(self, path: Path) -> Any:
        """Process a single file"""
        try:
            # Use aiofiles when available, fallback to sync read in executor
            try:
                import aiofiles

                async with aiofiles.open(path, encoding="utf-8") as f:
                    content = await f.read()
            except ImportError:
                # Fallback to sync read in executor
                loop = asyncio.get_event_loop()
                with open(path, encoding="utf-8") as f:
                    content = await loop.run_in_executor(None, f.read)

            return await self.process_file_content(content, path)

        except Exception as e:
            logger.error(f"Error processing file {path}: {e}")
            raise


class AsyncCacheBase(AsyncBase):
    """Base class for async caching components"""

    def __init__(self, ttl: int | None = None):
        super().__init__()
        self._cache = {}
        self._ttl = ttl
        self._locks = {}

    async def get(self, key: str) -> Any | None:
        """Get value from cache"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if self._ttl and (asyncio.get_event_loop().time() - timestamp) > self._ttl:
                del self._cache[key]
                return None
            return value
        return None

    async def set(self, key: str, value: Any):
        """Set value in cache"""
        self._cache[key] = (value, asyncio.get_event_loop().time())

    async def get_or_compute(self, key: str, compute_func: Callable) -> Any:
        """Get from cache or compute if not present

        Ensures compute_func is only called once even with concurrent requests.
        """
        # Check cache first
        cached = await self.get(key)
        if cached is not None:
            return cached

        # Use lock to prevent duplicate computation
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        async with self._locks[key]:
            # Double-check after acquiring lock
            cached = await self.get(key)
            if cached is not None:
                return cached

            # Compute value
            if asyncio.iscoroutinefunction(compute_func):
                value = await compute_func()
            else:
                value = compute_func()

            await self.set(key, value)
            return value

    async def clear(self):
        """Clear all cached values"""
        self._cache.clear()
        self._locks.clear()

    async def cleanup(self):
        """Clean up cache"""
        await self.clear()
        await super().cleanup()
