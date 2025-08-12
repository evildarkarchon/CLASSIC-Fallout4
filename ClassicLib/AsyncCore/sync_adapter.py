"""Standard sync adapter patterns for async-first components"""

import asyncio
import inspect
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SyncAdapter:
    """Base class for creating sync adapters for async classes

    This class provides a standard pattern for wrapping async-first
    components with synchronous interfaces for backwards compatibility.

    Example:
        class MyAsyncClass:
            async def process(self, data):
                ...

        class MySyncAdapter(SyncAdapter):
            def __init__(self):
                super().__init__(MyAsyncClass())
    """

    def __init__(self, async_instance: Any):
        """Initialize sync adapter with async instance

        Args:
            async_instance: Instance of async class to wrap
        """
        self._async_instance = async_instance
        self._loop: asyncio.AbstractEventLoop | None = None

        # Automatically create sync wrappers for all async methods
        self._create_sync_methods()

    def _create_sync_methods(self):
        """Automatically create sync wrappers for async methods"""
        for name in dir(self._async_instance):
            if name.startswith("_"):
                continue

            attr = getattr(self._async_instance, name)
            if inspect.iscoroutinefunction(attr):
                # Create a sync wrapper for this async method
                sync_method = self._create_sync_wrapper(attr)
                setattr(self, name, sync_method)

    def _create_sync_wrapper(self, async_method: Callable) -> Callable:
        """Create a sync wrapper for an async method

        Args:
            async_method: Async method to wrap

        Returns:
            Sync wrapper function
        """

        @wraps(async_method)
        def sync_wrapper(*args, **kwargs):
            return self._run_async(async_method(*args, **kwargs))

        return sync_wrapper

    def _run_async(self, coro: Any) -> Any:
        """Run async coroutine in sync context

        Handles existing event loops gracefully.

        Args:
            coro: Coroutine to run

        Returns:
            Result of coroutine
        """
        try:
            # Check if we're already in an async context
            loop = asyncio.get_running_loop()
            # We're in an async context, this shouldn't happen for sync adapter
            logger.warning("SyncAdapter called from async context, consider using async version directly")
            # Create a new event loop in a thread to avoid conflicts
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        except RuntimeError:
            # No event loop, safe to run normally
            return asyncio.run(coro)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to async instance for non-methods"""
        return getattr(self._async_instance, name)


def create_sync_adapter(async_class: type[T], *args, **kwargs) -> Any:
    """Factory function to create a sync adapter for an async class

    This function automatically creates a synchronous wrapper for any
    async-first class, providing backwards compatibility.

    Args:
        async_class: Async class to wrap
        *args: Arguments to pass to async class constructor
        **kwargs: Keyword arguments to pass to async class constructor

    Returns:
        Sync adapter instance

    Example:
        # Async class
        class AsyncProcessor:
            async def process(self, data):
                return await self._do_processing(data)

        # Create sync adapter
        sync_processor = create_sync_adapter(AsyncProcessor)
        result = sync_processor.process(data)  # Sync call
    """

    class DynamicSyncAdapter:
        """Dynamically generated sync adapter"""

        def __init__(self):
            self._async_instance = async_class(*args, **kwargs)
            self._create_sync_methods()

        def _create_sync_methods(self):
            """Create sync wrappers for all async methods"""
            for name in dir(self._async_instance):
                if name.startswith("_"):
                    continue

                attr = getattr(self._async_instance, name)
                if inspect.iscoroutinefunction(attr):
                    sync_method = self._create_sync_wrapper(attr)
                    setattr(self, name, sync_method)

        def _create_sync_wrapper(self, async_method: Callable) -> Callable:
            """Create a sync wrapper for an async method"""

            @wraps(async_method)
            def sync_wrapper(*args, **kwargs):
                return self._run_async(async_method(*args, **kwargs))

            return sync_wrapper

        def _run_async(self, coro: Any) -> Any:
            """Run async coroutine in sync context"""
            try:
                loop = asyncio.get_running_loop()
                # In async context, use thread executor
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            except RuntimeError:
                return asyncio.run(coro)

        def __getattr__(self, name: str) -> Any:
            """Delegate to async instance"""
            return getattr(self._async_instance, name)

    return DynamicSyncAdapter()


def sync_to_async_method(sync_func: Callable) -> Callable:
    """Convert a sync method to async

    Useful for gradually migrating sync code to async.

    Args:
        sync_func: Synchronous function

    Returns:
        Async wrapper

    Example:
        @sync_to_async_method
        def process_data(self, data):
            # Sync implementation
            return processed_data
    """

    @wraps(sync_func)
    async def async_wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_func, *args, **kwargs)

    return async_wrapper


def async_to_sync_method(async_func: Callable) -> Callable:
    """Convert an async method to sync

    Provides backwards compatibility for async methods.

    Args:
        async_func: Async function

    Returns:
        Sync wrapper

    Example:
        @async_to_sync_method
        async def process_data(self, data):
            # Async implementation
            return await self._process(data)
    """

    @wraps(async_func)
    def sync_wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
            # In async context, use thread executor
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, async_func(*args, **kwargs))
                return future.result()
        except RuntimeError:
            return asyncio.run(async_func(*args, **kwargs))

    return sync_wrapper


class HybridMethod:
    """Decorator for methods that can be called both sync and async

    This allows a single method to work in both sync and async contexts.

    Example:
        class MyClass:
            @HybridMethod
            async def process(self, data):
                # Async implementation
                return await self._do_processing(data)

        obj = MyClass()

        # Sync usage
        result = obj.process.sync(data)

        # Async usage
        result = await obj.process(data)
    """

    def __init__(self, async_func: Callable):
        self.async_func = async_func
        self.sync_func = None

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return BoundHybridMethod(self.async_func, obj)


class BoundHybridMethod:
    """Bound version of HybridMethod"""

    def __init__(self, async_func: Callable, instance: Any):
        self.async_func = async_func
        self.instance = instance

    async def __call__(self, *args, **kwargs):
        """Async call"""
        return await self.async_func(self.instance, *args, **kwargs)

    def sync(self, *args, **kwargs):
        """Sync call"""
        try:
            loop = asyncio.get_running_loop()
            # In async context, use thread executor
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                coro = self.async_func(self.instance, *args, **kwargs)
                future = executor.submit(asyncio.run, coro)
                return future.result()
        except RuntimeError:
            return asyncio.run(self.async_func(self.instance, *args, **kwargs))


def create_sync_wrapper(async_func: Callable, preserve_annotations: bool = True) -> Callable:
    """Create a synchronous wrapper for an async function

    Args:
        async_func: Async function to wrap
        preserve_annotations: Whether to preserve type annotations

    Returns:
        Sync wrapper function

    Example:
        async def process_async(data: str) -> dict:
            ...

        process_sync = create_sync_wrapper(process_async)
        result = process_sync("data")  # Sync call
    """

    @wraps(async_func)
    def sync_wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
            # In async context, use thread executor to avoid conflicts
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, async_func(*args, **kwargs))
                return future.result()
        except RuntimeError:
            # No event loop, safe to run normally
            return asyncio.run(async_func(*args, **kwargs))

    if preserve_annotations:
        # Copy annotations from async function
        sync_wrapper.__annotations__ = async_func.__annotations__.copy()

    return sync_wrapper


class AsyncCompatibilityMixin:
    """Mixin to add sync compatibility to async classes

    Add this mixin to async classes to automatically provide
    sync versions of all async methods.

    Example:
        class MyAsyncClass(AsyncCompatibilityMixin):
            async def process(self, data):
                ...

        obj = MyAsyncClass()

        # Both work:
        result = await obj.process(data)  # Async
        result = obj.process_sync(data)   # Sync (auto-generated)
    """

    def __init_subclass__(cls):
        """Add sync methods when class is defined"""
        super().__init_subclass__()

        for name, method in inspect.getmembers(cls, inspect.iscoroutinefunction):
            if not name.startswith("_"):
                # Create sync version with _sync suffix
                sync_name = f"{name}_sync"

                def make_sync_method(async_method):
                    @wraps(async_method)
                    def sync_method(self, *args, **kwargs):
                        return asyncio.run(async_method(self, *args, **kwargs))

                    return sync_method

                setattr(cls, sync_name, make_sync_method(method))
