"""Type stubs for classic_shared module.

This module provides Python bindings for the pure Rust utilities in classic-shared-core,
including path handling, string processing, and performance monitoring.
"""

__version__: str

class PathHandler:
    """High-performance path handler with caching.

    This class provides Python access to the high-performance path handling
    utilities implemented in Rust.

    Attributes:
        cache_ttl_seconds: Cache time-to-live in seconds (default: 300)

    """

    def __init__(self, cache_ttl_seconds: int = 300) -> None:
        """Create a new PathHandler with optional cache TTL.

        Args:
            cache_ttl_seconds: Cache time-to-live in seconds (default: 300)

        """

    def normalize_path(self, path: str) -> str:
        """Normalize a file path.

        Args:
            path: The path to normalize

        Returns:
            The normalized path

        Raises:
            IOError: If the path cannot be normalized

        """

    def clear_cache(self) -> None:
        """Clear all caches."""

    def cache_stats(self) -> tuple[int, int]:
        """Return cache statistics.

        Returns:
            Tuple of (path_cache_size, validation_cache_size)

        """

    def cleanup_cache(self) -> None:
        """Clean up expired cache entries."""

    def validate_paths_batch(self, paths: list[str]) -> list[tuple[str, bool, str]]:
        """Validate multiple paths in batch.

        Args:
            paths: List of paths to validate

        Returns:
            List of tuples: (path, is_valid, message)

        Note:
            This method releases the GIL during parallel validation, allowing concurrent
            Python threads to continue execution.

        """

    def join_paths(self, base: str, components: list[str]) -> str:
        """Join a base path with path components.

        Args:
            base: Base path
            components: List of path components to join

        Returns:
            The joined path

        """

    def split_path(self, path: str) -> list[str]:
        """Split a path into its components.

        Args:
            path: The path to split

        Returns:
            List of path components

        """

    def get_filename(self, path: str) -> str | None:
        """Get the filename from a path.

        Args:
            path: The path

        Returns:
            The filename, or None if not present

        """

    def get_extension(self, path: str) -> str | None:
        """Get the file extension from a path.

        Args:
            path: The path

        Returns:
            The extension, or None if not present

        """

    def get_parent(self, path: str) -> str | None:
        """Get the parent directory from a path.

        Args:
            path: The path

        Returns:
            The parent directory, or None if at root

        """

    def is_absolute(self, path: str) -> bool:
        """Check if a path is absolute.

        Args:
            path: The path to check

        Returns:
            True if absolute, false otherwise

        """

    def to_absolute(self, path: str, base: str | None = None) -> str:
        """Convert a path to absolute.

        Args:
            path: The path to convert
            base: Optional base directory (uses current directory if None)

        Returns:
            The absolute path

        Raises:
            IOError: If the path cannot be converted to absolute

        """

    def common_prefix(self, paths: list[str]) -> str | None:
        """Find the common prefix of multiple paths.

        Args:
            paths: List of paths to compare

        Returns:
            The common prefix, or None if there isn't one

        """

    def validate_paths_batch_fast(self, paths: list[str]) -> list[tuple[str, bool, str]]:
        """Validate multiple paths in batch (zero-copy optimization).

        Args:
            paths: List of paths to validate

        Returns:
            PyList of tuples: (path, is_valid, message)

        Note:
            Returns PyList of PyTuples directly, avoiding intermediate Vec allocations.
            This provides 3-4x better performance for large batches (100+ paths).

        """

    def cache_metrics(self) -> tuple[int, int, float]:
        """Return cache hit/miss statistics.

        Returns:
            Tuple of (hits, misses, hit_rate)

        """

    def split_path_fast(self, path: str) -> list[str]:
        """Split a path into its components (zero-copy optimization).

        Args:
            path: The path to split

        Returns:
            PyList of path components

        Note:
            Returns PyList directly, reducing allocations by 30-40%.

        """

class StringProcessor:
    """String processor with interning and parallel operations.

    This class provides Python access to the high-performance string processing
    utilities implemented in Rust.
    """

    def __init__(self) -> None:
        """Create a new StringProcessor."""

    def intern(self, s: str) -> str:
        """Intern a string for memory efficiency.

        Args:
            s: The string to intern

        Returns:
            The interned string

        """

    def process_batch(self, strings: list[str], operation: str) -> list[str]:
        """Process multiple strings in parallel.

        Args:
            strings: List of strings to process
            operation: Operation to perform ("upper", "lower", "trim", "normalize")

        Returns:
            List of processed strings

        Note:
            This method releases the GIL during parallel processing, allowing other Python
            threads to run concurrently.

        """

    def common_prefix(self, strings: list[str]) -> str:
        """Find common prefix of multiple strings.

        Args:
            strings: List of strings to compare

        Returns:
            The common prefix, or empty string if none

        Note:
            This method releases the GIL during computation and uses an optimized O(n)
            byte-wise comparison algorithm.

        """

    def split_lines(self, text: str) -> list[str]:
        """Split text into lines efficiently.

        Args:
            text: The text to split

        Returns:
            List of lines

        Note:
            This method releases the GIL during parallel line splitting.

        """

    def join_lines(self, lines: list[str], separator: str) -> str:
        """Join lines with a separator.

        Args:
            lines: List of lines to join
            separator: Separator string

        Returns:
            The joined string

        """

    def pool_stats(self) -> int:
        """Get string pool statistics.

        Returns:
            Number of interned strings

        """

    def clear_pool(self) -> None:
        """Clear the string pool.

        Note: ThreadedRodeo string interner doesn't support clearing.
        This will log a warning and not actually clear the pool.
        To reset the pool, create a new StringProcessor instance.
        """

    def intern_batch(self, strings: list[str]) -> list[str]:
        """Intern multiple strings at once (zero-copy optimization).

        Args:
            strings: List of strings to intern

        Returns:
            PyList of interned strings

        Note:
            This method releases the GIL and provides 2-3x faster bulk interning
            compared to individual intern() calls.

        """

    def process_batch_fast(self, strings: list[str], operation: str) -> list[str]:
        """Process multiple strings in parallel (zero-copy optimization).

        Args:
            strings: List of strings to process
            operation: Operation to perform ("upper", "lower", "trim", "normalize")

        Returns:
            PyList of processed strings

        Note:
            Returns PyList directly instead of Vec<String>, reducing allocations by 40-50%.

        """

    def split_lines_fast(self, text: str) -> list[str]:
        """Split text into lines efficiently (zero-copy optimization).

        Args:
            text: The text to split

        Returns:
            PyList of lines

        Note:
            Returns PyList directly, avoiding Vec<String> allocation and conversion.

        """

    def normalize(self, s: str) -> str:
        """Normalize a string (zero-copy when possible).

        Args:
            s: The string to normalize

        Returns:
            The normalized string

        """

class RustPerformanceMonitor:
    """Performance monitor for Python.

    This class provides Python access to the Rust performance monitoring system.
    """

    def __init__(self) -> None:
        """Create a new RustPerformanceMonitor instance."""

    def start_timer(self, operation: str) -> dict[str, object]:
        """Start timing an operation.

        Returns a dictionary containing the operation name and start time.
        Pass this dictionary to stop_timer() to record the elapsed time.

        Args:
            operation: Name of the operation to time

        Returns:
            Dictionary with "operation" and "start_time" keys

        """

    def stop_timer(self, timer_info: dict[str, object], bytes_processed: int | None = None) -> None:
        """Stop timing an operation and record metrics.

        Args:
            timer_info: Dictionary returned from start_timer()
            bytes_processed: Optional number of bytes processed

        """

    def get_all_stats(self) -> dict[str, dict[str, object]]:
        """Get performance statistics for all operations.

        Returns:
            Dictionary mapping operation names to their statistics

        """

    def get_operation_stats(self, operation: str) -> dict[str, object] | None:
        """Get statistics for a specific operation.

        Args:
            operation: Name of the operation

        Returns:
            Dictionary with statistics, or None if not found

        """

    def clear_metrics(self) -> None:
        """Clear all performance metrics."""

    def record_metric(
        self,
        operation: str,
        duration_ms: int,
        bytes_processed: int | None = None,
    ) -> None:
        """Record a custom metric.

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            bytes_processed: Optional bytes processed

        """

class RuntimeStats:
    """Runtime statistics from Tokio.

    Provides visibility into the Tokio runtime state for diagnostics and monitoring.

    Attributes:
        worker_threads: Number of worker threads in the runtime
        is_healthy: Whether runtime appears healthy

    """

    worker_threads: int
    is_healthy: bool

    def __repr__(self) -> str: ...

def get_runtime_stats() -> RuntimeStats:
    """Get Tokio runtime statistics.

    Returns basic diagnostic information about the shared Tokio runtime.
    Useful for detecting runtime issues in production.

    Returns:
        RuntimeStats object containing worker_threads and is_healthy

    """

def is_runtime_healthy() -> bool:
    """Check if Tokio runtime is healthy.

    Returns:
        True if the runtime appears to be functioning normally.

    """
