"""
Tests for YamlSettingsCache singleton pattern implementation.

This module validates the core singleton pattern functionality of YamlSettingsCache,
ensuring proper instance creation, thread-safe initialization, and efficient
double-check locking patterns.

Test Categories:
- Singleton instance creation and identity
- Thread-safe singleton creation
- Lock efficiency (double-check locking)
- Module-level yaml_cache proxy integration
"""

import threading
from unittest.mock import patch

import pytest

from ClassicLib.YamlSettings import YamlSettingsCache

pytestmark = pytest.mark.unit


class TestSingletonBehavior:
    """Core singleton pattern tests verifying correct implementation."""

    def test_singleton_instance_creation(self) -> None:
        """
        Test that YamlSettingsCache.get_instance() always returns the same instance.

        This validates that the singleton pattern is correctly implemented with
        proper double-check locking to prevent race conditions during instance creation.
        """
        # Get first instance
        instance1 = YamlSettingsCache.get_instance()
        assert instance1 is not None
        assert isinstance(instance1, YamlSettingsCache)

        # Get second instance - should be the same object
        instance2 = YamlSettingsCache.get_instance()
        assert instance2 is instance1
        assert id(instance1) == id(instance2)

        # Verify class-level storage
        assert YamlSettingsCache._instance is instance1

        # Multiple calls should not create new instances
        for _ in range(10):
            instance = YamlSettingsCache.get_instance()
            assert instance is instance1

    def test_singleton_thread_safety(self) -> None:
        """
        Test that singleton creation is thread-safe under concurrent access.

        This test simulates multiple threads trying to create the singleton
        simultaneously, verifying that only one instance is ever created.
        """
        # Clear any existing instance to test creation
        YamlSettingsCache._instance = None

        instances = []
        errors = []
        barrier = threading.Barrier(10)  # Synchronize thread starts

        def get_instance_thread():
            """Thread function to get singleton instance."""
            try:
                # Wait for all threads to be ready
                barrier.wait()
                # All threads try to get instance simultaneously
                instance = YamlSettingsCache.get_instance()
                instances.append(instance)
            except Exception as e:
                errors.append(e)

        # Create and start threads
        threads = [threading.Thread(target=get_instance_thread) for _ in range(10)]
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors in threads: {errors}"

        # Verify all threads got the same instance
        assert len(instances) == 10
        first_instance = instances[0]
        for instance in instances:
            assert instance is first_instance

    def test_singleton_lock_efficiency(self) -> None:
        """
        Test that the double-check locking pattern is efficient.

        Verifies that after initial creation, getting the instance doesn't
        require acquiring the lock, improving performance.
        """
        # Ensure instance exists
        instance = YamlSettingsCache.get_instance()
        assert instance is not None

        # Mock the lock to verify it's not acquired on fast path
        with patch.object(YamlSettingsCache, "_lock") as mock_lock:
            # Getting existing instance should not acquire lock
            instance2 = YamlSettingsCache.get_instance()
            assert instance2 is instance
            mock_lock.__enter__.assert_not_called()
            mock_lock.__exit__.assert_not_called()

    def test_module_level_yaml_cache_uses_singleton(self) -> None:
        """
        Test that the module-level yaml_cache variable uses the singleton.

        This ensures backward compatibility with code that imports yaml_cache directly.
        Note: The module-level yaml_cache is created at import time using get_instance().
        """
        # Import the module to ensure yaml_cache is initialized
        import importlib
        import sys

        # Force reload to ensure we get the module? No, that might break singletons.
        # Just try to get it.
        YamlSettingsCacheModule = importlib.import_module("ClassicLib.YamlSettings")

        print(f"DEBUG: YamlSettingsCacheModule type: {type(YamlSettingsCacheModule)}")
        print(f"DEBUG: sys.modules['ClassicLib.YamlSettings']: {sys.modules.get('ClassicLib.YamlSettings')}")

        # Get the singleton instance AFTER import
        singleton_instance = YamlSettingsCache.get_instance()

        # Get the module-level cache
        # Handle case where it might resolve to class (though it shouldn't)
        if isinstance(YamlSettingsCacheModule, type):
            # If it's the class, we can't get the module variable from it easily unless we look at sys.modules
            # But wait, if sys.modules has the class, we are in trouble.
            pytest.fail(f"ClassicLib.YamlSettings resolved to a class: {YamlSettingsCacheModule}")

        module_cache = getattr(YamlSettingsCacheModule, "yaml_cache", None)
        assert module_cache is not None, "yaml_cache not found in module"

        # The module_cache is a Proxy object that forwards calls to the singleton
        # It is NOT the singleton instance itself, but acts like it
        # Calling the proxy returns the singleton
        assert module_cache() is singleton_instance

        # Accessing attributes on the proxy should return attributes from the singleton
        # Accessing private attributes requires initialization
        assert module_cache._get_bridge() is singleton_instance._get_bridge()
        assert module_cache._get_async_core() is singleton_instance._get_async_core()
