"""Tests for GlobalRegistry state management and validation."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import pytest

from ClassicLib.core.registry import GlobalRegistry

pytestmark = [pytest.mark.unit]


class TestStateManagement:
    """Tests for registry state management."""

    def test_state_persistence_across_calls(self) -> None:
        """Test that registry state persists across multiple calls."""
        # Register multiple values
        GlobalRegistry.register("key1", "value1")
        GlobalRegistry.register("key2", "value2")
        GlobalRegistry.register("key3", "value3")

        # Verify all values are still accessible
        assert GlobalRegistry.get("key1") == "value1"
        assert GlobalRegistry.get("key2") == "value2"
        assert GlobalRegistry.get("key3") == "value3"

        # Modify one value
        GlobalRegistry.register("key2", "modified_value2")

        # Verify the change and that others remain unchanged
        assert GlobalRegistry.get("key1") == "value1"
        assert GlobalRegistry.get("key2") == "modified_value2"
        assert GlobalRegistry.get("key3") == "value3"

    def test_registry_isolation(self) -> None:
        """Test that registry maintains isolation between different keys."""
        # Register values with similar key names
        GlobalRegistry.register("test", "value1")
        GlobalRegistry.register("test_key", "value2")
        GlobalRegistry.register("test_key_extended", "value3")

        # Each should maintain its own value
        assert GlobalRegistry.get("test") == "value1"
        assert GlobalRegistry.get("test_key") == "value2"
        assert GlobalRegistry.get("test_key_extended") == "value3"

    def test_registry_clear_functionality(self) -> None:
        """Test clearing the registry."""
        # Register some values
        GlobalRegistry.register("key1", "value1")
        GlobalRegistry.register("key2", "value2")

        # Verify they exist
        assert GlobalRegistry.is_registered("key1")
        assert GlobalRegistry.is_registered("key2")

        # Clear the registry using the public API
        GlobalRegistry.clear()

        # Verify they're gone
        assert not GlobalRegistry.is_registered("key1")
        assert not GlobalRegistry.is_registered("key2")
        assert GlobalRegistry.get("key1") is None
        assert GlobalRegistry.get("key2") is None

    def test_none_value_handling(self) -> None:
        """Test handling of None values in the registry."""
        # Register None value
        GlobalRegistry.register("none_key", None)

        # Should be registered
        assert GlobalRegistry.is_registered("none_key")

        # Should return None
        assert GlobalRegistry.get("none_key") is None

        # Different from non-existent key
        assert not GlobalRegistry.is_registered("nonexistent_key")
        assert GlobalRegistry.get("nonexistent_key") is None

    def test_mutable_object_reference(self) -> None:
        """Test that mutable objects are stored by reference."""
        # Register a mutable object
        test_list = [1, 2, 3]
        GlobalRegistry.register("mutable_list", test_list)

        # Modify the original list
        test_list.append(4)

        # The registry should reflect the change (same reference)
        retrieved = GlobalRegistry.get("mutable_list")
        assert retrieved == [1, 2, 3, 4]
        assert retrieved is test_list

    def test_registry_with_special_characters_in_keys(self) -> None:
        """Test registry with special characters in keys."""
        # Test various special characters in keys
        special_keys = [
            "key.with.dots",
            "key-with-dashes",
            "key_with_underscores",
            "key:with:colons",
            "key/with/slashes",
            "key\\with\\backslashes",
            "key with spaces",
            "key\twith\ttabs",
            "кириллица",  # Cyrillic
            "中文",  # Chinese
            "😀emoji",  # Emoji
        ]

        for i, key in enumerate(special_keys):
            GlobalRegistry.register(key, f"value_{i}")
            assert GlobalRegistry.get(key) == f"value_{i}"
            assert GlobalRegistry.is_registered(key)
