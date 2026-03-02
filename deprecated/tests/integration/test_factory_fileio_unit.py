"""Unit tests for file I/O factory functions in ClassicLib.integration.factory.

This module tests the factory functions for file I/O and YAML operations,
including singleton behavior and fallback to Python implementations.
"""

import threading
from unittest.mock import patch

import pytest

import ClassicLib.integration.factory as factory_module

pytestmark = [pytest.mark.unit]


class TestGetFileIO:
    """Tests for get_file_io function."""

    def test_returns_file_io_instance(self) -> None:
        """Test returns a FileIOCore instance."""
        original = factory_module._file_io_instance
        factory_module._file_io_instance = None

        try:
            from ClassicLib.integration.factory import get_file_io

            result = get_file_io()

            assert result is not None
        finally:
            factory_module._file_io_instance = original

    def test_returns_same_instance_on_multiple_calls(self) -> None:
        """Test returns same singleton instance on multiple calls."""
        original = factory_module._file_io_instance
        factory_module._file_io_instance = None

        try:
            from ClassicLib.integration.factory import get_file_io

            instance1 = get_file_io()
            instance2 = get_file_io()

            assert instance1 is instance2
        finally:
            factory_module._file_io_instance = original

    def test_accepts_encoding_parameter(self) -> None:
        """Test accepts encoding parameter."""
        original = factory_module._file_io_instance
        factory_module._file_io_instance = None

        try:
            from ClassicLib.integration.factory import get_file_io

            result = get_file_io(encoding="utf-16")

            assert result is not None
        finally:
            factory_module._file_io_instance = original

    def test_accepts_errors_parameter(self) -> None:
        """Test accepts errors parameter."""
        original = factory_module._file_io_instance
        factory_module._file_io_instance = None

        try:
            from ClassicLib.integration.factory import get_file_io

            result = get_file_io(errors="replace")

            assert result is not None
        finally:
            factory_module._file_io_instance = original

    def test_raises_import_error_when_rust_unavailable(self) -> None:
        """Test raises ImportError when Rust import fails."""
        import builtins

        original = factory_module._file_io_instance
        factory_module._file_io_instance = None

        try:
            from ClassicLib.integration.factory import get_file_io

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if "file_io_rust" in str(args) or name == "ClassicLib.integration.rust.file_io_rust":
                    raise ImportError("No module")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                with pytest.raises(ImportError, match="No module"):
                    get_file_io()
        finally:
            factory_module._file_io_instance = original


class TestGetYamlOperations:
    """Tests for get_yaml_operations function."""

    def test_raises_import_error_on_import_failure(self) -> None:
        """Test raises ImportError when required YAML binding is missing."""
        import builtins

        from ClassicLib.integration.factory import get_yaml_operations

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "classic_yaml":
                raise ImportError("No module")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", mock_import):
            with pytest.raises(ImportError, match="classic_yaml"):
                get_yaml_operations()


class TestModuleCaching:
    """Tests for module-level caching behavior."""

    def test_file_io_instance_starts_as_none(self) -> None:
        """Test _file_io_instance attribute exists on the module."""
        assert hasattr(factory_module, "_file_io_instance")

    def test_file_io_lock_exists(self) -> None:
        """Test _file_io_lock exists for thread safety."""
        assert hasattr(factory_module, "_file_io_lock")
        assert isinstance(factory_module._file_io_lock, type(threading.Lock()))
