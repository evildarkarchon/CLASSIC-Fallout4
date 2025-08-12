"""AsyncCore - Async-first infrastructure for CLASSIC

This module provides the core async infrastructure for the CLASSIC application,
including base classes, utilities, error handling, and sync adapters.
"""

from .base import AsyncBase, AsyncProcessor
from .error_handler import AsyncErrorHandler, AsyncExecutionError, ErrorSeverity
from .resource_manager import AsyncResourceManager, AsyncSemaphorePool
from .sync_adapter import SyncAdapter, create_sync_adapter
from .utils import async_retry, async_timeout, batch_process, gather_with_concurrency, run_async_safe

__all__ = [
    # Base classes
    "AsyncBase",
    # Error handling
    "AsyncErrorHandler",
    "AsyncExecutionError",
    "AsyncProcessor",
    # Resource management
    "AsyncResourceManager",
    "AsyncSemaphorePool",
    "ErrorSeverity",
    # Sync adapters
    "SyncAdapter",
    "async_retry",
    "async_timeout",
    "batch_process",
    "create_sync_adapter",
    # Utilities
    "gather_with_concurrency",
    "run_async_safe",
]
