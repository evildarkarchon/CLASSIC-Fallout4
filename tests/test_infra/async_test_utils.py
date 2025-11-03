"""Async testing utilities for CLASSIC test suite."""

import asyncio
import unittest
from collections.abc import Coroutine
from typing import Any


class AsyncTestCase(unittest.TestCase):
    """Base class for async test cases with proper event loop handling."""

    def setUp(self) -> None:
        """Set up a new event loop for each test."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        super().setUp()

    def tearDown(self) -> None:
        """Clean up the event loop after each test."""
        if self.loop and not self.loop.is_closed():
            self.loop.close()
        super().tearDown()

    def run_async(self, coro: Coroutine[Any, Any, Any]) -> Any:
        """Run an async coroutine in the test event loop.

        Args:
            coro: The coroutine to run

        Returns:
            The result of the coroutine
        """
        return self.loop.run_until_complete(coro)
