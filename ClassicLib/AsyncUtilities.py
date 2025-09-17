"""General async utility functions for CLASSIC

This module contains general-purpose async utilities that were previously
in AsyncCore but are still useful for async programming patterns.
"""

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable, Iterable
from concurrent.futures import Executor
from functools import partial, wraps
from types import TracebackType
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

T = TypeVar("T")


async def gather_with_concurrency[T](max_concurrent: int, *coros: Awaitable[T]) -> list[T]:
    """
    Executes multiple asynchronous coroutine tasks concurrently, limiting the number of tasks allowed
    to run at the same time to the specified maximum concurrency.

    This function allows you to set a concurrency limit for running coroutines, which is useful for
    managing resource usage, such as database connections or API calls, that may have constraints
    on simultaneous access.

    Args:
        max_concurrent (int): The maximum number of concurrent tasks allowed to run simultaneously.
        *coros (Awaitable[T]): One or more coroutine tasks to be executed concurrently.

    Returns:
        list[T]: A list of all results returned by the provided coroutine tasks, in the order in
            which they were passed to the function.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_coro(coro: Awaitable[T]) -> T:
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


def async_retry(
    max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Retries the execution of an asynchronous function with customizable parameters for delay,
    backoff strategy, maximum attempts, and specified exception types to handle. This decorator
    is useful when implementing retry logic for operations susceptible to transient failures.

    Args:
        max_attempts (int): The maximum number of retry attempts before raising the last error.
        delay (float): The initial delay between retries in seconds.
        backoff (float): The factor by which the delay increases after each failed attempt.
        exceptions (tuple[type[Exception], ...]): A tuple of exception types to catch and retry upon.

    Returns:
        Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]: A decorator that wraps an
        asynchronous function and applies the retry logic.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        """
        Decorator that retries an asynchronous function with a retry logic.
        The function is retried for a specified number of attempts, with delays
        between attempts increasing geometrically based on a backoff factor.
        If all attempts fail, the last encountered exception is raised.

        Args:
            func (Callable): An asynchronous function to be retried. The
                function must be callable and capable of being awaited.

        Returns:
            Callable: A wrapped version of the input asynchronous function
                that includes retry functionality.

        Raises:
            Exception: The last encountered exception, if all attempts to
                execute the decorated function fail.
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_error = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff

            # Ensure we have a valid exception to raise
            if last_error is None:
                last_error = RuntimeError(f"Function {func.__name__} failed after {max_attempts} attempts with no captured exception")

            raise last_error

        return wrapper

    return decorator


def async_timeout(seconds: float) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Decorator to apply a timeout to an asynchronous function call.

    This decorator ensures that the wrapped asynchronous function completes
    within the specified time limit. If the function exceeds the provided
    time limit, a `TimeoutError` will be raised. The decorator leverages
    `asyncio.wait_for` to enforce the timeout.

    Args:
        seconds: The maximum time, in seconds, that the asynchronous function
            may take to complete execution before a timeout occurs.

    Returns:
        A decorated version of the input function with timeout handling.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        """
        A decorator that enforces a timeout for asynchronous functions.

        The wrapped function will be executed with a timeout limit defined by the `seconds`
        variable. If the execution exceeds this limit, a `TimeoutError` will be raised.

        Args:
            func (Callable): The asynchronous function to be wrapped.

        Returns:
            Callable: The decorated function that enforces the timeout.

        Raises:
            TimeoutError: Raised when the execution time of the function exceeds the
                timeout limit.
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            """
            Wraps an asynchronous function to set a timeout period, ensuring the function
            is executed within the specified time limit. If the function exceeds the given
            timeout duration, an exception is raised.

            Args:
                *args: Positional arguments passed to the wrapped function.
                **kwargs: Keyword arguments passed to the wrapped function.

            Raises:
                TimeoutError: If the wrapped function execution exceeds the specified
                    timeout duration.

            Returns:
                The result of the wrapped asynchronous function.

            """
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except TimeoutError as err:
                raise TimeoutError(f"{func.__name__} timed out after {seconds} seconds") from err

        return wrapper

    return decorator


async def _run_awaitable(coro: Awaitable[T] | Callable[[], Awaitable[T]]) -> T:
    """Internal helper to run an awaitable without timeout handling.

    Returns:
        The result of the awaitable execution.
    """
    # Handle callable case - call it to get the awaitable
    if callable(coro) and not hasattr(coro, "__await__"):
        # coro is a callable that returns an awaitable
        awaitable = coro()
        return await awaitable
    # coro is already an awaitable
    return await coro # pyright: ignore[reportGeneralTypeIssues]


def run_with_timeout(
    coro: Awaitable[T] | Callable[[], Awaitable[T]], timeout_seconds: float, default: T | None = None
) -> Callable[[], Awaitable[T | None]]:
    """Create a coroutine that runs with timeout, returning default on timeout

    This function returns a coroutine that can be awaited. The timeout is handled
    using asyncio.timeout() context manager for cleaner async patterns.

    Args:
        coro: Coroutine or coroutine function to run
        timeout_seconds: Timeout in seconds
        default: Value to return on timeout

    Returns:
        Coroutine function that when awaited returns the result or default

    Example:
        # Create the timeout-wrapped coroutine
        timed_operation = run_with_timeout(some_async_operation(), 5.0, "timeout")

        # Run it with proper timeout handling
        result = await timed_operation()
    """

    async def _timeout_wrapper() -> T | None:
        try:
            # Use asyncio.timeout for proper timeout handling
            async with asyncio.timeout(timeout_seconds):
                return await _run_awaitable(coro)
        except TimeoutError:
            return default

    return _timeout_wrapper


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

        async def bounded_func(item: T) -> Any:
            """
            Executes a function on the given item while ensuring concurrency is
            limited using a semaphore.

            Args:
                item: The input to be processed by the specified function, either
                    as a coroutine or executed in a thread pool.

            Returns:
                The result of the function execution on the provided item.

            Raises:
                Any exception raised by the provided function.
            """
            async with semaphore:
                if asyncio.iscoroutinefunction(func):
                    return await func(item)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, func, item)

    else:

        async def bounded_func(item: T) -> Any:
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

        async def check_item(item: T) -> bool:
            """
            Checks an item against a predicate function.

            This function asynchronously evaluates a given item using the provided
            predicate function. If the predicate is a coroutine function, it is awaited;
            otherwise, it is executed in a separate thread using an executor.

            Args:
                item: The item to be checked against the predicate function.

            Returns:
                Whether the item satisfies the predicate condition.
            """
            async with semaphore:
                if asyncio.iscoroutinefunction(predicate):
                    return await predicate(item)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, predicate, item)

    else:

        async def check_item(item: T) -> bool:
            if asyncio.iscoroutinefunction(predicate):
                return await predicate(item)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, predicate, item)

    results = await asyncio.gather(*[check_item(item) for item in items_list])
    return [item for item, keep in zip(items_list, results, strict=False) if keep]


# noinspection PyUnresolvedReferences
class AsyncTimer:
    """Context manager for timing async operations

    Example:
        async with AsyncTimer() as timer:
            await some_operation()
        print(f"Operation took {timer.elapsed:.2f} seconds")
    """

    def __init__(self) -> None:
        """
        Initializes the attributes required for tracking time within the instance.

        Attributes:
            start_time (float | None): Represents the start time of an event or
                process. It is initialized as None.
            end_time (float | None): Represents the end time of an event or
                process. It is initialized as None.
        """
        self.start_time: float | None = None
        self.end_time: float | None = None

    async def __aenter__(self) -> "AsyncTimer":
        """
        Asynchronous method for entering an asynchronous context manager.

        This method marks the starting point of the context manager's lifecycle.
        It initializes the timing mechanism by recording the current time when the
        context is entered asynchronously.

        Returns:
            self: An instance of the context manager.
        """
        self.start_time = time.perf_counter()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        """
        Handles the asynchronous exit of a context manager and records the end time.

        This method is called upon exiting an asynchronous context manager to
        perform cleanup operations. The time when the context exits is recorded.

        Args:
            exc_type (type[BaseException] | None): The exception type if an exception was raised,
                otherwise None.
            exc_val (BaseException | None): The exception instance if an exception was raised,
                otherwise None.
            exc_tb (TracebackType | None): The traceback object if an exception was raised,
                otherwise None.
        """
        self.end_time = time.perf_counter()

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time is None:
            return 0.0
        if self.end_time is None:
            return time.perf_counter() - self.start_time
        return self.end_time - self.start_time


class Throttler:
    """A testable throttling context manager for rate limiting.

    This class provides a cleaner, more testable alternative to the
    function-based throttle approach. It tracks background tasks and
    provides cleanup methods for testing.

    Example:
        throttler = Throttler(10, 1.0)  # 10 ops per second
        async with throttler:
            await process_item(item)
    """

    def __init__(self, rate_limit: int, time_window: float = 1.0) -> None:
        """Initialize the throttler.

        Args:
            rate_limit: Maximum operations per time window
            time_window: Time window in seconds
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.semaphore = asyncio.Semaphore(rate_limit)
        self.tasks: set[asyncio.Task] = set()

    async def __aenter__(self) -> "Throttler":
        """
        Manages the entry into an asynchronous context, acquiring a semaphore.

        The method is part of a context manager implementation, ensuring that
        the semaphore is acquired when entering the context.

        Returns:
            Throttler: The current instance as a context manager.
        """
        await self.semaphore.acquire()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        """
        Handles the exit from an asynchronous context manager and initiates a delayed
        release process.

        This method performs cleanup and triggers a release mechanism after a specified
        delay, ensuring proper resource management when exiting the context.

        Args:
            exc_type: The exception type, if an exception was raised within the context.
            exc_val: The exception value, if an exception was raised within the context.
            exc_tb: The traceback object, if an exception was raised within the context.
        """
        task = asyncio.create_task(self.release_after_delay())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def release_after_delay(self) -> None:
        """Release the semaphore after the time window."""
        await asyncio.sleep(self.time_window)
        self.semaphore.release()

    async def cleanup(self) -> None:
        """
        Cancels all currently running asynchronous tasks and clears the internal task list.

        This method iterates through all tasks managed by the instance. If a task is not
        yet completed, it sends a cancellation request. It ensures that the cancellation
        is handled properly and suppresses `asyncio.CancelledError` during this process.
        After completing the cancellation process for all tasks, the internal task list is
        cleared.

        Raises:
            asyncio.CancelledError: Suppressed internally for any task cancelled during
            the cleanup process.
        """
        for task in list(self.tasks):
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self.tasks.clear()


# Global throttler registry for backward compatibility
_throttler_registry: dict[tuple[int, float], Throttler] = {}


async def throttle(rate_limit: int, time_window: float = 1.0) -> None:
    """Throttle async operations to a specific rate.

    This is a backward-compatible wrapper that uses the new Throttler class
    internally. For new code, consider using Throttler directly as it's more
    testable and provides cleanup methods.

    Args:
        rate_limit: Maximum operations per time window
        time_window: Time window in seconds

    Example:
        for item in items:
            await throttle(10, 1.0)  # 10 ops per second
            await process_item(item)
    """
    key = (rate_limit, time_window)
    if key not in _throttler_registry:
        _throttler_registry[key] = Throttler(rate_limit, time_window)

    throttler = _throttler_registry[key]
    await throttler.semaphore.acquire()

    # Schedule release
    task = asyncio.create_task(throttler.release_after_delay())
    throttler.tasks.add(task)
    task.add_done_callback(throttler.tasks.discard)


def reset_throttlers() -> None:
    """Reset all throttler state. Useful for testing.

    This function clears the global throttler registry, effectively
    resetting all rate limits. Should be called in test setup/teardown.
    """
    _throttler_registry.clear()


async def run_in_executor[R](func: Callable[..., R], *args: Any, executor: Executor | None = None, **kwargs: Any) -> R:
    """
    Executes a given function in a separate thread or process pool using an executor and
    returns the result asynchronously. This function is useful for running blocking or
    synchronous code in an asynchronous environment.

    Args:
        func (Callable[..., R]): The function to be executed.
        *args (Any): Positional arguments to pass to the function.
        executor (Executor | None): Optional executor to use. If None, the default executor
            is used.
        **kwargs (Any): Keyword arguments to pass to the function.

    Returns:
        R: The result of the executed function.

    Raises:
        Exception: Propagates any exception raised by the executed function.
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

    def __init__(self, loader_func: Callable[[], Any] | Callable[[], Awaitable[Any]]) -> None:
        """
        Initializes an instance to manage and load data asynchronously.

        Args:
            loader_func: A callable function that supplies the data to load. This
                function is invoked when the data is being fetched.
        """
        self._loader_func = loader_func
        self._data = None
        self._loaded = False
        self._lock = asyncio.Lock()

    async def get(self) -> Any:
        """
        Retrieves the data, ensuring it is loaded only once.
        This asynchronous method employs a locking mechanism to ensure safe and efficient
        loading of the data. If the data is already loaded, it returns the cached result.
        Otherwise, it executes the provided loader function to fetch the data, stores the
        fetched data for future invocations, and ensures proper concurrency handling with
        locks.
        Returns:
            Any: The loaded data.
        Raises:
            Exception: Any exception raised during the execution of the loader function.
        """
        if self._loaded:
            return self._data
        async with self._lock:
            # Double-check after acquiring lock
            if self._loaded:
                return self._data
            self._data = await self._load_data()
            self._loaded = True
            return self._data

    # noinspection PyUnresolvedReferences,PyTypeChecker
    async def _load_data(self) -> Any:
        """
        Load data using the configured loader function.
        Handles both synchronous and asynchronous loader functions.
        Returns:
            Any: The loaded data.
        """
        if asyncio.iscoroutinefunction(self._loader_func):
            return await self._loader_func()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._loader_func)

    def reset(self) -> None:
        """
        Reset the loader to reload data on next access.

        This method clears any previously loaded data state. After calling this,
        the data will need to be reloaded when accessed next. It is useful to
        ensure the loader starts fresh without retaining old data.

        Raises:
            None
        """
        self._loaded = False
        self._data = None
        """Reset the loader to reload data on next access"""
        self._loaded = False
        self._data = None
        self._data = None
