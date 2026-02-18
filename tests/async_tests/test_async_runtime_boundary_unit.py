"""Unit tests for async runtime boundary helpers."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


def test_run_sync_uses_async_bridge() -> None:
    """run_sync should delegate sync-to-async execution to AsyncBridge."""
    from ClassicLib.core.async_runtime import run_sync

    async def sample() -> int:
        return 42

    with patch("ClassicLib.core.async_runtime.AsyncBridge") as mock_bridge_cls:
        mock_bridge = MagicMock()

        def run_async_side_effect(coro):
            coro.close()
            return 42

        mock_bridge.run_async.side_effect = run_async_side_effect
        mock_bridge_cls.get_instance.return_value = mock_bridge

        result = run_sync(sample())

    assert result == 42
    mock_bridge.run_async.assert_called_once()


def test_run_worker_thread_uses_asyncio_run() -> None:
    """run_worker_thread should use asyncio.run in worker-thread sync paths."""
    from ClassicLib.core.async_runtime import run_worker_thread

    async def sample() -> str:
        return "ok"

    def run_side_effect(coro):
        coro.close()
        return "ok"

    with patch("ClassicLib.core.async_runtime.asyncio.run", side_effect=run_side_effect) as mock_asyncio_run:
        result = run_worker_thread(sample())

    assert result == "ok"
    mock_asyncio_run.assert_called_once()


@pytest.mark.asyncio
async def test_run_sync_rejects_async_context() -> None:
    """run_sync should fail fast if called from async context."""
    from ClassicLib.core.async_runtime import run_sync

    async def sample() -> int:
        return 1

    with pytest.raises(RuntimeError, match="async context"):
        run_sync(sample())


@pytest.mark.asyncio
async def test_run_worker_thread_rejects_async_context() -> None:
    """run_worker_thread should fail fast if called from async context."""
    from ClassicLib.core.async_runtime import run_worker_thread

    async def sample() -> int:
        return 1

    with pytest.raises(RuntimeError, match="async context"):
        run_worker_thread(sample())
