"""Tests for basic GlobalRegistry operations."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from pathlib import Path
from typing import Any

import pytest

from ClassicLib import GlobalRegistry


class TestBasicRegistryOperations:
    """Tests for basic registry operations."""

    def test_register_get_basic_functionality(self) -> None:
        """Test basic register and get functionality."""
        # Test registering and retrieving a string
        GlobalRegistry.register("test_key", "test_value")
        result = GlobalRegistry.get("test_key")
        assert result == "test_value"

        # Test registering and retrieving different types
        GlobalRegistry.register("test_int", 42)
        assert GlobalRegistry.get("test_int") == 42

        GlobalRegistry.register("test_list", [1, 2, 3])
        assert GlobalRegistry.get("test_list") == [1, 2, 3]

        GlobalRegistry.register("test_dict", {"key": "value"})
        assert GlobalRegistry.get("test_dict") == {"key": "value"}

    def test_get_nonexistent_key(self) -> None:
        """Test get with nonexistent key returns None."""
        result = GlobalRegistry.get("nonexistent_key")
        assert result is None

    def test_register_overwrite_existing_key(self) -> None:
        """Test that registering overwrites existing values."""
        # Register initial value
        GlobalRegistry.register("test_key", "initial_value")
        assert GlobalRegistry.get("test_key") == "initial_value"

        # Overwrite with new value
        GlobalRegistry.register("test_key", "new_value")
        assert GlobalRegistry.get("test_key") == "new_value"

    def test_is_registered_functionality(self) -> None:
        """Test the is_registered method."""
        # Test non-existing key
        assert not GlobalRegistry.is_registered("test_key")

        # Register a key
        GlobalRegistry.register("test_key", "value")
        assert GlobalRegistry.is_registered("test_key")

        # Test that None values are still considered registered
        GlobalRegistry.register("null_key", None)
        assert GlobalRegistry.is_registered("null_key")

    def test_key_constants(self) -> None:
        """Test that registry key constants are properly defined."""
        # Check that all required Keys are defined
        keys = GlobalRegistry.Keys

        # Verify all expected keys are present
        assert hasattr(keys, "YAML_CACHE")
        assert hasattr(keys, "MANUAL_DOCS_GUI")
        assert hasattr(keys, "GAME_PATH_GUI")
        assert hasattr(keys, "IS_GUI_MODE")
        assert hasattr(keys, "VR")
        assert hasattr(keys, "GAME")
        assert hasattr(keys, "LOCAL_DIR")
        assert hasattr(keys, "OPEN_FILE_FUNC")
        assert hasattr(keys, "IS_PRERELEASE")

    def test_complex_object_storage(self) -> None:
        """Test storing and retrieving complex objects."""

        class TestClass:
            def __init__(self, value: int) -> None:
                self.value = value

            def get_value(self) -> int:
                return self.value

        # Register an instance
        obj = TestClass(42)
        GlobalRegistry.register("test_object", obj)

        # Retrieve and verify
        retrieved = GlobalRegistry.get("test_object")
        assert retrieved is obj
        assert retrieved.get_value() == 42

    def test_key_validation(self) -> None:
        """Test that keys can be any hashable type."""
        # Test with string key
        GlobalRegistry.register("string_key", "value")
        assert GlobalRegistry.get("string_key") == "value"

        # Test with integer key
        GlobalRegistry.register(42, "int_value")
        assert GlobalRegistry.get(42) == "int_value"

        # Test with tuple key
        GlobalRegistry.register(("tuple", "key"), "tuple_value")
        assert GlobalRegistry.get(("tuple", "key")) == "tuple_value"
