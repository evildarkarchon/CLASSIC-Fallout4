"""Type stubs for classic_pybridge.

Python bindings for classic-pybridge-core, providing Rust-accelerated metrics tracking
and runtime coordination for the AsyncBridge.

Architecture:
    - classic-pybridge-core: Business logic (metrics tracking, runtime info)
    - classic-pybridge-py: Python bindings (this module - PyO3 adapters)

Features:
    - Bridge operation metrics tracking
    - Runtime availability checking
    - Performance monitoring for async/sync operations

Usage:
    import classic_pybridge

    # Record an operation
    classic_pybridge.record_operation(
        classic_pybridge.BridgeOperationType.RunAsync,
        0.123,
        True
    )

    # Get metrics
    metrics = classic_pybridge.get_metrics()
    print(f"Total operations: {metrics.run_async_count}")
    print(f"Success rate: {metrics.run_async_success}/{metrics.run_async_count}")

    # Check runtime
    if classic_pybridge.is_runtime_available():
        info = classic_pybridge.get_runtime_info()
        print(f"Worker threads: {info.worker_threads}")
"""


from enum import Enum

__version__: str

class BridgeOperationType(Enum):
    """Bridge operation type for metrics tracking.

    Attributes:
        RunAsync: run_async() operation.
        RunAsyncWithTimeout: run_async_with_timeout() operation.
        LoopCreation: Event loop creation.
        LoopCleanup: Event loop cleanup.

    """

    RunAsync = ...
    RunAsyncWithTimeout = ...
    LoopCreation = ...
    LoopCleanup = ...

class BridgeMetrics:
    """Bridge metrics summary.

    Contains aggregated statistics for all bridge operations including
    counts, success/failure rates, and timing information.

    Attributes:
        run_async_count: Total run_async calls.
        run_async_success: Successful run_async calls.
        run_async_failure: Failed run_async calls.
        run_async_total_time: Total run_async time (seconds).
        timeout_count: Total timeout calls.
        timeout_success: Successful timeout calls.
        timeout_failure: Failed timeout calls.
        timeout_total_time: Total timeout time (seconds).
        loops_created: Loops created.
        loops_cleaned: Loops cleaned up.

    """

    run_async_count: int
    run_async_success: int
    run_async_failure: int
    run_async_total_time: float
    timeout_count: int
    timeout_success: int
    timeout_failure: int
    timeout_total_time: float
    loops_created: int
    loops_cleaned: int


class RuntimeInfo:
    """Runtime information.

    Contains information about the Tokio runtime availability and configuration.

    Attributes:
        available: Whether the runtime is available.
        worker_threads: Number of worker threads.

    """

    available: bool
    worker_threads: int


def record_operation(operation: BridgeOperationType, duration_secs: float, success: bool) -> None:
    """Record a bridge operation for metrics.

    This function records timing and success/failure information for
    async bridge operations.

    Args:
        operation: The type of operation (BridgeOperationType enum).
        duration_secs: Duration of the operation in seconds.
        success: Whether the operation succeeded.

    Example:
        >>> record_operation(
        ...     BridgeOperationType.RunAsync,
        ...     0.123,
        ...     True
        ... )

    """

def get_metrics() -> BridgeMetrics:
    """Get bridge metrics summary.

    Returns aggregated statistics for all bridge operations including
    counts, success/failure rates, and timing information.

    Returns:
        BridgeMetrics: Summary of all bridge operation metrics.

    Example:
        >>> metrics = get_metrics()
        >>> print(f"Total operations: {metrics.run_async_count}")
        >>> print(f"Success rate: {metrics.run_async_success}/{metrics.run_async_count}")

    """

def clear_metrics() -> None:
    """Clear all bridge metrics.

    Removes all recorded metrics. Useful for testing or resetting
    between measurement sessions.

    Example:
        >>> clear_metrics()
        >>> metrics = get_metrics()
        >>> metrics.run_async_count
        0

    """

def is_runtime_available() -> bool:
    """Check if runtime is available.

    Returns:
        True if the Tokio runtime is available.

    Example:
        >>> is_runtime_available()
        True

    """

def get_runtime_info() -> RuntimeInfo:
    """Get runtime information.

    Returns:
        RuntimeInfo: Information about the Tokio runtime.

    Example:
        >>> info = get_runtime_info()
        >>> info.worker_threads
        8

    """
