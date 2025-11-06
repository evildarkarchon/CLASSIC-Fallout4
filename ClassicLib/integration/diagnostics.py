"""Rust runtime diagnostics and health monitoring.

Provides visibility into the Tokio runtime state from Python,
enabling detection of runtime issues and performance monitoring.
"""

from __future__ import annotations

from typing import Any


def get_runtime_stats() -> dict[str, Any] | None:
    """Get Tokio runtime statistics.

    Returns:
        Dictionary with runtime stats, or None if unavailable:
        - worker_threads: Number of worker threads
        - is_healthy: Runtime health status

    Example:
        >>> stats = get_runtime_stats()
        >>> if stats and not stats["is_healthy"]:
        ...     print("Warning: Runtime may be stalled!")
    """
    try:
        import classic_shared

        stats = classic_shared.get_runtime_stats()
        return {
            "worker_threads": stats.worker_threads,
            "is_healthy": stats.is_healthy,
        }
    except (ImportError, AttributeError):
        return None


def is_runtime_healthy() -> bool:
    """Check if Tokio runtime is healthy.

    Returns:
        True if healthy, False if issues detected or unavailable
    """
    try:
        import classic_shared

        return classic_shared.is_runtime_healthy()
    except (ImportError, AttributeError):
        return False


def print_runtime_status() -> None:
    """Print human-readable runtime status."""
    stats = get_runtime_stats()
    if stats is None:
        print("Rust runtime diagnostics not available")
        return

    print("Tokio Runtime Status")
    print("=" * 40)
    print(f"Worker Threads:  {stats['worker_threads']}")
    print(f"Health Status:   {'✓ Healthy' if stats['is_healthy'] else '✗ Issues Detected'}")


__all__ = ["get_runtime_stats", "is_runtime_healthy", "print_runtime_status"]
