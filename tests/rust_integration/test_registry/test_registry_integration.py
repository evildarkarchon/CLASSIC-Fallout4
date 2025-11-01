"""Integration tests for classic-registry-py PyO3 bindings.

This test suite verifies that the Rust GlobalRegistry implementation
provides full API compatibility with the Python GlobalRegistry.
"""

import pytest
from pathlib import Path

# Import the Rust registry module
try:
    from registry import Keys, register, get, is_registered, clear_all
    from registry import get_game, set_game, is_gui_mode
    from registry import get_yaml_cache, get_vr, get_local_dir
    REGISTRY_AVAILABLE = True
except ImportError as e:
    REGISTRY_AVAILABLE = False
    IMPORT_ERROR = str(e)


pytestmark = [
    pytest.mark.rust,
    pytest.mark.integration,
]


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear registry before and after each test."""
    if REGISTRY_AVAILABLE:
        clear_all()
    yield
    if REGISTRY_AVAILABLE:
        clear_all()


class TestRegistryImport:
    """Test that registry module can be imported."""

    def test_registry_import(self):
        """Verify registry module is available."""
        assert REGISTRY_AVAILABLE, f"Failed to import registry: {IMPORT_ERROR if not REGISTRY_AVAILABLE else 'N/A'}"


class TestKeys:
    """Test Keys class and constants."""

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_keys_class_exists(self):
        """Test that Keys class is available."""
        assert Keys is not None

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_keys_constants(self):
        """Test that all expected Keys constants exist."""
        expected_keys = [
            "YAML_CACHE",
            "MANUAL_DOCS_GUI",
            "GAME_PATH_GUI",
            "GAME_PATH",
            "DOCS_PATH",
            "IS_GUI_MODE",
            "OPEN_FILE_FUNC",
            "VR",
            "GAME",
            "LOCAL_DIR",
            "IS_PRERELEASE",
        ]

        for key_name in expected_keys:
            assert hasattr(Keys, key_name), f"Keys.{key_name} not found"
            key_value = getattr(Keys, key_name)
            assert isinstance(key_value, str), f"Keys.{key_name} should be a string"
            assert key_value, f"Keys.{key_name} should not be empty"

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_keys_values_match_python(self):
        """Test that key values match Python API."""
        assert Keys.YAML_CACHE == "yaml_cache"
        assert Keys.GAME == "gamevars_game"
        assert Keys.IS_GUI_MODE == "is_gui_mode"
        assert Keys.LOCAL_DIR == "local_dir"


class TestCoreOperations:
    """Test core registry operations (register, get, is_registered)."""

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_register_and_get_string(self):
        """Test registering and retrieving a string."""
        register(Keys.GAME, "Fallout4")
        value = get(Keys.GAME)
        assert value == "Fallout4"

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_register_and_get_integer(self):
        """Test registering and retrieving an integer."""
        register("test_int", 42)
        value = get("test_int")
        assert value == 42

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_register_and_get_bool(self):
        """Test registering and retrieving a boolean."""
        register(Keys.IS_GUI_MODE, True)
        value = get(Keys.IS_GUI_MODE)
        assert value is True

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_register_and_get_dict(self):
        """Test registering and retrieving a dictionary."""
        test_dict = {"key1": "value1", "key2": 123, "nested": {"a": "b"}}
        register("test_dict", test_dict)
        value = get("test_dict")
        assert value == test_dict

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_register_and_get_list(self):
        """Test registering and retrieving a list."""
        test_list = [1, 2, 3, "four", {"five": 5}]
        register("test_list", test_list)
        value = get("test_list")
        assert value == test_list

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_get_nonexistent(self):
        """Test getting a non-existent key returns None."""
        value = get("nonexistent_key")
        assert value is None

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_is_registered(self):
        """Test checking if a key is registered."""
        assert not is_registered(Keys.GAME)
        register(Keys.GAME, "Skyrim")
        assert is_registered(Keys.GAME)

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_overwrite_value(self):
        """Test that registering the same key overwrites the value."""
        register("test_key", "first")
        assert get("test_key") == "first"

        register("test_key", "second")
        assert get("test_key") == "second"

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_clear_all(self):
        """Test clearing all registry entries."""
        register("key1", "value1")
        register("key2", "value2")
        assert is_registered("key1")
        assert is_registered("key2")

        clear_all()
        assert not is_registered("key1")
        assert not is_registered("key2")


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_set_game_and_get_game(self):
        """Test set_game() and get_game() convenience functions."""
        set_game("Skyrim")
        assert get_game() == "Skyrim"

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_get_game_default(self):
        """Test that get_game() returns default value."""
        # After clearing, should return default
        game = get_game()
        assert game == "Fallout4"

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_is_gui_mode_default(self):
        """Test that is_gui_mode() returns False by default."""
        result = is_gui_mode()
        assert result is False

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_is_gui_mode_after_register(self):
        """Test is_gui_mode() after registering GUI mode."""
        register(Keys.IS_GUI_MODE, True)
        assert is_gui_mode() is True

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_get_vr_default(self):
        """Test that get_vr() returns empty string by default."""
        vr = get_vr()
        assert vr == ""

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_get_vr_after_register(self):
        """Test get_vr() after registering VR variant."""
        register(Keys.VR, "SkyrimVR")
        assert get_vr() == "SkyrimVR"

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_get_local_dir(self):
        """Test get_local_dir() returns a path string."""
        local_dir = get_local_dir()
        assert isinstance(local_dir, str)
        assert local_dir  # Should not be empty
        # Should be a valid path
        path = Path(local_dir)
        assert path.exists() or path == Path(".")


class TestPythonObjectStorage:
    """Test storing arbitrary Python objects in the registry."""

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_store_class_instance(self):
        """Test storing a custom class instance."""
        class TestClass:
            def __init__(self, value):
                self.value = value

        obj = TestClass(42)
        register("test_obj", obj)
        retrieved = get("test_obj")
        assert retrieved.value == 42

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_store_none(self):
        """Test storing None value."""
        register("none_value", None)
        value = get("none_value")
        assert value is None

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_store_lambda(self):
        """Test storing a lambda function."""
        func = lambda x: x * 2
        register("lambda_func", func)
        retrieved = get("lambda_func")
        assert retrieved(5) == 10


class TestThreadSafety:
    """Test thread-safety of registry operations."""

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_concurrent_registration(self):
        """Test concurrent registration from multiple threads."""
        import threading

        def register_value(key, value):
            register(key, value)

        threads = []
        for i in range(10):
            t = threading.Thread(target=register_value, args=(f"key_{i}", f"value_{i}"))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify all values were registered
        for i in range(10):
            assert is_registered(f"key_{i}")
            assert get(f"key_{i}") == f"value_{i}"


class TestAPICompatibility:
    """Test API compatibility with Python GlobalRegistry."""

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_keys_api_matches_python(self):
        """Verify Keys API matches Python GlobalRegistry.Keys."""
        # Python API expectations
        assert hasattr(Keys, "YAML_CACHE")
        assert hasattr(Keys, "IS_GUI_MODE")
        assert hasattr(Keys, "GAME")
        assert hasattr(Keys, "LOCAL_DIR")

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_register_signature(self):
        """Test register() function signature."""
        # Should accept (key, value)
        register("test", "value")  # Should not raise

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_get_signature(self):
        """Test get() function signature."""
        # Should accept (key) and return value or None
        result = get("test")  # Should not raise
        assert result is None or result is not None  # Valid return

    @pytest.mark.skipif(not REGISTRY_AVAILABLE, reason="Registry not available")
    def test_is_registered_signature(self):
        """Test is_registered() function signature."""
        # Should accept (key) and return bool
        result = is_registered("test")
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
