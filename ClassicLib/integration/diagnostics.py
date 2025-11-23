"""Rust runtime diagnostics and health monitoring.

Provides visibility into the Tokio runtime state from Python,
enabling detection of runtime issues and performance monitoring.

Note:
    Runtime statistics require classic_shared v0.2.0+ with diagnostics support.
    Falls back gracefully if not available.
"""

from __future__ import annotations

from typing import Any


def get_runtime_stats() -> dict[str, Any] | None:
    """Get Tokio runtime statistics.

    Returns:
        Dictionary with runtime stats, or None if unavailable:
        - worker_threads: Number of worker threads
        - is_healthy: Runtime health status
        - has_diagnostics: Whether full diagnostics are available

    Example:
        >>> stats = get_runtime_stats()
        >>> if stats and not stats["is_healthy"]:
        ...     print("Warning: Runtime may be stalled!")
    """
    try:
        import classic_shared

        # Check if diagnostics functions are available
        if hasattr(classic_shared, "get_runtime_stats"):
            stats = classic_shared.get_runtime_stats()  # pyright: ignore[reportAttributeAccessIssue]
            return {
                "worker_threads": stats.worker_threads,
                "is_healthy": stats.is_healthy,
                "has_diagnostics": True,
            }
    except ImportError:
        # classic_shared not available at all
        return None


def is_runtime_healthy() -> bool:
    """Check if Tokio runtime is healthy.

    Returns:
        True if healthy or unavailable, False if issues detected

    Note:
        Returns True when diagnostics unavailable to avoid false alarms.
    """
    try:
        import classic_shared

        # Check if health check function is available
        if not hasattr(classic_shared, "is_runtime_healthy"):
            # Assume healthy if classic_shared exists but lacks diagnostics
            return True

        return classic_shared.is_runtime_healthy()  # pyright: ignore[reportAttributeAccessIssue]
    except ImportError:
        # Assume healthy if Rust not available (Python fallbacks work)
        return True


def print_runtime_status() -> None:
    """Print human-readable runtime status."""
    stats = get_runtime_stats()
    if stats is None:
        print("Rust runtime diagnostics not available (classic_shared not loaded)")
        return

    print("Tokio Runtime Status")
    print("=" * 40)

    if not stats.get("has_diagnostics", False):
        print("⚠ Limited diagnostics (classic_shared lacks diagnostics support)")
        print("   Update classic_shared to v0.2.0+ for full runtime statistics")
        return

    print(f"Worker Threads:  {stats['worker_threads']}")
    print(f"Health Status:   {'✓ Healthy' if stats['is_healthy'] else '✗ Issues Detected'}")


__all__ = ["get_runtime_stats", "is_runtime_healthy", "print_runtime_status"]
