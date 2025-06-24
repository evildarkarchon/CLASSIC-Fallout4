"""
Test suite for thread safety of ThreadSafeLogCache.

This module contains tests that specifically focus on the thread safety
aspects of the ThreadSafeLogCache class.
"""

import concurrent.futures
import random
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache

if TYPE_CHECKING:
    from concurrent.futures import Future


@pytest.fixture
def create_test_logs(tmp_path: Path) -> list[Path]:
    """Create temporary log files for testing."""
    log_dir: Path = tmp_path / "logs"
    log_dir.mkdir()

    # Create test log files
    log_files: list[Any] = []
    for i in range(5):
        log_file: Path = log_dir / f"test_log_{i}.log"
        # Write different content to each log file
        log_file.write_text(f"Log file {i} content\nLine 2\nLine 3\n")
        log_files.append(log_file)

    return log_files


@pytest.mark.thread
class TestThreadSafeLogCacheThreadSafety:
    """Tests specifically for thread safety of ThreadSafeLogCache."""

    def test_concurrent_log_reads(self, create_test_logs: list[Path]) -> None:
        """Test that multiple threads can read logs concurrently without conflicts."""
        log_cache: ThreadSafeLogCache = ThreadSafeLogCache(create_test_logs)

        # Function for threads to execute
        def read_random_log() -> None:
            log_names: list[str] = log_cache.get_log_names()
            for _ in range(10):  # Read multiple times to increase chance of contention
                log_name: str = random.choice(log_names)
                log_content: list[str] = log_cache.read_log(log_name)
                # Verify the content is correct
                assert log_content[0].startswith("Log file ")
                assert len(log_content) == 3

        # Create and start multiple threads
        threads: list[threading.Thread] = []
        for _ in range(10):
            thread: threading.Thread = threading.Thread(target=read_random_log)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

    def test_concurrent_reads_with_threadpool(self, create_test_logs: list[Path]) -> None:
        """Test that ThreadPoolExecutor can use the cache concurrently."""
        log_cache: ThreadSafeLogCache = ThreadSafeLogCache(create_test_logs)
        log_names: list[str] = log_cache.get_log_names()
        results: list[list[str]] = []

        # Create tasks that will read logs
        def read_log_task(log_name: str) -> list[str]:
            time.sleep(random.uniform(0.001, 0.01))  # Small random delay
            return log_cache.read_log(log_name)

        # Use ThreadPoolExecutor to run tasks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Submit 100 tasks that may run concurrently
            futures: list[Future[list[str]]] = [executor.submit(read_log_task, random.choice(log_names)) for _ in
                                                range(100)]

            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                log_content: list[str] = future.result()
                results.append(log_content)

        # Verify that all results are valid
        assert len(results) == 100
        for log_content in results:
            assert log_content[0].startswith("Log file ")
            assert len(log_content) == 3

    def test_reentrant_lock_behavior(self, create_test_logs: list[Path]) -> None:
        """Test that the reentrant lock allows nested lock acquisitions from the same thread."""
        log_cache: ThreadSafeLogCache = ThreadSafeLogCache(create_test_logs)
        log_names: list[str] = log_cache.get_log_names()

        # Create a custom method that acquires the lock twice
        def nested_lock_method() -> list[str]:
            with log_cache.lock:  # First acquisition
                time.sleep(0.01)  # Small delay
                with log_cache.lock:  # Second acquisition (should not block)
                    # If the lock is not reentrant, this would deadlock
                    return log_cache.read_log(log_names[0])

        # The test will time out if the lock is not reentrant
        result: list[str] = nested_lock_method()

        # Verify we got a valid result
        assert len(result) == 3
        assert result[0].startswith("Log file ")


@pytest.mark.thread
class TestThreadSafeLogCacheEdgeCases:
    """Test edge cases for ThreadSafeLogCache."""

    def test_nonexistent_log(self) -> None:
        """Test requesting a log that doesn't exist."""
        log_cache: ThreadSafeLogCache = ThreadSafeLogCache([])  # Empty cache
        result: list[str] = log_cache.read_log("nonexistent_log.log")
        assert result == []

    def test_empty_cache(self) -> None:
        """Test operations on an empty cache."""
        log_cache: ThreadSafeLogCache = ThreadSafeLogCache([])
        assert log_cache.get_log_names() == []

    def test_log_with_invalid_chars(self, tmp_path: Path) -> None:
        """Test handling of logs with invalid UTF-8 characters."""
        # Create a log file with invalid UTF-8
        log_file: Path = tmp_path / "invalid_utf8.log"
        with log_file.open("wb") as f:
            f.write(b"Valid text\n")
            f.write(b"\xff\xfe\xfd\n")  # Invalid UTF-8
            f.write(b"More valid text\n")

        log_cache: ThreadSafeLogCache = ThreadSafeLogCache([log_file])
        result: list[str] = log_cache.read_log("invalid_utf8.log")

        # Should handle invalid UTF-8 with the 'ignore' error strategy
        assert len(result) == 3
        assert result[0] == "Valid text"
        assert result[2] == "More valid text"
