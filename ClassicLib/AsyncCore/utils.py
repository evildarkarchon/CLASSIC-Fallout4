"""Unified async utilities for CLASSIC"""

import asyncio
import logging
import time
from collections.abc import Callable, Iterable
from functools import partial, wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def gather_with_concurrency(max_concurrent: int, *coros) -> list:
    """Execute coroutines with limited concurrency

    Args:
        max_concurrent: Maximum number of concurrent tasks
        *coros: Coroutines to execute

    Returns:
        List of results in order

    Example:
        results = await gather_with_concurrency(5, *[fetch(url) for url in urls])
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_coro(coro):
        async with semaphore:
            return await coro

    return await asyncio.gather(*[bounded_coro(c) for c in coros])


async def batch_process(items: list[T], processor: Callable[[T], Any], batch_size: int = 10, max_concurrent: int = 5) -> list[Any]:
    """Process items in batches with concurrency control

    Args:
        items: Items to process
        processor: Async function to process each item
        batch_size: Size of each batch
        max_concurrent: Max concurrent operations within each batch

    Returns:
        List of results

    Example:
        results = await batch_process(files, process_file, batch_size=20)
    """
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]

        if asyncio.iscoroutinefunction(processor):
            batch_coros = [processor(item) for item in batch]
        else:
            # If processor is not async, run it in executor
            loop = asyncio.get_event_loop()
            batch_coros = [loop.run_in_executor(None, processor, item) for item in batch]

        batch_results = await gather_with_concurrency(max_concurrent, *batch_coros)
        results.extend(batch_results)

    return results


def run_async_safe(coro: Callable | Any) -> Any:
    """Safely run an async coroutine from sync context

    Handles existing event loops gracefully.

    Args:
        coro: Coroutine to run

    Returns:
        Result of coroutine

    Example:
        result = run_async_safe(async_function())
    """
    try:
        # Try to get existing event loop
        loop = asyncio.get_running_loop()
        # We're already in an async context
        if asyncio.iscoroutine(coro):
            # Create a task and return a future that can be awaited
            return asyncio.create_task(coro)
        return coro
    except RuntimeError:
        # No event loop, create one
        if asyncio.iscoroutine(coro):
            return asyncio.run(coro)
        if asyncio.iscoroutinefunction(coro):
            return asyncio.run(coro())
        return coro


def async_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """Decorator for retrying async functions

    Args:
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Multiplier for delay on each retry
        exceptions: Exceptions to catch and retry

    Example:
        @async_retry(max_attempts=5, delay=0.5)
        async def flaky_api_call():
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        logger.debug(f"Retry {attempt + 1}/{max_attempts} for {func.__name__}: {e}")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff

            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_error

        return wrapper

    return decorator


def async_timeout(seconds: float):
    """Decorator to add timeout to async functions

    Args:
        seconds: Timeout in seconds

    Example:
        @async_timeout(5.0)
        async def slow_operation():
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except TimeoutError:
                logger.error(f"{func.__name__} timed out after {seconds} seconds")
                raise

        return wrapper

    return decorator


async def run_with_timeout(coro: Callable | Any, timeout: float, default: Any = None) -> Any:
    """Run coroutine with timeout, returning default on timeout

    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
        default: Value to return on timeout

    Returns:
        Result of coroutine or default value
    """
    try:
        if asyncio.iscoroutinefunction(coro):
            return await asyncio.wait_for(coro(), timeout=timeout)
        return await asyncio.wait_for(coro, timeout=timeout)
    except TimeoutError:
        logger.debug(f"Operation timed out after {timeout} seconds")
        return default


async def async_map(func: Callable[[T], Any], items: Iterable[T], max_concurrent: int | None = None) -> list[Any]:
    """Async version of map with concurrency control

    Args:
        func: Function to apply to each item
        items: Items to process
        max_concurrent: Max concurrent operations (None for unlimited)

    Returns:
        List of results

    Example:
        results = await async_map(process_item, items, max_concurrent=10)
    """
    if max_concurrent:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_func(item):
            async with semaphore:
                if asyncio.iscoroutinefunction(func):
                    return await func(item)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, func, item)

    else:

        async def bounded_func(item):
            if asyncio.iscoroutinefunction(func):
                return await func(item)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, item)

    tasks = [bounded_func(item) for item in items]
    return await asyncio.gather(*tasks)


async def async_filter(predicate: Callable[[T], bool], items: Iterable[T], max_concurrent: int | None = None) -> list[T]:
    """Async version of filter with concurrency control

    Args:
        predicate: Async predicate function
        items: Items to filter
        max_concurrent: Max concurrent operations

    Returns:
        Filtered list of items

    Example:
        valid_files = await async_filter(is_valid_file, files)
    """
    items_list = list(items)

    if max_concurrent:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def check_item(item):
            async with semaphore:
                if asyncio.iscoroutinefunction(predicate):
                    return await predicate(item)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, predicate, item)

    else:

        async def check_item(item):
            if asyncio.iscoroutinefunction(predicate):
                return await predicate(item)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, predicate, item)

    results = await asyncio.gather(*[check_item(item) for item in items_list])
    return [item for item, keep in zip(items_list, results, strict=False) if keep]


class AsyncTimer:
    """Context manager for timing async operations

    Example:
        async with AsyncTimer() as timer:
            await some_operation()
        print(f"Operation took {timer.elapsed:.2f} seconds")
    """

    def __init__(self):
        self.start_time = None
        self.end_time = None

    async def __aenter__(self):
        self.start_time = time.perf_counter()
        return self

    async def __aexit__(self, *args):
        self.end_time = time.perf_counter()

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds"""
        if self.end_time is None:
            return time.perf_counter() - self.start_time
        return self.end_time - self.start_time


async def throttle(rate_limit: int, time_window: float = 1.0):
    """Throttle async operations to a specific rate

    Args:
        rate_limit: Maximum operations per time window
        time_window: Time window in seconds

    Example:
        throttler = throttle(10, 1.0)  # 10 ops per second
        for item in items:
            await throttler
            await process_item(item)
    """
    if not hasattr(throttle, "_limiters"):
        throttle._limiters = {}

    key = (rate_limit, time_window)
    if key not in throttle._limiters:
        throttle._limiters[key] = asyncio.Semaphore(rate_limit)

    limiter = throttle._limiters[key]

    async def release_after_delay():
        await asyncio.sleep(time_window)
        limiter.release()

    await limiter.acquire()
    asyncio.create_task(release_after_delay())


def create_async_queue(maxsize: int = 0) -> asyncio.Queue:
    """Create an async queue with proper typing

    Args:
        maxsize: Maximum queue size (0 for unlimited)

    Returns:
        AsyncIO queue
    """
    return asyncio.Queue(maxsize=maxsize)


async def async_chain(*iterables):
    """Chain multiple async iterables

    Example:
        async for item in async_chain(iter1, iter2, iter3):
            process(item)
    """
    for iterable in iterables:
        async for item in iterable:
            yield item


async def run_in_executor(func: Callable, *args, executor=None, **kwargs) -> Any:
    """Run a sync function in an executor

    Args:
        func: Sync function to run
        *args: Positional arguments
        executor: Optional executor (None for default)
        **kwargs: Keyword arguments

    Returns:
        Function result
    """
    loop = asyncio.get_event_loop()
    if kwargs:
        func = partial(func, **kwargs)
    return await loop.run_in_executor(executor, func, *args)


class AsyncLazyLoader:
    """Lazy loader for async resources

    Example:
        loader = AsyncLazyLoader(load_large_dataset)
        # Data not loaded yet
        data = await loader.get()  # Loads on first access
        data2 = await loader.get()  # Returns cached data
    """

    def __init__(self, loader_func: Callable):
        self._loader_func = loader_func
        self._data = None
        self._loaded = False
        self._lock = asyncio.Lock()

    async def get(self) -> Any:
        """Get the lazily loaded data"""
        if self._loaded:
            return self._data

        async with self._lock:
            # Double-check after acquiring lock
            if self._loaded:
                return self._data

            if asyncio.iscoroutinefunction(self._loader_func):
                self._data = await self._loader_func()
            else:
                loop = asyncio.get_event_loop()
                self._data = await loop.run_in_executor(None, self._loader_func)

            self._loaded = True
            return self._data

    def reset(self):
        """Reset the loader to reload data on next access"""
        self._loaded = False
        self._data = None
