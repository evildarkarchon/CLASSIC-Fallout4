"""
Tests for YamlSettingsCache backward compatibility and regression scenarios.

This module validates that the singleton refactoring maintains backward
compatibility with existing code patterns, module-level functions, GlobalRegistry
integration, and existing test patterns.

Test Categories:
- Module-level convenience functions
- GlobalRegistry integration
- Existing test pattern compatibility
- Cache property access
- Memory leak prevention
- Import order independence
- Error handling during creation
"""

import gc
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML
from ClassicLib.YamlSettings import YamlSettingsCache

pytestmark = pytest.mark.unit


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility with existing code."""

    def test_module_level_functions_work(self, tmp_path: Path, monkeypatch) -> None:
        """
        Test that module-level convenience functions still work correctly.

        Functions like yaml_settings() and classic_settings() should work
        with the singleton pattern without changes.
        """
        # Create a test YAML file
        test_file = tmp_path / "test.yaml"
        test_data = {"test": {"key": "value", "number": 42}}

        import ruamel.yaml

        yaml_obj = ruamel.yaml.YAML()
        with Path(test_file).open("w") as f:
            yaml_obj.dump(test_data, f)

        # Mock yaml_cache which is used by yaml_settings function
        # Use MagicMock without spec for more flexible mocking
        mock_cache = MagicMock()

        # Configure the mock to return specific values based on key_path
        def mock_async_yaml_settings(_type, yaml_store, key_path, new_value=None):
            """Mock implementation that returns values based on key_path."""
            return {"test.key": "value", "test.number": 42}.get(key_path)

        mock_cache.async_yaml_settings = mock_async_yaml_settings

        # Patch the module-level yaml_cache
        # Use importlib to ensure we target the module
        import importlib

        YamlSettingsCacheModule = importlib.import_module("ClassicLib.YamlSettings")

        # We need to patch _get_yaml_cache in the convenience module where yaml_settings is defined
        with patch("ClassicLib.YamlSettings.sync.convenience._get_yaml_cache", return_value=mock_cache):
            # Test yaml_settings function from the module
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
        # Import should trigger registration
        import importlib

        YamlSettingsCacheModule = importlib.import_module("ClassicLib.YamlSettings")

        # Manually ensure registration if cleared (since module load only happens once)
        # Accessing an attribute on the proxy triggers _get_yaml_cache() which registers the real instance
        _ = getattr(YamlSettingsCacheModule.yaml_cache, "any_attribute", None)

        # Verify registration in GlobalRegistry
        assert GlobalRegistry.is_registered(GlobalRegistry.Keys.YAML_CACHE)
        registered_cache = GlobalRegistry.get(GlobalRegistry.Keys.YAML_CACHE)

        # Should be the same as singleton and module-level instances
        # Note: module.yaml_cache is a proxy in the new implementation,
        # but get_instance() returns the real instance.
        # The proxy returns the real instance when called or accessed.
        # GlobalRegistry might store the proxy or the real instance depending on implementation.
        # _get_yaml_cache() registers the real instance.

        # Force resolution
        real_cache = YamlSettingsCache.get_instance()

        # The registered object should be the real cache OR the proxy
        # Based on _get_yaml_cache implementation, it registers the real instance
        assert registered_cache is real_cache

    def test_existing_test_patterns_work(self, mock_yaml_settings) -> None:
        """
        Test that existing test patterns using mocks still work.

        Tests that mock yaml_settings or patch YamlSettingsCache still
        function correctly with the singleton pattern.
        """
        # Mock should work as before
        mock_yaml_settings.return_value = "mocked_value"

        # This simulates how existing tests use mocks
        # Note: yaml_settings is a module-level function, not a class method

        # The mock should intercept calls when patched properly
        # The mock_yaml_settings fixture patches the module function
        # We need to ensure we call the function from the module to see the patch
        import importlib

        YamlSettingsCacheModule = importlib.import_module("ClassicLib.YamlSettings")

        result = YamlSettingsCacheModule.yaml_settings(str, YAML.TEST, "any.key")
        assert result == "mocked_value"

    def test_cache_property_access(self) -> None:
        """
        Test that property accessors for cache compatibility still work.

        The cache, path_cache, settings_cache properties should be accessible
        for backward compatibility with tests that access them directly.
        """
        cache = YamlSettingsCache.get_instance()

        # These properties should be accessible
        assert hasattr(cache, "cache")
        assert hasattr(cache, "path_cache")
        assert hasattr(cache, "settings_cache")
        assert hasattr(cache, "file_mod_times")

        # They should return the correct objects
        # Ensure initialized
        core = cache._get_async_core()
        assert cache.cache is core.cache
        assert cache.settings_cache is core.cache.settings_cache
        assert cache.file_mod_times is core.cache.file_mod_times


class TestRegressionScenarios:
    """Specific regression tests for issues that might arise from refactoring."""

    def test_no_memory_leaks(self) -> None:
        """
        Test that singleton pattern doesn't cause memory leaks.

        Creating and clearing instances repeatedly shouldn't leak memory.
        """
        initial_objects = len(gc.get_objects())

        for _ in range(100):
            # Get instance
            instance = YamlSettingsCache.get_instance()

            # Use it
            # Ensure initialized
            core = instance._get_async_core()
            core.cache.settings_cache["temp"] = "data"  # pyright: ignore[reportArgumentType]

            # Clear it (simulate fixture cleanup)
            YamlSettingsCache._instance = None
            del instance
            gc.collect()

        # Get final instance for comparison
        YamlSettingsCache.get_instance()
        final_objects = len(gc.get_objects())

        # Should not have significant memory growth
        # Allow some growth for Python internals, but not 100x instances
        growth = final_objects - initial_objects
        assert growth < 1000, f"Possible memory leak: {growth} new objects"

    def test_import_order_independence(self) -> None:
        """
        Test that import order doesn't affect singleton behavior.

        The singleton should work correctly regardless of import order.
        """
        # Import everything first
        import ClassicLib.YamlSettings
        from ClassicLib.YamlSettings import YamlSettingsCache as Cache1
        from ClassicLib.YamlSettings import YamlSettingsCache as Cache2

        # All should reference the same class
        assert Cache1 is Cache2

        # Get instances from different import aliases
        instance1 = Cache1.get_instance()
        instance2 = Cache2.get_instance()

        # All should be the same singleton
        assert instance1 is instance2

        # The yaml_cache proxy should resolve to the same singleton
        # Note: yaml_cache is a proxy, accessing _get_bridge triggers resolution
        proxy = ClassicLib.YamlSettings.yaml_cache
        assert proxy._get_bridge() is instance1._get_bridge()

    def test_fixture_interaction_with_real_async(self, clean_yaml_cache_singleton) -> None:
        """
        Test that fixtures work correctly with real async operations.

        The singleton uses AsyncBridge which manages real async operations.
        This test ensures fixtures don't break async functionality.
        """
        cache = clean_yaml_cache_singleton

        # Should have AsyncBridge
        # Ensure initialized
        assert cache._get_bridge() is not None

        # Test async operation through bridge
        async def async_test_operation():
            return "async_result"

        # This should work through the bridge
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

        # Mock __init__ to fail first time, succeed second time
        original_init = YamlSettingsCache.__init__

        def mock_init(self):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated initialization failure")
            original_init(self)

        with patch.object(YamlSettingsCache, "__init__", mock_init):
            # First call should fail
            with pytest.raises(RuntimeError):
                YamlSettingsCache.get_instance()

            # Instance should not be set after failure
            assert YamlSettingsCache._instance is None

            # Second call should succeed
            instance = YamlSettingsCache.get_instance()
            assert instance is not None
            assert YamlSettingsCache._instance is instance
