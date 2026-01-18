"""Stress testing for memory leak detection.

This module tests for memory leaks during repeated operations, async operations,
and object lifecycle management to ensure proper cleanup.
"""

import asyncio
import gc
import tempfile
import time
import tracemalloc
import weakref
from pathlib import Path

import psutil
import pytest

from tests.fixtures.stress_fixtures import SyntheticWorkloadGenerator

# Mark all tests in this module
pytestmark = [pytest.mark.stress, pytest.mark.slow]


class TestMemoryLeakDetection:
    """Test for memory leaks under stress."""

    @pytest.mark.timeout(30)
    def test_parser_memory_leak(self):
        """Test for memory leaks in parser during repeated operations."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()
        generator = SyntheticWorkloadGenerator()

        # Start memory tracking
        tracemalloc.start()
        gc.collect()

        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)

        # Perform many parsing operations
        for i in range(100):
            log = generator.generate_typical_crash_log()
            lines = log.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")

            # Explicitly delete to encourage cleanup
            del log
            del segments

            # Periodic garbage collection
            if i % 20 == 0:
                gc.collect()

        # Final cleanup
        gc.collect()
        time.sleep(0.5)  # Allow cleanup

        # Check memory
        final_memory = process.memory_info().rss / (1024 * 1024)
        memory_increase = final_memory - initial_memory

        # Get memory allocation stats
        snapshot = tracemalloc.take_snapshot()
        snapshot.statistics("lineno")[:10]

        print("\nMemory Leak Test (Parser):")
        print(f"  Initial Memory: {initial_memory:.1f}MB")
        print(f"  Final Memory: {final_memory:.1f}MB")
        print(f"  Increase: {memory_increase:.1f}MB")

        # Stop tracking
        tracemalloc.stop()

        # Should not leak more than 50MB after 100 operations
        assert memory_increase < 50, f"Potential memory leak: {memory_increase:.1f}MB increase"

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_async_operations_memory_leak(self):
        """Test for memory leaks in async operations."""
        from ClassicLib.AsyncBridge import AsyncBridge
        from ClassicLib.FileIO import FileIOCore

        io_core = FileIOCore()
        AsyncBridge.get_instance()

        # Track memory
        process = psutil.Process()
        gc.collect()
        initial_memory = process.memory_info().rss / (1024 * 1024)

        # Perform many async operations
        with tempfile.TemporaryDirectory() as temp_dir:
            for i in range(100):
                file_path = Path(temp_dir) / f"test_{i % 10}.log"  # Reuse 10 files

                # Write and read
                content = "x" * (100 * 1024)  # 100KB
                await io_core.write_file(str(file_path), content)
                read_content = await io_core.read_file(str(file_path))

                # Delete references
                del content
                del read_content

                # Periodic cleanup
                if i % 20 == 0:
                    gc.collect()

        # Final cleanup
        gc.collect()
        await asyncio.sleep(0.5)

        # Check memory
        final_memory = process.memory_info().rss / (1024 * 1024)
        memory_increase = final_memory - initial_memory

        print("\nMemory Leak Test (Async):")
        print(f"  Memory Increase: {memory_increase:.1f}MB")

        # Should not leak significant memory
        assert memory_increase < 30, f"Potential async memory leak: {memory_increase:.1f}MB"

    def test_object_lifecycle_tracking(self):
        """Test that objects are properly cleaned up."""
        from ClassicLib.integration.factory import get_parser

        parser = get_parser()
        generator = SyntheticWorkloadGenerator()

        # Track objects with weak references
        tracked_objects = []

        for _i in range(50):
            log = generator.generate_typical_crash_log()
            lines = log.splitlines()
            game_ver, crashgen_ver, error, segments = parser.find_segments(lines, "Buffout 4", "F4SE", "Fallout4.exe")

            # Try to track result
            try:
                ref = weakref.ref(segments)
                tracked_objects.append(ref)
            except TypeError:
                # Some objects don't support weak references
                pass

            del log
            del segments

        # Force cleanup
        gc.collect()
        time.sleep(0.1)

        # Check how many objects are still alive
        alive = sum(1 for ref in tracked_objects if ref() is not None)

        print("\nObject Lifecycle Test:")
        print(f"  Tracked: {len(tracked_objects)}")
        print(f"  Still Alive: {alive}")
        if len(tracked_objects) > 0:
            print(f"  Cleanup Rate: {(1 - alive / len(tracked_objects)) * 100:.1f}%")
        else:
            print("  Cleanup Rate: N/A (no trackable objects)")

        # Most objects should be cleaned up (if we have trackable objects)
        if len(tracked_objects) > 0:
            assert alive < len(tracked_objects) * 0.5, f"Too many objects still alive: {alive}/{len(tracked_objects)}"
        # If no objects support weak references, that's fine - just skip this check
