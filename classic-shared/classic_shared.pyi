"""Type stubs for classic_shared Rust module.

This module provides shared foundational utilities used across all Rust crates:
- Global Tokio runtime (ONE RUNTIME RULE)
- Error types and result handling
- Path utilities
- String processing
- Performance monitoring
"""

from __future__ import annotations

from typing import Any

__version__: str

# =============================================================================
# String Processing
# =============================================================================

class StringProcessor:
    """High-performance string processing utilities.

    Provides optimized string operations using Rust's string handling.
    """

    def __init__(self) -> None:
        """Create string processor."""
        ...

    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text.

        Replaces multiple consecutive whitespace with single space,
        trims leading/trailing whitespace.

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace
        """
        ...

    def strip_ansi_codes(self, text: str) -> str:
        """Strip ANSI color codes from text.

        Removes all ANSI escape sequences for clean text output.

        Args:
            text: Text with ANSI codes

        Returns:
            Text without ANSI codes
        """
        ...

    def truncate_middle(self, text: str, max_length: int) -> str:
        """Truncate text in the middle with ellipsis.

        Example: "very_long_filename.txt" → "very_lo...name.txt"

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text with "..." in middle
        """
        ...

    def similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity score between two strings.

        Uses Levenshtein distance algorithm.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score from 0.0 (different) to 1.0 (identical)
        """
        ...


# =============================================================================
# Path Handling
# =============================================================================

class PathHandler:
    """Path handling utilities.

    Provides cross-platform path operations with Windows-specific optimizations.
    """

    def __init__(self) -> None:
        """Create path handler."""
        ...

    def normalize_path(self, path: str) -> str:
        """Normalize a file path.

        Handles:
        - Forward/backslash conversion
        - Case normalization (Windows)
        - Path component cleanup

        Args:
            path: Input path

        Returns:
            Normalized path
        """
        ...

    def is_valid_path(self, path: str) -> bool:
        """Check if path is syntactically valid.

        Args:
            path: Path to check

        Returns:
            True if path syntax is valid
        """
        ...

    def is_absolute(self, path: str) -> bool:
        """Check if path is absolute.

        Args:
            path: Path to check

        Returns:
            True if absolute path
        """
        ...

    def get_extension(self, path: str) -> str:
        """Get file extension from path.

        Args:
            path: File path

        Returns:
            Extension (without dot), empty string if no extension
        """
        ...

    def join_paths(self, paths: list[str]) -> str:
        """Join multiple path components.

        Args:
            paths: List of path components

        Returns:
            Joined path
        """
        ...


# =============================================================================
# Performance Monitoring
# =============================================================================

class PerformanceMonitor:
    """Performance monitoring for Rust components.

    Tracks operation timing and provides statistics.
    """

    def __init__(self) -> None:
        """Create performance monitor."""
        ...

    def start_timing(self, operation: str) -> None:
        """Start timing an operation.

        Args:
            operation: Operation name/identifier
        """
        ...

    def end_timing(self, operation: str) -> float:
        """End timing and get duration.

        Args:
            operation: Operation name

        Returns:
            Duration in seconds

        Raises:
            ValueError: If operation was not started
        """
        ...

    def record_metric(self, name: str, value: float) -> None:
        """Record a performance metric.

        Args:
            name: Metric name
            value: Metric value
        """
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics.

        Returns:
            Dictionary of operation stats including:
                - count: Number of operations
                - total_time: Total time spent
                - avg_time: Average time per operation
                - min_time: Minimum time
                - max_time: Maximum time
        """
        ...

    def reset(self) -> None:
        """Reset all statistics."""
        ...

    def get_summary(self) -> str:
        """Get formatted summary of statistics.

        Returns:
            Human-readable performance summary
        """
        ...


# =============================================================================
# Error Types
# =============================================================================

class ClassicError(Exception):
    """Base error type for all classic-shared errors.

    Provides structured error information with context.
    """

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Create error with message and optional context.

        Args:
            message: Error message
            context: Optional context dictionary
        """
        ...

    def get_context(self) -> dict[str, Any]:
        """Get error context.

        Returns:
            Context dictionary
        """
        ...


# =============================================================================
# Runtime Access
# =============================================================================

def get_runtime_info() -> dict[str, Any]:
    """Get information about the global Tokio runtime.

    Returns:
        Dictionary with runtime info:
            - worker_threads: Number of worker threads
            - active: Whether runtime is active
    """
    ...
