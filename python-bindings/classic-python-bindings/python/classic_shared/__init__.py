"""Python module initialization
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_shared import (
    GameId,
    PathHandler,
    RuntimeStats,
    RustPerformanceMonitor,
    StringProcessor,
    __version__,
    get_runtime_stats,
    is_runtime_healthy,
)

__all__ = [
    "GameId",
    "PathHandler",
    "RuntimeStats",
    "RustPerformanceMonitor",
    "StringProcessor",
    "__version__",
    "get_runtime_stats",
    "is_runtime_healthy",
]
