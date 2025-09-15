"""
Unit tests for thread_safe_log_cache - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

import concurrent.futures
import random
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
import pytest
from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache

pytestmark = pytest.mark.unit

@pytest.mark.thread
class TestThreadSafeLogCacheThreadSafety:
    """Tests specifically for thread safety of ThreadSafeLogCache."""

    def test_concurrent_log_reads(self, create_test_logs: list[Path]) -> None:
        """Test that multiple threads can read logs concurrently without conflicts."""
        log_cache: ThreadSafeLogCache = ThreadSafeLogCache(create_test_logs)

        def read_random_log() -> None:
            log_names: list[str] = log_cache.get_log_names()
            for _ in range(10):
                log_name: str = random.choice(log_names)
                log_content: list[str] = log_cache.read_log(log_name)
                assert log_content[0].startswith('Log file ')
                assert len(log_content) == 3
        threads: list[threading.Thread] = []
        for _ in range(10):
            thread: threading.Thread = threading.Thread(target=read_random_log)
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()

    def test_concurrent_reads_with_threadpool(self, create_test_logs: list[Path]) -> None:
        """Test that ThreadPoolExecutor can use the cache concurrently."""
        log_cache: ThreadSafeLogCache = ThreadSafeLogCache(create_test_logs)
        log_names: list[str] = log_cache.get_log_names()
        results: list[list[str]] = []

        def read_log_task(log_name: str) -> list[str]:
            time.sleep(random.uniform(0.001, 0.01))
            return log_cache.read_log(log_name)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures: list[Future[list[str]]] = [executor.submit(read_log_task, random.choice(log_names)) for _ in range(100)]
            for future in concurrent.futures.as_completed(futures):
                log_content: list[str] = future.result()
                results.append(log_content)
        assert len(results) == 100
        for log_content in results:
            assert log_content[0].startswith('Log file ')
            assert len(log_content) == 3

    def test_reentrant_lock_behavior(self, create_test_logs: list[Path]) -> None:
        """Test that the reentrant lock allows nested lock acquisitions from the same thread."""
        log_cache: ThreadSafeLogCache = ThreadSafeLogCache(create_test_logs)
        log_names: list[str] = log_cache.get_log_names()

        def nested_lock_method() -> list[str]:
            with log_cache.lock:
                time.sleep(0.01)
                with log_cache.lock:
                    return log_cache.read_log(log_names[0])
        result: list[str] = nested_lock_method()
        assert len(result) == 3
        assert result[0].startswith('Log file ')

@pytest.mark.thread
class TestThreadSafeLogCacheEdgeCases:
    """Test edge cases for ThreadSafeLogCache."""

    def test_nonexistent_log(self) -> None:
        """Test requesting a log that doesn't exist."""
        log_cache: ThreadSafeLogCache = ThreadSafeLogCache([])
        result: list[str] = log_cache.read_log('nonexistent_log.log')
        assert result == []

    def test_empty_cache(self) -> None:
        """Test operations on an empty cache."""
        log_cache: ThreadSafeLogCache = ThreadSafeLogCache([])
        assert log_cache.get_log_names() == []
