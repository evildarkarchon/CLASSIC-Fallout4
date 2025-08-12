"""Resource management utilities for async operations"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncResourceManager:
    """Centralized resource manager for async operations

    Manages lifecycle of async resources with automatic cleanup.

    Example:
        manager = AsyncResourceManager()

        async with manager:
            conn = await manager.acquire_resource('db', create_connection)
            # Use connection
        # All resources cleaned up automatically
    """

    def __init__(self, max_resources: int | None = None):
        """Initialize resource manager

        Args:
            max_resources: Maximum total resources (None for unlimited)
        """
        self._resources: dict[str, Any] = {}
        self._cleanup_handlers: dict[str, Callable] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._max_resources = max_resources
        self._resource_count = 0
        self._closed = False

    async def __aenter__(self):
        """Enter async context"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context with cleanup"""
        await self.cleanup_all()

    async def acquire_resource(self, key: str, factory: Callable, cleanup: Callable | None = None) -> Any:
        """Acquire or create a resource

        Args:
            key: Unique identifier for resource
            factory: Async callable to create resource
            cleanup: Optional async cleanup function

        Returns:
            Resource instance

        Raises:
            RuntimeError: If manager is closed or limit exceeded
        """
        if self._closed:
            raise RuntimeError("Resource manager is closed")

        # Check if resource exists
        if key in self._resources:
            return self._resources[key]

        # Ensure we have a lock for this resource
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        async with self._locks[key]:
            # Double-check after acquiring lock
            if key in self._resources:
                return self._resources[key]

            # Check resource limit
            if self._max_resources and self._resource_count >= self._max_resources:
                raise RuntimeError(f"Resource limit ({self._max_resources}) exceeded")

            # Create resource
            if asyncio.iscoroutinefunction(factory):
                resource = await factory()
            else:
                resource = factory()

            # Store resource and cleanup handler
            self._resources[key] = resource
            if cleanup:
                self._cleanup_handlers[key] = cleanup
            self._resource_count += 1

            logger.debug(f"Acquired resource: {key}")
            return resource

    async def release_resource(self, key: str):
        """Release a specific resource

        Args:
            key: Resource identifier
        """
        if key not in self._resources:
            return

        resource = self._resources[key]

        # Run cleanup handler if exists
        if key in self._cleanup_handlers:
            cleanup = self._cleanup_handlers[key]
            try:
                if asyncio.iscoroutinefunction(cleanup):
                    await cleanup(resource)
                else:
                    cleanup(resource)
            except Exception as e:
                logger.error(f"Error cleaning up resource {key}: {e}")

        # Remove resource
        del self._resources[key]
        if key in self._cleanup_handlers:
            del self._cleanup_handlers[key]
        if key in self._locks:
            del self._locks[key]
        self._resource_count -= 1

        logger.debug(f"Released resource: {key}")

    async def cleanup_all(self):
        """Clean up all resources"""
        if self._closed:
            return

        self._closed = True

        # Clean up all resources
        keys = list(self._resources.keys())
        for key in keys:
            await self.release_resource(key)

        logger.debug("All resources cleaned up")

    def get_resource(self, key: str) -> Any | None:
        """Get existing resource without creating

        Args:
            key: Resource identifier

        Returns:
            Resource if exists, None otherwise
        """
        return self._resources.get(key)

    @property
    def resource_count(self) -> int:
        """Get current resource count"""
        return self._resource_count

    @property
    def resources(self) -> dict[str, Any]:
        """Get copy of current resources"""
        return self._resources.copy()


class AsyncSemaphorePool:
    """Pool of semaphores for fine-grained concurrency control

    Example:
        pool = AsyncSemaphorePool(default_limit=5)

        async with pool.acquire('api_calls', limit=10):
            # Limited to 10 concurrent API calls
            await make_api_call()

        async with pool.acquire('file_io', limit=3):
            # Limited to 3 concurrent file operations
            await read_file()
    """

    def __init__(self, default_limit: int = 10):
        """Initialize semaphore pool

        Args:
            default_limit: Default semaphore limit
        """
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._default_limit = default_limit
        self._locks: dict[str, asyncio.Lock] = {}

    @asynccontextmanager
    async def acquire(self, key: str, limit: int | None = None):
        """Acquire semaphore for resource type

        Args:
            key: Resource type identifier
            limit: Semaphore limit (uses default if None)

        Yields:
            Context with semaphore acquired
        """
        limit = limit or self._default_limit

        # Get or create semaphore
        if key not in self._semaphores:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()

            async with self._locks[key]:
                # Double-check after lock
                if key not in self._semaphores:
                    self._semaphores[key] = asyncio.Semaphore(limit)

        semaphore = self._semaphores[key]

        async with semaphore:
            yield

    def get_semaphore(self, key: str, limit: int | None = None) -> asyncio.Semaphore:
        """Get or create a semaphore

        Args:
            key: Semaphore identifier
            limit: Semaphore limit

        Returns:
            Semaphore instance
        """
        if key not in self._semaphores:
            limit = limit or self._default_limit
            self._semaphores[key] = asyncio.Semaphore(limit)
        return self._semaphores[key]

    def reset(self, key: str | None = None):
        """Reset semaphore(s)

        Args:
            key: Specific semaphore to reset (None for all)
        """
        if key:
            if key in self._semaphores:
                del self._semaphores[key]
            if key in self._locks:
                del self._locks[key]
        else:
            self._semaphores.clear()
            self._locks.clear()


@dataclass
class PooledResource:
    """Resource in a connection pool"""

    resource: Any
    created_at: datetime
    last_used: datetime
    use_count: int = 0
    in_use: bool = False

    def __hash__(self):
        """Make PooledResource hashable based on resource identity"""
        return id(self.resource)


class AsyncConnectionPool:
    """Generic async connection/resource pool

    Example:
        pool = AsyncConnectionPool(
            factory=create_db_connection,
            min_size=2,
            max_size=10,
            max_idle_time=300
        )

        async with pool.acquire() as conn:
            # Use connection
            await conn.execute(query)
        # Connection returned to pool
    """

    def __init__(
        self, factory: Callable, min_size: int = 0, max_size: int = 10, max_idle_time: float | None = 300, cleanup: Callable | None = None
    ):
        """Initialize connection pool

        Args:
            factory: Async callable to create connections
            min_size: Minimum pool size
            max_size: Maximum pool size
            max_idle_time: Max idle time before cleanup (seconds)
            cleanup: Optional cleanup function for connections
        """
        self._factory = factory
        self._cleanup = cleanup
        self._min_size = min_size
        self._max_size = max_size
        self._max_idle_time = max_idle_time

        self._pool: list[PooledResource] = []
        self._in_use: set[PooledResource] = set()
        self._lock = asyncio.Lock()
        self._closed = False
        self._waiters: list[asyncio.Future] = []

        # Start background tasks
        self._maintenance_task = None

    async def initialize(self):
        """Initialize pool with minimum connections"""
        async with self._lock:
            for _ in range(self._min_size):
                resource = await self._create_resource()
                self._pool.append(resource)

        # Start maintenance task
        if self._max_idle_time:
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())

    async def _create_resource(self) -> PooledResource:
        """Create a new pooled resource"""
        if asyncio.iscoroutinefunction(self._factory):
            resource = await self._factory()
        else:
            resource = self._factory()

        return PooledResource(resource=resource, created_at=datetime.now(), last_used=datetime.now())

    async def _maintenance_loop(self):
        """Background task to clean up idle connections"""
        while not self._closed:
            await asyncio.sleep(60)  # Check every minute

            if self._closed:
                break

            async with self._lock:
                now = datetime.now()
                to_remove = []

                for resource in self._pool:
                    if resource.in_use:
                        continue

                    idle_time = (now - resource.last_used).total_seconds()
                    if idle_time > self._max_idle_time and len(self._pool) > self._min_size:
                        to_remove.append(resource)

                for resource in to_remove:
                    await self._cleanup_resource(resource)
                    self._pool.remove(resource)

    async def _cleanup_resource(self, resource: PooledResource):
        """Clean up a resource"""
        if self._cleanup:
            try:
                if asyncio.iscoroutinefunction(self._cleanup):
                    await self._cleanup(resource.resource)
                else:
                    self._cleanup(resource.resource)
            except Exception as e:
                logger.error(f"Error cleaning up resource: {e}")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool

        Yields:
            Connection resource
        """
        resource = await self._acquire()
        try:
            yield resource.resource
        finally:
            await self._release(resource)

    async def _acquire(self) -> PooledResource:
        """Acquire a resource from pool"""
        while True:
            async with self._lock:
                # Check for available resource
                for resource in self._pool:
                    if not resource.in_use:
                        resource.in_use = True
                        resource.last_used = datetime.now()
                        resource.use_count += 1
                        self._in_use.add(resource)
                        return resource

                # Create new resource if under limit
                if len(self._pool) < self._max_size:
                    resource = await self._create_resource()
                    resource.in_use = True
                    resource.use_count = 1
                    self._pool.append(resource)
                    self._in_use.add(resource)
                    return resource

                # Wait for resource to become available
                waiter = asyncio.Future()
                self._waiters.append(waiter)

            # Wait outside lock
            try:
                await waiter
            except asyncio.CancelledError:
                async with self._lock:
                    self._waiters.remove(waiter)
                raise

    async def _release(self, resource: PooledResource):
        """Release resource back to pool"""
        async with self._lock:
            resource.in_use = False
            resource.last_used = datetime.now()
            self._in_use.discard(resource)

            # Wake up a waiter if any
            if self._waiters:
                waiter = self._waiters.pop(0)
                if not waiter.done():
                    waiter.set_result(None)

    async def close(self):
        """Close the pool and clean up all resources"""
        self._closed = True

        # Cancel maintenance task
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass

        # Clean up all resources
        async with self._lock:
            for resource in self._pool:
                await self._cleanup_resource(resource)
            self._pool.clear()
            self._in_use.clear()

            # Cancel all waiters
            for waiter in self._waiters:
                if not waiter.done():
                    waiter.cancel()
            self._waiters.clear()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    @property
    def size(self) -> int:
        """Get current pool size"""
        return len(self._pool)

    @property
    def available(self) -> int:
        """Get number of available resources"""
        return sum(1 for r in self._pool if not r.in_use)

    @property
    def stats(self) -> dict:
        """Get pool statistics"""
        return {
            "total": len(self._pool),
            "in_use": len(self._in_use),
            "available": self.available,
            "waiters": len(self._waiters),
            "min_size": self._min_size,
            "max_size": self._max_size,
        }
