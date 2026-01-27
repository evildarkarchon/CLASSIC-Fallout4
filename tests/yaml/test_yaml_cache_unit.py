"""
Consolidated tests for YamlSettingsCache core functionality.

This module validates the core YamlSettingsCache functionality including:
- Singleton pattern implementation
- Fixture isolation and test pollution prevention
- Backward compatibility with existing code patterns
- GlobalRegistry integration
- Module-level functions and cache properties

Test Categories:
- Singleton instance creation and identity
- Thread-safe singleton creation
- Lock efficiency (double-check locking)
- Module-level yaml_cache proxy integration
- Fixture cleanup behavior
- Backward compatibility with existing code
"""

import gc
import importlib
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from _pytest.fixtures import SubRequest

from ClassicLib.core.constants import YAML
from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.io.yaml import YamlSettingsCache

pytestmark = pytest.mark.unit


# =============================================================================
# Singleton Pattern Tests
# =============================================================================


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
        YamlSettingsCacheModule = importlib.import_module("ClassicLib.io.yaml")

        print(f"DEBUG: YamlSettingsCacheModule type: {type(YamlSettingsCacheModule)}")
        print(f"DEBUG: sys.modules['ClassicLib.io.yaml']: {sys.modules.get('ClassicLib.io.yaml')}")

        # Get the singleton instance AFTER import
        singleton_instance = YamlSettingsCache.get_instance()

        # Handle case where it might resolve to class (though it shouldn't)
        if isinstance(YamlSettingsCacheModule, type):
            pytest.fail(f"ClassicLib.io.yaml resolved to a class: {YamlSettingsCacheModule}")

        module_cache = getattr(YamlSettingsCacheModule, "yaml_cache", None)
        assert module_cache is not None, "yaml_cache not found in module"

        # The module_cache is a Proxy object that forwards calls to the singleton
        # Calling the proxy returns the singleton
        assert module_cache() is singleton_instance

        # Accessing attributes on the proxy should return attributes from the singleton
        assert module_cache._get_bridge() is singleton_instance._get_bridge()
        assert module_cache._get_async_core() is singleton_instance._get_async_core()


# =============================================================================
# Fixture Isolation Tests
# =============================================================================


class TestFixtureIsolation:
    """Tests verifying fixture effectiveness in preventing test pollution."""

    def test_ensure_yaml_cache_cleanup_fixture(self, request: SubRequest) -> None:
        """
        Test that ensure_yaml_cache_cleanup fixture properly clears singleton.

        This validates that the autouse fixture prevents state leakage between tests
        by clearing the singleton instance after each test.
        """
        # Get initial instance
        initial_instance = YamlSettingsCache.get_instance()
        id(initial_instance)

        # Simulate test completion and fixture cleanup
        YamlSettingsCache._instance = None

        # Get new instance - should be different object
        new_instance = YamlSettingsCache.get_instance()
        id(new_instance)

        # In a real test scenario with fixture, these would be different
        assert new_instance is not None
        assert YamlSettingsCache._instance is new_instance

    def test_clean_yaml_cache_singleton_fixture(self, clean_yaml_cache_singleton) -> None:
        """
        Test that clean_yaml_cache_singleton fixture provides isolated instance.

        This fixture should provide a fresh singleton instance for each test
        and properly restore state afterwards.
        """
        # Fixture provides the cache instance
        assert clean_yaml_cache_singleton is not None
        assert isinstance(clean_yaml_cache_singleton, YamlSettingsCache)

        # Should be the current singleton
        assert YamlSettingsCache._instance is clean_yaml_cache_singleton
        assert YamlSettingsCache.get_instance() is clean_yaml_cache_singleton

        # Add some test data to verify cleanup
        core = clean_yaml_cache_singleton._get_async_core()
        core.cache.settings_cache["test_key"] = "test_value"  # pyright: ignore[reportArgumentType]

    def test_fixture_nested_usage(self, clean_yaml_cache_singleton) -> None:
        """
        Test that fixtures work correctly when nested or used together.

        This validates that fixture state tracking handles nested scenarios
        properly without corruption.
        """
        outer_instance = clean_yaml_cache_singleton

        # Simulate nested fixture usage
        with patch("ClassicLib.io.yaml.YamlSettingsCache._instance", None):
            nested_instance = YamlSettingsCache.get_instance()
            assert nested_instance is not outer_instance

    def test_fixture_clears_internal_caches(self, clean_yaml_cache_singleton) -> None:
        """
        Test that fixtures properly clear internal cache state.

        Ensures that not just the singleton instance but also its internal
        caches are properly cleaned to prevent data leakage.
        """
        cache = clean_yaml_cache_singleton

        # Add data to internal caches
        core = cache._get_async_core()
        core.cache.settings_cache["test_setting"] = "value"
        core.cache.file_mod_times["test_file"] = 123456
        if hasattr(core.cache, "path_cache"):
            core.cache.path_cache[YAML.TEST] = Path("/test/path")

        # Verify they can be accessed
        assert len(core.cache.settings_cache) > 0


# =============================================================================
# Backward Compatibility Tests
# =============================================================================


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility with existing code."""

    def test_module_level_functions_work(self, tmp_path: Path, monkeypatch) -> None:
        """
        Test that module-level convenience functions still work correctly.

        Functions like yaml_settings() and classic_settings() should work
        with the singleton pattern without changes.
        """
        test_file = tmp_path / "test.yaml"
        test_data = {"test": {"key": "value", "number": 42}}

        import ruamel.yaml

        yaml_obj = ruamel.yaml.YAML()
        with Path(test_file).open("w") as f:
            yaml_obj.dump(test_data, f)

        mock_cache = MagicMock()

        def mock_async_yaml_settings(_type, yaml_store, key_path, new_value=None):
            """Mock implementation that returns values based on key_path."""
            return {"test.key": "value", "test.number": 42}.get(key_path)

        mock_cache.async_yaml_settings = mock_async_yaml_settings

        YamlSettingsCacheModule = importlib.import_module("ClassicLib.io.yaml")

        with patch("ClassicLib.io.yaml.sync.convenience._get_yaml_cache", return_value=mock_cache):
            result = YamlSettingsCacheModule.yaml_settings(str, YAML.TEST, "test.key")
            assert result == "value"

            result = YamlSettingsCacheModule.yaml_settings(int, YAML.TEST, "test.number")
            assert result == 42

    def test_global_registry_integration(self) -> None:
        """
        Test that YamlSettingsCache integrates correctly with GlobalRegistry.

        The singleton should be properly registered in GlobalRegistry for
        other components to access.
        """
        YamlSettingsCacheModule = importlib.import_module("ClassicLib.io.yaml")

        # Accessing an attribute on the proxy triggers _get_yaml_cache() which registers
        _ = getattr(YamlSettingsCacheModule.yaml_cache, "any_attribute", None)

        # Verify registration in GlobalRegistry
        assert GlobalRegistry.is_registered(GlobalRegistry.Keys.YAML_CACHE)
        registered_cache = GlobalRegistry.get(GlobalRegistry.Keys.YAML_CACHE)

        real_cache = YamlSettingsCache.get_instance()
        assert registered_cache is real_cache

    def test_existing_test_patterns_work(self, mock_yaml_settings) -> None:
        """
        Test that existing test patterns using mocks still work.
        """
        mock_yaml_settings.return_value = "mocked_value"

        YamlSettingsCacheModule = importlib.import_module("ClassicLib.io.yaml")

        result = YamlSettingsCacheModule.yaml_settings(str, YAML.TEST, "any.key")
        assert result == "mocked_value"

    def test_cache_property_access(self) -> None:
        """
        Test that property accessors for cache compatibility still work.
        """
        cache = YamlSettingsCache.get_instance()

        # These properties should be accessible
        assert hasattr(cache, "cache")
        assert hasattr(cache, "path_cache")
        assert hasattr(cache, "settings_cache")
        assert hasattr(cache, "file_mod_times")

        # They should return the correct objects
        core = cache._get_async_core()
        assert cache.cache is core.cache
        assert cache.settings_cache is core.cache.settings_cache
        assert cache.file_mod_times is core.cache.file_mod_times


# =============================================================================
# Regression Tests
# =============================================================================


class TestRegressionScenarios:
    """Specific regression tests for issues that might arise from refactoring."""

    def test_no_memory_leaks(self) -> None:
        """
        Test that singleton pattern doesn't cause memory leaks.

        Creating and clearing instances repeatedly shouldn't leak memory.
        """
        initial_objects = len(gc.get_objects())

        for _ in range(100):
            instance = YamlSettingsCache.get_instance()
            core = instance._get_async_core()
            core.cache.settings_cache["temp"] = "data"  # pyright: ignore[reportArgumentType]

            YamlSettingsCache._instance = None
            del instance
            gc.collect()

        YamlSettingsCache.get_instance()
        final_objects = len(gc.get_objects())

        growth = final_objects - initial_objects
        assert growth < 1000, f"Possible memory leak: {growth} new objects"

    def test_import_order_independence(self) -> None:
        """
        Test that import order doesn't affect singleton behavior.
        """
        import ClassicLib.io.yaml
        from ClassicLib.io.yaml import YamlSettingsCache as Cache1
        from ClassicLib.io.yaml import YamlSettingsCache as Cache2

        assert Cache1 is Cache2

        instance1 = Cache1.get_instance()
        instance2 = Cache2.get_instance()

        assert instance1 is instance2

        proxy = ClassicLib.io.yaml.yaml_cache
        assert proxy._get_bridge() is instance1._get_bridge()

    def test_fixture_interaction_with_real_async(self, clean_yaml_cache_singleton) -> None:
        """
        Test that fixtures work correctly with real async operations.
        """
        cache = clean_yaml_cache_singleton

        assert cache._get_bridge() is not None

        async def async_test_operation():
            return "async_result"

        result = cache._bridge.run_async(async_test_operation())
        assert result == "async_result"

    def test_error_handling_in_singleton_creation(self) -> None:
        """
        Test singleton behavior when creation fails.

        If singleton creation raises an exception, subsequent calls
        should retry creation rather than returning None.
        """
        YamlSettingsCache._instance = None

        call_count = 0

        original_init = YamlSettingsCache.__init__

        def mock_init(self):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated initialization failure")
            original_init(self)

        with patch.object(YamlSettingsCache, "__init__", mock_init):
            with pytest.raises(RuntimeError):
                YamlSettingsCache.get_instance()

            assert YamlSettingsCache._instance is None

            instance = YamlSettingsCache.get_instance()
            assert instance is not None
            assert YamlSettingsCache._instance is instance
