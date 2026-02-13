"""Unified Async Utilities for CLASSIC.

This module consolidates general-purpose async utilities, including:
- Concurrency control (gather_with_concurrency, Throttler)
- Smart executor management (smart_run_in_executor)
- Async patterns (retry, timeout, lazy loading)
- Batch processing helpers

This replaces the legacy ClassicLib.AsyncUtilities and ClassicLib.AsyncUtilities_Enhanced modules.
"""

import asyncio
import contextlib
import inspect
import time
from collections.abc import Awaitable, Callable, Iterable
from concurrent.futures import Executor
from functools import partial, wraps
from types import TracebackType
from typing import Any, ParamSpec, TypeVar, cast

# -----------------------------------------------------------------------------
# Type Definitions
# -----------------------------------------------------------------------------
P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")

# -----------------------------------------------------------------------------
# Constants & Configuration
# -----------------------------------------------------------------------------

# Operations that are fast enough to run directly without executor overhead
# These have been profiled to complete in < 1ms on average
FAST_PATH_OPERATIONS = {
    # Path operations (filesystem metadata)
    "exists",
    "is_file",
    "is_dir",
    "is_symlink",
    "is_mount",
    "is_absolute",
    "is_relative_to",
    "stat",
    "lstat",
    "resolve",
    "absolute",
    "expanduser",
    "cwd",
    "home",
    "samefile",
    "parent",
    "name",
    "suffix",
    "stem",
    # String operations (all are CPU-bound but very fast)
    "split",
    "rsplit",
    "join",
    "strip",
    "lstrip",
    "rstrip",
    "upper",
    "lower",
    "capitalize",
    "title",
    "swapcase",
    "replace",
    "find",
    "rfind",
    "index",
    "rindex",
    "startswith",
    "endswith",
    "isalpha",
    "isdigit",
    "isalnum",
    "isspace",
    "isupper",
    "islower",
    # Fast built-ins
    "len",
    "bool",
    "int",
    "float",
    "str",
    "repr",
    "hash",
    "id",
    "type",
    "isinstance",
    "issubclass",
    "hasattr",
    "getattr",
    "setattr",
    "delattr",
    # Fast collections operations
    "append",
    "extend",
    "insert",
    "remove",
    "pop",
    "clear",
    "count",
    "reverse",
    "sort",
    "get",
    "keys",
    "values",
    "items",
    "update",
    # Fast Path operations that don't involve actual I/O
    "mkdir",  # Creating directories is near-instant on modern filesystems
    "joinpath",
    "with_name",
    "with_suffix",
    "with_stem",
    "parts",
    "parents",
    "anchor",
    "drive",
    "root",
}

# Operations that should use executor based on size/complexity
SIZE_DEPENDENT_OPERATIONS = {
    "read_text",
    "read_bytes",
    "write_text",
    "write_bytes",
    "open",
    "unlink",
    "rename",
    "replace",
    "chmod",
    "rmdir",
    "touch",
    "symlink_to",
    "hardlink_to",
}


# -----------------------------------------------------------------------------
# Base Async Utilities
# -----------------------------------------------------------------------------


async def gather_with_concurrency[T](max_concurrent: int, *coros: Awaitable[T]) -> list[T]:
    """Execute multiple asynchronous coroutine tasks concurrently, limiting the number of tasks allowed
    to run at the same time to the specified maximum concurrency.

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

    return await asyncio.gather(*[bounded_coro(c) for c in coros], return_exceptions=False)


async def run_in_executor[R](func: Callable[..., R], *args: Any, executor: Executor | None = None, **kwargs: Any) -> R:
    """Execute a given function in a separate thread or process pool using an executor.

    Args:
        func (Callable[..., R]): The function to be executed.
        *args (Any): Positional arguments to pass to the function.
        executor (Executor | None): Optional executor to use. If None, the default executor is used.
        **kwargs (Any): Keyword arguments to pass to the function.

    Returns:
        R: The result of the executed function.

    """
    loop = asyncio.get_running_loop()
    if kwargs:
        func = partial(func, **kwargs)
    return await loop.run_in_executor(executor, func, *args)


# -----------------------------------------------------------------------------
# Smart Executor Logic
# -----------------------------------------------------------------------------


class ExecutorDecisionMaker:
    """Helper class to encapsulate executor decision logic."""

    def __init__(self, func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any], threshold_bytes: int) -> None:
        """Initialize the executor decision maker.

        Args:
            func: The function to be executed
            args: Positional arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            threshold_bytes: Size threshold in bytes for determining executor usage
                           for I/O operations (files smaller than this run directly)

        """
        self.func = func
        self.args = args  # pyright: ignore[reportUnknownVariableType]
        self.kwargs = kwargs  # pyright: ignore[reportUnknownVariableType]
        self.threshold_bytes = threshold_bytes
        self.func_name = getattr(func, "__name__", "")

    async def _run_with_executor(self) -> Any:
        """Run the function using the thread pool executor.

        Returns:
            The result of the function execution.

        """
        loop = asyncio.get_running_loop()
        if self.kwargs:
            from functools import partial  # pyright: ignore[reportUnknownVariableType]

            func = partial(self.func, **self.kwargs)  # pyright: ignore[reportUnknownVariableType]
            return await loop.run_in_executor(None, func, *self.args)  # pyright: ignore[reportUnknownVariableType]
        return await loop.run_in_executor(None, self.func, *self.args)  # pyright: ignore[reportUnknownVariableType]

    def _run_directly(self) -> Any:
        """Run the function directly without executor.

        Returns:
            The result of the function execution.

        """
        return self.func(*self.args, **self.kwargs)

    def _should_use_executor_for_io(self) -> bool:
        """Determine if I/O operation should use executor based on size.

        Returns:
            True if the operation should use an executor, False if it can run directly.

        """
        if not self.args:
            return True

        from pathlib import Path

        first_arg = self.args[0]

        if not isinstance(first_arg, (Path, str)):
            return True

        try:
            path = Path(first_arg) if isinstance(first_arg, str) else first_arg

            # Check read operations
            if self.func_name in {"read_text", "read_bytes"}:
                if path.exists():
                    return path.stat().st_size >= self.threshold_bytes

            # Check write operations
            elif self.func_name in {"write_text", "write_bytes"} and len(self.args) > 1:
                content = self.args[1]
                if isinstance(content, (str, bytes)):
                    return len(content) >= self.threshold_bytes

        except (OSError, AttributeError, IndexError):
            return True  # Default to executor on error
        else:
            return True  # Default to executor if no specific condition matched

    async def execute(self, force_executor: bool | None) -> Any:
        """Execute the function with the appropriate strategy.

        Args:
            force_executor: If True, always use executor; if False, run directly;
                if None, auto-detect based on operation type.

        Returns:
            The result of the function execution.

        """
        # Handle explicit override
        if force_executor is True:
            return await self._run_with_executor()
        if force_executor is False:
            return self._run_directly()

        # Auto-detection: Fast path operations
        if self.func_name in FAST_PATH_OPERATIONS:
            return self._run_directly()

        # Auto-detection: Size-dependent operations
        if self.func_name in SIZE_DEPENDENT_OPERATIONS and not self._should_use_executor_for_io():
            return self._run_directly()

        # Default: use executor
        return await self._run_with_executor()


async def smart_run_in_executor[R](
    func: Callable[..., R],
    *args: Any,
    threshold_bytes: int = 1024,  # 1KB threshold for I/O operations
    force_executor: bool | None = None,
    **kwargs: Any,
) -> R:
    """Performance-aware executor that only uses thread pool for operations that benefit from it.

    Decision Logic:
    1. If force_executor is True/False, honor that explicitly
    2. Fast path operations (filesystem metadata, string ops) run directly
    3. I/O operations check file size - small files run directly
    4. Unknown operations default to executor for safety

    Args:
        func: The function to execute.
        *args: Positional arguments for the function.
        threshold_bytes: Size threshold for I/O operations (default 1KB).
        force_executor: Override auto-detection (True=always executor, False=never).
        **kwargs: Keyword arguments for the function.

    Returns:
        The result of the function execution.

    """
    decision_maker = ExecutorDecisionMaker(func, args, kwargs, threshold_bytes)
    return await decision_maker.execute(force_executor)


# -----------------------------------------------------------------------------
# Batch Processing & Mapping
# -----------------------------------------------------------------------------


async def async_map[T](func: Callable[[T], Any], items: Iterable[T], max_concurrent: int | None = None) -> list[Any]:
    """Async version of map with concurrency control.

    Args:
        func: Function to apply to each item (sync or async).
        items: Items to process.
        max_concurrent: Maximum concurrent operations (None for unlimited).

    Returns:
        List of results from applying func to each item.

    """
    if max_concurrent:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_func(item: T) -> Any:
            async with semaphore:
                if inspect.iscoroutinefunction(func):
                    return await func(item)
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, func, item)

    else:

        async def bounded_func(item: T) -> Any:
            if inspect.iscoroutinefunction(func):
                return await func(item)
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, func, item)

    tasks = [bounded_func(item) for item in items]
    return await asyncio.gather(*tasks, return_exceptions=False)


async def async_map_smart[T](
    func: Callable[[T], Any], items: list[T], max_concurrent: int | None = None, use_executor: bool | str = "auto"
) -> list[Any]:
    """Enhanced async map with intelligent executor usage.

    Args:
        func: Function to apply to each item
        items: Items to process
        max_concurrent: Maximum concurrent operations (None for unlimited)
        use_executor: Executor usage strategy ("auto", "always", "never", "profile")

    Returns:
        List of results from applying func to each item.

    """
    if use_executor == "profile" and items:
        # Profile mode - run a sample to determine best strategy
        sample_item = items[0]

        # Time with executor
        start = time.perf_counter()
        if inspect.iscoroutinefunction(func):
            await func(sample_item)
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, func, sample_item)
        with_executor_time = time.perf_counter() - start

        # Time without executor (if not async)
        without_executor_time = float("inf")
        if not inspect.iscoroutinefunction(func):
            start = time.perf_counter()
            func(sample_item)
            without_executor_time = time.perf_counter() - start

        # Choose strategy based on profiling
        # If direct execution is > 2x faster, avoid executor
        use_executor = "never" if without_executor_time * 2 < with_executor_time else "always"

        # Log the decision for debugging
        from ClassicLib.core.logger import logger

        logger.debug(
            f"Profiled {func.__name__ if hasattr(func, '__name__') else 'function'}: "
            f"executor={with_executor_time:.4f}s, direct={without_executor_time:.4f}s, "
            f"strategy={use_executor}"
        )

    # Build the execution strategy
    if max_concurrent:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_func(item: T) -> Any:
            async with semaphore:
                if inspect.iscoroutinefunction(func):
                    return await func(item)
                if use_executor == "never":
                    # Direct execution for fast operations
                    return func(item)
                if use_executor == "auto":
                    # Smart detection
                    return await smart_run_in_executor(func, item)
                # "always"
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, func, item)

    else:

        async def bounded_func(item: T) -> Any:
            if inspect.iscoroutinefunction(func):
                return await func(item)
            if use_executor == "never":
                return func(item)
            if use_executor == "auto":
                return await smart_run_in_executor(func, item)
            # "always"
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, func, item)

    tasks = [bounded_func(item) for item in items]
    return await asyncio.gather(*tasks, return_exceptions=False)


async def batch_process[T](items: list[T], processor: Callable[[T], Any], batch_size: int = 10, max_concurrent: int = 5) -> list[Any]:
    """Process items in batches with concurrency control.

    Args:
        items: Items to process.
        processor: Function to process each item (sync or async).
        batch_size: Number of items per batch.
        max_concurrent: Maximum concurrent operations within each batch.

    Returns:
        List of results from processing all items.

    """
    results: list[Any] = []

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]

        if inspect.iscoroutinefunction(processor):
            batch_coros = [processor(item) for item in batch]
        else:
            # If processor is not async, run it in executor
            loop = asyncio.get_running_loop()
            batch_coros = [loop.run_in_executor(None, processor, item) for item in batch]

        batch_results = await gather_with_concurrency(max_concurrent, *batch_coros)
        results.extend(batch_results)

    return results


async def batch_process_smart[T](
    items: list[T], processor: Callable[[T], Any], batch_size: int = 10, max_concurrent: int = 5, use_executor: bool | str = "auto"
) -> list[Any]:
    """Enhanced batch processing with intelligent executor usage.

    Args:
        items: Items to process
        processor: Function to process each item
        batch_size: Size of each batch
        max_concurrent: Max concurrent operations within each batch
        use_executor: Executor usage strategy (see async_map_smart for options)

    Returns:
        List of results from processing all items.

    """
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]

        if inspect.iscoroutinefunction(processor):
            batch_coros = [processor(item) for item in batch]
        elif use_executor == "never":
            # Fast path - run directly without executor
            batch_results_sync = [processor(item) for item in batch]
            results.extend(batch_results_sync)
            continue
        elif use_executor == "auto":
            # Smart detection per item
            batch_coros = [smart_run_in_executor(processor, item) for item in batch]
        else:  # "always" or True
            # Legacy behavior
            loop = asyncio.get_running_loop()
            batch_coros = [loop.run_in_executor(None, processor, item) for item in batch]

        batch_results = await gather_with_concurrency(max_concurrent, *batch_coros)
        results.extend(batch_results)

    return results  # pyright: ignore[reportUnknownVariableType]


async def async_filter_smart[T](
    predicate: Callable[[T], bool] | Callable[[T], Awaitable[bool]],
    items: Iterable[T],
    max_concurrent: int | None = None,
    use_executor: bool | str = "auto",
) -> list[T]:
    """Async version of filter with concurrency control and smart executor usage.

    Args:
        predicate: Boolean function (sync or async) to apply to each item
        items: Items to process
        max_concurrent: Maximum concurrent operations (None for unlimited)
        use_executor: Executor usage strategy ("auto", "always", "never")

    Returns:
        List of items for which the predicate returned True.

    """
    items_list = list(items)
    is_async_predicate = inspect.iscoroutinefunction(predicate)

    if max_concurrent:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def check_item(item: T) -> bool:
            async with semaphore:
                if is_async_predicate:
                    async_pred = cast("Callable[[T], Awaitable[bool]]", predicate)
                    return await async_pred(item)
                sync_pred = cast("Callable[[T], bool]", predicate)
                if use_executor == "never":
                    return sync_pred(item)
                if use_executor == "auto":
                    return await smart_run_in_executor(sync_pred, item)
                # "always"
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, sync_pred, item)

    else:

        async def check_item(item: T) -> bool:
            if is_async_predicate:
                async_pred = cast("Callable[[T], Awaitable[bool]]", predicate)
                return await async_pred(item)
            sync_pred = cast("Callable[[T], bool]", predicate)
            if use_executor == "never":
                return sync_pred(item)
            if use_executor == "auto":
                return await smart_run_in_executor(sync_pred, item)
            # "always"
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, sync_pred, item)

    results = await asyncio.gather(*[check_item(item) for item in items_list], return_exceptions=False)
    return [item for item, keep in zip(items_list, results, strict=False) if keep]


async def async_filter[T](
    predicate: Callable[[T], bool] | Callable[[T], Awaitable[bool]],
    items: Iterable[T],
    max_concurrent: int | None = None,
) -> list[T]:
    """Async version of filter with concurrency control (legacy wrapper).

    Args:
        predicate: Boolean function (sync or async) to apply to each item
        items: Items to filter
        max_concurrent: Maximum concurrent operations (None for unlimited)

    Returns:
        List of items for which the predicate returned True

    """
    return await async_filter_smart(predicate, items, max_concurrent, use_executor="always")


# -----------------------------------------------------------------------------
# Decorators & Context Managers
# -----------------------------------------------------------------------------


def async_retry(
    max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorate to retry an async function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier for delay after each retry.
        exceptions: Tuple of exception types to catch and retry.

    Returns:
        Decorator function that wraps async functions with retry logic.

    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
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

            if last_error is None:
                last_error = RuntimeError(f"Function {func.__name__} failed after {max_attempts} attempts with no captured exception")

            raise last_error

        return wrapper

    return decorator


def async_timeout(seconds: float) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorate to apply a timeout to an asynchronous function call.

    Args:
        seconds: Maximum time in seconds before raising TimeoutError.

    Returns:
        Decorator function that wraps async functions with timeout logic.

    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except TimeoutError as err:
                raise TimeoutError(f"{func.__name__} timed out after {seconds} seconds") from err

        return wrapper

    return decorator


async def _run_awaitable[T](coro: Awaitable[T] | Callable[[], Awaitable[T]]) -> T:
    """Provide internal helper to run an awaitable without timeout handling.

    Args:
        coro: Either an awaitable or a callable returning an awaitable.

    Returns:
        The result of awaiting the coroutine.

    """
    if callable(coro) and not hasattr(coro, "__await__"):
        awaitable = coro()
        return await awaitable
    return await coro  # type: ignore[misc]  # Union type handling for callable vs awaitable


def run_with_timeout[T](
    coro: Awaitable[T] | Callable[[], Awaitable[T]], timeout_seconds: float, default: T | None = None
) -> Callable[[], Awaitable[T | None]]:
    """Create a coroutine that runs with timeout, returning default on timeout.

    Args:
        coro: Either an awaitable or a callable returning an awaitable.
        timeout_seconds: Maximum time in seconds before timeout.
        default: Value to return if timeout occurs.

    Returns:
        A callable that returns an awaitable with timeout handling.

    """

    async def _timeout_wrapper() -> T | None:
        try:
            async with asyncio.timeout(timeout_seconds):
                return await _run_awaitable(coro)
        except TimeoutError:
            return default

    return _timeout_wrapper


class AsyncTimer:
    """Context manager for timing async operations."""

    def __init__(self) -> None:
        self.start_time: float | None = None
        self.end_time: float | None = None

    async def __aenter__(self) -> "AsyncTimer":
        self.start_time = time.perf_counter()
        return self

    async def __aexit__(self, _exc_type: type[BaseException] | None, _exc_val: BaseException | None, _exc_tb: TracebackType | None) -> None:
        self.end_time = time.perf_counter()

    @property
    def elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        if self.end_time is None:
            return time.perf_counter() - self.start_time
        return self.end_time - self.start_time


class Throttler:
    """A testable throttling context manager for rate limiting."""

    def __init__(self, rate_limit: int, time_window: float = 1.0) -> None:
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.semaphore = asyncio.Semaphore(rate_limit)
        self.tasks: set[asyncio.Task[Any]] = set()

    async def __aenter__(self) -> "Throttler":
        await self.semaphore.acquire()
        return self

    async def __aexit__(self, _exc_type: type[BaseException] | None, _exc_val: BaseException | None, _exc_tb: TracebackType | None) -> None:
        task: asyncio.Task[Any] = asyncio.create_task(self.release_after_delay())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def release_after_delay(self) -> None:
        await asyncio.sleep(self.time_window)
        self.semaphore.release()

    async def cleanup(self) -> None:
        for task in list(self.tasks):  # pyright: ignore[reportUnknownVariableType]
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self.tasks.clear()


# Global throttler registry for backward compatibility
_throttler_registry: dict[tuple[int, float], Throttler] = {}


async def throttle(rate_limit: int, time_window: float = 1.0) -> None:
    """Throttle async operations to a specific rate (Legacy helper)."""
    key = (rate_limit, time_window)
    if key not in _throttler_registry:
        _throttler_registry[key] = Throttler(rate_limit, time_window)

    throttler = _throttler_registry[key]
    await throttler.semaphore.acquire()

    task = asyncio.create_task(throttler.release_after_delay())
    throttler.tasks.add(task)
    task.add_done_callback(throttler.tasks.discard)


def reset_throttlers() -> None:
    """Reset all throttler state."""
    _throttler_registry.clear()


class AsyncLazyLoader:
    """Lazy loader for async resources."""

    def __init__(self, loader_func: Callable[[], Any] | Callable[[], Awaitable[Any]]) -> None:
        self._loader_func = loader_func
        self._data = None
        self._loaded = False
        self._lock = asyncio.Lock()

    async def get(self) -> Any:
        if self._loaded:
            return self._data
        async with self._lock:
            if self._loaded:
                return self._data
            self._data = await self._load_data()
            self._loaded = True
            return self._data

    async def _load_data(self) -> Any:
        if inspect.iscoroutinefunction(self._loader_func):
            return await self._loader_func()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._loader_func)

    def reset(self) -> None:
        """Reset the loader to reload data on next access."""
        self._loaded = False
        self._data = None
